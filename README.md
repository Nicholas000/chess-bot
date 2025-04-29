# chess-bot
AI chess bot integrated using Lichess API

Step 1: Install required libraries
----------------------
```
pip install -r requirements.txt
```

Step 2: Add .env file
----------------------
add the `.env` file with the following contents:

```
LICHESS_CLIENT_ID="lichess-oauth-flask"
SECRET_KEY="{ secure random key for flask sessions }"
```

Step 3: Run the App
-------------------
run the app:
```
python src\app\app.py
```

Step 4: Load the URL
--------------------
load this url in your browser: http://127.0.0.1:5000/

Step 5: Authorize
-----------
hit the "Authorize" button on the webpage that pops up

Step 6: UI
--------------
interact with the UI to start game, view games, etc. **(This functionality needs to be added)**