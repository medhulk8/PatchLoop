from models import WorkerJob


def preprocess(jobs: list[WorkerJob]) -> list[WorkerJob]:
    """Sort jobs by worker_id for deterministic output ordering."""
    return sorted(jobs, key=lambda j: j.worker_id)
