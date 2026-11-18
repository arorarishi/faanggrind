# Metrics Monitoring & Alerting System (Datadog / Prometheus) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/metrics-monitoring-alerting

[All system design questions](/system-design)

#22HLDHardHigh-level design

# Metrics Monitoring & Alerting System (Datadog / Prometheus)

time seriesaggregationdownsamplingpull vs push

## Problem statement

Design a system that collects metrics (CPU, latency, custom counters) from hundreds of thousands of hosts and services, stores them as time series, supports dashboards and queries, and fires alerts on rules.

## Requirements

### Functional

* Ingest metrics with tags (host, service, region…).
* Query time ranges with aggregation (avg, p99, sum by tag).
* Dashboards with near-real-time graphs.
* Alert rules (threshold, anomaly) with notification routing.
* Retention: raw for days, downsampled for a year+.

### Non-functional

* Ingest 10M+ data points/s; query recent data within seconds of arrival.
* Alert evaluation within 1 minute of the condition.
* Storage efficient: high-cardinality tags without exploding cost.
* Availability of ingest even when the query tier is degraded.

## Back-of-the-envelope estimates

* 100k hosts × 100 metrics × every 10 s = **1M points/s**; with services and custom metrics → 10M/s.
* Point = timestamp + value ≈ 16 B raw; with Gorilla-style compression ≈ 1.4 B → 10M/s ≈ 14 MB/s → ~1.2 TB/day compressed.
* Retention: 7 days raw (8 TB), 1 year at 1-min downsample (÷6 → ~70 TB), 5 years at 1-h (small).
* Series cardinality: 10M active series; the index (series id → tags) must fit in memory-ish (~10 GB).

## API

```
POST /v1/metrics/ingest   [{ name, tags:{...}, ts, value }]   (batched, from agents)
GET  /v1/query?q=avg:api.latency.p99{service:checkout} by {region}&from=&to=&step=
GET  /v1/series?match=api.latency*
POST /v1/alerts/rules     { name, query, condition: "> 500 for 5m", channels:[...] }
```

## Data model

```
series_index  (series_id, metric_name, tags[])          -- inverted index tag→series_ids for lookups
data (series_id, time bucket) → compressed block of (ts, value) pairs   -- TSDB (e.g. columnar blocks)
rollups_1m / rollups_1h (series_id, bucket, min, max, sum, count, p-sketch)
alert_rules (id, query, condition, for_duration, severity, routes)
alert_state (rule_id, series_id, state: ok|pending|firing, since)
```

## High-level design

1. **Collection**: an agent on each host scrapes/collects and **pushes** batches to ingest gateways (push scales better across NAT/ephemeral hosts than Prometheus-style pull; pull is simpler for fixed fleets).
2. **Ingest tier**: validates, assigns `series_id` from tags (hash), writes to Kafka partitioned by series id — this buffer decouples ingest availability from storage.
3. **Storage writers** consume Kafka and write to a **time-series DB**: in-memory head block per series (last ~2 h) + immutable compressed blocks on disk/object storage, with an inverted index over tags.
4. **Downsampling**: background jobs roll raw data into 1-min and 1-h aggregates (keeping count/sum/min/max and a quantile sketch so p99 can be re-aggregated).
5. **Query service**: parses the query, resolves series via the index, fans out to storage nodes/blocks, merges, aggregates; caches results for dashboards.
6. **Alert evaluator**: scheduled evaluation of rules against the query service (or a streaming evaluator on the Kafka feed for low latency), with `for` durations to avoid flapping; sends to the notification service with dedup and grouping.

## Architecture diagram

Rendering diagram…

## Deep dives

**Cardinality** is the real enemy: a tag like `user_id` creates millions of series. Enforce tag allow-lists, cap series per metric, and reject or aggregate offenders at ingest.

**Compression**: delta-of-delta timestamps + XOR values (Gorilla) give ~10× reduction; blocks are immutable and object-storage friendly.

**Percentiles across hosts** cannot be averaged; store sketches (t-digest/DDSketch) in rollups so p99 over a region is computable.

**Pull vs push**: pull gives target discovery and 'up' detection for free; push handles short-lived jobs and firewalls. Many systems do both.

## Bottlenecks & mitigations

* Ingest spikes (deploys, incidents) → Kafka buffering; ingest never blocks on storage.
* Wide queries (all hosts, 30 days) → answer from rollups automatically based on range/step; result caching.
* Index lookups for regex tag matches → inverted index with postings lists; limit series per query.
* Alert evaluation load → shard rules across evaluators; evaluate on streaming data for hot rules.

## Failure modes

* **Storage writers down**: Kafka retains data; writers catch up; dashboards show a gap that fills in.
* **Query tier overloaded**: query timeouts and per-tenant limits protect ingest and alerting (separate pools).
* **Missing data vs zero**: alert rules must distinguish 'no data' (host down) from value 0 — treat no-data as its own alert.
* **Alert storm**: grouping by rule/service, inhibition rules, and notification rate limits.

## Follow-up questions interviewers ask

* How would you add logs and traces and correlate them with metrics?
* How would you support multi-tenancy with isolation?
* How would you implement anomaly detection at scale?

## Further reading

* [Guide: Metrics, monitoring and alertingIllustrated guide on this site](/system-design/learn/monitoring)

[PreviousStock Exchange / Order Matching Engine](/system-design/stock-exchange)[NextAd Click Event Aggregation](/system-design/ad-click-aggregation)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

DatadogAmazonUberMicrosoftAtlassianSalesforce

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
