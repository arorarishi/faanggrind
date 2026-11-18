# Pastebin / Text Sharing Service — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/pastebin

[All system design questions](/system-design)

#36HLDEasyHigh-level design

# Pastebin / Text Sharing Service

object storagekey generationexpiryread-heavy

## Problem statement

Design a service where users paste text (up to a few MB), get a short URL, and others can read it; pastes may expire, be private, or be syntax-highlighted.

## Requirements

### Functional

* Create a paste with optional title, expiry, visibility (public/unlisted/private) and syntax.
* Read a paste by its short id; raw and rendered views.
* Delete by owner; list own pastes.
* Optional custom id.

### Non-functional

* Highly available reads; p99 read < 100 ms.
* Durable: a paste is never lost or corrupted before expiry.
* Read-heavy (10:1); 1M new pastes/day.
* Cost-efficient storage for large text.

## Back-of-the-envelope estimates

* 1M pastes/day × 10 KB avg = 10 GB/day; 5 years ≈ 18 TB → content in object storage, metadata in a DB.
* Reads 10M/day ≈ 115/s; trivial; cache hot pastes.
* Ids: base62, 8 chars → 218 trillion.
* Metadata row ~200 B → 200 MB/day → 365 GB over 5 years; fine for a sharded relational DB or KV.

## API

```
POST /v1/pastes   { content, title?, syntax?, expiresIn?, visibility, customId? } → { id, url }
GET  /v1/pastes/{id}         → metadata + content (or 404/410 if expired)
GET  /{id}/raw
DELETE /v1/pastes/{id}       (owner)
GET  /v1/users/me/pastes
```

## Data model

```
pastes (paste_id PK, user_id, title, syntax, visibility, content_key, size, created_at, expires_at, views)
Object storage: pastes/{paste_id}.txt   (or inline in the DB for < 4 KB)
users  (user_id, ...)
```

## High-level design

1. **API servers** behind a load balancer.
2. **Create**: get an id from a key-generation service (pre-generated unique keys, as in the URL shortener); write content to object storage; write metadata to the DB; return the URL.
3. **Read**: check cache (Redis, id → content + metadata) → DB for metadata → object storage for content; cache the result. Enforce visibility and expiry.
4. **Expiry**: `expires_at` checked on read (return 410) plus a cleanup job that deletes expired content from object storage and rows from the DB.
5. **Small pastes** can be stored inline in the DB row to save an object-storage round-trip; large ones in object storage; a CDN can serve public raw pastes.
6. **Abuse**: size limits, rate limits, malware/spam scanning for public pastes.

## Architecture diagram

Rendering diagram…

## Deep dives

**Separate metadata from content**: metadata is small and queried; content is large and only fetched by id. Object storage gives cheap durability; the DB stays small.

**Private pastes**: require auth; never CDN-cache; unlisted = accessible by id but not listed.

**Consistency**: write content before metadata; a metadata row without content is impossible, and orphan content is cleaned up by the job.

## Bottlenecks & mitigations

* Viral paste → cache + CDN; object storage handles the rest.
* Cleanup job scanning → index on `expires_at`; delete in batches.
* Large pastes (MBs) → streaming upload/download; size caps.

## Failure modes

* **Object storage write succeeds, DB write fails**: client retries; orphan object reclaimed by cleanup.
* **Cache down**: DB + object storage serve directly.
* **KGS unavailable**: servers hold a local batch of keys; fall back to random ids with a uniqueness check.

## Follow-up questions interviewers ask

* How would you add versioning/edits to pastes?
* How would you support burn-after-read pastes safely?
* How would you implement full-text search over public pastes?

## Further reading

* [Guide: URL shorteningIllustrated guide on this site](/system-design/learn/url-shortening)

[PreviousDistributed Lock / Coordination Service (ZooKeeper-like)](/system-design/distributed-lock-service)[NextE-commerce Product Search (Amazon / Flipkart search)](/system-design/ecommerce-search)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftAtlassianAdobe

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
