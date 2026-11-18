# Array Upper Bound · FAANGrind

Source: https://faangrind.vercel.app/problems/array-upper-bound

[All problems](/problems)

#50Easy· asked at 5 companies

# Array Upper Bound

[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given a **sorted** (non-decreasing) integer array `arr` of length `n` and an integer `x`, return the **upper bound** of `x`: the smallest index `i` such that `arr[i] > x`. If no such index exists, return `n`.

This is the counterpart of *lower bound* (first index with `arr[i] >= x`). Together they let you count occurrences of `x` as `upperBound - lowerBound`.

## Input / Output

* **Input:** sorted array `arr`, integer `x`.
* **Output:** an index in `[0, n]`.

## Examples

**Example 1**
Input: `arr = [1, 2, 2, 3, 3, 5]`, `x = 3`
Output: `5`
Explanation: `arr[5] = 5` is the first element strictly greater than 3.

**Example 2**
Input: `arr = [1, 2, 2, 3, 3, 5]`, `x = 5`
Output: `6`
Explanation: Nothing is greater than 5, so return `n`.

**Example 3**
Input: `arr = [10, 20, 30]`, `x = 5`
Output: `0`

## Constraints

* `1 <= n <= 10^5`
* `-10^9 <= arr[i], x <= 10^9`
* `arr` is sorted in non-decreasing order.

## Approach

A linear scan works in O(n), but the array is sorted, so binary search gives O(log n):

```
lo = 0, hi = n - 1, ans = n
while lo <= hi:
    mid = lo + (hi - lo) / 2
    if arr[mid] > x:
        ans = mid        // candidate; look for an earlier one
        hi = mid - 1
    else:
        lo = mid + 1     // arr[mid] <= x, answer is to the right
return ans
```

The invariant is that every index `>= ans` satisfies `arr[i] > x` and every index `< lo` satisfies `arr[i] <= x`. When the loop ends, `ans` is the smallest qualifying index.

Equivalently, the answer is `lowerBound(x + 1)` for integers, which is why some libraries expose only one primitive.

## Complexity

* **Time:** O(log n)
* **Space:** O(1)

## Where it is used

Counting elements `<= x`, finding the insertion position that keeps stability (insert after duplicates), floor/ceil queries, and as the building block for problems such as "count of smaller numbers", "K-th element of two sorted arrays" and many binary-search-on-answer problems.

## Reference solution (Python)

```
def upper_bound(arr, x):
    lo, hi, ans = 0, len(arr) - 1, len(arr)
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] > x:
            ans = mid
            hi = mid - 1
        else:
            lo = mid + 1
    return ans
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,2,2,3,3,5], x=3` | `5` |
| `[1,2,2,3,3,5], x=5` | `6` |
| `[10,20,30], x=5` | `0` |
| `[1,1,1], x=1` | `3` |

[PreviousApply Operations to Maximize Frequency Score](/problems/apply-operations-to-maximize-frequency-score)[NextBinary Tree Upside Down](/problems/binary-tree-upside-down)

Saved in this browser. No account needed.

## Asked at

5 companies

* [![](/logos/apple.ico)Apple#42 in list](/companies/apple)
* [![](/logos/goldman-sachs.png)Goldman Sachs#127 in list](/companies/goldman-sachs)
* [![](/logos/paypal.png)PayPal#152 in list](/companies/paypal)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#192 in list](/companies/palo-alto-networks)
* [![](/logos/amazon.ico)Amazon#589 in list](/companies/amazon)

## Details

Difficulty
:   Easy

Popularity
:   18/100

Source
:   Full statement on FAANGrind

Topics
:   [Binary Search](/topics?open=binary-search#binary-search)

[Solution](https://www.youtube.com/results?search_query=Array%20Upper%20Bound%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#795Koko eating bananasMedium](/problems/koko-eating-bananas)
* [#899Longest Increasing SubsequenceMedium](/problems/longest-increasing-subsequence)
* [#1122Median of 2 sorted arraysHard](/problems/median-of-2-sorted-arrays)
* [#557Find peak elementMedium](/problems/find-peak-element)
* [#1690Search in rotated sorted array-IMedium](/problems/search-in-rotated-sorted-array-i)
* [#1787Split array - largest sumMedium](/problems/split-array-largest-sum)
