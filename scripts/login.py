# scripts/login.py

import os
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

def check_logged_in(driver):
    """
    Checks if the user is already logged in by looking for a profile link.
    """
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/profile')]"))
        )
        logger.debug("User is logged in.")
        return True
    except Exception:
        logger.debug("User is not logged in.")
        return False

def login_using_credentials(driver):
    """
    Logs into the Lose It! account using provided credentials.
    """
    email = os.environ.get('LOSEIT_EMAIL')
    password = os.environ.get('LOSEIT_PASSWORD')
    if not email or not password:
        logger.error("LOSEIT_EMAIL or LOSEIT_PASSWORD environment variable not set.")
        return False
    try:
        login_url = "https://my.loseit.com/login?r=https://www.loseit.com/"
        driver.get(login_url)
        logger.debug("Navigated to login page.")

        # Wait for the email input field to be clickable
        email_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'email'))
        )
        logger.debug("Email input field located.")
        email_input.clear()
        email_input.send_keys(email)
        logger.debug("Email entered.")

        # Find and fill the password input field
        password_input = driver.find_element(By.ID, 'password')
        password_input.clear()
        password_input.send_keys(password)
        logger.debug("Password entered.")

        # Find and click the login button
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        logger.debug("Login button clicked.")

        # Wait for login to complete by checking for an element present after login
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/profile')]"))
        )
        logger.info("Logged in successfully using credentials.")
        return True
    except Exception as e:
        logger.error(f"Failed to log in using credentials: {e}")
        return False