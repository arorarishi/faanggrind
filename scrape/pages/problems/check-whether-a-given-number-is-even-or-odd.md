# Check whether a Given Number is Even or Odd · FAANGrind

Source: https://faangrind.vercel.app/problems/check-whether-a-given-number-is-even-or-odd

[All problems](/problems)

#175Medium· asked at 1 company

# Check whether a Given Number is Even or Odd

[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given an integer `N` (which may be negative), return `"Even"` if it is divisible by 2 and `"Odd"` otherwise. Solve it **without using the modulo or division operator** as a follow-up.

## Input / Output

* **Input:** integer `N`.
* **Output:** the string `"Even"` or `"Odd"`.

## Examples

| N | Output |
| --- | --- |
| 4 | Even |
| 7 | Odd |
| 0 | Even |
| -3 | Odd |
| -10 | Even |

## Constraints

* `-10^18 <= N <= 10^18`

## Approach

**Modulo.** `N % 2 == 0` → even. Beware that in C, C++, Java and JavaScript the result of `%` for a negative operand can be `-1`, so test `N % 2 == 0` rather than `N % 2 == 1`.

**Bitwise (preferred).** In two's-complement representation the least-significant bit is 1 for every odd number and 0 for every even number, positive or negative. So:

```
if (N & 1) == 0: Even else Odd
```

This is branch-free, works for negatives without special cases, and is what the follow-up is looking for.

**Other tricks worth mentioning.**

* `(N >> 1) << 1 == N` — shifting right then left clears the lowest bit; equality means it was already 0.
* `N ^ 1 == N + 1` holds only for even `N`.

## Complexity

* **Time:** O(1)
* **Space:** O(1)

## Interview angle

The question is a warm-up used to move into bit manipulation: expect follow-ups such as checking whether a number is a power of two (`N & (N-1) == 0`), counting set bits, or finding the single odd-occurring element with XOR.

## Reference solution (Python)

```
def parity(n: int) -> str:
    return "Even" if (n & 1) == 0 else "Odd"
```

## Test cases

| Input | Expected |
| --- | --- |
| `4` | `Even` |
| `7` | `Odd` |
| `0` | `Even` |
| `-3` | `Odd` |

[PreviousCheck Whether a Floating-Point Number is Even or Odd](/problems/check-whether-a-floating-point-number-is-even-or-odd)[NextCheck Whether a Number is Positive or Negative](/problems/check-whether-a-number-is-positive-or-negative)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/amazon.ico)Amazon#162 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   6/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Check%20whether%20a%20Given%20Number%20is%20Even%20or%20Odd%20dsa)

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
