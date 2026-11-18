# Fine-tuning a model for a real use case — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/fine-tuning-real-use-case

[AI roadmap](/ai)

Build with LLMsLesson #10StudyIntermediate 4 h

# Fine-tuning a model for a real use case

This lesson takes one real task, a model that sorts support tickets and drafts a reply, and walks the whole fine-tuning job from start to finish. You decide whether to fine-tune at all, build and clean the dataset, format it with the chat template, split it, train a QLoRA adapter, read the loss curves, compare with the base model, serve the adapter, and debug a run that made things worse.

fine-tuningqloradatasetchat templateevaluationloss curvesadapter serving

## Why it matters

Lesson 9 explains what LoRA is. Interviewers then ask what you did with it: where the data came from, how you split it, how you knew the model was better, and what you checked when it was not. These are project questions, and "I trained it and it looked good" fails them. In real work most fine-tuning failures have nothing to do with rank or alpha. They come from duplicated or mislabelled rows, a chat template that differs between training and serving, a test set that leaked, or no baseline to compare with. This lesson gives you one complete project story with numbers that you can adapt to your own.

Read first: [Hugging Face end to end](/ai/learn/hugging-face-end-to-end), [Vector DBs and RAG](/ai/learn/vector-dbs-rag), [What is fine-tuning - LoRA, QLoRA, DoRA](/ai/learn/fine-tuning-lora-qlora-dora)

## Lesson

### The use case

An online electronics store receives about 3,000 support tickets a day. For each ticket the system must return one JSON object: a `category` (one of 8), a `priority` (low, normal or urgent) and a `reply` draft of at most 80 words in the store's tone. A human agent checks the draft and sends it.

The whole lesson follows this case. Lesson 9 is the prerequisite: it explains LoRA, QLoRA, rank and alpha. This lesson covers the work around them.

![Six fine-tuning stages in a column, from the decision to serving, with a gate between each pair and the action to take when a gate fails](/ai/img/finetune-workflow-gates.svg)Six fine-tuning stages in a column, from the decision to serving, with a gate between each pair and the action to take when a gate fails

### Fine-tune, prompt or RAG?

Use the cheapest tool that passes the eval.

| What is missing | Tool | In the ticket case |
| --- | --- | --- |
| The model does not know what you want | Prompt: instructions and a few examples | Category list, JSON schema, 8 example tickets |
| The model lacks facts, or the facts change | RAG | Refund window, warranty terms |
| The model knows the task but does it unreliably, or the prompt is too long for your volume | Fine-tuning | Consistent categories, valid JSON every time, house tone |

Fine-tuning changes behaviour, not knowledge. Do not train the refund policy into the weights: when the window changes from 7 to 10 days you would have to retrain. Keep facts in retrieval, and put the retrieved policy snippet into every training prompt, so the model practises using context the way it will in production.

Fine-tune only when you have a stable task, a real eval and roughly 500 or more good examples, and only after you have measured a prompt baseline. Here the best few-shot prompt reaches 80% category accuracy with a 2,600-token prompt, and the target is 90%. At 3,000 tickets a day that prompt costs 7.8 million input tokens a day. A tuned model with a 400-token prompt needs 1.2 million.

### Building and cleaning the dataset

Each training example is one conversation in the `messages` format: a system message, a user message (ticket plus policy snippet) and an assistant message (the target JSON). The best source is your own resolved tickets, because they look like production inputs.

1. **Filter for quality.** Keep tickets that a human agent resolved without a reopen. A model trained on bad replies writes bad replies.
2. **Mask PII (personal data).** Replace emails, phone numbers and addresses with placeholders before the data leaves the ticket system.
3. **Remove duplicates.** Normalise case and whitespace, then drop repeats. Pasted macros can fill a large part of a support export, and a duplicate that lands in both train and test inflates the score.
4. **Check the labels.** Have two people relabel a sample of 200. If they often disagree with the stored label, fix the label guide first. The model cannot be more consistent than its labels.
5. **Validate the targets.** Every assistant message must parse as JSON and use only allowed labels. Malformed targets teach malformed output.
6. **Check the length.** Count tokens per example. The trainer cuts at `max_length` and keeps the start, so in a long example the part that is lost is the answer.
7. **Balance.** Cap the largest categories so "where is my order" does not fill most of the set, and keep every example of a rare class that matters, such as fraud.

How much data? For tone or instruction following, 500 to 2,000 clean examples often beat tens of thousands of noisy ones. Domain adaptation needs more, around 5,000 to 20,000. Preference tuning with DPO needs about 1,000 to 5,000 pairs. If real examples are too few, a larger model can draft targets for real inputs. People must still review a sample, and the test set stays human-labelled.

### Chat template and special tokens

Lesson 6 explains templates. For training, five rules matter.

* **Use the base model's own template.** The trainer applies it to a `messages` column. Print one rendered example and read it before any run.
* **End every assistant turn with the end-of-turn token.** That token is how the model learns to stop. A tuned model that keeps writing after the JSON usually never saw it in training.
* **Keep padding away from the end token.** If padding reuses the end token and your collator (the function that pads examples into a batch) removes every position with that id from the loss, the end token is never trained.
* **Train on the answer.** By default the loss covers every token, including the ticket text. `assistant_only_loss=True` in `SFTConfig` limits it to assistant tokens, if the template supports it.
* **Serve what you trained.** Same system prompt, same message order, same template, plus `add_generation_prompt=True` at inference.

Avoid adding new special tokens. If you must, the embedding table has to be resized, trained and saved with the adapter.

### Train, validation and test split

Hold out 10 to 20% of the data. The usual split is 80 / 10 / 10, and each part has one job.

* **Train:** the adapter learns from it.
* **Validation:** you choose the checkpoint and the hyperparameters on it.
* **Test:** you touch it once, to compare with the base model.

Split by customer, not by row. Two tickets from one customer share names, products and phrasing, so a random row split leaks. Remove duplicates before splitting, and check that every category appears in every split. If you can, take the test set from the most recent weeks, because production data is always newer than training data. Then freeze the test set and version it.

### QLoRA hyperparameters

| Setting | Start with | Change it when |
| --- | --- | --- |
| Rank and alpha | r = 16, alpha = 32 | Raise r if validation loss stalls high on clean data |
| Target modules | All linear layers | Attention projections only, if memory is tight |
| LoRA dropout | 0.05 | Raise to 0.1 if a small set overfits |
| Learning rate | 1e-4 to 2e-4 | Halve it if the loss is spiky |
| Epochs | 3, keeping the best checkpoint | Fewer for large sets |
| Effective batch | 16: 4 per step x 4 accumulation steps | Smaller steps and more accumulation if memory runs out |
| Warmup | About 5% of the steps | Longer if the first steps diverge |
| `max_length` | Above your longest example | Never below it |

PEFT's own defaults are r = 8 and alpha = 8, so set both yourself. Lesson 9 starts LoRA on the attention projections; with a 4-bit base the usual start is all linear layers, following the QLoRA paper's finding. Gradient accumulation adds up the gradients of 4 small batches before one optimiser step, so you get the effect of a batch of 16 in the memory of a batch of 4. Warmup raises the learning rate from zero over the first steps, so early updates stay small. With 1,920 training examples and an effective batch of 16, one epoch is 120 optimiser steps and the full run is 360.

```
# needs: transformers, peft, trl, datasets, bitsandbytes, torch
import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoTokenizer, BitsAndBytesConfig, EarlyStoppingCallback
from trl import SFTConfig, SFTTrainer

base_id = "HuggingFaceTB/SmolLM2-1.7B-Instruct"   # any instruct model your GPU can hold
data = load_dataset("json", data_files={"train": "train.jsonl", "validation": "validation.jsonl"})
tokenizer = AutoTokenizer.from_pretrained(base_id)
print(tokenizer.apply_chat_template(data["train"][0]["messages"], tokenize=False))  # read it

trainer = SFTTrainer(
    model=base_id,
    train_dataset=data["train"],
    eval_dataset=data["validation"],
    processing_class=tokenizer,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16),
    peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                           target_modules="all-linear", task_type="CAUSAL_LM"),
    args=SFTConfig(
        output_dir="ticket-triage-adapter", max_length=1024,
        learning_rate=2e-4, warmup_steps=20, num_train_epochs=3,
        per_device_train_batch_size=4, gradient_accumulation_steps=4,
        logging_steps=10, eval_strategy="steps", eval_steps=30,
        save_strategy="steps", save_steps=30, load_best_model_at_end=True,
        metric_for_best_model="eval_loss", greater_is_better=False),
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
)
trainer.train()
trainer.save_model("ticket-triage-adapter/best")
```

`EarlyStoppingCallback` ends the run after 3 evaluations without a lower validation loss, and `load_best_model_at_end` reloads the best checkpoint before saving.

The script uses a 1.7-billion-parameter model so it runs on a free notebook GPU. The 4-bit load is what lets you swap in an 8-billion-parameter model on the same 16 GB card: 16 GB of weights in 16-bit, about 4 GB in 4-bit.

### Reading loss curves

Training loss is logged every 10 steps and validation loss every 30. Read the two together.

| What you see | What it means | What to do |
| --- | --- | --- |
| Both fall, then validation flattens | A healthy run | Keep the checkpoint with the lowest validation loss |
| Training falls, validation rises | Overfitting | Earlier checkpoint, fewer epochs, more or cleaner data |
| Both flat from the first step | Nothing is learning | Raise the learning rate; check the adapter is attached |
| Loss jumps around or becomes NaN | Learning rate too high | Halve it, add warmup |
| Training loss near zero inside one epoch | Memorising | Look for duplicates or a leak |
| Very high loss at step 0 | The input looks strange to the model | Check the template |

A model that guesses evenly over a 32,000-token vocabulary has a loss of ln 32,000 = 10.4. A pretrained model on well-formatted text starts far below that. Loss also is not the goal: it picks the checkpoint, and task metrics decide whether you ship.

### Evaluating against the base model

Score the base and the fine-tuned model on the same test prompts with task metrics and an LLM judge, then run a regression check on general tasks. If the gain is not clear, do not ship.

* **Three contenders:** the base model with its best zero-shot prompt, the base model with the few-shot prompt (the real alternative), and the tuned model. Same test tickets, greedy decoding.
* **One metric per field:** JSON validity by a code check, category accuracy and recall on urgent tickets by exact match, reply quality by a judge model with a rubric that you have checked against about 50 human ratings.
* **Know the noise.** With 240 test tickets and 80% accuracy, the standard error is sqrt(0.8 x 0.2 / 240) = 2.6 points, so the 95% range is about plus or minus 5 points. A 2-point gain proves nothing.
* **Check for catastrophic forgetting:** the model gets better at the new task and worse at things it knew before. Run about 100 general prompts through both models.
* **Read 20 raw outputs.** Metrics miss a reply that is valid JSON and rude.

### Merging and serving the adapter

| Option | What you deploy | Use it when |
| --- | --- | --- |
| Merged | One full model with BA added into W | One task per deployment; no extra latency |
| Unmerged | The base model plus adapters loaded by name | Many tasks or customers on one GPU; fast rollback |

```
# needs: transformers, peft, torch (base_id and tokenizer come from the training script)
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM

base = AutoModelForCausalLM.from_pretrained(base_id, dtype=torch.bfloat16)   # 16-bit, not 4-bit
merged = PeftModel.from_pretrained(base, "ticket-triage-adapter/best").merge_and_unload()
merged.save_pretrained("ticket-triage-merged")
tokenizer.save_pretrained("ticket-triage-merged")
```

```
# needs: vllm
vllm serve HuggingFaceTB/SmolLM2-1.7B-Instruct --enable-lora \
    --lora-modules ticket-triage=ticket-triage-adapter/best
```

With vLLM a request selects the adapter by putting `ticket-triage` in the `model` field. Merge into the 16-bit base, then run the test set again on the exact artefact you serve, because the adapter was trained against 4-bit weights. Record the base model revision, the dataset version and the system prompt with the adapter. Roll out in shadow mode (the model runs on real tickets but agents do not see its output), then to a small share of traffic, called a canary. Rolling back means removing the adapter.

### Debugging a model that got worse

Check in this order, cheapest first.

1. **Template and special tokens.** Print a rendered training example and the inference prompt and compare them character by character. This is the most frequent bug.
2. **Is the adapter loaded?** If outputs match the base model exactly, it is not.
3. **Learning rate too high.** The loss curve is spiky.
4. **Too many epochs on small data.** Validation loss rose and you kept the last checkpoint.
5. **Noisy or mislabelled examples.** Read 50 random training rows.
6. **Training data that does not match production inputs.** For example, you trained on cleaned tickets and production tickets carry signatures and forwarded threads.
7. **The eval itself.** Sampling left on, or `max_new_tokens` so small that the JSON is cut off.

## Diagram

Rendering diagram…

## Worked example

**The ticket-triage run from baseline to decision.** The figures are for the example store. Follow the arithmetic, not the absolute values.

1. **Baseline.** On 240 test tickets, the base model with its best zero-shot prompt returns valid JSON for 214 (89.2%) and the right category for 170 (70.8%). With 8 few-shot examples in a 2,600-token prompt: 233 valid (97.1%) and 192 right (80.0%). The target is 90%.
2. **Data funnel.** 60,000 sampled resolved tickets. Quality filter (human-resolved, not reopened): 22,000 left. Duplicates removed: 9,500. Invalid targets and over-length examples removed: 9,100. Cap of 320 per category, with all 160 fraud tickets kept: 7 x 320 + 160 = 2,400.
3. **Split by customer, 80 / 10 / 10.** 1,920 train, 240 validation, 240 test. A real customer split lands a few rows off these round numbers.
4. **Steps.** Effective batch 16, so 1,920 / 16 = 120 steps per epoch and 360 for 3 epochs. Evaluating every 30 steps gives up to 12 validation points.
5. **Size of the job.** At an average of 420 tokens per example, one epoch is 1,920 x 420 = 806,400 tokens and the full run is 2,419,200. At an assumed 2,000 training tokens per second that is 1,210 seconds, about 20 minutes.
6. **Loss curve.** Validation loss is 1.12 at step 30, 0.78 at step 120 and 0.71 at step 240. The next three evaluations are all higher, ending at 0.74 at step 330, while training loss keeps falling to 0.36. With a patience of 3, early stopping ends the run there and reloads the step-240 checkpoint.
7. **Test.** The tuned model returns valid JSON for 240 of 240 and the right category for 218 (90.8%). That is 10.8 points above the few-shot prompt, against a noise range of about 5 points. It finds 31 of 36 urgent tickets (86%); the few-shot prompt found 24 (67%).
8. **Regression.** On 100 general prompts the base passes 93 and the tuned model 91. For 100 prompts at 93% the noise range is also about 5 points, so there is no sign of forgetting.
9. **Decision.** Ship behind a canary. The prompt shrinks from 2,600 to 400 tokens, so daily input drops from 3,000 x 2,600 = 7.8 million tokens to 3,000 x 400 = 1.2 million.

Had step 7 shown 82% against 80%, the right call would be not to ship: 2 points is inside the noise, and the prompt-only system has nothing to retrain.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""Two parts of a fine-tuning pipeline that run without a GPU.

Part 1, the data gates: validate, mask PII, dedupe and split support tickets
        by customer, so no customer appears in two splits.
Part 2, a toy LoRA run in NumPy: a frozen "base" classifier gets a rank-4
        adapter. Read the two loss curves, keep the best checkpoint, and
        compare base, best and last on a held-out test set.
"""
import hashlib
import json
import math
import random
import re
from collections import Counter

import numpy as np

CATEGORIES = ["billing", "delivery", "returns", "account"]
PRIORITIES = ["low", "normal", "urgent"]
MAX_TOKENS = 120                                   # budget for one ticket
TEXTS = {
    "billing": "I was charged twice for order {o}. Please refund one payment.",
    "delivery": "Order {o} was due on Monday and has still not arrived.",
    "returns": "The headphones from order {o} are faulty. How do I send them back?",
    "account": "I cannot log in after changing my phone. Order {o} is stuck in my cart.",
}

def make_raw(n=400, seed=7):
    """Synthetic export of resolved tickets, with the defects real exports have."""
    rnd, rows = random.Random(seed), []
    for i in range(n):
        cat = rnd.choice(CATEGORIES)
        ticket = TEXTS[cat].format(o=10000 + rnd.randrange(90000))
        target = json.dumps({"category": cat, "priority": rnd.choice(PRIORITIES),
                             "reply": "Sorry about this. We are checking it now."})
        if i % 9 == 4:                                 # the same ticket filed again, in capitals
            ticket, target = "  " + rows[i - 2]["ticket"].upper(), rows[i - 2]["target"]
        if i % 11 == 0:
            ticket += " Mail me at user%d@example.com." % i   # PII to mask
        if i % 25 == 3:
            target = target[:-9]                       # cut off: not valid JSON
        if i % 31 == 5:
            target = target.replace(cat, "misc")       # label outside the schema
        if i % 40 == 7:
            ticket = ticket + " Please help." * 80     # far over the token budget
        rows.append({"customer": "c%03d" % rnd.randrange(90), "ticket": ticket, "target": target})
    return rows

def est_tokens(text):
    return math.ceil(len(text.split()) / 0.75)         # 1 token is about 0.75 words

def reject_reason(row):
    try:
        out = json.loads(row["target"])
    except json.JSONDecodeError:
        return "target is not valid JSON"
    if out.get("category") not in CATEGORIES or out.get("priority") not in PRIORITIES:
        return "label outside the schema"
    if not out.get("reply", "").strip():
        return "empty reply"
    if est_tokens(row["ticket"]) > MAX_TOKENS:
        return "ticket over the token budget"
    return None

def clean(rows):
    kept, seen, dropped = [], set(), Counter()
    for row in rows:
        reason = reject_reason(row)
        if reason:
            dropped[reason] += 1
            continue
        row = dict(row, ticket=re.sub(r"\S+@\S+\.\w+", "<EMAIL>", row["ticket"]).strip())
        key = hashlib.sha1(" ".join(row["ticket"].lower().split()).encode()).hexdigest()
        if key in seen:                                # same text after normalising
            dropped["duplicate"] += 1
            continue
        seen.add(key)
        kept.append(row)
    return kept, dropped

def split_by_customer(rows, seed=0):
    """80/10/10 over customers, not rows: one customer's tickets stay together."""
    customers = sorted({r["customer"] for r in rows})
    random.Random(seed).shuffle(customers)
    a, b = int(0.8 * len(customers)), int(0.9 * len(customers))
    part = {c: "train" for c in customers[:a]}
    part.update({c: "validation" for c in customers[a:b]})
    part.update({c: "test" for c in customers[b:]})
    splits = {"train": [], "validation": [], "test": []}
    for r in rows:
        splits[part[r["customer"]]].append(r)
    return splits

def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)

def toy_run(lr, steps=400, seed=0):
    """Frozen W0 plus a trainable rank-4 update B A, trained on 120 noisy examples."""
    rng = np.random.default_rng(seed)
    d, k, r, scale = 4, 24, 4, 2.0                     # classes (outputs), features (inputs), rank, alpha / r
    W0 = rng.normal(0, 0.5, (d, k))                    # the frozen base, d x k as in lesson 9
    W_task = W0 + rng.normal(0, 0.8, (d, 2)) @ rng.normal(0, 0.8, (2, k))   # what the task needs

    def data(n, noise):
        X = rng.normal(size=(n, k))
        y = (X @ W_task.T).argmax(axis=1)
        flip = rng.random(n) < noise                   # mislabelled rows
        y[flip] = rng.integers(0, d, flip.sum())
        return X, y

    (Xtr, ytr), (Xva, yva), (Xte, yte) = data(120, 0.2), data(400, 0.2), data(2000, 0.0)
    A, B = rng.normal(0, 0.1, (r, k)), np.zeros((d, r))    # A is r x k, B is d x r and starts at 0

    def loss_acc(X, y, A, B):
        p = softmax(X @ (W0 + scale * B @ A).T)
        return float(-np.log(p[np.arange(len(y)), y] + 1e-12).mean()), float((p.argmax(1) == y).mean())

    curve, best = [], (np.inf, 0, A.copy(), B.copy())
    for step in range(steps + 1):
        tr, va = loss_acc(Xtr, ytr, A, B)[0], loss_acc(Xva, yva, A, B)[0]
        if step % 50 == 0:
            curve.append((step, tr, va))
        if va < best[0]:
            best = (va, step, A.copy(), B.copy())      # checkpoint with the lowest validation loss
        p = softmax(Xtr @ (W0 + scale * B @ A).T)
        p[np.arange(len(ytr)), ytr] -= 1               # gradient at the logits: p - y
        G = p.T @ Xtr / len(ytr)                       # gradient for the full matrix
        gB, gA = scale * G @ A.T, scale * B.T @ G      # chain rule into B and A; W0 gets nothing
        B, A = B - lr * gB, A - lr * gA
    acc = {"base": loss_acc(Xte, yte, A * 0, B * 0)[1],
           "best": loss_acc(Xte, yte, best[2], best[3])[1],
           "last": loss_acc(Xte, yte, A, B)[1]}
    return curve, best[1], acc

if __name__ == "__main__":
    print("PART 1. Data gates")
    raw = make_raw()
    kept, dropped = clean(raw)
    print(f"  raw rows: {len(raw)}   kept: {len(kept)}   dropped: {dict(dropped)}")
    assert not any("@" in r["ticket"] for r in kept), "PII left in the data"
    splits = split_by_customer(kept)
    owners = {name: {r["customer"] for r in rows} for name, rows in splits.items()}
    assert not (owners["train"] & owners["validation"] or owners["train"] & owners["test"]
                or owners["validation"] & owners["test"])
    for name, rows in splits.items():
        mix = Counter(json.loads(r["target"])["category"] for r in rows)
        print(f"  {name:10s} {len(rows):3d} rows, {len(owners[name]):2d} customers, {dict(sorted(mix.items()))}")
    print("  no customer appears in two splits")

    print("\nPART 2. Reading loss curves on a toy adapter")
    for lr, label in ((0.05, "sensible learning rate"), (1.0, "learning rate 20 times too high")):
        curve, best_step, acc = toy_run(lr)
        print(f"  {label} (lr = {lr})")
        for step, tr, va in curve:
            print(f"    step {step:3d}   train loss {tr:7.3f}   validation loss {va:7.3f}")
        print(f"    lowest validation loss at step {best_step}")
        print(f"    test accuracy: base {acc['base']:.3f}, best checkpoint {acc['best']:.3f}, "
              f"last checkpoint {acc['last']:.3f}")
```

## Key takeaways

* Fine-tune for behaviour (format, consistency, tone, a shorter prompt), keep facts in RAG, and measure a prompt baseline first. That baseline is the number to beat.
* The dataset decides the result: filter for quality, mask PII, dedupe, validate every target, check lengths and balance classes. 500 to 2,000 clean examples are enough for tone or instruction following.
* Format with the base model's own chat template, end every assistant turn with the end token, and serve with the same template and system prompt you trained with.
* Split 80 / 10 / 10 by customer, after deduplication. Validation picks the checkpoint; the test set is used once.
* Start QLoRA at r = 16, alpha = 32, learning rate 1e-4 to 2e-4, 3 epochs, effective batch 16, and keep the checkpoint with the lowest validation loss.
* Compare the tuned model with the base model and with the best prompt on the same test set, and know the noise: about 5 points for 240 examples at 80%.
* Merge the adapter for one task with no added latency, or serve it unmerged for many tasks on one base. Re-score the exact artefact you deploy.
* When a tuned model is worse than the base, check the template first, then that the adapter is loaded, then learning rate, epochs, labels and data mismatch.

## Common mistakes

* Fine-tuning before measuring what a good prompt and retrieval can do, so there is no baseline to beat.
* Splitting rows at random when one customer or one template appears many times, then reporting a test score that is partly memorised.
* Training with one system prompt or template and serving with another.
* Leaving `max_length` at a value below the longest example, which silently cuts off the answers the model was meant to learn.
* Keeping the last checkpoint when validation loss turned up an epoch earlier.
* Calling a 2-point gain on 200 test examples an improvement.

## Practice

* Run the code example. Change `split_by_customer` to split rows at random, remove the assert that forbids overlap, and count how many customers then appear in both train and test. Report the number.
* Take 200 examples of any classification-plus-text task you have. Write the validation rules for your schema, run them, and report how many rows fail each rule.
* Fine-tune a small instruct model on 500 to 1,000 examples with the script in this lesson. Report the validation loss at every evaluation, the step you kept, and the score of the base model and the tuned model on the same held-out set with greedy decoding.
* Break it on purpose: train once with the system prompt removed from the training data but kept at inference. Report the change in your test metric, and write down which check from the debugging list would have caught it.

## Interview questions (12)

1.How much data do you need?Easy

For tone or instruction following, 500 to 2,000 clean examples often beat tens of thousands of noisy ones. Domain adaptation needs more, around 5,000 to 20,000. Preference tuning with DPO needs about 1,000 to 5,000 pairs. Quality and match to real inputs matter more than volume. In practice I start small and measure. I train on 500, 1,000 and 2,000 examples and plot the test metric. If the curve is still rising I collect more; if it is flat, more rows of the same kind will not help and I look at label quality or coverage of rare cases. I also count per class: 2,000 examples with only 12 of the fraud class is not enough for that class.

2.What is catastrophic forgetting?Medium

The model gets better at the new task and worse at things it knew before. Reduce it with PEFT instead of full fine-tuning, a lower learning rate, fewer epochs, mixing in general data, and a regression eval on general tasks. In a project I make it measurable. I keep about 100 general prompts, such as summarising, simple reasoning and following a format instruction, and run them through the base and the tuned model. If the tuned model drops by more than the noise, I go back to an earlier checkpoint or mix some general examples into the training set. With an unmerged LoRA adapter there is also a simple escape: requests outside the task go to the base model with no adapter.

3.How do you evaluate a fine-tuned model before shipping?Medium

Hold out 10 to 20% of the data. Score the base and the fine-tuned model on the same prompts with task metrics and an LLM judge. Then run a regression check on general tasks. If the gain is not clear, do not ship. The details that matter: the held-out set is split by customer so nothing leaks, and it is frozen. The base model gets its best prompt, including few-shot examples, because that is the real alternative. Decoding is greedy so runs are repeatable. I use a code check where one exists, such as JSON validity and exact match on labels, and a judge with a rubric only for free text, checked against human ratings. I work out the noise for my test size, and I score the exact merged or served artefact, not only the training checkpoint.

4.Your fine-tuned model is worse than the base. What went wrong?Hard

Common causes: wrong chat template or missing special tokens, learning rate too high, too many epochs on small data, noisy or mislabelled examples, or training data that does not match production inputs. Check the template first; it is the most frequent bug. My order of checks is cheapest first. I print a rendered training example and the inference prompt and compare them character by character, including the end token and the generation prompt. I confirm the adapter is loaded, because outputs identical to the base mean it is not. Then I read the loss curves: spikes mean the learning rate, rising validation loss means too many epochs. Then I read 50 random training rows for label errors. Last, I compare training inputs with real production inputs.

5.When would you fine-tune and not just prompt or add RAG?Medium

I ask what is missing. If the model does not know what I want, that is a prompt problem. If it lacks facts or the facts change, that is retrieval. Fine-tuning is for behaviour that prompting cannot make reliable: a strict output format, consistent labels, a house tone, or tool-call style. It also pays when the prompt has grown long. In my ticket example a 2,600-token few-shot prompt became a 400-token prompt after tuning, which at 3,000 tickets a day is 7.8 million against 1.2 million input tokens. My conditions are a stable task, a real eval, about 500 or more good examples and a measured prompt baseline. Without a baseline I cannot show the fine-tune was worth it.

6.How do you build and clean a fine-tuning dataset?Medium

I start from real inputs, ideally production logs with outputs that a person approved, because the model must see the same kind of input it will get later. Then I filter. I keep only high-quality outputs, mask personal data, and remove exact and near duplicates. I validate every target against the schema, and I count tokens so that nothing is cut by the length limit. I check label quality by having two people relabel a sample. I balance the classes by capping the biggest and keeping all of the rare ones. I write each example in the messages format with the same system prompt I will use in production. Finally I read 50 random rows myself, which finds problems no script does.

7.How do you split the data, and what is leakage?Medium

I use 80 percent for training, 10 for validation and 10 for test. Validation chooses the checkpoint and hyperparameters, and the test set is used once for the final comparison. Leakage means information from the test set reached training, so the score is too optimistic. In text data the usual sources are duplicates, templates and related rows, such as several tickets from one customer or several chunks of one document. So I remove duplicates first and split by group, for example by customer id, and not by row. When data changes over time I take the test set from the latest period. A sign of leakage is a test score far above what you see in production.

8.Which QLoRA hyperparameters do you start with, and which do you tune first?Medium

I start with rank 16 and alpha 32 on all linear layers, LoRA dropout 0.05, a learning rate of 1e-4 to 2e-4, three epochs and an effective batch of 16 through gradient accumulation. The base is loaded in 4-bit NF4 with bfloat16 compute. I evaluate several times per epoch and keep the checkpoint with the lowest validation loss. I tune the learning rate first, because it causes the most damage: a spiky loss means halve it. Then the number of epochs, read from where validation loss turns up. I raise the rank only if the data is clean and validation loss stalls high. I change one thing per run so I know what helped.

9.Training loss keeps falling but outputs get worse. How do you read the loss curves?Medium

I look at training and validation loss together. If both fall and validation flattens, the run is healthy and I take the lowest-validation checkpoint. If training falls while validation rises, the model is memorising, so I take an earlier checkpoint, cut epochs or add data. Training loss near zero inside the first epoch suggests duplicates or a leak. A flat loss from step one means nothing is learning: the learning rate is too low or the adapter is not attached. Spikes or NaN mean the learning rate is too high. I also remember that loss is only a proxy. I pick the checkpoint on validation loss and then confirm with the task metric on generated outputs.

10.Your fine-tuned model never stops generating. Why?Hard

Most often the model never learned the end-of-turn token. In training, every assistant message must end with the token the chat template uses to close a turn, and that position must count in the loss. It goes wrong in three ways. The data was formatted by hand without the end token. The padding token is the same as the end token and the collator removes all positions with that id from the loss. Or the examples were truncated at the length limit, so the end of each answer was cut off. At inference I also check that generation stops on the same token the template uses. The fix is to render one training example, confirm the end token is there, and retrain.

11.Merge the adapter or serve it separately?Medium

Merging adds the low-rank update into the base weights, so I deploy one normal model with no extra latency. I do that when one deployment serves one task. I merge into the 16-bit base, not the 4-bit copy used for training, and I run the test set again on the merged model. Serving it unmerged keeps one base model in memory and loads adapters by name, which servers such as vLLM support. I choose that for many tasks or customers on one GPU, and because rollback is just removing a small file. The cost is a little extra compute per request.

12.Can you use an LLM to create the training data?Hard

Yes, with limits. The common pattern is distillation: take real inputs, let a large model write the outputs, and train a small model on them. It works well when the task is narrow and the large model is already good at it. The risks are that the student copies the teacher's mistakes and style, and that fully synthetic inputs do not look like real ones. So I keep the inputs real where I can, filter the generated outputs with code checks and a second-pass judge, and have people review a sample. The test set stays human-labelled and is never generated, or I would only measure agreement with the teacher.

## Quiz

1.The refund window changes every few months. Where should that fact live?

2.You have 1,920 training examples, a per-step batch of 4 and 4 gradient accumulation steps. How many optimiser steps is one epoch?

3.Training loss falls to 0.02 within the first epoch and validation loss is rising. What is the most likely cause?

4.On 240 test tickets the tuned model scores 82% and the few-shot prompt scores 80%. What should you conclude?

5.After training, the tuned model's outputs are identical to the base model's, token for token. What should you check first?

6.Why split by customer and not by row?

## Practice these problems

* [GENAILoRA fine-tuning pipeline with an adapter registryHard](/ai/problems/fine-tuning-pipeline)
* [GENAIEvaluation harness for LLM apps and agentsMedium](/ai/problems/llm-eval-harness)
* [GENAIStructured data extraction from documentsEasy](/ai/problems/structured-extraction)
* [MLSDMulti-tenant LoRA adapter servingMedium](/ai/problems/multi-lora-serving)
* [MLCODELoRA layer: forward, train and mergeMedium](/ai/problems/lora-layer)

## Further reading

* [Hugging Face TRL documentationGuidehuggingface.co](https://huggingface.co/docs/trl)
* [Hugging Face PEFT documentationGuidehuggingface.co](https://huggingface.co/docs/peft)
* [vLLM documentationGuidedocs.vllm.ai](https://docs.vllm.ai/)
* [Fine-Tuning LLMs in 2026: LoRA, QLoRA, DPO, GRPO ComparedArticlefutureagi.com](https://futureagi.com/blog/fine-tuning-llms-unlocking-peak-performance/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousWhat is fine-tuning - LoRA, QLoRA, DoRA](/ai/learn/fine-tuning-lora-qlora-dora)[NextInference and serving - KV cache, batching, vLLM](/ai/learn/inference-serving)

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

1. [The use case](#the-use-case)
2. [Fine-tune, prompt or RAG?](#fine-tune-prompt-or-rag)
3. [Building and cleaning the dataset](#building-and-cleaning-the-dataset)
4. [Chat template and special tokens](#chat-template-and-special-tokens)
5. [Train, validation and test split](#train-validation-and-test-split)
6. [QLoRA hyperparameters](#qlora-hyperparameters)
7. [Reading loss curves](#reading-loss-curves)
8. [Evaluating against the base model](#evaluating-against-the-base-model)
9. [Merging and serving the adapter](#merging-and-serving-the-adapter)
10. [Debugging a model that got worse](#debugging-a-model-that-got-worse)
