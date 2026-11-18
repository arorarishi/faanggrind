# Find the ASCII Value of a Character · FAANGrind

Source: https://faangrind.vercel.app/problems/find-the-ascii-value-of-a-character

[All problems](/problems)

#578Easy· asked at 1 company

# Find the ASCII Value of a Character

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given a single character `c`, return its ASCII (Unicode code point) value. As follow-ups: convert an integer back to its character, and explain how character arithmetic (`'a' + 1`, `c - '0'`) works.

## Input / Output

* **Input:** character `c`.
* **Output:** integer.

## Examples

| Input | Output |
| --- | --- |
| `'A'` | 65 |
| `'a'` | 97 |
| `'0'` | 48 |
| `' '` | 32 |
| `'~'` | 126 |

## Constraints

* `c` is a printable ASCII character (32–126).

## Approach

Every language exposes the code point directly: `ord(c)` in Python, `(int) c` in C/C++/Java, `c.charCodeAt(0)` in JavaScript. The reverse is `chr(n)` / `(char) n` / `String.fromCharCode(n)`.

What interviewers actually probe with this warm-up:

* Digits `'0'..'9'` are contiguous (48–57), so `c - '0'` converts a digit character to its numeric value.
* Uppercase `'A'..'Z'` are 65–90 and lowercase `'a'..'z'` are 97–122; they differ by 32, which is why `c ^ 32` toggles case and `c | 32` lowercases.
* Building a frequency array indexed by `ord(c) - ord('a')` is O(1) per character and is the basis of many string problems.
* Beyond ASCII, `ord` returns the Unicode code point; UTF-8 byte length is a separate concept.

## Complexity

* **Time:** O(1)
* **Space:** O(1)

## Reference solution (Python)

```
def ascii_value(c: str) -> int:
    return ord(c)

def char_from(n: int) -> str:
    return chr(n)
```

## Test cases

| Input | Expected |
| --- | --- |
| `'A'` | `65` |
| `'a'` | `97` |
| `'0'` | `48` |
| `char_from(126)` | `'~'` |

[PreviousFind Root of N-Ary Tree](/problems/find-root-of-n-ary-tree)[NextFind the city with the smallest number of neighbors](/problems/find-the-city-with-the-smallest-number-of-neighbors)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#93 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Find%20the%20ASCII%20Value%20of%20a%20Character%20dsa)

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
