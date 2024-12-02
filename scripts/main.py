# scripts/main.py

import os
import time
import logging
from datetime import datetime
import subprocess
from webdriver_manager.chrome import ChromeDriverManager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# Import modular functions
from scripts.login import check_logged_in, login_using_credentials
from scripts.navigation import navigate_day
from scripts.food_entry import click_create_custom_food, enter_food_details
from scripts.water_intake import update_water_intake, navigate_to_water_goals_page, navigate_water_day, get_current_water_intake, set_water_intake
from scripts.utils import parse_nutritional_data, compare_items

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for detailed logs
logger = logging.getLogger(__name__)

def kill_chrome_driver():
    """
    Kills any lingering Chrome or ChromeDriver processes.
    """
    try:
        if os.name == 'nt':
            subprocess.call("taskkill /f /im chromedriver.exe >nul 2>&1", shell=True)
            subprocess.call("taskkill /f /im chrome.exe >nul 2>&1", shell=True)
        else:
            subprocess.call("pkill chromedriver", shell=True)
            subprocess.call("pkill chrome", shell=True)
        logger.debug("Killed existing Chrome and ChromeDriver processes.")
    except Exception as e:
        logger.warning(f"Failed to kill Chrome/ChromeDriver processes: {e}")

def initialize_driver():
    """
    Initializes the Chrome WebDriver with specified options using webdriver-manager.
    """
    kill_chrome_driver()  # Ensure no previous instances are running

    # Set Chrome options
    options = Options()

    # Run in headless mode based on environment variable
    headless_mode = os.getenv('HEADLESS_MODE', 'True') == 'True'
    if headless_mode:
        options.add_argument("--headless=new")  # Use "--headless=new" for newer Chrome versions
        options.add_argument("--disable-gpu")
        logger.debug("Running in headless mode.")
    else:
        options.add_argument("--start-maximized")  # For visual debugging
        logger.debug("Running in non-headless mode.")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")

    # Initialize Chrome WebDriver using webdriver-manager
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        logger.info("Chrome WebDriver initialized.")
        return driver
    except WebDriverException as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        raise e

def initialize_driver_with_retry(retries=3):
    """
    Attempts to initialize the driver, retrying in case of failure.
    """
    for attempt in range(retries):
        try:
            logger.info(f"Attempting to initialize WebDriver (Attempt {attempt + 1})...")
            return initialize_driver()
        except WebDriverException as e:
            logger.warning(f"WebDriver initialization failed on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                logger.info("Retrying to initialize driver...")
                time.sleep(2)  # Wait before retrying
            else:
                logger.error(f"Failed to initialize WebDriver after {retries} attempts.")
                raise e

def visit_homepage(driver):
    """
    Navigates to the Lose It! homepage.
    """
    try:
        homepage_url = "https://www.loseit.com/"
        driver.get(homepage_url)
        logger.info("Visited homepage.")
        time.sleep(3)
    except Exception as e:
        logger.error(f"Failed to visit the homepage: {e}")

def main():
    start_time = time.time()

    log_text = os.getenv('LOG_TEXT', '')
    if not log_text:
        logger.error("No LOG_TEXT provided.")
        return

    driver = None
    logging_output = "<b style='color: #f9c74f;'>Logging Output:</b><br>"

    total_input_fluid_ounces = 0.0
    total_logged_fluid_ounces = 0.0

    try:
        logger.info("Initializing WebDriver...")
        driver = initialize_driver_with_retry()
        logger.info("WebDriver initialized.")

        logger.info("Navigating to Lose It! homepage...")
        visit_homepage(driver)

        logger.info("Checking login status...")
        if not check_logged_in(driver):
            logger.info("User not logged in. Attempting to log in...")
            if not login_using_credentials(driver):
                logger.error("Failed to log in using credentials.")
                return
        else:
            logger.info("User is already logged in.")

        logger.info("Navigated to Lose It! homepage after logging in.")

        food_items = parse_nutritional_data(log_text)
        logged_items = []

        for index, food_details in enumerate(food_items):
            current_date = datetime.now().strftime("%m/%d/%Y")
            food_date = food_details.get("date", current_date)
            try:
                food_date_obj = datetime.strptime(food_date, "%m/%d/%Y")
            except ValueError:
                # If year is missing, append current year
                try:
                    food_date_obj = datetime.strptime(f"{food_date}/{datetime.now().year}", "%m/%d/%Y")
                except ValueError as ve:
                    logger.error(f"Invalid date format for '{food_date}': {ve}")
                    continue
            current_date_obj = datetime.strptime(current_date, "%m/%d/%Y")
            days_difference = (food_date_obj - current_date_obj).days
            if days_difference != 0:
                navigate_day(driver, days=days_difference)

            meal = food_details.get("meal", "dinner").lower()
            # Updated to use meal name instead of tabindex
            enter_placeholder_text_in_search_box(driver, meal)

            if not click_create_custom_food(driver):
                logger.warning(f"Failed to find 'Create a custom food' button for '{food_details['name']}'. Skipping to next.")
                continue

            # Log food details
            enter_food_details(driver, food_details)

            logged_items.append(food_details)
            logging_output += f"Logging item {index + 1} of {len(food_items)}: {food_details['name']}<br>"

            # Update water intake and get fluid ounces added
            water_log_message, fluid_oz_added = update_water_intake(
                driver, food_details, days_difference,
                navigate_to_water_goals_page, navigate_water_day, get_current_water_intake, set_water_intake
            )
            if water_log_message:
                logging_output += f"{water_log_message}<br>"
            else:
                fluid_oz_added = 0.0

            # Store the fluid ounces added into food_details
            food_details['fluid_ounces_added'] = fluid_oz_added

            # Accumulate totals
            total_input_fluid_ounces += food_details.get('fluid_ounces', 0.0)
            total_logged_fluid_ounces += fluid_oz_added

            # Refresh the page to reset for the next item
            driver.refresh()
            visit_homepage(driver)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    finally:
        if driver:
            driver.quit()
            logger.info("WebDriver closed.")

    logging_output += f"Time to Log: {time.time() - start_time:.2f} seconds<br><br>"
    comparison = compare_items(food_items, logged_items, log_text, total_input_fluid_ounces, total_logged_fluid_ounces)
    logger.info(logging_output + comparison)
    print(logging_output + comparison)  # Ensure the output is sent to stdout

def convert_fraction_to_float(fraction_str):
    """
    Converts a fraction string to a float.
    """
    if '/' in fraction_str:
        numerator, denominator = fraction_str.split('/')
        return float(numerator) / float(denominator)
    else:
        try:
            return float(fraction_str)
        except ValueError:
            logger.warning(f"Cannot convert fraction string to float: {fraction_str}")
            return 0.0

def enter_placeholder_text_in_search_box(driver, meal):
    """
    Enters placeholder text in the search box based on the meal.
    """
    try:
        # Locate the meal section by its header
        meal_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//h2[contains(text(), '{meal.capitalize()}')]"))
        )
        # Then find the search box within that section
        search_box = meal_section.find_element(By.XPATH, ".//input[@placeholder='Search foods']")
        search_box.clear()
        search_box.click()
        search_box.send_keys("t3stf00dd03sn0t3xist")
        search_box.send_keys(Keys.ENTER)
        logger.info(f"Entered placeholder text in search box for meal '{meal}'.")
    except Exception as e:
        logger.error(f"Failed to enter text in search box: {e}")

if __name__ == "__main__":
    main()