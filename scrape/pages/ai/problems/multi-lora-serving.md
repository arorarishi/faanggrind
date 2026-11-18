# Multi-tenant LoRA adapter serving — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/multi-lora-serving

[AI problems](/ai#problems)

MLSDML system design#25Medium

# Multi-tenant LoRA adapter serving

loramulti-tenantinference servingadapter cachebatchingrouting

## Problem statement

Design the serving layer for a product where 5,000 business customers each have their own LoRA adapter, a small set of fine-tuned weights, on the same 7B base model. Requests arrive at 40 per second at peak. A few customers send most of them, and most adapters are idle at any moment. Serve every adapter with a p95 time to first token under 1 second, without giving each customer a GPU.

## Requirements

### Functional

* Serve a streamed chat completion with the adapter named in the request, through a per-customer alias.
* Register, update and retire adapters without restarting any replica.
* Run requests that use different adapters in the same batch.
* Load an adapter on demand when it is not in GPU memory, and evict idle adapters to make room.
* Route each request to a replica that already holds its adapter whenever one has capacity.
* Guarantee isolation: a request never runs with another customer's adapter.

### Non-functional

* 5,000 adapters, 40 requests per second at peak, with 750 prompt tokens and 250 output tokens per request on average.
* p95 time to first token (TTFT) under 1 second overall, and under 1.5 seconds when the adapter must be fetched from remote storage.
* At least 95% of requests find their adapter already in GPU memory.
* Throughput per replica within 20% of a merged model on the same GPU, confirmed by a load test.
* A new adapter version is servable within 60 seconds of registration, and a rollback takes effect within 60 seconds.
* GPU count follows traffic, not the number of adapters: about 26 GPUs for 5,000 customers.

## Back-of-the-envelope estimates

**Adapter size.** Rank 16 on the attention and MLP matrices of a 7B model with 32 layers, hidden size 4,096 and MLP width 11,008. An attention matrix adds 16 x (4,096 + 4,096) = 131,072. An MLP matrix adds 16 x (4,096 + 11,008) = 241,664. Per layer: 4 x 131,072 + 3 x 241,664 = 1,249,280. Times 32 layers: 39,976,960 values, 80 MB in 16-bit.

**All adapters.** 5,000 x 80 MB = 400 GB. Merged copies: 5,000 x 14 GB = 70 TB, and one GPU per customer.

**GPU memory, 80 GB.** Base weights: 14 GB. The KV cache holds attention keys and values for every token in flight: 2 x 32 layers x 4,096 x 2 bytes = 524,288 bytes per token, x 32 requests of up to 2,000 tokens = 33.6 GB. Working memory: 4 GB. Left: 80 - 14 - 33.6 - 4 = 28.4 GB, or 355 adapters. Cap the GPU cache at 250 adapters, 20 GB.

**Replicas.** Decode: 40 requests x 250 tokens = 10,000 output tokens per second. Assume a replica runs 32 requests at 40 ms per token merged, and 50 ms with unmerged adapters: 32 / 0.05 = 640 tokens per second. 10,000 / 640 = 15.6 GPUs. Prefill, the pass over the prompt: 40 x 750 = 30,000 tokens per second, at an assumed 8,000 per GPU: 3.8 GPUs. Total 19.4, so 26 replicas with 30% headroom.

**Placement.** Two owners per adapter: 10,000 placements / 26 = 385 adapters per replica, 31 GB of host RAM.

**Load times, assumed speeds.** Object store at 200 MB/s: 0.4 s. Local disk at 2 GB/s: 40 ms. Host RAM to GPU at 10 GB/s: 8 ms. The 14 GB base at 1 GB/s: 14 s.

**Cost.** At an assumed 2.5 USD per GPU-hour, 26 GPUs cost 65 USD per hour. 5,000 dedicated GPUs would cost 12,500 USD per hour.

## API

```
POST /v1/chat/completions
  body:   { model: "acme/support:prod", messages, max_tokens, stream: true }
  stream: token events
  headers: x-adapter-id, x-adapter-tier: gpu | ram | disk | remote

POST /internal/adapters                 (called by the fine-tuning pipeline)
  body: { adapter_id, version, base_model_hash, rank, alpha,
          target_modules, weights_uri, checksum }
PUT  /internal/aliases/{alias}          (deploy and rollback)
  body: { adapter_id }

POST /internal/replicas/{replica_id}/adapters/{adapter_id}/load     (pre-warm)
POST /internal/replicas/{replica_id}/adapters/{adapter_id}/unload
GET  /internal/replicas/{replica_id}/state
  -> { gpu_adapters[], ram_adapters[], queue_depth, tokens_in_flight,
       evictions_per_min }
```

## Data model

```
adapters(adapter_id PK, tenant_id, version, base_model_hash, rank, alpha,
         target_modules[], size_bytes, weights_uri, checksum, status)
aliases(alias PK, tenant_id, adapter_id, previous_adapter_id, updated_at)
placements(adapter_id, replica_id, role: owner | spill,
           tier: gpu | ram | disk, last_used_at)
adapter_stats(adapter_id, window_start, requests, tokens_per_s, gpu_hit_rate)

-- On each replica, for one adapted layer with weight W of shape [d, k].
-- S = GPU slots (250), r = largest allowed rank (16), n = rows in the batch.
A_stack  [S, r, k]        B_stack  [S, d, r]        scale [S]  = alpha / r
slots:   adapter_id -> { slot, ref_count, last_used }
batch:   x [n, k],  slot_of_row [n]
h = x W^T  +  scale[slot_of_row] * B_stack[slot_of_row] (A_stack[slot_of_row] x)
```

## High-level design

**Offline path (adapter lifecycle)**

1. The fine-tuning pipeline registers an adapter: weights file, rank, target modules and the hash of the base model it was trained on. The registry rejects a hash that does not match the served base, and a rank above the fleet's limit.
2. The control plane gives each adapter 2 owner replicas by rendezvous hashing: every replica gets a score from a hash of the adapter id and the replica id, and the top 2 win. Owners pull the file to local disk and host RAM. Adapters with steady traffic are also loaded into GPU memory.
3. An alias such as `acme/support:prod` maps to one adapter version. Changing the alias is how a deploy or a rollback happens.

**Online path (one request)**

4. The gateway authenticates the customer, resolves the alias to an adapter id and applies the customer's rate limit.
5. The router picks the owner with fewer tokens in flight. If both owners are overloaded, it spills to the least loaded replica.
6. On the replica, a request whose adapter is in the GPU cache joins the running batch at the next decode step. Otherwise it waits while a loader copies the adapter from RAM, disk or the object store into a GPU slot, evicting the least recently used idle adapter.
7. In each adapted layer the base output is computed once for the whole batch. Each row then adds its own adapter's output, selected by the row's slot index.
8. Tokens stream back. Every second the replica reports its loaded adapters, queue depth and tokens in flight to the router.
9. The autoscaler adds replicas on queue depth and tokens in flight. A new replica loads the base model first, then joins the router's replica list and warms its adapters.

## Architecture diagram

Rendering diagram…

## Deep dives

### Merged or unmerged

LoRA freezes each weight matrix W and learns two small matrices, B and A, of rank r. Merging adds (alpha / r) BA into W. The merged model runs at base speed, but it is a full 14 GB copy that serves one adapter, and its requests cannot share a batch with any other adapter. Unmerged serving keeps W shared and computes h = Wx + (alpha / r) B(Ax) for each request. The extra arithmetic is small: 131,072 multiply-adds per attention matrix against 16.8 million for W, under 1%. Measured overhead is higher because of the extra small operations and lookups, so load-test it. Use both modes: unmerged for the long tail, and dedicated merged replicas for a customer whose own traffic fills a replica, here more than 640 tokens per second.

### Batching requests that use different adapters

The base path ignores adapters: one matrix multiply covers all 32 rows. For the adapter path, stack the A and B matrices of every loaded adapter into two tensors, give each row its slot index, gather that row's A and B, and run one batched multiply. There is no loop over adapters. Ranks differ, and padding every slot to the largest rank wastes memory. A rank-64 adapter is 4 x 80 = 320 MB, so 250 slots sized for rank 64 would need 80 GB. Cap the allowed rank, or keep separate slot pools per rank.

### Routing to a replica that already holds the adapter

Under random routing, a replica caching 250 of 5,000 adapters holds the right one for 5% of evenly spread requests. Affinity routing fixes that. With rendezvous hashing, the top 2 replicas for an adapter id are its owners, and the router can compute them with no lookup table. Adding or removing a replica moves only about 1 in 26 placements. Hot adapters break pure hashing: a customer sending 2,000 tokens per second needs at least 4 replicas at 640 each. So the control plane raises the owner count with traffic.

### Cold starts and eviction

An adapter sits in one of four places: GPU (no wait), host RAM (8 ms), local disk (40 ms) or the object store (0.4 s). All are far cheaper than starting a replica, which pays the 14 s base load plus node start-up. So keep base replicas warm and let adapters move. Evict the least recently used adapter, and never one with running requests: keep a reference count. Watch for thrashing. When more than 250 adapters are active on one replica, each load evicts an adapter that is needed a moment later. The signal is evictions per minute, and the fix is more owners for those adapters or more replicas.

## Evaluation

**Correctness.** For a sample of adapters, compare unmerged outputs with a merged copy on the same prompts; logits should match within a small tolerance. Then check that a request gives the same tokens at temperature 0 whether it runs alone or in a batch with 31 other adapters.

**Isolation.** Train canary adapters that each emit a different marker string. Send 10,000 mixed requests and require zero markers from the wrong adapter. Run this in CI and as a production probe.

**Load test.** Replay prompts with real length distributions and a skewed adapter mix, where a few adapters carry most requests. Sweep the request rate and record p50 and p95 TTFT and time per output token, split by where the adapter was found: GPU, RAM, disk or object store. Also record throughput with 1, 8 and 32 distinct adapters in a batch, to measure the real unmerged overhead against the assumed 20%.

**Cache metrics.** GPU hit rate (target 95%), RAM hit rate, loads and evictions per minute per replica.

**Routing A/B.** Run the same replay with random routing and with affinity routing, and compare hit rate and p95 TTFT.

**Online.** The same metrics per customer, an alert when any customer's p95 TTFT passes the target, tokens per second per replica, and cost per million tokens. Answer quality for each adapter is checked when it is promoted; serving checks only that the base hash matches.

## Bottlenecks & mitigations

* The KV cache, not the adapters, takes the most GPU memory: 33.6 GB against 20 GB for 250 adapters. Longer contexts shrink the adapter cache.
* Unmerged overhead per decode step, assumed at 20% here, sets tokens per second per replica and so the fleet size.
* Traffic skew: one hot adapter can overload its 2 owners while the rest of the fleet is idle.
* Thrashing when the adapters active on a replica outnumber its GPU slots.
* Replica cold start. Loading the base model and starting a node limits how fast the fleet can grow.

## Failure modes

* **Wrong adapter applied.** A bug in the slot index gives one customer's request another customer's weights, which were trained on private data. Mitigation: the canary isolation test, and the adapter id checked at admission and logged on every request.
* **Adapter and base do not match.** An adapter trained on another base version loads without error and outputs degrade. Mitigation: base hash check at registration and at load.
* **Thrashing.** Loads and evictions chase each other and TTFT climbs. Mitigation: alert on evictions per minute, raise owner counts, add replicas.
* **Hot adapter overloads its owners.** Mitigation: owner count grows with traffic, spill to the least loaded replica, per-customer rate limits.
* **Adapter evicted while in use.** A running request loses its weights mid-generation. Mitigation: reference counts, and only idle adapters are evicted.
* **Stale version after an update.** One replica still serves version 6 after the alias moved to 7. Mitigation: versions are immutable ids, the alias is resolved only at the gateway, and old versions unload after their requests drain.
* **Corrupt or untrusted adapter file.** Mitigation: checksums, shape and rank checks, and loading only from the registry, never from a path supplied in a request.

## Follow-up questions interviewers ask

* One customer grows to 30% of all traffic. What changes for that adapter?
* Adapters arrive with ranks from 8 to 128. How do you manage GPU memory?
* Can a cached prompt prefix be reused across two different adapters? Why or why not?
* How does the design change if customers can choose between three base models?
* A request needs two adapters at once, one for style and one for domain. Can you serve it?
* A customer has been idle for a month. Where does its adapter live, and what TTFT does its next request get?

## Lessons that cover this

* [#9What is fine-tuning - LoRA, QLoRA, DoRABuild with LLMs](/ai/learn/fine-tuning-lora-qlora-dora)
* [#10Fine-tuning a model for a real use caseBuild with LLMs](/ai/learn/fine-tuning-real-use-case)
* [#11Inference and serving - KV cache, batching, vLLMServing](/ai/learn/inference-serving)

## Further reading

* [S-LoRA: Serving Thousands of Concurrent LoRA AdaptersPaperarxiv.org](https://arxiv.org/abs/2311.03285)
* [LoRA: Low-Rank Adaptation of Large Language ModelsPaperarxiv.org](https://arxiv.org/abs/2106.09685)
* [vLLM documentation: LoRA adaptersGuidedocs.vllm.ai](https://docs.vllm.ai/en/latest/features/lora.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousServe an open model to 1,000 concurrent users](/ai/problems/llm-serving-platform)[NextEmbedding service at scale](/ai/problems/embedding-service)

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
