# Video Streaming Platform (YouTube / Netflix) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/video-streaming-platform

[All system design questions](/system-design)

#7HLDHardHigh-level design

# Video Streaming Platform (YouTube / Netflix)

transcodingCDNadaptive bitrateobject storage

## Problem statement

Design a platform where users upload videos that are processed into multiple resolutions and streamed to viewers worldwide with adaptive bitrate, plus view counts and recommendations at a basic level.

## Requirements

### Functional

* Upload videos up to several GB with resumable uploads.
* Transcode into multiple resolutions/codecs; generate thumbnails.
* Stream with adaptive bitrate (HLS/DASH) on any device.
* Metadata: title, description, tags; search; view counts, likes, comments.

### Non-functional

* Playback start < 2 s; no rebuffering on stable connections.
* Uploads durable — never lose a user's video.
* Global scale: 1B+ hours watched/day, 500 h uploaded/minute.
* Cost-efficient storage and bandwidth (CDN offload > 95%).

## Back-of-the-envelope estimates

* Uploads: 500 h/min = 30k h/day. Raw ~1 GB/h → 30 TB/day raw; transcoded ladder (5 renditions) ≈ 3× → ~100 TB/day of stored video → ~36 PB/year.
* Views: 1B h/day at ~3 Mbps avg ≈ 1B × 3600 × 3 Mb ≈ 1.35 EB/day egress; that is why CDN and codec efficiency (VP9/AV1) matter more than any single server.
* Transcoding: ~1 CPU-hour per hour of video per rendition → 30k × 5 = 150k CPU-hours/day → ~6k always-on cores or GPU encoders.

## API

```
POST /v1/videos/upload/init   { filename, size, mime } → { uploadId, presignedParts[] }
PUT  <presigned part url>     (client uploads chunks directly to object storage)
POST /v1/videos/upload/complete { uploadId, etags[] }  → { videoId, status:"processing" }
GET  /v1/videos/{id}           → metadata + { manifestUrl: "https://cdn/.../master.m3u8" }
GET  /v1/videos/{id}/status
POST /v1/videos/{id}/view      (beacon; batched client-side)
```

## Data model

```
videos     (video_id, owner_id, title, description, status, duration, created_at)
renditions (video_id, resolution, codec, bitrate, manifest_path, size)
thumbnails (video_id, path)
view_events → Kafka → aggregated daily/hourly counts in an OLAP store
comments   (video_id, comment_id, user_id, text, ts)  -- separate service
Object storage: raw/{videoId}/source.mp4, hls/{videoId}/{rendition}/segment_N.ts + playlists
```

## High-level design

1. **Upload**: client gets presigned multipart URLs and uploads chunks straight to object storage (S3); resumable by part. Upload service records completion and enqueues a processing job.
2. **Processing pipeline (DAG)**: split source into GOP-aligned chunks → transcode each chunk to each rendition in parallel (thousands of workers) → stitch → package to HLS/DASH segments (2–6 s) → thumbnails, captions, content moderation → write manifests → mark video `ready`.
3. **Delivery**: manifests and segments served through a multi-CDN; origin is object storage with an origin shield. Adaptive bitrate is client-driven: the player measures throughput and picks the rendition per segment.
4. **Metadata service** backed by a relational DB with read replicas; heavy caching.
5. **View counting**: players send beacons; Kafka → stream processor → approximate counts (HyperLogLog for unique viewers) → displayed counts updated every few seconds.
6. **Search & recommendations**: metadata indexed in Elasticsearch; recs from a separate ML pipeline.

## Architecture diagram

Rendering diagram…

## Deep dives

**Chunked parallel transcoding** turns a 2-hour job into minutes; chunk on keyframe boundaries so chunks encode independently.

**Adaptive bitrate**: server produces the ladder (e.g. 240p→1080p/4K); the client's ABR algorithm (buffer-based or throughput-based) switches per segment. Short segments = faster start and adaptation; longer = better compression.

**CDN strategy**: popular content (top 1%) is pre-warmed to edge; long-tail served from origin shield. Cache key = segment path; immutable, long TTL.

**Cost**: cold-tier storage for videos with no views in 90 days; re-encode to a newer codec on demand.

## Bottlenecks & mitigations

* Origin egress during a viral launch → pre-warm CDN, origin shield, request coalescing.
* Transcoding queue backlog → autoscale workers; prioritise by creator tier and expected views; produce 360p first so playback can start while higher renditions finish.
* Metadata DB reads → cache aggressively; view counts served from the counter store, not the DB.
* Thumbnails at scroll speed → pre-generate sprite sheets.

## Failure modes

* **Transcode worker failure**: chunks are idempotent tasks; retry with a visibility timeout; a job with a persistently failing chunk is flagged for manual review.
* **CDN outage**: multi-CDN with DNS/manifest-level steering; player retries the alternate CDN URL.
* **Object storage regional outage**: cross-region replication for manifests and hot renditions; raw uploads replicated asynchronously.
* **Counter pipeline lag**: display counts marked approximate; no impact on playback.

## Follow-up questions interviewers ask

* How would you support live streaming (low-latency HLS)?
* How would you enforce DRM?
* How does the design change for short-form vertical video (Reels)?

## Further reading

* [Guide: Video streaming platformIllustrated guide on this site](/system-design/learn/video-platform)
* [YouTube architecture (High Scalability)Articlehighscalability.com](http://highscalability.com/youtube-architecture)
* [Scalability at YouTube (2012 talk)Videoyoutube.com](https://www.youtube.com/watch?v=w5WVu624fY8)
* [Transcoding: how we serve videos at scale (Egnyte)Articleegnyte.com](https://www.egnyte.com/blog/2018/12/transcoding-how-we-serve-videos-at-scale/)
* [Under the hood: broadcasting live video to millions (Facebook)Articleengineering.fb.com](https://engineering.fb.com/ios/under-the-hood-broadcasting-live-video-to-millions/)
* [High quality video encoding at scale (Netflix)Articlenetflixtechblog.com](https://netflixtechblog.com/high-quality-video-encoding-at-scale-d159db052746)
* [Optimized shot-based encodes (Netflix)Articlenetflixtechblog.com](https://netflixtechblog.com/optimized-shot-based-encodes-now-streaming-4b9464204830)

[PreviousNews Feed (Facebook / Instagram / LinkedIn feed)](/system-design/news-feed)[NextWeb Crawler](/system-design/web-crawler)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleNetflixAmazonMicrosoftHotstar

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
