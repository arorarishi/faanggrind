# Rabin Karp Algorithm · FAANGrind

Source: https://faangrind.vercel.app/problems/rabin-karp-algorithm

[All problems](/problems)

#1555Medium· asked at 3 companies

# Rabin Karp Algorithm

[![](/logos/salesforce.ico)Salesforce](/companies/salesforce)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given a text string `T` of length `n` and a pattern string `P` of length `m`, return all starting indices (0-based) where `P` occurs in `T`. Implement the **Rabin–Karp** rolling-hash algorithm rather than a naive character-by-character compare.

## Input / Output

* **Input:** strings `T` and `P` over lowercase letters (or any fixed alphabet).
* **Output:** list of starting indices, in increasing order; empty list if none.

## Examples

**Example 1**
Input: `T = "abracadabra"`, `P = "abra"`
Output: `[0, 7]`

**Example 2**
Input: `T = "aaaaa"`, `P = "aa"`
Output: `[0, 1, 2, 3]`

## Constraints

* `1 <= m <= n <= 10^6`

## Approach

The naive algorithm checks every window in O(m), giving O(n·m). Rabin–Karp reduces this by comparing **hash values** of windows first and only comparing characters when hashes match.

**Polynomial rolling hash.** Treat a string as a number in base `B` (a prime larger than the alphabet size, e.g. 31 or 257) modulo a large prime `M` (e.g. 10^9+7):
`hash(s) = (s[0]·B^(m-1) + s[1]·B^(m-2) + … + s[m-1]) mod M`

**Sliding the window.** When moving from window starting at `i` to `i+1`:
`newHash = ((oldHash − T[i]·B^(m-1)) · B + T[i+m]) mod M`
Precompute `B^(m-1) mod M` once. Keep everything non-negative by adding `M` before taking the modulus.

**Algorithm.**

1. Compute `hashP` and the hash of the first window of `T`.
2. For each window: if the hash equals `hashP`, compare the characters directly to confirm (this guards against collisions). Record the index if they match.
3. Roll the hash to the next window.

**Collisions.** Two different strings can share a hash. The direct comparison on hash match keeps the algorithm correct; using a double hash (two moduli) makes false matches astronomically rare so the verification almost never runs.

## Complexity

* **Time:** O(n + m) on average; O(n·m) in the pathological worst case where every window collides.
* **Space:** O(1) beyond the output.

## When to prefer it

Rabin–Karp shines for **multiple-pattern** search (hash all patterns of the same length into a set and scan once) and for problems like "longest duplicate substring", where KMP does not apply directly.

## Reference solution (Python)

```
def rabin_karp(text, pat, B=257, M=10**9 + 7):
    n, m = len(text), len(pat)
    if m > n:
        return []
    high = pow(B, m - 1, M)
    hp = ht = 0
    for i in range(m):
        hp = (hp * B + ord(pat[i])) % M
        ht = (ht * B + ord(text[i])) % M
    res = []
    for i in range(n - m + 1):
        if hp == ht and text[i:i + m] == pat:
            res.append(i)
        if i + m < n:
            ht = ((ht - ord(text[i]) * high) * B + ord(text[i + m])) % M
    return res
```

## Test cases

| Input | Expected |
| --- | --- |
| `text="abracadabra", pat="abra"` | `[0, 7]` |
| `text="aaaaa", pat="aa"` | `[0, 1, 2, 3]` |
| `text="abc", pat="d"` | `[]` |
| `text="ab", pat="abc"` | `[]` |

[PreviousPrint 1 to N using Recursion](/problems/print-1-to-n-using-recursion)[NextRank Transform of an Array](/problems/rank-transform-of-an-array)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/salesforce.ico)Salesforce#14 in list](/companies/salesforce)
* [![](/logos/apple.ico)Apple#161 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#507 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   17/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)

[Solution](https://www.youtube.com/results?search_query=Rabin%20Karp%20Algorithm%20dsa)

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
