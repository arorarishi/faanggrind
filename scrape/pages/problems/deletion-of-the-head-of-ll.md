# Deletion of the head of LL · FAANGrind

Source: https://faangrind.vercel.app/problems/deletion-of-the-head-of-ll

[All problems](/problems)

#369Medium· asked at 2 companies

# Deletion of the head of LL

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

Given the head of a **singly** linked list, delete the first node and return the new head. Return `null` if the list is empty or becomes empty.

## Input / Output

* **Input:** head of a singly linked list.
* **Output:** head after deleting the first node.

## Examples

**Example 1**
Input: `1 -> 2 -> 3`
Output: `2 -> 3`

**Example 2**
Input: `5`
Output: empty

**Example 3**
Input: empty
Output: empty

## Constraints

* `0 <= number of nodes <= 10^5`

## Approach

1. If `head` is `null`, return `null`.
2. `newHead = head.next`.
3. Detach the old head (`head.next = null`) so the memory can be reclaimed, and return `newHead`.

Deleting the head is O(1) because a linked list has no need to shift elements — contrast with deleting index 0 of an array, which is O(n). This is the property that makes linked lists suitable for queues and LRU caches.

In languages with manual memory management (C/C++), `free`/`delete` the old node after re-pointing.

## Complexity

* **Time:** O(1)
* **Space:** O(1)

## Reference solution (Python)

```
class ListNode:
    def __init__(self, val, nxt=None):
        self.val, self.next = val, nxt

def delete_head(head):
    if head is None:
        return None
    new_head = head.next
    head.next = None
    return new_head
```

## Test cases

| Input | Expected |
| --- | --- |
| `1->2->3` | `2->3` |
| `5` | `None` |
| empty | `None` |
| `1->1` | `1` |

[PreviousDelete Tail of Doubly Linked List](/problems/delete-tail-of-doubly-linked-list)[NextDeletion of the Kth element of Linked List](/problems/deletion-of-the-kth-element-of-linked-list)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#17 in list](/companies/palo-alto-networks)
* [![](/logos/goldman-sachs.png)Goldman Sachs#30 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Medium

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Deletion%20of%20the%20head%20of%20LL%20dsa)

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
