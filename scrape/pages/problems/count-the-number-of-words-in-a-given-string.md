# Count the Number of Words in a Given String · FAANGrind

Source: https://faangrind.vercel.app/problems/count-the-number-of-words-in-a-given-string

[All problems](/problems)

#326Easy· asked at 1 company

# Count the Number of Words in a Given String

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given a string `s`, return the number of **words** it contains. A word is a maximal sequence of non-space characters. The string may contain leading, trailing or multiple consecutive spaces, and may be empty.

## Input / Output

* **Input:** string `s`.
* **Output:** integer word count.

## Examples

**Example 1**
Input: `s = "the quick brown fox"`
Output: `4`

**Example 2**
Input: `s = " hello world "`
Output: `2`

**Example 3**
Input: `s = ""` or `s = " "`
Output: `0`

## Constraints

* `0 <= s.length <= 10^5`

## Approach

A word starts at every index `i` where `s[i]` is not a space and (`i == 0` or `s[i-1]` is a space). Count those positions in one pass:

```
count = 0
for i in range(n):
    if s[i] != ' ' and (i == 0 or s[i-1] == ' '):
        count += 1
```

This handles all the whitespace edge cases without allocating a list, unlike `len(s.split())`, which is fine in practice but is not what a "do it manually" interviewer wants.

Extensions: treat tabs and newlines as separators (`isspace()`), or count only words made of letters.

## Complexity

* **Time:** O(n)
* **Space:** O(1)

## Reference solution (Python)

```
def count_words(s):
    count = 0
    for i, c in enumerate(s):
        if not c.isspace() and (i == 0 or s[i - 1].isspace()):
            count += 1
    return count
```

## Test cases

| Input | Expected |
| --- | --- |
| `"the quick brown fox"` | `4` |
| `" hello world "` | `2` |
| `""` | `0` |
| `"a"` | `1` |

[PreviousCount the Number of K-free subsets](/problems/count-the-number-of-k-free-subsets)[NextCount Vowels, Consonants, and Spaces in a String](/problems/count-vowels-consonants-and-spaces-in-a-string)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#31 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Count%20the%20Number%20of%20Words%20in%20a%20Given%20String%20dsa)

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
