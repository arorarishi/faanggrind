# Maximum Nested Boxes · FAANGrind

Source: https://faangrind.vercel.app/problems/maximum-nested-boxes

[All problems](/problems)

#1025Medium· asked at 1 company

# Maximum Nested Boxes

[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)

## Problem

You are given `n` boxes, each described by its dimensions `[w, h, d]`. Box `A` can be **nested inside** box `B` if `A` is strictly smaller in **every** dimension (`wA < wB`, `hA < hB`, `dA < dB`). Boxes cannot be rotated. Return the maximum number of boxes that can be nested one inside another, forming a chain.

(The 2-D version is "Russian Doll Envelopes"; the rotatable-boxes version is "Box Stacking". This is the strict 3-D chain.)

## Input / Output

* **Input:** list of `[w, h, d]` triples.
* **Output:** integer — the longest nesting chain length.

## Examples

**Example 1**
Input: `boxes = [[1,1,1], [2,2,2], [3,3,3], [2,1,3]]`
Output: `3`
Explanation: `[1,1,1] → [2,2,2] → [3,3,3]`.

**Example 2**
Input: `boxes = [[5,4,3], [6,4,3]]`
Output: `1`
Explanation: `h` and `d` are equal, so neither fits strictly inside the other.

**Example 3**
Input: `boxes = [[1,2,3], [2,3,4], [3,4,5], [4,5,6]]`
Output: `4`

## Constraints

* `1 <= n <= 2000`
* `1 <= w, h, d <= 10^9`

## Approach

Sort the boxes by the first dimension (`w`) ascending. After sorting, any valid chain is a subsequence in which `h` and `d` are also strictly increasing, and `w` is strictly increasing (ties in `w` can never nest, so treat equal-`w` boxes as incompatible).

That is a **Longest Increasing Subsequence** with a three-way comparison:

* `dp[i]` = longest chain ending at box `i` (as the outermost box).
* For each `j < i`, if `w[j] < w[i]` and `h[j] < h[i]` and `d[j] < d[i]`, then `dp[i] = max(dp[i], dp[j] + 1)`.
* Answer is `max(dp)`.

Reconstruct the chain with a `prev[]` array if the boxes themselves are required.

O(n log n) is possible for 2-D via sorting plus LIS with patience sorting; for 3-D with strict inequalities it no longer reduces cleanly, so O(n²) is the expected solution at `n <= 2000`.

## Complexity

* **Time:** O(n²)
* **Space:** O(n)

## Reference solution (Python)

```
def max_nested_boxes(boxes):
    b = sorted(boxes)
    n = len(b)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if b[j][0] < b[i][0] and b[j][1] < b[i][1] and b[j][2] < b[i][2]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp) if n else 0
```

## Test cases

| Input | Expected |
| --- | --- |
| `[[1,1,1],[2,2,2],[3,3,3],[2,1,3]]` | `3` |
| `[[5,4,3],[6,4,3]]` | `1` |
| `[[1,2,3],[2,3,4],[3,4,5],[4,5,6]]` | `4` |
| `[]` | `0` |

[PreviousMaximum Good Subarray Sum](/problems/maximum-good-subarray-sum)[NextMaximum Number of Intersections on the Chart](/problems/maximum-number-of-intersections-on-the-chart)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/atlassian.ico)Atlassian#70 in list](/companies/atlassian)

## Details

Difficulty
:   Medium

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Dynamic Programming](/topics?open=dynamic-programming#dynamic-programming)

[Solution](https://www.youtube.com/results?search_query=Maximum%20Nested%20Boxes%20dsa)

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
