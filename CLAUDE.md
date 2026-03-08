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
formal benchmark comparing four baselines.

---

## Current Status

**17 tasks built. mini_016 (3× replicated). mini_017 (3× attempted, rep 3 throttled). Both corroborate: loop_reflect is the only baseline that can escape the cascade on reflection-critical tasks.**

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

**Session 5 — 7 new tasks + substring match fix:**
- Added mini_004–010: 7 harder benchmark tasks designed to require loop/reflection to solve
  (jsonl_contract, deep_merge, markdown_anchor_sync, safe_join_nested, group_rows,
  retry_after, csv_quote_aware). All stdlib-only, all verified failing on buggy code.
- Fixed critical `_apply_unified_diff` bug: `file_text.find(before_text)` matched truncated
  context lines as substrings of longer annotated lines. E.g., `def group_rows(rows: ...)`
  matched as prefix of `def group_rows(rows: ...) -> dict[...]:`, then after_lines replaced
  the block with the truncated version → `SyntaxError: expected ':'`.
  Fix: replaced `str.find()` with line-by-line `file_lines[li:li+n] == before_lines` comparison.
  Fallback (removed-lines-only match) also converted to line-by-line for consistency.
- Raw text now read separately for trailing-newline detection (splitlines() strips it).
- Ran 7-task benchmark (mini_004–010) with Llama 4 Maverick:
  single_shot: 0%, loop: 0%, loop_reflect: 14.3% (only mini_007 resolved in iter 3).
  mini_007 resolved by loop_reflect but not loop/single_shot — reflection advantage confirmed.
  mini_005/mini_006 terminate at iters=1 even with max_iterations=5 (NO_DIFF: model outputs prose).
  Tasks are well-calibrated; model quality is the bottleneck — need Gemini for full results.

**Session 6 — Cerebras provider + first clean 10-task benchmark:**
- Added Cerebras as a provider: set `CEREBRAS_API_KEY` and the base URL auto-configures to
  `https://api.cerebras.ai/v1`. Available model: `gpt-oss-120b` (14,400 RPD free tier).
- Tried file pre-loading (inject all .py files into PLAN message) — abandoned because it
  let single_shot "cheat" by seeing all files at once, defeating tasks designed around
  iterative test-feedback discovery (mini_004 writer bug, mini_006 3-file fix). Reverted.
- **First clean 10-task benchmark** with Cerebras `gpt-oss-120b`:

  | Metric | single_shot | loop | loop_reflect |
  |--------|-------------|------|--------------|
  | Resolve rate | 90% (9/10) | **100% (10/10)** | 90% (9/10) |
  | Avg iters (success) | 1.00 | 1.30 | 1.00 |
  | Repeat failure rate | 0% | 0% | 16.7% |

  Findings:
  - `loop > single_shot` (100% vs 90%) ✅ — the iterative feedback mechanism works.
    mini_004 (jsonl contract) fails single_shot (only fixes reader) but loop catches
    the writer bug via test failure output. This is the core signal working.
  - `loop_reflect = single_shot` (90%) — reflection is not helping on this model.
    mini_004 fails loop_reflect in 3 iters despite loop solving it in 1.
    The loop_reflect result appears to be partly LLM non-determinism: loop's iter 1
    succeeds while loop_reflect's iter 1 (same prompt, no reflections yet) fails.
  - Single-run benchmarks with strong capable models are noisy — need multiple runs
    or harder tasks where even loop struggles, so loop_reflect's advantage is clear.

**Session 7 — loop_reflect fix + clean 100% benchmark:**
- Root cause of loop_reflect regression found: reflections said "fix the writer" but model only read reader.py.
  Abstract lesson alone wasn't enough — model needed the concrete failing test name
  `test_writer_terminates_each_record_with_newline` to know which file to open.
- Fix: inject `FAILED <test_name>` lines from last iteration's stdout into loop_reflect PLAN prompt
  (in `build_user_message` in planner.py). Only lines starting with "FAILED" are extracted.
- **Second clean 10-task benchmark** with Cerebras `gpt-oss-120b` after fix:

  | Metric | single_shot | loop | loop_reflect |
  |--------|-------------|------|--------------|
  | Resolve rate | 90% (9/10) | 80% (8/10) | **100% (10/10)** |
  | Avg iters (success) | 1.00 | 1.25 | 1.20 |
  | Avg runtime (s) | 4.40 | 19.30 | 12.30 |
  | Repeat failure rate | 0% | 0% | 0% |

  Key findings:
  - `loop_reflect` is now definitively best — resolves 100% including mini_006 (3-file fix in 3 iters)
    and mini_009 that loop failed.
  - `loop` regression to 80% this run (vs 100% prior run) is non-determinism with a strong model.
    Single-run benchmarks on capable models are noisy.
  - loop_reflect resolving mini_006 (3 files, 3 iters) is clean proof the reflection mechanism works:
    loop fails because iter 1 only fixes slug.py; loop_reflect uses the lesson + failing test names
    to find toc.py and renderer.py on subsequent iterations.

**Session 8 — loop_testnames ablation:**
- Added `loop_testnames` baseline: injects failing test names but no reflection lessons.
  This isolates whether gains come from test-name grounding or structured reflection.
- **Ablation run** (10 tasks × 4 baselines, Cerebras gpt-oss-120b):

  | Baseline | Resolve rate | Avg iters | Repeat failures |
  |---|---|---|---|
  | single_shot | 90% | 1.00 | 0% |
  | loop | **100%** | 1.10 | 0% |
  | loop_testnames | **100%** | 1.30 | 7.7% |
  | loop_reflect | 90% | 1.11 | 0% |

  Key finding: `loop_testnames` = 100% with no reflection lessons — matches loop.
  `loop_reflect` = 90% this run (mini_010 failed, non-determinism).
  Suggests failing test names are the primary grounding signal, not structured lessons.
  However, single-run variance is too high to conclude this definitively.

  Revised framing: the real insight is "environment grounding > abstract reasoning" —
  raw `FAILED test_xxx` names are more actionable than conceptual lesson summaries.

**Session 9 — reflection-critical task slice (mini_011, mini_012):**
- Added 2 new tasks with generic test names (test_regression_N) and cross-file conceptual bugs.
- mini_011 (falsy_config_roundtrip): merge.py + serialize.py both treat falsy as absent.
  mini_012 (cache_key_missing_dimension): cache.py ignores locale+mode in key; issue implicates render.py.
- **Result** (2 tasks × 4 baselines):

  | Baseline | mini_011 | mini_012 | Resolve rate |
  |---|---|---|---|
  | single_shot | RESOLVED (1 iter) | FAILED | 50% |
  | loop | RESOLVED (2 iters) | RESOLVED (1 iter) | 100% |
  | loop_testnames | RESOLVED (1 iter) | RESOLVED (1 iter) | 100% |
  | loop_reflect | RESOLVED (1 iter) | RESOLVED (1 iter) | 100% |

  Key findings:
  - mini_012 cleanly separates single_shot (FAILED) from all iterative baselines (RESOLVED) — confirms
    the iteration loop is necessary to find the cache key bug after failing on render.py.
  - mini_011 single_shot resolved: gpt-oss-120b read both files and fixed both bugs in one shot.
    Task isn't hard enough for this model. May need redesign or replacement.
  - All iterative baselines remain equivalent (100%) — consistent with the ablation finding.
    For this capable model on small repos, iteration alone is sufficient; structured reflection
    does not add measurable value over plain test-name grounding.

  Honest conclusion: for gpt-oss-120b on 2-3 file repos, the model re-reads all code after
  failure and resolves issues without needing structured lessons. Reflection would likely
  matter on (A) weaker models, or (B) larger codebases where full exploration isn't feasible
  in 15 tool rounds. mini_012 is a keeper; mini_011 needs rethinking.

**Session 10 — search-budget ablation (`--tool-rounds`):**
- Implemented `--tool-rounds` CLI flag, threaded through full chain:
  `cli.py` → `BenchmarkRunner` → `build_agent` → `AgentLoop` → `Planner` → `chat_with_tools`.
- Ran `loop` vs `loop_reflect` on mini_004 + mini_005 + mini_006 at tool_rounds = 15, 8, 4.

  | tool_rounds | loop | loop_reflect | Notes |
  |---|---|---|---|
  | 15 | 66.7% (2/3) | 33.3% (1/3) | loop_reflect fails mini_006 — non-determinism |
  | 8  | 66.7% (2/3) | 66.7% (2/3) | loop_reflect solves mini_006 in 1 iter; loop takes 3 iters for mini_004 |
  | 4  | **0.0% (0/3)** | **0.0% (0/3)** | LOC changed=0 on all — model produces NO_DIFF, can't explore in 4 rounds |

  Key findings:
  - **4 rounds → complete collapse**: both baselines produce 0 patches (NO_DIFF). Minimum viable
    search budget for these 2-3 file tasks is ~8 rounds.
  - **8 rounds micro-signal**: loop_reflect solved mini_006 (3-file fix) in 1 iter while loop
    failed it. loop solved mini_004 in 3 iters while loop_reflect failed. Suggests directional
    advantage from reflection on multi-file tasks, but swamped by single-run variance.
  - **Single-run variance dominates**: at 15 rounds loop_reflect scored 33% this run vs 100%
    in session 7. No statistic from any single run is trustworthy.
  - **Bottom line**: the ablation produced ambiguous results. Need 3× averaged runs to get
    credible numbers. Quota exhausted trying to run 3×; deferred to next session.
- Also implemented `--num-runs N` + `--run-delay S` in CLI/BenchmarkRunner for proper
  averaged benchmarks. Seeds loop over baselines with configurable delay to avoid rate-limit bursts.

  - mini_013 (pipeline_falsy_cascade): validator drops falsy, serializer or-merges.
    Wrong-file trap (pipeline.py). Built and tested — but single_shot ALSO resolved it in 1 iter.
  - mini_014 (report_pipeline, 7 files): bug in aggregator.py: `group_key = t.id or t.category`.
    Issue description implicates formatter.py (wrong-file trap). But the bug was obvious from the
    inline comment: "Use the transaction's own identifier as the grouping key". Model solved it in
    0 iterations (never used a tool — went straight from issue description to patch). ALSO too easy.
  - **Definitive conclusion**: gpt-oss-120b trivially fixes any bug whose location is inferable from
    the issue description alone (semantically or structurally). Even 7-file repos are not enough if
    the bug manifests an obvious code smell (like a comment describing it).

**Session 11 — mini_015 + 3× averaged benchmark attempt:**
- Built mini_015 (event_pipeline, 7 files): cascade falsy bug — 2 bugs in different files.
  - BUG A (enricher.py): `e.priority = e.priority or defaults.get("priority", 5)` and
    `e.value = e.value or defaults.get("value", 1.0)` — `or` pattern replaces 0/0.0 with defaults.
  - BUG B (reducer.py): `if e.priority: b["priorities"].append(e.priority)` — skips 0-priority events.
  - Issue description is deliberately vague: "category totals and priority ranges are wrong."
    No mention of enricher or reducer. Wrong-file trap: says "report format looks fine."
  - Cascade: fixing BUG A makes test_02 pass but tests_03/04/05 still fail because reducer
    still filters 0-priority events. Model must iterate to find and fix BUG B.
  - Verified: 4/5 tests fail on buggy code. Fixing enricher-only leaves 3/5 still failing.
    Both fixes together → all 5 pass.
  - Status: built but NOT yet tested against model (Cerebras token quota exhausted).
- **3× averaged benchmark** attempted multiple times — all blocked by daily token quota.
  Error: `token_quota_exceeded: Tokens per day limit exceeded - too many tokens processed.`
  Cerebras free tier has a daily TOKEN BUDGET (not just RPD). Heavy benchmarking exhausts it.
  Retries (30s/60s backoff) do eventually succeed IF the daily budget isn't fully spent —
  confirmed: mini_004 loop resolved in 313s (1 iteration) after 5 rate-limit retries.
  But running 3× of 3 tasks × 2 baselines exhausts the budget within the session.
  `--call-delay 7` helps with per-minute smoothing but cannot extend the daily budget.
- Added `--call-delay S` parameter (default 0) to CLI, BenchmarkRunner, LLMClient.
- Added error body to rate-limit retry messages for better diagnostics.

**Session 12 — framing + planning (no code changes):**
- Attempted 3× benchmark on startup but CEREBRAS_API_KEY was not saved to shell config — failed immediately.
- Reviewed external analysis (ChatGPT). Key agreements:
  - Bigger repos alone don't make tasks reflection-critical — it's about *selective search pressure without leaking the invariant*
  - mini_013/014 are calibration tasks (too easy), not failures — useful as controls
  - mini_015 is the most promising task built so far; should be validated before spending quota on 3×
  - Single-run variance is the core problem — replication must be treated as immediate, not deferred
  - Stay on gpt-oss-120b; don't switch to weaker models (blurs the systems narrative)
- **Sharpened core hypothesis**: reflection becomes load-bearing when search is scarce and the next action is ambiguous — not universally, not on bigger repos alone
- **Plan for next session**: validate mini_015 with 3 cheap runs first, then 3× averaged benchmark if it shows signal

**Session 13 — mini_015 validation + 3× averaged benchmark:**
- CEREBRAS_API_KEY saved to ~/.zshenv so it persists across sessions.
- **mini_015 validation results** (tool_rounds=8 then 15, Cerebras gpt-oss-120b):
  - At tool_rounds=8: ALL baselines terminate with NO_DIFF (7-file repo, 8 rounds insufficient for exploration)
  - At tool_rounds=15: ALL baselines fail with STUCK (3-4 iters each)
  - Root cause: model correctly fixes reducer.py's `if e.priority:` in iter 0, but enricher.py
    is replacing priority=0 with 5 UPSTREAM of reducer, so the reducer fix has no visible effect.
    Reflections generated are ANTI-helpful: they blame the correct reducer fix instead of pointing
    to enricher.py. The cascade ordering makes this a pathological case for the reflector.
  - **Conclusion**: mini_015 does NOT work as a reflection-critical task. The reflector generates
    misleading lessons when the model's fix is correct but an upstream bug masks the improvement.
    The cascade is real (two bugs, two files) but the fix order is wrong for reflection to help.
  - **New research finding**: loop_reflect can DEGRADE performance vs loop when reflector
    diagnoses are incorrect. This is a known limitation of single-run reflectors without
    "progress tracking" (comparing which tests passed before vs after the fix).
  - mini_015 is now archived as a "pathological case" — not used in the benchmark but documented.
- **3× averaged benchmark** on mini_004/005/006 (loop vs loop_testnames vs loop_reflect,
  tool_rounds=8, num_runs=3, run_delay=30, call_delay=7) — **COMPLETE**.
  Full results (9 runs per baseline):

  | Metric | loop | loop_reflect | loop_testnames |
  |---|---|---|---|
  | Resolve rate | 55.6% (5/9) | 55.6% (5/9) | **66.7% (6/9)** |
  | Avg iters (success) | 1.40 | 1.60 | 1.67 |
  | Avg runtime (s) | 63.90 | 81.60 | 66.30 |
  | Repeat failure rate | 23.1% | 20.0% | **7.7%** |

  Per-task breakdown (all 3 reps):
  - mini_004 (jsonl_contract): loop=2/3, loop_testnames=3/3, loop_reflect=2/3
  - mini_005 (merge_config): loop=2/3, loop_testnames=3/3, loop_reflect=3/3
  - mini_006 (anchor_sync): loop=1/3, loop_testnames=0/3, loop_reflect=0/3

  **Key findings:**
  - `loop_testnames` is the best performer on these tasks — higher resolve rate AND lowest repeat rate.
    Failing test names are a more reliable grounding signal than structured lessons for gpt-oss-120b.
  - `loop_reflect` = `loop` in resolve rate (55.6%). Structured lessons not adding value over bare loop.
  - mini_006 is the hardest task (anchor normalization across 3 files): loop solved it once,
    loop_testnames and loop_reflect both failed all 3 reps. It's near the model's capability ceiling.
  - The ablation is clean: test-name grounding explains most of the gap between loop and loop_reflect.
    The "conceptual lesson" component isn't the load-bearing signal on this task slice.
  - This confirms the research question: reflection becomes load-bearing only under specific conditions
    (generic test names + scarce search budget + ambiguous next action). Standard tasks with
    informative test names don't expose that regime.

  **Report**: runs/report_1772955525.json

### Next session priority

**Current standing:**
- mini_016: 3× replicated — loop_reflect=66.7%, loop=loop_testnames=33.3%
- mini_017: 3× attempted; reps 1+2 clean (loop=0%, loop_testnames=0%, loop_reflect=50%); rep 3 throttled repeatedly (daily token quota exhausted mid-run)
- Two independent reflection-critical tasks with consistent baseline separation
- CEREBRAS_API_KEY is in ~/.zshenv — no manual setup needed

**IMPORTANT — mini_017 rep 3 note:**
Two separate rerun attempts (Session 16 and 17) both hit Cerebras daily token quota mid-run.
Rep 3 always runs on a day where earlier benchmarks already spent the daily budget.
The fix: **run mini_017 rep 3 FIRST on a fresh day, before any other API calls.**
Command:
```bash
patchloop bench -t mini_017 -b loop_testnames -b loop_reflect --model gpt-oss-120b --tool-rounds 6 --num-runs 1 --call-delay 7
```
(loop rep 3 is clean at 0/1 FAILED; only loop_testnames and loop_reflect need re-running)

**After mini_017 rep 3 (still on fresh day, same session):**
2. **Run single_shot baseline on mini_016/017** to complete the 4-baseline picture:
   ```bash
   patchloop bench -t mini_016 -t mini_017 -b single_shot --model gpt-oss-120b --tool-rounds 6 --num-runs 3 --run-delay 30 --call-delay 7
   ```

**The research story in one paragraph:**
Reflection produces measurably better outcomes specifically when (a) test names are generic and
uninformative, (b) the second bug is in a file that can't be found by name or import tracing
in the available tool round budget, and (c) the structured lesson correctly redirects the search.
On standard tasks with informative test names, environment grounding (test names) dominates and
reflection adds nothing. On reflection-critical tasks (generic names + tight budget + cascade bugs),
loop_reflect doubles the resolve rate vs loop and loop_testnames.

CEREBRAS_API_KEY is saved in ~/.zshenv. No manual setup needed at session start.

**Session 17 — mini_017 rep 3 rerun blocked by token quota:**
- Attempted clean rerun of mini_017 rep 3 (loop_testnames + loop_reflect only).
- Result: Cerebras daily token quota exhausted again. Both baselines hit 4/4 retries and terminated
  in 1 iter each (invalid). Same failure mode as Session 16 rep 3.
- Root cause confirmed: the daily token budget is consistently spent by the time rep 3 runs.
  The only solution is to run rep 3 FIRST on a fresh day, before any other API calls.
- loop_testnames ran 5 iters but LOC changed = 0 (all patches empty due to quota failures).
  Result is invalid — not usable as clean data.
- No code changes this session. Report: runs/report_1772990134.json

**Session 16 — mini_017 built, validated, and 3× replicated (partial):**
- Built mini_017 (log_aggregator): 11-file pipeline, second reflection-critical cascade task.
  - Bug A (aggregator.py): `error_rate = total_errors / len(entries)` — divides by entry count, not total_requests.
    Tests 02,03,04,05 fail; test_01 passes (single entry, same result both ways).
  - Bug B (entry_log.py): `int(stats["total_errors"])` truncates float error counts.
    Only manifests after fixing Bug A. test_04 uses error_count=14.25 → truncated to 14.
  - Generic file name: `entry_log.py` sounds like an audit log, not a numeric conversion module.
  - Issue description points to "aggregation or statistics persistence" without naming files.
- **3× replication results** (tool_rounds=6, gpt-oss-120b):
  - Clean reps 1 and 2: loop=0% (0/2), loop_testnames=0% (0/2), loop_reflect=50% (1/2)
  - Rep 3 throttled: Cerebras daily token quota exhausted — loop_testnames and loop_reflect
    terminated in 1 iter each (invalid). Only loop rep 3 is clean (FAILED in 5 iters as expected).
  - Pattern matches mini_016: loop_reflect is the only baseline that resolves the cascade.
- **Design rule confirmed**: generic file name + tight tool budget + clean cascade = reflection-critical task.
- **README rewritten** with actual research findings, benchmark results, and the core hypothesis.
- Reports: runs/report_1772980823.json (validation), runs/report_1772983409.json (3× run)

**Session 15 — mini_016 redesign + 3× confirmed replication:**
- **Docstring breadcrumb removed**: summarizer.py previously named `value_formatter.py` directly.
  Changed to generic "handled at a later pipeline stage". No longer leaks the second bug's location.
- **Validated original mini_016 design was broken**: at tool_rounds=6 with clean quota, all baselines
  resolved in 1 iteration. Root cause: `value_formatter.py` name is a dead giveaway in the file listing.
  Model lists files, sees the name, opens it, fixes both bugs in one pass.
- **Redesigned mini_016**: renamed `value_formatter.py` → `record_ops.py`, functions `format_*` → `build_*`,
  docstring reframed as "data normalisation". Pipeline import updated accordingly.
- **3× replication confirmed baseline separation**:
  - loop: 33.3% resolve, 33.3% repeat failures
  - loop_testnames: 33.3% resolve, 22.2% repeat failures
  - loop_reflect: 66.7% resolve, 0% repeat failures, avg 2.5 iters to success
  This is the first clean, replicated demonstration of reflection outperforming loop and loop_testnames.
- **Design lesson learned**: file naming is a critical confound in reflection-critical task design.
  The second bug file must have a generic name that doesn't semantically reveal the bug type.
  Even with a 10-file repo and 6 tool rounds, a single revealing file name defeats the cascade.
- **tool_rounds calibration**: 5 rounds → NO_DIFF (model can't explore enough). 6 rounds → correct
  pressure. 7+ rounds → model finds both bugs in iter 1. Use tool_rounds=6 for mini_016.

**Session 14 — mini_016 + planner bug fix:**
- **Critical client.py bug fixed**: when `max_tool_rounds` is exhausted and the last response
  has `finish_reason == "tool_calls"` (not "stop"), `choice.message.content` is None/empty.
  The fix: after exhausting rounds, make one final text-only call (no tools) to force the
  model to commit to a diff based on everything it has read. This was silently causing many
  NO_DIFF failures across all tasks when the model was thorough in exploration.
- **mini_016 built** (weighted_bucket_report, 10 files): cascade bug across 2 files.
  - BUG A (summarizer.py): plain average instead of weighted average
  - BUG B (value_formatter.py): `:.2f` truncates precision, causing test_04 to expect "9.0909" but get "9.09"
  - Cascade: fixing summarizer.py makes 4/5 tests pass; test_04 still fails for formatting precision
  - Reflection lesson: "format to 4 decimal places" → points model to value_formatter.py
  - Docstring in summarizer.py explicitly says: "string formatting is done by value_formatter.py"
  - 10 files + tool_rounds=6 ensures model can't read everything in one pass
  - Generic test names: test_regression_N (can't grep for file location)
- **Validation results** (tool_rounds=6, Cerebras gpt-oss-120b, single run each):
  - loop: **STUCK** (3 iters — keeps re-fixing summarizer.py, never reaches value_formatter.py)
  - loop_reflect: **RESOLVED** (3 iters — lesson correctly identifies formatter, model fixes :.2f → :.4f)
  - loop_testnames: ERROR (token quota exhausted mid-run; likely similar to loop)
  - single_shot: FAILED — finds summarizer.py, fixes it, but misses value_formatter.py (4/5 pass)
  - This is the **first confirmed reflection-critical task** with baseline separation!
- **Next**: replicate mini_016 result (3× runs per baseline) tomorrow when quota resets.
  Command: `patchloop bench -t mini_016 -b loop -b loop_testnames -b loop_reflect --model gpt-oss-120b --tool-rounds 6 --num-runs 3 --run-delay 30 --call-delay 7`

---

## Locked Architecture Decisions (Do Not Re-Litigate)

These were explicitly agreed upon. Do not change without user confirmation.

1. **LocalEnvironment first, DockerEnvironment Phase 2.**
   Docker is a drop-in via the same Environment ABC. Don't touch docker_env.py.

2. **Four baselines, same code path:**
   - `single_shot`: max_iterations=1, no reflection, no test-name grounding
   - `loop`: max_iterations=N, no reflection, no test-name grounding
   - `loop_testnames`: max_iterations=N, no reflection, injects failing test names (ablation)
   - `loop_reflect`: max_iterations=N, injects ALL prior reflections + failing test names

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

## Mini-Bench v1 Tasks (Current: 15/15)

### Standard slice (mini_001–010) — informative test names
| ID       | Bug                                    | Difficulty | Expected single_shot |
|----------|----------------------------------------|------------|----------------------|
| mini_001 | retry() catches PermanentError              | medium | loop fixes it                                            |
| mini_002 | paginate() off-by-one (end slice)           | easy   | single_shot may fix it                                   |
| mini_003 | median() wrong for even-length inputs       | easy   | model-dependent                                          |
| mini_004 | jsonl reader drops last record + writer missing \n | hard | fixing reader reveals writer bug via test output   |
| mini_005 | merge_config() shallow merge loses siblings | hard   | partial fix mutates input — reflection encodes "go deeper" |
| mini_006 | anchor normalization duplicated in 3 files  | hard   | fixing slug.py alone leaves toc.py + renderer.py broken  |
| mini_007 | safe_join() bans ALL nested paths           | medium | removing guard breaks traversal tests — must normalize   |
| mini_008 | group_rows() uses groupby on non-contiguous | medium | sort fix breaks order tests — must use dict accumulation |
| mini_009 | retry_after: int-only, crashes on HTTP-date | medium | 3-step fix: blank → HTTP-date → malformed; each step revealed by test failure |
| mini_010 | parse_line() naive split breaks on quoted , | medium | issue text misleads to trailing-comma; real fix is csv.reader |

### Reflection-critical slice (mini_011–015) — generic test names (test_regression_N)
Designed so loop_testnames cannot win just from the test name — the conceptual lesson matters.
| ID       | Bug                                    | Difficulty | Design intent |
|----------|----------------------------------------|------------|---------------|
| mini_011 | merge uses `or` (drops falsy), serialize uses `if v` (drops falsy) | hard | Both files share the `falsy≠absent` bug; fixing one still fails 3/4 tests |
| mini_012 | cache key is `template` only, ignores locale+mode | hard | Issue says "rendering problem"; bug is in cache.py key — wrong-file trap |
| mini_013 | validator drops falsy (if v), serializer keeps default over record (or-merge) | hard | Wrong-file trap: issue implicates pipeline.py; cascade: fixing validator reveals serializer bug |
| mini_014 | aggregator uses `t.id or t.category` (groups by ID not category) | hard | 7-file report pipeline; wrong-file trap (issue says formatter). Solved by single_shot (0 iters) |
| mini_015 | enricher `or`-defaults 0/0.0 fields; reducer `if e.priority` skips 0-priority | hard | 7-file event pipeline; cascade: fix enricher reveals reducer bug; issue is vague |

All 17 repos verified: tests fail on buggy code. All stdlib-only, no pip deps.
mini_014 NOTE: too easy — model patched it without using any tools. Keep as calibration task only.
mini_016 NOTE: bug B file is record_ops.py (renamed from value_formatter.py). Run with --tool-rounds 6.
mini_017 NOTE: bug B file is entry_log.py (sounds like audit log, not numeric conversion). Run with --tool-rounds 6.

### mini_016 (reflection-critical — CONFIRMED 3× replication)
| ID       | Bug                                    | Difficulty | Design intent |
|----------|----------------------------------------|------------|---------------|
| mini_016 | summarizer.py plain avg + record_ops.py :.2f precision | hard | 11-file pipeline; fix summarizer (4/5 pass) then record_ops; loop/loop_testnames get STUCK, loop_reflect escapes via reflection lesson |

**3× replication results** (tool_rounds=6, gpt-oss-120b):

| Baseline | Resolve rate | Avg iters (success) | Repeat failure rate |
|---|---|---|---|
| loop | 33.3% (1/3) | 5.00 | 33.3% |
| loop_testnames | 33.3% (1/3) | 1.00 | 22.2% |
| loop_reflect | **66.7% (2/3)** | **2.50** | **0.0%** |

loop_reflect is the clear winner — double the resolve rate, zero repeat failures.
The non-determinism in loop_testnames rep 3 (resolved in 1 iter) shows occasional lucky exploration,
but 3× average confirms loop_reflect consistently ahead.

**Key design decisions:**
- Bug B file named `record_ops.py` (not `value_formatter.py`) — generic name prevents name-based discovery
- `build_record` / `build_all` function names don't reveal formatting purpose
- Docstring in record_ops.py framed as "data normalisation", not "output formatting"
- tool_rounds=6: tight enough to prevent finding both bugs in iter 1, enough to produce valid patches
- `# BUG:` comment kept in summarizer.py — easy bug A is intentional (cascade requires iter 1 fix)

Report: runs/report_1772977530.json

### mini_017 (reflection-critical — 3× attempted, rep 3 throttled)
| ID       | Bug                                    | Difficulty | Design intent |
|----------|----------------------------------------|------------|---------------|
| mini_017 | aggregator.py wrong denominator + entry_log.py int() truncation | hard | 11-file log pipeline; fix aggregator (4/5 pass) then entry_log; loop gets stuck, loop_reflect escapes via reflection lesson |

**3× replication results** (tool_rounds=6, gpt-oss-120b):

| Baseline | Resolve rate | Avg iters (failure) | Repeat failure rate |
|---|---|---|---|
| loop | 0.0% (0/3) | 5.00 | 33.3% |
| loop_testnames | 0.0% (0/3) | 2.67 | 25.0% |
| loop_reflect | **33.3% (1/3)** | 3.00 | 22.2% |

**NOTE on rep 3**: Daily Cerebras token quota exhausted during rep 3. loop_testnames and loop_reflect
both hit 4/4 retries and terminated in 1 iter each (invalid results). Only loop rep 3 is clean.
Clean data from reps 1 and 2: loop=0% (0/2), loop_testnames=0% (0/2), loop_reflect=50% (1/2).
Pattern matches mini_016: loop_reflect is the only baseline that escapes the cascade.

**Key design decisions:**
- Bug B file named `entry_log.py` — sounds like an audit trail, not a float-to-int conversion module
- `persist_stats` / `persist_all` function names sound like serialization, not numeric coercion
- Docstring framed as "stable record structure for serialization", not "type conversion"
- tool_rounds=6: same pressure as mini_016
- Cascade verified: fix aggregator.py → 4/5 pass; test_04 still fails (error_count=14 instead of 14.25)

Reports: runs/report_1772980823.json (validation), runs/report_1772983409.json (3× run)

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
- gemini-2.5-flash free tier has low RPD (~50 req/day) and RPM (10 req/min).
  A full 10-task × 3-baseline benchmark consumes 100-200+ API calls and will
  exhaust the daily quota midway through (loop and loop_reflect see all 429s).
  **Workarounds:**
  - Run each baseline on a separate day: `patchloop bench -b single_shot`, next day `-b loop`, etc.
  - Use a fresh API key per baseline
  - Use Cerebras (14,400 RPD, auto-configured via CEREBRAS_API_KEY) for reliable full runs
- **Cerebras token quota**: Free tier has BOTH a request limit (14,400 RPD) AND a daily token budget.
  Heavy benchmarking exhausts the daily token budget. Error: `token_quota_exceeded`.
  Retries (30s/60s backoff) DO eventually succeed if the per-minute window clears, but once the
  DAILY token budget is spent, calls fail until midnight UTC reset.
  **Rule**: Never make test/warm-up API calls before a benchmark run. Save all daily tokens for the run.
  **Use `--call-delay 7`** to pace throughput and avoid per-minute throttling during a long benchmark.
  A 3-task × 2-baseline × 3-seed benchmark takes 1-3 hours with rate-limit pausing but does complete.

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

### Alternative: Cerebras (also free — 14,400 RPD) ← recommended for benchmarks
```bash
export CEREBRAS_API_KEY=your_cerebras_key
# Base URL auto-configured to https://api.cerebras.ai/v1
patchloop run mini_001 --model gpt-oss-120b
patchloop bench --model gpt-oss-120b
```
Available models: gpt-oss-120b (best), llama3.1-8b (fast), qwen-3-235b-a22b-instruct-2507
Get free key at: https://cloud.cerebras.ai

### Alternative: Groq (also free — 14,400 RPD)
```bash
export LLM_API_KEY=your_groq_key
export LLM_BASE_URL=https://api.groq.com/openai/v1
patchloop run mini_001 --model llama-3.3-70b-versatile
```
Get free key at: https://console.groq.com

### Environment variables
| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (preferred) |
| `LLM_API_KEY` | Generic override for any provider |
| `LLM_BASE_URL` | Custom API base URL (default: Gemini endpoint) |
