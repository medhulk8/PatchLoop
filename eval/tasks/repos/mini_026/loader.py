from models import InvoiceRecord


def load_invoices(raw: list[dict]) -> list[InvoiceRecord]:
    """Parse raw invoice dicts into InvoiceRecord dataclass instances."""
    return [
        InvoiceRecord(
            invoice_id=str(r["invoice_id"]),
            disputed_amount=float(r["disputed_amount"]),
            invoice_value=float(r["invoice_value"]),
            quantity=int(r.get("quantity", 1)),
        )
        for r in raw
    ]
