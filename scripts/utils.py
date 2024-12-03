# scripts/utils.py

import logging

logger = logging.getLogger(__name__)

def parse_food_items(log_text):
    """
    Parses the food items from the given log text.

    Args:
        log_text (str): The input text containing food items.

    Returns:
        list: A list of dictionaries, each representing a food item.
    """
    food_items = []
    current_food = {}
    for line in log_text.strip().splitlines():
        line = line.strip()
        if not line:
            if current_food:
                food_items.append(current_food)
                current_food = {}
            continue
        if ': ' in line:
            key, value = line.split(': ', 1)
            current_food[key.strip()] = value.strip()
    if current_food:
        food_items.append(current_food)
    return food_items

def compare_numeric_values(field_name, input_value, logged_value):
    """
    Compares numeric values and returns an HTML-formatted string indicating match status.

    Args:
        field_name (str): The name of the field being compared.
        input_value (str or float): The value from the input.
        logged_value (str or float): The value from the logged data.

    Returns:
        str: HTML-formatted comparison result.
    """
    try:
        input_value_num = float(input_value)
        logged_value_num = float(logged_value)
        if abs(input_value_num - logged_value_num) < 1e-6:
            return f'<span style="color: green;">**{field_name}:** {logged_value_num} (matches input value {input_value_num})</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value_num} (does not match input value {input_value_num})</span><br>'
    except ValueError:
        return f'<span style="color: red;">**{field_name}:** Invalid numerical values for comparison</span><br>'

def compare_values(field_name, input_value, logged_value):
    """
    Compares values (numeric or string) and returns an HTML-formatted string indicating match status.

    Args:
        field_name (str): The name of the field being compared.
        input_value (str or float): The value from the input.
        logged_value (str or float): The value from the logged data.

    Returns:
        str: HTML-formatted comparison result.
    """
    # Try to compare as floats first
    try:
        input_value_num = float(input_value)
        logged_value_num = float(logged_value)
        if abs(input_value_num - logged_value_num) < 1e-6:
            return f'<span style="color: green;">**{field_name}:** {logged_value_num} (matches input value)</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value_num} (does not match input value {input_value})</span><br>'
    except ValueError:
        # Fallback to string comparison
        if str(input_value).strip().lower() == str(logged_value).strip().lower():
            return f'<span style="color: green;">**{field_name}:** {logged_value} (matches input value)</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value} (does not match input value {input_value})</span><br>'

def compare_items(input_items, logged_items):
    """
    Compares input items with logged items and returns an HTML-formatted comparison report.

    Args:
        input_items (list): List of input food items.
        logged_items (list): List of logged food items.

    Returns:
        str: HTML-formatted comparison report.
    """
    comparison_check = ""
    for index, input_item in enumerate(input_items, 1):
        comparison_check += f"<b>Verifying item {index} of {len(input_items)}: {input_item.get('Food Name', '')}</b><br>"
        # Find matching logged item
        logged_item = next((item for item in logged_items if item.get('Food Name', '') == input_item.get('Food Name', '')), None)
        if not logged_item:
            comparison_check += f"<span style='color: red;'>Logged item not found for {input_item.get('Food Name', '')}</span><br><br>"
            continue

        fields_to_compare = [
            "Date", "Meal", "Brand", "Calories", "Fat (g)", "Saturated Fat (g)",
            "Cholesterol (mg)", "Sodium (mg)", "Carbs (g)", "Fiber (g)",
            "Sugar (g)", "Protein (g)"
        ]

        for field in fields_to_compare:
            comparison_check += compare_values(field, input_item.get(field, ''), logged_item.get(field, ''))

        # Compare fluid ounces if present
        input_fluid_ounces = input_item.get('fluid_ounces', None)
        logged_fluid_ounces = logged_item.get('fluid_ounces_added', None)
        if input_fluid_ounces is not None and logged_fluid_ounces is not None:
            comparison_check += compare_numeric_values("Fluid Ounces", input_fluid_ounces, logged_fluid_ounces)
        comparison_check += "<br>"

    # Compare total fluid ounces
    total_input_fluid_ounces = sum(float(item.get('fluid_ounces', 0.0)) for item in input_items if item.get('fluid_ounces') is not None)
    total_logged_fluid_ounces = sum(float(item.get('fluid_ounces_added', 0.0)) for item in logged_items if item.get('fluid_ounces_added') is not None)

    comparison_check += "<b style='color: #f9c74f;'>Total Fluid Ounces Comparison:</b><br>"
    comparison_check += compare_numeric_values("Total Fluid Ounces", total_input_fluid_ounces, total_logged_fluid_ounces)

    return comparison_check