# Search Autocomplete / Typeahead — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/search-autocomplete

[All system design questions](/system-design)

#9HLDMediumHigh-level design

# Search Autocomplete / Typeahead

trietop-kcachingoffline aggregation

## Problem statement

Design a system that returns the top 5–10 query suggestions as the user types, ranked by popularity, updated as search trends change.

## Requirements

### Functional

* Given a prefix, return the top-k most popular completions.
* Suggestions reflect recent popularity (updated hourly/daily).
* Support prefix lengths 1–50; case-insensitive; optionally personalised.

### Non-functional

* p99 latency < 100 ms end-to-end (users type ~5 chars/s).
* Highly available — degrade to stale suggestions rather than none.
* 10B search queries/day feeding the popularity data.
* Storage efficient: hundreds of millions of distinct queries.

## Back-of-the-envelope estimates

* 10B queries/day → ~120k QPS for the search backend; autocomplete calls ≈ 5–8× that → ~700k QPS, mostly cached.
* Distinct queries: 200M × avg 20 chars ≈ 4 GB raw; a trie with top-k cached per node ≈ 3–4× → ~15 GB, fits in memory on a few nodes, sharded by prefix.
* Popularity aggregation: 10B events/day = 116k/s into a stream processor; hourly batch produces ~200M counts.

## API

```
GET /v1/autocomplete?q=how+to&limit=8&locale=en-IN
→ { "suggestions": ["how to tie a tie", "how to cook rice", ...] }
```

Client debounces (~100 ms) and cancels in-flight requests when the prefix changes.

## Data model

Trie node: `{children, topK: [(query, score)]}`, `topK` precomputed. Persisted as a serialised snapshot in object storage; served from memory. Popularity source: `query_counts(query, window, count)` in a wide-column store.

## High-level design

1. **Data collection**: search service logs queries to Kafka; a stream/batch job aggregates counts per query per hour and writes to `query_counts`. Filter out low-frequency and unsafe queries.
2. **Trie builder** (offline, hourly/daily): reads aggregated counts, builds a trie where every node stores its top-k completions (computed bottom-up by merging children). Serialised and shipped to serving nodes.
3. **Serving**: nodes hold the trie in memory; sharded by first 1–2 characters with hot-prefix awareness (e.g. 'a…' gets more shards than 'x…'). A request routes to the shard, walks to the prefix node, returns its cached top-k — O(prefix length).
4. **Caching**: CDN/edge cache and browser cache for short popular prefixes (TTL minutes). Most requests never reach the trie.
5. **Personalisation** (optional): merge global top-k with the user's recent searches client-side or in a thin layer.

## Architecture diagram

Rendering diagram…

## Deep dives

**Why precompute top-k**: walking a subtree at query time is O(subtree) — too slow; storing top-k per node makes lookup O(L). The cost is rebuild time and memory, paid offline.

**Freshness vs cost**: hourly rebuilds for trending terms; a small 'trending' overlay merged at serve time gives minute-level freshness for breaking news.

**Sharding**: naive first-letter sharding is skewed; use a shard map built from prefix frequency so each shard carries similar QPS.

**Filtering**: profanity/PII filter applied at build time; a blocklist checked at serve time for urgent removals.

## Bottlenecks & mitigations

* Hot prefixes (single letters) → cache at edge; serve from every node (replicate the top level of the trie).
* Trie rebuild time as data grows → build incrementally per shard; blue-green swap snapshots.
* Long-tail prefixes with no data → return empty quickly; don't fall back to expensive search.

## Failure modes

* **Serving node down**: LB routes to replicas of the shard; snapshots reload in minutes.
* **Aggregation pipeline delay**: serve the last good snapshot; alert if a snapshot is > 2 hours old.
* **Bad snapshot** (corrupt/offensive): keep the previous snapshot and roll back atomically.
* **Edge cache serving stale after a takedown**: purge by prefix key; keep TTLs short for sensitive locales.

## Follow-up questions interviewers ask

* How would you support fuzzy matching (typos)?
* How would you do multi-language / transliterated (Hinglish) suggestions?
* How would you personalise without leaking other users' queries?

## Further reading

* [Guide: Search autocompleteIllustrated guide on this site](/system-design/learn/autocomplete)
* [How we built Prefixy: a scalable prefix search serviceArticlemedium.com](https://medium.com/@prefixyteam/how-we-built-prefixy-a-scalable-prefix-search-service-for-powering-autocomplete-c20f98e2eff1)
* [Prefix hash tree: an indexing data structure over DHTsPaperpeople.eecs.berkeley.edu](https://people.eecs.berkeley.edu/~sylvia/papers/pht.pdf)

[PreviousWeb Crawler](/system-design/web-crawler)[NextRide-Sharing Service (Uber / Ola)](/system-design/ride-sharing)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleAmazonLinkedInMicrosoftFlipkartSwiggy

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
