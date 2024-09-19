import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Variables
cookie_path = "C:\Projects\LoseIt\loseit_cookies.json"

# Initialize the Chrome driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
driver.maximize_window()

# Load cookies
if os.path.exists(cookie_path):
    with open(cookie_path, "r") as cookie_file:
        cookies = json.load(cookie_file)

try:
    driver.get("https://www.loseit.com")
    
    for cookie in cookies:
        driver.add_cookie(cookie)
    
    driver.refresh()
    time.sleep(5)  # Wait for the page to load

    print("Browser is now open and logged in. Pausing for inspection...")
    input("Press Enter to continue...")

except Exception as e:
    print(f"An error occurred: {type(e).__name__}, {e}")
finally:
    driver.quit()