# Proximity / Nearby Places Service (Yelp, Google Maps 'near me') — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/proximity-service

[All system design questions](/system-design)

#18HLDMediumHigh-level design

# Proximity / Nearby Places Service (Yelp, Google Maps 'near me')

geohashquadtreespatial indexread-heavy

## Problem statement

Design a service that returns businesses within a given radius of a user's location, with filters and ranking, for hundreds of millions of places and very high read traffic.

## Requirements

### Functional

* Return places within radius R of (lat, lng), paginated.
* Filters: category, open now, rating.
* Business owners add/update/delete places (low write rate).
* Place details page.

### Non-functional

* Search p99 < 100 ms.
* Highly available; reads must not depend on the write path.
* 200M places; 5k–20k search QPS.
* Eventual consistency for new places (minutes) is fine.

## Back-of-the-envelope estimates

* 200M places × ~1 KB details = 200 GB (relational + cache); geo index entries ~50 B each = 10 GB — fits in memory on a few nodes.
* 20k QPS reads; writes ~10/s.
* Geohash precision 6 (~1.2 km × 0.6 km) → ~200M / (cells covering land) ≈ tens of places per urban cell, more in dense cities → query 9 neighbouring cells and filter by exact distance.

## API

```
GET /v1/search/nearby?lat=&lng=&radius=1000&category=cafe&limit=20&cursor=
→ { places:[{id, name, distanceM, rating, lat, lng}], nextCursor }
GET /v1/places/{id}
POST/PUT/DELETE /v1/places  (owner/admin)
```

## Data model

```
places   (place_id, name, lat, lng, category, rating, address, hours, ...)
geo_index(geohash VARCHAR(6), place_id)  -- indexed on geohash; or a quadtree in memory
cache    Redis: cell:{geohash} → [place_ids], place:{id} → details
```

## High-level design

1. **Write path**: place service writes to the places DB (primary) and updates the geo index; replicas serve reads. Writes are rare, so no fancy pipeline.
2. **Read path**: location service computes the geohash of the query point and its 8 neighbours at the precision matching the radius (larger radius → shorter geohash), fetches place ids for those cells (cache → DB), computes exact haversine distance, filters, ranks, paginates.
3. **Index choices**: **geohash** (string prefix ranges, simple, works in any DB with a B-tree); **quadtree** (in-memory tree that adapts to density — dense cities get deeper nodes); **Google S2 / H3** cells (hierarchical, better edge handling). Geohash on a DB index is enough at this scale; quadtree in memory if you need sub-10 ms.
4. **Caching**: cell → ids in Redis with TTL; place details cached separately so a place update invalidates one key.
5. **Ranking**: distance, rating, popularity; can be a small model.

## Architecture diagram

Rendering diagram…

## Deep dives

**Why 9 cells**: a point near a cell edge has neighbours in adjacent cells; querying the 3×3 block guarantees coverage for radius ≤ cell size. For larger radii, drop to a shorter geohash.

**Precision vs density**: fixed geohash precision gives huge cells in Manhattan and empty ones in the desert; a quadtree subdivides until each leaf holds ≤ 100 places. Trade-off: quadtree must be rebuilt/kept in memory.

**Pagination**: cursor = (score, place\_id) after ranking; recompute per page (cheap) rather than storing result sets.

## Bottlenecks & mitigations

* Dense-city cells with thousands of places → deeper precision (7) in dense areas, or quadtree.
* Cache stampede on popular cells (airport, stadium) → request coalescing, short jittered TTLs.
* Read replica lag after a place update → owner sees own write via primary read; others eventually.

## Failure modes

* **Redis down**: replicas serve cell queries directly (indexed), higher latency but available.
* **Replica lag spike**: acceptable for this workload; alert if > minutes.
* **Bad data (place at 0,0)**: validation at write; geo bounds checks.

## Follow-up questions interviewers ask

* How would you support 'along my route' search?
* How would you handle moving objects (drivers) vs static places?
* How would you shard the index globally (by region)?

## Further reading

* [Guide: Proximity searchIllustrated guide on this site](/system-design/learn/proximity)

[PreviousCloud File Storage & Sync (Google Drive / Dropbox)](/system-design/cloud-file-storage)[NextMovie / Event Ticket Booking (BookMyShow)](/system-design/ticket-booking-system)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleUberSwiggyZomatoAmazonAirbnb

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
