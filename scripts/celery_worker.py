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
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_directory, "celery_worker.log"))
    ]
)
logger = logging.getLogger(__name__)

# Set up Redis URL
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Configure Celery with SSL options for `rediss://`
broker_use_ssl = None
redis_backend_use_ssl = None

if REDIS_URL.startswith('rediss://'):
    broker_use_ssl = {
        'ssl_cert_reqs': 'CERT_NONE'  # Change to 'CERT_REQUIRED' or 'CERT_OPTIONAL' if needed
    }
    redis_backend_use_ssl = {
        'ssl_cert_reqs': 'CERT_NONE'  # Same as above
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
