# Log Aggregation & Search (ELK / Splunk-like) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/log-aggregation-and-search

[All system design questions](/system-design)

#29HLDMediumHigh-level design

# Log Aggregation & Search (ELK / Splunk-like)

ingestion pipelineinverted indexhot-warm-coldretention

## Problem statement

Design a system that collects logs from thousands of services, makes them searchable within seconds, supports filtering by fields and time, and retains data cost-effectively for months.

## Requirements

### Functional

* Ship logs from hosts/containers with structured fields.
* Search by free text and fields over a time range; aggregations (count by status).
* Live tail; saved searches; alerts on patterns.
* Retention tiers and per-team quotas.

### Non-functional

* Searchable within 10 s of emission.
* Ingest 1 TB/day → 100 TB/day at scale; bursts 5×.
* Search on recent data < 2 s; older data may be slower.
* Loss tolerance: at-most a few seconds on agent crash acceptable; none in the pipeline.

## Back-of-the-envelope estimates

* 10 TB/day ≈ 115 MB/s ≈ 200k events/s at 500 B each; peaks 1M/s.
* Index expansion ~1.2× raw for full-text; hot tier 3 days = 36 TB on SSD; warm 30 days = 300 TB on HDD (compressed ~5× → 60 TB); cold in object storage.
* Shards: keep index shards 20–40 GB; 10 TB/day → ~300 shards/day across the hot nodes.

## API

```
Agents → POST /v1/ingest (batched, gzip)   { events:[{ts, service, level, message, fields{...}}] }
GET  /v1/search?q=level:ERROR AND service:checkout AND "timeout"&from=now-15m&to=now&limit=100
GET  /v1/aggregate?q=...&groupBy=status&interval=1m
WS   /v1/tail?q=...
POST /v1/alerts  { query, threshold, window }
```

## Data model

```
Index per (tenant, day) → shards; document = {@timestamp, service, host, level, message, fields...}
Field mappings: keyword fields (exact/aggregatable), text fields (tokenised), timestamp
Tiering metadata: index → tier (hot/warm/cold), size, docs, retention_until
Kafka topic per tenant/priority as the ingest buffer
```

## High-level design

1. **Agents** (Fluent Bit/Vector) tail files/containers, parse to JSON, batch and ship to the **ingest gateway** with backpressure and local disk buffering.
2. **Gateway** authenticates, applies quotas, and writes to **Kafka** (buffer; decouples bursts from the index).
3. **Processors** consume, enrich (geo, k8s metadata), redact secrets/PII, sample noisy debug logs, and bulk-index into the **search cluster** (Elasticsearch/OpenSearch or a columnar log store like Loki/ClickHouse).
4. **Index lifecycle**: hot (SSD, writes + recent queries) → warm (HDD, read-only, force-merged) → cold (snapshots in object storage, searchable on demand) → delete.
5. **Query service** routes by time range to the right tier, applies tenant filters, caches aggregations; **live tail** subscribes to the Kafka stream with a filter.
6. **Alerting** evaluates saved queries periodically or on the stream.

## Architecture diagram

Rendering diagram…

## Deep dives

**Structured logging** at the source is the biggest win: fields become keyword columns; message stays text.

**Sampling & redaction** happen in processors so the index never stores secrets and debug noise is cut by 90%.

**Time-based indices** make retention a delete of whole indices and let queries skip irrelevant shards entirely.

**Columnar vs inverted index**: inverted index (ES) for arbitrary text search; columnar/label-based (Loki, ClickHouse) is much cheaper when most queries filter by labels and time and grep the rest.

## Bottlenecks & mitigations

* Index write throughput during incidents → Kafka buffer; increase bulk sizes; add hot nodes; sample.
* Mapping explosion (thousands of dynamic fields) → strict mappings, field limits, flatten unknown fields into one object.
* Wide time-range queries over warm/cold → async queries, result caching, rollup indices for aggregations.
* Noisy tenants → per-tenant Kafka topics and quotas; separate hot nodes for big tenants.

## Failure modes

* **Search cluster down**: Kafka retains hours/days of logs; processors resume; live tail still works from Kafka.
* **Agent host crash**: at most the unflushed buffer is lost (seconds).
* **Hot node loss**: shard replicas (RF=2) on hot; warm/cold restored from snapshots.
* **Retention misconfig** (disk full): index write block → alerts on disk watermarks; emergency deletion of oldest indices.

## Follow-up questions interviewers ask

* How would you correlate logs with traces (trace\_id)?
* How would you implement per-field access control (PII)?
* How would you cut cost 10× for rarely-searched logs?

## Further reading

* [Guide: Metrics, monitoring and alertingIllustrated guide on this site](/system-design/learn/monitoring)

[PreviousEmail Service (Gmail-like)](/system-design/email-service)[NextDigital Wallet (Paytm / PhonePe balance & transfers)](/system-design/digital-wallet)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftSalesforceAtlassianUberPalo Alto Networks

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
