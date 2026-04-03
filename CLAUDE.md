# CLAUDE.md — PatchLoop

Working reference for Claude Code. Keep this short. Session history → SESSIONS.md.

---

## What This Project Is

`patchloop` is a benchmarkable self-improving coding agent.
Given a buggy Python repo and an issue description, it autonomously explores, patches, tests, reflects, and retries.
Goal: demonstrate measurable improvement from reflection via a formal benchmark (4 baselines).

---

## Current Status

**⚠ CONFOUND DISCOVERED + RESOLVED**: All reflection-critical tasks (mini_016–021) had `# BUG:` inline comments that leaked bug location and type to the model. Prior "confirmed" results (016=66.7%, 017=66.7%, 020=2/2) are invalidated — the model was reading the hints, not reasoning from reflection. Comments removed in Session 26.

**24 tasks built. Cleaned first sweep complete (report_1775208132.json). No task confirmed reflection-critical on cleaned data yet. Recalibration needed.**

Baselines: `single_shot` | `loop` | `loop_testnames` | `loop_reflect`

**First clean 54-run sweep** (6 tasks × 3 baselines × 3 reps, gpt-oss-120b via Fireworks, # BUG: comments removed):

| baseline | resolved | resolve_rate |
|---|---|---|
| loop | 2/18 | 11.1% |
| loop_testnames | 3/18 | 16.7% |
| loop_reflect | 3/18 | 16.7% |

Per-task loop_reflect: mini_016=1/3, mini_017=0/3, mini_018=0/3, mini_019=**2/3**, mini_020=0/3, mini_021=1/3

**Key finding from cleaned sweep**: tasks too hard without hints (11-17% solve rate, no signal). Led to multi-hop Bug B redesign.

**First significant result (mini_022 + mini_023 + mini_024, tool_rounds=8):**

| baseline | solved | solve_rate |
|---|---|---|
| loop | 2/26 | 7.7% |
| loop_testnames | 2/11 | 18.2% |
| loop_reflect | 5/15 | **33.3%** |

Fisher's exact (loop_reflect vs loop): **p=0.0495** — first p<0.05 on clean data.

**Caveats:** result is fragile (barely over threshold, small n, unbalanced run counts from triage). loop_reflect vs loop_testnames not yet significant (p=0.345) — reflection-as-mechanism is suggestive (log evidence) not statistically confirmed. mini_023 noisy (boolean classification Bug B too shallow). mini_022 and mini_024 are the clean signal tasks.

**Honest framing (per ChatGPT):**
> On a small set of fully clean cascade-bug tasks, loop_reflect outperformed blind retry (5/15 vs 2/26, one-sided Fisher p=0.0495). Evidence against loop_testnames is not yet significant, so the role of structured reflection is supported by directional results and log-level behavior rather than definitive statistical separation.

---

## Path Forward (priority order)

The goal is a **probabilistic regime** — not a perfect deterministic sweet spot. Tasks should make brute-force rare enough that reflection has measurable headroom, not impossible.

### Phase 1: Strengthen mini_022 + mini_024 signal (in progress)

Run 3 more reps on mini_022 and mini_024 to widen the margin above p=0.05:

```
patchloop bench -t mini_022 -t mini_024 -b loop -b loop_testnames -b loop_reflect \
  --model accounts/fireworks/models/gpt-oss-120b \
  --tool-rounds 8 --num-runs 3 --run-delay 45 --call-delay 5
```

### Phase 2: Build a 4th mini_022-style task

After Phase 1, add one more task in the arithmetic-expansion Bug B family to widen the task set from 2 to 3 confirmed tasks.

### Phase 3: Statistical update

```
python eval/analysis/stats.py --tasks 022 023 024
```

Minimum viable evidence: loop_reflect vs loop p<0.05 confirmed with wider margin, loop_reflect vs loop_testnames directional with log support.

**Note:** do NOT increase `max_iterations`. The bottleneck is exploration budget (tool_rounds), not iteration count.

---

## Setup

```bash
cd ~/Desktop/projects/patchloop
source .venv/bin/activate          # Python 3.13, venv at .venv/ (gitignored)
pip install -e ".[dev]"            # if reinstalling

# CEREBRAS_API_KEY is in ~/.zshenv — no manual setup needed
```

## Commands

```bash
patchloop run mini_019 --model accounts/fireworks/models/gpt-oss-120b --baseline loop_reflect --tool-rounds 8
# mini_019 anchor confirmation (10 reps):
patchloop bench -t mini_019 -b loop -b loop_testnames -b loop_reflect \
  --model accounts/fireworks/models/gpt-oss-120b --tool-rounds 8 --num-runs 10 --run-delay 45 --call-delay 5
pytest eval/tasks/repos/mini_016/ -q --tb=short   # verify task fails on buggy code
ruff check patchloop/ tests/ eval/analysis/
```

---

## Locked Architecture Decisions

1. LocalEnvironment first; DockerEnvironment is Phase 2 stub.
2. Four baselines share the same code path (see baselines.py).
3. Reflection injection = ALL prior reflections from the current run (no filtering).
4. Phases: PLAN → APPLY_PATCH → RUN_TESTS → ANALYZE_FAILURE → REFLECT → DECIDE_NEXT → TERMINATE
5. Git commit after every APPLY_PATCH (success or failure). Format: `[{run_id}] iter_{n}: apply patch`
6. Anti-repeat: MD5(last 500 chars stderr + last 200 chars stdout); STUCK after 3 consecutive identical.
7. No Claude authorship in git commits.

---

## Key Implementation Details

- **chat_with_tools exhaustion fallback** (client.py:286): after all tool rounds consumed with `finish_reason=tool_calls`, makes one final text-only call (tools=None) to force the model to commit a diff. Without this, NO_DIFF on every round-exhausted run.
- **_apply_unified_diff** (git_ops.py): pure Python, line-by-line comparison. Does NOT use `git apply`. Has a fallback: match removed lines only when full context match fails.
- **Reflection injection** (planner.py `build_user_message`): only when `baseline == "loop_reflect"` AND reflections non-empty. Injects all lessons + `FAILED test_xxx` lines from last stdout.
- **loc_changed**: uses `git diff <snapshot_sha>` not uncommitted edits (always empty after commit).
- **Cerebras token quota**: free tier has DAILY TOKEN BUDGET (not just RPD). 3× bench at tool_rounds≥10 exhausts it. Never make test calls before a benchmark. Use `--call-delay 7`.
- **patch_assessment** (state.py, reflector.py, planner.py): Reflector classifies each patch as `likely_wrong | likely_partial_success | unclear`. If `likely_partial_success`, planner prepends "do NOT revert — look for second bug" instead of standard lesson. Test delta (prev/curr pass counts) is injected into reflector prompt to enable this classification.
- **# BUG: comments removed**: All mini_016–021 buggy files had inline `# BUG: ...` comments that leaked bug location/type. Removed in Session 26 — do not re-add these to reflection-critical tasks.

---

## Reflection-Critical Task Design Rules

Tasks must satisfy ALL of:
1. Bug B file has a **generic name** that doesn't semantically reveal the bug type
2. **Generic test names** (test_regression_N) — model can't grep for file location
3. **Cascade**: fixing Bug A makes most tests pass, Bug B only manifests after
4. **tool_rounds=6**: tight enough to prevent finding both bugs in iter 1
5. Issue description is **vague** — no file names, no explicit bug type
6. 11-file pipeline repo

Confirmed working: `record_ops.py` (sounds like data ops, not formatting), `entry_log.py` (sounds like audit log, not numeric coercion), `batch_ops.py` (sounds like batch processing, not fee arithmetic).

Bug B type diversity (important for generalization claim):
- mini_016: string format precision (`.2f`)
- mini_017/018/019/020: `int()` truncation
- **mini_021: wrong arithmetic sign (`-` instead of `+`)** ← first non-truncation Bug B type

---

## Task Table

### Standard slice (mini_001–010) — informative test names
| ID | Bug | Notes |
|---|---|---|
| mini_001 | retry() catches PermanentError | medium |
| mini_002 | paginate() off-by-one | easy |
| mini_003 | median() wrong for even-length | easy |
| mini_004 | jsonl reader + writer cascade | hard |
| mini_005 | merge_config() shallow merge | hard |
| mini_006 | anchor normalization, 3 files | hard |
| mini_007 | safe_join() bans all nested paths | medium |
| mini_008 | group_rows() uses groupby | medium |
| mini_009 | retry_after int-only | medium |
| mini_010 | parse_line() naive split | medium |

### Reflection-critical slice (mini_011–017) — generic test names
| ID | Bug | Status |
|---|---|---|
| mini_011 | merge+serialize both drop falsy | too easy for gpt-oss-120b |
| mini_012 | cache key missing locale+mode | good calibration |
| mini_013 | validator+serializer falsy cascade | too easy (single_shot solves) |
| mini_014 | aggregator wrong group key | too easy (0 tool calls) |
| mini_015 | enricher+reducer 0-value cascade | PATHOLOGICAL — reflector gives anti-helpful lessons |
| mini_016 | summarizer avg + record_ops.py precision | Triage: loop=3/3 at tool_rounds=12 — too easy. Defer. |
| mini_017 | aggregator denominator + entry_log.py truncation | Triage: loop=0/3 at tool_rounds=12 — Bug A too hard. Drop or redesign. |
| mini_018 | rate_calc wrong divisor + job_ops.py truncation | Signal pass: all baselines 1/3 — pure noise. Drop. |
| mini_019 | shrink_calc wrong divisor + event_log.py truncation | **ANCHOR TASK.** loop_reflect=2/3 consistent across 2 sweeps. Confirm with 10 reps. |
| mini_020 | score_calc wrong divisor + score_entry.py truncation | Triage: loop=0/3 at tool_rounds=12 — Bug A too hard. Drop or redesign. |
| mini_021 | cost_calc wrong field (weight vs qty) + batch_ops.py **wrong sign** (- instead of +) | Signal pass: loop_testnames=3/3 > loop_reflect=1/3 — not reflection-critical. Drop. |
| mini_022 | rate_calc inverted division + record_ops.py expand_refund_rows copies full refund per item | **NEW** multi-hop Bug B: symptom in summary_builder → pipeline → record_ops (3-hop chain). Cascade verified. |
| mini_023 | score_calc inverted division + record_ops.py attach_risk_flags misses "review" decisions | **NEW** multi-hop Bug B: symptom in score_summary → record_ops (2-hop chain). Cascade verified. Signal pass: noisy (1/6 all baselines) — Bug B too shallow (boolean classification). |
| mini_024 | rate_calc inverted division + record_ops.py expand_dispute_rows copies full disputed_value per item | **NEW** mini_022-style replication (chargeback domain). 3-hop chain: summary_builder → pipeline → record_ops. Cascade verified. Run needed. |

---

## LLM Providers

| Provider | Key var | Model | TPD (free) | Notes |
|---|---|---|---|---|
| **Fireworks (primary)** | `LLM_API_KEY` (in ~/.zshenv) + `LLM_BASE_URL=https://api.fireworks.ai/inference/v1` | `accounts/fireworks/models/gpt-oss-120b` | $6 free credits | Paid but cheap. Confirmed working with tool use. Use tool_rounds=10 to avoid exhaustion fallback. |
| Cerebras (secondary) | `CEREBRAS_API_KEY` (in ~/.zshenv) | `qwen-3-235b-a22b-instruct-2507` | ~1M | Congestion issues during US hours. gpt-oss-120b removed 2026-03-15. |
| Groq | `LLM_API_KEY` + `LLM_BASE_URL=https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | 100K | llama tool use broken (outputs raw text). gpt-oss-120b only 200K TPD. Not viable for full sweep. |
| SambaNova | `LLM_API_KEY` + `LLM_BASE_URL=https://api.sambanova.ai/v1` | `Meta-Llama-3.3-70B-Instruct` | 200K | 20 RPD / 200K TPD. Second-model validation only. |

**⚠ Model cohort break**: prior mini_016/017 "confirmed" data used `gpt-oss-120b` via Cerebras AND had # BUG: comments — both are confounds. All valid cleaned data uses Fireworks gpt-oss-120b without BUG comments. Do not pool old and new.

**Token reduction (implemented in planner.py):**
- `read_file` truncated at 200 lines — minimal impact on small task repos, good hygiene
- `search_code` capped at 10 results — reduces tool result size
- Reflector already caps diff at 2000 chars, stdout/stderr at 1500 chars each

**No free provider solves the quota problem.** The real lever is token reduction per run or splitting sweeps across days.
