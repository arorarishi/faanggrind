# Ride-Sharing Service (Uber / Ola) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/ride-sharing

[All system design questions](/system-design)

#10HLDHardHigh-level design

# Ride-Sharing Service (Uber / Ola)

geospatialmatchingreal-time locationpricing

## Problem statement

Design the core of a ride-hailing app: riders request a trip, nearby drivers are matched, both parties see live locations, and the trip is priced and paid.

## Requirements

### Functional

* Drivers stream their location; riders see nearby cars.
* Rider requests a ride; system matches an available nearby driver who can accept/decline.
* Live trip tracking, ETA, route.
* Fare estimate before booking; surge pricing; payment at the end.
* Trip history, ratings.

### Non-functional

* Matching within 5–10 s; location updates visible within 1–2 s.
* High availability — the matching path is revenue-critical.
* Scale: 5M drivers online at peak, each sending a location every 4 s.
* Consistency where money is involved (one driver per trip, one charge per trip).

## Back-of-the-envelope estimates

* Location ingest: 5M drivers / 4 s = **1.25M updates/s**. ~50 B each → 60 MB/s; must be handled in memory (Redis / custom index), never a relational DB.
* Trips: 20M/day ≈ 230/s, peaks ~2k/s; trip records ~2 KB → 40 GB/day — relational is fine.
* Nearby query: geohash cell at precision 6 ≈ 1.2 km × 0.6 km; a city-centre cell may hold 500 drivers; query 9 cells → few thousand candidates, filtered by road distance.

## API

```
POST /v1/drivers/location   { lat, lng, heading, ts }         (every 4 s, over WebSocket/gRPC stream)
GET  /v1/riders/nearby?lat&lng                                  → cars within radius
POST /v1/rides/estimate      { pickup, drop }                   → { fare, eta, surge }
POST /v1/rides               { pickup, drop, paymentMethod }    → { rideId, status:"matching" }
POST /v1/rides/{id}/accept   (driver)  / POST /v1/rides/{id}/decline
WS   ride.{id} events: matched, arriving, started, completed
POST /v1/rides/{id}/complete → triggers payment
```

## Data model

```
drivers          (driver_id, status: offline|available|on_trip, vehicle, rating)
driver_locations Redis GEO / in-memory grid: geohash → set(driver_id), driver_id → (lat,lng,ts)
rides            (ride_id, rider_id, driver_id, status, pickup, drop, fare, surge, created_at, ...)  -- relational, ACID
ride_events      (ride_id, event, ts)  -- append-only
payments         (payment_id, ride_id UNIQUE, amount, status)
```

## High-level design

1. **Location service**: drivers push locations over a persistent connection to gateway servers, which write to an in-memory geospatial index (Redis GEO or a sharded quadtree/geohash grid), partitioned by city/region. Only the latest location per driver is kept; a sample is streamed to Kafka for analytics.
2. **Matching service**: on a ride request, query the index for available drivers in the surrounding geohash cells, rank by ETA (using the routing service), and **offer** the ride to the best driver with a 15 s timeout, then the next. Driver state transitions are done with an atomic compare-and-set (`available → offered → on_trip`) so two riders can never lock the same driver.
3. **Trip service**: owns the ride state machine in a relational DB; publishes events consumed by notifications, pricing, analytics.
4. **Pricing**: base fare + distance/time from routing + surge multiplier computed per geohash cell from supply/demand over the last few minutes.
5. **Routing/ETA service**: map data + traffic; heavy compute, cached per (cell, cell).
6. **Payments**: on completion, create a payment with `ride_id` unique; idempotent charge via the payment gateway.

## Architecture diagram

Rendering diagram…

## Deep dives

**Why geohash/quadtree over a DB**: 1.25M writes/s of ephemeral data; only 'latest position' matters. Redis GEO gives `GEORADIUS` in microseconds; shard by city so a cell never spans shards.

**Avoiding double booking**: driver state lives in a store that supports atomic CAS (Redis `SET NX`/Lua or a DB row lock). The offer holds the driver for the timeout window only.

**Surge**: computed per cell every 30–60 s from open requests vs available drivers; shown to the rider before confirmation and locked into the ride at booking.

**ETA accuracy**: precompute cell-to-cell travel times; refine with the routing engine only for the top few candidates.

## Bottlenecks & mitigations

* Location write throughput → in-memory index, batching on the gateway, drop updates that moved < 10 m.
* Matching in dense areas (thousands of candidates) → cap candidates by nearest cells, pre-filter by heading/availability, parallel ETA lookups.
* Routing service load → cache cell-pair ETAs; degrade to straight-line × factor under load.
* Rides DB writes at peak → fine at 2k/s; keep events append-only, archive completed rides.

## Failure modes

* **Geo index shard loss**: drivers re-send positions within 4 s, so the index self-heals; brief degradation in that city only.
* **Driver accepts but network drops**: ride stays `offered` until timeout, then re-offered; if the driver's accept arrives late it is rejected with a clear message.
* **Payment gateway failure**: ride completes, payment marked `pending`, retried asynchronously; rider can't book again until settled (policy).
* **Matching service outage**: ride requests queue; riders see 'finding drivers' longer; auto-cancel after N minutes.

## Follow-up questions interviewers ask

* How would you support pooled rides (shared trips)?
* How would you design driver-side dispatch to reduce idle time?
* How would you handle a city-wide event (concert) surge?

[PreviousSearch Autocomplete / Typeahead](/system-design/search-autocomplete)[NextFood Delivery Platform (Swiggy / Zomato)](/system-design/food-delivery-platform)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

UberOlaAmazonGoogleSwiggyMicrosoft

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
