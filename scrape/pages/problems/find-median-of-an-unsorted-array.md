# Find Median of an Unsorted Array · FAANGrind

Source: https://faangrind.vercel.app/problems/find-median-of-an-unsorted-array

[All problems](/problems)

#535Medium· asked at 1 company

# Find Median of an Unsorted Array

[![](/logos/apple.ico)Apple](/companies/apple)

## Problem

Given an unsorted array `arr` of `n` integers, return its **median**. If `n` is odd, the median is the middle element of the sorted order. If `n` is even, return the **floor of the average** of the two middle elements (some versions ask for the lower-middle element instead — the approach is identical).

## Input / Output

* **Input:** integer array `arr`.
* **Output:** the median as an integer.

## Examples

**Example 1**
Input: `arr = [3, 1, 4, 1, 5]`
Output: `3`
Explanation: Sorted → `[1, 1, 3, 4, 5]`; middle is 3.

**Example 2**
Input: `arr = [7, 2, 9, 4]`
Output: `5`
Explanation: Sorted → `[2, 4, 7, 9]`; `(4 + 7) / 2 = 5` (floor).

**Example 3**
Input: `arr = [10]`
Output: `10`

## Constraints

* `1 <= n <= 10^6`
* `-10^9 <= arr[i] <= 10^9`

## Approach

**Sort — O(n log n).** Sort and index the middle. Simple and usually accepted, but the interviewer will ask for better.

**Quickselect — expected O(n).** The median is the k-th smallest element with `k = n/2`. Quickselect partitions the array around a pivot (like quicksort) but recurses into **only** the side that contains index `k`:

1. Pick a pivot (random for expected linear time).
2. Partition into `< pivot`, `== pivot`, `> pivot`.
3. If `k` falls in the left part, recurse there; if in the equal part, the pivot is the answer; otherwise recurse right with `k` reduced.
   For even `n`, run it twice (for `n/2 - 1` and `n/2`) or find the max of the left partition after locating the upper middle.

**Median of medians** gives a guaranteed O(n) but is rarely expected in an interview beyond naming it.

**Two heaps** is the right answer when elements arrive as a **stream** (see "Find Median from Data Stream"); for a static array quickselect is simpler.

## Complexity

* Sort: O(n log n) time, O(1)–O(n) space depending on the sort.
* Quickselect: O(n) expected, O(n²) worst case with bad pivots, O(1) extra space (in-place, iterative).

## Reference solution (Python)

```
import random

def kth_smallest(arr, k):            # 0-based k
    lo, hi = 0, len(arr) - 1
    while True:
        if lo == hi:
            return arr[lo]
        p = arr[random.randint(lo, hi)]
        i, l, r = lo, lo, hi
        while i <= r:                # Dutch national flag partition
            if arr[i] < p:
                arr[i], arr[l] = arr[l], arr[i]; l += 1; i += 1
            elif arr[i] > p:
                arr[i], arr[r] = arr[r], arr[i]; r -= 1
            else:
                i += 1
        if k < l:      hi = l - 1
        elif k > r:    lo = r + 1
        else:          return p

def median(arr):
    a = list(arr)
    n = len(a)
    if n % 2:
        return kth_smallest(a, n // 2)
    return (kth_smallest(a, n // 2 - 1) + kth_smallest(a, n // 2)) // 2
```

## Test cases

| Input | Expected |
| --- | --- |
| `[3,1,4,1,5]` | `3` |
| `[7,2,9,4]` | `5` |
| `[10]` | `10` |
| `[5,5,5,5]` | `5` |

[PreviousFind Critical and Pseudo-Critical Edges in Minimum Spanning Tree](/problems/find-critical-and-pseudo-critical-edges-in-minimum-spanning-tree)[NextGuess Number Higher or Lower](/problems/guess-number-higher-or-lower)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/apple.ico)Apple#325 in list](/companies/apple)

## Details

Difficulty
:   Medium

Popularity
:   10/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)

[Solution](https://www.youtube.com/results?search_query=Find%20Median%20of%20an%20Unsorted%20Array%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#788Kadane's AlgorithmMedium](/problems/kadane-s-algorithm)
* [#53 SumMedium](/problems/3-sum)
* [#1678Rotten OrangesMedium](/problems/rotten-oranges)
* [#890Longest Consecutive Sequence in an ArrayMedium](/problems/longest-consecutive-sequence-in-an-array)
* [#1350Next PermutationMedium](/problems/next-permutation)
