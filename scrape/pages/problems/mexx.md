# MEXX · FAANGrind

Source: https://faangrind.vercel.app/problems/mexx

[All problems](/problems)

#1142Medium· asked at 7 companies

# MEXX

[![](/logos/jpmorgan-chase.png)JPMorgan Chase](/companies/jpmorgan-chase)[![](/logos/american-express.png)American Express](/companies/american-express)[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/palo-alto-networks.png)Palo Alto Networks](/companies/palo-alto-networks)[![](/logos/goldman-sachs.png)Goldman Sachs](/companies/goldman-sachs)[![](/logos/amazon.ico)Amazon](/companies/amazon)+1 more

## Problem

The **MEX** (minimum excluded value) of a collection of non-negative integers is the smallest non-negative integer that does **not** appear in it. For example, MEX of `{0, 1, 3}` is 2 and MEX of `{1, 2}` is 0.

You are given an array `arr` of `n` non-negative integers. Answer the following (the full problem typically asks for the third; the first two are its building blocks):

1. The MEX of the whole array.
2. The MEX of every **prefix** `arr[0..i]`.
3. Given `q` **updates** of the form `arr[i] = v`, output the MEX of the whole array after each update.

## Input / Output

* **Input:** array `arr`, then `q` updates `(i, v)`.
* **Output:** MEX after each update (or the prefix MEX array, depending on the version).

## Examples

**Example 1 (whole array)**
Input: `arr = [3, 0, 1, 5]`
Output: `2`

**Example 2 (prefix MEX)**
Input: `arr = [1, 0, 2, 4, 3]`
Output: `[0, 2, 3, 3, 5]`

**Example 3 (with updates)**
Input: `arr = [0, 1, 2]`, updates `(1, 5)`, `(1, 1)`
Output: `1, 3`
Explanation: After setting index 1 to 5 the array is `[0, 5, 2]` → MEX 1. Restoring it gives `[0, 1, 2]` → MEX 3.

## Constraints

* `1 <= n, q <= 2 * 10^5`
* `0 <= arr[i], v <= 10^9`

## Approach

**Key observation.** The MEX of `n` elements is at most `n`, so values above `n` can be ignored — they can never be the MEX and never block a smaller one.

**Static MEX in O(n).** Use a boolean/count array `seen[0..n]`; mark each value `<= n`; return the first index that is not marked.

**Prefix MEX in O(n).** Maintain the same `seen` array and a pointer `mex` that only moves forward: after adding each element, `while seen[mex]: mex++`. Since `mex` never decreases, the total pointer movement is O(n).

**MEX with point updates.** Keep `cnt[v]` for `v <= n` and a **min-heap (or ordered set)** of all values in `0..n` whose count is zero. Initially insert every absent value. On update `arr[i] = v`:

* Decrement `cnt[old]`; if it becomes 0 and `old <= n`, insert `old` into the set.
* Increment `cnt[v]`; if `v <= n` and it was 0, remove `v` from the set.
* The MEX is the minimum of the set (always non-empty because the set contains at least one value in `0..n`).

## Complexity

* Static / prefix: O(n) time, O(n) space.
* With updates: O((n + q) log n) time, O(n) space.

## Variants worth knowing

* **MEX of every subarray** or **count subarrays with MEX = k** uses a sliding window plus the monotone pointer.
* **Maximum MEX after at most k operations** (increment elements) is a greedy on sorted values.

## Reference solution (Python)

```
import heapq

def mex(arr):
    n = len(arr)
    seen = [False] * (n + 1)
    for v in arr:
        if v <= n:
            seen[v] = True
    return next(i for i in range(n + 1) if not seen[i])

def prefix_mex(arr):
    n = len(arr)
    seen = [False] * (n + 2)
    m, out = 0, []
    for v in arr:
        if v <= n:
            seen[v] = True
        while seen[m]:
            m += 1
        out.append(m)
    return out

def mex_with_updates(arr, updates):
    n = len(arr)
    cnt = [0] * (n + 1)
    for v in arr:
        if v <= n:
            cnt[v] += 1
    absent = [v for v in range(n + 1) if cnt[v] == 0]
    heapq.heapify(absent)
    gone = set()                     # lazy deletion
    out = []
    for i, v in updates:
        old = arr[i]
        if old <= n:
            cnt[old] -= 1
            if cnt[old] == 0:
                heapq.heappush(absent, old)
                gone.discard(old)
        arr[i] = v
        if v <= n:
            if cnt[v] == 0:
                gone.add(v)
            cnt[v] += 1
        while absent[0] in gone:
            heapq.heappop(absent)
        out.append(absent[0])
    return out
```

## Test cases

| Input | Expected |
| --- | --- |
| `mex([3,0,1,5])` | `2` |
| `prefix_mex([1,0,2,4,3])` | `[0,2,3,3,5]` |
| `mex_with_updates([0,1,2], [(1,5),(1,1)])` | `[1,3]` |
| `mex([])` | `0` |

[PreviousMetrics Monitoring & Alerting System (Datadog / Prometheus)](/problems/metrics-monitoring-alerting)[NextMice and Cheese](/problems/mice-and-cheese)

Saved in this browser. No account needed.

## Asked at

7 companies

* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#22 in list](/companies/jpmorgan-chase)
* [![](/logos/american-express.png)American Express#49 in list](/companies/american-express)
* [![](/logos/paypal.png)PayPal#53 in list](/companies/paypal)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#91 in list](/companies/palo-alto-networks)
* [![](/logos/goldman-sachs.png)Goldman Sachs#92 in list](/companies/goldman-sachs)
* [![](/logos/amazon.ico)Amazon#108 in list](/companies/amazon)
* [![](/logos/atlassian.ico)Atlassian#113 in list](/companies/atlassian)

## Details

Difficulty
:   Medium

Popularity
:   20/100

Source
:   Full statement on FAANGrind

Topics
:   [Arrays](/topics?open=arrays#arrays)[Hashing](/topics?open=hashing#hashing)

[Solution](https://www.youtube.com/results?search_query=MEXX%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#934LRU CacheMedium](/problems/lru-cache)
* [#788Kadane's AlgorithmMedium](/problems/kadane-s-algorithm)
* [#53 SumMedium](/problems/3-sum)
* [#1678Rotten OrangesMedium](/problems/rotten-oranges)
* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
