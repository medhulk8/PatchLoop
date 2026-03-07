# AGENTS.md — PatchLoop

Memory and guidance file for Codex. Updated after each session.
Read this at the start of every session before touching any code.

---

## What This Project Is

`patchloop` is a benchmarkable self-improving coding agent.

Given a buggy Python repo and an issue description, it autonomously:
1. Explores the codebase using tools (read_file, list_files, search_code)
2. Proposes a unified diff patch via Codex
3. Applies the patch and runs pytest
4. Analyzes failures and generates structured reflections
5. Injects those reflections into the next attempt ("lessons learned")
6. Repeats until tests pass, iteration cap, time limit, or stuck

The goal is to demonstrate **measurable improvement** from reflection via a
formal benchmark comparing four baselines.

---

## Current Status

**First full benchmark run complete. 3 tasks × 3 baselines.**

| Metric | single_shot | loop | loop_reflect |
|--------|-------------|------|--------------|
| Resolve rate | 33% (1/3) | 67% (2/3) | 67% (2/3) |
| Repeat failure rate | 0% | 0% | 42.9% |
| Avg runtime (s) | 28 | 30 | 107 |

Key findings: loop beats single_shot as designed. Reflection does not yet improve
resolve rate on 3 easy tasks — need harder tasks where the loop itself fails.

Next priority: add 7 harder benchmark tasks, try a better model (Gemini when quota resets).

---

## Locked Architecture Decisions (Do Not Re-Litigate)

These were explicitly agreed upon. Do not change without user confirmation.

1. **LocalEnvironment first, DockerEnvironment Phase 2.**
   Docker is a drop-in via the same Environment ABC. Don't touch docker_env.py.

2. **Four baselines, same code path:**
   - `single_shot`: max_iterations=1, no reflection
   - `loop`: max_iterations=N, no reflection
   - `loop_reflect`: max_iterations=N, inject ALL prior in-run reflections

3. **Reflection injection = ALL prior reflections from the current run.**
   No "most relevant 2-3" — that's overcomplicated for Phase 1.
   Inject all of them as "Lessons learned / do not repeat" in the PLAN prompt.
   Phase 2 adds cross-run vector retrieval.

4. **State machine phases (in order):**
   PLAN → APPLY_PATCH → RUN_TESTS → ANALYZE_FAILURE → REFLECT → DECIDE_NEXT → TERMINATE
   GATHER_CONTEXT was dropped — merged into PLAN.

5. **Git commit after APPLY_PATCH regardless of test outcome.**
   Every patch attempt is in git history for replay.
   Commit message format: `[{run_id}] iter_{n}: apply patch`

6. **Anti-repeat: MD5 hash of last 500 chars stderr + last 200 chars stdout.**
   3 consecutive identical failures → STUCK termination.

7. **Model defaults:**
   - Dev/iteration: `gemini-2.5-flash` (free, confirmed working default)
   - Alternative: `gemini-2.0-flash` (also listed as available)
   - Configurable via `--model` flag.

8. **Benchmark runtime target:**
   10 tasks × max_iters=5 × time_limit=360s per task.
   Full bench run should complete in 30–60 mins.

9. **No Codex authorship in git commits.** Never add Co-Authored-By tags.

---

## Setup

```bash
cd ~/Desktop/projects/patchloop

# Create and activate venv (Python 3.13 on this machine)
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev deps
pip install -e ".[dev]"

# Set API key
# Get free key at: https://aistudio.google.com
export GEMINI_API_KEY=your_key_here
```

The venv is at `.venv/` and is gitignored.

---

## Commands

```bash
# Run a single task (best for debugging)
patchloop run mini_003
patchloop run mini_001 --baseline single_shot
patchloop run mini_002 --baseline loop --model gemini-1.5-pro

# Run full benchmark (all tasks × all baselines)
patchloop bench

# Run specific subset
patchloop bench -t mini_001 -t mini_002 -b loop -b loop_reflect

# Verify a task's broken repo actually fails
pytest eval/tasks/repos/mini_001/ -q --tb=short
pytest eval/tasks/repos/mini_002/ -q --tb=short
pytest eval/tasks/repos/mini_003/ -q --tb=short

# Lint
ruff check patchloop/
```

---

## Repository Structure

```
patchloop/
├── pyproject.toml                  # build config, dependencies
├── AGENTS.md                       # this file
├── .gitignore
├── patchloop/                      # main Python package
│   ├── agent/
│   │   ├── state.py                # AgentPhase, LoopState, IterationRecord, Reflection
│   │   ├── loop.py                 # AgentLoop — the state machine
│   │   ├── planner.py              # PLAN phase: tool-use + diff extraction
│   │   ├── patcher.py              # APPLY_PATCH: validate + apply + commit
│   │   └── reflector.py            # REFLECT: structured JSON reflection from failures
│   ├── environment/
│   │   ├── task.py                 # Task, TestResult, TaskResult (Pydantic)
│   │   ├── base.py                 # Environment ABC (10 methods)
│   │   ├── local_env.py            # LocalEnvironment: temp dir + subprocess
│   │   ├── git_ops.py              # GitOps: subprocess git wrapper
│   │   └── docker_env.py           # DockerEnvironment stub (Phase 2)
│   ├── llm/
│   │   └── client.py               # LLMClient: Anthropic SDK + token tracking
│   ├── observability/
│   │   └── logger.py               # RunLogger: JSONL event log per run
│   ├── memory/
│   │   └── store.py                # ReflectionStore: flat JSON now, vector Phase 2
│   ├── eval/
│   │   ├── bench_runner.py         # BenchmarkRunner: orchestrates tasks × baselines
│   │   ├── metrics.py              # compute_metrics(), format_summary_table()
│   │   └── baselines.py            # build_agent() factory for all 3 baselines
│   └── cli.py                      # `patchloop bench` and `patchloop run`
└── eval/
    └── tasks/
        ├── mini_001.yaml
        ├── mini_002.yaml
        ├── mini_003.yaml
        └── repos/
            ├── mini_001/           # retry() catches PermanentError (should not retry)
            ├── mini_002/           # paginate() off-by-one in slice end
            └── mini_003/           # median() wrong for even-length lists
```

---

## Key Implementation Details

### run_id synchronization
`run_id` is generated in `baselines.build_agent()` and passed to both
`RunLogger` and `AgentLoop.run(run_id=...)`. This ensures the JSONL log
file and LoopState share the same identifier. Do not break this flow.

### LocalEnvironment reset()
Does `git reset --hard <snapshot_sha>` (NOT a re-copy).
- `snapshot_sha` is saved as `self._snapshot_sha` during `setup()`
- Fast: no filesystem copy, just git reset + clean
- Preserves full iteration git history for replay

### Diff extraction (planner.py)
`extract_diff()` looks for a fenced ` ```diff ``` ` block first,
then falls back to raw `--- / +++ / @@` headers.
If no diff found → `record.proposed_diff = None` → loop terminates with NO_DIFF.

### Reflection injection (planner.py `build_user_message`)
Only injected when `state.baseline == "loop_reflect"` AND `state.reflections` is non-empty.
Injects ALL reflections from the current run as bullet points under
"Lessons from previous failed attempts / Do NOT repeat these mistakes".

### Anti-repeat detection (state.py)
`LoopState.make_error_signature(stderr, stdout)` → MD5 hex[:12]
`register_error_signature(sig)` → returns True if repeat, increments consecutive_repeats
`is_stuck()` → True when consecutive_repeats >= max_consecutive_repeats (default 3)

### Benchmark task calibration rule
Tasks must be designed so:
- `single_shot` often fails (issue description alone is insufficient)
- `loop` can solve in 2–4 iterations
- `loop_reflect` reduces repeated failures vs `loop`

DO NOT add tasks that single_shot trivially solves. The delta is the point.

---

## Mini-Bench v1 Tasks (Current: 3/10)

| ID       | Bug                                    | Difficulty | Expected single_shot |
|----------|----------------------------------------|------------|----------------------|
| mini_001 | retry() catches PermanentError         | medium     | likely fails         |
| mini_002 | paginate() off-by-one (end slice)      | easy       | may pass             |
| mini_003 | median() wrong for even-length inputs  | easy       | likely passes        |

Need 7 more tasks. Target difficulties: 3 easy, 4 medium, 3 hard.

---

## Observability

Run logs: `runs/{run_id}/{task_id}.jsonl`
Benchmark report: `runs/report_{timestamp}.json`

Each JSONL line is one event: `run_start`, `phase`, `plan`, `patch_proposed`,
`patch_applied`, `test_result`, `reflection`, `error`, `run_end`.

All writes are flushed immediately (no buffering) to survive crashes.

---

## Phase 2 Roadmap (Not Started)

- DockerEnvironment: docker-py, CPU/mem/PID limits, no network
- Cross-run reflection retrieval: FAISS or Chroma vector store
  (ReflectionStore.query() already has the right interface)
- 7 more benchmark tasks (target: 10 total)
- Full benchmark run with results table
- Ablation analysis writeup

---

## Known Issues / Gotchas

- `Task.commit` is not implemented. `LocalEnvironment.setup()` raises `NotImplementedError`
  if a task YAML sets `commit:`. No current tasks use it. Deferred to Phase 2.
- `pyproject.toml` build-backend must be `setuptools.build_meta` (already fixed, don't change).
- PEP 668: never pip install without a venv on this machine.
- LocalEnvironment runs test_cmd via subprocess — the workspace uses whatever `pytest`
  is on PATH. Task repos must not have external dependencies if setup_cmd is None.
- gemini-2.5-flash free tier has 20 req/day limit. Use Groq as fallback (see LLM Provider Setup).

---

## LLM Provider Setup

We use Google Gemini (free) via an OpenAI-compatible endpoint.
The `openai` Python package is just a universal SDK — it talks to Google's servers, not OpenAI's.

### Default (Gemini — free)
```bash
export GEMINI_API_KEY=your_key_here
# Get free key at: https://aistudio.google.com (no credit card)
```
Default model: `gemini-2.5-flash` (free, confirmed working March 2026)

### Alternative: Groq (also free)
```bash
export LLM_API_KEY=your_groq_key
export LLM_BASE_URL=https://api.groq.com/openai/v1
# patchloop run mini_001 --model llama-3.1-70b-versatile
```
Get free key at: https://console.groq.com

### Environment variables
| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (preferred) |
| `LLM_API_KEY` | Generic override for any provider |
| `LLM_BASE_URL` | Custom API base URL (default: Gemini endpoint) |
