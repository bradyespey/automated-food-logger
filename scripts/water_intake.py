# scripts/water_intake.py

import logging
import re
import time
from datetime import datetime, date, timedelta
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scripts.logging_setup import get_logger
from scripts.decorators import retry_on_failure

logger = get_logger("water_intake")

GOALS_URL = "https://www.loseit.com/#Goals:Water%20Intake%5EWater%20Intake"
MAIN_URL = "https://www.loseit.com/"

@retry_on_failure(max_retries=3, delay=2)
def navigate_to_water_goals_page(driver):
    # Navigate to the water intake page
    try:
        driver.get(GOALS_URL)
        time.sleep(3)
        logger.info("Navigated to water intake page.")
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to water intake page: {e}")
        return False

@retry_on_failure(max_retries=3, delay=2)
def get_current_water_date(driver):
    # Get the current date displayed on the water intake page
    try:
        date_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "GCJ-IGUC0B"))
        )
        current_date_text = date_element.text.strip().replace('\xa0', ' ')
        logger.info(f"Current date on water intake page: {current_date_text}")
        current_date = datetime.strptime(current_date_text, '%A %b %d, %Y').date()
        return current_date
    except Exception as e:
        logger.error(f"Error retrieving current water date: {e}")
        return None

@retry_on_failure(max_retries=3, delay=2)
def navigate_water_day(driver, days):
    # Navigate back by specified number of days
    try:
        if days <= 0:
            logger.info("No need to navigate days.")
            return True
        for _ in range(days):
            prev_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@title='Previous']"))
            )
            prev_button.click()
            logger.info("Clicked 'Previous Day' button.")
            time.sleep(1)
        return True
    except TimeoutException:
        logger.error("Previous Day button not found or not clickable.")
        return False
    except Exception as e:
        logger.error(f"Error navigating back days: {e}")
        return False

@retry_on_failure(max_retries=3, delay=2)
def get_current_water_intake(driver):
    # Retrieve current water intake from input box
    try:
        water_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"))
        )
        water_value_str = water_input.get_attribute('value').strip()
        logger.info(f"Current water intake value in input box: {water_value_str}")
        current_water = float(water_value_str)
        logger.info(f"Current water intake: {current_water} oz")
        return current_water
    except Exception as e:
        logger.error(f"Failed to read current water intake: {e}")
        return None

@retry_on_failure(max_retries=3, delay=2)
def set_water_intake(driver, water_oz):
    # Set new water intake value and record it
    try:
        water_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"))
        )
        water_input.clear()
        water_input.send_keys(str(water_oz))
        logger.info(f"Entered new water intake: {water_oz} oz")

        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element_value(
                (By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"),
                str(water_oz)
            )
        )
        logger.info(f"Verified new water intake in input box: {water_oz} oz")

        record_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'recordButton')]"))
        )
        record_button.click()
        logger.info("Clicked Record button to save water intake.")

        time.sleep(2)
        return True
    except TimeoutException:
        logger.error("Water intake input box or Record button not found/clickable.")
        driver.save_screenshot("/tmp/set_water_intake_timeout.png")
        return False
    except Exception as e:
        logger.error(f"Failed to set water intake: {e}")
        driver.save_screenshot("/tmp/set_water_intake_error.png")
        return False

@retry_on_failure(max_retries=3, delay=2)
def navigate_to_main_page(driver):
    # Navigate back to the main Lose It! page
    try:
        driver.get(MAIN_URL)
        time.sleep(3)
        logger.info("Navigated back to the main page.")
        return True
    except Exception as e:
        logger.error(f"Failed to navigate back to the main page: {e}")
        return False

@retry_on_failure(max_retries=3, delay=2)
def update_water_intake(driver, food_item, days_difference):
    # Update water intake based on fluid ounces in the food item
    serving_size = food_item.get("Serving Size", "").lower()
    if "fluid ounce" in serving_size:
        try:
            fluid_oz_matches = re.findall(r"(\d+\.?\d*)\s*fluid ounce", serving_size)
            if not fluid_oz_matches:
                logger.error(f"Could not extract fluid ounces from serving size: {serving_size}")
                return None
            total_fluid_oz = sum(float(match) for match in fluid_oz_matches)

            logger.info(f"Serving size: {serving_size}")
            logger.info(f"Total fluid ounces to add: {total_fluid_oz}")

            if not navigate_to_water_goals_page(driver):
                return None

            target_date = date.today() + timedelta(days=days_difference)

            current_water_date = get_current_water_date(driver)
            if not current_water_date:
                logger.error("Could not retrieve current water date. Skipping update.")
                return None

            if current_water_date != target_date:
                days_to_navigate = (current_water_date - target_date).days
                if days_to_navigate > 0:
                    if not navigate_water_day(driver, days_to_navigate):
                        return None
                elif days_to_navigate < 0:
                    logger.warning("Cannot navigate forward past today's date for the water intake page.")
                    return None

                current_water_date = get_current_water_date(driver)
                if current_water_date != target_date:
                    logger.error(f"Failed to navigate to the correct date. Expected: {target_date}, Found: {current_water_date}")
                    return None
                else:
                    logger.info(f"Verified target date: {current_water_date}")
            else:
                logger.info(f"Already on target date: {current_water_date}")

            current_water = get_current_water_intake(driver)
            if current_water is None:
                logger.error("Could not retrieve current water intake. Skipping update.")
                return None

            updated_water = current_water + total_fluid_oz
            logger.info(f"Current water intake: {current_water} oz")
            logger.info(f"Adding {total_fluid_oz} oz")
            logger.info(f"Updated water intake will be: {updated_water} oz")

            if not set_water_intake(driver, updated_water):
                return None

            if not navigate_to_main_page(driver):
                return None

            return updated_water

        except Exception as e:
            logger.error(f"Failed to update water intake: {e}")
            return None
    else:
        logger.info(f"No fluid ounces found for: {food_item.get('Food Name', 'Unknown')}. Skipping.")
        return None
