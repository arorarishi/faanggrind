# Convert Doubly Linked List to Array I · FAANGrind

Source: https://faangrind.vercel.app/problems/convert-doubly-linked-list-to-array-i

[All problems](/problems)

#242Medium· asked at 6 companies

# Convert Doubly Linked List to Array I

[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/swiggy.png)Swiggy](/companies/swiggy)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

You are given the **head** of a doubly linked list. Each node has fields `val`, `prev` and `next`. Return an array containing the node values in forward order (from head to tail).

## Input / Output

* **Input:** head node of the list (possibly `null` for an empty list).
* **Output:** integer array of values.

## Examples

**Example 1**
Input: list `1 <-> 2 <-> 3 <-> 4`
Output: `[1, 2, 3, 4]`

**Example 2**
Input: empty list
Output: `[]`

## Constraints

* `0 <= number of nodes <= 10^5`
* `-10^9 <= val <= 10^9`

## Approach

Traverse from the head following `next` pointers, appending each value:

```
result = []
cur = head
while cur != null:
    result.append(cur.val)
    cur = cur.next
return result
```

Because we start at the head, the `prev` pointers are not needed. If the array size must be known up front (fixed-size arrays), do a first pass to count nodes, allocate, then fill.

## Complexity

* **Time:** O(n)
* **Space:** O(n) for the output; O(1) auxiliary.

## What the interviewer is checking

* Comfort with the doubly-linked node structure and null termination.
* Handling the empty list.
* Awareness that the reverse array (tail to head) can be produced just as easily by following `prev` from the tail — the natural lead-in to part II.

## Reference solution (Python)

```
def dll_to_array(head):
    out = []
    cur = head
    while cur:
        out.append(cur.val)
        cur = cur.next
    return out
```

## Test cases

| Input | Expected |
| --- | --- |
| `1<->2<->3<->4` | `[1,2,3,4]` |
| `empty list` | `[]` |
| `single node 9` | `[9]` |
| `5<->5` | `[5,5]` |

[PreviousConsistent Hashing (Data Partitioning)](/problems/consistent-hashing)[NextCount Binary Substrings](/problems/count-binary-substrings)

Saved in this browser. No account needed.

## Asked at

6 companies

* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#10 in list](/companies/jpmorgan-chase)
* [![](/logos/goldman-sachs.png)Goldman Sachs#16 in list](/companies/goldman-sachs)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#36 in list](/companies/palo-alto-networks)
* [![](/logos/swiggy.png)Swiggy#113 in list](/companies/swiggy)
* [![](/logos/apple.ico)Apple#329 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#540 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   19/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)[Linked List](/topics?open=linked-list#linked-list)

[Solution](https://www.youtube.com/results?search_query=Convert%20Doubly%20Linked%20List%20to%20Array%20I%20dsa)

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
