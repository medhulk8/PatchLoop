from models import WorkerJob


def compute_rate(job: WorkerJob) -> float:
    """
    Compute throughput rate: completed jobs per elapsed hour.

    The rate measures how many jobs a worker group processes per hour.
    Elapsed time in hours is the correct normalisation denominator for
    a per-hour throughput metric.
    """
    # BUG: divides by num_workers instead of elapsed_hours
    return job.completed_jobs / job.num_workers
