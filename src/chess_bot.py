# TODO: Add code for bot that actually makes intelligent moves
import random
import threading
from typing import Any, Dict

import berserk
import chess

from src.move_generator import get_moves_from_fen

# TODO: Move print statements to log to separate games when multiple instances


class ChessBot:
    def __init__(self, response: Dict[str, Any], client: berserk.Client):
        # TODO: Verify response is in the correct format
        self.id = response["id"]
        self.full_id = response["fullId"]
        self.fen = response["fen"]
        self.client = client
        self.bot_id = self.client.account.get()["id"]
        self.board = chess.Board(fen=self.fen)

        self.move_made_event = threading.Event()

        self.game_stream_thread = threading.Thread(target=self.stream_game_state)
        self.game_stream_thread.start()

        self.move_thread = threading.Thread(target=self.move_controller)
        self.move_thread.start()

        self.adversarial_search_thread = threading.Thread(
            target=self.adversarial_search
        )
        self.adversarial_search_thread.start()

        # TODO: Andrew: You may want to create a new thread here that fills out the search tree. This way, the search tree can be filled out

    def adversarial_search(self):
        # TODO: Andrew: Implement adversarial search tree building; You may need to create a class to control the search.
        # This class would implement some function (i.e. get_best_move) that the move thread can call to get the best move given the board state
        ...

    def move_controller(self):
        while True:
            self.move_made_event.wait()  # Block until the opponent makes their move

            # Choose Best Move and Make Move
            fen = self.board.fen()
            # get_best_move(fen) # TODO: Andrew: Implement adversarial search for best move

            # Random Move
            legal_moves = get_moves_from_fen(fen)  # Get legal moves
            if (
                len(legal_moves) == 0
            ):  # Must handle no legal moves; Game should end, but may not register until next event
                print("No legal moves!")
                continue
            best_move = random.choice(legal_moves)

            self.client.bots.make_move(self.id, best_move)

            self.move_made_event.clear()  # Clear to wait again until thread watching for opponent moves resets it

    def stream_game_state(self):
        print(f"Streaming game state on thread {self.game_stream_thread.getName()}")

        game_state_response = self.client.bots.stream_game_state(self.id)
        for event in game_state_response:
            match event["type"]:
                case "gameState":
                    match event["status"]:
                        case "started":
                            # TODO: Maybe implement check for takebacks
                            moves = event["moves"]
                            last_move = moves.split(" ")[-1]
                            try:
                                self.board.push(
                                    chess.Move.from_uci(last_move)
                                )  # Update board state with new move
                            except AssertionError as ae:
                                print(ae)

                            if self.is_my_turn:
                                print("You played:", last_move)
                            else:
                                print("Opponent played:", last_move)
                                self.move_made_event.set()  # Set so move making thread will make a move

                            # TODO: Use num_moves % 2 to determine whose move
                            self.is_my_turn = not self.is_my_turn  # change turns
                        case "mate" | "resign" | "draw" | "stalemate":  # Game ended
                            print(f"Game ended by {event["status"]}!")
                            print(
                                "You won!"
                                if event.get("winner") == self.player_color
                                else "You lost!"
                            )
                            return
                        case _:
                            print(event)
                case "gameFull":
                    match event["state"]["status"]:
                        case "started":
                            # Get player color of the bot
                            if self.bot_id == event["white"].get("id", None):
                                self.player_color = "white"
                            elif self.bot_id == event["black"].get("id", None):
                                self.player_color = "black"
                            else:
                                print(
                                    "Unable to determine bot color! Defaulting to white!"
                                )
                                self.player_color = "black"

                            # Set whos turn it is to start move control loop
                            self.is_my_turn = self.player_color == "white"
                            if self.is_my_turn:
                                self.move_made_event.set()
                        case _:
                            print(event)
                case _:
                    print(event)

        # Start listening for events
        # On move event from other player (LOOP):
        # - Pass board state to move engine
        # - Get best move from move engine
        # - Play best move


# TODO: Andrew
class MoveEngine:
    def __init__(self):
        pass

    def get_best_move(fen: str) -> str:
        """
        Use adversarial approach to get the best move given an initial position

        Approach: minimax, alpha-beta pruning;
        Depth-limited search: can only search a few levels deep in the search tree;
        heuristic function to evaluate position: each piece is assigned a weighted value which is added(subtracted) if that piece type is taken by(from) the bot

        Params:
        fen (str): encoded string representation of the board state

        Returns:
        move (str): UCI encoded string representation of best move
        """
