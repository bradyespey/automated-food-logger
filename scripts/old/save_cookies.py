import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import InvalidSessionIdException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up the Chrome driver using the same configuration as your main script
cookie_path = "C:\\Projects\\LoseIt\\loseit_cookies.json"
url = "https://www.loseit.com/"

service = Service("C:\\WebDriver\\chromedriver.exe")
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")  # Open in maximized window
options.add_argument("--disable-logging")  # Suppress logging
options.add_argument("--log-level=3")  # Suppress verbose logs

driver = webdriver.Chrome(service=service, options=options)

try:
    driver.get(url)
    delay = 60  # Adjust this delay as needed (in seconds)
    print(f"Waiting for {delay} seconds to allow manual login...")
    time.sleep(delay)

    print("Proceeding to save cookies...")

    if not os.path.exists(os.path.dirname(cookie_path)):
        os.makedirs(os.path.dirname(cookie_path))  # Create the directory if it does not exist
        print(f"Created directory: {os.path.dirname(cookie_path)}")

    cookies = driver.get_cookies()
    print(f"Retrieved cookies: {cookies}")  # Debugging: Print cookies

    with open(cookie_path, "w") as cookie_file:
        json.dump(cookies, cookie_file)
    print(f"Cookies saved to {cookie_path}")
except InvalidSessionIdException as e:
    print(f"Session invalid or no longer exists: {e}")
except Exception as e:
    print(f"An error occurred: {type(e).__name__}, {e}")
finally:
    driver.quit()
