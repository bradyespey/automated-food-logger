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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL, format='%(message)s')

# ======= TOGGLE OPTIONS =======
headless_mode = True  # Set to True for headless mode, False for non-headless (visible Chrome)
# =============================

cookie_path = "C:\\Projects\\LoseIt\\loseit_cookies.json"
url = "https://www.loseit.com/"

def kill_chrome_driver():
    # Kill any lingering Chrome or ChromeDriver processes
    subprocess.call("taskkill /f /im chromedriver.exe >nul 2>&1", shell=True)
    subprocess.call("taskkill /f /im chrome.exe >nul 2>&1", shell=True)

def initialize_driver():
    kill_chrome_driver()  # Ensure no previous instances are running

    # Set Chrome options
    options = webdriver.ChromeOptions()
    
    # Toggle headless mode based on the variable
    if headless_mode:
        options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Use webdriver_manager to manage ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    return driver

def initialize_driver_with_retry(retries=3):
    """Attempts to initialize the driver, retrying in case of failure."""
    for attempt in range(retries):
        try:
            return initialize_driver()
        except Exception as e:
            if attempt < retries - 1:
                print(f"Retrying to initialize driver (attempt {attempt + 1})...")
                time.sleep(2)  # Wait before retrying
            else:
                raise e

def load_cookies_and_navigate(driver, cookie_path):
    driver.get(url)
    if os.path.exists(cookie_path):
        with open(cookie_path, "r") as cookie_file:
            cookies = json.load(cookie_file)
        for cookie in cookies:
            driver.add_cookie(cookie)
    driver.get(url)
    time.sleep(3)

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

        serving_amount, serving_type = food_item.get("serving_quantity", "0 servings").split(" ", 1)
        whole_part = 0
        serving_fraction = 0
        if ' ' in serving_amount:
            parts = serving_amount.split(' ')
            whole_part = int(parts[0])
            serving_fraction = convert_fraction_to_float(parts[1])
        elif '/' in serving_amount:
            serving_fraction = convert_fraction_to_float(serving_amount)
        else:
            parts = serving_amount.split('.')
            whole_part = int(parts[0])
            if len(parts) > 1:
                serving_fraction = float('0.' + parts[1])

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

def compare_items(input_items, logged_items, content, start_time):
    logging_output = "<b style='color: #f9c74f;'>Logging Output:</b><br>"
    for i, logged_item in enumerate(logged_items, 1):
        logging_output += f"Logging item {i} of {len(input_items)}: {logged_item['name']}<br>"
    logging_output += f"Time to Log: {time.time() - start_time:.2f} seconds<br><br>"

    total_food_names = content.count('Food Name:')
    if total_food_names == len(input_items):
        parsing_check = f"<b style='color: #f9c74f;'>Parsing Check:</b><br><span style='color: green;'>All {total_food_names} foods in input parsed correctly</span><br><br>"
    else:
        parsing_check = f"<b style='color: #f9c74f;'>Parsing Check:</b><br><span style='color: red;'>Error: {total_food_names - len(input_items)} food items found in input but not parsed correctly.</span><br><br>"

    comparison_check = "<b style='color: #f9c74f;'>Comparison Check:</b><br>"
    for index, (input_item, logged_item) in enumerate(zip(input_items, logged_items), 1):
        comparison_check += compare_values("name", input_item['name'], logged_item['name'])
        comparison_check += compare_values("date", input_item['date'], logged_item['date'])
        comparison_check += compare_values("meal", input_item['meal'], logged_item['meal'])
        comparison_check += compare_values("brand", input_item['brand'], logged_item['brand'])
        comparison_check += compare_values("icon", input_item['icon'], logged_item['icon'])
        comparison_check += compare_values("serving_quantity", input_item['serving_quantity'], logged_item['serving_quantity'])
        comparison_check += compare_values("calories", input_item['calories'], logged_item['calories'])
        comparison_check += compare_values("fat", input_item['fat'], logged_item['fat'])
        comparison_check += compare_values("saturated_fat", input_item['saturated_fat'], logged_item['saturated_fat'])
        comparison_check += compare_values("cholesterol", input_item['cholesterol'], logged_item['cholesterol'])
        comparison_check += compare_values("sodium", input_item['sodium'], logged_item['sodium'])
        comparison_check += compare_values("carbs", input_item['carbs'], logged_item['carbs'])
        comparison_check += compare_values("fiber", input_item['fiber'], logged_item['fiber'])
        comparison_check += compare_values("sugar", input_item['sugar'], logged_item['sugar'])
        comparison_check += compare_values("protein", input_item['protein'], logged_item['protein'])
        comparison_check += "<br>"

    return logging_output + parsing_check + comparison_check

def compare_values(field_name, input_value, logged_value):
    if str(input_value) == str(logged_value):
        return f'<span style="color: green;">**{field_name}:** {logged_value} (matches input value)</span><br>'
    else:
        return f'<span style="color: red;">**{field_name}:** {logged_value} (does not match input value {input_value})</span><br>'

def main():
    start_time = time.time()
    
    log_text = os.getenv('LOG_TEXT', '')

    driver = None
    try:
        driver = initialize_driver_with_retry()

        load_cookies_and_navigate(driver, cookie_path)

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
            enter_placeholder_text_in_search_box(driver, tabindex=meal_tabindex[meal])

            if not click_create_custom_food(driver):
                print(f"Failed to find 'Create a custom food' button for {food_details['name']}. Skipping to next.")
                continue

            enter_food_details(driver, food_details)
            logged_items.append(food_details)
            driver.refresh()
            time.sleep(3)
    finally:
        if driver:
            driver.quit()

    comparison = compare_items(food_items, logged_items, log_text, start_time)
    print(comparison)

if __name__ == "__main__":
    main()
