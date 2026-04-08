from models import MaintenanceRecord


def expand_machine_rows(records: list[MaintenanceRecord]) -> list[dict]:
    """
    Expand each maintenance record into one row per affected machine.

    For multi-machine windows, total downtime and scheduled time are
    distributed evenly across the expanded machine rows so the downstream
    totals remain consistent.
    """
    rows = []
    for record in records:
        machine_minutes = record.scheduled_minutes / record.machine_count
        for _ in range(record.machine_count):
            rows.append(
                {
                    "site_id": record.site_id,
                    "downtime_minutes": record.downtime_minutes,
                    "scheduled_minutes": machine_minutes,
                }
            )
    return rows
