# Hotel Reservation System (Airbnb / Booking.com) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/hotel-reservation-system

[All system design questions](/system-design)

#20HLDMediumHigh-level design

# Hotel Reservation System (Airbnb / Booking.com)

inventory by dateoverbookingsearchconsistency

## Problem statement

Design a hotel booking platform: search rooms by location and dates, reserve a room type for a date range, pay, manage cancellations — with inventory tracked per room type per night.

## Requirements

### Functional

* Search hotels by location, dates, guests; show availability and price.
* Reserve a room type for a date range; confirm after payment.
* Cancel/modify with policy-based refunds.
* Hotel admins manage rooms, rates, inventory.
* Optional controlled overbooking (e.g. 10%).

### Non-functional

* Reservations strongly consistent: never below zero inventory beyond the overbooking allowance.
* Search p99 < 500 ms; reads scale independently.
* 5M hotels, 100M room-nights of inventory in a 2-year window.
* Multi-currency pricing.

## Back-of-the-envelope estimates

* Inventory rows: 5M hotels × 3 room types × 730 days ≈ **11B rows** (hotel\_id, room\_type, date, total, reserved) → partition by hotel\_id; ~50 B/row → 550 GB.
* Reservations: 1M/day ≈ 12/s; writes tiny.
* Search: 100M/day ≈ 1.2k/s; each search touches up to 30 nights × N hotels → precomputed availability caches per (city, date).

## API

```
GET  /v1/hotels/search?city=&checkin=&checkout=&guests=   → hotels with min price & availability
GET  /v1/hotels/{id}/rooms?checkin=&checkout=
POST /v1/reservations   { hotelId, roomTypeId, checkin, checkout, guests, idempotencyKey } → { reservationId, status }
POST /v1/reservations/{id}/pay
DELETE /v1/reservations/{id}
PUT  /v1/admin/hotels/{id}/inventory  { roomTypeId, date, total }
```

## Data model

```
hotels        (hotel_id, name, geo, address, ...)
room_types    (room_type_id, hotel_id, name, capacity)
rates         (room_type_id, date, price, currency)
room_inventory(hotel_id, room_type_id, date, total_rooms, reserved_rooms, version)  PK(hotel_id, room_type_id, date)
reservations  (reservation_id, user_id, hotel_id, room_type_id, checkin, checkout, status, amount, idempotency_key UNIQUE)
```

Inventory is per **room type per night**, not per physical room — assignment to a physical room happens at check-in.

## High-level design

1. **Search service**: Elasticsearch for hotel attributes + geo; availability from a **date-range availability cache** (per hotel/room type: bitmap of available nights) so search filters on availability without hitting the inventory DB. Cache updated on every reservation change.
2. **Reservation service**: in one transaction, for each night in `[checkin, checkout)`: `UPDATE room_inventory SET reserved_rooms = reserved_rooms + 1 WHERE … AND reserved_rooms + 1 <= total_rooms * (1 + overbook_pct)`. If any night fails → rollback → 409. Then insert the reservation as `pending_payment` with a TTL.
3. **Payment** via the payment service; success → `confirmed`; timeout → release inventory.
4. **Rates**: per-date pricing table; total computed at reservation time and stored (price lock).
5. **Sharding**: inventory and reservations sharded by `hotel_id` so a reservation's nights are in one shard → single-shard transaction.
6. **Hotel admin** writes inventory/rates; changes publish events for the availability cache.

## Architecture diagram

Rendering diagram…

## Deep dives

**Per-night inventory** is the key modelling decision: it makes overlapping stays trivial (each night is an independent counter) and search fast (bitmaps), at the cost of many rows — fine when partitioned.

**Overbooking**: `total × (1 + pct)` in the predicate; ops dashboards show hotels over 100%.

**Long stays**: a 30-night reservation updates 30 rows in one transaction — acceptable; cap stay length.

**Rate/price consistency**: store the computed price on the reservation; rate changes never affect existing bookings.

## Bottlenecks & mitigations

* Popular hotel on popular dates → contention on a few inventory rows; keep transactions short, retry with jitter.
* Search fan-out over availability → bitmaps in cache; precompute per (city, month).
* Availability cache invalidation lag → search may show a room that just sold; reservation returns 409 and search refreshes.

## Failure modes

* **Payment fails/times out**: reservation TTL expiry releases the nights.
* **Availability cache stale**: worst case a 409 at reservation — never an overbooking.
* **Shard down**: only that hotel set is unbookable; search degrades to 'availability unknown'.
* **Double reservation on retry**: idempotency key unique constraint.

## Follow-up questions interviewers ask

* How would you implement dynamic pricing?
* How would you handle a hotel that sells inventory on multiple platforms (channel manager)?
* How would you model physical room assignment and upgrades?

## Further reading

* [Guide: Hotel reservationsIllustrated guide on this site](/system-design/learn/reservations)

[PreviousMovie / Event Ticket Booking (BookMyShow)](/system-design/ticket-booking-system)[NextStock Exchange / Order Matching Engine](/system-design/stock-exchange)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AirbnbBooking.comAmazonMakeMyTripMicrosoft

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
