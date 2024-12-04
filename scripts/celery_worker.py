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
        'ssl_cert_reqs': ssl.CERT_REQUIRED  # Use CERT_OPTIONAL if you want to relax validation
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

@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def run_import_foods(self, log_text):
    from scripts.main import main as process_log
    try:
        result = process_log(log_text)
        logger.info(f"Task {self.request.id} completed successfully.")
        return result
    except Exception as e:
        logger.error(f"Task {self.request.id} failed: {e}", exc_info=True)
        raise self.retry(exc=e)
