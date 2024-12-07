# app.py

import os
import secrets
from flask import Flask, redirect, url_for, session, request, jsonify, render_template, Response
from authlib.integrations.flask_client import OAuth
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from dotenv import load_dotenv
from scripts.main import main as process_log
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# --------------------- Sentry Integration ---------------------

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),  # Ensure this environment variable is set in Heroku
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
)

# --------------------- Flask App Setup ---------------------

# Determine absolute path
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

env = os.getenv('ENV', 'dev')
if env == 'dev':
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(level=logging_level)
logger = logging.getLogger(__name__)

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
        'prompt': 'consent',
        'access_type': 'offline',
    }
)

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
    return redirect(url_for('foodlog'))

@app.route('/foodlog/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    nonce = secrets.token_urlsafe(16)
    session['nonce'] = nonce
    logger.info("Initiating OAuth flow.")
    return google.authorize_redirect(redirect_uri, nonce=nonce)

@app.route('/foodlog/oauth2callback')
def authorize():
    try:
        token = google.authorize_access_token()
        nonce = session.get('nonce')
        user_info = google.parse_id_token(token, nonce=nonce)
        session['user'] = user_info
        logger.info(f"User authenticated: {user_info}")
        return redirect(url_for('foodlog'))
    except Exception as e:
        logger.error(f"OAuth authorization failed: {e}")
        return "Authorization failed.", 500

@app.route('/foodlog/logout')
def logout():
    session.pop('user', None)
    logger.info("User logged out.")
    return redirect(url_for('login'))

@app.route('/foodlog')
@requires_auth
def foodlog():
    logger.info("Serving main application page.")
    return render_template('index.html')

# Define the path to the nutritional_data.txt file
EXAMPLE_FILE = os.path.join(basedir, 'txt', 'nutritional_data.txt')

# --------------------- Separate Saving Function ---------------------

def save_log_to_file(log_text):
    """
    Saves the provided log_text to the nutritional_data.txt file.
    Returns True if successful, False otherwise.
    """
    try:
        os.makedirs(os.path.dirname(EXAMPLE_FILE), exist_ok=True)
        with open(EXAMPLE_FILE, 'w', encoding='utf-8') as f:
            f.write(log_text)
        logger.info("Saved food log to nutritional_data.txt.")
        return True
    except Exception as e:
        logger.error(f"Failed to save food log: {e}", exc_info=True)
        return False

# --------------------- Modified save_log Route ---------------------

@app.route('/foodlog/save', methods=['POST'])
@requires_auth
def save_log():
    data = request.json
    log_text = data.get('log', '')
    success = save_log_to_file(log_text)
    if success:
        return "Saved", 200
    else:
        return "Failed to save log.", 500

# --------------------- Updated submit_log Function ---------------------

@app.route('/foodlog/submit-log', methods=['POST'])
@requires_auth
def submit_log():
    data = request.json
    log_text = data.get('log')
    logger.debug(f"Received log text: {log_text}")

    if log_text:
        try:
            output = process_log(log_text)
            logger.info("Log processed successfully.")
            # Save the current log to nutritional_data.txt using the separate function
            success = save_log_to_file(log_text)
            if not success:
                logger.error("Failed to save the log after processing.")
                return jsonify({"error": "Failed to save log."}), 500
            return jsonify(output=output), 200
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return jsonify(output=f"Processing failed: {e}"), 500
    else:
        logger.error("No log text provided.")
        return jsonify(output="No log text provided."), 400

# --------------------- Temporary Route for Debugging ---------------------

@app.route('/debug/env')
@requires_auth
def debug_env():
    chrome_shim = os.getenv("GOOGLE_CHROME_SHIM")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    return Response(f"GOOGLE_CHROME_SHIM: {chrome_shim}\nCHROMEDRIVER_PATH: {chromedriver_path}", mimetype='text/plain')

# --------------------- Run the Flask App ---------------------

if __name__ == "__main__":
    app.run(debug=(env == 'dev'))
