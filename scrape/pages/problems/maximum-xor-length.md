# Maximum XOR Length · FAANGrind

Source: https://faangrind.vercel.app/problems/maximum-xor-length

[All problems](/problems)

#1118Medium· asked at 1 company

# Maximum XOR Length

[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

You are given an array `arr` of non-negative integers and an integer `K`. Find the **length of the longest subarray** whose bitwise XOR of all elements equals `K`. If no such subarray exists, return `0`.

(Some versions ask for the longest subarray with XOR **at least** or **at most** `K`; the core technique is the same, with a binary trie replacing the hash map — see the note at the end.)

## Input / Output

* **Input:** integer array `arr`, integer `K`.
* **Output:** the maximum subarray length.

## Examples

**Example 1**
Input: `arr = [4, 2, 2, 6, 4]`, `K = 6`
Output: `5`
Explanation: The whole array XORs to `4^2^2^6^4 = 6`.

**Example 2**
Input: `arr = [1, 2, 3, 4]`, `K = 7`
Output: `2`
Explanation: `[3, 4]` gives `3^4 = 7`. `[1,2,3,4]` gives 4.

**Example 3**
Input: `arr = [5, 5, 5]`, `K = 1`
Output: `0`

## Constraints

* `1 <= n <= 10^5`
* `0 <= arr[i], K < 2^30`

## Approach — prefix XOR with first-occurrence map

Let `P[i]` be the XOR of `arr[0..i]` and define `P[-1] = 0`. The XOR of `arr[j+1..i]` equals `P[i] ^ P[j]`. We need `P[j] == P[i] ^ K`, and to maximise `i - j` we want the **earliest** `j` with that prefix value.

1. Create a hash map `first` from prefix value to the first index where it occurred, with `first[0] = -1`.
2. Scan the array maintaining `xr`. At index `i`, if `first` contains `xr ^ K`, update `best = max(best, i - first[xr ^ K])`.
3. Insert `xr` into `first` **only if it is not already present** — keeping the earliest index is what makes the subarray longest.

## Complexity

* **Time:** O(n)
* **Space:** O(n)

## Note on the "at least / at most K" variant

When the condition is an inequality rather than equality, a hash map cannot answer "is there an earlier prefix `P[j]` such that `P[i] ^ P[j] >= K`?". Insert prefixes into a **binary trie** over the 30 bits, storing the minimum index at each node, and walk the trie greedily bit by bit to find the earliest prefix satisfying the inequality. That is O(30 · n).

## Common mistakes

* Overwriting `first[xr]` on every occurrence (you would find the *shortest* subarray).
* Forgetting the sentinel `first[0] = -1`.

## Reference solution (Python)

```
def longest_subarray_xor_k(arr, k):
    first = {0: -1}
    xr, best = 0, 0
    for i, v in enumerate(arr):
        xr ^= v
        if (xr ^ k) in first:
            best = max(best, i - first[xr ^ k])
        if xr not in first:
            first[xr] = i
    return best
```

## Test cases

| Input | Expected |
| --- | --- |
| `[4,2,2,6,4], k=6` | `5` |
| `[1,2,3,4], k=7` | `2` |
| `[5,5,5], k=1` | `0` |
| `[3], k=3` | `1` |

[PreviousMaximum Number of People That Can Be Caught in Tag](/problems/maximum-number-of-people-that-can-be-caught-in-tag)[NextMinimum Cost to Make Array Equal](/problems/minimum-cost-to-make-array-equal)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/amazon.ico)Amazon#40 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   9/100

Source
:   Full statement on FAANGrind

Topics
:   [Tries](/topics?open=tries#tries)

[Solution](https://www.youtube.com/results?search_query=Maximum%20XOR%20Length%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#885Longest Common PrefixMedium](/problems/longest-common-prefix)
* [#1915Trie Implementation and Advanced OperationsMedium](/problems/trie-implementation-and-advanced-operations)
* [#1998Word Search IIHard](/problems/word-search-ii)
* [#1992Word Break IIHard](/problems/word-break-ii)
* [#1693Search Suggestions SystemMedium](/problems/search-suggestions-system)
* [#597Find the Length of the Longest Common PrefixMedium](/problems/find-the-length-of-the-longest-common-prefix)
