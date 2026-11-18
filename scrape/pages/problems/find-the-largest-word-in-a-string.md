# Find the Largest Word in a String · FAANGrind

Source: https://faangrind.vercel.app/problems/find-the-largest-word-in-a-string

[All problems](/problems)

#594Easy· asked at 1 company

# Find the Largest Word in a String

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given a sentence `s` containing words separated by spaces, return the **longest word**. If several words tie for the longest length, return the one that appears **first**.

## Input / Output

* **Input:** string `s`.
* **Output:** the longest word (empty string if `s` has no words).

## Examples

**Example 1**
Input: `s = "the quick brown fox jumped"`
Output: `"jumped"`

**Example 2**
Input: `s = "a bb cc dd"`
Output: `"bb"` (first of the length-2 words)

**Example 3**
Input: `s = " "`
Output: `""`

## Constraints

* `0 <= s.length <= 10^5`

## Approach

Scan the string once, tracking the start of the current word. When a space (or the end of the string) is reached, compare the finished word's length to the best so far and update only if it is **strictly** longer — that guarantees the first of equal-length words wins.

Handling punctuation is a common extension: strip non-letters before measuring, or treat any non-letter as a separator.

`max(s.split(), key=len)` is the one-liner; it also returns the first maximal element because `max` keeps the first maximum it sees, but you should be able to explain the manual scan.

## Complexity

* **Time:** O(n)
* **Space:** O(1) extra (besides the returned word).

## Reference solution (Python)

```
def largest_word(s: str) -> str:
    best_start = best_len = 0
    i, n = 0, len(s)
    while i < n:
        if s[i] == ' ':
            i += 1
            continue
        j = i
        while j < n and s[j] != ' ':
            j += 1
        if j - i > best_len:
            best_start, best_len = i, j - i
        i = j
    return s[best_start:best_start + best_len]
```

## Test cases

| Input | Expected |
| --- | --- |
| `"the quick brown fox jumped"` | `"jumped"` |
| `"a bb cc dd"` | `"bb"` |
| `" "` | `""` |
| `"single"` | `"single"` |

[PreviousFind the Distance Value Between Two Arrays](/problems/find-the-distance-value-between-two-arrays)[NextFind the Last Marked Nodes in Tree](/problems/find-the-last-marked-nodes-in-tree)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#133 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Find%20the%20Largest%20Word%20in%20a%20String%20dsa)

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
