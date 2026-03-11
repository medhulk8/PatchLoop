from loader import load_jobs
from validator import validate_records
from preprocessor import preprocess
from rate_calc import compute_rate
from aggregator import aggregate
from job_ops import build_all
from normalizer import normalize_output
from reporter import build_report


def run_pipeline(raw_records: list[dict]) -> list[dict]:
    """End-to-end throughput pipeline: raw record dicts -> formatted report."""
    validate_records(raw_records)
    jobs = load_jobs(raw_records)
    jobs = preprocess(jobs)
    rates = [compute_rate(j) for j in jobs]
    aggregated = aggregate(jobs, rates)
    records = build_all(aggregated)
    records = normalize_output(records)
    return build_report(records)
