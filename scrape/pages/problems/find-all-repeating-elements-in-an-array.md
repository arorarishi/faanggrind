# Find All Repeating Elements in an Array · FAANGrind

Source: https://faangrind.vercel.app/problems/find-all-repeating-elements-in-an-array

[All problems](/problems)

#507Easy· asked at 1 company

# Find All Repeating Elements in an Array

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given an integer array `arr`, return every element that appears **more than once**, listed once each, in the order of its first appearance.

## Input / Output

* **Input:** integer array `arr`.
* **Output:** list of integers (may be empty).

## Examples

**Example 1**
Input: `arr = [4, 3, 2, 4, 1, 3, 5, 4]`
Output: `[4, 3]`

**Example 2**
Input: `arr = [1, 2, 3]`
Output: `[]`

**Example 3**
Input: `arr = [2, 2, 2]`
Output: `[2]`

## Constraints

* `1 <= n <= 10^5`

## Approach

**Hash map, two passes.** Count frequencies, then walk the array and output an element the first time you meet it if its count is greater than 1 (track a `reported` set so each repeated value is printed once).

**Single pass with a seen-set.** Maintain `seen` and `reported`. For each `v`: if `v` in `seen` and not in `reported`, output it and add to `reported`; otherwise add to `seen`. Output order is the order of the *second* occurrence — acceptable when the problem only asks for the set.

**O(1) space when values are in `1..n`.** Use the sign trick: for each value `v`, look at index `|v|-1`; if `arr[|v|-1]` is already negative, `v` is a repeat, else negate it. This modifies the array in place and is a common follow-up.

## Complexity

* **Time:** O(n)
* **Space:** O(k), or O(1) with the in-place trick.

## Reference solution (Python)

```
from collections import Counter

def repeating(arr):
    freq = Counter(arr)
    out, done = [], set()
    for v in arr:
        if freq[v] > 1 and v not in done:
            out.append(v)
            done.add(v)
    return out
```

## Test cases

| Input | Expected |
| --- | --- |
| `[4,3,2,4,1,3,5,4]` | `[4,3]` |
| `[1,2,3]` | `[]` |
| `[2,2,2]` | `[2]` |
| `[1,2,1,2]` | `[1,2]` |

[PreviousFinal Prices With a Special Discount in a Shop](/problems/final-prices-with-a-special-discount-in-a-shop)[NextFind Pairs with Given Sum in Doubly Linked List](/problems/find-pairs-with-given-sum-in-doubly-linked-list)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#37 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Find%20All%20Repeating%20Elements%20in%20an%20Array%20dsa)

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
