from dataclasses import dataclass, field


@dataclass
class Event:
    id: str
    category: str
    priority: int   # 0 = lowest, 10 = highest; 0 is a valid value
    value: float    # monetary value; 0.0 is a valid value
    tags: list = field(default_factory=list)
