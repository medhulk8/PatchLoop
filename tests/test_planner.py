from __future__ import annotations

from pathlib import Path

from patchloop.agent.planner import _extract_failed_tests, build_user_message
from patchloop.agent.state import IterationRecord, LoopState, Reflection
from patchloop.environment.task import Task
from patchloop.environment.task import TestResult as TaskTestResult


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_task(issue: str = "Fix the bug.") -> Task:
    return Task(task_id="test_task", repo=Path("/tmp"), issue=issue)


def _make_state(
    baseline: str = "loop",
    reflections: list[Reflection] | None = None,
    iterations: list[IterationRecord] | None = None,
) -> LoopState:
    state = LoopState(task_id="test_task", baseline=baseline)
    if reflections:
        state.reflections = reflections
    if iterations:
        state.iterations = iterations
    return state


def _make_reflection(iteration: int = 1, lesson: str = "Fix the writer too.") -> Reflection:
    return Reflection(
        iteration=iteration,
        error_type="wrong_file",
        what_failed="writer bug not fixed",
        root_cause_hypothesis="only reader was patched",
        patch_summary="patched reader.py",
        lesson=lesson,
        error_signature="abc123def456",
    )


def _make_iter_record(passed: bool = False, stdout: str = "") -> IterationRecord:
    record = IterationRecord(iteration=1)
    record.test_result = TaskTestResult(
        passed=passed,
        returncode=0 if passed else 1,
        stdout=stdout,
        stderr="",
        duration_s=1.0,
    )
    return record


# ------------------------------------------------------------------ #
# _extract_failed_tests
# ------------------------------------------------------------------ #

class TestExtractFailedTests:
    def test_no_iterations_returns_empty(self) -> None:
        state = _make_state()
        assert _extract_failed_tests(state) == ""

    def test_passed_test_result_returns_empty(self) -> None:
        state = _make_state(iterations=[_make_iter_record(passed=True)])
        assert _extract_failed_tests(state) == ""

    def test_no_test_result_returns_empty(self) -> None:
        record = IterationRecord(iteration=1)
        state = _make_state(iterations=[record])
        assert _extract_failed_tests(state) == ""

    def test_extracts_failed_lines_from_stdout(self) -> None:
        stdout = "FAILED test_foo\nPASSED test_bar\nFAILED test_baz\n1 passed, 2 failed"
        state = _make_state(iterations=[_make_iter_record(stdout=stdout)])
        result = _extract_failed_tests(state)
        assert "FAILED test_foo" in result
        assert "FAILED test_baz" in result
        assert "PASSED test_bar" not in result

    def test_caps_at_10_lines(self) -> None:
        stdout = "\n".join(f"FAILED test_{i}" for i in range(20))
        state = _make_state(iterations=[_make_iter_record(stdout=stdout)])
        result = _extract_failed_tests(state)
        assert result.count("FAILED") == 10

    def test_no_failed_prefix_lines_returns_empty(self) -> None:
        # Lines that contain "FAILED" but don't start with it are not extracted
        stdout = "1 failed\nsome error\nERROR test_foo"
        state = _make_state(iterations=[_make_iter_record(stdout=stdout)])
        assert _extract_failed_tests(state) == ""


# ------------------------------------------------------------------ #
# build_user_message
# ------------------------------------------------------------------ #

class TestBuildUserMessage:
    def test_always_includes_issue(self) -> None:
        task = _make_task(issue="The bug is here.")
        msg = build_user_message(task, _make_state())
        assert "The bug is here." in msg

    def test_single_shot_no_lessons_no_tests(self) -> None:
        task = _make_task()
        state = _make_state(baseline="single_shot")
        msg = build_user_message(task, state)
        assert "Lessons" not in msg
        assert "Still-failing" not in msg

    def test_loop_no_lessons_even_with_iterations(self) -> None:
        task = _make_task()
        stdout = "FAILED test_something"
        state = _make_state(
            baseline="loop",
            iterations=[_make_iter_record(stdout=stdout)],
        )
        msg = build_user_message(task, state)
        assert "Lessons" not in msg
        assert "Still-failing" not in msg

    def test_loop_reflect_first_iteration_no_injection(self) -> None:
        # No prior reflections yet — nothing should be injected
        task = _make_task()
        state = _make_state(baseline="loop_reflect")
        msg = build_user_message(task, state)
        assert "Lessons" not in msg

    def test_loop_reflect_injects_lessons(self) -> None:
        task = _make_task()
        reflection = _make_reflection(lesson="Read writer.py not just reader.py.")
        state = _make_state(baseline="loop_reflect", reflections=[reflection])
        msg = build_user_message(task, state)
        assert "Lessons from previous failed attempts" in msg
        assert "Read writer.py not just reader.py." in msg

    def test_loop_reflect_includes_failed_test_names(self) -> None:
        task = _make_task()
        reflection = _make_reflection()
        stdout = "FAILED test_writer_terminates_each_record_with_newline"
        state = _make_state(
            baseline="loop_reflect",
            reflections=[reflection],
            iterations=[_make_iter_record(stdout=stdout)],
        )
        msg = build_user_message(task, state)
        assert "FAILED test_writer_terminates_each_record_with_newline" in msg

    def test_loop_reflect_no_failed_lines_no_still_failing_section(self) -> None:
        task = _make_task()
        reflection = _make_reflection()
        state = _make_state(
            baseline="loop_reflect",
            reflections=[reflection],
            iterations=[_make_iter_record(passed=True)],
        )
        msg = build_user_message(task, state)
        assert "Still-failing tests" not in msg

    def test_loop_testnames_injects_test_names_only(self) -> None:
        task = _make_task()
        stdout = "FAILED test_something_important"
        state = _make_state(
            baseline="loop_testnames",
            iterations=[_make_iter_record(stdout=stdout)],
        )
        msg = build_user_message(task, state)
        assert "FAILED test_something_important" in msg
        assert "Lessons from previous failed attempts" not in msg

    def test_loop_testnames_no_failures_no_section(self) -> None:
        task = _make_task()
        state = _make_state(baseline="loop_testnames")
        msg = build_user_message(task, state)
        assert "Still-failing" not in msg

    def test_loop_does_not_get_lessons_even_if_reflections_exist(self) -> None:
        # Guard: reflections on a non-loop_reflect baseline must not be injected
        task = _make_task()
        reflection = _make_reflection()
        state = _make_state(baseline="loop", reflections=[reflection])
        msg = build_user_message(task, state)
        assert "Lessons" not in msg

    def test_multiple_reflections_all_included(self) -> None:
        task = _make_task()
        reflections = [
            _make_reflection(iteration=1, lesson="First lesson."),
            _make_reflection(iteration=2, lesson="Second lesson."),
        ]
        state = _make_state(baseline="loop_reflect", reflections=reflections)
        msg = build_user_message(task, state)
        assert "First lesson." in msg
        assert "Second lesson." in msg
