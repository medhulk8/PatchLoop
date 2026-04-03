from dataclasses import dataclass


@dataclass
class InvoiceRecord:
    invoice_id: str
    disputed_amount: float
    invoice_value: float
    quantity: int
