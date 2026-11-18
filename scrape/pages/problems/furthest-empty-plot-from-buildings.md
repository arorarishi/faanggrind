# Furthest Empty Plot From Buildings · FAANGrind

Source: https://faangrind.vercel.app/problems/furthest-empty-plot-from-buildings

[All problems](/problems)

#671Medium· asked at 3 companies

# Furthest Empty Plot From Buildings

[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/amazon.ico)Amazon](/companies/amazon)[![](/logos/paypal.png)PayPal](/companies/paypal)

## Problem

A street is represented by a binary array `plots` of length `n`, where `plots[i] = 1` means a building stands on plot `i` and `plots[i] = 0` means the plot is empty. You want to build on an empty plot that is **as far as possible from the nearest building**. Return the maximum possible distance to the closest building. It is guaranteed that there is at least one building and at least one empty plot.

## Input / Output

* **Input:** binary array `plots`.
* **Output:** the maximum over all empty plots of (distance to nearest building).

## Examples

**Example 1**
Input: `plots = [1, 0, 0, 0, 1, 0, 1]`
Output: `2`
Explanation: Plot 2 is 2 away from buildings at 0 and 4. Plot 5 is only 1 away.

**Example 2**
Input: `plots = [1, 0, 0, 0]`
Output: `3`
Explanation: The last plot is 3 away from the only building.

**Example 3**
Input: `plots = [0, 0, 1]`
Output: `2`

## Constraints

* `2 <= n <= 2 * 10^5`

## Approach

The nearest building to an empty plot is either the closest one on its left or the closest one on its right, so two linear passes suffice:

1. **Left pass:** walk left to right keeping the index of the last building seen; for each empty plot store `left[i] = i - lastBuilding` (or infinity if none yet).
2. **Right pass:** walk right to left the same way to get `right[i]`.
3. For each empty plot, `dist[i] = min(left[i], right[i])`. The answer is the maximum `dist[i]`.

This can be done in O(1) extra space by handling the three cases directly:

* **Leading zeros** (before the first building): the best empty plot is index 0, distance = index of first building.
* **Trailing zeros** (after the last building): distance = `n - 1 - lastBuilding`.
* **A gap of `g` zeros between two buildings:** the middle plot achieves `(g + 1) / 2` (integer division after adding 1).
  Take the maximum of these.

## Complexity

* **Time:** O(n)
* **Space:** O(1) with the three-case scan, O(n) with the two auxiliary arrays.

## Related problems

"Maximize Distance to Closest Person" (LeetCode 849) is the identical problem in a cinema-seat setting. The two-pass "nearest on left / nearest on right" idea also solves "Shortest Distance to a Character" and "Distance of Nearest Cell Having 1" (in 2D, via multi-source BFS).

## Reference solution (Python)

```
def furthest_empty_plot(plots):
    n = len(plots)
    first = plots.index(1)
    last = n - 1 - plots[::-1].index(1)
    best = max(first, n - 1 - last)          # leading / trailing gaps
    prev = first
    for i in range(first + 1, last + 1):
        if plots[i] == 1:
            best = max(best, (i - prev) // 2)  # middle of the gap
            prev = i
    return best
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,0,0,0,1,0,1]` | `2` |
| `[1,0,0,0]` | `3` |
| `[0,0,1]` | `2` |
| `[1,0,1]` | `1` |

[PreviousFrog Jump](/problems/frog-jump)[NextGet Equal Substrings Within Budget](/problems/get-equal-substrings-within-budget)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/apple.ico)Apple#50 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#147 in list](/companies/amazon)
* [![](/logos/paypal.png)PayPal#189 in list](/companies/paypal)

## Details

Difficulty
:   Medium

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)

[Solution](https://www.youtube.com/results?search_query=Furthest%20Empty%20Plot%20From%20Buildings%20dsa)

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
