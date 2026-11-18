# Distributed Unique ID Generator (Snowflake) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/distributed-id-generator

[All system design questions](/system-design)

#14HLDEasyHigh-level design

# Distributed Unique ID Generator (Snowflake)

snowflakeclocksharding

## Problem statement

Design a service that generates unique 64-bit ids across many servers, roughly sortable by creation time, at millions of ids per second, with no single point of failure.

## Requirements

### Functional

* Generate unique ids; 64-bit numeric.
* Ids increase with time (k-sortable).
* At least 10k ids/s per node; millions/s cluster-wide.

### Non-functional

* No coordination on the hot path; each node generates independently.
* Highly available; no central DB round-trip.
* Tolerate clock skew safely.

## Back-of-the-envelope estimates

Snowflake layout: 1 sign bit | 41 bits ms timestamp (~69 years) | 10 bits machine id (1,024 nodes) | 12 bits sequence (4,096/ms).
Per node: 4,096 ids/ms = **4M ids/s**; 1,024 nodes → 4B ids/s theoretical. Way beyond any realistic need.

## API

```
GET /v1/ids?count=1..1000 → { ids: [ ... ] }
```

Usually embedded as a library in each service rather than a network call.

## Data model

No persistent data on the hot path. Machine ids are assigned from a coordination service (ZooKeeper/etcd) at startup; the last-used timestamp may be checkpointed to detect clock rollback.

## High-level design

1. **Options considered**: UUIDv4 (128-bit, random, not sortable, index-unfriendly); DB auto-increment (single point, hard to shard); ticket server (Flickr's MySQL with `REPLACE INTO`, simple but a bottleneck); **Snowflake** (chosen); UUIDv7/ULID (128-bit but time-sorted — good when 64-bit isn't required).
2. **Snowflake node**: on each call, read current ms; if same ms as last, increment sequence; if sequence overflows, spin until next ms; if the clock went backwards, refuse or wait.
3. **Machine id assignment**: from ZooKeeper ephemeral sequential nodes, or from the pod/instance metadata; must be unique across the fleet.
4. **Library, not service**: embed in each application process to avoid an RPC per id.

## Architecture diagram

Rendering diagram…

## Deep dives

**Clock skew**: NTP keeps skew small but leap seconds and VM pauses can move time backwards. Strategies: refuse to generate until the clock catches up; keep a 'logical' clock that never decreases; or use a few bits of the machine-id space to bump a 'epoch/incarnation' after a rollback.

**Custom epoch**: start the 41-bit timestamp at your launch date to extend lifetime.

**Sortability caveat**: ids are sortable only to millisecond precision and only across machines with synced clocks — good enough for DB index locality, not for ordering guarantees.

## Bottlenecks & mitigations

* Sequence overflow within a ms on a very hot node → spin to the next ms (rare) or add more nodes.
* ZooKeeper down at startup → fall back to a pre-assigned id from config; never generate without a unique machine id.

## Failure modes

* **Two nodes with the same machine id** (misconfiguration): duplicate ids — enforce with ephemeral znodes and fail startup on conflict.
* **Clock jumps backwards**: detected by comparing with the last timestamp; block or bump incarnation.
* **Node restart within the same ms**: sequence resets to 0 → possible duplicate; persist last timestamp and wait 1 ms on start.

## Follow-up questions interviewers ask

* When would you prefer UUIDv7/ULID over Snowflake?
* How would you generate ids that reveal nothing about volume (non-sequential)?
* How does MongoDB's ObjectId compare?

## Further reading

* [Guide: Unique IDs at scaleIllustrated guide on this site](/system-design/learn/unique-ids)
* [Ticket servers: distributed unique primary keys on the cheap (Flickr)Articlecode.flickr.net](https://code.flickr.net/2010/02/08/ticket-servers-distributed-unique-primary-keys-on-the-cheap)
* [Announcing Snowflake (Twitter engineering)Articleblog.twitter.com](https://blog.twitter.com/engineering/en_us/a/2010/announcing-snowflake.html)

[PreviousPayment System (Stripe / Razorpay)](/system-design/payment-system)[NextDistributed Key-Value Store (Dynamo / Cassandra)](/system-design/key-value-store)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

TwitterAmazonAtlassianMicrosoftPayPal

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
