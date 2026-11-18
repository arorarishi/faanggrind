# Twitter / X (tweets, timeline, search) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/twitter-timeline-and-search

[All system design questions](/system-design)

#24HLDHardHigh-level design

# Twitter / X (tweets, timeline, search)

fan-outtimelineinverted indextrending

## Problem statement

Design a microblogging service: post short messages, follow users, view a home timeline, search tweets, and see trending topics.

## Requirements

### Functional

* Post a tweet (text ≤ 280 chars, media); delete.
* Follow/unfollow; home timeline (from followees) and user timeline.
* Like, retweet, reply.
* Search tweets by keyword; trending hashtags.

### Non-functional

* Timeline load < 200 ms; new tweets visible to followers within ~5 s.
* 500M tweets/day; 300M DAU; celebrities with 100M followers.
* Read-heavy (timeline reads 100× writes).
* Search index near-real-time (< 1 min).

## Back-of-the-envelope estimates

* 500M tweets/day ≈ 6k/s, peak 60k/s.
* Timeline reads: 300M × 20/day ≈ 70k/s avg, 300k/s peak.
* Fan-out: 6k tweets/s × 200 avg followers = 1.2M timeline inserts/s — Redis can do it, but celebrities (100M followers) must be excluded from write fan-out.
* Timeline cache: 300M users × 800 tweet ids × 8 B ≈ 2 TB of Redis.
* Search: 500M tweets/day into an inverted index; ~30 B/posting × 10 terms ≈ 150 GB/day of index.

## API

```
POST /v1/tweets            { text, mediaIds[], replyTo? }
GET  /v1/timeline/home?cursor=&limit=20
GET  /v1/users/{id}/tweets?cursor=
POST /v1/tweets/{id}/like | retweet
GET  /v1/search?q=&cursor=
GET  /v1/trends?woeid=
```

## Data model

```
tweets      (tweet_id, user_id, text, media, created_at, reply_to, retweet_of)   -- sharded by tweet_id (Snowflake, time-sortable)
follows     (follower_id, followee_id)  + reverse index
user_timeline Redis LIST  ut:{user_id}   (own tweets, capped)
home_timeline Redis LIST  ht:{user_id}   (fanned-out ids, capped ~800)
tweet_cache  Redis HASH   tweet:{id}
counters     likes/retweets in Redis, flushed to DB
search index inverted index sharded by time (Earlybird-style)
```

## High-level design

1. **Tweet service** stores the tweet, caches it, and emits `tweet.created`.
2. **Fan-out service**: for non-celebrity authors, push the tweet id into each follower's home timeline list (write fan-out). Celebrity tweets are merged at read time.
3. **Timeline service**: read `ht:{user}`, merge with recent tweets from followed celebrities, apply ranking, hydrate from `tweet_cache`, paginate with cursor = tweet id (time-sortable ids make 'older than' trivial).
4. **Search**: an indexer consumes `tweet.created`, tokenises, and writes to time-sharded inverted-index nodes (newest shard in memory). Queries fan out to shards newest-first and stop when enough results are found.
5. **Trends**: stream processor counts hashtag/term frequency in sliding windows per region, compares to a baseline (z-score) to surface spikes; results cached and refreshed every minute.
6. **Media** via object storage + CDN; **notifications** for mentions/likes via the notification system.

## Architecture diagram

Rendering diagram…

## Deep dives

**Snowflake ids** give free time ordering for timelines and let the search index shard by id range = time range.

**Hybrid fan-out** threshold ~10k–100k followers; the read-time merge for celebrities is bounded because a user follows few celebrities.

**Retweets/replies** are tweets with pointers; the timeline hydrates the original.

**Search freshness**: an in-memory 'realtime' shard receives writes immediately; older shards are immutable and merged in the background.

**Deletion**: tombstone the tweet; hydration filters tombstones so no timeline scan is needed.

## Bottlenecks & mitigations

* Fan-out write burst when a mid-size account posts → parallel fan-out workers by follower shard; rate-limit fan-out per author.
* Home timeline memory → cap lists; drop inactive users' lists and rebuild lazily.
* Search hot terms (breaking news) → cache query results for seconds; early termination.
* Counter contention on viral tweets → sharded counters, summed on read.

## Failure modes

* **Fan-out lag**: timeline service falls back to pulling recent tweets from top followees.
* **Redis cache loss**: rebuild timelines lazily from the follow graph + tweets DB (slow first load).
* **Search index shard loss**: rebuild from Kafka/DB for that time range; serve partial results meanwhile.
* **Trends manipulation (spam)**: filter by unique users, account age, and dedupe near-identical text.

## Follow-up questions interviewers ask

* How would you rank the timeline instead of reverse-chronological?
* How would you implement 'who to follow'?
* How would you support 100M-follower accounts posting 50 times a day?

## Further reading

* [Guide: News feedsIllustrated guide on this site](/system-design/learn/feeds)

[PreviousAd Click Event Aggregation](/system-design/ad-click-aggregation)[NextPhoto Sharing App (Instagram)](/system-design/photo-sharing-app)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

TwitterMetaLinkedInMicrosoftAmazon

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
