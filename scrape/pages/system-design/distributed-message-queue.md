# Distributed Message Queue (Kafka) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/distributed-message-queue

[All system design questions](/system-design)

#16HLDHardHigh-level design

# Distributed Message Queue (Kafka)

logpartitionsconsumer groupsreplicationordering

## Problem statement

Design a durable, high-throughput publish-subscribe log where producers append messages to topics and independent consumer groups read them at their own pace, with ordering within a partition and configurable retention.

## Requirements

### Functional

* Producers publish to a topic; consumers subscribe via consumer groups.
* Each message delivered to every group; within a group, each partition consumed by one consumer.
* Ordering within a partition; configurable retention (time/size).
* Consumers can replay from an offset.

### Non-functional

* Throughput: millions of messages/s, GB/s per cluster.
* Durability: acknowledged messages survive broker crashes (replication).
* At-least-once by default; exactly-once semantics available at extra cost.
* Scale by adding partitions/brokers.

## Back-of-the-envelope estimates

* 1M msgs/s × 1 KB = 1 GB/s ingest. A broker can sustain ~100–200 MB/s sequential disk writes with page-cache-assisted reads → ~10 brokers for ingest, ×3 replication = ~30 brokers (or fewer, bigger ones).
* Retention 7 days: 1 GB/s × 604,800 s ≈ 600 TB × RF 3 = **1.8 PB**.
* Partitions: target ≤ 10 MB/s per partition for consumer parallelism → 100+ partitions per hot topic.

## API

```
produce(topic, key?, value, headers) → (partition, offset)      // batched, async with acks=all|1|0
consume: poll() → records; commit(offsets) (auto or manual)
admin: createTopic(name, partitions, replicationFactor, retention)
```

Wire protocol is binary over TCP; clients are partition-aware and talk directly to the leader broker.

## Data model

Topic → N partitions; each partition is an **append-only log** on disk split into segment files (`00000000000123.log` + sparse `.index`). Message = offset, timestamp, key, value, headers. Consumer group state: `(group, topic, partition) → committed offset`, stored in an internal compacted topic. Cluster metadata (leaders, ISR) in the controller (ZooKeeper or KRaft).

## High-level design

1. **Brokers** host partitions. Each partition has one **leader** and R−1 **followers**; producers/consumers talk to the leader. Followers fetch from the leader and are in the **ISR** (in-sync replica set) while caught up.
2. **Produce path**: client batches by partition (chosen by hash(key) or round-robin) → leader appends to its log → waits for ISR acks per `acks` setting → responds. Sequential I/O + zero-copy `sendfile` make this cheap.
3. **Consume path**: consumers pull (not push) from leaders using offsets; long-poll for low latency. A **group coordinator** assigns partitions to consumers and rebalances on membership change.
4. **Offsets** are committed by consumers to the coordinator; replay is just seeking to an earlier offset.
5. **Retention**: delete old segments by time/size, or **log compaction** (keep latest value per key) for changelog topics.
6. **Controller** elects leaders when a broker dies (unclean election disabled to avoid data loss).

## Architecture diagram

Rendering diagram…

## Deep dives

**Why pull**: consumers control rate (backpressure for free), batching is natural, and replay is trivial.

**Ordering** is per partition only; to order all events for an entity, key by that entity's id.

**Exactly-once**: idempotent producers (sequence numbers per producer/partition) + transactions spanning produce and offset commit; consumers read `read_committed`.

**Rebalance pain**: stop-the-world rebalances on every membership change; cooperative/incremental rebalancing and static membership reduce it.

**Backpressure**: consumer lag is the key metric; producers see backpressure via bounded in-flight buffers.

## Bottlenecks & mitigations

* Too few partitions → consumer parallelism capped; too many → controller/metadata overhead and more open files. Size partitions up front; repartitioning breaks key ordering.
* Hot partition from a skewed key → salt the key or use a custom partitioner.
* Page cache pollution from lagging consumers reading old segments → tiered storage moves cold segments to object storage.
* Controller failover with thousands of partitions → KRaft speeds metadata recovery.

## Failure modes

* **Leader broker dies**: controller promotes an ISR follower; producers refresh metadata and retry; no acknowledged data lost with `acks=all` and `min.insync.replicas ≥ 2`.
* **Consumer crashes before commit**: partition reassigned; messages since the last commit are re-delivered → consumers must be idempotent.
* **Disk full**: broker stops accepting; alerts on disk and retention misconfiguration.
* **Slow follower** falls out of ISR → writes still succeed on the remaining ISR; alert on under-replicated partitions.

## Follow-up questions interviewers ask

* How would you implement delayed/scheduled messages on top of this?
* How do you handle poison messages (dead-letter topics)?
* Compare with RabbitMQ / SQS — when would you choose each?

## Further reading

* [Guide: Distributed message queuesIllustrated guide on this site](/system-design/learn/message-queues)

[PreviousDistributed Key-Value Store (Dynamo / Cassandra)](/system-design/key-value-store)[NextCloud File Storage & Sync (Google Drive / Dropbox)](/system-design/cloud-file-storage)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

LinkedInUberAmazonAtlassianMicrosoftSalesforce

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
