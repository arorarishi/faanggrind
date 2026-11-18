# Implement PQ using Heaps · FAANGrind

Source: https://faangrind.vercel.app/problems/implement-pq-using-heaps

[All problems](/problems)

#725Medium· asked at 1 company

# Implement PQ using Heaps

[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)

## Problem

Implement a **priority queue** backed by a binary heap. It must support:

* `push(value, priority)` — insert an item with a numeric priority.
* `top()` — return the item with the **highest** priority (or lowest, depending on the variant) without removing it.
* `pop()` — remove and return the highest-priority item.
* `size()` / `empty()`.

Ties are broken by insertion order (**first in, first out** among equal priorities). All operations except `top` must be O(log n).

## Input / Output

A sequence of operations; return the results of `top` and `pop` in order.

## Examples

```
push("email", 2)
push("alert", 5)
push("log", 1)
push("page", 5)
pop()  -> "alert"    (priority 5, inserted before "page")
pop()  -> "page"
top()  -> "email"
pop()  -> "email"
pop()  -> "log"
```

## Constraints

* Up to `10^5` operations.

## Approach

A priority queue is an abstract type; a **binary heap** is the standard implementation because both insert and remove-max are O(log n) and the storage is a flat array.

**Representation.** Store tuples `(priority, seq, value)` in an array-backed max-heap where `seq` is a monotonically increasing counter used for tie-breaking. Comparing `(priority, -seq)` as the key gives higher priority first and, among equals, smaller `seq` (earlier insertion) first.

**push.** Append the tuple and **sift up**: swap with the parent while the parent's key is smaller.

**pop.** Save the root, move the last element to the root, shrink, then **sift down**: swap with the larger child while a child's key is greater.

**top.** Return the root's value.

**Why not a sorted list?** Insert would be O(n). **Why not a BST?** Works, but has pointer overhead and worse cache behaviour; the heap's implicit tree is more compact.

Mention `decreaseKey` / `changePriority` as the operation a plain heap does *not* support efficiently without an index map (needed for Dijkstra with updates).

## Complexity

* **push / pop:** O(log n)
* **top:** O(1)
* **Space:** O(n)

## Reference solution (Python)

```
class PriorityQueue:
    def __init__(self):
        self.h = []
        self.seq = 0

    def _key(self, i):
        p, s, _ = self.h[i]
        return (p, -s)

    def push(self, value, priority):
        self.h.append((priority, self.seq, value))
        self.seq += 1
        i = len(self.h) - 1
        while i > 0:
            par = (i - 1) // 2
            if self._key(par) >= self._key(i):
                break
            self.h[par], self.h[i] = self.h[i], self.h[par]
            i = par

    def top(self):
        return self.h[0][2] if self.h else None

    def pop(self):
        if not self.h:
            return None
        out = self.h[0][2]
        last = self.h.pop()
        if self.h:
            self.h[0] = last
            i, n = 0, len(self.h)
            while True:
                l, r, big = 2 * i + 1, 2 * i + 2, i
                if l < n and self._key(l) > self._key(big): big = l
                if r < n and self._key(r) > self._key(big): big = r
                if big == i: break
                self.h[big], self.h[i] = self.h[i], self.h[big]
                i = big
        return out

    def size(self):
        return len(self.h)
```

## Test cases

| Input | Expected |
| --- | --- |
| push email/2, alert/5, log/1, page/5; pop | `"alert"` |
| pop | `"page"` |
| top | `"email"` |
| pop, pop, pop | `"email"`, `"log"`, `None` |

[PreviousGray Code](/problems/gray-code)[NextIndex Pairs of a String](/problems/index-pairs-of-a-string)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#107 in list](/companies/jpmorgan-chase)

## Details

Difficulty
:   Medium

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Heaps](/topics?open=heaps#heaps)

[Solution](https://www.youtube.com/results?search_query=Implement%20PQ%20using%20Heaps%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
* [#1134Merge K sorted ListsMedium](/problems/merge-k-sorted-lists)
* [#534Find Median from Data StreamMedium](/problems/find-median-from-data-stream)
* [#785K-th Largest element in an arrayMedium](/problems/k-th-largest-element-in-an-array)
* [#1870Task SchedulerMedium](/problems/task-scheduler)
* [#1771Sort Characters by FrequencyMedium](/problems/sort-characters-by-frequency)
