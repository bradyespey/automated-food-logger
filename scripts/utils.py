# scripts/utils.py

import logging
import os
from selenium.webdriver.common.by import By
import time
import re
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs if needed
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "utils.log"))
    ]
)
logger = logging.getLogger(__name__)

# Parse food items from log text (original logic, just adding log_water)
def parse_food_items(log_text, log_water=True):
    food_items = []
    current_food = {}
    for line in log_text.strip().splitlines():
        line = line.strip()
        if not line:
            if current_food:
                current_food['log_water'] = log_water
                # Extract fluid_ounces if serving size includes fluid ounces
                serving_size = current_food.get('Serving Size', '').lower()
                if 'fluid ounce' in serving_size:
                    fluid_oz_matches = re.findall(r"(\d+\.?\d*)\s*fluid ounce", serving_size)
                    if fluid_oz_matches:
                        total_fluid_oz = sum(float(m) for m in fluid_oz_matches)
                        current_food['fluid_ounces'] = total_fluid_oz
                food_items.append(current_food)
                current_food = {}
            continue
        if ': ' in line:
            key, value = line.split(': ', 1)
            current_food[key.strip()] = value.strip()

    if current_food:
        current_food['log_water'] = log_water
        serving_size = current_food.get('Serving Size', '').lower()
        if 'fluid ounce' in serving_size:
            fluid_oz_matches = re.findall(r"(\d+\.?\d*)\s*fluid ounce", serving_size)
            if fluid_oz_matches:
                total_fluid_oz = sum(float(m) for m in fluid_oz_matches)
                current_food['fluid_ounces'] = total_fluid_oz
        food_items.append(current_food)
    return food_items

# Compare numeric values and return HTML-formatted result
def compare_numeric_values(field_name, input_value, logged_value):
    try:
        input_num = float(input_value)
        logged_num = float(logged_value)
        if abs(input_num - logged_num) < 1e-6:
            logger.info(f"{field_name}: Match found ({logged_num})")
            return f'<span style="color: green;">**{field_name}:** {logged_num} (matches input value {input_num})</span><br>'
        else:
            logger.warning(f"{field_name}: Mismatch (input: {input_num}, logged: {logged_num})")
            return f'<span style="color: red;">**{field_name}:** {logged_num} (does not match input value {input_value})</span><br>'
    except ValueError:
        logger.error(f"Invalid numerical values for {field_name}: {input_value}, {logged_value}")
        return f'<span style="color: red;">**{field_name}:** Invalid numerical values for comparison</span><br>'

# Compare values (numeric or string) and return HTML-formatted result
def compare_values(field_name, input_value, logged_value):
    try:
        input_num = float(input_value)
        logged_num = float(logged_value)
        if abs(input_num - logged_num) < 1e-6:
            logger.info(f"{field_name}: Match found ({logged_num})")
            return f'<span style="color: green;">**{field_name}:** {logged_num} (matches input value)</span><br>'
        else:
            logger.warning(f"{field_name}: Mismatch (input: {input_num}, logged: {logged_num})")
            return f'<span style="color: red;">**{field_name}:** {logged_num} (does not match input value {input_value})</span><br>'
    except ValueError:
        # Fallback to string comparison
        if str(input_value).strip().lower() == str(logged_value).strip().lower():
            logger.info(f"{field_name}: String match found")
            return f'<span style="color: green;">**{field_name}:** {logged_value} (matches input value)</span><br>'
        else:
            logger.warning(f"{field_name}: String mismatch")
            return f'<span style="color: red;">**{field_name}:** {logged_value} (does not match input value {input_value})</span><br>'

# Compare lists of food items and generate HTML report
def compare_items(input_items, logged_items):
    comparison = ""
    for idx, input_item in enumerate(input_items, 1):
        comparison += f"<b>Verifying item {idx} of {len(input_items)}: {input_item.get('Food Name', '')}</b><br>"

        # Find matching logged item by Food Name
        logged_item = next((item for item in logged_items if item.get('Food Name', '').lower() == input_item.get('Food Name', '').lower()), None)
        if not logged_item:
            logger.error(f"Logged item not found for {input_item.get('Food Name', 'Unknown')}")
            comparison += f"<span style='color: red;'>Logged item not found for {input_item.get('Food Name', '')}</span><br><br>"
            continue

        fields = [
            "Date", "Meal", "Brand", "Calories", "Fat (g)", "Saturated Fat (g)",
            "Cholesterol (mg)", "Sodium (mg)", "Carbs (g)", "Fiber (g)",
            "Sugar (g)", "Protein (g)"
        ]

        for field in fields:
            comparison += compare_values(field, input_item.get(field, ''), logged_item.get(field, ''))

        # Compare fluid ounces if available
        input_fluid = input_item.get('fluid_ounces')
        logged_fluid = logged_item.get('fluid_ounces_added')
        if input_fluid and logged_fluid:
            comparison += compare_numeric_values("Fluid Ounces", input_fluid, logged_fluid)
        comparison += "<br>"

    # Compare total fluid ounces
    total_input_fluid = sum(float(item.get('fluid_ounces', 0.0)) for item in input_items if item.get('fluid_ounces'))
    total_logged_fluid = sum(float(item.get('fluid_ounces_added', 0.0)) for item in logged_items if item.get('fluid_ounces_added'))
    logger.info(f"Total fluid ounces - Input: {total_input_fluid}, Logged: {total_logged_fluid}")
    comparison += "<b style='color: #f9c74f;'>Total Fluid Ounces Comparison:</b><br>"
    comparison += compare_numeric_values("Total Fluid Ounces", total_input_fluid, total_logged_fluid)

    return comparison

# Close overlays or popups
def close_overlays(driver):
    try:
        overlay_selectors = [
            "//div[@role='button' and @title='Close']",
            "//button[contains(text(), 'Close')]",
            "//div[contains(@class, 'overlay')]//button[contains(text(), 'Close')]"
        ]
        for selector in overlay_selectors:
            buttons = driver.find_elements(By.XPATH, selector)
            for btn in buttons:
                try:
                    btn.click()
                    logger.info("Closed an overlay or popup.")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Failed to click overlay close button: {e}")
    except Exception as e:
        logger.error(f"Error while closing overlays: {e}")
