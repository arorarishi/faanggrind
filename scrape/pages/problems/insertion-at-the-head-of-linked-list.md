# Insertion at the head of Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/insertion-at-the-head-of-linked-list

[All problems](/problems)

#748Easy· asked at 1 company

# Insertion at the head of Linked List

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)

## Problem

Given the head of a singly linked list and an integer `val`, insert a new node containing `val` at the **beginning** of the list and return the new head. The list may be empty.

## Input / Output

* **Input:** head (possibly `null`), integer `val`.
* **Output:** new head.

## Examples

**Example 1**
Input: `2 -> 3 -> 4`, `val = 1`
Output: `1 -> 2 -> 3 -> 4`

**Example 2**
Input: empty, `val = 7`
Output: `7`

## Constraints

* `0 <= number of nodes <= 10^5`

## Approach

1. Create `node = ListNode(val)`.
2. Set `node.next = head` (works even when `head` is `null`).
3. Return `node`.

No traversal is needed, which is why a linked list is preferred over an array for a **stack** or a **queue's front**: pushing to the front is O(1) versus O(n) for shifting array elements.

For a **doubly** linked list, also set `head.prev = node` when `head` exists.

## Complexity

* **Time:** O(1)
* **Space:** O(1)

## Reference solution (Python)

```
class ListNode:
    def __init__(self, val, nxt=None):
        self.val, self.next = val, nxt

def insert_head(head, val):
    return ListNode(val, head)

def to_list(head):
    out = []
    while head:
        out.append(head.val); head = head.next
    return out
```

## Test cases

| Input | Expected |
| --- | --- |
| `2->3->4, val=1` | `[1,2,3,4]` |
| `empty, val=7` | `[7]` |
| `5, val=5` | `[5,5]` |
| insert 1 then 0 at head | `[0,1,...]` |

[PreviousInsert before given node in Doubly Linked List](/problems/insert-before-given-node-in-doubly-linked-list)[NextInsertion at the Kth position of Linked List](/problems/insertion-at-the-kth-position-of-linked-list)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#122 in list](/companies/palo-alto-networks)

## Details

Difficulty
:   Easy

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Insertion%20at%20the%20head%20of%20Linked%20List%20dsa)

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
