# Left Rotate Array by One · FAANGrind

Source: https://faangrind.vercel.app/problems/left-rotate-array-by-one

[All problems](/problems)

#835Easy· asked at 6 companies

# Left Rotate Array by One

[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/swiggy.png)Swiggy](/companies/swiggy)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

Given an integer array `arr` of size `n`, rotate it **left by one position** in place: the first element moves to the end and every other element shifts one index to the left.

## Input / Output

* **Input:** integer array `arr`.
* **Output:** the rotated array.

## Examples

**Example 1**
Input: `arr = [1, 2, 3, 4, 5]`
Output: `[2, 3, 4, 5, 1]`

**Example 2**
Input: `arr = [7]`
Output: `[7]`

**Example 3**
Input: `arr = [4, 9]`
Output: `[9, 4]`

## Constraints

* `1 <= n <= 10^5`

## Approach

1. Save `first = arr[0]`.
2. For `i` from 1 to `n-1`, set `arr[i-1] = arr[i]`.
3. Set `arr[n-1] = first`.

Each element is moved exactly once, so the cost is linear with constant extra memory. Building a new array `arr[1:] + arr[:1]` is simpler but uses O(n) additional space, which the interviewer will point out.

This problem is the warm-up for **rotate by k**, which generalises the idea: either repeat the single rotation `k` times (O(n·k), bad), or use the three-reversal trick (reverse the first `k`, reverse the rest, reverse everything) for O(n) time and O(1) space.

## Complexity

* **Time:** O(n)
* **Space:** O(1)

## Reference solution (Python)

```
def left_rotate_by_one(arr):
    if len(arr) <= 1:
        return arr
    first = arr[0]
    for i in range(1, len(arr)):
        arr[i - 1] = arr[i]
    arr[-1] = first
    return arr
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,2,3,4,5]` | `[2,3,4,5,1]` |
| `[7]` | `[7]` |
| `[4,9]` | `[9,4]` |
| `[1,1,2]` | `[1,2,1]` |

[PreviousLargest Element](/problems/largest-element)[NextLeftmost Column with at Least a One](/problems/leftmost-column-with-at-least-a-one)

Saved in this browser. No account needed.

## Asked at

6 companies

* [![](/logos/adobe.ico)Adobe#68 in list](/companies/adobe)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#82 in list](/companies/walmart-global-tech)
* [![](/logos/american-express.png)American Express#116 in list](/companies/american-express)
* [![](/logos/swiggy.png)Swiggy#157 in list](/companies/swiggy)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#167 in list](/companies/jpmorgan-chase)
* [![](/logos/goldman-sachs.png)Goldman Sachs#266 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Easy

Popularity
:   21/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)

[Solution](https://www.youtube.com/results?search_query=Left%20Rotate%20Array%20by%20One%20dsa)

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
