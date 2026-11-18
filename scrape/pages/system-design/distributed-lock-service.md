# Distributed Lock / Coordination Service (ZooKeeper-like) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/distributed-lock-service

[All system design questions](/system-design)

#35HLDHardHigh-level design

# Distributed Lock / Coordination Service (ZooKeeper-like)

consensusraftleasesfencing tokenslinearizability

## Problem statement

Design a service that provides distributed locks, leader election and small strongly-consistent configuration/metadata storage for other systems, surviving node failures without ever granting a lock to two holders.

## Requirements

### Functional

* Acquire/release a named lock with a TTL (lease); blocking or try-lock.
* Leader election for a named group.
* Small key-value config with watches (notify on change).
* Ephemeral entries that disappear when a client session ends.

### Non-functional

* Linearizable operations (CP in CAP): correctness over availability during partitions.
* Available as long as a majority of nodes are up.
* Latency ~1–10 ms per operation; throughput ~10–50k ops/s.
* Small data (MBs to low GBs), many watchers.

## Back-of-the-envelope estimates

* 5-node ensemble tolerates 2 failures; 3 nodes tolerate 1. Write latency ≈ 1 RTT to a majority + fsync ≈ 2–5 ms in-region.
* 50k ops/s writes are the ceiling for one Raft group (log append + replication); reads can be served by followers if staleness is acceptable, or by the leader with a lease for linearizability.
* Sessions: 100k clients heartbeating every 2 s = 50k heartbeats/s — batch and keep them cheap (no log entry).

## API

```
acquire(lockName, ttlMs, waitMs) → { token (fencing), leaseUntil } | timeout
renew(lockName, token) → leaseUntil
release(lockName, token)
elect(groupName) → { isLeader, token }   // ephemeral sequential node semantics
put(key, value, expectedVersion?) → version   // CAS
get(key) → { value, version }
watch(prefix) → stream of change events
```

## Data model

Replicated state machine over a **Raft log**: tree/kv of nodes `{path, value, version, ephemeralOwnerSession, children}`; `sessions(sessionId, lastHeartbeat, timeout)`; `watches(session → paths)` kept in memory on the serving node. Locks are ephemeral, sequential children under `/locks/{name}/`.

## High-level design

1. **Consensus core**: an ensemble of 3–5 nodes running **Raft** (or ZAB/Paxos). All writes go to the leader, which appends to its log, replicates to followers, commits on a majority ack, and applies to the state machine. Reads served by the leader (linearizable via read-index/lease) or followers (sequentially consistent, may lag).
2. **Sessions & ephemerals**: clients hold a session with heartbeats; if heartbeats stop past the timeout, the leader expires the session and deletes its ephemeral nodes — this is how locks held by dead clients are released.
3. **Lock recipe**: create ephemeral-sequential `/locks/{name}/lock-000N`; if you have the lowest number you hold the lock; else watch the next-lower node and wait. Fair, no herd (each waiter watches one predecessor).
4. **Fencing tokens**: every lock grant returns a monotonically increasing token; downstream resources (DB, storage) reject writes carrying a token lower than one they've already seen → a client that paused (GC) and lost its lease cannot corrupt state.
5. **Watches**: one-shot (ZooKeeper) or streaming (etcd) notifications sent from the node the client is connected to.
6. **Observers/proxies** (non-voting) scale read/watch fan-out without slowing consensus.

## Architecture diagram

Rendering diagram…

## Deep dives

**Why fencing tokens matter**: a lease-based lock can't stop a paused client from acting after expiry; the token turns the resource into the final arbiter. Without it, 'distributed lock' is only a hint.

**Linearizable reads**: leader must confirm it is still leader (heartbeat quorum or lease) before answering, else a deposed leader could serve stale data.

**Leader election for others** is just the lock recipe on `/election/{group}`.

**Session timeouts** trade detection speed for false expirations under GC pauses; typical 5–30 s.

**Data size**: keep it tiny; this is a coordination service, not a database.

## Bottlenecks & mitigations

* Single Raft group write throughput → shard into multiple groups by key prefix (multi-raft) if ever needed; usually not.
* Watch storms (a key with 100k watchers changes) → observers/proxies fan out; coalesce events.
* Herd effect on lock release → the predecessor-watch recipe avoids it.
* Large values slow replication → enforce value size limits (e.g. 1 MB).

## Failure modes

* **Leader crash**: followers time out and elect a new leader (sub-second to seconds); in-flight uncommitted writes are retried by clients; committed writes are never lost.
* **Minority partition**: the minority side refuses writes (and linearizable reads) — correct CP behaviour; clients there see unavailability.
* **Client GC pause past session timeout**: session expired, lock released, ephemeral nodes gone; the client must treat token invalidation as losing the lock (fencing).
* **Disk full / slow fsync on a follower**: it falls behind; the majority continues; alert on lag.
* **Clock skew**: Raft doesn't depend on wall clocks; leases use monotonic local clocks with margins.

## Follow-up questions interviewers ask

* How would you build a Redlock-style lock on Redis and what are its weaknesses?
* How does etcd's MVCC and revision model enable watches?
* How would you do multi-region coordination with acceptable latency?

[PreviousLive Video Streaming (Twitch / Hotstar live match)](/system-design/live-streaming-platform)[NextPastebin / Text Sharing Service](/system-design/pastebin)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoogleAtlassianUber

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
