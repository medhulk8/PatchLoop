# CLAUDE.md — PatchLoop

Working reference for Claude Code. Keep this short. Session history → SESSIONS.md.

---

## What This Project Is

`patchloop` is a benchmarkable self-improving coding agent.
Given a buggy Python repo and an issue description, it autonomously explores, patches, tests, reflects, and retries.
Goal: demonstrate measurable improvement from reflection via a formal benchmark (4 baselines).

---

## Current Status

**21 tasks built. Confirmed reflection-critical: mini_016, mini_017 (3× each); mini_020 (2/2 valid). mini_021 built (different Bug B type: wrong sign). mini_019 Bug B file renamed (stock_log→event_log). mini_018 rerun needed.**

Baselines: `single_shot` | `loop` | `loop_testnames` | `loop_reflect`

Budget sweep results (mini_016 + mini_017, 3 baselines, 3 reps):

| tool_rounds | loop | loop_testnames | loop_reflect |
|---|---|---|---|
| 4 | 0% | 0% | 0% |
| 6 | 33.3% | 33.3% | **66.7%** |
| 8 | 50.0% | 33.3% | **66.7%** |
| 10 | dropped — free-tier daily token budget insufficient for 3× |

Benchmark bw2c2gz90 (mini_018/019/020, valid runs only, rep3 loop_testnames/loop_reflect lost to quota):

| task | loop | loop_testnames | loop_reflect | notes |
|---|---|---|---|---|
| mini_018 | 0/3 | 0/2 | 0/0 (all ERROR) | No valid loop_reflect data. Rerun needed. |
| mini_019 | **2/3** | 1/1 | 1/1 | NOT reflection-critical! loop=67% already. Bug B file renamed. |
| mini_020 | 0/3 | 0/2 | **2/2** | CONFIRMED reflection-critical. |

**Key finding:** mini_019 solved by loop=2/3 because `stock_log.py` was too obviously named in a stock pipeline — model found it in 6 rounds. Renamed to `event_log.py`. Rerun needed.

Pooled confirmed tasks (016/017/020 only): loop_reflect=6/7=86%, loop=1/9=11%, loop_testnames=1/7=14%.
(Prior pooled 016+017+019+020 stats are invalidated by mini_019 not being reflection-critical.)

---

## Path Forward (priority order)

1. **Fresh quota day: rerun mini_018 + mini_019 (fixed) + mini_020 (rep3) full 3×**
   ```
   patchloop bench -t mini_018 -t mini_019 -t mini_020 -b loop -b loop_testnames -b loop_reflect \
     --model gpt-oss-120b --tool-rounds 6 --num-runs 3 --run-delay 45 --call-delay 10
   ```
   Goal: confirm or deny each as reflection-critical. Target: 5 confirmed tasks.

2. **Fresh quota day: run mini_021 (new task, different Bug B type)**
   ```
   patchloop bench -t mini_021 -b loop -b loop_testnames -b loop_reflect \
     --model gpt-oss-120b --tool-rounds 6 --num-runs 3 --run-delay 45 --call-delay 10
   ```
   Goal: add task diversity (wrong-sign Bug B vs int() truncation in 016-020).

3. **Statistical update**: once 5+ confirmed tasks, repool and run:
   ```
   python eval/analysis/stats.py --tasks 016 017 018 019 020 021
   ```
   Report per-task outcomes as primary. Note pooled Fisher is optimistic (within-task clustering).

4. **Second model validation**: Run on Groq (llama-3.3-70b-versatile, 200K TPD) — one sweep/day.

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
patchloop run mini_016 --model gpt-oss-120b --baseline loop_reflect --tool-rounds 6
patchloop bench -t mini_016 -t mini_017 -b loop -b loop_testnames -b loop_reflect \
  --model gpt-oss-120b --tool-rounds 6 --num-runs 3 --run-delay 30 --call-delay 7
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
| mini_016 | summarizer avg + record_ops.py precision | **CONFIRMED** loop_reflect=66.7% (3×) |
| mini_017 | aggregator denominator + entry_log.py truncation | **CONFIRMED** loop_reflect=66.7% (3×) |
| mini_018 | rate_calc wrong divisor + job_ops.py truncation | Bug B redesigned; rerun needed (rep3 lost to quota) |
| mini_019 | shrink_calc wrong divisor + event_log.py truncation | Renamed Bug B file: stock_log→event_log (was too discoverable). Rerun needed. |
| mini_020 | score_calc wrong divisor + score_entry.py truncation | loop_reflect=1/2 (partial, rep3 needed) |
| mini_021 | cost_calc wrong field (weight vs qty) + batch_ops.py **wrong sign** (- instead of +) | Built, cascade verified. **Different Bug B type** — first non-truncation Bug B. Run needed. |

---

## LLM Providers

| Provider | Key var | Model | TPD (free) | Notes |
|---|---|---|---|---|
| **Cerebras (primary)** | `CEREBRAS_API_KEY` (in ~/.zshenv) | `gpt-oss-120b` | ~1M | Best free option. 14,400 RPD. Daily token budget (~1M/day estimated from use). |
| Groq | `LLM_API_KEY` + `LLM_BASE_URL=https://api.groq.com/openai/v1` | `gpt-oss-120b` or `llama-3.3-70b-versatile` | 200K / 100K | Free tier TPD confirmed lower than Cerebras. Use for second-model validation only. |
| SambaNova | `LLM_API_KEY` + `LLM_BASE_URL=https://api.sambanova.ai/v1` | `Meta-Llama-3.3-70B-Instruct` | 200K | 20 RPD / 200K TPD. Not better than Cerebras. Second-model validation only. |
| Gemini | `GEMINI_API_KEY` | `gemini-2.5-flash` | — | ~50 RPD (too low for bench) |

**Token reduction (implemented in planner.py):**
- `read_file` truncated at 200 lines — minimal impact on small task repos, good hygiene
- `search_code` capped at 10 results — reduces tool result size
- Reflector already caps diff at 2000 chars, stdout/stderr at 1500 chars each

**No free provider solves the quota problem.** The real lever is token reduction per run or splitting sweeps across days.
