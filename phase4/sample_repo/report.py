from basic_test import SavingsAccount, BankAccount

def print_report(account):
    return f"Account Holder : {account.name}\nAccount Balance : {account.principal}"

def print_growth_report(saving_account):
    return f"{saving_account.name}'s account grew by {saving_account.calculate_growth()}"

