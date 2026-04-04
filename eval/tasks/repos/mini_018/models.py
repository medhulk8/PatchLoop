from dataclasses import dataclass


@dataclass
class WorkerJob:
    worker_id: str
    completed_jobs: int
    elapsed_hours: float
    num_workers: int


@dataclass
class ThroughputRecord:
    worker_id: str
    rate: str  # formatted throughput rate (jobs per hour)
