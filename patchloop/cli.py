from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from patchloop.eval.baselines import BASELINES
from patchloop.eval.bench_runner import BenchmarkRunner

app = typer.Typer(
    name="patchloop",
    help="Benchmarkable self-improving coding agent.",
    add_completion=False,
)
console = Console()

_DEFAULT_TASKS_DIR = Path("eval/tasks")
_DEFAULT_RUNS_DIR = Path("runs")
_DEFAULT_MODEL = "gemini-2.5-flash"


@app.command()
def bench(
    baselines: Optional[list[str]] = typer.Option(
        None,
        "--baseline", "-b",
        help=f"Which baselines to run. Choices: {', '.join(BASELINES)}. "
             "Pass multiple times for multiple baselines. Default: all.",
    ),
    tasks: Optional[list[str]] = typer.Option(
        None,
        "--task", "-t",
        help="Specific task IDs to run. Default: all tasks in tasks-dir.",
    ),
    tasks_dir: Path = typer.Option(
        _DEFAULT_TASKS_DIR,
        "--tasks-dir",
        help="Directory containing task YAML files.",
    ),
    runs_dir: Path = typer.Option(
        _DEFAULT_RUNS_DIR,
        "--runs-dir",
        help="Directory for run logs and reports.",
    ),
    model: str = typer.Option(
        _DEFAULT_MODEL,
        "--model", "-m",
        help="Model to use for all LLM calls.",
    ),
    tool_rounds: int = typer.Option(
        15,
        "--tool-rounds",
        help="Max tool-use rounds per planning step (search budget). Default: 15.",
    ),
    num_runs: int = typer.Option(
        1,
        "--num-runs", "-n",
        help="Number of seeds per (task, baseline). Results are pooled for averaging. Default: 1.",
    ),
    run_delay: int = typer.Option(
        30,
        "--run-delay",
        help="Seconds to wait between repeated seeds (to avoid rate-limit bursts). Default: 30.",
    ),
    call_delay: float = typer.Option(
        0.0,
        "--call-delay",
        help="Seconds to sleep before each individual LLM API call (rate-limit pacing). "
             "Use ~7.0 for Cerebras free tier (10 RPM). Default: 0.",
    ),
    docker: bool = typer.Option(
        False,
        "--docker",
        help="Run tasks inside DockerEnvironment instead of LocalEnvironment.",
    ),
) -> None:
    """
    Run the full benchmark across tasks and baselines.

    Evaluates each (task, baseline) pair and prints a comparison table.
    Results and per-run JSONL logs are written to --runs-dir.

    Example:
        patchloop bench                            # all tasks, all baselines
        patchloop bench -b single_shot -b loop     # two baselines only
        patchloop bench -t mini_001 -t mini_002    # two specific tasks
        patchloop bench -m gemini-1.5-pro           # stronger model
        patchloop bench --tool-rounds 4            # constrained search budget
        patchloop bench --num-runs 3 --run-delay 60  # 3x averaged, 60s between seeds
        patchloop bench --call-delay 7             # pace calls for Cerebras 10 RPM limit
    """
    if num_runs < 1:
        raise typer.BadParameter("--num-runs must be >= 1", param_hint="'--num-runs'")
    if tool_rounds < 1:
        raise typer.BadParameter("--tool-rounds must be >= 1", param_hint="'--tool-rounds'")
    if run_delay < 0:
        raise typer.BadParameter("--run-delay must be >= 0", param_hint="'--run-delay'")
    if call_delay < 0:
        raise typer.BadParameter("--call-delay must be >= 0", param_hint="'--call-delay'")

    runner = BenchmarkRunner(
        tasks_dir=tasks_dir,
        runs_dir=runs_dir,
        model=model,
        max_tool_rounds=tool_rounds,
        num_runs=num_runs,
        run_delay_s=run_delay,
        call_delay=call_delay,
        use_docker=docker,
    )
    results = runner.run(
        baselines=list(baselines) if baselines else None,
        task_ids=list(tasks) if tasks else None,
    )
    runner.report(results)


@app.command()
def run(
    task_id: str = typer.Argument(..., help="Task ID to run (e.g. mini_001)."),
    baseline: str = typer.Option(
        "loop_reflect",
        "--baseline", "-b",
        help=f"Baseline to use. Choices: {', '.join(BASELINES)}",
    ),
    tasks_dir: Path = typer.Option(
        _DEFAULT_TASKS_DIR,
        "--tasks-dir",
    ),
    runs_dir: Path = typer.Option(
        _DEFAULT_RUNS_DIR,
        "--runs-dir",
    ),
    model: str = typer.Option(
        _DEFAULT_MODEL,
        "--model", "-m",
    ),
    tool_rounds: int = typer.Option(
        15,
        "--tool-rounds",
        help="Max tool-use rounds per planning step (search budget). Default: 15.",
    ),
    call_delay: float = typer.Option(
        0.0,
        "--call-delay",
        help="Seconds to sleep before each LLM API call (rate-limit pacing). Default: 0.",
    ),
    docker: bool = typer.Option(
        False,
        "--docker",
        help="Run task inside DockerEnvironment instead of LocalEnvironment.",
    ),
) -> None:
    """
    Run a single task with a single baseline. Useful for debugging.

    Example:
        patchloop run mini_001
        patchloop run mini_002 --baseline single_shot
        patchloop run mini_004 --tool-rounds 4
    """
    if tool_rounds < 1:
        raise typer.BadParameter("--tool-rounds must be >= 1", param_hint="'--tool-rounds'")
    if call_delay < 0:
        raise typer.BadParameter("--call-delay must be >= 0", param_hint="'--call-delay'")

    from patchloop.eval.baselines import build_agent
    from patchloop.environment.task import Task

    yaml_path = tasks_dir / f"{task_id}.yaml"
    if not yaml_path.exists():
        console.print(f"[red]Task file not found: {yaml_path}[/red]")
        raise typer.Exit(1)

    task = Task.from_yaml(yaml_path)
    loop, env, logger, run_id = build_agent(
        task=task,
        baseline=baseline,
        model=model,
        runs_dir=runs_dir,
        max_tool_rounds=tool_rounds,
        call_delay=call_delay,
        use_docker=docker,
    )

    console.print(
        f"\n[bold]Running[/bold] {task_id} | baseline={baseline} | "
        f"model={model} | run_id={run_id}\n"
    )

    try:
        with env:
            state, result = loop.run(run_id=run_id)
    finally:
        logger.close()

    status = "[green]RESOLVED[/green]" if result.resolved else "[red]FAILED[/red]"
    console.print(f"\nStatus:      {status}")
    console.print(f"Iterations:  {result.iterations_used}/{task.max_iterations}")
    console.print(f"Duration:    {result.total_duration_s:.1f}s")
    console.print(f"Terminated:  {result.termination_reason}")
    console.print(f"Log:         runs/{run_id}/{task_id}.jsonl")


if __name__ == "__main__":
    app()
