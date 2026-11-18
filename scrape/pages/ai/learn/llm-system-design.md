# LLM system design — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/llm-system-design

[AI roadmap](/ai)

ShipLesson #17StudyIntermediate 3 h

# LLM system design

LLM system design is the interview round where you design a whole product around a model: a chat service, document Q&A, a support agent or a serving platform. Almost every answer uses the same five layers and the same seven steps. This lesson gives you the layers, the steps, the arithmetic for capacity, cost and latency, and the points each common question expects.

system designcapacity planningcostlatency budgetcachinginterview framework

## Why it matters

This round decides the level you are hired at. The interviewer is not checking whether you know what RAG or vLLM is. They are checking whether you can turn a vague request into numbers, pick a model path and defend it, and say what breaks at 10 times the traffic. A fixed structure lets you spend your 45 minutes on the hard part and not on deciding what to draw. The same structure works at work: every design review for an LLM feature asks about traffic, tokens, latency, cost and evals.

Read first: [Vector DBs and RAG](/ai/learn/vector-dbs-rag), [Inference and serving - KV cache, batching, vLLM](/ai/learn/inference-serving), [Agents in depth - patterns, reliability, security](/ai/learn/agents-in-depth), [Evals, tracing and guardrails](/ai/learn/evals-tracing-guardrails)

## Lesson

Most LLM design questions use the same five layers. Draw them first, then go deep where the interviewer pushes.

### The five layers

![Five stacked layers of an LLM system with a data-and-tools box beside orchestration and an observability bar underneath](/ai/img/llm-system-five-layers.svg)Five stacked layers of an LLM system with a data-and-tools box beside orchestration and an observability bar underneath

| Layer | What sits in it |
| --- | --- |
| Client | Web or mobile app; tokens stream back to the user |
| API gateway | Auth, rate limits, model routing, response cache, fallback |
| Orchestration | Builds the context: prompt, retrieval, agent loop, guardrails |
| Model serving | vLLM or SGLang: continuous batching, KV cache, LoRA adapters |
| GPU nodes | Autoscaled on queue depth, with warm replicas |
| Data and tools (side box) | Vector DB and keyword index; MCP servers and external APIs; long-term memory store |

Observability and evals sit under every layer: traces, latency, cost and quality scores.

A request flows top to bottom; the orchestration layer is where RAG, agents and guardrails live, and it is where most of the design discussion happens. Orchestration is the only layer that talks to the data-and-tools box, and the link goes both ways: it reads chunks and memories, calls tools, and writes new memories back. If you use a hosted API, the provider runs the bottom two layers. You still own the top three, the data and the observability.

### The answer framework

1. **Clarify:** users, traffic, tokens per request, latency target, quality bar, data sensitivity, budget.
2. **Choose the model path:** hosted API or self-hosted open model, and why.
3. **Draw the layers** above and name what sits in each.
4. **Go deep on the hard part:** retrieval quality, agent reliability or serving capacity, depending on the question.
5. **Estimate capacity** with simple arithmetic.
6. **Add evals and monitoring:** what you measure offline and online.
7. **Cover failure and cost:** fallbacks, rate limits, caching, guardrails.

A workable split for a 45-minute round: clarify 5 minutes, model path 3, layers 5, the hard part 20, capacity 5, evals 4, failure and cost 3. Steps 1 to 3 are setup. Most of the time belongs to step 4.

### Step 1: what to ask, and why it changes the design

| Ask about | Why the answer changes the design |
| --- | --- |
| Users | Employees or the public? Public traffic needs moderation, abuse limits and stricter guardrails |
| Traffic | Peak requests per second sets the replica count and whether you need autoscaling at all |
| Tokens per request | Output tokens set GPU load and total latency; input tokens set prefill time, cost and whether prefix caching pays |
| Latency target | Decides streaming, model size and how many extra steps (reranker, guardrail, agent turns) fit |
| Quality bar | What does a wrong answer cost? Decides model size, citations, human approval and how strict the evals are |
| Data sensitivity | Personal or regulated data can rule out a public API and adds redaction and permission filters |
| Budget | A cost per request decides routing to small models, caching and the model path |

If the interviewer gives no numbers, state your own and move on: "I will assume 50 requests per second at peak and 500 output tokens."

### Step 2: hosted API or self-hosted

| Factor | Points to a hosted API | Points to self-hosting an open model |
| --- | --- | --- |
| Quality needed | Hardest reasoning, widest knowledge | A narrow task a small or fine-tuned model handles |
| Volume | Low or spiky; you pay per token | High and steady; GPUs stay busy |
| Data | May leave your network under a contract | Must stay inside your network |
| Control | Standard features are enough | You need LoRA adapters, constrained decoding or a fixed model version |
| Team | No GPU operations skill | Someone can run serving and be on call for it |
| Time | Launch this month | You can spend weeks on load tests and autoscaling |

A common answer is both: launch on a hosted API, then move the high-volume, simple requests to a small self-hosted model and keep the hosted model for hard requests and as a fallback.

### Step 4: find the hard part

| The question is about | The hard part | Go deep on |
| --- | --- | --- |
| Answering from documents | Retrieval quality | Chunking, hybrid search, reranking, permission filters, Recall@k on a labelled set |
| Taking actions for a user | Agent reliability | Tool design, step and cost limits, approval before risky actions, checkpoints, injection defence |
| Serving a model at scale | Serving capacity | KV cache memory, continuous batching, a load test, autoscaling signals, fallback |

If you are not sure which one the interviewer wants, ask: "Should I go deeper on retrieval or on serving?"

### Step 5: capacity arithmetic

A replica is one copy of the model server with its own GPU or GPUs. Headroom is spare capacity kept for spikes and for a replica that fails.

Formula

tokens per second=requests per second×output tokens per request

Formula

replicas=⌈tokens per second per replicatokens per second needed​×(1+headroom)⌉

**Capacity example (illustrative numbers):** peak load is 50 requests per second with 500 output tokens each, so you need 25,000 output tokens per second. If one replica sustains 2,500 tokens per second at your latency target, you need 10 replicas, or 13 with 30% headroom. Say that you would measure the per-replica number with a load test.

The per-replica figure is not a constant: it depends on model size, the GPU, the batch size, prompt length and the latency target. The inference lesson's example, one 7B replica with 32 requests in the batch at 40 ms per token, produces 32 / 0.040 = 800 tokens per second, while 2,500 assumes a replica that holds about 75 streams at 30 ms per token. Both are assumptions, and only a load test on your model, your GPU and your prompts gives the number to use.

Two more formulas help. Concurrent streams = requests per second x seconds each response stays open. This converts "1,000 concurrent users" into a rate. Daily tokens = requests per day x tokens per request, which feeds the cost estimate. Size for the peak, not the average: in the worked example below the peak is 3.5 times the daily mean.

### Cost

Formula

cost per request=106input tokens×pin​+output tokens×pout​​

Here p is the price per million tokens. At an assumed 0.50 USD per million input tokens and 1.50 USD per million output tokens, a request with 1,000 input and 500 output tokens costs (1,000 x 0.50 + 500 x 1.50) / 1,000,000 = 0.00125 USD.

For self-hosting, monthly cost = replicas x GPUs per replica x GPU-hour price x 720 hours. At an assumed 2.50 USD per GPU-hour, the 13 replicas above cost 13 x 2.50 x 720 = 23,400 USD a month. A GPU costs the same whether busy or idle, so utilisation decides the price per token: at 2,500 tokens per second, that GPU makes a million output tokens for 0.28 USD when always busy and 2.78 USD when 10% busy.

### Latency budget

Split the target across stages before choosing components. Here is an illustrative budget for a RAG chat whose p95 time to first token (TTFT) must be 1 second, meaning 95% of requests show their first token within that time:

| Stage | Budget |
| --- | --- |
| Gateway: auth, rate limit, cache lookup | 20 ms |
| Input guardrail | 50 ms |
| Embed the query | 30 ms |
| Hybrid search | 60 ms |
| Rerank 50 candidates | 150 ms |
| Queue wait at the model server | 100 ms |
| Prefill | 250 ms |
| Network | 40 ms |
| **Total** | **700 ms, leaving 300 ms spare** |

After the first token, time per output token takes over: 300 tokens at 30 ms each is another 9 seconds. Streaming is what makes that acceptable. Every extra model call before the first token (query rewriting, an LLM guardrail, an agent step) costs hundreds of milliseconds, so name the ones you can afford.

### Where caching goes

| Cache | Layer | Saves | Risk |
| --- | --- | --- | --- |
| Exact response cache | Gateway | The whole model call for a repeated prompt | Low hit rate outside FAQs |
| Semantic response cache | Gateway | The call for a similar question | A wrong match returns a wrong answer; never share across users with private data |
| Retrieval and embedding cache | Orchestration | Search time for popular queries | Stale results after re-indexing |
| Prefix (KV) cache | Model serving | Prefill for a shared system prompt or chat history | Breaks if the prompt start changes per request |

### Fallbacks and rate limits

* **Timeouts** on time to first token and on total time, so a stuck call fails fast.
* **Retries** with exponential backoff and jitter, only for errors that can succeed later (429, 5xx).
* **Fallback chain:** a second provider or model, then a smaller model, then a cached or fixed answer. Say that quality drops and how you would tell the user.
* **Rate limits in tokens per minute**, per user and per tenant, not only in requests. One request can cost 100 times another.
* **Backpressure:** when the queue is too long to meet the latency target, reject with a clear error; do not let every request get slow.
* **Guardrails** on input and output, and a cap on output tokens and agent steps.

### Evals and monitoring

Offline, before a change ships: a fixed eval set of real questions, task metrics, an LLM judge checked against human labels, and a gate that blocks a release when scores drop. Online, after it ships: p95 time to first token, time per output token, error and fallback rates, tokens and cost per request, cache hit rate, guardrail triggers, user feedback and the task metric (resolved tickets, accepted suggestions). Trace every request with one span per stage, and feed failed production cases back into the eval set.

### Common questions

| Question | Points your answer must include |
| --- | --- |
| Design a ChatGPT-like chat service | Token streaming, conversation store, context trimming and summarising, prefix caching, continuous batching, moderation, rate limits, autoscaling |
| Design document Q&A for an enterprise | Ingestion pipeline, chunking, hybrid search and reranking, permission filtering, citations, RAG evals, incremental re-indexing |
| Design a customer support agent | Tools for lookup and actions, approval before refunds, escalation to a human, customer memory, injection defence, task success as the metric |
| Serve an open model to 1,000 concurrent users | Engine choice, quantization, capacity maths, autoscaling on queue depth, multi-LoRA, gateway with fallback, a p95 TTFT target |
| Design a coding assistant | Small fast model for completion and a large one for chat, repository indexing, context selection, caching, test execution in a sandbox |
| Cut the cost of an LLM feature by half | Prompt trimming, caching, routing to smaller models, batching offline work, distilling or fine-tuning a small model, quality checks after each step |

### The serving question asked most often

"Design an inference batching system for one GPU while users wait" is reported again and again at AI labs. The expected answer: requests enter a queue, and a scheduler fires a batch when either the maximum batch size or a short maximum wait window is reached. Call the wait window your latency-throughput dial. Group requests by length so padding does not dominate, add backpressure when the queue grows, and mention continuous batching for token generation.

## Diagram

Rendering diagram…

## Worked example

**A support assistant for a shopping app.** Assumptions: 2,000,000 requests a day, a peak of 80 requests per second, 1,500 input tokens per request (system prompt, retrieved chunks, history) and 300 output tokens.

1. **Check the peak.** The average is 2,000,000 / 86,400 = 23.1 requests per second, so the peak is about 3.5 times the average. Size for 80.
2. **Tokens per second.** 80 x 300 = 24,000 output tokens per second at peak.
3. **Replicas.** Assume one replica sustains 3,000 output tokens per second while p95 TTFT stays under 1 second, a number to confirm with a load test using these 1,500-token prompts. 24,000 / 3,000 = 8 replicas.
4. **Headroom.** 8 x 1.3 = 10.4, so 11 replicas.
5. **Cross-check with concurrency.** With a 0.5 s TTFT and 30 ms per token, one response stays open for 0.5 + 299 x 0.03 = 9.47 s. Concurrent streams = 80 x 9.47 = 758, or 69 per replica across 11. At 30 ms per token a replica producing 3,000 tokens per second carries 90 streams, so 69 fits.
6. **Daily tokens.** Input: 2,000,000 x 1,500 = 3.0 billion. Output: 2,000,000 x 300 = 0.6 billion.
7. **Hosted cost.** At an assumed 0.50 USD per million input tokens and 1.50 USD per million output tokens: 3,000 x 0.50 + 600 x 1.50 = 1,500 + 900 = 2,400 USD a day, 72,000 USD a month, 0.0012 USD per request.
8. **Self-hosted cost.** At an assumed 2.50 USD per GPU-hour with one GPU per replica, always on: 11 x 2.50 x 720 = 19,800 USD a month, 0.00033 USD per request.
9. **Decision.** On these assumptions hosting is 3.6 times the GPU bill. That gap has to pay for the engineers who run the serving stack, and it only holds if a small open model meets the quality bar. Scaling down at night widens the gap. If traffic were 10 times lower, the hosted bill would be 7,200 USD a month against 3,600 USD for 2 replicas, and a 3,600 USD saving does not pay for running a serving stack.

Say the last step aloud. The interviewer wants the decision and what would change it, not only the numbers.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""Capacity and cost calculator for an LLM service. Pure Python.

Every price and every per-replica throughput below is an assumption.
Replace them with your provider's price list and your own load test.
"""
import math

HOURS_PER_MONTH = 24 * 30

def capacity(peak_rps, output_tokens, replica_tps, headroom=0.30):
    """Replicas needed at peak. replica_tps = output tokens per second that one
    replica sustains at the latency target (measure it with a load test)."""
    need_tps = peak_rps * output_tokens
    base = need_tps / replica_tps
    with_headroom = math.ceil(round(base * (1 + headroom), 9))
    return {"need_tps": need_tps, "base": base, "replicas": with_headroom}

def concurrent_streams(peak_rps, output_tokens, ttft_s, tpot_s):
    """Streams open at once = arrival rate x time each request stays open."""
    duration = ttft_s + (output_tokens - 1) * tpot_s
    return duration, peak_rps * duration

def hosted_cost(requests_per_day, input_tokens, output_tokens, usd_in_per_m, usd_out_per_m):
    per_request = (input_tokens * usd_in_per_m + output_tokens * usd_out_per_m) / 1e6
    return {"per_request": per_request, "per_day": per_request * requests_per_day,
            "per_month": per_request * requests_per_day * 30}

def self_hosted_cost(replicas, usd_per_gpu_hour, requests_per_day, gpus_per_replica=1):
    per_month = replicas * gpus_per_replica * usd_per_gpu_hour * HOURS_PER_MONTH
    return {"per_month": per_month, "per_request": per_month / (requests_per_day * 30)}

def estimate(name, peak_rps, requests_per_day, input_tokens, output_tokens, replica_tps,
             ttft_s, tpot_s, usd_in_per_m, usd_out_per_m, usd_per_gpu_hour):
    cap = capacity(peak_rps, output_tokens, replica_tps)
    duration, streams = concurrent_streams(peak_rps, output_tokens, ttft_s, tpot_s)
    api = hosted_cost(requests_per_day, input_tokens, output_tokens, usd_in_per_m, usd_out_per_m)
    own = self_hosted_cost(cap["replicas"], usd_per_gpu_hour, requests_per_day)
    print(name)
    print(f"  output tokens per second at peak : {peak_rps} x {output_tokens} = {cap['need_tps']:,}")
    print(f"  replicas before headroom         : {cap['need_tps']:,} / {replica_tps:,} = {cap['base']:.1f}")
    print(f"  replicas with 30% headroom       : {cap['base'] * 1.3:.1f} -> {cap['replicas']}")
    print(f"  one response stays open          : {duration:.2f} s, so {streams:.0f} concurrent streams,"
          f" {streams / cap['replicas']:.0f} per replica")
    print(f"  tokens per day                   : {requests_per_day * input_tokens / 1e9:.2f} B input,"
          f" {requests_per_day * output_tokens / 1e9:.2f} B output")
    print(f"  hosted API (assumed prices)      : {api['per_request']:.5f} USD per request,"
          f" {api['per_day']:,.0f} USD per day, {api['per_month']:,.0f} USD per month")
    print(f"  self-hosted (assumed GPU price)  : {own['per_month']:,.0f} USD per month,"
          f" {own['per_request']:.5f} USD per request")
    print(f"  hosted / self-hosted             : {api['per_month'] / own['per_month']:.1f}x, before engineering cost")
    return cap, api, own

if __name__ == "__main__":
    # 1. The guide's example: 50 requests per second, 500 output tokens,
    #    2,500 tokens per second per replica, 30% headroom -> 13 replicas.
    #    Requests per day, input tokens and prices are extra assumptions for the cost lines.
    cap, api, own = estimate("Guide example", peak_rps=50, requests_per_day=1_500_000,
                             input_tokens=1_000, output_tokens=500, replica_tps=2_500,
                             ttft_s=0.5, tpot_s=0.03, usd_in_per_m=0.50, usd_out_per_m=1.50,
                             usd_per_gpu_hour=2.50)
    assert (cap["need_tps"], cap["base"], cap["replicas"]) == (25_000, 10.0, 13)
    assert abs(api["per_request"] - 0.00125) < 1e-12 and round(own["per_month"]) == 23_400

    # 2. The worked example: shopping-app support assistant.
    cap, api, own = estimate("Worked example", peak_rps=80, requests_per_day=2_000_000,
                             input_tokens=1_500, output_tokens=300, replica_tps=3_000,
                             ttft_s=0.5, tpot_s=0.03, usd_in_per_m=0.50, usd_out_per_m=1.50,
                             usd_per_gpu_hour=2.50)
    assert (cap["need_tps"], cap["base"], cap["replicas"]) == (24_000, 8.0, 11)
    assert round(api["per_month"]) == 72_000 and round(own["per_month"]) == 19_800

    # 3. Cost per million output tokens on your own GPU depends on utilisation.
    print("Self-hosted cost per million output tokens at an assumed 2.50 USD per GPU-hour, 2,500 tokens/s:")
    for utilisation in (1.0, 0.5, 0.1):
        usd = 2.50 / 3600 / (2_500 * utilisation) * 1e6
        print(f"  GPU {utilisation:>4.0%} busy: {usd:.2f} USD")
    print("all checks passed")
```

## Key takeaways

* Five layers: client, API gateway, orchestration, model serving, GPU nodes. Data and tools sit beside orchestration; observability and evals sit under everything.
* Seven steps: clarify, choose the model path, draw the layers, go deep on the hard part, estimate capacity, add evals and monitoring, cover failure and cost.
* Tokens per second = requests per second x output tokens. Replicas = needed / per replica, plus headroom, rounded up. 50 x 500 = 25,000; / 2,500 = 10; with 30% headroom, 13.
* The per-replica number is an assumption until a load test measures it. Say so.
* Cost per request = (input tokens x input price + output tokens x output price) / 1,000,000. A self-hosted GPU costs the same idle or busy, so utilisation decides.
* Give time to first token a budget per stage. After the first token, output length times time per token dominates.
* Each cache has a layer: response caches at the gateway, retrieval caches in orchestration, the prefix cache in the model server.
* Always end with fallbacks, token-based rate limits, guardrails and what you measure offline and online.

## Common mistakes

* Drawing boxes before asking about traffic, tokens, latency and data sensitivity. The design depends on all four.
* Giving no numbers. "It should scale" is not an answer; 25,000 tokens per second and 13 replicas is.
* Sizing for average traffic. Queues form at the peak, and the peak is often several times the mean.
* Treating the model as a box with fixed latency. Latency depends on prompt length, output length and how many requests share the GPU.
* Spending twenty minutes on the layer you know best while the interviewer keeps asking about another one.
* Stopping at the happy path: no evals, no fallback, no rate limits, no plan for a wrong or harmful answer.

## Practice

* Pick one of the six common questions and answer it aloud in 35 minutes using the seven steps. Record it, then check that you stated traffic, tokens per request, a latency target and a replica count.
* Run the calculator with your own product idea: choose requests per day, peak rate and tokens per request, and find the daily volume at which self-hosting becomes cheaper than the hosted price you assumed.
* Write a latency budget for a voice agent whose first audio must start within 800 ms. List every stage and decide which steps from the RAG budget you must drop.
* Draw the five layers from memory, then list for each layer one metric you would put on a dashboard and one failure you would alert on.

## Interview questions (13)

1.How do you structure an answer to an LLM system design question?Easy

Seven steps. First clarify: users, traffic, tokens per request, latency target, quality bar, data sensitivity and budget. Second, choose the model path, hosted API or self-hosted open model, and say why. Third, draw the five layers and name what sits in each. Fourth, go deep on the hard part, which is retrieval quality, agent reliability or serving capacity depending on the question. Fifth, estimate capacity with simple arithmetic. Sixth, add evals and monitoring, offline and online. Seventh, cover failure and cost: fallbacks, rate limits, caching and guardrails. I keep the first three steps to under fifteen minutes so the hard part gets most of the time.

2.Design a ChatGPT-like chat service.Hard

I would clarify scale and latency first, say a p95 time to first token under one second. The client holds a streaming connection and tokens stream back as they are generated. The gateway does auth, moderation of the input and per-user token rate limits. A conversation store keeps every turn. Orchestration builds the context: system prompt, then history, trimming old turns and summarising them when the window fills. I keep the prompt start stable so prefix caching works across turns. The model server uses continuous batching so short and long answers share the GPU. Output moderation runs on the stream. GPU replicas autoscale on queue depth with a warm minimum. I would then size it: requests per second times output tokens, divided by measured tokens per second per replica.

3.Design document Q&A for an enterprise.Medium

Two paths. Offline, an ingestion pipeline parses documents, chunks them on structure, embeds the chunks and writes them to a vector index and a keyword index, with the access groups stored on every chunk. Incremental re-indexing handles changes: hash each document, re-embed only what changed and delete stale chunks. Online, the query runs through hybrid search and a reranker, with permission filtering inside the search so restricted text never reaches the prompt. The model answers only from the retrieved chunks and returns citations. For RAG evals I measure retrieval and generation separately: Recall@k on a labelled set, then faithfulness and answer correctness. The hard part is retrieval quality, so that is where I would spend the time.

4.Design a customer support agent.Hard

The agent is a model in a loop with tools. Lookup tools read orders, accounts and policies. Action tools change things: cancel an order, issue a refund. Lookups run freely; any refund needs approval first, from a human or a strict policy check, and every action is logged. The agent escalates to a human when it is unsure, when the customer asks, or when it hits its step limit, and passes on a summary. Customer memory stores past issues and preferences so the customer does not repeat themselves. For injection defence I treat ticket text and tool results as data, not instructions, and give the agent only the permissions of the customer it serves. The metric is task success: issues resolved without a human and without a reopened ticket.

5.Serve an open model to 1,000 concurrent users.Hard

I start with a target, say p95 TTFT under one second and 30 tokens per second per stream. Engine choice: vLLM as the default, SGLang if requests share long prefixes. Quantization: FP16 if memory allows, 8-bit or 4-bit after checking my eval set. Capacity maths: 1,000 streams x 30 tokens per second is 30,000 tokens per second. If a load test shows 2,500 per replica at the target, that is 12 replicas, or 16 with 30% headroom. I autoscale on queue depth with warm replicas because loading a model is slow. If tenants have fine-tuned variants I use multi-LoRA on one base model. A gateway in front handles rate limits, retries and fallback to another model.

6.Design a coding assistant.Hard

There are two workloads. Inline completion fires on keystrokes and needs a reply in a few hundred milliseconds, so it uses a small fast model, short outputs and cancellation when the user keeps typing. Chat and agent requests can take seconds and use a large model. Both depend on context selection: I index the repository, with embeddings and a symbol index, and send the open file, nearby code and the most relevant definitions, not the whole repository. Caching matters twice: the prefix cache for the stable part of the prompt and a cache for repeated completions. When the assistant edits code, tests run in a sandbox with no access to secrets or the network, and failures go back to the model. I would measure suggestion acceptance rate and test pass rate.

7.Cut the cost of an LLM feature by half.Medium

First I measure where tokens go, per feature and per step. Then I work from cheapest to hardest. Prompt trimming: shorter instructions, fewer retrieved chunks, a cap on output tokens. Caching: prefix caching for the shared prompt and a response cache for repeated questions. Routing: send easy requests to a smaller model and keep the large one for hard ones. Batching offline work, such as summaries and evals, on a cheaper batch path. If volume is steady, distil or fine-tune a small model for the main task. After each step I rerun the eval set, because a saving that drops quality below the bar is not a saving.

8.Design an inference batching system for one GPU while users wait.Hard

Requests enter a queue, and a scheduler fires a batch when either the maximum batch size or a short maximum wait window is reached. The wait window is the latency-throughput dial: 5 ms gives small batches and low wait, 50 ms gives full batches and higher throughput. I group requests by length so padding does not dominate. I add backpressure when the queue grows: past a limit, new requests get an error with a retry hint so the ones already waiting still meet the target. For token generation I would use continuous batching, where finished requests leave and waiting ones join at every decode step. I would watch queue wait, batch size and p95 TTFT to tune the two limits.

9.Hosted API or a self-hosted open model: how do you decide?Medium

Five things decide it. Quality: the hardest reasoning usually needs a top hosted model, while a narrow task can run on a small open one. Volume: per-token pricing wins when traffic is low or spiky, and owned GPUs win when traffic is high and steady enough to keep them busy. Data: if it cannot leave the network, self-host or use a private endpoint. Control: adapters, constrained decoding or a pinned model version point to self-hosting. Team: someone has to run the serving stack and be on call. I usually propose a hosted API to launch, then a self-hosted small model for the high-volume path once the numbers justify it, with the hosted model as fallback.

10.Peak load is 50 requests per second with 500 output tokens each. How many replicas do you need?Medium

50 x 500 is 25,000 output tokens per second. I need one more number: what one replica sustains at my latency target. If that is 2,500 tokens per second, I need 10 replicas, and with 30% headroom for spikes and a failed node, 13. I would say clearly that 2,500 is an assumption and that I would measure it with a load test on real prompts, because it depends on the model, the GPU, the prompt lengths and the latency target. I would also check the prefill load, since long prompts take GPU time that an output-token count does not show.

11.Where do you put caches in an LLM system?Medium

Three places. At the gateway, a response cache: exact match on the normalised prompt, and optionally a semantic cache that matches similar questions by embedding. The semantic cache needs a strict similarity threshold, and the user or tenant in the key when answers depend on private data. In orchestration, I cache query embeddings and retrieval results for popular queries and clear them on re-index. In the model server, the prefix cache reuses the KV cache for a shared system prompt and chat history, which cuts time to first token. To make that work I put stable text first in the prompt. I report hit rate for each cache, because an unused cache is only extra risk.

12.The model provider is slow or down. What does your system do?Medium

It degrades in steps. Every call has a timeout on first token and on total time. Errors that can succeed later, such as 429 and 5xx, are retried with exponential backoff and jitter, a small number of times. A circuit breaker stops sending traffic to a provider that keeps failing. Then the fallback chain: a second provider or region, then a smaller model I host, then a cached or fixed answer that says the service is limited. For agents, a step that changes data is retried only if it is idempotent. I alert on the fallback rate, and I run the eval set on the fallback model in advance so I know how much quality drops.

13.What do you monitor after launch?Medium

Four groups. Latency: p95 and p99 time to first token and time per output token, plus queue wait. Reliability: error rate, timeout rate, fallback rate and rate-limit rejections. Cost: input and output tokens per request, cost per request and per user, cache hit rate. Quality: user feedback, the task metric such as resolved tickets or accepted suggestions, guardrail triggers, and a sampled LLM-judge score on production traffic. Every request has a trace with a span per stage, so a slow or wrong answer can be followed from the gateway to the model. Failed cases go into the offline eval set, which runs before every prompt or model change.

## Quiz

1.Peak load is 40 requests per second with 250 output tokens each. One replica sustains 2,000 tokens per second. How many replicas with 30% headroom?

2.Which layer owns retrieval, the agent loop and guardrails?

3.A request has 2,000 input tokens and 400 output tokens. At an assumed 1 USD per million input tokens and 4 USD per million output tokens, what does it cost?

4.Why should rate limits count tokens and not only requests?

5.Where does the prefix (KV) cache live?

## Practice these problems

* [GENAIRAG pipeline for internal docs Q&AMedium](/ai/problems/rag-pipeline)
* [GENAICustomer support agent with tools and approvalsHard](/ai/problems/customer-support-agent)
* [GENAIAI code assistant: completion, chat and agentHard](/ai/problems/code-assistant)
* [GENAIChatGPT-like chat serviceHard](/ai/problems/chat-service)
* [GENAICut LLM cost by half: model routing and cascadesMedium](/ai/problems/llm-cost-router)
* [MLSDServe an open model to 1,000 concurrent usersHard](/ai/problems/llm-serving-platform)

## Further reading

* [vLLM documentationGuidedocs.vllm.ai](https://docs.vllm.ai/)
* [FrugalGPT: How to Use Large Language Models While Reducing CostPaperarxiv.org](https://arxiv.org/abs/2305.05176)
* [OpenTelemetry documentationGuideopentelemetry.io](https://opentelemetry.io/docs/)
* [45+ AI Engineer Interview Questions and Answers (2026 Guide)Articlecareerservices.upenn.edu](https://careerservices.upenn.edu/blog/2026/06/25/45-ai-engineer-interview-questions-answers-2026-guide/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousEvals, tracing and guardrails](/ai/learn/evals-tracing-guardrails)[NextWhat is new in 2026 + revision](/ai/learn/whats-new-2026-revision)

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

1. [The five layers](#the-five-layers)
2. [The answer framework](#the-answer-framework)
3. [Step 1: what to ask, and why it changes the design](#step-1-what-to-ask-and-why-it-changes-the-design)
4. [Step 2: hosted API or self-hosted](#step-2-hosted-api-or-self-hosted)
5. [Step 4: find the hard part](#step-4-find-the-hard-part)
6. [Step 5: capacity arithmetic](#step-5-capacity-arithmetic)
7. [Cost](#cost)
8. [Latency budget](#latency-budget)
9. [Where caching goes](#where-caching-goes)
10. [Fallbacks and rate limits](#fallbacks-and-rate-limits)
11. [Evals and monitoring](#evals-and-monitoring)
12. [Common questions](#common-questions)
13. [The serving question asked most often](#the-serving-question-asked-most-often)
