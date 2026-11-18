# Chess — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-chess

[All system design questions](/system-design)

#49LLDHardLow-level design

# Chess

OOPpolymorphismstatecommand

## Problem statement

Design a two-player chess game: board, pieces with their movement rules, move validation (including check, checkmate, stalemate, castling, en passant, promotion), turn management, move history and undo.

## Requirements

### Functional

* Standard 8×8 board and pieces with legal-move generation.
* Validate a move: piece rules, path blocking, own-king-in-check prevention.
* Detect check, checkmate, stalemate; special moves.
* Move history, undo; game result and resignation/draw offers.

### Non-functional

* Piece rules encapsulated per piece (Open/Closed).
* Move validation efficient enough for interactive play (ms).
* Board state easily serialisable (FEN).

## API

```
boolean Game.makeMove(Player p, Cell from, Cell to, PieceType promotion?)
List<Cell> Game.legalMoves(Cell from)
GameStatus Game.status()          // ACTIVE, CHECK, CHECKMATE, STALEMATE, DRAW, RESIGNED
void Game.undo()
String Board.toFEN()
```

## Data model

* `Board(Cell[8][8])`, `Cell(row, col, Piece?)`.
* `Piece` (abstract: `Color`, `hasMoved`) → `King`, `Queen`, `Rook`, `Bishop`, `Knight`, `Pawn`; each implements `List<Move> possibleMoves(Board, Cell)`.
* `Move(from, to, piece, captured?, promotion?, castling?, enPassant?)` — Command with `execute`/`undo`.
* `Player(Color)`, `Game(board, players, currentTurn,` Deque<Move>`history,`GameStatus`)`.
* `MoveValidator`: applies piece rules + global rules (check).

## Design

1. **Polymorphic piece movement**: each `Piece` generates pseudo-legal moves (ignoring check). Sliding pieces (rook/bishop/queen) walk directions until blocked; knight/king use offset lists; pawn handles direction by colour, double-step from start, captures, en passant, promotion.
2. **Legal filtering**: for each pseudo-legal move, apply it on the board (command `execute`), check whether the mover's king is attacked, then `undo`. `isAttacked(cell, byColor)` reuses piece move generation from the king's square (cheaper than scanning all enemy moves).
3. **Special rules** implemented in `King` (castling: neither piece moved, path empty, not through/into check) and `Pawn` (en passant needs the last move → passed in via `Game`).
4. **Game state**: after each move, if opponent has no legal moves → checkmate if in check else stalemate; also 50-move and threefold repetition (hash of positions).
5. **Command pattern** for `Move` gives undo and history for free.

## Class diagram

Rendering diagram…

## Deep dives

**Check detection trick**: to know if a square is attacked by colour X, pretend a piece of each type sits on that square and see whether it could capture an X piece of the same type (knight-from-square, rook-lines, etc.). O(1)-ish per square.

**Pseudo-legal then filter** keeps piece classes simple; the check rule lives once in `Game`.

**Sliding move generator** shared by Rook/Bishop/Queen via direction vectors — avoids duplicated loops.

**Serialisation**: FEN for board + turn + castling rights + en-passant square; PGN for history.

## Bottlenecks & mitigations

* Naive `attacked` scans all 64 squares × their moves → use the 'reverse attack' trick or incremental attack maps.
* Legal move generation copies the board → apply/undo in place with the command pattern.
* Threefold repetition → Zobrist hashing of positions.

## Failure modes

* **Move leaves own king in check** → filtered by legal-move check; never trust client-side validation.
* **Castling through check** → explicit path check in King/Game.
* **Promotion without a choice** → default to queen, allow override.
* **Undo across a promotion/en passant** → Move stores full info to restore.

## Code skeleton

```
DIRS = {"rook": [(1,0),(-1,0),(0,1),(0,-1)], "bishop": [(1,1),(1,-1),(-1,1),(-1,-1)]}
DIRS["queen"] = DIRS["rook"] + DIRS["bishop"]
KNIGHT = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
KING = DIRS["queen"]

def on(r, c): return 0 <= r < 8 and 0 <= c < 8

class Piece:
    def __init__(self, color): self.color, self.moved = color, False
    kind = "?"
    def moves(self, board, r, c): raise NotImplementedError

class Slider(Piece):
    def moves(self, board, r, c):
        out = []
        for dr, dc in DIRS[self.kind]:
            nr, nc = r + dr, c + dc
            while on(nr, nc):
                t = board[nr][nc]
                if t is None: out.append((nr, nc))
                else:
                    if t.color != self.color: out.append((nr, nc))
                    break
                nr, nc = nr + dr, nc + dc
        return out
class Rook(Slider): kind = "rook"
class Bishop(Slider): kind = "bishop"
class Queen(Slider): kind = "queen"

class Stepper(Piece):
    offsets = []
    def moves(self, board, r, c):
        return [(r+dr, c+dc) for dr, dc in self.offsets
                if on(r+dr, c+dc) and (board[r+dr][c+dc] is None or board[r+dr][c+dc].color != self.color)]
class Knight(Stepper): kind, offsets = "knight", KNIGHT
class King(Stepper): kind, offsets = "king", KING   # + castling handled in Game

class Pawn(Piece):
    kind = "pawn"
    def moves(self, board, r, c):
        d = -1 if self.color == "white" else 1; out = []
        if on(r+d, c) and board[r+d][c] is None:
            out.append((r+d, c))
            if not self.moved and board[r+2*d][c] is None: out.append((r+2*d, c))
        for dc in (-1, 1):
            if on(r+d, c+dc) and board[r+d][c+dc] and board[r+d][c+dc].color != self.color:
                out.append((r+d, c+dc))
        return out   # en passant / promotion added by Game using last move

class Game:
    def __init__(self, board): self.board, self.turn, self.history = board, "white", []
    def king_pos(self, color):
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p.kind == "king" and p.color == color: return r, c
    def attacked(self, r, c, by):
        for rr in range(8):
            for cc in range(8):
                p = self.board[rr][cc]
                if p and p.color == by and (r, c) in p.moves(self.board, rr, cc): return True
        return False
    def legal_moves(self, r, c):
        p = self.board[r][c]; out = []
        if not p or p.color != self.turn: return out
        for nr, nc in p.moves(self.board, r, c):
            cap = self.board[nr][nc]; self.board[nr][nc], self.board[r][c] = p, None
            kr, kc = self.king_pos(p.color)
            if not self.attacked(kr, kc, "black" if p.color == "white" else "white"): out.append((nr, nc))
            self.board[r][c], self.board[nr][nc] = p, cap
        return out
    def make_move(self, r, c, nr, nc):
        if (nr, nc) not in self.legal_moves(r, c): return False
        p = self.board[r][c]; self.history.append((r, c, nr, nc, self.board[nr][nc], p.moved))
        self.board[nr][nc], self.board[r][c], p.moved = p, None, True
        self.turn = "black" if self.turn == "white" else "white"; return True
    def undo(self):
        r, c, nr, nc, cap, moved = self.history.pop()
        p = self.board[nr][nc]; self.board[r][c], self.board[nr][nc], p.moved = p, cap, moved
        self.turn = p.color
```

## Follow-up questions interviewers ask

* Add a clock and time controls.
* Implement a simple engine (minimax with alpha-beta).
* Support online play with move validation on the server (see chat/realtime HLDs).

[PreviousBoard Games: Tic-Tac-Toe / Snake & Ladder](/system-design/lld-tic-tac-toe-snake-ladder)[NextVending Machine (State pattern)](/system-design/lld-vending-machine)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoogleAdobe

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Design](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Bottlenecks](#bottlenecks)
9. [Failure modes](#failures)
10. [Code skeleton](#code)
11. [Follow-ups](#follow-ups)

## Your notes

Saved

Autosaves to this browser.
