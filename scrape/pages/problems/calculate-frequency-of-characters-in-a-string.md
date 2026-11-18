# Calculate Frequency of Characters in a String · FAANGrind

Source: https://faangrind.vercel.app/problems/calculate-frequency-of-characters-in-a-string

[All problems](/problems)

#128Easy· asked at 8 companies

# Calculate Frequency of Characters in a String

[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/salesforce.ico)Salesforce](/companies/salesforce)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)+2 more

## Problem

Given a string `s` consisting of lowercase English letters, return the frequency of every character that appears in `s`. Output the characters in **alphabetical order**, each with its count.

## Input / Output

* **Input:** string `s`.
* **Output:** a list of `(character, count)` pairs sorted by character, or an array of 26 counts.

## Examples

**Example 1**
Input: `s = "banana"`
Output: `a:3, b:1, n:2`

**Example 2**
Input: `s = "zzzz"`
Output: `z:4`

## Constraints

* `1 <= s.length <= 10^5`
* `s` contains only `'a'`–`'z'`.

## Approach

Because the alphabet is fixed and small, a **counting array** of size 26 is the ideal structure:

1. Create `cnt[26]` filled with zeros.
2. For each character `c`, do `cnt[c - 'a']++`.
3. Iterate `cnt` from 0 to 25 and emit the letters whose count is non-zero.

This avoids hashing overhead and produces the output already sorted.

If the input can contain arbitrary Unicode, use a hash map from character to count and sort the keys at the end (O(k log k) where `k` is the number of distinct characters).

## Complexity

* **Time:** O(n + 26) = O(n)
* **Space:** O(26) = O(1) for the fixed alphabet; O(k) with a hash map.

## Follow-ups this problem sets up

* Find the first non-repeating character (single pass to count, second pass to find count 1).
* Check whether two strings are anagrams (compare the two count arrays).
* Most frequent character, with tie-breaking rules.
* Count frequencies in a stream with a bounded memory window.

## Reference solution (Python)

```
def char_frequency(s):
    cnt = [0] * 26
    for c in s:
        cnt[ord(c) - 97] += 1
    return [(chr(i + 97), cnt[i]) for i in range(26) if cnt[i]]
```

## Test cases

| Input | Expected |
| --- | --- |
| `"banana"` | `[('a',3),('b',1),('n',2)]` |
| `"zzzz"` | `[('z',4)]` |
| `"abc"` | `[('a',1),('b',1),('c',1)]` |
| `"a"` | `[('a',1)]` |

[PreviousBinary Tree Longest Consecutive Sequence](/problems/binary-tree-longest-consecutive-sequence)[NextCounting Bits](/problems/counting-bits)

Saved in this browser. No account needed.

## Asked at

8 companies

* [![](/logos/palo-alto-networks.png)Palo Alto Networks#33 in list](/companies/palo-alto-networks)
* [![](/logos/salesforce.ico)Salesforce#56 in list](/companies/salesforce)
* [![](/logos/american-express.png)American Express#89 in list](/companies/american-express)
* [![](/logos/goldman-sachs.png)Goldman Sachs#151 in list](/companies/goldman-sachs)
* [![](/logos/adobe.ico)Adobe#165 in list](/companies/adobe)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#165 in list](/companies/walmart-global-tech)
* [![](/logos/apple.ico)Apple#300 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#456 in list](/companies/amazon)

## Details

Difficulty
:   Easy

Popularity
:   23/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)[Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Calculate%20Frequency%20of%20Characters%20in%20a%20String%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#934LRU CacheMedium](/problems/lru-cache)
* [#923Longest Substring Without Repeating CharactersMedium](/problems/longest-substring-without-repeating-characters)
* [#909Longest Palindromic SubstringMedium](/problems/longest-palindromic-substring)
* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
* [#890Longest Consecutive Sequence in an ArrayMedium](/problems/longest-consecutive-sequence-in-an-array)
