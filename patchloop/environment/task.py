from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class TestResult(BaseModel):
    """Structured output of running the task's test command."""

    passed: bool
    returncode: int
    stdout: str
    stderr: str
    duration_s: float


class Task(BaseModel):
    """
    A single benchmark task definition.

    Loaded from a YAML file. The `repo` field is resolved to an absolute
    path relative to the YAML file's directory at load time.
    """

    task_id: str
    repo: Path
    commit: str | None = None       # None = use HEAD as-is
    issue: str
    setup_cmd: str | None = None
    test_cmd: str = "pytest -q --tb=short"
    time_limit_s: int = 360
    max_iterations: int = 5
    tags: list[str] = Field(default_factory=list)
    difficulty: str = "medium"      # easy | medium | hard

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_yaml(cls, path: Path) -> "Task":
        with open(path) as f:
            data = yaml.safe_load(f)
        # Resolve repo path relative to the yaml file's own directory.
        # This makes tasks portable — no hardcoded absolute paths.
        data["repo"] = (path.parent / data["repo"]).resolve()
        return cls(**data)


class TaskResult(BaseModel):
    """
    Final outcome of running an agent on a task.

    Written by the benchmark runner. Used to compute metrics across runs.
    """

    task_id: str
    run_id: str
    baseline: str               # "single_shot" | "loop" | "loop_testnames" | "loop_reflect"
    model: str
    base_url: str
    tool_rounds: int
    resolved: bool
    iterations_used: int
    total_duration_s: float
    termination_reason: str
    files_touched: list[str] = Field(default_factory=list)
    loc_changed: int = 0
    repeated_failure_count: int = 0
    error: str | None = None
