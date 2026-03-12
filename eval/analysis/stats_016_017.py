"""
Statistical analysis of benchmark results: mini_016 + mini_017, tool_rounds=6.

Data (from replicated runs, 3× each task):
  mini_016: loop=1/3, loop_testnames=1/3, loop_reflect=2/3
  mini_017: loop=0/3, loop_testnames=0/3, loop_reflect=2/3

Pooled (6 runs per baseline):
  loop:           2/6 resolved
  loop_testnames: 2/6 resolved
  loop_reflect:   4/6 resolved
"""

import math
from scipy import stats


# ── Raw data ──────────────────────────────────────────────────────────────────

results = {
    "mini_016": {"loop": (1, 3), "loop_testnames": (1, 3), "loop_reflect": (2, 3)},
    "mini_017": {"loop": (0, 3), "loop_testnames": (0, 3), "loop_reflect": (2, 3)},
}

BASELINES = ["loop", "loop_testnames", "loop_reflect"]

# Pooled
pooled = {}
for bl in BASELINES:
    k = sum(results[t][bl][0] for t in results)
    n = sum(results[t][bl][1] for t in results)
    pooled[bl] = (k, n)


# ── Helpers ───────────────────────────────────────────────────────────────────

def wilson_ci(k, n, z=1.96):
    """Wilson score interval."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0, center - margin), min(1, center + margin))


def exact_ci(k, n, alpha=0.05):
    """Clopper-Pearson exact interval."""
    lo = stats.beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = stats.beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return (lo, hi)


def fisher_2x2(k1, n1, k2, n2):
    """One-tailed Fisher's exact test: P(group1 > group2)."""
    table = [[k1, n1 - k1], [k2, n2 - k2]]
    _, p_two = stats.fisher_exact(table, alternative="two-sided")
    _, p_one = stats.fisher_exact(table, alternative="greater")
    return p_one, p_two


def power_needed(p1, p2, alpha=0.05, power=0.80):
    """
    Approximate sample size per group needed to detect p1 vs p2
    with given alpha and power (one-tailed, Fisher's exact approximation via normal).
    """
    if p1 == p2:
        return float("inf")
    z_a = stats.norm.ppf(1 - alpha)
    z_b = stats.norm.ppf(power)
    p_bar = (p1 + p2) / 2
    n = (z_a * math.sqrt(2 * p_bar * (1 - p_bar)) + z_b * math.sqrt(
        p1 * (1 - p1) + p2 * (1 - p2)
    ))**2 / (p1 - p2)**2
    return math.ceil(n)


# ── Print results ─────────────────────────────────────────────────────────────

print("=" * 65)
print("PatchLoop Statistical Analysis — mini_016 + mini_017")
print("tool_rounds=6, model=gpt-oss-120b, N=3 per task per baseline")
print("=" * 65)

print("\n── Per-task breakdown ──────────────────────────────────────")
for task, data in results.items():
    print(f"\n  {task}:")
    for bl in BASELINES:
        k, n = data[bl]
        pct = k / n * 100
        print(f"    {bl:<20} {k}/{n} = {pct:.1f}%")

print("\n── Pooled (6 runs per baseline) ────────────────────────────")
print(f"\n  {'Baseline':<20} {'k/n':>5}   {'%':>6}   {'Wilson 95% CI':>22}   {'Exact 95% CI':>22}")
print(f"  {'-'*20}  {'-'*5}   {'-'*6}   {'-'*22}   {'-'*22}")
for bl in BASELINES:
    k, n = pooled[bl]
    pct = k / n * 100
    wlo, whi = wilson_ci(k, n)
    elo, ehi = exact_ci(k, n)
    print(f"  {bl:<20} {k}/{n}    {pct:>5.1f}%"
          f"   [{wlo:.3f}, {whi:.3f}]          [{elo:.3f}, {ehi:.3f}]")

print("\n── Fisher's exact tests (one-tailed: row1 > row2) ─────────")
pairs = [
    ("loop_reflect", "loop"),
    ("loop_reflect", "loop_testnames"),
    ("loop",         "loop_testnames"),
]
for b1, b2 in pairs:
    k1, n1 = pooled[b1]
    k2, n2 = pooled[b2]
    p_one, p_two = fisher_2x2(k1, n1, k2, n2)
    table = f"[{k1}/{n1} vs {k2}/{n2}]"
    print(f"\n  {b1} > {b2}  {table}")
    print(f"    p (one-tailed) = {p_one:.4f}   p (two-tailed) = {p_two:.4f}")
    sig = "* (p<0.05)" if p_one < 0.05 else "n.s."
    print(f"    → {sig}")

print("\n── Power analysis ──────────────────────────────────────────")
print("  How many runs per baseline needed to detect loop_reflect advantage?\n")
p_reflect = pooled["loop_reflect"][0] / pooled["loop_reflect"][1]  # 0.667
p_loop    = pooled["loop"][0]         / pooled["loop"][1]           # 0.333
for alpha in [0.05, 0.10]:
    for power_level in [0.80, 0.90]:
        n = power_needed(p_reflect, p_loop, alpha=alpha, power=power_level)
        print(f"  α={alpha}, power={power_level}: need {n} runs/baseline "
              f"(= {n//3} task-reps per task if 3 tasks)")

print("\n── Summary ─────────────────────────────────────────────────")
print("""
  Current N=6 per baseline is too small to reach p<0.05.
  The direction is consistent (loop_reflect=4/6 vs loop=loop_testnames=1/6 each),
  but wide CIs mean the difference is not yet statistically significant.

  Note: CLAUDE.md budget table shows "loop=33.3%" at tool_rounds=6, which would
  imply 2/6. The actual per-task data (loop: mini_016=1/3, mini_017=0/3 = 1/6)
  gives a LARGER observed effect (p_reflect - p_loop = 0.50 vs 0.33 assumed).
  This should be verified against the raw JSONL logs.

  With the observed effect (p_reflect≈0.667, p_loop≈0.167):
  - Power formula gives N≈11 runs/baseline at α=0.05, power=0.80
  - With 5 confirmed tasks (016–020) × 3 reps = 15 runs/baseline → exceeds target
  - With just 018/019/020 confirmed (3 tasks × 3 reps = 9 runs) → N=15 pooled

  Practical path to significance:
  1. Confirm mini_018/019/020 replicate the pattern (currently running)
  2. Pool all 5 tasks: N=15/baseline — should reach p<0.05 if effect holds
  3. If CLAUDE.md table is correct (loop=2/6), need ~24 runs/baseline instead
""")
print("=" * 65)
