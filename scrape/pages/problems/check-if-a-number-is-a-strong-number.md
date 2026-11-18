# Check if a Number is a Strong Number · FAANGrind

Source: https://faangrind.vercel.app/problems/check-if-a-number-is-a-strong-number

[All problems](/problems)

#153Easy· asked at 1 company

# Check if a Number is a Strong Number

[![](/logos/amazon.ico)Amazon](/companies/amazon)

## Problem

A **strong number** (also called a factorion) is a number that equals the sum of the factorials of its digits. Given a positive integer `N`, return `true` if it is strong, otherwise `false`.

## Input / Output

* **Input:** integer `N`.
* **Output:** boolean.

## Examples

**Example 1**
Input: `N = 145`
Output: `true`
Explanation: `1! + 4! + 5! = 1 + 24 + 120 = 145`.

**Example 2**
Input: `N = 40585`
Output: `true`
Explanation: `4! + 0! + 5! + 8! + 5! = 24 + 1 + 120 + 40320 + 120 = 40585`.

**Example 3**
Input: `N = 123`
Output: `false`
Explanation: `1! + 2! + 3! = 9 ≠ 123`.

## Constraints

* `1 <= N <= 10^9`

## Approach

1. Precompute `fact[0..9]` once: `1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880`.
2. Extract digits of `N` with `% 10` and `/ 10`, summing `fact[digit]`.
3. Compare the sum with the original `N`.

Note that `0! = 1`, which matters for numbers containing a 0 digit.

```
sum = 0; temp = N
while temp > 0:
    sum += fact[temp % 10]
    temp /= 10
return sum == N
```

**Fun fact for the interview.** In base 10 there are exactly four strong numbers: `1, 2, 145, 40585`. Because `9! = 362880`, a number with `d` digits can have digit-factorial sum at most `d · 362880`, which for `d >= 8` is smaller than the smallest `d`-digit number, so no larger strong numbers exist. A cheeky O(1) solution is `return N in {1, 2, 145, 40585}` — mention it, but implement the general check.

## Complexity

* **Time:** O(number of digits) = O(log N)
* **Space:** O(1)

## Related warm-ups

Armstrong (narcissistic) numbers use digit powers instead of factorials; Harshad numbers use the digit sum as a divisor; automorphic numbers compare the square's trailing digits. They are commonly grouped as "digit manipulation" questions.

## Reference solution (Python)

```
FACT = [1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880]

def is_strong(n):
    s, t = 0, n
    while t > 0:
        s += FACT[t % 10]
        t //= 10
    return s == n
```

## Test cases

| Input | Expected |
| --- | --- |
| `145` | `true` |
| `40585` | `true` |
| `123` | `false` |
| `2` | `true` |

[Previous2 Keys Keyboard](/problems/2-keys-keyboard)[NextCheck if a Number is an Abundant Number](/problems/check-if-a-number-is-an-abundant-number)

Saved in this browser. No account needed.

## Asked at

1 companies

* [![](/logos/amazon.ico)Amazon#592 in list](/companies/amazon)

## Details

Difficulty
:   Easy

Popularity
:   10/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Check%20if%20a%20Number%20is%20a%20Strong%20Number%20dsa)

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
