# Understand Recursion by Printing · FAANGrind

Source: https://faangrind.vercel.app/problems/understand-recursion-by-printing

[All problems](/problems)

#1932Easy· asked at 1 company

# Understand Recursion by Printing

[![](/logos/american-express.png)American Express](/companies/american-express)

## Problem

Given a name string `name` and an integer `n`, print `name` exactly `n` times, each on its own line, **using recursion and no loops**. Then extend it to the standard recursion warm-ups: print `1..n`, print `n..1`, and print `1..n` using **backtracking** (the print happens *after* the recursive call).

## Input / Output

* **Input:** string `name`, integer `n`.
* **Output:** `n` lines each containing `name`.

## Examples

**Example 1**
Input: `name = "Raj"`, `n = 3`
Output:

```
Raj
Raj
Raj
```

**Example 2 (1 to n)**
Input: `n = 4`
Output: `1 2 3 4`

**Example 3 (n to 1)**
Input: `n = 4`
Output: `4 3 2 1`

## Constraints

* `1 <= n <= 10^4` (recursion depth; raise the limit or convert to iteration for larger `n`).

## Approach

Every recursive function needs a **base case** and a **recursive call that moves toward it**. Use a counter `i` that starts at 1:

```
print_name(i, n):
    if i > n: return          # base case
    print(name)
    print_name(i + 1, n)      # progress
```

Variants that teach the order of work relative to the recursive call:

* **1 to n:** print `i`, then recurse with `i+1`.
* **n to 1:** print `i`, then recurse with `i-1` (start at `n`).
* **1 to n with backtracking:** recurse with `i-1` *first* (start at `n`), then print `i` — the prints happen as the stack unwinds, producing ascending order without ever incrementing.

Each call adds a frame to the call stack, so the space cost is O(n) — the key thing to say when asked "why not just use a loop?"

## Complexity

* **Time:** O(n)
* **Space:** O(n) stack depth.

## Reference solution (Python)

```
import sys
sys.setrecursionlimit(20000)

def print_name(name, n, i=1, out=None):
    out = [] if out is None else out
    if i > n:
        return out
    out.append(name)
    return print_name(name, n, i + 1, out)

def one_to_n(n):
    return [] if n == 0 else one_to_n(n - 1) + [n]          # backtracking style

def n_to_one(n):
    return [] if n == 0 else [n] + n_to_one(n - 1)
```

## Test cases

| Input | Expected |
| --- | --- |
| `print_name("Raj", 3)` | `["Raj","Raj","Raj"]` |
| `one_to_n(4)` | `[1,2,3,4]` |
| `n_to_one(4)` | `[4,3,2,1]` |
| `one_to_n(0)` | `[]` |

[PreviousUgly Number](/problems/ugly-number)[NextUnique Length-3 Palindromic Subsequences](/problems/unique-length-3-palindromic-subsequences)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/american-express.png)American Express#107 in list](/companies/american-express)

## Details

Difficulty
:   Easy

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Recursion & Backtracking](/topics?open=recursion-and-backtracking#recursion-and-backtracking)

[Solution](https://www.youtube.com/results?search_query=Understand%20Recursion%20by%20Printing%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#845Letter Combinations of a Phone NumberMedium](/problems/letter-combinations-of-a-phone-number)
* [#1140Merge two Sorted ListsMedium](/problems/merge-two-sorted-lists)
* [#677Generate ParenthesesMedium](/problems/generate-parentheses)
* [#1997Word SearchMedium](/problems/word-search)
* [#202Combination SumMedium](/problems/combination-sum)
* [#1466Palindrome partitioningMedium](/problems/palindrome-partitioning)
