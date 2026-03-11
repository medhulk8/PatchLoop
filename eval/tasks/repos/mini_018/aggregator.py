from models import WorkerJob


def aggregate(jobs: list[WorkerJob], rates: list[float]) -> list[dict]:
    """Pair each job record with its computed throughput rate."""
    return [
        {"worker_id": j.worker_id, "rate": r}
        for j, r in zip(jobs, rates)
    ]
