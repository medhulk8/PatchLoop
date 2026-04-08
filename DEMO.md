# PatchLoop — Demo Trace

A real agent run on `mini_022` (refund-rate pipeline), baseline `loop_reflect`, `tool_rounds=8`.
Run ID: `9cfc3f66`.

This trace shows exactly what structured reflection does: it turns a partial fix into a complete one by encoding a lesson about *where to look next*.

---

## The Task

**Issue description given to the agent:**

> The refund analytics pipeline is producing refund rates well above 1.0, which is impossible — refund rate should be total refunded value divided by total order value, always a proportion between 0.0 and 1.0.
>
> The aggregated totals (total refunded, total order value) appear reasonable when inspected individually. The error is isolated to the final step that converts those two totals into a proportional rate — the formula appears to have the numerator and denominator swapped.

**The repo has two bugs:**

- **Bug A** — `rate_calc.py`: `return total_order_value / total_refunded` (inverted)
- **Bug B** — `record_ops.expand_refund_rows`: copies `r.refund_amount` per expanded row instead of `r.refund_amount / r.quantity`

The issue description deliberately points toward `rate_calc.py`. Bug B is in a generically-named file three hops away in the call chain.

---

## Iteration 0 — Agent finds Bug A

The agent reads the issue, opens `rate_calc.py`, and proposes:

```diff
--- a/rate_calc.py
+++ b/rate_calc.py
-    return total_order_value / total_refunded
+    return total_refunded / total_order_value
```

**Test result:**

```
test_regression_01 PASSED
test_regression_02 PASSED
test_regression_03 PASSED
test_regression_04 FAILED   ← still failing
test_regression_05 PASSED

assert 180.0 == 60.0
```

4 of 5 tests pass. Bug A is fixed. But `test_regression_04` — the multi-quantity case — is still wrong. `total_refunded` is `180.0` when it should be `60.0`. The rate formula is now correct; the problem is upstream.

---

## Reflection — Agent encodes a lesson

Because the patch only partially succeeded, the reflector classifies it as `likely_partial_success` and writes a structured lesson:

```json
{
  "what_failed": "total_refunded is 180.0 instead of 60.0 for a multi-quantity refund case",
  "root_cause_hypothesis": "The function that expands refund rows copies the full refund_amount for each item instead of dividing it by the quantity, inflating the aggregated total_refunded.",
  "patch_assessment": "likely_partial_success",
  "lesson": "Examine the logic that expands or aggregates refunds for items with quantity > 1 and adjust it to allocate refund_amount proportionally per unit before summing."
}
```

The planner receives this lesson prepended to its next prompt:

> **do NOT revert the rate_calc.py fix — it is correct. Look for a second bug.**
> Lesson: *Examine the logic that expands or aggregates refunds for items with quantity > 1 and adjust it to allocate refund_amount proportionally per unit before summing.*

Without `loop_reflect`, the agent has no signal here. `test_regression_04` failing says nothing about which file to open next. The agent would have to guess — and typically guesses `rate_calc.py` again, stuck in a loop.

---

## Iteration 1 — Agent traces to Bug B

Armed with the lesson, the agent searches for expansion logic and opens `record_ops.py`. It finds:

```python
for r in records:
    item_value = r.order_value / r.quantity
    for _ in range(r.quantity):
        rows.append({
            "order_id": r.order_id,
            "order_value": item_value,
            "refund_amount": r.refund_amount,   # BUG: full amount copied per row
        })
```

It proposes:

```diff
--- a/record_ops.py
+++ b/record_ops.py
     for r in records:
         item_value = r.order_value / r.quantity
+        item_refund = r.refund_amount / r.quantity
         for _ in range(r.quantity):
             rows.append({
                 "order_id": r.order_id,
                 "order_value": item_value,
-                "refund_amount": r.refund_amount,
+                "refund_amount": item_refund,
             })
```

**Test result:**

```
test_regression_01 PASSED
test_regression_02 PASSED
test_regression_03 PASSED
test_regression_04 PASSED
test_regression_05 PASSED

5 passed in 0.01s ✓
```

---

## What this demonstrates

| | `loop` | `loop_testnames` | `loop_reflect` |
|---|---|---|---|
| Knows which tests failed | ✗ | ✓ | ✓ |
| Knows *why* Bug A was only partial | ✗ | ✗ | ✓ |
| Redirected to `record_ops.py` | rarely | rarely | consistently |
| Solve rate on mini_022 + mini_024 | 8.3% | 10.0% | **38.5%** |

`loop_testnames` knows `test_regression_04` is still failing — but that tells it nothing about which file to open. The structured lesson is what makes the difference: it encodes the *semantic content* of the failure, not just which test failed.

This is the regime where reflection becomes load-bearing.
