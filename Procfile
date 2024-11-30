web: gunicorn app:app
worker: celery -A scripts.celery_worker worker --loglevel=info