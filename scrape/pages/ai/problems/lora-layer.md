# LoRA layer: forward, train and merge — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/lora-layer

[AI problems](/ai#problems)

MLCODEImplement it#36Medium

# LoRA layer: forward, train and merge

lorafine-tuningpeftnumpybackpropagation

## Problem statement

Implement a LoRA (low-rank adaptation) linear layer in NumPy with gradients written by hand. The layer holds a frozen weight W of shape d x k and two small trainable matrices, B (d x r) and A (r x k), and computes h = W x + (alpha / r) B A x. You must write the forward pass, the backward pass, a training step that updates only A and B, and merge and unmerge. No autograd is allowed; the interviewer wants to see the chain rule and the shapes.

## Requirements

### Functional

* `forward(X)` returns `X W^T + (alpha / r) (X A^T) B^T` for a batch X of shape `(n, k)`.
* `backward(dH)` stores the gradients of A and B and returns the gradient for the layer's input. W gets no gradient.
* `step(lr)` updates A and B only.
* `merge()` folds the update into W so the layer is one matrix; `unmerge()` takes it out again. Calling either twice is safe.
* B starts at zero and A starts random; `num_trainable()` reports r x (d + k).
* Self-checks print what they verify.

### Non-functional

* At initialisation the output equals the base layer exactly: the difference is 0, not just small.
* Gradients of A, B and the input match central finite differences within 1e-7.
* W is bit-for-bit unchanged after 300 training steps.
* Trainable values are r x (d + k): 448 for d = 64, k = 48, r = 4, which is 14.6% of the 3,072 frozen values.
* Merged output equals unmerged output within 1e-10, and unmerge restores W within 1e-12 in float64.
* On a toy regression whose target is the base plus a rank-2 change, the loss falls by at least 100 times in 300 steps.

## API

```
class LoRALinear:
    def __init__(self, W: np.ndarray, r: int, alpha: float, seed: int = 0): ...
        # W: (d, k), frozen. Creates A (r, k) random and B (d, r) zeros. scale = alpha / r
    def forward(self, X: np.ndarray) -> np.ndarray: ...     # (n, k) -> (n, d)
    def backward(self, dH: np.ndarray) -> np.ndarray: ...   # (n, d) -> dX (n, k); sets grad_A, grad_B
    def step(self, lr: float) -> None: ...                  # gradient descent on A and B only
    def delta(self) -> np.ndarray: ...                      # (d, k): scale * B @ A
    def merge(self) -> None: ...                            # W += delta()
    def unmerge(self) -> None: ...                          # W -= delta()
    def num_trainable(self) -> int: ...                     # r * (d + k)

def half_mse(H: np.ndarray, Y: np.ndarray) -> tuple[float, np.ndarray]: ...   # loss, dLoss/dH
def numeric_grad(f, M: np.ndarray, eps: float = 1e-6) -> np.ndarray: ...      # finite differences
```

## Data model

```
W        (d, k)    frozen base weight; d = output size, k = input size
B        (d, r)    trainable, starts at zero
A        (r, k)    trainable, starts random (normal, std 0.1)
scale    scalar    alpha / r
X        (n, k)    batch of inputs
Z        (n, r)    X @ A^T: the input squeezed down to rank r
H        (n, d)    X @ W^T + scale * Z @ B^T

Backward, given dH = dLoss/dH of shape (n, d):
grad_B   (d, r)    scale * dH^T @ Z
dZ       (n, r)    scale * dH @ B
grad_A   (r, k)    dZ^T @ X
dX       (n, k)    dH @ W + dZ @ A        W is read here but never updated
```

## Approach

1. Fix the convention before writing code: h = W x with W of shape (d, k), so a batch of row vectors uses `X @ W.T`. B is (d, r) and A is (r, k), and the update B A has the same shape as W.
2. In `__init__`, store W and give it no gradient slot, create A with small random values and B with zeros, and set `scale = alpha / r`.
3. Forward: compute `Z = X @ A.T`, then `H = X @ W.T + scale * Z @ B.T`. Never build the d x k matrix B A in the forward pass; two small products cost O(n r (d + k)), not O(n d k). Keep X and Z for the backward pass.
4. Backward: from `dH`, compute `grad_B = scale * dH.T @ Z`, then `dZ = scale * dH @ B`, then `grad_A = dZ.T @ X`. Return `dH @ W + dZ @ A` so that layers below this one can still train.
5. Step: subtract `lr * grad` from A and B. There is no line that writes to W.
6. Merge: add `scale * B @ A` to W and set a flag. While merged, forward uses W alone, and backward refuses to run. Unmerge subtracts the same matrix and clears the flag.
7. Check the gradients with finite differences on a small layer whose B is non-zero. At initialisation the gradient of A is exactly zero, so a check done there would pass even with a wrong formula.
8. Train on a toy regression and assert three things: the loss falls, W is unchanged, and the merged layer gives the same output.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why B starts at zero

With B = 0 the update B A is zero, so the adapted model starts as exactly the pretrained model. The first loss is the pretrained loss, not the loss of a model with random noise added to every layer. Only one of the two matrices may be zero. If A were zero too, both gradients would be zero and nothing would ever move; the self-check shows this case.

### Why the gradient of A is zero at the first step

Let G = dH^T X, the gradient with respect to the full d x k update. Then grad B = scale x G A^T and grad A = scale x B^T G. At step one B is zero, so grad A is exactly zero, while grad B is not, because A is random. After one step B is non-zero and A starts to move. The cost is one step out of thousands. It also means a gradient check at initialisation tests nothing about A.

### The role of alpha / r

The update is multiplied by alpha / r. Dividing by r keeps the size of the update in a similar range when you change the rank, so you do not have to retune the learning rate for every r. Alpha then acts like a learning-rate multiplier for the adapter: with plain gradient descent the scale appears in the forward pass and in both gradients, so the change in the output after one step grows with the scale squared. A common start is r = 16 and alpha = 32, a scale of 2. At high ranks alpha / r becomes small; rsLoRA divides by the square root of r to avoid that.

### Merging and serving

Merging computes W' = W + (alpha / r) B A once. The layer is a single d x k matrix again, so latency is the same as the base model. Unmerged, each adapted layer does two extra small multiplies, but one base model in memory can serve many adapters. Unmerge is a subtraction, so it restores W only up to rounding: about 1e-16 here in float64 (the test allows 1e-12), and far worse in 16-bit floats. If adapters are swapped often, keep the base clean and run them unmerged.

### Parameter arithmetic

B has d x r values and A has r x k, so the adapter trains r x (d + k). The toy layer trains 4 x (64 + 48) = 448 of 3,072, or 14.6%. A 4096 x 4096 layer has about 16.8 million values; at r = 8 the adapter trains 8 x 8,192 = 65,536, or 0.39%. For a square layer the fraction is 2r / d, so the saving grows with layer size.

## Evaluation

**Correctness tests.**

* Initialisation: B is all zeros and `forward(X)` is identical to `X @ W.T`.
* Count: `num_trainable()` equals r x (d + k) = 448, and the 4096 x 4096 example gives 65,536.
* First step: grad A is exactly zero and grad B is not. A second layer with A = B = 0 gets zero gradients for both.
* Gradient check: on a 5 x 7 layer with r = 3 and a non-zero B, the analytic gradients of A, B and the input match central finite differences within 1e-7. The forward pass is also compared with `X @ (W + 2 B A).T`.
* Training: 300 steps of gradient descent on a target that is the base plus a rank-2 change. The loss falls by more than 100 times, `W` is bit-for-bit unchanged, A has moved, and the update has rank at most r.
* Merge: merged output equals the unmerged output, a second `merge()` does not add the update twice, and `unmerge()` restores W.

**Complexity.** Forward and backward cost O(n d k) for the frozen path plus O(n r (d + k)) for the adapter. Extra memory is r (d + k) values plus their gradients. Merge costs O(d k r) once.

**What a strong answer adds.** Stating the shape convention first, checking gradients away from initialisation, returning the input gradient so the layer can sit inside a deeper network, and explaining that LoRA saves gradient and optimiser memory but not the forward pass through W. Mentioning dropout on the adapter input and the rsLoRA scale is a bonus.

## Bottlenecks & mitigations

* The frozen path still costs a full d x k multiply on every step; LoRA shrinks what is trained, not what is run.
* Activations X and Z are kept for the backward pass, so memory still grows with batch size and depth.
* Unmerged serving adds two small multiplies per adapted layer per token.
* `numeric_grad` needs two forward passes per parameter, so it is only usable on tiny layers.
* Merging builds a full d x k matrix, about 16.8 million values for a 4096 x 4096 layer, for every adapter you merge.

## Failure modes

* **Both A and B start at zero.** Every gradient is zero and the loss never moves. Mitigation: random A, zero B; test that grad B is non-zero at step one.
* **B starts random.** The model's output changes before any training, so step 0 is worse than the base model. Mitigation: assert that the initial output equals the base output.
* **Scale missing from one gradient.** Training still runs but follows the wrong direction. Mitigation: finite-difference check with a non-zero B and a scale that is not 1.
* **Gradient check done at initialisation.** Grad A is zero there, so a wrong formula passes. Mitigation: set B to random values for the check.
* **W updated by accident.** An optimiser that loops over every array also changes the base. Mitigation: keep W out of the trainable list and compare it with a saved copy after training.
* **Merging twice.** The update is added twice and outputs drift. Mitigation: a merged flag.
* **Training while merged.** Gradients are computed for an adapter that is already inside W. Mitigation: refuse to run backward when merged.
* **Shapes swapped.** Using A as (d, r) and B as (r, k) breaks the zero-start logic and any saved adapter. Mitigation: write the convention in the docstring and assert the shapes.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""A LoRA linear layer in NumPy with manual gradients, training, merge and unmerge.

Convention: h = W x with W of shape (d, k). d is the output size, k the input size.
B is (d, r), A is (r, k), and the layer computes h = W x + (alpha / r) B A x.
A batch X has shape (n, k), so the batched forward pass is H = X W^T + scale (X A^T) B^T.
"""
import numpy as np

class LoRALinear:
    def __init__(self, W, r, alpha, seed=0):
        d, k = W.shape
        rng = np.random.default_rng(seed)
        self.W = W                                   # (d, k) frozen: never gets a gradient
        self.A = rng.normal(0.0, 0.1, (r, k))        # (r, k) trainable, random start
        self.B = np.zeros((d, r))                    # (d, r) trainable, zero start
        self.r, self.scale = r, alpha / r
        self.merged = False
        self.grad_A = np.zeros_like(self.A)
        self.grad_B = np.zeros_like(self.B)

    def delta(self):
        """The low-rank update that training has learned, shape (d, k)."""
        return self.scale * self.B @ self.A

    def forward(self, X):
        """X (n, k) -> H (n, d). Keeps what backward needs."""
        if self.merged:                              # W already contains the update
            return X @ self.W.T
        self.X = X
        self.Z = X @ self.A.T                        # (n, r): the input squeezed to rank r
        return X @ self.W.T + self.scale * self.Z @ self.B.T

    def backward(self, dH):
        """dH = dLoss/dH, shape (n, d). Stores grad_A and grad_B, returns dLoss/dX."""
        assert not self.merged, "unmerge before training"
        self.grad_B = self.scale * dH.T @ self.Z     # (d, r)
        dZ = self.scale * dH @ self.B                # (n, r)
        self.grad_A = dZ.T @ self.X                  # (r, k): zero while B is zero
        return dH @ self.W + dZ @ self.A             # (n, k). W is used, never updated

    def step(self, lr):
        """Plain gradient descent on A and B only."""
        self.A -= lr * self.grad_A
        self.B -= lr * self.grad_B

    def merge(self):
        """Fold the update into W so serving costs one matrix multiply."""
        if not self.merged:
            self.W += self.delta()
            self.merged = True

    def unmerge(self):
        """Take the update out again, for example to swap in another adapter."""
        if self.merged:
            self.W -= self.delta()
            self.merged = False

    def num_trainable(self):
        return self.A.size + self.B.size

def half_mse(H, Y):
    """Loss = half the squared error per example, and its gradient with respect to H."""
    diff = H - Y
    n = H.shape[0]
    return float(0.5 * np.sum(diff ** 2) / n), diff / n

def numeric_grad(f, M, eps=1e-6):
    """Central finite differences of the scalar f() with respect to every entry of M."""
    grad = np.zeros_like(M)
    for idx in np.ndindex(*M.shape):
        old = M[idx]
        M[idx] = old + eps
        up = f()
        M[idx] = old - eps
        down = f()
        M[idx] = old
        grad[idx] = (up - down) / (2 * eps)
    return grad

if __name__ == "__main__":
    rng = np.random.default_rng(0)
    d, k, r, alpha, n = 64, 48, 4, 8, 256
    W0 = rng.normal(0.0, 0.1, (d, k))
    layer = LoRALinear(W0.copy(), r, alpha)
    X = rng.normal(size=(n, k))

    # 1. At initialisation B = 0, so the layer is exactly the base layer.
    assert np.array_equal(layer.B, np.zeros((d, r))) and layer.A.shape == (r, k)
    assert np.array_equal(layer.forward(X), X @ W0.T)
    print("init ok: B is zero, output is identical to the frozen base layer")

    # 2. Parameter count: r x (d + k).
    assert layer.num_trainable() == r * (d + k) == 448
    print(f"count ok: {layer.num_trainable()} trainable = {r} x ({d} + {k}), "
          f"{100 * layer.num_trainable() / W0.size:.1f}% of the {W0.size} frozen values")
    assert 8 * (4096 + 4096) == 65_536
    print(f"         a 4096 x 4096 layer at r = 8 trains 65,536 values, "
          f"{100 * 65_536 / 4096 ** 2:.2f}% of the layer")

    # 3. First step: grad_A is exactly zero, grad_B is not. If both started at zero, both stay.
    U, V = rng.normal(size=(d, 2)), rng.normal(size=(2, k))
    Y = X @ (W0 + 0.05 * U @ V).T                    # target: base plus a rank-2 change
    _, dH = half_mse(layer.forward(X), Y)
    layer.backward(dH)
    assert np.all(layer.grad_A == 0.0) and np.abs(layer.grad_B).max() > 1e-4
    stuck = LoRALinear(W0.copy(), r, alpha)
    stuck.A[:] = 0.0
    _, dH = half_mse(stuck.forward(X), Y)
    stuck.backward(dH)
    assert np.all(stuck.grad_A == 0.0) and np.all(stuck.grad_B == 0.0)
    print("first step ok: grad_A = 0 and grad_B != 0; with A = B = 0 both gradients are 0")

    # 4. Gradients match finite differences (with B non-zero, so grad_A is tested too).
    small = LoRALinear(rng.normal(0.0, 0.3, (5, 7)), r=3, alpha=6, seed=1)
    small.B[:] = rng.normal(0.0, 0.3, small.B.shape)
    Xs, Ys = rng.normal(size=(6, 7)), rng.normal(size=(6, 5))
    assert small.scale == 6 / 3
    assert np.allclose(small.forward(Xs), Xs @ (small.W + 2.0 * small.B @ small.A).T, atol=1e-12)
    loss_fn = lambda: half_mse(small.forward(Xs), Ys)[0]
    _, dH = half_mse(small.forward(Xs), Ys)
    dX = small.backward(dH)
    worst = 0.0
    for name, analytic, M in (("A", small.grad_A, small.A), ("B", small.grad_B, small.B), ("X", dX, Xs)):
        err = float(np.max(np.abs(analytic - numeric_grad(loss_fn, M))))
        assert err < 1e-7, (name, err)
        worst = max(worst, err)
    print(f"gradient ok: A, B and input gradients match finite differences (worst gap {worst:.1e})")

    # 5. Training lowers the loss and never touches W.
    A_start, losses = layer.A.copy(), []
    for _ in range(300):
        loss, dH = half_mse(layer.forward(X), Y)
        losses.append(loss)
        layer.backward(dH)
        layer.step(lr=0.01)
    final = half_mse(layer.forward(X), Y)[0]
    assert np.array_equal(layer.W, W0), "the frozen weight changed"
    assert final < 0.01 * losses[0]
    assert not np.array_equal(layer.A, A_start)      # A does move once B is non-zero
    assert np.linalg.matrix_rank(layer.delta()) <= r
    print(f"training ok: loss {losses[0]:.3f} -> {final:.1e} in 300 steps, W unchanged, A moved, "
          f"update has rank {np.linalg.matrix_rank(layer.delta())} (at most r = {r})")

    # 6. Merge and unmerge.
    before = layer.forward(X)
    layer.merge()
    assert np.allclose(layer.W, W0 + layer.delta(), atol=1e-12)
    assert np.allclose(layer.forward(X), before, atol=1e-10)
    layer.merge()                                    # a second merge must not add twice
    assert np.allclose(layer.forward(X), before, atol=1e-10)
    layer.unmerge()
    assert np.allclose(layer.W, W0, atol=1e-12) and np.allclose(layer.forward(X), before, atol=1e-10)
    print(f"merge ok: merged output equals base plus adapter; unmerge restores W "
          f"(largest error {float(np.max(np.abs(layer.W - W0))):.1e})")
```

## Follow-up questions interviewers ask

* Replace gradient descent with Adam. How much optimiser memory does LoRA save compared with training W?
* Change the scale to the rsLoRA form. When does it matter?
* Extend the layer to DoRA: what extra parameter is trained and how is the forward pass changed?
* Serve one batch in which every row uses a different adapter on the same base.
* Add this layer to the query and value projections of an attention block. Which gradients flow through the frozen weights?
* The base weight is stored in 4 bits. What changes in forward, backward and merge?

## Lessons that cover this

* [#2Neural networks and backpropFoundations](/ai/learn/neural-networks-backprop)
* [#9What is fine-tuning - LoRA, QLoRA, DoRABuild with LLMs](/ai/learn/fine-tuning-lora-qlora-dora)
* [#10Fine-tuning a model for a real use caseBuild with LLMs](/ai/learn/fine-tuning-real-use-case)

## Further reading

* [LoRA: Low-Rank Adaptation of Large Language ModelsPaperarxiv.org](https://arxiv.org/abs/2106.09685)
* [Hugging Face PEFT documentationGuidehuggingface.co](https://huggingface.co/docs/peft)
* [NumPy documentationGuidenumpy.org](https://numpy.org/doc/stable/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousBrute-force cosine top-k search](/ai/problems/cosine-top-k-search)[NextLogistic regression with SGD](/ai/problems/logistic-regression-sgd)

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
