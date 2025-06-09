# chess-bot
AI chess bot integrated using Lichess API

Step 1: Navigate to the project directory
----------------------
cd to the project directory.
i.e.:
```
cd C\Users\...\chess-bot
```

Step 2: Install required libraries
----------------------
```
pip install -r requirements.txt
```

Step 3: Add .env file
----------------------
Add the `.env` file with the following contents (to simplify the set-up work, I have provided this file in the zip folder):

```
SECRET_KEY="{ lichess API key }"
```
If you would like to create your own API key, this thread was helpful in setting it up: https://lichess.org/forum/general-chess-discussion/how-do-you-make-a-lichess-bot

Minimum API key access privileges:
- bot:play
- challenge:write

Step 4: Run the App
-------------------
Run the app:
```
python -m src.gui
```
This should pop up an application window

Step 4: Configure Game Settings and Play
--------------------
In the GUI that pops up, you may:
1. Use the "Settings" section to configure the game settings as you like.
2. Hit "Play AI" to start a game against the Stockfish AI. This should automatically load the game into your web browser.
3. Once you have started a game, use the "Current Game" section to view game settings and reopen the game in your web browser if you accidentally close it.