# Convert Binary to Decimal · FAANGrind

Source: https://faangrind.vercel.app/problems/convert-binary-to-decimal

[All problems](/problems)

#240Medium· asked at 1 company

# Convert Binary to Decimal

[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)

## Problem

Given a string `b` representing a binary number (digits `0` and `1` only), return its decimal value as an integer. The string may be long enough that you must be careful about overflow; a follow-up asks for the value modulo `10^9 + 7`, and another asks to solve it **without** using built-in base conversion.

## Input / Output

* **Input:** binary string `b`.
* **Output:** integer (or integer mod `10^9+7` for the long version).

## Examples

| b | Output |
| --- | --- |
| `"101"` | 5 |
| `"1111"` | 15 |
| `"0"` | 0 |
| `"100000"` | 32 |

## Constraints

* `1 <= b.length <= 10^5`
* `b` has no leading `+`/`-`; leading zeros are allowed.

## Approach

**Horner's method (left to right).** Maintain `value = 0`; for each bit `d`, set `value = value * 2 + d`. Each step shifts the accumulated value one binary place left and adds the new bit. This is O(n) with a single pass and no need to know the length up front. Using bit operations: `value = (value << 1) | d`.

**Right to left with powers.** Walk from the last character, adding `d * 2^i` for position `i`. Equivalent but needs a running power.

**Overflow.** A 64-bit integer holds at most 63 bits, so for long strings either use arbitrary-precision integers (Python) or reduce modulo `M` at each step: `value = (value * 2 + d) % M`. The modular version is what appears in contest settings.

**Validation.** Reject characters other than `0`/`1` if the input is untrusted.

## Complexity

* **Time:** O(n)
* **Space:** O(1)

## Reference solution (Python)

```
def binary_to_decimal(b: str) -> int:
    value = 0
    for c in b:
        value = (value << 1) | (ord(c) - 48)
    return value

def binary_to_decimal_mod(b: str, M: int = 10**9 + 7) -> int:
    value = 0
    for c in b:
        value = (value * 2 + (ord(c) - 48)) % M
    return value
```

## Test cases

| Input | Expected |
| --- | --- |
| `"101"` | `5` |
| `"1111"` | `15` |
| `"0"` | `0` |
| `binary_to_decimal_mod("1"*40)` | `(2**40-1) % (10**9+7) = 511620082` |

[PreviousConcatenate Non-Zero Digits and Multiply by Sum I](/problems/concatenate-non-zero-digits-and-multiply-by-sum-i)[NextCount Subarrays With More Ones Than Zeros](/problems/count-subarrays-with-more-ones-than-zeros)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#106 in list](/companies/walmart-global-tech)

## Details

Difficulty
:   Medium

Popularity
:   12/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Convert%20Binary%20to%20Decimal%20dsa)

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
