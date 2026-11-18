# URL Shortener (TinyURL / bit.ly) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/url-shortener

[All system design questions](/system-design)

#1HLDEasyHigh-level design

# URL Shortener (TinyURL / bit.ly)

hashingkey-value storecachingread-heavy

## Problem statement

Design a service that takes a long URL and returns a short alias (e.g. `sho.rt/aB3xY9`). Visiting the alias redirects to the original URL. Aliases may optionally expire and users may request custom aliases.

## Requirements

### Functional

* Create a short URL for a given long URL; optional custom alias and optional expiry.
* Redirect a short URL to its long URL with an HTTP 301/302.
* Basic analytics: click count per short URL (nice-to-have).
* Delete or expire links.

### Non-functional

* Highly available — redirects must work even if creation is degraded.
* Low latency redirect (< 50 ms p99), since it sits in the user's critical path.
* Read-heavy: ~100 reads per write.
* Short codes must be unpredictable enough to prevent enumeration.
* Durable: a link must never resolve to the wrong target.

## Back-of-the-envelope estimates

* Writes: 100M new URLs/month → ~40 writes/s (peak ×10 = 400/s).
* Reads: 100:1 → ~4,000 reads/s, peak 40k/s.
* Storage: 100M/month × 5 years = 6B rows. ~500 bytes/row (long URL + metadata) → **3 TB**.
* Short-code space: base62, 7 chars → 62^7 ≈ 3.5 trillion, plenty.
* Cache: 20% of daily reads cover 80% of traffic → cache ~20% of hot links: 4k/s × 86,400 × 0.2 × 500 B ≈ 35 GB/day of hot data; a few Redis nodes.

## API

```
POST /v1/urls
  body: { longUrl, customAlias?, expiresAt? }
  → 201 { shortUrl, code, expiresAt }

GET /{code}
  → 302 Location: <longUrl>   (301 if you want browsers to cache; 302 keeps analytics)

DELETE /v1/urls/{code}   (auth required)
GET  /v1/urls/{code}/stats → { clicks, createdAt }
```

Use 302 by default: 301 is cached by browsers, so the redirect stops hitting your servers and you lose click analytics.

## Data model

```
urls
  code        VARCHAR(8)  PK   -- base62
  long_url    TEXT
  user_id     BIGINT
  created_at  TIMESTAMP
  expires_at  TIMESTAMP NULL
  clicks      BIGINT         -- or a separate counter store
```

Key-value store (DynamoDB / Cassandra) keyed by `code`. All lookups are by primary key; no joins.

## High-level design

1. **API gateway / load balancer** in front of stateless app servers.
2. **Write path**: generate a code, write `code → long_url` to the KV store, return.
3. **Read path**: look up `code` in Redis; on miss read the KV store, populate cache, 302 redirect.
4. **Code generation** — two sound options:
   * **Hash & truncate**: MD5/SHA of the long URL, take first 7 base62 chars, retry on collision. Simple but needs a collision check per write.
   * **Pre-generated key service (KGS)**: a service pre-mints unique random codes into a `unused_keys` table and hands them out; app servers grab batches of, say, 1,000 keys and keep them in memory. No collision checks, no DB round-trip per write.
   * Counter + base62 (via a range allocator like ZooKeeper/Flickr ticket server) is also fine but produces guessable sequential codes unless you shuffle/obfuscate.
5. **Analytics** — publish click events to Kafka; aggregate asynchronously. Never write to the primary DB on the read path.
6. **Expiry** — lazy delete on read (return 404 if expired) plus a periodic cleanup job.

## Architecture diagram

Rendering diagram…

## Deep dives

**Why KV instead of relational?** Single-key lookups, no relationships, need for horizontal partitioning — a wide-column or KV store partitioned on `code` scales linearly.

**Custom aliases**: treat as a conditional put (`INSERT IF NOT EXISTS`); return 409 on conflict.

**Caching strategy**: cache-aside with LRU; TTL matched to link expiry. Warm the cache from the previous day's top-N codes after a deploy.

**Redirect status**: 302 for analytics; 301 if you explicitly want to offload traffic to browser caches.

## Bottlenecks & mitigations

* Cache hot-spot: a viral link sends all reads to one Redis shard → replicate hot keys or use client-side caching with short TTL.
* KGS single point of failure → run KGS as a replicated service; each app server holds a local batch so brief KGS outages don't block writes.
* Analytics write amplification → never update `clicks` synchronously; batch through Kafka.

## Failure modes

* **Cache down**: reads fall through to the KV store; provision the DB for at least 30% of peak read load so a cache outage degrades latency, not availability.
* **KV partition unavailable**: use a store with multi-AZ replication (DynamoDB/Cassandra RF=3); reads with `ONE` consistency remain available.
* **Duplicate code issued** (KGS bug): detect with a conditional write; the second writer fails and retries with a new key.
* **Malicious/phishing links**: run URLs through a safe-browsing check on creation; allow reporting and takedown.

## Follow-up questions interviewers ask

* How would you support per-user link history and listing?
* How would you rate-limit creation to stop abuse?
* How would you geo-route redirects (different targets by country)?

## Further reading

* [Guide: URL shorteningIllustrated guide on this site](/system-design/learn/url-shortening)

[NextDistributed Rate Limiter](/system-design/rate-limiter)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftAtlassianAdobePayPal

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
