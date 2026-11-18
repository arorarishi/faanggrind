# Capitalize First and Last Character of Each Word · FAANGrind

Source: https://faangrind.vercel.app/problems/capitalize-first-and-last-character-of-each-word

[All problems](/problems)

#138Easy· asked at 5 companies

# Capitalize First and Last Character of Each Word

[![](/logos/linkedin.ico)LinkedIn](/companies/linkedin)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

You are given a string `s` made up of words separated by single spaces. Each word contains only lowercase English letters. Return a new string in which, for every word, the **first** and the **last** character are converted to uppercase while every other character stays unchanged. Words of length 1 have the same first and last character, so that single character becomes uppercase.

## Input / Output

* **Input:** a string `s` with `1 <= s.length <= 10^5`, words separated by exactly one space, no leading or trailing spaces.
* **Output:** the transformed string.

## Examples

**Example 1**
Input: `s = "hello world"`
Output: `"HellO WorlD"`
Explanation: In `hello` the first letter `h` and the last letter `o` become uppercase. Same for `world`.

**Example 2**
Input: `s = "a quick brown fox"`
Output: `"A QuicK BrowN FoX"`
Explanation: The single-letter word `a` becomes `A`.

**Example 3**
Input: `s = "abc"`
Output: `"AbC"`

## Constraints

* `1 <= s.length <= 10^5`
* `s` contains only lowercase letters and spaces.
* There is exactly one space between consecutive words.

## Approach

This is a straightforward string-scanning problem, but interviewers use it to check whether you can handle boundaries cleanly without splitting the string into a list (which costs extra memory).

1. Convert the string to a mutable character array.
2. Walk through the array with an index `i`. A character at index `i` is the **first** letter of a word if `i == 0` or `s[i-1] == ' '`. It is the **last** letter of a word if `i == n-1` or `s[i+1] == ' '`.
3. If either condition holds and the character is a letter, replace it with its uppercase form.
4. Join the characters back into a string.

Because each position is inspected once and the checks are constant time, the algorithm is linear.

Alternative: split on spaces, transform each word (`w[0].upper() + w[1:-1] + w[-1].upper()` with a guard for length 1) and join with a single space. This is simpler to write but allocates a list of words.

## Complexity

* **Time:** O(n), where n is the length of the string.
* **Space:** O(n) for the output (O(1) extra if the language allows in-place mutation).

## Follow-ups often asked

* Handle multiple consecutive spaces or leading/trailing spaces without collapsing them.
* Do it in place in a language with mutable strings (C/C++).
* Extend to Unicode words where "letter" is not just `a`–`z`.

## Reference solution (Python)

```
def capitalize_ends(s: str) -> str:
    chars = list(s)
    n = len(chars)
    for i, c in enumerate(chars):
        if c == ' ':
            continue
        first = i == 0 or chars[i - 1] == ' '
        last = i == n - 1 or chars[i + 1] == ' '
        if first or last:
            chars[i] = c.upper()
    return ''.join(chars)
```

## Test cases

| Input | Expected |
| --- | --- |
| `"hello world"` | `"HellO WorlD"` |
| `"a quick brown fox"` | `"A QuicK BrowN FoX"` |
| `"x"` | `"X"` |
| `"ab"` | `"AB"` |

[PreviousBitwise OR of Adjacent Elements](/problems/bitwise-or-of-adjacent-elements)[NextCar Fleet](/problems/car-fleet)

Saved in this browser. No account needed.

## Asked at

5 companies

* [![](/logos/linkedin.ico)LinkedIn#65 in list](/companies/linkedin)
* [![](/logos/american-express.png)American Express#139 in list](/companies/american-express)
* [![](/logos/apple.ico)Apple#225 in list](/companies/apple)
* [![](/logos/goldman-sachs.png)Goldman Sachs#309 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#648 in list](/companies/amazon)

## Details

Difficulty
:   Easy

Popularity
:   26/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Capitalize%20First%20and%20Last%20Character%20of%20Each%20Word%20dsa)

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
