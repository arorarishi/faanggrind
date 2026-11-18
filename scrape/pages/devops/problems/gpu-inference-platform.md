# GPU inference platform on EKS for OpenAI-compatible LLM serving — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/gpu-inference-platform

[DevOps problems](/devops#problems)

DESIGNPlatform design#18Hard

# GPU inference platform on EKS for OpenAI-compatible LLM serving

gpuvllmekskedaapi-gatewaymetering

## Problem statement

A company wants one internal LLM serving platform instead of every team renting GPUs on its own. It must expose an OpenAI-compatible API (chat completions with streaming) for 3 open models: a small 8B model that most teams use, a 32B model, and a 70B model used rarely. Peak load is 200 concurrent streaming requests. GPU nodes are expensive, and a batch of GPU servers sits on-premises behind NAT and must be used too. Design the platform on EKS: the GPU node pools, model serving, the gateway, the control plane for the on-premises nodes, autoscaling, metering and quotas.

## Requirements

### Functional

* `POST /v1/chat/completions` and `GET /v1/models` with the OpenAI request and response shape, including `stream: true` server-sent events, so existing SDKs work unchanged.
* Every request is authenticated with an API key or a JWT, routed to the right model, and counted: prompt tokens and completion tokens per request go to a usage ledger that bills a team's credit balance.
* Per-key limits: requests per minute, tokens per day, and concurrent streams; a key with no balance is refused before any GPU work starts.
* Cloud GPU nodes scale with demand; on-premises GPU nodes behind NAT join the platform by dialling out and are given work the same way.
* Models are pulled from S3 at startup, never baked into container images; rare models scale to zero and hot models keep a warm pool.
* Operators see time to first token, tokens per second, queue depth and GPU memory use per model, and can drain a node without failing in-flight streams.

### Non-functional

* Time to first token under 1 second at p50 and under 3 seconds at p95 for the 8B model at 200 concurrent streams.
* Steady output of at least 20 tokens per second per stream for the 8B model (faster than a person reads).
* A request waits in the gateway queue at most 30 seconds before it is rejected with 429 or 503, never silently dropped.
* Metering is exact: the ledger never under-counts a completed request and never double-debits a retried one, including when a stream is cut mid-way.
* GPU cost under 20,000 USD per month at the stated peak; idle cloud GPUs released within 10 minutes.
* No tenant can read another tenant's prompts, usage or keys; a single leaked key is bounded by its quota.

## Back-of-the-envelope estimates

**KV-cache memory, 8B model.** With 32 layers, 8 key-value heads, head size 128 and 16-bit values, the KV cache per token is 2 x 32 x 8 x 128 x 2 bytes = 131,072 bytes, 128 KiB. A 2,048-token context (prompt plus answer) needs 256 MiB; an 8,192-token context needs 1 GiB. An L40S GPU (g6e family) has 48 GB, about 44 GiB; vLLM takes 90 percent, 39.6 GiB. Weights in 16-bit take 15 GiB and activations about 2 GiB, leaving 22.6 GiB for KV cache: about 90 streams at 2k context, only 22 at 8k. Memory sets the batch size.

**GPUs for 200 streams.** Assume the split is 140 streams on 8B, 50 on 32B, 10 on 70B. Plan 32 streams per 8B replica for latency headroom: 140 / 32 = 4.4, so 6 replicas on 1 GPU each. The 32B model needs 2 GPUs per replica (64 GB of 16-bit weights) at 16 streams: 50 / 16 = 3.1, so 4 replicas, 8 GPUs. The 70B model in FP8 needs 4 GPUs per replica at 8 streams: 2 replicas, 8 GPUs. Peak total 22 GPUs; 8 of them are the on-premises nodes.

**Cost.** Assume 2.5 USD per GPU-hour for a cloud L40S. Peak is 14 cloud GPUs x 2.5 = 35 USD per hour; at an average of 8 cloud GPUs, 8 x 2.5 x 730 = 14,600 USD per month, under the 20,000 USD target.

**Cost per million tokens.** Assume an 8B replica produces 1,500 output tokens per second across its batch: 5.4 million tokens per hour, so 2.5 / 5.4 = 0.46 USD per million tokens at full load, about 0.93 USD at 50 percent utilisation. The 70B replica at 300 tokens per second on 4 GPUs costs 10 / 1.08 = 9.3 USD per million.

**Queue budget.** An 8B request with a 400-token answer at 47 tokens per second per stream takes about 8.5 seconds, so a 32-stream replica finishes about 3.8 requests per second, and a 30-second queue limit holds a burst of about 110 requests per replica.

## API

```
Gateway (Go), OpenAI-compatible, TLS at the edge
  POST /v1/chat/completions   Authorization: Bearer <api key or JWT>
        body: {model, messages, stream, max_tokens, ...}
        stream: true -> text/event-stream, "data: {...}" chunks, "data: [DONE]"
        headers back: x-request-id, x-ratelimit-remaining-requests, x-ratelimit-remaining-tokens
        429 rate limit or queue full (Retry-After), 402 no balance, 503 no healthy node
  GET  /v1/models              models the key is allowed to use
  GET  /v1/usage?from=&to=     tokens and cost per model for the key's team

Admin API (JWT with admin role)
  POST /admin/keys             {team, model_allowlist, rpm, tokens_per_day, max_streams, expires_at}
  POST /admin/credits          {team, amount}  -> ledger entry
  GET  /admin/nodes            registered nodes, models loaded, health, queue depth

Node control plane (on-premises and cloud GPU nodes)
  WSS /v1/nodes/connect        node dials out; first frame {node_id, token, gpus, models, version}
        server -> node: assign {request_id, model, body}, cancel {request_id}, load_model {name}, drain
        node -> server: chunk {request_id, delta}, done {request_id, prompt_tokens, completion_tokens},
                        heartbeat {queue_depth, kv_cache_usage, gpu_util} every 5 s

Inside a GPU node: vLLM listens on port 8000 and serves /v1/chat/completions, /health and /metrics
```

## Data model

```
EKS cluster "inference"
  Karpenter NodePools
    gpu-l40s      karpenter.k8s.aws/instance-family In [g6e], capacity-type on-demand,
                  taint nvidia.com/gpu=present:NoSchedule, limits nvidia.com/gpu: 16, consolidateAfter 10m
    gpu-l40s-spot same families, capacity-type spot, only for the 8B pool
    system        m6i, runs gateway, orchestrator, KEDA, DCGM exporter targets, Redis clients
  EKS AL2023 NVIDIA AMI: driver and container toolkit on the node; NVIDIA device plugin
                  installed separately (or GPU Operator with driver and toolkit disabled)

Deployments (one per model)
  vllm-8b    replicas 2..8,  resources nvidia.com/gpu: 1, args --max-model-len 8192 --max-num-seqs 64
  vllm-32b   replicas 1..5,  nvidia.com/gpu: 2, --tensor-parallel-size 2
  vllm-70b   replicas 0..3,  nvidia.com/gpu: 4, --tensor-parallel-size 4, KEDA scale to zero
  model cache: hostPath /models on local NVMe, filled from s3://models/<name>/<revision>/ by an init container

PostgreSQL (Aurora)
  teams(id, name, balance_microcredits)
  api_keys(id, team_id, hash, model_allowlist, rpm, tokens_per_day, max_streams, expires_at)
  usage_ledger(id, request_id UNIQUE, team_id, model, prompt_tokens, completion_tokens,
               cost_microcredits, status ENUM(reserved, settled, cancelled), created_at)
  nodes(id, location ENUM(cloud, onprem), gpus, models, last_seen, orchestrator_id)

Redis (ElastiCache)
  rl:{key_id}:rpm      sliding window counter, TTL 60 s
  streams:{key_id}     SET of active request ids, max_streams check
  node:{node_id}       HASH of last heartbeat, TTL 15 s; owner orchestrator id
  q:{model}            LIST of waiting request ids with enqueue time (gateway queue)
```

## High-level design

**Nodes and serving**

1. Create the EKS cluster with a system node pool and two Karpenter GPU NodePools (g6e on-demand, g6e spot) that carry the `nvidia.com/gpu` taint and a `nvidia.com/gpu` limit so a runaway scale-up cannot buy 100 GPUs. Use the EKS AL2023 NVIDIA AMI and install the NVIDIA device plugin; the GPU Operator is the alternative when you must manage drivers yourself.
2. Run one vLLM Deployment per model with `nvidia.com/gpu` requests, a toleration for the taint, `--max-model-len` and `--max-num-seqs` set from the KV-cache arithmetic, and a readiness probe on `/health` so a pod gets traffic only after the model is loaded.
3. An init container syncs the model from S3 to local NVMe and skips the copy when the revision is already there; a second pod on the same node starts in seconds instead of minutes.

**Gateway and control plane**

4. The Go gateway terminates TLS, verifies the API key hash or the JWT (JWKS cached), checks the model allowlist, the balance, the per-key rate limit and the concurrent stream count in Redis, then reserves a ledger row and enqueues the request for its model.
5. The orchestrator (several replicas) picks a node with free KV-cache for that model, forwards the request, and relays the stream back to the client. Cloud nodes are reached through their Service; on-premises nodes are reached over the WebSocket they opened to the orchestrator. Node ownership and heartbeats live in Redis so any orchestrator replica can route to any node.
6. When the stream ends, the orchestrator settles the ledger row with exact token counts and debits the team balance in one transaction.

**Scaling and operations**

7. KEDA scales each model Deployment on `vllm:num_requests_waiting` and `vllm:kv_cache_usage_perc` from Prometheus; the 70B model has `minReplicaCount: 0`, the 8B model keeps a warm floor. Karpenter adds GPU nodes when pods are pending and removes empty ones after `consolidateAfter`.
8. DCGM exporter on every GPU node and vLLM `/metrics` feed Prometheus; Grafana shows time to first token, tokens per second, queue depth and KV-cache use per model.
9. Draining a node sends `drain` over the control plane: no new assignments, in-flight streams finish, then the pod or machine is removed.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why GPU serving scales on memory and batching, not CPU

A decoding step for one request reads every weight once and produces one token. The GPU is nowhere near busy doing that; it is waiting on memory bandwidth. vLLM's continuous batching runs the decoding step for all active requests together, so one pass over the weights produces one token for each of 32 or 64 streams, and throughput grows almost linearly with batch size until compute saturates. The limit on batch size is KV-cache memory: every active token of every request keeps its keys and values in GPU memory, 128 KiB per token for the 8B model in the estimate above. That is why the sizing flags are `--max-model-len` (the longest context you allow) and `--max-num-seqs` (how many streams share the GPU), and why `--gpu-memory-utilization` matters more than CPU requests. Once the KV cache fills, vLLM preempts requests (`vllm:num_preemptions`) and time to first token jumps. The HPA on CPU is useless here; scale on `vllm:num_requests_waiting` and `vllm:kv_cache_usage_perc`.

### The control plane for nodes behind NAT

An on-premises node has no public address, so the orchestrator cannot connect to it. The node dials out instead: one WebSocket to `wss://.../v1/nodes/connect`, authenticated with a per-node token, then a register frame with its GPUs and loaded models. From then on the orchestrator sends assignments down the socket and the node sends chunks, completions and a heartbeat every 5 seconds. Three failure modes decide the design. Reconnect storms: when the orchestrator restarts, every node reconnects at once; nodes use exponential backoff with jitter (1 s, 2 s, 4 s, capped at 60 s) and the server limits registrations per second. Excessive heartbeat writes: 200 nodes writing to PostgreSQL every 5 seconds is 40 writes per second for no reason; heartbeats go to a Redis hash with a 15-second TTL and PostgreSQL stores only registration and drain events. Dead-node detection: a node whose Redis key expires is removed from routing; the orchestrator that owned its socket cancels its in-flight requests and the gateway retries them once on another node, but only if no chunk has been sent to the client yet. Multiple orchestrator replicas each own some sockets; a request for a node owned by another replica is forwarded through a Redis pub/sub channel keyed by node id.

### Metering that stays correct through streams and crashes

Billing has two steps so a crash in the middle cannot lose or double-count money. Before the GPU does anything the gateway inserts a ledger row with `status: reserved` and an estimated cost (prompt tokens, known from the tokenizer, plus `max_tokens`) and checks the balance against reservations in the same transaction. When the stream finishes, the orchestrator updates the same row to `settled` with the exact `prompt_tokens` and `completion_tokens` from vLLM's final usage chunk and debits the balance atomically: `UPDATE teams SET balance = balance - cost WHERE id = ? AND balance >= cost`. The `request_id` is unique, so a retried settle is a no-op. If the client disconnects mid-stream, the orchestrator cancels the request on the node and settles with the tokens produced so far; if the orchestrator itself crashes, a sweeper settles rows older than the maximum request time from the node's own completion log, or cancels them when the node never reported.

### Quota enforcement in the gateway

Limits are checked in the cheapest order: key validity and expiry from a local cache, then concurrent streams with `SADD` plus `SCARD` on `streams:{key}` (removed with `SREM` when the stream ends, and the set expires in case the gateway dies), then requests per minute with a sliding window counter in Redis, then tokens per day as a counter incremented at settle time and checked at admission. All of this costs a few Redis round trips and happens before any GPU work. Rejections return 429 with `Retry-After`, and a request that waits longer than 30 seconds in the model queue is removed and gets 503. Goroutine leaks are the usual bug in streaming gateways: every stream goroutine must be tied to the request `context`, and the cancel function must run on client disconnect, on node death and on timeout, otherwise the goroutine, its channel and the ledger reservation live forever. A `goroutines` gauge per gateway pod with an alert on steady growth catches this early.

## Evaluation

**SLIs.** Time to first token p50 and p95 per model (targets 1 s and 3 s for 8B); output tokens per second per stream (at least 20); gateway queue wait p95 (under 5 s) and the rate of 429 and 503 responses; KV-cache usage per replica (alert above 90 percent for 5 minutes); ledger drift, computed daily as settled tokens versus the sum of `vllm:generation_tokens` across replicas (target under 0.1 percent); idle GPU hours per week.

**Load and chaos tests.** Replay 200 concurrent streams with a 2k prompt and confirm the latency targets and that KEDA adds replicas before the queue limit is hit. Kill a vLLM pod mid-stream and confirm the client gets an error, not a hang, and the ledger settles the partial tokens. Cut the WebSocket of an on-premises node and confirm it reconnects with backoff, its requests are re-routed and no request is sent to it while it is dead. Restart all orchestrator replicas at once and watch for a reconnect storm. Run a client that opens 500 streams with one key and confirm `max_streams` holds.

**Cost review.** Weekly report of GPU hours per model against tokens served; cost per million tokens per model; alert when the 70B pool runs for more than 2 hours with an empty queue or when a GPU shows under 20 percent `DCGM_FI_PROF_GR_ENGINE_ACTIVE` for an hour.

**Security checks.** Keys stored as hashes and expire; JWT verification uses the JWKS endpoint with caching, not a shared secret; the gateway blocks requests whose body references internal URLs (SSRF through tool or image inputs); node tokens are per node and revocable; prompts are not logged; per-team queries in the usage API are scoped by the key's team id and tested with a second team's key.

## Bottlenecks & mitigations

* KV-cache memory on each GPU caps concurrency; long contexts cut the batch size by 4x and quietly destroy throughput.
* Model load time (tens of GB from S3) sets the scale-up latency; a cold 70B replica can take 5 to 10 minutes without a local cache.
* The orchestrator relays every stream chunk, so its network and goroutine count grow with concurrent streams; it must be horizontally scalable and stateless apart from socket ownership.
* Redis is in the path of every admission and heartbeat; a slow Redis means a slow gateway, so it needs its own alerting and a fail-closed policy for quotas.
* GPU capacity in one region or one instance family can be unavailable; Karpenter needs several allowed families and the on-premises pool as a floor.

## Failure modes

* **Reconnect storm after an orchestrator deploy.** Hundreds of nodes reconnect in the same second and the registration path falls over. Mitigation: jittered exponential backoff on nodes, a registration rate limit, and rolling restarts of orchestrator replicas.
* **Requests routed to an unresponsive node.** A node stops answering but still looks registered, and requests hang until the client gives up. Mitigation: heartbeat TTL in Redis, per-request timeouts on first token, remove the node after 2 missed heartbeats and retry once if nothing was streamed.
* **Goroutine and channel leak in streaming.** Memory of the gateway grows for days then it is OOM-killed under peak. Mitigation: every stream bound to a context with cancel on disconnect, timeout and node death; goroutine gauge alert; load test that opens and abandons streams.
* **KV cache full, preemptions rising.** Time to first token spikes although GPU utilisation looks fine. Mitigation: scale on `vllm:kv_cache_usage_perc` and waiting requests, cap `max_tokens` and context per key, lower `--max-num-seqs`.
* **Double debit on retry.** A retried settle charges a team twice. Mitigation: unique `request_id` in the ledger and an idempotent `UPDATE ... WHERE status = 'reserved'`.
* **Cross-tenant read in the usage API.** A key lists another team's usage. Mitigation: team id taken from the verified key, never from the request; a regression test with two teams.
* **Spot reclaim takes an 8B replica mid-stream.** Streams die with 2 minutes of warning. Mitigation: drain on the interruption notice, keep at least 2 on-demand replicas for the hot model.
* **Scale-to-zero cold start for the 70B model.** The first request waits 8 minutes and times out. Mitigation: local NVMe cache, a 503 with `Retry-After` while loading, and a schedule-based warm replica during office hours.

## Follow-up questions interviewers ask

* A team wants a fine-tuned variant of the 8B model. Do you load a LoRA adapter into the shared replicas or run a separate pool, and how does metering change?
* How would you use prefix caching for a team whose requests share a 3,000-token system prompt, and what does it do to your KV-cache arithmetic?
* Replace the home-grown orchestrator with KServe or Ray Serve. What do you gain, what do you lose, and what happens to the on-premises nodes?
* The 70B model is needed at 2 a.m. once a week for a batch job. How do you serve it without paying for warm GPUs?
* How do you upgrade vLLM across all pools without failing in-flight streams?
* A key is leaked on GitHub. What limits the damage in the first hour, and how do you rotate it?

## Lessons that cover this

* [#12AWS managed platforms - EKS, ECS, Fargate, Lambda, SQS, ElastiCache, CloudFrontCloud and IaC](/devops/learn/aws-managed-platforms-eks-ecs)
* [#30GPU and ML infrastructure - serving models on KubernetesLater](/devops/learn/gpu-and-ml-infrastructure)

## Further reading

* [vLLM documentationGuidedocs.vllm.ai](https://docs.vllm.ai/)
* [About the NVIDIA GPU OperatorGuidedocs.nvidia.com](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/index.html)
* [KEDA documentationGuidekeda.sh](https://keda.sh/docs/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousCut the AWS bill by 40 percent](/devops/problems/cloud-cost-reduction)[NextUptime monitoring service with global probes and alerting](/devops/problems/uptime-monitoring-service)

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
