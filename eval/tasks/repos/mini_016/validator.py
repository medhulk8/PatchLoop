from models import Record


def validate_records(records: list[Record]) -> list[Record]:
    """Remove records that fail basic validity checks."""
    valid = []
    for r in records:
        if r.weight <= 0:
            continue
        if r.amount is None:
            continue
        valid.append(r)
    return valid
