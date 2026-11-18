# Number of Greater Elements to the Right · FAANGrind

Source: https://faangrind.vercel.app/problems/number-of-greater-elements-to-the-right

[All problems](/problems)

#1384Medium· asked at 3 companies

# Number of Greater Elements to the Right

[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/swiggy.png)Swiggy](/companies/swiggy)

## Problem

Given an integer array `arr` of length `n`, return an array `res` where `res[i]` is the number of elements to the **right** of index `i` that are **strictly greater** than `arr[i]`.

## Input / Output

* **Input:** integer array `arr`.
* **Output:** integer array `res` of the same length.

## Examples

**Example 1**
Input: `arr = [3, 7, 1, 5, 9]`
Output: `[3, 1, 2, 1, 0]`
Explanation: Right of 3 → {7, 5, 9} greater; right of 7 → {9}; right of 1 → {5, 9}; right of 5 → {9}; nothing right of 9.

**Example 2**
Input: `arr = [5, 4, 3]`
Output: `[0, 0, 0]`

**Example 3**
Input: `arr = [1, 2, 3]`
Output: `[2, 1, 0]`

## Constraints

* `1 <= n <= 10^5`
* `-10^9 <= arr[i] <= 10^9`

## Approach

**Brute force** is O(n²): for each `i` scan `j > i`. Fine for `n <= 10^4`, too slow beyond.

**Merge-sort counting — O(n log n).** Process indices, not values. During the merge step of merge sort, when an element from the **left** half is placed, every element still remaining in the **right** half that has already been placed before it is smaller… For "greater to the right" it is easier to count while placing right-half elements: sort in *descending* order; when an element from the right half is placed before elements of the left half, it is greater than all of the remaining left-half elements, so add 1 to each of their counts (accumulate via a running counter attached to left-half indices). This is the classic "Count of Smaller Numbers After Self" (LeetCode 315) with the comparison flipped.

**Fenwick tree — O(n log n), simpler to reason about.** Coordinate-compress the values to ranks `1..m`. Scan from right to left; before inserting `arr[i]`, query how many inserted values have rank greater than `rank(arr[i])` — that is `inserted_total - prefix(rank)`. Then add `rank(arr[i])` to the tree. Every query and update is O(log m).

## Complexity

* **Time:** O(n log n)
* **Space:** O(n)

## Reference solution (Python)

```
def greater_to_right(arr):
    ranks = {v: i + 1 for i, v in enumerate(sorted(set(arr)))}
    m = len(ranks)
    tree = [0] * (m + 1)

    def add(i):
        while i <= m:
            tree[i] += 1
            i += i & -i

    def prefix(i):          # count of inserted values with rank <= i
        s = 0
        while i > 0:
            s += tree[i]
            i -= i & -i
        return s

    res = [0] * len(arr)
    inserted = 0
    for i in range(len(arr) - 1, -1, -1):
        r = ranks[arr[i]]
        res[i] = inserted - prefix(r)
        add(r)
        inserted += 1
    return res
```

## Test cases

| Input | Expected |
| --- | --- |
| `[3,7,1,5,9]` | `[3,1,2,1,0]` |
| `[5,4,3]` | `[0,0,0]` |
| `[1,2,3]` | `[2,1,0]` |
| `[2,2,2]` | `[0,0,0]` |

[PreviousNumber of Good Leaf Nodes Pairs](/problems/number-of-good-leaf-nodes-pairs)[NextNumber of Matching Subsequences](/problems/number-of-matching-subsequences)

Saved in this browser. No account needed.

## Asked at

3 companies

* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#11 in list](/companies/jpmorgan-chase)
* [![](/logos/goldman-sachs.png)Goldman Sachs#38 in list](/companies/goldman-sachs)
* [![](/logos/swiggy.png)Swiggy#166 in list](/companies/swiggy)

## Details

Difficulty
:   Medium

Popularity
:   17/100

Source
:   Full statement on FAANGrind

Topics
:   [Stack & Queues](/topics?open=stack-and-queues#stack-and-queues)

[Solution](https://www.youtube.com/results?search_query=Number%20of%20Greater%20Elements%20to%20the%20Right%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1912Trapping RainwaterMedium](/problems/trapping-rainwater)
* [#1748Sliding Window MaximumMedium](/problems/sliding-window-maximum)
* [#55Asteroid CollisionMedium](/problems/asteroid-collision)
* [#819Largest rectangle in a histogramHard](/problems/largest-rectangle-in-a-histogram)
* [#724Implement Min StackMedium](/problems/implement-min-stack)
* [#1615Remove K DigitsMedium](/problems/remove-k-digits)
