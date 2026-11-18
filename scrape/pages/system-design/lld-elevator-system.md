# Elevator System — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-elevator-system

[All system design questions](/system-design)

#44LLDMediumLow-level design

# Elevator System

state machineschedulingstrategyobserver

## Problem statement

Design the control system for a building with multiple elevators: handle hall calls (up/down buttons on floors) and car calls (floor buttons inside), move elevators efficiently, open/close doors, and respect capacity and emergency states.

## Requirements

### Functional

* Multiple elevators; N floors; external (hall) and internal (car) requests.
* Dispatch a hall call to the best elevator; serve requests in an efficient order.
* Door open/close with timers and obstruction sensor; overload detection.
* Maintenance/emergency modes; display current floor and direction.

### Non-functional

* Real-time responsiveness; no starvation of any floor.
* Pluggable dispatch algorithms (nearest car, SCAN/LOOK, load-balanced).
* Thread-safe request queues; each elevator runs independently.

## API

```
void ElevatorSystem.requestElevator(int floor, Direction dir)   // hall button
void Elevator.selectFloor(int floor)                             // car button
void Elevator.step()                                             // advance one tick (simulation) / run loop
ElevatorStatus Elevator.status()
void ElevatorSystem.setMaintenance(int elevatorId, boolean on)
```

## Data model

* `ElevatorSystem` (controller): `List<Elevator>`, `DispatchStrategy`, hall-call queues per floor.
* `Elevator`: id, `currentFloor`, `Direction` (UP/DOWN/IDLE), `ElevatorState` (MOVING/STOPPED/DOOR\_OPEN/MAINTENANCE), `TreeSet<Integer> upStops`, `TreeSet<Integer> downStops`, `Door`, capacity/load.
* `Request`: floor, direction (hall) or target floor (car), timestamp.
* `Door`: state, open/close with timer.
* `DispatchStrategy` (interface): `Elevator select(List<Elevator>, HallRequest)`.
* `Display`, `Button` panels as observers.

## Design

1. **Per-elevator LOOK algorithm**: keep two sorted sets of stops (up and down). While moving up, serve the next stop ≥ current from `upStops`; when none remain, reverse and serve `downStops`. This is the disk-scheduling LOOK algorithm and avoids starvation.
2. **Dispatch strategy** for hall calls: score each elevator by estimated arrival time considering direction and pending stops (an idle elevator or one moving toward the floor in the same direction scores best); assign to the minimum.
3. **State machine** per elevator: `IDLE → MOVING → STOPPED → DOOR_OPEN → DOOR_CLOSING → (obstruction? DOOR_OPEN) → MOVING/IDLE`; `MAINTENANCE` is a terminal state until cleared.
4. **Observer**: displays and hall lights subscribe to elevator events (`ArrivedAt(floor)`, `DirectionChanged`).
5. **Threading**: one worker thread per elevator consuming its stop sets; controller adds stops under a lock per elevator.

## Class diagram

Rendering diagram…

## Deep dives

**Why two sorted sets**: the next stop in the current direction is a `ceiling`/`floor` lookup — O(log n) — and direction reversal is just switching sets.

**Nearest-car scoring** example: if elevator is at 3 going UP and the call is at 7 UP → distance 4; call at 2 DOWN → must finish up-run first, so cost = (top stop − 3) + (top stop − 2).

**Starvation**: LOOK guarantees each pending stop is reached within one sweep.

**Capacity**: overloaded elevator ignores new hall calls until load drops; car calls still honoured.

## Bottlenecks & mitigations

* Single controller lock for all elevators → lock per elevator; controller only reads snapshots for scoring.
* Many hall calls at rush hour → batch assignment; consider destination dispatch (user enters floor at the hall).
* Scoring cost O(elevators × stops) → fine for real buildings (≤ 32 elevators).

## Failure modes

* **Door obstruction**: sensor event re-opens the door; after N retries alert maintenance.
* **Elevator fault**: state → MAINTENANCE; controller redistributes its pending hall calls; car calls cancelled with an announcement.
* **Power failure**: elevators move to the nearest floor on backup power and open doors.
* **Duplicate button presses**: stops are sets — idempotent.

## Code skeleton

```
from enum import Enum
from bisect import insort, bisect_left, bisect_right
from threading import Lock

class Dir(Enum): UP=1; DOWN=-1; IDLE=0

class Elevator:
    def __init__(self, eid, floors):
        self.id, self.floor, self.dir = eid, 0, Dir.IDLE
        self.up, self.down, self.lock = [], [], Lock()
    def add_stop(self, f):
        with self.lock:
            if f > self.floor: insort(self.up, f)
            elif f < self.floor: insort(self.down, f)
            if self.dir == Dir.IDLE: self.dir = Dir.UP if f > self.floor else Dir.DOWN
    def step(self):
        with self.lock:
            if self.dir == Dir.UP:
                if self.up: self.floor += 1
                if self.up and self.up[0] == self.floor: self.up.pop(0); self.open_door()
                if not self.up: self.dir = Dir.DOWN if self.down else Dir.IDLE
            elif self.dir == Dir.DOWN:
                if self.down: self.floor -= 1
                if self.down and self.down[-1] == self.floor: self.down.pop(); self.open_door()
                if not self.down: self.dir = Dir.UP if self.up else Dir.IDLE
    def open_door(self): print(f"E{self.id} door open at {self.floor}")
    def cost(self, floor, d):
        if self.dir == Dir.IDLE: return abs(self.floor - floor)
        same_dir_ahead = (self.dir == Dir.UP and d == Dir.UP and floor >= self.floor) or \
                         (self.dir == Dir.DOWN and d == Dir.DOWN and floor <= self.floor)
        if same_dir_ahead: return abs(self.floor - floor)
        far = (self.up[-1] if self.up else self.floor) if self.dir == Dir.UP else (self.down[0] if self.down else self.floor)
        return abs(self.floor - far) + abs(far - floor)

class ElevatorSystem:
    def __init__(self, n, floors): self.elevators = [Elevator(i, floors) for i in range(n)]
    def request(self, floor, d):
        best = min(self.elevators, key=lambda e: e.cost(floor, d))
        best.add_stop(floor); return best.id
```

## Follow-up questions interviewers ask

* Implement destination dispatch (enter destination before boarding).
* Add express elevators serving only certain floors.
* How would you simulate and measure average wait time?

[PreviousParking Lot](/system-design/lld-parking-lot)[NextLRU / LFU Cache](/system-design/lld-lru-cache)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

Goldman SachsMicrosoftAmazonAdobeSalesforce

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
