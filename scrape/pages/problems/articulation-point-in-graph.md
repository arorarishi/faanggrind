# Articulation point in graph · FAANGrind

Source: https://faangrind.vercel.app/problems/articulation-point-in-graph

[All problems](/problems)

#52Hard· asked at 7 companies

# Articulation point in graph

[![](/logos/linkedin.ico)LinkedIn](/companies/linkedin)[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/apple.ico)Apple](/companies/apple)+1 more

## Problem

You are given an undirected, connected graph with `V` vertices (numbered 0 to V-1) and `E` edges. A vertex is an **articulation point** (or cut vertex) if removing it, along with all edges incident to it, disconnects the graph into two or more components. Return all articulation points in ascending order; if there are none, return `[-1]`.

## Input / Output

* **Input:** `V`, and an adjacency list `adj` where `adj[u]` lists the neighbours of `u`.
* **Output:** sorted list of articulation points, or `[-1]`.

## Examples

**Example 1**
Input: `V = 5`, edges `0-1, 1-2, 2-0, 1-3, 3-4`
Output: `[1, 3]`
Explanation: Removing vertex 1 separates `{0,2}` from `{3,4}`; removing 3 isolates vertex 4.

**Example 2**
Input: `V = 4`, edges `0-1, 1-2, 2-3, 3-0` (a cycle)
Output: `[-1]`
Explanation: Removing any single vertex leaves a path, still connected.

## Constraints

* `1 <= V <= 10^5`, `0 <= E <= 2 * 10^5`
* Graph is connected and has no self-loops.

## Approach — Tarjan's algorithm

A naive solution removes each vertex and runs BFS/DFS to test connectivity: O(V · (V+E)), too slow.

Tarjan's DFS-based algorithm finds all articulation points in one pass using two arrays:

* `tin[u]` — the time (DFS order) at which `u` was first visited.
* `low[u]` — the smallest `tin` reachable from the subtree of `u` using at most one **back edge** (an edge to an already-visited ancestor).

Run DFS from any vertex. For every tree edge `u -> v`:

1. Recurse into `v`, then set `low[u] = min(low[u], low[v])`.
2. If `low[v] >= tin[u]` and `u` is **not** the root, then `v`'s subtree cannot climb above `u` without passing through `u`, so `u` is an articulation point.
3. For a back edge `u -> v` (where `v` is already visited and is not the parent), set `low[u] = min(low[u], tin[v])`.

The **root** is a special case: it is an articulation point if and only if it has **two or more** children in the DFS tree.

Collect vertices into a set (a vertex may satisfy the condition for several children), then sort.

## Complexity

* **Time:** O(V + E)
* **Space:** O(V) for `tin`, `low`, visited, and recursion stack.

## Why it matters

Articulation points identify single points of failure in networks (routers, bridges in infrastructure). The same `low`-link idea extends to finding **bridges** (critical edges) and biconnected components.

## Reference solution (Python)

```
import sys
sys.setrecursionlimit(1 << 20)

def articulation_points(V, adj):
    tin = [-1] * V
    low = [0] * V
    is_ap = [False] * V
    timer = 0

    def dfs(u, parent):
        nonlocal timer
        tin[u] = low[u] = timer
        timer += 1
        children = 0
        for v in adj[u]:
            if v == parent:
                continue
            if tin[v] != -1:
                low[u] = min(low[u], tin[v])
            else:
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if low[v] >= tin[u] and parent != -1:
                    is_ap[u] = True
                children += 1
        if parent == -1 and children > 1:
            is_ap[u] = True

    for i in range(V):
        if tin[i] == -1:
            dfs(i, -1)
    res = [i for i in range(V) if is_ap[i]]
    return res if res else [-1]
```

## Test cases

| Input | Expected |
| --- | --- |
| `V=5, edges 0-1,1-2,2-0,1-3,3-4` | `[1, 3]` |
| `V=4, cycle 0-1-2-3-0` | `[-1]` |
| `V=3, path 0-1-2` | `[1]` |
| `V=1, no edges` | `[-1]` |

[Previous4 Keys Keyboard](/problems/4-keys-keyboard)[NextBasic Calculator III](/problems/basic-calculator-iii)

Saved in this browser. No account needed.

## Asked at

7 companies

* [![](/logos/linkedin.ico)LinkedIn#9 in list](/companies/linkedin)
* [![](/logos/paypal.png)PayPal#108 in list](/companies/paypal)
* [![](/logos/adobe.ico)Adobe#112 in list](/companies/adobe)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#176 in list](/companies/walmart-global-tech)
* [![](/logos/goldman-sachs.png)Goldman Sachs#217 in list](/companies/goldman-sachs)
* [![](/logos/apple.ico)Apple#268 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#664 in list](/companies/amazon)

## Details

Difficulty
:   Hard

Popularity
:   24/100

Source
:   Full statement on FAANGrind

Topics
:   [Graphs](/topics?open=graphs#graphs)

[Solution](https://www.youtube.com/results?search_query=Articulation%20point%20in%20graph%20dsa)

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
