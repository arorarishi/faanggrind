# Movie / Event Ticket Booking (BookMyShow) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/ticket-booking-system

[All system design questions](/system-design)

#19HLDHardHigh-level design

# Movie / Event Ticket Booking (BookMyShow)

seat lockingconcurrencytransactionshigh contention

## Problem statement

Design a system where users browse shows, pick seats from a seat map, hold them briefly while paying, and get confirmed tickets — without two users ever getting the same seat, even when a blockbuster opens bookings.

## Requirements

### Functional

* Browse cities, theatres, movies, showtimes.
* View seat map with real-time availability.
* Select seats → temporary hold (e.g. 10 min) → pay → confirm.
* Cancel; refunds; e-ticket with QR.

### Non-functional

* No double booking under any circumstance (strong consistency for seats).
* Seat map loads < 300 ms; hold within 500 ms.
* Spikes: 1M users for a single show's opening minute.
* Availability for browsing even if booking is degraded.

## Back-of-the-envelope estimates

* 500k shows/day × 200 seats = 100M seat-show rows/day; keep 30 days ahead → 3B rows — partition by show.
* Peak: 1M users, one show, 2,000 seats: 1M seat-map reads/min (cache) and maybe 50k hold attempts/s on ~2k rows — extreme contention on a tiny hot set.
* Bookings: 5M/day ≈ 60/s — trivial write volume overall.

## API

```
GET  /v1/shows/{id}/seats            → seat map with status (available/held/booked), ETag
POST /v1/shows/{id}/holds            { seatIds[], idempotencyKey } → { holdId, expiresAt } | 409 {conflictingSeats}
POST /v1/bookings                     { holdId, paymentMethod }  → { bookingId, status }
DELETE /v1/holds/{holdId}
GET  /v1/bookings/{id}   (QR)
WS   show.{id}.seats  → seat status deltas
```

## Data model

```
shows      (show_id, movie_id, screen_id, starts_at, price_tiers)
seats      (screen_id, seat_id, row, number, tier)
show_seats (show_id, seat_id, status: AVAILABLE|HELD|BOOKED, hold_id, version)   PK (show_id, seat_id)
holds      (hold_id, show_id, user_id, seat_ids[], expires_at, status)
bookings   (booking_id, hold_id UNIQUE, user_id, show_id, amount, status, created_at)
payments   (payment_id, booking_id UNIQUE, ...)
```

## High-level design

1. **Catalogue** (movies, theatres, showtimes): read-heavy, cached, served from replicas/CDN.
2. **Seat map**: served from Redis (`show:{id}:seats` bitmap/hash) with WebSocket deltas; the DB is the truth, Redis a fast projection updated on every change.
3. **Hold** (the critical path): one DB transaction: `UPDATE show_seats SET status='HELD', hold_id=?, version=version+1 WHERE show_id=? AND seat_id IN (...) AND status='AVAILABLE'`; if the updated row count ≠ requested count → rollback, return 409 with the seats that were taken. Row-level locking + the status predicate guarantees no double hold. Hold row written with `expires_at`.
4. **Expiry**: a scheduler (or Redis keyspace expiry as a trigger) releases holds past `expires_at` back to AVAILABLE.
5. **Booking**: payment via the payment service (idempotent on `booking_id`); on success, seats move `HELD → BOOKED` in a transaction that checks `hold_id` matches and hold not expired.
6. **Spike protection**: virtual waiting room for hot shows; seat-map reads from cache; holds limited to N seats per user.
7. **Partitioning**: `show_seats` partitioned by `show_id` so a hot show is one partition on one primary — contention is inherent; keep transactions tiny.

## Architecture diagram

Rendering diagram…

## Deep dives

**Pessimistic vs optimistic**: the conditional `UPDATE` is optimistic concurrency at the row level — no explicit `SELECT … FOR UPDATE`, no lock ordering issues, and losers fail fast. For hot shows, an alternative is a single-threaded per-show allocator (actor) in memory backed by a write-ahead log, which removes DB contention entirely.

**Hold length**: 5–10 minutes balances abandonment vs fairness; show a countdown.

**Idempotent holds**: same `idempotencyKey` returns the same hold rather than a second one.

**Seat map freshness**: projection updates go through the same service that commits, in the same request, after the DB commit — small window of staleness, self-corrected by the WS delta.

## Bottlenecks & mitigations

* Hot show partition → keep hold transactions minimal; per-show actor for extreme cases; shard other shows away.
* Seat-map reads → Redis + WebSocket deltas so clients don't poll.
* Payment gateway TPS → waiting room admission matched to gateway capacity.
* Hold expiry scans → index on `expires_at`; or Redis TTL events.

## Failure modes

* **Payment succeeds but confirm transaction fails**: booking stays `pending`; reconciliation confirms or refunds; the hold is extended automatically while payment is pending.
* **Redis projection stale/lost**: rebuild from DB per show on demand; clients tolerate a 409 on hold.
* **Scheduler down**: holds linger; seats appear unavailable — degraded but safe; alert on oldest unexpired-past-due hold.
* **DB primary failover**: in-flight transactions roll back; clients retry with the same idempotency key.

## Follow-up questions interviewers ask

* How would you support best-available seat selection?
* How would you design dynamic pricing?
* How would you prevent scalper bots?

## Further reading

* [Guide: Hotel reservationsIllustrated guide on this site](/system-design/learn/reservations)

[PreviousProximity / Nearby Places Service (Yelp, Google Maps 'near me')](/system-design/proximity-service)[NextHotel Reservation System (Airbnb / Booking.com)](/system-design/hotel-reservation-system)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

BookMyShowAmazonPaytmFlipkartMicrosoft

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
