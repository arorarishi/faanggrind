# Parking Lot — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-parking-lot

[All system design questions](/system-design)

#43LLDEasyLow-level design

# Parking Lot

strategyfactorystateOOP

## Problem statement

Design a parking lot with multiple floors and spot types (motorcycle, compact, large, electric). Vehicles enter, get a ticket, park in a suitable spot, and pay on exit based on duration. The system must track availability and support multiple entry/exit gates.

## Requirements

### Functional

* Multiple floors; spots of different sizes; a vehicle fits only in compatible spots.
* Issue a ticket at entry with timestamp and assigned spot; free the spot at exit.
* Fee calculation by vehicle type and duration; multiple payment methods.
* Display available spots per floor/type; handle a full lot.

### Non-functional

* Thread-safe spot assignment (concurrent gates).
* Extensible: new vehicle types, pricing rules, spot-allocation strategies without touching core classes.
* Spot lookup near O(1)/O(log n).

## API

```
Ticket  ParkingLot.parkVehicle(Vehicle v, EntryGate g)       throws LotFullException
Receipt ParkingLot.unparkVehicle(Ticket t, PaymentMethod m, ExitGate g)
int     ParkingLot.availableSpots(SpotType type)
ParkingSpot SpotAllocationStrategy.findSpot(List<ParkingFloor>, VehicleType)
Money   PricingStrategy.calculate(Ticket t)
```

## Data model

**Core entities**

* `ParkingLot` (singleton-ish aggregate): floors, gates, `SpotAllocationStrategy`, `PricingStrategy`.
* `ParkingFloor`: id, `Map<SpotType, Set<ParkingSpot>>` available, display board.
* `ParkingSpot` (abstract) → `CompactSpot`, `LargeSpot`, `MotorcycleSpot`, `ElectricSpot`; fields: id, floor, `isFree`, `vehicle`.
* `Vehicle` (abstract) → `Car`, `Motorcycle`, `Truck`, `ElectricCar`; `licensePlate`, `VehicleType`.
* `Ticket`: id, vehicle, spot, entryTime, exitTime, status.
* `EntryGate` / `ExitGate`.
* `PricingStrategy` (interface) → `HourlyPricing`, `FlatRatePricing`.
* `Payment` (abstract) → `CashPayment`, `CardPayment`, `UpiPayment`.

## Design

1. **Strategy** for spot allocation (`NearestToEntry`, `FirstAvailable`, `LowestFloorFirst`) and pricing (`Hourly`, `Flat`, `Weekend`) — swap without changing `ParkingLot`.
2. **Factory** for vehicles and spots from type enums.
3. **State** on `Ticket` (`ACTIVE → PAID → EXITED`) and on `ParkingSpot` (`FREE / OCCUPIED / OUT_OF_SERVICE`).
4. **Observer**: display boards subscribe to spot events and refresh counts.
5. **Compatibility matrix**: `VehicleType → List<SpotType>` ordered by preference (motorcycle can use motorcycle/compact/large).
6. **Concurrency**: each floor keeps available spots in a concurrent set per type; `findSpot` + `occupy` done atomically (compare-and-set on the spot, or a lock per floor).

## Class diagram

Rendering diagram…

## Deep dives

**Key flow — park**: gate → `parkVehicle` → allocator picks a spot (lock floor) → `spot.occupy(vehicle)` → create `Ticket` → notify display → return ticket.

**Key flow — unpark**: ticket lookup → `pricing.calculate` → `payment.pay` → `spot.release` → ticket `EXITED` → notify.

**Why strategy for pricing**: pricing changes constantly (weekend rates, EV discount); isolating it prevents `ParkingLot` churn.

**Why not put `findSpot` in `ParkingSpot`**: allocation is a lot-wide policy; spots should only know their own state.

## Bottlenecks & mitigations

* Global lock on the whole lot serialises all gates → lock per floor or per spot type; CAS on the spot.
* Linear scan for a free spot → keep per-type free sets/queues; nearest-to-gate needs a min-heap per gate.
* Ticket map growing → evict on exit; persist to a DB in a real system.

## Failure modes

* **Lot full**: raise a clear exception; display boards show 'FULL'; entry gate stays closed.
* **Lost ticket**: lookup by plate (index `plate → ticket`) with a penalty fee rule.
* **Power/crash mid-parking**: spots must be persisted; on restart rebuild free sets from occupied spots.
* **Vehicle in wrong spot type** (manual override): admin API to reassign; audit log.

## Code skeleton

```
from abc import ABC, abstractmethod
from enum import Enum
from threading import Lock
import time, uuid

class VehicleType(Enum): MOTORCYCLE=1; CAR=2; TRUCK=3
class SpotType(Enum): MOTORCYCLE=1; COMPACT=2; LARGE=3
COMPAT = {VehicleType.MOTORCYCLE:[SpotType.MOTORCYCLE,SpotType.COMPACT,SpotType.LARGE],
          VehicleType.CAR:[SpotType.COMPACT,SpotType.LARGE],
          VehicleType.TRUCK:[SpotType.LARGE]}

class Vehicle:
    def __init__(self, plate, vtype): self.plate, self.type = plate, vtype

class ParkingSpot:
    def __init__(self, sid, stype): self.id, self.type, self.vehicle = sid, stype, None
    def is_free(self): return self.vehicle is None

class ParkingFloor:
    def __init__(self, no, spots):
        self.no, self.lock = no, Lock()
        self.free = {t: {s for s in spots if s.type == t} for t in SpotType}
    def take(self, vtype):
        with self.lock:
            for st in COMPAT[vtype]:
                if self.free[st]:
                    return self.free[st].pop()
        return None
    def give_back(self, spot):
        with self.lock: self.free[spot.type].add(spot)

class Ticket:
    def __init__(self, vehicle, spot):
        self.id, self.vehicle, self.spot = uuid.uuid4().hex[:8], vehicle, spot
        self.entry, self.exit = time.time(), None

class PricingStrategy(ABC):
    @abstractmethod
    def calculate(self, ticket) -> float: ...
class HourlyPricing(PricingStrategy):
    RATE = {VehicleType.MOTORCYCLE:10, VehicleType.CAR:20, VehicleType.TRUCK:40}
    def calculate(self, t):
        hours = max(1, int((t.exit - t.entry) // 3600 + 1))
        return hours * self.RATE[t.vehicle.type]

class ParkingLot:
    def __init__(self, floors, pricing): self.floors, self.pricing, self.tickets = floors, pricing, {}
    def park(self, vehicle):
        for f in self.floors:
            spot = f.take(vehicle.type)
            if spot:
                spot.vehicle = vehicle
                t = Ticket(vehicle, spot); self.tickets[t.id] = t; return t
        raise Exception("Lot full")
    def unpark(self, ticket_id):
        t = self.tickets.pop(ticket_id); t.exit = time.time()
        fee = self.pricing.calculate(t)
        t.spot.vehicle = None
        for f in self.floors:
            if t.spot in sum((list(v) for v in f.free.values()), []) or True:
                pass
        self.floors[0].give_back(t.spot)  # in practice: spot.floor.give_back(spot)
        return fee
```

## Follow-up questions interviewers ask

* Add EV charging spots with a separate charging fee.
* Add reservations for a time window.
* Support multiple lots with a central availability service.

[PreviousS3-like Object Storage](/system-design/object-storage)[NextElevator System](/system-design/lld-elevator-system)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoldman SachsAdobeFlipkartAtlassian

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
