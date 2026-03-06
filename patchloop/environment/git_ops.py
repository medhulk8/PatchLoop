from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


class GitOps:
    """
    Thin subprocess wrapper around git commands for a specific directory.

    We use raw subprocess (not GitPython) because:
    - `git apply` flag control is cleaner via CLI
    - Diff format is exactly what we need without translation
    - Fewer abstraction layers = easier debugging
    """

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir

    def _run(self, *args: str, timeout: int = 30) -> tuple[int, str, str]:
        result = subprocess.run(
            ["git", *args],
            cwd=self.workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        self._run("init")
        # Set a local identity so commits don't fail in CI or fresh environments
        self._run("config", "user.name", "patchloop-agent")
        self._run("config", "user.email", "agent@patchloop.local")

    def add_all(self) -> None:
        self._run("add", "-A")

    # ------------------------------------------------------------------ #
    # Committing
    # ------------------------------------------------------------------ #

    def commit(self, message: str) -> str:
        """Stage all changes, commit, return the short SHA."""
        self.add_all()
        rc, stdout, stderr = self._run("commit", "-m", message, "--allow-empty")
        if rc != 0:
            raise RuntimeError(f"git commit failed: {stderr.strip()}")
        # stdout looks like: "[main abc1234] message"
        for line in stdout.splitlines():
            if line.startswith("["):
                return line.split()[1].rstrip("]")
        return "unknown"

    # ------------------------------------------------------------------ #
    # Diff / status
    # ------------------------------------------------------------------ #

    def diff(self) -> str:
        """Unified diff of working tree + staged changes vs HEAD."""
        _, staged, _ = self._run("diff", "--cached", "HEAD")
        _, unstaged, _ = self._run("diff", "HEAD")
        return staged or unstaged

    def diff_stat(self) -> str:
        _, stdout, _ = self._run("diff", "HEAD", "--stat")
        return stdout

    # ------------------------------------------------------------------ #
    # Patching
    # ------------------------------------------------------------------ #

    def apply_patch(self, diff: str) -> tuple[bool, str]:
        """
        Apply a unified diff string via `git apply`.

        Writes the diff to a temp file (git apply requires a file path,
        not stdin, for reliable whitespace handling).
        Returns (success, message).
        """
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".patch", delete=False, encoding="utf-8"
        ) as f:
            f.write(diff)
            patch_path = f.name

        try:
            rc, stdout, stderr = self._run(
                "apply", "--whitespace=fix", patch_path
            )
            if rc != 0:
                return False, stderr.strip()
            return True, stdout.strip()
        finally:
            os.unlink(patch_path)

    # ------------------------------------------------------------------ #
    # Reset
    # ------------------------------------------------------------------ #

    def reset_hard(self, ref: str = "HEAD") -> None:
        """Hard reset to ref, discarding all local changes and untracked files."""
        self._run("reset", "--hard", ref)
        self._run("clean", "-fd")

    def initial_sha(self) -> str:
        """Return the SHA of the very first commit (our clean snapshot)."""
        _, stdout, _ = self._run("rev-list", "--max-parents=0", "HEAD")
        return stdout.strip()

    def current_sha(self) -> str:
        _, stdout, _ = self._run("rev-parse", "HEAD")
        return stdout.strip()

    def log_oneline(self, n: int = 10) -> str:
        _, stdout, _ = self._run("log", f"-{n}", "--oneline")
        return stdout
