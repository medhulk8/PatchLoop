from __future__ import annotations

import re
from typing import Any

from patchloop.agent.state import IterationRecord, LoopState
from patchloop.environment.base import Environment
from patchloop.environment.task import Task
from patchloop.llm.client import CODING_TOOLS, LLMClient

_SYSTEM_PROMPT = """\
You are an expert software engineer fixing a bug in a Python codebase.

Your workflow:
1. Read the issue description carefully.
2. The repository files are already provided in the message — read them thoroughly.
   Use the tools only if you need to re-read a file or search for something specific.
3. Produce a minimal, correct unified diff (git diff format) that fixes the issue.

Rules:
- Make the smallest change that fixes the bug. Do not refactor unrelated code.
- Output the diff inside a ```diff ... ``` code block at the END of your response.
- The diff must use correct file paths relative to the repo root.
- If you truly cannot determine a fix, say so clearly — do not produce a broken patch.
"""


def _build_repo_context(env: Environment) -> str:
    """
    Pre-load all Python source files from the workspace into a single string.

    Injecting file contents upfront eliminates the need for the model to
    spend multiple tool-call rounds reading files it will need anyway.
    For our small benchmark repos (1–3 files) this cuts calls per iteration
    from ~8 down to ~1-2.
    """
    try:
        files = env.list_files("**/*.py")
    except Exception:
        return ""

    if not files:
        return ""

    parts = ["## Repository Files\n"]
    for path in files:
        try:
            content = env.read_file(path)
            parts.append(f"### `{path}`\n```python\n{content}\n```")
        except Exception:
            pass

    return "\n\n".join(parts)


def build_user_message(task: Task, state: LoopState, repo_context: str = "") -> str:
    """
    Build the user message for the PLAN phase.

    On iteration 0: issue + repo file contents.
    On iteration >= 1 with reflections: also prepend "Lessons learned" from
    prior failed attempts. This is the core of the in-run reflection mechanism.
    """
    parts = [f"## Issue\n\n{task.issue.strip()}"]

    if repo_context:
        parts.append(repo_context)

    if state.reflections and state.baseline == "loop_reflect":
        lessons = "\n".join(
            f"- **Iteration {r.iteration}**: {r.lesson}"
            for r in state.reflections
        )
        parts.append(
            "## Lessons from previous failed attempts\n\n"
            "Do NOT repeat these mistakes:\n\n" + lessons
        )

    parts.append(
        "## Task\n\n"
        "Produce a unified diff that fixes the issue. "
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

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

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
        def tool_handler(name: str, inputs: dict[str, Any]) -> str:
            try:
                if name == "read_file":
                    return env.read_file(inputs["path"])
                elif name == "list_files":
                    files = env.list_files(inputs.get("pattern", "**/*.py"))
                    return "\n".join(files) if files else "(no files found)"
                elif name == "search_code":
                    results = env.search_code(inputs["query"])
                    if not results:
                        return "(no matches)"
                    return "\n".join(
                        f"{r['file']}:{r['line']}: {r['text']}"
                        for r in results
                    )
                else:
                    return f"Unknown tool: {name}"
            except FileNotFoundError as e:
                return f"File not found: {e}"
            except Exception as e:
                return f"Tool error ({name}): {e}"

        repo_context = _build_repo_context(env)
        user_message = build_user_message(task, state, repo_context)

        response_text = self.llm.chat_with_tools(
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            tools=CODING_TOOLS,
            tool_handler=tool_handler,
            record=record,
        )

        record.plan = response_text
        record.proposed_diff = extract_diff(response_text)
