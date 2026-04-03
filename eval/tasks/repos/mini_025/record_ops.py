from models import BatchRecord


def expand_sample_rows(batches: list[BatchRecord]) -> list[dict]:
    """
    Expand each batch record into one row per sampled unit.

    For multi-unit samples the total defective count is divided evenly
    across individual units so that per-unit totals sum correctly in the
    downstream aggregation step.
    """
    rows = []
    for b in batches:
        unit_total = b.total_units / b.sample_size
        for _ in range(b.sample_size):
            rows.append({
                "batch_id": b.batch_id,
                "defective_units": b.defective_units,
                "total_units": unit_total,
            })
    return rows
