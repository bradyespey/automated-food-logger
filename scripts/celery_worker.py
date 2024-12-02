# scripts/celery_worker.py

from celery import Celery
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env in development
env = os.getenv('ENV', 'dev')
if env == 'dev':
    load_dotenv()

# Configure logging for Celery
if env == 'dev':
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(level=logging_level)
logger = logging.getLogger(__name__)

# Initialize Celery with Redis broker and backend
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app = Celery(
    'worker',
    broker=redis_url,
    backend=redis_url
)

# Update Celery configuration to include SSL parameters if using SSL (e.g., Upstash)
if redis_url.startswith('rediss://'):
    import ssl
    app.conf.broker_transport_options = {
        'ssl': {
            'ssl_cert_reqs': ssl.CERT_NONE  # Use ssl.CERT_REQUIRED in production for security
        }
    }
    app.conf.result_backend_transport_options = {
        'ssl': {
            'ssl_cert_reqs': ssl.CERT_NONE
        }
    }

# Address the deprecation warning
app.conf.broker_connection_retry_on_startup = True

@app.task(bind=True, max_retries=3, default_retry_delay=10)
def run_import_foods(self, log_text):
    """
    Celery task to run the main food logging process.
    """
    logger.info(f"Task {self.request.id} started with log_text: {log_text}")
    try:
        # Import the main process function
        from scripts.main import main as process_log

        # Set the LOG_TEXT environment variable
        os.environ['LOG_TEXT'] = log_text

        # Run the main function
        process_log()

        logger.info(f"Task {self.request.id} succeeded.")
        return "Food log processed successfully."
    except Exception as exc:
        logger.error(f"Task {self.request.id} failed: {exc}")
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(f"Task {self.request.id} exceeded max retries.")
            return f"Task failed after retries: {exc}"