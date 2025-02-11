# scripts/login.py

import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scripts.logging_setup import get_logger

logger = get_logger("login")

def initialize_driver(headless=True): # Change to True to run with visible Chrome, change to False to run without visible Chrome
    try:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-setuid-sandbox")
            logger.info("Running in headless mode.")
        else:
            chrome_options.add_argument("--start-maximized")
            logger.info("Running in headed mode.")

        # Mimic normal browser behavior
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # **Add the following preferences to disable password saving prompts**
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        logger.debug("Disabled Chrome password manager.")

        chrome_binary = os.getenv("GOOGLE_CHROME_SHIM")
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")

        logger.debug(f"GOOGLE_CHROME_SHIM is set: {'Yes' if chrome_binary else 'No'}")
        logger.debug(f"CHROMEDRIVER_PATH is set: {'Yes' if chromedriver_path else 'No'}")

        if chrome_binary and chromedriver_path:
            chrome_options.binary_location = chrome_binary
            logger.debug(f"Using Chrome binary at: {chrome_binary}")
            service = Service(executable_path=chromedriver_path)
        else:
            logger.debug("GOOGLE_CHROME_SHIM and CHROMEDRIVER_PATH not set. Using webdriver-manager locally.")
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Prevent detection as bot
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
                """
            },
        )

        logger.info("Chrome WebDriver initialized successfully.")
        return driver

    except WebDriverException as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}", exc_info=True)
        raise RuntimeError("Chrome WebDriver initialization failed")

def login(driver, email, password):
    try:
        login_url = "https://my.loseit.com/login?r=https://www.loseit.com/"
        driver.get(login_url)
        logger.info("Navigated to Lose It! login page.")

        email_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'email'))
        )
        logger.info("Email input field verified.")
        email_input.clear()
        email_input.send_keys(email)
        logger.info("Entered email.")

        password_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'password'))
        )
        password_input.clear()
        password_input.send_keys(password)
        logger.info("Entered password.")

        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        login_button.click()
        logger.info("Clicked login button.")
        return True

    except TimeoutException:
        logger.error("Timeout while attempting to log in. Elements not found.", exc_info=True)
        return False
    except NoSuchElementException as e:
        logger.error(f"Login element not found: {e}", exc_info=True)
        return False
    except ElementNotInteractableException as e:
        logger.error(f"Login element not interactable: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during login: {e}", exc_info=True)
        return False

def verify_login(driver):
    try:
        current_date_element = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "GMQI3OOBIYB"))
        )
        current_date_text = current_date_element.text.strip()
        logger.info(f"Login verified. Current date found: {current_date_text}")
        return True
    except TimeoutException:
        logger.error("Login may have failed; current date not found on home page.", exc_info=True)
        return False
    except NoSuchElementException as e:
        logger.error(f"Verification element not found: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error during login verification: {e}", exc_info=True)
        return False
