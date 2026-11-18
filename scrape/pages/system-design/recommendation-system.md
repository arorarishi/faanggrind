# Recommendation System (product / video recommendations) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/recommendation-system

[All system design questions](/system-design)

#39HLDHardHigh-level design

# Recommendation System (product / video recommendations)

candidate generationrankingfeature storeoffline/online

## Problem statement

Design a system that recommends items (products/videos) to users on the home page and item pages, using their history and item similarity, with real-time signals and A/B-testable models.

## Requirements

### Functional

* Home-page recommendations; 'similar items'; 'customers also bought'.
* Use user history (views, purchases), item metadata, and real-time session signals.
* Exclude seen/purchased items; business rules (in stock, not banned).
* A/B test models; explanations ('because you watched X').

### Non-functional

* p99 < 150 ms for the recommendation call.
* Freshness: session signals influence recs within seconds; new items within an hour.
* 100M users, 50M items, 1B events/day.
* Graceful fallback to popularity-based recs.

## Back-of-the-envelope estimates

* 1B events/day ≈ 12k/s into the feature pipeline.
* Precomputed candidates: 100M users × 500 ids × 8 B = 400 GB → KV store; refreshed daily plus real-time updates for active users.
* Item embeddings: 50M × 128 floats × 4 B = 25 GB → ANN index (HNSW) sharded across a few nodes.
* Online ranking: 500 candidates × ~100 features per request; 20k QPS → 10M feature lookups/s → feature store must be an in-memory KV with batching.

## API

```
GET /v1/recs/home?userId=&limit=20&context={device,page}     → { items:[{itemId, score, reason}], modelVersion }
GET /v1/recs/similar?itemId=&limit=20
POST /v1/events   { userId, itemId, type: view|click|purchase, ts }   (batched from clients)
```

## Data model

```
events            Kafka → data lake (Parquet) ; user_history (user_id → recent item ids, Redis)
item_features     (item_id, category, price, popularity_7d, embedding)       -- feature store
user_features     (user_id, affinity vector, segment, recent_items)          -- feature store (online + offline)
candidates        (user_id → [item_id...]) precomputed (KV)
similar_items     (item_id → [item_id...]) precomputed from co-occurrence / embeddings
ann_index         HNSW over item embeddings
experiments       (exp_id, variants, allocation)
```

## High-level design

1. **Event ingestion**: client/server events → Kafka → (a) stream processor updating **online features** (recent items, session vectors) in Redis; (b) data lake for offline training.
2. **Offline pipeline** (daily/hourly): train collaborative-filtering / two-tower models → produce user and item embeddings, item-to-item similarity tables, and per-user candidate lists → publish to the feature store, ANN index and candidate KV.
3. **Online serving** on each request:
   * **Candidate generation** (fast, high recall): precomputed user candidates + ANN neighbours of the user's session embedding + similar-items of recently viewed + trending — merged to ~500.
   * **Filtering**: remove seen/purchased, out-of-stock, policy violations.
   * **Ranking**: fetch features for user × candidates from the feature store; score with the ranking model (served via a model server); apply diversity/business re-ranking.
   * **Explanations** attached from the candidate source.
4. **Experimentation**: request assigned to a variant by user id hash; models/config resolved per variant; metrics logged with variant ids.
5. **Caching**: home recs cached per user for a few minutes, invalidated by strong signals (purchase).

## Architecture diagram

Rendering diagram…

## Deep dives

**Two-stage architecture** (retrieve then rank) is the standard: retrieval is cheap and broad; ranking is expensive and narrow.

**Feature consistency**: the same feature definitions must be used offline (training) and online (serving) — a feature store solves the training/serving skew.

**Real-time**: session embedding = average of recently viewed item embeddings, updated in-stream; ANN over it captures 'what you're doing right now'.

**Cold start**: new users → popularity by segment/geo; new items → content-based embeddings from metadata until interaction data exists.

**Diversity & rules** re-rank after scoring: category caps, price spread, promoted slots.

## Bottlenecks & mitigations

* Feature lookups per request → batch `MGET`, co-locate hot item features in process memory.
* Ranking model latency → distilled small model online; batch inference; strict deadline with partial scoring fallback.
* ANN index size/updates → shard by item range; rebuild periodically; small delta index for new items.
* Offline pipeline time → incremental training; publish candidates per user shard as they complete.

## Failure modes

* **Feature store down**: serve precomputed candidate order (no re-ranking) or popularity.
* **Model server down**: fall back to previous model version or heuristic score.
* **Stale candidates** (pipeline failed): keep serving yesterday's; alert on staleness.
* **Feedback loop** (only recommending popular items): exploration slots (ε-greedy/bandits) in the re-ranker.

## Follow-up questions interviewers ask

* How would you evaluate a new model offline and online?
* How would you build 'complete the look' bundles?
* How would you avoid recommending items the user just bought (e.g. a fridge)?

[PreviousAPI Gateway (auth, routing, rate limiting, observability)](/system-design/api-gateway)[NextConsistent Hashing (Data Partitioning)](/system-design/consistent-hashing)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonNetflixFlipkartGoogleLinkedInSwiggy

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
