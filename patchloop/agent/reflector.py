from __future__ import annotations

import json
import re

from patchloop.agent.state import IterationRecord, LoopState, Reflection
from patchloop.llm.client import LLMClient

_SYSTEM_PROMPT = """\
You are analyzing a failed software patch attempt. Your job is to produce a structured
reflection that will help the next patch attempt avoid repeating the same mistake.

Critical rules:
- If the patch caused MORE tests to pass than before, treat it as LIKELY CORRECT BUT INCOMPLETE.
  Do NOT recommend reverting it unless you have direct evidence it caused a regression.
- A patch that improved test outcomes probably fixed one bug. The remaining failures
  likely indicate a SECOND bug elsewhere in the codebase.
- Frame the lesson as a SEARCH DIRECTION (where to look next), not a root-cause verdict.
- Be concise and specific. Focus on actionable guidance, not generic advice.
"""

_USER_TEMPLATE = """\
## Test results before this patch

Tests passing before patch: {prev_passed}
Tests failing before patch: {prev_failed}

## Attempted patch

```diff
{diff}
```

## Test results after this patch

Tests passing after patch: {curr_passed}
Tests failing after patch: {curr_failed}

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
  "what_failed": "<one sentence: what is still failing after the patch>",
  "root_cause_hypothesis": "<one or two sentences: why the remaining failure likely occurs>",
  "patch_summary": "<one sentence: what the patch attempted to do>",
  "patch_assessment": "<one of: likely_wrong | likely_partial_success | unclear>",
  "lesson": "<one or two sentences: WHERE TO LOOK NEXT — a search direction, not a root-cause verdict. If tests improved, do not suggest reverting the patch.>"
}}
```

Rules for patch_assessment:
- Use "likely_partial_success" if more tests pass now than before.
- Use "likely_wrong" only if the patch caused a regression (fewer tests pass now) or no change at all AND there is direct evidence the patch is wrong.
- Use "unclear" otherwise.

Respond with ONLY the JSON object. No markdown fences, no extra text.
"""


def _count_tests(output: str) -> tuple[int, int]:
    """
    Parse pytest output to count passed and not-passed tests.
    Returns (passed, not_passed) where not_passed includes failed + error + xfailed.

    Parses all "N <status>" tokens from the pytest summary line, e.g.:
      "4 passed, 1 failed, 2 error in 0.5s"
      "5 failed in 0.3s"
      "3 passed in 0.1s"
    """
    passed = 0
    not_passed = 0
    for m in re.finditer(r"(\d+)\s+(passed|failed|error|errors|xfailed|xpassed)", output, re.IGNORECASE):
        count = int(m.group(1))
        status = m.group(2).lower()
        if status == "passed":
            passed += count
        else:
            not_passed += count
    return passed, not_passed


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
        data = {
            "error_type": "unknown",
            "what_failed": text[:200],
            "root_cause_hypothesis": "Could not parse reflection.",
            "patch_summary": "Unknown",
            "patch_assessment": "unclear",
            "lesson": "Re-read the failing test before proposing a patch.",
        }

    return Reflection(
        iteration=iteration,
        error_type=data.get("error_type", "unknown"),
        what_failed=data.get("what_failed", ""),
        root_cause_hypothesis=data.get("root_cause_hypothesis", ""),
        patch_summary=data.get("patch_summary", ""),
        patch_assessment=data.get("patch_assessment", "unclear"),
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

        # Compute test delta: how many tests passed before vs after this patch
        prev_record = state.iterations[-2] if len(state.iterations) >= 2 else None
        if prev_record and prev_record.test_result:
            prev_combined = (prev_record.test_result.stdout or "") + "\n" + (prev_record.test_result.stderr or "")
            prev_passed, prev_failed = _count_tests(prev_combined)
        else:
            # Iteration 0 — no prior test result, assume all failed
            prev_passed, prev_failed = 0, "unknown"

        curr_combined = (record.test_result.stdout or "") + "\n" + (record.test_result.stderr or "")
        curr_passed, curr_failed = _count_tests(curr_combined)

        user_message = _USER_TEMPLATE.format(
            prev_passed=prev_passed,
            prev_failed=prev_failed,
            diff=diff[:2000],
            curr_passed=curr_passed,
            curr_failed=curr_failed,
            stdout=record.test_result.stdout[-1500:],
            stderr=record.test_result.stderr[-1500:],
        )

        response_text = self.llm.chat(
            system=_SYSTEM_PROMPT,
            user_message=user_message,
            record=record,
        )

        return _parse_reflection_json(response_text, state.iteration, sig)
