# CLAUDE.md — PatchLoop

Working reference for Claude Code. Keep this short. Session history → SESSIONS.md.

---

## What This Project Is

`patchloop` is a benchmarkable self-improving coding agent.
Given a buggy Python repo and an issue description, it autonomously explores, patches, tests, reflects, and retries.
Goal: demonstrate measurable improvement from reflection via a formal benchmark (4 baselines).

---

## Current Status

**26 tasks built. First statistically significant result on clean data achieved (Session 27).**

Baselines: `single_shot` | `loop` | `loop_testnames` | `loop_reflect`

**Main result** (mini_022 + mini_023 + mini_024, tool_rounds=8, gpt-oss-120b via Fireworks):

| baseline | solved | rate | 95% CI |
|---|---|---|---|
| loop | 2/35 | 5.7% | [0.007, 0.192] |
| loop_testnames | 2/19 | 10.5% | [0.013, 0.331] |
| **loop_reflect** | **9/25** | **36.0%** | [0.180, 0.575] |

Fisher's exact (one-tailed):
- **loop_reflect vs loop: p=0.0039** ← primary result
- loop_reflect vs loop_testnames: p=0.054 ← suggestive, not definitive

**Core claim:**
> On fully clean cascade-bug tasks with multi-hop hidden Bug B, loop_reflect substantially outperforms blind retry (9/25=36% vs 2/35=5.7%, p=0.0039). Separation from the test-name ablation is suggestive but not definitive (p=0.054).

**Per-task breakdown:**

| Task | loop | loop_testnames | loop_reflect |
|---|---|---|---|
| mini_022 | 1/16 = 6% | 1/7 = 14% | **4/9 = 44%** |
| mini_023 | 1/11 = 9% | 1/5 = 20% | 1/6 = 17% (noisy — weak Bug B) |
| mini_024 | 0/8 = 0% | 0/7 = 0% | **4/10 = 40%** |

mini_022 and mini_024 are the confirmed tasks. mini_023 is a negative design variant.

---

## Path Forward

**Result is locked. Main claim uses mini_022 + mini_023 + mini_024 only.**

mini_025 is a second negative design variant — loop_testnames=2/5, loop_reflect=0/5 because test_04 directly referenced `sample_size`, letting loop_testnames infer the expansion mechanic from the test body. Exclude from main claim pool.

**Negative design lessons:**
- mini_023: boolean classification Bug B → baseline stumbles on it by lucky file open
- mini_025: test_04 assertions expose expansion-related fields → loop_testnames infers Bug B from test body
- Implication: test_regression_04 must assert on a downstream metric (refund_rate, chargeback_rate) — NOT on intermediate fields like total_refunded or sample_size directly

**Next steps:**
1. Run signal pass on mini_026 (3 baselines, 5 reps, tool_rounds=8) — potential 4th confirmed task.
2. If mini_026 replicates: pool 022+024+026 for tighter stats (loop_testnames p<0.05 target).
3. **Stats**: `python eval/analysis/stats.py --tasks 022 023 024`

---

## Setup & Commands

```bash
cd ~/Desktop/projects/patchloop && source .venv/bin/activate
pip install -e ".[dev]"   # if reinstalling

# Run a task:
patchloop run mini_022 --model accounts/fireworks/models/gpt-oss-120b --baseline loop_reflect --tool-rounds 8

# Benchmark:
patchloop bench -t mini_022 -t mini_024 -b loop -b loop_testnames -b loop_reflect \
  --model accounts/fireworks/models/gpt-oss-120b --tool-rounds 8 --num-runs 3 --run-delay 45 --call-delay 5

# Stats:
python eval/analysis/stats.py --tasks 022 023 024

# Verify task cascade:
pytest eval/tasks/repos/mini_022/ -q --tb=short

ruff check patchloop/ tests/ eval/analysis/
```

---

## Reflection-Critical Task Design Rules

**Confirmed working pattern (mini_022, mini_024):**
1. **Bug A**: inverted division in `rate_calc.py` — findable in 1-2 reads from issue description
2. **Bug B**: `record_ops.expand_*_rows` copies full amount per expanded row instead of dividing by item count — requires tracing 3-hop chain (summary_builder → pipeline → record_ops)
3. **Issue description**: explicitly says "aggregated totals look correct, error is in final proportional step" — pulls model to calc file
4. **Generic test names**: `test_regression_N` — no file location signal
5. **tool_rounds=8**: Bug A findable, Bug B requires directed search

**Why arithmetic expansion works:** opening record_ops.py is not enough — model must understand row expansion semantics. Reflection provides "keep Bug A fix, look earlier in data path."

**Why boolean classification fails (mini_023):** once model opens the file, bug is visually obvious. No semantic reasoning required → baseline solves by luck.

---

## Locked Architecture Decisions

1. LocalEnvironment first; DockerEnvironment is Phase 2 stub.
2. Four baselines share the same code path (see baselines.py).
3. Reflection injection = ALL prior reflections from the current run (no filtering).
4. Phases: PLAN → APPLY_PATCH → RUN_TESTS → ANALYZE_FAILURE → REFLECT → DECIDE_NEXT → TERMINATE
5. Git commit after every APPLY_PATCH. Format: `[{run_id}] iter_{n}: apply patch`
6. Anti-repeat: MD5(last 500 chars stderr + last 200 chars stdout); STUCK after 3 consecutive identical.
7. No Claude authorship in git commits.

---

## Key Implementation Details

- **chat_with_tools exhaustion fallback** (client.py): after all tool rounds consumed, makes one final text-only call to force the model to commit a diff.
- **_apply_unified_diff** (git_ops.py): pure Python. Fallback: match removed lines only when full context match fails.
- **Reflection injection** (planner.py): only when `baseline == "loop_reflect"` AND reflections non-empty. Injects all lessons + `FAILED test_xxx` lines.
- **patch_assessment**: Reflector classifies each patch as `likely_wrong | likely_partial_success | unclear`. If partial success, planner prepends "do NOT revert — look for second bug."
- **# BUG: comments**: removed from all mini_016–021 in Session 26. Do not re-add.
- **loc_changed**: uses `git diff <snapshot_sha>` not uncommitted edits.
- **tool_rounds=8**: sweet spot for current task family. 6=too tight, 12=too permissive.

---

## Task Table (reflection-critical slice only)

| ID | Bug A | Bug B | Status |
|---|---|---|---|
| mini_016–021 | various | various | Dropped/deferred — # BUG: confound, then miscalibrated after removal |
| mini_022 | rate_calc.py inverted division | record_ops.expand_refund_rows: copies full refund per item | **CONFIRMED** loop_reflect=4/9=44%, loop=1/16=6% |
| mini_023 | score_calc.py inverted division | record_ops.attach_risk_flags: misses "review" | Negative variant — boolean Bug B too shallow. loop_reflect=1/6=17% |
| mini_024 | rate_calc.py inverted division | record_ops.expand_dispute_rows: copies full disputed_value per item | **CONFIRMED** loop_reflect=4/10=40%, loop=0/8=0%, loop_testnames=0/7=0% |
| mini_025 | rate_calc.py inverted division | record_ops.expand_sample_rows: copies full defective_units per item | **Negative variant 2.** loop_testnames=2/5, loop_reflect=0/5. test_04 exposes sample_size parameter directly — loop_testnames can infer expansion mechanic from test body. Exclude from main claim. |
| mini_026 | rate_calc.py inverted division | record_ops.expand_line_rows: copies full disputed_amount per item | **Pending signal pass.** Cascade verified (0/5 → 4/5 → 5/5). test_04 asserts only on dispute_rate. |

---

## LLM Providers

| Provider | Key | Model | Notes |
|---|---|---|---|
| **Fireworks (primary)** | `LLM_API_KEY` + `LLM_BASE_URL=https://api.fireworks.ai/inference/v1` | `accounts/fireworks/models/gpt-oss-120b` | Confirmed working. Use tool_rounds=8. |
| Cerebras | `CEREBRAS_API_KEY` | `qwen-3-235b-a22b-instruct-2507` | Congestion issues US hours. Secondary only. |
| SambaNova | `LLM_API_KEY` + `LLM_BASE_URL=https://api.sambanova.ai/v1` | `Meta-Llama-3.3-70B-Instruct` | 20 RPD. Second-model validation target. |

**All valid data uses Fireworks gpt-oss-120b without BUG comments. Do not pool with old Cerebras runs.**
