from models import MaintenanceRecord


def filter_records(records: list[MaintenanceRecord]) -> list[MaintenanceRecord]:
    """Exclude rows with invalid scheduled time or negative downtime."""
    return [r for r in records if r.scheduled_minutes > 0 and r.downtime_minutes >= 0]
