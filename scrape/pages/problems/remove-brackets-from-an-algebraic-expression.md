# Remove Brackets from an Algebraic Expression · FAANGrind

Source: https://faangrind.vercel.app/problems/remove-brackets-from-an-algebraic-expression

[All problems](/problems)

#1597Medium· asked at 9 companies

# Remove Brackets from an Algebraic Expression

[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/linkedin.ico)LinkedIn](/companies/linkedin)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)[![](/logos/salesforce.ico)Salesforce](/companies/salesforce)[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)+3 more

## Problem

You are given an algebraic expression `s` containing lowercase variables, the operators `+` and `-`, and possibly nested parentheses `(` `)`. Return an equivalent expression with **all parentheses removed** and the signs adjusted so that the meaning is preserved. The output should not start with a `+`.

## Input / Output

* **Input:** a valid expression string.
* **Output:** the simplified expression string.

## Examples

**Example 1**
Input: `s = "a-(b+c)"`
Output: `"a-b-c"`

**Example 2**
Input: `s = "a-(b-(c-d)+e)"`
Output: `"a-b+c-d-e"`
Explanation: Inside the outer minus, `b` becomes `-b`, `-(c-d)` becomes `+c-d`, `+e` becomes `-e`.

**Example 3**
Input: `s = "(a+b)-(c-d)"`
Output: `"a+b-c+d"`

## Constraints

* `1 <= |s| <= 10^5`
* The expression is well-formed; there is no multiplication or division (only sign propagation matters).

## Approach — Stack of signs

Every character inside a bracket is affected by the sign immediately in front of that bracket, and the effect **compounds** with the enclosing brackets. Keep a stack whose top holds the effective sign (`+1` or `-1`) for the current nesting level.

Walk through the string:

1. Start with the stack containing `+1` and a variable `cur = +1` meaning "the sign to apply to the next operand".
2. On a variable: compute `sign = cur × stack.top`. Output `-` if `sign` is negative, `+` if positive and the output is non-empty, then the variable. Reset `cur = +1`.
3. On `+`: `cur = +1`. On `-`: `cur = -1`.
4. On `(`: push `cur × stack.top` (the sign that applies to everything inside), then reset `cur = +1`.
5. On `)`: pop.

Each character is processed once, so the algorithm is linear.

## Complexity

* **Time:** O(n)
* **Space:** O(depth of nesting) for the stack, plus O(n) for the output.

## Interview notes

* This is a simplified version of "Basic Calculator" (LeetCode 224) where the sign-stack technique is used to evaluate the expression numerically instead of rewriting it.
* Be careful with a leading `-` and with an expression that begins with `(`.
* Follow-up: support multiplication by a constant in front of a bracket, e.g. `2*(a-b)` → `2*a-2*b`, which requires distributing coefficients.

## Reference solution (Python)

```
def remove_brackets(s):
    out = []
    stack = [1]      # effective sign of the current nesting level
    cur = 1          # sign preceding the next operand / bracket
    for c in s:
        if c == '+':
            cur = 1
        elif c == '-':
            cur = -1
        elif c == '(':
            stack.append(cur * stack[-1])
            cur = 1
        elif c == ')':
            stack.pop()
        else:
            sign = cur * stack[-1]
            if sign < 0:
                out.append('-')
            elif out:
                out.append('+')
            out.append(c)
            cur = 1
    return ''.join(out)
```

## Test cases

| Input | Expected |
| --- | --- |
| `"a-(b+c)"` | `"a-b-c"` |
| `"a-(b-(c-d)+e)"` | `"a-b+c-d-e"` |
| `"(a+b)-(c-d)"` | `"a+b-c+d"` |
| `"-(a-b)"` | `"-a+b"` |

[PreviousRansom Note](/problems/ransom-note)[NextShortest path in DAG](/problems/shortest-path-in-dag)

Saved in this browser. No account needed.

## Asked at

9 companies

* [![](/logos/adobe.ico)Adobe#2 in list](/companies/adobe)
* [![](/logos/linkedin.ico)LinkedIn#30 in list](/companies/linkedin)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#50 in list](/companies/walmart-global-tech)
* [![](/logos/salesforce.ico)Salesforce#51 in list](/companies/salesforce)
* [![](/logos/paypal.png)PayPal#70 in list](/companies/paypal)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#138 in list](/companies/jpmorgan-chase)
* [![](/logos/swiggy.png)Swiggy#148 in list](/companies/swiggy)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#167 in list](/companies/palo-alto-networks)
* [![](/logos/amazon.ico)Amazon#384 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   23/100

Source
:   Full statement on FAANGrind

Topics
:   [Strings](/topics?open=strings#strings)[Stack & Queues](/topics?open=stack-and-queues#stack-and-queues)

[Solution](https://www.youtube.com/results?search_query=Remove%20Brackets%20from%20an%20Algebraic%20Expression%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#923Longest Substring Without Repeating CharactersMedium](/problems/longest-substring-without-repeating-characters)
* [#1912Trapping RainwaterMedium](/problems/trapping-rainwater)
* [#909Longest Palindromic SubstringMedium](/problems/longest-palindromic-substring)
* [#1748Sliding Window MaximumMedium](/problems/sliding-window-maximum)
* [#1313Minimum Window SubstringMedium](/problems/minimum-window-substring)
* [#55Asteroid CollisionMedium](/problems/asteroid-collision)
