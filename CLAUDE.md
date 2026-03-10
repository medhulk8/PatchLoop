# CLAUDE.md — PatchLoop

Working reference for Claude Code. Keep this short. Session history → SESSIONS.md.

---

## What This Project Is

`patchloop` is a benchmarkable self-improving coding agent.
Given a buggy Python repo and an issue description, it autonomously explores, patches, tests, reflects, and retries.
Goal: demonstrate measurable improvement from reflection via a formal benchmark (4 baselines).

---

## Current Status

**17 tasks built. Budget sweep COMPLETE (tool_rounds 4/6/8, 3× replicated). loop_reflect holds 66.7% at all feasible budgets. Next: build mini_018+ tasks (no API needed), then statistical analysis.**

Baselines: `single_shot` | `loop` | `loop_testnames` | `loop_reflect`
Reflection-critical tasks confirmed: `mini_016`, `mini_017` (both 3× replicated, loop_reflect=66.7%, all others ≤33.3%)

Budget sweep results (mini_016 + mini_017, 3 baselines, 3 reps):

| tool_rounds | loop | loop_testnames | loop_reflect |
|---|---|---|---|
| 4 | 0% | 0% | 0% |
| 6 | 33.3% | 33.3% | **66.7%** |
| 8 | 50.0% | 33.3% | **66.7%** |
| 10 | dropped — free-tier daily token budget insufficient for 3× |

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
ruff check patchloop/
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

Confirmed working: `record_ops.py` (sounds like data ops, not formatting), `entry_log.py` (sounds like audit log, not numeric coercion).

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

---

## LLM Providers

| Provider | Key var | Model | Notes |
|---|---|---|---|
| Cerebras (recommended) | `CEREBRAS_API_KEY` (in ~/.zshenv) | `gpt-oss-120b` | 14,400 RPD + daily token budget |
| Groq | `LLM_API_KEY` + `LLM_BASE_URL=https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | 14,400 RPD |
| Gemini | `GEMINI_API_KEY` | `gemini-2.5-flash` | ~50 RPD (too low for bench) |
