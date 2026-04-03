from models import InvoiceRecord


def expand_line_rows(invoices: list[InvoiceRecord]) -> list[dict]:
    """
    Expand each invoice record into one row per line item.

    For multi-line invoices the total disputed amount is divided evenly
    across individual line items so that per-line totals sum correctly
    in the downstream aggregation step.
    """
    rows = []
    for inv in invoices:
        item_value = inv.invoice_value / inv.quantity
        for _ in range(inv.quantity):
            rows.append({
                "invoice_id": inv.invoice_id,
                "disputed_amount": inv.disputed_amount,
                "invoice_value": item_value,
            })
    return rows
