# temp_script.py

import os
import time
import logging
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Loaded .env file from {dotenv_path}")
else:
    logger.error(".env file not found. Ensure that a .env file exists with LOSEIT_EMAIL and LOSEIT_PASSWORD.")
    exit(1)

def initialize_driver(headless=False):
    """
    Initializes the Chrome WebDriver with specified options.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
    else:
        chrome_options.add_argument("--start-maximized")  # For visual debugging

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize Chrome WebDriver using webdriver-manager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    logger.info("Chrome WebDriver initialized.")
    return driver

def login(driver, email, password):
    """
    Logs into the Lose It! account using provided credentials.
    """
    try:
        login_url = "https://my.loseit.com/login?r=https%3A%2F%2Fwww.loseit.com%2F"
        driver.get(login_url)
        logger.info("Navigated to login page.")

        # Wait for the email input field to be present and enter email
        email_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, 'email'))
        )
        email_input.clear()
        email_input.send_keys(email)
        logger.info("Entered email.")

        # Wait for the password input field to be present and enter password
        password_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, 'password'))
        )
        password_input.clear()
        password_input.send_keys(password)
        logger.info("Entered password.")

        # Locate and click the login button
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
        login_button.click()
        logger.info("Clicked login button.")

        # Wait until the 'Next Day' navigation button is present to confirm successful login
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'nextArrowButton') and @role='button' and @title='Next']"))
        )
        logger.info("Login successful. 'Next Day' button found.")

    except TimeoutException:
        logger.error("Timeout while trying to log in or find the 'Next Day' button. Please check your selectors or network connection.")
        driver.quit()
        raise
    except Exception as e:
        logger.error(f"An error occurred during login: {e}")
        driver.quit()
        raise

def get_displayed_date(driver):
    """
    Retrieves the current date displayed on the page.
    """
    try:
        # XPath based on provided HTML snippet
        # Adjust if the actual structure differs
        date_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'gwt-HTML') and contains(@class, 'GCJ-IGUD0B')]"))
        )
        date_text = date_element.text.replace("\xa0", " ")  # Replace non-breaking space
        logger.info(f"Displayed date on website: {date_text}")
        # Parse date, e.g., "Monday Dec 02, 2024"
        displayed_date = datetime.strptime(date_text, "%A %b %d, %Y")
        return displayed_date
    except TimeoutException:
        logger.error("Timeout while trying to retrieve the displayed date.")
        raise
    except Exception as e:
        logger.error(f"Error retrieving displayed date: {e}")
        raise

def navigate_day(driver, direction='next'):
    """
    Navigates forward or backward by one day.

    :param driver: Selenium WebDriver instance.
    :param direction: 'next' to navigate forward, 'previous' to navigate backward.
    """
    try:
        if direction == 'next':
            button_xpath = "//div[contains(@class, 'nextArrowButton') and @role='button' and @title='Next']"
            action = "Navigating to the next day."
        elif direction == 'previous':
            button_xpath = "//div[contains(@class, 'prevArrowButton') and @role='button' and @title='Previous']"
            action = "Navigating to the previous day."
        else:
            logger.error("Invalid direction specified. Use 'next' or 'previous'.")
            return

        logger.info(action)

        # Wait for the navigation button to be clickable
        nav_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, button_xpath))
        )

        # Scroll into view and click
        driver.execute_script("arguments[0].scrollIntoView(true);", nav_button)
        nav_button.click()
        logger.info(f"Clicked the '{direction}' day button.")

        # Short pause to allow for the navigation effect
        time.sleep(1)

    except TimeoutException:
        logger.error(f"Timeout while trying to click the '{direction}' day button.")
        raise
    except ElementClickInterceptedException:
        logger.error(f"ElementClickInterceptedException: Could not click the '{direction}' day button.")
        raise
    except Exception as e:
        logger.error(f"An error occurred while navigating '{direction}' day: {e}")
        raise

def log_food(driver, food_details):
    """
    Logs a food item on the current day.

    :param driver: Selenium WebDriver instance.
    :param food_details: Dictionary containing food details.
    """
    try:
        logger.info("Attempting to log food item.")

        # Locate and click the 'Log Food' button
        log_food_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log Food')]"))
        )
        log_food_button.click()
        logger.info("Clicked 'Log Food' button.")

        # Wait for the food logging modal/form to appear
        # Update the XPath based on the actual modal structure
        # Example: Assuming the form has a specific class or identifier
        food_form = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'food-log-modal') or contains(@class, 'food-log-form')]"))
        )
        logger.info("Food logging form appeared.")

        # Fill out the form fields
        # Replace 'name' attributes with actual names from the form
        # Example fields based on provided details

        # Enter Meal
        meal_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, 'meal'))
        )
        meal_input.clear()
        meal_input.send_keys(food_details['Meal'])
        logger.info(f"Entered Meal: {food_details['Meal']}")

        # Enter Brand
        brand_input = driver.find_element(By.NAME, 'brand')
        brand_input.clear()
        brand_input.send_keys(food_details['Brand'])
        logger.info(f"Entered Brand: {food_details['Brand']}")

        # Enter Icon
        icon_input = driver.find_element(By.NAME, 'icon')
        icon_input.clear()
        icon_input.send_keys(food_details['Icon'])
        logger.info(f"Entered Icon: {food_details['Icon']}")

        # Enter Serving Size
        serving_size_input = driver.find_element(By.NAME, 'servingSize')
        serving_size_input.clear()
        serving_size_input.send_keys(food_details['Serving Size'])
        logger.info(f"Entered Serving Size: {food_details['Serving Size']}")

        # Enter Calories
        calories_input = driver.find_element(By.NAME, 'calories')
        calories_input.clear()
        calories_input.send_keys(food_details['Calories'])
        logger.info(f"Entered Calories: {food_details['Calories']}")

        # Enter Fat
        fat_input = driver.find_element(By.NAME, 'fat')
        fat_input.clear()
        fat_input.send_keys(food_details['Fat (g)'])
        logger.info(f"Entered Fat: {food_details['Fat (g)']}g")

        # Enter Saturated Fat
        sat_fat_input = driver.find_element(By.NAME, 'saturatedFat')
        sat_fat_input.clear()
        sat_fat_input.send_keys(food_details['Saturated Fat (g)'])
        logger.info(f"Entered Saturated Fat: {food_details['Saturated Fat (g)']}g")

        # Enter Cholesterol
        cholesterol_input = driver.find_element(By.NAME, 'cholesterol')
        cholesterol_input.clear()
        cholesterol_input.send_keys(food_details['Cholesterol (mg)'])
        logger.info(f"Entered Cholesterol: {food_details['Cholesterol (mg)']}mg")

        # Enter Sodium
        sodium_input = driver.find_element(By.NAME, 'sodium')
        sodium_input.clear()
        sodium_input.send_keys(food_details['Sodium (mg)'])
        logger.info(f"Entered Sodium: {food_details['Sodium (mg)']}mg")

        # Enter Carbs
        carbs_input = driver.find_element(By.NAME, 'carbs')
        carbs_input.clear()
        carbs_input.send_keys(food_details['Carbs (g)'])
        logger.info(f"Entered Carbs: {food_details['Carbs (g)']}g")

        # Enter Fiber
        fiber_input = driver.find_element(By.NAME, 'fiber')
        fiber_input.clear()
        fiber_input.send_keys(food_details['Fiber (g)'])
        logger.info(f"Entered Fiber: {food_details['Fiber (g)']}g")

        # Enter Sugar
        sugar_input = driver.find_element(By.NAME, 'sugar')
        sugar_input.clear()
        sugar_input.send_keys(food_details['Sugar (g)'])
        logger.info(f"Entered Sugar: {food_details['Sugar (g)']}g")

        # Enter Protein
        protein_input = driver.find_element(By.NAME, 'protein')
        protein_input.clear()
        protein_input.send_keys(food_details['Protein (g)'])
        logger.info(f"Entered Protein: {food_details['Protein (g)']}g")

        # Locate and click the 'Save' or 'Submit' button to log the food
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save') or contains(text(), 'Submit')]")
        save_button.click()
        logger.info("Clicked 'Save' button to log the food item.")

        # Wait for the form/modal to disappear, indicating successful logging
        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'food-log-modal') or contains(@class, 'food-log-form')]"))
        )
        logger.info("Food item logged successfully.")

    except Exception as e:
        logger.error(f"An error occurred while logging food: {e}")
        # Optionally, capture a screenshot for debugging
        driver.save_screenshot('error_log_food.png')
        logger.info("Screenshot saved as 'error_log_food.png'.")
        raise

def main():
    # Define the target date and food details
    target_date_str = '12/3/2024'  # MM/DD/YYYY format
    target_date = datetime.strptime(target_date_str, "%m/%d/%Y")

    food_details = {
        'Meal': 'Snacks',
        'Brand': 'Modelo',
        'Icon': 'Beer',
        'Serving Size': '12 fluid ounces',
        'Calories': '600',
        'Fat (g)': '2',
        'Saturated Fat (g)': '3.5',
        'Cholesterol (mg)': '4.25',
        'Sodium (mg)': '45',
        'Carbs (g)': '45',
        'Fiber (g)': '17',
        'Sugar (g)': '0',
        'Protein (g)': '6'
    }

    # Retrieve credentials from .env file
    email = os.getenv('LOSEIT_EMAIL')
    password = os.getenv('LOSEIT_PASSWORD')

    if not email or not password:
        logger.error("LOSEIT_EMAIL and LOSEIT_PASSWORD environment variables must be set.")
        return

    logger.info("Credentials loaded from .env file.")

    # Initialize WebDriver (set headless=False to see the browser actions)
    driver = initialize_driver(headless=False)

    try:
        # Perform login
        login(driver, email, password)

        # Get the displayed date from the website
        displayed_date = get_displayed_date(driver)
        delta_days = (target_date - displayed_date).days

        logger.info(f"Today's Date: {displayed_date.strftime('%m/%d/%Y')}")
        logger.info(f"Target Date: {target_date.strftime('%m/%d/%Y')}")
        logger.info(f"Days to navigate: {delta_days}")

        # Navigate to the target date
        if delta_days > 0:
            for _ in range(delta_days):
                navigate_day(driver, direction='next')
        elif delta_days < 0:
            for _ in range(abs(delta_days)):
                navigate_day(driver, direction='previous')
        else:
            logger.info("Already on the target date. No navigation needed.")

        # Log the food item on the target date
        log_food(driver, food_details)

        # Pause to observe the browser
        logger.info("Food logging completed. Pausing to observe the browser...")
        time.sleep(10)  # Adjust the sleep time as needed

    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}")
    finally:
        # Close the browser
        driver.quit()
        logger.info("WebDriver closed.")

if __name__ == "__main__":
    main()