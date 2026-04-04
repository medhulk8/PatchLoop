def persist_stats(stats: dict) -> dict:
    """
    Prepare a statistics record for downstream consumption.

    Converts the aggregate statistics into a stable record structure
    with normalised field types suitable for serialization and reporting.
    """
    return {
        "total_requests": stats["total_requests"],
        "total_window": stats["total_window"],
        "error_count": int(stats["total_errors"]),
        "error_rate": stats["error_rate"],
    }


def persist_all(aggregates: dict[str, dict]) -> dict[str, dict]:
    return {service: persist_stats(agg) for service, agg in aggregates.items()}
