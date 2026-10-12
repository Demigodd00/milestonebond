"""A limited public CI smoke test; semantic review remains necessary."""

from order_service import create_order


def main():
    first = create_order("A")
    assert first["key"] == "A"
    assert isinstance(first["sequence"], int)


if __name__ == "__main__":
    main()
