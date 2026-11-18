# Nearby Friends (Live Location Sharing) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/nearby-friends

[All system design questions](/system-design)

#41HLDHardHigh-level design

# Nearby Friends (Live Location Sharing)

websocketspub/subgeospatialreal-time

## Problem statement

Design the backend for a mobile feature that shows a user which of their friends are currently nearby (e.g. within 5 miles), each with a distance and a last-updated time, refreshing every few seconds as people move. Unlike a *proximity service* for businesses, every location here changes constantly, and a user must only ever see friends who have opted in.

## Requirements

### Functional

* Show nearby friends (within a configurable radius, default 5 miles) with distance and last-seen timestamp.
* The list updates every few seconds as friends move; a friend who stops sharing drops off within ~10 minutes.
* Only mutual friends who have opted in can see each other; a user can pause sharing at any time.
* Keep a location history for analytics / ML (not needed to serve the feature).

### Non-functional

* Low latency: a location update should reach nearby friends within a few seconds.
* Reliability over strictness: losing an occasional update is fine; the service must stay available.
* Eventual consistency is acceptable for the location cache (replica lag of seconds is OK).
* Scale to hundreds of millions of daily users with tens of millions concurrently sharing.

## Back-of-the-envelope estimates

* 100M DAU use the feature, **10M concurrent** sharers. Each sends a location every 30 s → **~334k updates/s**.
* Average 400 friends, assume all share → each update fans out to 400 subscribers → **~134M messages/s** inside the system before distance filtering. (Most are discarded as too far away; the WebSocket tier never forwards them.)
* Location cache: 10M users × (user id 8 B + lat/lon 16 B + timestamp 8 B ≈ 32 B) ≈ **320 MB** — fits in one Redis node; shard for throughput, not size.
* Pub/sub channels: one per active user → 10M channels; each WebSocket server subscribes to the channels of its connected users' friends → **4B subscriptions** (10M users × 400) spread across the pub/sub cluster, ~200 bytes each ≈ **800 GB** of subscription state in memory → needs a cluster of ~100 nodes, which is the key scaling argument.
* Location history: 334k writes/s × 32 B ≈ 10 MB/s → ~900 GB/day; Cassandra-style time-series store.

## API

WebSocket (bidirectional, long-lived):

```
client → server   { type: "location_update", lat, lon, ts }
server → client   { type: "nearby_update", friends: [{ userId, lat, lon, ts, distanceKm }] }
client → server   { type: "subscribe",  friendIds: [...] }   // on connect / friend added
client → server   { type: "unsubscribe", friendIds: [...] }  // friend removed
```

REST (auxiliary):

```
GET  /v1/friends/nearby?lat&lon           seed the list once on app open
PUT  /v1/me/location-sharing { enabled }  opt in / pause
GET  /v1/friends                           friendship graph (cached)
```

## Data model

**Location cache** (Redis, TTL ~10 min so inactive users vanish):

```
key   loc:{userId}
value { lat, lon, ts }      SET … EX 600
```

**Location history** (Cassandra / time-series, write-heavy, rarely read):

```
user_id | ts | lat | lon          partition by user_id, clustered by ts desc
```

**User / friendship DB** (relational or graph): `friend(user_id, friend_id, since, sharing_enabled)`; cached per user as a friend-id set.

**Pub/sub**: one channel per user, `chan:{userId}`; messages carry `{userId, lat, lon, ts}`.

## High-level design

**Why not peer-to-peer?** Mobile clients have flaky connections and tight battery budgets, so the backend acts as the fan-out hub.

**Components**

* **Load balancer** — routes REST calls to API servers and WebSocket connects to the WebSocket tier (sticky by connection).
* **WebSocket servers (stateful)** — hold one connection per active user. On connect they load the user's friend list, **subscribe** to each friend's pub/sub channel, seed the client with current friend locations from the cache, and keep the user's own last location in memory for distance checks.
* **Redis location cache** — latest location per active user with TTL.
* **Redis pub/sub cluster** — one channel per user; the lightweight message bus that fans each update out to the WebSocket servers hosting that user's friends.
* **User DB** — profiles and friendships.
* **Location history DB** — append-only time series.

**Update flow**: client → WebSocket server → (a) write history, (b) `SET loc:{me}` in cache, (c) `PUBLISH chan:{me}`. Every WebSocket server subscribed to `chan:{me}` receives the message, computes the distance to each of *its* connected friends of mine, and forwards it only to those within the radius (the server already holds their latest positions in memory). Everything else is dropped — this is where the 134M/s collapses to a trickle.

**Friend added/removed**: the API server publishes a control message; the WebSocket server subscribes/unsubscribes the affected channel without a reconnect.

**Nearby strangers** (follow-up): same pipeline, but subscribe to geohash-cell channels (`geo:{cell}`) instead of per-user channels; users publish into the cells around them.

## Architecture diagram

Rendering diagram…

## Deep dives

**Scaling the WebSocket tier.** Stateful servers can be autoscaled, but *removing* one must be graceful: mark it draining in the load balancer, stop accepting connects, and let clients reconnect elsewhere (clients reconnect and re-subscribe on their own). Use a connection budget (~100k–500k connections per server with epoll/NIO).

**Scaling pub/sub.** The bottleneck is subscription memory and fan-out CPU, not channel count. Shard channels across pub/sub nodes by `hash(userId)` using a **consistent-hash ring** so a WebSocket server knows which node holds `chan:{friend}`. Resizing the cluster is disruptive (every subscription on moved channels must be re-established), so over-provision and resize during low traffic.

**Why Redis pub/sub and not Kafka?** Pub/sub here is fire-and-forget: no persistence, no consumer groups, millions of tiny channels with ad-hoc subscribe/unsubscribe. Kafka topics are heavy and partitions are not meant to be created per user. Alternatives: Erlang/Elixir processes (Discord/WhatsApp style), NATS, or a custom in-memory router.

**Users with thousands of friends.** A celebrity with 5,000 friends causes 5,000 subscriptions per connect and 5,000 fan-outs per update. Cap the feature (e.g. 1,000 friends), or for heavy users have the WebSocket server pull friend locations from the cache every few seconds instead of subscribing.

**Distance filtering at the edge.** Because every WebSocket server keeps the last known position of each *connected* user, it can filter without touching the cache. Haversine on 400 friends per update is trivial CPU.

**Privacy.** Only mutual, opted-in friends are subscribed; the server never forwards a location to anyone not in the friend set, and pausing sharing deletes `loc:{me}` and stops publishing. Keep precision coarse (≈100 m) for the feature while raw history stays in a restricted store.

**Alternative to pub/sub**: geohash-partitioned *location servers* that own a cell and keep all users in it in memory; WebSocket servers query the cells around a user every few seconds. Simpler state, but polling cost grows with user count and it is harder to restrict to friends.

## Bottlenecks & mitigations

* Pub/sub subscription memory (billions of subscriptions) → shard channels with consistent hashing across ~100 nodes; drop subscriptions when a user disconnects.
* Fan-out amplification (334k updates/s × 400 friends) → filter by distance on the WebSocket server; only forward to the handful of friends actually nearby.
* WebSocket server hot spots when many friends share one server → spread connections with a least-connections balancer and cap connections per server.
* Location history write volume (~900 GB/day) → batch writes through a queue (Kafka) into a wide-column store with TTL / compaction.

## Failure modes

* **WebSocket server dies**: its users reconnect to another server, which re-subscribes and re-seeds them from the cache; friends see a gap of a few seconds. No data is lost beyond in-flight updates.
* **Pub/sub node dies**: subscriptions on that node are gone; WebSocket servers detect the disconnect and re-subscribe once a replica is promoted. Updates during the window are dropped (acceptable by the requirements).
* **Redis location cache lost**: the feature shows stale/empty lists until users send their next update (≤30 s). Keep a replica; this store is cheap to rebuild.
* **Friend-list cache stale** after an unfriend: the ex-friend keeps receiving updates until the control message arrives — make the unfriend path publish synchronously and have the WebSocket server double-check the friendship on subscribe.
* **Client offline**: the server's TTL (10 min) expires `loc:{user}`, so friends stop seeing them without any explicit sign-off.

## Follow-up questions interviewers ask

* How would you extend this to *nearby strangers* (random people, not friends)?
* How do you resize the pub/sub cluster without dropping every subscription at once?
* What changes if updates must be delivered at least once (e.g. for a safety feature) rather than best-effort?
* How would you cut battery drain on the client while keeping freshness?
* How would you handle a user with 10,000 friends?

## Further reading

* [Guide: Live location sharingIllustrated guide on this site](/system-design/learn/live-location)

[PreviousConsistent Hashing (Data Partitioning)](/system-design/consistent-hashing)[NextS3-like Object Storage](/system-design/object-storage)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

MetaGoogleUberSnapMicrosoftSwiggy

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
