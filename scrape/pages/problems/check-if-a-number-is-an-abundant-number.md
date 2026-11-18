# Check if a Number is an Abundant Number · FAANGrind

Source: https://faangrind.vercel.app/problems/check-if-a-number-is-an-abundant-number

[All problems](/problems)

#154Easy· asked at 1 company

# Check if a Number is an Abundant Number

[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

A positive integer `N` is **abundant** if the sum of its **proper divisors** (all positive divisors except `N` itself) is strictly greater than `N`. Given `N`, return `true` if it is abundant and `false` otherwise.

Related terms: if the sum equals `N` the number is *perfect*; if the sum is less it is *deficient*.

## Input / Output

* **Input:** integer `N`.
* **Output:** boolean.

## Examples

**Example 1**
Input: `N = 12`
Output: `true`
Explanation: Proper divisors are `1, 2, 3, 4, 6`; sum = 16 > 12.

**Example 2**
Input: `N = 28`
Output: `false`
Explanation: Proper divisors `1, 2, 4, 7, 14` sum to 28 exactly — 28 is perfect, not abundant.

**Example 3**
Input: `N = 15`
Output: `false`
Explanation: `1 + 3 + 5 = 9 < 15`.

## Constraints

* `1 <= N <= 10^9`

## Approach

Enumerating all divisors up to `N` is O(N) — too slow for 10^9. Instead iterate only up to `√N`, because divisors come in pairs `(i, N/i)`:

```
sum = 1                      // 1 is a proper divisor of every N > 1
for i in 2 .. floor(sqrt(N)):
    if N % i == 0:
        sum += i
        if i != N / i: sum += N / i   // avoid double-counting a perfect square root
return sum > N
```

Handle `N = 1` separately (no proper divisors → not abundant).

Use 64-bit integers for the sum; for highly composite `N` near 10^9 the divisor sum can exceed 2^31.

## Complexity

* **Time:** O(√N)
* **Space:** O(1)

## Follow-ups

* Precompute abundance for all numbers `1..M` using a sieve-like loop (for each `i`, add `i` to every multiple of `i`), giving O(M log M) for many queries.
* Classify a number as abundant, perfect or deficient in one function.
* The smallest odd abundant number is 945 — a fun check for your implementation.

## Reference solution (Python)

```
from math import isqrt

def is_abundant(n):
    if n <= 1:
        return False
    total = 1
    for i in range(2, isqrt(n) + 1):
        if n % i == 0:
            total += i
            if i != n // i:
                total += n // i
    return total > n
```

## Test cases

| Input | Expected |
| --- | --- |
| `12` | `true` |
| `28` | `false (perfect)` |
| `15` | `false` |
| `945` | `true (smallest odd abundant)` |

[PreviousCheck if a Number is a Strong Number](/problems/check-if-a-number-is-a-strong-number)[NextCount of Range Sum](/problems/count-of-range-sum)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/amazon.ico)Amazon#260 in list](/companies/amazon)

## Details

Difficulty
:   Easy

Popularity
:   10/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Check%20if%20a%20Number%20is%20an%20Abundant%20Number%20dsa)

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
