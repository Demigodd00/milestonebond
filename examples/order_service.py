"""Small public StudioNet fixture. The initial implementation is deliberately incomplete."""

orders = {}


def create_order(key):
    if not key:
        raise ValueError("key required")
    if key in orders:
        return orders[key]
    order = {"key": key, "sequence": len(orders) + 1}
    orders[key] = order
    return order
