from basic_test import SavingsAccount
from report import print_report, print_growth_report

def test_print_report():
    sa = SavingsAccount("Pranay", 10000)
    assert print_report(sa) == "Account Holder : Pranay\nAccount Balance : 10000"

def test_print_growth_report():
    sa = SavingsAccount("Pranay", 10000)
    assert print_growth_report(sa) == "Pranay's account grew by 10500.0"