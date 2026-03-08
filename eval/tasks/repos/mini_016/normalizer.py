from models import Record

_UNIT_SCALE = {
    "cents": 0.01,
    "usd": 1.0,
    "thousands": 1000.0,
}


def normalize_records(records: list[Record], unit: str = "usd") -> list[Record]:
    """
    Normalize monetary amounts to a canonical unit.

    Most datasets arrive in 'usd' (no conversion needed).
    Legacy datasets may arrive in 'cents' or 'thousands' and require scaling.
    The unit is specified per-batch, not per-record.
    """
    scale = _UNIT_SCALE.get(unit, 1.0)
    if scale == 1.0:
        return records
    return [
        Record(id=r.id, category=r.category, amount=r.amount * scale, weight=r.weight)
        for r in records
    ]
