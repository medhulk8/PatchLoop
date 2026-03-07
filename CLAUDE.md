# CLAUDE.md — PatchLoop

Memory and guidance file for Claude Code. Updated after each session.
Read this at the start of every session before touching any code.

---

## What This Project Is

`patchloop` is a benchmarkable self-improving coding agent.

Given a buggy Python repo and an issue description, it autonomously:
1. Explores the codebase using tools (read_file, list_files, search_code)
2. Proposes a unified diff patch via LLM
3. Applies the patch and runs pytest
4. Analyzes failures and generates structured reflections
5. Injects those reflections into the next attempt ("lessons learned")
6. Repeats until tests pass, iteration cap, time limit, or stuck

The goal is to demonstrate **measurable improvement** from reflection via a
formal benchmark comparing three baselines.

---

## Current Status

**First full benchmark run complete. 3 tasks × 3 baselines. Results documented below.**

### Completed this project so far

**Session 1 — Core build:**
- Full skeleton implemented and pushed to GitHub
- All phases: PLAN → APPLY_PATCH → RUN_TESTS → ANALYZE_FAILURE → REFLECT → DECIDE_NEXT
- 3 benchmark tasks: mini_001, mini_002, mini_003
- RunLogger, IterationRecord, Reflection, LoopState all wired up

**Session 2 — End-to-end fixes:**
- Switched default model: gemini-1.5-flash (deprecated) → gemini-2.5-flash
- Removed `required: []` from list_files tool schema (Gemini rejects empty arrays)
- Fixed `model_dump(exclude_none=True, exclude_unset=True)` to strip null fields
  from tool_calls messages (caused 400 INVALID_ARGUMENT from Gemini)
- Replaced `git apply` with pure Python `_apply_unified_diff()` in git_ops.py
  (git apply was failing on macOS despite correct patch content)
- First successful end-to-end runs: mini_001 ✅, mini_003 ✅

**Session 3 — Code review fixes (Codex review):**
- STUCK detection: track `last_error_signature`; only increment `consecutive_repeats`
  when current sig == previous. Alternating failures no longer falsely trigger STUCK.
- `iterations_used`: changed from `state.iteration` (0-indexed, never incremented on
  success) to `len(state.iterations)`. Was showing "0/5" on first-attempt resolve.
- LOC metric: fixed operator precedence bug — parenthesized `(+/-) and not (+++/---)`.
  `+++` header lines were being counted as added lines.
- `repeated_failure_count`: use `Counter` + `sum(max(count-1,0))` — clean and correct.
- Path traversal in `read_file`: resolve + `is_relative_to(workdir)` guard.
- Lint: ruff auto-fixed unused imports and ambiguous variable names.
- `list_files` glob escape: filter out-of-workdir matches via `is_relative_to`.
- `git_diff` drop bug: simplified from `staged or unstaged` to `git diff <ref>`.
- `loc_changed` was always 0: pass `_snapshot_sha` as ref so diff compares against
  clean baseline, not just uncommitted edits (always empty after git_commit).
- Patch-path escape in `_apply_unified_diff`: resolve + `is_relative_to` guard.
- Removed dead `TerminationReason.APPLY_FAILED` enum value (was never used; apply
  failures correctly route to DECIDE_NEXT to allow retry).
- `IterationRecord.close()` made idempotent: guard with `if ended_at is not None`.
  Was being called twice on apply failure (once in _handle_apply_patch, once in
  _handle_decide_next), giving slightly wrong iteration timing.

**Session 4 — Groq migration + first full benchmark run:**
- Migrated from Gemini (20 req/day free tier, exhausted) to Groq (14,400/day free).
  Default provider stays Gemini; use `--model` + env vars to target Groq.
- Groq models sometimes skip tool calls and output text → Groq raises `tool_use_failed`
  (HTTP 400). Fixed: catch `BadRequestError` in `chat_with_tools`, extract
  `body["failed_generation"]` (model's actual text), return it so diff extractor works.
  Key: `e.body` from Groq IS the error dict directly (no `"error"` wrapper key).
- `_apply_unified_diff` fallback: when full context match fails, try matching just the
  removed (`-`) lines. Handles patches where context lines are hallucinated (model
  skipped tools) but changed lines are correct.
- **First full benchmark run** with `meta-llama/llama-4-maverick-17b-128e-instruct`:

  | Metric | single_shot | loop | loop_reflect |
  |--------|-------------|------|--------------|
  | Resolve rate | 33% (1/3) | 67% (2/3) | 67% (2/3) |
  | Repeat failure rate | 0% | 0% | 42.9% |
  | Avg runtime (s) | 28 | 30 | 107 |

  Findings:
  - `loop` improves significantly over `single_shot` (as designed)
  - `loop_reflect` doesn't improve resolve rate on these 3 easy tasks — the reflection
    mechanism accumulates lessons (42.9% repeat rate shows cycling), but tasks aren't
    hard enough or model doesn't follow reflections well enough to show benefit
  - mini_003 (median even-length) fails all baselines — model generates consistently
    wrong fix even across 5 iterations with reflections
  - To show reflection benefit we need harder tasks where loop fails but loop_reflect succeeds

### Next session priority
1. Add harder benchmark tasks (7 more toward 10 total) where loop fails but loop_reflect
   succeeds — this is where reflection demonstrates measurable value
2. Investigate mini_003: model keeps generating wrong median fix even with 5 iters
3. Try a better model (Gemini when quota resets) that uses tools properly and follows reflections
4. Produce final results table across all 10 tasks showing reflection advantage

---

## Locked Architecture Decisions (Do Not Re-Litigate)

These were explicitly agreed upon. Do not change without user confirmation.

1. **LocalEnvironment first, DockerEnvironment Phase 2.**
   Docker is a drop-in via the same Environment ABC. Don't touch docker_env.py.

2. **Three baselines, same code path:**
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
   consecutive_repeats only increments when sig == last_error_signature.

7. **Model defaults:**
   - Dev/iteration: `gemini-2.5-flash` (free, confirmed working March 2026)
   - Alternative: `gemini-2.0-flash` (also listed as available)
   - Configurable via `--model` flag.

8. **Benchmark runtime target:**
   10 tasks × max_iters=5 × time_limit=360s per task.
   Full bench run should complete in 30–60 mins.

9. **No Claude authorship in git commits.** Never add Co-Authored-By tags.

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
patchloop run mini_002 --baseline loop

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
├── CLAUDE.md                       # this file
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
│   │   ├── git_ops.py              # GitOps: subprocess git wrapper + _apply_unified_diff
│   │   └── docker_env.py           # DockerEnvironment stub (Phase 2)
│   ├── llm/
│   │   └── client.py               # LLMClient: OpenAI SDK → Gemini endpoint
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

### Patch application (_apply_unified_diff in git_ops.py)
Pure Python unified diff applier — does NOT use `git apply`.
- git apply was failing on macOS for unknown reasons
- Searches for context lines via exact string match anywhere in the file
- Robust to LLM-generated patches with wrong line numbers in @@ headers
- Guards: resolve path + is_relative_to(workdir) before writing any file

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
`register_error_signature(sig)` → compares against `last_error_signature`,
  only increments `consecutive_repeats` on exact consecutive match.
`is_stuck()` → True when consecutive_repeats >= max_consecutive_repeats (default 3)

### loc_changed in TaskResult
`env.git_diff()` passes `_snapshot_sha` as ref → `git diff <snapshot_sha>`.
This compares committed patches against the clean initial state, not just
uncommitted edits (which are always empty after git_commit()).

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

- `Task.commit` field is not yet implemented. `LocalEnvironment.setup()` raises
  `NotImplementedError` if a task YAML specifies `commit: <sha>`. No current tasks use it.
  Implementation requires `git archive` or copying `.git`. Deferred to Phase 2.


- `pyproject.toml` build-backend must be `setuptools.build_meta` not
  `setuptools.backends.legacy:build` (already fixed, don't change it back).
- PEP 668: never pip install without a venv on this machine.
- Tasks run with the venv's pytest, but LocalEnvironment runs test_cmd
  via subprocess in the workspace — the workspace uses whatever `pytest`
  is on PATH inside the sandbox. If setup_cmd is None, the task repo
  must not have external dependencies beyond stdlib + pytest.
- mini_001's original retry.py had a non-bug. Fixed: now uses a single
  `except Exception` clause that incorrectly catches PermanentError.
- gemini-2.5-flash free tier has low RPD (requests per day). If quota
  hits during a bench run, the run errors with 429. Wait until next day
  or use a fresh API key from aistudio.google.com.

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
