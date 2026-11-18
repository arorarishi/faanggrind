# Distributed Key-Value Store (Dynamo / Cassandra) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/key-value-store

[All system design questions](/system-design)

#15HLDHardHigh-level design

# Distributed Key-Value Store (Dynamo / Cassandra)

consistent hashingquorumvector clocksLSM treegossip

## Problem statement

Design a highly available, partition-tolerant key-value store that scales horizontally, tolerates node failures, and offers tunable consistency for `get` and `put`.

## Requirements

### Functional

* `put(key, value)`, `get(key)`, `delete(key)`; values up to ~10 KB.
* Tunable consistency per request (e.g. W=2, R=2 of N=3).
* Add/remove nodes online; data rebalances automatically.

### Non-functional

* Always writable (AP in CAP): a partition must not block writes.
* Single-digit ms latency within a datacentre.
* Petabyte scale across hundreds of nodes; no single point of failure.
* Durable: acknowledged writes survive node crashes.

## Back-of-the-envelope estimates

* 100 TB data, RF=3 → 300 TB raw; nodes with 4 TB usable → ~80 nodes.
* 500k ops/s; per node ~10k ops/s with disk-backed reads → 50+ nodes: capacity and throughput both land near 80–100 nodes.
* Write path cost: commit-log append + memtable insert → ~0.1 ms; read: memtable → bloom filters → 1–2 SSTable seeks → ~1–5 ms.

## API

```
PUT    /v1/kv/{key}     body value; headers: X-Consistency: W=2 ; returns version/vector clock
GET    /v1/kv/{key}     headers: X-Consistency: R=2 ; may return multiple conflicting versions
DELETE /v1/kv/{key}
```

## Data model

Per node: **commit log** (append-only, fsync) → **memtable** (sorted in-memory) → flushed to immutable **SSTables** on disk with bloom filters and sparse indexes; background **compaction** merges SSTables and drops tombstones. Cluster: hash ring with virtual nodes; each key stored on N successive nodes (preference list).

## High-level design

1. **Partitioning**: consistent hashing with virtual nodes; the coordinator for a key is the first node on the ring; replicas on the next N−1 distinct physical nodes.
2. **Replication & quorum**: write sent to N replicas, acknowledged after W succeed; read from N, returned after R respond. With `W + R > N` a read overlaps the latest write. W=1 for speed, W=N for strong durability.
3. **Consistency & conflicts**: last-write-wins by timestamp (simple, Cassandra) or **vector clocks** to detect concurrent writes and return siblings for the client to reconcile (Dynamo).
4. **Failure handling**: **hinted handoff** — if a replica is down, a neighbour stores the write with a hint and replays it later; **read repair** — on read, stale replicas are updated; **anti-entropy** — Merkle trees compare replicas in the background.
5. **Membership**: gossip protocol spreads node state; failure detection with phi-accrual, avoiding false positives.
6. **Storage engine**: LSM-tree for write-heavy workloads (see data model).

## Architecture diagram

Rendering diagram…

## Deep dives

**Why LSM over B-tree**: sequential writes to the commit log and SSTables are far cheaper than in-place B-tree updates; reads pay with multiple SSTable lookups, mitigated by bloom filters and compaction.

**Tombstones**: deletes are writes of a marker; physically removed at compaction after `gc_grace` so that a node that missed the delete does not resurrect the value.

**Vector clocks vs LWW**: LWW loses concurrent updates silently; vector clocks preserve them but push merge logic to clients (shopping-cart merge is the classic).

**Virtual nodes** also spread the load of rebuilding a failed node across many peers instead of one.

## Bottlenecks & mitigations

* Hot keys/partitions → salt keys or split hot partitions; cache in front.
* Compaction I/O storms → throttle compaction; use size-tiered vs levelled compaction depending on read/write mix.
* Large partitions (wide rows) → cap partition size; bucket by time.
* Coordinator overload → clients token-aware, sending requests straight to a replica.

## Failure modes

* **Node crash**: writes continue via hinted handoff; reads served by remaining replicas if R can be met; the node replays the commit log on restart.
* **Network partition**: both sides keep accepting writes (AP); conflicts surface as siblings/LWW after healing; anti-entropy repairs divergence.
* **Disk corruption**: SSTable checksums; rebuild the node from replicas (streaming).
* **Clock skew with LWW**: a lagging clock loses its writes — keep NTP tight or use vector clocks for critical keys.

## Follow-up questions interviewers ask

* How would you add secondary indexes?
* How do you implement lightweight transactions (compare-and-set) with Paxos?
* How would you do multi-datacentre replication?

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

[PreviousDistributed Unique ID Generator (Snowflake)](/system-design/distributed-id-generator)[NextDistributed Message Queue (Kafka)](/system-design/distributed-message-queue)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoogleAppleAtlassian

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
