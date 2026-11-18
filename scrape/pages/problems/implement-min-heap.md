# Implement Min Heap · FAANGrind

Source: https://faangrind.vercel.app/problems/implement-min-heap

[All problems](/problems)

#723Medium· asked at 11 companies

# Implement Min Heap

[![](/logos/salesforce.ico)Salesforce](/companies/salesforce)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/swiggy.png)Swiggy](/companies/swiggy)[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)+5 more

## Problem

Design a **min-heap** data structure from scratch (without using a library priority queue) that supports the following operations:

* `insert(x)` — add an integer.
* `getMin()` — return the smallest element without removing it.
* `extractMin()` — remove and return the smallest element.
* `deleteAt(i)` / `decreaseKey(i, newVal)` — optional extensions.
* `isEmpty()`, `size()`.

All operations except `getMin` must run in O(log n).

## Input / Output

A sequence of operations; return the results of `getMin` and `extractMin` calls in order. Return `-1` (or raise) when the heap is empty.

## Examples

Operations: `insert(5)`, `insert(3)`, `insert(8)`, `getMin()`, `extractMin()`, `getMin()`
Output: `3, 3, 5`

## Constraints

* Up to `10^5` operations.
* Values fit in 32-bit signed integers.

## Approach

Store the heap in a dynamic array. For index `i`: parent is `(i-1)/2`, children are `2i+1` and `2i+2`. The invariant is `arr[parent] <= arr[child]` for every edge.

**insert(x)** — append `x` at the end, then **sift up**: while `x` is smaller than its parent, swap them. Height is `log n`, so at most `log n` swaps.

**getMin()** — return `arr[0]`.

**extractMin()** — save `arr[0]`, move the last element to index 0, shrink the array, then **sift down** from index 0: repeatedly swap with the smaller child while a child is smaller.

**decreaseKey(i, v)** — set `arr[i] = v` and sift up.

**deleteAt(i)** — `decreaseKey(i, -inf)` then `extractMin()`.

Handle the empty heap explicitly in `getMin` and `extractMin`.

## Complexity

* `insert`, `extractMin`, , : O(log n)

[PreviousDesign Tic-Tac-Toe](/problems/design-tic-tac-toe)[NextLongest String Chain](/problems/longest-string-chain)

Saved in this browser. No account needed.

## Asked at

11 companies

* [![](/logos/salesforce.ico)Salesforce#20 in list](/companies/salesforce)
* [![](/logos/apple.ico)Apple#68 in list](/companies/apple)
* [![](/logos/swiggy.png)Swiggy#84 in list](/companies/swiggy)
* [![](/logos/atlassian.ico)Atlassian#85 in list](/companies/atlassian)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#98 in list](/companies/jpmorgan-chase)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#104 in list](/companies/walmart-global-tech)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#118 in list](/companies/palo-alto-networks)
* [![](/logos/paypal.png)PayPal#126 in list](/companies/paypal)
* [![](/logos/adobe.ico)Adobe#150 in list](/companies/adobe)
* [![](/logos/goldman-sachs.png)Goldman Sachs#220 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#478 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   29/100

Source
:   Full statement on FAANGrind

Topics
:   [Heaps](/topics?open=heaps#heaps)

[Solution](https://www.youtube.com/results?search_query=Implement%20Min%20Heap%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
* [#1134Merge K sorted ListsMedium](/problems/merge-k-sorted-lists)
* [#534Find Median from Data StreamMedium](/problems/find-median-from-data-stream)
* [#785K-th Largest element in an arrayMedium](/problems/k-th-largest-element-in-an-array)
* [#1870Task SchedulerMedium](/problems/task-scheduler)
* [#1771Sort Characters by FrequencyMedium](/problems/sort-characters-by-frequency)

`decreaseKey`

`deleteAt`

- `getMin`: O(1)

- Space: O(n)

## Interview discussion points
