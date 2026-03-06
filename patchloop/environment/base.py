from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from patchloop.environment.task import Task, TestResult


class Environment(ABC):
    """
    Abstract execution environment for a single agent task.

    All agent-to-code interactions go through this interface.
    Concrete implementations: LocalEnvironment, DockerEnvironment.

    The interface is intentionally small — only what the agent
    actually needs to solve a coding task.
    """

    def __init__(self, task: Task) -> None:
        self.task = task

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    @abstractmethod
    def setup(self) -> None:
        """Prepare the workspace (copy repo, run setup_cmd, etc.)."""
        ...

    @abstractmethod
    def teardown(self) -> None:
        """Release all resources (temp dirs, containers, etc.)."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """
        Reset the workspace to the initial repo snapshot.

        Called between iterations so each PLAN phase starts from
        the same clean state. Must preserve git history so patch
        replay works correctly.
        """
        ...

    # ------------------------------------------------------------------ #
    # File operations
    # ------------------------------------------------------------------ #

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Return file contents as a UTF-8 string."""
        ...

    @abstractmethod
    def list_files(self, pattern: str = "**/*.py") -> list[str]:
        """Return file paths matching a glob pattern, relative to repo root."""
        ...

    @abstractmethod
    def search_code(self, query: str) -> list[dict[str, Any]]:
        """
        Case-insensitive search across all Python files.
        Returns list of {file, line, text} dicts, capped at 50 results.
        """
        ...

    # ------------------------------------------------------------------ #
    # Patching
    # ------------------------------------------------------------------ #

    @abstractmethod
    def apply_patch(self, diff: str) -> tuple[bool, str]:
        """
        Apply a unified diff string to the workspace via `git apply`.
        Returns (success, message). Does NOT commit — caller does that.
        """
        ...

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    @abstractmethod
    def run_tests(self) -> TestResult:
        """Run the task's test_cmd and return structured results."""
        ...

    @abstractmethod
    def run_cmd(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
        """
        Run an arbitrary shell command in the workspace.
        Returns (returncode, stdout, stderr).
        """
        ...

    # ------------------------------------------------------------------ #
    # Git
    # ------------------------------------------------------------------ #

    @abstractmethod
    def git_diff(self) -> str:
        """Return the current unified diff of the working tree vs HEAD."""
        ...

    @abstractmethod
    def git_commit(self, message: str) -> str:
        """Stage all changes and create a commit. Returns the commit SHA."""
        ...

    # ------------------------------------------------------------------ #
    # Context manager
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "Environment":
        self.setup()
        return self

    def __exit__(self, *args: Any) -> None:
        self.teardown()
