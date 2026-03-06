from __future__ import annotations

import json
import os
from typing import Any, Callable

from openai import OpenAI

from patchloop.agent.state import IterationRecord

# Default provider: Google Gemini via its OpenAI-compatible endpoint.
# Free API key from: https://aistudio.google.com
# Set env var: GEMINI_API_KEY=<your_key>
_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_DEFAULT_MODEL = "gemini-2.0-flash"

# Tool definitions in OpenAI function-calling format.
# This format is accepted by Gemini, Groq, and any OpenAI-compatible provider.
CODING_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a file in the workspace.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the workspace matching a glob pattern.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search for a string across all Python files. "
                "Returns file path, line number, and matching line text."
            ),
            "parameters": {
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
    },
]


class LLMClient:
    """
    Provider-agnostic LLM client using the OpenAI-compatible API format.

    Default: Google Gemini 2.0 Flash (free tier via aistudio.google.com).
    Can target any OpenAI-compatible provider by setting env vars:
      GEMINI_API_KEY  — for Gemini (default)
      LLM_API_KEY     — generic override
      LLM_BASE_URL    — custom base URL (e.g. Groq, local Ollama, etc.)

    Responsibilities:
    - Token tracking per call, accumulated into IterationRecord
    - Agentic tool-use loop (chat_with_tools) for the PLAN phase
    - Simple text completion (chat) for ANALYZE and REFLECT phases
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = 4096,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens

        resolved_key = (
            api_key
            or os.environ.get("LLM_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        resolved_url = base_url or os.environ.get("LLM_BASE_URL", _DEFAULT_BASE_URL)

        if not resolved_key:
            raise RuntimeError(
                "No API key found.\n"
                "Set GEMINI_API_KEY to use Google Gemini (free tier).\n"
                "Get a free key at: https://aistudio.google.com"
            )

        self._client = OpenAI(api_key=resolved_key, base_url=resolved_url)

    # ------------------------------------------------------------------ #
    # Core API call
    # ------------------------------------------------------------------ #

    def _call(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        record: IterationRecord | None = None,
    ) -> Any:
        """Single API call. Updates record token counts if provided."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.chat.completions.create(**kwargs)

        if record is not None and response.usage:
            record.llm_calls += 1
            record.total_tokens += response.usage.total_tokens or 0

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
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]
        response = self._call(messages=messages, record=record)
        return response.choices[0].message.content or ""

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

        The model repeatedly calls tools until finish_reason == "stop",
        meaning it has finished exploring and produced its final answer.

        tool_handler: called for each tool call with (tool_name, tool_args_dict).
                      Must return a string result.
        max_tool_rounds: safety cap to prevent runaway loops.
        """
        # System message goes first in the messages list
        full_messages: list[dict[str, Any]] = (
            [{"role": "system", "content": system}] + messages
        )

        for _ in range(max_tool_rounds):
            response = self._call(
                messages=full_messages,
                tools=tools,
                record=record,
            )
            choice = response.choices[0]

            if choice.finish_reason == "stop":
                return choice.message.content or ""

            if choice.finish_reason == "tool_calls":
                # Append the assistant turn (contains tool_calls) to history
                full_messages.append(
                    choice.message.model_dump(exclude_unset=False)
                )

                # Execute each tool call and append result messages
                for tc in choice.message.tool_calls or []:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                        result = tool_handler(tc.function.name, args)
                    except Exception as e:
                        result = f"Tool error: {e}"

                    full_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(result),
                        }
                    )
                continue

            # Any other finish reason — return whatever content we have
            return choice.message.content or ""

        # Exhausted rounds without reaching "stop"
        return response.choices[0].message.content or ""
