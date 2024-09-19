import os
import json
from flask import Flask, redirect, url_for, session, request, jsonify, send_from_directory
from authlib.integrations.flask_client import OAuth
from functools import wraps
import subprocess
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)

# Load API credentials from JSON file (without printing to terminal)
with open('C:\\Projects\\LoseIt\\api_credentials.json') as f:
    credentials = json.load(f)

# OAuth configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=credentials['client_id'],
    client_secret=credentials['client_secret'],
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    redirect_uri='https://theespeys.com/foodlog/oauth2callback',  # Hard-coded for debugging
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

@app.route('/foodlog/login')
def login():
    # Manually set the correct redirect_uri to use https
    redirect_uri = 'https://theespeys.com/foodlog/oauth2callback'
    return google.authorize_redirect(redirect_uri)

@app.route('/foodlog/oauth2callback')
def authorize():
    token = google.authorize_access_token()
    session['user'] = token
    return redirect(url_for('index'))

@app.route('/foodlog/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/foodlog')
@requires_auth
def index():
    return send_from_directory(directory='.', path='index.html')

@app.route('/foodlog/submit-log', methods=['POST'])
@requires_auth
def submit_log():
    data = request.json
    log_text = data.get('log')
    app.logger.debug(f"Received log text: {log_text}")

    if log_text:
        script_path = "C:\\Projects\\LoseIt\\scripts\\import_foods.py"
        env = os.environ.copy()
        env['LOG_TEXT'] = log_text

        try:
            result = subprocess.run(
                ["python", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )

            output = result.stdout + result.stderr
            app.logger.debug(f"Script output: {output}")

            return jsonify(output=output), 200
        except subprocess.CalledProcessError as e:
            app.logger.error(f"Script execution failed: {e}")
            return jsonify(output=f"Script execution failed: {e}"), 500
        except Exception as e:
            app.logger.error(f"Unexpected error occurred: {e}")
            return jsonify(output=f"Unexpected error occurred: {e}"), 500
    else:
        app.logger.error("No log text provided.")
        return jsonify(output="No log text provided."), 400

@app.route('/foodlog/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.DEBUG)
    app.run(host='0.0.0.0', port=5001, debug=True)
