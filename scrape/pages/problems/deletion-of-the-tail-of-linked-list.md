# Deletion of the tail of Linked List · FAANGrind

Source: https://faangrind.vercel.app/problems/deletion-of-the-tail-of-linked-list

[All problems](/problems)

#371Medium· asked at 2 companies

# Deletion of the tail of Linked List

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

Given the head of a **singly** linked list, delete the last node and return the head. If the list is empty or has one node, return `null`.

## Input / Output

* **Input:** head of a singly linked list.
* **Output:** head after deleting the tail.

## Examples

**Example 1**
Input: `1 -> 2 -> 3`
Output: `1 -> 2`

**Example 2**
Input: `9`
Output: empty

**Example 3**
Input: `4 -> 8`
Output: `4`

## Constraints

* `0 <= number of nodes <= 10^5`

## Approach

Because nodes only point forward, deleting the tail requires the **second-to-last** node:

1. If `head` is `null` or `head.next` is `null`, return `null`.
2. Walk `cur` until `cur.next.next` is `null` — `cur` is now the second-to-last node.
3. Set `cur.next = null`.

Unlike a doubly linked list (where a stored tail pointer makes this O(1)), a singly linked list needs the full traversal even if a tail pointer exists, because the new tail's predecessor is unknown. Interviewers use this contrast to ask *when would you choose a doubly linked list?*

## Complexity

* **Time:** O(n)
* **Space:** O(1)

## Reference solution (Python)

```
def delete_tail(head):
    if head is None or head.next is None:
        return None
    cur = head
    while cur.next.next:
        cur = cur.next
    cur.next = None
    return head
```

## Test cases

| Input | Expected |
| --- | --- |
| `1->2->3` | `1->2` |
| `9` | `None` |
| `4->8` | `4` |
| empty | `None` |

[PreviousDeletion of the Kth element of Linked List](/problems/deletion-of-the-kth-element-of-linked-list)[NextDesign Authentication Manager](/problems/design-authentication-manager)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#174 in list](/companies/palo-alto-networks)
* [![](/logos/goldman-sachs.png)Goldman Sachs#292 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Medium

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Deletion%20of%20the%20tail%20of%20Linked%20List%20dsa)

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
