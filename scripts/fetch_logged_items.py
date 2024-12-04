# scripts/fetch_logged_items.py

import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scripts.navigation import navigate_to_date
from selenium.common.exceptions import NoSuchElementException
from scripts.logging_setup import get_logger

# Get a logger for this script
logger = get_logger("fetch_logged_items")

def fetch_logged_items(driver, target_date):
    """
    Fetches logged food items from Lose It! for the specified date.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        target_date (date): The date for which to fetch logged items.

    Returns:
        list: A list of dictionaries representing logged food items.
    """
    logged_items = []
    try:
        # Navigate to the target date
        if not navigate_to_date(driver, target_date):
            logger.error(f"Cannot fetch logged items for date {target_date} because navigation failed.")
            return logged_items

        # Wait for meal sections to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.mealWrapper"))
        )

        # Locate all meal sections (Breakfast, Lunch, Dinner, Snacks)
        meal_sections = driver.find_elements(By.CSS_SELECTOR, "div.mealWrapper")

        for meal_section in meal_sections:
            try:
                # Extract meal name
                meal_name_element = meal_section.find_element(By.CSS_SELECTOR, "div.mealTitle")
                meal_name = meal_name_element.text.strip()

                # Locate all food item rows within the meal
                food_rows = meal_section.find_elements(By.CSS_SELECTOR, "div.foodRow")

                for row in food_rows:
                    try:
                        # Extract details from each row
                        # Adjust selectors based on actual website structure

                        # Food Name
                        food_name_element = row.find_element(By.CSS_SELECTOR, "div.foodName")
                        food_name = food_name_element.text.strip()

                        # Serving (Assuming serving size is available)
                        serving_element = row.find_element(By.CSS_SELECTOR, "div.foodServing")
                        serving = serving_element.text.strip()

                        # Calories
                        calories_element = row.find_element(By.CSS_SELECTOR, "div.foodCalories")
                        calories = calories_element.text.strip()

                        # Fluid Ounces (if available)
                        fluid_ounces_added = 0.0
                        try:
                            fluid_element = row.find_element(By.CSS_SELECTOR, "div.foodFluidOunces")
                            fluid_text = fluid_element.text.strip()
                            fluid_ounces_added = float(fluid_text.split()[0])  # Assuming format like "12.0 oz"
                        except NoSuchElementException:
                            # Fluid ounces might not be present
                            pass

                        logged_item = {
                            "Food Name": food_name,
                            "Date": target_date.strftime('%m/%d/%Y'),
                            "Meal": meal_name,
                            "Brand": "",  # Extract if available
                            "Calories": calories,
                            "Fat (g)": "",  # Extract if available
                            "Saturated Fat (g)": "",  # Extract if available
                            "Cholesterol (mg)": "",  # Extract if available
                            "Sodium (mg)": "",  # Extract if available
                            "Carbs (g)": "",  # Extract if available
                            "Fiber (g)": "",  # Extract if available
                            "Sugar (g)": "",  # Extract if available
                            "Protein (g)": "",  # Extract if available
                            "fluid_ounces_added": fluid_ounces_added
                        }

                        logged_items.append(logged_item)
                        logger.debug(f"Fetched logged item: {logged_item}")

                    except Exception as e:
                        logger.warning(f"Failed to parse a food entry in meal '{meal_name}': {e}")

            except Exception as e:
                logger.warning(f"Failed to process a meal section: {e}")

    except Exception as e:
        logger.error(f"An error occurred while fetching logged items: {e}", exc_info=True)

    logger.info(f"Fetched {len(logged_items)} logged items for date {target_date}.")
    return logged_items