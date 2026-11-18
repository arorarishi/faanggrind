# Number of Jumps · FAANGrind

Source: https://faangrind.vercel.app/problems/number-of-jumps

[All problems](/problems)

#1387Medium· asked at 1 company

# Number of Jumps

[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

A frog stands at position `0` on a number line and wants to reach (or pass) position `target`. Each jump moves it forward by exactly `d` units. Return the **minimum number of jumps** required. If `target` is already `<= 0`, the answer is `0`.

A common variant gives a starting position `start` instead of 0, and another gives an array of jump lengths where the frog may pick any of them each time; both are covered below.

## Input / Output

* **Input:** integers `start`, `target`, `d` (all positive, up to 10^9).
* **Output:** the minimum number of jumps.

## Examples

**Example 1**
Input: `start = 0`, `target = 10`, `d = 3`
Output: `4`
Explanation: Positions after each jump: 3, 6, 9, 12 — four jumps to reach or exceed 10.

**Example 2**
Input: `start = 5`, `target = 5`, `d = 2`
Output: `0`

**Example 3**
Input: `start = 2`, `target = 11`, `d = 3`
Output: `3` (2 → 5 → 8 → 11)

## Constraints

* `1 <= start <= target <= 10^9`
* `1 <= d <= 10^9`

## Approach

Simulating jump by jump is O(target / d), which can be 10^9 iterations. The answer is a single formula:

`jumps = ceil((target - start) / d)`

In integer arithmetic without floating point: `(target - start + d - 1) / d`. Guard the `target <= start` case, which returns 0.

**Variant with several jump lengths `lengths[]`.** If any jump length may be used at each step and you only need to reach or pass the target, always pick the largest length: `ceil((target - start) / max(lengths))`.

**Variant requiring exact landing.** If the frog must land **exactly** on `target` using lengths from an array, it becomes a coin-change / BFS problem: BFS over positions `0..target` where each position expands to `pos + len` for every length. Return the BFS level at which `target` is reached, or `-1`. That costs O(target × |lengths|).

## Complexity

* Formula version: O(1) time, O(1) space.
* Exact-landing BFS: O(target × k) time and O(target) space.

## Pitfalls

* Integer overflow in `target - start + d - 1` for 32-bit ints when values are near 10^9; use 64-bit.
* Off-by-one: "reach or pass" vs "land exactly".

## Reference solution (Python)

```
def min_jumps(start, target, d):
    if target <= start:
        return 0
    return (target - start + d - 1) // d

# exact-landing variant with several jump lengths
from collections import deque
def min_jumps_exact(target, lengths):
    dist = [-1] * (target + 1)
    dist[0] = 0
    q = deque([0])
    while q:
        p = q.popleft()
        for L in lengths:
            nxt = p + L
            if nxt <= target and dist[nxt] == -1:
                dist[nxt] = dist[p] + 1
                q.append(nxt)
    return dist[target]
```

## Test cases

| Input | Expected |
| --- | --- |
| `start=0, target=10, d=3` | `4` |
| `start=5, target=5, d=2` | `0` |
| `start=2, target=11, d=3` | `3` |
| `exact: target=7, lengths=[2,3]` | `3 # 2+2+3` |

[PreviousNumber of Good Paths](/problems/number-of-good-paths)[NextNumber of People That Can Be Seen in a Grid](/problems/number-of-people-that-can-be-seen-in-a-grid)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/amazon.ico)Amazon#637 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Number%20of%20Jumps%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1464Palindrome NumberEasy](/problems/palindrome-number)
* [#1652Reverse IntegerMedium](/problems/reverse-integer)
* [#1521Pow(x,n)Medium](/problems/pow-x-n)
* [#1514Plus OneEasy](/problems/plus-one)
* [#1532Print all primes till NMedium](/problems/print-all-primes-till-n)
* [#1247Minimum number of platforms required for a railwayMedium](/problems/minimum-number-of-platforms-required-for-a-railway)
