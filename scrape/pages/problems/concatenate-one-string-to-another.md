# Concatenate One String to Another · FAANGrind

Source: https://faangrind.vercel.app/problems/concatenate-one-string-to-another

[All problems](/problems)

#210Easy· asked at 2 companies

# Concatenate One String to Another

[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

Given two strings `s1` and `s2`, return the string formed by appending `s2` to the end of `s1`. Then handle the follow-ups: concatenate a **list** of `n` strings efficiently, and explain why naive repeated concatenation is slow in languages with immutable strings.

## Input / Output

* **Input:** strings `s1`, `s2` (or a list of strings).
* **Output:** the concatenated string.

## Examples

**Example 1**
Input: `s1 = "Hello, "`, `s2 = "World"`
Output: `"Hello, World"`

**Example 2**
Input: `s1 = ""`, `s2 = "abc"`
Output: `"abc"`

**Example 3 (list)**
Input: `["a", "b", "c", "d"]`
Output: `"abcd"`

## Constraints

* `0 <= |s1|, |s2| <= 10^5`; total length of a list `<= 10^6`.

## Approach

**Two strings.** Allocate a buffer of size `|s1| + |s2|`, copy `s1`, then copy `s2`. In C this is `strcat` after ensuring the destination has room; in most high-level languages the `+` operator does exactly this in O(|s1| + |s2|).

**Many strings — the trap.** Writing `result += s` inside a loop copies the growing `result` every iteration in Java, Python, JavaScript, C#, etc., because strings are immutable there. `n` appends of length-`L` strings cost O(n²·L). The fix is a **string builder** (`StringBuilder`, `''.join(list)`, `Array.join`) which accumulates pieces and copies once at the end, giving O(total length).

**Manual implementation without library help** (what the interviewer may ask for): compute the total length, allocate a character array once, and copy each string into place with a running offset.

## Complexity

* **Time:** O(total length)
* **Space:** O(total length) for the result.

## Reference solution (Python)

```
def concat(s1: str, s2: str) -> str:
    return s1 + s2

def concat_many(parts):
    # manual builder: single allocation, single pass
    buf = []
    for p in parts:
        buf.append(p)
    return ''.join(buf)
```

## Test cases

| Input | Expected |
| --- | --- |
| `"Hello, ", "World"` | `"Hello, World"` |
| `"", "abc"` | `"abc"` |
| `["a","b","c","d"]` | `"abcd"` |
| `[]` | `""` |

[PreviousCoin Path](/problems/coin-path)[NextConfusing Number II](/problems/confusing-number-ii)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/american-express.png)American Express#65 in list](/companies/american-express)
* [![](/logos/goldman-sachs.png)Goldman Sachs#101 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Easy

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Concatenate%20One%20String%20to%20Another%20dsa)

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
