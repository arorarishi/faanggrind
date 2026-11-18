# Attention variations - GQA, MLA — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/attention-variations-gqa-mla

[AI roadmap](/ai)

LaterLesson #19LaterAdvanced 1.5 h

# Attention variations - GQA, MLA

Standard multi-head attention stores a key and a value for every head, every layer and every past token. That store, the KV cache, is the main memory cost of serving besides the weights. This lesson covers the variants that shrink it: multi-query attention, grouped-query attention (GQA) and multi-head latent attention (MLA). It also places FlashAttention and sliding-window attention, which solve different problems.

attentionkv cachegqamqamlaflashattention

## Why it matters

In a serving or system-design round, "how much memory does one request need?" comes down to the KV cache, and the attention variant sets its size. Open model configs expose the choice directly, so you should be able to read a config and compute the cache in bytes. Interviewers also use this topic to check precision: GQA shares heads, MLA compresses into a latent vector, and FlashAttention changes nothing about the result. Mixing these up is a common way to lose a senior-level question.

Read first: [LLM fundamentals - tokens, embeddings, decoding](/ai/learn/llm-fundamentals), [Coding simple attention](/ai/learn/coding-simple-attention), [Inference and serving - KV cache, batching, vLLM](/ai/learn/inference-serving)

## Lesson

### The cost that these variants attack

During generation, the keys and values of all earlier tokens are stored for every layer, so each new token only computes its own. That is the KV cache. With standard multi-head attention (MHA) each of the H heads has its own key and its own value of size d\_head, so one token costs 2 x H x d\_head numbers in every layer.

Formula

KV cache bytes=2×L×Hkv​×dhead​×n×b×bytes per number

L is the number of layers, H\_kv the number of key/value heads, n the tokens per sequence and b the number of sequences in the batch. In MHA, H\_kv = H. The cache grows with layers, sequence length and concurrent requests, so it decides how many users fit on one GPU.

Memory size is not the only cost. The paper that introduced GQA points at memory bandwidth: at every decoding step the stored keys and values must be loaded again, and that loading is the bottleneck of decoder inference.

Every variant below changes one term of the formula.

### Multi-query attention (MQA)

MQA keeps H query heads but uses a single key head and a single value head, shared by all of them. H\_kv = 1, so the cache is H times smaller.

Each query head still has its own query vector, so each head still produces its own attention weights. What is lost is variety in what the heads can read: all of them score against the same keys and mix the same values. The GQA paper states that MQA can lead to quality degradation.

### Grouped-query attention (GQA)

GQA is the middle setting. The H query heads are divided into G groups, and each group shares one key head and one value head. H\_kv = G.

* G = H is ordinary multi-head attention.
* G = 1 is multi-query attention.
* Anything between gives a cache H / G times smaller than MHA.

![Multi-head, grouped-query and multi-query attention with 8 query heads and 8, 2 or 1 cached key/value heads](/ai/img/gqa-head-sharing.svg)Multi-head, grouped-query and multi-query attention with 8 query heads and 8, 2 or 1 cached key/value heads

In code the change is small. The key and value projections output G heads, not H. Before the scores are computed, each cached key/value head is repeated for the H / G query heads in its group, and the attention formula runs unchanged.

What the GQA paper reports:

* An existing multi-head checkpoint can be converted. The key and value projection matrices of the heads in a group are mean-pooled into one, then the model is trained a little more ("uptraining") with about 5% of the original pretraining compute.
* Uptrained GQA reaches quality close to multi-head attention at a speed comparable to MQA.
* The experiments use encoder-decoder models, and the main results use 8 groups.

In Hugging Face configs for Llama-style models the setting is `num_key_value_heads`. Equal to the number of attention heads means MHA, 1 means MQA, and anything between is GQA.

GQA does not reduce the number of attention scores. All H query heads still compute their own scores at every step. The saving is in memory and in the loading of keys and values.

### Multi-head latent attention (MLA)

MLA comes from the DeepSeek-V2 paper. It does not share heads. It compresses.

1. For each token, the hidden state is projected down to one small latent vector of size d\_c. The paper calls this low-rank joint compression of keys and values.
2. Only the latent vector is cached.
3. When attention runs, the keys and values for all heads are rebuilt from the latent with up-projection matrices.

So the cache per token and per layer is d\_c numbers, where MHA stores 2 x H x d\_head.

There is a complication with position. The paper states that RoPE is incompatible with this low-rank compression, so it adds a "decoupled" RoPE: a small extra key of size d\_R that carries the position and is shared by the heads. It is cached too. The total per token and per layer is d\_c + d\_R.

DeepSeek-V2 sets d\_c = 4 x d\_head and d\_R = d\_head / 2, a total of 4.5 x d\_head. The paper notes that this equals the cache of GQA with only 2.25 groups, and its comparison table rates MLA's capability above MHA. The abstract reports a 93.3% smaller KV cache than the earlier DeepSeek 67B model. That figure compares two whole models, so do not quote it as the saving from MLA alone.

The price is a more complex layer: extra projection matrices and a special position scheme.

### FlashAttention is an implementation, not a variant

FlashAttention computes exact attention. The output is the same as the standard formula. What changes is how the GPU does the work.

A plain implementation writes the full n x n score matrix to the GPU's main memory and reads it back, and that traffic is the slow part. FlashAttention splits the queries, keys and values into blocks that fit in the GPU's small, fast on-chip memory, computes the softmax block by block, and never reads or writes the full matrix in main memory. Its extra memory is linear in sequence length, not quadratic. Same result, less memory, faster.

It is independent of everything above. GQA and MLA shrink what is stored between decoding steps. FlashAttention speeds up the attention computation itself, which matters most in training and when a long prompt is processed. A model can use both.

### Sliding-window and sparse attention

Here each token attends only to the last w tokens, or to a fixed sparse pattern, so the cost falls from n x n to n x w and only w tokens need to stay in the cache. Unlike FlashAttention this changes the model: direct links to far-away tokens are gone, and distant information has to travel through several layers, reaching roughly w more tokens per layer.

### Comparison

| Variant | What is shared or compressed | KV cache size, per token and layer | Quality cost |
| --- | --- | --- | --- |
| MHA | Nothing; every head has its own key and value | 2 x H x d\_head | Baseline |
| MQA | All H query heads share one key/value head | 2 x d\_head | Can degrade quality |
| GQA | Each group of H / G query heads shares one key/value head | 2 x G x d\_head | Close to MHA after uptraining, in the GQA paper |
| MLA | Keys and values of all heads compressed into one latent vector, plus a small position key | d\_c + d\_R (4.5 x d\_head in DeepSeek-V2) | Rated above MHA in the DeepSeek-V2 paper |
| FlashAttention | Nothing; same maths, computed in blocks | Unchanged | None; exact |
| Sliding window | Each token reads only the last w tokens | Same per token, but only w tokens kept | Loses direct long-range links |

## Diagram

Rendering diagram…

## Worked example

**Sizing the KV cache for one model shape.** The shape below is invented for clean arithmetic: L = 32 layers, H = 32 query heads, d\_head = 128 (so d\_model = 4,096), numbers stored in FP16 (2 bytes). One sequence of n = 8,192 tokens.

**MHA (H\_kv = 32).** Per token: 2 x 32 layers x 32 heads x 128 x 2 bytes = 524,288 bytes, which is 0.5 MiB (1 MiB = 1,048,576 bytes; 1 GiB = 1,024 MiB). For 8,192 tokens: 524,288 x 8,192 = 4,294,967,296 bytes = 4 GiB.

**GQA with 8 groups (H\_kv = 8).** Per token: 2 x 32 x 8 x 128 x 2 = 131,072 bytes. For 8,192 tokens: 1,073,741,824 bytes = 1 GiB. That is 32 / 8 = 4 times smaller.

**MQA (H\_kv = 1).** Per token: 2 x 32 x 1 x 128 x 2 = 16,384 bytes. For 8,192 tokens: 134,217,728 bytes = 128 MiB. That is 32 times smaller.

**MLA with the DeepSeek-V2 ratios.** d\_c + d\_R = 4.5 x 128 = 576 numbers per layer. Per token: 576 x 32 x 2 = 36,864 bytes. For 8,192 tokens: 301,989,888 bytes = 288 MiB. Check against the "2.25 groups" statement: 2 x 32 x 2.25 x 128 x 2 = 36,864 bytes. It matches.

**What this means for serving.** Assume 24 GiB of GPU memory is left after loading the weights, and every request uses the full 8,192 tokens.

| Variant | Cache per sequence | Sequences that fit in 24 GiB |
| --- | --- | --- |
| MHA | 4 GiB | 6 |
| GQA, 8 groups | 1 GiB | 24 |
| MLA, 4.5 x d\_head | 288 MiB | 85 |
| MQA | 128 MiB | 192 |

Going from MHA to GQA with 8 groups lets the same GPU hold 4 times as many concurrent requests. This is the reason the variants exist.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""KV-cache memory calculator: MHA vs GQA vs MQA (and MLA with the DeepSeek-V2 ratios)."""

LAYERS = 32
QUERY_HEADS = 32
D_HEAD = 128                 # d_model = 32 * 128 = 4096
BYTES_PER_NUMBER = 2         # FP16
TOKENS = 8192
SPARE_GPU_BYTES = 24 * 2**30

def kv_cache_bytes(layers, kv_heads, d_head, tokens, batch=1, bytes_per_number=2):
    """2 (keys and values) x layers x kv_heads x d_head, for every token of every sequence."""
    return 2 * layers * kv_heads * d_head * tokens * batch * bytes_per_number

def latent_cache_bytes(layers, latent_size, tokens, batch=1, bytes_per_number=2):
    """MLA caches one latent vector (plus a small position key) per token and layer."""
    return int(layers * latent_size * tokens * batch * bytes_per_number)

def human(n_bytes):
    for unit, size in (("GiB", 2**30), ("MiB", 2**20), ("KiB", 2**10)):
        if n_bytes >= size:
            return f"{n_bytes / size:,.2f} {unit}"
    return f"{n_bytes} B"

if __name__ == "__main__":
    variants = [
        ("MHA (32 kv heads)", kv_cache_bytes(LAYERS, QUERY_HEADS, D_HEAD, TOKENS)),
        ("GQA (8 kv heads)", kv_cache_bytes(LAYERS, 8, D_HEAD, TOKENS)),
        ("MQA (1 kv head)", kv_cache_bytes(LAYERS, 1, D_HEAD, TOKENS)),
        ("MLA (4.5 x d_head)", latent_cache_bytes(LAYERS, 4.5 * D_HEAD, TOKENS)),
    ]
    mha = variants[0][1]
    print(f"model: {LAYERS} layers, {QUERY_HEADS} query heads, d_head {D_HEAD}, FP16, {TOKENS} tokens")
    print(f"{'variant':<20}{'bytes per token':>16}{'bytes per sequence':>20}{'size':>12}{'vs MHA':>9}{'fit in 24 GiB':>15}")
    for name, total in variants:
        per_token = total // TOKENS
        print(f"{name:<20}{per_token:>16,}{total:>20,}{human(total):>12}"
              f"{mha / total:>8.1f}x{SPARE_GPU_BYTES // total:>15}")

    # Checks against the worked example.
    assert variants[0][1] == 4 * 2**30
    assert variants[1][1] == 1 * 2**30
    assert variants[2][1] == 128 * 2**20
    assert variants[3][1] == 288 * 2**20
    # MLA at 4.5 x d_head equals GQA with 2.25 groups.
    assert variants[3][1] == 2 * LAYERS * 2.25 * D_HEAD * TOKENS * BYTES_PER_NUMBER

    # The same GQA model with 16 concurrent sequences of 8,192 tokens.
    batch16 = kv_cache_bytes(LAYERS, 8, D_HEAD, TOKENS, batch=16)
    print(f"\nGQA, batch of 16 full-length sequences: {batch16:,} bytes = {human(batch16)}")
```

## Key takeaways

* KV cache bytes = 2 x layers x key/value heads x d\_head x tokens x batch x bytes per number. The variants change the "key/value heads" term or replace it.
* MQA: all query heads share one key/value head. The cache is H times smaller, and quality can drop.
* GQA: G groups of query heads, one key/value head per group. The cache is H / G times smaller and quality stays close to MHA.
* MLA: keys and values are compressed into one latent vector per token, which is what gets cached. They are rebuilt when attention runs.
* None of these reduce the number of attention scores. They save memory and memory traffic.
* FlashAttention is an exact, memory-efficient way to compute standard attention. It is not a different attention.
* Sliding-window attention does change the model: it gives up direct long-range links for n x w cost.

## Common mistakes

* Calling FlashAttention an approximation. Its output equals standard attention.
* Saying GQA makes attention cheaper to compute. The query heads and the scores are unchanged; the cache is what shrinks.
* Quoting the 93.3% KV-cache figure as "what MLA saves". It compares DeepSeek-V2 with an earlier, different model.
* Forgetting the factor 2 (keys and values) or the layer count when sizing a cache.
* Describing MLA as "GQA with more sharing". GQA shares heads; MLA stores a compressed latent and rebuilds keys and values from it.

## Practice

* Extend the calculator to take a batch size and a mix of sequence lengths. Result: the largest batch of 2,000-token requests that fits in 24 GiB for MHA, GQA with 8 groups and MQA.
* Open the config of any open-weight model, read the layer count, head count, key/value head count and hidden size, and compute its KV cache per token in FP16. Result: one number in bytes, and whether the model is MHA, GQA or MQA.
* Change the related problem "Self-attention from scratch" so the key and value projections output G heads and each is repeated for its group. Result: with G = H the outputs match the original within 1e-9, and the weights still have shape (b, h, n, n).

## Interview questions (7)

1.What is grouped-query attention, and why do models use it?Medium

GQA splits the query heads into G groups, and each group shares one key head and one value head. With G equal to the number of heads it is ordinary multi-head attention, and with G = 1 it is multi-query attention. Models use it because the KV cache stores keys and values, not queries, so the cache shrinks by H / G. For 32 query heads and 8 key/value heads that is 4 times less cache per token, which means more concurrent requests or longer contexts on the same GPU. The paper that introduced it reports quality close to multi-head attention.

2.How much memory does the KV cache need, and how does GQA change it?Medium

Per token it is 2, for keys and values, times layers, times key/value heads, times d\_head, times bytes per number. Take 32 layers, 32 heads, d\_head 128 and FP16: 2 x 32 x 32 x 128 x 2 bytes = 524,288 bytes, about half a mebibyte per token. An 8,192-token sequence needs 4 GiB. With GQA and 8 key/value heads the same sequence needs 1 GiB. Then I multiply by the number of concurrent sequences, because every request has its own cache.

3.MQA vs GQA: what is the trade-off?Medium

MQA uses one key/value head for all query heads. It gives the largest saving, a cache H times smaller, but every head reads the same keys and values, and the GQA paper notes that this can degrade quality. GQA keeps a few key/value heads, so groups of heads can still read different things. You give back part of the saving, for example 4 times smaller where MQA would give 32 times, and quality stays close to full multi-head attention. GQA is a dial between the two ends.

4.What is multi-head latent attention (MLA)?Hard

MLA is the attention design from the DeepSeek-V2 paper. For each token it projects the hidden state down to one small latent vector and caches only that. When attention runs, keys and values for all heads are rebuilt from the latent with up-projection matrices. So the cache holds d\_c numbers per token and layer, where multi-head attention holds 2 x H x d\_head. Because the paper found RoPE incompatible with this compression, it adds a small separate key that carries position, which is cached too. In DeepSeek-V2 the total is 4.5 x d\_head, the same cache as GQA with 2.25 groups.

5.Is FlashAttention a different kind of attention?Medium

No. It computes exact attention, so the output is the same as the standard formula. It is a different implementation on the GPU. A plain version writes the full n by n score matrix to the GPU's main memory, and that memory traffic is the slow part. FlashAttention works on blocks of queries, keys and values that fit in fast on-chip memory and builds the softmax block by block, so the full matrix never goes to main memory. Same result, less memory, faster. It combines with GQA or MLA, because those change what is cached and it changes how attention is computed.

6.Does GQA reduce the compute of attention?Hard

Not the main term. Every query head still computes a score against every past token, so the number of scores per step is unchanged, and so is the weighted sum per head. The key and value projections are smaller, since they output G heads where MHA outputs H, but that is a small part of the work. The real gain is memory: fewer keys and values stored, and fewer loaded at each decoding step. The GQA paper names that loading, memory bandwidth, as the bottleneck of decoder inference.

7.You have a multi-head checkpoint. Can you turn it into a GQA model without training from scratch?Hard

Yes, that is the recipe in the GQA paper. For each group, mean-pool the key projection matrices of its heads into one, and do the same for the value projections. The pooled model is worse at first, so you continue pretraining for a short time, which the paper calls uptraining, using about 5% of the original pretraining compute. I would then run my own evals before and after, because the paper's experiments were on encoder-decoder models and my model and tasks may behave differently.

## Quiz

1.A model has 40 layers, 40 query heads, 8 key/value heads and d\_head = 128, stored in FP16. How many bytes of KV cache does one token need?

2.Which statement about FlashAttention is correct?

3.In GQA with 32 query heads and 4 groups, how many query heads share each key/value head?

4.What does MLA store in the KV cache for each token?

5.Which change alters what the model can attend to?

## Practice these problems

* [MLSDServe an open model to 1,000 concurrent usersHard](/ai/problems/llm-serving-platform)
* [MLCODESelf-attention from scratchMedium](/ai/problems/attention-from-scratch)
* [MLCODEDecoder with a KV cacheHard](/ai/problems/kv-cache-decoding)

## Further reading

* [GQA: Training Generalized Multi-Query Transformer Models from Multi-Head CheckpointsPaperarxiv.org](https://arxiv.org/abs/2305.13245)
* [DeepSeek-V2 (multi-head latent attention)Paperarxiv.org](https://arxiv.org/abs/2405.04434)
* [FlashAttentionPaperarxiv.org](https://arxiv.org/abs/2205.14135)
* [Efficient Memory Management for LLM Serving with PagedAttentionPaperarxiv.org](https://arxiv.org/abs/2309.06180)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousWhat is new in 2026 + revision](/ai/learn/whats-new-2026-revision)[NextRL fine-tuning](/ai/learn/rl-fine-tuning)

## On this page

1. [Lesson](#lesson)
2. [Diagram](#diagram)
3. [Worked example](#example)
4. [Code](#code)
5. [Key takeaways](#takeaways)
6. [Common mistakes](#mistakes)
7. [Practice](#practice)
8. [Interview questions](#interview)
9. [Quiz](#quiz)
10. [Related problems](#problems)
11. [Further reading](#reading)
12. [My notes](#notes)

## In this lesson

1. [The cost that these variants attack](#the-cost-that-these-variants-attack)
2. [Multi-query attention (MQA)](#multi-query-attention-mqa)
3. [Grouped-query attention (GQA)](#grouped-query-attention-gqa)
4. [Multi-head latent attention (MLA)](#multi-head-latent-attention-mla)
5. [FlashAttention is an implementation, not a variant](#flashattention-is-an-implementation-not-a-variant)
6. [Sliding-window and sparse attention](#sliding-window-and-sparse-attention)
7. [Comparison](#comparison)
