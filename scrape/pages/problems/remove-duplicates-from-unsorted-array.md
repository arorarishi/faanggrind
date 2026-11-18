# Remove Duplicates from Unsorted Array · FAANGrind

Source: https://faangrind.vercel.app/problems/remove-duplicates-from-unsorted-array

[All problems](/problems)

#1610Medium· asked at 4 companies

# Remove Duplicates from Unsorted Array

[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/swiggy.png)Swiggy](/companies/swiggy)[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)

## Problem

Given an **unsorted** integer array `arr`, remove every duplicate so that each value appears once, **keeping the order of first appearance**. Return the resulting array (or, in the in-place variant, the number of unique elements after packing them at the front).

Unlike the sorted version, duplicates are not adjacent, so the two-pointer scan alone is not enough.

## Input / Output

* **Input:** integer array `arr`.
* **Output:** array of unique values in first-appearance order.

## Examples

**Example 1**
Input: `arr = [4, 2, 4, 1, 2, 3, 4]`
Output: `[4, 2, 1, 3]`

**Example 2**
Input: `arr = [1, 1, 1]`
Output: `[1]`

**Example 3**
Input: `arr = []`
Output: `[]`

## Constraints

* `0 <= n <= 10^5`
* `-10^9 <= arr[i] <= 10^9`

## Approach

**Hash set + write pointer (O(n)).** Scan left to right with a `seen` set. Keep a write index `w`; when a value is not in `seen`, add it, copy it to `arr[w]`, and increment `w`. The prefix `arr[0..w-1]` is the answer, and the relative order is preserved because each value is written the first time it is met.

**Sorting (O(n log n), O(1) extra).** Sort, then apply the sorted-array dedupe. This loses the original order — acceptable only if the problem does not require it.

**Why not nested loops?** Comparing each element against every earlier one is O(n²), too slow at 10^5.

The hash-set approach is the one interviewers expect; the follow-up is usually "what if memory is tight?" (answer: sort in place, or a bitset if values are bounded).

## Complexity

* **Time:** O(n) average
* **Space:** O(k) for the set of distinct values.

## Reference solution (Python)

```
def remove_duplicates_unsorted(arr):
    seen = set()
    w = 0
    for v in arr:
        if v not in seen:
            seen.add(v)
            arr[w] = v
            w += 1
    del arr[w:]
    return arr
```

## Test cases

| Input | Expected |
| --- | --- |
| `[4,2,4,1,2,3,4]` | `[4,2,1,3]` |
| `[1,1,1]` | `[1]` |
| `[]` | `[]` |
| `[3,1,2]` | `[3,1,2]` |

[PreviousRemove Duplicates From an Unsorted Linked List](/problems/remove-duplicates-from-an-unsorted-linked-list)[NextRemove Max Number of Edges to Keep Graph Fully Traversable](/problems/remove-max-number-of-edges-to-keep-graph-fully-traversable)

Saved in this browser. No account needed.

## Asked at

4 companies

* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#53 in list](/companies/jpmorgan-chase)
* [![](/logos/swiggy.png)Swiggy#103 in list](/companies/swiggy)
* [![](/logos/paypal.png)PayPal#153 in list](/companies/paypal)
* [![](/logos/atlassian.ico)Atlassian#167 in list](/companies/atlassian)

## Details

Difficulty
:   Medium

Popularity
:   19/100

Source
:   Full statement on FAANGrind

Topics
:   [Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Remove%20Duplicates%20from%20Unsorted%20Array%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#934LRU CacheMedium](/problems/lru-cache)
* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
* [#890Longest Consecutive Sequence in an ArrayMedium](/problems/longest-consecutive-sequence-in-an-array)
* [#303Count subarrays with given sumMedium](/problems/count-subarrays-with-given-sum)
* [#854LFU CacheHard](/problems/lfu-cache)
