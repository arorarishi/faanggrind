# Delete Tail of Doubly Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/delete-tail-of-doubly-linked-list

[All problems](/problems)

#366Medium· asked at 3 companies

# Delete Tail of Doubly Linked List

[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/apple.ico)Apple](/companies/apple)

## Problem

Given the head of a doubly linked list, delete the **last** node and return the head of the resulting list. If the list is empty return `null`; if it has one node the result is empty.

## Input / Output

* **Input:** head of a DLL.
* **Output:** head after deleting the tail.

## Examples

**Example 1**
Input: `1 <-> 2 <-> 3`
Output: `1 <-> 2`

**Example 2**
Input: `9`
Output: empty list

**Example 3**
Input: `4 <-> 8`
Output: `4`

## Constraints

* `0 <= number of nodes <= 10^5`

## Approach

1. If `head` is `null`, return `null`.
2. If `head.next` is `null`, the only node is the tail — return `null`.
3. Otherwise walk to the last node `tail` (follow `next` until `next` is `null`).
4. Let `prev = tail.prev`. Set `prev.next = null` and `tail.prev = null`.
5. Return `head`.

If the structure also maintains a `tail` pointer (common in production implementations), step 3 becomes O(1) and the whole deletion is constant time — worth mentioning as the reason doubly linked lists make good deques.

## Complexity

* **Time:** O(n) to find the tail (O(1) with a stored tail pointer).
* **Space:** O(1)

## Reference solution (Python)

```
def delete_tail(head):
    if head is None or head.next is None:
        return None
    tail = head
    while tail.next:
        tail = tail.next
    prev = tail.prev
    prev.next = None
    tail.prev = None
    return head
```

## Test cases

| Input | Expected |
| --- | --- |
| `1<->2<->3` | `1<->2` |
| `9` | `None` |
| `4<->8` | `4` |
| empty | `None` |

[PreviousDelete Kth Element of Doubly Linked List](/problems/delete-kth-element-of-doubly-linked-list)[NextDeletion of the head of LL](/problems/deletion-of-the-head-of-ll)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/goldman-sachs.png)Goldman Sachs#69 in list](/companies/goldman-sachs)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#104 in list](/companies/palo-alto-networks)
* [![](/logos/apple.ico)Apple#134 in list](/companies/apple)

## Details

Difficulty
:   Medium

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Delete%20Tail%20of%20Doubly%20Linked%20List%20dsa)

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
