# Change Every Letter with the Next Lexicographic · FAANGrind

Source: https://faangrind.vercel.app/problems/change-every-letter-with-the-next-lexicographic

[All problems](/problems)

#144Easy· asked at 3 companies

# Change Every Letter with the Next Lexicographic

[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given a string `s` of lowercase English letters, replace every character with the **next letter in the alphabet**: `a → b`, `b → c`, …, `y → z`, and `z` wraps around to `a`. Return the resulting string. Non-letter characters, if present, stay as they are.

## Input / Output

* **Input:** string `s`.
* **Output:** the shifted string.

## Examples

**Example 1**
Input: `s = "abc"`
Output: `"bcd"`

**Example 2**
Input: `s = "xyz"`
Output: `"yza"`

**Example 3**
Input: `s = "hello world"`
Output: `"ifmmp xpsme"`

## Constraints

* `1 <= s.length <= 10^5`

## Approach

For each lowercase letter `c`, compute `(c - 'a' + 1) % 26 + 'a'`. The modulo handles the wrap from `z` to `a` without a special case.

```
result = []
for c in s:
    if 'a' <= c <= 'z':
        result.append(chr((ord(c) - ord('a') + 1) % 26 + ord('a')))
    else:
        result.append(c)
return ''.join(result)
```

Work on a character buffer for linear time in languages with immutable strings.

**Generalisation.** This is a Caesar cipher with shift 1. Replace `+ 1` with `+ k` for an arbitrary shift, and use `(c - 'a' - k) % 26` (normalising negatives) to decode. Uppercase letters use the same formula with `'A'`.

## Complexity

* **Time:** O(n)
* **Space:** O(n) for the output.

## Follow-ups

* Shift each character by its **position** in the string (`i`-th character shifts by `i`).
* Apply the shift only to vowels, or only to characters inside a given index range.
* Given the shifted string and the original, recover `k`.

## Reference solution (Python)

```
def shift_next(s):
    out = []
    for c in s:
        if 'a' <= c <= 'z':
            out.append(chr((ord(c) - 97 + 1) % 26 + 97))
        else:
            out.append(c)
    return ''.join(out)
```

## Test cases

| Input | Expected |
| --- | --- |
| `"abc"` | `"bcd"` |
| `"xyz"` | `"yza"` |
| `"hello world"` | `"ifmmp xpsme"` |
| `"z"` | `"a"` |

[PreviousChange Case of Each Character in a String](/problems/change-case-of-each-character-in-a-string)[NextCheck if a Large Number is Divisible by 9](/problems/check-if-a-large-number-is-divisible-by-9)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/american-express.png)American Express#115 in list](/companies/american-express)
* [![](/logos/goldman-sachs.png)Goldman Sachs#282 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#432 in list](/companies/amazon)

## Details

Difficulty
:   Easy

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Change%20Every%20Letter%20with%20the%20Next%20Lexicographic%20dsa)

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
