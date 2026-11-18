# Pascal's Triangle III · FAANGrind

Source: https://faangrind.vercel.app/problems/pascal-s-triangle-iii

[All problems](/problems)

#1486Medium· asked at 4 companies

# Pascal's Triangle III

[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)

## Problem

This is the third variation of the Pascal's-triangle family:

* **Variation I:** given row `r` and column `c`, return the single element at that position.
* **Variation II:** given `n`, return the entire n-th row.
* **Variation III (this problem):** given `n`, return the **first `n` rows** of Pascal's triangle as a list of lists.

Row `i` (1-based) has `i` elements; the first and last are 1 and every interior element is the sum of the two elements above it.

## Input / Output

* **Input:** integer `n`.
* **Output:** `n` rows.

## Examples

**Example 1**
Input: `n = 5`
Output:

```
[1]
[1, 1]
[1, 2, 1]
[1, 3, 3, 1]
[1, 4, 6, 4, 1]
```

**Example 2**
Input: `n = 1`
Output: `[[1]]`

## Constraints

* `1 <= n <= 30` (values fit in 32-bit; use 64-bit or big integers for larger `n`).

## Approach

**Build from the previous row (O(n²)).** Start with `[1]`. Each new row is `[1] + [prev[i] + prev[i+1] for i in range(len(prev)-1)] + [1]`. Total work equals the number of cells, `n(n+1)/2`.

**Generate each row independently with the binomial recurrence.** Row `r` (0-based) is `C(r, 0), C(r, 1), …, C(r, r)`, and `C(r, k) = C(r, k-1) × (r - k + 1) / k`. This computes any single row in O(r) without the earlier rows, which is what Variation II asks for and is the trick the interviewer wants you to know.

**Why not `C(r, k) = r! / (k!(r-k)!)`?** Factorials overflow quickly and cost O(r) per element, giving O(n³) overall.

## Complexity

* **Time:** O(n²) — optimal, since the output has that many numbers.
* **Space:** O(n²) for the output (O(n) extra if rows are printed as they are generated).

## Reference solution (Python)

```
def pascal_rows(n):
    rows = []
    for r in range(n):
        row = [1] * (r + 1)
        for k in range(1, r):
            row[k] = row[k - 1] * (r - k + 1) // k
        rows.append(row)
    return rows
```

## Test cases

| Input | Expected |
| --- | --- |
| `5` | `[[1],[1,1],[1,2,1],[1,3,3,1],[1,4,6,4,1]]` |
| `1` | `[[1]]` |
| `2` | `[[1],[1,1]]` |
| `6` (last row) | `[1,5,10,10,5,1]` |

[PreviousParallel Courses III](/problems/parallel-courses-iii)[NextPerfect Number](/problems/perfect-number)

Saved in this browser. No account needed.

## Asked at

4 companies

* [![](/logos/apple.ico)Apple#36 in list](/companies/apple)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#151 in list](/companies/walmart-global-tech)
* [![](/logos/adobe.ico)Adobe#166 in list](/companies/adobe)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#173 in list](/companies/jpmorgan-chase)

## Details

Difficulty
:   Medium

Popularity
:   17/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)[Mathematics](/topics?open=mathematics#mathematics)

[Solution](https://www.youtube.com/results?search_query=Pascal's%20Triangle%20III%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#788Kadane's AlgorithmMedium](/problems/kadane-s-algorithm)
* [#53 SumMedium](/problems/3-sum)
* [#1678Rotten OrangesMedium](/problems/rotten-oranges)
* [#890Longest Consecutive Sequence in an ArrayMedium](/problems/longest-consecutive-sequence-in-an-array)
* [#1350Next PermutationMedium](/problems/next-permutation)
