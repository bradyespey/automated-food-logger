# app.py

import os
import json
from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from authlib.integrations.flask_client import OAuth
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from scripts.celery_worker import run_import_foods # Import the Celery task

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Apply ProxyFix to handle Heroku's proxy headers correctly
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# OAuth configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('CLIENT_ID'),
    client_secret=os.environ.get('CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    redirect_uri=os.environ.get('REDIRECT_URI'),  # Set in environment variables
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
        'token_endpoint_auth_method': 'client_secret_post',
        'userinfo_endpoint': 'https://openidconnect.googleapis.com/v1/userinfo',
    }
)

# Function to require authentication
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    # Redirect root URL to /foodlog
    return redirect(url_for('foodlog'))

@app.route('/foodlog/login')
def login():
    # Initiate OAuth flow
    redirect_uri = os.environ.get('REDIRECT_URI')
    return google.authorize_redirect(redirect_uri)

@app.route('/foodlog/oauth2callback')
def authorize():
    # Handle OAuth callback
    try:
        token = google.authorize_access_token()
        session['user'] = token
        app.logger.debug(f"User authenticated: {session['user']}")
        return redirect(url_for('foodlog'))
    except Exception as e:
        app.logger.error(f"OAuth authorization failed: {e}")
        return "Authorization failed.", 500

@app.route('/foodlog/logout')
def logout():
    # Logout user
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/foodlog')
@requires_auth
def foodlog():
    # Serve the main application page
    return render_template('index.html')

@app.route('/foodlog/submit-log', methods=['POST'])
@requires_auth
def submit_log():
    # Handle food log submission
    data = request.json
    log_text = data.get('log')
    app.logger.debug(f"Received log text: {log_text}")

    if log_text:
        try:
            # Enqueue the Celery task
            task = run_import_foods.delay(log_text)
            app.logger.debug(f"Task {task.id} enqueued.")
            return jsonify(output="Your food log is being processed."), 202
        except Exception as e:
            app.logger.error(f"Task enqueue failed: {e}")
            return jsonify(output=f"Task enqueue failed: {e}"), 500
    else:
        app.logger.error("No log text provided.")
        return jsonify(output="No log text provided."), 400

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.DEBUG)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)