# LLM gateway with routing, caching and fallback — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/llm-gateway

[AI problems](/ai#problems)

GENAIGenAI systems#4Hard

# LLM gateway with routing, caching and fallback

gatewayrate limitingfallbackstreamingbudgetsredaction

## Problem statement

A company has 400 internal services that call large language models. Today each service holds its own provider keys, so nobody can see total spend, one team's batch job can use up a shared provider quota, and a provider outage takes features down. Design one internal gateway that sits between these services and three hosted model providers plus a self-hosted vLLM pool. It serves 5 million requests a day, most of them streamed, and it must be more available than any single provider behind it.

## Requirements

### Functional

* One API for every model. Callers name an alias such as `chat-large`; the gateway maps it to an ordered list of provider deployments.
* Authenticate each call with a per-team virtual key, a key the gateway issues itself. Real provider keys never leave the gateway.
* Enforce limits per key in requests per minute and tokens per minute, and a monthly budget in USD per team.
* Retry and fall back to another deployment on failure, and charge the team exactly once per request.
* Pass streamed tokens through as they arrive, and return an exact-match cached response when a caller opts in.
* Record tokens, cost and latency for every attempt, and store prompts and outputs only after redaction.

### Non-functional

* The gateway adds under 20 ms at p95 before the upstream call, and forwards each streamed chunk within 5 ms.
* 300 requests per second at peak and about 3,200 open streams at once.
* 99.99% availability for the request path, while a single provider is assumed to offer 99.9%.
* A team may overshoot its monthly budget by at most 1%. Usage shows on the dashboard within 1 minute.
* Each `request_id` is charged at most once. Ledger cost matches provider invoices within 1% per month.
* No provider key and no raw personal data in logs. Redacted payloads are kept for 30 days.

## Back-of-the-envelope estimates

**Traffic.** 5,000,000 requests/day / 86,400 = 58 QPS on average. Internal traffic is bursty, so plan for 5 times that, about 300 QPS at peak.

**Tokens and spend.** An average request has 2,000 input and 400 output tokens. Per day: 10 billion input and 2 billion output tokens. At an assumed 1 USD and 5 USD per million, that is 10,000 + 10,000 = 20,000 USD/day, about 600,000 USD a month. One request costs 0.004 USD.

**Peak token rate.** 300 x 2,400 = 720,000 tokens per second, or 43.2 million tokens per minute. Provider quotas plus the self-hosted pool must add up to more than this, and the gateway has to share that total between teams.

**Open streams.** One response lasts an assumed 0.6 s to first token + 400 tokens x 25 ms = 10.6 s. 300 x 10.6 = about 3,200 concurrent streams. Assume one async gateway instance holds 2,000 streams (confirm with a load test). Two instances carry the peak; run 6 across 3 zones so that losing a zone still leaves 4.

**Limiter load.** One reserve and one settle per request = 600 operations per second at peak. One in-memory store handles that easily; its availability matters more than its speed.

**Logs.** 5,000,000 x 2,400 tokens x 4 bytes = 48 GB/day of payload text. With an assumed 5 times compression: 9.6 GB/day, 288 GB for 30 days. Ledger rows at 300 bytes: 1.5 GB/day.

**Why exactly-once matters.** If 1% of requests were blindly sent twice, that is 50,000 x 0.004 = 200 USD/day charged for nothing.

## API

```
POST /v1/chat/completions
  headers: Authorization: Bearer <virtual key>
           Idempotency-Key: <uuid>            (optional, kept 24 h)
  body:    { model: "chat-large",             (an alias, not a provider model)
             messages, max_tokens, stream?, cache?: "exact",
             metadata?: { feature, user_hash } }
  returns: JSON, or an SSE stream of { delta } events ending with
           { done, usage: { input_tokens, output_tokens, cost_usd },
             served_by, attempts }
  429:     { error: "rpm_exceeded" | "tpm_exceeded" | "budget_exceeded",
             retry_after_s }

POST /v1/embeddings                same auth, limits and ledger
GET  /v1/usage?team=&from=&to=&group_by=alias|feature|key

POST   /admin/keys     { team_id, rpm, tpm, allowed_aliases[] } -> key, shown once
DELETE /admin/keys/{key_id}
PUT    /admin/teams/{team_id}/budget  { monthly_usd, hard_cap, alert_at: [0.5, 0.8, 1.0] }
PUT    /admin/routes/{alias}
       { targets: [{ deployment_id, priority, weight }],
         ttft_timeout_ms, total_timeout_ms, max_attempts }
```

## Data model

```
-- config store (relational), cached in every gateway instance
teams(team_id PK, name, monthly_budget_usd, hard_cap, alert_at[])
api_keys(key_id PK, key_hash, team_id FK, rpm, tpm,
         allowed_aliases[], status, expires_at)
deployments(deployment_id PK, provider, model, region, secret_ref,
            usd_in_per_m, usd_out_per_m, tpm_quota, status)
routes(alias PK, targets[{deployment_id, priority, weight}],
       ttft_timeout_ms, total_timeout_ms, max_attempts, version)

-- usage ledger (append only), one row per attempt
usage_ledger(request_id, attempt_no, team_id, key_id, alias, deployment_id,
             tokens_in, tokens_out, cached_tokens, cost_usd, billed BOOL,
             status, ttft_ms, total_ms, started_at)
             PK (request_id, attempt_no)
request_logs(request_id, redacted_prompt_uri, redacted_output_uri,
             redaction_counts, expires_at)

-- in-memory store, replicated
rl:{key_id}:rpm            bucket of requests, refilled every second
rl:{key_id}:tpm            bucket of tokens, refilled every second
budget:{team_id}:{yyyymm}  spent_usd, reserved_usd
breaker:{deployment_id}    state, error window, opened_at
idem:{team_id}:{key}       request_id, status, result_ref   (TTL 24 h)
cache:{team_id}:{sha256 of model + messages + params}       (TTL per alias)
```

## High-level design

**Control plane (slow path)**

1. Admins create teams, virtual keys, budgets and routes in a config store. Provider keys sit in a secret manager, and only the gateway's service account can read them.
2. Every gateway instance pulls config changes and keeps the full config in memory. If the config store is down, instances keep serving with the last copy they have.

**Data plane (every request)**

3. A load balancer sends the call to any gateway instance. Instances hold no state of their own.
4. Auth: hash the virtual key and look it up in the local cache. Check that the alias is allowed for this key.
5. Admission: estimate the input tokens from the prompt size, add `max_tokens`, and reserve that amount against the key's request bucket, token bucket and the team budget in one atomic call to the in-memory store. If any limit fails, return 429 with `retry_after_s`.
6. If the caller asked for the exact cache, look up the hash of model, messages and parameters under the team's namespace. A hit returns at once, releases the reservation and costs nothing.
7. Routing: resolve the alias to its targets, skip any deployment whose circuit breaker is open (a switch that stops traffic to a target that keeps failing), and pick by priority, then weight.
8. An adapter translates the request into that provider's format, attaches the provider key and sends it. Streamed chunks are translated back to one format, server-sent events (SSE), and flushed to the caller as they arrive.
9. If the attempt fails before the first token, the gateway tries the next target. After the first token it does not switch silently.
10. Settle: read the real token counts from the provider's final chunk, return unused reserved tokens to the bucket, add the cost to the budget and append one ledger row per attempt.
11. Publish a log event to a queue. Workers redact the prompt and output and store them. Metrics go out per team, alias and deployment.

## Sequence diagram

Rendering diagram…

## Deep dives

### Limits and budgets counted in tokens

A request limit alone is unfair: a 200,000-token prompt and a 50-token prompt each count as one. So every key has two buckets, one that counts requests per minute and one that counts tokens per minute (TPM). A bucket holds up to its limit and refills at limit / 60 per second.

The problem is that output length is unknown at admission. The gateway reserves, then settles. A call with 6,000 input tokens and `max_tokens` 2,000 reserves 8,000. If it ends after 350 output tokens, settle returns 1,650 to the bucket. Reserve and settle each run as one atomic script in the in-memory store, so two instances cannot both spend the last tokens.

TPM protects capacity. The monthly budget protects money, and it uses the same reserve-then-settle step in USD with the price of the chosen deployment. Reservations bound the overshoot to the requests in flight. Send alerts at 50%, 80% and 100%, and let each team choose a hard cap or alert only.

### Fallback and retries without double billing

Sort errors first. Timeouts, 429 and 5xx can succeed elsewhere. A 400 or a content-policy refusal will fail everywhere, so return it. A provider 401 means the gateway's own key is bad: fall back and alert.

Before the first token, fallback is safe: nothing reached the caller. Use a short time-to-first-token timeout, close the upstream connection so the provider stops generating, and try the next target. Each attempt gets a ledger row under the same `request_id`, and only the attempt that delivered the answer is marked `billed`. A provider may still invoice a timed-out attempt; that cost goes to a platform account, and its rate is an alert.

After the first token, a second model cannot continue the same sentence. Send an error event, charge the partial tokens, and let the caller decide.

Callers retry too. The idempotency key, a unique id the caller sends with each logical request, maps a repeated call to the stored `request_id`: the gateway attaches it to the running attempt or returns the stored result, and does not generate again.

A circuit breaker opens when a deployment's error rate passes 50% over 20 seconds and probes again after 30 seconds. A retry budget caps retries at 10% of traffic, so a slow provider does not receive double load.

### Streaming pass-through

The gateway must not buffer. It reads a chunk, translates it, writes it and flushes. It estimates output tokens as they pass, which gives the settle step a number even when a stream breaks before the usage chunk.

If the caller disconnects, cancel the upstream call at once, or the team pays for tokens nobody reads. Streams last about 10 seconds and some last minutes, so a deploy stops new requests on an instance and waits for open streams to drain before it exits. A slow caller applies backpressure: when the small write buffer is full, the gateway stops reading from the provider, so memory per stream stays bounded.

### Logging with redaction

The ledger row (ids, tokens, cost, latency) is written for every attempt and holds no text. Payloads are different: prompts contain customer data and sometimes secrets. Redaction runs in async workers, off the request path. Patterns and checksums catch emails, phone numbers, card numbers and API keys, and a named-entity model catches names. Each value becomes a typed placeholder such as `<EMAIL_1>`. Teams with regulated data can turn payload logging off, and everything else expires after 30 days.

### Keeping the gateway itself available

Every call now depends on the gateway, so it needs fewer hard dependencies than its callers. Instances are stateless and spread over 3 zones. Config is cached in memory. If the limiter store is down, the gateway fails open: each instance enforces limit / 6 locally and budgets are rebuilt from the ledger later. Ledger and log writes go through a local buffer and a queue, so a slow database never blocks a request.

Fallback is what buys the extra nines. If two providers are each up 99.9% of the time and fail independently, both are down together 0.1% x 0.1% = 0.0001% of the time.

## Evaluation

A gateway has no answer quality of its own, so most of the evaluation is correctness under failure.

**Offline, limits.** Fire 1,000 concurrent requests at one key from several instances and assert that admitted tokens never pass the TPM limit, and that settle returns every unused reserved token. Repeat with the limiter store killed halfway.

**Offline, fault injection.** A fake provider returns 429s, 503s, slow first tokens and streams that stop midway. For each case assert three things: the caller got one answer or one clear error, the ledger has one `billed` row for each answered request and none for a failed one, and the breaker opened and closed at the expected times.

**Offline, redaction.** A labelled set of 2,000 payloads with planted emails, card numbers, names and API keys. Track recall (target 0.99 for structured values) and the false-redaction rate, because over-masking makes logs useless for debugging.

**Fallback quality.** A fallback model answers differently. Run each team's eval set against every target of an alias before the route ships, so the quality drop during an outage is a known number.

**Online.** Added latency at p95, time to forward a chunk, client-seen error rate against upstream error rate (the gap is what the gateway buys), fallback rate, 429 rate per team, budget overshoot, cache hit rate, and a daily reconciliation of ledger cost against provider invoices.

**Rollout.** New gateway builds take 1% of traffic first. Route changes move by weight, 5% then 50% then 100%, with automatic rollback when the error rate rises.

## Bottlenecks & mitigations

* The limiter store sits on the hot path: every request makes two atomic calls, so its latency and uptime bound the gateway's.
* About 3,200 long-lived streams pin connections and memory, and they make deploys and zone failover slow.
* Counting input tokens for a 100,000-token prompt costs CPU on every request. Estimate from bytes at admission and correct at settle.
* Provider TPM quotas, not the gateway, cap total capacity at peak (43.2 million tokens per minute needed).
* The redaction workers must process 48 GB of text a day; a backlog delays logs but must never slow requests.

## Failure modes

* **A provider returns errors for ten minutes.** An outage or an exhausted quota. Mitigation: per-deployment circuit breaker, fallback to the next target, and an alert on fallback rate.
* **Retry storm.** Callers and the gateway both retry a slow provider and triple its load. Mitigation: a 10% retry budget, exponential backoff with jitter, and honouring the provider's `Retry-After`.
* **A request is charged twice.** The caller times out and resends while the first call is still running. Mitigation: idempotency keys, one `billed` row per `request_id`, and daily invoice reconciliation.
* **The limiter store is down.** No shared counters. Mitigation: fail open with local per-instance limits, then rebuild budgets from the ledger.
* **One team's batch job starves interactive traffic.** It fills the provider quota that everyone shares. Mitigation: per-key TPM, a lower priority class for batch, and a reserved share of each deployment for interactive aliases.
* **A stream stops midway.** The provider drops the connection after 200 tokens. Mitigation: an idle timeout between chunks, an error event to the caller, and partial tokens charged from the gateway's own count.
* **A bad route is pushed.** An alias points at a model that rejects the request format. Mitigation: versioned config, validation with a test call, weighted rollout and one-step rollback.
* **Secrets end up in logs.** A caller pastes an API key into a prompt. Mitigation: redact before any payload is stored, restrict who can read payloads, and expire them after 30 days.

## Follow-up questions interviewers ask

* One provider gives your account 10 million TPM. How do you split it fairly between 400 services?
* How would you add a semantic cache without one team ever seeing another team's answer?
* A stream returns 200 and then stalls after 50 tokens. How do you detect it, and what does the caller see?
* The gateway now runs in three regions. Where does the limiter state live, and how exact do the limits stay?
* The self-hosted pool is full. Do you queue, reject, or spill over to a hosted provider, and who pays?
* A team wants to bring its own provider key. What changes in auth, limits and the ledger?

## Lessons that cover this

* [#11Inference and serving - KV cache, batching, vLLMServing](/ai/learn/inference-serving)
* [#24LLMs on cloud - Bedrock, Azure OpenAI, Vertex AILater](/ai/learn/llms-on-cloud)

## Further reading

* [vLLM documentationGuidedocs.vllm.ai](https://docs.vllm.ai/)
* [OpenTelemetry documentationGuideopentelemetry.io](https://opentelemetry.io/docs/)
* [Python asyncio documentationGuidedocs.python.org](https://docs.python.org/3/library/asyncio.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAgentic research assistant with multi-step retrieval](/ai/problems/agentic-research-assistant)[NextSemantic cache for LLM responses](/ai/problems/semantic-cache)

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
