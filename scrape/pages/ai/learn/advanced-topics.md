# Advanced topics — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/advanced-topics

[AI roadmap](/ai)

LaterLesson #22LaterAdvanced 1.5 h

# Advanced topics

This lesson is a map of what to study after the core roadmap. It covers ten topics that sit one level below the basics: reasoning models, mixture of experts, distillation, constrained decoding, speculative decoding, long-running agents, harness engineering, open-weight models, the small tuned model plus RAG pattern, and GraphRAG. For each one you get what it is, why a system builder cares, and what to learn first.

reasoning modelsmixture of expertsdistillationconstrained decodingspeculative decodingharness engineeringgraphrag

## Why it matters

Senior interviews go one question deeper than the definition. After "how do you get JSON out of a model?" comes "how does the server guarantee it?". After "what is an agent?" comes "what is in the code around the model?". These ten topics are where those second questions come from. They are also the levers you pull in real work: most of them trade cost, latency or reliability against quality. You do not need all ten at once. Use the table to pick the two or three that match the system you are building, and learn those properly.

Read first: [LLM fundamentals - tokens, embeddings, decoding](/ai/learn/llm-fundamentals), [Vector DBs and RAG](/ai/learn/vector-dbs-rag), [What is fine-tuning - LoRA, QLoRA, DoRA](/ai/learn/fine-tuning-lora-qlora-dora), [Inference and serving - KV cache, batching, vLLM](/ai/learn/inference-serving), [Agents in depth - patterns, reliability, security](/ai/learn/agents-in-depth), [What is new in 2026 + revision](/ai/learn/whats-new-2026-revision)

## Lesson

### The map

| Topic | One-line idea | Learn it when |
| --- | --- | --- |
| Reasoning models | The model thinks before answering; effort is a setting | Hard tasks fail, or thinking costs too much |
| Mixture of experts | Many expert networks, a few run per token | You size hardware for an open model |
| Distillation | A small student learns from a large teacher's outputs | A large model works but costs too much |
| Constrained decoding | Invalid tokens cannot be sampled | Code parses the model's output |
| Speculative decoding | A small model drafts, the large one verifies | You self-host and latency is the limit |
| Long-running agents | Agents that work for hours and keep state | Tasks outgrow one context window |
| Harness engineering | The code around the model: skills, hooks, sub-agents, compaction | Your agent works in demos but not in production |
| Open-weight models | Open models are close to closed ones | Cost, privacy or control matter |
| Small tuned model plus RAG | Tuning for behaviour, retrieval for facts | One narrow task has high volume |
| GraphRAG | Retrieve over a graph of entities and relations | Answers need facts joined across documents |

### Reasoning models and adaptive reasoning

Reasoning models think before answering: they write reasoning tokens first, then the answer. Training adds reinforcement learning with verifiable rewards. The focus has moved from raw ability to efficiency: effort adjusts to how hard the prompt is.

Reasoning tokens are generated like any other output tokens. You pay for them and you wait for them before the answer starts. So treat effort as a setting per task: low for extraction and routing, high for planning and debugging. A line to say aloud: "I set the thinking level per task, because reasoning tokens cost latency and money." These models need a clear goal more than a step-by-step script. Learn first: run one eval set at two effort levels and compare pass rate, latency and tokens.

### Mixture of experts (MoE)

The feed-forward layer is split into many expert networks, and a router sends each token to only a few of them. The model has many parameters but uses a small part per token, so quality rises without the same rise in compute. Many recent open-weight models use sparse MoE designs.

![A mixture-of-experts router sending one token to 2 of 8 expert networks](/ai/img/moe-router-top2-of-8.svg)A mixture-of-experts router sending one token to 2 of 8 expert networks

Formula

y=i∈top-k∑​gi​Ei​(x)

Here E\_i is expert i and g\_i is the weight the router gives it. For a builder the point is two different numbers. Speed follows the active parameters, the experts that run. Memory follows the total parameters, because every expert stays loaded. Training adds a load-balancing loss so the router does not send everything to the same few experts. Learn first: top-k routing, and total versus active parameters.

### Distillation

A large teacher model generates outputs and a small student model is trained to match them. This is how small models get close to large-model quality on a narrow task. The classic form matches the teacher's whole probability distribution, softened with a temperature. These soft targets carry more signal than one label: a teacher that gives 70% to one answer and 25% to another shows the student which wrong answer is nearly right. With an API teacher you only see text, so you fine-tune the student on the teacher's answers.

It is the standard move when a large model works but costs too much at volume. The risk: the student copies the teacher's mistakes, so filter the teacher's outputs and evaluate on human-checked examples. Learn first: generate 1,000 to 2,000 teacher answers for one task and fine-tune a small model on them.

### Constrained (structured) decoding

At each step the model gives a score to every token in the vocabulary. In constrained decoding, a grammar or JSON schema is compiled into a state machine that knows which tokens are legal next. Every other token is masked (its score is set to minus infinity) before sampling, so invalid tokens cannot be sampled.

This guarantees the form, not the content: the output parses and matches the schema, but a value can still be wrong. Output can also be cut off by the token limit. So validate in code, and retry with the error message if validation fails.

Two practical points. The mask is needed at every step over a vocabulary of tens of thousands of tokens or more, so engines compile the grammar once and reuse it. And the schema shapes quality: if a field for the reasoning comes after the answer field, the model must answer before it has thought, so put reasoning fields first. Learn first: the structured output option of your provider or serving engine. SGLang is known for fast constrained decoding.

### Speculative decoding

A small draft model proposes several tokens and the large model checks them in one pass. Accepted tokens are free speed, and the output distribution stays the same, because the large model verifies every drafted token and rejects the ones it would not have produced.

The rule that makes this exact: a drafted token x is accepted with probability min(1, p(x) / q(x)), where p is the large model's probability and q is the draft's. On the first rejection, the large model samples a replacement from a corrected distribution and the rest of the draft is dropped. The large model needs no retraining.

You only gain when the draft guesses right often, so it works best on predictable text such as code and boilerplate. The price is a second model in memory. Learn first: the acceptance rate and the expected-tokens formula in the worked example.

### Long-running and persistent agents

These are agents that work for hours and keep state. Reliability and security are the open problems. Errors compound over long tasks, so add checkpoints, limits and approvals. The state must live outside the context window: a progress file the agent re-reads, saved checkpoints, and a memory store. Then a run can stop, resume a day later, or survive a crash. More hours also means more untrusted content read, so the injection risk grows with run length. Learn first: checkpoint and resume, idempotent writes (a retry has no extra effect), and budgets for steps, tokens, time and money.

### Harness engineering

The harness is everything around the model: the loop, the tools, context management, permissions and checks. With the same model, a better harness often finishes more tasks. Four parts to know:

* **Skills:** packaged instructions, a folder with an instruction file and sometimes scripts, that the agent loads when a task needs them. Until then only a short description sits in the context.
* **Hooks:** your own checks that run before or after a tool call. A before-hook can block a call, such as a delete outside the project folder. An after-hook can run tests. The rule lives in code, not in the prompt.
* **Sub-agents:** a sub-agent explores in its own window and returns a short summary, so the lead agent's context stays clean. The cost is more total tokens, more latency if they run in sequence, and lost detail when results are summarised. They pay off when sub-tasks are independent and large.
* **Compaction:** when the window is nearly full, summarise the history and keep decisions, open items and key facts.

Learn first: write the agent loop yourself, then add one hook and compaction.

### Open-weight models closing the gap

Open models are close to closed ones on many benchmarks, often with sparse MoE designs and long context. Self-hosting is now a real option when cost, privacy or control matter. You take on the serving work in exchange: GPUs, autoscaling, upgrades and your own evals. Learn first: serve one open model and compare it with a hosted model on your eval set.

### Small fine-tuned model plus RAG

A QLoRA-tuned small open model with good retrieval is a common cost-for-quality choice. Fine-tuning teaches the behaviour (format, tone, tool-call style) and retrieval supplies the facts. The usual split: a large model for hard reasoning and a small tuned one for high-volume tasks, with a router between them. Learn first: the router and the eval that proves the small model is good enough.

### GraphRAG

Build a knowledge graph of entities and relations from the documents, then retrieve over the graph. It helps with questions that need facts joined across many documents, such as "which suppliers are shared by our three largest customers?". One published design also writes a summary in advance for each cluster of closely related entities, which answers corpus-wide questions such as "what are the main themes?". The cost is at indexing: a model must read every chunk to extract entities and relations, and again when documents change. Learn first: plain hybrid RAG. Add a graph only when your eval shows multi-document questions failing.

## Diagram

Rendering diagram…

## Worked example

**Is speculative decoding worth it?** A draft model proposes 4 tokens per round (call this g = 4). The large model accepts each drafted token with probability a, and stops at the first rejection. Every round also yields one token from the large model itself: the correction after a rejection, or a bonus token when all four are accepted. So the expected number of tokens per round is

Formula

E=1+a+a2+⋯+ag=1−a1−ag+1​

With a = 0.8: E = (1 - 0.8^5) / 0.2 = (1 - 0.328) / 0.2 = 3.36 tokens per round, against 1 token per pass without drafting.

The draft is not free. Assume one draft step costs 5% of a large-model pass. A round costs 4 x 0.05 + 1 = 1.2 large passes. Speed-up = 3.36 / 1.2 = 2.8 times.

| Assumed acceptance rate a | Tokens per round | Speed-up |
| --- | --- | --- |
| 0.8 (predictable text) | 3.36 | 2.8x |
| 0.5 | 1.94 | 1.6x |
| 0.3 (unpredictable text) | 1.43 | 1.2x |

The method pays off only when the draft is right most of the time. Measure the acceptance rate on your own traffic before you deploy it.

**MoE sizing.** Take a layer with width 4,096 and a feed-forward hidden size of 16,384. One expert has 2 x 4,096 x 16,384 = 134 million weights. Eight experts hold 1.07 billion weights in this layer, and all of them use GPU memory. With top-2 routing, a token passes through 268 million of them, which is 25% of the feed-forward compute. Size memory from the total and speed from the active part.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""Constrained decoding in miniature.

A tiny state machine tracks where we are inside a JSON object with the schema
{"city": string, "temp": number}. At every step it lists the tokens that keep
the output valid, masks every other token to minus infinity, and picks the
best token that is left. The model scores are scripted, so this runs anywhere.
"""
import json
import math

VOCAB = ["Sure", "!", "{", "}", '"city"', '"temp"', ":", ",", '"Pune"', '"hot"', "31", "<eos>"]
SCHEMA = {'"city"': "string", '"temp"': "number"}       # every key is required
STRINGS = {'"Pune"', '"hot"'}
NUMBERS = {"31"}

def allowed_tokens(state):
    """Return the set of tokens that keep the output inside the grammar."""
    phase, used, key = state["phase"], state["used"], state["key"]
    if phase == "start":
        return {"{"}
    if phase == "key":                                   # a key not used yet
        return set(SCHEMA) - used
    if phase == "colon":
        return {":"}
    if phase == "value":                                 # type comes from the schema
        return STRINGS if SCHEMA[key] == "string" else NUMBERS
    if phase == "after_value":                           # "}" only when all keys are present
        return {"}"} if used == set(SCHEMA) else {","}
    if phase == "end":
        return {"<eos>"}
    return set()

def advance(state, token):
    """Move the state machine forward by one emitted token."""
    phase = state["phase"]
    if phase == "start":
        state["phase"] = "key"
    elif phase == "key":
        state["key"] = token
        state["used"] = state["used"] | {token}
        state["phase"] = "colon"
    elif phase == "colon":
        state["phase"] = "value"
    elif phase == "value":
        state["phase"] = "after_value"
    elif phase == "after_value":
        state["phase"] = "end" if token == "}" else "key"
    elif phase == "end":
        state["phase"] = "done"

# Scripted "model" scores (logits) for each step. The top choice is often a
# token that would break the JSON, which is what real models sometimes do.
# A real model would react to its earlier tokens; this script does not.
SCRIPT = [
    {"Sure": 3.1, "{": 2.4, '"city"': 0.3},              # wants to chat first
    {'"temp"': 1.9, '"city"': 1.7, "}": 2.2},            # wants to close early
    {":": 4.0, ",": 0.5},
    {"31": 2.0, '"hot"': 1.5, "}": 0.2},                 # schema says number here
    {"}": 2.6, ",": 1.1, "!": 0.4},                      # "city" is still missing
    {'"temp"': 2.8, '"city"': 1.0},                      # would repeat a key
    {":": 3.5},
    {"31": 2.2, '"Pune"': 2.1, '"hot"': 0.9},            # schema says string here
    {",": 1.8, "}": 1.6, "!": 1.0},
    {"!": 2.0, "<eos>": 1.9},
]

def decode(constrained):
    state = {"phase": "start", "used": set(), "key": None}
    out = []
    for step, scores in enumerate(SCRIPT, start=1):
        logits = {tok: scores.get(tok, -5.0) for tok in VOCAB}     # unlisted tokens score low
        free_pick = max(logits, key=logits.get)
        if not constrained:
            out.append(free_pick)
            continue
        allowed = allowed_tokens(state)
        masked = {tok: (s if tok in allowed else -math.inf) for tok, s in logits.items()}
        pick = max(masked, key=masked.get)
        note = "" if pick == free_pick else f"   (model wanted {free_pick})"
        print(f"step {step:>2}  allowed = {sorted(allowed)}  ->  pick {pick}{note}")
        out.append(pick)
        advance(state, pick)
        if state["phase"] == "done":
            break
    return out

if __name__ == "__main__":
    free = decode(constrained=False)
    print("unconstrained:", " ".join(free))
    try:
        json.loads("".join(t for t in free if t != "<eos>"))
    except json.JSONDecodeError as e:
        print("  json.loads fails:", e.msg, "\n")

    tokens = decode(constrained=True)
    text = "".join(t for t in tokens if t != "<eos>")
    parsed = json.loads(text)
    print("\nconstrained  :", text)
    assert parsed == {"temp": 31, "city": "Pune"}
    assert set(parsed) == {"city", "temp"} and isinstance(parsed["temp"], int)
    print("parses, has both keys, types match the schema")
```

## Key takeaways

* Reasoning effort is a setting per task: reasoning tokens cost latency and money, so spend them only on hard steps.
* MoE splits the feed-forward layer into experts and runs a few per token. Compute follows active parameters; memory follows total parameters.
* Distillation trains a small student on a large teacher's outputs to cut cost on a narrow task.
* Constrained decoding masks every token that would break the grammar, so the output always parses. It does not make the values correct.
* Speculative decoding keeps the large model's output distribution and gains speed only when the draft is accepted often.
* Long-running agents need checkpoints, limits and approvals because errors compound.
* The harness (skills, hooks, sub-agents, compaction) decides how reliable an agent is as much as the model does.
* A small fine-tuned model plus RAG, behind a router, is a common cost-for-quality design; GraphRAG is for questions that join facts across documents.

## Common mistakes

* Running every request at maximum reasoning effort, then being surprised by latency and cost.
* Sizing GPU memory for an MoE model from its active parameters. All experts must be loaded.
* Treating schema-valid JSON as correct JSON and skipping validation of the values.
* Turning on speculative decoding without measuring the acceptance rate on real traffic.
* Putting a hard safety rule only in the system prompt when a hook in code could enforce it.
* Building GraphRAG before plain hybrid retrieval has been measured and shown to fail.

## Practice

* Extend the code example: add a third required key `"unit"` whose value must be `"C"` or `"F"`, and confirm the output still parses.
* Compute the speculative decoding speed-up for a = 0.6 and 0.9 with g = 4 and a 5% draft cost (expected: about 1.9x and 3.4x).
* Run 30 eval tasks on a reasoning model at low and high effort. Report pass rate, median latency and output tokens for each.
* Add one before-hook to an agent loop that blocks a named tool call, and a test that proves the block works.

## Interview questions (10)

1.What is a Mixture of Experts (MoE) model?Easy

The feed-forward layer is split into many expert networks and a router sends each token to only a few of them. The model has many parameters but uses a small part per token, so quality rises without the same rise in compute. Many recent open-weight models use sparse MoE designs. One detail matters for serving: all experts must stay in memory, so I size the GPU from total parameters and estimate speed from the active ones. Training also needs a load-balancing loss so the router spreads tokens across experts.

2.How do you get reliable JSON from an LLM?Medium

Use the provider's structured output or constrained decoding with a JSON schema, so invalid tokens cannot be sampled. Under the hood the schema becomes a state machine; at each step it masks every token that would break the grammar, and the model samples only from what is left. Then validate the result in code and retry with the error message if validation fails, because the schema guarantees the form, not the values, and output can still be cut off by the token limit. Never rely on "please return JSON" alone.

3.How does speculative decoding keep quality the same?Hard

The large model verifies every drafted token and rejects the ones it would not have produced. The draft model proposes a few tokens, and the large model scores all of them in one parallel pass. Each drafted token is accepted with probability min(1, p / q), where p is the large model's probability for it and q is the draft's. At the first rejection the large model samples a replacement from a corrected distribution and the rest of the draft is dropped, which makes the output distribution exactly the large model's. You only gain speed when the draft model guesses right often, so it works best on predictable text. With an 80% acceptance rate and 4 drafted tokens, you get about 3.4 tokens per large-model pass.

4.What do sub-agents cost you?Medium

More total tokens, more latency if they run in sequence, and lost detail when results are summarised. They pay off when sub-tasks are independent and large enough to pollute the lead agent's context. A sub-agent explores in its own window and returns a short summary, so the lead agent stays clean. I use them for broad search or research, and avoid them when steps are tightly coupled, because then the lead agent needs the detail that the summary drops.

5.When do you turn reasoning effort up, and when down?Medium

Reasoning models think before answering, and those reasoning tokens are billed as output and delay the visible answer. So I set the thinking level per task. Low or off for extraction, classification, routing and simple lookups. High for planning, debugging, multi-step maths and decisions that are costly to get wrong. I check the choice with an eval: run the same set at two effort levels and compare pass rate, latency and tokens. If the pass rate does not move, the extra thinking is wasted money. I also give these models a clear goal, not a step-by-step script.

6.What is distillation, and how is it different from ordinary fine-tuning?Medium

Distillation is fine-tuning where the labels come from a larger model. A large teacher generates outputs and a small student is trained to match them. In the classic form the student matches the teacher's full probability distribution, softened with a temperature, which carries more signal than one correct label. With an API teacher you only get text, so you train on its answers. It is how small models get close to large-model quality on a narrow task. The risks are copying the teacher's errors and drifting from real inputs, so I filter the teacher's outputs and evaluate on human-checked examples.

7.What is harness engineering? Give an example of a hook.Medium

The harness is all the code around the model: the loop, tool execution, context management, permissions and checks. Harness engineering is improving that code, and it often raises the task pass rate more than a model change. A hook is my own check that runs before or after a tool call. For example, a before-hook inspects every shell command and blocks a delete outside the project folder, and an after-hook runs the tests after each file edit and feeds failures back. The rule is enforced in code, so a confused or injected model cannot talk its way past it.

8.How do you manage context for an agent that runs for hours?Hard

Compact the history when the window fills, clear old tool results, keep notes in an external file, and push exploration into sub-agents that return summaries. I also keep the start of the context stable so the prompt cache keeps working. For the run itself I checkpoint state after each step so a crash resumes instead of restarting, make write actions idempotent, and set budgets for steps, tokens, time and money. Errors compound over long tasks, so I add approvals before anything irreversible.

9.Open-weight model or hosted API: how do you decide?Medium

Open models are now close to closed ones on many benchmarks, so self-hosting is a real option when cost, privacy or control matter. I would self-host when data cannot leave our environment, when volume is high and steady enough to keep GPUs busy, or when I need a fine-tuned adapter or fixed model version. I would stay on a hosted API when traffic is low or spiky, when the hardest reasoning is needed, or when the team cannot run GPUs. Either way I decide on my own eval set, not on public benchmarks.

10.When is GraphRAG worth building?Medium

GraphRAG builds a knowledge graph of entities and relations from the documents and retrieves over the graph. It helps with questions that need facts joined across many documents, where no single chunk holds the answer. The cost is indexing: a model reads every chunk to extract entities and relations, and updates repeat that work. So I start with hybrid retrieval and a reranker, build an eval set that includes multi-document questions, and add a graph only if those questions keep failing.

## Quiz

1.An MoE model has 8 experts per layer and routes each token to 2. What is true?

2.What does constrained decoding guarantee?

3.Speculative decoding gives a small speed-up on your traffic. What is the most likely cause?

4.A coding agent must never delete files outside the project folder. Where should this rule live?

5.A support bot handles 2 million similar tickets a month with a large model and the cost is too high. What is the usual first design to test?

## Practice these problems

* [GENAIAgent runtime: loop, tools, checkpoints and budgetsHard](/ai/problems/agent-runtime-harness)
* [GENAIMulti-agent orchestrator for deep researchHard](/ai/problems/multi-agent-orchestrator)
* [GENAICut LLM cost by half: model routing and cascadesMedium](/ai/problems/llm-cost-router)
* [MLCODEDecoder with a KV cacheHard](/ai/problems/kv-cache-decoding)

## Further reading

* [Switch Transformers (mixture of experts)Paperarxiv.org](https://arxiv.org/abs/2101.03961)
* [Fast Inference from Transformers via Speculative DecodingPaperarxiv.org](https://arxiv.org/abs/2211.17192)
* [From Local to Global: A Graph RAG Approach to Query-Focused SummarizationPaperarxiv.org](https://arxiv.org/abs/2404.16130)
* [Effective context engineering for AI agentsArticleanthropic.com](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousComputer use and multimodal agents](/ai/learn/computer-use-multimodal-agents)[NextProjects - RAG app, fine-tuned model, agent + evals](/ai/learn/projects)

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

1. [The map](#the-map)
2. [Reasoning models and adaptive reasoning](#reasoning-models-and-adaptive-reasoning)
3. [Mixture of experts (MoE)](#mixture-of-experts-moe)
4. [Distillation](#distillation)
5. [Constrained (structured) decoding](#constrained-structured-decoding)
6. [Speculative decoding](#speculative-decoding)
7. [Long-running and persistent agents](#long-running-and-persistent-agents)
8. [Harness engineering](#harness-engineering)
9. [Open-weight models closing the gap](#open-weight-models-closing-the-gap)
10. [Small fine-tuned model plus RAG](#small-fine-tuned-model-plus-rag)
11. [GraphRAG](#graphrag)
