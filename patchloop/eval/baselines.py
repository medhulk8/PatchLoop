from __future__ import annotations

import uuid
from pathlib import Path

from patchloop.agent.loop import AgentLoop
from patchloop.environment.local_env import LocalEnvironment
from patchloop.environment.task import Task
from patchloop.llm.client import LLMClient
from patchloop.observability.logger import RunLogger

BASELINES = ("single_shot", "loop", "loop_testnames", "loop_reflect")


def build_agent(
    task: Task,
    baseline: str,
    model: str,
    runs_dir: Path,
) -> tuple[AgentLoop, LocalEnvironment, RunLogger, str]:
    """
    Build an AgentLoop + Environment + Logger for the given task and baseline.

    run_id is generated here and shared between RunLogger and LoopState so
    log files and state objects are always correlated by the same identifier.

    Returns (loop, env, logger, run_id). The caller passes run_id into
    loop.run(run_id=...) so LoopState uses the same id as the log file.
    """
    if baseline not in BASELINES:
        raise ValueError(
            f"Unknown baseline '{baseline}'. Choose from: {', '.join(BASELINES)}"
        )

    run_id = uuid.uuid4().hex[:8]
    env = LocalEnvironment(task)
    llm = LLMClient(model=model)
    logger = RunLogger(run_id=run_id, task_id=task.task_id, runs_dir=runs_dir)
    loop = AgentLoop(task=task, env=env, llm=llm, logger=logger, baseline=baseline)

    return loop, env, logger, run_id
