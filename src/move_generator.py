"""Chess Board
8 -  -  -  -  -  -  -  -
7 -  -  -  -  -  -  -  -
6 -  -  -  -  -  -  -  -
5 -  -  -  -  -  -  -  -
4 -  -  -  -  -  -  -  -
3 -  -  -  -  -  -  -  -
2 -  -  -  -  -  -  -  -
1 -  -  -  -  -  -  -  -
  a  b  c  d  e  f  g  h
"""

import chess


def get_moves_from_fen(fen: str) -> list:
    board = BoardState()
    board.set_fen(fen)
    return list(board.legal_moves)


class BoardState(chess.Board):
    def __init__(self):
        super().__init__()

    def get_moves_from_fen(self, fen: str) -> list[str]:
        self.set_fen(fen)
        return [str(m) for m in self.legal_moves]


# class FenParser:
#     def __init__(self):
#         pass

#     @staticmethod
#     def parse(fen: str):
#         """
#         Example fen: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
#         Decode: https://www.chess.com/terms/fen-chess#en-passant-targets
#         ---------------------------------------
#         lists board from in a8 to h1
#         white uppercase; black lowercase
#         / indicates new line
#         number indicates consecutive blank spaces
#         -----
#         w or b indicates whos turn
#         -----
#         KQkq indicated availability for castling: k/K for kingside, q/Q for queenside
#         -----
#         indicates en passant target (location to move when capturing, not location of captured piece)
#         - when no en passant possible
#         -----
#         number of moves since last pawn move or piece capture; used for 50 move draw
#         -----
#         number of total turns in the game
#         """


def main():
    board = BoardState()
    possible_moves = board.get_moves_from_fen(
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    print(board)
    print("Possible Moves:", ", ".join([str(m) for m in possible_moves]))


if __name__ == "__main__":
    main()
