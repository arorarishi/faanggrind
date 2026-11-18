# Ad Click Event Aggregation — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/ad-click-aggregation

[All system design questions](/system-design)

#23HLDHardHigh-level design

# Ad Click Event Aggregation

stream processingexactly-oncewindowinglambda vs kappa

## Problem statement

Design a system that ingests billions of ad click events per day and answers 'clicks for ad X in the last M minutes' and 'top-N ads by clicks in the last M minutes', with correctness good enough for billing.

## Requirements

### Functional

* Ingest click events (ad\_id, user\_id, ts, ip, country…).
* Query: clicks per ad per minute; top-100 ads per minute; filter by attributes.
* Late events (up to minutes) must be counted; duplicates removed.
* Data must be re-computable for billing audits.

### Non-functional

* 1B clicks/day (~10k/s avg, 50k/s peak); end-to-end aggregation latency ≤ 1 minute.
* Exactly-once counting for billing (at least a reconciled path).
* Fault-tolerant; no data loss.
* Raw data retained for reprocessing.

## Back-of-the-envelope estimates

* 1B events/day × 100 B = 100 GB/day raw; 2-year retention ≈ 70 TB in columnar format (~10× smaller compressed).
* Aggregates: 2M ads × 1,440 minutes = 2.9B rows/day if every ad clicked every minute; realistically ~10% → 300M rows/day, ~20 B each → 6 GB/day.
* Peak 50k/s is modest for Kafka + Flink; the challenge is correctness (late data, dedup) rather than throughput.

## API

```
POST /v1/clicks  (from ad servers, batched)  { adId, clickId, userId, ts, attrs }
GET  /v1/ads/{adId}/clicks?from=&to=&granularity=1m           → [{minute, count}]
GET  /v1/ads/top?window=1m&n=100&filter=country:IN            → [{adId, count}]
```

## Data model

```
Raw:      click events in Kafka (retention days) → archived to a data lake (Parquet, partitioned by hour)
Aggregates: ad_clicks_1m (ad_id, minute, count, version)          -- OLAP/columnar or Cassandra
            top_ads_1m   (minute, filter_key, [ (ad_id, count) x100 ])
Dedup:    click_id seen-set with TTL (Redis/RocksDB in the stream processor state)
```

## High-level design

1. **Ingest**: ad servers send clicks to a gateway → Kafka (partitioned by `ad_id` so all events for an ad hit one stream partition).
2. **Stream processing (Flink/Kafka Streams)**: keyed by `ad_id`, **tumbling 1-minute windows** with **event-time** semantics and **watermarks** (allowed lateness e.g. 5 minutes). State stores the running count; on window close, emit `(ad_id, minute, count)`; late events trigger an updated emission (upsert by version).
3. **Dedup** inside the processor: keep `click_id` in state with a TTL; drop repeats. Exactly-once via Kafka transactions / Flink checkpoints.
4. **Top-N**: a second stage keyed by minute (and filter dimension) maintains a min-heap of size N over incoming `(ad_id, count)` updates; emits the list at window close.
5. **Serving**: aggregates written to an OLAP store (ClickHouse/Druid) or Cassandra for point queries; a query service serves dashboards/APIs.
6. **Batch reconciliation**: nightly job recomputes aggregates from the data lake and fixes discrepancies — the billing source of truth (lambda-style safety net; a pure kappa design would just replay the stream).

## Architecture diagram

Rendering diagram…

## Deep dives

**Event time vs processing time**: bill by when the click happened; watermarks bound how long you wait for stragglers; events later than the allowed lateness go to a side output and are handled by the batch job.

**Exactly-once**: Kafka → Flink checkpoints (offsets + state atomically) → transactional sink; plus idempotent upserts keyed by (ad\_id, minute) so re-emissions overwrite rather than add.

**Hot ads** (a viral campaign) skew one partition → pre-aggregate at the gateway (local 1-second counts) or salt the key and merge.

**Fraud**: bot filtering runs as a separate enrichment stage before aggregation; flagged clicks are counted separately.

## Bottlenecks & mitigations

* Skewed ad\_id partitions → key salting + two-phase aggregation.
* State size for dedup (1B ids/day) → TTL 10 minutes; bloom-filter-backed state.
* Aggregates store write rate → batch upserts; columnar store with async merges.
* Top-N across many filter dimensions → precompute only supported dimensions; others via OLAP query.

## Failure modes

* **Processor crash**: restart from last checkpoint; Kafka offsets rewind; transactional sink discards uncommitted output → no double counting.
* **Kafka partition unavailable**: gateway buffers briefly; ad servers retry with the same click\_id (dedup protects).
* **Watermark stalls** (one idle partition holds back the window) → idle-source timeouts.
* **Aggregates store outage**: processor backpressures; Kafka retains; recompute path available.

## Follow-up questions interviewers ask

* How would you support arbitrary ad-hoc filters (country × device × hour)?
* How would you detect click fraud in real time?
* How would you present approximate counts with error bounds?

## Further reading

* [Guide: Click event aggregationIllustrated guide on this site](/system-design/learn/event-aggregation)

[PreviousMetrics Monitoring & Alerting System (Datadog / Prometheus)](/system-design/metrics-monitoring-alerting)[NextTwitter / X (tweets, timeline, search)](/system-design/twitter-timeline-and-search)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleMetaAmazonFlipkartMicrosoft

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
