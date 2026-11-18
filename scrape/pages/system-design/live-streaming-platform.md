# Live Video Streaming (Twitch / Hotstar live match) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/live-streaming-platform

[All system design questions](/system-design)

#34HLDHardHigh-level design

# Live Video Streaming (Twitch / Hotstar live match)

low-latencyHLSCDNfan-outchat

## Problem statement

Design a platform that ingests a live video stream from a broadcaster, transcodes it in real time, and delivers it to millions of concurrent viewers with a few seconds of latency, plus live chat.

## Requirements

### Functional

* Broadcaster streams via RTMP/SRT; viewers watch on web/mobile/TV.
* Adaptive bitrate; DVR (seek back a few minutes); VOD after the stream ends.
* Live chat/reactions; viewer count.
* Regional restrictions, ads insertion (basic).

### Non-functional

* Glass-to-glass latency 3–10 s (LL-HLS) ; < 1 s for interactive use cases (WebRTC).
* 25M concurrent viewers for a cricket final; stable during spikes (wicket moments).
* No single stream outage: redundant ingest and transcoding.
* Cost: CDN egress dominates.

## Back-of-the-envelope estimates

* 25M viewers × 3 Mbps = 75 Tbps egress — only feasible via multi-CDN with ISP peering; origin serves CDNs, not users.
* Transcoding a 1080p60 source to a 6-rendition ladder in real time ≈ 1 GPU or ~16 CPU cores per stream; 10k concurrent channels → a big but bounded fleet.
* Segments: 2 s parts (LL-HLS) → manifest updates every 2 s; origin request rate per CDN edge is tiny; the fan-out is the CDN's job.
* Chat: 25M viewers, 1% chatting at 1 msg/10 s → 25k msgs/s in; fan-out is 25M × 25k = impossible raw → sample/aggregate chat for huge rooms.

## API

```
Ingest: RTMP/SRT publish to rtmp://ingest/{streamKey}
GET  /v1/streams/{id}/manifest.m3u8      (LL-HLS master; CDN)
GET  /v1/streams/{id}/{rendition}/seg_{n}.m4s
WS   /v1/streams/{id}/chat   → { user, text } ; ← batched messages
GET  /v1/streams/{id}/viewers → approximate count
POST /v1/streams/{id}/start | stop
```

## Data model

```
streams      (stream_id, channel_id, status, ingest_region, started_at, dvr_window_s)
renditions   (stream_id, name, bitrate, resolution)
segments     object storage: live/{stream}/{rendition}/seg_n ; manifests updated in place
vod          (stream_id, vod_asset_id)  -- created from the recorded segments
chat_messages(stream_id, msg_id, user_id, text, ts)   -- short retention; Kafka-backed
viewer_counts Redis HyperLogLog per stream per minute
```

## High-level design

1. **Ingest**: broadcaster pushes to the nearest ingest PoP; the stream is duplicated to two transcoding pipelines in different AZs (primary/backup).
2. **Real-time transcoding**: produces the ABR ladder; **packager** emits LL-HLS/DASH parts (sub-second chunks) and updates playlists; writes to origin storage.
3. **Origin + CDN**: origin shield → multiple CDNs → edge; clients fetch manifests and parts from the edge. Manifests have very short TTLs (1–2 s); parts are immutable and cache forever.
4. **Player**: ABR selects rendition; LL-HLS uses blocking playlist reloads and partial segments to keep latency low; DVR by keeping the last N minutes in the playlist.
5. **Chat**: WebSocket gateway → Kafka → chat fan-out service. For huge rooms, fan-out is *sampled*: each viewer sees a rate-limited subset (e.g. 20 msgs/s) chosen from the stream; moderation filters run inline.
6. **Viewer count**: heartbeat pings aggregated into HLL per stream; displayed approximately.
7. **VOD**: after the stream ends, segments are stitched into a VOD asset (or referenced directly).
8. **Ads**: server-side ad insertion (SSAI) stitches ad segments into the manifest per region/user segment.

## Architecture diagram

Rendering diagram…

## Deep dives

**Latency budget**: encoder (~1 s) + packaging (part size) + CDN propagation + player buffer (2–3 parts). LL-HLS gets 3–5 s; WebRTC (< 1 s) is used for interactive streams but scales poorly to millions without an SFU cascade.

**Spike handling**: a wicket moment causes millions of manifest requests simultaneously → CDN edge caching of manifests with request coalescing at the shield is essential; origin must never see per-viewer traffic.

**Redundant pipelines**: manifests can reference segments from either pipeline as long as timestamps align (synchronised encoders).

**Chat at scale**: the room is partitioned; the fan-out service sends batches every 200 ms; big rooms use sampling and 'slow mode'.

## Bottlenecks & mitigations

* CDN capacity in one ISP → multi-CDN steering by region/ISP with real-time QoE feedback.
* Transcoder failure → hot backup pipeline; player retries alternate manifest.
* Chat fan-out → sampling, batching, regional chat servers.
* Manifest churn at 2 s intervals → tiny manifests, delta playlists (LL-HLS `EXT-X-SKIP`).

## Failure modes

* **Ingest PoP loss**: broadcaster reconnects to another PoP (backup stream key); a few seconds of black.
* **CDN degradation**: player-side failover to the other CDN's URL; steering service updates weights.
* **Origin storage outage**: CDNs serve cached parts for a while; failover origin in another region receives the backup pipeline.
* **Chat abuse storm**: rate limits per user, shadow-bans, ML moderation; chat can be disabled without affecting video.

## Follow-up questions interviewers ask

* How would you get to sub-second latency for 100k viewers?
* How would you implement multi-camera angle switching?
* How would you do per-user ad insertion at 25M scale?

## Further reading

* [Guide: Video streaming platformIllustrated guide on this site](/system-design/learn/video-platform)
* [YouTube architecture (High Scalability)Articlehighscalability.com](http://highscalability.com/youtube-architecture)
* [Scalability at YouTube (2012 talk)Videoyoutube.com](https://www.youtube.com/watch?v=w5WVu624fY8)
* [Transcoding: how we serve videos at scale (Egnyte)Articleegnyte.com](https://www.egnyte.com/blog/2018/12/transcoding-how-we-serve-videos-at-scale/)
* [Under the hood: broadcasting live video to millions (Facebook)Articleengineering.fb.com](https://engineering.fb.com/ios/under-the-hood-broadcasting-live-video-to-millions/)
* [High quality video encoding at scale (Netflix)Articlenetflixtechblog.com](https://netflixtechblog.com/high-quality-video-encoding-at-scale-d159db052746)
* [Optimized shot-based encodes (Netflix)Articlenetflixtechblog.com](https://netflixtechblog.com/optimized-shot-based-encodes-now-streaming-4b9464204830)

[PreviousMaps & Navigation (routing, ETA)](/system-design/google-maps-navigation)[NextDistributed Lock / Coordination Service (ZooKeeper-like)](/system-design/distributed-lock-service)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

HotstarAmazonGoogleMicrosoftJioCinema

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
