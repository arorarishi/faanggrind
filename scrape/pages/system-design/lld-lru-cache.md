# LRU / LFU Cache — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-lru-cache

[All system design questions](/system-design)

#45LLDEasyLow-level design

# LRU / LFU Cache

hash mapdoubly linked listevictionthread safety

## Problem statement

Design an in-memory cache with fixed capacity supporting `get(key)` and `put(key, value)` in O(1), evicting the least-recently-used entry when full. Extend to LFU (least-frequently-used) and to a thread-safe version with TTL.

## Requirements

### Functional

* `get` returns the value or a miss and marks the entry as recently used.
* `put` inserts/updates and marks as recently used; evicts LRU when over capacity.
* Optional TTL per entry; optional LFU policy.
* Optional eviction callbacks/metrics (hit rate).

### Non-functional

* O(1) get/put.
* Thread-safe under concurrent access (variant).
* Pluggable eviction policy.

## API

```
V    get(K key)                     // null/Optional on miss or expired
void put(K key, V value)            // put(key, value, ttlMillis) variant
void remove(K key)
int  size()
CacheStats stats()                  // hits, misses, evictions
```

## Data model

* `Cache<K,V>` (interface): `get`, `put`, `remove`, `size`.
* `LRUCache`: `HashMap<K, Node>` + doubly linked list with sentinel head/tail; `Node{key, value, prev, next, expiresAt}`.
* `LFUCache`: `HashMap<K, Node>`, `HashMap<freq, DoublyLinkedList>`, `minFreq`.
* `EvictionPolicy` (interface) for a generic cache: `onAccess(key)`, `onInsert(key)`, `evict() → key`.

## Design

1. **LRU**: map gives O(1) lookup; the list keeps recency order. `get` → move node to head. `put` → update+move, or insert at head; if size > capacity, remove the tail node and its map entry. Sentinel nodes remove null checks.
2. **LFU**: each node has a frequency; nodes with the same frequency live in one LRU list (ties broken by recency). `minFreq` tracks the lowest frequency; on access, move the node from list f to list f+1; on insert when full, evict from list `minFreq` tail, then set `minFreq = 1`.
3. **TTL**: store `expiresAt`; `get` treats expired entries as misses and removes them lazily; a background sweeper optional.
4. **Thread safety**: coarse-grained `ReentrantLock` around get/put (simplest, correct), or segment the cache into N stripes each with its own lock (like `ConcurrentHashMap`), trading global LRU accuracy for throughput.
5. **Policy abstraction**: `Cache` delegates ordering to an `EvictionPolicy` so LRU/LFU/FIFO are interchangeable.

## Class diagram

Rendering diagram…

## Deep dives

**Why a doubly linked list**: removing an arbitrary node in O(1) requires both neighbours; a singly linked list would need O(n) to find the predecessor.

**`LinkedHashMap(accessOrder=true)`** in Java gives LRU for free by overriding `removeEldestEntry`; mention it, then implement manually.

**LFU subtlety**: after moving a node from freq f to f+1, if list f became empty and `minFreq == f`, increment `minFreq`.

**Striped locking** loses strict global LRU (each stripe evicts its own LRU) — acceptable for most caches; sampled-LRU (Redis) is another pragmatic alternative.

## Bottlenecks & mitigations

* Global lock under high concurrency → striped/segmented cache or lock-free reads with periodic reordering.
* TTL sweeper scanning everything → lazy expiry on access plus a small periodic random sample.
* Memory overhead per node (pointers) → `__slots__`/compact structs; consider array-backed lists.

## Failure modes

* **Capacity 0 or negative**: validate in constructor.
* **put of an existing key at capacity**: must update, not evict — test this.
* **Expired entry counted in size**: size reflects map size; document or sweep.
* **Re-entrant callbacks** (eviction listener calling `put`): use `RLock` or invoke listeners outside the lock.

## Code skeleton

```
from threading import RLock
import time

class Node:
    __slots__ = ("key", "val", "prev", "next", "exp")
    def __init__(self, key=None, val=None, exp=None):
        self.key, self.val, self.exp, self.prev, self.next = key, val, exp, None, None

class LRUCache:
    def __init__(self, capacity):
        self.cap, self.map, self.lock = capacity, {}, RLock()
        self.head, self.tail = Node(), Node()
        self.head.next, self.tail.prev = self.tail, self.head
    def _unlink(self, n): n.prev.next, n.next.prev = n.next, n.prev
    def _to_front(self, n):
        n.next, n.prev = self.head.next, self.head
        self.head.next.prev = n; self.head.next = n
    def get(self, key):
        with self.lock:
            n = self.map.get(key)
            if not n: return None
            if n.exp and n.exp < time.time():
                self._unlink(n); del self.map[key]; return None
            self._unlink(n); self._to_front(n); return n.val
    def put(self, key, val, ttl=None):
        with self.lock:
            exp = time.time() + ttl if ttl else None
            n = self.map.get(key)
            if n:
                n.val, n.exp = val, exp; self._unlink(n); self._to_front(n); return
            n = Node(key, val, exp); self.map[key] = n; self._to_front(n)
            if len(self.map) > self.cap:
                lru = self.tail.prev; self._unlink(lru); del self.map[lru.key]

class LFUCache:
    def __init__(self, capacity):
        from collections import OrderedDict, defaultdict
        self.cap, self.kv, self.kf = capacity, {}, {}
        self.freq = defaultdict(OrderedDict); self.min = 0
    def _touch(self, k):
        f = self.kf[k]; del self.freq[f][k]
        if not self.freq[f]:
            del self.freq[f]
            if self.min == f: self.min += 1
        self.kf[k] = f + 1; self.freq[f + 1][k] = None
    def get(self, k):
        if k not in self.kv: return None
        self._touch(k); return self.kv[k]
    def put(self, k, v):
        if self.cap == 0: return
        if k in self.kv: self.kv[k] = v; self._touch(k); return
        if len(self.kv) >= self.cap:
            old, _ = self.freq[self.min].popitem(last=False)
            del self.kv[old]; del self.kf[old]
        self.kv[k], self.kf[k] = v, 1; self.freq[1][k] = None; self.min = 1
```

## Follow-up questions interviewers ask

* Implement a write-through cache backed by a DB with a loader function.
* Add a 2Q/ARC policy to resist scan pollution.
* Make it distributed (see distributed cache HLD).

[PreviousElevator System](/system-design/lld-elevator-system)[NextSplitwise (expense sharing)](/system-design/lld-splitwise)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoogleAdobePayPalAtlassian

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
