from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from patchloop.environment.task import TestResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentPhase(str, Enum):
    """
    States of the agent loop state machine.

    Transitions:
        PLAN -> APPLY_PATCH -> RUN_TESTS -> ANALYZE_FAILURE -> REFLECT -> DECIDE_NEXT -> PLAN
                                         -> TERMINATE (on success or limit)
    """
    PLAN            = "PLAN"
    APPLY_PATCH     = "APPLY_PATCH"
    RUN_TESTS       = "RUN_TESTS"
    ANALYZE_FAILURE = "ANALYZE_FAILURE"
    REFLECT         = "REFLECT"
    DECIDE_NEXT     = "DECIDE_NEXT"
    TERMINATE       = "TERMINATE"


class TerminationReason(str, Enum):
    SUCCESS         = "SUCCESS"
    MAX_ITERATIONS  = "MAX_ITERATIONS"
    TIME_LIMIT      = "TIME_LIMIT"
    STUCK           = "STUCK"           # anti-repeat: same failure N times in a row
    NO_DIFF         = "NO_DIFF"         # LLM produced no diff
    ERROR           = "ERROR"           # unexpected runtime error


class Reflection(BaseModel):
    """
    Structured reflection from a failed iteration.

    Each field has a specific role:
    - error_type: categorized error class (used for retrieval in Phase 2)
    - what_failed: describes the observed failure in one sentence
    - root_cause_hypothesis: the agent's best guess at why it happened
    - patch_summary: what the attempted patch did
    - patch_assessment: whether patch was wrong, partially correct, or unclear
    - lesson: actionable search direction for the next attempt — this is what
              gets injected into the PLAN prompt for future iterations
    - error_signature: MD5 of the test output, used for anti-repeat detection
    """
    iteration: int
    error_type: str
    what_failed: str
    root_cause_hypothesis: str
    patch_summary: str
    patch_assessment: Literal["likely_wrong", "likely_partial_success", "unclear"] = "unclear"
    lesson: str
    error_signature: str


class IterationRecord(BaseModel):
    """
    Complete record of everything that happened in one agent iteration.

    One IterationRecord is created at the start of each iteration and
    populated as the loop progresses through phases. Stored in LoopState.iterations.
    """
    iteration: int
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: datetime | None = None
    duration_s: float = 0.0

    # PLAN phase
    plan: str | None = None
    proposed_diff: str | None = None
    tool_truncations: dict[str, int] = Field(default_factory=dict)

    # APPLY_PATCH phase
    patch_applied: bool | None = None
    patch_error: str | None = None
    git_sha: str | None = None

    # RUN_TESTS phase
    test_result: TestResult | None = None

    # ANALYZE_FAILURE + REFLECT phase
    error_analysis: str | None = None
    error_signature: str | None = None
    reflection: Reflection | None = None

    # LLM usage tracking (for cost accounting)
    llm_calls: int = 0
    total_tokens: int = 0

    def close(self) -> None:
        """Mark the iteration as finished and compute duration. Idempotent."""
        if self.ended_at is not None:
            return
        self.ended_at = _utcnow()
        self.duration_s = round(
            (self.ended_at - self.started_at).total_seconds(), 2
        )


class LoopState(BaseModel):
    """
    Fully serializable state of a single agent run.

    This is the primary unit of observability. Every run can be replayed
    by inspecting the sequence of IterationRecords. On disk it's written
    as a JSONL log by RunLogger.

    Design:
    - One LoopState per (task, run_id, baseline) triple
    - IterationRecords are append-only
    - Reflections accumulate during the run; injected into PLAN prompts
      when baseline == "loop_reflect"
    - Anti-repeat: error signatures are hashed; 3 consecutive identical
      failures triggers STUCK termination
    """
    task_id: str
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    baseline: str = "loop"          # "single_shot" | "loop" | "loop_testnames" | "loop_reflect"
    phase: AgentPhase = AgentPhase.PLAN
    iteration: int = 0
    max_iterations: int = 5
    started_at: datetime = Field(default_factory=_utcnow)

    # Append-only history
    iterations: list[IterationRecord] = Field(default_factory=list)

    # Reflections from failed iterations (for in-run injection)
    reflections: list[Reflection] = Field(default_factory=list)

    # Anti-repeat tracking
    seen_error_signatures: list[str] = Field(default_factory=list)
    last_error_signature: str | None = None
    consecutive_repeats: int = 0
    max_consecutive_repeats: int = 3

    # Terminal state
    terminated: bool = False
    termination_reason: TerminationReason | None = None
    resolved: bool = False

    # ------------------------------------------------------------------ #
    # Iteration management
    # ------------------------------------------------------------------ #

    def begin_iteration(self) -> IterationRecord:
        """Create and register a new IterationRecord for the current iteration."""
        record = IterationRecord(iteration=self.iteration)
        self.iterations.append(record)
        return record

    def current_record(self) -> IterationRecord | None:
        return self.iterations[-1] if self.iterations else None

    # ------------------------------------------------------------------ #
    # Phase transitions
    # ------------------------------------------------------------------ #

    def transition(self, next_phase: AgentPhase) -> None:
        self.phase = next_phase

    def terminate(self, reason: TerminationReason, resolved: bool = False) -> None:
        self.terminated = True
        self.termination_reason = reason
        self.resolved = resolved
        self.phase = AgentPhase.TERMINATE

    # ------------------------------------------------------------------ #
    # Anti-repeat
    # ------------------------------------------------------------------ #

    def register_error_signature(self, sig: str) -> bool:
        """
        Register an error signature. Returns True if this is a consecutive
        repeat (same failure as the immediately preceding iteration).

        consecutive_repeats only increments when sig == last_error_signature.
        Different failures reset the counter to 1 so alternating errors
        (a, b, a, b, a) do NOT trigger STUCK.
        """
        is_repeat = sig == self.last_error_signature
        if is_repeat:
            self.consecutive_repeats += 1
        else:
            self.consecutive_repeats = 1
        self.last_error_signature = sig
        if sig not in self.seen_error_signatures:
            self.seen_error_signatures.append(sig)
        return is_repeat

    def is_stuck(self) -> bool:
        return self.consecutive_repeats >= self.max_consecutive_repeats

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    @property
    def elapsed_s(self) -> float:
        return round(
            (datetime.now(timezone.utc) - self.started_at).total_seconds(), 2
        )

    @staticmethod
    def make_error_signature(stderr: str, stdout: str) -> str:
        """
        Hash test output to identify unique failure modes.

        We use: last 500 chars of stderr + last 200 chars of stdout.
        This captures the failure summary without being sensitive to
        line numbers or minor formatting changes.
        """
        content = (stderr[-500:] + stdout[-200:]).strip()
        return hashlib.md5(content.encode()).hexdigest()[:12]
