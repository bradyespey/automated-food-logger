# scripts/fetch_logged_items.py

import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scripts.navigation import navigate_to_date
from scripts.decorators import retry_on_failure  # Ensure correct import path
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException
)

logger = logging.getLogger("fetch_logged_items")

@retry_on_failure(max_retries=3, delay=2)
def fetch_logged_items(driver, target_date):
    logged_items = []
    try:
        if not navigate_to_date(driver, target_date):
            logger.error(f"Cannot fetch logged items for date {target_date} because navigation failed.")
            return logged_items

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.mealWrapper"))
            )
            logger.debug("Meal sections loaded successfully.")
        except TimeoutException:
            logger.error("Timeout while waiting for meal sections to load.")
            return logged_items

        try:
            meal_sections = driver.find_elements(By.CSS_SELECTOR, "div.mealWrapper")
            logger.info(f"Found {len(meal_sections)} meal sections.")
        except NoSuchElementException:
            logger.error("No meal sections found on the page.")
            return logged_items

        for meal_section in meal_sections:
            try:
                meal_name_element = meal_section.find_element(By.CSS_SELECTOR, "div.mealTitle")
                meal_name = meal_name_element.text.strip()
                logger.debug(f"Processing meal: {meal_name}")

                food_rows = meal_section.find_elements(By.CSS_SELECTOR, "div.foodRow")
                logger.info(f"Found {len(food_rows)} food rows in meal '{meal_name}'.")

                for row in food_rows:
                    try:
                        food_name = row.find_element(By.CSS_SELECTOR, "div.foodName").text.strip()
                        serving = row.find_element(By.CSS_SELECTOR, "div.foodServing").text.strip()
                        calories = row.find_element(By.CSS_SELECTOR, "div.foodCalories").text.strip()

                        fluid_ounces_added = 0.0
                        try:
                            fluid_text = row.find_element(By.CSS_SELECTOR, "div.foodFluidOunces").text.strip()
                            fluid_ounces_added = float(fluid_text.split()[0])
                        except NoSuchElementException:
                            pass

                        try:
                            fat = row.find_element(By.CSS_SELECTOR, "div.foodFat").text.strip()
                        except NoSuchElementException:
                            fat = ""
                        try:
                            saturated_fat = row.find_element(By.CSS_SELECTOR, "div.foodSaturatedFat").text.strip()
                        except NoSuchElementException:
                            saturated_fat = ""
                        try:
                            cholesterol = row.find_element(By.CSS_SELECTOR, "div.foodCholesterol").text.strip()
                        except NoSuchElementException:
                            cholesterol = ""
                        try:
                            sodium = row.find_element(By.CSS_SELECTOR, "div.foodSodium").text.strip()
                        except NoSuchElementException:
                            sodium = ""
                        try:
                            carbs = row.find_element(By.CSS_SELECTOR, "div.foodCarbs").text.strip()
                        except NoSuchElementException:
                            carbs = ""
                        try:
                            fiber = row.find_element(By.CSS_SELECTOR, "div.foodFiber").text.strip()
                        except NoSuchElementException:
                            fiber = ""
                        try:
                            sugar = row.find_element(By.CSS_SELECTOR, "div.foodSugar").text.strip()
                        except NoSuchElementException:
                            sugar = ""
                        try:
                            protein = row.find_element(By.CSS_SELECTOR, "div.foodProtein").text.strip()
                        except NoSuchElementException:
                            protein = ""

                        logged_item = {
                            "Food Name": food_name,
                            "Date": target_date.strftime('%m/%d/%Y'),
                            "Meal": meal_name,
                            "Brand": "",
                            "Calories": calories,
                            "Fat (g)": fat,
                            "Saturated Fat (g)": saturated_fat,
                            "Cholesterol (mg)": cholesterol,
                            "Sodium (mg)": sodium,
                            "Carbs (g)": carbs,
                            "Fiber (g)": fiber,
                            "Sugar (g)": sugar,
                            "Protein (g)": protein,
                            "fluid_ounces_added": fluid_ounces_added
                        }

                        logged_items.append(logged_item)
                        logger.debug(f"Fetched logged item: {logged_item}")

                    except NoSuchElementException as e:
                        logger.warning(f"Missing element in food row: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to parse a food entry in meal '{meal_name}': {e}")

            except NoSuchElementException as e:
                logger.warning(f"Missing meal title element: {e}")
            except Exception as e:
                logger.warning(f"Failed to process a meal section: {e}")

    except WebDriverException as e:
        logger.error(f"WebDriverException occurred: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching logged items: {e}", exc_info=True)

    logger.info(f"Fetched {len(logged_items)} logged items for date {target_date}.")
    return logged_items
