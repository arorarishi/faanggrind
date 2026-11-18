# Change Case of Each Character in a String · FAANGrind

Source: https://faangrind.vercel.app/problems/change-case-of-each-character-in-a-string

[All problems](/problems)

#143Easy· asked at 3 companies

# Change Case of Each Character in a String

[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/amazon.ico)Amazon](/companies/amazon)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

Given a string `s`, return a new string in which every **uppercase** letter is converted to lowercase and every **lowercase** letter is converted to uppercase. Non-alphabetic characters (digits, spaces, punctuation) remain unchanged.

## Input / Output

* **Input:** string `s`.
* **Output:** the case-toggled string.

## Examples

**Example 1**
Input: `s = "Hello World"`
Output: `"hELLO wORLD"`

**Example 2**
Input: `s = "aBc123!"`
Output: `"AbC123!"`

**Example 3**
Input: `s = ""`
Output: `""`

## Constraints

* `0 <= s.length <= 10^5`
* ASCII characters only (extend with Unicode-aware library calls if required).

## Approach

Iterate over each character and branch on its range:

* `'a'..'z'` → subtract 32 (or `c - 'a' + 'A'`).
* `'A'..'Z'` → add 32.
* otherwise → copy unchanged.

**Bit trick.** In ASCII, uppercase and lowercase letters differ only in bit 5 (value 32). So for any letter, `c ^ 32` flips its case in one operation, and the check `isLetter(c)` guards non-letters. Interviewers often ask you to explain why `'A' = 65 = 0b1000001` and `'a' = 97 = 0b1100001`.

Build the result in a character array or string builder rather than concatenating strings in a loop (which is O(n²) in languages with immutable strings).

## Complexity

* **Time:** O(n)
* **Space:** O(n) for the output; O(1) extra if done in place on a mutable buffer.

## Follow-ups

* Toggle case only for alternate characters or only within words.
* Handle non-ASCII scripts using library functions such as `swapcase()` in Python.
* Count how many characters changed.

## Reference solution (Python)

```
def toggle_case(s):
    out = []
    for c in s:
        if 'a' <= c <= 'z' or 'A' <= c <= 'Z':
            out.append(chr(ord(c) ^ 32))
        else:
            out.append(c)
    return ''.join(out)
```

## Test cases

| Input | Expected |
| --- | --- |
| `"Hello World"` | `"hELLO wORLD"` |
| `"aBc123!"` | `"AbC123!"` |
| `""` | `""` |
| `"ZZZ"` | `"zzz"` |

[PreviousCalculate Digit Sum of a String](/problems/calculate-digit-sum-of-a-string)[NextChange Every Letter with the Next Lexicographic](/problems/change-every-letter-with-the-next-lexicographic)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/american-express.png)American Express#30 in list](/companies/american-express)
* [![](/logos/amazon.ico)Amazon#32 in list](/companies/amazon)
* [![](/logos/goldman-sachs.png)Goldman Sachs#146 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Easy

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Change%20Case%20of%20Each%20Character%20in%20a%20String%20dsa)

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
