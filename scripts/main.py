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
from scripts.utils import parse_food_items, compare_items
from scripts.fetch_logged_items import fetch_logged_items
from scripts.logging_setup import get_logger

logger = get_logger("main")

def attempt_food_logging(driver, food_item):
    """
    Attempts to log a single food item from scratch:
    1. Navigate to the target date.
    2. Select search box.
    3. Enter placeholder text.
    4. Click 'Create a custom food'.
    5. Enter food details and save.

    Returns True if successful, False otherwise.
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
            else:
                logger.debug(f"Updated water intake successfully to {new_water_intake} oz.")
        except Exception as e:
            logger.error(f"Error updating water intake: {e}")
    else:
        logger.info(f"No fluid ounces found for: {food_item.get('Food Name', 'Unknown')}. Skipping water intake.")

    logger.info(f"Successfully logged food item: {food_item.get('Food Name', 'Unknown')}")
    return True

def main(log_text):
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

        processed_dates = set()
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
                # Try again from scratch
                success = attempt_food_logging(driver, food_item)
                if not success:
                    # Give up on this food item
                    output_messages.append("<span style='color: red;'>Failed to log this food item after refresh. Skipping.</span>")
                    continue

            # If we reach here, success is True
            date_str = food_item.get("Date")
            if date_str:
                target_date = parse_food_item_date(date_str)
                if target_date:
                    processed_dates.add(target_date)
            output_messages.append("Logged nutritional values")

        # Fetch logged items for comparison
        for proc_date in processed_dates:
            items = fetch_logged_items(driver, proc_date)
            if items:
                logged_items.extend(items)
            else:
                logger.warning(f"No logged items found for date {proc_date}.")
                output_messages.append(f"No logged items for {proc_date}.")

        # Perform comparison
        if logged_items:
            comparison_output = compare_items(food_items, logged_items)
            output_messages.append(f"<br><b style='color: #f9c74f;'>Comparison Check:</b><br>{comparison_output}")
        else:
            output_messages.append("<br><b style='color: red;'>No logged items found for comparison.</b>")

        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        output_messages.append(f"<br>Time to Log: {time_taken:.2f} seconds")

        logger.info("All food items processed successfully.")
        return "<br>".join(output_messages)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"

    finally:
        driver.quit()
        logger.info("WebDriver closed.")

if __name__ == "__main__":
    log_text = """Your sample food log text here."""
    output = main(log_text)
    print(output)
