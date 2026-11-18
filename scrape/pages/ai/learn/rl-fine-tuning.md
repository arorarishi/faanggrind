# RL fine-tuning — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/rl-fine-tuning

[AI roadmap](/ai)

LaterLesson #20LaterAdvanced 1.5 h

# RL fine-tuning

Supervised fine-tuning needs the right answer written out for every example. Reinforcement learning (RL) fine-tuning needs only a score: which of two answers a person preferred, or whether a program accepted the answer. This lesson explains policy, reward and policy gradient in plain words, then the three methods used on LLMs: RLHF with PPO, DPO and GRPO, with what each needs and how each fails.

reinforcement learningrlhfppodpogrporlvrreward hacking

## Why it matters

"RLHF vs DPO vs GRPO?" is a standard follow-up once you say you have fine-tuned a model, and "what have you been following lately?" often leads to reasoning models trained with verifiable rewards. Interviewers want one thing: can you pick the method from the signal you have, and do you know how a reward gets gamed. In real work the same knowledge stops you from building a reward model when 2,000 preference pairs and one training pass would do, and from trusting a reward curve that goes up while the model gets worse.

Read first: [Neural networks and backprop](/ai/learn/neural-networks-backprop), [LLM fundamentals - tokens, embeddings, decoding](/ai/learn/llm-fundamentals), [What is fine-tuning - LoRA, QLoRA, DoRA](/ai/learn/fine-tuning-lora-qlora-dora)

## Lesson

### Where RL fits in training an LLM

An LLM is trained in stages: pretraining on raw text (next-token prediction), then supervised fine-tuning (SFT) on instructions, then preference alignment (RLHF or DPO). Reasoning models add reinforcement learning with verifiable rewards.

SFT copies answers you wrote. Often you have no such answer. You only know that answer A is better than answer B, or that a program can check the final result. RL trains from that weaker signal: a score, not a target text.

### RL in five terms

| Term | Plain meaning | For an LLM |
| --- | --- | --- |
| Policy | The rule that picks the next action | The LLM: a probability for every next token |
| State | What the policy sees | The prompt plus the tokens written so far |
| Action | One choice | One token; an answer is a sequence of actions |
| Reward | A number that scores the result | The score of the finished answer |
| Advantage | Reward minus a baseline | How much better this answer was than a typical one |

### Policy gradient in plain words

Let the model answer, score the answer, then raise the probability of answers that scored above average and lower the rest.

Formula

∇θ​J=E[(R−b)∇θ​logπθ​(y∣x)]

Here y is an answer the model sampled for prompt x, R is its reward and b is the baseline, for example the average reward. Compare it with SFT. SFT raises the log-probability of an answer you supplied, with weight 1. Policy gradient raises the log-probability of an answer the model produced, with weight R - b, which can be negative.

Two problems follow. The estimate is noisy, because a few samples say little. And one large step can damage the policy, which then generates bad samples and learns from them. Each method below is a way to control these two problems.

### RLHF with PPO

RLHF (reinforcement learning from human feedback) trains a reward model on human preferences, then optimises the LLM against it. It is strong but heavy to run.

1. **Collect comparisons.** People see two answers to one prompt and pick the better one.
2. **Train a reward model.** A network reads a prompt and an answer and outputs one number. It is trained so the preferred answer scores higher.
3. **Optimise with PPO.** The LLM generates new answers (online sampling), the reward model scores them, and PPO updates the LLM.

PPO (proximal policy optimisation) limits each update. It takes the ratio between the new and the old probability of a sampled answer and clips it to a narrow range, commonly 0.8 to 1.2 (a clip value of 0.2, the example the PPO paper gives), so one batch cannot move the policy far. A KL penalty also keeps the LLM close to the SFT model. KL divergence measures how different two probability distributions are.

The cost: up to four networks in memory (the policy, a frozen reference copy, the reward model and a value model that predicts expected reward), sampling inside the training loop, and many settings to tune.

### DPO

DPO (direct preference optimisation) is preference tuning from chosen and rejected pairs with one loss and no reward model. It is the usual first choice for preference tuning after SFT, and it needs about 1,000 to 5,000 pairs. One row looks like this:

```
{"prompt": "I bought this 40 days ago. Can I get a refund?",
 "chosen": "Refunds close at 30 days, so I cannot refund this. I can offer store credit.",
 "rejected": "Sure, your refund is on its way!"}
```

Formula

LDPO​=−logσ(β[logπref​(yw​∣x)πθ​(yw​∣x)​−logπref​(yl​∣x)πθ​(yl​∣x)​])

y\_w is the chosen answer, y\_l the rejected one, and the reference is a frozen copy of the model from before DPO. The loss falls when the model raises the chosen answer more than the rejected one, both measured against the reference. Beta sets how far the model may move from the reference; 0.1 is a common default.

It is one offline pass with no sampling, so it runs like SFT with two answers per row. The limit comes from the same fact: the model never gets a score for its own new answers, so it learns only what the pairs cover.

### GRPO and RLVR

RLVR (reinforcement learning with verifiable rewards) is RL where the reward comes from an automatic correctness check, not a human-trained reward model. DeepSeek-R1 made it mainstream. The line to say: "If I have a verifier, such as unit tests, I can train reasoning without human labels." GRPO (group relative policy optimisation) is the usual algorithm:

1. Generate a group of answers per prompt, for example 16.
2. Score each with an automatic verifier: tests pass, maths correct, valid JSON.
3. Push the model toward the above-average ones.

Formula

Ai​=std(r1​,…,rG​)ri​−mean(r1​,…,rG​)​

The group mean is the baseline, so no value model is needed. The clip from PPO stays. The original formulation also keeps a KL penalty toward a frozen reference; some trainers, such as the one in the TRL library, set it to zero by default, and then no reference copy is needed. GRPO is used for reasoning fine-tunes. It needs prompts whose answers a program can check, and compute to generate G answers per prompt at every step. If every answer in a group gets the same reward, all advantages are zero and that prompt teaches nothing. Tasks must be hard enough to fail sometimes and easy enough to pass sometimes.

### What each one needs

![Three columns comparing the signal and the training loop of RLHF with PPO, DPO and GRPO](/ai/img/rlhf-dpo-grpo-signal.svg)Three columns comparing the signal and the training loop of RLHF with PPO, DPO and GRPO

|  | RLHF with PPO | DPO | GRPO (RLVR) |
| --- | --- | --- | --- |
| Signal | Human comparisons, turned into a reward model | Chosen and rejected pairs | A verifier that checks answers automatically |
| Human labels | Yes | Yes | No |
| Sampling in training | Online | None, one pass | Online, a group per prompt |
| Extra networks | Reward, value, reference | Reference | Reference, only if the KL penalty is on |
| Right tool when | Quality is a matter of taste and you can afford the loop | You want tone, style or helpfulness tuned cheaply | Correctness can be checked: maths, code, structured output |

Choose by what signal you have.

### How they fail

* **Reward hacking.** The model scores high without doing the task. A verifier that only checks "the output ends with a number" rewards any number. Weak unit tests reward code that special-cases the tests. A reward model that likes long, polite text gets long, polite text.
* **A judge that can be gamed.** An LLM judge used as the reward is a reward model nobody calibrated, and training gives the policy thousands of tries to find its blind spots. The DeepSeek-R1 paper used rule-based accuracy and format rewards for this reason: it states that neural reward models are open to reward hacking in large-scale RL.
* **Collapse.** The policy puts almost all probability on one kind of answer. Outputs lose variety, groups become identical and learning stops. Usual causes: a learning rate that is too high, a KL penalty that is too weak, too many steps.
* **DPO drift.** The loss sees only the gap between chosen and rejected. The gap can grow while the probability of the chosen answer itself falls, so read generated text, not only the loss.

Defences for all three methods: keep a held-out eval the reward never touches, read samples at every checkpoint, stop when the reward rises but the held-out score does not, and run a regression eval on general tasks.

## Diagram

Rendering diagram…

## Worked example

**One GRPO step by hand.** The prompt is "A shop packs 17 boxes of 23 pens. How many pens?" The verifier reads the final number and gives 1 if it equals 391, else 0. The model samples a group of 6 answers and the rewards are 1, 0, 0, 1, 0, 0.

1. **Mean.** 2 / 6 = 0.333.
2. **Standard deviation.** Two answers are 0.667 above the mean and four are 0.333 below. Variance = (2 x 0.667^2 + 4 x 0.333^2) / 6 = (0.889 + 0.444) / 6 = 0.222. Std = 0.471.
3. **Advantages.** Correct answers: (1 - 0.333) / 0.471 = +1.414. Wrong answers: (0 - 0.333) / 0.471 = -0.707.
4. **Update.** Raise the log-probability of the two correct answers with weight 1.414 and lower the four wrong ones with weight 0.707. The weights sum to zero: 2 x 1.414 - 4 x 0.707 = 0.
5. **The empty case.** If all six answers were correct, the std is 0 and every advantage is 0. Nothing is learned from this prompt. The same happens when all six are wrong.

**One DPO pair by hand, with beta = 0.1.** Before training the model equals the reference, so both log-ratios are 0 and the loss is -log(sigmoid(0)) = log 2 = 0.693 for every pair.

Later in training the log-probabilities are:

| Answer | Model | Reference | Log-ratio |
| --- | --- | --- | --- |
| Chosen | -12.0 | -14.0 | +2.0 |
| Rejected | -11.0 | -10.5 | -0.5 |

The margin is 2.0 - (-0.5) = 2.5. Times beta: 0.25. Sigmoid(0.25) = 0.562, and the loss is -log(0.562) = 0.576, down from 0.693. Note that the rejected answer is still more likely than the chosen one in absolute terms (-11.0 against -12.0). DPO rewards movement relative to the reference, so check generated answers before you call the run a success.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""Policy gradient (GRPO style) and the DPO loss on a toy "LLM" with five possible answers.

The policy is a softmax over five logits, one per candidate answer to "What is 17 x 23?".
A real LLM gets the same kind of update, with log pi summed over the tokens of an answer.
"""
import numpy as np

ANSWERS = ["391", "381", "401", "40", "I am not sure"]
CORRECT = 0
START = np.array([0.0, 1.5, 0.5, 0.0, 0.5])    # the SFT model prefers the wrong answer "381"

def softmax(z):
    e = np.exp(z - z.max())
    return e / e.sum()

def show(p):
    return ", ".join(f"{a}: {x:.3f}" for a, x in zip(ANSWERS, p))

def strict_verifier(i):
    """Reward 1 only for the right answer."""
    return 1.0 if i == CORRECT else 0.0

def weak_verifier(i):
    """A careless check: 'is it a three-digit number?'. Three answers pass."""
    return 1.0 if ANSWERS[i].isdigit() and len(ANSWERS[i]) == 3 else 0.0

def grpo_train(verifier, steps=300, group=8, lr=0.2, seed=0):
    rng = np.random.default_rng(seed)
    logits = START.copy()
    history = {}
    for step in range(steps + 1):
        p = softmax(logits)
        if step in (0, 25, 50, 100, 300):
            history[step] = p[CORRECT]
        sampled = rng.choice(len(ANSWERS), size=group, p=p)      # a group of answers for one prompt
        r = np.array([verifier(i) for i in sampled])
        if r.std() == 0:                                         # all rewards equal: no signal
            continue
        adv = (r - r.mean()) / r.std()                           # group-relative advantage
        grad = np.zeros_like(logits)
        for i, a in zip(sampled, adv):
            one_hot = np.eye(len(ANSWERS))[i]
            grad += a * (one_hot - p)                            # a * d log pi(i) / d logits
        logits += lr * grad / group                              # gradient ascent on reward
    return softmax(logits), history

def dpo_loss(logits, ref_logits, chosen, rejected, beta):
    logp, logp_ref = np.log(softmax(logits)), np.log(softmax(ref_logits))
    margin = (logp[chosen] - logp_ref[chosen]) - (logp[rejected] - logp_ref[rejected])
    sig = 1.0 / (1.0 + np.exp(-beta * margin))
    grad = np.zeros_like(logits)
    grad[chosen], grad[rejected] = -beta * (1 - sig), beta * (1 - sig)   # d loss / d logits
    return -np.log(sig), grad

if __name__ == "__main__":
    print("start policy  :", show(softmax(START)))

    p, hist = grpo_train(strict_verifier)
    print("\nGRPO, strict verifier (reward 1 only for 391)")
    for step, prob in hist.items():
        print(f"  step {step:3d}  p(correct) = {prob:.3f}")

    p_weak, _ = grpo_train(weak_verifier)
    reward = sum(p_weak[i] * weak_verifier(i) for i in range(len(ANSWERS)))
    print("\nGRPO, weak verifier (any three-digit number passes)")
    print(f"  average reward = {reward:.3f}, but p(correct) = {p_weak[CORRECT]:.3f}")
    print("  final policy :", show(p_weak))

    print("\nDPO on one pair: chosen '391', rejected '381', beta = 0.1")
    logits, beta = START.copy(), 0.1
    for step in range(301):
        loss, grad = dpo_loss(logits, START, chosen=0, rejected=1, beta=beta)
        if step % 100 == 0:
            p = softmax(logits)
            print(f"  step {step:3d}  loss = {loss:.4f}  p(391) = {p[0]:.3f}  p(381) = {p[1]:.3f}")
        logits -= 1.0 * grad                                     # gradient descent on the loss
    assert abs(dpo_loss(START, START, 0, 1, beta)[0] - np.log(2)) < 1e-12
    print("  loss at step 0 is log 2 = 0.6931, because the policy equals the reference")
```

## Key takeaways

* Training stages: pretraining, SFT, then preference alignment (RLHF or DPO). Reasoning models add RL with verifiable rewards.
* Policy gradient: sample an answer, score it, and raise its probability in proportion to reward minus a baseline.
* RLHF with PPO needs a reward model and online sampling. It is strong but heavy to run.
* DPO is preference tuning from chosen and rejected pairs, no reward model. One offline pass on about 1,000 to 5,000 pairs. Try it first.
* GRPO and RLVR are reinforcement learning with rewards from automatic verification. The group mean is the baseline, so there is no value model.
* Choose by what signal you have: human comparisons, fixed pairs, or a verifier.
* Every reward gets gamed if it can be. Keep a held-out eval the reward never touches and read samples.

## Common mistakes

* Starting with RLHF when a set of preference pairs already exists. DPO is one training pass: run it and measure before you build a reward model.
* Using an LLM judge as the reward without checking it against people, then trusting the rising reward curve.
* Writing a verifier that checks format only. The model learns the format and skips the reasoning.
* Running GRPO on tasks the model always passes or always fails. Every group has identical rewards, so no gradient.
* Skipping SFT. RL on a model that cannot yet produce a usable answer has nothing to reward.
* Watching only the DPO loss. The loss measures a gap, not the quality of what the model generates.

## Practice

* Run the code example, then add a third verifier that gives 1.0 for "391" and 0.2 for any other three-digit number. Report p(correct) after 300 steps and explain the difference from the weak verifier in one sentence.
* In the code example, set the starting logits so that p(correct) is below 0.01. Count how many of the 300 steps had a group with mixed rewards, then repeat with a group size of 32. Report both counts.
* Write 20 preference pairs for a support bot in the prompt, chosen, rejected format, where the rejected answer breaks one clear policy. Have a classmate label the same 20 blind and report the agreement rate. Target: 18 of 20.
* Write a verifier for "return JSON with fields city and pincode". List three wrong outputs that your first version accepts, then tighten it until all three fail.

## Interview questions (8)

1.RLHF vs DPO vs GRPO?Hard

RLHF needs a reward model and online sampling: you train a model to score answers from human comparisons, then optimise the LLM against it with PPO. DPO needs only preference pairs and one training pass, with one loss and no reward model. GRPO needs a verifier that can check answers automatically, not human labels: it samples a group of answers per prompt and pushes the model toward the above-average ones. Choose by what signal you have. With pairs of better and worse answers I use DPO. With an automatic checker such as unit tests I use GRPO. I would reach for RLHF only when quality is a matter of human taste, the pairs cannot cover it, and there is budget for the loop.

2.Explain policy gradient in plain words. How is it different from supervised fine-tuning?Medium

Let the model generate an answer, score it, and then change the weights so that answers with an above-average score become more likely and the others less likely. The gradient is the gradient of the log-probability of the sampled answer, multiplied by reward minus a baseline. Supervised fine-tuning uses the same log-probability gradient, but on an answer I supplied and with weight one. So the difference is where the answer comes from and what the weight is. Policy gradient needs no reference answer, only a score. The price is noise, because the score of a few samples is a weak signal, which is why baselines, clipping and KL penalties exist.

3.Why does PPO clip the probability ratio?Medium

In RL the model creates its own training data. If one update moves the policy too far, the next batch of samples comes from a damaged policy, and the run can spiral down. PPO measures how much the probability of each sampled answer changed, as the ratio of new to old, and clips that ratio to a narrow range such as 0.8 to 1.2. Beyond the range, the objective gives no extra credit, so there is no reason to move further on this batch. In LLM training a KL penalty against the starting model is added for the same purpose: stay close to a model that is known to write sensible text.

4.Why is DPO usually tried before RLHF?Medium

Because it removes most of the machinery. RLHF needs a reward model, a value model, a frozen reference and sampling inside the training loop. DPO needs a dataset of prompt, chosen answer and rejected answer, plus a frozen copy of the model, and it trains in one offline pass like supervised fine-tuning. About 1,000 to 5,000 pairs is a usual size. The trade-off is that DPO never scores the model's own new answers, so it cannot fix a behaviour that the pairs do not cover. If the eval stalls and I can afford the loop, that is when online methods are worth the cost.

5.What is reward hacking, and how do you catch it?Hard

Reward hacking is when the model finds a way to score high without doing the task. A verifier that only checks that the output is a number rewards any number. Weak tests reward code that special-cases them. A learned reward model that likes long answers gets padding. I catch it in three ways. First, a held-out eval that the reward never touches, scored by a stricter check or by people. Second, reading samples at every checkpoint, especially the highest-reward ones. Third, watching for the pattern where reward climbs and the held-out score is flat or falling. The fix is in the reward: make the check stricter, add hidden tests, or cap the term being exploited.

6.Can you use an LLM judge as the reward signal?Hard

You can, but treat it as a reward model that nobody trained on human labels. In evaluation a judge sees each output once. In training the policy gets thousands of attempts to find what the judge likes, such as length, confident tone or certain phrases, and it will find them. So I prefer a programmatic check wherever the task allows one. If a judge is the only option, I calibrate it against human labels first, use a binary rubric, keep a second judge or a human sample that is never used for training, and stop the run when the two disagree. The DeepSeek-R1 paper chose rule-based rewards over neural reward models for exactly this reason.

7.What do you need before you can run GRPO, and what happens when every answer in a group gets the same reward?Hard

Three things: a model that already solves the task some of the time, prompts whose answers a program can check, and compute to sample a group of answers per prompt at every step. The advantage of each answer is its reward minus the group mean, divided by the group standard deviation. If all rewards in the group are equal, every advantage is zero and that prompt gives no gradient. So the task mix matters. Problems the model always solves or never solves waste compute. I track the share of groups with mixed rewards, and I move to harder problems as the pass rate rises.

8.Where does RL fit in the training stages of an LLM?Easy

There are three main stages. Pretraining on raw text with next-token prediction gives the model language and knowledge. Supervised fine-tuning on instructions teaches it to follow a request. Preference alignment, with RLHF or DPO, then moves it toward answers people prefer. Reasoning models add a further stage: reinforcement learning with verifiable rewards, where a program checks the final answer and the model is rewarded for getting it right. RL comes last because it needs a model that can already produce usable answers to score.

## Quiz

1.You have 3,000 prompts, each with one answer reviewers preferred and one they rejected. No reward model exists. What do you run first?

2.In a GRPO group of 4 answers the rewards are 1, 1, 1, 1. What does this prompt contribute to the update?

3.At the first step of DPO training with beta = 0.1, what is the loss for every pair?

4.During GRPO training the average reward rises from 0.4 to 0.95, but accuracy on a held-out set with a stricter checker stays at 40%. What is the most likely cause?

5.Which method removes the value model by using the average reward of several sampled answers as the baseline?

## Practice these problems

* [GENAIAI code assistant: completion, chat and agentHard](/ai/problems/code-assistant)
* [GENAILoRA fine-tuning pipeline with an adapter registryHard](/ai/problems/fine-tuning-pipeline)
* [GENAIEvaluation harness for LLM apps and agentsMedium](/ai/problems/llm-eval-harness)

## Further reading

* [Training language models to follow instructions with human feedbackPaperarxiv.org](https://arxiv.org/abs/2203.02155)
* [Direct Preference OptimizationPaperarxiv.org](https://arxiv.org/abs/2305.18290)
* [DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement LearningPaperarxiv.org](https://arxiv.org/abs/2501.12948)
* [Hugging Face TRL documentationGuidehuggingface.co](https://huggingface.co/docs/trl)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAttention variations - GQA, MLA](/ai/learn/attention-variations-gqa-mla)[NextComputer use and multimodal agents](/ai/learn/computer-use-multimodal-agents)

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

1. [Where RL fits in training an LLM](#where-rl-fits-in-training-an-llm)
2. [RL in five terms](#rl-in-five-terms)
3. [Policy gradient in plain words](#policy-gradient-in-plain-words)
4. [RLHF with PPO](#rlhf-with-ppo)
5. [DPO](#dpo)
6. [GRPO and RLVR](#grpo-and-rlvr)
7. [What each one needs](#what-each-one-needs)
8. [How they fail](#how-they-fail)
