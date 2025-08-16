# scripts/login.py

import logging
import os
import time
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

def initialize_driver(headless=False): # Change to False to run with visible Chrome, change to True to run without visible Chrome
    try:
        logger.info(f"Initializing Chrome driver with headless={headless}")
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
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            logger.info("Running in headed mode.")

        # Mimic normal browser behavior
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use a unique Chrome profile for each session to avoid conflicts
        import tempfile
        import uuid
        temp_dir = tempfile.mkdtemp(prefix="chrome_profile_")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        chrome_options.add_argument("--profile-directory=temp_profile")
        logger.info(f"Using temporary Chrome profile: {temp_dir}")

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
            logger.info("Importing ChromeDriverManager...")
            from webdriver_manager.chrome import ChromeDriverManager
            logger.info("ChromeDriverManager imported successfully")
            
            logger.info("Installing ChromeDriver...")
            chromedriver_path = ChromeDriverManager().install()
            logger.info(f"ChromeDriver installed at: {chromedriver_path}")
            
            service = Service(executable_path=chromedriver_path)
            logger.info("ChromeDriver service created successfully.")

        logger.info("Creating Chrome WebDriver instance...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome WebDriver instance created successfully.")

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
        
        # Wait a moment for the login process to start
        time.sleep(2)
        
        # Check if there are any error messages
        try:
            error_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'Error') or contains(text(), 'invalid') or contains(text(), 'Invalid')]")
            if error_elements:
                for error in error_elements:
                    if error.is_displayed():
                        logger.warning(f"Login error message found: {error.text}")
        except:
            pass
        
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
        # Wait for page to load after login
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Try multiple verification methods
        verification_successful = False
        
        # Method 1: Look for current date element (original method)
        try:
            current_date_element = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "GMQI3OOBIYB"))
            )
            current_date_text = current_date_element.text.strip()
            logger.info(f"Login verified. Current date found: {current_date_text}")
            verification_successful = True
        except:
            logger.debug("Method 1 failed: Could not find GMQI3OOBIYB class")
        
        # Method 2: Look for common dashboard elements
        if not verification_successful:
            try:
                # Look for common dashboard indicators
                dashboard_indicators = [
                    "//div[contains(text(), 'Today')]",
                    "//div[contains(text(), 'Daily')]",
                    "//div[contains(text(), 'Food')]",
                    "//div[contains(text(), 'Calories')]",
                    "//a[contains(@href, 'food')]",
                    "//button[contains(text(), 'Add')]"
                ]
                
                for xpath in dashboard_indicators:
                    try:
                        element = WebDriverWait(driver, 2).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        logger.info(f"Login verified. Dashboard element found: {xpath}")
                        verification_successful = True
                        break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"Method 2 failed: {e}")
        
        # Method 3: Check if we're still on login page
        if not verification_successful:
            try:
                # If we can still find login elements, login failed
                login_elements = driver.find_elements(By.ID, "email")
                if login_elements:
                    logger.error("Login failed: Still on login page")
                    return False
            except:
                pass
        
        # Method 4: Check URL to see if we're redirected to dashboard
        if not verification_successful:
            current_url = driver.current_url
            if "login" not in current_url.lower() and "my.loseit.com" in current_url:
                logger.info(f"Login verified. Redirected to: {current_url}")
                verification_successful = True
        
        if verification_successful:
            logger.info("Login verification successful")
            return True
        else:
            logger.error("Login verification failed: Could not confirm successful login")
            return False
            
    except TimeoutException:
        logger.error("Timeout during login verification", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error during login verification: {e}", exc_info=True)
        return False
