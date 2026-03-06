# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`patchloop` is a benchmarkable, self-improving coding agent. Given a buggy Python repo and an issue description, it uses Claude to iteratively generate unified diffs, apply them, run tests, and reflect on failures — comparing three baselines: `single_shot`, `loop`, and `loop_reflect`.

## Installation

```bash
pip install -e ".[dev]"
```

Requires `ANTHROPIC_API_KEY` in the environment.

## Commands

```bash
# Run all tasks across all baselines
patchloop bench

# Run specific task(s) or baseline(s)
patchloop bench -t mini_001 -b loop_reflect

# Run a single task interactively (good for debugging)
patchloop run mini_001
patchloop run mini_002 --baseline single_shot --model claude-sonnet-4-6

# Lint
ruff check patchloop/

# Run tests (note: there are no framework-level unit tests — the eval tasks ARE the tests)
pytest eval/tasks/repos/mini_001/ -q --tb=short
```

## Architecture

### Agent Loop State Machine

`patchloop/agent/loop.py` — `AgentLoop` drives a state machine per task run:

```
PLAN -> APPLY_PATCH -> RUN_TESTS -> ANALYZE_FAILURE -> REFLECT -> DECIDE_NEXT -> PLAN (next iter)
                                                                              -> TERMINATE
```

- **PLAN** (`planner.py`): LLM gets tool access (`read_file`, `list_files`, `search_code`) to explore the codebase, then produces a unified diff in a ` ```diff ``` ` block.
- **APPLY_PATCH** (`patcher.py`): Applies the diff via `git apply` in the sandboxed workspace.
- **RUN_TESTS**: Runs `task.test_cmd` (default: `pytest -q --tb=short`) and captures results.
- **ANALYZE_FAILURE**: Computes an MD5 error signature from test output to detect repeated failures.
- **REFLECT** (`reflector.py`): LLM analyzes the failure and produces a structured JSON `Reflection` (only in `loop_reflect` baseline).
- **DECIDE_NEXT**: Terminates if stuck (3 identical failures), at iteration cap, or time limit; otherwise resets workspace and loops.

### Three Baselines

Defined in `patchloop/eval/baselines.py`:
- `single_shot` — one iteration, no reflection
- `loop` — up to N iterations, no reflection
- `loop_reflect` — up to N iterations; reflections from failures are injected as "Lessons learned" into the next PLAN prompt

All three run through the same `AgentLoop` code path — only `baseline` string controls behavior.

### Environment Abstraction

`patchloop/environment/base.py` — `Environment` ABC. Current implementation: `LocalEnvironment` (temp dir + subprocess). `DockerEnvironment` is stubbed for future use.

`LocalEnvironment` flow:
1. Copies the task's `repo` to a temp dir (never modifies source)
2. Creates a single-commit git snapshot as a reset target
3. Each iteration resets via `git reset --hard <snapshot_sha>` (fast, preserves history)

### Task Definition

Tasks are YAML files in `eval/tasks/`. Each points to a `repo` directory containing buggy Python source + a pytest test file. The `repo` path is resolved relative to the YAML file.

```yaml
task_id: mini_001
repo: repos/mini_001         # relative to this yaml file
issue: |
  <natural language bug description>
test_cmd: pytest -q --tb=short
time_limit_s: 360
max_iterations: 5
difficulty: medium
```

### Observability

`RunLogger` writes JSONL event logs to `runs/{run_id}/{task_id}.jsonl`. Each event is a structured dict (phase transitions, patches, test results, reflections). The benchmark runner also writes `runs/report_{timestamp}.json` with aggregated metrics.

### LLM Client

`patchloop/llm/client.py` — thin Anthropic SDK wrapper. Two call modes:
- `chat()` — single-turn (used by Reflector)
- `chat_with_tools()` — agentic tool-use loop up to 15 rounds (used by Planner)

Token usage is accumulated into `IterationRecord` for cost tracking.

## Adding a New Task

1. Create `eval/tasks/repos/<task_id>/` with buggy Python source + test file(s)
2. Create `eval/tasks/<task_id>.yaml` pointing to that directory
3. Verify: `patchloop run <task_id>`
