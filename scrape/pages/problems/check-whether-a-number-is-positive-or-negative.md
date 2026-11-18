# Check Whether a Number is Positive or Negative · FAANGrind

Source: https://faangrind.vercel.app/problems/check-whether-a-number-is-positive-or-negative

[All problems](/problems)

#176Easy· asked at 1 company

# Check Whether a Number is Positive or Negative

[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given an integer `N`, return `"Positive"` if `N > 0`, `"Negative"` if `N < 0`, and `"Zero"` if `N == 0`. As a follow-up, determine the sign **without using comparison operators** (`<`, `>`, `==`).

## Input / Output

* **Input:** integer `N`.
* **Output:** one of `"Positive"`, `"Negative"`, `"Zero"`.

## Examples

| N | Output |
| --- | --- |
| 15 | Positive |
| -2 | Negative |
| 0 | Zero |
| -2147483648 | Negative |

## Constraints

* `-2^63 <= N <= 2^63 - 1`

## Approach

**Straightforward.** Three-way `if / else if / else` on `N`.

**Without comparisons (bit manipulation).** In two's-complement, the most-significant bit is the sign bit. For a 32-bit `int`:

* `(N >> 31) & 1` is `1` for negative numbers, `0` otherwise (using an arithmetic shift; use `>>>` in Java/JS for an unsigned shift and mask).
* To distinguish zero from positive without `==`, note that `(-N >> 31) & 1` is `1` iff `N > 0` (negating a positive number makes it negative). So:
  + `neg = (N >> 31) & 1`
  + `pos = (-N >> 31) & 1`
  + `neg == 1` → Negative; `pos == 1` → Positive; otherwise Zero.
    Be careful: `-INT_MIN` overflows in 32-bit; use 64-bit arithmetic or handle it explicitly.

**Using the sign function.** Many languages provide `Math.signum`, `Integer.signum`, `np.sign`, which return `-1, 0, 1`.

## Complexity

* **Time:** O(1)
* **Space:** O(1)

## Discussion points

* Why two's-complement makes the top bit a sign indicator.
* Difference between arithmetic and logical right shifts across languages.
* Edge cases: `INT_MIN`, `-0` for floating-point (which compares equal to `0`).

## Reference solution (Python)

```
def sign_of(n: int) -> str:
    if n > 0:
        return "Positive"
    if n < 0:
        return "Negative"
    return "Zero"

# comparison-free version (64-bit)
def sign_of_bits(n: int) -> str:
    neg = (n >> 63) & 1
    pos = ((-n) >> 63) & 1
    return ["Zero", "Positive", "Negative"][neg * 2 + pos]
```

## Test cases

| Input | Expected |
| --- | --- |
| `15` | `Positive` |
| `-2` | `Negative` |
| `0` | `Zero` |
| `-2147483648` | `Negative` |

[PreviousCheck whether a Given Number is Even or Odd](/problems/check-whether-a-given-number-is-even-or-odd)[NextCount Different Palindromic Subsequences](/problems/count-different-palindromic-subsequences)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/amazon.ico)Amazon#58 in list](/companies/amazon)

## Details

Difficulty
:   Easy

Popularity
:   6/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Check%20Whether%20a%20Number%20is%20Positive%20or%20Negative%20dsa)

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
