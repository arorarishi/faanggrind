# Maps & Navigation (routing, ETA) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/google-maps-navigation

[All system design questions](/system-design)

#33HLDHardHigh-level design

# Maps & Navigation (routing, ETA)

graphshortest pathtilesgeospatial

## Problem statement

Design the core of a maps product: render map tiles, compute routes between points with turn-by-turn directions and ETA that accounts for traffic, and update location during navigation.

## Requirements

### Functional

* Display map at any zoom level; pan/zoom; search places.
* Route from A to B (driving/walking) with alternatives and ETA.
* Live navigation: re-route when off course; traffic-aware.
* Collect anonymised location data to estimate traffic.

### Non-functional

* Tile load < 100 ms (CDN); route computation < 1 s for intercity.
* Accuracy: ETA within ~10%.
* 1B users; 100M navigations/day.
* Global data: 100M+ road segments.

## Back-of-the-envelope estimates

* Road graph: ~1B nodes/edges worldwide; with contraction hierarchies preprocessing, in-memory per continent ≈ tens of GB — fits on big machines, partitioned by region.
* Tiles: 21 zoom levels; ~4^21 tiles at max zoom is impractical to precompute → precompute z0–z14, render/cache deeper on demand; CDN handles delivery.
* Location pings during navigation: 100M sessions × 1 ping/5 s over avg 30 min ≈ 36B/day ≈ 400k/s → stream to a traffic pipeline.
* Route requests: 100M/day ≈ 1.2k/s average; peaks 10k/s.

## API

```
GET  /v1/tiles/{z}/{x}/{y}.pbf            (vector tiles, CDN-cached)
GET  /v1/route?from=lat,lng&to=lat,lng&mode=driving&departAt=  → { legs[], steps[], distanceM, durationS, polyline }
POST /v1/navigation/{sessionId}/location   { lat, lng, speed, heading, ts }  → { rerouted?: route }
GET  /v1/eta?from&to                       (lightweight)
GET  /v1/search?q=&near=                   (places)
```

## Data model

```
road_graph   nodes(id, lat, lng), edges(id, from, to, length_m, speed_limit, road_class, restrictions, geometry)
ch_index     precomputed shortcuts/levels for contraction hierarchies, per region
traffic      edge_id → current_speed (Redis, TTL minutes) ; historical speed profiles by (edge, weekday, 15-min bucket)
tiles        object storage / tile cache keyed by (z,x,y, style_version)
places       search index (see proximity service)
```

## High-level design

1. **Map data pipeline**: ingest OSM/vendor data → build the road graph → validate → publish versioned graph snapshots and pre-rendered **vector tiles** (z0–14) to object storage + CDN.
2. **Tile service**: CDN → tile cache → on-demand renderer for deep zooms; clients render vector tiles locally.
3. **Routing service**: per-region servers hold the graph + **contraction hierarchies** (or CRP) in memory; a query = bidirectional Dijkstra on the CH, returning a path in ms even for 1,000 km. Edge weights = time using live traffic where fresh, historical profile otherwise. Cross-region routes stitch via border nodes.
4. **Traffic service**: ingests navigation pings (Kafka), map-matches them to edges (HMM map matching), aggregates speeds per edge per minute, and publishes current speeds; historical profiles computed offline.
5. **Navigation service**: keeps the session's route; on each ping, checks distance from the route; if off-route beyond a threshold, requests a reroute; sends the next instruction.
6. **Places search** uses the proximity/search design.

## Architecture diagram

Rendering diagram…

## Deep dives

**Contraction hierarchies**: preprocess by contracting unimportant nodes and adding shortcut edges; queries become tiny bidirectional searches. Trade-off: preprocessing takes hours and live traffic changes weights → use *customisable* CH/CRP where metric customisation takes seconds.

**Map matching**: raw GPS is noisy; an HMM over candidate edges with transition probabilities from road distance yields the true path.

**ETA**: sum of edge travel times using time-dependent speeds (departure time matters); ML correction models on top for turn delays, signals.

**Alternatives**: penalise the found path's edges and re-run, or plateau method; ensure alternatives are meaningfully different.

**Privacy**: pings anonymised, sessions rotated, aggregated before storage.

## Bottlenecks & mitigations

* Route computation at peak → in-memory graphs, CH; cache popular OD pairs at coarse granularity.
* Traffic ingestion → Kafka + stream aggregation; sample pings on dense roads.
* Tile rendering for deep zoom → on-demand with caching; vector tiles offload styling to clients.
* Graph updates (road closures) → hot-patch edge weights in the traffic layer; full graph rebuilds nightly.

## Failure modes

* **Traffic service down**: routing falls back to historical profiles; ETAs less accurate but available.
* **Regional routing server loss**: replicas per region; cross-region stitch continues.
* **Bad map data release**: versioned snapshots; canary a region; instant rollback.
* **GPS loss in tunnels**: dead reckoning on the client; server tolerates gaps.

## Follow-up questions interviewers ask

* How would you support multi-stop route optimisation (delivery)?
* How would you model turn restrictions and time-based closures?
* How would you compute an isochrone (all points reachable in 15 min)?

## Further reading

* [Guide: Maps and navigationIllustrated guide on this site](/system-design/learn/maps)

[PreviousCollaborative Document Editing (Google Docs)](/system-design/collaborative-document-editing)[NextLive Video Streaming (Twitch / Hotstar live match)](/system-design/live-streaming-platform)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleUberOlaAmazonSwiggyMicrosoft

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
