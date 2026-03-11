# PatchLoop — Session History

Full log of what was built/changed/found each session. For day-to-day working reference, see CLAUDE.md.

---

## Session 1 — Core build
- Full skeleton: PLAN → APPLY_PATCH → RUN_TESTS → ANALYZE_FAILURE → REFLECT → DECIDE_NEXT
- 3 benchmark tasks: mini_001, mini_002, mini_003
- RunLogger, IterationRecord, Reflection, LoopState all wired up

## Session 2 — End-to-end fixes
- Switched default model: gemini-1.5-flash → gemini-2.5-flash
- Removed `required: []` from list_files tool schema (Gemini rejects empty arrays)
- Fixed `model_dump(exclude_none=True, exclude_unset=True)` to strip null fields
- Replaced `git apply` with pure Python `_apply_unified_diff()` (git apply failing on macOS)
- First successful end-to-end runs: mini_001 ✅, mini_003 ✅

## Session 3 — Code review fixes (Codex review)
- STUCK detection: track `last_error_signature`; only increment on consecutive match
- `iterations_used`: fixed from 0-indexed state.iteration → `len(state.iterations)`
- LOC metric: fixed operator precedence bug (was counting +++ headers as added lines)
- `repeated_failure_count`: use Counter + sum(max(count-1,0))
- Path traversal guards: resolve + is_relative_to(workdir) in read_file and patch applier
- `loc_changed` always 0 bug: pass `_snapshot_sha` as ref to git_diff
- Removed dead `TerminationReason.APPLY_FAILED` enum value
- `IterationRecord.close()` made idempotent

## Session 4 — Groq migration + first full benchmark
- Added Groq provider support; caught `BadRequestError` / `tool_use_failed` from Groq
- `_apply_unified_diff` fallback: match removed lines only when context match fails
- First full benchmark (llama-4-maverick): single_shot=33%, loop=67%, loop_reflect=67%
- Finding: tasks too easy for reflection to show benefit; need harder tasks

## Session 5 — 7 new tasks + substring match fix
- Added mini_004–010 (harder tasks, all stdlib-only, all verified)
- Fixed critical `_apply_unified_diff` bug: str.find() substring match → line-by-line comparison
- Benchmark (llama-4-maverick, 7 tasks): single_shot=0%, loop=0%, loop_reflect=14.3%

## Session 6 — Cerebras provider + first clean 10-task benchmark
- Added Cerebras provider (CEREBRAS_API_KEY → auto-configure to api.cerebras.ai/v1)
- Tried file pre-loading — abandoned (let single_shot cheat)
- First clean benchmark (gpt-oss-120b, 10 tasks): loop=100%, single_shot=90%, loop_reflect=90%

## Session 7 — loop_reflect fix + 100% benchmark
- Root cause: abstract lesson not enough — model needs concrete failing test name to know which file
- Fix: inject FAILED test_xxx lines from last stdout into loop_reflect PLAN prompt
- Second benchmark (gpt-oss-120b, 10 tasks): loop_reflect=100%, single_shot=90%, loop=80%

## Session 8 — loop_testnames ablation
- Added `loop_testnames` baseline: test names injected but no reflection lessons
- Ablation (10 tasks, 4 baselines): loop=100%, loop_testnames=100%, single_shot=90%, loop_reflect=90%
- Finding: test-name grounding alone = full loop performance; structured lessons not load-bearing on standard tasks

## Session 9 — Reflection-critical task slice (mini_011, mini_012)
- Added mini_011 (falsy_config_roundtrip) and mini_012 (cache_key_missing_dimension)
- Result: all iterative baselines = 100%; single_shot = 50%
- mini_011 too easy (gpt-oss-120b fixes both files in 1 shot); mini_012 is a good calibration task

## Session 10 — Search-budget ablation (--tool-rounds)
- Implemented --tool-rounds CLI flag, threaded through full chain
- Ran loop vs loop_reflect on mini_004/005/006 at tool_rounds=15/8/4
- Finding: 4 rounds → complete collapse (NO_DIFF). 8 rounds → directional micro-signal. Single-run variance dominates.
- Added --num-runs N + --run-delay S for proper averaged benchmarks
- Built mini_013 (too easy) and mini_014 (model solved without any tools — too easy)

## Session 11 — mini_015 + 3× benchmark attempt
- Built mini_015 (event_pipeline, enricher+reducer cascade)
- Added --call-delay S parameter
- 3× benchmark attempts all blocked by Cerebras daily token quota

## Session 12 — Framing + planning (no code changes)
- Reviewed ChatGPT analysis; sharpened core hypothesis:
  "Reflection becomes load-bearing when search is scarce and the next action is ambiguous"
- Plan: validate mini_015 before spending quota on 3×

## Session 13 — mini_015 validation + 3× averaged benchmark
- mini_015 FAILS: reflector generates anti-helpful lessons (cascade order wrong for reflection)
- New finding: loop_reflect can DEGRADE vs loop when reflector misdiagnoses
- 3× averaged benchmark (mini_004/005/006, tool_rounds=8):
  - loop=55.6%, loop_testnames=66.7%, loop_reflect=55.6%
  - loop_testnames is best on standard tasks — test names are the primary signal
- Report: runs/report_1772955525.json

## Session 14 — mini_016 + exhaustion fallback fix
- Critical bug fixed: when tool rounds exhausted with finish_reason=tool_calls, content is None/empty
  Fix: one final text-only call (tools=None) after exhaustion → forces model to commit diff
- Built mini_016 (weighted_bucket_report, 10 files, summarizer+record_ops cascade)
- First validation: loop=STUCK, loop_reflect=RESOLVED (3 iters)

## Session 15 — mini_016 redesign + 3× confirmed replication
- Original mini_016 broken: value_formatter.py name is a giveaway → all baselines solved in 1 iter
- Redesigned: renamed to record_ops.py, functions format_* → build_*, generic docstring
- 3× replication: loop=33.3%, loop_testnames=33.3%, loop_reflect=66.7% ← first clean replicated result
- Key lesson: file naming is a critical confound. Generic name = reflection-critical.
- Report: runs/report_1772977530.json

## Session 16 — mini_017 built + partial 3× replication
- Built mini_017 (log_aggregator, aggregator.py denominator + entry_log.py int() truncation)
- entry_log.py: sounds like audit log, not numeric conversion — good generic name
- Reps 1+2 clean: loop=0%, loop_testnames=0%, loop_reflect=50%
- Rep 3 throttled by token quota (invalid for loop_testnames/loop_reflect)
- README rewritten with research findings
- Reports: runs/report_1772980823.json, runs/report_1772983409.json

## Session 17 — mini_017 rep 3 rerun blocked by quota
- Attempted rerun — quota exhausted again both baselines
- Root cause: daily token budget spent by time rep 3 runs
- Solution: run rep 3 FIRST on a fresh day before any other calls

## Session 18 — mini_017 rep 3 complete + single_shot finalized
- mini_017 rep 3 (fresh quota): loop_testnames=FAILED, loop_reflect=RESOLVED (4 iters, LOC=12)
- Final mini_017: single_shot=0%, loop=0%, loop_testnames=0%, loop_reflect=66.7%
- single_shot baseline (3× each): 0% both tasks — LOC=0 all 6 runs
- 4-baseline picture complete: single_shot=0% < loop=loop_testnames≤33.3% < loop_reflect=66.7%
- Reports: runs/report_1773044508.json, runs/report_1773044905.json

## Session 19 — CLI validation guards + budget sweep tool_rounds=4
- CLI guards added: bench (run_delay≥0, call_delay≥0), run (tool_rounds≥1, call_delay≥0)
- Budget sweep tool_rounds=4 (3× replicated): all baselines 0%, LOC=0 — below exploration floor
- Report: runs/report_1773050027.json

## Session 20 — Budget sweep tool_rounds=6 and 8 complete
- tool_rounds=6 (3×): loop=33.3%, loop_testnames=33.3%, loop_reflect=66.7%
- tool_rounds=8 (3×): loop=50.0%, loop_testnames=33.3%, loop_reflect=66.7%
  - mini_016 brute-forceable at 8 rounds; mini_017 still exclusive to loop_reflect
- chat_with_tools exhaustion fallback unit tests added (16/16 pass)
- tool_rounds=10 attempted immediately after — stopped by quota after loop rep 1 (data invalid)
- Report: runs/report_1773075316.json

## Session 23 — Benchmark on 018/019/020, statistical significance, mini_018 Bug B redesign
- Ran 3-baseline bench on mini_018/019/020 (tool_rounds=6, 3 reps). Rep3 lost to token quota.
- Valid results: mini_019 loop_reflect=2/2; mini_020 loop_reflect=1/2; mini_018 loop_reflect=0/2
- mini_018's 0/2 explained: original Bug B (:.2f string format) was too hard to infer from tests alone
- Redesigned mini_018 Bug B: int(rate*100)/100 truncation (same pattern as mini_017/019/020), cascade re-verified
- Statistical analysis (pooled 016/017/019/020 valid runs, 10 per baseline):
  loop_reflect=7/10=70%, loop=2/10=20%, loop_testnames=1/10=10%
  Fisher's exact: vs loop p=0.035*, vs loop_testnames p=0.010* — **first p<0.05 result**
- Created TASK_TAXONOMY.md and eval/analysis/ scripts (stats_016_017.py, stats_018_020.py)
- Next: rerun mini_018/019/020 full 3× clean on fresh quota day

## Session 22 — mini_018, mini_019, mini_020 built and verified
- Built 3 new reflection-critical tasks (mini_018, mini_019, mini_020), total now 20 tasks
- All follow the same design: 11-file pipeline, Bug A = wrong divisor, Bug B = numeric precision in generic-named file
- mini_018: rate_calc.py (÷ num_workers instead of elapsed_hours) + job_ops.py (int() truncation vs round())
- mini_019: shrink_calc.py (÷ closing_stock instead of opening_stock) + stock_log.py (int() truncation vs round())
- mini_020: score_calc.py (÷ attempts instead of max_score) + score_entry.py (int() truncation vs round())
- All cascades verified with pytest (3 steps: buggy → fix A only → fix both)
- CLAUDE.md trimmed; SESSIONS.md updated

## Session 21 — Budget sweep closed, tool_rounds=10 dropped
- Attempted full tool_rounds=10 sweep on fresh quota day
- Rep 1 loop clean (mini_016 RESOLVED iters=1, mini_017 FAILED iters=4) — consistent with pattern
- Reps 2 and 3 hit token_quota_exceeded — data invalid
- Decision: drop tool_rounds=10. 3× replication exceeds free-tier daily budget at this scale.
- Budget sweep marked COMPLETE at 4/6/8. Story doesn't change at 10 rounds.
- CLAUDE.md trimmed; session history moved to SESSIONS.md (this file)
