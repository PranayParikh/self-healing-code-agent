from target import get_last_n_items, is_within_budget

def test_get_last_n_items():
    assert get_last_n_items([1, 2, 3, 4, 5], 3) == [1, 2, 3]

def test_is_within_budget_under():
    assert is_within_budget(80, 100) == True

def test_is_within_budget_over():
    assert is_within_budget(120, 100) == False

def test_is_within_budget_exact():
    assert is_within_budget(100, 100) == True