from models import InvoiceRecord


def normalize_invoices(invoices: list[InvoiceRecord]) -> list[InvoiceRecord]:
    """Round monetary values to cent precision for consistent downstream processing."""
    for i in invoices:
        i.disputed_amount = round(i.disputed_amount, 2)
        i.invoice_value = round(i.invoice_value, 2)
    return invoices
