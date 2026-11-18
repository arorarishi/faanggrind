# Design Array Modifier · FAANGrind

Source: https://faangrind.vercel.app/problems/design-array-modifier

[All problems](/problems)

#382Medium· asked at 1 company

# Design Array Modifier

[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)

## Problem

Design a data structure `ArrayModifier` initialised with an integer array `arr` of length `n` that supports the following operations efficiently:

* `update(i, val)` — set `arr[i] = val`.
* `add(l, r, val)` — add `val` to every element in the index range `[l, r]`.
* `sumRange(l, r)` — return the sum of elements in `[l, r]`.
* `get(i)` — return the current value of `arr[i]`.

All operations must run in O(log n).

## Input / Output

A sequence of operations; return the results of `sumRange` and `get`.

## Examples

```
ArrayModifier([1, 2, 3, 4, 5])
sumRange(0, 2)  -> 6
add(1, 3, 10)   -> array is [1, 12, 13, 14, 5]
get(2)          -> 13
update(0, 7)    -> array is [7, 12, 13, 14, 5]
sumRange(0, 4)  -> 51
```

## Constraints

* `1 <= n <= 10^5`, up to `10^5` operations.
* Values fit in 64-bit integers.

## Approach

Point updates plus range sums alone need a **Fenwick tree**; adding **range add** on top requires either a segment tree with lazy propagation or the classic **two-Fenwick-tree** trick.

**Segment tree with lazy propagation (recommended).**

* Each node stores the sum of its interval and a pending `lazy` value to be added to every element in the interval.
* `add(l, r, val)`: descend; when a node's interval is fully inside `[l, r]`, add `val × length` to its sum and `val` to its lazy, and stop. Push lazy values to children before descending further.
* `sumRange(l, r)`: descend the same way, pushing lazies, summing fully covered nodes.
* `update(i, val)`: compute `get(i)` first, then `add(i, i, val - current)` — this reuses range add and avoids a separate code path.
* `get(i)` = `sumRange(i, i)`.

**Alternative (two BITs).** Maintain two Fenwick trees `B1`, `B2` such that prefix sum `S(x) = sum(B1, x) × x − sum(B2, x)`; range add becomes four point updates. Shorter code, slightly trickier to explain.

## Complexity

* **All operations:** O(log n)
* **Space:** O(n)

## Reference solution (Python)

```
class ArrayModifier:
    def __init__(self, arr):
        self.n = len(arr)
        self.sum = [0] * (4 * self.n)
        self.lazy = [0] * (4 * self.n)
        self._build(1, 0, self.n - 1, arr)

    def _build(self, node, lo, hi, arr):
        if lo == hi:
            self.sum[node] = arr[lo]; return
        mid = (lo + hi) // 2
        self._build(2*node, lo, mid, arr); self._build(2*node+1, mid+1, hi, arr)
        self.sum[node] = self.sum[2*node] + self.sum[2*node+1]

    def _push(self, node, lo, hi):
        if self.lazy[node]:
            mid = (lo + hi) // 2
            for c, a, b in ((2*node, lo, mid), (2*node+1, mid+1, hi)):
                self.sum[c] += self.lazy[node] * (b - a + 1)
                self.lazy[c] += self.lazy[node]
            self.lazy[node] = 0

    def _add(self, node, lo, hi, l, r, val):
        if r < lo or hi < l: return
        if l <= lo and hi <= r:
            self.sum[node] += val * (hi - lo + 1); self.lazy[node] += val; return
        self._push(node, lo, hi)
        mid = (lo + hi) // 2
        self._add(2*node, lo, mid, l, r, val); self._add(2*node+1, mid+1, hi, l, r, val)
        self.sum[node] = self.sum[2*node] + self.sum[2*node+1]

    def _query(self, node, lo, hi, l, r):
        if r < lo or hi < l: return 0
        if l <= lo and hi <= r: return self.sum[node]
        self._push(node, lo, hi)
        mid = (lo + hi) // 2
        return self._query(2*node, lo, mid, l, r) + self._query(2*node+1, mid+1, hi, l, r)

    def add(self, l, r, val): self._add(1, 0, self.n - 1, l, r, val)
    def sumRange(self, l, r): return self._query(1, 0, self.n - 1, l, r)
    def get(self, i): return self.sumRange(i, i)
    def update(self, i, val): self.add(i, i, val - self.get(i))
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,2,3,4,5]; sumRange(0,2)` | `6` |
| `add(1,3,10); get(2)` | `13` |
| `update(0,7); sumRange(0,4)` | `51` |
| `get(4)` | `5` |

[PreviousDesign an Ordered Stream](/problems/design-an-ordered-stream)[NextDivide Intervals Into Minimum Number of Groups](/problems/divide-intervals-into-minimum-number-of-groups)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#163 in list](/companies/jpmorgan-chase)

## Details

Difficulty
:   Medium

Popularity
:   17/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)

[Solution](https://www.youtube.com/results?search_query=Design%20Array%20Modifier%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#788Kadane's AlgorithmMedium](/problems/kadane-s-algorithm)
* [#53 SumMedium](/problems/3-sum)
* [#1678Rotten OrangesMedium](/problems/rotten-oranges)
* [#890Longest Consecutive Sequence in an ArrayMedium](/problems/longest-consecutive-sequence-in-an-array)
* [#1350Next PermutationMedium](/problems/next-permutation)
