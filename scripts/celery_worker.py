# scripts/celery_worker.py

from celery import Celery
import os
import subprocess

# Initialize Celery with Redis broker using rediss:// for SSL
app = Celery('worker', broker=os.environ.get('REDIS_URL'), backend=os.environ.get('REDIS_URL'))

# Optional: Additional Celery configuration
app.conf.update(
    broker_transport_options={
        'ssl': {
            'cert_reqs': None  # Upstash handles SSL certificates, so you can set cert_reqs to None
        }
    }
)

@app.task
def run_import_foods(log_text):
    env = os.environ.copy()
    env['LOG_TEXT'] = log_text
    result = subprocess.run(
        ["python", "scripts/import_foods.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    return result.stdout + result.stderr