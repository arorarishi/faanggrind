# Coding simple attention — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/coding-simple-attention

[AI roadmap](/ai)

FoundationsLesson #5StudyIntermediate 2.5 h

# Coding simple attention

Self-attention lets every token update its vector using the other tokens in the sequence. This lesson builds it in small steps: measure similarity with a dot product, turn the scores into weights with softmax, and take a weighted sum. Then it adds the three things a real layer needs: the scaling by the square root of d\_k, the causal mask and multiple heads. Every step is worked with numbers you can check by hand.

attentionself-attentioncausal maskmulti-headnumpytransformer

## Why it matters

"Implement self-attention" is one of the most common coding questions in LLM interviews, and "explain attention" is a standard warm-up. Both are graded the same way: can you name every tensor shape, say why the scaling is there, and put the mask in the right place? People who memorised the formula fail on the follow-ups. People who have computed a 3-token example by hand do not. The same picture is needed later for the KV cache, for FlashAttention and for every attention variant, because all of them change how this one computation is stored or scheduled, not what it computes.

Read first: [Neural networks and backprop](/ai/learn/neural-networks-backprop), [LLM fundamentals - tokens, embeddings, decoding](/ai/learn/llm-fundamentals)

## Lesson

### What attention has to do

After the embedding table, every token has a vector that ignores its neighbours. "bank" has the same vector in "river bank" and "bank loan". We want each token to pull in information from the tokens that matter to it.

The plan is a weighted average. For each token, give every token in the sequence a weight, with the weights adding up to 1, and replace the token's vector with the weighted average of all the vectors. Three questions follow. How do we score relevance? How do scores become weights? What exactly gets averaged?

We use one running example with 3 tokens and 2-dimensional vectors:

```
A = [2, 0]     B = [0, 2]     C = [1, 1]
```

### Step 1: similarity by dot product

The dot product of two vectors multiplies them entry by entry and adds the results. It is large when the vectors point the same way, zero when they are at right angles, and negative when they point in opposite directions.

A.A = 2 x 2 + 0 x 0 = 4. A.B = 2 x 0 + 0 x 2 = 0. A.C = 2 x 1 + 0 x 1 = 2.

Stack the vectors as rows of a matrix X with shape (3, 2). Then X times its transpose gives every pair at once: a 3 by 3 matrix of scores, where entry (i, j) says how well token i matches token j.

### Step 2: softmax turns scores into weights

Scores can be any size and sign. Softmax makes each row positive and makes it sum to 1:

Formula

wij​=∑k​exp(sik​)exp(sij​)​

Row A has scores [4, 0, 2]. The exponentials are 54.6, 1 and 7.39, which sum to 62.99. The weights are [0.867, 0.016, 0.117]. Token A puts most of its attention on itself, some on C and almost none on B.

### Step 3: weighted sum of values

The new vector for token i is the sum of every token's vector times its weight. In matrix form: output = weights times X. For A that is 0.867 x [2, 0] + 0.016 x [0, 2] + 0.117 x [1, 1] = [1.851, 0.149]. A has moved a little toward C.

That is attention: scores, softmax, weighted sum. The rest makes it trainable.

### Queries, keys and values

So far one vector did three jobs. A real layer gives each job its own learned matrix:

* **Query** Q = X W\_Q: what this token is looking for.
* **Key** K = X W\_K: the label this token shows to others.
* **Value** V = X W\_V: the content it hands over when chosen.

Each token asks a question (query) and every token offers a label (key) and content (value). Scores compare queries with keys, and the weighted sum is taken over values. The three matrices are the learned parameters of attention. Without them a token would mostly attend to itself, since a vector's dot product with itself is usually the largest.

Formula

Attention(Q,K,V)=softmax(dk​​QKT​)V

### Step 4: divide by the square root of d\_k

d\_k is the length of the query and key vectors. The formula divides every score by its square root. Here is the variance argument.

Take a query q and a key k whose entries are independent, with mean 0 and variance 1. Each product q\_i k\_i then has mean 0 and variance 1. The dot product adds d\_k of them, and variances of independent terms add:

Formula

Var(q⋅k)=i=1∑dk​​Var(qi​ki​)=dk​

So the scores have a standard deviation of sqrt(d\_k): 8 when d\_k = 64, and about 22.6 when d\_k = 512. Dot products grow with vector size. Softmax over scores that far apart is almost one-hot: one token gets nearly all the weight.

| Scores for one token | Softmax weights |
| --- | --- |
| [8, 0, -8], unscaled at d\_k = 64 | [0.9997, 0.0003, 0.0000] |
| [1, 0, -1], after dividing by 8 | [0.665, 0.245, 0.090] |

The gradient of a softmax weight w with respect to its own score is w(1 - w). At w = 0.9997 that is 0.0003, so almost no learning signal passes. At w = 0.665 it is 0.22. Dividing by sqrt(d\_k) divides the variance by d\_k and brings it back to 1, whatever the vector size. Scaling keeps the scores in a stable range so training works.

### Step 5: the causal mask

A model that generates text produces token 5 before token 6 exists. Training must follow the same rule, or the model would learn to copy the next token from the input. So token i may attend only to positions up to i.

The mask is applied to the scores, before the softmax. Every score above the diagonal is replaced by a large negative number such as -1e9. Its exponential is 0, so its weight is 0, and the remaining weights in the row still sum to 1.

![A five by five grid of attention weights with the cells above the diagonal blocked by the causal mask](/ai/img/causal-attention-grid.svg)A five by five grid of attention weights with the cells above the diagonal blocked by the causal mask

Masking after the softmax would be a bug: the rows would no longer sum to 1. Use a finite number, not minus infinity, so that a fully blocked row does not turn into NaN (minus infinity minus minus infinity is undefined).

The mask also makes training efficient. One pass over an n-token text trains n - 1 predictions at once, one for each next token, because position i never saw the answer at position i + 1.

### Step 6: multiple heads as a batch dimension

One head gives one set of weights per token. Multi-head attention runs h smaller attentions side by side. Each head can learn a different relationship, for example syntax in one and coreference in another. Their outputs are concatenated and passed through an output matrix W\_O.

Heads cost almost nothing extra, because each works in d\_head = d\_model / h dimensions. In code a head is only one more batch dimension:

```
# NumPy: split (b, n, d_model) into heads. Reshape, THEN transpose. k and v are split the same way.
q = (x @ W_q).reshape(b, n, h, d_head).transpose(0, 2, 1, 3)   # (b, h, n, d_head)
scores = q @ k.transpose(0, 1, 3, 2) / np.sqrt(d_head)          # (b, h, n, n)
```

Matrix multiplication works on the last two axes and treats all leading axes as a batch, so one line computes every head of every sequence. Reshaping straight to (b, h, n, d\_head) also runs, but it mixes tokens across heads. This is the classic silent bug.

### Shapes

Say the shapes aloud as you write the code. Here b = batch size, n = tokens, h = heads.

| Tensor | Shape | With b = 2, n = 10, d\_model = 512, h = 8 |
| --- | --- | --- |
| Input x | (b, n, d\_model) | (2, 10, 512) |
| W\_Q, W\_K, W\_V, W\_O | (d\_model, d\_model) | (512, 512) each |
| Q, K, V after the split | (b, h, n, d\_head) | (2, 8, 10, 64) |
| Scores | (b, h, n, n) | (2, 8, 10, 10) |
| Causal mask | (n, n), broadcast over b and h | (10, 10) |
| Weights | (b, h, n, n), each row sums to 1 | (2, 8, 10, 10) |
| Output per head | (b, h, n, d\_head) | (2, 8, 10, 64) |
| Output after merge and W\_O | (b, n, d\_model) | (2, 10, 512) |

The output has the same shape as the input, which is why layers stack.

### Where positions come in

Nothing above uses word order. Without a mask, if you shuffle the rows of X the output rows are shuffled in the same way and nothing else changes. Position has to be added, and there are two places to do it.

* **At the input.** Add a position vector to each token embedding before the first block. The vector is either fixed sine and cosine waves or a learned table.
* **Inside attention.** RoPE (rotary position embeddings) rotates each query and key by an angle that depends on its position, just before the dot product. The score then depends on how far apart two tokens are. Values are not rotated. Most modern LLMs use RoPE.

### Cost

The score matrix has n x n entries per head, per layer. Attention is quadratic in sequence length, because every token attends to every other token. Time is O(n^2 d) and memory is O(n^2).

| Tokens n | Scores per head |
| --- | --- |
| 1,000 | 1 million |
| 10,000 | 100 million |
| 100,000 | 10 billion |

That is why long context is expensive in memory and latency, and why KV caching, FlashAttention and context compression exist.

Generation is where this matters most. To produce token n + 1 the model needs only the last row of the score matrix: the new token's query against all n keys. Earlier rows cannot change, because the mask stopped them from seeing later tokens. So a server stores the keys and values of earlier tokens (the KV cache) and each step costs n scores per head, not n x n.

## Diagram

Rendering diagram…

## Worked example

Three tokens, d\_k = 2, and to keep it by hand the queries, keys and values are all X (as if W\_Q, W\_K and W\_V were the identity). This time we include the scaling.

```
X = [[2, 0],   A
     [0, 2],   B
     [1, 1]]   C
```

**1. Scores = X times X transposed.**

|  | A | B | C |
| --- | --- | --- | --- |
| A | 4 | 0 | 2 |
| B | 0 | 4 | 2 |
| C | 2 | 2 | 2 |

**2. Divide by sqrt(2) = 1.414.** Row A becomes [2.83, 0, 1.41]. Row B becomes [0, 2.83, 1.41]. Row C becomes [1.41, 1.41, 1.41].

**3. Softmax each row.** Row A: exp(2.83) = 16.92, exp(0) = 1, exp(1.41) = 4.11. The sum is 22.03, so the weights are 16.92 / 22.03 = 0.768, 1 / 22.03 = 0.045 and 4.11 / 22.03 = 0.187. Row B is the mirror image. Row C has three equal scores, so each weight is 1/3.

|  | A | B | C |
| --- | --- | --- | --- |
| A | 0.768 | 0.045 | 0.187 |
| B | 0.045 | 0.768 | 0.187 |
| C | 0.333 | 0.333 | 0.333 |

**4. Output = weights times X.** Row A: 0.768 x [2, 0] + 0.045 x [0, 2] + 0.187 x [1, 1] = [1.536 + 0.187, 0.090 + 0.187] = [1.723, 0.277]. Row B is [0.277, 1.723]. Row C is the plain average of the three vectors: [1, 1].

Compare with Step 2 of the lesson: without the scaling, A gave itself 0.867. With it, 0.768. Scaling makes the weights less extreme.

**5. Add the causal mask.** Scores above the diagonal become -1e9.

* Row A sees only A. Its weights are [1, 0, 0] and its output is [2, 0].
* Row B sees A and B, with scaled scores 0 and 2.83. The exponentials are 1 and 16.92, the sum is 17.92, and the weights are [0.056, 0.944, 0]. Output: 0.056 x [2, 0] + 0.944 x [0, 2] = [0.112, 1.888].
* Row C sees everything, so it stays [1, 1].

The first token of any causal sequence always returns its own value, because it has nothing else to read.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""Single-head attention on the 3-token example, printing every intermediate matrix.

Queries, keys and values are all X here (as if W_Q = W_K = W_V = identity),
so every number can be checked against the hand-worked example.
"""
import numpy as np

X = np.array([[2.0, 0.0],    # token A
              [0.0, 2.0],    # token B
              [1.0, 1.0]])   # token C
NAMES = ["A", "B", "C"]

def show(title, m):
    """Print a small matrix with row labels; masked scores are shown as 'blocked'."""
    print(title)
    for name, row in zip(NAMES, m):
        cells = ["blocked" if v < -1e8 else f"{v:7.3f}" for v in row]
        print(f"   {name}  " + "  ".join(cells))

def softmax_rows(s):
    s = s - s.max(axis=-1, keepdims=True)      # stable: largest exponent is 0
    e = np.exp(s)
    return e / e.sum(axis=-1, keepdims=True)

def attention_verbose(q, k, v, mask=None):
    d_k = q.shape[-1]
    scores = q @ k.T                           # (n, n): every query against every key
    show("1. scores = Q @ K.T", scores)
    scaled = scores / np.sqrt(d_k)
    show(f"2. scaled = scores / sqrt({d_k})", scaled)
    if mask is not None:
        scaled = np.where(mask, scaled, -1e9)  # before the softmax, finite on purpose
        show("2b. after the causal mask", scaled)
    weights = softmax_rows(scaled)             # (n, n): each row sums to 1
    show("3. weights = softmax of each row", weights)
    out = weights @ v                          # (n, d_v): weighted sum of values
    show("4. output = weights @ V", out)
    return out, weights

if __name__ == "__main__":
    print("=== No mask: every token reads every token ===")
    out, w = attention_verbose(X, X, X)
    assert np.allclose(w.sum(axis=-1), 1.0)
    assert np.allclose(w[0].round(3), [0.768, 0.045, 0.187])
    assert np.allclose(out.round(3), [[1.723, 0.277], [0.277, 1.723], [1.0, 1.0]])

    print("\n=== Causal mask: a token reads itself and earlier tokens only ===")
    mask = np.tril(np.ones((3, 3), dtype=bool))   # True = may attend
    out_c, w_c = attention_verbose(X, X, X, mask)
    assert np.all(np.triu(w_c, k=1) == 0.0)
    assert np.allclose(w_c[1].round(3), [0.056, 0.944, 0.0])
    assert np.allclose(out_c.round(3), [[2.0, 0.0], [0.112, 1.888], [1.0, 1.0]])

    # With the mask, changing the last token must not change earlier outputs.
    X2 = X.copy()
    X2[2] = [9.0, -9.0]
    w2 = softmax_rows(np.where(mask, X2 @ X2.T / np.sqrt(2), -1e9))
    assert np.allclose((w2 @ X2)[:2], out_c[:2])
    print("\ncheck: rows A and B ignore a change to token C when the mask is on")

    # Why divide by sqrt(d_k): the variance of a dot product grows with d_k.
    rng = np.random.default_rng(0)
    print("\n d_k   var(q.k)   var(q.k / sqrt(d_k))")
    for d_k in (4, 64, 512):
        q = rng.normal(size=(20_000, d_k))
        k = rng.normal(size=(20_000, d_k))
        dots = np.sum(q * k, axis=1)
        print(f"{d_k:4d}   {dots.var():8.1f}   {(dots / np.sqrt(d_k)).var():8.3f}")
```

## Key takeaways

* Attention is three steps: dot-product scores, softmax into weights, weighted sum of values.
* Queries, keys and values come from three learned matrices applied to the same input. Scores compare queries with keys; the sum is over values.
* A dot product of d\_k unit-variance terms has variance d\_k. Dividing by sqrt(d\_k) brings it back to 1 and keeps softmax out of its flat region.
* The causal mask sets scores above the diagonal to a large negative number before the softmax. Rows still sum to 1.
* Heads are a batch dimension: reshape to (b, n, h, d\_head), then transpose to (b, h, n, d\_head).
* Attention ignores order. Position is added at the input or rotated into queries and keys with RoPE.
* The score matrix is n by n per head, so time and memory grow with the square of the sequence length.

## Common mistakes

* Applying the mask after the softmax. The rows stop summing to 1.
* Reshaping to (b, h, n, d\_head) without the transpose. The code runs and the heads are scrambled.
* Taking the softmax over the wrong axis, so columns sum to 1 and the causal property breaks.
* Dividing by d\_k, or by sqrt(d\_model) in a multi-head layer. The scale is the square root of the per-head key size.
* Using minus infinity for the mask and getting NaN when a whole row is blocked.
* Explaining the scaling as "for stability" with no reason. Give the variance argument.

## Practice

* Redo the worked example by hand with X = [[1, 0], [0, 1], [1, 1]], then check your weights and outputs by changing X in the code example (delete the asserts that hold the old numbers). Result: three weight rows that match to 3 decimals.
* Add learned projections: create random W\_Q, W\_K and W\_V of shape (2, 2) and print the weights. Confirm that the score matrix is no longer symmetric.
* Extend the code to 2 heads on d\_model = 4 using reshape then transpose. Result: weights of shape (2, n, n) where every row sums to 1 and a permutation test passes.
* Solve the related problem "Self-attention from scratch" without looking at this lesson, and time yourself. Target: a passing solution in under 30 minutes.

## Interview questions (10)

1.Explain self-attention simply.Easy

Each token asks a question (query) and every token offers a label (key) and content (value). The dot product of query and key gives a score, softmax turns scores into weights, and the output is the weighted sum of values. So each token's new representation is a mix of the tokens most relevant to it. The queries, keys and values all come from the same sequence through three learned matrices, which is why it is called self-attention.

2.Why divide by the square root of d\_k?Medium

Dot products grow with vector size. If the query and key entries are independent with mean 0 and variance 1, the dot product is a sum of d\_k terms, each with variance 1, so its variance is d\_k and its standard deviation is sqrt(d\_k). At d\_k = 64 that is 8. Large values push softmax into regions with tiny gradients: one weight is close to 1, the rest are close to 0, and almost no learning signal flows back. Dividing by sqrt(d\_k) returns the variance to 1 for any head size. Scaling keeps the scores in a stable range so training works.

3.Why multiple heads?Easy

Each head can learn a different relationship, for example syntax in one and coreference in another. Their outputs are concatenated, which gives a richer representation than one large head. One head gives each token a single set of weights, so it must blend every relationship into one average. With h heads a token can read its subject through one head and the previous word through another. The cost stays about the same because each head has size d\_model / h.

4.What is the cost of attention, and why does it matter?Medium

It is quadratic in sequence length, because every token attends to every other token. The score matrix is n by n per head and per layer, so time is O(n squared times d) and memory is O(n squared). Going from 1,000 to 10,000 tokens multiplies the scores by 100. That is why long context is expensive in memory and latency, and why KV caching, FlashAttention and context compression exist.

5.Why is the causal mask applied before the softmax and not after?Medium

Softmax normalises a row so it sums to 1. If I zero the future positions after the softmax, the weights that remain sum to less than 1, and by a different amount in every row. If I set the blocked scores to a large negative number before the softmax, their weights come out as 0 and the softmax renormalises over the allowed positions. I use a finite value such as -1e9, not minus infinity, so a fully blocked row does not turn into NaN.

6.Walk me through the tensor shapes in multi-head self-attention.Medium

The input is (b, n, d\_model). I multiply by W\_Q, W\_K and W\_V, each (d\_model, d\_model), and get three tensors of the same shape. I reshape each to (b, n, h, d\_head) with d\_head = d\_model / h, then transpose to (b, h, n, d\_head). Scores are Q times K transposed on the last two axes: (b, h, n, n). The mask is (n, n) and broadcasts. Softmax over the last axis keeps (b, h, n, n). Weights times V gives (b, h, n, d\_head). I transpose back, reshape to (b, n, d\_model) and multiply by W\_O.

7.Attention has no sense of order. Where does position come in?Medium

Without a mask, attention is permutation-equivariant: shuffle the input tokens and the outputs are shuffled the same way. So position must be injected. The original way is at the input: add a sinusoidal or learned position vector to each token embedding before the first block. The modern way is inside attention: RoPE rotates each query and key by an angle that depends on its position, just before the dot product, so the score depends on the relative distance between tokens. Values are not rotated.

8.Why have separate query, key and value matrices? Why not use the token vector for all three?Medium

The three roles are different. What a token is looking for is not what it should advertise, and neither is the content it should pass on. A verb may look for its subject while advertising that it is a verb. With one shared vector the score is a plain similarity, and a vector is most similar to itself, so every token would mostly attend to itself. Separate matrices let the model learn asymmetric relations: A can attend strongly to B while B ignores A.

9.Self-attention vs cross-attention: what changes?Easy

Only where the keys and values come from. In self-attention the queries, keys and values all come from the same sequence. In cross-attention the queries come from one sequence, for example the decoder's tokens, and the keys and values come from another, for example the encoder output. The score matrix becomes (n\_q, n\_k), not square, and no causal mask is needed over the source. The formula is the same.

10.What are the most common bugs when coding attention from scratch?Hard

Four, and I test for each. One: reshape to heads without the transpose, which scrambles heads but keeps the shape; a permutation test catches it. Two: softmax over the wrong axis; I assert that rows sum to 1. Three: the mask after the softmax or with flipped polarity; I assert the upper triangle of the weights is exactly 0 and that changing a later token leaves earlier outputs unchanged. Four: an unstable softmax that overflows; I subtract the row maximum before the exponential.

## Quiz

1.Scores for one token are [2, 2, 2] against three keys. What are its attention weights?

2.Query and key entries are independent with mean 0 and variance 1, and d\_k = 256. What is the standard deviation of the unscaled dot product?

3.Where does the causal mask go?

4.With batch 4, 6 heads, 20 tokens and d\_model = 384, what is the shape of the attention weights?

5.In a causal layer, what is the output for the first token when the values are the token vectors themselves?

## Practice these problems

* [MLCODESelf-attention from scratchMedium](/ai/problems/attention-from-scratch)
* [MLCODEDecoder with a KV cacheHard](/ai/problems/kv-cache-decoding)

## Further reading

* [Attention Is All You NeedPaperarxiv.org](https://arxiv.org/abs/1706.03762)
* [RoFormer: Rotary Position EmbeddingPaperarxiv.org](https://arxiv.org/abs/2104.09864)
* [NumPy documentationGuidenumpy.org](https://numpy.org/doc/stable/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousLLM fundamentals - tokens, embeddings, decoding](/ai/learn/llm-fundamentals)[NextHugging Face end to end](/ai/learn/hugging-face-end-to-end)

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

1. [What attention has to do](#what-attention-has-to-do)
2. [Step 1: similarity by dot product](#step-1-similarity-by-dot-product)
3. [Step 2: softmax turns scores into weights](#step-2-softmax-turns-scores-into-weights)
4. [Step 3: weighted sum of values](#step-3-weighted-sum-of-values)
5. [Queries, keys and values](#queries-keys-and-values)
6. [Step 4: divide by the square root of dk](#step-4-divide-by-the-square-root-of-dk)
7. [Step 5: the causal mask](#step-5-the-causal-mask)
8. [Step 6: multiple heads as a batch dimension](#step-6-multiple-heads-as-a-batch-dimension)
9. [Shapes](#shapes)
10. [Where positions come in](#where-positions-come-in)
11. [Cost](#cost)
