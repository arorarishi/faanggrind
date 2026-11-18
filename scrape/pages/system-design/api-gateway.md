# API Gateway (auth, routing, rate limiting, observability) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/api-gateway

[All system design questions](/system-design)

#38HLDMediumHigh-level design

# API Gateway (auth, routing, rate limiting, observability)

reverse proxyauthenticationroutingresilience

## Problem statement

Design the single entry point for a company's public and internal APIs: TLS termination, authentication, routing to services, rate limiting, request/response transformation, retries/circuit breaking, and observability — without becoming a bottleneck or single point of failure.

## Requirements

### Functional

* Route requests by path/host/header to backend services with versioning.
* Authenticate (API keys, OAuth/JWT), authorise scopes.
* Rate limiting, quotas, IP allow/deny lists.
* Retries, timeouts, circuit breakers, canary routing.
* Logging, metrics, tracing; request/response transforms.

### Non-functional

* Adds < 5 ms p99; handles 500k RPS.
* Horizontally scalable, stateless data plane; no SPOF.
* Config changes propagate in seconds without restarts.
* Secure by default (TLS, header sanitisation).

## Back-of-the-envelope estimates

* 500k RPS; a well-tuned proxy node (Envoy/Nginx) does ~50–100k RPS → 10–20 nodes per region + headroom.
* Per-request work: TLS (offloaded/session resumption), JWT verify (~50 µs with cached keys), route match (trie), rate-limit check (local + Redis), forward.
* Logs: 500k RPS × 500 B = 250 MB/s → sample or ship asynchronously; never block the request path.

## API

Data plane: any HTTP/gRPC request. Control plane:

```
PUT  /admin/routes   { match:{ host, pathPrefix:"/v2/orders" }, upstream:"orders-svc", timeoutMs, retries, auth:["jwt"], rateLimit:{...} }
PUT  /admin/upstreams/{name}   { endpoints via service discovery, healthCheck, lb:"least_request" }
PUT  /admin/plugins/{route}    ordered filters
```

## Data model

Config store (etcd/DB): routes, upstreams, policies, API keys (hashed), JWKS cache. Runtime state on each node: compiled route table, connection pools, circuit-breaker state, local rate-limit buckets. Shared state: Redis for global rate limits and key revocation.

## High-level design

1. **Edge**: DNS/anycast → L4 load balancers → **gateway nodes** (Envoy-based) in each region; stateless.
2. **Filter chain per request**: TLS terminate → request id/tracing headers → auth (API key lookup in local cache; JWT verified with cached JWKS) → authz (scopes) → rate limit (local token bucket, then Redis for global) → route match → transform → upstream call with timeout/retry/circuit breaker → response transform → logging/metrics.
3. **Control plane**: an admin API writes config to a store; a config distributor pushes versioned snapshots to nodes (xDS-style). Nodes validate and hot-swap the route table atomically.
4. **Service discovery** integration for upstream endpoints; active + passive health checks; outlier ejection.
5. **Observability**: metrics per route/upstream, access logs sampled to a pipeline, distributed tracing headers propagated.
6. **Resilience**: per-route timeouts, retry budgets (not blind retries), circuit breakers per upstream, load shedding under overload (priority-based).

## Architecture diagram

Rendering diagram…

## Deep dives

**Retries are dangerous**: use retry budgets (≤ 10% extra load) and only on idempotent methods/errors; add jitter.

**Auth caching**: API keys validated against a local cache refreshed from the control plane; revocations pushed immediately.

**Config safety**: validate, canary to 1 node, then roll; keep the last N snapshots for rollback.

**Load shedding**: when CPU/queue thresholds trip, reject low-priority routes first (return 503 fast) to protect critical ones.

**gRPC/WebSocket**: pass-through support with proper timeouts (idle vs request).

## Bottlenecks & mitigations

* TLS handshakes → session resumption, TLS 1.3, offload to L4 where possible.
* Global rate-limit calls → local pre-check; batch/pipelined Redis.
* Log volume → async, sampled, aggregated.
* Route table size (10k routes) → trie/radix matching; compiled snapshots.

## Failure modes

* **Control plane down**: data plane keeps serving with the last config (must be fully decoupled).
* **Redis down**: rate limits fall back to local buckets (fail-open); alert.
* **Upstream slow**: circuit breaker opens; fast 503; retries stop; health checks bring it back gradually.
* **Gateway node crash**: L4 stops routing to it; connections re-established elsewhere.
* **Bad config push**: validation + canary + auto-rollback on error-rate spike.

## Follow-up questions interviewers ask

* How would you implement request coalescing/caching at the gateway?
* How would you support multi-tenant quotas and billing?
* Gateway vs service mesh — what belongs where?

[PreviousE-commerce Product Search (Amazon / Flipkart search)](/system-design/ecommerce-search)[NextRecommendation System (product / video recommendations)](/system-design/recommendation-system)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftAtlassianSalesforceStripe

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

## Your notes

Saved

Autosaves to this browser.
