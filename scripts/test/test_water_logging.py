# test_water_logging.py

import os
import logging
import time
from datetime import datetime, date, timedelta
import re
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

# ----------------------- Configuration -----------------------

# Load environment variables from .env file
load_dotenv()

# Configure paths
LOG_DIR = "/tmp/test_logs"
os.makedirs(LOG_DIR, exist_ok=True)  # Ensure temporary log directory exists

TXT_FILE_PATH = "/Users/bradyespey/Projects/GitHub/LoseIt/txt/nutritional_data.txt"
if not os.path.exists(TXT_FILE_PATH):
    raise FileNotFoundError(f"Nutritional data file not found at: {TXT_FILE_PATH}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler(os.path.join(LOG_DIR, "test_food_logging.log"))  # Log to a file in /tmp/test_logs
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Log files will be stored in: {LOG_DIR}")
logger.info(f"Using nutritional data file path: {TXT_FILE_PATH}")

# Retrieve credentials and settings from environment variables
LOSEIT_EMAIL = os.getenv('LOSEIT_EMAIL')
LOSEIT_PASSWORD = os.getenv('LOSEIT_PASSWORD')
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'False').lower() == 'true'

if not LOSEIT_EMAIL or not LOSEIT_PASSWORD:
    logger.error("LOSEIT_EMAIL and LOSEIT_PASSWORD must be set in the .env file.")
    exit(1)

# ----------------------- Helper Functions -----------------------

def initialize_driver(headless=False):
    """
    Initializes the Chrome WebDriver with specified options.
    """
    try:
        options = Options()
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            logger.info("Running in headless mode.")
        else:
            options.add_argument("--start-maximized")
            logger.info("Running in headed mode (browser window will be visible).")
        
        # Additional options to mimic regular browser behavior
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/131.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Prevent detection as a bot
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
                """
            },
        )

        logger.info("Chrome WebDriver initialized successfully.")
        return driver
    except WebDriverException as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        exit(1)

def login(driver, email, password):
    """
    Logs into the Lose It! account using provided credentials.
    """
    try:
        login_url = "https://my.loseit.com/login?r=https://www.loseit.com/"
        driver.get(login_url)
        logger.info("Navigated to Lose It! login page.")

        # Wait for email input
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'email'))
        )
        logger.info("Email input field verified.")

        # Enter email
        email_input.clear()
        email_input.send_keys(email)
        logger.info("Entered email.")

        # Enter password
        password_input = driver.find_element(By.ID, 'password')
        password_input.clear()
        password_input.send_keys(password)
        logger.info("Entered password.")

        # Click login button
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        logger.info("Clicked login button.")

        # Wait for login to complete by checking that the URL has changed from the login page
        WebDriverWait(driver, 15).until(
            EC.url_changes(login_url)
        )

        # Verify that the URL is now the home page
        current_url = driver.current_url
        if "https://www.loseit.com/" in current_url or "https://my.loseit.com/" in current_url:
            logger.info("Logged in successfully.")
            return True
        else:
            logger.error(f"Login failed: Unexpected URL after login: {current_url}")
            return False
    except TimeoutException:
        logger.error("Login failed: Timeout while waiting for home page to load.")
        return False
    except Exception as e:
        logger.error(f"An error occurred during login: {e}", exc_info=True)
        return False

def verify_login(driver):
    """
    Verifies that the user is logged in by checking for the current date on the homepage.
    """
    try:
        # Use the class name that works in test_food_logging.py
        current_date_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "GCJ-IGUD0B"))
        )
        current_date_text = current_date_element.text.strip()
        logger.info(f"Current date found on home page: {current_date_text}")
        # Optionally, parse and verify the date format
        current_date = datetime.strptime(current_date_text, '%A %b %d, %Y').date()
        logger.info(f"Parsed current date: {current_date}")
        return True
    except TimeoutException:
        logger.error("Login may have failed; current date not found on home page.")
        driver.save_screenshot(os.path.join(LOG_DIR, "verify_login_timeout.png"))
        return False
    except Exception as e:
        logger.error(f"An error occurred while verifying login: {e}", exc_info=True)
        return False

def parse_food_items(file_path):
    """
    Parses the food items from the given text file.
    """
    food_items = []
    current_food = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:
                    if current_food:
                        food_items.append(current_food)
                        current_food = {}
                    continue
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    current_food[key.strip()] = value.strip()
        if current_food:
            food_items.append(current_food)
        return food_items
    except FileNotFoundError:
        logger.error(f"Food data file not found at path: {file_path}")
        return []
    except Exception as e:
        logger.error(f"An error occurred while parsing food items: {e}", exc_info=True)
        return []

def parse_food_item_date(date_str):
    """
    Parses the date string from the food item into a date object.
    Assumes the input format is 'MM/DD' and appends the current year.
    """
    try:
        # Assume the year is the current year
        current_year = date.today().year
        # Handle single-digit month or day by ensuring two digits
        month, day = date_str.split('/')
        month = month.zfill(2)
        day = day.zfill(2)
        date_obj = datetime.strptime(f"{month}/{day}/{current_year}", '%m/%d/%Y').date()
        return date_obj
    except Exception as e:
        logger.error(f"An error occurred while parsing food item date '{date_str}': {e}", exc_info=True)
        return None

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
        driver.save_screenshot(os.path.join(LOG_DIR, "navigate_to_water_goals_page_error.png"))

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
        driver.save_screenshot(os.path.join(LOG_DIR, "get_current_water_date_error.png"))

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
        driver.save_screenshot(os.path.join(LOG_DIR, "navigate_water_day_timeout.png"))
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
        driver.save_screenshot(os.path.join(LOG_DIR, "get_current_water_intake_error.png"))

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
            EC.text_to_be_present_in_element_value((By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"), str(water_oz))
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
                return
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
                driver.save_screenshot(os.path.join(LOG_DIR, "update_water_intake_date_error.png"))

            if current_water_date != target_date:
                # Navigate back to the target date if necessary
                days_to_navigate = (current_water_date - target_date).days
                if days_to_navigate > 0:
                    navigate_water_day(driver, days_to_navigate)
                elif days_to_navigate < 0:
                    logger.warning("Cannot navigate forward past today's date for the water intake page.")
                    return  # Cannot proceed

                # Re-verify the date
                current_water_date = get_current_water_date(driver)
                if current_water_date != target_date:
                    logger.error(f"Failed to navigate to the correct date. Expected: {target_date}, Found: {current_water_date}")
                    driver.save_screenshot(os.path.join(LOG_DIR, "update_water_intake_navigation_error.png"))
                else:
                    logger.info(f"Verified target date: {current_water_date}")
            else:
                logger.info(f"Already on target date: {current_water_date}")

            # Get current water intake
            current_water = get_current_water_intake(driver)
            if current_water is None:
                logger.error("Could not retrieve current water intake. Skipping update.")
                return

            # Calculate updated water intake
            updated_water = current_water + total_fluid_oz
            logger.info(f"Current water intake: {current_water} oz")
            logger.info(f"Adding {total_fluid_oz} oz")
            logger.info(f"Updated water intake will be: {updated_water} oz")

            # Set the new water intake value
            set_water_intake(driver, updated_water)

            # Navigate back to the main page
            navigate_to_main_page(driver)

        except Exception as e:
            logger.error(f"Failed to update water intake: {e}", exc_info=True)
    else:
        logger.info(f"No fluid ounces found for: {food_item.get('Food Name', 'Unknown')}. Skipping.")

# ----------------------- Main Execution -----------------------

def main():
    logger.info("Test Water Logging Script started.")
    driver = initialize_driver(headless=HEADLESS_MODE)

    try:
        # Step 1: Log in
        login_success = login(driver, LOSEIT_EMAIL, LOSEIT_PASSWORD)
        if not login_success:
            logger.error("Login failed. Exiting script.")
            return

        # Step 2: Verify login
        login_verified = verify_login(driver)
        if not login_verified:
            logger.error("Login verification failed. Exiting script.")
            return

        # Step 3: Read food items from the text file
        if not os.path.exists(TXT_FILE_PATH):
            logger.error(f"File not found: {TXT_FILE_PATH}")
            food_items = []
        else:
            logger.info(f"Using nutritional data file: {TXT_FILE_PATH}")
            food_items = parse_food_items(TXT_FILE_PATH)
            logger.info(f"Parsed {len(food_items)} food items from the text file.")

        # Step 4: Process each food item
        for food_item in food_items:
            # Parse the date
            date_str = food_item.get("Date")
            if not date_str:
                logger.error("Date is missing for a food item. Skipping.")
                continue
            target_date = parse_food_item_date(date_str)
            if not target_date:
                logger.error(f"Invalid date format for food item: {date_str}. Skipping.")
                continue

            # Calculate days difference
            days_difference = (target_date - date.today()).days

            # Check if serving size includes fluid ounces
            serving_size = food_item.get("Serving Size", "").lower()
            if "fluid ounce" in serving_size:
                logger.info(f"Processing water intake for: {food_item.get('Food Name', 'Unknown')}")
                update_water_intake(driver, food_item, days_difference)
            else:
                logger.info(f"No fluid ounces found for: {food_item.get('Food Name', 'Unknown')}. Skipping.")

            # Wait before processing the next food item
            time.sleep(2)

        logger.info("All food items processed.")
        logger.info("Test Water Logging Script completed successfully.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    finally:
        driver.quit()
        logger.info("WebDriver closed.")

if __name__ == "__main__":
    main()
