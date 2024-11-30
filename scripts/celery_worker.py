# celery_worker.py

from celery import Celery
import os
import subprocess

app = Celery('worker', broker=os.environ.get('REDIS_URL'))

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