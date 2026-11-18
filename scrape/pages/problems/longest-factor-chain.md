# Longest Factor Chain · FAANGrind

Source: https://faangrind.vercel.app/problems/longest-factor-chain

[All problems](/problems)

#895Medium· asked at 2 companies

# Longest Factor Chain

[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)

## Problem

Given an array of distinct positive integers `nums`, find the length of the **longest chain** `a₁, a₂, …, a_k` of elements from `nums` such that each element is a **factor** of the next: `a₁ | a₂`, `a₂ | a₃`, …, `a_{k-1} | a_k`. Chain elements need not be adjacent in the array. Return the length (a variant asks for the chain itself).

## Input / Output

* **Input:** integer array `nums`.
* **Output:** integer — length of the longest divisibility chain.

## Examples

**Example 1**
Input: `nums = [1, 2, 4, 8, 3]`
Output: `4`
Explanation: `1 → 2 → 4 → 8`.

**Example 2**
Input: `nums = [3, 5, 7]`
Output: `1`
Explanation: No element divides another; any single element is a chain of length 1.

**Example 3**
Input: `nums = [2, 3, 6, 12, 18]`
Output: `3`
Explanation: `2 → 6 → 12`, `3 → 6 → 12` or `3 → 6 → 18`.

## Constraints

* `1 <= n <= 10^3`
* `1 <= nums[i] <= 2 · 10^9`, all distinct.

## Approach

Divisibility is transitive: if `a | b` and `b | c` then `a | c`. So after **sorting** ascending, a valid chain is simply an increasing subsequence in which consecutive elements divide — the same shape as Longest Increasing Subsequence, but with the comparison `nums[j] % nums[i] == 0` instead of `nums[j] > nums[i]`.

1. Sort `nums`.
2. `dp[i]` = length of the longest chain **ending** at `nums[i]`; initialise all to 1.
3. For each `i`, for every `j < i` with `nums[i] % nums[j] == 0`, set `dp[i] = max(dp[i], dp[j] + 1)`.
4. The answer is `max(dp)`.

To recover the chain, store `prev[i]` = the `j` that gave the best `dp[i]` and walk back from the argmax.

This is exactly "Largest Divisible Subset" (LeetCode 368) — in a divisible subset every pair divides, and after sorting that is the same as a chain.

## Complexity

* **Time:** O(n²)
* **Space:** O(n)

## Reference solution (Python)

```
def longest_factor_chain(nums):
    a = sorted(nums)
    n = len(a)
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if a[i] % a[j] == 0 and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    best = max(range(n), key=lambda i: dp[i])
    chain, i = [], best
    while i != -1:
        chain.append(a[i])
        i = prev[i]
    return dp[best], chain[::-1]
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,2,4,8,3]` | `4, [1,2,4,8]` |
| `[3,5,7]` | `1` |
| `[2,3,6,12,18]` | `3` |
| `[10]` | `1, [10]` |

[PreviousLongest Duplicate Substring](/problems/longest-duplicate-substring)[NextMake Lexicographically Smallest Array by Swapping Elements](/problems/make-lexicographically-smallest-array-by-swapping-elements)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/paypal.png)PayPal#6 in list](/companies/paypal)
* [![](/logos/atlassian.ico)Atlassian#11 in list](/companies/atlassian)

## Details

Difficulty
:   Medium

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Dynamic Programming](/topics?open=dynamic-programming#dynamic-programming)

[Solution](https://www.youtube.com/results?search_query=Longest%20Factor%20Chain%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#75Best time to buy and sell stockMedium](/problems/best-time-to-buy-and-sell-stock)
* [#909Longest Palindromic SubstringMedium](/problems/longest-palindromic-substring)
* [#714House robberMedium](/problems/house-robber)
* [#899Longest Increasing SubsequenceMedium](/problems/longest-increasing-subsequence)
* [#458Edit distanceMedium](/problems/edit-distance)
* [#184Climbing stairsMedium](/problems/climbing-stairs)
