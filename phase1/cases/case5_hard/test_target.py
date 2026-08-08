from target import calculate_average_with_outlier_removal, apply_discount

def test_average_excludes_outliers():
    assert calculate_average_with_outlier_removal([1, 2, 3, 100], 10) == 2.0

def test_average_all_under_threshold():
    assert calculate_average_with_outlier_removal([4, 6, 8], 10) == 6.0

def test_discount_percent_form():
    assert apply_discount(100, 20) == 80

def test_discount_decimal_form():
    assert apply_discount(50, 0.1) == 45