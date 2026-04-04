# Task Taxonomy

All 20 tasks, categorized for analysis and experiment planning.

## Category Definitions

- **standard**: Informative test names, single bug, solvable without reflection
- **control**: Generic test names but too easy / pathological — unsuitable for reflection experiment
- **reflection-critical**: Generic test names + cascade bugs + generic Bug B filename + tight tool budget required

## Full Table

| task_id | domain | category | files | test names | bug mechanism | observed pattern |
|---|---|---|---|---|---|---|
| mini_001 | error handling | standard | 1 | informative | retry() catches PermanentError | solved by most baselines |
| mini_002 | pagination | standard | 1 | informative | paginate() off-by-one | easy |
| mini_003 | statistics | standard | 1 | informative | median() wrong for even-length | easy |
| mini_004 | file I/O | standard | 2 | informative | jsonl reader + writer cascade | hard |
| mini_005 | config | standard | 2 | informative | merge_config() shallow merge | hard |
| mini_006 | URL normalization | standard | 3 | informative | anchor normalization multi-file | hard |
| mini_007 | path safety | standard | 1 | informative | safe_join() over-restricts | medium |
| mini_008 | data grouping | standard | 1 | informative | group_rows() uses wrong groupby | medium |
| mini_009 | HTTP retry | standard | 1 | informative | retry_after int-only parse | medium |
| mini_010 | log parsing | standard | 1 | informative | parse_line() naive split | medium |
| mini_011 | config merge | control | 2 | generic | merge+serialize both drop falsy | too easy (gpt-oss-120b fixes in 1 shot) |
| mini_012 | caching | control | 2 | generic | cache key missing locale+mode | good calibration task, not reflection-critical |
| mini_013 | validation | control | 2 | generic | validator+serializer falsy cascade | too easy (single_shot solves) |
| mini_014 | aggregation | control | 2 | generic | aggregator wrong group key | too easy (0 tool calls needed) |
| mini_015 | event pipeline | control | 11 | generic | enricher+reducer 0-value cascade | PATHOLOGICAL — reflector generates anti-helpful lessons |
| mini_016 | report pipeline | reflection-critical | 11 | generic | summarizer wrong avg + record_ops.py precision | **CONFIRMED** loop_reflect=66.7%, loop=loop_testnames≤33.3% (3×) |
| mini_017 | log pipeline | reflection-critical | 11 | generic | aggregator wrong denominator + entry_log.py truncation | **CONFIRMED** loop_reflect=66.7%, loop=loop_testnames=0% (3×) |
| mini_018 | throughput pipeline | reflection-critical | 11 | generic | rate_calc wrong divisor + job_ops.py string precision | built, cascade verified, not yet benchmarked |
| mini_019 | inventory pipeline | reflection-critical | 11 | generic | shrink_calc wrong divisor + stock_log.py truncation | built, cascade verified, not yet benchmarked |
| mini_020 | score pipeline | reflection-critical | 11 | generic | score_calc wrong divisor + score_entry.py truncation | built, cascade verified, not yet benchmarked |

## Experiment Slices

### Slice A — Standard (mini_001–010)
Used to verify baselines work at all. Informative test names mean reflection signal is weaker here;
loop and loop_testnames can match or exceed loop_reflect.

### Slice B — Confirmed reflection-critical (mini_016, mini_017)
The core validated result. N=2, 3× replicated each. loop_reflect=66.7%, all others ≤33.3%.

### Slice C — New reflection-critical candidates (mini_018, mini_019, mini_020)
Same design as Slice B. If these replicate the pattern, the result is much harder to dismiss (N=5).
**Next action: run 4-baseline benchmark, tool_rounds=6, 3× each.**

### Slice D — Control (mini_011–015)
Disqualified tasks — too easy, or pathological for reflection. Useful for understanding failure modes
but not for the main experiment.

## Bug B Generic Filename Examples
Files whose names do NOT reveal the bug type (confirmed working):
- `record_ops.py` — sounds like data operations, not float formatting
- `entry_log.py` — sounds like audit log, not numeric coercion
- `job_ops.py` — sounds like job data ops, not string precision
- `stock_log.py` — sounds like inventory log, not truncation vs rounding
- `score_entry.py` — sounds like data entry, not integer division

## Key Design Invariants for Reflection-Critical Tasks
1. Bug B file name must NOT semantically reveal the bug type
2. Test names must be generic (`test_regression_N`) — model can't grep its way to the file
3. Cascade: fix Bug A → most tests pass; only test_04 fails → reveals Bug B
4. test_01 passes on buggy code (degenerate case where Bug A is invisible)
5. Issue description is vague — no file names, no explicit bug type
6. 11-file pipeline — enough surface area that exhaustive exploration takes > tool_rounds=6
