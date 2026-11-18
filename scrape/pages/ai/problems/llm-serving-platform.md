# Serve an open model to 1,000 concurrent users — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/llm-serving-platform

[AI problems](/ai#problems)

MLSDML system design#24Hard

# Serve an open model to 1,000 concurrent users

model servingautoscalingroutingquantizationmulti-tenantrolloutReported at Anthropic, Scale AI

## Problem statement

Design a platform that serves open models to many product teams through one API, on the company's own GPUs. The main model is a 7B chat model that must carry 1,000 concurrent streaming users at peak. A 70B model takes harder, low-volume requests, and more models will follow. The teams share the GPUs, so the platform needs per-team limits and priority tiers. It must also scale with load, roll out a new model version without an outage, and survive the loss of a region.

## Requirements

### Functional

* One streaming chat API for every model in the catalogue. A team picks a model by name and the platform picks the version and the replica.
* Per-team API keys with token limits and three priority tiers: interactive, standard and batch.
* Route each request to a healthy replica of the right version, preferring a replica that already holds the prompt's prefix in its cache.
* Scale every model pool up and down with load, and keep a warm minimum.
* Roll out a new model version through shadow traffic and a canary, with automatic rollback.
* Fail over to a second region, and meter token usage per team.

### Non-functional

* 1,000 concurrent streams on the 7B model at peak, each at 30 tokens per second or more.
* p95 time to first token (TTFT) under 1 second for the interactive tier. Batch requests may wait up to 1 hour.
* 99.9% availability for the interactive tier, including the loss of one of the 2 regions at peak.
* A new replica serves traffic within 6 minutes on a fresh node, and within 1 minute on a node that already has the weights on disk.
* Rolling back a bad model version takes under 1 minute.
* GPU cost is reported per pool in USD per million tokens, with a target of at least 50% utilisation at peak.

## Back-of-the-envelope estimates

**What "concurrent" means.** Here: 1,000 answers streaming at once. One answer lasts 0.5 s + 300 tokens at 30 per second, about 10.5 s. With 1,000 logged-in users each sending a message every 40 s, only 10.5 / 40 = 26% would be streaming: a fleet 4 times smaller. Ask.

**Tokens per second.** 1,000 streams x 30 = 30,000 output tokens per second. At 300 tokens per answer: 100 requests per second.

**Replicas, 7B.** A replica is one model server: 14 GB of FP16 weights on an 80 GB GPU. Assume 2,500 output tokens per second per replica: 83 streams at 30 each. The one-GPU batching problem assumes 800 at 32 rows. Here grouped-query attention (8 KV heads, not 32) makes each row's KV cache 4 times smaller, and the batch is larger. Both are assumptions; a load test with real prompts replaces them. 30,000 / 2,500 = 12 replicas.

**Prefill.** The pass over the prompt: 100 requests x 1,200 prompt tokens = 120,000 prompt tokens per second. If 800 of the 1,200 are a prefix cached on the replica, and routing finds it 80% of the time: 100 x (1,200 - 0.8 x 800) = 56,000, less than half.

**Replicas, 70B.** FP16 weights are 140 GB, leaving 20 GB on 2 GPUs. INT8 weights are 70 GB, leaving 90 GB. Peak: 60 streams x 20 tokens per second = 1,200. At an assumed 400 per replica: 3 replicas.

**Two regions.** Each region must carry the whole peak alone: 12 chat replicas and 3 of the 70B. Total: 24 + 6 x 2 = 36 GPUs. Normally each region runs at half load: that is the headroom.

**Cost.** At an assumed 2.50 USD per GPU-hour: 36 x 2.50 x 720 = 64,800 USD per month. A chat replica makes 2,500 x 3,600 = 9 million tokens per hour: 0.28 USD per million when full, 0.56 when half busy.

## API

```
POST /v1/chat/completions
  headers: Authorization: Bearer <team key>
           x-priority: interactive | standard | batch
           x-conversation-id: <id>            optional, used as the routing key
  body:   { model: "chat-7b" | "reason-70b" | "chat-7b@v13",
            messages, max_tokens, temperature, stream: true }
  stream: token events, then
          { usage: { prompt_tokens, cached_tokens, completion_tokens },
            model_version, region, replica_id }
  errors: 429  team is over its token limit; Retry-After
          503  pool overloaded and this tier was shed; Retry-After

POST /v1/batches      { model, input_uri, output_uri, deadline } -> { batch_id }
GET  /v1/batches/{batch_id}

-- control plane
POST /admin/models/{model}/versions
     { weights_uri, weights_hash, tokenizer_hash, chat_template,
       precision, gpus_per_replica, engine_config }
PUT  /admin/models/{model}/rollout   { version, stage: shadow | canary, percent }
PUT  /admin/models/{model}/alias     { version }        promote or roll back
PUT  /admin/teams/{team}/limits
     { model, tokens_per_minute, max_concurrency, guaranteed_share }
GET  /admin/pools/{model}/state
     -> { replicas[], queue_depth, tokens_in_flight, prefix_hit_rate }
```

## Data model

```
models(model PK, live_version, canary_version, canary_percent)
model_versions(model, version PK, weights_uri, weights_hash, tokenizer_hash,
               chat_template_hash, precision: fp16 | int8 | 4bit,
               gpus_per_replica, engine_config, eval_report_uri,
               load_test_tokens_per_s, load_test_tokens_in_flight, status)
pools(model, version, region, min_replicas, max_replicas)
replicas(replica_id PK, model, version, region, node,
         state: starting | loading | serving | draining,
         queue_depth, tokens_in_flight, last_heartbeat)

teams(team PK, name)
team_limits(team, model, tokens_per_minute, max_concurrency, guaranteed_share)
usage(team, model, version, minute, prompt_tokens, cached_tokens,
      output_tokens, requests, shed)
rollouts(model, version, stage, percent, started_at, guard_metrics, decision)

Router state, in memory, one copy per region:
  ring[model@version]    replicas on a consistent-hash ring
  load[replica_id]       tokens_in_flight and queue_depth, refreshed every second
  bucket[team, model]    tokens left in this minute
```

## High-level design

**Offline path (life of a model version)**

1. A team registers a version: weights, tokenizer, chat template, precision and engine settings, each stored with a hash. A version never changes after that.
2. A gate runs the quality eval set and a load test. The measured tokens per second per replica, and the tokens in flight at that point, are saved with the version. The autoscaler uses them as that version's capacity.
3. The weights are copied to object storage in both regions and pulled onto the local disks of the GPU nodes ahead of time.
4. The version goes out in stages: shadow traffic, then a canary at 1%, 10% and 50%, then the model name is pointed at it. The old version stays loaded for 24 hours.

**Online path (one request)**

5. A global load balancer sends the request to the nearest healthy region.
6. The gateway checks the team key, reads the priority tier, and charges the team's token bucket with prompt tokens plus max tokens. Unused tokens are refunded when the answer ends.
7. The router turns the model name into a version, then picks a replica by consistent hashing on the conversation id. If that replica is overloaded, it takes the next one on the ring.
8. The replica runs an inference engine: vLLM by default, or SGLang where requests share long prefixes. The engine batches requests continuously and manages the KV cache, the stored attention keys and values of past tokens. Its prefix cache keeps that state for a prompt's opening tokens, so a later request that starts the same way skips prefill for them. Tokens stream back through the gateway.
9. Every second each replica reports its queue depth and tokens in flight to the router and the autoscaler.
10. When a pool is full, interactive requests queue first in line, standard requests behind them, and batch requests run only on idle capacity. Past the queue limit the lowest tier is shed with a 503.
11. The autoscaler adds replicas when tokens in flight pass 70% of measured capacity, and removes them slowly.
12. Usage records go to metering, one row per team, model and minute.

## Architecture diagram

Rendering diagram…

## Deep dives

### Routing: tokens in flight and a warm prefix

Round-robin fails in two ways. Requests differ in size by 100 times, so balance on tokens in flight, meaning prompt plus remaining output tokens of everything a replica holds, not on connections. And a prefix cache lives in one replica's GPU memory. With 12 replicas, round-robin sends the next turn of a conversation to the replica that holds its history 1 time in 12. Consistent hashing on the conversation id sends it there unless that replica is overloaded or gone. That is where the assumed 80% hit rate comes from, and it cuts prefill from 120,000 to 56,000 tokens per second. Affinity and balance pull against each other, so bound the load: skip a replica whose tokens in flight are above 125% of the pool average. Adding a replica moves only about 1 key in 13.

### Autoscaling and cold starts

CPU stays idle while the GPU is saturated, and GPU utilisation reads high at any batch size. So scale on tokens in flight against the load-tested capacity, with queue depth as the fast trigger. The cold-start sum, with assumed speeds: node start 4 minutes, 14 GB of weights at 0.5 GB per second 28 s, load into GPU memory at 1 GB per second 14 s, warm-up 30 s. That is about 5 minutes, so plan for 6. If load grows 5% a minute, 6 minutes multiplies it by 1.05^6 = 1.34. Scaling at 70% leaves 0.70 x 1.34 = 0.94 of capacity in use when the replica arrives: just enough. A running node with the weights on its disk needs only the last two steps, under a minute, so keep a few warm. Scale down one replica per 10 minutes, after its streams drain.

### Precision is chosen per model

Quantization, storing weights in fewer bits, is a capacity decision that an eval must approve. The 7B model fits in FP16 with room to spare. Its weights are 14 GB, and with 8 KV heads (grouped-query attention) its cache is 2 x 32 layers x 8 x 128 x 2 bytes = 131,072 bytes per token, so 83 streams of 1,500 tokens hold 16 GB. Quantizing it would only risk quality. The 70B model does not fit on one GPU, so a replica splits every layer across GPUs (tensor parallelism). FP16 needs 4 GPUs per replica to have a useful cache (320 - 140 = 180 GB); the usual 32 or 64 attention heads cannot be split evenly over 3 GPUs. INT8 on 2 GPUs leaves 90 GB and halves the cost. 4-bit fits on 1 GPU (80 - 35 = 45 GB), but this is the reasoning model, and 4-bit can hurt reasoning, maths and long outputs. Ship INT8 only if the team's own eval set shows no real drop. Precision is part of the version, so changing it is a full rollout. Quantized weights do not shrink the KV cache.

### Priority tiers and team limits

Limit tokens per minute, not requests, because one request can cost 100 times another. Each team gets a guaranteed share of every pool and may burst into idle capacity. Under overload the order is fixed: batch pauses first, then teams above their guaranteed share get a 429, then standard requests queue. Interactive traffic inside a guarantee is never shed. The batch tier also pays for the fleet: it fills the idle half, which moves the cost from 0.56 towards 0.28 USD per million tokens.

### Rollout and region loss

A new version can be worse without raising any error. Shadow mode copies 1% of requests to it and discards the output, to compare latency and judge scores. The canary is split by conversation id, so a chat never changes version halfway, and canary replicas are extra capacity on top of the pool. Guard metrics (error rate, p95 TTFT, output length, refusal rate) trigger rollback, which is one alias change because the old version is still loaded. When a region fails, the load balancer moves traffic. Open streams break and clients retry, which is safe because every request carries its full history. The survivor is at 100% with cold prefix caches, so it sheds batch and scales up.

## Evaluation

**Capacity per version.** Before a version is promoted, replay logged prompts at a fixed arrival rate and raise the rate step by step. The highest output tokens per second at which p95 TTFT stays under 1 second and streams keep 30 tokens per second replaces the assumed 2,500. The number matters: at 800, the figure assumed in the one-GPU batching problem, the same peak needs 38 replicas, not 12. Replay with the real prefix hit rate as well: at an assumed 10,000 prompt tokens per second per GPU, the 56,000 uncached prompt tokens are 5.6 GPUs of prefill work that an output-token count hides.

**Quality gate.** Score the new and the current version on the same prompts with task metrics and an LLM judge, and check the judge against human labels. For a precision change, compare FP16, INT8 and 4-bit on the team's own eval set, with separate scores for reasoning, maths and long outputs.

**Routing A/B.** Run one replay three times: round-robin, least tokens in flight, and prefix affinity with bounded load. Compare prefix hit rate, p95 TTFT and imbalance (highest tokens in flight divided by the pool average).

**Autoscaling drill.** Replay a ramp of 5% per minute and a sudden doubling. Record time until new capacity serves, peak queue depth, requests shed per tier and minutes outside the TTFT target.

**Isolation test.** One team sends 10 times its limit. Every other team's p95 TTFT must not move, and only the noisy team may see 429s.

**Canary rules.** Roll back automatically if, against the live version, the error rate rises by more than 0.5 points, p95 TTFT rises by more than 20%, or average output length shifts by more than 15%. These thresholds are starting values to tune.

**Failover game day.** Drain one region at peak every quarter. Measure the time until errors stop, interactive TTFT during the shift, and how much batch work was delayed.

**Online.** Per pool: tokens per second, tokens in flight, queue depth, p95 and p99 TTFT, time per output token, prefix hit rate, utilisation and USD per million tokens. Per team: tokens used, 429s and shed requests.

## Bottlenecks & mitigations

* Cold start. Capacity cannot arrive faster than about 5 minutes on a fresh node, and GPU nodes may not be available at all during a regional shortage.
* Prefill for long prompts. It is 120,000 tokens per second before caching, 4 times the output rate, and it depends on the prefix hit rate.
* The 70B pool. With 3 replicas of 2 GPUs each, one failed GPU removes a third of the pool.
* A hot routing key. Affinity can send one busy team's traffic to the same few replicas while the others idle.
* Idle cost. Sizing each region for the full peak means the fleet is at most 50% busy in normal times.

## Failure modes

* **The autoscaler lags a spike.** Traffic doubles in a minute and new replicas need 5. Mitigation: a warm minimum, the 70% threshold, weights on local disk, scheduled scale-up before known peaks, and shedding the batch tier first.
* **A bad model version reaches every user.** A wrong chat template lowers quality and no error is raised. Mitigation: hashed versions, the eval gate, shadow traffic, a canary with guard metrics, and rollback by alias.
* **One team starves the others.** A runaway script fills the pool. Mitigation: token buckets per team, concurrency caps and guaranteed shares.
* **A region is lost at peak.** Mitigation: each region sized for the full peak, health-checked global routing, batch shed on the survivor, and a failover drill every quarter.
* **A replica dies mid-stream.** A GPU error kills up to 83 streams (2,500 / 30). Mitigation: heartbeats every second, removal from the ring after 3 missed beats, an automatic retry on another replica only if no token was sent yet, and an explicit error event otherwise.
* **Retry storm.** Shed requests come straight back and multiply the load. Mitigation: Retry-After on every 429 and 503, client backoff with jitter, and a retry budget in the gateway.
* **The control plane is down.** The registry or rollout service fails. Mitigation: gateways and routers keep serving from the last configuration they received. Only rollouts and limit changes wait.

## Follow-up questions interviewers ask

* The peak lasts 4 hours a day. How do you cut the bill for the other 20 without breaking the 6-minute scale-up rule?
* 500 teams each want their own fine-tuned variant of the 7B model. What changes?
* A team starts sending 30,000-token prompts. What happens to capacity, routing and that team's limits?
* A team's token limit must hold across both regions. Where does the counter live, and what happens during failover?
* No more GPUs are available in a region. What is your order of fallbacks?
* For the 70B model, compare one FP16 replica on 4 GPUs with two INT8 replicas on 2 GPUs each.

## Lessons that cover this

* [#6Hugging Face end to endFoundations](/ai/learn/hugging-face-end-to-end)
* [#11Inference and serving - KV cache, batching, vLLMServing](/ai/learn/inference-serving)
* [#17LLM system designShip](/ai/learn/llm-system-design)
* [#18What is new in 2026 + revisionShip](/ai/learn/whats-new-2026-revision)
* [#19Attention variations - GQA, MLALater](/ai/learn/attention-variations-gqa-mla)
* [#24LLMs on cloud - Bedrock, Azure OpenAI, Vertex AILater](/ai/learn/llms-on-cloud)

## Further reading

* [vLLM documentationGuidedocs.vllm.ai](https://docs.vllm.ai/)
* [SGLang documentationGuidedocs.sglang.ai](https://docs.sglang.ai/)
* [AWQ: Activation-aware Weight QuantizationPaperarxiv.org](https://arxiv.org/abs/2306.00978)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousInference batching system for one GPU](/ai/problems/llm-inference-batching)[NextMulti-tenant LoRA adapter serving](/ai/problems/multi-lora-serving)

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
