# scripts/login.py

import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, ElementNotInteractableException
from scripts.logging_setup import get_logger

# Get a logger for this script
logger = get_logger("login")

def initialize_driver(headless=True):
    """
    Initializes the Selenium WebDriver with specified options.

    Args:
        headless (bool): Determines if the browser should run in headless mode.

    Returns:
        WebDriver: Configured Selenium WebDriver instance.
    """
    try:
        options = Options()
        if headless:
            options.add_argument("--headless=new")  # Use "--headless=new" for newer Chrome versions
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            logger.info("Running in headless mode.")
        else:
            options.add_argument("--start-maximized")
            logger.info("Running in headed mode (browser window will be visible).")
        
        # Additional options to mimic regular browser behavior
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/131.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Prevent detection as a bot
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
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        exit(1)

def login(driver, email, password):
    """
    Logs into Lose It! using provided credentials.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        email (str): User's email.
        password (str): User's password.

    Returns:
        bool: True if login was successful, False otherwise.
    """
    try:
        login_url = "https://my.loseit.com/login?r=https://www.loseit.com/"
        driver.get(login_url)
        logger.info("Navigated to Lose It! login page.")

        # Wait for email input to be present and visible
        email_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'email'))
        )
        logger.info("Email input field verified.")

        # Enter email
        email_input.clear()
        email_input.send_keys(email)
        logger.info("Entered email.")

        # Wait for password input to be present and visible
        password_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'password'))
        )
        password_input.clear()
        password_input.send_keys(password)
        logger.info("Entered password.")

        # Click login button
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        login_button.click()
        logger.info("Clicked login button.")

        return True
    except TimeoutException:
        logger.error("Timeout while attempting to log in. Elements not found.")
        driver.save_screenshot("/tmp/login_timeout.png")
        return False
    except NoSuchElementException as e:
        logger.error(f"Login element not found: {e}", exc_info=True)
        driver.save_screenshot("/tmp/login_no_element.png")
        return False
    except ElementNotInteractableException as e:
        logger.error(f"Login element not interactable: {e}", exc_info=True)
        driver.save_screenshot("/tmp/login_not_interactable.png")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during login: {e}", exc_info=True)
        driver.save_screenshot("/tmp/login_unexpected_error.png")
        return False

def verify_login(driver):
    """
    Verifies that the user is successfully logged in by checking the presence of a specific element.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.

    Returns:
        bool: True if login is verified, False otherwise.
    """
    try:
        # Adjust the class name based on the provided HTML snippet
        # Assuming "GCJ-IGUD0B" is the class for the current date element post-login
        current_date_element = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "GCJ-IGUD0B"))
        )
        current_date_text = current_date_element.text.strip()
        logger.info(f"Login verified. Current date found: {current_date_text}")
        return True
    except TimeoutException:
        logger.error("Login may have failed; current date not found on home page.")
        driver.save_screenshot("/tmp/verify_login_timeout.png")
        return False
    except NoSuchElementException as e:
        logger.error(f"Verification element not found: {e}", exc_info=True)
        driver.save_screenshot("/tmp/verify_login_no_element.png")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during login verification: {e}", exc_info=True)
        driver.save_screenshot("/tmp/verify_login_unexpected_error.png")
        return False