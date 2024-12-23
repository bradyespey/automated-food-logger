import os
import secrets
from flask import Flask, redirect, url_for, session, request, jsonify, render_template, Response
from flask_session import Session
from authlib.integrations.flask_client import OAuth
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from dotenv import load_dotenv
from scripts.main import main as process_log
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Initialize Sentry for error tracking
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
)

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# Flask app setup
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Fix proxy headers for Cloudflare/Heroku
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Logging setup
env = os.getenv('ENV', 'dev')
logging_level = logging.DEBUG if env == 'dev' else logging.INFO
logging.basicConfig(level=logging_level)
logger = logging.getLogger(__name__)

# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(basedir, 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
        'token_endpoint_auth_method': 'client_secret_post',
        'prompt': 'consent',
        'access_type': 'offline',
    }
)

# Authentication decorator
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            logger.info("User not authenticated. Redirecting to login.")
            return redirect(url_for('login_route'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return redirect(url_for('foodlog'))

@app.route('/foodlog/login')
def login_route():
    redirect_uri = url_for('authorize', _external=True)
    nonce = secrets.token_urlsafe(16)
    session['nonce'] = nonce
    logger.info(f"Generated redirect URI: {redirect_uri}")
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
        logger.error(f"OAuth authorization failed: {e}", exc_info=True)
        return "Authorization failed.", 500

@app.route('/foodlog/logout')
def logout():
    session.pop('user', None)
    logger.info("User logged out.")
    return redirect(url_for('login_route'))

@app.route('/foodlog')
@requires_auth
def foodlog():
    logger.info("Serving main application page.")
    return render_template('index.html')

# Example directory and file setup
EXAMPLE_DIR = os.path.join(basedir, 'txt')
EXAMPLE_FILE = os.path.join(EXAMPLE_DIR, 'nutritional_data.txt')

if not os.path.exists(EXAMPLE_DIR):
    os.makedirs(EXAMPLE_DIR, exist_ok=True)

if not os.path.exists(EXAMPLE_FILE):
    with open(EXAMPLE_FILE, 'w', encoding='utf-8') as f:
        f.write("Sample food log content.\nYou can modify this file at runtime, but changes won't persist after a dyno restart.\n")

# Save log to file
def save_log_to_file(log_text):
    try:
        with open(EXAMPLE_FILE, 'w', encoding='utf-8') as f:
            f.write(log_text)
        logger.info("Saved food log to nutritional_data.txt.")
        return True
    except Exception as e:
        logger.error(f"Failed to save food log: {e}", exc_info=True)
        return False

@app.route('/foodlog/example', methods=['GET'])
@requires_auth
def get_example():
    if os.path.exists(EXAMPLE_FILE):
        with open(EXAMPLE_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, 200
    else:
        logger.warning("No example file found.")
        return "No example file found.", 404

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

@app.route('/foodlog/submit-log', methods=['POST'])
@requires_auth
def submit_log():
    data = request.json
    log_text = data.get('log', '')
    logger.debug(f"Received log text: {log_text}")

    if log_text:
        try:
            output = process_log(log_text)
            logger.info("Log processed successfully.")
            success = save_log_to_file(log_text)
            if not success:
                logger.error("Failed to save the log after processing.")
                return jsonify({"error": "Failed to save log."}), 500
            return jsonify({"output": output}), 200
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return jsonify({"output": f"Processing failed: {e}"}), 500
    else:
        logger.error("No log text provided.")
        return jsonify({"output": "No log text provided."}), 400

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    return "Internal Server Error", 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return "Internal Server Error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=(env == 'dev'))
