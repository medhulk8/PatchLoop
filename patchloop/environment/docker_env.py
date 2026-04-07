from __future__ import annotations

import io
import posixpath
import shlex
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

import docker
from docker.errors import BuildError, DockerException, ImageNotFound
from docker.models.containers import Container

from patchloop.environment.base import Environment
from patchloop.environment.task import Task, TestResult


class DockerEnvironment(Environment):
    """
    Docker-based execution environment.

    Drop-in replacement for LocalEnvironment via the shared Environment
    interface. Each task runs in a fresh container with strict resource
    limits and no network access.
    """

    def __init__(self, task: Task, image: str = "patchloop-sandbox:latest") -> None:
        super().__init__(task)
        self.image = image
        self._client: docker.DockerClient | None = None
        self._container: Container | None = None
        self._snapshot_sha: str | None = None

    # ------------------------------------------------------------------ #
    # Properties (guard against use before setup)
    # ------------------------------------------------------------------ #

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    @property
    def container(self) -> Container:
        if self._container is None:
            raise RuntimeError("Environment not set up. Call setup() first.")
        return self._container

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def setup(self) -> None:
        if self.task.commit is not None:
            raise NotImplementedError(
                f"task.commit pinning is not yet supported in DockerEnvironment "
                f"(task: {self.task.task_id}, commit: {self.task.commit}). "
                "Implement via git archive or .git copy in Phase 2."
            )

        try:
            self._ensure_image()
            self._container = self.client.containers.run(
                self.image,
                command=["sleep", "infinity"],
                detach=True,
                working_dir="/workspace",
                nano_cpus=1_000_000_000,
                mem_limit="512m",
                pids_limit=64,
                network_disabled=True,
            )
            self._copy_repo_to_container()
            if self.task.setup_cmd:
                self._run_setup()
            self._snapshot_sha = self._init_git_snapshot()
        except Exception:
            self.teardown()
            raise

    def teardown(self) -> None:
        if self._container is not None:
            try:
                self._container.stop(timeout=1)
            except Exception:
                pass
            try:
                self._container.remove(force=True)
            except Exception:
                pass

        self._container = None
        self._snapshot_sha = None

        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def reset(self) -> None:
        if not self._snapshot_sha:
            raise RuntimeError("Environment not set up. Call setup() first.")
        self._git_run("reset", "--hard", self._snapshot_sha)
        self._git_run("clean", "-fd")

    # ------------------------------------------------------------------ #
    # File operations
    # ------------------------------------------------------------------ #

    def read_file(self, path: str) -> str:
        target = self._workspace_target(path)
        rc, stdout, stderr = self.run_cmd(f"cat {shlex.quote(target)}")
        if rc != 0:
            if "No such file or directory" in stderr:
                raise FileNotFoundError(f"Not found in workspace: {path}")
            raise RuntimeError(stderr.strip() or f"Failed to read file: {path}")
        return stdout

    def list_files(self, pattern: str = "**/*.py") -> list[str]:
        script = (
            "from pathlib import Path\n"
            "import json, sys\n"
            "workdir = Path('/workspace').resolve()\n"
            "results = []\n"
            "for p in workdir.glob(sys.argv[1]):\n"
            "    try:\n"
            "        resolved = p.resolve()\n"
            "    except Exception:\n"
            "        continue\n"
            "    if not str(resolved).startswith(str(workdir)):\n"
            "        continue\n"
            "    if not p.is_file():\n"
            "        continue\n"
            "    rel = resolved.relative_to(workdir)\n"
            "    if any(part.startswith('.') for part in rel.parts):\n"
            "        continue\n"
            "    results.append(str(rel))\n"
            "print(json.dumps(sorted(results)))\n"
        )
        cmd = f"python -c {shlex.quote(script)} {shlex.quote(pattern)}"
        rc, stdout, stderr = self.run_cmd(cmd)
        if rc != 0:
            raise RuntimeError(stderr.strip() or "Failed to list files")

        try:
            import json

            data = json.loads(stdout.strip() or "[]")
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception:
            pass
        return []

    def search_code(self, query: str) -> list[dict[str, Any]]:
        escaped_query = shlex.quote(query)
        cmd = (
            "grep -rni --include='*.py' --exclude-dir='.git' "
            f"{escaped_query} /workspace"
        )
        rc, stdout, _ = self.run_cmd(cmd)
        if rc not in (0, 1):
            return []

        results: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) != 3:
                continue
            file_path, line_no, text = parts
            rel_path = PurePosixPath(file_path).as_posix().replace("/workspace/", "", 1)
            rel_parts = PurePosixPath(rel_path).parts
            if any(part.startswith(".") for part in rel_parts):
                continue
            try:
                lineno = int(line_no)
            except ValueError:
                continue
            results.append({"file": rel_path, "line": lineno, "text": text.rstrip()})
            if len(results) >= 50:
                break

        return results

    # ------------------------------------------------------------------ #
    # Patching
    # ------------------------------------------------------------------ #

    def apply_patch(self, diff: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".diff", delete=False) as f:
            f.write(diff)
            temp_path = Path(f.name)

        try:
            self._put_file(temp_path, "/tmp/patchloop.diff")
        finally:
            temp_path.unlink(missing_ok=True)

        rc, stdout, stderr = self.run_cmd("git apply /tmp/patchloop.diff")
        self.run_cmd("rm -f /tmp/patchloop.diff")

        if rc != 0:
            return False, (stderr.strip() or stdout.strip() or "git apply failed")

        msg = stdout.strip() or "Patch applied successfully"
        return True, msg

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
            stdout=stdout[:8000],
            stderr=stderr[:4000],
            duration_s=duration,
        )

    def run_cmd(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
        if timeout <= 0:
            timeout = 1

        wrapped = f"timeout {timeout}s /bin/sh -lc {shlex.quote(cmd)}"
        try:
            result = self.container.exec_run(
                cmd=["/bin/sh", "-lc", wrapped],
                workdir="/workspace",
                demux=True,
            )
            stdout_bytes, stderr_bytes = result.output if result.output else (b"", b"")
            stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
            stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")
            return int(result.exit_code or 0), stdout, stderr
        except DockerException as e:
            return 1, "", str(e)

    # ------------------------------------------------------------------ #
    # Git
    # ------------------------------------------------------------------ #

    def git_diff(self) -> str:
        ref = self._snapshot_sha or "HEAD"
        rc, stdout, stderr = self._git_run("diff", ref)
        if rc != 0:
            raise RuntimeError(stderr.strip() or "git diff failed")
        return stdout

    def git_commit(self, message: str) -> str:
        self._git_run("add", "-A")
        rc, stdout, stderr = self._git_run("commit", "-m", message, "--allow-empty")
        if rc != 0:
            raise RuntimeError(f"git commit failed: {stderr.strip()}")

        for line in stdout.splitlines():
            if line.startswith("["):
                return line.split()[1].rstrip("]")
        return "unknown"

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _ensure_image(self) -> None:
        try:
            self.client.images.get(self.image)
            return
        except ImageNotFound:
            pass

        repo_root = Path(__file__).resolve().parents[2]
        dockerfile = repo_root / "Dockerfile.sandbox"
        if dockerfile.exists():
            try:
                self.client.images.build(
                    path=str(repo_root),
                    dockerfile="Dockerfile.sandbox",
                    tag=self.image,
                    rm=True,
                )
                return
            except BuildError as e:
                raise RuntimeError(f"Failed to build sandbox image: {e}") from e

        try:
            self.client.images.pull(self.image)
        except DockerException as e:
            raise RuntimeError(
                f"Sandbox image '{self.image}' not found and pull failed. "
                "Add Dockerfile.sandbox or pre-build the image."
            ) from e

    def _copy_repo_to_container(self) -> None:
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            root = self.task.repo.resolve()
            for path in sorted(root.rglob("*")):
                rel = path.relative_to(root)
                if any(part.startswith(".") for part in rel.parts):
                    continue
                if ".git" in rel.parts:
                    continue
                if any(part == "__pycache__" for part in rel.parts):
                    continue
                if path.is_file() and path.suffix in {".pyc", ".pyo"}:
                    continue

                arcname = rel.as_posix()
                info = tar.gettarinfo(str(path), arcname=arcname)
                if info is None:
                    continue
                if path.is_file():
                    with path.open("rb") as f:
                        tar.addfile(info, f)
                else:
                    tar.addfile(info)

        stream.seek(0)
        self.container.put_archive("/workspace", stream.getvalue())

    def _init_git_snapshot(self) -> str:
        self._git_run("init")
        self._git_run("config", "user.name", "patchloop-agent")
        self._git_run("config", "user.email", "agent@patchloop.local")
        self._git_run("add", "-A")

        rc, _, stderr = self._git_run(
            "commit", "-m", f"snapshot: {self.task.task_id}", "--allow-empty"
        )
        if rc != 0 and "nothing to commit" not in stderr:
            raise RuntimeError(f"Failed to create snapshot commit: {stderr}")

        _, stdout, _ = self._git_run("rev-parse", "HEAD")
        return stdout.strip()

    def _run_setup(self) -> None:
        rc, _, stderr = self.run_cmd(self.task.setup_cmd, timeout=120)
        if rc != 0:
            raise RuntimeError(
                f"setup_cmd failed for {self.task.task_id}:\n{stderr[:500]}"
            )

    def _workspace_target(self, path: str) -> str:
        if PurePosixPath(path).is_absolute():
            raise PermissionError(f"Path escapes workspace: {path}")

        normalized = posixpath.normpath(f"/workspace/{path}")
        if normalized != "/workspace" and not normalized.startswith("/workspace/"):
            raise PermissionError(f"Path escapes workspace: {path}")
        return normalized

    def _git_run(self, *args: str) -> tuple[int, str, str]:
        cmd = "git " + " ".join(shlex.quote(arg) for arg in args)
        return self.run_cmd(cmd, timeout=30)

    def _put_file(self, src_path: Path, dest_path: str) -> None:
        dest_dir = posixpath.dirname(dest_path)
        arcname = posixpath.basename(dest_path)

        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as tar:
            tar.add(str(src_path), arcname=arcname)

        data.seek(0)
        self.container.put_archive(dest_dir, data.getvalue())
