# Find the Kth Lucky Number · FAANGrind

Source: https://faangrind.vercel.app/problems/find-the-kth-lucky-number

[All problems](/problems)

#591Medium· asked at 2 companies

# Find the Kth Lucky Number

[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)

## Problem

A **lucky number** is a positive integer whose decimal representation contains only the digits `4` and `7`. The lucky numbers in increasing order are `4, 7, 44, 47, 74, 77, 444, 447, …`. Given an integer `k`, return the k-th lucky number as a string.

## Input / Output

* **Input:** integer `k` (1-based).
* **Output:** the k-th lucky number as a string.

## Examples

| k | Output |
| --- | --- |
| 1 | `"4"` |
| 2 | `"7"` |
| 3 | `"44"` |
| 4 | `"47"` |
| 5 | `"74"` |
| 6 | `"77"` |
| 7 | `"444"` |

## Constraints

* `1 <= k <= 10^9`

## Approach

Generating lucky numbers one by one (BFS on "append 4 / append 7") works but is O(k). There is an O(log k) formula.

Group lucky numbers by length: there are `2^1` of length 1, `2^2` of length 2, … `2^L` of length `L`, and they are the binary strings of length `L` with `0 → 4` and `1 → 7`, in the same order.

1. Find the length `L` of the k-th lucky number: subtract `2, 4, 8, …` from `k` until the next group would exceed it. After this, `k` is the 1-based index **within** the group of length `L`.
2. Convert `k - 1` to an `L`-bit binary string (left-padded with zeros).
3. Replace `0 → 4` and `1 → 7`.

Equivalently: the k-th lucky number is the binary representation of `k + 1` with its leading `1` removed and digits mapped `0 → 4`, `1 → 7`. Both views come from the fact that lucky numbers form a complete binary tree in BFS order.

## Complexity

* **Time:** O(log k)
* **Space:** O(log k) for the output string.

## Reference solution (Python)

```
def kth_lucky(k: int) -> str:
    b = bin(k + 1)[3:]                # drop '0b' and the leading 1
    return b.replace('0', '4').replace('1', '7')

# brute-force cross-check
def lucky_numbers(limit):
    from collections import deque
    q, out = deque(['4', '7']), []
    while len(out) < limit:
        s = q.popleft()
        out.append(s)
        q.append(s + '4'); q.append(s + '7')
    return out
```

## Test cases

| Input | Expected |
| --- | --- |
| `1` | `"4"` |
| `5` | `"74"` |
| `7` | `"444"` |
| `10` | `"477"` |

[PreviousFind Missing and Repeated Values](/problems/find-missing-and-repeated-values)[NextFlip Game II](/problems/flip-game-ii)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/goldman-sachs.png)Goldman Sachs#35 in list](/companies/goldman-sachs)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#133 in list](/companies/jpmorgan-chase)

## Details

Difficulty
:   Medium

Popularity
:   11/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Find%20the%20Kth%20Lucky%20Number%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#923Longest Substring Without Repeating CharactersMedium](/problems/longest-substring-without-repeating-characters)
* [#909Longest Palindromic SubstringMedium](/problems/longest-palindromic-substring)
* [#1313Minimum Window SubstringMedium](/problems/minimum-window-substring)
* [#1951Valid AnagramEasy](/problems/valid-anagram)
* [#1463Palindrome CheckMedium](/problems/palindrome-check)
* [#911Longest Repeating Character ReplacementMedium](/problems/longest-repeating-character-replacement)
