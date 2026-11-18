# News Feed (Facebook / Instagram / LinkedIn feed) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/news-feed

[All system design questions](/system-design)

#6HLDHardHigh-level design

# News Feed (Facebook / Instagram / LinkedIn feed)

fan-out on writefan-out on readrankingcaching

## Problem statement

Design a home feed that shows a user recent posts from people/pages they follow, ranked, with infinite scroll, at social-network scale.

## Requirements

### Functional

* Publish a post (text/image/video) visible to followers.
* Retrieve a user's feed: paginated, newest/ranked first.
* Like/comment counts on posts; feed reflects them (eventually).
* Follow/unfollow affects the feed.

### Non-functional

* Feed load p99 < 500 ms.
* Post appears in followers' feeds within seconds (eventual consistency OK).
* 1B users, 300M DAU, average 300 follows, some accounts with 50M followers.
* Read-heavy: feed reads ≫ posts.

## Back-of-the-envelope estimates

* 300M DAU × 10 feed loads/day = 3B loads/day ≈ 35k/s, peak 100k/s.
* Posts: 300M × 0.5/day = 150M posts/day ≈ 1,700/s.
* Fan-out on write: 150M posts × 300 followers = 45B feed-cache inserts/day ≈ 520k/s — feasible in Redis but heavy.
* Feed cache: 300M users × 500 post ids × 8 B = 1.2 TB → sharded Redis cluster.
* Celebrity post (50M followers) → 50M inserts for one post: the reason hybrid fan-out exists.

## API

```
POST /v1/posts                { text, mediaIds[] }         → { postId }
GET  /v1/feed?cursor=&limit=20 → { items:[{postId, author, text, media, likeCount, ts}], nextCursor }
POST /v1/posts/{id}/like
POST /v1/users/{id}/follow
```

Cursor = (rank score, post id) so pagination is stable while new posts arrive.

## Data model

```
posts      (post_id, author_id, content, media, created_at)          -- sharded by post_id
follows    (follower_id, followee_id)                                  -- graph DB or sharded table, both directions indexed
feed_cache Redis ZSET  feed:{user_id} → {post_id: score}  capped at 500-1000 entries
post_cache Redis HASH  post:{post_id} → content + counters
counters   like_count/comment_count kept in Redis, flushed to DB periodically
```

## High-level design

1. **Post service** writes the post, then emits a `post.created` event.
2. **Fan-out service** (consumer): fetches the author's follower ids and pushes the post id into each follower's `feed_cache` ZSET (**fan-out on write**). For authors above a follower threshold (e.g. 100k), it skips fan-out (**fan-out on read**).
3. **Feed service** on read: pulls the user's ZSET (pre-computed), merges in posts from followed celebrities fetched directly (small list), runs the **ranker**, hydrates post content from `post_cache`/DB, returns a page.
4. **Ranking**: features (recency, affinity, engagement counts, content type) → a lightweight model scoring a candidate set of ~500; heavy models run offline to produce per-user affinity scores.
5. **Media** via CDN; the feed carries URLs only.
6. **Inactive users**: skip fan-out for users inactive > 30 days; build their feed lazily on next login.

## Architecture diagram

Rendering diagram…

## Deep dives

**Hybrid fan-out** is the core decision: write-fan-out gives O(1) reads but O(followers) writes; read-fan-out the reverse. Split by follower count.

**Feed cache sizing**: keep only ids (not content) and cap the ZSET; older items fall off and are rebuilt from the DB if a user scrolls far.

**Counters**: likes are written to Redis with periodic flush; the feed shows slightly stale counts — fine.

**Deletion/privacy**: on post delete, remove from the post cache and let feeds filter out missing posts at hydration time rather than scanning every feed.

## Bottlenecks & mitigations

* Fan-out lag for popular authors → threshold to read-fan-out; parallelise fan-out by follower shard.
* Feed cache memory → cap entries, evict inactive users, compress ids.
* Hydration N+1 → batch `MGET`, request coalescing for viral posts.
* Ranker latency → precompute affinity offline, keep online model tiny, time-box scoring.

## Failure modes

* **Fan-out workers lag**: feeds go stale; feed service can supplement with a direct query of recent posts from top-N followed accounts.
* **Feed cache loss**: rebuild lazily from the posts DB on next read (slow first load) — keep the DB indexed on (author\_id, created\_at).
* **Ranker down**: fall back to reverse-chronological.
* **Hot post** (viral): post cache replicated; counters batched to avoid write contention.

## Follow-up questions interviewers ask

* How would you add stories (24h expiry) to the same system?
* How do you avoid showing the same post twice across sessions?
* How would you implement 'seen' tracking cheaply?

## Further reading

* [Guide: News feedsIllustrated guide on this site](/system-design/learn/feeds)

[PreviousChat / Messaging System (WhatsApp, Slack)](/system-design/chat-messaging-system)[NextVideo Streaming Platform (YouTube / Netflix)](/system-design/video-streaming-platform)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

MetaLinkedInTwitterAmazonMicrosoft

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
