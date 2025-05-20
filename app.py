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
env_file = '.env.development' if os.getenv('ENV', 'dev') == 'dev' else '.env.production'
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

ENV = os.getenv("ENV", "dev").lower()
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
    }
)

@app.before_request
def enforce_production_domain():
    if ENV == "production":
        # Always redirect to foodlog.theespeys.com if not already there
        if request.host != "foodlog.theespeys.com":
            # If coming from theespeys.com/foodlog, strip the /foodlog prefix
            if request.host == "theespeys.com" and request.path.startswith("/foodlog"):
                new_path = request.path[7:] if request.path.startswith("/foodlog") else request.path
                return redirect(f"https://foodlog.theespeys.com{new_path}", code=301)
            # For any other host, redirect to the root of foodlog.theespeys.com
            return redirect(f"https://foodlog.theespeys.com{request.path}", code=301)

# Public route: the index page is now viewable by anyone.
@app.route('/', methods=['GET'])
def index():
    logger.info("Serving main application page.")
    return render_template('index.html')

# Legacy route - redirect to new domain
@app.route('/foodlog', methods=['GET'], strict_slashes=False)
@app.route('/foodlog/', methods=['GET'], strict_slashes=False)
def foodlog():
    return redirect("https://foodlog.theespeys.com", code=301)

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

@app.route('/foodlog/example', methods=['GET'])
def get_example_legacy():
    return redirect(url_for('get_example'))

# This route now checks if a user is logged in.
@app.route('/submit-log', methods=['POST'])
def submit_log():
    if not session.get("user"):
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

@app.route('/foodlog/submit-log', methods=['POST'])
def submit_log_legacy():
    return redirect(url_for('submit_log'), code=307)

# Authentication routes
@app.route('/login')
@app.route('/foodlog/login')
def login_route():
    redirect_uri = get_oauth_callback()
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
@app.route('/foodlog/logout')
def logout():
    session.pop('user', None)
    logger.info("User logged out.")
    if ENV == "production":
        return redirect("https://foodlog.theespeys.com")
    else:
        return redirect(url_for('index'))

def get_oauth_callback():
    if ENV == "production":
        return "https://foodlog.theespeys.com/oauth2callback"
    else:
        return "http://localhost:5001/oauth2callback"

@app.route('/debug/env')
def debug_env():
    chrome_shim = os.getenv("GOOGLE_CHROME_SHIM")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    return Response(
        f"ENV: {ENV}\nGOOGLE_CHROME_SHIM: {chrome_shim}\nCHROMEDRIVER_PATH: {chromedriver_path}",
        mimetype='text/plain'
    )

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
