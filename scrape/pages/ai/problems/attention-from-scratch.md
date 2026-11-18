# Self-attention from scratch — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/attention-from-scratch

[AI problems](/ai#problems)

MLCODEImplement it#31Medium

# Self-attention from scratch

attentiontransformernumpycausal maskmulti-head

## Problem statement

Implement scaled dot-product attention and a multi-head self-attention layer using only NumPy. Your code must support batches, an optional causal mask so a token cannot look at later tokens, and it must return the attention weights as well as the output. No deep-learning library is allowed; the interviewer wants to see that you know what every tensor shape is.

## Requirements

### Functional

* `scaled_dot_product_attention(q, k, v, mask)` returns the output and the attention weights.
* `causal_mask(n)` returns a lower-triangular boolean mask.
* `MultiHeadSelfAttention(d_model, n_heads)` projects the input to queries, keys and values, splits them into heads, attends, merges the heads and applies an output projection.
* Works on batched input of shape `(batch, tokens, d_model)`.
* Includes self-checks that print what they verify.

### Non-functional

* Fully vectorised: 0 Python loops over tokens or heads.
* A forward pass with batch 8, 512 tokens and d\_model 64 finishes in under 1 second on a laptop CPU.
* Numerically stable: scores as large as 1e4 must not produce NaN or inf.
* Every row of the attention weights sums to 1 within 1e-9.
* With the causal mask, weights above the diagonal are exactly 0 and output at position i does not change when tokens after i change (within 1e-9).

## API

```
def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray: ...

def scaled_dot_product_attention(
    q: np.ndarray,                 # (..., n_q, d_k)
    k: np.ndarray,                 # (..., n_k, d_k)
    v: np.ndarray,                 # (..., n_k, d_v)
    mask: np.ndarray | None = None # broadcastable to (..., n_q, n_k); True = may attend
) -> tuple[np.ndarray, np.ndarray]:  # output (..., n_q, d_v), weights (..., n_q, n_k)
    ...

def causal_mask(n: int) -> np.ndarray: ...   # (n, n) bool, lower triangular

class MultiHeadSelfAttention:
    def __init__(self, d_model: int, n_heads: int, seed: int = 0): ...
    def __call__(self, x: np.ndarray, causal: bool = False) -> tuple[np.ndarray, np.ndarray]: ...
    # x: (b, n, d_model) -> output (b, n, d_model), weights (b, n_heads, n, n)
```

## Data model

```
x        (b, n, d_model)          input token vectors
W_q/k/v  (d_model, d_model)       projection matrices, one each
q, k, v  (b, h, n, d_head)        after split; d_head = d_model / h
scores   (b, h, n, n)             q @ k^T / sqrt(d_head)
mask     (n, n) bool              broadcasts over b and h
weights  (b, h, n, n)             softmax over the last axis
heads    (b, h, n, d_head)        weights @ v
output   (b, n, d_model)          merge heads, then @ W_o
```

## Approach

1. Write a stable `softmax`: subtract the row maximum before `exp`, so the largest exponent is 0.
2. In `scaled_dot_product_attention`, compute `scores = q @ k^T / sqrt(d_k)`. Use `swapaxes(-1, -2)` for the transpose so any number of leading batch dimensions works.
3. Apply the mask by replacing blocked positions with a large negative number (`-1e9`) before the softmax. After softmax those positions are 0.
4. Take the softmax over the last axis to get weights, then `weights @ v` for the output.
5. For multi-head attention, project `x` with `W_q`, `W_k`, `W_v`, then reshape `(b, n, d_model)` to `(b, n, h, d_head)` and transpose to `(b, h, n, d_head)`. Heads become a batch dimension, so step 2 runs for all heads at once.
6. Merge by reversing the transpose and reshape, then multiply by `W_o`.
7. Test properties, not just shapes: rows sum to 1, the causal mask blocks the future, and an unmasked layer is permutation-equivariant.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why divide by the square root of d\_k

A dot product of two d\_k-dimensional vectors with unit-variance entries has variance d\_k. With d\_k = 64 the scores have a standard deviation near 8, and softmax over values that far apart puts almost all weight on one token. Its gradient there is close to zero, so training stalls. Dividing by sqrt(d\_k) brings the variance back to 1. Interviewers ask this more than any other attention question; answer with the variance argument, not "for stability".

### The mask goes in before softmax

Masking after softmax would leave rows that no longer sum to 1. Setting blocked scores to a large negative number first means softmax gives them weight 0 and renormalises the rest. Use a finite value like -1e9, not `-inf`: a row that is fully masked would become `nan` with `-inf`, because the stable softmax would compute -inf minus -inf (a naive one, 0 / 0).

### Stable softmax

`exp(1e4)` overflows float64. Subtracting the row maximum does not change the result, since softmax is invariant to adding a constant, and it guarantees the largest exponent is exactly 0. This one line is what separates a toy from code that survives real inputs.

### Heads are just another batch dimension

The reshape to `(b, n, h, d_head)` followed by `transpose(0, 2, 1, 3)` is where most bugs hide. Reshaping straight to `(b, h, n, d_head)` runs without error but mixes tokens across heads. Because `@` broadcasts over leading dimensions, no loop over heads is needed.

### Cost

Scores are an n by n matrix per head, so time is O(n^2 d) and memory is O(n^2) per head. At 512 tokens that is 262,144 scores per head; at 100,000 tokens it is 10 billion. This quadratic term is why KV caching, FlashAttention and context limits exist.

## Evaluation

**Correctness tests.**

* Shapes: output `(b, n, d_model)`, weights `(b, h, n, n)`.
* Reference: a loop that builds each head from column slices gives the same weights and the same output.
* Hand case: with d\_k = 4, scores [2, 0] / sqrt(4) = [1, 0] give weights 0.731 and 0.269. Without the scale they would be 0.881 and 0.119.
* Each weight row sums to 1 within 1e-9.
* Causal: `np.triu(weights, k=1)` is all zeros, and changing the last token leaves outputs at earlier positions unchanged.
* Permutation: without a mask, permuting the input tokens permutes the output the same way. This proves attention has no built-in sense of order.
* Peaked case: if one key equals the query times a large constant, its weight is near 1.
* Stability: scores of 1e4 give finite weights.

**Complexity.** Time O(b h n^2 d\_head), memory O(b h n^2) for the score matrix. State both without being asked.

**What a strong answer adds.** Naming each shape aloud, explaining the scaling by variance, and pointing out that a real layer would add dropout on the weights and a padding mask combined with the causal mask by logical AND.

## Bottlenecks & mitigations

* The n by n score matrix: memory grows with the square of the sequence length.
* Recomputing attention over the whole prefix for every new token during generation; a KV cache removes this.
* `np.where` and the softmax allocate fresh n by n arrays on every call.
* Float64 by default uses 2 times the memory of float32 and 4 times that of float16, which real models use.

## Failure modes

* **Reshape without transpose.** Output has the right shape but heads are scrambled. Mitigation: the per-head reference and the permutation-equivariance test both catch it.
* **Mask applied after softmax.** Rows no longer sum to 1. Mitigation: the row-sum test on the masked weights.
* **`-inf` with a fully masked row.** Produces `nan`. Mitigation: a finite large negative, or handle empty rows explicitly.
* **Softmax over the wrong axis.** Columns sum to 1, not rows, and the causal test fails. Mitigation: always pass `axis=-1` and test row sums.
* **Forgetting the scale.** Still runs; weights are nearly one-hot. Mitigation: a hand-computed case whose weights depend on the scale.
* **Mask polarity flipped.** True meaning "blocked" in one place and "allowed" in another. Mitigation: state the convention in the docstring and test the upper triangle.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""Scaled dot-product attention and multi-head self-attention in NumPy."""
import time

import numpy as np

def softmax(x, axis=-1):
    """Stable softmax: subtracting the max does not change the result."""
    x = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=axis, keepdims=True)

def scaled_dot_product_attention(q, k, v, mask=None):
    """q (..., n_q, d_k), k (..., n_k, d_k), v (..., n_k, d_v).

    mask is broadcastable to (..., n_q, n_k); True means "may attend".
    Returns (output (..., n_q, d_v), weights (..., n_q, n_k)).
    """
    d_k = q.shape[-1]
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d_k)
    if mask is not None:
        scores = np.where(mask, scores, -1e9)   # before softmax, finite on purpose
    weights = softmax(scores, axis=-1)
    return weights @ v, weights

def causal_mask(n):
    """Lower-triangular mask: position i may attend to positions <= i."""
    return np.tril(np.ones((n, n), dtype=bool))

class MultiHeadSelfAttention:
    def __init__(self, d_model, n_heads, seed=0):
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        rng = np.random.default_rng(seed)
        scale = 1.0 / np.sqrt(d_model)
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.w_q = rng.normal(0.0, scale, (d_model, d_model))
        self.w_k = rng.normal(0.0, scale, (d_model, d_model))
        self.w_v = rng.normal(0.0, scale, (d_model, d_model))
        self.w_o = rng.normal(0.0, scale, (d_model, d_model))

    def _split(self, x):
        """(b, n, d_model) -> (b, h, n, d_head). Reshape THEN transpose."""
        b, n, _ = x.shape
        return x.reshape(b, n, self.n_heads, self.d_head).transpose(0, 2, 1, 3)

    def _merge(self, x):
        """(b, h, n, d_head) -> (b, n, d_model)."""
        b, h, n, d = x.shape
        return x.transpose(0, 2, 1, 3).reshape(b, n, h * d)

    def __call__(self, x, causal=False):
        n = x.shape[1]
        q = self._split(x @ self.w_q)
        k = self._split(x @ self.w_k)
        v = self._split(x @ self.w_v)
        mask = causal_mask(n) if causal else None   # (n, n) broadcasts over b and h
        heads, weights = scaled_dot_product_attention(q, k, v, mask)
        return self._merge(heads) @ self.w_o, weights

if __name__ == "__main__":
    rng = np.random.default_rng(42)
    b, n, d_model, h = 2, 6, 16, 4
    x = rng.normal(size=(b, n, d_model))
    layer = MultiHeadSelfAttention(d_model, h)

    out, w = layer(x)
    assert out.shape == (b, n, d_model) and w.shape == (b, h, n, n)
    assert np.allclose(w.sum(axis=-1), 1.0, atol=1e-9)
    print("shapes ok:", out.shape, w.shape, "| rows sum to 1")

    # Reference: build every head from plain column slices, one head per loop turn.
    ref_heads = []
    for i in range(h):
        cols = slice(i * layer.d_head, (i + 1) * layer.d_head)
        head_i, w_i = scaled_dot_product_attention(
            (x @ layer.w_q)[..., cols], (x @ layer.w_k)[..., cols], (x @ layer.w_v)[..., cols])
        assert np.allclose(w[:, i], w_i, atol=1e-12)
        ref_heads.append(head_i)
    assert np.allclose(out, np.concatenate(ref_heads, axis=-1) @ layer.w_o, atol=1e-12)
    print("heads ok: split, attend and merge match a loop over the heads")

    out_c, w_c = layer(x, causal=True)
    assert np.all(np.triu(w_c, k=1) == 0.0) and np.allclose(w_c.sum(axis=-1), 1.0, atol=1e-9)
    x2 = x.copy()
    x2[:, -1, :] += 10.0                      # change only the last token
    out_c2, _ = layer(x2, causal=True)
    assert np.allclose(out_c[:, :-1], out_c2[:, :-1], atol=1e-9)
    print("causal ok: future weights are 0 and earlier outputs ignore later tokens")

    perm = rng.permutation(n)
    out_p, _ = layer(x[:, perm, :])
    assert np.allclose(out[:, perm, :], out_p, atol=1e-9)
    print("permutation ok: no mask means no sense of order")

    # Hand case with d_k = 4: the scores are [2, 0] / sqrt(4) = [1, 0].
    q1 = np.array([[2.0, 0.0, 0.0, 0.0]])
    k1 = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]])
    v1 = np.array([[10.0, 0.0], [0.0, 10.0]])
    out1, w1 = scaled_dot_product_attention(q1, k1, v1)
    assert np.allclose(w1, [[np.e / (1 + np.e), 1 / (1 + np.e)]]) and np.allclose(out1, 10.0 * w1)
    print("hand case ok: scores [2, 0] / sqrt(4) give weights", np.round(w1[0], 3).tolist())

    keys = np.eye(4)
    query = 50.0 * keys[2:3]                  # points hard at key 2
    _, w_peak = scaled_dot_product_attention(query, keys, keys)
    assert w_peak[0, 2] > 0.999
    print("peaked ok: weight on the matching key =", round(float(w_peak[0, 2]), 6))

    big = np.full((1, 3, 4), 1e4)
    _, w_big = scaled_dot_product_attention(big, big, big)
    assert np.all(np.isfinite(w_big))
    print("stability ok: scores near 1e8 stay finite")

    big_layer = MultiHeadSelfAttention(64, 8)
    xb = rng.normal(size=(8, 512, 64))
    t0 = time.perf_counter()
    big_layer(xb, causal=True)
    print(f"speed: batch 8 x 512 tokens x d_model 64 in {time.perf_counter() - t0:.3f} s")
```

## Follow-up questions interviewers ask

* Add a padding mask and combine it with the causal mask.
* Turn this into cross-attention. Which shapes change?
* Add a KV cache so generating token t reuses the keys and values of tokens before t.
* Why does attention need positional information, and where would you add it here?
* How would you cut the memory of the score matrix for a 100,000-token input?
* Write the backward pass for the softmax and the scaled dot product.

## Lessons that cover this

* [#1History - how AI got to transformersFoundations](/ai/learn/history-ai-to-transformers)
* [#2Neural networks and backpropFoundations](/ai/learn/neural-networks-backprop)
* [#3RNNs, LSTMs, CNNsFoundations](/ai/learn/rnns-lstms-cnns)
* [#4LLM fundamentals - tokens, embeddings, decodingFoundations](/ai/learn/llm-fundamentals)
* [#5Coding simple attentionFoundations](/ai/learn/coding-simple-attention)
* [#19Attention variations - GQA, MLALater](/ai/learn/attention-variations-gqa-mla)

## Further reading

* [Attention Is All You NeedPaperarxiv.org](https://arxiv.org/abs/1706.03762)
* [NumPy documentationGuidenumpy.org](https://numpy.org/doc/stable/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousMultimodal search over images and text](/ai/problems/multimodal-search)[NextBPE tokenizer: train, encode, decode](/ai/problems/bpe-tokenizer)

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
