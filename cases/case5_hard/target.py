def calculate_average_with_outlier_removal(numbers, threshold):
    filtered = [n for n in numbers if n < threshold]
    total = sum(numbers)
    return total / len(filtered)


def apply_discount(price, discount_percent):
    if discount_percent > 1:
        discount_percent = discount_percent / 100
    return price - discount_percent