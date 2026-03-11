from models import StockItem


def compute_shrinkage(item: StockItem) -> float:
    """
    Compute inventory shrinkage as a fraction (0.0 to 1.0).

    Shrinkage is the proportion of opening stock that was lost:
        shrinkage = (opening - closing) / opening

    The opening stock is the correct denominator — it represents
    the baseline from which loss is measured.
    """
    lost = item.opening_stock - item.closing_stock
    # BUG: divides by closing_stock instead of opening_stock
    return lost / item.closing_stock
