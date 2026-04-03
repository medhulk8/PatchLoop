from models import InvoiceRecord


def filter_invoices(invoices: list[InvoiceRecord]) -> list[InvoiceRecord]:
    """Exclude invoices with non-positive invoice values or negative disputed amounts."""
    return [i for i in invoices if i.invoice_value > 0 and i.disputed_amount >= 0]
