from __future__ import annotations

import re
from typing import Any

from patchloop.agent.state import IterationRecord, LoopState
from patchloop.environment.base import Environment
from patchloop.environment.task import Task
from patchloop.llm.client import CODING_TOOLS, LLMClient

# Tool output limits — deliberate budget controls, not arbitrary.
# Raising these increases token spend per iteration; lowering may hide context.
_READ_FILE_MAX_LINES = 200
_SEARCH_CODE_MAX_RESULTS = 10

_SYSTEM_PROMPT = """\
You are an expert software engineer fixing a bug in a Python codebase.

Your workflow:
1. Read the issue description carefully.
2. Use the provided tools to explore the codebase. Read the relevant files before proposing a fix.
3. Produce a minimal, correct unified diff (git diff format) that fixes the issue.

Rules:
- ALWAYS read the relevant source files before writing a patch. Do not guess.
- Make the smallest change that fixes the bug. Do not refactor unrelated code.
- Output the diff inside a ```diff ... ``` code block at the END of your response.
- The diff must use correct file paths relative to the repo root.
- If you truly cannot determine a fix, say so clearly — do not produce a broken patch.
"""


def _extract_failed_tests(state: LoopState) -> str:
    """
    Extract FAILED test lines from the last iteration's stdout and stderr.

    Returns a formatted string ready to append to a prompt section,
    or empty string if there are no failed lines to report.
    Capped at 10 lines to prevent prompt bloat on large test suites.
    """
    if not state.iterations:
        return ""
    last_result = state.iterations[-1].test_result
    if not last_result or last_result.passed:
        return ""
    combined = (last_result.stdout or "") + "\n" + (last_result.stderr or "")
    failed_lines = [
        line for line in combined.splitlines()
        if line.startswith("FAILED")
    ][:10]
    if not failed_lines:
        return ""
    return "\n\nStill-failing tests:\n" + "\n".join(f"  {line}" for line in failed_lines)


def build_user_message(task: Task, state: LoopState) -> str:
    """
    Build the user message for the PLAN phase.

    On iteration 0: just the issue.
    On iteration >= 1:
    - loop_reflect: inject reflection lessons + failing test names (grounding)
    - loop_testnames: inject only failing test names (ablation — no lessons)
    - loop / single_shot: issue only
    """
    parts = [f"## Issue\n\n{task.issue.strip()}"]

    if state.reflections and state.baseline == "loop_reflect":
        lessons = "\n".join(
            f"- **Iteration {r.iteration}**: {r.lesson}"
            for r in state.reflections
        )
        parts.append(
            "## Lessons from previous failed attempts\n\n"
            "Do NOT repeat these mistakes:\n\n" + lessons + _extract_failed_tests(state)
        )
    elif state.iterations and state.baseline == "loop_testnames":
        failed_tests = _extract_failed_tests(state)
        if failed_tests:
            parts.append(
                "## Still-failing tests from last attempt\n\n"
                "Your previous patch did not pass all tests. "
                "Focus on these:" + failed_tests
            )

    parts.append(
        "## Task\n\n"
        "Explore the codebase and produce a unified diff that fixes the issue. "
        "End your response with the diff in a ```diff ... ``` block."
    )

    return "\n\n".join(parts)


def extract_diff(text: str) -> str | None:
    """
    Extract a unified diff from the LLM's response.

    Looks for a ```diff ... ``` code block first. Falls back to detecting
    a raw diff header (--- / +++ / @@) in case the model forgot the fences.
    Returns None if no diff found.
    """
    # Primary: fenced diff block
    match = re.search(r"```diff\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: raw unified diff header
    match = re.search(r"(--- .+?\n\+\+\+ .+?\n@@.+)", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


class Planner:
    """
    Handles the PLAN phase of the agent loop.

    The planner gives the LLM access to file-reading tools and asks it to
    explore the codebase, reason about the bug, then produce a unified diff.
    """

    def __init__(self, llm: LLMClient, max_tool_rounds: int = 15) -> None:
        self.llm = llm
        self.max_tool_rounds = max_tool_rounds

    def run(
        self,
        state: LoopState,
        env: Environment,
        task: Task,
        record: IterationRecord,
    ) -> None:
        """
        Execute the PLAN phase. Mutates `record` in place.

        After this call:
        - record.plan contains the full LLM response (plan + reasoning)
        - record.proposed_diff contains the extracted unified diff (or None)
        """
        truncations: dict[str, int] = {"read_file": 0, "search_code": 0}

        def tool_handler(name: str, inputs: dict[str, Any]) -> str:
            try:
                if name == "read_file":
                    content = env.read_file(inputs["path"])
                    lines = content.splitlines()
                    if len(lines) > _READ_FILE_MAX_LINES:
                        truncations["read_file"] += 1
                        truncated = "\n".join(lines[:_READ_FILE_MAX_LINES])
                        return truncated + f"\n\n[...truncated: {len(lines) - _READ_FILE_MAX_LINES} more lines not shown]"
                    return content
                elif name == "list_files":
                    files = env.list_files(inputs.get("pattern", "**/*.py"))
                    return "\n".join(files) if files else "(no files found)"
                elif name == "search_code":
                    results = env.search_code(inputs["query"])
                    if not results:
                        return "(no matches)"
                    capped = results[:_SEARCH_CODE_MAX_RESULTS]
                    output = "\n".join(
                        f"{r['file']}:{r['line']}: {r['text']}"
                        for r in capped
                    )
                    if len(results) > _SEARCH_CODE_MAX_RESULTS:
                        truncations["search_code"] += 1
                        output += f"\n[...{len(results) - _SEARCH_CODE_MAX_RESULTS} more results not shown]"
                    return output
                else:
                    return f"Unknown tool: {name}"
            except FileNotFoundError as e:
                return f"File not found: {e}"
            except Exception as e:
                return f"Tool error ({name}): {e}"

        user_message = build_user_message(task, state)

        response_text = self.llm.chat_with_tools(
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            tools=CODING_TOOLS,
            tool_handler=tool_handler,
            record=record,
            max_tool_rounds=self.max_tool_rounds,
        )

        record.plan = response_text
        record.proposed_diff = extract_diff(response_text)
        record.tool_truncations = truncations
