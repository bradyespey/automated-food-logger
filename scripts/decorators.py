# scripts/decorators.py

import logging
import time
from functools import wraps
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
)

from scripts.navigation import close_overlays

def retry_on_failure(max_retries=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(driver, *args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(driver, *args, **kwargs)
                except (
                    NoSuchElementException,
                    TimeoutException,
                    ElementClickInterceptedException,
                    StaleElementReferenceException,
                    WebDriverException,
                ) as e:
                    attempts += 1
                    logger = logging.getLogger(func.__module__)
                    logger.warning(f"Attempt {attempts} for '{func.__name__}' failed: {e}")
                    if attempts < max_retries:
                        logger.info("Refreshing the page and retrying.")
                        driver.refresh()
                        close_overlays(driver)
                        time.sleep(delay)
                    else:
                        logger.error(f"Failed to execute '{func.__name__}' after {max_retries} attempts.")
                        raise e  # Raise the exception after final attempt
        return wrapper
    return decorator
