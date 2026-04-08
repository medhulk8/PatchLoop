from dataclasses import dataclass


@dataclass
class MaintenanceRecord:
    site_id: str
    downtime_minutes: float
    scheduled_minutes: float
    machine_count: int
