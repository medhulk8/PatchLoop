from __future__ import annotations

from typing import Any

from patchloop.environment.base import Environment
from patchloop.environment.task import Task, TestResult


class DockerEnvironment(Environment):
    """
    Docker-based execution environment. Phase 2 — not yet implemented.

    Drop-in replacement for LocalEnvironment via the shared Environment
    interface. Each task will run in a fresh container with:
      - CPU and memory limits (--cpus, --memory)
      - PID limit (--pids-limit)
      - No network access (--network none)
      - Workspace mounted as a volume

    To implement: use the `docker` Python SDK (docker-py).
    Sandbox image: Dockerfile.sandbox at repo root.
    """

    def __init__(self, task: Task, image: str = "patchloop-sandbox:latest") -> None:
        super().__init__(task)
        raise NotImplementedError(
            "DockerEnvironment is a Phase 2 component. "
            "Use LocalEnvironment for now."
        )

    def setup(self) -> None: ...
    def teardown(self) -> None: ...
    def reset(self) -> None: ...
    def read_file(self, path: str) -> str: ...
    def list_files(self, pattern: str = "**/*.py") -> list[str]: ...
    def search_code(self, query: str) -> list[dict[str, Any]]: ...
    def apply_patch(self, diff: str) -> tuple[bool, str]: ...
    def run_tests(self) -> TestResult: ...
    def run_cmd(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]: ...
    def git_diff(self) -> str: ...
    def git_commit(self, message: str) -> str: ...
