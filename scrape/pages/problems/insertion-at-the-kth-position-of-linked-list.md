# Insertion at the Kth position of Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/insertion-at-the-kth-position-of-linked-list

[All problems](/problems)

#749Medium· asked at 1 company

# Insertion at the Kth position of Linked List

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)

## Problem

Given the head of a singly linked list, an integer `val` and a 1-based position `k`, insert a new node with value `val` so that it becomes the **k-th** node of the list. If `k` is greater than `length + 1`, leave the list unchanged. Return the head.

## Input / Output

* **Input:** head, `val`, `k`.
* **Output:** head after insertion.

## Examples

**Example 1**
Input: `1 -> 2 -> 4`, `val = 3`, `k = 3`
Output: `1 -> 2 -> 3 -> 4`

**Example 2**
Input: `1 -> 2`, `val = 0`, `k = 1`
Output: `0 -> 1 -> 2`

**Example 3**
Input: `1 -> 2`, `val = 3`, `k = 3`
Output: `1 -> 2 -> 3`

**Example 4**
Input: `1 -> 2`, `val = 9`, `k = 5`
Output: `1 -> 2` (unchanged)

## Constraints

* `0 <= number of nodes <= 10^5`
* `1 <= k <= 10^9`

## Approach

To insert at position `k` you need a pointer to node `k-1`. Use a **dummy** node before the head so that `k = 1` needs no special case:

1. `prev = dummy`; move it `k-1` steps. If `prev` becomes `null` before finishing, `k` is out of range — return `head`.
2. `node.next = prev.next; prev.next = node`.
3. Return `dummy.next`.

The dummy-node pattern is the same one that simplifies deletion, so master it once and reuse it.

## Complexity

* **Time:** O(k)
* **Space:** O(1)

## Reference solution (Python)

```
def insert_kth(head, val, k):
    dummy = ListNode(0, head)
    prev = dummy
    for _ in range(k - 1):
        prev = prev.next
        if prev is None:
            return head
    prev.next = ListNode(val, prev.next)
    return dummy.next
```

## Test cases

| Input | Expected |
| --- | --- |
| `1->2->4, val=3, k=3` | `[1,2,3,4]` |
| `1->2, val=0, k=1` | `[0,1,2]` |
| `1->2, val=3, k=3` | `[1,2,3]` |
| `1->2, val=9, k=5` | `[1,2]` |

[PreviousInsertion at the head of Linked List](/problems/insertion-at-the-head-of-linked-list)[NextInsertion at the tail of Linked List](/problems/insertion-at-the-tail-of-linked-list)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#129 in list](/companies/palo-alto-networks)

## Details

Difficulty
:   Medium

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Insertion%20at%20the%20Kth%20position%20of%20Linked%20List%20dsa)

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
