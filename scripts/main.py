# scripts/main.py

import os
import time
import logging
from datetime import date, datetime
from dotenv import load_dotenv

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

load_dotenv()

LOSEIT_EMAIL = os.getenv('LOSEIT_EMAIL')
LOSEIT_PASSWORD = os.getenv('LOSEIT_PASSWORD')
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'False').lower() == 'true'

from scripts.login import initialize_driver, login, verify_login
from scripts.navigation import (
    parse_food_item_date,
    navigate_to_date,
    close_overlays,
    select_search_box,
    enter_placeholder_text,
    click_create_custom_food
)
from scripts.food_entry import enter_food_details, save_food
from scripts.water_intake import update_water_intake
from scripts.utils import parse_food_items, compare_items, logger


def main(log_text):
    """
    Processes the provided food log text, logs each food item, updates water intake,
    and performs a comparison check.

    Args:
        log_text (str): The raw food log text to be processed.

    Returns:
        str: An HTML-formatted string summarizing the logging and comparison results.
    """
    logger.info("Script started.")
    driver = initialize_driver(headless=HEADLESS_MODE)
    output_messages = []
    start_time = datetime.now()

    try:
        if not login(driver, LOSEIT_EMAIL, LOSEIT_PASSWORD):
            output_messages.append("<span style='color: red;'>Login failed.</span>")
            return "<br>".join(output_messages)

        if not verify_login(driver):
            output_messages.append("<span style='color: red;'>Login verification failed.</span>")
            return "<br>".join(output_messages)

        food_items = parse_food_items(log_text)
        num_items = len(food_items)
        logger.info(f"Parsed {num_items} food items.")

        if not food_items:
            output_messages.append("No food items to process.")
            return "<br>".join(output_messages)

        logged_items = []
        for idx, food_item in enumerate(food_items, 1):
            output_messages.append(f"<b style='color: #f9c74f;'>Logging item {idx} of {num_items}: {food_item.get('Food Name', 'Unknown')}</b>")

            # Attempt once
            success = attempt_food_logging(driver, food_item)
            if not success:
                # Refresh and try again from scratch
                logger.info("Attempting a page refresh and retrying the entire process for this food item.")
                driver.refresh()
                time.sleep(3)  # Wait for page load
                success = attempt_food_logging(driver, food_item)
                if not success:
                    output_messages.append("<span style='color: red;'>Failed to log this food item after refresh. Skipping.</span>")
                    continue

            # If we reach here, success is True
            # We've updated food_item in attempt_food_logging (including fluid_ounces_added)
            logged_items.append(food_item)
            output_messages.append("Logged nutritional values")

        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        output_messages.append(f"<br>Time to Log: {time_taken:.2f} seconds")

        # Perform comparison using old logic
        # We have food_items (input), logged_items (output)
        # This will give a stable immediate comparison
        comparison_output = compare_items(food_items, logged_items)
        output_messages.append("<br><b style='color: #f9c74f;'>Comparison Check:</b><br>" + comparison_output)

        return "<br>".join(output_messages)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"

    finally:
        driver.quit()
        logger.info("WebDriver closed.")


def attempt_food_logging(driver, food_item):
    """
    Attempts to log a single food item from scratch:
    1. Navigate to the target date.
    2. Select search box.
    3. Enter placeholder text.
    4. Click 'Create a custom food'.
    5. Enter food details and save.

    Args:
        driver (webdriver): The Selenium WebDriver instance.
        food_item (dict): A dictionary containing food item details.

    Returns:
        bool: True if successful, False otherwise.
    """
    date_str = food_item.get("Date")
    if not date_str:
        logger.error("Date is missing for a food item.")
        return False
    target_date = parse_food_item_date(date_str)
    if not target_date:
        logger.error(f"Invalid date: {date_str}")
        return False

    # Step 1: Navigate to the target date
    if not navigate_to_date(driver, target_date):
        logger.error(f"Failed to navigate to {target_date}.")
        return False

    # Step 2: Select search box for the meal
    meal_name = food_item.get("Meal", "Dinner")
    search_input = select_search_box(driver, meal_name)
    if not search_input:
        logger.error(f"Failed to locate search box for {meal_name}.")
        return False

    # Step 3: Enter placeholder text
    placeholder_text = "t3stf00dd03sn0t3xist"
    if not enter_placeholder_text(driver, search_input, placeholder_text):
        logger.error("Failed to enter placeholder text.")
        return False

    # Step 4: Click 'Create a custom food'
    if not click_create_custom_food(driver):
        logger.error("Failed to click 'Create a custom food' button.")
        return False

    # Step 5: Enter food details and save
    if not enter_food_details(driver, food_item):
        logger.error("Failed to enter food details.")
        return False

    if not save_food(driver):
        logger.error("Failed to save the food.")
        return False

    # Close overlays
    close_overlays(driver)

    # Update water intake if applicable
    serving_size = food_item.get("Serving Size", "").lower()
    if "fluid ounce" in serving_size:
        try:
            days_difference_calculation = (target_date - date.today()).days
            new_water_intake = update_water_intake(driver, food_item, days_difference_calculation)
            if new_water_intake is None:
                logger.error(f"Failed to update water intake for {food_item.get('Food Name', 'Unknown')}.")
                food_item['fluid_ounces_added'] = 0.0
            else:
                # Assuming fluid_ounces was parsed from food_item['fluid_ounces']
                fluid_oz = float(food_item.get('fluid_ounces', 0.0))
                food_item['fluid_ounces_added'] = fluid_oz
        except Exception as e:
            logger.error(f"Error updating water intake: {e}")
            food_item['fluid_ounces_added'] = 0.0
    else:
        logger.info(f"No fluid ounces found for: {food_item.get('Food Name', 'Unknown')}. Skipping water intake.")
        food_item['fluid_ounces_added'] = 0.0

    logger.info(f"Successfully logged food item: {food_item.get('Food Name', 'Unknown')}")
    return True
