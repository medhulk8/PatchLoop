from models import WorkerJob


def load_jobs(records: list[dict]) -> list[WorkerJob]:
    """Parse raw record dicts into WorkerJob dataclass instances."""
    return [
        WorkerJob(
            worker_id=str(r["worker_id"]),
            completed_jobs=int(r["completed_jobs"]),
            elapsed_hours=float(r["elapsed_hours"]),
            num_workers=int(r["num_workers"]),
        )
        for r in records
    ]
