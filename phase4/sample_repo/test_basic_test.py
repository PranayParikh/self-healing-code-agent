from basic_test import SavingsAccount, BankAccount

def test_calculate_growth():
    sa = SavingsAccount("Pranay", 10000)
    assert sa.calculate_growth() == 10500.0

def test_bank_account_attributes():
    ba = BankAccount("Test", 5000)
    assert ba.name == "Test"
    assert ba.principal == 5000