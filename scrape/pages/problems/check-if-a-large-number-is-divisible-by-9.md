# Check if a Large Number is Divisible by 9 · FAANGrind

Source: https://faangrind.vercel.app/problems/check-if-a-large-number-is-divisible-by-9

[All problems](/problems)

#150Easy· asked at 1 company

# Check if a Large Number is Divisible by 9

[![](/logos/salesforce.ico)Salesforce](/companies/salesforce)

## Problem

You are given a very large non-negative integer `num` as a **string** (it can have up to 10^5 digits, far beyond any built-in integer type). Determine whether it is divisible by 9. Return `true` or `false`.

## Input / Output

* **Input:** string `num` of decimal digits, no leading `+`/`-`.
* **Output:** boolean.

## Examples

| num | Output | Why |
| --- | --- | --- |
| `"123456789"` | `true` | digit sum 45, divisible by 9 |
| `"99999999999999999999"` | `true` | digit sum 180 |
| `"1234"` | `false` | digit sum 10 |
| `"0"` | `true` | 0 is divisible by 9 |

## Constraints

* `1 <= num.length <= 10^5`

## Approach

Converting the string to an integer is impossible in fixed-width types and slow in big-integer types. Use the **divisibility rule**: because `10 ≡ 1 (mod 9)`, every power of ten is `≡ 1 (mod 9)`, so a number is congruent to its **digit sum** modulo 9. Hence `num` is divisible by 9 iff the sum of its digits is divisible by 9.

1. Sum the digits (`ord(c) - 48`).
2. Return `sum % 9 == 0`.

The same reasoning gives the rules for 3 (digit sum) and 11 (alternating digit sum, because `10 ≡ -1 (mod 11)`). A general "large number mod m" check keeps a running remainder `r = (r * 10 + d) % m`, which works for any `m` and is the natural follow-up.

## Complexity

* **Time:** O(n) digits
* **Space:** O(1)

## Reference solution (Python)

```
def divisible_by_9(num: str) -> bool:
    return sum(ord(c) - 48 for c in num) % 9 == 0

def large_mod(num: str, m: int) -> int:
    r = 0
    for c in num:
        r = (r * 10 + ord(c) - 48) % m
    return r
```

## Test cases

| Input | Expected |
| --- | --- |
| `"123456789"` | `true` |
| `"1234"` | `false` |
| `"0"` | `true` |
| `large_mod("123456789", 9)` | `0` |

[PreviousChange Every Letter with the Next Lexicographic](/problems/change-every-letter-with-the-next-lexicographic)[NextCheck if a Number is a Harshad (Niven) Number](/problems/check-if-a-number-is-a-harshad-niven-number)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/salesforce.ico)Salesforce#40 in list](/companies/salesforce)

## Details

Difficulty
:   Easy

Popularity
:   14/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Check%20if%20a%20Large%20Number%20is%20Divisible%20by%209%20dsa)

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
