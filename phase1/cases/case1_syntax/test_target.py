from target import divide_and_report

def test_integer_division_returns_float():
    assert divide_and_report(7, 2) == 3.5

def test_exact_division():
    assert divide_and_report(10, 2) == 5