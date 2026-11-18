# Count Substrings Without Repeating Characters · FAANGrind

Source: https://faangrind.vercel.app/problems/count-substrings-without-repeating-characters

[All problems](/problems)

#311Medium· asked at 6 companies

# Count Substrings Without Repeating Characters

[![](/logos/salesforce.ico)Salesforce](/companies/salesforce)[![](/logos/amazon.ico)Amazon](/companies/amazon)[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/swiggy.png)Swiggy](/companies/swiggy)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

Given a string `s`, count the number of **substrings** (contiguous, non-empty) in which **all characters are distinct**.

## Input / Output

* **Input:** string `s` of lowercase letters (or ASCII).
* **Output:** the count (may exceed 32 bits for long strings).

## Examples

**Example 1**
Input: `s = "abc"`
Output: `6`
Explanation: `a, b, c, ab, bc, abc` — every substring has distinct characters.

**Example 2**
Input: `s = "aab"`
Output: `4`
Explanation: `a, a, b, ab`. The substrings `aa` and `aab` repeat `a`.

**Example 3**
Input: `s = "abab"`
Output: `7`
Explanation: `a, b, a, b, ab, ba, ab`.

## Constraints

* `1 <= s.length <= 10^5`

## Approach — Sliding window

Fix the right end `r` and maintain the smallest `l` such that `s[l..r]` has no repeated character. Every substring ending at `r` and starting at any index in `[l, r]` is valid, so add `r - l + 1` to the answer.

Maintain `last[c]` = the most recent index of character `c`:

```
l = 0; ans = 0; last = {}
for r in 0..n-1:
    if s[r] in last and last[s[r]] >= l:
        l = last[s[r]] + 1
    last[s[r]] = r
    ans += r - l + 1
```

Because `l` only moves forward, the whole scan is linear. A frequency array plus a `while` loop that shrinks the window until `freq[s[r]] == 1` is an equivalent formulation.

## Complexity

* **Time:** O(n)
* **Space:** O(alphabet size)

## Relationship to other problems

This is "Longest Substring Without Repeating Characters" with a different accumulation step: instead of `max(len)` you sum the window length at each `r`. The same skeleton gives "number of substrings with at most K distinct characters" and "count subarrays with at most K odd numbers".

## Reference solution (Python)

```
def count_distinct_substrings(s):
    last = {}
    l = ans = 0
    for r, c in enumerate(s):
        if c in last and last[c] >= l:
            l = last[c] + 1
        last[c] = r
        ans += r - l + 1
    return ans
```

## Test cases

| Input | Expected |
| --- | --- |
| `"abc"` | `6` |
| `"aab"` | `4` |
| `"abab"` | `7` |
| `"aaaa"` | `4` |

[PreviousCount Substrings Without Repeating Character](/problems/count-substrings-without-repeating-character)[NextCount Unreachable Pairs of Nodes in an Undirected Graph](/problems/count-unreachable-pairs-of-nodes-in-an-undirected-graph)

Saved in this browser. No account needed.

## Asked at

6 companies

* [![](/logos/salesforce.ico)Salesforce#17 in list](/companies/salesforce)
* [![](/logos/amazon.ico)Amazon#45 in list](/companies/amazon)
* [![](/logos/adobe.ico)Adobe#57 in list](/companies/adobe)
* [![](/logos/american-express.png)American Express#60 in list](/companies/american-express)
* [![](/logos/swiggy.png)Swiggy#122 in list](/companies/swiggy)
* [![](/logos/goldman-sachs.png)Goldman Sachs#226 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Medium

Popularity
:   19/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Count%20Substrings%20Without%20Repeating%20Characters%20dsa)

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
