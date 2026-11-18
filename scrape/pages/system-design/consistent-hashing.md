# Consistent Hashing (Data Partitioning) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/consistent-hashing

[All system design questions](/system-design)

#40HLDMediumHigh-level design

# Consistent Hashing (Data Partitioning)

hashingpartitioningvirtual nodesload balancing

## Problem statement

Design a scheme that maps keys (cache entries, user ids, shard keys) to a fleet of `N` servers so that when a server is added or removed only a small fraction of keys move. Plain `hash(key) % N` remaps almost every key whenever `N` changes, which stampedes caches and forces mass data migration. Explain the hash ring, virtual nodes, how lookups work, and how real systems (Dynamo, Cassandra, Discord, Maglev) use it.

## Requirements

### Functional

* Map any key to exactly one server (deterministically, from the key alone plus the current membership).
* Adding or removing a server moves only ~`K/N` keys (K = total keys), not nearly all of them.
* Spread keys and load evenly across servers, including heterogeneous servers of different capacity.
* Support replication: find the next `R` distinct servers for a key, not just one.

### Non-functional

* Lookup in O(log V) where V = number of virtual nodes (binary search on the ring) — microseconds, no network call.
* Membership changes propagate to all clients within seconds; during propagation the system degrades gracefully (extra cache misses, not wrong answers).
* Standard deviation of per-server load ≤ ~5–10% with enough virtual nodes.
* Ring state is tiny (a few hundred KB) so every client can hold a copy in memory.

## Back-of-the-envelope estimates

* Why modulo fails: with 4 servers and 8 keys, removing 1 server changes `N` from 4 to 3 and **≈75% of keys** move; consistent hashing moves only the ≈25% that belonged to the removed server.
* Ring size: a 64-bit hash space (e.g. MurmurHash3 or the first 8 bytes of SHA-1 / MD5) is ample; 160-bit SHA-1 is the textbook choice.
* Virtual nodes: 100–200 per physical server. 100 servers × 150 vnodes = 15,000 ring points × (8 B hash + 4 B server id) ≈ **180 KB** per client copy.
* Lookup: binary search over 15,000 sorted points ≈ 14 comparisons; ~100 ns.
* Rebalancing cost when a server joins a 100-node cluster holding 1 TB of cache: ≈ 1/101 of the data (≈ 10 GB) warms on the new node; nothing else moves.

## API

A library API rather than an HTTP one — every client embeds the ring:

```
addNode(nodeId, weight = 1)            // adds `weight × V` virtual nodes
removeNode(nodeId)
getNode(key) → nodeId                  // owner of the key
getNodes(key, n) → [nodeId, …]         // next n DISTINCT physical nodes clockwise (for replication)
snapshot() → { version, members[] }    // for gossip / config service
```

Membership is usually fed from a coordination service (ZooKeeper / etcd) or gossip, with a monotonically increasing `version` so stale views are detectable.

## Data model

The whole structure is a sorted array (or tree map) of ring points:

```
ring:  [ (hash: uint64, node: "s3", vnode: 17), (hash, node, vnode), … ]  sorted by hash
nodes: { "s3": { weight: 1, address: "10.0.1.3:6379", status: UP } }
```

`getNode(key)` = first ring point with `hash ≥ hash(key)`, wrapping to index 0 past the end.

For **bounded loads** (Google's variant) add a per-node counter: `load[node]` and a cap `c × avgLoad`; if the owner is over the cap, walk clockwise to the next node.

## High-level design

**The ring**: hash both keys and servers into the same space `[0, 2^m)` and treat it as a circle. A key is owned by the first server encountered walking **clockwise** from the key's hash. Only the keys between a server and its predecessor change hands when that server joins or leaves.

**Virtual nodes (vnodes)**: with one point per server the arcs are wildly uneven (random gaps). Give each server `V` points — `hash("s3#0")`, `hash("s3#1")`, … — so every server owns many small, interleaved arcs. More vnodes → lower variance; heavier servers get proportionally more vnodes (weights).

**Replication**: walk clockwise from the key and take the first `R` points that belong to *different physical* servers (skip repeats of the same server, and in rack-aware setups skip the same rack/AZ too).

**Where it lives**: (1) *client-side* — every app server/cache client holds the ring (Memcached clients, Cassandra drivers); (2) *in a router* — a proxy tier (Twemproxy, Envoy) owns the ring and apps stay dumb; (3) *in the storage nodes* — Dynamo/Cassandra nodes gossip the ring and forward requests to the right owner.

**Alternatives**: *rendezvous (HRW) hashing* — for each key compute `hash(key, node)` for every node and pick the max; zero state, no ring, O(N) per lookup (fine for small N). *Jump consistent hash* — O(1) memory, O(log N) time, but only supports adding/removing the **last** node (good for numbered shards, not arbitrary departures). *Maglev* — a lookup table built from permutations, giving O(1) lookups and minimal disruption for load balancers.

## Architecture diagram

Rendering diagram…

## Deep dives

**How many virtual nodes?** With `V` vnodes per server, the fraction of the ring a server owns has standard deviation ≈ `1/√(N·V)` relative to the mean. 100 servers × 150 vnodes → ~0.8%; Cassandra defaults to 16–256 tokens per node. Too many vnodes slow repair/streaming and bloat the ring; too few cause hot servers.

**Hot keys are not solved by hashing.** A single viral key still lands on one server. Mitigate with request coalescing, local (L1) caches in front of the ring, or splitting the key (`key#0..k`) across several owners.

**Membership consistency.** Two clients with different ring versions may write the same key to different servers. Caches tolerate this (a miss); stores do not — Dynamo-style systems add *hinted handoff* (temporarily accept writes for the intended owner) and *read repair* / anti-entropy (Merkle trees) to converge.

**Graceful join/leave.** A joining node first *streams* its future arcs from the current owners, then flips to serving; a leaving node drains the other way. Dynamo calls these ranges *token ranges*; Cassandra `nodetool decommission` streams them out.

**Bounded-load variant.** Pure consistent hashing can still overload a node when load is skewed. *Consistent hashing with bounded loads* (Mirrokni et al., used in Google Cloud Pub/Sub and Vimeo's HAProxy patch) caps each node at `(1+ε) × average` and spills overflow to the next node clockwise with minimal reshuffling.

**Cache stampede on rebalance.** When a cache node joins, its arcs start cold: a burst of misses hits the database. Warm the node first (replay recent keys) or use *request coalescing* so one miss fills many waiting requests.

## Bottlenecks & mitigations

* Uneven arcs with few vnodes → raise vnodes per server (100–200) and weight by capacity.
* Hot key on one owner → L1 in-process cache, key splitting, or bounded-load spill-over to the next node.
* Stale ring views after a membership change → version the ring, push changes via watch (etcd) or gossip, and make reads tolerate a brief window of misses.
* Rebalance traffic saturating the network when many nodes join at once → add nodes gradually, throttle streaming, and prefer a few large nodes over many tiny ones.

## Failure modes

* **Server crash**: its arcs fall to the next clockwise owners automatically; with replication factor `R` those replicas already hold the data, so reads continue. Hinted handoff holds writes until it returns.
* **Flapping node** (joins/leaves repeatedly): every flip moves `1/N` of the keys. Add a grace period before removing a node from the ring and require quorum agreement on membership.
* **Split brain in membership** (two groups see different rings): clients write to different owners for the same key. Use a single source of truth (etcd/ZooKeeper with leader election) or Dynamo-style vector clocks plus read repair.
* **Hash function change**: changing the hash moves every key — treat it like a full migration with dual-write.

## Follow-up questions interviewers ask

* How would you implement `getNodes(key, R)` so that replicas land in different availability zones?
* Compare consistent hashing with rendezvous hashing and jump hashing — when would you pick each?
* How does Dynamo use the ring for *preference lists*, sloppy quorums and hinted handoff?
* What breaks if two clients disagree on the ring version, and how do you detect it?
* How would you shard a relational database using consistent hashing versus range partitioning?

## Further reading

* [Guide: Consistent hashingIllustrated guide on this site](/system-design/learn/consistent-hashing-explained)
* [Consistent hashing explained (Tom White)Articletom-e-white.com](https://tom-e-white.com/2007/11/consistent-hashing.html)
* [Stanford CS168: Introduction and consistent hashingPapertheory.stanford.edu](http://theory.stanford.edu/~tim/s16/l/l1.pdf)
* [Cassandra: a decentralized structured storage systemPapercs.cornell.edu](http://www.cs.cornell.edu/Projects/ladis2009/papers/Lakshman-ladis2009.PDF)
* [How Discord scaled Elixir to 5M concurrent usersArticleblog.discord.com](https://blog.discord.com/scaling-elixir-f9b8e1e7c29b)
* [Maglev: a fast and reliable software network load balancer (Google)Paperstatic.googleusercontent.com](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44824.pdf)

[PreviousRecommendation System (product / video recommendations)](/system-design/recommendation-system)[NextNearby Friends (Live Location Sharing)](/system-design/nearby-friends)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoogleAtlassianUberFlipkart

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
