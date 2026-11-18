# Find Distinct Expressions · FAANGrind

Source: https://faangrind.vercel.app/problems/find-distinct-expressions

[All problems](/problems)

#517Easy· asked at 3 companies

# Find Distinct Expressions

[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/linkedin.ico)LinkedIn](/companies/linkedin)

## Problem

You are given `n` arithmetic expressions, each of the form `x op y` where `x` and `y` are single lowercase letters or integers and `op` is one of `+`, `*` (commutative) or `-`, `/` (not commutative). Two expressions are considered **the same** if they are mathematically identical after normalisation: `a+b` and `b+a` are the same, `a*b` and `b*a` are the same, but `a-b` and `b-a` are different. Return the number of **distinct** expressions.

## Input / Output

* **Input:** list of strings `exprs`.
* **Output:** integer count of distinct expressions.

## Examples

**Example 1**
Input: `exprs = ["a+b", "b+a", "a*b", "a-b", "b-a"]`
Output: `4`
Explanation: `a+b` and `b+a` collapse into one; the rest are distinct.

**Example 2**
Input: `exprs = ["x*y", "y*x", "x*y"]`
Output: `1`

**Example 3**
Input: `exprs = ["1+2", "2+1", "3+0"]`
Output: `2` (no evaluation — `3+0` is a different expression from `1+2`).

## Constraints

* `1 <= n <= 10^5`
* Expressions contain no spaces and exactly one operator.

## Approach

This is a **canonical-form hashing** problem. For each expression:

1. Split into `left`, `op`, `right`.
2. If `op` is commutative (`+` or `*`), sort the two operands so the smaller one comes first: `canonical = min(left, right) + op + max(left, right)`.
3. Otherwise keep the order as is.
4. Insert the canonical string into a hash set.

The answer is the size of the set. Normalising before hashing is the whole idea: it turns "are these mathematically the same?" into "are these strings equal?", which a hash set answers in O(1).

**Extension.** For longer expressions with parentheses, build an expression tree, sort children of commutative nodes recursively, and serialise the tree — the same technique used to detect duplicate subtrees.

## Complexity

* **Time:** O(n · L) where `L` is the expression length.
* **Space:** O(n · L) for the set.

## Reference solution (Python)

```
import re

def count_distinct_expressions(exprs):
    seen = set()
    for e in exprs:
        m = re.fullmatch(r'([a-z0-9]+)([+\-*/])([a-z0-9]+)', e)
        l, op, r = m.groups()
        if op in '+*' and l > r:
            l, r = r, l
        seen.add(l + op + r)
    return len(seen)
```

## Test cases

| Input | Expected |
| --- | --- |
| `["a+b","b+a","a*b","a-b","b-a"]` | `4` |
| `["x*y","y*x","x*y"]` | `1` |
| `["1+2","2+1","3+0"]` | `2` |
| `["a/b","b/a"]` | `2` |

[PreviousFind a Safe Walk Through a Grid](/problems/find-a-safe-walk-through-a-grid)[NextFind Lucky Integer in an Array](/problems/find-lucky-integer-in-an-array)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/american-express.png)American Express#44 in list](/companies/american-express)
* [![](/logos/apple.ico)Apple#81 in list](/companies/apple)
* [![](/logos/linkedin.ico)LinkedIn#113 in list](/companies/linkedin)

## Details

Difficulty
:   Easy

Popularity
:   15/100

Source
:   Full statement on FAANGrind

Topics
:   [Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=Find%20Distinct%20Expressions%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#934LRU CacheMedium](/problems/lru-cache)
* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
* [#890Longest Consecutive Sequence in an ArrayMedium](/problems/longest-consecutive-sequence-in-an-array)
* [#303Count subarrays with given sumMedium](/problems/count-subarrays-with-given-sum)
* [#854LFU CacheHard](/problems/lfu-cache)
