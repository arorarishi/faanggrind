# Remove Characters Except Alphabets · FAANGrind

Source: https://faangrind.vercel.app/problems/remove-characters-except-alphabets

[All problems](/problems)

#1598Easy· asked at 1 company

# Remove Characters Except Alphabets

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given a string `s`, return a new string containing **only the alphabetic characters** of `s` (`a`–`z`, `A`–`Z`), in their original order. Digits, spaces, punctuation and other symbols are dropped.

## Input / Output

* **Input:** string `s`.
* **Output:** filtered string.

## Examples

**Example 1**
Input: `s = "He11o, W0rld!"`
Output: `"HeoWrld"`

**Example 2**
Input: `s = "123 456"`
Output: `""`

**Example 3**
Input: `s = "abc"`
Output: `"abc"`

## Constraints

* `0 <= s.length <= 10^5`

## Approach

Single pass; keep a character if it is a letter. Two ways to test:

* `isalpha()` / `Character.isLetter` — Unicode-aware, accepts accented letters.
* Range check `'a' <= c <= 'z' or 'A' <= c <= 'Z'` — ASCII only, what most such problems intend.

Use a builder/list and join once; repeated string concatenation is quadratic in immutable-string languages.

This is the filtering half of "Valid Palindrome" (LeetCode 125), where you strip non-alphanumerics and lowercase before comparing — knowing this problem makes that one a two-liner.

## Complexity

* **Time:** O(n)
* **Space:** O(n) for the output.

## Reference solution (Python)

```
def only_alphabets(s: str) -> str:
    return ''.join(c for c in s if ('a' <= c <= 'z') or ('A' <= c <= 'Z'))
```

## Test cases

| Input | Expected |
| --- | --- |
| `"He11o, W0rld!"` | `"HeoWrld"` |
| `"123 456"` | `""` |
| `"abc"` | `"abc"` |
| `"a-b_c"` | `"abc"` |

[PreviousReformat Date](/problems/reformat-date)[NextRemove Characters from First String Present in the Second String](/problems/remove-characters-from-first-string-present-in-the-second-string)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#98 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Remove%20Characters%20Except%20Alphabets%20dsa)

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
