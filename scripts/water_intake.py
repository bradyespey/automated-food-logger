# scripts/water_intake.py
# Contains functions for updating water intake.

import logging
import time
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

def get_current_water_intake(driver):
    """
    Reads the current water intake value from the water intake page.
    """
    try:
        # Locate the input field that contains the current water intake value
        water_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@class='gwt-TextBox GCJ-IGUKWC']"))
        )
        current_water = float(water_input.get_attribute('value') or 0.0)
        logger.info(f"Current water intake: {current_water} oz.")
        return current_water
    except Exception as e:
        logger.error(f"Failed to read current water intake: {e}")
        return 0.0

def set_water_intake(driver, water_oz):
    """
    Sets the water intake value.
    """
    try:
        # Locate the input field for water intake
        water_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@class='gwt-TextBox GCJ-IGUKWC']"))
        )
        water_input.clear()
        water_input.send_keys(str(water_oz))
        time.sleep(1)
        water_input.send_keys(Keys.ENTER)  # Press Enter to submit
        logger.info(f"Set water intake to {water_oz} oz.")
        time.sleep(2)
    except Exception as e:
        logger.error(f"Failed to set water intake: {e}")

def navigate_to_water_goals_page(driver):
    """
    Navigates to the water intake goals page.
    """
    try:
        goals_url = "https://www.loseit.com/#Goals:Water%20Intake%5EWater%20Intake"
        driver.get(goals_url)
        logger.info("Navigated to water intake goals page.")
        time.sleep(3)
    except Exception as e:
        logger.error(f"Failed to navigate to water intake goals page: {e}")

def navigate_water_day(driver, days):
    """
    Navigates forward or backward by 'days' in the Water Intake interface.
    """
    direction = "next" if days > 0 else "previous"
    logger.info(f"Attempting to navigate {days} water day(s) to the {direction}.")

    try:
        day_button_xpath = "//div[@role='button' and @title='{}']".format("Next" if direction == "next" else "Previous")
        for _ in range(abs(days)):
            for attempt in range(3):
                try:
                    day_button = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, day_button_xpath))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", day_button)
                    day_button.click()
                    logger.info(f"Clicked '{direction}' water day button.")
                    time.sleep(1)
                    break
                except Exception as e:
                    logger.warning(f"Water day navigation attempt {attempt + 1} failed: {e}")
                    if attempt < 2:
                        logger.info("Retrying to navigate water day...")
                        time.sleep(1)
                    else:
                        logger.error(f"Failed to navigate '{direction}' water day after 3 attempts.")
    except Exception as e:
        logger.error(f"Failed to navigate '{direction}' on water intake page: {e}")

def update_water_intake(driver, food_details, days_difference, navigate_to_water_goals_page_func, navigate_water_day_func, get_current_water_intake_func, set_water_intake_func):
    """
    Updates the water intake based on the fluid ounces in the food details.
    """
    serving_quantity = food_details.get("serving_quantity", "").lower()
    if "fluid ounces" in serving_quantity:
        try:
            fluid_oz_match = re.search(r"(\d+\.?\d*)\s*fluid ounces", serving_quantity)
            if not fluid_oz_match:
                logger.warning("No fluid ounces found in serving_quantity.")
                return "", 0.0
            fluid_oz = float(fluid_oz_match.group(1))

            # Navigate to the water intake page and the correct day
            navigate_to_water_goals_page_func(driver)
            if days_difference != 0:
                navigate_water_day_func(driver, days=days_difference)

            # Get the current water intake value
            current_water = get_current_water_intake_func(driver)
            updated_water = current_water + fluid_oz

            # Set the new water intake value
            set_water_intake_func(driver, updated_water)

            logger.info(f"Updated water intake from {current_water} oz to {updated_water} oz.")
            return f"Updated the water intake from {current_water} oz to {updated_water} oz", fluid_oz
        except Exception as e:
            logger.error(f"Failed to update water intake: {e}")
            return "", 0.0
    return "", 0.0