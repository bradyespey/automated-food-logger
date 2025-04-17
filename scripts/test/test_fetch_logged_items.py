# scripts/test/test_fetch_logged_items.py

import os
import time
import logging
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager

# ----------------------- Configuration -----------------------

# Load environment variables from .env file
load_dotenv()

# Configure paths
LOG_DIR = "/tmp/test_logs"
os.makedirs(LOG_DIR, exist_ok=True)

TXT_FILE_PATH = "/Users/bradyespey/Projects/GitHub/LoseIt/txt/nutritional_data.txt"
if not os.path.exists(TXT_FILE_PATH):
    raise FileNotFoundError(f"Nutritional data file not found at: {TXT_FILE_PATH}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler(os.path.join(LOG_DIR, "test_fetch_logged_items.log"))  # Log to a file in /tmp/test_logs
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

def initialize_driver(headless=True):
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

        # Wait for email input to be present and visible
        email_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'email'))
        )
        logger.info("Email input field verified.")

        # Enter email
        email_input.clear()
        email_input.send_keys(email)
        logger.info("Entered email.")

        # Wait for password input to be present and visible
        password_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'password'))
        )
        password_input.clear()
        password_input.send_keys(password)
        logger.info("Entered password.")

        # Click login button
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
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
        driver.save_screenshot(os.path.join(LOG_DIR, "login_timeout.png"))
        return False
    except Exception as e:
        logger.error(f"An error occurred during login: {e}", exc_info=True)
        driver.save_screenshot(os.path.join(LOG_DIR, "login_unexpected_error.png"))
        return False

def verify_login(driver):
    """
    Verifies that the user is successfully logged in by checking the presence of a specific element.
    """
    try:
        # Locate the element that confirms login, e.g., current date or user profile
        current_date_element = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "GCJ-IGUD0B"))
        )
        current_date_text = current_date_element.text.strip()
        logger.info(f"Login verified. Current date found: {current_date_text}")
        return True
    except TimeoutException:
        logger.error("Login may have failed; current date not found on home page.")
        driver.save_screenshot(os.path.join(LOG_DIR, "verify_login_timeout.png"))
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during login verification: {e}", exc_info=True)
        driver.save_screenshot(os.path.join(LOG_DIR, "verify_login_unexpected_error.png"))
        return False

def fetch_logged_items(driver, target_date):
    """
    Fetches logged food items from Lose It! for the specified date.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        target_date (date): The date for which to fetch logged items.

    Returns:
        list: A list of dictionaries representing logged food items.
    """
    logged_items = []
    try:
        # Navigate to the target date
        if not navigate_to_date(driver, target_date):
            logger.error(f"Cannot fetch logged items for date {target_date} because navigation failed.")
            return logged_items

        # Define the meals to fetch
        meals = ["Breakfast", "Lunch", "Dinner", "Snacks"]

        for meal in meals:
            try:
                # Locate the meal section by meal name
                meal_section = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{meal}:')]"))
                )
                meal_tr = meal_section.find_element(By.XPATH, "./ancestor::tr")
                
                # Find all food item tables under this meal
                food_tables = meal_tr.find_elements(By.XPATH, "./following-sibling::tr[contains(@class, 'GCJ-IGUPIB')]//table")
                
                if not food_tables:
                    logger.info(f"No food items found for meal '{meal}' on date {target_date}.")
                    continue
                
                for food_table in food_tables:
                    try:
                        # Extract Food Name
                        food_name = food_table.find_element(By.XPATH, ".//a[contains(@class, 'gwt-Anchor')]").text.strip()
                        
                        # Extract Serving Size
                        serving = food_table.find_element(By.XPATH, ".//div[contains(@class, 'GCJ-IGULIB')]").text.strip()
                        
                        # Extract Calories
                        calories = food_table.find_element(By.XPATH, ".//div[@style='width: 35px;']").text.strip()
                        
                        # Extract Fluid Ounces (if applicable)
                        fluid_ounces_added = 0.0
                        try:
                            # Adjust this based on how fluid ounces are represented in 'serving'
                            fluid_ounces_text = serving.split('Fluid ounces')[0].strip()
                            fluid_ounces_added = float(fluid_ounces_text)
                        except (ValueError, IndexError):
                            pass  # Fluid ounces not present or not in expected format
                        
                        logged_item = {
                            "Food Name": food_name,
                            "Date": target_date.strftime('%m/%d/%Y'),
                            "Meal": meal,
                            "Calories": calories,
                            "fluid_ounces_added": fluid_ounces_added
                            # Add other fields as needed
                        }
                        
                        logged_items.append(logged_item)
                        logger.debug(f"Fetched logged item: {logged_item}")
                    
                    except NoSuchElementException as e:
                        logger.warning(f"Failed to parse a food entry in meal '{meal}': {e}")
                        driver.save_screenshot(os.path.join(LOG_DIR, f"error_{meal}_food_entry.png"))
                    except Exception as e:
                        logger.warning(f"Unexpected error parsing food entry in meal '{meal}': {e}")
                        driver.save_screenshot(os.path.join(LOG_DIR, f"unexpected_error_{meal}_food_entry.png"))
            
            except TimeoutException:
                logger.warning(f"No items found for meal '{meal}' on date {target_date}.")
                driver.save_screenshot(os.path.join(LOG_DIR, f"no_items_{meal}.png"))
            except Exception as e:
                logger.error(f"Failed to process meal '{meal}': {e}", exc_info=True)
                driver.save_screenshot(os.path.join(LOG_DIR, f"error_{meal}.png"))

    except Exception as e:
        logger.error(f"An error occurred while fetching logged items: {e}", exc_info=True)

    logger.info(f"Fetched {len(logged_items)} logged items for date {target_date}.")
    return logged_items

def navigate_to_date(driver, target_date):
    """
    Navigates to the target date by clicking 'Next Day' or 'Previous Day' buttons.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        target_date (date): The date to navigate to.

    Returns:
        bool: True if navigation was successful, False otherwise.
    """
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
                    close_overlays(driver)
                    continue
            time.sleep(1)  # Wait for the date to update
            attempts += 1

        logger.error(f"Failed to navigate to target date {target_date} after {max_attempts} attempts.")
        return False
    except Exception as e:
        logger.error(f"An error occurred while navigating to date: {e}", exc_info=True)
        return False

def get_current_date(driver):
    """
    Retrieves the current date displayed in the Lose It! application.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.

    Returns:
        date: The current date displayed in the app.
    """
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
        driver.save_screenshot(os.path.join(LOG_DIR, "get_current_date_error.png"))
        return None

def close_overlays(driver):
    """
    Closes any overlays or popups that might be obstructing interactions.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
    """
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

# ----------------------- Main Execution -----------------------

def main():
    logger.info("Test Fetch Logged Items Script started.")
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

        # Step 3: Define dates to fetch (today and yesterday)
        dates_to_fetch = [date.today(), date.today() - timedelta(days=1)]

        for target_date in dates_to_fetch:
            logger.info(f"Fetching logged items for date: {target_date}")
            logged_items = fetch_logged_items(driver, target_date)
            logger.info(f"Logged items for {target_date}:")
            for item in logged_items:
                logger.info(item)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    finally:
        driver.quit()
        logger.info("WebDriver closed.")

if __name__ == "__main__":
    main()
