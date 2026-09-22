from basic_test import SavingsAccount, BankAccount
from report import print_growth_report,print_report

name = "Pranay"
balance = 10000

sa1 = SavingsAccount(name, balance)

print(print_report(sa1))
print(print_growth_report(sa1))

