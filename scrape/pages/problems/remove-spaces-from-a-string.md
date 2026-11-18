# Remove Spaces from a String · FAANGrind

Source: https://faangrind.vercel.app/problems/remove-spaces-from-a-string

[All problems](/problems)

#1623Easy· asked at 1 company

# Remove Spaces from a String

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given a string `s`, return a new string with **all space characters removed**. Then solve the in-place variant: modify a mutable character array so that the non-space characters are packed at the front, and return the new length.

## Input / Output

* **Input:** string `s` (or char array).
* **Output:** the string without spaces (or the new length).

## Examples

**Example 1**
Input: `s = "a b c d"`
Output: `"abcd"`

**Example 2**
Input: `s = " "`
Output: `""`

**Example 3**
Input: `s = "nospaces"`
Output: `"nospaces"`

## Constraints

* `0 <= s.length <= 10^5`

## Approach

**Immutable strings.** Filter characters and join: O(n).

**In place (two pointers).** Keep a write index `w = 0`. For each read index `r`, if `s[r] != ' '`, copy `s[r]` to `s[w]` and increment `w`. At the end `w` is the new length. This is the same compaction pattern as "Move Zeroes" and "Remove Element", and the interviewer wants to see you recognise it.

Generalisation: remove all whitespace (`isspace`), or collapse runs of spaces into one (keep a space only if `w == 0` or `s[w-1] != ' '`).

## Complexity

* **Time:** O(n)
* **Space:** O(n) for the new string; O(1) in place.

## Reference solution (Python)

```
def remove_spaces(s):
    return ''.join(c for c in s if c != ' ')

def remove_spaces_inplace(chars):
    w = 0
    for c in chars:
        if c != ' ':
            chars[w] = c
            w += 1
    del chars[w:]
    return w
```

## Test cases

| Input | Expected |
| --- | --- |
| `"a b c d"` | `"abcd"` |
| `" "` | `""` |
| `"nospaces"` | `"nospaces"` |
| `list("x y")` (in place) | `['x','y']`, returns `2` |

[PreviousRemove Characters from First String Present in the Second String](/problems/remove-characters-from-first-string-present-in-the-second-string)[NextRemoving Stars From a String](/problems/removing-stars-from-a-string)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#68 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Remove%20Spaces%20from%20a%20String%20dsa)

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
