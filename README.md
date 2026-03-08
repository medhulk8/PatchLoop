# PatchLoop

**A benchmarkable self-improving coding agent.**

PatchLoop gives an LLM a buggy Python repository and an issue description. The agent explores the code using tools, proposes a unified diff fix, applies it, runs the tests, and — if it still fails — writes a structured lesson about what went wrong. That lesson feeds into the next attempt.

The central question:

> **Under what conditions does structured reflection become the load-bearing signal for an autonomous coding agent?**

---

## What Was Found

Reflection does not universally improve autonomous coding agents. Whether it helps depends on the *task regime*:

### Standard tasks (informative test names)

On tasks where failing test names point toward the broken file, **test-name grounding alone accounts for most of the improvement**. Structured lessons add little.

3× averaged benchmark on mini_004/005/006 (tool_rounds=8, gpt-oss-120b):

| Baseline | Resolve rate | Repeat failure rate |
|---|---|---|
| `loop` | 55.6% | 23.1% |
| `loop_testnames` | **66.7%** | **7.7%** |
| `loop_reflect` | 55.6% | 20.0% |

`loop_testnames` wins. Injecting the names of still-failing tests (e.g., `test_writer_terminates_each_record_with_newline`) is more actionable than an abstract conceptual lesson. The model can open the right file directly.

### Reflection-critical tasks (generic test names + tight budget + cascade bugs)

When test names are generic (`test_regression_01`…`test_regression_05`), the second bug is in a file with a non-revealing name, and the tool budget prevents reading everything in one pass — **structured reflection becomes the load-bearing signal**.

**mini_016** (weighted_bucket_report, 11 files) — 3× replication, tool_rounds=6:

| Baseline | Resolve rate | Avg iters (success) | Repeat failure rate |
|---|---|---|---|
| `loop` | 33.3% | 5.00 | 33.3% |
| `loop_testnames` | 33.3% | 1.00 | 22.2% |
| `loop_reflect` | **66.7%** | **2.50** | **0.0%** |

**mini_017** (log_aggregator, 11 files) — 3× replication, tool_rounds=6 (reps 1+2 clean; rep 3 throttled by daily token quota):

| Baseline | Resolve rate | Repeat failure rate |
|---|---|---|
| `loop` | 0.0% (0/3) | 33.3% |
| `loop_testnames` | 0.0% (0/3) | 25.0% |
| `loop_reflect` | **33.3% (1/3)** | **22.2%** |

Clean data (reps 1+2 only): loop=0%, loop_testnames=0%, loop_reflect=50% (1/2). Rep 3 quota-throttled — loop_testnames and loop_reflect terminated in 1 iter each (invalid). Loop rep 3 clean: FAILED in 5 iters. Pattern matches mini_016: loop_reflect is the only baseline that resolves the cascade.

### Why reflection matters in this regime

Both tasks follow the same cascade structure:
- **Bug A** is findable from the issue description. Fixing it makes 4/5 tests pass.
- **Bug B** is in a generically-named file (`record_ops.py`, `entry_log.py`) that doesn't reveal its role. With only 6 tool rounds, the model cannot read every file — it must choose.
- After fixing Bug A, `loop` and `loop_testnames` have no signal about where to look next. They cycle back to the file they already fixed.
- `loop_reflect` encodes a lesson like *"the output value is being truncated — look at where the statistics are persisted"* and uses it to redirect exploration to the right file.

The structured lesson carries information that neither the test name nor the issue description contains.

---

## How It Works

```
Issue description + buggy repo
        │
        ▼
   ┌─────────┐
   │  PLAN   │  ← Agent reads files, searches code, proposes a unified diff
   └────┬────┘
        │ (diff found)
        ▼
┌──────────────┐
│ APPLY PATCH  │  ← Diff applied to files, committed to git
└──────┬───────┘
       │
       ▼
┌───────────┐
│ RUN TESTS │  ← pytest runs; if green → RESOLVED ✓
└─────┬─────┘
      │ (still failing)
      ▼
┌──────────────────┐
│ ANALYZE + REFLECT│  ← Structured JSON lesson written from the failure
└────────┬─────────┘
         │
         ▼
    ┌──────────┐
    │  REPEAT  │  ← Lesson injected into next PLAN prompt
    └──────────┘
```

Every patch attempt is committed to git regardless of outcome. Every run is logged in structured JSONL for analysis.

---

## The Four Baselines

All four run through the same code path. The only difference is what gets injected into the planning prompt:

| Baseline | Loops | Structured lessons | Failing test names |
|---|:---:|:---:|:---:|
| `single_shot` | ✗ | ✗ | ✗ |
| `loop` | ✓ | ✗ | ✗ |
| `loop_testnames` | ✓ | ✗ | ✓ |
| `loop_reflect` | ✓ | ✓ | ✓ |

`loop_testnames` is an ablation baseline that isolates whether test-name grounding alone accounts for improvement over bare looping, or whether the conceptual lesson is doing real work.

---

## The Task Design Constraint

The critical insight from building these tasks: **file naming is a confound**.

A first version of mini_016 used a file named `value_formatter.py`. The model would list the repo files, see the name, immediately open it, and fix both bugs in a single pass — bypassing the cascade entirely and making all baselines equivalent. Renaming it to `record_ops.py` (with generic functions and a docstring framed as "data normalisation") restored the intended search pressure.

This generalizes: for a task to be reflection-critical, the second bug file must not semantically reveal the bug type from its name alone. The model's file selection must be genuinely ambiguous after the first fix, so the structured lesson can redirect it.

---

## Benchmark Tasks

17 hand-crafted Python mini-repos, all stdlib-only (no pip deps beyond pytest).

### Standard slice (mini_001–010) — informative test names

| ID | Bug | Domain |
|---|---|---|
| mini_001 | `retry()` catches `PermanentError` (should not retry) | Error handling |
| mini_002 | `paginate()` off-by-one in slice end | Pagination |
| mini_003 | `median()` wrong for even-length inputs | Statistics |
| mini_004 | JSONL reader drops last record + writer missing `\n` | File I/O |
| mini_005 | `merge_config()` shallow merge loses sibling keys | Config merging |
| mini_006 | Anchor normalization bug duplicated across 3 files | Text processing |
| mini_007 | `safe_join()` bans all nested paths | Path handling |
| mini_008 | `group_rows()` uses groupby on non-contiguous data | Data grouping |
| mini_009 | `retry_after` parser: int-only, crashes on HTTP-date | HTTP parsing |
| mini_010 | CSV parser splits on commas inside quoted fields | CSV parsing |

### Reflection-critical slice — generic test names, cascade bugs, tight budget

| ID | Bug A | Bug B | Design |
|---|---|---|---|
| mini_011 | `merge.py`: `or` drops falsy values | `serialize.py`: `if v` drops falsy | Two-file shared bug pattern |
| mini_012 | `cache.py`: key ignores locale+mode | n/a | Issue implicates `render.py` (wrong-file trap) |
| mini_013 | `validator.py`: drops falsy fields | `serializer.py`: or-merge overwrites record with defaults | Wrong-file trap: issue implicates `pipeline.py` |
| mini_014 | `aggregator.py`: groups by ID instead of category | n/a | Calibration task (too easy for this model) |
| mini_015 | `enricher.py`: `or`-defaults 0-valued fields | `reducer.py`: `if e.priority` skips 0s | Pathological cascade: wrong fix order makes reflection anti-helpful |
| mini_016 | `summarizer.py`: plain avg instead of weighted | `record_ops.py`: `:.2f` truncates precision | **Confirmed reflection-critical** (3× replicated) |
| mini_017 | `aggregator.py`: divides by entry count not requests | `entry_log.py`: `int()` truncates float error counts | **Confirmed reflection-critical** (validated) |

---

## Setup

Requires Python 3.11+.

```bash
git clone https://github.com/medhulk8/PatchLoop.git
cd PatchLoop

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

### API Keys

**Cerebras is the recommended provider** — generous free tier (14,400 requests/day), fast inference.

```bash
# Cerebras (free — https://cloud.cerebras.ai)
export CEREBRAS_API_KEY=your_key_here
# base URL is auto-configured; use --model gpt-oss-120b
```

Other supported providers:

```bash
# Google Gemini (free — https://aistudio.google.com)
export GEMINI_API_KEY=your_key_here

# Groq or any OpenAI-compatible endpoint
export LLM_API_KEY=your_key_here
export LLM_BASE_URL=https://api.groq.com/openai/v1
```

---

## Usage

### Run a single task

```bash
patchloop run mini_016 --model gpt-oss-120b --tool-rounds 6
patchloop run mini_016 --baseline loop_reflect --model gpt-oss-120b --tool-rounds 6
```

### Run the benchmark

```bash
# Reflection-critical slice, 3 reps each (recommended)
patchloop bench \
  -t mini_016 -t mini_017 \
  -b loop -b loop_testnames -b loop_reflect \
  --model gpt-oss-120b \
  --tool-rounds 6 \
  --num-runs 3 \
  --run-delay 30 \
  --call-delay 7

# All tasks × all baselines
patchloop bench --model gpt-oss-120b
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--model` | `gemini-2.5-flash` | LLM model |
| `--tool-rounds` | `15` | Max tool calls per planning step |
| `--num-runs` | `1` | Repetitions per task/baseline |
| `--run-delay` | `30` | Seconds between repetitions |
| `--call-delay` | `0` | Seconds between individual API calls |

---

## Project Structure

```
patchloop/
├── patchloop/
│   ├── agent/
│   │   ├── loop.py          # State machine orchestrating all phases
│   │   ├── planner.py       # PLAN: tool-use loop, prompt assembly, diff extraction
│   │   ├── patcher.py       # APPLY: diff validation, application, git commit
│   │   ├── reflector.py     # REFLECT: structured JSON lesson from test failure
│   │   └── state.py         # LoopState, IterationRecord, Reflection, anti-repeat logic
│   ├── environment/
│   │   ├── local_env.py     # Sandboxed temp dir + subprocess test runner
│   │   ├── git_ops.py       # Pure Python unified diff applier + git wrapper
│   │   └── task.py          # Task and TaskResult models (loaded from YAML)
│   ├── llm/
│   │   └── client.py        # Provider-agnostic client (Cerebras / Gemini / Groq)
│   ├── eval/
│   │   ├── bench_runner.py  # Benchmark orchestration: tasks × baselines × repetitions
│   │   ├── baselines.py     # build_agent() factory
│   │   └── metrics.py       # Resolve rate, repeat failure rate, iteration stats
│   └── cli.py               # patchloop run / patchloop bench
└── eval/
    └── tasks/
        ├── mini_001.yaml    # Task: issue text, repo path, test command, limits
        └── repos/
            └── mini_001/    # Buggy Python repo + pytest suite
```

---

## Key Implementation Details

**Pure Python diff application** — PatchLoop does not use `git apply`. It implements its own unified diff applier that searches for context blocks line-by-line rather than trusting the `@@` line numbers in the patch. This makes it robust to LLM-generated patches with slightly wrong offsets.

**Anti-repeat detection** — If the agent produces the same failure three times in a row (detected by MD5 hash of test output), the run terminates with `STUCK` instead of looping indefinitely.

**Full git history** — Every patch attempt is committed to git regardless of outcome. The entire iteration history is preserved for replay and analysis.

**Structured reflection** — Reflections are JSON objects with fields: `what_failed`, `root_cause_hypothesis`, `patch_summary`, `lesson`. Only the `lesson` field is injected into subsequent prompts, keeping the signal tight.

**Tool round budget** — `--tool-rounds` controls how many tool calls (file reads, searches) the agent can make per planning step. Lowering this creates search pressure: the agent cannot read every file in one pass and must choose. At `tool_rounds=6` on 11-file repos, the model reads 3–4 files per iteration — enough to fix Bug A but not enough to independently discover Bug B.

---

## The Hypothesis

> Reflection becomes load-bearing when search is scarce and the next action is ambiguous.

Not universally. Not just because a repo is large. The condition is **selective search pressure without leaking the invariant**: the issue description, test names, and file names must not point directly at the second bug. The agent must choose which files to explore, and when it chooses wrong, the structured lesson encodes something that neither the test name nor the issue description contains.

On standard tasks — where `FAILED test_writer_terminates_each_record_with_newline` points straight to the writer — test-name grounding is sufficient and reflection adds nothing. On reflection-critical tasks — where `FAILED test_regression_04` tells you nothing about which of 11 files to open next — the structured lesson is the only signal that breaks the cycle.
