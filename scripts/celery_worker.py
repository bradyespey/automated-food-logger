# scripts/celery_worker.py

from celery import Celery
import os
import subprocess
import ssl
from dotenv import load_dotenv
import logging

# Load environment variables from .env
load_dotenv()

# Configure logging for Celery
logging.basicConfig(level=logging.INFO)
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
    app.conf.broker_transport_options = {
        'ssl': {
            'ssl_cert_reqs': ssl.CERT_NONE  # Use CERT_REQUIRED in production
        }
    }
    app.conf.result_transport_options = {
        'ssl': {
            'ssl_cert_reqs': ssl.CERT_NONE
        }
    }

@app.task(bind=True, max_retries=3, default_retry_delay=10)
def run_import_foods(self, log_text):
    """
    Celery task to run the import_foods.py script.
    """
    logger.info(f"Task {self.request.id} started with log_text: {log_text}")
    try:
        env = os.environ.copy()
        env['LOG_TEXT'] = log_text
        result = subprocess.run(
            ["python", "scripts/import_foods.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            check=True  # Raise CalledProcessError if the command fails
        )
        logger.info(f"Task {self.request.id} succeeded.")
        return result.stdout + result.stderr
    except subprocess.CalledProcessError as exc:
        logger.error(f"Task {self.request.id} failed: {exc.stderr}")
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(f"Task {self.request.id} exceeded max retries.")
            return f"Task failed after retries: {exc.stderr}"
    except Exception as e:
        logger.error(f"Task {self.request.id} encountered an unexpected error: {e}")
        return f"Unexpected error: {str(e)}"