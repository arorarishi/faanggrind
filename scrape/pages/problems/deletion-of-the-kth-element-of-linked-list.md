# Deletion of the Kth element of Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/deletion-of-the-kth-element-of-linked-list

[All problems](/problems)

#370Medium· asked at 2 companies

# Deletion of the Kth element of Linked List

[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)

## Problem

Given the head of a **singly** linked list and a 1-based position `k`, delete the k-th node and return the head of the modified list. If `k` exceeds the list length, return the list unchanged.

## Input / Output

* **Input:** head, integer `k`.
* **Output:** head after deletion.

## Examples

**Example 1**
Input: `1 -> 2 -> 3 -> 4`, `k = 3`
Output: `1 -> 2 -> 4`

**Example 2**
Input: `1 -> 2 -> 3`, `k = 1`
Output: `2 -> 3`

**Example 3**
Input: `1 -> 2`, `k = 2`
Output: `1`

**Example 4**
Input: `1 -> 2`, `k = 7`
Output: `1 -> 2`

## Constraints

* `1 <= number of nodes <= 10^5`
* `1 <= k <= 10^9`

## Approach

In a singly linked list you cannot step backwards, so to unlink node `k` you must hold a pointer to node `k-1`.

1. If `k == 1`, the answer is simply `head.next` (delete head).
2. Otherwise walk a pointer `prev` `k-2` steps from `head`. If `prev` or `prev.next` becomes `null` along the way, `k` is out of range — return `head`.
3. Set `prev.next = prev.next.next`.

A **dummy node** in front of `head` removes the special case: start `prev` at the dummy, walk `k-1` steps, unlink, and return `dummy.next`. This trick is worth showing in interviews because it also simplifies "remove N-th from end", "delete duplicates", and most insertion problems.

## Complexity

* **Time:** O(k)
* **Space:** O(1)

## Reference solution (Python)

```
def delete_kth(head, k):
    dummy = ListNode(0, head)
    prev = dummy
    for _ in range(k - 1):
        if prev.next is None:
            return head
        prev = prev.next
    if prev.next is None:
        return head
    prev.next = prev.next.next
    return dummy.next
```

## Test cases

| Input | Expected |
| --- | --- |
| `1->2->3->4, k=3` | `1->2->4` |
| `1->2->3, k=1` | `2->3` |
| `1->2, k=2` | `1` |
| `1->2, k=7` | `1->2` |

[PreviousDeletion of the head of LL](/problems/deletion-of-the-head-of-ll)[NextDeletion of the tail of Linked List](/problems/deletion-of-the-tail-of-linked-list)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/goldman-sachs.png)Goldman Sachs#10 in list](/companies/goldman-sachs)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#171 in list](/companies/palo-alto-networks)

## Details

Difficulty
:   Medium

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Deletion%20of%20the%20Kth%20element%20of%20Linked%20List%20dsa)

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
