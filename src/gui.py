import os
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import berserk
import berserk.exceptions
import requests
from dotenv import load_dotenv

from src.chess_bot import ChessBot


# TODO: Figure out why program locks after closing gui
class ChessGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Lichess AI")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        # self.root.geometry("800x500")

        self.ai_difficulty = tk.IntVar(self.root, 1)
        self.player_color = tk.StringVar(self.root, value="random")

        self.start_game_button = ttk.Button(
            self.root, text="Play AI", command=self.play_ai
        )
        self.status_thread = None

        self.active_game = False
        self.active_game_bot: ChessBot = None
        self.active_game_player_color = None

        self.define_styles()

        self.create_game_controls_frame()
        self.create_active_game_frame()

        self.root_grid_layout()

        self.connect_to_lichess()

        self.root.mainloop()

    def _on_closing(self):
        if self.active_game_bot:
            if self.active_game_bot.is_active:
                if messagebox.askokcancel(
                    "Exit",
                    "Are you sure you want to exit? A game is still active and will be resigned if you leave now.",
                ):
                    self.active_game_bot.close()
                    self.root.destroy()
        else:
            self.root.destroy()

    def define_styles(self):
        self.root.wm_iconphoto(
            True, tk.PhotoImage(file=os.path.abspath("src/assets/pawn.png"))
        )

    def create_game_controls_frame(self):
        self.controls_frame = ttk.Labelframe(
            self.root, text="Settings", borderwidth=2, relief="solid", padding=5
        )

        # Set AI Difficulty
        self.ai_difficulty_frame = ttk.Labelframe(
            self.controls_frame,
            text="AI Difficulty",
            borderwidth=2,
            relief="solid",
            padding=5,
        )
        self.ai_difficulty_scale = ttk.LabeledScale(
            self.ai_difficulty_frame,
            from_=1,
            to=9,
            variable=self.ai_difficulty,
            compound="bottom",
            padding=3,
        )
        self.ai_difficulty_scale.grid(row=1, column=1)

        # Set Player Color
        self.player_color_frame = ttk.Labelframe(
            self.controls_frame,
            text="Player Color",
            borderwidth=2,
            relief="solid",
            padding=5,
        )
        self.set_pcol_white_rb = ttk.Radiobutton(
            self.player_color_frame,
            variable=self.player_color,
            value="white",
            text="White",
        )
        self.set_pcol_black_rb = ttk.Radiobutton(
            self.player_color_frame,
            variable=self.player_color,
            value="black",
            text="Black",
        )
        self.set_pcol_random_rb = ttk.Radiobutton(
            self.player_color_frame,
            variable=self.player_color,
            value="random",
            text="Random",
        )
        self.set_pcol_random_rb.grid(row=1, column=1, sticky="w")
        self.set_pcol_white_rb.grid(row=2, column=1, sticky="w")
        self.set_pcol_black_rb.grid(row=3, column=1, sticky="w")

        # Controls frame grid layout
        self.ai_difficulty_frame.grid(row=1, column=1, sticky="ew")
        self.player_color_frame.grid(row=2, column=1, sticky="ew")

    def create_active_game_frame(self):
        self.active_game_frame = ttk.Labelframe(
            self.root, text="Current Game", borderwidth=2, relief="solid", padding=5
        )

    def create_game_info_frame(self, url: str, ai_difficulty: int, player_color: str):
        self.game_info_frame = ttk.Frame(self.active_game_frame)
        self.ai_difficulty_label = ttk.Label(
            self.game_info_frame, text=f"AI Difficulty: {ai_difficulty}"
        )
        self.player_color_label = ttk.Label(
            self.game_info_frame,
            text=f"Player Color: {(
            "Unknown" if player_color == "random" else player_color.capitalize()
        )}",
        )
        self.link_button = ttk.Button(
            self.game_info_frame,
            text="Open Game",
            command=lambda: webbrowser.open(url),
        )
        self.status_var = tk.StringVar(self.game_info_frame, value="Starting")
        self.status_var.trace_add("write", self._update_status_style)
        self.status_label = ttk.Label(
            self.game_info_frame,
            textvariable=self.status_var,
            relief="solid",
            padding=5,
            anchor="center",
        )
        self.status_label.grid(row=1, column=1, pady=5, sticky="nsew")
        self.ai_difficulty_label.grid(row=2, column=1, pady=5, sticky="nsew")
        self.player_color_label.grid(row=3, column=1, pady=5, sticky="nsew")
        self.link_button.grid(row=4, column=1, pady=5, sticky="nsew")

        self.game_info_frame.grid(row=1, column=1, sticky="nsew")
        self.game_info_frame.grid_columnconfigure(1, weight=1)
        self.active_game_frame.grid_columnconfigure(1, weight=1)

    def _update_status_style(self, _, _1, _2):
        status_styles = {
            "Starting": {"background": "lightgrey"},
            "Active": {"background": "white"},
            "Win": {"background": "b6d7a8"},  # gree
            "Loss": {"background": "#e06666"},  # red
            "Draw": {"background": "#ffe599"},  # yellow
        }

        print(f"Updating to status: {self.status_var.get()}")
        configs = status_styles.get(self.status_var.get(), {"background": "white"})

        self.status_label.configure(**configs)

    def start_status_watcher(self):
        self.last_status = None
        self.watch_status_loop()

    def watch_status_loop(self):
        """Repeatedly check the status of the game and update the status display"""
        current_status = self.active_game_bot.status

        if current_status != self.last_status:
            self.last_status = current_status
            self.status_var.set(current_status.capitalize())

        # Schedule the next check (non-blocking)
        self.root.after(1000, self.watch_status_loop)  # every 1 second

    def start_color_watcher(self):
        self.last_color = None
        self.watch_color_loop()

    def watch_color_loop(self):
        """Look for player color value from ChessBot and update the display when it is found"""
        current_color = self.active_game_bot.player_color

        if current_color != self.last_color and current_color is not None:
            self.last_color = current_color
            self.player_color_label.configure(
                text=f"Player Color: {current_color.capitalize()}"
            )
        else:
            self.root.after(1000, self.watch_color_loop)  # every 1 second

    def start_watchers(self):
        self.start_status_watcher()
        self.start_color_watcher()

    def root_grid_layout(self):
        self.root.grid_columnconfigure(2, minsize=180, weight=1)
        self.controls_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.start_game_button.grid(
            row=2, column=1, columnspan=2, padx=10, pady=10, sticky="nsew"
        )
        self.active_game_frame.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")

    # Non-gui Functions
    def connect_to_lichess(self):
        load_dotenv()
        self.LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")
        secret_key = os.getenv("SECRET_KEY")

        # session = berserk.TokenSession(secret_key)
        # Create a custom requests session
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {secret_key}",
                "User-Agent": "chess-bot/1.0 (contact: github.com/Nicholas000/chess-bot)",
            }
        )

        self.client = berserk.Client(session=session)

    def play_ai(self):
        # Warn user if game is active already
        def confirm_and_close():
            if messagebox.askokcancel(
                "Start New Game",
                "Are you sure you want to start a new game? The current game is still active and will be resigned if you start a new one.",
            ):
                self.active_game_bot.close()

        if self.active_game_bot and self.active_game_bot.is_active:
            self.root.after(0, confirm_and_close)  # Must be called from main GUI thread
            return

        # Create a new AI
        self.create_ai()

    def create_ai(self):
        args = {
            "level": self.ai_difficulty.get(),
            "clock_limit": 3600,
            "clock_increment": 30,
            "variant": "standard",
            "color": self.player_color.get(),
        }

        try:
            response = self.client.challenges.create_ai(**args)
            self.on_ai_created(response, args)
        except berserk.exceptions.ResponseError as re:
            if re.status_code == 429:
                print("Too many API requests! Waiting 1min...")
                self.root.after(60000, self.create_ai)

    def on_ai_created(self, response, args):
        fullId = response["fullId"]
        url = f"{self.LICHESS_HOST}/{fullId}"
        webbrowser.open(url)

        self.active_game_bot = ChessBot(response, self.client)
        self.active_game = True

        self.create_game_info_frame(url, args["level"], args["color"])
        self.start_watchers()


def main():
    ChessGUI()


if __name__ == "__main__":
    main()
