# PatchLoop: Benchmarkable Self-Improving Coding Agent

## Overview

PatchLoop is a research platform for studying autonomous code repair. Given a buggy Python repository and an issue description, PatchLoop autonomously explores the codebase, proposes a fix, applies it, and runs the test suite. When tests fail, the agent writes a structured reflection on what went wrong and why — then uses that lesson in the next attempt.

The central research question:

> **Under what conditions does structured reflection become the load-bearing signal for an autonomous coding agent?**

## Core Capabilities

- **Agentic code exploration** using tool calls — the agent reads files, lists directories, and searches code before proposing any fix
- **Structured reflection** — failed attempts produce a JSON lesson capturing what went wrong, the root cause, and a specific instruction for the next attempt
- **Controlled baseline comparison** across four configurations to isolate what actually improves performance
- **Search-budget ablation** via configurable tool-round limits, revealing the regime where reflection matters
- **Full observability** — every patch attempt is committed to git and every event is logged in structured JSONL

## How It Works

The agent runs a state machine loop:

1. **PLAN** — reads the issue, explores the codebase with tools, proposes a unified diff
2. **APPLY** — applies the diff to the repo and commits it to git
3. **TEST** — runs pytest; if all tests pass, the task is resolved
4. **REFLECT** — if tests fail, the agent generates a structured lesson from the failure output
5. **REPEAT** — the lesson is injected into the next planning prompt, and the loop continues

Every patch attempt is committed regardless of outcome. The full iteration history is preserved for replay and analysis.

## Research Design

Four baselines share the same code path. The only difference is what gets injected into each planning prompt:

| Baseline | Loops | Structured lessons | Failing test names |
|---|:---:|:---:|:---:|
| `single_shot` | ✗ | ✗ | ✗ |
| `loop` | ✓ | ✗ | ✗ |
| `loop_testnames` | ✓ | ✗ | ✓ |
| `loop_reflect` | ✓ | ✓ | ✓ |

`loop_testnames` is an ablation baseline — it injects the names of still-failing tests with no structured lessons. This isolates whether test-name grounding alone accounts for any improvement.

## Benchmark Tasks

15 hand-crafted Python mini-repos with deliberately planted bugs and pytest suites that fail on buggy code and pass on correct fixes. All stdlib-only, no external dependencies beyond pytest.

**Standard slice (mini_001–010)** — informative test names, single and multi-file bugs at varying difficulty levels.

**Reflection-critical slice (mini_011–015)** — generic test names (`test_regression_N`), cascade bugs across multiple files, vague issue descriptions, and wrong-file traps. Designed so the agent cannot succeed by matching test names to file names — it must encode and apply a conceptual lesson.

## Getting Started

Requires Python 3.11+.

```bash
git clone https://github.com/medhulk8/PatchLoop.git
cd PatchLoop

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

PatchLoop uses the OpenAI-compatible API format and works with any provider that supports it. **Cerebras is the recommended provider** for benchmarking — it has a generous free tier and low latency.

```bash
# Recommended: Cerebras (free — https://cloud.cerebras.ai)
export CEREBRAS_API_KEY=your_key_here
```

Other supported providers:

```bash
# Google Gemini (free — https://aistudio.google.com)
export GEMINI_API_KEY=your_key_here

# Groq or any OpenAI-compatible endpoint
export LLM_API_KEY=your_key_here
export LLM_BASE_URL=https://api.groq.com/openai/v1
```

## Usage

### Single task

```bash
patchloop run mini_004 --baseline loop_reflect --model gpt-oss-120b
```

### Full benchmark

```bash
patchloop bench --model gpt-oss-120b
```

### Specific tasks and baselines with averaged repetitions

```bash
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
| `--model` | `gemini-2.5-flash` | LLM model |
| `--tool-rounds` | `15` | Max tool calls per planning step (search budget) |
| `--num-runs` | `1` | Repetitions per task/baseline pair |
| `--run-delay` | `30` | Seconds between repetitions |
| `--call-delay` | `0` | Seconds between individual API calls |

## Technical Architecture

The system consists of four primary layers:

1. **Agent** (`patchloop/agent/`) — state machine loop, planner, patcher, reflector, and state tracking
2. **Environment** (`patchloop/environment/`) — sandboxed temp directory, subprocess test runner, pure Python diff applier, and git operations
3. **LLM Client** (`patchloop/llm/`) — provider-agnostic client supporting Cerebras, Gemini, Groq, and any OpenAI-compatible endpoint
4. **Eval Harness** (`patchloop/eval/`) — benchmark runner, baseline factory, and metrics computation

Run logs are written to `runs/{run_id}/{task_id}.jsonl`. Benchmark reports are written to `runs/report_{timestamp}.json`.

## Status

Active research project. Infrastructure and benchmark suite are complete. Averaged multi-run results across the reflection-critical task slice are in progress.

## License

MIT
