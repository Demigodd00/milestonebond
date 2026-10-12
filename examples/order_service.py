"""Small public StudioNet fixture. The initial implementation is deliberately incomplete."""

orders = {}


def create_order(key):
    return {"key": key, "sequence": len(orders) + 1}
