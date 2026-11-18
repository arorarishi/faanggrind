# Counting Frequencies of Array Elements · FAANGrind

Source: https://faangrind.vercel.app/problems/counting-frequencies-of-array-elements

[All problems](/problems)

#337Easy· asked at 4 companies

# Counting Frequencies of Array Elements

[![](/logos/amazon.ico)Amazon](/companies/amazon)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/apple.ico)Apple](/companies/apple)

## Problem

Given an integer array `arr` of length `n`, return the frequency of each **distinct** element. Output the pairs in ascending order of the element value.

## Input / Output

* **Input:** integer array `arr`.
* **Output:** list of `(value, count)` pairs sorted by value.

## Examples

**Example 1**
Input: `arr = [10, 5, 10, 15, 10, 5]`
Output: `5:2, 10:3, 15:1`

**Example 2**
Input: `arr = [1, 1, 1, 1]`
Output: `1:4`

## Constraints

* `1 <= n <= 10^5`
* `-10^9 <= arr[i] <= 10^9`

## Approach

**Hash map (general case).** Iterate the array and increment `freq[arr[i]]`. Then collect the keys, sort them, and print. O(n) to count plus O(k log k) to sort the `k` distinct keys.

**Sorting (no extra map).** Sort the array, then scan: whenever the value changes, emit the previous value and the run length. O(n log n) time, O(1) extra space if in-place sorting is allowed.

**Counting array (bounded values).** If the elements are known to lie in a small range `[0, MAX]`, use `cnt[MAX+1]` for O(n + MAX) time — the fastest approach when it applies.

**In-place trick (values 1..n).** If every element lies in `[1, n]`, you can store the counts inside the array itself: for each element `v = arr[i] % (n+1)` (original value), add `n+1` to `arr[v-1]`. Afterwards `arr[j] / (n+1)` is the frequency of `j+1`. This is O(n) time and O(1) space and is a favourite follow-up question.

## Complexity

* Hash map: O(n) average time, O(k) space.
* Sorting: O(n log n) time, O(1) extra space.

## Related

Majority element, top-K frequent elements, first repeating element, and "count distinct elements in every window" all start from this counting step.

## Reference solution (Python)

```
from collections import Counter

def element_frequencies(arr):
    c = Counter(arr)
    return sorted(c.items())

# O(1)-space variant when all values are in 1..n
def frequencies_in_place(arr):
    n = len(arr)
    for i in range(n):
        v = arr[i] % (n + 1)
        arr[v - 1] += n + 1
    return [(i + 1, arr[i] // (n + 1)) for i in range(n) if arr[i] // (n + 1)]
```

## Test cases

| Input | Expected |
| --- | --- |
| `[10,5,10,15,10,5]` | `[(5,2),(10,3),(15,1)]` |
| `[1,1,1,1]` | `[(1,4)]` |
| `[3,1,2] (in-place variant)` | `[(1,1),(2,1),(3,1)]` |
| `[2,2,1] (in-place variant)` | `[(1,1),(2,2)]` |

[PreviousCount the Number of Infection Sequences](/problems/count-the-number-of-infection-sequences)[NextDecoded String at Index](/problems/decoded-string-at-index)

Saved in this browser. No account needed.

## Asked at

4 companies

* [![](/logos/amazon.ico)Amazon#71 in list](/companies/amazon)
* [![](/logos/american-express.png)American Express#79 in list](/companies/american-express)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#189 in list](/companies/palo-alto-networks)
* [![](/logos/apple.ico)Apple#270 in list](/companies/apple)

## Details

Difficulty
:   Easy

Popularity
:   18/100

Source
:   Full statement on FAANGrind

Topics
:   [Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Counting%20Frequencies%20of%20Array%20Elements%20dsa)

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
