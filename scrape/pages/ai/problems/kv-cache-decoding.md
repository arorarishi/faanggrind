# Decoder with a KV cache — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/kv-cache-decoding

[AI problems](/ai#problems)

MLCODEImplement it#33Hard

# Decoder with a KV cache

kv cachetransformerdecodinginferencenumpycausal mask

## Problem statement

Build a tiny decoder-only transformer in NumPy (random weights are fine) and write two greedy generation functions for it. The first pushes the whole sequence through the model at every step. The second keeps a KV cache, which stores the attention keys and values of every earlier token for every layer, and feeds in only the newest token. Prove that both return the same logits at every step, and show with counters and a timer how much work the cache saves.

## Requirements

### Functional

* `TinyDecoder.forward(ids, cache=None)` runs a pre-norm decoder stack: token and position embeddings, then per layer causal multi-head attention and an MLP, then logits.
* With a cache, `forward` treats `ids` as the next tokens after the cached ones, appends their keys and values, and returns logits for the new tokens only.
* `generate_no_cache(model, prompt, n_new)` recomputes the full sequence each step.
* `generate_with_cache(model, prompt, n_new)` does one prefill pass over the prompt, then one single-token pass per step.
* `KVCache` reserves its memory once and exposes its shapes and fill length.
* Self-checks print the logit gap, the work counters, the timings and the cache size.

### Non-functional

* The two functions return identical token ids, and logits that agree within 1e-9 at every step in float64.
* Work: for a prompt of P tokens and N new tokens, the cached path pushes P + N - 1 token positions through the stack; the uncached path pushes N x P + N x (N - 1) / 2. For P = 48 and N = 160 that is 207 against 20,400.
* Cache shape is `(n_layers, n_heads, max_len, d_head)` for keys and the same for values. Memory per token is 2 x 4 x 4 x 32 x 8 = 8,192 bytes for the default model in float64.
* Adding a token writes one slot per layer: 0 reallocations and 0 copies of older entries.
* The whole self-check, 160 generated tokens on both paths, finishes in under 10 seconds on a laptop CPU.

## API

```
def kv_bytes(layers, heads, head_dim, seq_len, batch=1, bytes_per_value=2) -> int: ...

class KVCache:
    k: np.ndarray        # (n_layers, n_heads, max_len, d_head)
    v: np.ndarray        # (n_layers, n_heads, max_len, d_head)
    length: int          # number of filled slots (tokens seen so far)
    def append(self, layer: int, k_new: np.ndarray, v_new: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...
        # k_new, v_new: (n_heads, m, d_head) -> all keys and values so far: (n_heads, t + m, d_head)

class TinyDecoder:
    def __init__(self, vocab=96, d_model=128, n_heads=4, n_layers=4, max_len=256, seed=0): ...
    def new_cache(self) -> KVCache: ...
    def forward(self, ids: list[int], cache: KVCache | None = None) -> np.ndarray: ...
        # m token ids -> logits (m, vocab)

def generate_no_cache(model, prompt: list[int], n_new: int) -> tuple[list[int], np.ndarray]: ...
def generate_with_cache(model, prompt: list[int], n_new: int) -> tuple[list[int], np.ndarray, KVCache]: ...
    # ids: P + n_new tokens; step logits: (n_new, vocab)
```

## Data model

```
t = tokens already in the cache      m = new tokens in this call
no cache: t = 0, m = whole sequence  prefill: t = 0, m = P      decode: t grows, m = 1

ids        (m,)                       new token ids
x          (m, d_model)               tok_emb[ids] + pos_emb[t : t+m]
q          (h, m, d_head)             queries of the new tokens; used once, never stored
k_new      (h, m, d_head)             written to cache.k[layer, :, t : t+m]
v_new      (h, m, d_head)             written to cache.v[layer, :, t : t+m]
k, v       (h, t+m, d_head)           everything this layer has seen, read from the cache
mask       (m, t+m) bool              row i (position t+i) may attend to columns 0 .. t+i
scores     (h, m, t+m)                q @ k^T / sqrt(d_head)
logits     (m, vocab)                 generation reads the last row only

cache.k    (L, h, max_len, d_head)    slots 0 .. length-1 filled, the rest are zeros
cache.v    (L, h, max_len, d_head)
```

## Approach

1. Write the model as one `forward(ids, cache)` function. Let t be the number of cached tokens (0 without a cache) and m the number of new tokens. A full pass, prefill and a decode step are then the same code with different t and m.
2. Embed the new tokens and add the position rows `t` to `t + m - 1`. The position of a new token is the cache length, not 0.
3. Build the mask with shape `(m, t + m)`: row i may attend to columns 0 to t + i. With t = 0 this is the usual lower triangle. With m = 1 it is a single row of all True.
4. In each layer, apply layer norm, then project the m new tokens to queries, keys and values.
5. Without a cache, attend over those keys and values. With a cache, write the new keys and values into slots `t` to `t + m - 1` of this layer and read back all `t + m`.
6. Compute scores of shape `(h, m, t + m)`, mask, softmax, multiply by the values, merge heads, project and add to the residual stream. Then apply layer norm and the MLP to the m new positions.
7. After the last layer, set `cache.length = t + m`. Do this once per call, not once per layer, or the second layer writes into the wrong slots.
8. `generate_no_cache` calls `forward(all_ids)` each step and reads the last row of logits.
9. `generate_with_cache` calls `forward(prompt, cache)` once (prefill), then `forward([new_token], cache)` per step (decode).
10. Count work inside `forward` (positions processed, attention scores computed) so the saving is a number, and compare the logits of the two paths at every step.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why the causal mask makes caching exact

In a decoder, the hidden state of token i at every layer depends only on tokens 0 to i. The mask stops attention from reading later tokens, and layer norm and the MLP work on one position at a time. So the key and value of token i are the same whether the sequence has i + 1 tokens or 10,000. Computing them once and storing them changes nothing. The self-check shows this directly: appending 20 tokens leaves the keys and values of the first 48 unchanged to 1e-12. A bidirectional encoder has no such property, because a new token changes every earlier hidden state. The two paths still differ by about 1e-15, because they group the same floating-point additions differently. In 16-bit floats on a GPU the gap is larger and can flip a near-tie between two tokens.

### What is cached, what is not, and what it costs

Stored: the key and value vectors of every past token, per layer and per head. Not stored: queries (a token uses its query once), attention weights, MLP activations and the hidden states themselves. Later tokens read earlier tokens only through keys and values, so nothing else is needed.

Formula

KV bytes=2×layers×heads×head dim×sequence length×batch×bytes per value

The toy model needs 2 x 4 x 4 x 32 x 8 = 8,192 bytes per token. A model with 32 layers, 32 heads and head dimension 128 in FP16 needs 2 x 32 x 32 x 128 x 2 = 524,288 bytes, about 0.52 MB per token, so a 4,000-token request holds about 2.1 GB. With grouped-query attention, count the KV heads only. Reserve the memory up front or in blocks: growing the arrays with `concatenate` copies the whole cache on every step.

### Prefill and decode

Prefill is the call with t = 0 and m = P. It is one parallel pass with a P x P score matrix per head, and it sets the time to first token. Decode is the call with m = 1: one row of t + 1 scores per head, plus the projections and the MLP for a single position. Over the 160 generated tokens of the self-check, the uncached path computes 47,077,120 attention scores and the cached path 362,496, about 130 times fewer. Per step, attention cost falls from O(n^2) to O(n).

### Position information with a cache

A decode step receives one token id and nothing else, so the code must supply its position. With learned or sinusoidal positions, add row t of the table, where t is the cache length. Adding row 0 is the classic bug: it runs and returns confident, wrong logits. With rotary positions (RoPE) nothing is added at the input. The query and key are rotated by an angle that depends on their absolute position, keys are normally stored already rotated, and the new query is rotated by position t. The score depends only on the distance between the two positions, so cached keys never need updating.

### Batching caches of different lengths

In a batch, requests have different cache lengths. The simple layout adds a batch axis, pads every cache to the longest, and needs two extra pieces: a per-request length for positions, and a key mask so that no query attends to a padded slot. Padding wastes memory, and a request that finishes leaves a hole. Serving engines store the cache in fixed-size blocks with a table from each request to its blocks, so a sequence takes a new block only when it grows into it and frees its blocks the moment it ends.

## Evaluation

**Correctness tests.**

* Equality: 160 greedy steps after a 48-token prompt. Token ids are identical and the largest logit difference is below 1e-9. The printed logit spread shows the logits are not all near zero, so the test means something.
* Work counters: positions pushed through the stack equal `sum(P + i)` without the cache and `P + N - 1` with it; attention scores equal `L x h x sum((P + i)^2)` and `L x h x (P^2 + sum(P + i))`.
* Timing: the wall time of both paths and their ratio are printed but not asserted. A timer on a busy machine is noisy; the counters are exact, so the test asserts on them.
* Cache: shapes are `(L, h, max_len, d_head)`, the fill length is `P + N - 1`, the bytes in the filled part equal the formula, and unfilled slots are still zero.
* Causality: keys and values of a prefix do not change when the sequence is extended.
* Prefill: one pass over the prompt, two chunks of 30 and 18 tokens, and P single-token passes all build the same cache and the same first logits. The chunked case is the only one with a non-empty cache and more than one new token.

**Complexity.** For sequence length n, model width d and L layers, one uncached step costs O(L (n^2 d + n d^2)). One cached decode step costs O(L (n d + d^2)). Generating n tokens costs O(L n^3 d) attention work without the cache and O(L n^2 d) with it. The cache takes O(L n d) memory.

**What a strong answer adds.** Explaining exactness from the mask before writing code, reserving memory instead of concatenating, noting that the last sampled token is not in the cache yet, stating the memory formula with a real model's numbers, and describing how positions and padding masks change in a batch.

## Bottlenecks & mitigations

* Cache memory grows linearly with sequence length, layers and batch size. At long contexts and high concurrency it is larger than the weights.
* Each decode step still reads every weight of the model to produce one token, which is why servers batch requests into one pass.
* Attention in decode is still O(n) per step, so the last tokens of a long answer are slower than the first.
* Reserving `max_len` slots per request wastes memory for short answers; block allocation fixes this.
* The uncached path redoes O(n^2) attention per step and is only useful as a reference for tests.

## Failure modes

* **Position restarts at 0.** The new token gets the first position row, the code runs, and the logits are wrong. Mitigation: use the cache length as the position; the equality test catches it.
* **Mask built as (m, m).** It is right for prefill and, by broadcasting, for single-token steps, so the bug hides until several tokens are appended to a non-empty cache. Mitigation: build the mask as `(m, t + m)` with the diagonal shifted by t, and test a chunked prefill.
* **Cache length updated inside the layer loop.** Layer 2 writes into the next slot and reads garbage. Mitigation: commit the length once after the last layer.
* **Feeding the whole sequence with a cache.** Earlier tokens are appended twice and attention double counts them. Mitigation: feed only tokens that are not in the cache; assert on `max_len`.
* **Growing the cache by concatenation.** Every step copies all earlier entries, so copying becomes O(n^2) and hides the speedup. Mitigation: reserve memory or allocate blocks.
* **Reusing a cache after the prefix changed.** Editing one early token invalidates every later key and value. Mitigation: reuse a cache only for an exact token-for-token prefix match.
* **Off-by-one after generation.** The last sampled token has not been fed, so the cache holds P + N - 1 tokens. Mitigation: track which tokens are cached, and feed the pending token before continuing a chat.
* **Padded slots attended in a batch.** Shorter requests read zeros as real keys and their outputs change with batch composition. Mitigation: a per-request key mask.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""A tiny decoder-only transformer in NumPy, generated with and without a KV cache."""
import time

import numpy as np

def softmax(x):
    x = x - np.max(x, axis=-1, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=-1, keepdims=True)

def layer_norm(x, gain, bias, eps=1e-5):
    """Normalises each position on its own, so it never mixes tokens."""
    mean = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    return gain * (x - mean) / np.sqrt(var + eps) + bias

def kv_bytes(layers, heads, head_dim, seq_len, batch=1, bytes_per_value=2):
    """KV cache size: the 2 is keys plus values."""
    return 2 * layers * heads * head_dim * seq_len * batch * bytes_per_value

class KVCache:
    """Keys and values of every token seen so far, for every layer and head.

    k, v: (n_layers, n_heads, max_len, d_head). Only the first `length` slots are filled.
    Memory is reserved once, so adding a token is a write, not a copy of the whole cache.
    """

    def __init__(self, n_layers, n_heads, max_len, d_head):
        self.k = np.zeros((n_layers, n_heads, max_len, d_head))
        self.v = np.zeros((n_layers, n_heads, max_len, d_head))
        self.length = 0

    def append(self, layer, k_new, v_new):
        """Store (h, m, d_head) keys and values; return all t + m of them for this layer."""
        t, m = self.length, k_new.shape[1]
        self.k[layer, :, t:t + m] = k_new
        self.v[layer, :, t:t + m] = v_new
        return self.k[layer, :, :t + m], self.v[layer, :, :t + m]

class TinyDecoder:
    def __init__(self, vocab=96, d_model=128, n_heads=4, n_layers=4, max_len=256, seed=0):
        assert d_model % n_heads == 0
        rng = np.random.default_rng(seed)
        self.vocab, self.d_model, self.max_len = vocab, d_model, max_len
        self.n_heads, self.n_layers, self.d_head = n_heads, n_layers, d_model // n_heads

        def w(rows, cols):                       # random weights are enough for this task
            return rng.normal(0.0, 1.0 / np.sqrt(rows), (rows, cols))

        self.tok_emb = rng.normal(0.0, 1.0, (vocab, d_model))
        self.pos_emb = rng.normal(0.0, 1.0, (max_len, d_model))   # learned absolute positions
        self.layers = [{
            "w_q": w(d_model, d_model), "w_k": w(d_model, d_model),
            "w_v": w(d_model, d_model), "w_o": w(d_model, d_model),
            "w_1": w(d_model, 4 * d_model), "w_2": w(4 * d_model, d_model),
            "g1": np.ones(d_model), "b1": np.zeros(d_model),
            "g2": np.ones(d_model), "b2": np.zeros(d_model),
        } for _ in range(n_layers)]
        self.g_out, self.b_out = np.ones(d_model), np.zeros(d_model)
        self.w_out = w(d_model, vocab)
        self.positions = 0        # work counter: token positions pushed through the stack
        self.scores = 0           # work counter: attention scores computed

    def new_cache(self):
        return KVCache(self.n_layers, self.n_heads, self.max_len, self.d_head)

    def _split(self, x):
        """(m, d_model) -> (h, m, d_head)."""
        return x.reshape(x.shape[0], self.n_heads, self.d_head).transpose(1, 0, 2)

    def forward(self, ids, cache=None):
        """Run m new tokens and return their logits, shape (m, vocab).

        cache=None: `ids` is the whole sequence and nothing is kept.
        With a cache holding t tokens: `ids` are the next m tokens, at positions t..t+m-1.
        Their keys and values are appended, and their queries attend to all t + m keys.
        """
        t = 0 if cache is None else cache.length
        m = len(ids)
        assert t + m <= self.max_len, "sequence is longer than max_len"
        x = self.tok_emb[ids] + self.pos_emb[t:t + m]            # (m, d_model)
        # Row i is the token at position t + i. It may attend to keys 0..t+i.
        mask = np.tril(np.ones((m, t + m), dtype=bool), k=t)     # (m, t + m)
        for i, p in enumerate(self.layers):
            h = layer_norm(x, p["g1"], p["b1"])
            q = self._split(h @ p["w_q"])                        # (h, m, d_head): used once
            k = self._split(h @ p["w_k"])                        # (h, m, d_head): only new tokens
            v = self._split(h @ p["w_v"])
            if cache is not None:
                k, v = cache.append(i, k, v)                     # (h, t + m, d_head)
            scores = q @ k.transpose(0, 2, 1) / np.sqrt(self.d_head)   # (h, m, t + m)
            weights = softmax(np.where(mask, scores, -1e9))
            heads = weights @ v                                  # (h, m, d_head)
            x = x + heads.transpose(1, 0, 2).reshape(m, self.d_model) @ p["w_o"]
            h = layer_norm(x, p["g2"], p["b2"])
            x = x + np.maximum(h @ p["w_1"], 0.0) @ p["w_2"]     # MLP: one position at a time
            self.scores += self.n_heads * m * (t + m)
        if cache is not None:
            cache.length = t + m                                 # commit after the last layer
        self.positions += m
        return layer_norm(x, self.g_out, self.b_out) @ self.w_out

def generate_no_cache(model, prompt, n_new):
    """Greedy decoding that pushes the whole sequence through the model at every step."""
    ids, step_logits = list(prompt), []
    for _ in range(n_new):
        logits = model.forward(ids)[-1]          # only the last row is used
        step_logits.append(logits)
        ids.append(int(np.argmax(logits)))
    return ids, np.array(step_logits)

def generate_with_cache(model, prompt, n_new):
    """Greedy decoding with a KV cache: one prefill pass, then one token per step."""
    cache = model.new_cache()
    ids, step_logits = list(prompt), []
    new = list(prompt)                           # tokens that are not in the cache yet
    for _ in range(n_new):
        logits = model.forward(new, cache)[-1]   # first pass: prefill. Later passes: decode.
        step_logits.append(logits)
        new = [int(np.argmax(logits))]
        ids.append(new[0])
    return ids, np.array(step_logits), cache

if __name__ == "__main__":
    model = TinyDecoder()
    L, H, D = model.n_layers, model.n_heads, model.d_head
    rng = np.random.default_rng(1)
    P, N = 48, 160
    prompt = [int(i) for i in rng.integers(0, model.vocab, size=P)]

    # 1. Same tokens and same logits at every step.
    model.positions = model.scores = 0
    t0 = time.perf_counter()
    ids_a, logits_a = generate_no_cache(model, prompt, N)
    time_a, pos_a, scores_a = time.perf_counter() - t0, model.positions, model.scores

    model.positions = model.scores = 0
    t0 = time.perf_counter()
    ids_b, logits_b, cache = generate_with_cache(model, prompt, N)
    time_b, pos_b, scores_b = time.perf_counter() - t0, model.positions, model.scores

    assert ids_a == ids_b and logits_a.shape == logits_b.shape == (N, model.vocab)
    gap = float(np.max(np.abs(logits_a - logits_b)))
    assert gap < 1e-9, gap
    print(f"exact ok: {N} steps, same tokens, largest logit gap {gap:.1e} "
          f"(logit spread {float(np.ptp(logits_a)):.1f})")

    # 2. Less work, counted and timed.
    assert pos_a == sum(P + i for i in range(N)) and pos_b == P + N - 1
    assert scores_a == L * H * sum((P + i) ** 2 for i in range(N))
    assert scores_b == L * H * (P * P + sum(P + i for i in range(1, N)))
    assert pos_a > 50 * pos_b and scores_a > 100 * scores_b
    # Wall time is printed, not asserted: a timer on a busy machine is noisy, the counters are exact.
    print(f"positions through the stack: {pos_a:,} without the cache, {pos_b:,} with it")
    print(f"attention scores computed:   {scores_a:,} without, {scores_b:,} with")
    print(f"wall time: {time_a:.2f} s without, {time_b:.3f} s with ({time_a / time_b:.0f}x faster)")
    assert sum(range(2000, 2300)) == 644_850 and 2000 + 300 - 1 == 2299
    print("same formulas for a 2,000-token prompt and a 300-token answer: 644,850 vs 2,299")

    # 3. Cache shapes and memory.
    assert cache.k.shape == cache.v.shape == (L, H, model.max_len, D)
    assert cache.length == P + N - 1             # the last sampled token was never fed in
    used = cache.k[:, :, :cache.length].nbytes + cache.v[:, :, :cache.length].nbytes
    assert used == kv_bytes(L, H, D, cache.length, bytes_per_value=8)
    assert np.all(cache.k[:, :, cache.length:] == 0.0)
    print(f"cache ok: k and v are {cache.k.shape}, {cache.length} slots filled, "
          f"{used:,} bytes = 2 x {L} x {H} x {D} x {cache.length} x 8")
    assert kv_bytes(layers=32, heads=32, head_dim=128, seq_len=1) == 524_288
    print("formula ok: 32 layers, 32 heads, head dim 128, FP16 -> 524,288 bytes per token")

    # 4. Why it is exact: a token's keys and values do not depend on later tokens.
    short, long_ = model.new_cache(), model.new_cache()
    model.forward(ids_a[:P], short)
    model.forward(ids_a[:P + 20], long_)
    assert np.allclose(short.k[:, :, :P], long_.k[:, :, :P], atol=1e-12)
    assert np.allclose(short.v[:, :, :P], long_.v[:, :, :P], atol=1e-12)
    print("causal ok: 20 extra tokens leave the keys and values of the first", P, "unchanged")

    # 5. Prefill in one pass, in two chunks, or one token at a time: same cache, same logits.
    one_by_one, chunked = model.new_cache(), model.new_cache()
    for tok in prompt:
        last = model.forward([tok], one_by_one)[-1]
    model.forward(prompt[:30], chunked)
    last_chunked = model.forward(prompt[30:], chunked)[-1]      # 18 tokens on top of 30 cached
    for other, logits in ((one_by_one, last), (chunked, last_chunked)):
        assert other.length == P
        assert np.allclose(other.k, short.k, atol=1e-12) and np.allclose(other.v, short.v, atol=1e-12)
        assert np.allclose(logits, logits_a[0], atol=1e-9)
    print(f"prefill ok: one pass, chunks of 30 + 18, and {P} single-token passes build the same cache")
```

## Follow-up questions interviewers ask

* Add a batch dimension for prompts of different lengths. What changes in the mask and the positions?
* Replace the learned positions with RoPE. What exactly is stored in the cache?
* Two requests share a 1,500-token system prompt. How do you reuse the cache between them?
* The context window is full. Can you drop the oldest cache entries and keep generating?
* How does the cache change with grouped-query attention?
* How would beam search or speculative decoding fork and roll back a cache?

## Lessons that cover this

* [#3RNNs, LSTMs, CNNsFoundations](/ai/learn/rnns-lstms-cnns)
* [#4LLM fundamentals - tokens, embeddings, decodingFoundations](/ai/learn/llm-fundamentals)
* [#5Coding simple attentionFoundations](/ai/learn/coding-simple-attention)
* [#11Inference and serving - KV cache, batching, vLLMServing](/ai/learn/inference-serving)
* [#19Attention variations - GQA, MLALater](/ai/learn/attention-variations-gqa-mla)
* [#22Advanced topicsLater](/ai/learn/advanced-topics)

## Further reading

* [Attention Is All You NeedPaperarxiv.org](https://arxiv.org/abs/1706.03762)
* [Efficient Memory Management for LLM Serving with PagedAttentionPaperarxiv.org](https://arxiv.org/abs/2309.06180)
* [RoFormer: Rotary Position EmbeddingPaperarxiv.org](https://arxiv.org/abs/2104.09864)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousBPE tokenizer: train, encode, decode](/ai/problems/bpe-tokenizer)[NextTemperature, top-k and top-p sampling](/ai/problems/top-k-top-p-sampling)

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
