from __future__ import annotations

from typing import Any, Callable

import anthropic

from patchloop.agent.state import IterationRecord

# Tool definitions exposed to the LLM during the PLAN phase.
# The agent uses these to explore the codebase before proposing a patch.
CODING_TOOLS: list[dict[str, Any]] = [
    {
        "name": "read_file",
        "description": "Read the full contents of a file in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to repo root (e.g. src/utils.py)",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List files in the workspace matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern. Default: **/*.py",
                }
            },
            "required": [],
        },
    },
    {
        "name": "search_code",
        "description": (
            "Search for a string across all Python files. "
            "Returns file path, line number, and matching line text."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search string (case-insensitive).",
                }
            },
            "required": ["query"],
        },
    },
]


class LLMClient:
    """
    Thin wrapper around the Anthropic SDK.

    Responsibilities:
    - Token usage tracking per call, accumulated into IterationRecord
    - Agentic tool-use loop (chat_with_tools) for the PLAN phase
    - Simple text completion (chat) for ANALYZE and REFLECT phases

    All API calls go through _call() so token tracking is never missed.
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic()

    # ------------------------------------------------------------------ #
    # Core API call
    # ------------------------------------------------------------------ #

    def _call(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        record: IterationRecord | None = None,
    ) -> anthropic.types.Message:
        """Single API call. Updates record token counts if provided."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.messages.create(**kwargs)

        if record is not None:
            record.llm_calls += 1
            if response.usage:
                record.total_tokens += (
                    response.usage.input_tokens + response.usage.output_tokens
                )

        return response

    # ------------------------------------------------------------------ #
    # Simple chat (ANALYZE, REFLECT phases)
    # ------------------------------------------------------------------ #

    def chat(
        self,
        system: str,
        user_message: str,
        record: IterationRecord | None = None,
    ) -> str:
        """Single-turn text completion. Returns assistant text."""
        response = self._call(
            system=system,
            messages=[{"role": "user", "content": user_message}],
            record=record,
        )
        return self._extract_text(response)

    # ------------------------------------------------------------------ #
    # Tool-use loop (PLAN phase)
    # ------------------------------------------------------------------ #

    def chat_with_tools(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_handler: Callable[[str, dict[str, Any]], str],
        record: IterationRecord | None = None,
        max_tool_rounds: int = 15,
    ) -> str:
        """
        Agentic tool-use loop.

        The model can call tools repeatedly until it reaches end_turn
        (meaning it's done exploring and has produced a final answer).

        tool_handler: called for each tool_use block with (tool_name, tool_input).
                      Must return a string result.
        max_tool_rounds: safety cap to prevent infinite loops.
        """
        for _ in range(max_tool_rounds):
            response = self._call(
                system=system,
                messages=messages,
                tools=tools,
                record=record,
            )

            if response.stop_reason == "end_turn":
                return self._extract_text(response)

            if response.stop_reason == "tool_use":
                # Append the assistant's tool-use message to history
                messages = messages + [
                    {"role": "assistant", "content": response.content}
                ]

                # Execute each tool and collect results
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        try:
                            result = tool_handler(block.name, block.input)
                        except Exception as e:
                            result = f"Tool error: {e}"
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(result),
                            }
                        )

                # Feed results back as a user message (Anthropic's convention)
                messages = messages + [
                    {"role": "user", "content": tool_results}
                ]
                continue

            # Unexpected stop reason — return what we have
            return self._extract_text(response)

        return self._extract_text(response)

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        return "\n".join(
            block.text for block in response.content if hasattr(block, "text")
        ).strip()
