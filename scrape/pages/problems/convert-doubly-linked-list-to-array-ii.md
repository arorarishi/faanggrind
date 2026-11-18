# Convert Doubly Linked List to Array II · FAANGrind

Source: https://faangrind.vercel.app/problems/convert-doubly-linked-list-to-array-ii

[All problems](/problems)

#243Medium· asked at 5 companies

# Convert Doubly Linked List to Array II

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

You are given **any node** of a doubly linked list — not necessarily the head. Each node has fields `val`, `prev` and `next`. Return an array containing all values of the list in forward order (head to tail).

## Input / Output

* **Input:** a reference to one node somewhere in the list.
* **Output:** integer array of all values from head to tail.

## Examples

**Example 1**
Input: list `1 <-> 2 <-> 3 <-> 4 <-> 5`, given node is the one with value `3`
Output: `[1, 2, 3, 4, 5]`

**Example 2**
Input: list `7 <-> 9`, given node is `9`
Output: `[7, 9]`

**Example 3**
Input: single node `42`
Output: `[42]`

## Constraints

* `1 <= number of nodes <= 10^5`

## Approach

**Two-phase walk (O(1) extra space).**

1. From the given node, follow `prev` pointers until `prev` is `null` — that node is the head.
2. From the head, follow `next` pointers and append every value.

Total steps: at most `n` backwards plus `n` forwards.

**Alternative without finding the head first.** Collect values going backwards from the given node into a temporary list, reverse it, then append the values going forward from `node.next`. Same complexity but slightly more code; the two-phase version is cleaner.

## Complexity

* **Time:** O(n)
* **Space:** O(n) for the output; O(1) auxiliary.

## Follow-ups

* What if the list is **circular** (the tail's `next` points to the head)? You cannot search for a `null` `prev`; instead remember the starting node and stop when you return to it — walk backwards to collect the "before" portion, then forwards, using the start node as the sentinel.
* Return values in reverse order (follow `next` to the tail, then walk `prev`).
* Detect corruption where `a.next.prev != a` while traversing.

## Reference solution (Python)

```
def dll_to_array_from_any(node):
    if node is None:
        return []
    while node.prev:
        node = node.prev
    out = []
    while node:
        out.append(node.val)
        node = node.next
    return out
```

## Test cases

| Input | Expected |
| --- | --- |
| `list 1<->2<->3<->4<->5, given node 3` | `[1,2,3,4,5]` |
| `list 7<->9, given node 9` | `[7,9]` |
| `single node 42` | `[42]` |
| `given node is head` | `same as forward traversal` |

[PreviousConstructing Two Increasing Arrays](/problems/constructing-two-increasing-arrays)[NextConvex Polygon](/problems/convex-polygon)

Saved in this browser. No account needed.

## Asked at

5 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#21 in list](/companies/palo-alto-networks)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#75 in list](/companies/jpmorgan-chase)
* [![](/logos/goldman-sachs.png)Goldman Sachs#93 in list](/companies/goldman-sachs)
* [![](/logos/apple.ico)Apple#274 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#537 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   18/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)[Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Convert%20Doubly%20Linked%20List%20to%20Array%20II%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#934LRU CacheMedium](/problems/lru-cache)
* [#788Kadane's AlgorithmMedium](/problems/kadane-s-algorithm)
* [#53 SumMedium](/problems/3-sum)
* [#1678Rotten OrangesMedium](/problems/rotten-oranges)
* [#1140Merge two Sorted ListsMedium](/problems/merge-two-sorted-lists)
