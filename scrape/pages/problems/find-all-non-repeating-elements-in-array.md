# Find All Non-Repeating Elements in Array · FAANGrind

Source: https://faangrind.vercel.app/problems/find-all-non-repeating-elements-in-array

[All problems](/problems)

#502Easy· asked at 1 company

# Find All Non-Repeating Elements in Array

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given an integer array `arr`, return every element that appears **exactly once**, in the order of its first appearance in the array.

## Input / Output

* **Input:** integer array `arr`.
* **Output:** list of integers (may be empty).

## Examples

**Example 1**
Input: `arr = [4, 3, 2, 4, 1, 3, 5]`
Output: `[2, 1, 5]`

**Example 2**
Input: `arr = [1, 1, 2, 2]`
Output: `[]`

**Example 3**
Input: `arr = [9]`
Output: `[9]`

## Constraints

* `1 <= n <= 10^5`

## Approach

Two passes with a hash map:

1. Count occurrences of each element.
2. Walk the array again and emit elements whose count is 1. Walking the original array (rather than the map) preserves input order.

**Why not XOR?** XOR-ing all elements cancels pairs and finds a *single* unique element when every other value appears exactly twice; it cannot list several unique elements or handle values that appear three times. Mention it as a related trick, not as the solution.

**Order-preserving with one structure:** an insertion-ordered map (Python `dict`, Java `LinkedHashMap`) lets you iterate the map itself in first-appearance order.

## Complexity

* **Time:** O(n)
* **Space:** O(k)

## Reference solution (Python)

```
from collections import Counter

def non_repeating(arr):
    freq = Counter(arr)
    return [v for v in arr if freq[v] == 1]
```

## Test cases

| Input | Expected |
| --- | --- |
| `[4,3,2,4,1,3,5]` | `[2,1,5]` |
| `[1,1,2,2]` | `[]` |
| `[9]` | `[9]` |
| `[2,2,2,3]` | `[3]` |

[PreviousExpressive Words](/problems/expressive-words)[NextFind All Possible Stable Binary Arrays II](/problems/find-all-possible-stable-binary-arrays-ii)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#131 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   17/100

Source
:   Full statement on FAANGrind

Topics
:   [Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Find%20All%20Non-Repeating%20Elements%20in%20Array%20dsa)

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
