# Delete head of Doubly Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/delete-head-of-doubly-linked-list

[All problems](/problems)

#361Easy· asked at 2 companies

# Delete head of Doubly Linked List

[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)

## Problem

Given the head of a **doubly linked list**, delete the head node and return the new head. Each node has `val`, `prev` and `next`. If the list is empty, return `null`. If it has a single node, the result is an empty list.

## Input / Output

* **Input:** head of a DLL.
* **Output:** head of the list after removing the first node.

## Examples

**Example 1**
Input: `1 <-> 2 <-> 3`
Output: `2 <-> 3`

**Example 2**
Input: `5`
Output: empty list

**Example 3**
Input: empty list
Output: empty list

## Constraints

* `0 <= number of nodes <= 10^5`

## Approach

The head node is `head`; its successor is `head.next`.

1. If `head` is `null`, return `null`.
2. Let `newHead = head.next`.
3. If `newHead` is not `null`, set `newHead.prev = null` — this is the step people forget; leaving a dangling `prev` pointer breaks backward traversal.
4. Detach the old head (`head.next = null`) so it can be garbage collected / freed, and return `newHead`.

The operation touches at most two nodes and runs in constant time regardless of list length — one of the reasons a doubly linked list is chosen over an array for queue-like structures.

## Complexity

* **Time:** O(1)
* **Space:** O(1)

## Reference solution (Python)

```
class Node:
    def __init__(self, val):
        self.val, self.prev, self.next = val, None, None

def delete_head(head):
    if head is None:
        return None
    new_head = head.next
    if new_head:
        new_head.prev = None
    head.next = None
    return new_head
```

## Test cases

| Input | Expected |
| --- | --- |
| `1<->2<->3` | `2<->3`, and `new_head.prev is None` |
| `5` | `None` |
| empty | `None` |
| `1<->1` | `1` (second node) |

[PreviousCount the Number of Good Subarrays](/problems/count-the-number-of-good-subarrays)[NextDelete Kth Element of Doubly Linked List](/problems/delete-kth-element-of-doubly-linked-list)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/apple.ico)Apple#88 in list](/companies/apple)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#153 in list](/companies/palo-alto-networks)

## Details

Difficulty
:   Easy

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Delete%20head%20of%20Doubly%20Linked%20List%20dsa)

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
