# Disjoint Set · FAANGrind

Source: https://faangrind.vercel.app/problems/disjoint-set

[All problems](/problems)

#430Medium· asked at 5 companies

# Disjoint Set

[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Implement the **Disjoint Set Union** (DSU, also called Union–Find) data structure for `n` elements numbered `0..n-1`. It must support:

* `find(x)` — return a representative (root) of the set containing `x`; two elements are in the same set iff they have the same representative.
* `union(x, y)` — merge the sets containing `x` and `y`.
* `connected(x, y)` — return whether `x` and `y` are in the same set.

Both operations must run in (amortised) near-constant time. Then answer a sequence of `q` queries of the form `union a b` or `check a b`.

## Input / Output

* **Input:** `n`, then `q` operations.
* **Output:** for each `check`, print `YES` or `NO`.

## Examples

Operations on `n = 5`: `union 0 1`, `union 1 2`, `check 0 2`, `check 0 3`, `union 3 4`, `union 2 3`, `check 0 4`
Output: `YES, NO, YES`

## Constraints

* `1 <= n, q <= 10^6`

## Approach

Store `parent[i]` (initially `i`) and either `rank[i]` (upper bound on tree height) or `size[i]` (set size).

**find with path compression.** Walk up to the root, then set every node on the path to point directly at the root:

```
find(x): if parent[x] != x: parent[x] = find(parent[x]); return parent[x]
```

(Use an iterative two-pass version to avoid deep recursion.)

**union by rank / size.** Attach the shorter (or smaller) tree under the taller (larger) one, so trees stay shallow:

```
union(x, y): rx = find(x); ry = find(y); if rx == ry: return
             if rank[rx] < rank[ry]: swap
             parent[ry] = rx; if rank[rx] == rank[ry]: rank[rx]++
```

With both optimisations, any sequence of `m` operations costs O(m · α(n)), where α is the inverse Ackermann function — effectively constant.

## Complexity

* **find / union:** O(α(n)) amortised ≈ O(1)
* **Space:** O(n)

## Applications you should be able to name

Kruskal's minimum spanning tree, detecting cycles in an undirected graph, counting connected components, "accounts merge", "number of islands II" (dynamic connectivity), "number of operations to make network connected", offline connectivity queries, and grouping equivalent elements.

## Reference solution (Python)

```
class DSU:
    def __init__(self, n):
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x):
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:       # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return True

    def connected(self, a, b):
        return self.find(a) == self.find(b)
```

## Test cases

| Input | Expected |
| --- | --- |
| `n=5: union(0,1), union(1,2), check(0,2)` | `YES` |
| `check(0,3)` | `NO` |
| `union(3,4), union(2,3), check(0,4)` | `YES` |
| `union(0,4) again` | `returns False (already connected)` |

[PreviousDiagonal Traverse](/problems/diagonal-traverse)[NextDistribute Elements Into Two Arrays II](/problems/distribute-elements-into-two-arrays-ii)

Saved in this browser. No account needed.

## Asked at

5 companies

* [![](/logos/paypal.png)PayPal#35 in list](/companies/paypal)
* [![](/logos/goldman-sachs.png)Goldman Sachs#96 in list](/companies/goldman-sachs)
* [![](/logos/apple.ico)Apple#140 in list](/companies/apple)
* [![](/logos/adobe.ico)Adobe#161 in list](/companies/adobe)
* [![](/logos/amazon.ico)Amazon#301 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   19/100

Source
:   Full statement on FAANGrind

Topics
:   [Graphs](/topics?open=graphs#graphs)

[Solution](https://www.youtube.com/results?search_query=Disjoint%20Set%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1385Number of islandsMedium](/problems/number-of-islands)
* [#1678Rotten OrangesMedium](/problems/rotten-oranges)
* [#340Course Schedule IIMedium](/problems/course-schedule-ii)
* [#197Coin ChangeMedium](/problems/coin-change)
* [#1993Word ladder IMedium](/problems/word-ladder-i)
* [#339Course Schedule IMedium](/problems/course-schedule-i)
