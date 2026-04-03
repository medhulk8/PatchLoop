from dataclasses import dataclass


@dataclass
class BatchRecord:
    batch_id: str
    defective_units: float
    total_units: float
    sample_size: int
