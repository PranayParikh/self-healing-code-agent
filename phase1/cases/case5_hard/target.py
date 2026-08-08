def calculate_average_with_outlier_removal(numbers, threshold):
    filtered = [n for n in numbers if n < threshold]
    total = sum(filtered)  # Corrected to sum the filtered list
    return total / len(filtered) if filtered else 0  # Handle division by zero

def apply_discount(price, discount_percent):
    if discount_percent > 1:
        discount_percent = discount_percent / 100
    return price - (price * discount_percent)  # Corrected to apply discount as percentage