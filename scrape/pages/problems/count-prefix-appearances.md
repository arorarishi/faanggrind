# Count Prefix Appearances · FAANGrind

Source: https://faangrind.vercel.app/problems/count-prefix-appearances

[All problems](/problems)

#297Medium· asked at 11 companies

# Count Prefix Appearances

[![](/logos/linkedin.ico)LinkedIn](/companies/linkedin)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/paypal.png)PayPal](/companies/paypal)+5 more

## Problem

You are given a list of `n` words and a list of `q` query strings. For each query `p`, return the number of words in the list that have `p` as a **prefix** (a word is a prefix of itself).

## Input / Output

* **Input:** `words[]` (lowercase strings), `queries[]` (lowercase strings).
* **Output:** an integer array of length `q`, where the i-th value is the count for `queries[i]`.

## Examples

**Example 1**
Input: `words = ["apple", "app", "apricot", "banana"]`, `queries = ["ap", "app", "b", "c"]`
Output: `[3, 2, 1, 0]`
Explanation: `"ap"` prefixes apple, app, apricot; `"app"` prefixes apple and app; `"b"` prefixes banana; nothing starts with `"c"`.

**Example 2**
Input: `words = ["a", "a", "ab"]`, `queries = ["a"]`
Output: `[3]`

## Constraints

* `1 <= n, q <= 10^5`
* Total length of all words and queries `<= 10^6`.

## Approach

**Brute force** compares every query against every word: O(n · q · L), far too slow.

**Trie with subtree counts (recommended).**

1. Insert every word into a trie. At each node passed during insertion, increment a `count` field — the number of words that pass through this node, i.e. the number of words having the node's path as a prefix.
2. For each query, walk down the trie character by character. If a character is missing, the answer is 0. Otherwise the answer is the `count` at the final node.

Every insertion and every query costs O(length of the string), independent of `n`.

**Alternative — sorting + binary search.** Sort the words. For a query `p`, all words with prefix `p` form a contiguous block: the first index is `lowerBound(p)` and the end is `lowerBound(p + '{')` (`'{'` is the character after `'z'`). The count is the difference. Cost O((n + q) · L · log n).

## Complexity (trie)

* **Build:** O(total characters in words)

[PreviousCount of Subarrays with Sum Divisible by K](/problems/count-of-subarrays-with-sum-divisible-by-k)[NextCount the Number of Good Subsequences](/problems/count-the-number-of-good-subsequences)

Saved in this browser. No account needed.

## Asked at

11 companies

* [![](/logos/linkedin.ico)LinkedIn#27 in list](/companies/linkedin)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#29 in list](/companies/jpmorgan-chase)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#51 in list](/companies/walmart-global-tech)
* [![](/logos/apple.ico)Apple#70 in list](/companies/apple)
* [![](/logos/american-express.png)American Express#87 in list](/companies/american-express)
* [![](/logos/paypal.png)PayPal#90 in list](/companies/paypal)
* [![](/logos/atlassian.ico)Atlassian#112 in list](/companies/atlassian)
* [![](/logos/salesforce.ico)Salesforce#117 in list](/companies/salesforce)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#173 in list](/companies/palo-alto-networks)
* [![](/logos/goldman-sachs.png)Goldman Sachs#328 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#494 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   26/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)[Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Count%20Prefix%20Appearances%20dsa)

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

- **Each query:** O(|query|)

- **Space:** O(total characters × alphabet size) in the worst case; use hash-map children to reduce it.

## Variants

* Count words that are prefixes of the query (reverse direction — sum `endCount` along the path).
* Support deletions (decrement counts along the path).
* Return the words themselves (DFS from the query node).

## Reference solution (Python)
