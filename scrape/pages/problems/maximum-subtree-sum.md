# Maximum subtree sum · FAANGrind

Source: https://faangrind.vercel.app/problems/maximum-subtree-sum

[All problems](/problems)

#1087Hard· asked at 3 companies

# Maximum subtree sum

[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given the root of a binary tree where nodes may have negative values, return the **maximum sum of node values over all subtrees**. A subtree consists of a node together with **all** of its descendants (you cannot cut branches off). The entire tree is itself a subtree, and each single leaf is a subtree.

## Input / Output

* **Input:** root of a binary tree with `n` nodes.
* **Output:** an integer, the maximum subtree sum.

## Examples

**Example 1**

```
       1
      / \
    -2   3
    / \   \
   4  5   -6
```

Output: `9`
Explanation: Subtree rooted at `-2` has sum `-2+4+5 = 7`; subtree at `1` has sum `1+7+(3-6) = 5`; subtree at `4` has sum 4. The best is the whole tree? No — whole tree is 5. Rooted at `-2` gives 7, rooted at `3` gives `3-6 = -3`. Maximum is **7**... but wait: `4 + 5 = 9` is not a subtree since 4 and 5 are siblings. So the answer is `7`.

**Example 2**
Input: all nodes negative, e.g. a single node `-3`.
Output: `-3` (the answer can be negative; a subtree must be non-empty).

## Constraints

* `1 <= n <= 10^5`
* `-10^4 <= node.val <= 10^4`

## Approach

A post-order DFS computes each subtree's sum bottom-up:

```
function dfs(node):
    if node is null: return 0
    left  = dfs(node.left)
    right = dfs(node.right)
    total = node.val + left + right
    best  = max(best, total)
    return total
```

Initialise `best = -infinity`. Every node's subtree sum is computed exactly once, and the global maximum is updated at each node.

**Do not confuse with "maximum path sum".** In the path-sum problem you may drop a negative child branch; here you must include all descendants, so the recursion returns the full sum rather than `max(0, child)`.

## Complexity

* **Time:** O(n)
* **Space:** O(h) recursion stack, where `h` is the tree height (O(n) worst case for a skewed tree).

## Follow-ups

* Return the root of the best subtree, not just the sum (track the node along with the max).
* Count how many subtrees achieve the maximum.
* Iterative version using an explicit stack to avoid recursion depth limits.

## Reference solution (Python)

```
def max_subtree_sum(root):
    best = float('-inf')

    def dfs(node):
        nonlocal best
        if not node:
            return 0
        total = node.val + dfs(node.left) + dfs(node.right)
        best = max(best, total)
        return total

    dfs(root)
    return best
```

## Test cases

| Input | Expected |
| --- | --- |
| `tree 1(-2(4,5), 3(null,-6))` | `7` |
| `single node -3` | `-3` |
| `tree 1(2,3)` | `6` |
| `tree -1(-2,-3)` | `-2` |

[PreviousMaximum Number of Alloys](/problems/maximum-number-of-alloys)[NextMaximum Sum Obtained of Any Permutation](/problems/maximum-sum-obtained-of-any-permutation)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/atlassian.ico)Atlassian#4 in list](/companies/atlassian)
* [![](/logos/apple.ico)Apple#284 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#514 in list](/companies/amazon)

## Details

Difficulty
:   Hard

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Binary Trees](/topics?open=binary-trees#binary-trees)[Dynamic Programming](/topics?open=dynamic-programming#dynamic-programming)

[Solution](https://www.youtube.com/results?search_query=Maximum%20subtree%20sum%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#75Best time to buy and sell stockMedium](/problems/best-time-to-buy-and-sell-stock)
* [#909Longest Palindromic SubstringMedium](/problems/longest-palindromic-substring)
* [#714House robberMedium](/problems/house-robber)
* [#899Longest Increasing SubsequenceMedium](/problems/longest-increasing-subsequence)
* [#458Edit distanceMedium](/problems/edit-distance)
* [#184Climbing stairsMedium](/problems/climbing-stairs)
