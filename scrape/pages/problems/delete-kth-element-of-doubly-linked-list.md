# Delete Kth Element of Doubly Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/delete-kth-element-of-doubly-linked-list

[All problems](/problems)

#362Medium· asked at 3 companies

# Delete Kth Element of Doubly Linked List

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/apple.ico)Apple](/companies/apple)

## Problem

Given the head of a doubly linked list and a 1-based position `k`, delete the k-th node and return the head of the modified list. If `k` is larger than the length of the list, return the list unchanged.

## Input / Output

* **Input:** head of a DLL, integer `k`.
* **Output:** head after deletion.

## Examples

**Example 1**
Input: `1 <-> 2 <-> 3 <-> 4`, `k = 3`
Output: `1 <-> 2 <-> 4`

**Example 2**
Input: `1 <-> 2 <-> 3`, `k = 1`
Output: `2 <-> 3`

**Example 3**
Input: `1 <-> 2`, `k = 2`
Output: `1`

**Example 4**
Input: `1 <-> 2`, `k = 5`
Output: `1 <-> 2` (unchanged)

## Constraints

* `1 <= number of nodes <= 10^5`
* `1 <= k <= 10^9`

## Approach

1. Walk from `head` `k-1` steps to reach the target node `cur`. If you run off the end, `k` is out of range — return `head`.
2. Let `p = cur.prev` and `q = cur.next`.
3. Re-link around `cur`:
   * If `p` is not `null`, `p.next = q`; otherwise `cur` was the head, so the new head is `q`.
   * If `q` is not `null`, `q.prev = p`.
4. Clear `cur.prev` and `cur.next`, then return the (possibly new) head.

Because the list is doubly linked, no separate "previous" pointer needs to be tracked during the walk — `cur.prev` is already available. Handle three cases explicitly: deleting the head, deleting the tail, deleting a middle node.

## Complexity

* **Time:** O(k) to reach the node, O(1) to unlink.
* **Space:** O(1)

## Reference solution (Python)

```
def delete_kth(head, k):
    cur = head
    for _ in range(k - 1):
        if cur is None:
            return head
        cur = cur.next
    if cur is None:
        return head
    p, q = cur.prev, cur.next
    if p:
        p.next = q
    else:
        head = q
    if q:
        q.prev = p
    cur.prev = cur.next = None
    return head
```

## Test cases

| Input | Expected |
| --- | --- |
| `1<->2<->3<->4, k=3` | `1<->2<->4` |
| `1<->2<->3, k=1` | `2<->3` |
| `1<->2, k=2` | `1` |
| `1<->2, k=5` | `1<->2` |

[PreviousDelete head of Doubly Linked List](/problems/delete-head-of-doubly-linked-list)[NextDelete Tail of Doubly Linked List](/problems/delete-tail-of-doubly-linked-list)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#137 in list](/companies/palo-alto-networks)
* [![](/logos/goldman-sachs.png)Goldman Sachs#242 in list](/companies/goldman-sachs)
* [![](/logos/apple.ico)Apple#318 in list](/companies/apple)

## Details

Difficulty
:   Medium

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Delete%20Kth%20Element%20of%20Doubly%20Linked%20List%20dsa)

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
