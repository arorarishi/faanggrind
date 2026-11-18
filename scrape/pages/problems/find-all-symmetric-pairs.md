# Find All Symmetric Pairs · FAANGrind

Source: https://faangrind.vercel.app/problems/find-all-symmetric-pairs

[All problems](/problems)

#508Easy· asked at 4 companies

# Find All Symmetric Pairs

[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/linkedin.ico)LinkedIn](/companies/linkedin)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)

## Problem

You are given an array of `n` pairs of integers, `pairs[i] = [a, b]`. Two pairs `[a, b]` and `[c, d]` are **symmetric** if `a == d` and `b == c`. Return all symmetric pairs found in the array. Each symmetric relationship should be reported once, as the pair that appears **first** in the input. The first elements of all pairs are distinct.

## Input / Output

* **Input:** 2-D array `pairs` of shape `n × 2`.
* **Output:** list of pairs `[a, b]` such that `[b, a]` also exists later in the array.

## Examples

**Example 1**
Input: `pairs = [[11, 20], [30, 40], [5, 10], [40, 30], [10, 5]]`
Output: `[[30, 40], [5, 10]]`
Explanation: `[30,40]` is symmetric with `[40,30]`; `[5,10]` with `[10,5]`.

**Example 2**
Input: `pairs = [[1, 2], [3, 4]]`
Output: `[]`

**Example 3**
Input: `pairs = [[2, 2]]`
Output: `[[2, 2]]` — a pair is symmetric with itself when `a == b` (some versions exclude this; state your assumption).

## Constraints

* `1 <= n <= 10^5`
* `-10^9 <= a, b <= 10^9`
* All first elements are distinct.

## Approach

The naive O(n²) scan compares every pair with every other. Because first elements are unique, a **hash map from first element to second element** lets us test symmetry in O(1):

1. Iterate through the pairs in order.
2. For the current pair `[a, b]`, check whether the map contains key `b` **and** `map[b] == a`. If so, `[b, a]` appeared earlier, so report the earlier pair `[b, a]` (or the current one — follow the required convention).
3. Insert `map[a] = b`.

Checking before inserting guarantees each symmetric relationship is reported exactly once, and reporting on the second sighting preserves input order when the earlier pair is emitted.

If first elements are not distinct, store a set of second elements per key instead of a single value.

## Complexity

* **Time:** O(n) average.
* **Space:** O(n) for the map.

## Reference solution (Python)

```
def symmetric_pairs(pairs):
    seen = {}
    out = []
    for a, b in pairs:
        if b in seen and seen[b] == a:
            out.append([b, a])
        seen[a] = b
    return out
```

## Test cases

| Input | Expected |
| --- | --- |
| `[[11,20],[30,40],[5,10],[40,30],[10,5]]` | `[[30,40],[5,10]]` |
| `[[1,2],[3,4]]` | `[]` |
| `[[1,2],[2,1],[3,1]]` | `[[1,2]]` |
| `[[7,7]]` | `[]` (self-pair not counted in this implementation) |

[PreviousFind All Employees Reporting to the Head of the Company](/problems/find-all-employees-reporting-to-the-head-of-the-company)[NextFind Continuous Ranges in Logs](/problems/find-continuous-ranges-in-logs)

Saved in this browser. No account needed.

## Asked at

4 companies

* [![](/logos/american-express.png)American Express#18 in list](/companies/american-express)
* [![](/logos/linkedin.ico)LinkedIn#36 in list](/companies/linkedin)
* [![](/logos/apple.ico)Apple#75 in list](/companies/apple)
* [![](/logos/atlassian.ico)Atlassian#139 in list](/companies/atlassian)

## Details

Difficulty
:   Easy

Popularity
:   19/100

Source
:   Full statement on FAANGrind

Topics
:   [Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Find%20All%20Symmetric%20Pairs%20dsa)

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
