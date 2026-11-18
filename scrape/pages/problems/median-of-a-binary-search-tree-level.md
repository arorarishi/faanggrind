# Median of a Binary Search Tree Level · FAANGrind

Source: https://faangrind.vercel.app/problems/median-of-a-binary-search-tree-level

[All problems](/problems)

#1123Medium· asked at 1 company

# Median of a Binary Search Tree Level

[![](/logos/linkedin.ico)LinkedIn](/companies/linkedin)

## Problem

Given the root of a **binary search tree** and an integer `L` (0-based, root is level 0), return the **median** of the node values on level `L`. If the level has an even number of nodes, return the average of the two middle values (as a float, or the floor if integers are required). If level `L` does not exist, return `-1`.

## Input / Output

* **Input:** BST root, integer `L`.
* **Output:** median value of that level.

## Examples

**Example 1**

```
        8
      /   \
     3     10
    / \      \
   1   6      14
```

Input: `L = 2`
Output: `6`
Explanation: Level 2 contains `1, 6, 14`; median is 6.

**Example 2**
Input: same tree, `L = 1`
Output: `6.5` (values `3, 10`; average of the two middles)

**Example 3**
Input: same tree, `L = 5`
Output: `-1`

## Constraints

* `1 <= number of nodes <= 10^5`
* `0 <= L <= height`

## Approach

**Key observation.** In a BST, an in-order-style traversal visits keys in ascending order, and within any single level the nodes ordered **left to right** are also in ascending order (each node's subtree lies entirely between its ancestors' keys). So a plain **BFS** that collects level `L` left to right already yields the level's values sorted — no extra sort is needed.

1. Run BFS level by level, keeping only the current level's list.
2. Stop when level `L` is reached (early exit saves work on deep trees).
3. If the level is empty, return `-1`.
4. Let `k = len(level)`. If `k` is odd, the median is `level[k//2]`; otherwise it is `(level[k//2 - 1] + level[k//2]) / 2`.

If the tree were **not** a BST, you would sort the level's values (O(k log k)) or use quickselect for O(k).

## Complexity

* **Time:** O(number of nodes up to level L)
* **Space:** O(width of the tree) for the BFS queue.

## Reference solution (Python)

```
from collections import deque

class TreeNode:
    def __init__(self, val, left=None, right=None):
        self.val, self.left, self.right = val, left, right

def median_of_level(root, L):
    if root is None:
        return -1
    level, depth = [root], 0
    while level and depth < L:
        nxt = []
        for n in level:
            if n.left: nxt.append(n.left)
            if n.right: nxt.append(n.right)
        level, depth = nxt, depth + 1
    if not level:
        return -1
    vals = [n.val for n in level]        # already ascending in a BST
    k = len(vals)
    return vals[k // 2] if k % 2 else (vals[k // 2 - 1] + vals[k // 2]) / 2
```

## Test cases

| Input | Expected |
| --- | --- |
| tree above, `L=2` | `6` |
| tree above, `L=1` | `6.5` |
| tree above, `L=0` | `8` |
| tree above, `L=5` | `-1` |

[PreviousMaximum XOR for Each Query](/problems/maximum-xor-for-each-query)[NextMinesweeper](/problems/minesweeper)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/linkedin.ico)LinkedIn#71 in list](/companies/linkedin)

## Details

Difficulty
:   Medium

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Binary Search Trees](/topics?open=binary-search-trees#binary-search-trees)

[Solution](https://www.youtube.com/results?search_query=Median%20of%20a%20Binary%20Search%20Tree%20Level%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#802Kth Smallest and Largest element in BSTMedium](/problems/kth-smallest-and-largest-element-in-bst)
* [#1925Two sum in BSTMedium](/problems/two-sum-in-bst)
* [#358Delete a node in BSTMedium](/problems/delete-a-node-in-bst)
* [#799Kth largest element in a stream of running integersMedium](/problems/kth-largest-element-in-a-stream-of-running-integers)
* [#85Binary Search Tree Iterator IIMedium](/problems/binary-search-tree-iterator-ii)
* [#244Convert Sorted Array to Binary Search TreeEasy](/problems/convert-sorted-array-to-binary-search-tree)
