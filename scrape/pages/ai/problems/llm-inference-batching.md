# Inference batching system for one GPU — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/llm-inference-batching

[AI problems](/ai#problems)

MLSDML system design#23Hard

# Inference batching system for one GPU

continuous batchingkv cacheschedulingstreaminggpu inferenceadmission controlReported at Anthropic

## Problem statement

You have one 80 GB GPU with a 7B open model loaded. Design the server that turns it into an API for sampling from the model: a prompt and sampling settings go in, tokens stream out. Many users call it at once and wait for their answers. Prompts run from 50 to 8,000 tokens and answers from 1 to 1,000 tokens. Batch the requests so the GPU does as much work as possible, while the first token still arrives fast, short requests are not stuck behind long ones, and a cancelled request stops costing GPU time.

## Requirements

### Functional

* Accept a prompt with per-request sampling settings (temperature, top-k, top-p, seed, stop strings, max tokens) and stream the sampled tokens back.
* Run many requests in one forward pass. A request joins the batch and leaves it between two decode steps.
* Queue requests when the GPU is full, and reject new ones with a retry hint when the wait would be too long.
* Never run out of GPU memory, whatever mix of prompt and answer lengths arrives.
* Stop a request within one step when the client cancels or disconnects, and free its memory.
* Share the GPU fairly between API keys and between short and long requests.

### Non-functional

* One 80 GB GPU, one 7B model in FP16. Sustain 1.5 requests per second at an average of 1,250 prompt tokens and 300 output tokens.
* p95 time to first token (TTFT) under 1 second for prompts up to 2,000 tokens at that load.
* p95 time per output token (TPOT) under 70 ms, which is at least 14 tokens per second for every stream.
* In a burst, at most 2 seconds of GPU work may wait in the queue. Past that, new requests get a 429 with a Retry-After header.
* A cancelled request frees its batch row and memory within one decode step, under 70 ms.
* Prompt plus max tokens is limited to 8,192 tokens, and the cache pool is capped at 60 GB, so the server cannot crash from memory.

## Back-of-the-envelope estimates

**Model.** 7 billion parameters x 2 bytes (FP16) = 14 GB. 32 layers, 32 heads, head dimension 128.

**KV cache.** The KV cache stores the attention keys and values of every past token, so each decode step computes only the new token. Per token: 2 x 32 x 32 x 128 x 2 bytes = 524,288 bytes (0.52 MB). Keep 6 GB for activations. Pool: 80 - 14 - 6 = 60 GB. In blocks of 16 tokens (8.39 MB each) that is 7,152 blocks, or 114,432 tokens.

**How many requests fit.** An average request holds 1,250 + 300 = 1,550 tokens = 0.81 GB, so 73 fit. A request at the 8,192-token limit holds 4.29 GB, so only 13 fit.

**Speed (assumptions, to be replaced by a load test).** Prefill, the single pass over the prompt, runs at 10,000 tokens per second: 0.1 ms per prompt token. A decode step takes 25 ms for 1 request and 40 ms for 32, because each step reads all 14 GB of weights once, however many rows share it.

**One at a time.** 0.125 s of prefill + 299 x 25 ms = 7.6 s per request. That is 0.13 requests per second and 40 tokens per second.

**Batched.** 32 / 0.040 = 800 tokens per second, 20 times more, and each user still gets up to 25 tokens per second.

**GPU time per request.** Prefill: 1,250 x 0.1 ms = 125 ms. Decode: 300 tokens x (40 ms / 32) = 375 ms. Total 0.5 s, so the GPU is full at 2 requests per second, 15 times the unbatched rate. Plan for 75% of that: 1.5 requests per second, which is 1,875 prompt tokens and 450 output tokens per second.

**Which cap binds.** 32 average requests hold 26 GB, so the latency cap of 32 rows binds first. With long prompts the memory cap binds first, at 13 rows.

## API

```
POST /v1/completions
  body:   { prompt | prompt_token_ids, max_tokens (up to 1,000),
            temperature, top_k, top_p, stop[], seed?, n?, logprobs?,
            stream: true }
  stream: server-sent events
          { request_id, index, text, token_id, logprob? }      one per token
          { finish_reason: "stop" | "length" | "cancelled",
            usage:  { prompt_tokens, completion_tokens },
            timing: { queue_ms, ttft_ms } }                     last event
  errors: 400  prompt + max_tokens is over 8,192 tokens
          429  more than 2 s of GPU work is queued; Retry-After: seconds

DELETE /v1/requests/{request_id}     cancel; a client disconnect does the same

GET /metrics
  -> queue_depth, queued_gpu_seconds, running_rows, kv_blocks_free,
     ttft and tpot histograms, preemptions, cancelled_tokens
```

## Data model

```
Request  { request_id, api_key, prompt_ids[], max_tokens,
           sampling: { temperature, top_k, top_p, seed, stop[] },
           arrival_ts, deadline_ts, est_gpu_ms,
           state: QUEUED | PREFILL | DECODE | PREEMPTED | DONE | CANCELLED,
           prefilled, generated[], block_ids[], rng_state, out_queue }

KeyUsage { api_key, weighted_tokens_served, running_rows }   -- fair queueing

KV pool: 7,152 blocks. One block holds keys and values for 16 tokens:
         [32 layers, 2, 32 heads, 16 tokens, 128]  FP16  = 8.39 MB
block_table: request_id -> [block_id, ...]
ref_count[block_id]        -- above 1 when n samples share one prompt
free_list: [block_id, ...]

One step with B decode rows and a prefill chunk of C prompt tokens:
  token_ids [B + C]    positions [B + C]    request_of_token [B + C]
  logits    [B, 32,000]                     -- assumed vocabulary size
  temperature [B], top_k [B], top_p [B]  ->  next_token [B]
```

## High-level design

There is one path, and it is online. The centre is a loop that runs one decode step per pass. Requests join and leave between passes.

1. An API worker on the CPU validates the request, tokenizes the prompt and rejects it if prompt plus max tokens is over 8,192. It estimates the GPU cost: prompt tokens x 0.1 ms + expected output tokens x 1.25 ms, where the expectation is the smaller of max tokens and the recent average answer length.
2. Admission control adds up the estimated cost of everything waiting. Above 2 GPU-seconds it returns 429 with Retry-After. Otherwise the request joins the queue of its API key.
3. One scheduler thread owns the GPU. Steps 4 to 9 are one pass of its loop.
4. Leave: rows that sampled a stop token, reached max tokens, were cancelled or passed their deadline are removed. Their blocks go back to the free list.
5. Join: while fewer than 32 rows are running and the free blocks cover the next prompt plus a safety margin, admit a request. The next one comes from the API key with the fewest weighted tokens served so far.
6. Build the step: one new token for every decoding row, plus up to 256 prompt tokens for requests still in prefill.
7. Run one forward pass. Each row reads its own blocks through the block table, and its new keys and values are appended. A row takes a new block every 16 tokens.
8. Sample one token per row with that row's temperature, top-k and top-p, using the request's own seeded random generator. A request whose last prompt chunk was in this step samples its first token here, and its TTFT ends.
9. Push each token id to the request's output queue. CPU workers detokenize and write server-sent events, so the loop never waits on a network socket.
10. If the free list runs empty, the scheduler preempts the most recently admitted request: it frees the blocks and puts the request at the front of the queue.

## Sequence diagram

Rendering diagram…

## Deep dives

### Static, dynamic or continuous batching

A decode step for one request reads every weight to produce one token, and most of the GPU's arithmetic units sit idle. Rows added to the same step reuse that read, which is why 32 rows cost 40 ms and not 32 x 25 ms. The question is how to form the batch. Static batching waits for a fixed number of requests and runs them to the end. Dynamic batching fires when the batch is full or when the oldest request has waited a maximum window, say 10 ms. That window is the latency-throughput dial: a longer window fills bigger batches and adds waiting. Both hold the batch until its longest request ends. A 20-token answer beside a 1,000-token answer leaves its row idle for 980 steps, and a new arrival can wait 1,000 x 40 ms = 40 s. Dynamic batching suits work of fixed size, such as embeddings. For generation use continuous batching: the batch is rebuilt at every decode step, so a request waits at most one step to join and leaves the moment it ends. The dials become the row cap, the KV block budget and the prefill chunk.

### Two caps on the batch: latency and memory

The row cap comes from the TPOT target, because every extra row slows the step. The memory cap comes from the pool. Allocate blocks as a sequence grows, the idea behind PagedAttention, so a request wastes at most 15 token slots. Reserving prompt plus max tokens up front is simpler, but with max tokens set to 1,000 an average request would reserve 2,250 tokens and use 1,550, and the pool would hold 50 requests where 73 fit. Growing on demand needs a safety net. Keep 5% of the pool free (358 blocks) when admitting. 32 rows take about 2 new blocks per step, so that covers about 180 steps. If the pool still empties, preempt the newest request and prefill it again later, including the tokens it already produced. Its user sees a pause, not an error.

### Prefill and decode share each step

TTFT is queue wait plus prefill, and TPOT is the step time, so the two are tuned separately. Prefilling an 8,000-token prompt in one pass takes 0.8 s, and all 32 running streams freeze for that time. So cap prefill at 256 prompt tokens per step. A step then takes 40 + 25.6 = 65.6 ms at worst, inside the 70 ms target. The cost moves to the newcomer: 8,000 tokens need 32 steps, about 2.1 s to its first token where 0.8 s was possible. The chunk size trades one user's TTFT against everyone's TPOT, so raise it when few rows are decoding. Padding only matters in prefill, because a decode row adds exactly one token. Prompts of 200, 400, 600 and 8,000 tokens padded to 8,000 compute 32,000 positions for 9,200 real tokens, 71% waste. Group prompts by length, or pass the chunk as a flat list of tokens tagged with their request, which needs no padding.

### Fairness, cancellation and streaming

Continuous batching already lets a short answer leave early. Two problems remain. One API key can fill every row, so admit from the key with the fewest weighted tokens served, and cap a key at 8 rows while others wait. Weight an output token about 12 times a prompt token: it costs 1.25 ms of GPU against 0.1 ms. Do not sort the queue by declared max tokens: clients would under-declare, and long requests would starve. A disconnect sets a cancel flag that the loop reads at the next step boundary. Without it, an abandoned 1,000-token answer holds a row for 40 s. For streaming, the loop only pushes token ids to a per-request queue. CPU workers detokenize, hold back a half-finished character, and cancel a client that reads nothing for 30 s.

## Evaluation

**Load test.** Replay logged prompts with their real length mix. Send them at fixed arrival rates of 0.5, 1, 1.5, 2 and 2.5 requests per second, not with a fixed number of simulated users, because users who wait for replies hide the queue. At each rate record p50, p95 and p99 of TTFT, TPOT and the longest gap between two tokens, plus queue wait, rows per step, pool use, preemptions and 429s. The capacity number is goodput: the highest rate at which 95% of requests meet both latency targets. It replaces the assumed 2 requests per second.

**Scheduler comparison.** Run the same trace through static, dynamic (10 ms window), continuous, and continuous with chunked prefill. Then sweep the row cap (16, 32, 48) and the chunk (128, 256, 512), and plot throughput against p95 TPOT.

**Correctness.** At temperature 0, a request must produce the same tokens alone and in a batch of 32 with mixed lengths. This catches mask, position and block-table bugs. With a fixed seed, sampling must repeat. Give 1,000 concurrent requests each a unique marker string and require that no output contains another request's marker.

**Fairness.** One key sends 100 long requests at once while another sends 1 short request per second. The second key's p95 TTFT must stay under 1 second.

**Cancellation and memory.** Disconnect 20% of clients mid-stream. Each must cost at most one more step, and after a one-hour soak test the free list must be back at 7,152 blocks.

**Online.** The same latency metrics split by prompt-length bucket, the 429 rate, and tokens generated for requests that were later cancelled.

## Bottlenecks & mitigations

* Decode step time. It grows with every row, so the TPOT target sets the row cap and with it the 800 tokens per second.
* The KV pool. Contexts near 8,192 tokens cut the batch from 32 rows to 13.
* Prefill. It takes 25% of GPU time at full load here, and more when prompts get longer.
* CPU work between steps: admission, sampling settings and detokenizing. 5 ms of it per pass adds 12.5% to a 40 ms step.
* One scheduler process on one GPU. Any crash drops all 32 streams at once.

## Failure modes

* **The KV pool runs out in the middle of generation.** Blocks are given out on demand and answers ran longer than usual. Mitigation: admit with a 5% free margin, preempt the newest request, and enforce the 8,192-token limit at the API.
* **One long prompt freezes every stream.** Its prefill runs as a single 0.8 s pass. Mitigation: the 256-token prefill budget per step, and an alert on the longest gap between tokens.
* **Abandoned requests keep generating.** The client left but its row runs to max tokens. Mitigation: disconnect detection, a cancel flag read at every step boundary, and a deadline on every request.
* **Overload turns into a retry storm.** Arrivals pass 2 requests per second, the queue grows, clients time out and send again. Mitigation: bound the queue in GPU-seconds, return 429 with Retry-After, and drop queued requests whose client has already gone before spending prefill on them.
* **A row reads another request's cache.** A block is freed while still referenced, or the block table is wrong, and one user's text leaks into another's answer. Mitigation: reference counts on blocks, and the marker-string test in CI and as a production probe.
* **Output depends on batch neighbours.** A shared random generator or a wrong padding mask changes a request's tokens. Mitigation: one generator per request, and the batch-invariance test at temperature 0.
* **The scheduler process or the GPU fails.** All streams end. Mitigation: a supervisor restarts the process, the 14 GB of weights reload in about 14 s at an assumed 1 GB per second, and every open stream gets an explicit error event so the client can retry.

## Follow-up questions interviewers ask

* Most requests share a 1,000-token system prompt. How would you add prefix caching, and what changes in the block reference counts and in eviction?
* A client asks for n = 4 samples of one prompt. How do the four rows share the prompt's KV blocks?
* Add an offline tier whose requests can wait for minutes. How do you schedule it without hurting interactive latency?
* You are given a second GPU. Do you run two copies of this server or one larger batch, and what if the model no longer fits on one GPU?
* Answers must match a JSON schema. What does constrained decoding add to each step, and where does that work run?
* How does speculative decoding with a small draft model interact with a full batch?

## Lessons that cover this

* [#11Inference and serving - KV cache, batching, vLLMServing](/ai/learn/inference-serving)

## Further reading

* [Orca: A Distributed Serving System for Transformer-Based Generative ModelsPaperusenix.org](https://www.usenix.org/conference/osdi22/presentation/yu)
* [Efficient Memory Management for LLM Serving with PagedAttentionPaperarxiv.org](https://arxiv.org/abs/2309.06180)
* [Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-ServePaperarxiv.org](https://arxiv.org/abs/2403.02310)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousCut LLM cost by half: model routing and cascades](/ai/problems/llm-cost-router)[NextServe an open model to 1,000 concurrent users](/ai/problems/llm-serving-platform)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [High-level design](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Evaluation](#evaluation)
10. [Bottlenecks](#bottlenecks)
11. [Failure modes](#failures)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
