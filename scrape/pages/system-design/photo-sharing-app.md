# Photo Sharing App (Instagram) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/photo-sharing-app

[All system design questions](/system-design)

#25HLDMediumHigh-level design

# Photo Sharing App (Instagram)

object storageCDNimage processingfeed

## Problem statement

Design a service where users upload photos, follow others, and browse a feed of photos with likes and comments — optimised for fast image delivery worldwide.

## Requirements

### Functional

* Upload photos (with captions, tags); generate multiple sizes.
* Follow users; home feed and profile grid.
* Like, comment; notifications.
* Explore/search by hashtag (basic).

### Non-functional

* Image load p99 < 200 ms globally (CDN).
* Uploads durable; processing within seconds.
* 500M DAU; 100M uploads/day.
* Read-heavy: 100:1.

## Back-of-the-envelope estimates

* 100M uploads/day × 2 MB original + ~1 MB of derived sizes = 300 TB/day → ~100 PB/year. Object storage with lifecycle tiering.
* Feed reads: 500M × 10 = 5B/day ≈ 60k/s, peak 200k/s.
* Metadata per photo ~1 KB → 100 GB/day; sharded DB by user.
* CDN egress dominates: 5B feed loads × 10 images × 200 KB = 10 PB/day.

## API

```
POST /v1/media/upload/init   → presigned URL(s)
POST /v1/posts               { mediaIds[], caption, tags[] }
GET  /v1/feed?cursor=
GET  /v1/users/{id}/posts?cursor=
POST /v1/posts/{id}/like     /   POST /v1/posts/{id}/comments
GET  /v1/tags/{tag}/posts
```

## Data model

```
posts     (post_id, user_id, caption, created_at)                 -- sharded by user_id
media     (media_id, post_id, original_key, variants:{thumb, medium, large}, width, height)
follows   (follower_id, followee_id)
likes     (post_id, user_id, ts)  PK(post_id, user_id)
comments  (post_id, comment_id, user_id, text, ts)
feed      Redis LIST per user (post ids)
counters  Redis: post:{id}:likes
Object storage keys: media/{media_id}/{variant}.jpg
```

## High-level design

1. **Upload**: client uploads the original directly to object storage via presigned URL; the media service enqueues a processing job.
2. **Image pipeline**: workers generate variants (thumbnail 150, feed 640, full 1080), strip EXIF (privacy), run moderation/NSFW models, store variants, update `media`.
3. **Post service**: creates the post once media is ready (or marks `processing` and lets the feed skip it); emits `post.created`.
4. **Feed**: same hybrid fan-out as a news feed — push post ids to followers' Redis lists, read-time merge for large accounts; hydrate metadata; image URLs point to the CDN.
5. **CDN**: all variants served from a global CDN with long cache TTLs; image URLs are immutable (media id + variant), so no invalidation is needed.
6. **Engagement**: likes/comments write to sharded tables + Redis counters; notification events published.

## Architecture diagram

Rendering diagram…

## Deep dives

**Immutable image URLs** are the simplest CDN strategy: a new upload = new id; edits create new media. Cache TTL can be a year.

**Variant generation** on upload (eager) vs on first request (lazy): eager for the 3 standard sizes; lazy resize-on-the-fly (with caching) for unusual sizes.

**Storage cost**: originals to cold storage after 30 days; keep variants hot.

**Privacy**: strip location EXIF before storing variants; originals access-controlled.

## Bottlenecks & mitigations

* Image processing backlog at peak → autoscale workers; generate the feed variant first.
* Feed fan-out for popular accounts → hybrid fan-out threshold.
* Like counters on viral posts → sharded counters / batched increments.
* CDN cache misses for long-tail content → origin shield; regional object-storage replicas.

## Failure modes

* **Processing worker fails**: job retried; post stays `processing`; feed skips it until ready.
* **CDN outage**: multi-CDN or direct-to-origin fallback with rate limiting.
* **Object storage regional outage**: cross-region replication for variants; uploads fail over to another region.
* **Feed cache loss**: rebuild lazily from follows + posts DB.

## Follow-up questions interviewers ask

* How would you add Stories with 24h expiry?
* How would you do image deduplication?
* How would you build the Explore ranking?

[PreviousTwitter / X (tweets, timeline, search)](/system-design/twitter-timeline-and-search)[NextReal-time Gaming Leaderboard](/system-design/realtime-leaderboard)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

MetaSnapAmazonMicrosoftAdobe

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
