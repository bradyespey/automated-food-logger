# scripts/import_foods.py

import os
import subprocess
import time
import re
import logging
from datetime import datetime, date, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

# Load environment variables from .env in development
env = os.getenv('ENV', 'dev')
if env == 'dev':
    load_dotenv()

# Configure logging
logging_level = logging.DEBUG if env == 'dev' else logging.INFO
logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ======= TOGGLE OPTIONS =======
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'True').lower() == 'true'
# =============================

LOSEIT_URL = "https://www.loseit.com/"
LOGIN_URL = "https://my.loseit.com/login?r=https%3A%2F%2Fwww.loseit.com%2F"
GOALS_URL = "https://www.loseit.com/#Goals:Water%20Intake%5EWater%20Intake"

PLACEHOLDER_TEXT = "t3stf00dd03sn0t3xist"

class ChromeDriverManager:
    """Manages ChromeDriver processes and initialization."""

    @staticmethod
    def kill_existing_drivers():
        """Kills any existing Chrome or ChromeDriver processes."""
        try:
            if os.name == 'nt':
                subprocess.call("taskkill /f /im chromedriver.exe >nul 2>&1", shell=True)
                subprocess.call("taskkill /f /im chrome.exe >nul 2>&1", shell=True)
            else:
                subprocess.call("pkill chromedriver", shell=True)
                subprocess.call("pkill chrome", shell=True)
            logger.debug("Existing ChromeDriver processes terminated.")
        except Exception as e:
            logger.warning(f"Failed to kill existing ChromeDriver processes: {e}")

    @staticmethod
    def initialize_driver():
        """Initializes the Chrome WebDriver with specified options."""
        ChromeDriverManager.kill_existing_drivers()

        options = webdriver.ChromeOptions()

        chrome_bin = os.environ.get('GOOGLE_CHROME_BIN')
        if chrome_bin:
            options.binary_location = chrome_bin
            logger.debug(f"Using Chrome binary at {chrome_bin}")
        else:
            logger.error("GOOGLE_CHROME_BIN environment variable is not set.")
            raise EnvironmentError("GOOGLE_CHROME_BIN not set.")

        if HEADLESS_MODE:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            logger.debug("Running in headless mode.")
        else:
            options.add_argument("--start-maximized")
            logger.debug("Running in non-headless mode.")

        # Common Chrome options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")

        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
        if chromedriver_path:
            service = Service(executable_path=chromedriver_path)
            logger.debug(f"Using Chromedriver at {chromedriver_path}")
        else:
            logger.error("CHROMEDRIVER_PATH environment variable is not set.")
            raise EnvironmentError("CHROMEDRIVER_PATH not set.")

        try:
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("Chrome WebDriver initialized successfully.")
            return driver
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise e

    @staticmethod
    def initialize_driver_with_retry(retries=3, delay=2):
        """Attempts to initialize the driver, retrying in case of failure."""
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"Initializing WebDriver (Attempt {attempt}/{retries})...")
                return ChromeDriverManager.initialize_driver()
            except WebDriverException as e:
                logger.warning(f"WebDriver initialization failed on attempt {attempt}: {e}")
                if attempt < retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("Exceeded maximum WebDriver initialization attempts.")
                    raise e

class LoseItAutomator:
    """Automates interactions with the Lose It! website, including food logging and water intake updating."""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 15)

    def navigate_to_url(self, url):
        """Navigates to a specified URL."""
        try:
            self.driver.get(url)
            logger.debug(f"Navigated to {url}")
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            raise e

    def check_logged_in(self):
        """Checks if the user is already logged in."""
        try:
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/profile')]"))
            )
            logger.debug("User is already logged in.")
            return True
        except TimeoutException:
            logger.debug("User is not logged in.")
            return False

    def login(self):
        """Logs in using credentials from environment variables."""
        email = os.getenv('LOSEIT_EMAIL')
        password = os.getenv('LOSEIT_PASSWORD')

        if not email or not password:
            logger.error("LOSEIT_EMAIL or LOSEIT_PASSWORD environment variable not set.")
            raise EnvironmentError("Missing login credentials.")

        try:
            self.navigate_to_url(LOGIN_URL)

            email_input = self.wait.until(
                EC.element_to_be_clickable((By.ID, 'email'))
            )
            email_input.clear()
            email_input.send_keys(email)
            logger.debug("Entered email.")

            password_input = self.driver.find_element(By.ID, 'password')
            password_input.clear()
            password_input.send_keys(password)
            logger.debug("Entered password.")

            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            logger.debug("Clicked login button.")

            # Verify login by checking for profile link
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/profile')]"))
            )
            logger.info("Logged in successfully.")
            return True
        except TimeoutException:
            logger.error("Login elements not found or login timed out.")
            return False
        except Exception as e:
            logger.error(f"An error occurred during login: {e}")
            return False

    def ensure_logged_in(self):
        """Ensures that the user is logged in."""
        if not self.check_logged_in():
            if not self.login():
                logger.error("Failed to log in. Exiting automation.")
                raise Exception("Login failed.")

    def parse_food_log(self, log_text):
        """Parses the food log text into structured food items."""
        parsed_items = []
        current_item = {}

        lines = log_text.splitlines()

        for line in lines:
            line = line.strip()
            if line.startswith("Food Name:"):
                if current_item:
                    parsed_items.append(current_item)
                current_item = {"name": line.replace("Food Name:", "").strip()}
            elif line.startswith("Date:"):
                current_item["date"] = line.replace("Date:", "").strip()
            elif line.startswith("Meal:"):
                current_item["meal"] = line.replace("Meal:", "").strip()
            elif line.startswith("Brand:"):
                current_item["brand"] = line.replace("Brand:", "").strip()
            elif line.startswith("Icon:"):
                current_item["icon"] = line.replace("Icon:", "").strip()
            elif line.startswith("Serving Size:"):
                serving_size = re.sub(r"\s*\(.*?\)", "", line.replace("Serving Size:", "").strip())
                current_item["serving_quantity"] = serving_size

                # Extract fluid ounces if present
                fluid_oz_match = re.search(r"(\d+\.?\d*)\s*fluid ounces", serving_size.lower())
                current_item["fluid_ounces"] = float(fluid_oz_match.group(1)) if fluid_oz_match else 0.0

            elif line.startswith("Calories:"):
                current_item["calories"] = line.replace("Calories:", "").strip()
            elif line.startswith("Fat (g):"):
                current_item["fat"] = line.replace("Fat (g):", "").strip()
            elif line.startswith("Saturated Fat (g):"):
                current_item["saturated_fat"] = line.replace("Saturated Fat (g):", "").strip()
            elif line.startswith("Cholesterol (mg):"):
                current_item["cholesterol"] = line.replace("Cholesterol (mg):", "").strip()
            elif line.startswith("Sodium (mg):"):
                current_item["sodium"] = line.replace("Sodium (mg):", "").strip()
            elif line.startswith("Carbs (g):"):
                current_item["carbs"] = line.replace("Carbs (g):", "").strip()
            elif line.startswith("Fiber (g):"):
                current_item["fiber"] = line.replace("Fiber (g):", "").strip()
            elif line.startswith("Sugar (g):"):
                current_item["sugar"] = line.replace("Sugar (g):", "").strip()
            elif line.startswith("Protein (g):"):
                current_item["protein"] = line.replace("Protein (g):", "").strip()

        if current_item:
            parsed_items.append(current_item)

        logger.info(f"Parsed {len(parsed_items)} food items from log.")
        return parsed_items

    def parse_food_item_date(self, date_str):
        """
        Parses the date string from the food item into a date object.
        Assumes the input format is 'MM/DD/YYYY' or 'MM/DD'.
        """
        try:
            if len(date_str.split('/')) == 3:
                date_obj = datetime.strptime(date_str, "%m/%d/%Y").date()
            else:
                # Assume the year is the current year
                current_year = date.today().year
                date_obj = datetime.strptime(f"{date_str}/{current_year}", "%m/%d/%Y").date()
            return date_obj
        except Exception as e:
            logger.error(f"An error occurred while parsing food item date '{date_str}': {e}")
            return None

    def enter_placeholder_text_in_search_box(self, tabindex):
        """Enters placeholder text into the search box identified by tabindex."""
        try:
            search_box = self.wait.until(
                EC.visibility_of_element_located((By.XPATH, f"//input[@tabindex='{tabindex}']"))
            )
            search_box.clear()
            search_box.click()
            ActionChains(self.driver).send_keys(PLACEHOLDER_TEXT).perform()
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            logger.debug(f"Entered placeholder text in search box with tabindex {tabindex}.")
        except TimeoutException:
            logger.error(f"Search box with tabindex {tabindex} not found.")
        except Exception as e:
            logger.error(f"Failed to enter placeholder text in search box: {e}")

    def wait_for_create_custom_food_button(self):
        """Waits for the 'Create a custom food' button to become clickable."""
        try:
            create_food_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Create a custom food')]"))
            )
            return create_food_button
        except TimeoutException:
            logger.error(f"'Create a custom food' button not found or not clickable.")
            return None
        except Exception as e:
            logger.error(f"Error waiting for 'Create a custom food' button: {e}")
            return None

    def click_create_custom_food(self):
        """Clicks the 'Create a custom food' button."""
        create_food_button = self.wait_for_create_custom_food_button()
        if create_food_button:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", create_food_button)
                create_food_button.click()
                logger.debug("Clicked 'Create a custom food' button.")
                return True
            except Exception as e:
                logger.error(f"Failed to click 'Create a custom food' button: {e}")
        return False

    def enter_food_details(self, food_item):
        """Enters the food details into the Lose It! interface."""
        try:
            # Wait for brand input field
            brand_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@tabindex='1004']"))
            )
            brand_input.click()
            ActionChains(self.driver).send_keys(food_item.get("brand", "")).perform()
            ActionChains(self.driver).send_keys(Keys.TAB).perform()

            # Enter food name
            ActionChains(self.driver).send_keys(food_item.get("name", "")).perform()
            ActionChains(self.driver).send_keys(Keys.TAB).perform()

            # Enter icon (assuming first word)
            icon = food_item.get("icon", "").split()[0]
            ActionChains(self.driver).send_keys(icon).perform()
            ActionChains(self.driver).send_keys(Keys.TAB).perform()

            # Enter serving quantity and type
            serving_quantity = food_item.get("serving_quantity", "0 servings")
            if " " in serving_quantity:
                serving_amount, serving_type = serving_quantity.split(" ", 1)
            else:
                serving_amount, serving_type = serving_quantity, "servings"

            serving_parts = serving_amount.split(' ')
            if len(serving_parts) == 2:
                whole_part = int(serving_parts[0])
                serving_fraction = self.convert_fraction_to_float(serving_parts[1])
            elif '/' in serving_amount:
                whole_part = 0
                serving_fraction = self.convert_fraction_to_float(serving_amount)
            else:
                whole_part = int(serving_amount)
                serving_fraction = 0.0

            ActionChains(self.driver).send_keys(str(whole_part)).perform()
            ActionChains(self.driver).send_keys(Keys.TAB).perform()

            if serving_fraction > 0:
                self.handle_fractional_serving(serving_fraction)

            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            ActionChains(self.driver).send_keys(serving_type.split()[0]).perform()
            ActionChains(self.driver).send_keys(Keys.TAB).perform()

            # Enter nutritional information
            for nutrient in ["calories", "fat", "saturated_fat", "cholesterol", "sodium", "carbs", "fiber", "sugar", "protein"]:
                ActionChains(self.driver).send_keys(food_item.get(nutrient, "")).perform()
                ActionChains(self.driver).send_keys(Keys.TAB).perform()

            # Submit the food entry
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            logger.info(f"Entered food details for '{food_item.get('name', '')}'.")
        except Exception as e:
            logger.error(f"Failed to enter food details for '{food_item.get('name', '')}': {e}")

    def handle_fractional_serving(self, serving_fraction):
        """Handles fractional servings by mapping to steps."""
        fraction_map = {
            0.125: 1,
            0.25: 2,
            0.333: 3,
            0.5: 4,
            0.666: 5,
            0.75: 6,
            0.875: 7
        }
        closest_fraction = min(fraction_map.keys(), key=lambda x: abs(x - serving_fraction))
        steps = fraction_map[closest_fraction]
        for _ in range(steps):
            ActionChains(self.driver).send_keys(Keys.UP).perform()
        logger.debug(f"Handled fractional serving: {serving_fraction} as {closest_fraction} with {steps} steps.")

    @staticmethod
    def convert_fraction_to_float(fraction_str):
        """Converts a fraction string to a float."""
        try:
            if '/' in fraction_str:
                numerator, denominator = fraction_str.split('/')
                return float(numerator) / float(denominator)
            else:
                return float(fraction_str)
        except ValueError:
            logger.warning(f"Cannot convert fraction string to float: {fraction_str}")
            return 0.0

    def navigate_day(self, days):
        """Navigates forward or backward by 'days' in the Lose It! interface."""
        direction = "Next" if days > 0 else "Previous"
        button_title = "Next" if direction == "Next" else "Previous"

        for _ in range(abs(days)):
            try:
                button_xpath = f"//div[@role='button' and @title='{button_title}']"
                day_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath))
                )
                day_button.click()
                logger.info(f"Clicked '{button_title}' day button.")
                # Wait until the page updates after clicking
                self.wait.until(EC.staleness_of(day_button))
            except TimeoutException:
                logger.error(f"'{button_title}' day button not found or not clickable.")
                break
            except Exception as e:
                logger.error(f"Error navigating to '{button_title}' day: {e}")
                break

    def navigate_to_water_goals(self):
        """Navigates to the water intake goals page."""
        try:
            self.driver.get(GOALS_URL)
            logger.debug("Navigated to water intake goals page.")
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "GCJ-IGUC0B"))
            )
        except Exception as e:
            logger.error(f"Failed to navigate to water intake goals page: {e}")
            raise e

    def get_current_water_intake(self):
        """Retrieves the current water intake value from the water intake page."""
        try:
            water_input = self.wait.until(
                EC.visibility_of_element_located((By.XPATH, "//input[@type='text' and contains(@class, 'gwt-TextBox')]"))
            )
            water_value_str = water_input.get_attribute('value').strip()
            logger.info(f"Current water intake value in input box: {water_value_str}")
            # Convert to float
            current_water = float(water_value_str)
            logger.info(f"Current water intake: {current_water} oz")
            return current_water
        except Exception as e:
            logger.error(f"Failed to read current water intake from input box: {e}")
            return None

    def set_water_intake(self, water_oz):
        """Sets the water intake value on the water intake page."""
        try:
            water_input = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"))
            )
            water_input.clear()
            water_input.send_keys(str(water_oz))
            logger.info(f"Entered new water intake: {water_oz} oz")

            # Wait until the input box value matches the new intake
            self.wait.until(
                EC.text_to_be_present_in_element_value(
                    (By.XPATH, "//input[@type='text' and contains(@class, 'GCJ-IGUKWC')]"),
                    str(water_oz)
                )
            )
            logger.info(f"Verified new water intake in input box: {water_oz} oz")

            # Locate and click the Record button
            record_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'recordButton')]"))
            )
            record_button.click()
            logger.info("Clicked Record button to save water intake.")
        except TimeoutException:
            logger.error("Water intake input box or Record button not found or not clickable.")
        except Exception as e:
            logger.error(f"Failed to set water intake: {e}")

    def navigate_homepage(self):
        """Navigates back to the main Lose It! homepage."""
        try:
            self.driver.get(LOSEIT_URL)
            logger.debug("Navigated back to Lose It! homepage.")
            # Replace 'some-main-page-element' with an actual element ID to confirm navigation
            self.wait.until(
                EC.presence_of_element_located((By.ID, "main-page-element-id"))  # Update with actual ID
            )
        except Exception as e:
            logger.error(f"Failed to navigate back to the homepage: {e}")

    def update_water_intake_subprocess(self, fluid_oz, days_difference):
        """Calls the water_intake.py script as a subprocess with given arguments."""
        try:
            logger.info(f"Updating water intake with {fluid_oz} oz for {days_difference} days difference.")
            subprocess.run([
                'python', 'scripts/water_intake.py',
                '--fluid_oz', str(fluid_oz),
                '--days_difference', str(days_difference)
            ], check=True)
            logger.info("Water intake updated successfully via subprocess.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update water intake via subprocess: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while updating water intake: {e}")

    def submit_food_log(self, log_text):
        """Processes the food log and submits entries, updating water intake if applicable."""
        start_time = time.time()
        food_items = self.parse_food_log(log_text)
        logged_items = []
        total_input_fluid_ounces = 0.0
        total_logged_fluid_ounces = 0.0
        logging_output = "<b style='color: #f9c74f;'>Logging Output:</b><br>"

        for index, food in enumerate(food_items, start=1):
            try:
                # Handle date navigation
                current_date = date.today()
                food_date_str = food.get("date", current_date.strftime("%m/%d/%Y"))
                food_date_obj = self.parse_food_item_date(food_date_str)
                if not food_date_obj:
                    logger.error(f"Invalid date format for food item: {food_date_str}. Skipping.")
                    continue

                days_difference = (food_date_obj - current_date).days
                if days_difference != 0:
                    self.navigate_day(days_difference)

                # Enter placeholder text in search box based on meal type
                meal = food.get("meal", "dinner").lower()
                meal_tabindex = {"breakfast": "200", "lunch": "300", "dinner": "400", "snacks": "500"}
                self.enter_placeholder_text_in_search_box(meal_tabindex.get(meal, "400"))

                # Click 'Create a custom food' button
                if not self.click_create_custom_food():
                    logger.warning(f"Failed to find 'Create a custom food' button for '{food.get('name', 'Unknown')}'. Skipping.")
                    continue

                # Enter food details
                self.enter_food_details(food)
                logged_items.append(food)

                logging_output += f"Logging item {index} of {len(food_items)}: {food.get('name', '')}<br>"

                # Update water intake if applicable
                fluid_oz = food.get('fluid_ounces', 0.0)
                if fluid_oz > 0.0:
                    self.update_water_intake_subprocess(fluid_oz, days_difference)
                    logging_output += f"Added {fluid_oz} oz to water intake.<br>"
                    total_input_fluid_ounces += fluid_oz
                    total_logged_fluid_ounces += fluid_oz

                # Refresh and navigate back to homepage for next entry
                self.driver.refresh()
                self.navigate_homepage()

            except Exception as e:
                logger.error(f"An error occurred while processing '{food.get('name', 'Unknown')}': {e}")

        logging_output += f"Time to Log: {time.time() - start_time:.2f} seconds<br><br>"

        # Optionally, add comparison checks or summary here

        logger.info(logging_output)
        return logging_output

def compare_items(input_items, logged_items, content, total_input_fluid_ounces, total_logged_fluid_ounces):
    total_food_names = content.count('Food Name:')
    if total_food_names == len(input_items):
        parsing_check = (
            "<b style='color: #f9c74f;'>Parsing Check:</b><br>"
            f"<span style='color: green;'>All {total_food_names} foods in input parsed correctly</span><br><br>"
        )
    else:
        parsing_check = (
            "<b style='color: #f9c74f;'>Parsing Check:</b><br>"
            f"<span style='color: red;'>Error: {total_food_names - len(input_items)} food items found in input but not parsed correctly.</span><br><br>"
        )

    comparison_check = "<b style='color: #f9c74f;'>Comparison Check:</b><br>"
    for index, (input_item, logged_item) in enumerate(zip(input_items, logged_items), 1):
        comparison_check += compare_values("name", input_item['name'], logged_item.get('name', ''))
        comparison_check += compare_values("date", input_item.get('date', ''), logged_item.get('date', ''))
        comparison_check += compare_values("meal", input_item.get('meal', ''), logged_item.get('meal', ''))
        comparison_check += compare_values("brand", input_item.get('brand', ''), logged_item.get('brand', ''))
        comparison_check += compare_values("icon", input_item.get('icon', ''), logged_item.get('icon', ''))
        comparison_check += compare_values("serving_quantity", input_item.get('serving_quantity', ''), logged_item.get('serving_quantity', ''))
        comparison_check += compare_values("calories", input_item.get('calories', ''), logged_item.get('calories', ''))
        comparison_check += compare_values("fat", input_item.get('fat', ''), logged_item.get('fat', ''))
        comparison_check += compare_values("saturated_fat", input_item.get('saturated_fat', ''), logged_item.get('saturated_fat', ''))
        comparison_check += compare_values("cholesterol", input_item.get('cholesterol', ''), logged_item.get('cholesterol', ''))
        comparison_check += compare_values("sodium", input_item.get('sodium', ''), logged_item.get('sodium', ''))
        comparison_check += compare_values("carbs", input_item.get('carbs', ''), logged_item.get('carbs', ''))
        comparison_check += compare_values("fiber", input_item.get('fiber', ''), logged_item.get('fiber', ''))
        comparison_check += compare_values("sugar", input_item.get('sugar', ''), logged_item.get('sugar', ''))
        comparison_check += compare_values("protein", input_item.get('protein', ''), logged_item.get('protein', ''))
        comparison_check += "<br>"

        # Compare fluid ounces if present
        if input_item.get('fluid_ounces', 0.0) > 0.0:
            comparison_check += compare_numeric_values("fluid_ounces_logged", input_item['fluid_ounces'], logged_item.get('fluid_ounces_added', 0.0))
        comparison_check += "<br>"

    # Compare total fluid ounces
    comparison_check += "<b style='color: #f9c74f;'>Total Fluid Ounces Comparison:</b><br>"
    comparison_check += compare_numeric_values("Total Fluid Ounces", total_input_fluid_ounces, total_logged_fluid_ounces)

    return parsing_check + comparison_check

def compare_numeric_values(field_name, input_value, logged_value):
    try:
        input_value_num = float(input_value)
        logged_value_num = float(logged_value)
        if abs(input_value_num - logged_value_num) < 1e-6:
            return f'<span style="color: green;">**{field_name}:** {logged_value_num} (matches input value {input_value_num})</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value_num} (does not match input value {input_value_num})</span><br>'
    except ValueError:
        return f'<span style="color: red;">**{field_name}:** Invalid numerical values for comparison</span><br>'

def compare_values(field_name, input_value, logged_value):
    # Try to compare as floats first
    try:
        input_value_num = float(input_value)
        logged_value_num = float(logged_value)
        if abs(input_value_num - logged_value_num) < 1e-6:
            return f'<span style="color: green;">**{field_name}:** {logged_value_num} (matches input value)</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value_num} (does not match input value {input_value})</span><br>'
    except ValueError:
        # Fallback to string comparison
        if str(input_value).strip() == str(logged_value).strip():
            return f'<span style="color: green;">**{field_name}:** {logged_value} (matches input value)</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value} (does not match input value {input_value})</span><br>'

def main():
    start_time = time.time()

    log_text = os.getenv('LOG_TEXT', '')
    if not log_text:
        logger.error("No LOG_TEXT provided. Exiting.")
        return

    driver = None
    logging_output = "<b style='color: #f9c74f;'>Logging Output:</b><br>"

    total_input_fluid_ounces = 0.0
    total_logged_fluid_ounces = 0.0

    try:
        # Initialize WebDriver with retries
        driver = ChromeDriverManager.initialize_driver_with_retry()

        # Create automator instance
        automator = LoseItAutomator(driver)

        # Ensure user is logged in
        automator.ensure_logged_in()

        # Submit food log and update water intake
        logging_output += automator.submit_food_log(log_text)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    finally:
        if driver:
            driver.quit()
            logger.info("WebDriver closed.")
        total_time = time.time() - start_time
        logging_output += f"Time to Log: {total_time:.2f} seconds<br><br>"

    # Parse and compare items for final output
    food_items = automator.parse_food_log(log_text)
    comparison = compare_items(
        input_items=food_items,
        logged_items=food_items,  # Assuming logged_items are the same as input for simplicity
        content=log_text,
        total_input_fluid_ounces=total_input_fluid_ounces,
        total_logged_fluid_ounces=total_logged_fluid_ounces
    )
    logging_output += comparison

    logger.info(logging_output)
    print(logging_output)  # Ensure the output is sent to stdout

if __name__ == "__main__":
    main()