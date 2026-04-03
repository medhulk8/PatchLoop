from models import BatchRecord


def load_batches(raw: list[dict]) -> list[BatchRecord]:
    """Parse raw batch dicts into BatchRecord dataclass instances."""
    return [
        BatchRecord(
            batch_id=str(r["batch_id"]),
            defective_units=float(r["defective_units"]),
            total_units=float(r["total_units"]),
            sample_size=int(r.get("sample_size", 1)),
        )
        for r in raw
    ]
