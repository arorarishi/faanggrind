# Movie Ticket Booking (BookMyShow) — LLD — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-movie-ticket-booking

[All system design questions](/system-design)

#47LLDMediumLow-level design

# Movie Ticket Booking (BookMyShow) — LLD

concurrencystatelockingOOP

## Problem statement

Design the object model and seat-locking logic for a ticket booking system: cities, theatres, screens, shows, seats; a user selects seats for a show, seats are temporarily locked, payment completes the booking, and locks expire if unpaid. No two users may book the same seat.

## Requirements

### Functional

* Browse shows by city/movie/theatre; view seat availability for a show.
* Lock selected seats for a user for N minutes; confirm after payment; release on timeout/cancel.
* Booking history; cancellation with refund policy.

### Non-functional

* Correct under concurrent lock attempts (no double booking).
* Lock provider pluggable (in-memory, DB, Redis).
* Clear separation of catalogue vs booking concerns.

## API

```
List<Show> ShowService.getShows(cityId, movieId, date)
List<ShowSeat> SeatAvailabilityService.getAvailableSeats(showId)
Booking BookingService.createBooking(userId, showId, List<seatId>)      // locks seats, PENDING
Booking BookingService.confirm(bookingId, paymentDetails)             // validates locks, BOOKED
void    BookingService.cancel(bookingId)
```

## Data model

* `City`, `Theatre(city, screens)`, `Screen(theatre, seats)`, `Seat(id, row, col, SeatType)`.
* `Movie(id, title, duration)`, `Show(id, movie, screen, startTime, pricing)`.
* `ShowSeat(show, seat, status: AVAILABLE|LOCKED|BOOKED, lockedBy, lockedAt)` — the per-show projection of a physical seat.
* `SeatLockProvider` (interface): `lockSeats(show, seats, user)`, `unlockSeats`, `validateLock(show, seat, user)`, `getLockedSeats(show)`.
* `Booking(id, show, user, seats, status: PENDING|CONFIRMED|CANCELLED, amount)`.
* `Payment` and `PaymentStrategy`.
* Services: `TheatreService`, `ShowService`, `BookingService`, `PaymentService`, `SeatAvailabilityService`.

## Design

1. **Lock-then-pay**: `createBooking` asks `SeatLockProvider.lockSeats` atomically for all requested seats; if any is locked/booked by someone else, fail the whole request (all-or-nothing).
2. **In-memory lock provider**: `Map<Show, Map<Seat, SeatLock{user, expiry}>>` guarded by a lock per show (`synchronized` on the show's map or a `ReentrantLock` per show). Expired locks are treated as free when checked.
3. **Confirm**: validate every seat is still locked *by this user* and not expired → mark `BOOKED` in the show's seat map → booking `CONFIRMED` → release locks.
4. **Expiry**: a scheduler sweeps expired locks, or expiry is lazy (checked on access). With Redis: `SET key user NX PX ttl` per seat plus a Lua script for all-or-nothing.
5. **State pattern** on `Booking`: transitions validated (`PENDING → CONFIRMED | CANCELLED`, `CONFIRMED → CANCELLED` with refund rules).
6. **Catalogue services** are read-mostly and independent; only `BookingService` touches seat state.

## Class diagram

Rendering diagram…

## Deep dives

**Atomic multi-seat lock**: check all, then lock all, under one lock per show; otherwise two users can each get half of a pair.

**Why ShowSeat exists**: a physical `Seat` belongs to a screen; its availability is per show — never store status on `Seat`.

**Lock ownership**: validating `lockedBy == user` at confirm prevents a user from confirming seats another user locked after theirs expired.

**Pricing**: `Show` carries a `Map<SeatType, Money>`; booking amount computed at lock time and stored.

## Bottlenecks & mitigations

* Lock per show serialises all users of a hot show → acceptable (operations are microseconds); shard by show across servers.
* Expired-lock sweeping → lazy checks on access plus a periodic cleaner.
* In-memory provider is single-node → swap for Redis/DB provider via the interface.

## Failure modes

* **Payment success but confirm fails** (lock expired due to slow payment) → extend locks while payment is in progress; else refund and inform.
* **Process crash** → in-memory locks lost; a persistent provider (Redis TTL/DB) is required in production.
* **User closes the app** → locks expire naturally.
* **Cancellation after show start** → policy check in `cancel` (state + time rule).

## Code skeleton

```
import time
from threading import Lock
from collections import defaultdict

class SeatLock:
    def __init__(self, user, ttl): self.user, self.exp = user, time.time() + ttl
    def expired(self): return time.time() > self.exp

class InMemorySeatLockProvider:
    def __init__(self, ttl=600):
        self.ttl, self.locks, self.mutex = ttl, defaultdict(dict), defaultdict(Lock)
    def lock_seats(self, show, seats, user):
        with self.mutex[show]:
            held = self.locks[show]
            for s in seats:
                lk = held.get(s)
                if lk and not lk.expired() and lk.user != user:
                    raise Exception(f"seat {s} unavailable")
            for s in seats: held[s] = SeatLock(user, self.ttl)
    def validate(self, show, seat, user):
        lk = self.locks[show].get(seat)
        return bool(lk) and not lk.expired() and lk.user == user
    def unlock(self, show, seats, user):
        with self.mutex[show]:
            for s in seats:
                lk = self.locks[show].get(s)
                if lk and lk.user == user: del self.locks[show][s]

class BookingService:
    def __init__(self, lock_provider):
        self.lp, self.booked, self.bookings, self.mutex = lock_provider, defaultdict(set), {}, defaultdict(Lock)
    def create(self, user, show, seats):
        with self.mutex[show]:
            if any(s in self.booked[show] for s in seats): raise Exception("already booked")
            self.lp.lock_seats(show, seats, user)
        b = {"id": len(self.bookings)+1, "user": user, "show": show, "seats": seats, "status": "PENDING"}
        self.bookings[b["id"]] = b; return b
    def confirm(self, bid, pay_ok=True):
        b = self.bookings[bid]
        if not pay_ok: raise Exception("payment failed")
        with self.mutex[b["show"]]:
            if not all(self.lp.validate(b["show"], s, b["user"]) for s in b["seats"]):
                raise Exception("lock expired")
            self.booked[b["show"]].update(b["seats"]); b["status"] = "CONFIRMED"
            self.lp.unlock(b["show"], b["seats"], b["user"])
        return b
```

## Follow-up questions interviewers ask

* Add seat categories with different hold times.
* Support group bookings that must be adjacent.
* How does this map to the HLD (DB rows, Redis, waiting room)?

[PreviousSplitwise (expense sharing)](/system-design/lld-splitwise)[NextBoard Games: Tic-Tac-Toe / Snake & Ladder](/system-design/lld-tic-tac-toe-snake-ladder)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

FlipkartAmazonMicrosoftBookMyShowPaytm

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Design](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Bottlenecks](#bottlenecks)
9. [Failure modes](#failures)
10. [Code skeleton](#code)
11. [Follow-ups](#follow-ups)

## Your notes

Saved

Autosaves to this browser.
