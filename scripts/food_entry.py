# scripts/food_entry.py
# Contains functions for entering food details.

import logging
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)

def wait_for_create_custom_food_button(driver):
    """
    Waits for the 'Create a custom food' button to be clickable.
    """
    try:
        create_food_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Create a custom food')]"))
        )
        return create_food_button
    except Exception as e:
        logger.error(f"Failed to locate 'Create a custom food' button: {e}")
        return None

def click_create_custom_food(driver):
    """
    Clicks the 'Create a custom food' button.
    """
    create_food_button = wait_for_create_custom_food_button(driver)
    if create_food_button:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", create_food_button)
            create_food_button.click()
            logger.info("Clicked 'Create a custom food' button.")
            time.sleep(2)  # Wait for the custom food form to appear
            return True
        except Exception as e:
            logger.error(f"Failed to click 'Create a custom food' button: {e}")
    return False

def handle_fractional_serving(actions, serving_fraction):
    """
    Handles fractional servings by sending the appropriate number of UP key presses.
    """
    fraction_map = {
        0.125: 1, 0.25: 2, 0.333: 3, 0.5: 4,
        0.666: 5, 0.75: 6, 0.875: 7
    }
    closest_fraction = min(fraction_map.keys(), key=lambda x: abs(x - serving_fraction))
    steps = fraction_map[closest_fraction]
    for _ in range(steps):
        actions.send_keys(Keys.UP).perform()
    logger.debug(f"Handled fractional serving: {serving_fraction} as {closest_fraction} with {steps} steps.")

def convert_fraction_to_float(fraction_str):
    """
    Converts a fraction string (e.g., '1/2') to a float.
    """
    numerator, denominator = map(int, fraction_str.split('/'))
    return numerator / denominator

def enter_food_details(driver, food_item):
    """
    Enters the details of a food item into the logging form.
    """
    try:
        time.sleep(2)  # Ensure the form is loaded

        actions = ActionChains(driver)

        # Locate the Brand input field by its tabindex=1004
        brand_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@tabindex='1004']"))
        )
        brand_input.click()
        actions.send_keys(food_item.get("brand", "")).perform()
        actions.send_keys(Keys.TAB).perform()

        # Enter Food Name
        food_name_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Food Name']"))
        )
        food_name_input.send_keys(food_item.get("name", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Icon (assuming the first word of the icon text is used)
        icon_text = food_item.get("icon", "").split()[0]
        icon_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Icon']"))
        )
        icon_input.send_keys(icon_text)
        actions.send_keys(Keys.TAB).perform()

        # Serving Quantity
        serving_quantity = food_item.get("serving_quantity", "0 servings")
        serving_amount, serving_type = serving_quantity.split(" ", 1) if " " in serving_quantity else (serving_quantity, "servings")

        if '/' in serving_amount:
            whole_part = 0
            serving_fraction = convert_fraction_to_float(serving_amount)
        else:
            parts = serving_amount.split('.')
            if len(parts) == 2:
                whole_part = int(parts[0])
                serving_fraction = float('0.' + parts[1])
            else:
                whole_part = int(serving_amount)
                serving_fraction = 0.0

        # Enter whole part
        whole_part_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Serving Size']"))
        )
        whole_part_input.send_keys(str(whole_part))
        actions.send_keys(Keys.TAB).perform()

        # Handle fractional serving if any
        if serving_fraction > 0:
            handle_fractional_serving(actions, serving_fraction)
        actions.send_keys(Keys.TAB).perform()

        # Enter serving type
        serving_type_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Serving Type']"))
        )
        serving_type_input.send_keys(serving_type.split()[0])  # Assuming first word
        actions.send_keys(Keys.TAB).perform()

        # Enter Calories
        calories_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Calories']"))
        )
        calories_input.send_keys(food_item.get("calories", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Fat
        fat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Fat (g)']"))
        )
        fat_input.send_keys(food_item.get("fat", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Saturated Fat
        saturated_fat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Saturated Fat (g)']"))
        )
        saturated_fat_input.send_keys(food_item.get("saturated_fat", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Cholesterol
        cholesterol_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Cholesterol (mg)']"))
        )
        cholesterol_input.send_keys(food_item.get("cholesterol", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Sodium
        sodium_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Sodium (mg)']"))
        )
        sodium_input.send_keys(food_item.get("sodium", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Carbs
        carbs_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Carbs (g)']"))
        )
        carbs_input.send_keys(food_item.get("carbs", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Fiber
        fiber_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Fiber (g)']"))
        )
        fiber_input.send_keys(food_item.get("fiber", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Sugar
        sugar_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Sugar (g)']"))
        )
        sugar_input.send_keys(food_item.get("sugar", ""))
        actions.send_keys(Keys.TAB).perform()

        # Enter Protein
        protein_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Protein (g)']"))
        )
        protein_input.send_keys(food_item.get("protein", ""))
        actions.send_keys(Keys.TAB).perform()

        # Click the Save/Add Food button
        add_food_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'addFoodToLog')]"))
        )
        add_food_button.click()
        logger.info(f"Entered food details for '{food_item.get('name', '')}'.")
        time.sleep(2)  # Wait for the food to be added
    except Exception as e:
        logger.error(f"Failed to enter food details: {e}")