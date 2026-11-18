# Un Palindromic Strings · FAANGrind

Source: https://faangrind.vercel.app/problems/un-palindromic-strings

[All problems](/problems)

#1930Easy· asked at 1 company

# Un Palindromic Strings

[![](/logos/apple.ico)Apple](/companies/apple)

## Problem

Given a string `s` of lowercase letters, determine whether its characters can be **rearranged** so that the result is **not** a palindrome. If it is possible, return any such rearrangement; otherwise return `-1`.

A string cannot be made non-palindromic only when **every** arrangement is a palindrome — which happens exactly when all characters are identical (including the single-character case).

## Input / Output

* **Input:** string `s`.
* **Output:** a non-palindromic rearrangement of `s`, or `-1`.

## Examples

**Example 1**
Input: `s = "aba"`
Output: `"aab"` (any non-palindrome such as `"baa"` is accepted).

**Example 2**
Input: `s = "aaaa"`
Output: `-1`

**Example 3**
Input: `s = "abccba"`
Output: `"aabbcc"`

**Example 4**
Input: `s = "z"`
Output: `-1`

## Constraints

* `1 <= s.length <= 10^5`

## Approach

**Key insight.** If `s` contains at least two different characters, sorting it produces a string whose first character is the smallest letter and whose last character is the largest letter, and those differ — so the sorted string is automatically **not** a palindrome. If all characters are equal, every arrangement is the same palindrome, so the answer is `-1`.

Algorithm:

1. If every character of `s` equals `s[0]`, return `-1`.
2. Otherwise return `sorted(s)`.

**Alternative without sorting.** Find the first index `i` where `s[i] != s[n-1-i]`; if none exists and the string is a palindrome, swap two different characters to break the symmetry. Sorting is simpler and clearly correct.

**Related follow-ups.**

* *Check if a string is a palindrome* — two pointers.
* *Can the string be rearranged into a palindrome?* — at most one character with odd count.
* *Minimum deletions to make it non-palindromic* — 0 if not a palindrome, 1 if it has two different characters, impossible otherwise.

## Complexity

* **Time:** O(n log n) with sorting, or O(n + 26) with counting sort.
* **Space:** O(n) for the output.

## Reference solution (Python)

```
def un_palindromic(s):
    if all(c == s[0] for c in s):
        return -1
    return ''.join(sorted(s))

def is_palindrome(t):
    return t == t[::-1]
```

## Test cases

| Input | Expected |
| --- | --- |
| `"aba"` | any non-palindrome, e.g. `"aab"` |
| `"aaaa"` | `-1` |
| `"abccba"` | `"aabbcc"` |
| `"z"` | `-1` |

[PreviousTree Diameter](/problems/tree-diameter)[NextValid Mountain Array](/problems/valid-mountain-array)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/apple.ico)Apple#136 in list](/companies/apple)

## Details

Difficulty
:   Easy

Popularity
:   13/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Un%20Palindromic%20Strings%20dsa)

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
