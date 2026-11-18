# Temperature, top-k and top-p sampling — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/top-k-top-p-sampling

[AI problems](/ai#problems)

MLCODEImplement it#34Easy

# Temperature, top-k and top-p sampling

samplingdecodingtemperaturetop-pnumpy

## Problem statement

A language model returns one logit (raw score) per vocabulary token. Write the NumPy code that turns those logits into the next token: temperature scaling, top-k filtering, top-p (nucleus) filtering, and greedy decoding as the temperature-zero case. The function must return the filtered distribution as well as a sampled id, so that each step can be tested. The interviewer is checking the order of the steps and the edge cases, not the ten lines of happy path.

## Requirements

### Functional

* `next_token_probs(logits, temperature, top_k, top_p)` returns the distribution that will be sampled from.
* Temperature 0 means greedy: all probability on the argmax, with no division by zero.
* Top-k keeps exactly the k most likely tokens; top-p keeps the smallest set of most likely tokens whose total probability reaches p.
* Filters can be combined, and each one renormalises so the result sums to 1.
* `sample(...)` draws one token id from that distribution with a seeded generator.

### Non-functional

* The returned probabilities sum to 1 within 1e-12 for every setting.
* Stable: logits as large as 1e4 with a temperature of 0.01 give no NaN and no inf.
* Top-k leaves exactly k non-zero entries even when tokens tie at the cut; top-p never leaves 0 tokens.
* One sort per filter, so at most 2 per call: O(V log V) for a vocabulary of V tokens, with no Python loop over tokens.
* With a fixed seed, 20,000 draws match the target distribution within 0.015 per token, and removed tokens appear 0 times.

## API

```
def softmax(x: np.ndarray) -> np.ndarray: ...                    # (V,) -> (V,), stable

def top_k_filter(probs: np.ndarray, k: int) -> np.ndarray: ...   # (V,) -> (V,), exactly k non-zero

def top_p_filter(probs: np.ndarray, p: float) -> np.ndarray: ... # (V,) -> (V,), smallest set with mass >= p

def next_token_probs(
    logits: np.ndarray,            # (V,)
    temperature: float = 1.0,      # 0 means greedy
    top_k: int | None = None,
    top_p: float | None = None,    # in (0, 1]
) -> np.ndarray: ...               # (V,), sums to 1

def sample(logits, temperature=1.0, top_k=None, top_p=None, rng=None) -> int: ...
```

## Data model

```
logits        (V,) float64     raw scores from the model, any real numbers
probs         (V,) float64     softmax(logits / T); every entry > 0, sum 1
order         (V,) int         token ids sorted by probability, highest first
mass_before   (V,) float64     for each sorted token, the total probability of the tokens ahead of it
keep          (V,) bool        top-p: mass_before < p
filtered      (V,) float64     removed tokens are exactly 0, the rest are renormalised, sum 1

Example, V = 5, probs = [0.50, 0.20, 0.15, 0.10, 0.05], top_p = 0.9:
mass_before = [0.00, 0.50, 0.70, 0.85, 0.95]  ->  keep 4 tokens  ->  divide by 0.95
filtered    = [0.526, 0.211, 0.158, 0.105, 0.000]
```

## Approach

1. Write a stable `softmax`: subtract the maximum, take `exp`, divide by the sum.
2. Handle temperature 0 first. Return a one-hot vector on `argmax(logits)`. This avoids dividing by zero and makes greedy a normal case of the same function.
3. For any other temperature T, compute `probs = softmax(logits / T)`. T below 1 sharpens the distribution and T above 1 flattens it.
4. Top-k: sort the token ids by probability with a stable sort, keep the first k, set the rest to 0, and divide by the new sum.
5. Top-p: sort again, and for each token compute the probability mass of the tokens ahead of it (`cumsum - probs`). Keep a token when that mass is below p. Set the rest to 0 and divide by the new sum.
6. Apply the filters in the order temperature, top-k, top-p. Because top-k renormalises, top-p works on what top-k left.
7. `sample` calls `next_token_probs` and draws one id with `rng.choice(V, p=probs)`. Passing the generator in makes the function repeatable in tests.
8. Test each step on a five-token example you can check by hand, then test the sampler by counting 20,000 draws.

## Architecture diagram

Rendering diagram…

## Deep dives

### Order of operations

Temperature goes first because it changes what top-p keeps: at T = 0.5 the top token of the example has 0.77 of the mass, so top-p = 0.9 keeps 3 tokens, not 4. Top-k is unaffected by T, since scaling never reorders tokens. Top-p runs after top-k on the renormalised survivors. In the self-check, top-k = 3 then top-p = 0.8 keeps 2 tokens, while top-p = 0.8 alone keeps 3.

### Stable softmax

`exp(1e4)` overflows float64, and dividing logits by T = 0.01 makes them 100 times larger. Subtracting the maximum first makes the largest exponent exactly 0. The result is unchanged because softmax ignores a constant added to every logit.

### The boundary token in top-p

The token that crosses p is kept. The rule "keep while the cumulative sum is at most p" drops it, and returns nothing when the top token alone exceeds p. Testing the mass before each token fixes both: the top token has 0 before it, so it always stays. When the mass equals p exactly, the set is already large enough.

### Ties

Tokens with equal probability at the cut must not all survive, or top-k = 2 returns 3 tokens. A stable sort keeps the lower id. `argmax` does the same for greedy.

### What each knob does to the output

Temperature reshapes every probability and removes nothing. Top-k cuts the tail at a fixed size. Top-p cuts at a fixed mass, so few tokens survive when the model is confident and many when it is unsure. Low settings give repeatable, plain text. High settings give varied text and more mistakes.

## Evaluation

**Correctness tests.** All use probabilities 0.50, 0.20, 0.15, 0.10, 0.05.

* Sum: six settings, including greedy and all three knobs together, each return non-negative values that sum to 1.
* Temperature: T = 1 returns the input distribution, T = 0.5 equals `p**2` renormalised, T = 2 lowers the top token and raises the last, and T = 0 and T = 1e-6 are both one-hot on the argmax.
* Top-k: k = 2 gives 0.714 and 0.286; a tie at the cut still leaves exactly k; k larger than V keeps everything.
* Top-p: p = 0.9 gives 0.526, 0.211, 0.158, 0.105, 0. For seven values of p the kept set is a prefix of the sorted tokens, its mass is at least p, and dropping its last token would fall below p. A tiny p keeps one token.
* Sampling: 20,000 seeded draws match the filtered distribution within 0.015, and removed tokens never appear.

**Complexity.** O(V log V) time for the sort and O(V) memory. With V = 100,000 that is one sort of 100,000 floats per generated token. `np.argpartition` gets top-k in O(V).

**What a strong answer adds.** A batched version on logits of shape `(batch, V)`, doing the filtering on logits by setting removed entries to minus infinity so one final softmax is enough, and a note that temperature 0 removes sampling but not floating-point differences between runs on a GPU.

## Bottlenecks & mitigations

* A full sort of the vocabulary on every generated token; `argpartition` or a top-k on the GPU avoids most of it.
* Two sorts when top-k and top-p are both set; sorting once and reusing the order removes one.
* `rng.choice` with probabilities rebuilds a cumulative table on every call.
* One Python call per token; a real server samples a whole batch of requests in one tensor operation.

## Failure modes

* **Naive softmax.** Large logits or a small temperature overflow to inf, and inf / inf is NaN. Mitigation: subtract the maximum first.
* **Dividing by a temperature of 0.** Produces inf or NaN. Mitigation: branch to argmax before dividing.
* **Dropping the boundary token.** Top-p keeps less mass than p, or nothing at all. Mitigation: keep tokens whose mass before them is below p.
* **Forgetting to renormalise.** The probabilities sum to less than 1 and the sampler raises an error or is biased. Mitigation: divide by the kept sum and test the sum.
* **Threshold-style top-k.** `probs >= kth value` keeps every tied token, so more than k survive. Mitigation: select k indices from a stable sort.
* **Top-p before temperature.** The nucleus is computed on the wrong distribution. Mitigation: fix the order and test a combined setting.
* **Unseeded generator in tests.** The frequency test fails at random. Mitigation: pass a seeded generator and use a tolerance several standard errors wide.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""Temperature, top-k and top-p (nucleus) sampling from logits in NumPy."""
import numpy as np

def softmax(x):
    """Stable softmax over a 1-D array: the largest exponent is exactly 0."""
    x = x - np.max(x)
    e = np.exp(x)
    return e / e.sum()

def top_k_filter(probs, k):
    """Keep exactly the k most likely tokens, zero the rest, renormalise."""
    k = min(k, probs.size)
    order = np.argsort(-probs, kind="stable")   # stable: ties go to the lower id
    out = np.zeros_like(probs)
    out[order[:k]] = probs[order[:k]]
    return out / out.sum()

def top_p_filter(probs, p):
    """Keep the smallest set of most likely tokens whose mass is at least p."""
    order = np.argsort(-probs, kind="stable")
    sorted_probs = probs[order]
    mass_before = np.cumsum(sorted_probs) - sorted_probs   # mass of the tokens ahead of each one
    keep = mass_before < p        # the token that crosses p is kept; the top token always is
    out = np.zeros_like(probs)
    out[order[keep]] = sorted_probs[keep]
    return out / out.sum()

def next_token_probs(logits, temperature=1.0, top_k=None, top_p=None):
    """logits (V,) -> the distribution to sample from, shape (V,), sums to 1.

    Order: temperature, softmax, top-k, top-p. Each filter renormalises,
    so top-p sees what top-k left.
    """
    logits = np.asarray(logits, dtype=np.float64)
    if temperature == 0.0:                       # greedy: all mass on the argmax
        probs = np.zeros_like(logits)
        probs[np.argmax(logits)] = 1.0           # argmax returns the lowest id on a tie
        return probs
    assert temperature > 0.0, "temperature must be >= 0"
    probs = softmax(logits / temperature)
    if top_k is not None:
        assert top_k >= 1
        probs = top_k_filter(probs, top_k)
    if top_p is not None:
        assert 0.0 < top_p <= 1.0
        probs = top_p_filter(probs, top_p)
    return probs

def sample(logits, temperature=1.0, top_k=None, top_p=None, rng=None):
    """Draw one token id."""
    rng = rng if rng is not None else np.random.default_rng()
    probs = next_token_probs(logits, temperature, top_k, top_p)
    return int(rng.choice(probs.size, p=probs))

if __name__ == "__main__":
    # The five-token example: tea, coffee, water, milk, sugar.
    P = np.array([0.50, 0.20, 0.15, 0.10, 0.05])
    LOGITS = np.log(P)

    # 1. Every setting returns a distribution.
    settings = [dict(), dict(temperature=0.7), dict(top_k=3), dict(top_p=0.9),
                dict(temperature=1.5, top_k=4, top_p=0.8), dict(temperature=0.0)]
    for s in settings:
        q = next_token_probs(LOGITS, **s)
        assert q.shape == P.shape and np.all(q >= 0) and abs(q.sum() - 1.0) < 1e-12
    print(f"sums ok: {len(settings)} settings each return probabilities that sum to 1")

    # 2. Temperature: 1 changes nothing, T equals p^(1/T) renormalised, 0 is argmax.
    assert np.allclose(next_token_probs(LOGITS), P)
    assert np.allclose(next_token_probs(LOGITS, temperature=0.5), P ** 2 / np.sum(P ** 2))
    hot = next_token_probs(LOGITS, temperature=2.0)
    assert hot[0] < P[0] and hot[4] > P[4]
    for t in (0.0, 1e-6):
        assert np.array_equal(next_token_probs(LOGITS, temperature=t), np.eye(5)[0])
    print("temperature ok: T=0.5 sharpens, T=2 flattens, T=0 and T=1e-6 are one-hot on the argmax")

    # 3. Top-k keeps exactly k, even with a tie at the boundary.
    q = next_token_probs(LOGITS, top_k=2)
    assert np.count_nonzero(q) == 2 and np.allclose(q, [0.5 / 0.7, 0.2 / 0.7, 0, 0, 0])
    tied = np.log(np.array([0.4, 0.2, 0.2, 0.2]))
    q = next_token_probs(tied, top_k=2)
    assert np.count_nonzero(q) == 2 and q[1] > 0 and q[2] == 0
    assert np.count_nonzero(next_token_probs(LOGITS, top_k=99)) == 5
    print("top-k ok: exactly k survive, a tie at the cut goes to the lower id, k > V keeps all")

    # 4. Top-p keeps the smallest prefix of the sorted tokens whose mass reaches p.
    q = next_token_probs(LOGITS, top_p=0.9)
    assert np.allclose(q, np.array([0.50, 0.20, 0.15, 0.10, 0.0]) / 0.95)
    for p_cut in (0.01, 0.3, 0.6, 0.75, 0.9, 0.99, 1.0):
        kept = np.flatnonzero(next_token_probs(LOGITS, top_p=p_cut))
        mass = P[kept].sum()
        assert kept.size >= 1 and list(kept) == list(range(kept.size))   # a prefix: P is sorted
        assert mass >= p_cut - 1e-12                                     # reaches p
        assert mass - P[kept[-1]] < p_cut                                # and is the smallest
    exact = np.array([0.5, 0.25, 0.125, 0.125])      # powers of 2: the sum 0.75 is exact
    assert np.count_nonzero(top_p_filter(exact, 0.75)) == 2    # mass equal to p is enough
    assert np.count_nonzero(next_token_probs(LOGITS, top_p=1e-9)) == 1
    print("top-p ok: smallest set with mass >= p, boundary token kept, never empty")

    # 5. Order of operations: top-p runs on what top-k left, after renormalising.
    q = next_token_probs(LOGITS, top_k=3, top_p=0.8)       # top-3 renormalised: .588 .235 .176
    assert np.count_nonzero(q) == 2
    assert np.count_nonzero(next_token_probs(LOGITS, top_p=0.8)) == 3
    assert np.count_nonzero(next_token_probs(LOGITS, top_p=0.9)) == 4
    assert np.count_nonzero(next_token_probs(LOGITS, temperature=0.5, top_p=0.9)) == 3
    print("order ok: top-k=3 then top-p=0.8 keeps 2 tokens, top-p=0.8 alone keeps 3;"
          " top-p=0.9 keeps 4 at T=1 and 3 at T=0.5")

    # 6. Stability: huge logits and a tiny temperature stay finite.
    big = np.array([1e4, 1e4 - 1.0, -1e4])
    q = next_token_probs(big, temperature=0.01)
    assert np.all(np.isfinite(q)) and abs(q.sum() - 1.0) < 1e-12
    print("stability ok: logits of 1e4 at T=0.01 give finite probabilities")

    # 7. Sampling follows the filtered distribution, and removed tokens never appear.
    rng = np.random.default_rng(0)
    n = 20_000
    target = next_token_probs(LOGITS, temperature=0.8, top_k=4, top_p=0.9)
    draws = [sample(LOGITS, temperature=0.8, top_k=4, top_p=0.9, rng=rng) for _ in range(n)]
    freq = np.bincount(draws, minlength=5) / n
    assert np.all(freq[target == 0] == 0)
    assert np.max(np.abs(freq - target)) < 0.015
    print("sampling ok:", n, "draws with seed 0")
    print("  target   ", np.round(target, 3))
    print("  observed ", np.round(freq, 3))
    greedy = {sample(LOGITS, temperature=0.0, rng=rng) for _ in range(100)}
    assert greedy == {0}
    print("greedy ok: 100 draws at T=0 all return token 0")
```

## Follow-up questions interviewers ask

* Make it work on a batch of logits with shape `(batch, V)` and no Python loop.
* Do the filtering in logit space. What value do removed tokens get, and why is it safe in the softmax?
* Add a repetition penalty. Where does it go in the order?
* Sample without `rng.choice`, using a cumulative sum and one uniform random number.
* Why can two runs at temperature 0 still give different text on a GPU?

## Lessons that cover this

* [#4LLM fundamentals - tokens, embeddings, decodingFoundations](/ai/learn/llm-fundamentals)
* [#6Hugging Face end to endFoundations](/ai/learn/hugging-face-end-to-end)

## Further reading

* [The Curious Case of Neural Text Degeneration (nucleus sampling)Paperarxiv.org](https://arxiv.org/abs/1904.09751)
* [Hierarchical Neural Story Generation (top-k sampling)Paperarxiv.org](https://arxiv.org/abs/1805.04833)
* [NumPy documentationGuidenumpy.org](https://numpy.org/doc/stable/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousDecoder with a KV cache](/ai/problems/kv-cache-decoding)[NextBrute-force cosine top-k search](/ai/problems/cosine-top-k-search)

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
