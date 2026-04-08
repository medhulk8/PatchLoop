from models import MaintenanceRecord


def normalize_records(records: list[MaintenanceRecord]) -> list[MaintenanceRecord]:
    """Normalize minute values to stable decimal precision."""
    for r in records:
        r.downtime_minutes = round(r.downtime_minutes, 2)
        r.scheduled_minutes = round(r.scheduled_minutes, 2)
    return records
