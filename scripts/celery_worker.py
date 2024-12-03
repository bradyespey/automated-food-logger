# scripts/celery_worker.py

from celery import Celery
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Ensure the logs directory exists
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
log_directory = os.path.join(project_root, 'logs')
os.makedirs(log_directory, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Adjust as needed
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to console
        logging.FileHandler(os.path.join(log_directory, "celery_worker.log"))
    ]
)
logger = logging.getLogger(__name__)

# Initialize Celery
celery = Celery(
    'worker',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def run_import_foods(self, log_text):
    from scripts.main import main as process_log  # Import after ensuring environment variables are loaded
    try:
        result = process_log(log_text)
        logger.info(f"Task {self.request.id} completed successfully.")
        return result  # Ensure the result is returned to the backend
    except Exception as e:
        logger.error(f"Task {self.request.id} failed: {e}", exc_info=True)
        raise self.retry(exc=e)