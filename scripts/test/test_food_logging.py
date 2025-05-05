# scripts/test/test_food_logging.py


import os
import time
import logging
from datetime import datetime, date, timedelta
from fractions import Fraction
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
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

TXT_FILE_PATH = "/Users/bradyespey/Projects/LoseIt/txt/nutritional_data.txt"
if not os.path.exists(TXT_FILE_PATH):
    raise FileNotFoundError(f"Nutritional data file not found at: {TXT_FILE_PATH}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler(os.path.join(LOG_DIR, "test_food_logging.log"))  # Log to a file in /tmp
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
            options.add_argument("--headless=new")  # Use "--headless=new" for newer Chrome versions
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

        # Verify email input exists
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

        return True
    except Exception as e:
        logger.error(f"An error occurred during login: {e}", exc_info=True)
        return False

def verify_login(driver):
    """
    Verifies that the user is logged in by checking for the current date on the homepage.
    """
    try:
        # Adjust the class name based on the provided HTML snippet
        current_date_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "GCJ-IGUD0B"))
        )
        current_date_text = current_date_element.text.strip()
        logger.info(f"Current date found: {current_date_text}")
        return True
    except TimeoutException:
        logger.error("Login may have failed; current date not found on home page.")
        # Optional: Take a screenshot for debugging
        driver.save_screenshot(os.path.join(LOG_DIR, "verify_login_timeout.png"))
        return False

def get_current_date(driver):
    """
    Retrieves the current date displayed in the Lose It! application.
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
        return None

def parse_food_item_date(date_str):
    """
    Parses the date string from the food item into a date object.
    """
    try:
        # Assume the year is the current year
        current_year = date.today().year
        date_obj = datetime.strptime(f"{date_str}/{current_year}", '%m/%d/%Y').date()
        return date_obj
    except Exception as e:
        logger.error(f"An error occurred while parsing food item date '{date_str}': {e}", exc_info=True)
        return None

def navigate_to_date(driver, target_date):
    """
    Navigates to the target date by clicking 'Next Day' or 'Previous Day' buttons.
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
    """
    Closes any overlays or popups that might be obstructing interactions.
    """
    try:
        # Look for common overlay elements and attempt to close them
        # This may need to be adjusted based on actual overlay structures
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
    """
    Selects the 'search & add food' box for the specified meal.
    """
    try:
        # Define the tabindex based on the meal
        tabindex_map = {
            "Breakfast": "200",
            "Lunch": "300",
            "Dinner": "400",
            "Snacks": "500"
        }
        tabindex = tabindex_map.get(meal_name, "400")  # Default to Dinner if not found

        # Locate the search input using the tabindex
        search_input_xpath = f"//input[@tabindex='{tabindex}']"
        search_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, search_input_xpath))
        )
        logger.info(f"Located search box for '{meal_name}'.")
        return search_input
    except TimeoutException:
        logger.error(f"Search input for meal '{meal_name}' not found or not clickable.")
        # Optional: Take a screenshot for debugging
        driver.save_screenshot(os.path.join(LOG_DIR, f"select_search_box_{meal_name}_timeout.png"))

        return None
    except Exception as e:
        logger.error(f"An error occurred while selecting search box for meal '{meal_name}': {e}", exc_info=True)
        return None

def enter_placeholder_text(driver, search_input, placeholder_text):
    """
    Enters the placeholder text into the search box to trigger the 'Create a custom food' button.
    """
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
    """
    Waits until the 'fixedGlass' overlay is no longer visible.
    """
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
    """
    Clicks the 'Create a custom food' button.
    """
    try:
        # Define the XPath for the 'Create a custom food' button
        create_food_button_xpath = "//div[contains(@class, 'gwt-HTML') and normalize-space(text())='Create a custom food']"

        # Wait until 'fixedGlass' is invisible to ensure no overlay is blocking the click
        fixed_glass_invisible = wait_for_fixed_glass_invisibility(driver)
        if not fixed_glass_invisible:
            logger.error("Cannot proceed to click 'Create a custom food' due to 'fixedGlass' overlay.")
            return False

        # Locate the 'Create a custom food' button
        create_food_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, create_food_button_xpath))
        )
        # Scroll into view and click
        driver.execute_script("arguments[0].scrollIntoView(true);", create_food_button)
        create_food_button.click()
        logger.info("Clicked 'Create a custom food' button.")
        return True
    except TimeoutException:
        logger.error("Create Food button not found or not clickable.")
        # Optional: Take a screenshot for debugging
        driver.save_screenshot(os.path.join(LOG_DIR, "click_create_food_timeout.png"))
        return False
    except ElementClickInterceptedException as e:
        logger.error(f"Element click intercepted: {e}")
        # Optional: Attempt to click via JavaScript as a workaround
        try:
            create_food_button = driver.find_element(By.XPATH, create_food_button_xpath)
            driver.execute_script("arguments[0].click();", create_food_button)
            logger.info("Clicked 'Create a custom food' button via JavaScript.")
            return True
        except Exception as ex:
            logger.error(f"Failed to click 'Create a custom food' button via JavaScript: {ex}", exc_info=True)
            driver.save_screenshot(os.path.join(LOG_DIR, "click_create_food_js_timeout.png"))
            return False
    except Exception as e:
        logger.error(f"An error occurred while clicking 'Create a custom food' button: {e}", exc_info=True)
        return False

def handle_fractional_serving(actions, fraction_str):
    """
    Handles entering fractional serving sizes using up arrow keys.
    """
    try:
        fraction_to_up_arrows = {
            '1/8': 1,
            '1/4': 2,
            '1/3': 3,
            '1/2': 4,
            '2/3': 5,
            '3/4': 6,
            '7/8': 7
        }
        up_arrow_presses = fraction_to_up_arrows.get(fraction_str)
        if up_arrow_presses:
            for _ in range(up_arrow_presses):
                actions.send_keys(Keys.ARROW_UP).perform()
                time.sleep(0.1)  # Small delay between key presses
            logger.info(f"Selected fractional serving: {fraction_str}")
        else:
            logger.warning(f"Unhandled serving fraction: {fraction_str}")
        actions.send_keys(Keys.TAB).perform()
    except Exception as e:
        logger.error(f"An error occurred while handling fractional serving: {e}", exc_info=True)
        actions.send_keys(Keys.TAB).perform()

def parse_serving_amount(serving_amount_str):
    """
    Parses the serving amount string and returns whole number and fraction.
    """
    try:
        # Remove any parentheses or additional text
        serving_amount_str = serving_amount_str.strip()
        if '(' in serving_amount_str:
            serving_amount_str = serving_amount_str.split('(')[0].strip()
        
        # Check if the amount is a mixed number (e.g., "3 1/2")
        if ' ' in serving_amount_str:
            whole_part_str, fraction_part_str = serving_amount_str.split(' ', 1)
            whole_part = int(whole_part_str)
            fraction_part = Fraction(fraction_part_str)
        elif '/' in serving_amount_str:
            # It's a fraction like '1/2'
            fraction_part = Fraction(serving_amount_str)
            whole_part = 0
        else:
            # Parse as decimal
            amount_float = float(serving_amount_str)
            whole_part = int(amount_float)
            fractional_value = amount_float - whole_part
            if fractional_value > 0:
                fraction_part = Fraction(fractional_value).limit_denominator(8)
            else:
                fraction_part = Fraction(0)
        return whole_part, fraction_part
    except Exception as e:
        logger.error(f"Error parsing serving amount '{serving_amount_str}': {e}", exc_info=True)
        return None, None

def round_fraction_to_nearest_common(fraction):
    """
    Rounds a fraction to the nearest common fraction from the provided list.
    """
    common_fractions = {
        Fraction(1, 8): '1/8',
        Fraction(1, 4): '1/4',
        Fraction(1, 3): '1/3',
        Fraction(1, 2): '1/2',
        Fraction(2, 3): '2/3',
        Fraction(3, 4): '3/4',
        Fraction(7, 8): '7/8',
    }
    min_diff = None
    nearest_fraction = None
    for cf, cf_str in common_fractions.items():
        diff = abs(fraction - cf)
        if min_diff is None or diff < min_diff:
            min_diff = diff
            nearest_fraction = cf_str
    logger.info(f"Rounded fraction {fraction} to nearest common fraction: {nearest_fraction}")
    return nearest_fraction

def enter_food_details(driver, food_item):
    """
    Enters the food details into the custom food form.
    """
    try:
        # Wait for the form to load
        brand_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@tabindex='1004']"))
        )
        actions = ActionChains(driver)
        time.sleep(0.5)

        # Brand
        brand = food_item.get("Brand", "")
        actions.click(brand_input).send_keys(brand).perform()
        actions.send_keys(Keys.TAB).perform()

        # Food Name
        food_name = food_item.get("Food Name", "")
        actions.send_keys(food_name).perform()
        actions.send_keys(Keys.TAB).perform()

        # Icon
        icon = food_item.get("Icon", "")
        if icon:
            icon_first_word = icon.split()[0]
            actions.send_keys(icon_first_word).perform()
            actions.send_keys(Keys.TAB).perform()
        else:
            actions.send_keys(Keys.TAB).perform()

        # Serving Quantity
        serving_size = food_item.get("Serving Size", "")
        if serving_size:
            try:
                # Split the serving size into amount and type
                serving_amount_str, serving_type = serving_size.split(" ", 1)
                serving_amount_str = serving_amount_str.strip()
                serving_type = serving_type.strip()

                # Parse serving amount
                whole_part, fraction_part = parse_serving_amount(serving_amount_str)
                if whole_part is None:
                    raise ValueError(f"Unable to parse serving amount '{serving_amount_str}'")

                logger.info(f"Parsed serving amount: whole_part={whole_part}, fraction_part={fraction_part}")

                # Enter whole part
                actions.send_keys(str(whole_part)).perform()
                actions.send_keys(Keys.TAB).perform()

                # Handle fractional serving
                if fraction_part > 0:
                    # Round to nearest common fraction
                    fraction_str = round_fraction_to_nearest_common(fraction_part)
                    if fraction_str:
                        handle_fractional_serving(actions, fraction_str)
                    else:
                        # If no matching common fraction, skip fractional part
                        logger.warning(f"No matching common fraction for {fraction_part}")
                        actions.send_keys(Keys.TAB).perform()
                else:
                    # No fractional part
                    actions.send_keys(Keys.TAB).perform()

                # Serving Type
                serving_type_first_word = serving_type.split()[0]
                actions.send_keys(serving_type_first_word).perform()
                actions.send_keys(Keys.TAB).perform()
            except Exception as e:
                logger.error(f"Error parsing serving size '{serving_size}': {e}", exc_info=True)
                # Skip serving size inputs if parsing fails
                actions.send_keys(Keys.TAB).perform()
                actions.send_keys(Keys.TAB).perform()
                actions.send_keys(Keys.TAB).perform()
        else:
            # Skip serving size inputs if not provided
            actions.send_keys(Keys.TAB).perform()
            actions.send_keys(Keys.TAB).perform()
            actions.send_keys(Keys.TAB).perform()

        # Nutritional Information
        nutrition_fields = [
            ("Calories", "Calories"),
            ("Fat (g)", "Fat"),
            ("Saturated Fat (g)", "Saturated Fat"),
            ("Cholesterol (mg)", "Cholesterol"),
            ("Sodium (mg)", "Sodium"),
            ("Carbs (g)", "Carbohydrates"),
            ("Fiber (g)", "Fiber"),
            ("Sugar (g)", "Sugars"),
            ("Protein (g)", "Protein"),
        ]

        for field_key, field_name in nutrition_fields:
            value = food_item.get(field_key, "")
            if value:
                actions.send_keys(str(value)).perform()
            actions.send_keys(Keys.TAB).perform()

        logger.info("Entered food details successfully.")
        return True
    except Exception as e:
        logger.error(f"An error occurred while entering food details: {e}", exc_info=True)
        return False

def save_food(driver):
    """
    Clicks the 'Add Food' button to save the custom food.
    """
    try:
        # Locate the 'Add Food' button
        add_food_button_xpath = "//div[@tabindex='1020' and contains(@class, 'addFoodToLog')]"
        add_food_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, add_food_button_xpath))
        )
        add_food_button.click()
        logger.info("Clicked 'Add Food' button to save the custom food.")
        return True
    except Exception as e:
        logger.error(f"An error occurred while clicking 'Add Food' button: {e}", exc_info=True)
        driver.save_screenshot(os.path.join(LOG_DIR, "save_food_error.png"))
        return False

def parse_food_items(filename):
    """
    Parses the food items from the given text file.

    Args:
        filename (str): Path to the text file containing food data.

    Returns:
        list: List of dictionaries representing the food items.
    """
    food_items = []
    current_food = {}
    try:
        with open(filename, 'r') as file:
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
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
    except Exception as e:
        logger.error(f"Error reading nutritional data file: {e}", exc_info=True)
    return food_items

# ----------------------- Main Execution -----------------------

def main():
    logger.info("Script started.")
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
            food_items = parse_food_items(TXT_FILE_PATH)  # Pass the path, not a file object
            logger.info(f"Parsed {len(food_items)} food items from the text file.")

        # Process each food item
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

            # Navigate to the target date
            date_navigated = navigate_to_date(driver, target_date)
            if not date_navigated:
                logger.error(f"Failed to navigate to date {target_date}. Skipping food item.")
                continue

            # Get the meal name
            meal_name = food_item.get("Meal", "Dinner")
            # Select the search box for the meal
            search_input = select_search_box(driver, meal_name)
            if not search_input:
                logger.error(f"Failed to locate '{meal_name}' search box. Skipping food item.")
                continue

            # Enter placeholder text to trigger 'Create a custom food' button
            placeholder_text = "pjzFqiRjygwY"
            placeholder_entered = enter_placeholder_text(driver, search_input, placeholder_text)
            if not placeholder_entered:
                logger.error("Failed to enter placeholder text. Skipping food item.")
                continue

            # Click the 'Create a custom food' button
            create_food_clicked = click_create_custom_food(driver)
            if not create_food_clicked:
                logger.error("Failed to click 'Create a custom food' button. Skipping food item.")
                continue

            # Enter food details
            food_details_entered = enter_food_details(driver, food_item)
            if not food_details_entered:
                logger.error("Failed to enter food details. Skipping food item.")
                continue

            # Save the food
            food_saved = save_food(driver)
            if not food_saved:
                logger.error("Failed to save the food. Skipping food item.")
                continue

            # Close any overlays or popups after saving
            close_overlays(driver)

            logger.info(f"Successfully logged food item: {food_item.get('Food Name', 'Unknown')}")

            # Optional: Wait before processing the next food item
            time.sleep(2)

        logger.info("All food items processed.")
        logger.info("Script completed successfully.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    finally:
        driver.quit()
        logger.info("WebDriver closed.")

if __name__ == "__main__":
    main()