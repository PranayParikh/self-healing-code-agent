import datetime
from math import floor

def calculate_interest(principal, rate):
    return principal*rate

class BankAccount():
    RATE = 0.05

    def __init__(self,name,principal):
        self.name = name
        self.principal = principal

class SavingsAccount(BankAccount):
    def calculate_growth(self):
        return self.principal+ calculate_interest(self.principal,self.RATE)

