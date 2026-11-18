# In-memory File System — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-in-memory-file-system

[All system design questions](/system-design)

#57LLDMediumLow-level design

# In-memory File System

compositetrieOOPpath resolution

## Problem statement

Design an in-memory file system supporting `mkdir -p`, `ls`, `addContentToFile`, `readContentFromFile`, `rm`, `mv`, `find` by name/size, permissions and symlinks (optional), with paths like `/a/b/c`.

## Requirements

### Functional

* Create directories (recursively), create/append/read files.
* List a directory (sorted) or return a file name.
* Delete, move/rename, copy.
* Find by name pattern/extension/size (with pluggable filters).
* Optional: permissions, symlinks, quotas.

### Non-functional

* Path resolution O(depth); ls O(k log k) for k children.
* Thread-safe for concurrent readers and writers (per-directory locking).
* Composite structure: files and directories share an interface.

## API

```
void   mkdir(String path)                       // -p semantics
List<String> ls(String path)                    // sorted names, or [fileName]
void   addContentToFile(String path, String content)
String readContentFromFile(String path)
void   rm(String path, boolean recursive)
void   mv(String from, String to)
List<String> find(String path, Filter f)
```

## Data model

* `Node` (abstract): name, parent, createdAt, modifiedAt, permissions → `File(content: StringBuilder / byte[] chunks, size)`, `Directory(`TreeMap<String, Node> `children)`, `SymLink(target)`.
* `FileSystem`: root `Directory`, `resolve(path) → Node`, `resolveParent(path) → (Directory, name)`.
* `Filter` (interface) for find: `NameFilter`, `ExtensionFilter`, `SizeFilter`, `AndFilter`.
* `Path` helper: normalise, split, handle `.`/`..`.

## Design

1. **Composite pattern**: `Directory` and `File` both extend `Node`; directories hold children in a `TreeMap` so `ls` is sorted automatically.
2. **Path resolution**: split on `/`, walk from root; `resolveParent` returns the directory and last segment for create/move/delete. Normalise `.` and `..` (never above root).
3. **mkdir -p**: walk, creating missing directories; error if a segment exists as a file.
4. **Files as chunked buffers** (`List<byte[]>`) so append is O(1) amortised and reads don't copy the whole content.
5. **Find**: DFS from a directory applying a `Filter` composite (AND/OR/NOT) — Specification pattern.
6. **Concurrency**: `ReadWriteLock` per directory; lock ordering by path depth to avoid deadlocks in `mv` (lock both parents in canonical order).
7. **mv** = detach node from old parent, rename, attach to new parent; reject moving a directory into its own subtree.

## Class diagram

Rendering diagram…

## Deep dives

**TreeMap vs HashMap for children**: sorted `ls` for free at O(log k) insert; HashMap + sort on `ls` is fine too — state the trade-off.

**Directory size** = sum of children (cache with invalidation up the parent chain on writes, or compute lazily).

**Symlinks**: resolve with a hop limit to avoid loops.

**Why parent pointers**: needed for `..`, `mv`, and recomputing sizes; keep them consistent in `add`/`remove`.

## Bottlenecks & mitigations

* Directory size recomputed recursively on every query → cached sizes with invalidation up the tree.
* Huge directories → `ls` O(k log k); paginate.
* Global lock → per-directory RW locks; lock in path order.

## Failure modes

* **File and directory name clash** → error on mkdir over a file or write into a directory.
* **Move into own subtree** → cycle check up the parent chain.
* **Concurrent rm and read** → readers hold a read lock on the parent; rm takes a write lock.
* **Path normalisation edge cases** (`//`, trailing `/`, `..` above root) → normalise centrally.

## Code skeleton

```
from threading import RLock

class Node:
    def __init__(self, name, parent=None): self.name, self.parent = name, parent
class File(Node):
    def __init__(self, name, parent): super().__init__(name, parent); self.chunks = []
    def append(self, s): self.chunks.append(s)
    def read(self): return "".join(self.chunks)
    def size(self): return sum(len(c) for c in self.chunks)
class Directory(Node):
    def __init__(self, name, parent=None): super().__init__(name, parent); self.children, self.lock = {}, RLock()
    def size(self): return sum(c.size() for c in self.children.values())

class FileSystem:
    def __init__(self): self.root = Directory("")
    def _parts(self, path): return [p for p in path.split("/") if p and p != "."]
    def _resolve(self, path, create=False):
        node = self.root
        for p in self._parts(path):
            if p == "..": node = node.parent or node; continue
            if not isinstance(node, Directory): raise FileNotFoundError(path)
            with node.lock:
                if p not in node.children:
                    if not create: raise FileNotFoundError(path)
                    node.children[p] = Directory(p, node)
                node = node.children[p]
        return node
    def mkdir(self, path): self._resolve(path, create=True)
    def ls(self, path):
        n = self._resolve(path)
        return sorted(n.children) if isinstance(n, Directory) else [n.name]
    def add_content(self, path, content):
        parts = self._parts(path); d = self._resolve("/" + "/".join(parts[:-1]), create=True)
        with d.lock:
            f = d.children.get(parts[-1])
            if f is None: f = d.children[parts[-1]] = File(parts[-1], d)
            if isinstance(f, Directory): raise IsADirectoryError(path)
            f.append(content)
    def read(self, path):
        f = self._resolve(path)
        if isinstance(f, Directory): raise IsADirectoryError(path)
        return f.read()
    def rm(self, path, recursive=False):
        n = self._resolve(path)
        if isinstance(n, Directory) and n.children and not recursive: raise OSError("directory not empty")
        with n.parent.lock: del n.parent.children[n.name]
    def mv(self, src, dst):
        n = self._resolve(src); parts = self._parts(dst); dparent = self._resolve("/" + "/".join(parts[:-1]))
        cur = dparent
        while cur:
            if cur is n: raise OSError("cannot move into itself")
            cur = cur.parent
        with n.parent.lock: del n.parent.children[n.name]
        n.name, n.parent = parts[-1], dparent
        with dparent.lock: dparent.children[n.name] = n
    def find(self, path, pred):
        out, stack = [], [(self._resolve(path), path.rstrip("/") or "")]
        while stack:
            n, p = stack.pop()
            if pred(n): out.append(p or "/")
            if isinstance(n, Directory):
                for name, c in n.children.items(): stack.append((c, f"{p}/{name}"))
        return sorted(out)
```

## Follow-up questions interviewers ask

* Add permissions (rwx per owner/group) and an access check on every op.
* Add a journal so the FS can be persisted and replayed.
* Add quotas per directory subtree.

[PreviousText Editor with Undo/Redo (Command pattern)](/system-design/lld-text-editor-undo-redo)[NextMeeting Scheduler / Calendar](/system-design/lld-meeting-scheduler)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoogleAtlassianAdobe

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
