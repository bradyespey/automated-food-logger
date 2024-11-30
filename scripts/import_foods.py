# scripts/import_foods.py

import os
import subprocess
import time
import json
import warnings
import logging
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import base64

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL, format='%(message)s')

# ======= TOGGLE OPTIONS =======
headless_mode = True  # Set to True for headless mode
# =============================

url = "https://www.loseit.com/"

def kill_chrome_driver():
    # Kill any lingering Chrome or ChromeDriver processes
    if os.name == 'nt':
        subprocess.call("taskkill /f /im chromedriver.exe >nul 2>&1", shell=True)
        subprocess.call("taskkill /f /im chrome.exe >nul 2>&1", shell=True)
    else:
        subprocess.call("pkill chromedriver", shell=True)
        subprocess.call("pkill chrome", shell=True)

def initialize_driver():
    kill_chrome_driver()  # Ensure no previous instances are running

    # Set Chrome options
    options = webdriver.ChromeOptions()

    # Run in headless mode
    if headless_mode:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")

    # Use webdriver_manager to manage ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver

def initialize_driver_with_retry(retries=3):
    """Attempts to initialize the driver, retrying in case of failure."""
    for attempt in range(retries):
        try:
            return initialize_driver()
        except WebDriverException as e:
            if attempt < retries - 1:
                print(f"Retrying to initialize driver (attempt {attempt + 1})...")
                time.sleep(2)  # Wait before retrying
            else:
                raise e

def load_cookies_and_navigate(driver):
    driver.get(url)
    cookies_base64 = os.environ.get('LOSEIT_COOKIES', '')
    if cookies_base64:
        try:
            cookies_json = base64.b64decode(cookies_base64).decode('utf-8')
            cookies = json.loads(cookies_json)
            for cookie in cookies:
                # Adjust cookie domain if necessary
                if 'domain' in cookie:
                    del cookie['domain']
                driver.add_cookie(cookie)
        except Exception as e:
            print(f"Failed to decode and load cookies: {e}")
            return False
    else:
        print("LOSEIT_COOKIES environment variable is not set.")
        return False
    driver.get(url)
    time.sleep(3)
    return True

def navigate_day(driver, days):
    try:
        direction = "next" if days > 0 else "previous"
        day_button_class = 'nextArrowButton' if direction == 'next' else 'prevArrowButton'
        day_button_xpath = f"//div[contains(@class, '{day_button_class}') and @role='button']"
        for _ in range(abs(days)):
            for attempt in range(3):
                try:
                    day_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, day_button_xpath)))
                    driver.execute_script("arguments[0].scrollIntoView(true);", day_button)
                    day_button.click()
                    time.sleep(1)
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"Navigation failed for {direction}. Error: {e}")
                        return
    except Exception as e:
        print(f"Failed to navigate {direction}: {e}")

def enter_placeholder_text_in_search_box(driver, tabindex):
    try:
        search_box = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, f"//input[@tabindex='{tabindex}']")))
        search_box.clear()
        search_box.click()
        search_box.send_keys("t3stf00dd03sn0t3xist")
        search_box.send_keys(Keys.ENTER)
    except Exception as e:
        print(f"Failed to enter text in search box: {e}")

def wait_for_create_custom_food_button(driver):
    try:
        create_food_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Create a custom food')]")))
        return create_food_button
    except Exception as e:
        print(f"Failed to locate 'Create a custom food' button: {e}")
        return None

def click_create_custom_food(driver):
    create_food_button = wait_for_create_custom_food_button(driver)
    if create_food_button:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", create_food_button)
            create_food_button.click()
            return True
        except Exception as e:
            print(f"Failed to click 'Create a custom food' button: {e}")
    return False

def handle_fractional_serving(actions, serving_fraction):
    fraction_map = {
        0.125: 1, 0.25: 2, 0.333: 3, 0.5: 4,
        0.666: 5, 0.75: 6, 0.875: 7
    }
    closest_fraction = min(fraction_map.keys(), key=lambda x: abs(x - serving_fraction))
    steps = fraction_map[closest_fraction]
    for _ in range(steps):
        actions.send_keys(Keys.UP).perform()

def convert_fraction_to_float(fraction_str):
    if '/' in fraction_str:
        numerator, denominator = fraction_str.split('/')
        return float(numerator) / float(denominator)
    else:
        return float(fraction_str)

def enter_food_details(driver, food_item):
    try:
        time.sleep(2)
        actions = ActionChains(driver)
        brand_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@tabindex='1004']")))
        brand_input.click()
        actions.send_keys(food_item.get("brand", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("name", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("icon", "").split()[0]).perform()
        actions.send_keys(Keys.TAB).perform()

        serving_quantity = food_item.get("serving_quantity", "0 servings")
        if " " in serving_quantity:
            serving_amount, serving_type = serving_quantity.split(" ", 1)
        else:
            serving_amount, serving_type = serving_quantity, "servings"

        serving_parts = serving_amount.split(' ')
        if len(serving_parts) == 2:
            whole_part = int(serving_parts[0])
            serving_fraction = convert_fraction_to_float(serving_parts[1])
        elif '/' in serving_amount:
            whole_part = 0
            serving_fraction = convert_fraction_to_float(serving_amount)
        else:
            whole_part = int(serving_amount)
            serving_fraction = 0.0

        actions.send_keys(str(whole_part)).perform()
        
        time.sleep(1)  # Adding a short delay to allow the serving type to update
        
        actions.send_keys(Keys.TAB).perform()
        if serving_fraction > 0:
            handle_fractional_serving(actions, serving_fraction)
        actions.send_keys(Keys.TAB).perform()
        
        actions.send_keys(serving_type.split()[0]).perform()
        actions.send_keys(Keys.TAB).perform()

        actions.send_keys(food_item.get("calories", "")).perform()
        actions.send_keys(Keys.TAB).perform()

        actions.send_keys(food_item.get("fat", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("saturated_fat", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("cholesterol", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("sodium", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("carbs", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("fiber", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("sugar", "")).perform()
        actions.send_keys(Keys.TAB).perform()
        actions.send_keys(food_item.get("protein", "")).perform()
        actions.send_keys(Keys.TAB).perform()

        actions.send_keys(Keys.ENTER).perform()
    except Exception as e:
        print(f"Failed to enter food details: {e}")

def parse_nutritional_data(content):
    parsed_items = []
    current_item = {}

    lines = content.splitlines()

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
            if fluid_oz_match:
                current_item["fluid_ounces"] = float(fluid_oz_match.group(1))
            else:
                current_item["fluid_ounces"] = 0.0

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

    return parsed_items

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
        comparison_check += compare_values("name", input_item['name'], logged_item['name'])
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
            return f'<span style="color: green;">**{field_name}:** {logged_value} (matches input value)</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value} (does not match input value {input_value})</span><br>'
    except ValueError:
        # Fallback to string comparison
        if str(input_value).strip() == str(logged_value).strip():
            return f'<span style="color: green;">**{field_name}:** {logged_value} (matches input value)</span><br>'
        else:
            return f'<span style="color: red;">**{field_name}:** {logged_value} (does not match input value {input_value})</span><br>'

def navigate_to_water_goals_page(driver):
    """Navigates to the water intake goals page."""
    goals_url = "https://www.loseit.com/#Goals:Water%20Intake%5EWater%20Intake"
    driver.get(goals_url)
    time.sleep(3)

def navigate_water_day(driver, days):
    """Navigate forward or backward by 'days' in the Water Intake interface."""
    try:
        direction = "next" if days > 0 else "previous"
        day_button_xpath = "//div[@role='button' and @title='{}']".format("Next" if direction == "next" else "Previous")
        for _ in range(abs(days)):
            for attempt in range(3):
                try:
                    day_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, day_button_xpath)))
                    driver.execute_script("arguments[0].scrollIntoView(true);", day_button)
                    day_button.click()
                    time.sleep(1)
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"Navigation failed for {direction} on water intake page: {e}")
                        return
    except Exception as e:
        print(f"Failed to navigate {direction} on water intake page: {e}")

def get_current_water_intake(driver):
    """Reads the current water intake value from the water intake page."""
    try:
        # Locate the input field that contains the current water intake value
        water_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@type='text' and contains(@class, 'gwt-TextBox')]"))
        )
        current_water = float(water_input.get_attribute('value') or 0.0)
        return current_water
    except Exception as e:
        print(f"Failed to read current water intake: {e}")
        return 0.0

def set_water_intake(driver, water_oz):
    try:
        # Locate the input field for water intake
        water_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='text' and contains(@class, 'gwt-TextBox')]"))
        )
        water_input.clear()
        water_input.send_keys(str(water_oz))
        time.sleep(1)
        water_input.send_keys(Keys.ENTER)  # Press Enter to submit
        time.sleep(2)
    except Exception as e:
        print(f"Failed to set water intake: {e}")

def update_water_intake(driver, food_details, days_difference):
    if "fluid ounces" in food_details.get("serving_quantity", "").lower():
        try:
            fluid_oz_match = re.search(r"(\d+\.?\d*)", food_details["serving_quantity"])
            if not fluid_oz_match:
                return "", 0.0
            fluid_oz = float(fluid_oz_match.group(1))

            # Navigate to the water intake page and the correct day
            navigate_to_water_goals_page(driver)
            if days_difference != 0:
                navigate_water_day(driver, days_difference)

            # Get the current water intake value
            current_water = get_current_water_intake(driver)
            updated_water = current_water + fluid_oz

            # Set the new water intake value
            set_water_intake(driver, updated_water)

            return f"Updated the water intake from {current_water} oz to {updated_water} oz", fluid_oz
        except Exception as e:
            print(f"Failed to update water intake: {e}")
            return "", 0.0
    return "", 0.0

def visit_homepage(driver):
    try:
        homepage_url = "https://www.loseit.com/"
        driver.get(homepage_url)
        time.sleep(3)
    except Exception as e:
        print(f"Failed to visit the homepage: {e}")

def main():
    start_time = time.time()

    log_text = os.getenv('LOG_TEXT', '')

    driver = None
    logging_output = "<b style='color: #f9c74f;'>Logging Output:</b><br>"

    total_input_fluid_ounces = 0.0
    total_logged_fluid_ounces = 0.0

    try:
        driver = initialize_driver_with_retry()

        if not load_cookies_and_navigate(driver):
            print("Failed to load cookies and navigate.")
            return

        food_items = parse_nutritional_data(log_text)
        logged_items = []

        for index, food_details in enumerate(food_items):
            current_date = datetime.now().strftime("%m/%d/%Y")
            food_date = food_details.get("date", current_date)
            try:
                food_date_obj = datetime.strptime(food_date, "%m/%d/%Y")
            except ValueError:
                food_date_obj = datetime.strptime(food_date + f"/{datetime.now().year}", "%m/%d/%Y")
            current_date_obj = datetime.strptime(current_date, "%m/%d/%Y")
            days_difference = (food_date_obj - current_date_obj).days
            if days_difference != 0:
                navigate_day(driver, days=days_difference)

            meal = food_details.get("meal", "dinner").lower()
            meal_tabindex = {"breakfast": "200", "lunch": "300", "dinner": "400", "snacks": "500"}
            enter_placeholder_text_in_search_box(driver, tabindex=meal_tabindex.get(meal, "400"))

            if not click_create_custom_food(driver):
                print(f"Failed to find 'Create a custom food' button for {food_details['name']}. Skipping to next.")
                continue

            # Log food details
            enter_food_details(driver, food_details)
            logged_items.append(food_details)
            logging_output += f"Logging item {index + 1} of {len(food_items)}: {food_details['name']}<br>"

            # Update water intake and get fluid ounces added
            water_log_message, fluid_oz_added = update_water_intake(driver, food_details, days_difference)
            if water_log_message:
                logging_output += f"{water_log_message}<br>"
            else:
                fluid_oz_added = 0.0

            # Store the fluid ounces added into food_details
            food_details['fluid_ounces_added'] = fluid_oz_added

            # Accumulate totals
            total_input_fluid_ounces += food_details.get('fluid_ounces', 0.0)
            total_logged_fluid_ounces += fluid_oz_added

            # Refresh the page to reset for the next item
            driver.refresh()
            visit_homepage(driver)
            time.sleep(3)

    finally:
        if driver:
            driver.quit()

    logging_output += f"Time to Log: {time.time() - start_time:.2f} seconds<br><br>"
    comparison = compare_items(food_items, logged_items, log_text, total_input_fluid_ounces, total_logged_fluid_ounces)
    print(logging_output + comparison)

if __name__ == "__main__":
    main()