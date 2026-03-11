"""
Statistical analysis: mini_018 + mini_019 + mini_020 benchmark results.
tool_rounds=6, model=gpt-oss-120b, target N=3 per task per baseline.

Data validity:
  SUCCESS / TIME_LIMIT = valid run
  ERROR = truncated by rate-limit exhaustion or token quota — excluded

Termination breakdown:
  mini_018: loop=[TL,ERR,TL], loop_testnames=[TL,TL,ERR], loop_reflect=[TL,TL,ERR]
  mini_019: loop=[ERR,ERR,TL], loop_testnames=[TL,TL,ERR], loop_reflect=[SUC,SUC,ERR]
  mini_020: loop=[TL,TL,SUC], loop_testnames=[TL,TL,ERR], loop_reflect=[TL,SUC,ERR]

Valid runs only (excluding ERROR):
  mini_018: loop=0/2, loop_testnames=0/2, loop_reflect=0/2
  mini_019: loop=0/1, loop_testnames=0/2, loop_reflect=2/2
  mini_020: loop=1/3, loop_testnames=0/2, loop_reflect=1/2

Note: mini_018 loop_reflect=0/2 is likely due to Bug B design issue (custom string
formatting spec too hard to reverse-engineer), not a reflection failure.
Rep 3 of loop_testnames and loop_reflect needs rerun on a fresh quota day.
"""

import math
from scipy import stats


# ── Valid data (excluding ERROR terminations) ─────────────────────────────────

results_new = {
    "mini_018": {"loop": (0, 2), "loop_testnames": (0, 2), "loop_reflect": (0, 2)},
    "mini_019": {"loop": (0, 1), "loop_testnames": (0, 2), "loop_reflect": (2, 2)},
    "mini_020": {"loop": (1, 3), "loop_testnames": (0, 2), "loop_reflect": (1, 2)},
}

# Prior confirmed data: mini_016 + mini_017 (all 3 reps valid, tool_rounds=6)
results_prior = {
    "mini_016": {"loop": (1, 3), "loop_testnames": (1, 3), "loop_reflect": (2, 3)},
    "mini_017": {"loop": (0, 3), "loop_testnames": (0, 3), "loop_reflect": (2, 3)},
}

BASELINES = ["loop", "loop_testnames", "loop_reflect"]


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0, center - margin), min(1, center + margin))


def exact_ci(k, n, alpha=0.05):
    lo = stats.beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = stats.beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return (lo, hi)


def fisher_one_tail(k1, n1, k2, n2):
    table = [[k1, n1 - k1], [k2, n2 - k2]]
    _, p = stats.fisher_exact(table, alternative="greater")
    return p


print("=" * 68)
print("PatchLoop Statistical Analysis — mini_019 + mini_020 (new tasks)")
print("=" * 68)

print("\n── New tasks: valid runs only ───────────────────────────────────")
for task, data in results_new.items():
    print(f"\n  {task}:")
    for bl in BASELINES:
        k, n = data[bl]
        note = ""
        if task == "mini_018" and bl == "loop_reflect":
            note = "  ← Bug B design issue (too hard, not reflection-critical)"
        print(f"    {bl:<20} {k}/{n} = {k/n*100 if n else 0:.0f}%{note}")

# Exclude mini_018 from the analysis (design issue)
print("\n── Pooled analysis: mini_019 + mini_020 (valid runs only) ──────")
pooled_new = {}
for bl in BASELINES:
    k = sum(results_new[t][bl][0] for t in ["mini_019", "mini_020"])
    n = sum(results_new[t][bl][1] for t in ["mini_019", "mini_020"])
    pooled_new[bl] = (k, n)
for bl in BASELINES:
    k, n = pooled_new[bl]
    print(f"  {bl:<20} {k}/{n} = {k/n*100 if n else 0:.1f}%")

print("\n── ALL confirmed reflection-critical tasks pooled ───────────────")
print("   (mini_016, mini_017 full 3×; mini_019, mini_020 valid runs only)\n")

pooled_all = {}
for bl in BASELINES:
    k_prior = sum(results_prior[t][bl][0] for t in results_prior)
    n_prior = sum(results_prior[t][bl][1] for t in results_prior)
    k_new = sum(results_new[t][bl][0] for t in ["mini_019", "mini_020"])
    n_new = sum(results_new[t][bl][1] for t in ["mini_019", "mini_020"])
    k, n = k_prior + k_new, n_prior + n_new
    pooled_all[bl] = (k, n)
    wlo, whi = wilson_ci(k, n)
    elo, ehi = exact_ci(k, n)
    print(f"  {bl:<20} {k}/{n} = {k/n*100:.1f}%  "
          f"Wilson [{wlo:.3f},{whi:.3f}]  Exact [{elo:.3f},{ehi:.3f}]")

print("\n── Fisher's exact (loop_reflect vs others, pooled all) ─────────")
k1, n1 = pooled_all["loop_reflect"]
for bl in ["loop", "loop_testnames"]:
    k2, n2 = pooled_all[bl]
    p = fisher_one_tail(k1, n1, k2, n2)
    sig = "* p<0.05" if p < 0.05 else ("† p<0.10" if p < 0.10 else "n.s.")
    print(f"  loop_reflect [{k1}/{n1}] > {bl} [{k2}/{n2}]: p={p:.4f}  {sig}")

print("\n── What's needed for clean 3× completion ────────────────────────")
print("""
  Still needed (fresh quota day):
    loop_testnames rep3: mini_018, mini_019, mini_020
    loop_reflect   rep3: mini_018, mini_019, mini_020
    loop           rep3: mini_019 (only 1 valid rep currently)

  Decision: redesign mini_018 Bug B (current spec is too hard for any baseline).
  Replace :.2f format bug with int() truncation (same as mini_017/019/020 pattern).
  Then rerun all 3 reps on a fresh quota day.
""")
print("=" * 68)
