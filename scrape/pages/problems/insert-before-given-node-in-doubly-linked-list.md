# Insert before given node in Doubly Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/insert-before-given-node-in-doubly-linked-list

[All problems](/problems)

#743Medium· asked at 1 company

# Insert before given node in Doubly Linked List

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)

## Problem

You are given a reference to a node `node` inside a doubly linked list (each node has `val`, `prev`, `next`) and an integer `val`. Insert a new node containing `val` **immediately before** `node`. The list's head may change if `node` was the head; return the (possibly new) head.

## Input / Output

* **Input:** head, `node` (a node in the list), integer `val`.
* **Output:** head after insertion.

## Examples

**Example 1**
Input: `1 <-> 3 <-> 4`, `node = 3`, `val = 2`
Output: `1 <-> 2 <-> 3 <-> 4`

**Example 2**
Input: `5 <-> 6`, `node = 5`, `val = 4`
Output: `4 <-> 5 <-> 6` (new head)

## Constraints

* `1 <= number of nodes <= 10^5`
* `node` is guaranteed to be in the list.

## Approach

Because each node knows its predecessor, no traversal is needed — this is the operation a doubly linked list is built for.

1. `p = node.prev`.
2. Create `new` with `new.prev = p` and `new.next = node`.
3. `node.prev = new`.
4. If `p` is not `null`, `p.next = new`; otherwise `node` was the head, so `new` becomes the head.
5. Return the head.

Four pointer assignments in a fixed order; drawing the before/after picture prevents the classic mistake of overwriting `node.prev` before reading it.

## Complexity

* **Time:** O(1)
* **Space:** O(1)

## Reference solution (Python)

```
class DNode:
    def __init__(self, val):
        self.val, self.prev, self.next = val, None, None

def insert_before(head, node, val):
    new = DNode(val)
    p = node.prev
    new.prev, new.next = p, node
    node.prev = new
    if p:
        p.next = new
        return head
    return new

def dll_to_list(head):
    out = []
    while head:
        out.append(head.val); head = head.next
    return out
```

## Test cases

| Input | Expected |
| --- | --- |
| `1<->3<->4, node=3, val=2` | `[1,2,3,4]` |
| `5<->6, node=5, val=4` | `[4,5,6]` |
| `9, node=9, val=8` | `[8,9]` |
| backward walk after insert | `prev` links consistent |

[PreviousImplement Stack using Queue](/problems/implement-stack-using-queue)[NextInsertion at the head of Linked List](/problems/insertion-at-the-head-of-linked-list)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#168 in list](/companies/palo-alto-networks)

## Details

Difficulty
:   Medium

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Insert%20before%20given%20node%20in%20Doubly%20Linked%20List%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#934LRU CacheMedium](/problems/lru-cache)
* [#1140Merge two Sorted ListsMedium](/problems/merge-two-sorted-lists)
* [#20Add two numbers in Linked ListMedium](/problems/add-two-numbers-in-linked-list)
* [#1134Merge K sorted ListsMedium](/problems/merge-k-sorted-lists)
* [#854LFU CacheHard](/problems/lfu-cache)
* [#1644Reverse a LLMedium](/problems/reverse-a-ll)
