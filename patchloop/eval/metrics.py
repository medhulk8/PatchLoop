from __future__ import annotations

from collections import defaultdict
from typing import Any

from patchloop.environment.task import TaskResult


def compute_metrics(results: list[TaskResult]) -> dict[str, Any]:
    """
    Compute benchmark metrics from a list of TaskResults.

    Returns a dict with top-level summary stats and a per-baseline
    breakdown. The per-baseline breakdown is what we use to compare
    single_shot vs loop vs loop_testnames vs loop_reflect.
    """
    if not results:
        return {}

    # Group results by baseline
    by_baseline: dict[str, list[TaskResult]] = defaultdict(list)
    for r in results:
        by_baseline[r.baseline].append(r)

    unique_tasks = len({r.task_id for r in results})
    summary: dict[str, Any] = {
        "total_runs": len(results),
        "total_tasks": unique_tasks,
        "baselines": {},
    }

    for baseline, baseline_results in by_baseline.items():
        resolved = [r for r in baseline_results if r.resolved]
        failed = [r for r in baseline_results if not r.resolved]

        resolve_rate = len(resolved) / len(baseline_results) if baseline_results else 0.0

        avg_iters_success = (
            sum(r.iterations_used for r in resolved) / len(resolved)
            if resolved else None
        )

        avg_iters_fail = (
            sum(r.iterations_used for r in failed) / len(failed)
            if failed else None
        )

        avg_runtime = (
            sum(r.total_duration_s for r in baseline_results) / len(baseline_results)
        )

        avg_loc = (
            sum(r.loc_changed for r in resolved) / len(resolved)
            if resolved else 0
        )

        repeat_rate = (
            sum(r.repeated_failure_count for r in baseline_results)
            / max(sum(r.iterations_used for r in baseline_results), 1)
        )

        summary["baselines"][baseline] = {
            "n_tasks": len(baseline_results),
            "n_resolved": len(resolved),
            "resolve_rate": round(resolve_rate, 3),
            "avg_iterations_to_success": round(avg_iters_success, 2)
            if avg_iters_success is not None else None,
            "avg_iterations_on_failure": round(avg_iters_fail, 2)
            if avg_iters_fail is not None else None,
            "avg_runtime_s": round(avg_runtime, 1),
            "avg_loc_changed": round(avg_loc, 1),
            "repeat_failure_rate": round(repeat_rate, 3),
            "termination_reasons": _count_termination_reasons(baseline_results),
        }

    return summary


def _count_termination_reasons(results: list[TaskResult]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in results:
        counts[r.termination_reason] += 1
    return dict(counts)


def format_summary_table(summary: dict[str, Any]) -> str:
    """
    Format the metrics summary as a readable table for CLI output.
    Ordered: single_shot < loop < loop_testnames < loop_reflect so the comparison reads left-to-right.
    """
    if not summary:
        return "No results."

    baseline_order = ["single_shot", "loop", "loop_testnames", "loop_reflect"]
    available = [b for b in baseline_order if b in summary.get("baselines", {})]
    # Append any baselines not in the standard order
    available += [
        b for b in summary["baselines"] if b not in baseline_order
    ]

    if not available:
        return "No baselines found."

    col_w = 18
    header = f"{'Metric':<28}" + "".join(f"{b:>{col_w}}" for b in available)
    sep = "-" * len(header)

    rows = [header, sep]

    def row(label: str, key: str, fmt: str = "") -> str:
        vals = []
        for b in available:
            v = summary["baselines"][b].get(key)
            if v is None:
                vals.append(f"{'—':>{col_w}}")
            elif fmt == "%":
                vals.append(f"{v*100:>{col_w-1}.1f}%")
            elif fmt == "f":
                vals.append(f"{v:>{col_w}.2f}")
            else:
                vals.append(f"{str(v):>{col_w}}")
        return f"{label:<28}" + "".join(vals)

    rows += [
        row("Tasks",                     "n_tasks"),
        row("Resolved",                  "n_resolved"),
        row("Resolve rate",              "resolve_rate",              "%"),
        row("Avg iters (success)",       "avg_iterations_to_success", "f"),
        row("Avg iters (failure)",       "avg_iterations_on_failure", "f"),
        row("Avg runtime (s)",           "avg_runtime_s",             "f"),
        row("Avg LOC changed",           "avg_loc_changed",           "f"),
        row("Repeat failure rate",       "repeat_failure_rate",       "%"),
    ]

    return "\n".join(rows)
