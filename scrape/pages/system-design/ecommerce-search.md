# E-commerce Product Search (Amazon / Flipkart search) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/ecommerce-search

[All system design questions](/system-design)

#37HLDHardHigh-level design

# E-commerce Product Search (Amazon / Flipkart search)

inverted indexrankingfacetsindexing pipeline

## Problem statement

Design product search for a catalogue of hundreds of millions of items: keyword search with typo tolerance, filters/facets (brand, price, rating), sorting, personalised ranking, and near-real-time index updates for price and stock.

## Requirements

### Functional

* Search by keywords with spelling correction and synonyms.
* Facets and filters; sort by relevance/price/rating.
* Show only in-stock/serviceable items; fresh prices.
* Personalised ranking; A/B testing of ranking models.

### Non-functional

* p99 < 300 ms; 50k QPS peak.
* Index freshness: price/stock changes visible within 1 min; new products within 10 min.
* Highly available; degrade to non-personalised results if needed.
* 300M products, 50 attributes each.

## Back-of-the-envelope estimates

* 300M docs × ~2 KB indexed = 600 GB index; with replicas ×3 → 1.8 TB across ~60 shards of 30 GB.
* 50k QPS × fan-out to 60 shards = 3M shard-queries/s → each shard node handles ~50k/s → replicas per shard 2–3 → ~150–200 nodes.
* Updates: 100M price/stock updates/day ≈ 1.2k/s — fine for near-real-time indexing.
* Facet computation over millions of hits → doc values/columnar fields; cap facet candidates.

## API

```
GET /v1/search?q=running shoes&filters=brand:nike,price:2000-5000&sort=relevance&page=2&userId=
→ { results:[{sku, title, price, rating, imageUrl}], facets:{brand:[...], price:[...]}, total, spellSuggestion }
GET /v1/suggest?q=run   (typeahead; see autocomplete design)
Internal: catalogue events → indexer
```

## Data model

```
search document: {sku, title, description, brand, category_path[], attributes{}, price, in_stock, rating, popularity, region_serviceable[] , embedding?}
inverted index: term → postings (doc ids + positions); doc values for sortable/facetable fields
catalogue source of truth: products DB + price service + inventory service
ranking features store: per-sku popularity, CTR; per-user affinity vector
```

## High-level design

1. **Indexing pipeline**: catalogue, price and inventory services publish change events → Kafka → indexer builds/updates search documents. Two paths: **bulk rebuild** (nightly full index from the source) and **near-real-time** updates (price/stock as partial doc updates within a minute).
2. **Search cluster** (Elasticsearch/Solr/Vespa or custom): sharded by hash of sku, replicated; a **query coordinator** parses the query, expands (synonyms, spell-correct via a fuzzy/ngram index), builds the boolean + filter query, scatters to shards, gathers top-k per shard, merges.
3. **Ranking**: stage 1 — BM25 relevance + filters → top ~1,000; stage 2 — a **learning-to-rank** model on features (text match, popularity, price competitiveness, personalisation) → top 50. Stage 2 runs in a ranking service so models deploy independently.
4. **Facets** computed from doc values on the matched set (approximate for very large sets).
5. **Freshness for stock/price**: store fast-changing fields in a separate small store (Redis) and post-filter/re-score results with live values so the heavy index isn't rewritten for every change.
6. **Caching**: query-result cache for popular (query, filters) combos with short TTL; personalisation applied after cache.

## Architecture diagram

Rendering diagram…

## Deep dives

**Two-stage ranking** keeps the expensive model off millions of candidates.

**Typo tolerance**: edit-distance automata (Levenshtein) over the term dictionary, or an n-gram index; apply only when the exact query has few results to protect precision.

**Zero-result handling**: relax filters, drop the least important term, show similar categories.

**Index layout**: separate 'hot' fields (price, stock) from the main index; keep the main index rebuilds nightly; live overlays give freshness.

**Vector search** (embeddings) as a supplementary candidate source for semantic queries; merged with lexical candidates.

## Bottlenecks & mitigations

* Scatter-gather latency dominated by the slowest shard → replicas with adaptive routing; hedged requests.
* Facet aggregation on broad queries ('shoes') → sampled/approximate facets; precomputed for top categories.
* Index rebuild time → blue-green index aliases; incremental segments.
* Ranking service latency → feature caching; batch scoring; strict time budget with fallback to stage-1 order.

## Failure modes

* **Ranking service down**: return stage-1 results (relevance only).
* **Shard replica loss**: cluster rebalances; reduced capacity; shed personalisation first.
* **Indexer lag**: stale stock shown → live overlay filters out-of-stock at query time as a safety net.
* **Bad synonym/model deploy**: A/B-gated rollouts; instant rollback via config.

## Follow-up questions interviewers ask

* How would you implement query understanding (brand vs category detection)?
* How would you support multi-language search for India (Hinglish)?
* How would you measure search quality offline and online?

[PreviousPastebin / Text Sharing Service](/system-design/pastebin)[NextAPI Gateway (auth, routing, rate limiting, observability)](/system-design/api-gateway)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonFlipkartWalmartMyntraGoogle

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
