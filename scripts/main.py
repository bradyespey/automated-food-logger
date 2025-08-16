# scripts/main.py

import os
import time
import logging
from datetime import date, datetime
from dotenv import load_dotenv

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

basedir = os.path.abspath(os.path.dirname(__file__))
# Try to load .env.development first, then fall back to .env
env_file = os.path.join(basedir, '..', '.env.development')
if not os.path.exists(env_file):
    env_file = os.path.join(basedir, '..', '.env')
load_dotenv(env_file)

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
    click_create_custom_food,
    goto_initial_position
)
from scripts.food_entry import enter_food_details, save_food
from scripts.water_intake import update_water_intake
from scripts.utils import parse_food_items, compare_items, logger

def main(log_text, log_water=True):
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

        food_items = parse_food_items(log_text, log_water=log_water)
        num_items = len(food_items)
        logger.info(f"Parsed {num_items} food items.")

        if not food_items:
            output_messages.append("No food items to process.")
            return "<br>".join(output_messages)

        logged_items = []
        for idx, food_item in enumerate(food_items, 1):
            output_messages.append(f"<b style='color: #f9c74f;'>Logging item {idx} of {num_items}: {food_item.get('Food Name', 'Unknown')}</b>")

            success = attempt_food_logging(driver, food_item)
            if not success:
                # Refresh and try again
                driver.refresh()
                time.sleep(3)
                success = attempt_food_logging(driver, food_item)
                if not success:
                    output_messages.append("<span style='color: red;'>Failed to log this food item after refresh. Skipping.</span>")
                    continue

            logged_items.append(food_item)
            output_messages.append("Logged nutritional values")

        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        output_messages.append(f"<br>Time to Log: {time_taken:.2f} seconds")

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
    date_str = food_item.get("Date")
    if not date_str:
        logger.error("Date is missing for a food item.")
        return False
    target_date = parse_food_item_date(date_str)
    if not target_date:
        logger.error(f"Invalid date: {date_str}")
        return False

    if not navigate_to_date(driver, target_date):
        logger.error(f"Failed to navigate to {target_date}.")
        return False

    # Always move cursor to the initial "Breakfast" position first
    goto_initial_position(driver)

    meal_name = food_item.get("Meal", "Dinner")
    search_input = select_search_box(driver, meal_name)
    if not search_input:
        logger.error(f"Failed to locate search box for {meal_name}.")
        return False

    placeholder_text = "pjzFqiRjygwY"
    if not enter_placeholder_text(driver, search_input, placeholder_text):
        logger.error("Failed to enter placeholder text.")
        return False

    if not click_create_custom_food(driver):
        logger.error("Failed to click 'Create a custom food' button.")
        return False

    if not enter_food_details(driver, food_item):
        logger.error("Failed to enter food details.")
        return False

    if not save_food(driver):
        logger.error("Failed to save the food.")
        return False

    close_overlays(driver)

    if food_item.get('fluid_ounces') and food_item.get('log_water', True):
        try:
            days_difference_calculation = (target_date - date.today()).days
            new_water_intake = update_water_intake(driver, food_item, days_difference_calculation)
            if new_water_intake is None:
                logger.error(f"Failed to update water intake for {food_item.get('Food Name', 'Unknown')}.")
                food_item['fluid_ounces_added'] = 0.0
            else:
                fluid_oz = float(food_item.get('fluid_ounces', 0.0))
                food_item['fluid_ounces_added'] = fluid_oz
        except Exception as e:
            logger.error(f"Error updating water intake: {e}")
            food_item['fluid_ounces_added'] = 0.0
    else:
        logger.info(f"No fluid ounces found or water logging disabled for: {food_item.get('Food Name', 'Unknown')}. Skipping water intake.")
        food_item['fluid_ounces_added'] = 0.0

    logger.info(f"Successfully logged food item: {food_item.get('Food Name', 'Unknown')}")
    return True
