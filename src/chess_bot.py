# TODO: Add code for bot that actually makes intelligent moves
import math
import random
import threading
import time
from queue import Queue
from typing import Any, Dict

import berserk
import berserk.exceptions
import chess
import pandas as pd

from src.move_generator import get_moves_from_fen

# TODO: Move print statements to log to separate games when multiple instances


class ChessBot:
    def __init__(self, response: Dict[str, Any], client: berserk.Client):
        self.id = response["id"]
        self.full_id = response["fullId"]
        self.fen = response["fen"]
        self.player_color = None
        self.client = client

        while True:
            try:
                self.bot_id = self.client.account.get()["id"]
                break
            except berserk.exceptions.ResponseError as re:
                if re.status_code == 429:
                    print("Too many API requests! Waiting 1min...")
                    time.sleep(60)
        self.board = chess.Board(
            fen=self.fen
        )  # Keep an internal representation of the board
        self.is_active = (
            True  # Keep track of whether game is active to allow move making
        )
        self.status = None
        self.update_status("starting")
        self.engine = MoveEngine(depth=4)

        self.move_made_event = threading.Event()

        self.game_stream_thread = threading.Thread(target=self.stream_game_state)
        self.game_stream_thread.start()

        self.move_thread = threading.Thread(target=self.move_controller)
        self.move_thread.start()

        self.best_move_message_queue = Queue(1)

        self.best_move_thread = threading.Thread(target=self.best_move_controller)
        self.best_move_thread.start()

    def close(self):
        """Closes any bot game if active and stops threads"""
        print("Closing Game...")
        self.is_active = False  # This should cause all threads to stop after one cycle
        self.best_move_thread.join()
        self.move_thread.join()

        while True:
            try:
                self.client.bots.resign_game(self.id)
                break
            except berserk.exceptions.ResponseError as re:
                if re.status_code == 429:
                    print("Too many API requests! Waiting 1min...")
                    time.sleep(60)

        self.game_stream_thread.join()
        print("Game closed!")

    def wait_for_move_event(self) -> bool:
        while True:
            event_set = self.move_made_event.wait(3)
            if event_set:
                return True
            elif (
                not self.is_active
            ):  # If bot is no longer active, but the thread is still waiting, set the event flag to allow thread to finish
                self.move_made_event.set()
                return False

    def best_move_controller(self):
        print("Playing from Opening Book!")
        self.opening_controller()

        if not self.is_active:
            return

        print("Opening Book exhausted! Using Adversarial Search!")
        self.adversarial_search()

    def random_move_controller(self):
        while self.is_active:
            if not self.wait_for_move_event():
                return  # Block until the opponent makes their move

            fen = self.board.fen()

            # Random Move
            legal_moves = get_moves_from_fen(fen)  # Get legal moves
            if (
                len(legal_moves) == 0
            ):  # Must handle no legal moves; Game should end, but may not register until next event
                print("No legal moves!")
                continue
            best_move = random.choice(legal_moves)

            self.best_move_message_queue.put(best_move)
            self.move_made_event.clear()

    def adversarial_search(self):
        while self.is_active:
            if not self.wait_for_move_event():
                return  # wait for opponents move
            best_move = self.engine.get_best_move(self.board)
            self.best_move_message_queue.put(best_move.uci())  # convert move to string
            self.move_made_event.clear()

    def opening_controller(self):
        """Uses Lichess' Masters DB to get the most popular opening moves and statistics for which player won each game given the set of opening moves."""
        while self.is_active:
            if not self.wait_for_move_event():
                return  # Block until the opponent makes their move
            fen = self.board.fen()

            while True:
                try:
                    opening_statistics = self.client.opening_explorer.get_masters_games(
                        position=fen
                    )
                    break
                except berserk.exceptions.ResponseError as re:
                    if re.status_code == 429:
                        print("Too many API requests! Waiting 1min...")
                        time.sleep(60)

            top_moves_data = pd.DataFrame(data=opening_statistics["moves"])
            if len(top_moves_data) == 0:
                return

            top_moves_data["total"] = top_moves_data[["white", "draws", "black"]].sum(
                axis=1
            )
            top_moves_data["eval"] = (
                top_moves_data[self.player_color]
                - top_moves_data[self.opponent_color(self.player_color)]
            ) / top_moves_data["total"]

            # Filter for only moves with higher win percentage for our player and with a significant number of times it has been played
            good_moves_data = top_moves_data[
                (top_moves_data["eval"] > 0.05) & (top_moves_data["total"] > 10)
            ]
            good_moves_data = good_moves_data.sort_values(by="eval", ascending=False)
            print(good_moves_data)
            if len(good_moves_data) == 0:
                return

            best_move = good_moves_data.iloc[0]["uci"]
            print(f"Best move: {best_move}")

            self.best_move_message_queue.put(best_move)
            self.move_made_event.clear()

    def move_controller(self):
        while self.is_active:
            if not self.wait_for_move_event():
                return  # Block until the opponent makes their move

            # Choose Best Move and Make Move
            best_move = self.best_move_message_queue.get(
                block=True
            )  # Waits until best move is provided in the queue

            while True:
                try:
                    self.client.bots.make_move(self.id, best_move)
                    break
                except berserk.exceptions.ResponseError as re:
                    print(re)
                    if re.status_code == 429:
                        print("Too many API requests! Waiting 1min...")
                        time.sleep(60)

            self.move_made_event.clear()  # Clear to wait again until thread watching for opponent moves resets it

    def stream_game_state(self):
        print(f"Streaming game state on thread {self.game_stream_thread.getName()}")

        while True:
            try:
                game_state_response = self.client.bots.stream_game_state(self.id)
                break
            except berserk.exceptions.ResponseError as re:
                if re.status_code == 429:
                    print("Too many API requests! Waiting 1min...")
                    time.sleep(60)

        for event in game_state_response:
            if not self.is_active:
                return
            match event["type"]:
                case "gameState":
                    match event["status"]:
                        case "started":
                            # TODO: Maybe implement check for takebacks
                            moves = event["moves"]
                            last_move = moves.split(" ")[-1]
                            try:
                                self.board.push(
                                    chess.Move.from_uci(
                                        last_move
                                    )  # TODO: Ensure no race conditions on this
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
                            self.is_active = False
                            if event["status"] in ["draw", "stalemate"]:
                                print(f"Tie!")
                                self.update_status("draw")
                            elif event.get("winner") == self.player_color:
                                print("You won!")
                                self.update_status("win")
                            else:
                                print("You lost!")
                                self.update_status("loss")
                            return
                        # case _:
                        #     print(event)
                case "gameFull":
                    match event["state"]["status"]:
                        case "started":
                            self.update_status("active")

                            # Get player color of the bot
                            if self.bot_id == event["white"].get("id", None):
                                self.player_color = "white"
                                self.engine.player_color = chess.WHITE
                            elif self.bot_id == event["black"].get("id", None):
                                self.player_color = "black"
                                self.engine.player_color = chess.BLACK
                            else:
                                raise Exception("Unable to determine bot color!")

                            # Set whos turn it is to start move control loop
                            self.is_my_turn = self.player_color == "white"
                            if self.is_my_turn:
                                self.move_made_event.set()
                #         case _:
                #             print(event)
                # case _:
                #     print(event)

    def opponent_color(self, player_color: str):
        opponent_colors = {"black": "white", "white": "black"}
        return opponent_colors.get(player_color)

    def update_status(self, status: str):
        self.status = status


PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


# TODO: continue to test MoveEngine or add other advanced moves to its playlist
class MoveEngine:
    def __init__(self, depth=3):  # depth of minimax tree
        self.depth = depth
        self.seen_fens = (
            set()
        )  # store FEN strings of previous positions to penalize repeating moves
        self.player_color = None

    # assigns a value to the current board state. Positive is good for White, negative is good for Black.
    def evaluate_board(self, board: chess.Board) -> float:
        if board.is_checkmate():
            return -9999 if board.turn else 9999
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        # material evaluation; sum up piece values for both sides
        score = sum(
            PIECE_VALUES[piece_type]
            * (
                len(board.pieces(piece_type, self.player_color))
                - len(board.pieces(piece_type, not self.player_color))
            )
            for piece_type in PIECE_VALUES
        )

        # mobility bonus to encourage more legal moves
        mobility = board.legal_moves.count()
        score += 0.1 * mobility if board.turn == self.player_color else -0.1 * mobility

        # castling bonus for king safety
        if board.has_kingside_castling_rights(
            self.player_color
        ) and board.has_queenside_castling_rights(self.player_color):
            score += 0.3
        if board.has_kingside_castling_rights(
            not self.player_color
        ) and board.has_queenside_castling_rights(not self.player_color):
            score -= 0.3

        # penalize repetition (same board position over and over)
        if board.fen() in self.seen_fens:
            score -= 2

        # TODO: Add some incentive for pawn pushing in the endgame

        # bonus for attacking undefended opponent pieces
        for square, piece in board.piece_map().items():
            if piece.color != board.turn:
                if board.is_attacked_by(board.turn, square):
                    if not board.is_attacked_by(
                        not board.turn, square
                    ):  # same as not defended
                        score += 0.3 * PIECE_VALUES[piece.piece_type]

        # bonus for attacking undefended opponent pieces
        for square, piece in board.piece_map().items():
            if board.is_attacked_by(piece.color, square):
                if not board.is_attacked_by(
                    not piece.color, square
                ):  # same as not defended
                    score += 0.3 * PIECE_VALUES[piece.piece_type]

        return score

    # Main interface for the bot to decide its move; returns the best legal move based on minimax evaluation
    def get_best_move(self, board: chess.Board) -> chess.Move:
        maximizing = board.turn == self.player_color
        best_score = -math.inf if maximizing else math.inf
        best_move = None

        # order moves to improve alpha-beta pruning efficiency
        ordered_moves = self.order_moves(board)

        for move in ordered_moves:
            board.push(move)
            # detects mate in 1
            if board.is_checkmate():
                board.pop()
                print(f"Mate in 1 found: {move}")
                return move
            score = self.minimax(
                board, self.depth - 1, -math.inf, math.inf, not maximizing
            )
            board.pop()

            print(f"Evaluating: {move}, Score: {score:.2f}")

            # chooses the best move based on score value
            if (maximizing and score > best_score) or (
                not maximizing and score < best_score
            ):
                best_score = score
                best_move = move

        if best_move:
            self.seen_fens.add(board.fen())

        print(f"Best move: {best_move}, Eval: {best_score:.2f}")
        return best_move if best_move else random.choice(list(board.legal_moves))

    # returns moves sorted by heuristic: Highest priority is captures, then it does its checks and last makes a quiet move. This method improves speed for search performance
    def order_moves(self, board: chess.Board):
        def move_score(move: chess.Move):
            if board.is_capture(move):
                captured = board.piece_at(move.to_square)
                return PIECE_VALUES.get(captured.piece_type, 0) if captured else 0
            if board.gives_check(move):
                return 0.5
            return 0

        return sorted(board.legal_moves, key=move_score, reverse=True)

    # minimax with alpha-beta pruning. Tries to maximize score for white and minimize for black
    def minimax(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
        maximizing: bool,
    ) -> float:
        # Detect leaf nodes
        if depth == 0 or board.is_game_over():
            return self.evaluate_board(board)

        # improve search efficiency by trying promising moves first
        ordered_moves = self.order_moves(board)

        # if maximizing:
        #     max_eval = -math.inf
        #     for move in ordered_moves:
        #         board.push(move)
        #         eval_score = self.minimax(board, depth - 1, alpha, beta, False)
        #         board.pop()

        #         max_eval = max(max_eval, eval_score)
        #         alpha = max(alpha, eval_score)
        #         # cutoff search. no need to explore worse branches
        #         if beta <= alpha:
        #             break
        #     return max_eval
        # else:
        #     min_eval = math.inf
        #     for move in ordered_moves:
        #         board.push(move)
        #         eval_score = self.minimax(board, depth - 1, alpha, beta, True)
        #         board.pop()

        #         min_eval = min(min_eval, eval_score)
        #         beta = min(beta, eval_score)
        #         # cutoff
        #         if beta <= alpha:
        #             break
        #     return min_eval

        if maximizing:
            for move in ordered_moves:
                board.push(move)
                alpha = max(alpha, self.minimax(board, depth - 1, alpha, beta, False))
                board.pop()

                if beta <= alpha:
                    return beta

            return alpha
        else:
            for move in ordered_moves:
                board.push(move)
                beta = min(beta, self.minimax(board, depth - 1, alpha, beta, True))
                board.pop()

                if beta <= alpha:
                    return alpha

            return beta
