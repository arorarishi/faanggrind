# Distributed Cache (Redis / Memcached) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/distributed-cache

[All system design questions](/system-design)

#3HLDMediumHigh-level design

# Distributed Cache (Redis / Memcached)

consistent hashingevictionreplicationLRU

## Problem statement

Design a horizontally scalable in-memory key-value cache that application servers use to offload reads from their databases, with sub-millisecond gets/sets, TTLs and eviction.

## Requirements

### Functional

* `get(key)`, `set(key, value, ttl)`, `delete(key)`; values up to ~1 MB.
* Automatic expiry via TTL and eviction under memory pressure (LRU/LFU).
* Add and remove nodes without full cache invalidation.
* Optional: atomic increment, compare-and-set.

### Non-functional

* p99 latency < 1 ms within a datacentre.
* Scale to hundreds of nodes and millions of ops/s.
* Node loss should cost only that node's share of keys (or nothing with replication).
* Eventual consistency is acceptable; a cache is not the source of truth.

## Back-of-the-envelope estimates

* 1M ops/s, 80% reads. A node does ~200k ops/s → ≥ 5 nodes for throughput.
* Data: 50M keys × 1 KB avg = 50 GB. With 64 GB nodes and ~70% usable → 2 nodes for capacity; throughput dominates, so run 8–10 nodes.
* Replication factor 2 doubles memory → ~16–20 nodes.
* Network: 1M × 1 KB = 1 GB/s aggregate — fine over 10/25 GbE spread across nodes.

## API

```
GET   /cache/{key}                 → 200 value | 404
PUT   /cache/{key}?ttl=300         body: value
DELETE /cache/{key}
POST  /cache/{key}/incr?by=1
POST  /cache/{key}/cas             { expectedVersion, value }
```

In practice a binary protocol (RESP / memcached text) over persistent TCP connections, with a smart client library that knows the ring.

## Data model

Per node: hash table `key → {value, expiresAt, lastAccess, version}` plus an eviction structure (doubly linked list for LRU, or sampled-LRU / TinyLFU for lower overhead). Cluster metadata: the hash ring (node id → virtual node positions), stored in a coordination service (ZooKeeper/etcd) or gossiped.

## High-level design

1. **Client-side routing with consistent hashing**: each key hashes to a position on a ring; the first node clockwise owns it. Each physical node gets 100–200 **virtual nodes** to balance load. Adding a node moves only ~1/N of keys.
2. **Node internals**: single-threaded event loop per core (Redis) or multi-threaded with striped locks (memcached); slab allocator to fight fragmentation; LRU via clock/sampling rather than an exact list.
3. **Expiry**: lazy on access + a background sampler that deletes a random slice of expired keys each tick.
4. **Replication**: each key also written to the next node on the ring (RF=2). Reads go to the primary; on failure, the replica.
5. **Consistency with the DB**: cache-aside (app reads DB on miss and populates), with **write-invalidate** on updates. Avoid write-through for hot-write data.
6. **Membership**: heartbeats via gossip or a coordinator; a node marked dead is removed from the ring and its replica promoted.

## Architecture diagram

Rendering diagram…

## Deep dives

**Cache stampede** (thundering herd on a hot key expiry): use *request coalescing* (one loader, others wait), *probabilistic early expiry* (refresh slightly before TTL with probability rising as expiry nears), or serve stale while revalidating.

**Hot keys**: detect via per-key access counters; replicate hot keys to multiple nodes and let clients pick randomly, or add an L1 in-process cache with a 1–5 s TTL.

**Large values**: chunk values > 1 MB across keys or reject them; large values block the event loop.

**Consistency**: never do read-modify-write from the app; use server-side `INCR`/`CAS`.

## Bottlenecks & mitigations

* Single hot key saturating one node → replicate hot keys / L1 cache.
* Uneven distribution without virtual nodes → use 150+ vnodes per node.
* Full-table `KEYS *` style scans → forbid; use cursor-based `SCAN`.
* Network round-trips for multi-get → batch with pipelining / `MGET`, group keys by node.

## Failure modes

* **Node crash**: keys move to the replica; misses spike briefly; DB must handle the temporary extra load (cap with a circuit breaker).
* **Network partition / split brain**: two nodes both think they own a range; with cache-aside this only causes stale reads, not corruption — acceptable.
* **Memory exhaustion**: eviction policy kicks in; monitor eviction rate as the key health metric.
* **Cold start after full outage**: pre-warm from a snapshot (RDB) or replay recent access logs; ramp traffic gradually.

## Follow-up questions interviewers ask

* How would you build a write-behind cache and what consistency issues appear?
* How does Redis Cluster's slot-based sharding differ from a hash ring?
* How would you make the cache multi-region?

## Further reading

* [Guide: Consistent hashingIllustrated guide on this site](/system-design/learn/consistent-hashing-explained)
* [Consistent hashing explained (Tom White)Articletom-e-white.com](https://tom-e-white.com/2007/11/consistent-hashing.html)
* [Stanford CS168: Introduction and consistent hashingPapertheory.stanford.edu](http://theory.stanford.edu/~tim/s16/l/l1.pdf)
* [Cassandra: a decentralized structured storage systemPapercs.cornell.edu](http://www.cs.cornell.edu/Projects/ladis2009/papers/Lakshman-ladis2009.PDF)
* [How Discord scaled Elixir to 5M concurrent usersArticleblog.discord.com](https://blog.discord.com/scaling-elixir-f9b8e1e7c29b)
* [Maglev: a fast and reliable software network load balancer (Google)Paperstatic.googleusercontent.com](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44824.pdf)
* [Guide: Distributed key-value storesIllustrated guide on this site](/system-design/learn/key-value-stores)
* [Dynamo: Amazon's highly available key-value storePaperallthingsdistributed.com](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
* [Cassandra architecture overview (DataStax docs)Articledocs.datastax.com](https://docs.datastax.com/en/archived/cassandra/3.0/cassandra/architecture/archIntro.html)
* [Bigtable: a distributed storage system for structured dataPaperstatic.googleusercontent.com](https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf)
* [Amazon's Dynamo (Werner Vogels)Articleallthingsdistributed.com](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)
* [Design patterns in Amazon DynamoDB (re:Invent)Videoyoutube.com](https://www.youtube.com/watch?v=HaEPXoXVf2k)
* [Internals of Amazon DynamoDB (re:Invent)Videoyoutube.com](https://www.youtube.com/watch?v=yvBR71D0nAQ)

[PreviousDistributed Rate Limiter](/system-design/rate-limiter)[NextNotification System (push, SMS, email)](/system-design/notification-system)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoogleAtlassianSalesforce

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
