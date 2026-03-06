from __future__ import annotations

import json
import re

from patchloop.agent.state import IterationRecord, LoopState, Reflection
from patchloop.llm.client import LLMClient

_SYSTEM_PROMPT = """\
You are analyzing a failed software patch attempt. Your job is to produce a structured
reflection that will help the next patch attempt avoid repeating the same mistake.

Be concise and specific. Focus on actionable insights, not generic advice.
"""

_USER_TEMPLATE = """\
## Attempted patch

```diff
{diff}
```

## Test failure output

**stdout:**
```
{stdout}
```

**stderr:**
```
{stderr}
```

## Task

Analyze the failure and respond with a JSON object matching this exact schema:

```json
{{
  "error_type": "<short category: assertion_error | import_error | type_error | syntax_error | name_error | attribute_error | runtime_error | logic_error | other>",
  "what_failed": "<one sentence: what went wrong>",
  "root_cause_hypothesis": "<one or two sentences: why it likely failed>",
  "patch_summary": "<one sentence: what the patch attempted to do>",
  "lesson": "<one or two sentences: specific instruction for the next attempt to avoid this failure>"
}}
```

Respond with ONLY the JSON object. No markdown fences, no extra text.
"""


def _parse_reflection_json(text: str, iteration: int, sig: str) -> Reflection:
    """
    Parse the LLM's JSON response into a Reflection object.
    Falls back gracefully if the model doesn't follow the schema exactly.
    """
    # Strip markdown fences if the model included them anyway
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Best-effort: extract any recognizable content
        data = {
            "error_type": "unknown",
            "what_failed": text[:200],
            "root_cause_hypothesis": "Could not parse reflection.",
            "patch_summary": "Unknown",
            "lesson": "Re-read the failing test before proposing a patch.",
        }

    return Reflection(
        iteration=iteration,
        error_type=data.get("error_type", "unknown"),
        what_failed=data.get("what_failed", ""),
        root_cause_hypothesis=data.get("root_cause_hypothesis", ""),
        patch_summary=data.get("patch_summary", ""),
        lesson=data.get("lesson", ""),
        error_signature=sig,
    )


class Reflector:
    """
    Handles the REFLECT phase of the agent loop.

    Generates a structured Reflection from the test failure output.
    The reflection is stored in LoopState.reflections and injected
    into future PLAN prompts when baseline == "loop_reflect".
    """

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def reflect(self, state: LoopState, record: IterationRecord) -> Reflection:
        """
        Call the LLM to analyze the failure and produce a Reflection.
        Uses the simple chat() path (no tools needed here).
        """
        assert record.test_result is not None, "Reflect called without test result"

        diff = record.proposed_diff or "(no diff was applied)"
        sig = record.error_signature or LoopState.make_error_signature(
            record.test_result.stderr, record.test_result.stdout
        )

        user_message = _USER_TEMPLATE.format(
            diff=diff[:2000],               # cap diff size
            stdout=record.test_result.stdout[-1500:],
            stderr=record.test_result.stderr[-1500:],
        )

        response_text = self.llm.chat(
            system=_SYSTEM_PROMPT,
            user_message=user_message,
            record=record,
        )

        return _parse_reflection_json(response_text, state.iteration, sig)
