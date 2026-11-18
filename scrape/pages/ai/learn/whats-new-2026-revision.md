# What is new in 2026 + revision — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/whats-new-2026-revision

[AI roadmap](/ai)

ShipLesson #18StudyIntermediate 2.5 h

# What is new in 2026 + revision

This is the last stop before the interview. It lists the eleven 2026 trends an interviewer may probe, each with what it is, why it matters to someone who builds systems, and a line you can say. It then gives the 37-term revision sheet for the rapid-fire round, and a structure for answering "what have you been following lately?" in two minutes.

2026 trendsrevisionreasoning modelsmcprlvrservinginterview strategy

## Why it matters

Interviewers use "what have you been following lately?" to check that you are current. A list of product names is a weak answer. A strong one names a few trends, gives one concrete fact for each, and ties one to work you did. The rapid-fire round is the other place where preparation shows: thirty-seven terms, one line each, with no time to think. Both are easy marks if you have said the answers aloud, and both go badly if you have only read them.

Read first: [LLM fundamentals - tokens, embeddings, decoding](/ai/learn/llm-fundamentals), [Vector DBs and RAG](/ai/learn/vector-dbs-rag), [What is fine-tuning - LoRA, QLoRA, DoRA](/ai/learn/fine-tuning-lora-qlora-dora), [Inference and serving - KV cache, batching, vLLM](/ai/learn/inference-serving), [Agents in depth - patterns, reliability, security](/ai/learn/agents-in-depth), [Evals, tracing and guardrails](/ai/learn/evals-tracing-guardrails), [LLM system design](/ai/learn/llm-system-design)

## Lesson

### Three rules that make the difference in interviews

1. **Say answers aloud.** Reading feels like knowing. Speaking shows the gaps.
2. **Always give the trade-off.** "It depends on X; if A then this, if B then that" beats a one-word answer.
3. **Tie every topic to one project.** "I used QLoRA on a 7B model and saw..." beats any definition.

Short on time: do LLM fundamentals, RAG, fine-tuning, and inference and serving first (sections 2, 4, 5 and 6 of the guide; lessons 4, 8, 9 and 11 here). Those four produce most of the LLM questions in interviews.

### How to answer "what have you been following lately?"

Know each trend in the next table well enough to explain it in two sentences. Then pick three, not eleven, and give each one four beats:

1. **Name it** in a few words.
2. **Give one concrete fact:** a date, a product, a mechanism.
3. **Say why it matters** to someone who builds systems.
4. **Tie it to your work:** what you built, measured, or would build next.

Choose trends near the role: serving for an infrastructure team, MCP and agents for a product team. Include one you have touched with your own hands. Two minutes is the budget, which is about 260 words at 130 words a minute. If you have only read about something, say so. "I have read about it and not run it yet" is a fine sentence. Invented experience falls apart at the first follow-up.

### The eleven trends

| Trend | What it is | Why it matters when you build | A line you can say |
| --- | --- | --- | --- |
| Reasoning models and adaptive reasoning | Models that think before answering. The focus has moved from raw ability to efficiency: effort adjusts to how hard the prompt is | Thinking tokens add latency and cost, so effort is a dial you set per task | "I set the thinking level per task, because reasoning tokens cost latency and money." |
| RLVR and GRPO | Reinforcement learning where the reward comes from an automatic correctness check, not a human-trained reward model. DeepSeek-R1 made it mainstream | A task with a checker (tests, a maths answer, valid JSON) can be trained on with no human labels | "If I have a verifier, such as unit tests, I can train reasoning without human labels." |
| Context engineering | Managing everything in the context window, not only the prompt wording | Tool results and history grow every turn, so what you select and drop decides quality and cost | "In agents, many failures come from what is in the context, not from the model." |
| MCP and A2A | Open protocols for agent-to-tool and agent-to-agent connections. Major frameworks ship MCP support | A tool written once is reusable across models and frameworks | "I build tools as MCP servers so they work across models and frameworks." |
| Long-running and persistent agents | Agents that work for hours and keep state. Reliability and security are the open problems | A mistake in an early step feeds every later step, so recovery has to be designed in | "Errors compound over long tasks, so I add checkpoints, limits and approvals." |
| Coding agents | Agents that read a whole repository, edit files, run tests and fix failures | Review and tests become the limit on speed, and the agent needs a sandbox | "I review and test agent output the way I would a junior engineer's pull request." |
| Open-weight models catching up | Open models are close to closed ones on many benchmarks, often with sparse MoE designs and long context | Hosted API or self-hosted is now a cost, privacy and control decision | "Self-hosting is now a real option when cost, privacy or control matter." |
| Small fine-tuned model plus RAG | A QLoRA-tuned small open model with good retrieval is a common cost-for-quality choice | Narrow, high-volume tasks do not need a large model on every call | "I would use a large model for hard reasoning and a small tuned one for high-volume tasks." |
| Serving stack shift | TGI is in maintenance mode; vLLM and SGLang are the active choices. Prefix caching matters more as agents reuse long contexts | The engine for new work changed, and agent traffic rewards prefix reuse | "For agent traffic I would benchmark SGLang against vLLM because of prefix reuse." |
| Framework consolidation | Microsoft merged AutoGen and Semantic Kernel into the Microsoft Agent Framework | Code tied to one framework's API ages fast; the patterns carry over | "Frameworks change fast, so I learn the patterns underneath them." |
| Native multimodal models | One model handles text, images and often audio and video in the same context | Fewer pipeline stages between a document and the model | "I can pass a diagram or screenshot directly instead of building an OCR pipeline." |

Four dated details from the guide sit behind these rows. Keep them exact:

* TGI has been in maintenance mode since December 2025, and Hugging Face recommends vLLM or SGLang for new work.
* The Microsoft merge happened in April 2026. AutoGen itself is now effectively in maintenance mode, so say "Microsoft Agent Framework" if asked about it.
* The latest MCP revision is 2026-07-28. The protocol became stateless: the initialize handshake and sessions were removed, each request carries its version, and state is passed through explicit handles. Tutorials written before this may be out of date.
* QLoRA is treated as the default in most open-source fine-tuning stacks in 2026, with plain LoRA chosen when memory is not the constraint.

This field moves monthly. Before an interview, spend 30 minutes on the latest model releases and on the company's own engineering blog. The facts above were checked on 12 October 2026; anything newer is yours to check.

### How to use the revision sheet

If you can say each line below without looking, you are ready for the rapid-fire round.

1. **Cover the answer column and say each line aloud.** Thinking it does not count.
2. **Then go one level deeper.** The third column is the follow-up an interviewer asks next. Answer it in two sentences.
3. **Mark every miss,** re-read that lesson, and drill only the misses the next day.
4. **For the terms nearest your project,** add the trade-off (rule 2) and one sentence from your own work (rule 3).

![Five stacked layers, Foundations, Build, Serve, Agents and Ship, each listing its revision terms and its 2026 trends](/ai/img/stack-map-revision-terms.svg)Five stacked layers, Foundations, Build, Serve, Agents and Ship, each listing its revision terms and its 2026 trends

### The revision sheet: 37 terms

**Foundations**

| Term | One-line answer | One level deeper |
| --- | --- | --- |
| Token | The unit of text a model reads; about 0.75 English words | How does BPE build its vocabulary? |
| Embedding | A vector that represents meaning; close vectors mean similar text | How is closeness measured? |
| Self-attention | Each token weighs every other token to build its representation | Why divide by the square root of d\_k? |
| Causal mask | Stops a token from attending to future tokens during generation | Which architecture has no causal mask? |
| RoPE | Position encoded by rotating query and key vectors | Why does attention need position at all? |
| Temperature | Controls how random sampling is | Why can output differ even at temperature 0? |
| Top-p | Sample from the smallest token set whose probability adds up to p | How is top-k different? |
| Context window | Maximum tokens per call, input plus output | Why does quality drop as it fills? |
| Hallucination | Fluent output that is not supported by facts or context | Name three fixes |
| MoE | Many expert sub-networks; a router activates a few per token | Why does that save compute? |

**Build: RAG**

| Term | One-line answer | One level deeper |
| --- | --- | --- |
| RAG | Retrieve relevant text, add it to the prompt, then generate | RAG or fine-tuning? |
| Hybrid search | Dense embeddings plus keyword search, fused | What does BM25 catch that embeddings blur? |
| Reranker | Cross-encoder that reorders retrieved chunks by relevance | Why not run it over the whole corpus? |
| HNSW | Layered graph index for fast approximate nearest neighbour search | What is the trade-off? |
| Faithfulness | Share of answer claims supported by the retrieved context | How do you measure it? |

**Build: fine-tuning**

| Term | One-line answer | One level deeper |
| --- | --- | --- |
| PEFT | Methods that train a small share of parameters | Why not full fine-tuning? |
| LoRA | Frozen base plus trainable low-rank matrices B and A | Why does a low rank work? |
| Rank r | Size of the low-rank update; the capacity knob | When do you raise it? |
| QLoRA | LoRA on a base loaded in 4-bit | Which three things does it add? |
| DoRA | LoRA applied to weight direction, with magnitude trained separately | Which gap does it close? |
| DPO | Preference tuning from chosen and rejected pairs, no reward model | How does RLHF differ? |
| GRPO and RLVR | Reinforcement learning with rewards from automatic verification | What can act as a verifier? |
| Distillation | A small student model learns from a large teacher's outputs | When is it worth doing? |
| Catastrophic forgetting | Losing old abilities while learning a new task | How do you reduce it? |

**Serve**

| Term | One-line answer | One level deeper |
| --- | --- | --- |
| KV cache | Stored keys and values of past tokens, so they are not recomputed | What makes its memory grow? |
| TTFT | Time to first token; set by queue wait and prefill | What sets tokens per second? |
| Continuous batching | Requests join and leave the batch at every decode step | What is wrong with static batching? |
| PagedAttention | KV cache kept in fixed-size blocks to cut fragmentation | Why does that allow bigger batches? |
| Quantization | Fewer bits per weight: less memory, small quality loss | What does 4-bit hurt first? |
| Speculative decoding | A small model drafts tokens, the large model verifies them | Why is the output distribution unchanged? |

**Agents**

| Term | One-line answer | One level deeper |
| --- | --- | --- |
| Agent | An LLM in a loop with tools and a goal | Workflow or agent? |
| Tool calling | The model outputs a structured call; your code executes it | Who validates the arguments? |
| MCP | Open standard to expose tools and data to any model client | MCP vs plain function calling? |
| A2A | Protocol for agents to talk to other agents | How is it different from MCP? |

**Ship**

| Term | One-line answer | One level deeper |
| --- | --- | --- |
| Prompt injection | Untrusted text that overrides the application's instructions | Direct or indirect? |
| LLM-as-judge | A model scoring outputs against a rubric | Which biases does it have? |
| Guardrails | Checks on inputs and outputs around the model | Which checks go on outputs? |

### Prepare your own answer to these five

No sheet can answer these for you. They are rule 3 turned into questions.

* Walk me through an LLM project you built: problem, design, trade-offs, numbers.
* What went wrong, and how did you debug it?
* How did you evaluate it?
* How would you scale it to ten times the traffic?
* What would you do differently now?

Write each answer once, then say it in under two minutes. Each needs at least one number you measured: a latency, a cost, a pass rate, a Recall@k.

### What this roadmap does not cover

These lessons cover LLM, GenAI and agent concepts. At the best-paying companies the AI engineer interview is a software or ML engineering loop with these topics added, so the rounds below need their own preparation.

| Round | What to prepare |
| --- | --- |
| Coding | Data structures and algorithms, plus project-style tasks such as a retry mechanism with backoff or a key-value store with transactions |
| ML coding from scratch | Self-attention, a BPE tokenizer, top-p sampling, a LoRA layer, a minimal RAG loop |
| ML and deep learning basics | Bias and variance, regularisation, optimisers, backpropagation, loss functions, classification metrics |
| General system design | Queues, caches, databases, load balancing, backpressure |
| Your own projects in depth | Numbers for latency, cost and quality |
| Behavioural round | Stories with a measured result, including one where you were wrong |
| Engineering around the model | Python async, Docker, Kubernetes, CI/CD, cloud GPUs |
| The company itself | Its product, its stack and its engineering blog |

The problem set on this site has the ML coding tasks and retry with backoff as runnable problems, lesson 2 covers the deep learning basics, and lesson 23 covers the projects. The rest is outside this course.

No list removes every surprise question. What interviewers reward when you do not know something is clear reasoning from what you do know.

## Diagram

Rendering diagram…

## Worked example

**The question:** "What have you been following lately?" A model answer, written to be spoken:

"Three things, mostly on the serving and agent side, because that is what I build.

First, the serving stack has shifted. TGI has been in maintenance mode since December 2025, and vLLM and SGLang are the active choices for new work. The reason I care is that agents resend a long, mostly identical context on every step, so prefix caching now decides a lot of the cost. For agent traffic I would benchmark SGLang against vLLM on my own prompts.

Second, MCP. The latest revision, dated 2026-07-28, made the protocol stateless: the initialize handshake and sessions are gone, and each request carries its version. So tutorials written before that date may be out of date. I build tools as MCP servers so they work across models and frameworks.

Third, RLVR and GRPO: reinforcement learning where the reward comes from an automatic check, not a human-trained reward model. DeepSeek-R1 made it mainstream. The practical point is that if I have a verifier, such as unit tests, I can train reasoning without human labels. I have read about this one and not run it yet.

To make it concrete: I built an eval harness for a support agent, 30 tasks with three runs each, and reported pass rate and cost per task. Next I would put our order API behind an MCP server and measure how much prefix caching saves on the agent's traffic. Which of these is closest to what your team works on?"

**Why it works.** The answer is 243 words. At 130 words a minute that is 243 / 130 = 1.87 minutes, about 1 minute 52 seconds, inside the two-minute budget.

| Beat | Serving shift | MCP | RLVR |
| --- | --- | --- | --- |
| One concrete fact | TGI in maintenance mode since December 2025 | Revision 2026-07-28 is stateless | DeepSeek-R1 made it mainstream |
| Why it matters | Prefix caching sets agent cost | Old tutorials may be wrong | No human labels if a verifier exists |
| Tie to work | Would benchmark both engines | Builds tools as MCP servers | Honest: read, not run |

Every fact comes from the trends table. The project at the end is an example: replace it with your own, and never claim work you did not do.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""Flashcard drill over ten revision-sheet terms.

Round 1 shows the term and expects the one-line answer. Round 2 reverses the
cards you missed: it shows the answer and expects the term, which is how a
rapid-fire round often goes. The shuffle uses a fixed seed, so the order is
the same on every run. Change the seed for a new order.
"""
import random

CARDS = {
    "KV cache": "Stored keys and values of past tokens, so they are not recomputed",
    "TTFT": "Time to first token; set by queue wait and prefill",
    "Continuous batching": "Requests join and leave the batch at every decode step",
    "LoRA": "Frozen base plus trainable low-rank matrices B and A",
    "QLoRA": "LoRA on a base loaded in 4-bit",
    "Hybrid search": "Dense embeddings plus keyword search, fused",
    "Reranker": "Cross-encoder that reorders retrieved chunks by relevance",
    "MCP": "Open standard to expose tools and data to any model client",
    "A2A": "Protocol for agents to talk to other agents",
    "Prompt injection": "Untrusted text that overrides the application's instructions",
}

def shuffled(terms, seed):
    order = list(terms)
    random.Random(seed).shuffle(order)
    return order

def drill(cards, order, reverse=False):
    for i, term in enumerate(order, start=1):
        question, answer = (cards[term], term) if reverse else (term, cards[term])
        print(f"{i:>2}. Q: {question}")
        print(f"    A: {answer}")

if __name__ == "__main__":
    order = shuffled(CARDS, seed=2026)
    print("Round 1: say the one-line answer aloud before you read it")
    drill(CARDS, order)

    missed = ["A2A", "TTFT", "Reranker"]          # in a real drill, you mark these yourself
    print("\nRound 2: missed cards only, reversed (name the term)")
    drill(CARDS, shuffled(missed, seed=7), reverse=True)

    assert sorted(order) == sorted(CARDS)                      # every card asked exactly once
    assert shuffled(CARDS, seed=2026) == order                 # same seed, same order
    print(f"\n{len(order)} cards drilled, {len(missed)} repeated, order is reproducible")
```

## Key takeaways

* Three rules: say answers aloud, always give the trade-off, tie every topic to one project.
* For "what have you been following lately?", pick three trends and give each a name, one concrete fact, why it matters, and a tie to your work. Two minutes, about 260 words.
* Dated facts to keep exact: TGI in maintenance mode since December 2025; AutoGen and Semantic Kernel merged into the Microsoft Agent Framework in April 2026; MCP revision 2026-07-28 is stateless.
* MCP connects an agent to tools; A2A connects agents to each other.
* RLVR needs a verifier, not human labels. No verifier, no RLVR.
* The revision sheet has 37 one-line answers. Say each aloud, then answer the follow-up one level deeper.
* Short on time: fundamentals, RAG, fine-tuning and serving first. Those four produce most of the LLM questions.
* The field moves monthly: spend 30 minutes on the latest model releases and the company's engineering blog before the interview.

## Common mistakes

* Listing ten product names with no fact, no consequence and no link to anything you built.
* Quoting a "latest" version or date from memory. If you are not sure, state the idea without the date.
* Reading the revision sheet silently and counting that as revision.
* Stopping at the one-line answer, then freezing on "why?" or "what does it cost?".
* Calling AutoGen the current Microsoft framework, or recommending TGI for a new deployment.
* Claiming hands-on experience with a trend you have only read about.

## Practice

* Record a two-minute answer to "what have you been following lately?" with three trends, one fact each and one project. Play it back and check it is 220 to 280 words and under 2 minutes 15 seconds.
* Drill all 37 terms aloud with the answer column covered. Write down the number missed. Repeat daily until you miss none in under 7 minutes.
* For the ten terms nearest your project, write the "one level deeper" answer and a trade-off in two sentences each.
* Write and time your answers to the five own-project questions. Each must be under two minutes and contain at least one number you measured.

## Interview questions (13)

1.What have you been following lately?Medium

I pick three things close to the role and give one fact and one consequence for each. For example: the serving stack shifted, with TGI in maintenance mode and vLLM and SGLang the active choices, so for agent traffic I would benchmark both because of prefix reuse. MCP's latest revision made the protocol stateless, so older tutorials may be out of date. And RLVR lets you train reasoning from an automatic verifier with no human labels. Then I tie one of them to something I built, and I say plainly which ones I have only read about.

2.What is adaptive reasoning and when would you lower the thinking effort?Medium

Reasoning models think before answering, and that thinking uses extra tokens. Adaptive reasoning means the effort adjusts to how hard the prompt is: the focus has moved from raw ability to efficiency. I set the thinking level per task, because reasoning tokens cost latency and money. I lower it for extraction, classification, routing and simple lookups, where no multi-step work is needed, and raise it for planning, debugging and maths. A reasoning model needs a clear goal more than a step-by-step script. I confirm the setting on an eval set by comparing pass rate, latency and cost at each level.

3.What is RLVR?Medium

Reinforcement learning with verifiable rewards. The reward comes from an automatic correctness check, such as unit tests passing, a maths answer matching or JSON being valid, and not from a reward model trained on human preferences. DeepSeek-R1 made it mainstream. GRPO is the algorithm usually named with it: generate a group of answers per prompt, score each with the verifier, and push the model toward the above-average ones. The condition is the verifier. If I have one, I can train reasoning without human labels. If quality is a matter of preference, I need preference pairs and DPO.

4.What changed in the serving stack?Medium

TGI has been in maintenance mode since December 2025, and Hugging Face recommends vLLM or SGLang for new work. vLLM is the safe default: PagedAttention plus continuous batching, an OpenAI-compatible API and broad hardware support. SGLang's RadixAttention reuses shared prefixes automatically, and it is fast at constrained decoding. Prefix caching matters more now because agents reuse long contexts on every step. So for agent or multi-turn traffic I would benchmark SGLang against vLLM on my real prompts, and keep TGI only where it already runs.

5.MCP and A2A: what does each connect?Easy

MCP, the Model Context Protocol, connects an agent to tools and data. A server exposes tools, resources and prompts, and any compatible client can use them, so you build a tool once and reuse it across models and frameworks. A2A, Agent2Agent, is a protocol for agents to discover and talk to other agents. In one line: MCP is agent-to-tool, A2A is agent-to-agent. Major frameworks ship MCP support, and MCP is maintained under the Linux Foundation's Agentic AI Foundation, not by one vendor.

6.What changed in the latest MCP revision, and why should you care?Hard

The latest revision is dated 2026-07-28, and it made the protocol stateless. The initialize handshake and sessions were removed, each request carries its version, and state is passed through explicit handles. Two practical effects: a request no longer depends on an earlier handshake with the same server, and tutorials written before this revision may be out of date. The transports to name are stdio for local servers and Streamable HTTP for remote ones; the older HTTP plus SSE transport is deprecated. I would re-read the current specification before an interview, because this moves fast.

7.What is context engineering, and why does it matter more for agents?Medium

Prompt engineering tunes the wording of one instruction. Context engineering manages everything that enters the context window: instructions, examples, retrieved data, tool definitions and history. It matters for agents because tool results and history grow every turn, and many failures come from what is in the context, not from the model. The four moves are select, compress, isolate and persist: bring in only what is relevant, summarise old turns, give sub-tasks their own context, and write notes or memory outside the window. I also keep the start of the context stable so the prompt cache keeps working.

8.Why are long-running agents hard, and what do you add to make them safe?Hard

Agents that work for hours and keep state have two open problems: reliability and security. Errors compound over long tasks, because a mistake in an early step becomes the input to every later one, and the context fills up. So I add checkpoints after each step so a crashed run resumes, budgets for steps, tokens, time and money, idempotent write tools, and approval before actions that cannot be undone. For context I compact the history, clear old tool results and keep notes outside the window. For security I remove at least one of three things: access to private data, exposure to untrusted content, and a way to send data out.

9.Open-weight models are catching up. When would you self-host?Medium

Open models are close to closed ones on many benchmarks, often with sparse MoE designs and long context, so self-hosting is now a real option when cost, privacy or control matter. I would self-host for high and steady volume, for data that must stay inside our environment, or when I need my own fine-tuned adapters or a pinned model version. I would stay on a hosted API when volume is low or spiky, or when I need the strongest reasoning available. Self-hosting brings its own work: capacity maths, an engine such as vLLM, autoscaling on queue depth, and my own evals.

10.Why is a small fine-tuned model plus RAG a common choice?Medium

Because it splits two jobs. Fine-tuning changes behaviour: format, tone, domain vocabulary. RAG supplies knowledge that is fresh or private. A QLoRA-tuned small open model with good retrieval is a common cost-for-quality choice, and QLoRA is treated as the default in most open-source fine-tuning stacks in 2026. I would use a large model for hard reasoning and a small tuned one for high-volume tasks such as routing, classification and extraction. I would fine-tune only with a stable task, a real eval and roughly 500 or more good examples.

11.Microsoft merged AutoGen and Semantic Kernel. What does that tell you about choosing a framework?Easy

Microsoft merged AutoGen and Semantic Kernel into one SDK, the Microsoft Agent Framework, in April 2026. AutoGen itself is now effectively in maintenance mode, so if asked about it I say Microsoft Agent Framework. The lesson is that frameworks change fast, so I learn the patterns underneath them: the agent loop, tool schemas, state and checkpoints, human approval and tracing. Those carry over. I pick a framework for what it gives me today, such as persistence or tracing, and keep tools and prompts in plain code so that moving is cheap.

12.How would you use a coding agent safely on a real repository?Medium

A coding agent reads a whole repository, edits files, runs tests and fixes failures. I review and test its output the way I would a junior engineer's pull request: small scoped tasks, a diff I read, and tests that must pass. Generated code runs in a sandbox with restricted network access, and the agent gets the least repository and secret access it needs. Text it reads from issues or web pages is untrusted, because that is an injection path. And I measure it: tasks completed, review time, and how often its changes are reverted.

13.What do native multimodal models change in a design?Easy

One model handles text, images and often audio and video in the same context. So I can pass a diagram or screenshot directly instead of building an OCR pipeline, and I lose one stage that can drop layout, tables and arrows. The trade-offs remain: images use context tokens, latency rises, and I still need evals on my own documents, because a model can misread a dense table without any error. For large volumes of clean text, a text pipeline is still the cheaper path.

## Quiz

1.Which statement about the serving stack matches the guide?

2.In RLVR, where does the reward come from?

3.What do MCP and A2A connect?

4.Which is the revision-sheet line for TTFT?

5.You have two minutes for "what have you been following lately?". Which plan is strongest?

## Practice these problems

* [GENAIAgent runtime: loop, tools, checkpoints and budgetsHard](/ai/problems/agent-runtime-harness)
* [GENAIMCP tool platform for internal APIsMedium](/ai/problems/mcp-tool-platform)
* [GENAILoRA fine-tuning pipeline with an adapter registryHard](/ai/problems/fine-tuning-pipeline)
* [MLSDServe an open model to 1,000 concurrent usersHard](/ai/problems/llm-serving-platform)

## Further reading

* [What's Next in AI: Five Trends to Watch in 2026Articleblog.bytebytego.com](https://blog.bytebytego.com/p/whats-next-in-ai-five-trends-to-watch)
* [Latest AI Agent Frameworks in 2026Articleampcome.com](https://www.ampcome.com/post/latest-ai-agent-frameworks-2026)
* [LLM Inference Servers Compared: vLLM vs TGI vs SGLang vs TritonArticleblog.premai.io](https://blog.premai.io/llm-inference-servers-compared-vllm-vs-tgi-vs-sglang-vs-triton-2026)
* [Fine-Tuning LLMs in 2026: LoRA, QLoRA, DPO, GRPO ComparedArticlefutureagi.com](https://futureagi.com/blog/fine-tuning-llms-unlocking-peak-performance/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousLLM system design](/ai/learn/llm-system-design)[NextAttention variations - GQA, MLA](/ai/learn/attention-variations-gqa-mla)

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

1. [Three rules that make the difference in interviews](#three-rules-that-make-the-difference-in-interviews)
2. [How to answer "what have you been following lately?"](#how-to-answer-what-have-you-been-following-lately)
3. [The eleven trends](#the-eleven-trends)
4. [How to use the revision sheet](#how-to-use-the-revision-sheet)
5. [The revision sheet: 37 terms](#the-revision-sheet-37-terms)
6. [Prepare your own answer to these five](#prepare-your-own-answer-to-these-five)
7. [What this roadmap does not cover](#what-this-roadmap-does-not-cover)
