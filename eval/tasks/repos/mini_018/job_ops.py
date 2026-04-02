def build_record(worker_id: str, rate: float) -> dict:
    """
    Assemble the final output record for a worker group.

    The throughput rate is stored as a two-decimal-precision value,
    rounded for consistent reporting across worker configurations.
    """
    return {
        "worker_id": worker_id,
        "rate": int(rate * 100) / 100,
    }


def build_all(aggregated: list[dict]) -> list[dict]:
    return [build_record(item["worker_id"], item["rate"]) for item in aggregated]
