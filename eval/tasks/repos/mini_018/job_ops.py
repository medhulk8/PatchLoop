def build_record(worker_id: str, rate: float) -> dict:
    """
    Assemble the final output record for a worker group.

    Encodes the throughput rate as a stable string representation
    suitable for downstream consumption and archival storage.
    """
    # BUG: formats to only 2 decimal places, losing precision for repeating decimals
    return {
        "worker_id": worker_id,
        "rate": f"{rate:.2f}",
    }


def build_all(aggregated: list[dict]) -> list[dict]:
    return [build_record(item["worker_id"], item["rate"]) for item in aggregated]
