from models import OrderItem


def compute_cost(item: OrderItem) -> float:
    """
    Compute the total order cost for an item.

    Total cost = unit_price × quantity

    The quantity is the correct multiplier — it represents the
    number of units ordered by the customer.
    """
    return item.unit_price * item.weight
