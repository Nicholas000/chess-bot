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
SECRET_KEY="{ lichess API key }"
```
Minimum API key access privileges:
- bot:play
- challenge:write

Step 3: Run the App
-------------------
run the app:
```
python -m src.app.app
```

Step 4: Load the URL
--------------------
load this url in your browser: http://127.0.0.1:5000/

Step 5: Start Game
-----------
hit the "Play AI" button to start a game with the Stockfish AI. It will automatically open up the game in a separate tab

<!-- Step 6: UI
--------------
interact with the UI to start game, view games, etc. **(This functionality needs to be added)** -->