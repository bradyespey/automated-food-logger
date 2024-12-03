# main.py

import os
import time
import logging
from datetime import date, datetime
from dotenv import load_dotenv

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Load environment variables
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed logs
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "main.log"))
    ]
)
logger = logging.getLogger(__name__)

def main(log_text):
    """
    Main function to process food log input, log food items into Lose It!,
    and generate a comparison report.
    """
    logger.info("Script started.")
    driver = initialize_driver(headless=HEADLESS_MODE)

    output_messages = []  # Collect output messages to return
    start_time = datetime.now()

    try:
        # Step 1: Log in
        if not login(driver, LOSEIT_EMAIL, LOSEIT_PASSWORD):
            logger.error("Login failed. Exiting script.")
            output_messages.append("<span style='color: red;'>Login failed.</span>")
            driver.save_screenshot(os.path.join(LOG_DIR, "login_failed.png"))
            return "<br>".join(output_messages)

        # Step 2: Verify login
        if not verify_login(driver):
            logger.error("Login verification failed. Exiting script.")
            output_messages.append("<span style='color: red;'>Login verification failed.</span>")
            driver.save_screenshot(os.path.join(LOG_DIR, "login_verification_failed.png"))
            return "<br>".join(output_messages)

        # Parse food items from the log text
        food_items = parse_food_items(log_text)
        num_items = len(food_items)
        logger.info(f"Parsed {num_items} food items from the input.")

        if not food_items:
            logger.info("No food items to process.")
            output_messages.append("No food items to process.")
            return "<br>".join(output_messages)

        # Collect dates processed
        processed_dates = set()
        total_fluid_ounces_input = 0.0

        # Initialize water intake tracking
        water_intake_history = {}

        # Process each food item
        for idx, food_item in enumerate(food_items, 1):
            # Log the food_item structure for debugging
            logger.debug(f"Processing food item: {food_item}")

            # Logging output
            output_messages.append(f"<b style='color: #f9c74f;'>Logging item {idx} of {num_items}: {food_item.get('Food Name', 'Unknown')}</b>")

            # Parse the date
            date_str = food_item.get("Date")
            if not date_str:
                logger.error("Date is missing for a food item. Skipping.")
                output_messages.append("<span style='color: red;'>Date is missing for a food item. Skipping.</span>")
                continue
            target_date = parse_food_item_date(date_str)
            if not target_date:
                logger.error(f"Invalid date format for food item: {date_str}. Skipping.")
                output_messages.append(f"<span style='color: red;'>Invalid date format for food item: {date_str}. Skipping.</span>")
                continue

            # Navigate to the target date
            if not navigate_to_date(driver, target_date):
                logger.error(f"Failed to navigate to date {target_date}. Skipping food item.")
                output_messages.append(f"<span style='color: red;'>Failed to navigate to date {target_date}. Skipping food item.</span>")
                continue

            # Retry mechanism for locating search box
            max_retries = 2  # Number of times to retry before refreshing
            for attempt in range(1, max_retries + 1):
                # Get the meal name
                meal_name = food_item.get("Meal", "Dinner")
                # Select the search box for the meal
                search_input = select_search_box(driver, meal_name)
                if search_input:
                    break  # Found the search input, proceed
                else:
                    logger.warning(f"Attempt {attempt} to locate '{meal_name}' search box failed.")
                    if attempt < max_retries:
                        time.sleep(2)  # Wait before retrying
                    else:
                        logger.info("Performing page refresh and retrying.")
                        driver.refresh()
                        time.sleep(3)  # Wait for the page to load
                        # Navigate back to the target date after refresh
                        if not navigate_to_date(driver, target_date):
                            logger.error(f"Failed to navigate to date {target_date} after refresh. Skipping food item.")
                            output_messages.append(f"<span style='color: red;'>Failed to navigate to date {target_date} after refresh. Skipping food item.</span>")
                            continue  # Move to the next food item

            if not search_input:
                logger.error(f"Failed to locate '{meal_name}' search box after retries. Skipping food item.")
                output_messages.append(f"<span style='color: red;'>Failed to locate '{meal_name}' search box after retries. Skipping food item.</span>")
                continue

            # Enter placeholder text to trigger 'Create a custom food' button
            placeholder_text = "t3stf00dd03sn0t3xist"
            if not enter_placeholder_text(driver, search_input, placeholder_text):
                logger.error("Failed to enter placeholder text. Skipping food item.")
                output_messages.append("<span style='color: red;'>Failed to enter placeholder text. Skipping food item.</span>")
                continue

            # Retry mechanism for clicking 'Create a custom food' button
            if not click_create_custom_food(driver):
                logger.info("Attempting to refresh the page and retry clicking 'Create a custom food' button.")
                driver.refresh()
                time.sleep(3)  # Wait for the page to load
                # Navigate back to the target date after refresh
                if not navigate_to_date(driver, target_date):
                    logger.error(f"Failed to navigate to date {target_date} after refresh. Skipping food item.")
                    output_messages.append(f"<span style='color: red;'>Failed to navigate to date {target_date} after refresh. Skipping food item.</span>")
                    continue  # Move to the next food item
                # Try to locate the search box again
                search_input = select_search_box(driver, meal_name)
                if not search_input:
                    logger.error(f"Failed to locate '{meal_name}' search box after refresh. Skipping food item.")
                    output_messages.append(f"<span style='color: red;'>Failed to locate '{meal_name}' search box after refresh. Skipping food item.</span>")
                    continue
                # Enter placeholder text again
                if not enter_placeholder_text(driver, search_input, placeholder_text):
                    logger.error("Failed to enter placeholder text after refresh. Skipping food item.")
                    output_messages.append("<span style='color: red;'>Failed to enter placeholder text after refresh. Skipping food item.</span>")
                    continue
                # Try clicking the 'Create a custom food' button again
                if not click_create_custom_food(driver):
                    logger.error("Failed to click 'Create a custom food' button after refresh. Skipping food item.")
                    output_messages.append("<span style='color: red;'>Failed to click 'Create a custom food' button after refresh. Skipping food item.</span>")
                    continue

            # Enter food details
            if not enter_food_details(driver, food_item):
                logger.error("Failed to enter food details. Skipping food item.")
                output_messages.append("<span style='color: red;'>Failed to enter food details. Skipping food item.</span>")
                continue

            # Save the food
            if not save_food(driver):
                logger.error("Failed to save the food. Skipping food item.")
                output_messages.append("<span style='color: red;'>Failed to save the food. Skipping food item.</span>")
                continue

            # Close any overlays or popups after saving
            close_overlays(driver)

            # Update water intake if applicable
            serving_size = food_item.get("Serving Size", "").lower()
            if "fluid ounce" in serving_size:
                try:
                    # Calculate days_difference based on target_date
                    days_difference_calculation = (target_date - date.today()).days
                    previous_water_intake = water_intake_history.get(target_date, 0.0)
                    new_water_intake = update_water_intake(driver, food_item, days_difference_calculation)
                    if new_water_intake is not None:
                        water_intake_history[target_date] = new_water_intake
                        output_messages.append(f"Updated the water intake on {target_date.strftime('%m/%d/%Y')} from {previous_water_intake} oz to {new_water_intake} oz")
                    else:
                        output_messages.append(f"<span style='color: red;'>Failed to update water intake for {food_item.get('Food Name', 'Unknown')}</span>")
                except Exception as e:
                    logger.error(f"Error updating water intake: {e}")
                    output_messages.append(f"<span style='color: red;'>Error updating water intake: {e}</span>")
            else:
                logger.info(f"No fluid ounces found for: {food_item.get('Food Name', 'Unknown')}. Skipping water intake.")

            output_messages.append("Logged nutritional values")
            logger.info(f"Successfully logged food item: {food_item.get('Food Name', 'Unknown')}")

            # Keep track of processed dates
            processed_dates.add(target_date)

        # Fetch logged items for comparison
        logged_items = []
        for proc_date in processed_dates:
            items = fetch_logged_items(driver, proc_date)
            logged_items.extend(items)

        # Perform comparison
        comparison_output = compare_items(food_items, logged_items)
        output_messages.append(f"<br><b style='color: #f9c74f;'>Comparison Check:</b><br>{comparison_output}")

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
    # For testing purposes
    log_text = """Your sample food log text here."""
    output = main(log_text)
    print(output)