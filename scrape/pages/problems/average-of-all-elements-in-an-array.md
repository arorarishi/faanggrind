# Average of All Elements in an Array · FAANGrind

Source: https://faangrind.vercel.app/problems/average-of-all-elements-in-an-array

[All problems](/problems)

#59Easy· asked at 1 company

# Average of All Elements in an Array

[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)

## Problem

Given an integer array `arr` of size `n`, return the **average** (arithmetic mean) of its elements. Return the result as a floating-point number rounded to two decimal places, or as an integer floor if the problem demands integer output. Handle the empty array by returning `0`.

## Input / Output

* **Input:** integer array `arr`.
* **Output:** the mean.

## Examples

| arr | Output |
| --- | --- |
| `[1, 2, 3, 4, 5]` | `3.0` |
| `[10, 20]` | `15.0` |
| `[7]` | `7.0` |
| `[-3, 3]` | `0.0` |
| `[]` | `0` |

## Constraints

* `0 <= n <= 10^6`
* `-10^9 <= arr[i] <= 10^9`

## Approach

Sum all elements and divide by `n`. The interesting parts are the edge cases the interviewer is really asking about:

* **Overflow.** With `n = 10^6` and values up to `10^9`, the sum reaches `10^15`, which overflows a 32-bit integer. Use 64-bit (`long`) or accumulate in floating point.
* **Integer vs. floating division.** In C, C++ and Java, `sum / n` with both operands integers truncates. Cast one operand to `double` first.
* **Empty input.** Division by zero — return 0 or raise, but decide explicitly.
* **Streaming / running average.** If values arrive one at a time, keep `count` and `mean` and update with `mean += (x - mean) / count` — this avoids storing the sum and is numerically stabler for very long streams (Welford's method).
* **Sliding-window average** (average of the last `k` elements) is the natural follow-up and uses a circular buffer plus a running sum.

## Complexity

* **Time:** O(n)
* **Space:** O(1)

## Reference solution (Python)

```
def average(arr):
    if not arr:
        return 0
    return round(sum(arr) / len(arr), 2)

def running_mean(stream):
    mean, count = 0.0, 0
    for x in stream:
        count += 1
        mean += (x - mean) / count
    return mean
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,2,3,4,5]` | `3.0` |
| `[10,20]` | `15.0` |
| `[]` | `0` |
| `running_mean([2,4,6])` | `4.0` |

[PreviousWord Abbreviation](/problems/word-abbreviation)[NextBest Time to Buy and Sell Stock using Strategy](/problems/best-time-to-buy-and-sell-stock-using-strategy)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#25 in list](/companies/jpmorgan-chase)

## Details

Difficulty
:   Easy

Popularity
:   17/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)

[Solution](https://www.youtube.com/results?search_query=Average%20of%20All%20Elements%20in%20an%20Array%20dsa)

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
