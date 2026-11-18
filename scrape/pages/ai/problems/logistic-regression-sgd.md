# Logistic regression with SGD — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/logistic-regression-sgd

[AI problems](/ai#problems)

MLCODEImplement it#37Easy

# Logistic regression with SGD

logistic regressionsgdcross-entropygradient checknumpyregularisation

## Problem statement

Implement binary logistic regression and train it with mini-batch stochastic gradient descent (SGD), using only NumPy. Write the sigmoid, the cross-entropy loss with L2 regularisation, the gradient and the training loop yourself. The loss must stay finite for any logit, and you must prove the gradient is right with a finite-difference check. Then train on a synthetic two-class dataset and reach a stated test accuracy. Interviewers use this problem to see whether you can derive a gradient and write a training loop without a framework.

## Requirements

### Functional

* `sigmoid(z)` works for any real z without overflow.
* `loss_fn(w, b, x, y, l2)` returns the mean binary cross-entropy plus the L2 penalty, computed from the logits.
* `gradients(w, b, x, y, l2)` returns the analytic gradient for the weights and the bias.
* `numerical_gradients(...)` returns the same gradient from central finite differences.
* `train(x, y, lr, epochs, batch_size, l2, seed)` runs mini-batch SGD with a new shuffle every epoch and returns the weights, the bias and the loss after each epoch.
* `predict(w, b, x)` returns class 0 or 1, and the self-checks report train and test accuracy.

### Non-functional

* No overflow, `nan` or `inf` for logits from -1,000 to 1,000. The loss for a logit of 1,000 with label 0 must be exactly 1,000.
* The analytic gradient matches finite differences with a relative error below 1e-6.
* Test accuracy of at least 0.95 on the synthetic dataset (4,000 training and 1,000 test points, 10 features), where the best possible accuracy is about 0.977.
* 20 epochs with batch size 32 finish in under 1 second on a laptop CPU.
* Fully vectorised over examples: the only Python loops are over epochs and batches.
* Same seed, same result.

## API

```
def sigmoid(z: np.ndarray) -> np.ndarray: ...                 # any shape, values in [0, 1]

def loss_fn(w, b, x, y, l2: float = 0.0) -> float: ...
    # mean of ln(1 + e^z) - y z over the rows, plus (l2 / 2) * ||w||^2, with z = x @ w + b

def gradients(w, b, x, y, l2: float = 0.0) -> tuple[np.ndarray, float]: ...
    # dw (d,) = x.T @ (p - y) / n + l2 * w      db = mean(p - y)

def numerical_gradients(w, b, x, y, l2: float = 0.0, eps: float = 1e-6): ...

def train(x, y, lr=0.1, epochs=20, batch_size=32, l2=0.0, seed=0): ...
    # returns w (d,), b, history (list of the full training loss after each epoch)

def predict(w, b, x, threshold: float = 0.5) -> np.ndarray: ...   # (n,) of 0 or 1
```

## Data model

```
x        (n, d) float64    one example per row; here n = 4,000 train + 1,000 test, d = 10
y        (n,)   float64    labels, 0.0 or 1.0
w        (d,)              weights, start at zero
b        scalar            bias, start at zero, not regularised
z        (n,)              logits: x @ w + b
p        (n,)              sigmoid(z): predicted probability of class 1
err      (n,)              p - y: the gradient of the loss with respect to each logit
dw       (d,)              x.T @ err / n + l2 * w
db       scalar            mean(err)
rows     (batch_size,)     indices of one mini-batch, a slice of a shuffled permutation
history  list of floats    full training loss after each epoch
```

## Approach

1. Model. The logit is z = w.x + b. The predicted probability of class 1 is p = sigmoid(z) = 1 / (1 + e^-z).
2. Stable sigmoid. For z >= 0 use 1 / (1 + e^-z). For z < 0 use e^z / (1 + e^z). Both are the same function, and in both the exponent is never positive, so `exp` cannot overflow.
3. Stable loss. Do not compute ln(p): when p rounds to 0 it becomes minus infinity. Substitute p into the cross-entropy and simplify to ln(1 + e^z) - y z per example. `np.logaddexp(0, z)` computes ln(1 + e^z) safely. Average over the batch, then add (l2 / 2) x ||w||^2.
4. Gradient. With err = p - y, the gradient is dw = X^T err / n + l2 x w and db = mean(err). The derivation is in the first deep dive.
5. Gradient check. For each parameter, move it by +eps and -eps, recompute the loss and take (L+ - L-) / (2 eps). Compare with the analytic value using relative error. Run it on 50 examples with l2 switched on, at a random point, not at zero.
6. Training loop. Start from w = 0 and b = 0. Every epoch, shuffle the row indices, walk through them in slices of `batch_size`, compute the gradient on that slice and update w = w - lr x dw and b = b - lr x db.
7. Track the loss on the full training set after each epoch. It must start below ln 2 = 0.693, the loss of a model that always answers 0.5.
8. Evaluate on held-out data: predict class 1 when p >= 0.5 and report accuracy. On synthetic data, also compare the learned weight direction with the true one.

## Architecture diagram

Rendering diagram…

## Deep dives

### The gradient in three lines

For one example, L = -[y ln p + (1 - y) ln(1 - p)] with p = sigmoid(z) and z = w.x + b.

* dL/dp = -y / p + (1 - y) / (1 - p) = (p - y) / (p (1 - p)).
* dp/dz = p (1 - p), the slope of the sigmoid.
* The product is dL/dz = p - y. The p (1 - p) terms cancel.

Since dz/dw = x and dz/db = 1, the batch gradient is X^T (p - y) / n for w and mean(p - y) for b. The error is large when the model is confidently wrong, so learning is fastest exactly then.

### Why the naive loss breaks

In float64, `exp(710)` overflows, and sigmoid(40) rounds to exactly 1, so ln(1 - p) is ln(0). Working from the logit avoids both: ln(1 + e^z) - y z stays finite and accurate for any z.

### L2 regularisation

Adding (lambda / 2) ||w||^2 to the loss adds lambda x w to the gradient, so every step shrinks the weights a little. It matters most on separable data, where the unregularised weights grow without limit. The bias is left out: it only shifts the decision boundary. Say whether your penalty has the 1/2, because without it the gradient is 2 lambda w.

### The gradient check

Central differences have error of order eps^2. With eps = 1e-6 in float64, a correct gradient gives a relative error near 1e-9. An error near 1e-2 means a bug, often a missing 1/n or a forgotten penalty term.

### Mini-batches and the learning rate

A batch of 32 gives a noisy but unbiased estimate of the full gradient at 1/125 of the cost of all 4,000 rows. Shuffle every epoch so batches differ. Too high a learning rate makes the loss jump; too low wastes epochs.

## Evaluation

**Correctness tests.**

* Stability: sigmoid(-1,000) is exactly 0 and sigmoid(1,000) is exactly 1, with NumPy set to raise on overflow, division by zero and invalid values. The naive formula raises an overflow under the same setting.
* Symmetry: sigmoid(-z) = 1 - sigmoid(z) within 1e-12 on random z.
* Loss values you can compute by hand: ln 2 = 0.6931 at zero weights; exactly 1,000 for a logit of 1,000 with label 0; exactly 0 with label 1.
* Gradient check: worst relative error against central differences below 1e-6, with l2 = 0.1 so the penalty term is tested too.
* Training: the loss after epoch 1 is below ln 2, and the loss after epoch 20 is lower still.
* Accuracy: at least 0.95 on 1,000 held-out points. The two classes are Gaussians 4 standard deviations apart, so no classifier can beat about 0.977, and a result far below that means a bug.
* The learned weight vector points along the true direction: cosine above 0.98.
* Bias and shuffling: with all-zero features and 75% positive labels sorted by class, the bias ends within 0.1 of ln 3 = 1.099, the log-odds of the base rate. Without the shuffle it ends near 1.42; with no bias update it stays at 0.
* L2: the weight norm falls as lambda goes from 0 to 0.01 to 0.1.

**Complexity.** One epoch costs O(n d) time: every row is used once and each use is one dot product. Memory is O(n d) for the data and O(d) for the model. The gradient check costs 2 (d + 1) loss evaluations, so it is run on a small sample only.

**What a strong answer adds.** Deriving p - y aloud. Computing the loss from logits. Saying that the loss is convex, so there are no local minima for SGD to get stuck in. Mentioning feature scaling: features with very different ranges force a small learning rate. Knowing that accuracy at threshold 0.5 misleads on imbalanced data, where precision, recall and the area under the ROC curve are the right metrics.

## Bottlenecks & mitigations

* The Python loop over mini-batches: with batch size 32, the loop overhead costs more than the arithmetic. Larger batches use the hardware better.
* Indexing `x[rows]` copies the batch on every step. Shuffling the data once per epoch and slicing avoids the copy.
* The full-data loss after every epoch is a second pass over the data. On large data, track a running average of batch losses.
* The finite-difference check needs two loss evaluations per parameter, so it does not scale past a few hundred parameters.
* Data that does not fit in memory: SGD only needs one batch at a time, so stream it from disk.

## Failure modes

* **Overflow in exp.** The naive sigmoid calls `exp(-z)` on a large negative z and returns `inf` with a warning. Mitigation: the two-branch sigmoid and a test at z = -1,000.
* **log(0) in the loss.** A confident wrong prediction gives p = 0 or 1 exactly and the loss becomes `inf`. Mitigation: compute the loss from logits with `logaddexp`, not from p.
* **Sign or scale error in the gradient.** Using y - p, or forgetting 1/n, still runs. Mitigation: the gradient check, and a loss that must fall below ln 2 after the first epoch.
* **Labels in -1 and +1.** The formulas here assume 0 and 1, and the loss goes negative with -1. Mitigation: assert the label set before training.
* **No shuffling.** If rows are sorted by class, each batch holds one class and the weights swing back and forth. Mitigation: a new permutation every epoch.
* **Learning rate too high.** The loss oscillates or grows. Mitigation: plot the loss per epoch, reduce the rate by a factor of 3 to 10, or decay it over time.
* **Unscaled features.** One feature in the thousands dominates the gradient. Mitigation: standardise each feature with the mean and standard deviation of the training split only.
* **Weights grow without limit.** On perfectly separable data the unregularised loss has no minimum. Mitigation: L2 or early stopping.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""Logistic regression trained with mini-batch SGD, in NumPy."""
import time

import numpy as np

def sigmoid(z):
    """Stable sigmoid: never calls exp on a positive number."""
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))      # z >= 0: exp(-z) is at most 1
    ez = np.exp(z[~pos])                          # z < 0: exp(z) is below 1
    out[~pos] = ez / (1.0 + ez)
    return out

def loss_fn(w, b, x, y, l2=0.0):
    """Mean binary cross-entropy computed from the logits, plus (l2 / 2) * ||w||^2.

    Per example: -[y ln p + (1 - y) ln(1 - p)] = ln(1 + e^z) - y z.
    logaddexp(0, z) is ln(1 + e^z) without overflow, so no log(0) can happen.
    """
    z = x @ w + b                                 # (n,)
    return float(np.mean(np.logaddexp(0.0, z) - y * z) + 0.5 * l2 * (w @ w))

def gradients(w, b, x, y, l2=0.0):
    """dL/dw = X^T (p - y) / n + l2 * w and dL/db = mean(p - y). The bias is not regularised."""
    err = sigmoid(x @ w + b) - y                  # (n,) this is dL/dz for every example
    return x.T @ err / len(y) + l2 * w, float(np.mean(err))

def numerical_gradients(w, b, x, y, l2=0.0, eps=1e-6):
    """Central differences: (L(theta + eps) - L(theta - eps)) / (2 eps), one parameter at a time."""
    dw = np.zeros_like(w)
    for j in range(len(w)):
        step = np.zeros_like(w)
        step[j] = eps
        dw[j] = (loss_fn(w + step, b, x, y, l2) - loss_fn(w - step, b, x, y, l2)) / (2 * eps)
    db = (loss_fn(w, b + eps, x, y, l2) - loss_fn(w, b - eps, x, y, l2)) / (2 * eps)
    return dw, db

def train(x, y, lr=0.1, epochs=20, batch_size=32, l2=0.0, seed=0):
    """Mini-batch SGD. Returns w (d,), b and the full training loss after every epoch."""
    assert set(np.unique(y)) <= {0.0, 1.0}, "labels must be 0 or 1"
    rng = np.random.default_rng(seed)
    n, d = x.shape
    w, b = np.zeros(d), 0.0
    history = []
    for _ in range(epochs):
        order = rng.permutation(n)                # new shuffle every epoch
        for start in range(0, n, batch_size):
            rows = order[start:start + batch_size]
            dw, db = gradients(w, b, x[rows], y[rows], l2)
            w -= lr * dw
            b -= lr * db
        history.append(loss_fn(w, b, x, y, l2))
    return w, b, history

def predict(w, b, x, threshold=0.5):
    return (sigmoid(x @ w + b) >= threshold).astype(np.int64)

def make_blobs(n, d, rng):
    """Two Gaussian classes, 4 standard deviations apart along one random direction."""
    direction = rng.normal(size=d)
    direction /= np.linalg.norm(direction)
    y = rng.integers(0, 2, size=n)
    x = rng.normal(size=(n, d)) + np.outer(2.0 * (2 * y - 1), direction)   # means at -2 and +2
    return x, y.astype(np.float64), direction

if __name__ == "__main__":
    rng = np.random.default_rng(0)

    with np.errstate(over="raise", divide="raise", invalid="raise"):   # overflow, log(0) or nan would raise
        s = sigmoid(np.array([-1000.0, -30.0, 0.0, 30.0, 1000.0]))
        assert s[0] == 0.0 and s[2] == 0.5 and s[4] == 1.0 and np.all(np.diff(s) >= 0)
        zs = rng.normal(scale=5.0, size=100)
        assert np.allclose(sigmoid(-zs), 1.0 - sigmoid(zs), atol=1e-12)
        x_one, w_one = np.array([[1.0]]), np.array([1000.0])
        wrong = loss_fn(w_one, 0.0, x_one, np.array([0.0]))    # sure of class 1, label is 0
        right = loss_fn(w_one, 0.0, x_one, np.array([1.0]))
        assert wrong == 1000.0 and right == 0.0
        try:
            1.0 / (1.0 + np.exp(-np.array([-1000.0])))          # the textbook formula
            naive = "no error"
        except FloatingPointError:
            naive = "overflow"
        assert naive == "overflow"
    print("stable ok: sigmoid(-1000) = 0, sigmoid(1000) = 1; loss at logit 1000 is", wrong, "or", right,
          "| naive sigmoid:", naive)

    x, y, direction = make_blobs(5000, 10, rng)
    x_train, y_train, x_test, y_test = x[:4000], y[:4000], x[4000:], y[4000:]
    assert abs(loss_fn(np.zeros(10), 0.0, x_train, y_train) - np.log(2)) < 1e-12
    print("start ok: loss with zero weights is ln 2 =", round(float(np.log(2)), 4))

    w0, b0 = rng.normal(size=10), 0.3                           # a random point, not zero
    dw, db = gradients(w0, b0, x_train[:50], y_train[:50], l2=0.1)
    num_dw, num_db = numerical_gradients(w0, b0, x_train[:50], y_train[:50], l2=0.1)
    ana, num = np.append(dw, db), np.append(num_dw, num_db)
    rel = np.max(np.abs(ana - num) / (np.abs(ana) + np.abs(num) + 1e-12))
    assert rel < 1e-6
    print(f"gradient check ok: worst relative error vs finite differences = {rel:.1e}")

    t0 = time.perf_counter()
    w, b, history = train(x_train, y_train, lr=0.1, epochs=20, batch_size=32, l2=1e-3)
    seconds = time.perf_counter() - t0
    train_acc = float(np.mean(predict(w, b, x_train) == y_train))
    test_acc = float(np.mean(predict(w, b, x_test) == y_test))
    cos = float(w @ direction / np.linalg.norm(w))
    assert history[-1] < history[0] < np.log(2)
    assert test_acc >= 0.95 and cos > 0.98
    print(f"training ok: loss {np.log(2):.4f} -> {history[0]:.4f} -> {history[-1]:.4f} "
          f"after 1 and 20 epochs, {seconds:.2f} s")
    print(f"accuracy: train {train_acc:.3f}, test {test_acc:.3f} (target 0.95, best possible about 0.977)")
    print(f"learned direction: cosine with the true direction = {cos:.3f}")

    # With all-zero features only the bias can learn: it must reach the log-odds of the base rate.
    # The rows are sorted by class, so this also fails if train() does not shuffle.
    y_sorted = np.array([0.0] * 250 + [1.0] * 750)
    _, b_only, _ = train(np.zeros((1000, 1)), y_sorted)
    assert abs(b_only - np.log(3)) < 0.1
    print(f"bias ok: 75% ones, rows sorted by class -> bias {b_only:.3f}, log-odds ln 3 = {np.log(3):.3f}")

    norms = [float(np.linalg.norm(train(x_train, y_train, l2=lam)[0])) for lam in (0.0, 0.01, 0.1)]
    assert norms[0] > norms[1] > norms[2]
    print("L2 ok: weight norm for lambda 0, 0.01, 0.1 =", [round(v, 2) for v in norms])
```

## Follow-up questions interviewers ask

* Extend this to K classes with softmax. What does the gradient become?
* Add momentum or Adam. What state do you keep for each parameter?
* The positive class is 1% of the data. What do you change in the loss, the threshold and the metric?
* How would you use L1 regularisation, and why does it give exactly zero weights when L2 does not?
* The gradient check passes but the test accuracy is 0.5. Where do you look?
* How is this model related to one neuron of a neural network, and what does backpropagation add?

## Lessons that cover this

* [#1History - how AI got to transformersFoundations](/ai/learn/history-ai-to-transformers)
* [#2Neural networks and backpropFoundations](/ai/learn/neural-networks-backprop)

## Further reading

* [Linear models: logistic regression (scikit-learn documentation)Guidescikit-learn.org](https://scikit-learn.org/stable/modules/linear_model.html)
* [numpy.logaddexp (NumPy documentation)Guidenumpy.org](https://numpy.org/doc/stable/reference/generated/numpy.logaddexp.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousLoRA layer: forward, train and merge](/ai/problems/lora-layer)[NextAgent loop from scratch with tools and a step limit](/ai/problems/agent-loop-from-scratch)

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
