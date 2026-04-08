from models import MaintenanceRecord


def load_records(raw: list[dict]) -> list[MaintenanceRecord]:
    """Parse raw maintenance dicts into MaintenanceRecord instances."""
    return [
        MaintenanceRecord(
            site_id=str(r["site_id"]),
            downtime_minutes=float(r["downtime_minutes"]),
            scheduled_minutes=float(r["scheduled_minutes"]),
            machine_count=int(r.get("machine_count", 1)),
        )
        for r in raw
    ]
