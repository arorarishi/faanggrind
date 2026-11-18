# Requirements needed to construct a unique BT · FAANGrind

Source: https://faangrind.vercel.app/problems/requirements-needed-to-construct-a-unique-bt

[All problems](/problems)

#1639Medium· asked at 3 companies

# Requirements needed to construct a unique BT

[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given two of the three classic binary-tree traversals — **preorder**, **inorder**, **postorder** — decide whether the pair is sufficient to reconstruct a **unique** binary tree. The input is a pair of traversal names (e.g. `"preorder"` and `"postorder"`), and the output is `true` if a unique tree can always be built from those two sequences and `false` otherwise.

## Input / Output

* **Input:** two distinct values from `{preorder, inorder, postorder}` (often encoded as 1, 2, 3).
* **Output:** boolean.

## Examples

* `preorder + inorder` → `true`
* `postorder + inorder` → `true`
* `preorder + postorder` → `false`

## Explanation

**Inorder is the key.** Inorder traversal visits `left subtree, root, right subtree`. Once you know which element is the root, inorder tells you exactly which nodes belong to the left subtree and which to the right.

* **Preorder** gives the root first (`root, left, right`). So `preorder + inorder`: take the first element of preorder as root, find it in inorder, split into left/right, recurse. Every split is forced, hence unique.
* **Postorder** gives the root last (`left, right, root`). Same argument with `postorder + inorder`.
* **Preorder + postorder** both tell you the root but neither tells you how to split the remaining nodes between left and right. Consider a root `A` with a single child `B`: preorder is `A B` and postorder is `B A` **whether `B` is the left or the right child**. Two different trees, same traversals, so reconstruction is not unique.

**When is pre + post enough?** If the tree is a **full** binary tree (every node has 0 or 2 children), the ambiguity disappears: the second element of preorder is the left child's root, and its position in postorder marks the end of the left subtree. This is a common follow-up.

## Constraints

* The traversals contain distinct values.

## Approach (implementation)

The decision itself is a lookup: return `true` iff one of the two traversals is inorder. Interviewers usually then ask you to actually build the tree for the valid case:

1. Map each value to its index in inorder (hash map) for O(1) lookup.
2. Recursively take the root from preorder (front) or postorder (back), split inorder around it, and build subtrees.

## Complexity

* Decision: O(1).
* Construction: O(n) time and O(n) space with the index map.

## Reference solution (Python)

```
def is_unique_possible(a: int, b: int) -> bool:
    # 1 = preorder, 2 = inorder, 3 = postorder
    return a == 2 or b == 2

# Building the tree for the valid (pre + in) case:
class Node:
    def __init__(self, v): self.val, self.left, self.right = v, None, None

def build_pre_in(pre, ino):
    idx = {v: i for i, v in enumerate(ino)}
    it = iter(pre)
    def rec(lo, hi):
        if lo > hi: return None
        root = Node(next(it))
        m = idx[root.val]
        root.left = rec(lo, m - 1)
        root.right = rec(m + 1, hi)
        return root
    return rec(0, len(ino) - 1)
```

## Test cases

| Input | Expected |
| --- | --- |
| `preorder, inorder` | `true` |
| `inorder, postorder` | `true` |
| `preorder, postorder` | `false` |
| `pre=[1,2,4,5,3], in=[4,2,5,1,3]` | `tree with root 1, left 2 (children 4,5), right 3` |

[PreviousRemove Vowels from a String](/problems/remove-vowels-from-a-string)[NextSmallest Divisible Digit Product II](/problems/smallest-divisible-digit-product-ii)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/atlassian.ico)Atlassian#166 in list](/companies/atlassian)
* [![](/logos/apple.ico)Apple#180 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#363 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Binary Trees](/topics?open=binary-trees#binary-trees)

[Solution](https://www.youtube.com/results?search_query=Requirements%20needed%20to%20construct%20a%20unique%20BT%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#424Diameter of Binary TreeMedium](/problems/diameter-of-binary-tree)
* [#1706Serialize and De-serialize BTHard](/problems/serialize-and-de-serialize-bt)
* [#828LCA in BTMedium](/problems/lca-in-bt)
* [#157Check if a tree is a BST or notMedium](/problems/check-if-a-tree-is-a-bst-or-not)
* [#1531Print all nodes at a distance of K in BTMedium](/problems/print-all-nodes-at-a-distance-of-k-in-bt)
* [#1059Maximum path sumHard](/problems/maximum-path-sum)
