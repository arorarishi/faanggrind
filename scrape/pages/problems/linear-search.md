# Linear Search · FAANGrind

Source: https://faangrind.vercel.app/problems/linear-search

[All problems](/problems)

#857Easy· asked at 5 companies

# Linear Search

[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/swiggy.png)Swiggy](/companies/swiggy)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

Given an integer array `arr` of size `n` and a target value `x`, return the **index of the first occurrence** of `x` in `arr`. If `x` is not present, return `-1`. The array is **not** sorted, so binary search does not apply.

## Input / Output

* **Input:** array `arr`, integer `x`.
* **Output:** index (0-based) or `-1`.

## Examples

**Example 1**
Input: `arr = [4, 2, 7, 2, 9]`, `x = 2`
Output: `1`

**Example 2**
Input: `arr = [4, 2, 7]`, `x = 5`
Output: `-1`

**Example 3**
Input: `arr = [1]`, `x = 1`
Output: `0`

## Constraints

* `1 <= n <= 10^5`

## Approach

Scan the array from left to right and return the first index whose value equals `x`. There is no shortcut when the data is unsorted: any algorithm must, in the worst case, inspect every element, so O(n) is optimal.

Discussion points the interviewer may steer towards:

* **Sentinel search:** temporarily place `x` at `arr[n-1]` so the loop needs no bounds check, then restore it — a micro-optimisation from older textbooks.
* **Multiple queries:** if the same array is searched many times, preprocess it — sort (O(n log n)) then binary search each query in O(log n), or build a hash map from value to first index for O(1) lookups.
* **Return all occurrences** or the **last** occurrence (scan from the right).

## Complexity

* **Time:** O(n) worst case, O(1) best case.
* **Space:** O(1)

## Reference solution (Python)

```
def linear_search(arr, x):
    for i, v in enumerate(arr):
        if v == x:
            return i
    return -1
```

## Test cases

| Input | Expected |
| --- | --- |
| `[4,2,7,2,9], x=2` | `1` |
| `[4,2,7], x=5` | `-1` |
| `[1], x=1` | `0` |
| `[3,3,3], x=3` | `0` |

[PreviousLemonade Change](/problems/lemonade-change)[NextLive Video Streaming (Twitch / Hotstar live match)](/problems/live-streaming-platform)

Saved in this browser. No account needed.

## Asked at

5 companies

* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#60 in list](/companies/walmart-global-tech)
* [![](/logos/american-express.png)American Express#100 in list](/companies/american-express)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#106 in list](/companies/jpmorgan-chase)
* [![](/logos/swiggy.png)Swiggy#117 in list](/companies/swiggy)
* [![](/logos/goldman-sachs.png)Goldman Sachs#198 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Easy

Popularity
:   20/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)

[Solution](https://www.youtube.com/results?search_query=Linear%20Search%20dsa)

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
