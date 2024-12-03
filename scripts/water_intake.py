# scripts/water_intake.py

import os
import logging
import re
import time
from datetime import datetime, date, timedelta
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Adjust as needed
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "water_intake.log"))
    ]
)
logger = logging.getLogger(__name__)

GOALS_URL = "https://www.loseit.com/#Goals:Water%20Intake%5EWater%20Intake"
MAIN_URL = "https://www.loseit.com/"

def navigate_to_water_goals_page(driver):
    """
    Navigates to the water intake page.
    """
    try:
        water_page_url = "https://www.loseit.com/#Goals:Water%20Intake%5EWater%20Intake"
        driver.get(water_page_url)
        time.sleep(3)  # Wait for the page to load
        logger.info("Navigated to water intake page.")
    except Exception as e:
        logger.error(f"Failed to navigate to water intake page: {e}", exc_info=True)

def get_current_water_date(driver):
    """
    Retrieves the current date displayed on the water intake page.
    """
    try:
        # The date element has class "gwt-HTML GCJ-IGUC0B"
        date_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "GCJ-IGUC0B"))
        )
        current_date_text = date_element.text.strip().replace('\xa0', ' ')
        logger.info(f"Current date on water intake page: {current_date_text}")
        # Expected format: 'Monday Dec 02, 2024'
        current_date = datetime.strptime(current_date_text, '%A %b %d, %Y').date()
        return current_date
    except Exception as e:
        logger.error(f"An error occurred while retrieving current date on water intake page: {e}", exc_info=True)
        return None

def navigate_water_day(driver, days):
    """
    Navigates back by the specified number of days on the water intake page.
    Note: Cannot navigate past today's date for the water intake page.
    """
    try:
        if days <= 0:
            logger.info("No need to navigate days.")
            return
        for _ in range(days):
            prev_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@title='Previous']"))
            )
            prev_button.click()
            logger.info("Clicked 'Previous Day' button.")
            time.sleep(1)  # Wait for the date to update
    except TimeoutException:
        logger.error("Previous Day button not found or not clickable.")
    except Exception as e:
        logger.error(f"An error occurred while navigating back days: {e}", exc_info=True)

def get_current_water_intake(driver):
    """
    Retrieves the current water intake value from the water intake page.
    Reads from the input box where intake is set.
    """
    try:
        # The water intake is displayed in an input box with class "gwt-TextBox GCJ-IGUKWC"
        water_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"))
        )
        water_value_str = water_input.get_attribute('value').strip()
        logger.info(f"Current water intake value in input box: {water_value_str}")
        # Convert to float
        current_water = float(water_value_str)
        logger.info(f"Current water intake: {current_water} oz")
        return current_water
    except Exception as e:
        logger.error(f"Failed to read current water intake from input box: {e}", exc_info=True)
        return None

def set_water_intake(driver, water_oz):
    """
    Sets the water intake value on the water intake page.
    Reads from the input box, clears it, enters the new value, and clicks Record.
    """
    try:
        # Locate the water intake input box
        water_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"))
        )
        water_input.clear()
        water_input.send_keys(str(water_oz))
        logger.info(f"Entered new water intake: {water_oz} oz")

        # Wait until the input box value matches the new intake
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element_value(
                (By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"),
                str(water_oz)
            )
        )
        logger.info(f"Verified new water intake in input box: {water_oz} oz")

        # Locate and click the Record button
        record_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'recordButton')]"))
        )
        record_button.click()
        logger.info("Clicked Record button to save water intake.")

        time.sleep(2)  # Wait for the update to process

        # Do not attempt to verify the intake after Record to avoid discrepancies
    except TimeoutException:
        logger.error("Water intake input box or Record button not found or not clickable.")
        driver.save_screenshot(os.path.join(LOG_DIR, "set_water_intake_timeout.png"))
    except Exception as e:
        logger.error(f"Failed to set water intake: {e}", exc_info=True)
        driver.save_screenshot(os.path.join(LOG_DIR, "set_water_intake_error.png"))

def navigate_to_main_page(driver):
    """
    Navigates back to the main Lose It! page.
    """
    try:
        main_url = "https://www.loseit.com/"
        driver.get(main_url)
        time.sleep(3)  # Wait for the page to load
        logger.info("Navigated back to the main page.")
    except Exception as e:
        logger.error(f"Failed to navigate back to the main page: {e}", exc_info=True)

def update_water_intake(driver, food_item, days_difference):
    """
    Updates water intake based on fluid ounces in the food item.
    """
    serving_size = food_item.get("Serving Size", "").lower()
    if "fluid ounce" in serving_size:
        try:
            # Extract fluid ounces from the serving size
            fluid_oz_matches = re.findall(r"(\d+\.?\d*)\s*fluid ounce", serving_size)
            if not fluid_oz_matches:
                logger.error(f"Could not extract fluid ounces from serving size: {serving_size}")
                return None
            total_fluid_oz = sum(float(match) for match in fluid_oz_matches)

            logger.info(f"Serving size: {serving_size}")
            logger.info(f"Total fluid ounces to add: {total_fluid_oz}")

            # Navigate to the water intake page
            navigate_to_water_goals_page(driver)

            # Calculate target date
            target_date = date.today() + timedelta(days=days_difference)

            # Verify current date on water page
            current_water_date = get_current_water_date(driver)
            if not current_water_date:
                logger.error("Could not retrieve current water date. Skipping update.")
                return None

            if current_water_date != target_date:
                # Navigate back to the target date if necessary
                days_to_navigate = (current_water_date - target_date).days
                if days_to_navigate > 0:
                    navigate_water_day(driver, days_to_navigate)
                elif days_to_navigate < 0:
                    logger.warning("Cannot navigate forward past today's date for the water intake page.")
                    return None  # Cannot proceed

                # Re-verify the date
                current_water_date = get_current_water_date(driver)
                if current_water_date != target_date:
                    logger.error(f"Failed to navigate to the correct date. Expected: {target_date}, Found: {current_water_date}")
                    return None
                else:
                    logger.info(f"Verified target date: {current_water_date}")
            else:
                logger.info(f"Already on target date: {current_water_date}")

            # Get current water intake
            current_water = get_current_water_intake(driver)
            if current_water is None:
                logger.error("Could not retrieve current water intake. Skipping update.")
                return None

            # Calculate updated water intake
            updated_water = current_water + total_fluid_oz
            logger.info(f"Current water intake: {current_water} oz")
            logger.info(f"Adding {total_fluid_oz} oz")
            logger.info(f"Updated water intake will be: {updated_water} oz")

            # Set the new water intake value
            set_water_intake(driver, updated_water)

            # Navigate back to the main page
            navigate_to_main_page(driver)

            return updated_water

        except Exception as e:
            logger.error(f"Failed to update water intake: {e}", exc_info=True)
            return None
    else:
        logger.info(f"No fluid ounces found for: {food_item.get('Food Name', 'Unknown')}. Skipping.")
        return None