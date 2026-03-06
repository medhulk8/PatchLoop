from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from patchloop.environment.base import Environment
from patchloop.environment.git_ops import GitOps
from patchloop.environment.task import Task, TestResult


class LocalEnvironment(Environment):
    """
    Sandboxed environment using a temp directory + subprocess.

    Design decisions:
    - Each task gets its own TemporaryDirectory. The source repo is NEVER
      modified — we copy it in and operate on the copy.
    - A clean single-commit git snapshot is created on setup(). This gives
      us a stable reset target and a git history to replay patches.
    - reset() does `git reset --hard <initial_sha>` instead of re-copying.
      This is ~10x faster and preserves the full iteration commit history.
    - All commands run with subprocess (no Docker overhead). This is Phase 1;
      Docker is a drop-in for Phase 2 via the same Environment interface.
    """

    def __init__(self, task: Task) -> None:
        super().__init__(task)
        self._tmpdir: tempfile.TemporaryDirectory | None = None
        self._workdir: Path | None = None
        self._git: GitOps | None = None
        self._snapshot_sha: str | None = None   # the clean-state commit SHA

    # ------------------------------------------------------------------ #
    # Properties (guard against use before setup)
    # ------------------------------------------------------------------ #

    @property
    def workdir(self) -> Path:
        if self._workdir is None:
            raise RuntimeError("Environment not set up. Call setup() first.")
        return self._workdir

    @property
    def git(self) -> GitOps:
        if self._git is None:
            raise RuntimeError("Environment not set up. Call setup() first.")
        return self._git

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def setup(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(
            prefix=f"patchloop_{self.task.task_id}_"
        )
        self._workdir = Path(self._tmpdir.name) / "repo"
        self._copy_repo()
        self._git = GitOps(self._workdir)
        self._snapshot_sha = self._init_git_snapshot()
        if self.task.setup_cmd:
            self._run_setup()

    def teardown(self) -> None:
        if self._tmpdir:
            self._tmpdir.cleanup()
        self._tmpdir = None
        self._workdir = None
        self._git = None
        self._snapshot_sha = None

    def reset(self) -> None:
        """
        Reset to the initial clean snapshot.

        Uses git reset --hard instead of re-copying the repo. This:
        1. Is ~10x faster than a fresh copy
        2. Preserves the iteration commit history (good for replay/analysis)
        3. Removes any untracked files with `git clean -fd`
        """
        self.git.reset_hard(self._snapshot_sha)

    # ------------------------------------------------------------------ #
    # File operations
    # ------------------------------------------------------------------ #

    def read_file(self, path: str) -> str:
        target = self.workdir / path
        if not target.exists():
            raise FileNotFoundError(f"Not found in workspace: {path}")
        return target.read_text(encoding="utf-8", errors="replace")

    def list_files(self, pattern: str = "**/*.py") -> list[str]:
        return sorted(
            str(p.relative_to(self.workdir))
            for p in self.workdir.glob(pattern)
            if not any(part.startswith(".") for part in p.relative_to(self.workdir).parts)
            and p.is_file()
        )

    def search_code(self, query: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for py_file in sorted(self.workdir.rglob("*.py")):
            rel = py_file.relative_to(self.workdir)
            if any(part.startswith(".") for part in rel.parts):
                continue
            try:
                lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, start=1):
                    if query.lower() in line.lower():
                        results.append({"file": str(rel), "line": i, "text": line.rstrip()})
            except Exception:
                continue
        return results[:50]  # cap to avoid flooding LLM context

    # ------------------------------------------------------------------ #
    # Patching
    # ------------------------------------------------------------------ #

    def apply_patch(self, diff: str) -> tuple[bool, str]:
        return self.git.apply_patch(diff)

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def run_tests(self) -> TestResult:
        start = time.monotonic()
        rc, stdout, stderr = self.run_cmd(
            self.task.test_cmd, timeout=self.task.time_limit_s
        )
        duration = round(time.monotonic() - start, 2)
        return TestResult(
            passed=(rc == 0),
            returncode=rc,
            stdout=stdout[:8000],   # cap — avoid multi-MB logs
            stderr=stderr[:4000],
            duration_s=duration,
        )

    def run_cmd(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout}s"

    # ------------------------------------------------------------------ #
    # Git
    # ------------------------------------------------------------------ #

    def git_diff(self) -> str:
        return self.git.diff()

    def git_commit(self, message: str) -> str:
        return self.git.commit(message)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _copy_repo(self) -> None:
        shutil.copytree(
            self.task.repo,
            self._workdir,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.pyo"),
        )

    def _init_git_snapshot(self) -> str:
        """
        Initialize a fresh git repo in the workspace and create a single
        'snapshot' commit. Returns the commit SHA.

        This commit is our reset target — every iteration resets back here.
        """
        self.git.init()
        self.git.add_all()
        rc, stdout, stderr = self.git._run(
            "commit", "-m", f"snapshot: {self.task.task_id}", "--allow-empty"
        )
        if rc != 0 and "nothing to commit" not in stderr:
            raise RuntimeError(f"Failed to create snapshot commit: {stderr}")
        return self.git.current_sha()

    def _run_setup(self) -> None:
        rc, _, stderr = self.run_cmd(self.task.setup_cmd, timeout=120)
        if rc != 0:
            raise RuntimeError(
                f"setup_cmd failed for {self.task.task_id}:\n{stderr[:500]}"
            )
