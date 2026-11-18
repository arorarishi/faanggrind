# Amazon Locker (package pickup) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-amazon-locker

[All system design questions](/system-design)

#59LLDMediumLow-level design

# Amazon Locker (package pickup)

allocationstateOTPexpiry

## Problem statement

Design the locker system: a delivery agent places a package into a suitable free locker slot at a location; the customer receives a one-time code, opens the locker, and picks up within a window; unclaimed packages are returned. Slots come in sizes; the system tracks availability and access codes securely.

## Requirements

### Functional

* Locations with lockers of sizes S/M/L; find a free slot fitting a package near the customer.
* Delivery: assign slot, store package, generate a 6-digit code valid for N days, notify customer.
* Pickup: validate code → open slot → mark picked up; code single-use.
* Expiry: after N days, notify and mark for return; agent retrieves.
* Returns via locker (customer drops, code for agent).

### Non-functional

* Slot allocation atomic; codes unguessable and single-use.
* Works offline-ish: locker unit can validate codes locally if the network is down (signed codes or synced list).
* Audit trail of every open event.

## API

```
Locker  allocate(locationId, Package)                    // smallest fitting free locker
AccessCode deliver(lockerId, Package, agentId)          // stores, generates code, notifies
PickupResult pickup(locationId, String code)             // validates + opens, single-use
void    markExpired()                                    // scheduler
AccessCode initiateReturn(orderId, locationId)
```

## Data model

* `LockerLocation(id, address,` List<Locker>`)`, `Locker(id, size, status: FREE|OCCUPIED|OUT_OF_SERVICE, package?,` AccessCode`?)`.
* `Package(id, orderId, size, customerId, status: IN_TRANSIT|IN_LOCKER|PICKED_UP|EXPIRED|RETURNED)`.
* `AccessCode(code, lockerId, packageId, expiresAt, used)`.
* `Customer`, `DeliveryAgent`.
* Services: `LockerAllocationService`, `AccessCodeService`, `NotificationService`, `ExpiryScheduler`.
* `SizeCompatibility: Package.size → allowed Locker.size` (S fits S/M/L…).

## Design

1. **Allocation strategy**: per location keep free lockers grouped by size in queues; pick the **smallest size** that fits (best-fit) so large lockers stay available; allocation + status change under a lock per location (or a conditional DB update `status='FREE'`).
2. **Access codes**: cryptographically random 6–8 digits stored hashed (like passwords) with expiry; validate by hashing input and comparing; mark `used` atomically. Rate-limit attempts per locker to stop brute force (10^6 space).
3. **State machines**: `Locker` (`FREE → OCCUPIED → FREE`), `Package` (`IN_TRANSIT → IN_LOCKER → PICKED_UP | EXPIRED → RETURNED`).
4. **Expiry scheduler**: daily job finds `IN_LOCKER` packages past `expiresAt`, notifies, marks `EXPIRED`, generates an agent retrieval code; locker freed on retrieval.
5. **Offline validation**: the locker kiosk periodically syncs the set of valid code hashes for its lockers; opens are queued and reconciled when online.
6. **Notifications** via observer on delivery/expiry/pickup events.

## Class diagram

Rendering diagram…

## Deep dives

**Best-fit allocation** keeps large lockers for large packages; consider reserving a fraction of large lockers.

**Code security**: never store plaintext; hash + attempt limits + short expiry. QR codes carry a signed token instead of a number.

**Idempotent delivery**: a package can be delivered once; re-scans return the same code.

**Return flow** reuses allocation with the customer as the depositor and the agent as the picker.

## Bottlenecks & mitigations

* Code lookup by hash across all locations → index by (location, hash); codes are per location.
* Peak delivery hours contention per location → per-location lock is short; fine.
* Brute-force attempts → per-locker attempt counter and lockout.

## Failure modes

* **Locker door fails to open** → keep code valid, log fault, offer alternative locker or support.
* **Network down at kiosk** → offline validation via synced hashes; queue events.
* **Package placed in the wrong locker** → agent scan verifies locker id before close; mismatch alert.
* **Customer never picks up** → expiry → return flow; locker freed only after agent retrieval.

## Code skeleton

```
import secrets, hashlib, time
from collections import deque
from threading import Lock

SIZES = ["S", "M", "L"]
class Locker:
    def __init__(self, lid, size): self.id, self.size, self.package, self.code = lid, size, None, None

class Location:
    def __init__(self, lockers):
        self.free = {s: deque(l for l in lockers if l.size == s) for s in SIZES}
        self.by_id, self.lock = {l.id: l for l in lockers}, Lock()
    def allocate(self, pkg_size):
        with self.lock:
            for s in SIZES[SIZES.index(pkg_size):]:
                if self.free[s]: return self.free[s].popleft()
        raise Exception("no locker available")
    def release(self, locker):
        with self.lock: locker.package = locker.code = None; self.free[locker.size].append(locker)

class AccessCode:
    def __init__(self, locker_id, ttl_days=3):
        self.plain = f"{secrets.randbelow(10**6):06d}"
        self.hash, self.locker_id = hashlib.sha256(self.plain.encode()).hexdigest(), locker_id
        self.exp, self.used, self.attempts = time.time() + ttl_days*86400, False, 0
    def matches(self, code):
        return hashlib.sha256(code.encode()).hexdigest() == self.hash

class LockerService:
    def __init__(self, location): self.loc, self.codes = location, {}
    def deliver(self, package):
        locker = self.loc.allocate(package["size"]); locker.package = package
        code = AccessCode(locker.id); locker.code = code; self.codes[code.hash] = code
        package["status"] = "IN_LOCKER"; return code.plain            # send to customer, then forget plaintext
    def pickup(self, code_input):
        h = hashlib.sha256(code_input.encode()).hexdigest(); code = self.codes.get(h)
        if not code or code.used or time.time() > code.exp: raise Exception("invalid or expired code")
        locker = self.loc.by_id[code.locker_id]; code.used = True
        pkg = locker.package; pkg["status"] = "PICKED_UP"; self.loc.release(locker); return locker.id, pkg
    def expire(self):
        for code in list(self.codes.values()):
            if not code.used and time.time() > code.exp:
                locker = self.loc.by_id[code.locker_id]
                if locker.package: locker.package["status"] = "EXPIRED"
```

## Follow-up questions interviewers ask

* Add locker reservation at checkout (size estimate from cart).
* Add multi-package consolidation into one locker.
* How would you place lockers and size the mix from demand data?

[PreviousMeeting Scheduler / Calendar](/system-design/lld-meeting-scheduler)[NextStack Overflow (Q&A platform) — LLD](/system-design/lld-stack-overflow)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonFlipkartWalmartMicrosoft

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
