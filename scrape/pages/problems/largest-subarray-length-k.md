# Largest Subarray Length K · FAANGrind

Source: https://faangrind.vercel.app/problems/largest-subarray-length-k

[All problems](/problems)

#820Medium· asked at 1 company

# Largest Subarray Length K

[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)

## Problem

Given an integer array `arr` of **distinct** integers and an integer `k`, return the **largest subarray of length `k`**, where "largest" means lexicographically greatest: comparing two subarrays element by element from the left, the one with the larger element at the first differing position is larger.

## Input / Output

* **Input:** integer array `arr` (distinct values), integer `k`.
* **Output:** the subarray (list of `k` integers).

## Examples

**Example 1**
Input: `arr = [1, 4, 5, 2, 3]`, `k = 3`
Output: `[5, 2, 3]`
Explanation: Candidates: `[1,4,5]`, `[4,5,2]`, `[5,2,3]`. The one starting with 5 wins.

**Example 2**
Input: `arr = [1, 4, 5, 2, 3]`, `k = 4`
Output: `[4, 5, 2, 3]`

**Example 3**
Input: `arr = [1, 4, 5, 2, 3]`, `k = 1`
Output: `[5]`

## Constraints

* `1 <= k <= n <= 10^5`
* All elements are distinct.

## Approach

Because the elements are **distinct**, two different windows always differ at their first element (their starting values are different). So the lexicographically largest window is simply the one whose **first element is the largest** among all valid starting positions `0 .. n-k`.

1. Scan indices `0..n-k`, track the index `best` with the maximum `arr[i]`.
2. Return `arr[best : best+k]`.

That is a single pass, O(n) time and O(1) extra space — the whole trick is noticing that distinctness collapses the comparison to the first element.

**Without distinctness** the problem becomes harder: ties on the first element must be broken by later elements. A direct approach compares windows in O(k) each for O(n·k); using suffix-array ranks or a Z-function on the reversed comparison gets O(n log n), but that is beyond the usual interview scope.

## Complexity

* **Time:** O(n)
* **Space:** O(1) plus the output.

## Reference solution (Python)

```
def largest_subarray_length_k(arr, k):
    n = len(arr)
    best = 0
    for i in range(1, n - k + 1):
        if arr[i] > arr[best]:
            best = i
    return arr[best:best + k]
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,4,5,2,3], k=3` | `[5,2,3]` |
| `[1,4,5,2,3], k=4` | `[4,5,2,3]` |
| `[1,4,5,2,3], k=1` | `[5]` |
| `[9,1,2], k=3` | `[9,1,2]` |

[PreviousK Empty Slots](/problems/k-empty-slots)[NextLargest Subarray with Sum 0](/problems/largest-subarray-with-sum-0)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#172 in list](/companies/jpmorgan-chase)

## Details

Difficulty
:   Medium

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Greedy Algorithms](/topics?open=greedy-algorithms#greedy-algorithms)

[Solution](https://www.youtube.com/results?search_query=Largest%20Subarray%20Length%20K%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1132Merge IntervalsMedium](/problems/merge-intervals)
* [#1957Valid Paranthesis CheckerMedium](/problems/valid-paranthesis-checker)
* [#228Container With Most WaterMedium](/problems/container-with-most-water)
* [#1126Meeting Rooms IIMedium](/problems/meeting-rooms-ii)
* [#771Jump Game - IMedium](/problems/jump-game-i)
* [#135CandyMedium](/problems/candy)
