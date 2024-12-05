# app.py

import os
import secrets
from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from authlib.integrations.flask_client import OAuth
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from dotenv import load_dotenv
from scripts.main import main as process_log

# Determine the absolute path to the directory containing app.py
basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from the .env file located in the same directory as app.py
load_dotenv(os.path.join(basedir, '.env'))

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Apply ProxyFix to handle proxy headers correctly
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure logging based on environment
env = os.getenv('ENV', 'dev')
if env == 'dev':
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(level=logging_level)
logger = logging.getLogger(__name__)

# OAuth configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('CLIENT_ID'),
    client_secret=os.environ.get('CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
        'token_endpoint_auth_method': 'client_secret_post',
        'prompt': 'consent',  # Always ask for consent
        'access_type': 'offline',  # Get refresh token
    }
)

# Function to require authentication
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            logger.info("User not authenticated. Redirecting to login.")
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
    redirect_uri = url_for('authorize', _external=True)
    nonce = secrets.token_urlsafe(16)  # Generate a secure nonce
    session['nonce'] = nonce  # Store nonce in session for later verification
    logger.info("Initiating OAuth flow.")
    return google.authorize_redirect(redirect_uri, nonce=nonce)

@app.route('/foodlog/oauth2callback')
def authorize():
    # Handle OAuth callback
    try:
        token = google.authorize_access_token()
        nonce = session.get('nonce')  # Retrieve the stored nonce
        user_info = google.parse_id_token(token, nonce=nonce)  # Pass nonce for verification
        session['user'] = user_info
        logger.info(f"User authenticated: {user_info}")
        return redirect(url_for('foodlog'))
    except Exception as e:
        logger.error(f"OAuth authorization failed: {e}")
        return "Authorization failed.", 500

@app.route('/foodlog/logout')
def logout():
    # Logout user
    session.pop('user', None)
    logger.info("User logged out.")
    return redirect(url_for('login'))

@app.route('/foodlog')
@requires_auth
def foodlog():
    # Serve the main application page
    logger.info("Serving main application page.")
    return render_template('index.html')

@app.route('/foodlog/submit-log', methods=['POST'])
@requires_auth
def submit_log():
    # Handle food log submission
    data = request.json
    log_text = data.get('log')
    logger.debug(f"Received log text: {log_text}")

    if log_text:
        try:
            # Call the processing function synchronously
            output = process_log(log_text)
            logger.info("Log processed successfully.")
            # Return the output directly
            return jsonify(output=output), 200
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return jsonify(output=f"Processing failed: {e}"), 500
    else:
        logger.error("No log text provided.")
        return jsonify(output="No log text provided."), 400

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    logger.info(f"Starting Flask app in {env} mode on port {port}.")
    app.run(host='0.0.0.0', port=port, debug=(env == 'dev'))
