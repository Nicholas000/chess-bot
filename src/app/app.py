import os
import webbrowser

import berserk
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, url_for

load_dotenv()

# import ndjson
# import requests
# from authlib.integrations.flask_client import OAuth

from src.chess_bot import ChessBot

LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

session = berserk.TokenSession(app.secret_key)
client = berserk.Client(session=session)


@app.route("/")
def root():
    return render_template("index.html")


# @app.route("/home")
# def home():
#     return render_template("index.html")
#     # return "Home Page!"


@app.route("/start_stream", methods=["POST"])
def start_stream():
    events = client.bots.stream_incoming_events()
    for i in events:
        print(i)
    return [i for i in events]


# TODO: Support playing multiple games at once although should limit max games to avoid reaching API limit
@app.route("/play_ai", methods=["POST"])
def play_ai():
    # TODO: Possibly implement settings controls on app webpage
    level = 5
    clock_limit = 3600
    clock_increment = 30
    color = None
    response = client.challenges.create_ai(
        level=level,
        clock_limit=clock_limit,
        clock_increment=clock_increment,
        variant="standard",
        color=color,
    )
    fullId = response["fullId"]
    url = f"{LICHESS_HOST}/{fullId}"
    webbrowser.open(url)

    ChessBot(response, client)

    return redirect("/")


@app.route("/get_opponent", methods=["GET"])
def get_opponent():
    bots = client.bots.get_online_bots(1)
    # for bot in bots:
    #     print(bot["id"])
    return [b for b in bots][0]


if __name__ == "__main__":
    app.run()
