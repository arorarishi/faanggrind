# Pre, Post, Inorder in one traversal · FAANGrind

Source: https://faangrind.vercel.app/problems/pre-post-inorder-in-one-traversal

[All problems](/problems)

#1526Medium· asked at 1 company

# Pre, Post, Inorder in one traversal

[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)

## Problem

Given the root of a binary tree, produce its **preorder**, **inorder** and **postorder** traversals using a **single pass** over the tree with one explicit stack — not three separate traversals.

## Input / Output

* **Input:** root of a binary tree.
* **Output:** three lists: `[preorder, inorder, postorder]`.

## Examples

**Example 1**

```
      1
     / \
    2   3
   / \
  4   5
```

Output:

* preorder `[1, 2, 4, 5, 3]`
* inorder `[4, 2, 5, 1, 3]`
* postorder `[4, 5, 2, 3, 1]`

**Example 2**
Input: single node `7`
Output: `[[7], [7], [7]]`

## Constraints

* `0 <= number of nodes <= 10^5`

## Approach — stack of (node, state)

Every node is visited three times during a DFS: on the way down (preorder), between its children (inorder) and on the way up (postorder). Encode that with a state number 1, 2, 3 stored alongside the node on the stack:

* **state 1:** record the value in `pre`, increment the state to 2, and push the left child with state 1 if it exists.
* **state 2:** record the value in `in`, increment to 3, and push the right child with state 1 if it exists.
* **state 3:** record the value in `post` and pop the node.

Each node is pushed once and its state advances exactly twice, so the total number of stack operations is O(n). The technique generalises the usual "iterative inorder" and is the cleanest way to explain why the three orders differ only by *when* the node is emitted.

Recursion produces the same three lists by placing the append calls before, between and after the recursive calls — worth showing as the mental model, then converting to the explicit stack to avoid recursion-depth limits.

## Complexity

* **Time:** O(n)
* **Space:** O(h) for the stack, where `h` is the tree height.

## Reference solution (Python)

```
def all_traversals(root):
    pre, ino, post = [], [], []
    if root is None:
        return [pre, ino, post]
    stack = [(root, 1)]
    while stack:
        node, state = stack.pop()
        if state == 1:
            pre.append(node.val)
            stack.append((node, 2))
            if node.left:
                stack.append((node.left, 1))
        elif state == 2:
            ino.append(node.val)
            stack.append((node, 3))
            if node.right:
                stack.append((node.right, 1))
        else:
            post.append(node.val)
    return [pre, ino, post]
```

## Test cases

| Input | Expected |
| --- | --- |
| tree `1(2(4,5),3)` | `[[1,2,4,5,3],[4,2,5,1,3],[4,5,2,3,1]]` |
| single node `7` | `[[7],[7],[7]]` |
| empty | `[[],[],[]]` |
| left-skewed `1(2(3))` | `[[1,2,3],[3,2,1],[3,2,1]]` |

[PreviousPopulating Next Right Pointers in Each Node II](/problems/populating-next-right-pointers-in-each-node-ii)[NextReverse a Stack](/problems/reverse-a-stack)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/atlassian.ico)Atlassian#12 in list](/companies/atlassian)

## Details

Difficulty
:   Medium

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Binary Trees](/topics?open=binary-trees#binary-trees)

[Solution](https://www.youtube.com/results?search_query=Pre%2C%20Post%2C%20Inorder%20in%20one%20traversal%20dsa)

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
