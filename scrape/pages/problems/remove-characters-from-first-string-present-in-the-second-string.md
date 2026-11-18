# Remove Characters from First String Present in the Second String · FAANGrind

Source: https://faangrind.vercel.app/problems/remove-characters-from-first-string-present-in-the-second-string

[All problems](/problems)

#1599Easy· asked at 1 company

# Remove Characters from First String Present in the Second String

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given two strings `s1` and `s2`, return `s1` with **every character that appears anywhere in `s2` removed**. The relative order of the remaining characters is preserved.

## Input / Output

* **Input:** strings `s1`, `s2`.
* **Output:** filtered string.

## Examples

**Example 1**
Input: `s1 = "computer"`, `s2 = "cat"`
Output: `"ompuer"`
Explanation: `c`, `a` and `t` are removed.

**Example 2**
Input: `s1 = "hello"`, `s2 = ""`
Output: `"hello"`

**Example 3**
Input: `s1 = "aaaa"`, `s2 = "a"`
Output: `""`

## Constraints

* `0 <= |s1|, |s2| <= 10^5`

## Approach

The naive method checks each character of `s1` against the whole of `s2`: O(|s1| · |s2|). Instead:

1. Put the characters of `s2` into a **set** (or a boolean array of size 128/256 for ASCII) — O(|s2|).
2. Scan `s1` once and keep only characters not in the set — O(|s1|).

The set turns membership into O(1), giving linear total time. If the alphabet is lowercase letters, a 26-entry boolean array is the fastest and most memory-frugal version; a **bitmask** in a single integer (`mask |= 1 << (c - 'a')`) is the trick to mention.

## Complexity

* **Time:** O(|s1| + |s2|)
* **Space:** O(|Σ|) — the alphabet size.

## Reference solution (Python)

```
def remove_chars(s1: str, s2: str) -> str:
    banned = set(s2)
    return ''.join(c for c in s1 if c not in banned)
```

## Test cases

| Input | Expected |
| --- | --- |
| `"computer", "cat"` | `"ompuer"` |
| `"hello", ""` | `"hello"` |
| `"aaaa", "a"` | `""` |
| `"abc", "xyz"` | `"abc"` |

[PreviousRemove Characters Except Alphabets](/problems/remove-characters-except-alphabets)[NextRemove Spaces from a String](/problems/remove-spaces-from-a-string)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#63 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Remove%20Characters%20from%20First%20String%20Present%20in%20the%20Second%20String%20dsa)

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
