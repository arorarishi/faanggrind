# Calculate the Power of a Number using Binary Exponentiation · FAANGrind

Source: https://faangrind.vercel.app/problems/calculate-the-power-of-a-number-using-binary-exponentiation

[All problems](/problems)

#129Easy· asked at 3 companies

# Calculate the Power of a Number using Binary Exponentiation

[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)

## Problem

Given a base `x` and a non-negative integer exponent `n`, compute `x^n`. Because the result can be enormous, return it modulo `M = 10^9 + 7` when asked (the same technique also solves the floating-point version, `pow(double x, int n)`, including negative `n`).

## Input / Output

* **Input:** integers `x`, `n` (and optionally `M`).
* **Output:** `x^n mod M`.

## Examples

| x | n | Output |
| --- | --- | --- |
| 2 | 10 | 1024 |
| 3 | 0 | 1 |
| 5 | 3 | 125 |
| 2 | 100 (mod 10^9+7) | 976371285 |

## Constraints

* `0 <= x <= 10^9`, `0 <= n <= 10^18`

## Approach

Multiplying `x` by itself `n` times costs O(n) — hopeless for `n = 10^18`. **Binary exponentiation** uses the binary representation of `n`:

`x^n = x^(b_k · 2^k) · … · x^(b_1 · 2) · x^(b_0)` where `b_i` are the bits of `n`.

Keep a running value `base` that squares every step (`x, x², x⁴, x⁸, …`) and multiply it into the result whenever the current bit of `n` is 1:

```
result = 1
while n > 0:
    if n & 1: result = result * base % M
    base = base * base % M
    n >>= 1
```

Each loop iteration halves `n`, so there are O(log n) multiplications. The recursive form `pow(x, n) = pow(x, n/2)² · (x if n odd)` is equivalent.

**Negative exponents (floating point):** compute `pow(x, |n|)` then return `1 / result`.
**Modular inverse:** by Fermat's little theorem, `x^(M-2) mod M` is the inverse of `x` when `M` is prime — this is why the problem is a building block for combinatorics questions.

## Complexity

* **Time:** O(log n)
* **Space:** O(1) iterative, O(log n) recursive.

## Reference solution (Python)

```
def power(x, n, M=10**9 + 7):
    result, base = 1, x % M
    while n > 0:
        if n & 1:
            result = result * base % M
        base = base * base % M
        n >>= 1
    return result

def fpow(x: float, n: int) -> float:
    neg = n < 0
    n, r = abs(n), 1.0
    while n:
        if n & 1: r *= x
        x *= x
        n >>= 1
    return 1 / r if neg else r
```

## Test cases

| Input | Expected |
| --- | --- |
| `power(2,10)` | `1024` |
| `power(3,0)` | `1` |
| `power(2,100)` | `976371285` |
| `fpow(2.0,-2)` | `0.25` |

[PreviousBridges in graph](/problems/bridges-in-graph)[NextCheck if a String Is an Acronym of Words](/problems/check-if-a-string-is-an-acronym-of-words)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#47 in list](/companies/walmart-global-tech)
* [![](/logos/adobe.ico)Adobe#49 in list](/companies/adobe)
* [![](/logos/goldman-sachs.png)Goldman Sachs#193 in list](/companies/goldman-sachs)

## Details

Difficulty
:   Easy

Popularity
:   16/100

Source
:   Full statement on FAANGrind

Topics
:   [Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Calculate%20the%20Power%20of%20a%20Number%20using%20Binary%20Exponentiation%20dsa)

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
