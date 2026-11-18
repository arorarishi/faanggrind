# Count subarrays with given xor K · FAANGrind

Source: https://faangrind.vercel.app/problems/count-subarrays-with-given-xor-k

[All problems](/problems)

#304Medium· asked at 3 companies

# Count subarrays with given xor K

[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given an array of integers `arr` and an integer `K`, count the number of **subarrays** (contiguous, non-empty) whose bitwise XOR of all elements equals `K`.

## Input / Output

* **Input:** integer array `arr` of length `n`, integer `K`.
* **Output:** a single integer, the count of subarrays with XOR equal to `K`.

## Examples

**Example 1**
Input: `arr = [4, 2, 2, 6, 4]`, `K = 6`
Output: `4`
Explanation: The subarrays are `[4,2]`, `[4,2,2,6,4]`, `[2,2,6]` and `[6]`. Each has XOR 6.

**Example 2**
Input: `arr = [5, 6, 7, 8, 9]`, `K = 5`
Output: `2`
Explanation: `[5]` and `[5,6,7,8,9]` (5^6^7^8^9 = 5).

## Constraints

* `1 <= n <= 10^5`
* `0 <= arr[i], K <= 10^9`

## Approach

**Brute force (O(n²))** — for every start index, extend the end index, maintaining a running XOR, and increment the count when it equals `K`. Fine for small n, too slow for 10^5.

**Prefix-XOR + hash map (O(n))** — the key identity is that XOR is its own inverse: if `P[i]` is the XOR of `arr[0..i]`, then the XOR of `arr[j+1..i]` is `P[i] ^ P[j]`. We want `P[i] ^ P[j] == K`, i.e. `P[j] == P[i] ^ K`.

So while scanning left to right:

1. Maintain `xr`, the prefix XOR so far.
2. Keep a hash map `freq` from prefix-XOR value to how many times it has appeared. Initialise `freq[0] = 1` to account for subarrays that start at index 0.
3. At each element, update `xr ^= arr[i]`, then add `freq[xr ^ K]` to the answer — every earlier prefix with value `xr ^ K` closes a valid subarray ending here.
4. Increment `freq[xr]`.

This mirrors the "subarray sum equals K" pattern but with XOR instead of addition, which is exactly why interviewers like it: it tests whether you understand the prefix technique rather than having memorised one instance.

## Complexity

* **Time:** O(n)
* **Space:** O(n) for the hash map.

## Common mistakes

* Forgetting `freq[0] = 1`, which drops all subarrays starting at index 0.
* Updating `freq[xr]` **before** reading `freq[xr ^ K]` — when `K = 0` this would wrongly count the empty subarray.

## Reference solution (Python)

```
from collections import defaultdict

def count_subarrays_xor(arr, k):
    freq = defaultdict(int)
    freq[0] = 1
    xr, ans = 0, 0
    for v in arr:
        xr ^= v
        ans += freq[xr ^ k]
        freq[xr] += 1
    return ans
```

## Test cases

| Input | Expected |
| --- | --- |
| `[4,2,2,6,4], k=6` | `4` |
| `[5,6,7,8,9], k=5` | `2` |
| `[1,1,1], k=0` | `2 # [1,1] at positions 0-1 and 1-2` |
| `[7], k=7` | `1` |

[PreviousCount Strictly Increasing Subarrays](/problems/count-strictly-increasing-subarrays)[NextCount Substrings Without Repeating Character](/problems/count-substrings-without-repeating-character)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/adobe.ico)Adobe#8 in list](/companies/adobe)
* [![](/logos/goldman-sachs.png)Goldman Sachs#231 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#487 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   19/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)[Bit Manipulation](/topics?open=bit-manipulation#bit-manipulation)

[Solution](https://www.youtube.com/results?search_query=Count%20subarrays%20with%20given%20xor%20K%20dsa)

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
