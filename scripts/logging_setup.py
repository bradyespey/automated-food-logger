# scripts/logging_setup.py

import logging
import os

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels of logs

    # Create handlers if they don't already exist
    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # File handler
        log_file = os.path.join('logs', f'{name}.log')
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger
