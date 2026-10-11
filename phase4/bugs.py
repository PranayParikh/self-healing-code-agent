BUGS = [
    {"id": "report_principal", "type": "wrong_output", "edits": [
        ("report.py", "saving_account.calculate_growth()", "saving_account.principal")]},
    {"id": "report_attr", "type": "crash", "edits": [
        ("report.py", "{account.principal}", "{account.balance}")]},
    {"id": "report_syntax", "type": "syntax", "edits": [
        ("report.py", "calculate_growth()}\"", "calculate_growth()}")]},
    {"id": "base_minus", "type": "wrong_output", "edits": [
        ("basic_test.py", "self.principal + calculate_interest", "self.principal - calculate_interest")]},
    {"id": "base_formula", "type": "wrong_output", "edits": [
        ("basic_test.py", "principal * rate / 100", "principal + rate")]},
    {"id": "base_init", "type": "wrong_attribute", "edits": [
        ("basic_test.py", "self.principal = principal", "self.principal = name")]},
    {"id": "two_files", "type": "multi_file", "edits": [
        ("basic_test.py", "self.principal + calculate_interest", "self.principal - calculate_interest"),
        ("report.py", "{account.principal}", "{account.balance}")]},
]