from target import calculate_total_price

def test_total_price_basic():
    assert calculate_total_price(10, 3) == 30

def test_total_price_zero_quantity():
    assert calculate_total_price(10, 0) == 0

