# Board Games: Tic-Tac-Toe / Snake & Ladder — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-tic-tac-toe-snake-ladder

[All system design questions](/system-design)

#48LLDEasyLow-level design

# Board Games: Tic-Tac-Toe / Snake & Ladder

OOPstrategyextensibilitygame loop

## Problem statement

Design an extensible board-game framework and implement Tic-Tac-Toe (N×N, 2+ players, pluggable win rules) and Snake & Ladder (configurable board, dice, snakes/ladders, multiple players). Interviewers care about clean class boundaries and O(1)/O(N) win detection.

## Requirements

### Functional

* Tic-Tac-Toe: N×N board, K players with distinct symbols, detect win/draw, undo (optional).
* Snake & Ladder: board of size M, dice (1–6 or custom), snakes and ladders, turn order, first to reach the end wins; exact-landing rule optional.
* Print board/state; play via CLI or API.

### Non-functional

* Win detection in O(1) per move for Tic-Tac-Toe (row/col/diag counters).
* Game rules isolated from game loop; easy to add a bot player.
* Deterministic with a seeded dice for tests.

## API

```
// TicTacToe
MoveResult TicTacToe.play(playerId, row, col)   // OK | INVALID | WIN | DRAW
Optional<Player> TicTacToe.winner()
// Snake & Ladder
TurnResult SnakeLadder.playTurn()               // rolls dice for the current player, returns new position/event
Optional<Player> SnakeLadder.winner()
```

## Data model

**Shared**: `Player(id, name)`, `Game` (abstract: players, turn order, `GameState`), `Board`.
**Tic-Tac-Toe**: `TicTacToeBoard(N, cells, rowCount[N][players], colCount, diagCount, antiDiagCount)`, `Move(player, row, col)`, `WinningStrategy` (interface) → `CounterWinStrategy`, `PlayingPiece(symbol)`.
**Snake & Ladder**: `SLBoard(size, Map<int,int> jumps)` where snakes map high→low and ladders low→high, `Dice(faces, count, rng)`, `Player.position`, `Queue<Player>` turn order.

## Design

1. **Tic-Tac-Toe win in O(1)**: maintain per-player counters for each row, column, main diagonal and anti-diagonal; after placing at (r,c) for player p, increment `row[r][p]`, `col[c][p]`, and diagonals if applicable; if any equals N → win. Draw when moves == N².
2. **Strategy** for win rules so 'K in a row' variants or gravity (Connect-4) drop in.
3. **Snake & Ladder loop**: dequeue player → roll → `next = pos + roll`; if `next > size` (exact rule) skip; else apply `jumps.getOrDefault(next, next)`; if `next == size` → winner; else enqueue player.
4. **Dice** injected for testability; `Board` validates no snake/ladder starts on the last cell and no chains that loop.
5. **Common `Game` skeleton** with template method `start() { while(!over) { takeTurn(); } }` and hooks per game.

## Class diagram

Rendering diagram…

## Deep dives

**Why counters instead of scanning**: scanning rows/cols/diagonals after each move is O(N); counters make it O(1) and the code shorter.

**Undo** in Tic-Tac-Toe: keep a move stack; undo decrements counters and clears the cell.

**Snake & Ladder chains**: a ladder landing on a snake head — decide the rule (apply once vs chain) and enforce in `Board.destination`.

**Bot player**: implement `Player.nextMove(board)` — minimax for Tic-Tac-Toe fits in a few lines for N=3.

## Bottlenecks & mitigations

* N×N board with many players → counters are O(N·P) memory, fine.
* Snake & Ladder with thousands of turns → trivial; watch for infinite games if snakes dominate (cap turns).

## Failure modes

* **Move out of bounds / occupied cell** → return INVALID without changing state.
* **Play after game over** → reject.
* **Invalid board config** (snake at cell 1, ladder to cell > size) → validate at construction.
* **Dice count > 1 with doubles rules** → make dice a strategy.

## Code skeleton

```
import random
from collections import deque

class TicTacToe:
    def __init__(self, n, players):
        self.n, self.players, self.board = n, players, [[None]*n for _ in range(n)]
        self.row = {p: [0]*n for p in players}; self.col = {p: [0]*n for p in players}
        self.diag = {p: 0 for p in players}; self.anti = {p: 0 for p in players}
        self.moves, self.turn, self.winner = 0, 0, None
    def play(self, r, c):
        p = self.players[self.turn]
        if self.winner or self.board[r][c] is not None: return "INVALID"
        self.board[r][c] = p; self.moves += 1
        self.row[p][r] += 1; self.col[p][c] += 1
        if r == c: self.diag[p] += 1
        if r + c == self.n - 1: self.anti[p] += 1
        if self.n in (self.row[p][r], self.col[p][c], self.diag[p], self.anti[p]):
            self.winner = p; return "WIN"
        if self.moves == self.n * self.n: return "DRAW"
        self.turn = (self.turn + 1) % len(self.players); return "OK"

class SnakeLadder:
    def __init__(self, size, jumps, players, dice_faces=6, seed=None):
        self.size, self.jumps, self.rng = size, jumps, random.Random(seed)
        self.faces, self.turns, self.pos, self.winner = dice_faces, deque(players), {p: 0 for p in players}, None
    def play_turn(self):
        p = self.turns.popleft(); roll = self.rng.randint(1, self.faces)
        nxt = self.pos[p] + roll
        if nxt <= self.size:
            nxt = self.jumps.get(nxt, nxt); self.pos[p] = nxt
        if self.pos[p] == self.size: self.winner = p
        else: self.turns.append(p)
        return p, roll, self.pos[p]
```

## Follow-up questions interviewers ask

* Add Connect-4 using the same framework (gravity + K in a row).
* Add a minimax bot.
* Persist game state and support resuming.

[PreviousMovie Ticket Booking (BookMyShow) — LLD](/system-design/lld-movie-ticket-booking)[NextChess](/system-design/lld-chess)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AtlassianAmazonMicrosoftFlipkartAdobe

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
