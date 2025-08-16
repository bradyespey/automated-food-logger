# app.py

import os
import logging
from flask import Flask, redirect, url_for, session, request, jsonify, render_template, Response
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from scripts.main import main as process_log

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
# Try to load .env.development first, then fall back to .env
env_file = '.env.development' if os.getenv('ENV', 'dev') == 'dev' else '.env.production'
if not os.path.exists(os.path.join(basedir, env_file)):
    env_file = '.env'
load_dotenv(os.path.join(basedir, env_file))

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
)

app = Flask(
    __name__,
    static_folder='static',
    static_url_path='/static',
    template_folder='templates'
)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

ENV = os.getenv('ENV', 'dev').lower()
logging_level = logging.DEBUG if ENV == "dev" else logging.INFO
logging.basicConfig(level=logging_level)
logger = logging.getLogger(__name__)

if ENV in ["production", "heroku"]:
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True
else:
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
        'prompt': 'consent',
        'access_type': 'offline',
        'redirect_uri': 'https://foodlog.theespeys.com/oauth2callback' if ENV == "production" else 'http://localhost:5001/foodlog/oauth2callback'
    }
)

@app.before_request
def enforce_production_domain():
    if ENV == "production":
        # For any host that's not foodlog.theespeys.com, redirect to foodlog.theespeys.com
        if request.host != "foodlog.theespeys.com" and not request.path.startswith("/static/"):
            return redirect(f"https://foodlog.theespeys.com{request.path}", code=301)

# Public route: the index page is now viewable by anyone.
@app.route('/', methods=['GET'])
def index():
    logger.info("Serving main application page.")
    return render_template('index.html')

# Public route: the example file is viewable by anyone.
@app.route('/example', methods=['GET'])
def get_example():
    EXAMPLE_DIR = os.path.join(basedir, 'txt')
    EXAMPLE_FILE = os.path.join(EXAMPLE_DIR, 'nutritional_data_example.txt')
    if not os.path.exists(EXAMPLE_DIR):
        os.makedirs(EXAMPLE_DIR, exist_ok=True)
    if not os.path.exists(EXAMPLE_FILE):
        with open(EXAMPLE_FILE, 'w', encoding='utf-8') as f:
            f.write("Sample food log content.\nYou can modify this file manually.")
    if os.path.exists(EXAMPLE_FILE):
        with open(EXAMPLE_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, 200
    else:
        logger.warning("No example file found.")
        return "No example file found.", 404

# This route now checks if a user is logged in.
@app.route('/submit-log', methods=['POST'])
def submit_log():
    # Temporarily bypass OAuth for testing ChromeDriver
    if not session.get("user") and ENV != "dev":
        return jsonify({"output": "<span style='color: red;'>Please log in to log food.</span>"}), 403
    data = request.json
    log_text = data.get('log', '')
    log_water = data.get('log_water', True)
    logger.debug(f"Received log text: {log_text}")
    logger.debug(f"Log water flag: {log_water}")
    if log_text:
        try:
            output = process_log(log_text, log_water)
            logger.info("Log processed successfully.")
            return jsonify({"output": output}), 200
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return jsonify({"output": f"Processing failed: {e}"}), 500
    else:
        logger.error("No log text provided.")
        return jsonify({"output": "No log text provided."}), 400

# Authentication routes
@app.route('/login')
def login_route():
    redirect_uri = 'https://foodlog.theespeys.com/oauth2callback' if ENV == "production" else 'http://localhost:5001/foodlog/oauth2callback'
    logger.info(f"Initiating OAuth flow. Redirect URI = {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route('/oauth2callback')
@app.route('/foodlog/oauth2callback')
def authorize():
    logger.debug(f"OAuth callback received with args: {request.args}")
    try:
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token, nonce=None)
        session['user'] = user_info
        logger.info(f"User authenticated: {user_info}")
        if ENV == "production":
            return redirect("https://foodlog.theespeys.com")
        else:
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"OAuth authorization failed: {e}", exc_info=True)
        return "Authorization failed.", 400

@app.route('/logout')
def logout():
    session.pop('user', None)
    logger.info("User logged out.")
    if ENV == "production":
        return redirect("https://foodlog.theespeys.com")
    else:
        return redirect(url_for('index'))

def get_oauth_callback():
    """Get the OAuth callback URL based on the environment."""
    redirect_uri = os.getenv('REDIRECT_URI')
    if not redirect_uri:
        if ENV == "production":
            redirect_uri = "https://foodlog.theespeys.com/oauth2callback"
        else:
            redirect_uri = "http://localhost:5001/oauth2callback"
    logger.info(f"Using OAuth callback URL: {redirect_uri}")
    return redirect_uri

@app.route('/debug/env')
def debug_env():
    chrome_shim = os.getenv("GOOGLE_CHROME_SHIM")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    return Response(
        f"ENV: {ENV}\nGOOGLE_CHROME_SHIM: {chrome_shim}\nCHROMEDRIVER_PATH: {chromedriver_path}",
        mimetype='text/plain'
    )

# Catch-all route for /foodlog paths
@app.route('/foodlog/<path:path>')
def foodlog_redirect(path):
    return redirect(f"/{path}", code=301)

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"Page not found: {request.path}")
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    return "Internal Server Error", 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return "Internal Server Error", 500

@app.after_request
def set_secure_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 5001)), debug=(ENV == 'dev'), use_reloader=False)
