# PatchLoop

**A benchmarkable self-improving coding agent.**

PatchLoop gives an LLM a buggy Python repository and an issue description. The agent explores the code using tools, proposes a unified diff fix, applies it, runs the tests, and — if it still fails — writes a structured lesson about what went wrong. That lesson feeds into the next attempt.

---

## Result

> Built a self-reflective bug-fixing agent and showed that structured reflection improved solve rate on hidden cascade bugs from **5.7% to 36.0%** over blind retry (Fisher's exact, p=0.0039).

**Benchmark** — mini_022 + mini_023 + mini_024, tool_rounds=8, `gpt-oss-120b` via Fireworks AI:

| Baseline | Solved | Rate | 95% CI |
|---|---|---|---|
| `loop` | 2/35 | 5.7% | [0.7%, 19.2%] |
| `loop_testnames` | 2/19 | 10.5% | [1.3%, 33.1%] |
| **`loop_reflect`** | **9/25** | **36.0%** | [18.0%, 57.5%] |

Fisher's exact (one-tailed):
- **loop_reflect vs loop: p = 0.0039** ← primary result
- loop_reflect vs loop_testnames: p = 0.054 ← suggestive, not definitive

**The claim is narrow and intentional.** This result holds specifically on cascade bugs with multi-hop hidden Bug B, generic test names, and a tight tool budget. On standard tasks with informative test names, test-name grounding alone accounts for most of the improvement and reflection adds little.

---

## What Makes a Task Reflection-Critical

Both confirmed tasks (mini_022, mini_024) follow the same structure:

- **Bug A** — inverted division in `rate_calc.py`. Findable in 1–2 reads from the issue description. Fixing it makes 4/5 tests pass.
- **Bug B** — `record_ops.expand_*_rows` copies the full amount per expanded row instead of dividing by item count. Requires tracing a 3-hop call chain: `summary_builder` → `pipeline` → `record_ops`. Not reachable from the issue description or test names.
- **Issue text** — says "aggregated totals look correct, error is in the final proportional step" — intentionally pulls the model toward `rate_calc.py` first.
- **Generic test names** — `test_regression_01` … `test_regression_05` — no file location signal.
- **Tool budget** — `tool_rounds=8` — enough to fix Bug A, not enough to read every file. The model must choose.

After fixing Bug A, `loop` and `loop_testnames` have no signal about where to look next. They cycle back to the file they already fixed. `loop_reflect` encodes a lesson like *"the rate calculation looks correct now — look at how totals are being accumulated upstream"* and uses it to redirect exploration to `record_ops.py`.

The structured lesson carries information that neither the test name nor the issue description contains.

---

## Negative Variants (Task Design Lessons)

Three tasks were built that did *not* produce clean reflection signal — each for an instructive reason:

| Task | Bug B type | What happened | Lesson |
|---|---|---|---|
| mini_023 | Boolean flag (`== "block"` vs `in {"block", "review"}`) | Visually obvious once file is opened. Baseline solves by lucky file choice. | Bug B must require semantic reasoning, not just visual inspection. |
| mini_025 | Arithmetic expansion | test_04 asserted on `total_defective == 8.0` (intermediate field) | loop_testnames inferred the expansion mechanic from the test body. test_04 must assert only on the final rate. |
| mini_026 | Arithmetic expansion | loop_reflect=1/5=20%. Weak replication, excluded from headline. | Pattern works but 5 reps is too small to confirm; kept as non-confirmed variant. |

These failures directly motivated the final task design rules and make the confirmed results more credible, not less.

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

All four share the same code path. The only difference is what gets injected into the planning prompt:

| Baseline | Loops | Structured lessons | Failing test names |
|---|:---:|:---:|:---:|
| `single_shot` | ✗ | ✗ | ✗ |
| `loop` | ✓ | ✗ | ✗ |
| `loop_testnames` | ✓ | ✗ | ✓ |
| `loop_reflect` | ✓ | ✓ | ✓ |

`loop_testnames` is the key ablation: it isolates whether structured lessons do real work beyond simply knowing which tests still fail.

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

Results were produced using **Fireworks AI** (`gpt-oss-120b`):

```bash
export LLM_API_KEY=your_fireworks_key
export LLM_BASE_URL=https://api.fireworks.ai/inference/v1
```

Any OpenAI-compatible provider works:

```bash
# Groq, SambaNova, etc.
export LLM_API_KEY=your_key
export LLM_BASE_URL=https://your-provider/v1
```

---

## Usage

### Run a single task

```bash
# Local execution (default)
patchloop run mini_022 --model accounts/fireworks/models/gpt-oss-120b --baseline loop_reflect --tool-rounds 8

# Docker execution (sandboxed — requires Docker)
patchloop run mini_022 --model accounts/fireworks/models/gpt-oss-120b --baseline loop_reflect --tool-rounds 8 --docker
```

### Docker setup

Build the sandbox image once:

```bash
docker build -t patchloop-sandbox:latest -f Dockerfile.sandbox .
```

If you use **Colima** instead of Docker Desktop, export the socket before running:

```bash
export DOCKER_HOST=unix:///~/.colima/default/docker.sock
```

### Run the benchmark

```bash
patchloop bench \
  -t mini_022 -t mini_024 \
  -b loop -b loop_testnames -b loop_reflect \
  --model accounts/fireworks/models/gpt-oss-120b \
  --tool-rounds 8 \
  --num-runs 3 \
  --run-delay 45 \
  --call-delay 5
```

### Stats

```bash
python eval/analysis/stats.py --tasks 022 023 024
```

---

## Project Structure

```
patchloop/
├── patchloop/
│   ├── agent/
│   │   ├── loop.py          # State machine: PLAN → APPLY → TEST → REFLECT → DECIDE
│   │   ├── planner.py       # Tool-use loop, prompt assembly, diff extraction
│   │   ├── patcher.py       # Diff validation, application, git commit
│   │   ├── reflector.py     # Structured JSON lesson from test failure
│   │   └── state.py         # LoopState, IterationRecord, Reflection, anti-repeat
│   ├── environment/
│   │   ├── local_env.py     # Sandboxed temp dir + subprocess test runner
│   │   ├── git_ops.py       # Pure Python unified diff applier + git wrapper
│   │   └── task.py          # Task and TaskResult models (loaded from YAML)
│   ├── llm/
│   │   └── client.py        # Provider-agnostic OpenAI-compatible client
│   └── cli.py               # patchloop run / patchloop bench
└── eval/
    ├── tasks/
    │   ├── mini_022.yaml    # Task: issue text, repo path, test command, limits
    │   └── repos/
    │       └── mini_022/    # Buggy Python repo + pytest suite
    └── analysis/
        └── stats.py         # Fisher's exact, Wilson CIs, per-task breakdown
```

---

## Key Implementation Details

**Pure Python diff application** — does not use `git apply`. Implements its own unified diff applier that searches for context blocks line-by-line, making it robust to LLM-generated patches with slightly wrong offsets.

**Anti-repeat detection** — If the agent produces the same failure three times in a row (MD5 hash of test output), the run terminates with `STUCK` instead of looping indefinitely.

**Full git history** — Every patch attempt is committed to git regardless of outcome.

**Structured reflection** — JSON objects with fields: `what_failed`, `root_cause_hypothesis`, `patch_summary`, `lesson`. Only the `lesson` field is injected into subsequent prompts.

**patch_assessment** — The reflector classifies each patch as `likely_wrong | likely_partial_success | unclear`. On partial success, the planner prepends "do NOT revert — look for a second bug."

**Tool round budget** — `--tool-rounds 8` creates search pressure: enough to fix Bug A, not enough to read every file. The model must choose which files to explore.
