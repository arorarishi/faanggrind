# Web Crawler — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/web-crawler

[All system design questions](/system-design)

#8HLDHardHigh-level design

# Web Crawler

BFSpolitenessdedupdistributed queue

## Problem statement

Design a distributed crawler that starts from seed URLs, downloads pages, extracts links, and keeps crawling the web — storing page content for a search index — while being polite to websites and avoiding traps.

## Requirements

### Functional

* Crawl from seeds, extract and follow links, store page content.
* Respect `robots.txt` and per-domain rate limits (politeness).
* Deduplicate URLs and near-duplicate content.
* Re-crawl pages on a freshness schedule; prioritise important pages.

### Non-functional

* Scale: 1B pages/month.
* Robust to malformed HTML, slow servers, infinite URL spaces (traps).
* Extensible to new content types (PDF, images).
* Fault-tolerant: worker loss must not lose the frontier.

## Back-of-the-envelope estimates

* 1B pages/month ≈ 400 pages/s average; with ~500 KB avg page → 200 MB/s ingest, **500 TB/month** stored (compress ~5× → 100 TB).
* URL frontier: ~10B known URLs × 100 B = 1 TB — must be on disk, not memory.
* Seen-URL check: 10B URLs in a Bloom filter at 1% FP ≈ 12 GB — fits in memory across a few nodes.
* DNS: 400 req/s is trivial, but DNS latency (~50 ms) is the hidden bottleneck without caching.

## API

Mostly internal:

```
POST /crawl/seeds        { urls[] , priority }
GET  /crawl/status/{domain}
Internal: frontier.enqueue(url, priority, notBefore) / frontier.next(workerId)
Storage: putPage(url, fetchedAt, headers, bodyHash, bodyRef)
```

## Data model

```
url_frontier     (url_hash PK, url, domain, priority, next_fetch_at, last_fetched_at, depth)
domain_state     (domain, robots_txt, crawl_delay, last_access_at, in_progress)
pages            (url_hash, fetched_at, http_status, content_hash, storage_key)  -- content in object storage
content_hashes   (simhash → url_hash)   -- near-duplicate detection
```

## High-level design

1. **URL frontier**: two-level queue system. *Front queues* by priority (page rank, freshness); *back queues* one per host to enforce politeness — each host queue is checked out by exactly one worker at a time with a `crawl_delay` between fetches. Implemented on Kafka/Redis + disk-backed store.
2. **Fetchers**: pull a URL, resolve DNS via a local cache, honour `robots.txt` (cached per domain), download with timeouts and size limits.
3. **Parser/extractor**: parse HTML, extract links and text, normalise URLs (lowercase host, strip fragments, resolve relative).
4. **Dedup**: URL-seen test (Bloom filter + exact check in the frontier store); content dedup via SimHash so mirrors/near-copies aren't stored twice.
5. **Storage**: raw content to object storage; metadata to the pages table; a downstream indexer consumes new pages.
6. **Scheduler**: re-enqueue pages with `next_fetch_at` based on observed change frequency.
7. **Trap protection**: max depth, max URLs per domain, URL length limits, pattern detection for calendar-style infinite links.

## Architecture diagram

Rendering diagram…

## Deep dives

**Politeness** is the hard part: the mapping *host → single back queue → single worker* guarantees one in-flight request per host; a min-heap of `(next_allowed_time, host)` decides which back queue to serve next.

**Prioritisation**: PageRank-like score + update frequency; news sites re-crawled hourly, static docs monthly.

**Distributed frontier**: partition hosts across frontier nodes by hash; a worker talks to one partition; rebalancing moves whole hosts.

**Content freshness vs cost**: adaptive re-crawl — if a page didn't change in N visits, back off exponentially.

## Bottlenecks & mitigations

* DNS resolution latency → aggressive local caching with TTL respect.
* A few huge domains dominate the frontier → per-domain caps and fair scheduling across hosts.
* Bloom filter false positives skip real URLs → accept ~1%, or use a second exact check for high-priority URLs.
* Parser CPU on giant pages → size caps (e.g. 10 MB), streaming parsers.

## Failure modes

* **Worker crash mid-fetch**: URL lease with visibility timeout; re-queued after expiry; fetches are idempotent.
* **Frontier node loss**: frontier persisted to disk/replicated; rebuildable from the pages table + seeds if needed.
* **Being blocked/banned**: respect `Retry-After` and 429/503; back off per domain; identify with a clear user-agent and contact URL.
* **Crawler trap**: depth and per-domain URL limits stop runaway growth; alert on domains exceeding thresholds.

## Follow-up questions interviewers ask

* How would you crawl JavaScript-rendered pages?
* How would you detect and skip duplicate content across domains?
* How would you prioritise for a news vertical vs a general index?

## Further reading

* [Guide: Web crawlingIllustrated guide on this site](/system-design/learn/web-crawling)
* [Web crawling (Olston & Najork survey)Paperinfolab.stanford.edu](http://infolab.stanford.edu/~olston/publications/crawling_survey.pdf)
* [Dynamic rendering for JavaScript sites (Google Search docs)Articledevelopers.google.com](https://developers.google.com/search/docs/guides/dynamic-rendering)

[PreviousVideo Streaming Platform (YouTube / Netflix)](/system-design/video-streaming-platform)[NextSearch Autocomplete / Typeahead](/system-design/search-autocomplete)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleAmazonMicrosoftAtlassianAdobe

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
