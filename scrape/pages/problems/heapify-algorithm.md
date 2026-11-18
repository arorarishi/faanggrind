# Heapify Algorithm · FAANGrind

Source: https://faangrind.vercel.app/problems/heapify-algorithm

[All problems](/problems)

#703Medium· asked at 12 companies

# Heapify Algorithm

[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/adobe.ico)Adobe](/companies/adobe)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/apple.ico)Apple](/companies/apple)[![](/logos/atlassian.ico)Atlassian](/companies/atlassian)+6 more

## Problem

Given an integer array `arr` of size `n`, transform it **in place** into a valid **max-heap**: for every index `i`, `arr[i] >= arr[2i+1]` and `arr[i] >= arr[2i+2]` whenever those children exist. Also implement the `heapify(arr, n, i)` routine that repairs the heap property at a single index assuming both of its subtrees are already heaps.

## Input / Output

* **Input:** an unsorted integer array.
* **Output:** the same array rearranged into a max-heap (any valid heap arrangement is accepted).

## Examples

**Example 1**
Input: `arr = [4, 10, 3, 5, 1]`
Output: `[10, 5, 3, 4, 1]`
Explanation: 10 is the root; its children 5 and 3 are smaller; 5's children 4 and 1 are smaller.

**Example 2**
Input: `arr = [1, 2, 3, 4, 5, 6]`
Output: `[6, 5, 3, 4, 2, 1]`

## Constraints

* `1 <= n <= 10^6`
* `-10^9 <= arr[i] <= 10^9`

## Approach

**The heapify (sift-down) step.** At index `i`, compare `arr[i]` with its left child `2i+1` and right child `2i+2`. Let `largest` be the index of the biggest of the three. If `largest != i`, swap `arr[i]` and `arr[largest]` and recursively heapify at `largest` — the swapped-down value may still violate the property further down. Each call moves down one level, so a single heapify is O(log n).

**Building the heap.** Leaves (indices `n/2` to `n-1`) are trivially heaps. Starting from the last non-leaf index `n/2 - 1` and moving to index 0, call `heapify` on each. Because each node's subtrees are already valid by the time we reach it, the entire array becomes a heap.

**Why building is O(n), not O(n log n).** Most nodes are near the bottom and sift down only a few levels. Summing `(number of nodes at height h) × h` over all heights gives `n × Σ h/2^h`, which converges to a constant times `n`. This is a classic interview follow-up.

## Complexity

* `heapify`: O(log n) time, O(log n) stack (or O(1) iteratively).
* : O(n) time, O(1) extra space.

[PreviousFind Middle of Linked List](/problems/find-middle-of-linked-list)[NextLongest Increasing Path in a Matrix](/problems/longest-increasing-path-in-a-matrix)

Saved in this browser. No account needed.

## Asked at

12 companies

* [![](/logos/paypal.png)PayPal#22 in list](/companies/paypal)
* [![](/logos/adobe.ico)Adobe#29 in list](/companies/adobe)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#45 in list](/companies/walmart-global-tech)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#54 in list](/companies/jpmorgan-chase)
* [![](/logos/apple.ico)Apple#67 in list](/companies/apple)
* [![](/logos/atlassian.ico)Atlassian#116 in list](/companies/atlassian)
* [![](/logos/linkedin.ico)LinkedIn#151 in list](/companies/linkedin)
* [![](/logos/salesforce.ico)Salesforce#151 in list](/companies/salesforce)
* [![](/logos/swiggy.png)Swiggy#154 in list](/companies/swiggy)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#163 in list](/companies/palo-alto-networks)
* [![](/logos/goldman-sachs.png)Goldman Sachs#221 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#532 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   31/100

Source
:   Full statement on FAANGrind

Topics
:   [Heaps](/topics?open=heaps#heaps)

[Solution](https://www.youtube.com/results?search_query=Heapify%20Algorithm%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
* [#1134Merge K sorted ListsMedium](/problems/merge-k-sorted-lists)
* [#534Find Median from Data StreamMedium](/problems/find-median-from-data-stream)
* [#785K-th Largest element in an arrayMedium](/problems/k-th-largest-element-in-an-array)
* [#1870Task SchedulerMedium](/problems/task-scheduler)
* [#1771Sort Characters by FrequencyMedium](/problems/sort-characters-by-frequency)

`buildHeap`

## Related

Heap sort uses `buildHeap` followed by repeatedly swapping the root with the last element and heapifying a shrinking prefix. Priority queues in most languages are implemented exactly this way.

## Reference solution (Python)

```
def heapify(arr, n, i):
    while True:
        largest = i
        l, r = 2 * i + 1, 2 * i + 2
        if l < n and arr[l] > arr[largest]:
            largest = l
        if r < n and arr[r] > arr[largest]:
            largest = r
        if largest == i:
            return
        arr[i], arr[largest] = arr[largest], arr[i]
        i = largest

def build_max_heap(arr):
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        heapify(arr, n, i)
    return arr
```
