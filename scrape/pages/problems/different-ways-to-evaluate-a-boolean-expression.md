# Different Ways to Evaluate a Boolean Expression · FAANGrind

Source: https://faangrind.vercel.app/problems/different-ways-to-evaluate-a-boolean-expression

[All problems](/problems)

#426Hard· asked at 2 companies

# Different Ways to Evaluate a Boolean Expression

[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

You are given a boolean expression as a string containing the symbols `T` (true), `F` (false) and the binary operators `&` (AND), `|` (OR) and `^` (XOR). Count the number of ways to **parenthesise** the expression so that it evaluates to `true`. Since the answer can be large, return it modulo `1000000007` (some versions use 1003).

## Input / Output

* **Input:** string `s` with alternating operands and operators, e.g. `"T|T&F^T"`.
* **Output:** integer count of parenthesisations evaluating to true.

## Examples

**Example 1**
Input: `s = "T|T&F^T"`
Output: `4`
Explanation: The four ways are `((T|T)&(F^T))`, `(T|(T&(F^T)))`, `(((T|T)&F)^T)`, `(T|((T&F)^T))`.

**Example 2**
Input: `s = "T^F|F"`
Output: `2`
Explanation: `((T^F)|F)` and `(T^(F|F))`.

## Constraints

* `1 <= |s| <= 201` (i.e. up to about 100 operators).

## Approach — Interval Dynamic Programming

Define two tables over operand indices `i..j`:

* `T[i][j]` = number of ways the sub-expression from operand `i` to operand `j` evaluates to true.
* `F[i][j]` = number of ways it evaluates to false.

Base case (`i == j`): `T[i][i] = 1` if the operand is `T` else 0; `F[i][i]` is the opposite.

For `i < j`, try every operator position `k` between operands `i..j` as the **last** operation applied. Let `lt, lf` be the true/false counts of the left part and `rt, rf` of the right part. Then:

* `&` : true += `lt·rt`; false += `lt·rf + lf·rt + lf·rf`
* `|` : true += `lt·rt + lt·rf + lf·rt`; false += `lf·rf`
* `^` : true += `lt·rf + lf·rt`; false += `lt·rt + lf·rf`

Fill the tables by increasing interval length. The answer is `T[0][m-1]` where `m` is the number of operands.

A top-down memoised recursion `solve(i, j, wantTrue)` is equivalent and often easier to write in an interview.

## Complexity

* **Time:** O(m³) — O(m²) intervals, each split in O(m) ways.
* **Space:** O(m²).

## Why it is asked

It is the boolean cousin of Matrix Chain Multiplication and "Burst Balloons": the skill being tested is recognising that the last operator applied splits the problem into two independent subproblems.

## Reference solution (Python)

```
from functools import lru_cache
MOD = 1_000_000_007

def count_ways(s):
    ops = s[1::2]
    vals = s[0::2]
    m = len(vals)

    @lru_cache(None)
    def solve(i, j):
        # returns (ways_true, ways_false) for operands i..j
        if i == j:
            return (1, 0) if vals[i] == 'T' else (0, 1)
        t = f = 0
        for k in range(i, j):
            lt, lf = solve(i, k)
            rt, rf = solve(k + 1, j)
            op = ops[k]
            if op == '&':
                t += lt * rt
                f += lt * rf + lf * rt + lf * rf
            elif op == '|':
                t += lt * rt + lt * rf + lf * rt
                f += lf * rf
            else:  # '^'
                t += lt * rf + lf * rt
                f += lt * rt + lf * rf
        return (t % MOD, f % MOD)

    return solve(0, m - 1)[0]
```

## Test cases

| Input | Expected |
| --- | --- |
| `"T | T&F^T"` |
| `"T^F | F"` |
| `"F"` | `0` |
| `"T&F"` | `0` |

[PreviousDestroying Asteroids](/problems/destroying-asteroids)[NextFind All Lonely Numbers in the Array](/problems/find-all-lonely-numbers-in-the-array)

Saved in this browser. No account needed.

## Asked at

2 companies

* [![](/logos/goldman-sachs.png)Goldman Sachs#307 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#561 in list](/companies/amazon)

## Details

Difficulty
:   Hard

Popularity
:   11/100

Source
:   Full statement on FAANGrind

Topics
:   [Dynamic Programming](/topics?open=dynamic-programming#dynamic-programming)

[Solution](https://www.youtube.com/results?search_query=Different%20Ways%20to%20Evaluate%20a%20Boolean%20Expression%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#75Best time to buy and sell stockMedium](/problems/best-time-to-buy-and-sell-stock)
* [#909Longest Palindromic SubstringMedium](/problems/longest-palindromic-substring)
* [#714House robberMedium](/problems/house-robber)
* [#899Longest Increasing SubsequenceMedium](/problems/longest-increasing-subsequence)
* [#458Edit distanceMedium](/problems/edit-distance)
* [#184Climbing stairsMedium](/problems/climbing-stairs)
