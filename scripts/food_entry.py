# scripts/food_entry.py

import logging
from fractions import Fraction
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scripts.logging_setup import get_logger
from scripts.decorators import retry_on_failure

logger = get_logger("food_entry")

def parse_serving_amount(serving_amount_str):
    try:
        serving_amount_str = serving_amount_str.strip()
        if '(' in serving_amount_str:
            serving_amount_str = serving_amount_str.split('(')[0].strip()
        if ' ' in serving_amount_str:
            whole_part_str, fraction_part_str = serving_amount_str.split(' ', 1)
            whole_part = int(whole_part_str)
            fraction_part = Fraction(fraction_part_str)
        elif '/' in serving_amount_str:
            fraction_part = Fraction(serving_amount_str)
            whole_part = 0
        else:
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
    logger.debug(f"Rounded fraction {fraction} to {nearest_fraction}")
    return nearest_fraction

def handle_fractional_serving(actions, fraction_str):
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
            logger.warning(f"Unhandled fraction: {fraction_str}")
        actions.send_keys(Keys.TAB).perform()
    except Exception as e:
        logger.error(f"Error handling fractional serving: {e}", exc_info=True)
        actions.send_keys(Keys.TAB).perform()

@retry_on_failure(max_retries=3, delay=2)
def enter_food_details(driver, food_item):
    try:
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
            logger.debug("No brand provided.")
        actions.send_keys(Keys.TAB).perform()

        # Food Name
        food_name = food_item.get("Food Name", "")
        if food_name:
            actions.send_keys(food_name).perform()
            logger.debug(f"Entered food name: {food_name}")
        else:
            logger.warning("No food name provided.")
        actions.send_keys(Keys.TAB).perform()

        # Icon
        icon = food_item.get("Icon", "")
        if icon:
            icon_first_word = icon.split()[0]
            actions.send_keys(icon_first_word).perform()
            logger.debug(f"Entered icon: {icon_first_word}")
        actions.send_keys(Keys.TAB).perform()

        # Serving Size
        serving_size = food_item.get("Serving Size", "")
        if serving_size:
            try:
                serving_amount_str, serving_type = serving_size.split(" ", 1)
                serving_amount_str = serving_amount_str.strip()
                serving_type = serving_type.strip()

                whole_part, fraction_part = parse_serving_amount(serving_amount_str)
                if whole_part is None:
                    raise ValueError(f"Unable to parse serving amount '{serving_amount_str}'")

                actions.send_keys(str(whole_part)).perform()
                actions.send_keys(Keys.TAB).perform()

                if fraction_part > 0:
                    fraction_str = round_fraction_to_nearest_common(fraction_part)
                    if fraction_str:
                        handle_fractional_serving(actions, fraction_str)
                    else:
                        logger.warning(f"No matching fraction for {fraction_part}, skipping fraction.")
                        actions.send_keys(Keys.TAB).perform()
                else:
                    actions.send_keys(Keys.TAB).perform()

                serving_type_first_word = serving_type.split()[0]
                actions.send_keys(serving_type_first_word).perform()
                logger.debug(f"Entered serving type: {serving_type_first_word}")
                actions.send_keys(Keys.TAB).perform()

            except ValueError as ve:
                logger.error(f"ValueError parsing serving size '{serving_size}': {ve}", exc_info=True)
                for _ in range(3):
                    actions.send_keys(Keys.TAB).perform()
            except Exception as e:
                logger.error(f"Unexpected error parsing serving size '{serving_size}': {e}", exc_info=True)
                for _ in range(3):
                    actions.send_keys(Keys.TAB).perform()
        else:
            logger.debug("No serving size provided.")
            for _ in range(3):
                actions.send_keys(Keys.TAB).perform()

        # Nutrition Fields
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
                logger.debug(f"No value for {field_name}, skipping.")
            actions.send_keys(Keys.TAB).perform()

        logger.debug("Entered all food details successfully.")
        return True
    except Exception as e:
        logger.error(f"Error entering food details: {e}", exc_info=True)
        return False

@retry_on_failure(max_retries=3, delay=2)
def save_food(driver):
    try:
        add_food_button_xpath = "//div[@tabindex='1020' and contains(@class, 'addFoodToLog')]"
        add_food_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, add_food_button_xpath))
        )
        add_food_button.click()
        logger.debug("Clicked 'Add Food' button to save the custom food.")
        return True
    except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
        logger.error(f"Error clicking 'Add Food' button: {e}", exc_info=True)
        driver.save_screenshot("/tmp/save_food_error.png")
        return False
    except Exception as e:
        logger.error(f"Unexpected error clicking 'Add Food' button: {e}", exc_info=True)
        driver.save_screenshot("/tmp/save_food_error.png")
        return False
