# Meeting Scheduler / Calendar — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-meeting-scheduler

[All system design questions](/system-design)

#58LLDMediumLow-level design

# Meeting Scheduler / Calendar

interval schedulingobserverconflict detectionOOP

## Problem statement

Design a meeting scheduler: users have calendars; a meeting has a time range, organiser, attendees and a room; the system finds free slots for a set of users, books rooms without double-booking, handles recurring meetings, invitations/RSVPs and reminders.

## Requirements

### Functional

* Create/update/cancel meetings; invite attendees; RSVP.
* Book a meeting room with capacity; no double booking.
* Find common free slots for attendees in a window.
* Recurring meetings (daily/weekly) with exceptions.
* Reminders/notifications.

### Non-functional

* Conflict checks O(log n) per calendar (interval tree / sorted structure).
* Room booking atomic under concurrency.
* Time zones handled correctly (store UTC, display local).

## API

```
Meeting schedule(organiserId, attendeeIds, Interval, roomId?, RecurrenceRule?)   // throws ConflictException
List<Interval> findFreeSlots(attendeeIds, Interval window, Duration length)
void rsvp(meetingId, userId, InviteStatus)
void cancel(meetingId) ; Meeting reschedule(meetingId, Interval)
List<Room> availableRooms(Interval, capacity)
```

## Data model

* `User(id, email, tz)`, `Calendar(owner,` TreeMap<startUtc, Meeting> `or interval tree)`.
* `Meeting(id, title, organiser,` List<Invite>`, interval [start, end) UTC, room?, recurrence?)`.
* `Invite(user, status: PENDING|ACCEPTED|DECLINED)`.
* `Room(id, capacity,` Calendar`)`.
* `RecurrenceRule(freq, interval, until, exceptions)` expanded lazily into occurrences.
* `Interval(start, end)` value object with `overlaps`.
* `MeetingScheduler` service; `RoomBookingService`; `NotificationService` (observer).

## Design

1. **Calendar as a sorted map** keyed by start time: conflict check = look at the floor entry (`floorEntry(start)`) and the ceiling entry and test overlap — O(log n). Interval tree if overlapping ranges are common.
2. **Scheduling flow**: validate attendees' calendars for conflicts (soft: warn; hard for organiser) → **room booking** under a lock per room (check-then-insert atomically) → create meeting → add to each attendee's calendar with `PENDING` → notify.
3. **Free-slot search**: merge all attendees' busy intervals in the window (sort by start, coalesce), then walk gaps ≥ `length` (classic 'employee free time'). O(total intervals log n).
4. **Recurrence**: store the rule, not occurrences; when checking conflicts or listing, expand occurrences in the query window; exceptions stored as overrides (cancelled/moved instances).
5. **Observer**: `NotificationService` subscribes to meeting events; reminders scheduled via a scheduler (see job scheduler HLD).
6. **Time zones**: all intervals in UTC; conversions at the edges.

## Class diagram

Rendering diagram…

## Deep dives

**Half-open intervals** `[start, end)` make back-to-back meetings non-conflicting.

**Free-slot algorithm**: gather busy intervals of all attendees (expanding recurrences in the window), sort, merge, then gaps; return the first K.

**Room booking atomicity**: per-room lock (or DB unique constraint on (room, slot bucket) / exclusion constraint on tstzrange in Postgres).

**Recurrence exceptions**: 'this and following' edits split the rule into two rules with an `until`.

## Bottlenecks & mitigations

* Free-slot search over many attendees with long histories → restrict to the query window; index calendars by day.
* Recurring expansion over years → expand lazily per window; cap horizon.
* Room lock contention in peak hours → fine; rooms are few and ops are fast.

## Failure modes

* **Two organisers book the same room simultaneously** → per-room lock/constraint; second gets a conflict.
* **Attendee conflict** → soft conflict: schedule with a warning; attendee may decline.
* **DST transitions** → UTC storage; recurrence expansion in the organiser's tz.
* **Cancelling one occurrence of a series** → exception entry, not deletion of the rule.

## Code skeleton

```
import bisect
from threading import Lock
from datetime import datetime, timedelta

class Interval:
    def __init__(self, s, e): assert s < e; self.s, self.e = s, e
    def overlaps(self, o): return self.s < o.e and o.s < self.e

class Calendar:
    def __init__(self): self.starts, self.items, self.lock = [], [], Lock()
    def conflict(self, iv):
        i = bisect.bisect_right(self.starts, iv.s)
        cands = self.items[max(0, i-1):i+1]
        return any(m.overlaps(iv) for m in cands)
    def add(self, iv):
        with self.lock:
            if self.conflict(iv): raise Exception("conflict")
            i = bisect.bisect(self.starts, iv.s); self.starts.insert(i, iv.s); self.items.insert(i, iv)
    def busy(self, window):
        return [m for m in self.items if m.overlaps(window)]

def free_slots(calendars, window, length):
    busy = sorted((b.s, b.e) for c in calendars for b in c.busy(window))
    merged = []
    for s, e in busy:
        if merged and s <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], e)
        else: merged.append([s, e])
    out, cur = [], window.s
    for s, e in merged + [[window.e, window.e]]:
        if s - cur >= length: out.append(Interval(cur, s))
        cur = max(cur, e)
    return out

class Scheduler:
    def __init__(self): self.cals, self.rooms, self.meetings = {}, {}, {}
    def cal(self, uid): return self.cals.setdefault(uid, Calendar())
    def schedule(self, organiser, attendees, iv, room=None):
        if self.cal(organiser).conflict(iv): raise Exception("organiser busy")
        if room:
            self.rooms.setdefault(room, Calendar()).add(iv)   # atomic per room
        for u in [organiser] + attendees: self.cal(u).add(iv)
        mid = len(self.meetings) + 1
        self.meetings[mid] = {"organiser": organiser, "attendees": attendees, "iv": iv, "room": room}
        return mid
```

## Follow-up questions interviewers ask

* Add 'find a time' that suggests the slot maximising attendance.
* Add resources beyond rooms (projectors) with capacities.
* How would you sync with external calendars (CalDAV, Google)?

[PreviousIn-memory File System](/system-design/lld-in-memory-file-system)[NextAmazon Locker (package pickup)](/system-design/lld-amazon-locker)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleMicrosoftAtlassianAmazonSalesforce

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
