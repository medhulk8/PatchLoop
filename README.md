# PatchLoop

A benchmarkable self-improving coding agent.

PatchLoop takes a buggy Python repository and an issue description, then autonomously explores the code, proposes a fix, applies it, runs the tests, and learns from failures — repeating until the bug is resolved or it runs out of attempts.

The core research question:

> **Under what conditions does structured reflection become the load-bearing signal for an autonomous coding agent?**

---

## What It Does

Given a buggy repo and an issue description, PatchLoop runs an agentic loop:

1. **Explore** — the agent reads files, lists the codebase, and searches for relevant code using LLM tool calls
2. **Plan** — the agent proposes a fix as a unified diff
3. **Apply** — the diff is applied to the repo and committed to git
4. **Test** — pytest runs; if tests pass, the task is resolved
5. **Reflect** — if tests fail, the agent writes a structured lesson about what went wrong and why
6. **Repeat** — lessons from past failures are injected into the next attempt

Every patch attempt is preserved in git history. Every run is logged in structured JSONL for analysis.

---

## The Research Design

PatchLoop compares four baselines to isolate what actually helps:

| Baseline | Iterations | Reflection lessons | Failing test names |
|---|---|---|---|
| `single_shot` | 1 | ✗ | ✗ |
| `loop` | N | ✗ | ✗ |
| `loop_testnames` | N | ✗ | ✓ |
| `loop_reflect` | N | ✓ | ✓ |

`loop_testnames` is an ablation baseline: it injects the names of still-failing tests into each attempt without structured lessons, isolating whether test-name grounding alone accounts for any improvement.

The benchmark measures resolve rate, average iterations to success, and repeated failure rate across a suite of 15 hand-crafted tasks at varying difficulty levels.

---

## Benchmark Tasks

Tasks are small, self-contained Python repos with a deliberately planted bug and a pytest test suite. The tests fail on the buggy code and pass on the correct fix.

Tasks are divided into two slices:

**Standard slice (mini_001–010)** — informative test names, single or multi-file bugs
**Reflection-critical slice (mini_011–015)** — generic test names (`test_regression_N`), cascade bugs across multiple files, vague issue descriptions, and wrong-file traps

The reflection-critical slice is designed so that test-name grounding alone is insufficient — the agent needs to encode and apply a conceptual lesson to make progress.

All task repos are stdlib-only (no pip dependencies beyond pytest).

---

## Setup

Requires Python 3.11+. Tested on Python 3.13.

```bash
git clone https://github.com/medhulk8/PatchLoop.git
cd PatchLoop

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

### API Key

PatchLoop uses an OpenAI-compatible API format and works with any provider that supports it. The default is Google Gemini (free tier).

```bash
# Option 1: Google Gemini (free — https://aistudio.google.com)
export GEMINI_API_KEY=your_key_here

# Option 2: Cerebras (free, higher quota — https://cloud.cerebras.ai)
export CEREBRAS_API_KEY=your_key_here
# base URL auto-configured; use --model gpt-oss-120b

# Option 3: Groq or any OpenAI-compatible provider
export LLM_API_KEY=your_key_here
export LLM_BASE_URL=https://api.groq.com/openai/v1
```

---

## Usage

### Run a single task

```bash
# Default: loop_reflect baseline, gemini-2.5-flash
patchloop run mini_001

# Specify baseline and model
patchloop run mini_004 --baseline loop --model gpt-oss-120b

# Constrain the search budget (tool rounds per planning step)
patchloop run mini_006 --baseline loop_reflect --tool-rounds 8
```

### Run the benchmark

```bash
# All tasks × all baselines
patchloop bench --model gpt-oss-120b

# Specific tasks and baselines
patchloop bench -t mini_004 -t mini_005 -t mini_006 -b loop -b loop_reflect

# Averaged over multiple repetitions (recommended for credible results)
patchloop bench \
  -t mini_004 -t mini_005 -t mini_006 \
  -b loop -b loop_reflect \
  --model gpt-oss-120b \
  --tool-rounds 8 \
  --num-runs 3 \
  --run-delay 30 \
  --call-delay 7
```

### Key flags

| Flag | Default | Description |
|---|---|---|
| `--model` | `gemini-2.5-flash` | LLM model to use |
| `--tool-rounds` | `15` | Max tool calls per planning step (search budget) |
| `--num-runs` | `1` | Repetitions per task/baseline pair (for averaging) |
| `--run-delay` | `30` | Seconds between repetitions (avoids quota bursts) |
| `--call-delay` | `0` | Seconds to sleep before each API call (rate pacing) |

---

## Project Structure

```
patchloop/
├── patchloop/
│   ├── agent/
│   │   ├── loop.py          # State machine: PLAN → APPLY → TEST → REFLECT → repeat
│   │   ├── planner.py       # PLAN phase: tool-use loop + diff extraction + prompt assembly
│   │   ├── patcher.py       # APPLY phase: diff validation + application + git commit
│   │   ├── reflector.py     # REFLECT phase: structured JSON lesson from test failure
│   │   └── state.py         # LoopState, IterationRecord, Reflection, anti-repeat detection
│   ├── environment/
│   │   ├── local_env.py     # Sandboxed temp dir + subprocess test runner
│   │   ├── git_ops.py       # Pure Python unified diff applier + git subprocess wrapper
│   │   └── task.py          # Task and TaskResult data models (loaded from YAML)
│   ├── llm/
│   │   └── client.py        # Provider-agnostic LLM client (Gemini / Cerebras / Groq)
│   ├── eval/
│   │   ├── bench_runner.py  # Benchmark orchestration: tasks × baselines × repetitions
│   │   ├── baselines.py     # build_agent() factory wiring all components together
│   │   └── metrics.py       # Resolve rate, repeat failure rate, iteration stats
│   └── cli.py               # patchloop run / patchloop bench CLI
└── eval/
    └── tasks/
        ├── mini_001.yaml    # Task definition: issue, repo path, test command, limits
        ├── ...
        └── repos/
            ├── mini_001/    # Buggy repo + pytest suite
            └── ...
```

---

## How the Patch Application Works

PatchLoop uses a pure Python unified diff applier instead of `git apply`. This makes it robust to LLM-generated patches that have slightly wrong line numbers — the applier searches for the context block anywhere in the file using exact line-by-line comparison, rather than trusting the `@@` header line numbers. Every applied patch is committed to git regardless of whether tests pass, so the full iteration history is preserved for analysis.

---

## Observability

Every run produces a structured JSONL log at `runs/{run_id}/{task_id}.jsonl`. Each line is one event: phase transition, plan text, proposed diff, patch outcome, test result, reflection, or run summary. All writes are flushed immediately so logs survive crashes.

Benchmark reports are written to `runs/report_{timestamp}.json` with full per-task, per-baseline breakdowns.

---

## Hypothesis

The working hypothesis being tested:

> Reflection becomes load-bearing when search is scarce and the next action is ambiguous — not universally, and not simply because a repo is large.

The key design constraint for reflection-critical tasks: **selective search pressure without leaking the invariant**. The issue description, test names, and code comments must not point too directly at the bug location. The agent must choose which files to explore, and when it chooses wrong, it needs the structured lesson from the failure to course-correct — not just the failing test name.

---

## Status

Active research project. Benchmark suite and infrastructure are complete. Averaged multi-run results across the reflection-critical task slice are in progress.
