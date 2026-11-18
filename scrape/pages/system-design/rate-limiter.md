# Distributed Rate Limiter — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/rate-limiter

[All system design questions](/system-design)

#2HLDMediumHigh-level design

# Distributed Rate Limiter

token bucketsliding windowredismiddleware

## Problem statement

Design a rate limiter that caps how many requests a client (by user id, API key or IP) may make in a time window — e.g. 100 requests/minute — across a fleet of API servers, returning HTTP 429 when the limit is exceeded.

## Requirements

### Functional

* Limit requests per client per rule (e.g. 100/min, 1000/hour); rules configurable without redeploy.
* Return 429 with `Retry-After` and `X-RateLimit-Remaining` headers when limited.
* Support multiple dimensions: user, IP, API key, endpoint.
* Work across all API servers (distributed), not per-instance.

### Non-functional

* Adds < 2 ms p99 latency to each request.
* Highly available — if the limiter fails, decide explicitly between fail-open and fail-closed.
* Accurate enough: small over-admission at window edges is acceptable; systematic under-admission is not.
* Memory efficient: millions of clients tracked concurrently.

## Back-of-the-envelope estimates

* 10M active clients, 1 rule each; sliding-window-counter state ≈ 2 counters × 8 B + key ~40 B ≈ 60 B → **600 MB** in Redis.
* Peak 100k req/s → 100k Redis ops/s; a single Redis node handles ~100k simple ops/s, so shard by client key across a small cluster.
* Sliding-window **log** (store every timestamp) would be 100 req × 8 B = 800 B/client → 8 GB — too heavy; prefer counters.

## API

Rate limiting is middleware, not a public API, but the contract is the headers:

```
HTTP 200 / 429
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 37
X-RateLimit-Reset: 1717000000     (epoch seconds)
Retry-After: 12                   (only on 429)
```

Internal:

```
isAllowed(clientKey, ruleId) → { allowed: bool, remaining: int, retryAfterSec: int }
PUT /admin/rules/{ruleId}  { limit, windowSec, keyBy: "user|ip|apikey", scope: "/v1/search" }
```

## Data model

Rules live in a config store (etcd/DB) and are cached in every server. Counters live in Redis:

```
key:  rl:{ruleId}:{clientKey}:{windowStart}
val:  integer counter, TTL = 2 × window
```

For token bucket: `rl:{ruleId}:{clientKey}` → hash `{tokens, lastRefillTs}`.

## High-level design

**Algorithms**

* **Token bucket** — bucket of capacity `C` refilled at `r` tokens/s; each request takes one. Allows bursts up to `C`. Two numbers per client. Used by Stripe, AWS.
* **Fixed window counter** — `INCR` a counter per window. Cheapest, but allows 2× the limit at the window boundary.
* **Sliding window log** — store timestamps, count those inside the window. Exact but memory-heavy.
* **Sliding window counter** — weighted mix of current and previous fixed windows: `count = cur + prev × (1 − elapsed/window)`. Near-exact with 2 counters. Cloudflare's choice.

**Placement**: as middleware in the API gateway so every service gets it for free. The gateway calls Redis (co-located, same AZ) with a Lua script so read-check-increment is atomic.

**Rules**: pushed from the admin service to gateways via a config topic; gateways keep an in-memory copy and hot-reload.

## Architecture diagram

Rendering diagram…

## Deep dives

**Atomicity**: `GET` then `INCR` is a race across servers. Use a Lua script (`EVAL`) so the check-and-increment runs atomically inside Redis.

**Clock skew**: derive window boundaries from Redis `TIME`, not each server's clock.

**Local pre-check**: keep a small in-memory token bucket per client on each gateway as a first filter; only clients close to their limit hit Redis. Reduces Redis load 5–10× at the cost of slight over-admission.

**Fail-open vs fail-closed**: for public APIs fail-open (better a few extra requests than an outage); for login/OTP endpoints fail-closed.

## Bottlenecks & mitigations

* Redis becomes the single hot dependency → shard by client key, use Redis Cluster with replicas, and add the local pre-check.
* One abusive client hammering a single shard → hash the key to spread, and short-circuit at the gateway once a client is over limit (cache the 'blocked until' timestamp locally).
* Rule fan-out to thousands of gateways → push via pub/sub with versioning; gateways reject stale versions.

## Failure modes

* **Redis unreachable**: gateway falls back to local in-memory buckets (per instance, so effective limit becomes limit × instances) — acceptable fail-open behaviour; alert immediately.
* **Redis failover**: counters on the replica may lag by a few ms → brief over-admission, acceptable.
* **Thundering retry**: clients retrying instantly on 429 → return `Retry-After` and document exponential backoff; consider a tiny random jitter server-side.
* **Rule misconfiguration** (limit=0): validate rules and require a canary rollout.

## Follow-up questions interviewers ask

* How would you rate-limit by cost (weighted requests) rather than count?
* How would you implement a global limit shared across regions?
* How do you handle bursts — token bucket vs leaky bucket?

## Further reading

* [Guide: Rate limitingIllustrated guide on this site](/system-design/learn/rate-limiting)
* [Circuit Breaker pattern (Martin Fowler)Articlemartinfowler.com](https://martinfowler.com/bliki/CircuitBreaker.html)
* [Uber's leaky-bucket rate limiter (Go source)Codegithub.com](https://github.com/uber-go/ratelimit/blob/master/ratelimit.go)

[PreviousURL Shortener (TinyURL / bit.ly)](/system-design/url-shortener)[NextDistributed Cache (Redis / Memcached)](/system-design/distributed-cache)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AtlassianAmazonStripeUberMicrosoftSalesforce

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [High-level design](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Follow-ups](#follow-ups)
12. [Further reading](#reading)

## Your notes

Saved

Autosaves to this browser.
