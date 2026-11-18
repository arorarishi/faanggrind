# Text Editor with Undo/Redo (Command pattern) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-text-editor-undo-redo

[All system design questions](/system-design)

#56LLDMediumLow-level design

# Text Editor with Undo/Redo (Command pattern)

commandmementodata structuresOOP

## Problem statement

Design a text editor supporting insert, delete, replace at a cursor position, selection, undo/redo of any depth, and efficient editing of large documents; optionally with formatting and multiple cursors.

## Requirements

### Functional

* Insert/delete text at cursor; move cursor; select ranges; cut/copy/paste.
* Undo/redo with unlimited depth (bounded by memory); grouping of consecutive keystrokes.
* Find/replace.
* Efficient for documents of MBs.

### Non-functional

* Edits O(log n) or O(piece count), not O(n) copies.
* Undo/redo O(1) per step.
* Clean separation: document model, commands, cursor/selection, UI.

## API

```
void insert(String text)              // at cursor, replaces selection if any
void delete()                         // backspace/delete or selection
void moveCursor(int pos) ; void select(int start, int end)
void undo() ; void redo()
void cut() / copy() / paste()
int  find(String needle, int from) ; void replaceAll(String a, String b)
String text()
```

## Data model

* `Document` (interface): `insert(pos, text)`, `delete(pos, len)`, `charAt`, `substring`, `length` → implementations: `StringBuilderDocument` (simple), `GapBuffer`, `PieceTable` (original + add buffers, list of pieces), `Rope`.
* `Command` (interface): `execute()`, `undo()` → `InsertCommand(pos, text)`, `DeleteCommand(pos, deletedText)`, `ReplaceCommand`, `CompositeCommand`.
* `Editor`: document, cursor, selection, `Deque<Command> undoStack`, `Deque<Command> redoStack`, clipboard.
* `Cursor(pos)`, `Selection(start, end)`.
* `Memento` (optional) for snapshots of small documents.

## Design

1. **Command pattern**: every edit is a `Command` with enough info to undo (delete stores the removed text). `Editor.apply(cmd)` executes it, pushes on `undoStack`, and clears `redoStack`. `undo` pops, calls `undo()`, pushes onto `redoStack`; `redo` the reverse.
2. **Grouping**: consecutive single-char inserts within ~500 ms merge into one `InsertCommand` so undo removes a word, not a character; `CompositeCommand` for replace-all.
3. **Piece table** as the document: text = sequence of pieces pointing into an immutable original buffer and an append-only add buffer; insert = split a piece + add a piece; delete = adjust/split pieces. No large copies; undo is cheap because buffers are never mutated. (Gap buffer is simpler and great for a single cursor; rope for huge files with random access.)
4. **Selection-aware operations**: insert with a selection = `CompositeCommand(delete selection, insert)`.
5. **Find** over the document via an iterator; for large docs keep a line index for navigation.

## Class diagram

Rendering diagram…

## Deep dives

**Command vs Memento**: memento snapshots the whole state (simple, memory-heavy); command stores deltas (cheap, needs inverse operations). Editors use commands; mementos suit small state (settings).

**Redo invalidation**: any new edit after an undo must clear the redo stack — the classic bug when forgotten.

**Cursor restoration**: commands should also record cursor/selection before and after so undo puts the cursor back.

**Piece table + undo**: since buffers are append-only, an undo of insert just removes the piece; the text remains in the add buffer (no copying).

## Bottlenecks & mitigations

* `_split` linear in piece count → balanced tree of pieces (red-black tree keyed by offset) for O(log n).
* `"".join(self.add)` on every read → keep the add buffer as one growable string/array.
* Undo stack memory → cap depth; coalesce commands.

## Failure modes

* **Undo after redo stack cleared** → correct behaviour; test the sequence insert-undo-insert-redo (redo must be empty).
* **Merge across cursor jumps** → merge only when contiguous and recent.
* **Multi-cursor edits** → apply commands from highest position to lowest so offsets stay valid; group in a Composite.
* **Large paste** → single Insert command; piece table handles it without copying.

## Code skeleton

```
import time

class Command:
    def execute(self, doc): ...
    def undo(self, doc): ...

class Insert(Command):
    def __init__(self, pos, text): self.pos, self.text, self.ts = pos, text, time.time()
    def execute(self, doc): doc.insert(self.pos, self.text)
    def undo(self, doc): doc.delete(self.pos, len(self.text))
    def try_merge(self, other):
        if isinstance(other, Insert) and other.pos == self.pos + len(self.text) and other.ts - self.ts < 0.5 and not other.text[:1].isspace():   # merge keystrokes within a word
            self.text += other.text; self.ts = other.ts; return True
        return False

class Delete(Command):
    def __init__(self, pos, length): self.pos, self.length, self.removed = pos, length, None
    def execute(self, doc): self.removed = doc.delete(self.pos, self.length)
    def undo(self, doc): doc.insert(self.pos, self.removed)

class Composite(Command):
    def __init__(self, cmds): self.cmds = cmds
    def execute(self, doc):
        for c in self.cmds: c.execute(doc)
    def undo(self, doc):
        for c in reversed(self.cmds): c.undo(doc)

class PieceTable:
    def __init__(self, text=""):
        self.orig, self.add, self.pieces = text, [], [("o", 0, len(text))] if text else []
    def _split(self, pos):        # returns index in pieces where offset pos begins, splitting if needed
        acc = 0
        for i, (b, s, l) in enumerate(self.pieces):
            if acc + l > pos:
                if acc == pos: return i
                self.pieces[i:i+1] = [(b, s, pos - acc), (b, s + pos - acc, l - (pos - acc))]; return i + 1
            acc += l
        return len(self.pieces)
    def insert(self, pos, text):
        start = sum(len(t) for t in self.add); self.add.append(text)
        i = self._split(pos); self.pieces.insert(i, ("a", start, len(text)))
    def delete(self, pos, length):
        i, j = self._split(pos), self._split(pos + length)
        removed = "".join(self._text(p) for p in self.pieces[i:j]); del self.pieces[i:j]; return removed
    def _text(self, p):
        b, s, l = p
        src = self.orig if b == "o" else "".join(self.add)
        return src[s:s+l]
    def text(self): return "".join(self._text(p) for p in self.pieces)

class Editor:
    def __init__(self, text=""): self.doc, self.cursor, self.undo_s, self.redo_s = PieceTable(text), len(text), [], []
    def _apply(self, cmd):
        cmd.execute(self.doc); self.redo_s.clear()
        if self.undo_s and hasattr(self.undo_s[-1], "try_merge") and self.undo_s[-1].try_merge(cmd): return
        self.undo_s.append(cmd)
    def insert(self, s): self._apply(Insert(self.cursor, s)); self.cursor += len(s)
    def backspace(self):
        if self.cursor: self._apply(Delete(self.cursor - 1, 1)); self.cursor -= 1
    def undo(self):
        if self.undo_s: c = self.undo_s.pop(); c.undo(self.doc); self.redo_s.append(c)
    def redo(self):
        if self.redo_s: c = self.redo_s.pop(); c.execute(self.doc); self.undo_s.append(c)
```

## Follow-up questions interviewers ask

* Add rich-text attributes as range annotations that survive edits.
* Add collaborative editing (see Google Docs HLD — OT/CRDT).
* Implement a rope and compare with piece table.

[PreviousRate Limiter (token bucket, sliding window) — LLD](/system-design/lld-rate-limiter)[NextIn-memory File System](/system-design/lld-in-memory-file-system)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleMicrosoftAdobeAtlassianAmazon

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
