# Determine Simple Graph · FAANGrind

Source: https://faangrind.vercel.app/problems/determine-simple-graph

[All problems](/problems)

#419Medium· asked at 1 company

# Determine Simple Graph

[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

You are given an undirected graph with `V` vertices (numbered `0..V-1`) and a list of `E` edges `[u, v]`. Determine whether the graph is a **simple graph** — one that contains **no self-loops** (an edge from a vertex to itself) and **no multi-edges** (two or more edges between the same pair of vertices). Return `true` if it is simple, `false` otherwise.

## Input / Output

* **Input:** `V`, `edges` (list of `[u, v]` pairs).
* **Output:** boolean.

## Examples

**Example 1**
Input: `V = 3`, `edges = [[0,1],[1,2],[2,0]]`
Output: `true`

**Example 2**
Input: `V = 3`, `edges = [[0,1],[1,1]]`
Output: `false` (self-loop at vertex 1)

**Example 3**
Input: `V = 3`, `edges = [[0,1],[1,0]]`
Output: `false` (the same undirected edge appears twice)

**Example 4**
Input: `V = 4`, `edges = []`
Output: `true`

## Constraints

* `1 <= V <= 10^5`, `0 <= E <= 2 * 10^5`

## Approach

1. For every edge `[u, v]`: if `u == v`, it is a self-loop → return `false`.
2. Normalise the pair so the smaller endpoint comes first (`(min(u,v), max(u,v))`), since `[0,1]` and `[1,0]` are the same undirected edge.
3. Insert the normalised pair into a hash set. If it is already present → duplicate edge → return `false`.
4. If the loop finishes, return `true`.

Bonus check often expected: a simple undirected graph on `V` vertices can have at most `V(V-1)/2` edges, so if `E` exceeds that, you can return `false` immediately.

For a **directed** graph the normalisation step is skipped: `(u, v)` and `(v, u)` are different edges, and only exact duplicates and self-loops disqualify it.

## Complexity

* **Time:** O(E) average
* **Space:** O(E)

## Reference solution (Python)

```
def is_simple_graph(V, edges):
    if len(edges) > V * (V - 1) // 2:
        return False
    seen = set()
    for u, v in edges:
        if u == v:
            return False
        key = (u, v) if u < v else (v, u)
        if key in seen:
            return False
        seen.add(key)
    return True
```

## Test cases

| Input | Expected |
| --- | --- |
| `V=3, [[0,1],[1,2],[2,0]]` | `true` |
| `V=3, [[0,1],[1,1]]` | `false` |
| `V=3, [[0,1],[1,0]]` | `false` |
| `V=4, []` | `true` |

[PreviousDetect Squares](/problems/detect-squares)[NextFind All People With Secret](/problems/find-all-people-with-secret)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/goldman-sachs.png)Goldman Sachs#209 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Medium

Popularity
:   5/100

Source
:   Full statement on FAANGrind

Topics
:   [Graphs](/topics?open=graphs#graphs)

[Solution](https://www.youtube.com/results?search_query=Determine%20Simple%20Graph%20dsa)

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
