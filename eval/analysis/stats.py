"""
PatchLoop statistical analysis — reads directly from runs/report_*.json.

Usage:
    python eval/analysis/stats.py                          # all tasks
    python eval/analysis/stats.py --tasks 016 017 020      # specific tasks
    python eval/analysis/stats.py --runs-dir path/to/runs  # custom runs dir

Valid runs: all termination_reason values except ERROR
Invalid (excluded): termination_reason == ERROR (infrastructure failure — quota, API crash)

NO_DIFF and MAX_ITERATIONS are agent failures and count in the denominator.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from scipy import stats as scipy_stats

BASELINES = ["loop", "loop_testnames", "loop_reflect"]
INVALID_TERMINATIONS = {"ERROR"}


# ── Data loading ──────────────────────────────────────────────────────────────

def load_results(runs_dir: Path) -> list[dict]:
    """Load all run records from every report_*.json in runs_dir."""
    records = []
    for path in sorted(runs_dir.glob("report_*.json")):
        with open(path) as f:
            data = json.load(f)
        for r in data.get("results", []):
            r["_source"] = path.name
            records.append(r)
    return records


def compute_kn(
    records: list[dict],
    task_ids: list[str],
    baseline: str,
) -> tuple[int, int]:
    """Return (successes, valid_runs) for the given tasks and baseline."""
    relevant = [
        r for r in records
        if r["task_id"] in task_ids
        and r["baseline"] == baseline
        and r["termination_reason"] not in INVALID_TERMINATIONS
    ]
    k = sum(1 for r in relevant if r["resolved"])
    return k, len(relevant)


# ── Statistics ────────────────────────────────────────────────────────────────

def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def exact_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lo = scipy_stats.beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = scipy_stats.beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return (lo, hi)


def fisher_one_tail(k1: int, n1: int, k2: int, n2: int) -> float:
    table = [[k1, n1 - k1], [k2, n2 - k2]]
    _, p = scipy_stats.fisher_exact(table, alternative="greater")
    return p


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_task_breakdown(
    records: list[dict],
    task_ids: list[str],
) -> None:
    print("\n── Per-task breakdown (valid runs only) ─────────────────────────")
    for tid in sorted(task_ids):
        print(f"\n  {tid}:")
        for bl in BASELINES:
            k, n = compute_kn(records, [tid], bl)
            pct = f"{k/n*100:.0f}%" if n else "—"
            print(f"    {bl:<20} {k}/{n} = {pct}")


def print_pooled(
    records: list[dict],
    task_ids: list[str],
    label: str,
) -> dict[str, tuple[int, int]]:
    print(f"\n── Pooled: {label} ──────────────────────────────────────────────")
    pooled: dict[str, tuple[int, int]] = {}
    for bl in BASELINES:
        k, n = compute_kn(records, task_ids, bl)
        pooled[bl] = (k, n)
        wlo, whi = wilson_ci(k, n)
        elo, ehi = exact_ci(k, n)
        pct = f"{k/n*100:.1f}%" if n else "—"
        print(
            f"  {bl:<20} {k}/{n} = {pct:<7} "
            f"Wilson [{wlo:.3f},{whi:.3f}]  Exact [{elo:.3f},{ehi:.3f}]"
        )
    return pooled


def print_fisher(pooled: dict[str, tuple[int, int]]) -> None:
    print("\n── Fisher's exact (loop_reflect vs others, one-tailed) ──────────")
    k1, n1 = pooled["loop_reflect"]
    for bl in ["loop", "loop_testnames"]:
        k2, n2 = pooled[bl]
        if n1 == 0 or n2 == 0:
            print(f"  loop_reflect vs {bl}: insufficient data")
            continue
        p = fisher_one_tail(k1, n1, k2, n2)
        sig = "* p<0.05" if p < 0.05 else ("† p<0.10" if p < 0.10 else "n.s.")
        print(f"  loop_reflect [{k1}/{n1}] > {bl} [{k2}/{n2}]: p={p:.4f}  {sig}")


def print_error_summary(records: list[dict], task_ids: list[str]) -> None:
    print("\n── ERROR/excluded runs ───────────────────────────────────────────")
    errors = [
        r for r in records
        if r["task_id"] in task_ids
        and r["termination_reason"] == "ERROR"
    ]
    if not errors:
        print("  (none)")
        return
    by_task_bl: dict[str, dict[str, int]] = {}
    for r in errors:
        by_task_bl.setdefault(r["task_id"], {}).setdefault(r["baseline"], 0)
        by_task_bl[r["task_id"]][r["baseline"]] += 1
    for tid in sorted(by_task_bl):
        parts = [f"{bl}={cnt}" for bl, cnt in sorted(by_task_bl[tid].items())]
        print(f"  {tid}: {', '.join(parts)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="PatchLoop statistical analysis")
    parser.add_argument(
        "--tasks", nargs="+", metavar="ID",
        help="Task suffixes to include, e.g. 016 017 020 (default: all in reports)",
    )
    parser.add_argument(
        "--runs-dir", default="runs", metavar="DIR",
        help="Directory containing report_*.json files (default: runs/)",
    )
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    if not runs_dir.exists():
        print(f"Error: runs directory not found: {runs_dir}", file=sys.stderr)
        sys.exit(1)

    records = load_results(runs_dir)
    if not records:
        print(f"No report_*.json files found in {runs_dir}", file=sys.stderr)
        sys.exit(1)

    # Determine task IDs to analyse
    all_task_ids = sorted({r["task_id"] for r in records})
    if args.tasks:
        task_ids = [
            tid for tid in all_task_ids
            if any(tid.endswith(suffix) for suffix in args.tasks)
        ]
        if not task_ids:
            print(f"No tasks matched suffixes: {args.tasks}", file=sys.stderr)
            sys.exit(1)
    else:
        task_ids = all_task_ids

    print("=" * 68)
    print("PatchLoop Statistical Analysis")
    print(f"Tasks: {', '.join(task_ids)}")
    print(f"Source: {runs_dir}/report_*.json  ({len(records)} total run records)")
    print("=" * 68)

    print_task_breakdown(records, task_ids)
    pooled = print_pooled(records, task_ids, ", ".join(task_ids))
    print_fisher(pooled)
    print_error_summary(records, task_ids)
    print("\n" + "=" * 68)


if __name__ == "__main__":
    main()
