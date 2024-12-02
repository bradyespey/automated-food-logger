# scripts/navigation.py
# Contains functions for navigating days, meals, etc.

import logging
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

def navigate_day(driver, days):
    """
    Navigates forward or backward by 'days' in the Lose It! interface.
    """
    direction = "next" if days > 0 else "previous"
    logger.info(f"Attempting to navigate {days} day(s) to the {direction}.")

    try:
        day_button_xpath = "//div[contains(@class, '{}') and @role='button' and @title='{}']".format(
            'nextArrowButton' if direction == 'next' else 'prevArrowButton',
            'Next' if direction == 'next' else 'Previous'
        )
        for _ in range(abs(days)):
            for attempt in range(3):
                try:
                    day_button = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, day_button_xpath))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", day_button)
                    day_button.click()
                    logger.info(f"Clicked '{direction}' day button.")
                    time.sleep(1)
                    break
                except Exception as e:
                    logger.warning(f"Navigation attempt {attempt + 1} failed for '{direction}': {e}")
                    if attempt < 2:
                        logger.info("Retrying to navigate...")
                        time.sleep(1)
                    else:
                        logger.error(f"Failed to navigate '{direction}' after 3 attempts.")
    except Exception as e:
        logger.error(f"Failed to navigate '{direction}': {e}")

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