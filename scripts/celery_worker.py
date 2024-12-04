# scripts/celery_worker.py

from celery import Celery
import os
from dotenv import load_dotenv
import ssl
from scripts.logging_setup import get_logger

# Load environment variables
load_dotenv()

# Get logger from centralized setup
logger = get_logger("celery_worker")

# Set up Redis URL
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Configure Celery with SSL options for `rediss://`
broker_use_ssl = None
redis_backend_use_ssl = None

if REDIS_URL.startswith('rediss://'):
    broker_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_REQUIRED  # Use CERT_OPTIONAL if validation is relaxed
    }
    redis_backend_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_REQUIRED  # Same as above
    }

celery = Celery(
    'worker',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Apply SSL configurations
if broker_use_ssl:
    celery.conf.update(
        broker_use_ssl=broker_use_ssl,
        redis_backend_use_ssl=redis_backend_use_ssl
    )

# General Celery configurations to prevent overloading Redis
celery.conf.update(
    task_acks_late=True,  # Acknowledge tasks only after successful execution
    worker_prefetch_multiplier=1,  # Prevent prefetching too many tasks
    task_reject_on_worker_lost=True,  # Avoid duplicate processing
)

# Retry policy: Backoff logic for retries
@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def run_import_foods(self, log_text):
    from scripts.main import main as process_log
    try:
        logger.info(f"Processing task {self.request.id}.")
        result = process_log(log_text)
        logger.info(f"Task {self.request.id} completed successfully.")
        return result
    except Exception as e:
        # Use exponential backoff for retries
        delay = self.default_retry_delay * (2 ** self.request.retries)
        if self.request.retries >= self.max_retries:
            logger.error(f"Task {self.request.id} failed after {self.max_retries} retries: {e}", exc_info=True)
            raise
        else:
            logger.warning(f"Task {self.request.id} failed, retrying in {delay} seconds: {e}", exc_info=True)
            raise self.retry(exc=e, countdown=delay)
