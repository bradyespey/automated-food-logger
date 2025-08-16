# scripts/navigation.py

import logging
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from scripts.logging_setup import get_logger

logger = get_logger("navigation")

def get_current_date(driver):
    try:
        # Try multiple selectors for the current date element
        date_selectors = [
            (By.CLASS_NAME, "GNOSQVDBIYB"),  # Current dynamic class
            (By.CLASS_NAME, "GMQI3OOBIYB"),  # Previous dynamic class
            (By.XPATH, "//div[contains(@class, 'gwt-HTML') and contains(text(), ', 2025')]"),  # Generic pattern
            (By.XPATH, "//div[contains(text(), ', 2025')]")  # Most generic
        ]
        
        current_date_element = None
        for selector_type, selector_value in date_selectors:
            try:
                current_date_element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                logger.info(f"Found date element using selector: {selector_type} = {selector_value}")
                break
            except TimeoutException:
                continue
        
        if not current_date_element:
            logger.error("Could not find current date element with any selector")
            return None
            
        current_date_text = current_date_element.text.strip()
        logger.info(f"Current date displayed in app: {current_date_text}")
        
        # Handle different date formats
        try:
            current_date = datetime.strptime(current_date_text, '%A %b %d, %Y').date()
        except ValueError:
            # Try alternative format
            current_date = datetime.strptime(current_date_text, '%A %B %d, %Y').date()
            
        return current_date
    except Exception as e:
        logger.error(f"Error retrieving current date: {e}", exc_info=True)
        return None

def parse_food_item_date(date_str):
    try:
        current_year = datetime.today().year
        date_obj = datetime.strptime(f"{date_str}/{current_year}", '%m/%d/%Y').date()
        return date_obj
    except Exception as e:
        logger.error(f"Error parsing food item date '{date_str}': {e}", exc_info=True)
        return None

def close_overlays(driver):
    try:
        overlay_selectors = [
            "//div[@role='button' and @title='Close']",
            "//button[contains(text(), 'Close')]",
            "//div[contains(@class, 'overlay')]//button[contains(text(), 'Close')]"
        ]
        for selector in overlay_selectors:
            buttons = driver.find_elements(By.XPATH, selector)
            for btn in buttons:
                try:
                    btn.click()
                    logger.info("Closed an overlay or popup.")
                    time.sleep(1)  # Allow time for the overlay to close
                except Exception as e:
                    logger.error(f"Failed to click overlay close button: {e}")
    except Exception as e:
        logger.error(f"Error while closing overlays: {e}")

def navigate_to_date(driver, target_date):
    max_attempts = 30
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
                # Try multiple selectors for next button
                next_selectors = [
                    (By.XPATH, "//div[@role='button' and @title='Next']"),
                    (By.XPATH, "//div[contains(@class, 'nextArrowButton')]"),
                    (By.XPATH, "//div[contains(@class, 'nextArrowButton') and @role='button']"),
                    (By.XPATH, "//div[@title='Next' and @role='button']")
                ]
                
                next_button = None
                for selector_type, selector_value in next_selectors:
                    try:
                        next_button = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((selector_type, selector_value))
                        )
                        logger.info(f"Found next button using selector: {selector_type} = {selector_value}")
                        break
                    except TimeoutException:
                        continue
                
                if next_button:
                    next_button.click()
                    logger.info("Clicked 'Next Day' button.")
                else:
                    logger.error("Could not find next button with any selector")
            except (TimeoutException, ElementClickInterceptedException) as e:
                logger.error(f"Could not click 'Next Day' button: {e}")
                close_overlays(driver)
        else:
            # Click 'Previous Day' button
            try:
                # Try multiple selectors for previous button
                prev_selectors = [
                    (By.XPATH, "//div[@role='button' and @title='Previous']"),
                    (By.XPATH, "//div[contains(@class, 'prevArrowButton')]"),
                    (By.XPATH, "//div[contains(@class, 'prevArrowButton') and @role='button']"),
                    (By.XPATH, "//div[@title='Previous' and @role='button']")
                ]
                
                prev_button = None
                for selector_type, selector_value in prev_selectors:
                    try:
                        prev_button = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((selector_type, selector_value))
                        )
                        logger.info(f"Found previous button using selector: {selector_type} = {selector_value}")
                        break
                    except TimeoutException:
                        continue
                
                if prev_button:
                    prev_button.click()
                    logger.info("Clicked 'Previous Day' button.")
                else:
                    logger.error("Could not find previous button with any selector")
            except (TimeoutException, ElementClickInterceptedException) as e:
                logger.error(f"Could not click 'Previous Day' button: {e}")
                close_overlays(driver)
        time.sleep(1)
        attempts += 1

    logger.error(f"Failed to navigate to target date {target_date} after {max_attempts} attempts.")
    return False

def goto_initial_position(driver):
    """
    Always go to the breakfast search box (tabindex='200') first, 
    ensuring the cursor is at a known baseline position before selecting any meal box.
    """
    logger.info("Moving cursor to the initial 'Breakfast' search box (tabindex=200).")
    try:
        breakfast_xpath = "//input[@tabindex='200']"
        breakfast_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, breakfast_xpath))
        )
        breakfast_input.click()
        logger.info("Cursor moved to the initial position (Breakfast box).")
    except Exception as e:
        logger.warning(f"Could not move cursor to the initial position: {e}")

def select_search_box(driver, meal_name):
    try:
        tabindex_map = {
            "Breakfast": "200",
            "Lunch": "300",
            "Dinner": "400",
            "Snacks": "500"
        }
        tabindex = tabindex_map.get(meal_name, "400")
        search_input_xpath = f"//input[@tabindex='{tabindex}']"
        search_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, search_input_xpath))
        )
        logger.info(f"Located search box for '{meal_name}'.")
        return search_input
    except (TimeoutException, StaleElementReferenceException) as e:
        logger.warning(f"Failed to locate search input for meal '{meal_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error selecting search box for '{meal_name}': {e}", exc_info=True)
        return None

def enter_placeholder_text(driver, search_input, placeholder_text):
    try:
        search_input.clear()
        search_input.send_keys(placeholder_text)
        search_input.send_keys(Keys.ENTER)
        logger.info(f"Entered placeholder text '{placeholder_text}' in the search box.")
        return True
    except Exception as e:
        logger.error(f"Error entering placeholder text: {e}", exc_info=True)
        return False

def wait_for_fixed_glass_invisibility(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "fixedGlass"))
        )
        logger.info("'fixedGlass' overlay is no longer visible.")
        return True
    except TimeoutException:
        logger.error("'fixedGlass' overlay is still visible after waiting.")
        driver.save_screenshot("/tmp/fixed_glass_still_visible.png")
        return False

def click_create_custom_food(driver):
    """
    Attempts to click the 'Create a custom food' button once.
    Returns True if successful, False if it fails.
    """
    create_food_button_xpath = "//div[contains(@class, 'gwt-HTML') and normalize-space(text())='Create a custom food']"

    if not wait_for_fixed_glass_invisibility(driver):
        logger.error("Cannot click 'Create a custom food' due to fixedGlass overlay.")
        return False

    try:
        create_food_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, create_food_button_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", create_food_button)
        create_food_button.click()
        logger.info("Clicked 'Create a custom food' button on the first attempt.")
        return True
    except (TimeoutException, ElementClickInterceptedException, StaleElementReferenceException) as e:
        logger.warning(f"Failed to click 'Create a custom food' button: {e}")
        driver.save_screenshot(f"/tmp/create_custom_food_failure_{int(time.time())}.png")
        return False
    except Exception as e:
        logger.error(f"Unexpected error clicking 'Create a custom food' button: {e}", exc_info=True)
        return False
