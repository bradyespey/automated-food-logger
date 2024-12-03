# scripts/food_entry.py

import logging
import os
from fractions import Fraction
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
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
        logging.FileHandler(os.path.join(LOG_DIR, "food_entry.log"))
    ]
)
logger = logging.getLogger(__name__)

def parse_serving_amount(serving_amount_str):
    """
    Parses the serving amount string and returns whole number and fraction.

    Args:
        serving_amount_str (str): The serving amount string (e.g., "3 1/2").

    Returns:
        tuple: (whole_part (int), fraction_part (Fraction))
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

    Args:
        fraction (Fraction): The fraction to round.

    Returns:
        str: The nearest common fraction as a string.
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
    logger.debug(f"Rounded fraction {fraction} to nearest common fraction: {nearest_fraction}")
    return nearest_fraction

def handle_fractional_serving(actions, fraction_str):
    """
    Handles entering fractional serving sizes using up arrow keys.

    Args:
        actions (ActionChains): The Selenium ActionChains instance.
        fraction_str (str): The fractional serving string (e.g., "1/2").
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
            logger.debug(f"Selected fractional serving: {fraction_str}")
        else:
            logger.warning(f"Unhandled serving fraction: {fraction_str}")
        actions.send_keys(Keys.TAB).perform()
    except Exception as e:
        logger.error(f"An error occurred while handling fractional serving: {e}", exc_info=True)
        actions.send_keys(Keys.TAB).perform()

def enter_food_details(driver, food_item):
    """
    Enters the food details into the custom food form.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        food_item (dict): Dictionary containing food item details.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Wait for the form to load and locate the brand input
        brand_input_xpath = "//input[@tabindex='1004']"
        brand_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, brand_input_xpath))
        )
        actions = ActionChains(driver)

        # Brand
        brand = food_item.get("Brand", "")
        if brand:
            actions.click(brand_input).send_keys(brand).perform()
            logger.debug(f"Entered brand: {brand}")
        else:
            logger.debug("No brand provided; skipping brand entry.")
        actions.send_keys(Keys.TAB).perform()

        # Food Name
        food_name = food_item.get("Food Name", "")
        if food_name:
            actions.send_keys(food_name).perform()
            logger.debug(f"Entered food name: {food_name}")
        else:
            logger.warning("No food name provided; skipping food name entry.")
        actions.send_keys(Keys.TAB).perform()

        # Icon (if applicable)
        icon = food_item.get("Icon", "")
        if icon:
            icon_first_word = icon.split()[0]
            actions.send_keys(icon_first_word).perform()
            logger.debug(f"Entered icon first word: {icon_first_word}")
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

                logger.debug(f"Parsed serving amount: whole_part={whole_part}, fraction_part={fraction_part}")

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
                        logger.warning(f"No matching common fraction for {fraction_part}; skipping fractional serving.")
                        actions.send_keys(Keys.TAB).perform()
                else:
                    # No fractional part
                    actions.send_keys(Keys.TAB).perform()

                # Serving Type
                serving_type_first_word = serving_type.split()[0]
                actions.send_keys(serving_type_first_word).perform()
                logger.debug(f"Entered serving type: {serving_type_first_word}")
                actions.send_keys(Keys.TAB).perform()
            except ValueError as ve:
                logger.error(f"ValueError while parsing serving size '{serving_size}': {ve}", exc_info=True)
                # Skip serving size inputs if parsing fails
                for _ in range(3):
                    actions.send_keys(Keys.TAB).perform()
            except Exception as e:
                logger.error(f"Unexpected error while parsing serving size '{serving_size}': {e}", exc_info=True)
                # Skip serving size inputs if parsing fails
                for _ in range(3):
                    actions.send_keys(Keys.TAB).perform()
        else:
            # Skip serving size inputs if not provided
            logger.debug("No serving size provided; skipping serving size entry.")
            for _ in range(3):
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
                logger.debug(f"Entered {field_name}: {value}")
            else:
                logger.debug(f"No value provided for {field_name}; skipping entry.")
            actions.send_keys(Keys.TAB).perform()

        logger.debug("Entered food details successfully.")
        return True
    except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
        logger.error(f"Exception during entering food details: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error during entering food details: {e}", exc_info=True)
        return False


def save_food(driver):
    """
    Clicks the 'Add Food' button to save the custom food.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.

    Returns:
        bool: True if the button was clicked successfully, False otherwise.
    """
    try:
        # Locate the 'Add Food' button
        add_food_button_xpath = "//div[@tabindex='1020' and contains(@class, 'addFoodToLog')]"
        add_food_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, add_food_button_xpath))
        )
        add_food_button.click()
        logger.debug("Clicked 'Add Food' button to save the custom food.")
        return True
    except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
        logger.error(f"Exception while clicking 'Add Food' button: {e}", exc_info=True)
        driver.save_screenshot(os.path.join(LOG_DIR, "save_food_error.png"))
        return False
    except Exception as e:
        logger.error(f"Unexpected error while clicking 'Add Food' button: {e}", exc_info=True)
        driver.save_screenshot(os.path.join(LOG_DIR, "save_food_error.png"))
        return False