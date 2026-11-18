# Insertion at the tail of Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/insertion-at-the-tail-of-linked-list

[All problems](/problems)

#750Medium· asked at 1 company

# Insertion at the tail of Linked List

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)

## Problem

Given the head of a singly linked list and an integer `val`, append a new node with value `val` at the **end** of the list and return the head. If the list is empty, the new node becomes the head.

## Input / Output

* **Input:** head (possibly `null`), integer `val`.
* **Output:** head of the updated list.

## Examples

**Example 1**
Input: `1 -> 2 -> 3`, `val = 4`
Output: `1 -> 2 -> 3 -> 4`

**Example 2**
Input: empty, `val = 9`
Output: `9`

## Constraints

* `0 <= number of nodes <= 10^5`

## Approach

1. If `head` is `null`, return a new node.
2. Walk `cur` until `cur.next` is `null` (the last node).
3. Set `cur.next = ListNode(val)` and return `head`.

Appending costs O(n) because a singly linked list has no direct reference to its last node. In practice, list implementations keep a **tail pointer** so that append becomes O(1) — a good point to raise. With a tail pointer: `tail.next = node; tail = node`.

Follow-up: append `k` values in one pass by keeping `cur` at the tail after the first append rather than re-walking each time.

## Complexity

* **Time:** O(n) (O(1) with a tail pointer)
* **Space:** O(1)

## Reference solution (Python)

```
def insert_tail(head, val):
    node = ListNode(val)
    if head is None:
        return node
    cur = head
    while cur.next:
        cur = cur.next
    cur.next = node
    return head
```

## Test cases

| Input | Expected |
| --- | --- |
| `1->2->3, val=4` | `[1,2,3,4]` |
| `empty, val=9` | `[9]` |
| `7, val=8` | `[7,8]` |
| append twice to empty (1 then 2) | `[1,2]` |

[PreviousInsertion at the Kth position of Linked List](/problems/insertion-at-the-kth-position-of-linked-list)[NextJump Game VI](/problems/jump-game-vi)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#27 in list](/companies/palo-alto-networks)

## Details

Difficulty
:   Medium

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Insertion%20at%20the%20tail%20of%20Linked%20List%20dsa)

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
