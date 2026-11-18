# Count Vowels, Consonants, and Spaces in a String · FAANGrind

Source: https://faangrind.vercel.app/problems/count-vowels-consonants-and-spaces-in-a-string

[All problems](/problems)

#332Easy· asked at 1 company

# Count Vowels, Consonants, and Spaces in a String

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given a string `s`, return three counts: the number of **vowels** (`a e i o u`, either case), the number of **consonants** (all other English letters), and the number of **spaces**. Digits and punctuation are ignored.

## Input / Output

* **Input:** string `s`.
* **Output:** `[vowels, consonants, spaces]`.

## Examples

**Example 1**
Input: `s = "Hello World"`
Output: `[3, 7, 1]`

**Example 2**
Input: `s = "AEIOU xyz"`
Output: `[5, 3, 1]`

**Example 3**
Input: `s = "123 !!"`
Output: `[0, 0, 1]`

## Constraints

* `0 <= s.length <= 10^5`

## Approach

Single pass; classify each character:

1. If it is a space → `spaces++`.
2. Else if it is a letter → lowercase it; if it is in `{a,e,i,o,u}` → `vowels++`, else `consonants++`.
3. Otherwise ignore.

Use a set for the vowel test (O(1)) rather than a chain of `or` comparisons. Note that `y` counts as a consonant here.

## Complexity

* **Time:** O(n)
* **Space:** O(1)

## Reference solution (Python)

```
def count_vcs(s):
    vowels = consonants = spaces = 0
    V = set("aeiou")
    for c in s:
        if c == ' ':
            spaces += 1
        elif c.isalpha():
            if c.lower() in V:
                vowels += 1
            else:
                consonants += 1
    return [vowels, consonants, spaces]
```

## Test cases

| Input | Expected |
| --- | --- |
| `"Hello World"` | `[3,7,1]` |
| `"AEIOU xyz"` | `[5,3,1]` |
| `"123 !!"` | `[0,0,1]` |
| `""` | `[0,0,0]` |

[PreviousCount the Number of Words in a Given String](/problems/count-the-number-of-words-in-a-given-string)[NextDecode Ways II](/problems/decode-ways-ii)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#91 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Count%20Vowels%2C%20Consonants%2C%20and%20Spaces%20in%20a%20String%20dsa)

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
