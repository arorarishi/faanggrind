# Z function · FAANGrind

Source: https://faangrind.vercel.app/problems/z-function

[All problems](/problems)

#2004Medium· asked at 2 companies

# Z function

[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given a string `S` of length `n`, compute its **Z-array**: `Z[i]` is the length of the longest substring starting at index `i` that is also a prefix of `S`. By convention `Z[0] = 0` (or `n`). Then use it to find all occurrences of a pattern `P` in a text `T`.

## Input / Output

* **Input:** string `S` (for the Z-array), or strings `P` and `T` (for matching).
* **Output:** the Z-array, or the list of match indices.

## Examples

**Example 1**
Input: `S = "aabxaab"`
Output: `Z = [0, 1, 0, 0, 3, 1, 0]`
Explanation: At index 4 the substring `aab` matches the prefix `aab`, so `Z[4] = 3`.

**Example 2 (pattern matching)**
Input: `P = "ab"`, `T = "abcabab"`
Concatenate `P + "$" + T = "ab$abcabab"`. Any index in the text part with `Z[i] == |P|` is a match → indices `0, 3, 5` in `T`.

## Constraints

* `1 <= n <= 10^6`

## Approach

A naive computation compares from each index and costs O(n²). The linear algorithm maintains a **Z-box** `[l, r]` — the rightmost segment found so far that matches a prefix.

For each `i` from 1 to n-1:

1. If `i > r`, there is no useful information: compare characters from scratch starting at `i` against the prefix, set `Z[i]`, and if `Z[i] > 0` update `l = i, r = i + Z[i] - 1`.
2. If `i <= r`, then `S[i..r]` equals `S[i-l .. r-l]`, so `Z[i]` is at least `min(Z[i-l], r-i+1)`. Start from that value and extend by direct comparison only if it reaches `r`. Update `[l, r]` if the new box goes further right.

Each character comparison either fails once per `i` or extends `r`, and `r` only ever increases, so the total work is O(n).

## Complexity

* **Time:** O(n)
* **Space:** O(n) for the Z-array.

## Uses

* Pattern matching in O(n + m) (an alternative to KMP).
* Counting distinct substrings, finding periods of a string, longest prefix that is also a suffix, string compression checks.

## Reference solution (Python)

```
def z_function(s):
    n = len(s)
    z = [0] * n
    l = r = 0
    for i in range(1, n):
        if i <= r:
            z[i] = min(r - i + 1, z[i - l])
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1
        if i + z[i] - 1 > r:
            l, r = i, i + z[i] - 1
    return z

def find_pattern(pat, text):
    s = pat + '$' + text
    z = z_function(s)
    m = len(pat)
    return [i - m - 1 for i in range(m + 1, len(s)) if z[i] == m]
```

## Test cases

| Input | Expected |
| --- | --- |
| `s="aabxaab"` | `[0,1,0,0,3,1,0]` |
| `pat="ab", text="abcabab"` | `[0, 3, 5]` |
| `s="aaaa"` | `[0,3,2,1]` |
| `pat="z", text="abc"` | `[]` |

[PreviousValid Palindrome III](/problems/valid-palindrome-iii)[NextArithmetic Slices](/problems/arithmetic-slices)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/apple.ico)Apple#187 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#418 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   12/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Z%20function%20dsa)

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
