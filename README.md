# PatchLoop

**A benchmarkable self-improving coding agent.**

PatchLoop gives an LLM a buggy Python repository and an issue description. The agent explores the code using tools, proposes a fix, applies it, runs the tests, and — if it fails — writes a structured lesson about what went wrong. That lesson feeds back into the next attempt.

The central question this project is trying to answer:

> **Under what conditions does structured reflection become the load-bearing signal for an autonomous coding agent?**

---

## How It Works

```
Issue description + buggy repo
        │
        ▼
   ┌─────────┐
   │  PLAN   │  ← Agent reads files, searches code, proposes a unified diff
   └────┬────┘
        │
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
│ ANALYZE + REFLECT│  ← Agent writes a structured lesson from the failure
└────────┬─────────┘
         │
         ▼
    ┌──────────┐
    │  REPEAT  │  ← Lesson injected into next PLAN prompt
    └──────────┘
```

Every patch attempt is committed to git regardless of outcome. Every run is logged in structured JSONL for analysis.

---

## The Research Design

Four baselines run through the same code path. The only difference is what gets injected into each planning prompt:

| Baseline | Loops | Structured lessons | Failing test names |
|---|:---:|:---:|:---:|
| `single_shot` | ✗ | ✗ | ✗ |
| `loop` | ✓ | ✗ | ✗ |
| `loop_testnames` | ✓ | ✗ | ✓ |
| `loop_reflect` | ✓ | ✓ | ✓ |

`loop_testnames` is an ablation baseline — it injects the names of still-failing tests but no structured lessons. This isolates whether test-name grounding alone accounts for any improvement, or whether the conceptual lesson is doing real work.

---

## Benchmark Tasks

15 hand-crafted Python mini-repos, each with a deliberately planted bug and a pytest suite that fails on the buggy code and passes on the correct fix. All stdlib-only — no pip dependencies beyond pytest.

**Standard slice (mini_001–010)** — informative test names, single and multi-file bugs

**Reflection-critical slice (mini_011–015)** — generic test names (`test_regression_N`), cascade bugs across multiple files, vague issue descriptions, wrong-file traps

The reflection-critical slice is designed so that test-name grounding alone is insufficient. The agent must encode and apply a conceptual lesson to make progress — it cannot just grep for the failing test name and open the obvious file.

Example cascade bug (mini_015):
- **Bug A** (`enricher.py`): `e.priority = e.priority or default` — replaces `0` with a default value because `0` is falsy
- **Bug B** (`reducer.py`): `if e.priority:` — silently skips all zero-priority events
- Fixing Bug A makes some tests pass, but Bug B still silently drops data. The agent must iterate to find and fix both.

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

### API Key

PatchLoop uses the OpenAI-compatible API format. **Cerebras is the recommended provider** — it has a generous free tier (14,400 requests/day) and runs fast.

```bash
# Recommended: Cerebras (free — https://cloud.cerebras.ai)
export CEREBRAS_API_KEY=your_key_here
# base URL is auto-configured; use --model gpt-oss-120b
```

Other supported providers:

```bash
# Google Gemini (free — https://aistudio.google.com)
export GEMINI_API_KEY=your_key_here
# default model: gemini-2.5-flash

# Groq or any OpenAI-compatible endpoint
export LLM_API_KEY=your_key_here
export LLM_BASE_URL=https://api.groq.com/openai/v1
```

---

## Usage

### Run a single task

```bash
# Run one task with one baseline
patchloop run mini_001 --model gpt-oss-120b

# Specify baseline
patchloop run mini_004 --baseline loop --model gpt-oss-120b

# Constrain the search budget (tool calls per planning step)
patchloop run mini_006 --baseline loop_reflect --model gpt-oss-120b --tool-rounds 8
```

### Run the full benchmark

```bash
# All tasks × all baselines
patchloop bench --model gpt-oss-120b

# Specific tasks and baselines
patchloop bench \
  -t mini_004 -t mini_005 -t mini_006 \
  -b loop -b loop_reflect \
  --model gpt-oss-120b

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

### Flags

| Flag | Default | Description |
|---|---|---|
| `--model` | `gemini-2.5-flash` | LLM model |
| `--tool-rounds` | `15` | Max tool calls per planning step |
| `--num-runs` | `1` | Repetitions per task/baseline (for averaging) |
| `--run-delay` | `30` | Seconds between repetitions |
| `--call-delay` | `0` | Seconds between individual API calls (rate pacing) |

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

## Key Design Details

**Pure Python diff application** — PatchLoop does not use `git apply`. It implements its own unified diff applier that searches for context blocks line-by-line rather than trusting the `@@` line numbers in the patch. This makes it robust to LLM-generated patches with slightly wrong offsets.

**Anti-repeat detection** — If the agent produces the same failure three times in a row (detected by MD5 hash of test output), the run terminates with `STUCK` instead of looping indefinitely.

**Full git history** — Every patch attempt is committed to git regardless of outcome. The entire iteration history is preserved for replay and analysis.

**Structured reflection** — Reflections are JSON objects with fields: `what_failed`, `root_cause_hypothesis`, `patch_summary`, `lesson`. Only the `lesson` field is injected into subsequent prompts, keeping the signal tight.

---

## The Hypothesis

> Reflection becomes load-bearing when search is scarce and the next action is ambiguous.

Not universally. Not just because a repo is large. The key design constraint for reflection-critical tasks is **selective search pressure without leaking the invariant** — the issue description, test names, and code must not point too directly at the bug. The agent must choose which files to explore, and when it chooses wrong, the structured lesson needs to encode something the test name alone does not.

---

## Status

Active research project. Infrastructure and benchmark suite are complete. Averaged multi-run results across the reflection-critical task slice are in progress.
