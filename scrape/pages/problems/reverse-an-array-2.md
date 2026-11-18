# Reverse an array 2 · FAANGrind

Source: https://faangrind.vercel.app/problems/reverse-an-array-2

[All problems](/problems)

#1649Medium· asked at 4 companies

# Reverse an array 2

[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/amazon.ico)Amazon](/companies/amazon)[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/apple.ico)Apple](/companies/apple)

## Problem

Given an integer array `arr` of size `n` and a positive integer `k`, reverse the array **in blocks of size k**: reverse the first `k` elements, then the next `k`, and so on. If the final block has fewer than `k` elements, reverse that partial block as well. Do this **in place**.

(The "Reverse an array 1" warm-up is the plain full reversal; this is the block variant that is actually asked in interviews.)

## Input / Output

* **Input:** array `arr`, integer `k`.
* **Output:** the modified array.

## Examples

**Example 1**
Input: `arr = [1, 2, 3, 4, 5, 6, 7, 8]`, `k = 3`
Output: `[3, 2, 1, 6, 5, 4, 8, 7]`

**Example 2**
Input: `arr = [1, 2, 3, 4, 5]`, `k = 10`
Output: `[5, 4, 3, 2, 1]`
Explanation: `k` exceeds the length, so the whole array is one block.

**Example 3**
Input: `arr = [1, 2, 3, 4]`, `k = 1`
Output: `[1, 2, 3, 4]` (each block of one element is unchanged).

## Constraints

* `1 <= n <= 10^6`
* `1 <= k <= 10^9`

## Approach

Write a helper `reverse(arr, lo, hi)` that swaps `arr[lo]` and `arr[hi]` while `lo < hi`, moving the pointers inward. Then:

```
for start in 0, k, 2k, ... while start < n:
    end = min(start + k - 1, n - 1)
    reverse(arr, start, end)
```

Every element is swapped at most once, so the total work is linear regardless of `k`.

**Common follow-up: reverse in groups only if the block is full** (like LeetCode's "Reverse Nodes in k-Group"). The only change is to skip the final partial block when `end - start + 1 < k`.

**Another follow-up: rotate the array by `d` positions using three reversals.** Reverse the first `d` elements, reverse the remaining `n-d`, then reverse the whole array — a neat trick that reuses the same helper and runs in O(n) time, O(1) space.

## Complexity

* **Time:** O(n)
* **Space:** O(1)

## Pitfalls

* Using `k` as the block end without clamping to `n-1` (index out of bounds when `k` does not divide `n`).
* Overflow in `start + k` when `k` is near 10^9 — compute `end` with care or use 64-bit.

## Reference solution (Python)

```
def reverse_range(arr, lo, hi):
    while lo < hi:
        arr[lo], arr[hi] = arr[hi], arr[lo]
        lo += 1
        hi -= 1

def reverse_in_blocks(arr, k):
    n = len(arr)
    for start in range(0, n, k):
        reverse_range(arr, start, min(start + k - 1, n - 1))
    return arr
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,2,3,4,5,6,7,8], k=3` | `[3,2,1,6,5,4,8,7]` |
| `[1,2,3,4,5], k=10` | `[5,4,3,2,1]` |
| `[1,2,3,4], k=1` | `[1,2,3,4]` |
| `[1,2,3,4], k=2` | `[2,1,4,3]` |

[PreviousRemoving Stars From a String](/problems/removing-stars-from-a-string)[NextSentence Screen Fitting](/problems/sentence-screen-fitting)

Saved in this browser. No account needed.

## Asked at

4 companies

* [![](/logos/goldman-sachs.png)Goldman Sachs#86 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#112 in list](/companies/amazon)
* [![](/logos/paypal.png)PayPal#175 in list](/companies/paypal)
* [![](/logos/apple.ico)Apple#316 in list](/companies/apple)

## Details

Difficulty
:   Medium

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)

[Solution](https://www.youtube.com/results?search_query=Reverse%20an%20array%202%20dsa)

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
