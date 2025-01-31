# app.py

import os
import logging
from flask import Flask, redirect, url_for, session, request, jsonify, render_template, Response
from authlib.integrations.flask_client import OAuth
from functools import wraps
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Import your main Selenium script
from scripts.main import main as process_log

# Load Environment
basedir = os.path.abspath(os.path.dirname(__file__))
env_file = '.env.development' if os.getenv('ENV', 'dev') == 'dev' else '.env.production'
load_dotenv(os.path.join(basedir, env_file))

# Initialize Sentry for error tracking
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
)

# Flask App Initialization
app = Flask(
    __name__,
    static_folder='static',
    static_url_path='/foodlog/static',  # Serve static files under /foodlog/static
    template_folder='templates'
)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')  # Updated variable name

# Environment-specific Configurations
ENV = os.getenv("ENV", "dev").lower()
logging_level = logging.DEBUG if ENV == "dev" else logging.INFO
logging.basicConfig(level=logging_level)
logger = logging.getLogger(__name__)

# Remove ProxyFix since you're not using a reverse proxy
# app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure session cookie settings based on environment
if ENV in ["production", "heroku"]:
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True
    # Optionally set the session cookie domain if needed
    # app.config["SESSION_COOKIE_DOMAIN"] = ".theespeys.com"
else:
    # Development environment => local testing
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False

# Configure Authlib / Google OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),           # Updated variable name
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),   # Updated variable name
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
        'prompt': 'consent',
        'access_type': 'offline',
    }
)

# Authentication Decorator
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            logger.info("User not authenticated. Redirecting to login.")
            return redirect(url_for('login_route'))
        return f(*args, **kwargs)
    return decorated

# Google OAuth Routes
@app.route('/foodlog/login')
def login_route():
    redirect_uri = get_oauth_callback()
    logger.info(f"Initiating OAuth flow. Redirect URI = {redirect_uri}")
    return google.authorize_redirect(redirect_uri)  # Removed custom nonce

@app.route('/foodlog/oauth2callback')
def authorize():
    logger.debug(f"OAuth callback received with args: {request.args}")
    try:
        # Exchange code for token
        token = google.authorize_access_token()

        # Parse user info from ID token with nonce=None
        user_info = google.parse_id_token(token, nonce=None)
        session['user'] = user_info
        logger.info(f"User authenticated: {user_info}")

        return redirect(url_for('foodlog'))
    except Exception as e:
        logger.error(f"OAuth authorization failed: {e}", exc_info=True)
        return "Authorization failed.", 400

@app.route('/foodlog/logout')
def logout():
    session.pop('user', None)
    logger.info("User logged out.")
    return redirect(url_for('login_route'))

# Dynamic OAuth Callback URI
def get_oauth_callback():
    if ENV == "production":
        # Production = theespeys.com
        return "https://theespeys.com/foodlog/oauth2callback"
    else:
        # Dev
        return "http://localhost:5001/foodlog/oauth2callback"

# Optional: Enforce Production Domain
@app.before_request
def enforce_production_domain():
    if ENV == "production":
        # Ensure the request is coming from the correct domain
        if request.host not in ["theespeys.com", "www.theespeys.com"]:
            # Avoid redirecting if already at the desired path
            if request.path != "/foodlog":
                return redirect("https://theespeys.com/foodlog", code=301)

# Routes
@app.route('/')
def home():
    return redirect(url_for('foodlog'))

@app.route('/foodlog', methods=['GET'], strict_slashes=False)
@requires_auth
def foodlog():
    logger.info("Serving main application page.")
    return render_template('index.html')

# Example Log Management
EXAMPLE_DIR = os.path.join(basedir, 'txt')
EXAMPLE_FILE = os.path.join(EXAMPLE_DIR, 'nutritional_data.txt')

if not os.path.exists(EXAMPLE_DIR):
    os.makedirs(EXAMPLE_DIR, exist_ok=True)

if not os.path.exists(EXAMPLE_FILE):
    with open(EXAMPLE_FILE, 'w', encoding='utf-8') as f:
        f.write("Sample food log content.\nYou can modify this file at runtime, but changes won't persist after a dyno restart.\n")

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
    log_water = data.get('log_water', True)  # from frontend toggle

    logger.debug(f"Received log text: {log_text}")
    logger.debug(f"Log water flag: {log_water}")

    if log_text:
        try:
            output = process_log(log_text, log_water)
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

@app.route('/debug/env')
@requires_auth
def debug_env():
    chrome_shim = os.getenv("GOOGLE_CHROME_SHIM")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    return Response(
        f"ENV: {ENV}\nGOOGLE_CHROME_SHIM: {chrome_shim}\nCHROMEDRIVER_PATH: {chromedriver_path}",
        mimetype='text/plain'
    )

# Error Handlers
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    return "Internal Server Error", 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return "Internal Server Error", 500

# Secure Headers (Optional but Recommended)
@app.after_request
def set_secure_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

# Run the Flask App
if __name__ == "__main__":
    # For local dev usage, run on port 5001
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 5001)), debug=(ENV == 'dev'))
