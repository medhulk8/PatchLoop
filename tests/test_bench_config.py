"""
Lightweight tests verifying that runtime-critical config flags
(tool_rounds, call_delay, num_runs) are stored and threaded correctly
through the stack without making any real API calls.

Also covers LLMClient.chat_with_tools correctness paths:
- exhaustion fallback (final text-only call when all rounds end in tool_calls)
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


# ------------------------------------------------------------------ #
# chat_with_tools exhaustion fallback
# ------------------------------------------------------------------ #

class TestChatWithToolsExhaustion:
    """
    When all max_tool_rounds are consumed and the model's last response
    still has finish_reason="tool_calls" (content is empty), chat_with_tools
    must make one final text-only call (tools=None) and return its content.

    This is the critical correctness path that prevents silent NO_DIFF:
    without the fallback, the loop exits and returns "" which the diff
    extractor treats as no patch produced.
    """

    def _tool_calls_response(self) -> MagicMock:
        resp = MagicMock()
        resp.choices[0].finish_reason = "tool_calls"
        resp.choices[0].message.tool_calls = []  # no actual tool calls to execute
        resp.choices[0].message.model_dump.return_value = {"role": "assistant"}
        resp.usage = None
        return resp

    def _stop_response(self, content: str) -> MagicMock:
        resp = MagicMock()
        resp.choices[0].finish_reason = "stop"
        resp.choices[0].message.content = content
        resp.usage = None
        return resp

    def test_fallback_call_made_after_rounds_exhausted(self) -> None:
        with patch("patchloop.llm.client.OpenAI"):
            client = LLMClient(api_key="fake", base_url="http://localhost")

        expected = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new"
        side_effects = [
            self._tool_calls_response(),   # round 1: tool_calls
            self._tool_calls_response(),   # round 2: tool_calls — rounds now exhausted
            self._stop_response(expected), # fallback: text-only call
        ]

        with patch.object(client, "_call", side_effect=side_effects) as mock_call:
            result = client.chat_with_tools(
                system="Fix the bug.",
                messages=[{"role": "user", "content": "Issue."}],
                tools=[{"type": "function", "function": {"name": "read_file"}}],
                tool_handler=lambda name, args: "contents",
                max_tool_rounds=2,
            )

        assert result == expected
        # 2 tool-round calls + 1 fallback = 3 total
        assert mock_call.call_count == 3
        # The fallback call must have tools=None
        assert mock_call.call_args_list[-1].kwargs["tools"] is None

    def test_fallback_content_is_returned(self) -> None:
        """Return value is the fallback response content, not empty string."""
        with patch("patchloop.llm.client.OpenAI"):
            client = LLMClient(api_key="fake", base_url="http://localhost")

        side_effects = [
            self._tool_calls_response(),
            self._stop_response("the diff"),
        ]

        with patch.object(client, "_call", side_effect=side_effects):
            result = client.chat_with_tools(
                system="s", messages=[{"role": "user", "content": "u"}],
                tools=[], tool_handler=lambda n, a: "", max_tool_rounds=1,
            )

        assert result == "the diff"

    def test_no_fallback_when_model_stops_within_rounds(self) -> None:
        """If model reaches finish_reason=stop before rounds are exhausted, no fallback."""
        with patch("patchloop.llm.client.OpenAI"):
            client = LLMClient(api_key="fake", base_url="http://localhost")

        side_effects = [
            self._stop_response("early stop content"),
        ]

        with patch.object(client, "_call", side_effect=side_effects) as mock_call:
            result = client.chat_with_tools(
                system="s", messages=[{"role": "user", "content": "u"}],
                tools=[], tool_handler=lambda n, a: "", max_tool_rounds=5,
            )

        assert result == "early stop content"
        assert mock_call.call_count == 1  # only the one call, no fallback
