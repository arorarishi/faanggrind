# Brute-force cosine top-k search — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/cosine-top-k-search

[AI problems](/ai#problems)

MLCODEImplement it#35Easy

# Brute-force cosine top-k search

cosine similaritynearest neighbournumpytop-kembeddings

## Problem statement

Implement exact nearest neighbour search with NumPy. Given a corpus of N embedding vectors and a batch of Q query vectors, return for every query the indices and cosine similarities of its k most similar corpus vectors, best first. This is the "flat index" inside every vector database and the ground truth that approximate indexes are measured against. The interviewer wants one matrix product in place of Python loops, a top k that does not sort all N scores, and correct handling of zero vectors and ties.

## Requirements

### Functional

* `normalize_rows(x)` scales every row to length 1 and leaves a zero row as zeros.
* `top_k_desc(scores, k)` returns the k largest entries of each row, best first, without a full sort.
* `cosine_top_k(queries, corpus, k)` returns indices `(Q, k)` and scores `(Q, k)`, accepts one query or a batch, and processes queries in batches of `batch_size`.
* A flag skips normalising the corpus when the caller has already done it once.
* A slow loop version computes the same answer straight from the cosine formula, and the self-checks compare the two.

### Non-functional

* 0 Python loops over vectors. The only loop is over query batches.
* 100 queries against 100,000 vectors of 128 dimensions, top 10, in under 1 second on a laptop CPU.
* Same ids as the loop version and scores within 1e-5 of it, in float32.
* Selection costs O(N + k log k) per query, not O(N log N).
* Working memory is at most `batch_size` x N x 12 bytes on top of the corpus: 4 bytes per float32 score and 8 per int64 index.
* No `nan` or `inf` in the output for any finite input, including zero vectors.

## API

```
def normalize_rows(x: np.ndarray, dtype=np.float32) -> np.ndarray: ...
    # (rows, d) or (d,) -> (rows, d), every non-zero row has length 1

def top_k_desc(scores: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]: ...
    # scores (rows, n) -> indices (rows, k) int64, values (rows, k), best first

def cosine_top_k(
    queries: np.ndarray,                 # (Q, d) or (d,)
    corpus: np.ndarray,                  # (N, d)
    k: int,
    corpus_is_normalized: bool = False,  # True: skip the O(N d) normalisation
    batch_size: int = 256,               # queries scored per matrix product
) -> tuple[np.ndarray, np.ndarray]: ...  # indices (Q, k) int64, scores (Q, k) float32

def cosine_top_k_slow(queries, corpus, k): ...   # reference with Python loops
```

## Data model

```
corpus    (N, d) float32     one embedding per row; normalised once, reused for every query
queries   (Q, d) float32     normalised per call
batch     (B, d)             B = batch_size queries, a slice of queries
scores    (B, N) float32     batch @ corpus.T; scores[i, j] = cosine(query i, vector j)
part      (B, k) int64       ids of the k largest scores per row, in no particular order
indices   (Q, k) int64       ids sorted by score, best first; equal scores by lower id
values    (Q, k) float32     the matching cosine similarities, each in [-1, 1]

Sizes for N = 1,000,000 and d = 768:
corpus    1,000,000 x 768 x 4 bytes  = 3.07 GB
scores    256 x 1,000,000 x 4 bytes  = 1.02 GB per batch
```

## Approach

1. Normalise the corpus once: divide every row by its L2 norm (the square root of the sum of its squares). Replace a norm of 0 by 1 before dividing, so a zero row stays zero and never becomes `nan`.
2. Normalise the queries the same way. Cast both to float32: it halves memory compared with float64 and the matrix product runs faster.
3. Take a batch of B queries and compute `scores = batch @ corpus.T`. After step 1 and 2 every entry of this (B, N) matrix is a cosine similarity. One call to the BLAS matrix product replaces B x N Python-level dot products.
4. Select the top k per row with `np.argpartition(scores, N - k, axis=1)[:, N - k:]`. This moves the k largest scores to the end of each row in O(N) time. Their order inside that block is undefined.
5. Sort only those k: gather their scores with `np.take_along_axis`, then order by score descending and by index ascending for equal scores (`np.lexsort`).
6. Write the batch result into the output arrays and move to the next batch. The batch size caps the score matrix at B x N numbers.
7. Clamp k to N. When k equals N there is nothing to select, so skip step 4 and sort the row.
8. Write the slow version from the definition, cosine = a.b / (|a| |b|), with a Python loop and a full sort. Test the fast version against it, then test properties: scale invariance, self-match, zero vectors, ties, and batch size not changing the answer.

## Architecture diagram

Rendering diagram…

## Deep dives

### Normalise first, then cosine is a dot product

Cosine similarity is a.b / (|a| |b|). If both vectors already have length 1 the denominator is 1, so cosine equals the dot product, and all Q x N dot products are one matrix product. The corpus is normalised once at indexing time, not once per query.

### argpartition against a full sort

Sorting N scores costs O(N log N) and orders all of them, but only k are needed. `argpartition` uses a selection algorithm that runs in O(N), then sorting k items costs O(k log k). For N = 1,000,000 and k = 10 that is about 1 million steps against 20 million.

### Zero vectors and ties

A zero vector has norm 0, and 0 / 0 is `nan`, which then poisons every comparison. Treat its norm as 1 so it scores 0 against everything. Ties: the order of equal scores inside the top k is fixed by index here, but which of several equal scores at the cut-off gets in is arbitrary, because the selection is not stable.

### Memory

The corpus is small next to the temporaries. `scores` holds B x N float32 values, and `argpartition` returns an int64 index for each one: 12 bytes per score. With B = 256 and N = 1,000,000 that is 3 GB, so lower B as N grows.

### When to stop using brute force

Each query costs N x d multiply-adds: 768 million for 1,000,000 vectors of 768 dimensions. That is acceptable for offline jobs and for corpora up to about a million vectors. Beyond that, or at high query rates, use an approximate index such as HNSW or IVF, and keep this function to measure its recall.

## Evaluation

**Correctness tests.**

* Agreement with the loop version: the same k ids for every query and scores within 1e-5. Use random vectors with mixed lengths, so a missing normalisation shows up.
* Scores in each row never increase from left to right.
* Scale invariance: multiplying queries by 1,000 and the corpus by 0.001 does not change any id.
* Self-match: searching the corpus against itself returns each vector as its own top hit with score 1.
* Zero vectors: a zero query gives k scores of exactly 0, and a zero row in the corpus never produces `nan`.
* Ties: on hand-written score rows, equal scores come back in index order. One row has 12 entries, because on a very short row `argpartition` may leave the ties in index order by luck.
* Batching: batch sizes 7 and 256 and a single 1-D query give identical output.
* k larger than N returns N results.

**Complexity.** Time O(Q N d) for the product plus O(Q (N + k log k)) for selection. Memory O(N d) for the corpus plus O(B N) working space. The product dominates: with d = 128 it is 128 multiply-adds per score, against a handful of comparisons for selection.

**What a strong answer adds.** Saying that the result is exact, so its recall is 1.0 and it is the ground truth for Recall@k of any approximate index. Normalising the corpus once and storing it. Choosing float32 on purpose. Pointing out that the same matrix product runs on a GPU, and that inner-product search and Euclidean search on unit vectors give the same ranking, because |a - b|^2 = 2 - 2 a.b.

## Bottlenecks & mitigations

* The matrix product: Q x N x d multiply-adds, all of the real work. It is limited by memory bandwidth once the corpus no longer fits in the CPU cache.
* The (B, N) score matrix and the (B, N) int64 index array from `argpartition`, allocated again for every batch.
* Normalising the corpus on every call. Do it once and pass `corpus_is_normalized=True`.
* float64 input: twice the memory and a slower product than float32.
* One process and one machine: there is no way to add a filter, an insert or a delete without touching the whole matrix.

## Failure modes

* **Corpus not normalised.** The product then ranks by dot product, and long vectors win. Mitigation: the scale-invariance test, and one clear owner for normalisation.
* **Division by a zero norm.** One empty document creates a `nan` row, and `nan` breaks ordering for every query. Mitigation: replace zero norms by 1 and test with a zero vector.
* **Assuming argpartition output is sorted.** The k results are the right set in the wrong order. Mitigation: sort the k and test that scores never increase along a row.
* **Smallest k returned by mistake.** Partitioning at k without negating or using N - k returns the least similar vectors. Mitigation: the self-match test fails at once.
* **Out of memory on a large query batch.** Q x N scores are allocated in one go. Mitigation: the batch loop, with B chosen from N and the 12 bytes per score.
* **k larger than N.** `N - k` is negative, so `argpartition` raises an error or quietly selects the wrong number of items. Mitigation: clamp k and test it.
* **Flaky tests from ties.** Two equal scores at the cut-off may swap between runs or library versions. Mitigation: compare scores, not ids, when ties are possible, and break ties by index inside the top k.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""Brute-force cosine top-k search in NumPy: normalise, one matrix product, argpartition."""
import time

import numpy as np

def normalize_rows(x, dtype=np.float32):
    """Scale every row to length 1. A zero row stays zero, so it scores 0 against everything."""
    x = np.atleast_2d(np.asarray(x, dtype=dtype))
    norms = np.linalg.norm(x, axis=1, keepdims=True)       # (rows, 1)
    norms[norms == 0.0] = 1.0                              # avoid 0 / 0 = nan
    return x / norms

def top_k_desc(scores, k):
    """Indices and values of the k largest entries of each row, best first.

    argpartition is O(n) per row and leaves the k largest in the last k slots in no
    particular order; only those k are then sorted, O(k log k). Equal scores inside
    the top k are ordered by lower index. Which of several equal scores at the
    cut-off gets in is arbitrary, because the selection is not stable.
    """
    n = scores.shape[1]
    k = min(k, n)
    if k == n:                                             # nothing to select
        part = np.broadcast_to(np.arange(n), scores.shape)
    else:
        part = np.argpartition(scores, n - k, axis=1)[:, n - k:]   # (rows, k), unordered
    part_scores = np.take_along_axis(scores, part, axis=1)
    order = np.lexsort((part, -part_scores), axis=1)       # by score down, then index up
    idx = np.take_along_axis(part, order, axis=1)
    return idx, np.take_along_axis(part_scores, order, axis=1)

def cosine_top_k(queries, corpus, k, corpus_is_normalized=False, batch_size=256):
    """queries (q, d) or (d,), corpus (n, d) -> (indices (q, k), scores (q, k)).

    Scores are cosine similarities, best first. Queries are processed in batches so
    the score matrix never holds more than batch_size x n numbers.
    """
    c = np.asarray(corpus, dtype=np.float32) if corpus_is_normalized else normalize_rows(corpus)
    q = normalize_rows(queries)
    assert q.shape[1] == c.shape[1], "queries and corpus must have the same dimension"
    k = min(k, c.shape[0])
    idx = np.empty((q.shape[0], k), dtype=np.int64)
    val = np.empty((q.shape[0], k), dtype=np.float32)
    for start in range(0, q.shape[0], batch_size):         # loop over batches, not vectors
        scores = q[start:start + batch_size] @ c.T         # (b, n): every cosine in one product
        idx[start:start + batch_size], val[start:start + batch_size] = top_k_desc(scores, k)
    return idx, val

def cosine_top_k_slow(queries, corpus, k):
    """Reference: one pair at a time, straight from the cosine formula, then a full sort."""
    out_idx, out_val = [], []
    for q in np.atleast_2d(np.asarray(queries, dtype=np.float64)):
        row = []
        for i, c in enumerate(np.asarray(corpus, dtype=np.float64)):
            denom = np.sqrt(q @ q) * np.sqrt(c @ c)
            cos = q @ c / denom if denom > 0 else 0.0
            row.append((-cos, i))
        row.sort()                                         # by score down, then index up
        out_idx.append([i for _, i in row[:k]])
        out_val.append([-s for s, _ in row[:k]])
    return np.array(out_idx), np.array(out_val)

if __name__ == "__main__":
    rng = np.random.default_rng(0)
    corpus = rng.normal(size=(500, 32)) * rng.uniform(0.1, 10.0, size=(500, 1))   # mixed lengths
    queries = rng.normal(size=(20, 32))

    idx, val = cosine_top_k(queries, corpus, k=10)
    slow_idx, slow_val = cosine_top_k_slow(queries, corpus, k=10)
    assert idx.shape == (20, 10) and val.shape == (20, 10)
    assert np.array_equal(idx, slow_idx) and np.allclose(val, slow_val, atol=1e-5)
    assert np.all(np.diff(val, axis=1) <= 0)
    print("matches the loop version: same 10 ids for 20 queries, scores within 1e-5, best first")

    idx_b, val_b = cosine_top_k(queries, corpus, k=10, batch_size=7)
    assert np.array_equal(idx, idx_b) and np.allclose(val, val_b, atol=1e-6)
    one_idx, _ = cosine_top_k(queries[0], corpus, k=10)                 # a single 1-D query
    assert np.array_equal(one_idx[0], idx[0])
    print("batching ok: batches of 7 and a single 1-D query give the same answer")

    self_idx, self_val = cosine_top_k(corpus, corpus, k=1)
    assert np.array_equal(self_idx[:, 0], np.arange(500)) and np.allclose(self_val, 1.0, atol=1e-5)
    scaled_idx, _ = cosine_top_k(queries * 1000.0, corpus * 0.001, k=10)
    assert np.array_equal(scaled_idx, idx)
    print("cosine ok: every vector is its own nearest neighbour with score 1; length does not matter")

    corpus_z = corpus.copy()
    corpus_z[3] = 0.0                                                   # a zero vector in the corpus
    _, z_val = cosine_top_k(np.zeros((1, 32)), corpus_z, k=5)           # and a zero query
    assert np.all(z_val == 0.0)
    all_idx, all_val = cosine_top_k(queries, corpus_z, k=999)           # k above n is clamped
    assert all_val.shape == (20, 500) and np.all(np.isfinite(all_val))
    assert np.all(all_val[all_idx == 3] == 0.0)
    print("zero vectors ok: a zero query scores", z_val[0].tolist(), "and nothing is nan; k=999 returns 500")

    ties = np.array([[0.5, 0.9, 0.9, 0.1, 0.9], [0.3, 0.3, 0.3, 0.3, 0.3]], dtype=np.float32)
    t_idx, _ = top_k_desc(ties, 3)
    assert t_idx[0].tolist() == [1, 2, 4]                               # all three 0.9s, by index
    long_row = np.array([[0.9, 0.1, 0.2, 0.9, 0.3, 0.4, 0.9, 0.5, 0.6, 0.7, 0.9, 0.8]], dtype=np.float32)
    assert top_k_desc(long_row, 5)[0][0].tolist() == [0, 3, 6, 10, 11]  # argpartition returns the 0.9s out of order
    c_idx, c_val = top_k_desc(ties, 2)                                  # the cut-off splits a tie
    assert np.all(c_val[0] == np.float32(0.9)) and set(c_idx[0].tolist()) < {1, 2, 4}
    assert np.all(np.diff(c_idx, axis=1) > 0)
    print("ties ok: equal scores come back in index order", t_idx[0].tolist(),
          "| a tie at the cut-off kept", c_idx[0].tolist())

    n, d, nq = 100_000, 128, 100
    big = normalize_rows(rng.normal(size=(n, d)))
    qs = rng.normal(size=(nq, d))
    t0 = time.perf_counter()
    fast_idx, _ = cosine_top_k(qs, big, k=10, corpus_is_normalized=True)
    t_search = time.perf_counter() - t0
    scores = normalize_rows(qs) @ big.T
    t0 = time.perf_counter()
    top_k_desc(scores, 10)
    t_part = time.perf_counter() - t0
    t0 = time.perf_counter()
    full = np.argsort(-scores, axis=1)[:, :10]
    t_sort = time.perf_counter() - t0
    assert np.array_equal(full, fast_idx)
    print(f"speed: {nq} queries x {n:,} vectors x {d} dims, top 10 in {t_search:.2f} s")
    print(f"selection only: argpartition {t_part:.3f} s vs full argsort {t_sort:.3f} s; "
          f"score matrix {scores.nbytes / 1e6:.0f} MB")
```

## Follow-up questions interviewers ask

* The corpus has 100 million vectors. What changes, and what do you give up?
* Add a metadata filter, for example "only vectors with category = 3". Where does it go and what does it cost?
* How would you keep a running top k over a corpus that is too large to load, reading it in chunks from disk?
* Change the metric to Euclidean distance. Can you still use one matrix product?
* Queries arrive one at a time at 1,000 per second. How do you keep the benefit of batching?
* How would you use this function to report Recall@10 for an HNSW index?

## Lessons that cover this

* [#8Vector DBs and RAGBuild with LLMs](/ai/learn/vector-dbs-rag)

## Further reading

* [numpy.argpartition (NumPy documentation)Guidenumpy.org](https://numpy.org/doc/stable/reference/generated/numpy.argpartition.html)
* [Billion-scale similarity search with GPUsPaperarxiv.org](https://arxiv.org/abs/1702.08734)
* [Efficient and robust approximate nearest neighbor search using HNSW graphsPaperarxiv.org](https://arxiv.org/abs/1603.09320)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousTemperature, top-k and top-p sampling](/ai/problems/top-k-top-p-sampling)[NextLoRA layer: forward, train and merge](/ai/problems/lora-layer)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Approach](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Evaluation](#evaluation)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Reference solution](#code)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
