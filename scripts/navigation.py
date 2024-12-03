# scripts/navigation.py

import os
import logging
from datetime import datetime
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# ----------------------- Configuration -----------------------

# Dynamically set the base directory for logs and screenshots
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "navigation.log"))  # Log to a file in LOG_DIR
    ]
)
logger = logging.getLogger(__name__)

def get_current_date(driver):
    try:
        current_date_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "GCJ-IGUD0B"))
        )
        current_date_text = current_date_element.text.strip()
        logger.info(f"Current date displayed in app: {current_date_text}")
        # Expected format: 'Monday Dec 02, 2024'
        current_date = datetime.strptime(current_date_text, '%A %b %d, %Y').date()
        return current_date
    except Exception as e:
        logger.error(f"An error occurred while retrieving current date: {e}", exc_info=True)
        return None

def parse_food_item_date(date_str):
    try:
        # Assume the year is the current year
        current_year = datetime.today().year
        date_obj = datetime.strptime(f"{date_str}/{current_year}", '%m/%d/%Y').date()
        return date_obj
    except Exception as e:
        logger.error(f"An error occurred while parsing food item date '{date_str}': {e}", exc_info=True)
        return None

def navigate_to_date(driver, target_date):
    try:
        max_attempts = 30  # To prevent infinite loops
        attempts = 0

        while attempts < max_attempts:
            current_date = get_current_date(driver)
            if not current_date:
                logger.error("Unable to retrieve current date from the app.")
                return False

            if current_date == target_date:
                logger.info(f"Already on the target date: {target_date}")
                return True
            elif current_date < target_date:
                # Click 'Next Day' button
                try:
                    next_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @title='Next']"))
                    )
                    next_button.click()
                    logger.info("Clicked 'Next Day' button.")
                except TimeoutException:
                    logger.error("Next Day button not found or not clickable.")
                    driver.save_screenshot(os.path.join(LOG_DIR, "next_button_not_found.png"))
                    return False
                except ElementClickInterceptedException as e:
                    logger.error(f"Element click intercepted: {e}")
                    # Close any overlays
                    close_overlays(driver)
                    continue
            else:
                # Click 'Previous Day' button
                try:
                    prev_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @title='Previous']"))
                    )
                    prev_button.click()
                    logger.info("Clicked 'Previous Day' button.")
                except TimeoutException:
                    logger.error("Previous Day button not found or not clickable.")
                    driver.save_screenshot(os.path.join(LOG_DIR, "prev_button_not_found.png"))
                    return False
                except ElementClickInterceptedException as e:
                    logger.error(f"Element click intercepted: {e}")
                    # Close any overlays
                    close_overlays(driver)
                    continue
            time.sleep(1)  # Wait for the date to update
            attempts += 1

        logger.error(f"Failed to navigate to target date {target_date} after {max_attempts} attempts.")
        return False
    except Exception as e:
        logger.error(f"An error occurred while navigating to date: {e}", exc_info=True)
        return False

def close_overlays(driver):
    try:
        # Look for common overlay elements and attempt to close them
        close_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and @title='Close']")
        for button in close_buttons:
            try:
                button.click()
                logger.info("Closed an overlay or popup.")
            except Exception as e:
                logger.error(f"Failed to click close button: {e}")
    except Exception as e:
        logger.error(f"An error occurred while closing overlays: {e}")

def select_search_box(driver, meal_name):
    try:
        # Define the tabindex based on the meal
        tabindex_map = {
            "Breakfast": "200",
            "Lunch": "300",
            "Dinner": "400",
            "Snacks": "500"
        }
        tabindex = tabindex_map.get(meal_name, "400")  # Default to Dinner if not found

        # Retry mechanism
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                # Locate the search input using the tabindex
                search_input_xpath = f"//input[@tabindex='{tabindex}']"
                search_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, search_input_xpath))
                )
                logger.info(f"Located search box for '{meal_name}' on attempt {attempt}.")
                return search_input
            except (TimeoutException, StaleElementReferenceException):
                logger.warning(f"Attempt {attempt} to locate search input for meal '{meal_name}' failed.")
                if attempt < max_retries:
                    time.sleep(2)  # Wait before retrying
                else:
                    logger.error(f"Failed to locate search input for meal '{meal_name}' after {max_retries} attempts.")
        return None
    except Exception as e:
        logger.error(f"An error occurred while selecting search box for meal '{meal_name}': {e}", exc_info=True)
        return None

def enter_placeholder_text(driver, search_input, placeholder_text):
    try:
        search_input.clear()
        search_input.send_keys(placeholder_text)
        search_input.send_keys(Keys.ENTER)
        logger.info(f"Entered placeholder text '{placeholder_text}' in the search box.")
        return True
    except Exception as e:
        logger.error(f"An error occurred while entering placeholder text: {e}", exc_info=True)
        return False

def wait_for_fixed_glass_invisibility(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "fixedGlass"))
        )
        logger.info("'fixedGlass' overlay is no longer visible.")
        return True
    except TimeoutException:
        logger.error("'fixedGlass' overlay is still visible after waiting.")
        # Optional: Take a screenshot for debugging
        driver.save_screenshot(os.path.join(LOG_DIR, "fixed_glass_still_visible.png"))
        return False

def click_create_custom_food(driver):
    try:
        # Define the XPath for the 'Create a custom food' button
        create_food_button_xpath = "//div[contains(@class, 'gwt-HTML') and normalize-space(text())='Create a custom food']"

        # Retry mechanism
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            # Wait until 'fixedGlass' is invisible to ensure no overlay is blocking the click
            fixed_glass_invisible = wait_for_fixed_glass_invisibility(driver)
            if not fixed_glass_invisible:
                logger.error("Cannot proceed to click 'Create a custom food' due to 'fixedGlass' overlay.")
                return False

            try:
                # Locate the 'Create a custom food' button
                create_food_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, create_food_button_xpath))
                )
                # Scroll into view and click
                driver.execute_script("arguments[0].scrollIntoView(true);", create_food_button)
                create_food_button.click()
                logger.info(f"Clicked 'Create a custom food' button on attempt {attempt}.")
                return True
            except (TimeoutException, ElementClickInterceptedException, StaleElementReferenceException) as e:
                logger.warning(f"Attempt {attempt} to click 'Create a custom food' button failed: {e}")
                if attempt < max_retries:
                    time.sleep(2)  # Wait before retrying
                else:
                    logger.error(f"Failed to click 'Create a custom food' button after {max_retries} attempts.")
        return False
    except Exception as e:
        logger.error(f"An error occurred while clicking 'Create a custom food' button: {e}", exc_info=True)
        return False