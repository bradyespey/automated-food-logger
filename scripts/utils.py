# scripts/utils.py
# Contains utility functions like parsing data and comparison functions.

import logging
import re

logger = logging.getLogger(__name__)

def parse_nutritional_data(content):
    """
    Parses the nutritional data from the log text.
    """
    parsed_items = []
    current_item = {}

    lines = content.splitlines()

    for line in lines:
        line = line.strip()
        if line.startswith("Food Name:"):
            if current_item:
                parsed_items.append(current_item)
            current_item = {"name": line.replace("Food Name:", "").strip()}
        elif line.startswith("Date:"):
            current_item["date"] = line.replace("Date:", "").strip()
        elif line.startswith("Meal:"):
            current_item["meal"] = line.replace("Meal:", "").strip()
        elif line.startswith("Brand:"):
            current_item["brand"] = line.replace("Brand:", "").strip()
        elif line.startswith("Icon:"):
            current_item["icon"] = line.replace("Icon:", "").strip()
        elif line.startswith("Serving Size:"):
            serving_size = re.sub(r"\s*\(.*?\)", "", line.replace("Serving Size:", "").strip())
            current_item["serving_quantity"] = serving_size

            # Extract fluid ounces if present
            fluid_oz_match = re.search(r"(\d+\.?\d*)\s*fluid ounces", serving_size.lower())
            if fluid_oz_match:
                current_item["fluid_ounces"] = float(fluid_oz_match.group(1))
            else:
                current_item["fluid_ounces"] = 0.0

        elif line.startswith("Calories:"):
            current_item["calories"] = line.replace("Calories:", "").strip()
        elif line.startswith("Fat (g):"):
            current_item["fat"] = line.replace("Fat (g):", "").strip()
        elif line.startswith("Saturated Fat (g):"):
            current_item["saturated_fat"] = line.replace("Saturated Fat (g):", "").strip()
        elif line.startswith("Cholesterol (mg):"):
            current_item["cholesterol"] = line.replace("Cholesterol (mg):", "").strip()
        elif line.startswith("Sodium (mg):"):
            current_item["sodium"] = line.replace("Sodium (mg):", "").strip()
        elif line.startswith("Carbs (g):"):
            current_item["carbs"] = line.replace("Carbs (g):", "").strip()
        elif line.startswith("Fiber (g):"):
            current_item["fiber"] = line.replace("Fiber (g):", "").strip()
        elif line.startswith("Sugar (g):"):
            current_item["sugar"] = line.replace("Sugar (g):", "").strip()
        elif line.startswith("Protein (g):"):
            current_item["protein"] = line.replace("Protein (g):", "").strip()

    if current_item:
        parsed_items.append(current_item)

    logger.info(f"Parsed {len(parsed_items)} food items from log.")
    return parsed_items

def compare_numeric_values(field_name, input_value, logged_value):
    """
    Compares numeric values and returns an HTML-formatted string indicating match status.
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
        if str(input_value).strip() == str(logged_value).strip():
            return f'<span style="color: green;">**{field_name}:** {logged_value} (matches input value)</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value} (does not match input value {input_value})</span><br>'

def compare_items(input_items, logged_items, content, total_input_fluid_ounces, total_logged_fluid_ounces):
    """
    Compares input items with logged items and returns an HTML-formatted comparison report.
    """
    total_food_names = content.count('Food Name:')
    if total_food_names == len(input_items):
        parsing_check = (
            "<b style='color: #f9c74f;'>Parsing Check:</b><br>"
            f"<span style='color: green;'>All {total_food_names} foods in input parsed correctly</span><br><br>"
        )
    else:
        parsing_check = (
            "<b style='color: #f9c74f;'>Parsing Check:</b><br>"
            f"<span style='color: red;'>Error: {total_food_names - len(input_items)} food items found in input but not parsed correctly.</span><br><br>"
        )

    comparison_check = "<b style='color: #f9c74f;'>Comparison Check:</b><br>"
    for index, (input_item, logged_item) in enumerate(zip(input_items, logged_items), 1):
        comparison_check += compare_values("name", input_item['name'], logged_item.get('name', ''))
        comparison_check += compare_values("date", input_item.get('date', ''), logged_item.get('date', ''))
        comparison_check += compare_values("meal", input_item.get('meal', ''), logged_item.get('meal', ''))
        comparison_check += compare_values("brand", input_item.get('brand', ''), logged_item.get('brand', ''))
        comparison_check += compare_values("icon", input_item.get('icon', ''), logged_item.get('icon', ''))
        comparison_check += compare_values("serving_quantity", input_item.get('serving_quantity', ''), logged_item.get('serving_quantity', ''))
        comparison_check += compare_values("calories", input_item.get('calories', ''), logged_item.get('calories', ''))
        comparison_check += compare_values("fat", input_item.get('fat', ''), logged_item.get('fat', ''))
        comparison_check += compare_values("saturated_fat", input_item.get('saturated_fat', ''), logged_item.get('saturated_fat', ''))
        comparison_check += compare_values("cholesterol", input_item.get('cholesterol', ''), logged_item.get('cholesterol', ''))
        comparison_check += compare_values("sodium", input_item.get('sodium', ''), logged_item.get('sodium', ''))
        comparison_check += compare_values("carbs", input_item.get('carbs', ''), logged_item.get('carbs', ''))
        comparison_check += compare_values("fiber", input_item.get('fiber', ''), logged_item.get('fiber', ''))
        comparison_check += compare_values("sugar", input_item.get('sugar', ''), logged_item.get('sugar', ''))
        comparison_check += compare_values("protein", input_item.get('protein', ''), logged_item.get('protein', ''))
        comparison_check += "<br>"

        # Compare fluid ounces if present
        if input_item.get('fluid_ounces', 0.0) > 0.0:
            comparison_check += compare_numeric_values("fluid_ounces_logged", input_item['fluid_ounces'], logged_item.get('fluid_ounces_added', 0.0))
        comparison_check += "<br>"

    # Compare total fluid ounces
    comparison_check += "<b style='color: #f9c74f;'>Total Fluid Ounces Comparison:</b><br>"
    comparison_check += compare_numeric_values("Total Fluid Ounces", total_input_fluid_ounces, total_logged_fluid_ounces)

    return parsing_check + comparison_check