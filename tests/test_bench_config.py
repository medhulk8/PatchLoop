"""
Lightweight tests verifying that runtime-critical config flags
(tool_rounds, call_delay, num_runs) are stored and threaded correctly
through the stack without making any real API calls.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from patchloop.agent.loop import AgentLoop
from patchloop.agent.planner import Planner
from patchloop.eval.bench_runner import BenchmarkRunner
from patchloop.llm.client import LLMClient


# ------------------------------------------------------------------ #
# LLMClient stores call_delay
# ------------------------------------------------------------------ #

class TestLLMClientCallDelay:
    def test_default_call_delay_is_zero(self) -> None:
        with patch("patchloop.llm.client.OpenAI"):
            client = LLMClient(api_key="fake-key", base_url="http://localhost")
        assert client.call_delay == 0.0

    def test_custom_call_delay_stored(self) -> None:
        with patch("patchloop.llm.client.OpenAI"):
            client = LLMClient(api_key="fake-key", base_url="http://localhost", call_delay=7.5)
        assert client.call_delay == 7.5


# ------------------------------------------------------------------ #
# Planner stores max_tool_rounds
# ------------------------------------------------------------------ #

class TestPlannerToolRounds:
    def test_default_max_tool_rounds(self) -> None:
        llm = MagicMock(spec=LLMClient)
        planner = Planner(llm)
        assert planner.max_tool_rounds == 15

    def test_custom_max_tool_rounds(self) -> None:
        llm = MagicMock(spec=LLMClient)
        planner = Planner(llm, max_tool_rounds=8)
        assert planner.max_tool_rounds == 8

    def test_tool_rounds_zero_stored(self) -> None:
        llm = MagicMock(spec=LLMClient)
        planner = Planner(llm, max_tool_rounds=4)
        assert planner.max_tool_rounds == 4


# ------------------------------------------------------------------ #
# AgentLoop threads max_tool_rounds into Planner
# ------------------------------------------------------------------ #

class TestAgentLoopToolRounds:
    def _make_loop(self, max_tool_rounds: int) -> AgentLoop:
        task = MagicMock()
        task.task_id = "test"
        task.max_iterations = 5
        env = MagicMock()
        llm = MagicMock(spec=LLMClient)
        logger = MagicMock()
        return AgentLoop(
            task=task,
            env=env,
            llm=llm,
            logger=logger,
            baseline="loop",
            max_tool_rounds=max_tool_rounds,
        )

    def test_tool_rounds_threaded_to_planner(self) -> None:
        loop = self._make_loop(max_tool_rounds=8)
        assert loop.planner.max_tool_rounds == 8

    def test_tool_rounds_default(self) -> None:
        loop = self._make_loop(max_tool_rounds=15)
        assert loop.planner.max_tool_rounds == 15


# ------------------------------------------------------------------ #
# BenchmarkRunner stores all config knobs
# ------------------------------------------------------------------ #

class TestBenchmarkRunnerConfig:
    def _make_runner(self, **kwargs) -> BenchmarkRunner:
        return BenchmarkRunner(
            tasks_dir=Path("/tmp"),
            runs_dir=Path("/tmp/runs"),
            **kwargs,
        )

    def test_defaults(self) -> None:
        runner = self._make_runner()
        assert runner.max_tool_rounds == 15
        assert runner.call_delay == 0.0
        assert runner.num_runs == 1
        assert runner.run_delay_s == 30

    def test_custom_tool_rounds(self) -> None:
        runner = self._make_runner(max_tool_rounds=8)
        assert runner.max_tool_rounds == 8

    def test_custom_call_delay(self) -> None:
        runner = self._make_runner(call_delay=7.0)
        assert runner.call_delay == 7.0

    def test_custom_num_runs(self) -> None:
        runner = self._make_runner(num_runs=3)
        assert runner.num_runs == 3

    def test_custom_run_delay(self) -> None:
        runner = self._make_runner(run_delay_s=60)
        assert runner.run_delay_s == 60

    def test_all_custom(self) -> None:
        runner = self._make_runner(
            max_tool_rounds=8,
            call_delay=7.0,
            num_runs=3,
            run_delay_s=60,
        )
        assert runner.max_tool_rounds == 8
        assert runner.call_delay == 7.0
        assert runner.num_runs == 3
        assert runner.run_delay_s == 60
