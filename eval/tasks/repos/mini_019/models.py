from dataclasses import dataclass


@dataclass
class StockItem:
    item_id: str
    opening_stock: float
    closing_stock: float
    category: str


@dataclass
class ShrinkageRecord:
    item_id: str
    category: str
    shrinkage_pct: float  # shrinkage expressed as a percentage (0-100)
