# Automorphic Number · FAANGrind

Source: https://faangrind.vercel.app/problems/automorphic-number

[All problems](/problems)

#56Easy· asked at 1 company

# Automorphic Number

[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

A number `N` is **automorphic** if its square ends with the same digits as `N` itself. Given a non-negative integer `N`, return `true` if it is automorphic and `false` otherwise.

## Input / Output

* **Input:** integer `N`.
* **Output:** boolean (or the string `"Automorphic"` / `"Not Automorphic"`).

## Examples

| N | N² | Ends with N? | Result |
| --- | --- | --- | --- |
| 5 | 25 | yes | true |
| 6 | 36 | yes | true |
| 25 | 625 | yes | true |
| 76 | 5776 | yes | true |
| 376 | 141376 | yes | true |
| 7 | 49 | no | false |
| 10 | 100 | no | false |

## Constraints

* `0 <= N <= 10^9` (use 64-bit arithmetic for the square).

## Approach

**Digit comparison.** Compute `sq = N * N`. Then compare the last `k` digits of `sq` with `N`, where `k` is the number of digits in `N`:

```
while N > 0:
    if N % 10 != sq % 10: return false
    N /= 10; sq /= 10
return true
```

This peels one digit from each number at a time and stops as soon as a mismatch appears.

**Modular check.** Let `p = 10^k`. `N` is automorphic iff `sq % p == N`. Computing `p` is O(k).

**String method.** Convert both to strings and test `str(sq).endswith(str(N))`. Simplest to write, slightly slower.

Edge cases: `N = 0` and `N = 1` are automorphic (0² = 0, 1² = 1).

## Complexity

* **Time:** O(k) where `k` is the number of digits, i.e. O(log N).
* **Space:** O(1).

## Background

Automorphic numbers are also called circular numbers. There are only two infinite families ending in 5 and 6; each longer automorphic number extends a shorter one (5 → 25 → 625 → 0625…, 6 → 76 → 376 → 9376…). Interviewers use the problem to test overflow awareness — `N = 10^9` gives a square of 10^18, which does not fit in 32 bits.

## Reference solution (Python)

```
def is_automorphic(n):
    sq = n * n
    t = n
    while t > 0:
        if t % 10 != sq % 10:
            return False
        t //= 10
        sq //= 10
    return True
```

## Test cases

| Input | Expected |
| --- | --- |
| `5` | `true` |
| `76` | `true` |
| `7` | `false` |
| `0` | `true` |

[PreviousArray With Elements Not Equal to Average of Neighbors](/problems/array-with-elements-not-equal-to-average-of-neighbors)[NextCalculate Digit Sum of a String](/problems/calculate-digit-sum-of-a-string)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/amazon.ico)Amazon#469 in list](/companies/amazon)

## Details

Difficulty
:   Easy

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Automorphic%20Number%20dsa)

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
