# scripts/logging_setup.py

import logging
import os

LOG_DIR = os.getenv('LOG_DIR', '/tmp/logs' if os.getenv('ENV') == 'prod' else 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(LOG_DIR, f"{name}.log"))
        ]
    )
    return logging.getLogger(name)
