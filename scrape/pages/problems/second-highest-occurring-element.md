# Second Highest Occurring Element · FAANGrind

Source: https://faangrind.vercel.app/problems/second-highest-occurring-element

[All problems](/problems)

#1695Easy· asked at 1 company

# Second Highest Occurring Element

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given an integer array `arr`, return the element with the **second highest frequency**. If several elements share that frequency, return the **smallest** of them. If no element has a second-distinct frequency (for example every element occurs equally often, or the array has a single distinct value), return `-1`.

## Input / Output

* **Input:** integer array `arr` of length `n`.
* **Output:** integer.

## Examples

**Example 1**
Input: `arr = [1, 2, 2, 3, 3, 3, 4]`
Output: `2`
Explanation: Frequencies — 3:3, 2:2, 1:1, 4:1. Highest is 3 (element 3); second highest is 2 (element 2).

**Example 2**
Input: `arr = [5, 5, 6, 6, 7, 7, 7, 8]`
Output: `5`
Explanation: Second-highest frequency is 2, shared by 5 and 6 → smallest is 5.

**Example 3**
Input: `arr = [4, 4, 4]`
Output: `-1`

## Constraints

* `1 <= n <= 10^5`

## Approach

1. Count frequencies with a hash map: O(n).
2. Find the maximum frequency `f1`.
3. Among elements whose frequency is **strictly less** than `f1`, find the maximum frequency `f2`. If none exists, return `-1`.
4. Return the smallest element with frequency `f2`.

Steps 2–4 are single passes over the map, so no sorting is needed. Sorting the map entries by `(-frequency, value)` and picking the first entry whose frequency differs from the top one is a valid alternative at O(k log k).

Be careful with the definition: "second highest **frequency**" is a frequency value, not the second entry in a sorted list — two elements tied at the top do not make one of them the second-highest.

## Complexity

* **Time:** O(n)
* **Space:** O(k) distinct elements.

## Reference solution (Python)

```
from collections import Counter

def second_highest_occurring(arr):
    freq = Counter(arr)
    f1 = max(freq.values())
    lower = [f for f in freq.values() if f < f1]
    if not lower:
        return -1
    f2 = max(lower)
    return min(v for v, f in freq.items() if f == f2)
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,2,2,3,3,3,4]` | `2` |
| `[5,5,6,6,7,7,7,8]` | `5` |
| `[4,4,4]` | `-1` |
| `[1,2]` | `-1` |

[PreviousReverse an array](/problems/reverse-an-array)[NextSecond Largest Element](/problems/second-largest-element)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#69 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   17/100

Source
:   Full statement on FAANGrind

Topics
:   [Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Second%20Highest%20Occurring%20Element%20dsa)

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
