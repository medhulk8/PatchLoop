from __future__ import annotations

import json
import time
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from patchloop.environment.task import Task, TaskResult
from patchloop.eval.baselines import BASELINES, build_agent
from patchloop.eval.metrics import compute_metrics, format_summary_table

console = Console()


class BenchmarkRunner:
    """
    Runs Mini-Bench v1: evaluates one or more baselines across a task set.

    Usage:
        runner = BenchmarkRunner(tasks_dir=..., runs_dir=..., model=...)
        results = runner.run(baselines=["single_shot", "loop", "loop_testnames", "loop_reflect"])
        runner.report(results)

    Each (task, baseline) pair is an independent run. Tasks are run
    sequentially to keep resource usage predictable.

    Output:
        runs/{run_id}/{task_id}.jsonl   <- per-run structured event log
        runs/report_{timestamp}.json    <- full results + metrics summary
    """

    def __init__(
        self,
        tasks_dir: Path,
        runs_dir: Path = Path("runs"),
        model: str = "gemini-2.5-flash",
        max_tool_rounds: int = 15,
        num_runs: int = 1,
        run_delay_s: int = 30,
        call_delay: float = 0.0,
        use_docker: bool = False,
    ) -> None:
        self.tasks_dir = tasks_dir
        self.runs_dir = runs_dir
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.num_runs = num_runs
        self.run_delay_s = run_delay_s
        self.call_delay = call_delay
        self.use_docker = use_docker
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Task loading
    # ------------------------------------------------------------------ #

    def load_tasks(self, task_ids: list[str] | None = None) -> list[Task]:
        """
        Load all tasks from the tasks directory.
        If task_ids is provided, only load those specific tasks.
        """
        yaml_files = sorted(self.tasks_dir.glob("*.yaml"))
        if not yaml_files:
            raise FileNotFoundError(
                f"No task YAML files found in {self.tasks_dir}"
            )

        tasks = []
        for yaml_file in yaml_files:
            task = Task.from_yaml(yaml_file)
            if task_ids is None or task.task_id in task_ids:
                tasks.append(task)

        if task_ids and len(tasks) < len(task_ids):
            found = {t.task_id for t in tasks}
            missing = set(task_ids) - found
            console.print(f"[yellow]Warning: tasks not found: {missing}[/yellow]")

        return tasks

    # ------------------------------------------------------------------ #
    # Main run
    # ------------------------------------------------------------------ #

    def run(
        self,
        baselines: list[str] | None = None,
        task_ids: list[str] | None = None,
    ) -> list[TaskResult]:
        """
        Run the benchmark.

        baselines: which baselines to evaluate. Defaults to all four.
        task_ids: subset of tasks to run. None = all tasks.

        If num_runs > 1, each (task, baseline) pair is run num_runs times
        and results are pooled for averaging. A delay of run_delay_s seconds
        is inserted between repetitions to avoid rate-limit bursts.
        """
        baselines = baselines or list(BASELINES)
        tasks = self.load_tasks(task_ids)

        runs_label = f" × {self.num_runs} repetitions" if self.num_runs > 1 else ""
        console.print(
            f"\n[bold]PatchLoop Benchmark[/bold] | "
            f"{len(tasks)} tasks × {len(baselines)} baselines{runs_label} "
            f"| model: {self.model}\n"
        )

        all_results: list[TaskResult] = []

        for rep in range(self.num_runs):
            if rep > 0:
                console.print(
                    f"\n[dim]Repetition {rep + 1}/{self.num_runs} — "
                    f"waiting {self.run_delay_s}s before next run...[/dim]"
                )
                time.sleep(self.run_delay_s)

            if self.num_runs > 1:
                console.rule(f"[bold]Repetition {rep + 1}/{self.num_runs}[/bold]")

            for baseline in baselines:
                console.rule(f"[bold blue]Baseline: {baseline}[/bold blue]")
                baseline_results = self._run_baseline(baseline, tasks)
                all_results.extend(baseline_results)

        return all_results

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #

    def report(self, results: list[TaskResult]) -> None:
        """Print the comparison table and write the JSON report to disk."""
        summary = compute_metrics(results)
        console.print("\n[bold]Results[/bold]\n")
        console.print(format_summary_table(summary))

        # Write full report to disk
        timestamp = int(time.time())
        report_path = self.runs_dir / f"report_{timestamp}.json"
        report_data = {
            "summary": summary,
            "results": [r.model_dump() for r in results],
        }
        report_path.write_text(
            json.dumps(report_data, indent=2), encoding="utf-8"
        )
        console.print(f"\n[dim]Full report written to: {report_path}[/dim]")

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _run_baseline(
        self, baseline: str, tasks: list[Task]
    ) -> list[TaskResult]:
        results: list[TaskResult] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            for task in tasks:
                task_label = progress.add_task(
                    f"  {task.task_id} ({task.difficulty})", total=None
                )

                result = self._run_single(task, baseline)
                results.append(result)

                status = "[green]RESOLVED[/green]" if result.resolved else "[red]FAILED[/red]"
                progress.update(
                    task_label,
                    description=(
                        f"  {task.task_id} {status} "
                        f"iters={result.iterations_used} "
                        f"t={result.total_duration_s:.0f}s"
                    ),
                    completed=True,
                )

        return results

    def _run_single(self, task: Task, baseline: str) -> TaskResult:
        """Run one (task, baseline) pair and return the result."""
        loop, env, logger, run_id = build_agent(
            task=task,
            baseline=baseline,
            model=self.model,
            runs_dir=self.runs_dir,
            max_tool_rounds=self.max_tool_rounds,
            call_delay=self.call_delay,
            use_docker=self.use_docker,
        )

        try:
            with env:
                _, result = loop.run(run_id=run_id)
        except Exception as e:
            result = TaskResult(
                task_id=task.task_id,
                run_id=run_id,
                baseline=baseline,
                model=self.model,
                tool_rounds=self.max_tool_rounds,
                resolved=False,
                iterations_used=0,
                total_duration_s=0.0,
                termination_reason="ERROR",
                error=str(e),
            )
        finally:
            logger.close()

        return result
