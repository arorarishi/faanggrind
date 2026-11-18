# Check Whether a Floating-Point Number is Even or Odd · FAANGrind

Source: https://faangrind.vercel.app/problems/check-whether-a-floating-point-number-is-even-or-odd

[All problems](/problems)

#174Medium· asked at 1 company

# Check Whether a Floating-Point Number is Even or Odd

[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

Given a floating-point number `x` provided as a string (e.g. `"42.0"`, `"17.5"`, `"-8.000"`), determine whether it represents an **even** integer, an **odd** integer, or is **not an integer** at all. Return `"Even"`, `"Odd"` or `"Not an integer"`.

The value is passed as a string because reading it into a `double` can lose precision for large magnitudes (e.g. `"12345678901234567891.0"`), and the point of the question is to reason about that.

## Input / Output

* **Input:** a string representing a decimal number, optionally with a sign and a fractional part.
* **Output:** one of the three labels.

## Examples

| Input | Output |
| --- | --- |
| `"42.0"` | Even |
| `"17"` | Odd |
| `"17.5"` | Not an integer |
| `"-8.000"` | Even |
| `"0.0"` | Even |
| `"3.10"` | Not an integer |

## Constraints

* `1 <= |x| <= 100` characters.
* The string is a valid decimal literal.

## Approach

1. Strip a leading `+` or `-` (parity does not depend on sign).
2. Split on the decimal point (if present) into `intPart` and `fracPart`.
3. If `fracPart` contains any non-zero digit, the number is **not an integer**.
4. Otherwise the parity is decided by the **last digit of `intPart`**: even if it is `0, 2, 4, 6, 8`, odd otherwise. Treat an empty `intPart` (e.g. `".0"`) as `0`.

Because only the last integer digit and the fractional digits are inspected, no numeric conversion is needed and the solution is exact for any length.

**If you must work with an actual `double`.** Use `x == floor(x)` (or `modf`) to check integrality, then `fmod(x, 2) == 0` for evenness. Explain in the interview that for `|x| >= 2^53` every double is an even integer (the spacing between representable values is at least 2), so the string approach is the only fully correct one.

## Complexity

* **Time:** O(length of the string)
* **Space:** O(1)

## Why interviewers like it

It looks trivial but exposes whether a candidate knows that floating-point numbers are not exact, that `%` is not defined on floats in some languages, and that parsing beats numeric tricks when precision matters.

## Reference solution (Python)

```
def float_parity(x: str) -> str:
    x = x.strip().lstrip('+-')
    int_part, _, frac_part = x.partition('.')
    if frac_part.strip('0'):
        return "Not an integer"
    last = int_part[-1] if int_part else '0'
    return "Even" if last in "02468" else "Odd"
```

## Test cases

| Input | Expected |
| --- | --- |
| `"42.0"` | `Even` |
| `"17.5"` | `Not an integer` |
| `"-8.000"` | `Even` |
| `"12345678901234567891.0"` | `Odd` |

[PreviousBest Sightseeing Pair](/problems/best-sightseeing-pair)[NextCheck whether a Given Number is Even or Odd](/problems/check-whether-a-given-number-is-even-or-odd)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/amazon.ico)Amazon#486 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   6/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Check%20Whether%20a%20Floating-Point%20Number%20is%20Even%20or%20Odd%20dsa)

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
