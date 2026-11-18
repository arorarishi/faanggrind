# System design fundamentals: illustrated guides · FAANGrind

Source: https://faangrind.vercel.app/system-design/learn

[System design questions](/system-design)

Learn

# Fundamentals.

28 illustrated guides, about 5 hours end to end. Foundations first, then the building blocks, then full worked designs.

## 1Foundations

Read these first: how systems scale, how to estimate, and how to run the interview.

3 guides

1. [#1 8 min 11Scaling a web app from one server to millions of usersLoad balancers, replication, caching, CDNs, stateless tiers, queues and sharding: the building blocks every design reuses.Read](/system-design/learn/scaling-to-millions)
2. [#2 3 min 1Capacity estimation in your headPowers of two, latency numbers, availability nines and a worked QPS and storage estimate.Read](/system-design/learn/capacity-estimation)
3. [#3 3 minThe system design interview playbookA four-step flow (scope, high-level design, deep dive, wrap-up), what to say, what to avoid, and how to split 45 minutes.Read](/system-design/learn/interview-playbook)

## 2Building blocks

Components that show up inside almost every design.

4 guides

1. [#4 4 min 8Rate limitingToken bucket, leaky bucket, fixed and sliding windows, and where the limiter lives.Read](/system-design/learn/rate-limiting)
2. [#5 5 min 10Consistent hashingWhy modulo hashing breaks, the hash ring, virtual nodes and which keys move when servers change.Read](/system-design/learn/consistent-hashing-explained)
3. [#6 11 min 17Distributed key-value storesPartitioning, replication, quorum consistency, vector clocks, hinted handoff, Merkle trees and the read/write paths.Read](/system-design/learn/key-value-stores)
4. [#7 3 min 5Unique IDs at scaleMulti-master increments, UUIDs, ticket servers and Snowflake-style 64-bit IDs.Read](/system-design/learn/unique-ids)

## 3Worked designs

Full walkthroughs of classic interview systems, step by step.

21 guides

1. [#8 4 min 7URL shorteningHash-and-collision versus base-62 encoding, redirects, caching and the data flow.Read](/system-design/learn/url-shortening)
2. [#9 5 min 4Web crawlingSeed URLs, the URL frontier, politeness, priority, dedup and traps.Read](/system-design/learn/web-crawling)
3. [#10 4 min 6Notification deliveryPush, SMS and email providers, queues, retries, rate limits and user settings.Read](/system-design/learn/notifications)
4. [#11 4 min 5News feedsFan-out on write versus on read, feed caches and the publish and retrieval flows.Read](/system-design/learn/feeds)
5. [#12 7 min 14Chat and messagingWebSockets, message storage, message ids, group chat, presence and sync across devices.Read](/system-design/learn/chat)
6. [#13 6 min 9Search autocompleteTrie data structure, data gathering pipeline, sharding and caching the top suggestions.Read](/system-design/learn/autocomplete)
7. [#14 7 min 14Video streaming platformUpload flow, transcoding DAGs, CDN delivery, adaptive streaming and cost control.Read](/system-design/learn/video-platform)
8. [#15 7 min 9Cloud file storage and syncBlock-level uploads, metadata database, sync conflicts, notifications and storage savings.Read](/system-design/learn/file-sync)
9. [#16 10 min 14Proximity searchGeohash, quadtrees and Google S2 for finding nearby businesses, plus caching and scaling.Read](/system-design/learn/proximity)
10. [#17 11 min 10Live location sharingWebSocket servers, a location cache, pub/sub fan-out and scaling to millions of moving users.Read](/system-design/learn/live-location)
11. [#18 15 min 22Maps and navigationMap tiles, geocoding, routing graphs, ETA and the location and navigation services.Read](/system-design/learn/maps)
12. [#19 25 min 34Distributed message queuesTopics, partitions, consumer groups, replication, delivery semantics and the broker's data layout.Read](/system-design/learn/message-queues)
13. [#20 18 min 22Metrics, monitoring and alertingTime-series storage, pull versus push collection, aggregation, query service and alerting.Read](/system-design/learn/monitoring)
14. [#21 22 min 29Click event aggregationStreaming aggregation, exactly-once concerns, watermarks, reconciliation and fault tolerance.Read](/system-design/learn/event-aggregation)
15. [#22 18 min 17Hotel reservationsInventory model, double-booking prevention, concurrency control and scaling the reservation service.Read](/system-design/learn/reservations)
16. [#23 13 min 14Email at scaleSending and receiving flows, mail storage, search, deliverability and spam handling.Read](/system-design/learn/email)
17. [#24 18 min 23Object storage internalsBuckets and objects, data versus metadata stores, replication, erasure coding and garbage collection.Read](/system-design/learn/object-storage-internals)
18. [#25 16 min 23Real-time leaderboardsSorted sets, score updates, top-k and rank queries, and sharding by score range.Read](/system-design/learn/leaderboards)
19. [#26 14 min 10PaymentsPay-in and pay-out flows, ledgers, idempotency, reconciliation and handling failures.Read](/system-design/learn/payments)
20. [#27 19 min 25Digital walletsBalance transfers, distributed transactions, event sourcing and reproducibility.Read](/system-design/learn/wallets)
21. [#28 22 min 24Stock exchangeOrder matching, market data, low-latency design and fault tolerance.Read](/system-design/learn/exchange)

Each worked design links back to the matching question in the question bank, and every question links here.
