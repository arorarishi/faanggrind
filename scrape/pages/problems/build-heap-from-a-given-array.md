# Build heap from a given Array · FAANGrind

Source: https://faangrind.vercel.app/problems/build-heap-from-a-given-array

[All problems](/problems)

#118Medium· asked at 9 companies

# Build heap from a given Array

[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)+3 more

## Problem

Given an integer array `arr` of size `n`, rearrange it **in place** so that it satisfies the **max-heap** property: for every index `i`, `arr[i] >= arr[2i+1]` and `arr[i] >= arr[2i+2]` where those indices exist. Do it in **O(n)** time, not O(n log n).

## Input / Output

* **Input:** integer array `arr`.
* **Output:** the array arranged as a max-heap (any valid arrangement is accepted).

## Examples

**Example 1**
Input: `arr = [1, 3, 5, 4, 6, 13, 10, 9, 8, 15, 17]`
Output: `[17, 15, 13, 9, 6, 5, 10, 4, 8, 3, 1]`
Explanation: The root 17 is the maximum; every parent is >= its children.

**Example 2**
Input: `arr = [2, 1]`
Output: `[2, 1]`

## Constraints

* `1 <= n <= 10^6`

## Approach

**Why not insert one at a time?** Inserting `n` elements with sift-up costs O(n log n) in the worst case.

**Bottom-up construction (Floyd's method).** Indices `n/2 .. n-1` are leaves and trivially satisfy the heap property. Process the internal nodes from the last one (`n/2 - 1`) down to 0, calling `siftDown(i)` on each:

```
siftDown(i):
    while true:
        l = 2i + 1; r = 2i + 2; largest = i
        if l < n and arr[l] > arr[largest]: largest = l
        if r < n and arr[r] > arr[largest]: largest = r
        if largest == i: break
        swap(arr[i], arr[largest]); i = largest
```

When we reach node `i`, both of its subtrees are already heaps, so a single sift-down restores the property for the subtree rooted at `i`.

**Why it is O(n).** A node at height `h` sifts down at most `h` levels, and there are about `n / 2^(h+1)` nodes at height `h`. Total work ≈ `Σ h · n / 2^(h+1)`, and `Σ h / 2^h` converges to 2, so the sum is O(n). Being able to state this bound is the main thing interviewers look for.

## Complexity

* **Time:** O(n)
* **Space:** O(1)

## Related

Heap sort (build heap, then repeatedly extract the max), building a priority queue from a bulk collection, and the "k-th largest element" problem where an O(n) build followed by k extractions beats sorting.

## Reference solution (Python)

```
def sift_down(arr, n, i):
    while True:
        l, r, big = 2 * i + 1, 2 * i + 2, i
        if l < n and arr[l] > arr[big]: big = l
        if r < n and arr[r] > arr[big]: big = r
        if big == i: return
        arr[i], arr[big] = arr[big], arr[i]
        i = big

def build_heap(arr):
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        sift_down(arr, n, i)
    return arr

def is_max_heap(arr):
    n = len(arr)
    return all(arr[i] >= arr[c] for i in range(n) for c in (2*i+1, 2*i+2) if c < n)
```

## Test cases

| Input | Expected |
| --- | --- |
| `[1,3,5,4,6,13,10,9,8,15,17]` | `[17,15,13,9,6,5,10,4,8,3,1]` |
| `[2,1]` | `[2,1]` |
| `[1,2,3]` | `[3,2,1]` |
| `is_max_heap([10,5,3,4,1])` | `true` |

[PreviousBroken Calculator](/problems/broken-calculator)[NextBuilding H2O](/problems/building-h2o)

Saved in this browser. No account needed.

## Asked at

9 companies

* [![](/logos/atlassian.ico)Atlassian#21 in list](/companies/atlassian)
* [![](/logos/goldman-sachs.png)Goldman Sachs#31 in list](/companies/goldman-sachs)
* [![](/logos/american-express.png)American Express#80 in list](/companies/american-express)
* [![](/logos/paypal.png)PayPal#119 in list](/companies/paypal)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#139 in list](/companies/palo-alto-networks)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#155 in list](/companies/jpmorgan-chase)
* [![](/logos/swiggy.png)Swiggy#159 in list](/companies/swiggy)
* [![](/logos/apple.ico)Apple#196 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#270 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   21/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)[Heaps](/topics?open=heaps#heaps)

[Solution](https://www.youtube.com/results?search_query=Build%20heap%20from%20a%20given%20Array%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#788Kadane's AlgorithmMedium](/problems/kadane-s-algorithm)
* [#53 SumMedium](/problems/3-sum)
* [#1678Rotten OrangesMedium](/problems/rotten-oranges)
* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
* [#1134Merge K sorted ListsMedium](/problems/merge-k-sorted-lists)
