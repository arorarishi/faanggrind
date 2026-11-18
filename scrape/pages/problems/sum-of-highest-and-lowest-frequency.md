# Sum of Highest and Lowest Frequency · FAANGrind

Source: https://faangrind.vercel.app/problems/sum-of-highest-and-lowest-frequency

[All problems](/problems)

#1844Easy· asked at 1 company

# Sum of Highest and Lowest Frequency

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given an integer array `arr`, compute the frequency of every distinct element, then return the **sum of the highest frequency and the lowest frequency**.

## Input / Output

* **Input:** integer array `arr`.
* **Output:** integer.

## Examples

**Example 1**
Input: `arr = [1, 2, 2, 3, 3, 3]`
Output: `4`
Explanation: Frequencies are 1, 2, 3. Highest 3 + lowest 1 = 4.

**Example 2**
Input: `arr = [7, 7, 7]`
Output: `6`
Explanation: Only one distinct element with frequency 3; highest and lowest are both 3.

**Example 3**
Input: `arr = [1, 2, 3, 4]`
Output: `2`

## Constraints

* `1 <= n <= 10^5`

## Approach

1. Build a frequency map in one pass.
2. Scan the map's values once, tracking the maximum and the minimum.
3. Return `max + min`.

The problem is deliberately simple; what interviewers check is that you don't sort the whole array (O(n log n)) when a hash map gives O(n), and that you handle the single-distinct-value case where max and min coincide.

If elements are bounded (e.g. `0 <= arr[i] <= 10^5`) a counting array replaces the hash map and avoids hashing overhead entirely.

## Complexity

* **Time:** O(n)
* **Space:** O(k) for `k` distinct values.

## Reference solution (Python)

```
from collections import Counter

def sum_high_low_freq(arr):
    freq = Counter(arr).values()
    return max(freq) + min(freq)
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,2,2,3,3,3]` | `4` |
| `[7,7,7]` | `6` |
| `[1,2,3,4]` | `2` |
| `[5,5,9]` | `3` |

[PreviousSubstrings of Size Three with Distinct Characters](/problems/substrings-of-size-three-with-distinct-characters)[NextSum of Two Integers](/problems/sum-of-two-integers)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#160 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   17/100

Source
:   Full statement on FAANGrind

Topics
:   [Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Sum%20of%20Highest%20and%20Lowest%20Frequency%20dsa)

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
