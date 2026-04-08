from __future__ import annotations

import traceback
from collections import Counter
from typing import TYPE_CHECKING

from patchloop.agent.patcher import Patcher
from patchloop.agent.planner import Planner
from patchloop.agent.reflector import Reflector
from patchloop.agent.state import (
    AgentPhase,
    LoopState,
    TerminationReason,
)
from patchloop.environment.base import Environment
from patchloop.environment.task import Task, TaskResult
from patchloop.llm.client import LLMClient

if TYPE_CHECKING:
    from patchloop.observability.logger import RunLogger


class AgentLoop:
    """
    The main agent execution loop.

    Implements the state machine:
        PLAN -> APPLY_PATCH -> RUN_TESTS -> ANALYZE_FAILURE -> REFLECT
                                                             -> DECIDE_NEXT -> PLAN (next iter)
                                                                            -> TERMINATE

    Configurable via `baseline`:
      - "single_shot": max_iterations=1, no reflection
      - "loop":        max_iterations=N, no reflection
      - "loop_reflect": max_iterations=N, inject reflections into PLAN prompt

    This design means all three baselines run through the same code path —
    the only difference is whether reflections are generated and injected.
    """

    def __init__(
        self,
        task: Task,
        env: Environment,
        llm: LLMClient,
        logger: "RunLogger",
        baseline: str = "loop_reflect",
        max_tool_rounds: int = 15,
    ) -> None:
        self.task = task
        self.env = env
        self.llm = llm
        self.logger = logger
        self.baseline = baseline
        self.max_tool_rounds = max_tool_rounds

        # Agent components
        self.planner = Planner(llm, max_tool_rounds=max_tool_rounds)
        self.patcher = Patcher()
        self.reflector = Reflector(llm)

    def run(self, run_id: str | None = None) -> tuple[LoopState, TaskResult]:
        """
        Execute the full agent loop for the task.

        run_id: pass the same run_id used when constructing RunLogger so that
                LoopState and the log file share a consistent identifier.
                If None, LoopState generates its own UUID.

        Returns the final LoopState (for analysis) and a TaskResult
        (the compact summary written to the benchmark report).
        """
        max_iters = 1 if self.baseline == "single_shot" else self.task.max_iterations
        state_kwargs: dict = dict(
            task_id=self.task.task_id,
            baseline=self.baseline,
            max_iterations=max_iters,
        )
        if run_id:
            state_kwargs["run_id"] = run_id
        state = LoopState(**state_kwargs)

        self.logger.log_run_start(state)

        while not state.terminated:
            try:
                self._step(state)
            except Exception as e:
                # Catch unexpected errors so one bad task doesn't crash the
                # whole benchmark. Log the traceback and terminate cleanly.
                tb = traceback.format_exc()
                self.logger.log_error(state.iteration, str(e), tb)
                state.terminate(TerminationReason.ERROR)

        self.logger.log_run_end(state)
        return state, self._build_task_result(state)

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #

    def _step(self, state: LoopState) -> None:
        handlers = {
            AgentPhase.PLAN:            self._handle_plan,
            AgentPhase.APPLY_PATCH:     self._handle_apply_patch,
            AgentPhase.RUN_TESTS:       self._handle_run_tests,
            AgentPhase.ANALYZE_FAILURE: self._handle_analyze_failure,
            AgentPhase.REFLECT:         self._handle_reflect,
            AgentPhase.DECIDE_NEXT:     self._handle_decide_next,
            AgentPhase.TERMINATE:       lambda s: None,
        }
        handler = handlers.get(state.phase)
        if handler is None:
            raise ValueError(f"No handler for phase: {state.phase}")
        handler(state)

    # ------------------------------------------------------------------ #
    # Phase handlers
    # ------------------------------------------------------------------ #

    def _handle_plan(self, state: LoopState) -> None:
        record = state.begin_iteration()
        state.transition(AgentPhase.PLAN)
        self.logger.log_phase(state.iteration, AgentPhase.PLAN)

        self.planner.run(state, self.env, self.task, record)
        self.logger.log_plan(
            state.iteration,
            record.plan or "",
            tool_truncations=record.tool_truncations or None,
        )

        if record.proposed_diff:
            self.logger.log_patch_proposed(state.iteration, record.proposed_diff)
            state.transition(AgentPhase.APPLY_PATCH)
        else:
            # LLM could not produce a diff — terminate this run
            record.close()
            state.terminate(TerminationReason.NO_DIFF)

    def _handle_apply_patch(self, state: LoopState) -> None:
        record = state.current_record()
        assert record is not None
        state.transition(AgentPhase.APPLY_PATCH)
        self.logger.log_phase(state.iteration, AgentPhase.APPLY_PATCH)

        outcome = self.patcher.apply(
            diff=record.proposed_diff,
            env=self.env,
            run_id=state.run_id,
            iteration=state.iteration,
        )

        record.patch_applied = outcome.success
        record.patch_error = None if outcome.success else outcome.message
        record.git_sha = outcome.git_sha

        self.logger.log_patch_applied(
            state.iteration, outcome.success, outcome.message, outcome.git_sha
        )

        if outcome.success:
            state.transition(AgentPhase.RUN_TESTS)
        else:
            # Patch couldn't apply — skip to DECIDE_NEXT without running tests
            record.close()
            state.transition(AgentPhase.DECIDE_NEXT)

    def _handle_run_tests(self, state: LoopState) -> None:
        record = state.current_record()
        assert record is not None
        state.transition(AgentPhase.RUN_TESTS)
        self.logger.log_phase(state.iteration, AgentPhase.RUN_TESTS)

        result = self.env.run_tests()
        record.test_result = result

        self.logger.log_test_result(
            state.iteration,
            result.passed,
            result.returncode,
            result.stdout,
            result.stderr,
            result.duration_s,
        )

        if result.passed:
            record.close()
            state.terminate(TerminationReason.SUCCESS, resolved=True)
            return

        # Time limit check
        if state.elapsed_s >= self.task.time_limit_s:
            record.close()
            state.terminate(TerminationReason.TIME_LIMIT)
            return

        # Single-shot baseline: no further iterations
        if self.baseline == "single_shot":
            record.close()
            state.terminate(TerminationReason.MAX_ITERATIONS)
            return

        state.transition(AgentPhase.ANALYZE_FAILURE)

    def _handle_analyze_failure(self, state: LoopState) -> None:
        record = state.current_record()
        assert record is not None and record.test_result is not None
        state.transition(AgentPhase.ANALYZE_FAILURE)
        self.logger.log_phase(state.iteration, AgentPhase.ANALYZE_FAILURE)

        sig = LoopState.make_error_signature(
            record.test_result.stderr, record.test_result.stdout
        )
        record.error_signature = sig
        state.register_error_signature(sig)

        # Only generate reflections for the loop_reflect baseline
        if self.baseline == "loop_reflect":
            state.transition(AgentPhase.REFLECT)
        else:
            state.transition(AgentPhase.DECIDE_NEXT)

    def _handle_reflect(self, state: LoopState) -> None:
        record = state.current_record()
        assert record is not None
        state.transition(AgentPhase.REFLECT)
        self.logger.log_phase(state.iteration, AgentPhase.REFLECT)

        reflection = self.reflector.reflect(state, record)
        record.reflection = reflection
        state.reflections.append(reflection)
        self.logger.log_reflection(state.iteration, reflection.model_dump())

        state.transition(AgentPhase.DECIDE_NEXT)

    def _handle_decide_next(self, state: LoopState) -> None:
        record = state.current_record()
        if record:
            record.close()

        state.transition(AgentPhase.DECIDE_NEXT)
        self.logger.log_phase(state.iteration, AgentPhase.DECIDE_NEXT)

        state.iteration += 1

        # Anti-repeat: same failure N times in a row
        if state.is_stuck():
            state.terminate(TerminationReason.STUCK)
            return

        # Iteration cap
        if state.iteration >= state.max_iterations:
            state.terminate(TerminationReason.MAX_ITERATIONS)
            return

        # Time budget
        if state.elapsed_s >= self.task.time_limit_s:
            state.terminate(TerminationReason.TIME_LIMIT)
            return

        # Reset workspace to clean snapshot before next attempt.
        # This undoes the previous patch so the next PLAN starts fresh.
        self.env.reset()
        state.transition(AgentPhase.PLAN)

    # ------------------------------------------------------------------ #
    # Result construction
    # ------------------------------------------------------------------ #

    def _build_task_result(self, state: LoopState) -> TaskResult:
        # Count iterations that repeated a previously-seen failure signature.
        sig_counts = Counter(
            rec.error_signature
            for rec in state.iterations
            if rec.error_signature
        )
        repeated = sum(max(count - 1, 0) for count in sig_counts.values())

        diff_text = self.env.git_diff()
        loc = len([
            line for line in diff_text.splitlines()
            if (line.startswith("+") or line.startswith("-"))
            and not line.startswith("+++")
            and not line.startswith("---")
        ])

        return TaskResult(
            task_id=self.task.task_id,
            run_id=state.run_id,
            baseline=self.baseline,
            model=self.llm.model,
            tool_rounds=self.max_tool_rounds,
            resolved=state.resolved,
            iterations_used=len(state.iterations),
            total_duration_s=state.elapsed_s,
            termination_reason=state.termination_reason.value
            if state.termination_reason
            else "UNKNOWN",
            loc_changed=loc,
            repeated_failure_count=repeated,
        )
