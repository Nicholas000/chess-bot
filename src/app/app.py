# Authorization code from https://github.com/lakinwecker/lichess-oauth-flask/blob/master/README.md 
import os

from flask import Flask, jsonify, render_template
from flask import url_for

from dotenv import load_dotenv
load_dotenv()

import requests

from authlib.integrations.flask_client import OAuth

LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['LICHESS_CLIENT_ID'] =  os.getenv("LICHESS_CLIENT_ID")
app.config['LICHESS_AUTHORIZE_URL'] = f"{LICHESS_HOST}/oauth"
app.config['LICHESS_ACCESS_TOKEN_URL'] = f"{LICHESS_HOST}/api/token"

oauth = OAuth(app)
oauth.register('lichess', client_kwargs={"code_challenge_method": "S256"})

@app.route('/')
def login():
    redirect_uri = url_for("authorize", _external=True)
    """
    If you need to append scopes to your requests, add the `scope=...` named argument
    to the `.authorize_redirect()` method. For admissible values refer to https://lichess.org/api#section/Authentication. 
    Example with scopes for allowing the app to read the user's email address:
    `return oauth.lichess.authorize_redirect(redirect_uri, scope="email:read")`
    """
    return oauth.lichess.authorize_redirect(redirect_uri, scope="bot:play")

@app.route('/authorize')
def authorize():
    token = oauth.lichess.authorize_access_token()
    bearer = token['access_token']
    headers = {'Authorization': f'Bearer {bearer}'}
    response = requests.get(f"{LICHESS_HOST}/api/account", headers=headers)
    # return jsonify(**response.json())

    # Redirect to home page after authorization
    redirect_uri = url_for("home")
    return app.redirect(redirect_uri)

@app.route('/home')
def home():
    return render_template('index.html')
    # return "Home Page!"

@app.route('/start_game', methods=['POST'])
def start_game():
    # Code to handle the button click (e.g., process data, redirect)
    return "Starting Game!" # Or redirect using redirect(url_for('some_other_route'))

if __name__ == '__main__':
    app.run()