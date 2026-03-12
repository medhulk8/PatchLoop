from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from patchloop.agent.state import LoopState


class RunLogger:
    """
    Structured JSONL logger for a single agent run.

    Every meaningful event (phase transition, plan, patch, test result,
    reflection, etc.) is written as one JSON object per line to:
        runs/{run_id}/{task_id}.jsonl

    Design goals:
    - Every write is flushed immediately so logs survive crashes
    - One file per (run_id, task_id) — easy to correlate with TaskResult
    - Schema is flat — no nested lists — so log lines are grep-friendly
    - Logs contain enough information to reconstruct what happened without
      re-running anything (full replay support)
    """

    def __init__(
        self,
        run_id: str,
        task_id: str,
        runs_dir: Path = Path("runs"),
    ) -> None:
        self.run_id = run_id
        self.task_id = task_id
        log_dir = runs_dir / run_id
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = log_dir / f"{task_id}.jsonl"
        self._fp = self.log_path.open("w", encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Internal write primitive
    # ------------------------------------------------------------------ #

    def _write(self, event: str, data: dict[str, Any]) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "task_id": self.task_id,
            "event": event,
            **data,
        }
        self._fp.write(json.dumps(record) + "\n")
        self._fp.flush()     # guarantee durability — never buffer run logs

    # ------------------------------------------------------------------ #
    # Event methods (one per logical event in the loop)
    # ------------------------------------------------------------------ #

    def log_run_start(self, state: LoopState) -> None:
        self._write("run_start", {
            "baseline": state.baseline,
            "max_iterations": state.max_iterations,
        })

    def log_phase(self, iteration: int, phase: Any) -> None:
        self._write("phase", {
            "iteration": iteration,
            "phase": str(phase.value) if hasattr(phase, "value") else str(phase),
        })

    def log_plan(
        self,
        iteration: int,
        plan: str,
        tool_truncations: dict[str, int] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "iteration": iteration,
            "plan_length": len(plan),
            "plan_preview": plan[:500],    # first 500 chars for quick inspection
        }
        if tool_truncations:
            payload["tool_truncations"] = tool_truncations
        self._write("plan", payload)

    def log_patch_proposed(self, iteration: int, diff: str) -> None:
        self._write("patch_proposed", {
            "iteration": iteration,
            "diff_lines": len(diff.splitlines()),
            "diff": diff[:3000],           # cap — huge diffs aren't useful in logs
        })

    def log_patch_applied(
        self,
        iteration: int,
        success: bool,
        message: str,
        sha: str | None,
    ) -> None:
        self._write("patch_applied", {
            "iteration": iteration,
            "success": success,
            "message": message,
            "git_sha": sha,
        })

    def log_test_result(
        self,
        iteration: int,
        passed: bool,
        returncode: int,
        stdout: str,
        stderr: str,
        duration_s: float,
    ) -> None:
        self._write("test_result", {
            "iteration": iteration,
            "passed": passed,
            "returncode": returncode,
            "duration_s": duration_s,
            "stdout": stdout[:2000],
            "stderr": stderr[:2000],
        })

    def log_reflection(self, iteration: int, reflection: dict[str, Any]) -> None:
        self._write("reflection", {
            "iteration": iteration,
            **reflection,
        })

    def log_error(self, iteration: int, error: str, traceback: str) -> None:
        self._write("error", {
            "iteration": iteration,
            "error": error,
            "traceback": traceback[:2000],
        })

    def log_run_end(self, state: LoopState) -> None:
        self._write("run_end", {
            "resolved": state.resolved,
            "termination_reason": state.termination_reason.value
            if state.termination_reason else None,
            "iterations_used": state.iteration,
            "elapsed_s": state.elapsed_s,
            "total_llm_calls": sum(r.llm_calls for r in state.iterations),
            "total_tokens": sum(r.total_tokens for r in state.iterations),
        })

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        self._fp.close()

    def __enter__(self) -> "RunLogger":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
