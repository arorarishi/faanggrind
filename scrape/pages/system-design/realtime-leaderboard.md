# Real-time Gaming Leaderboard — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/realtime-leaderboard

[All system design questions](/system-design)

#26HLDMediumHigh-level design

# Real-time Gaming Leaderboard

sorted setredisshardingranking

## Problem statement

Design a leaderboard for a game with millions of players that updates scores in real time and answers 'top 10', 'my rank', and 'players around me' within milliseconds.

## Requirements

### Functional

* Update a player's score (increment or set).
* Top-N players; a player's rank; N players around a rank.
* Monthly/weekly leaderboards (reset) and all-time.
* Optional: leaderboards per region/friends.

### Non-functional

* Rank queries < 10 ms; score updates visible immediately.
* 25M DAU, 50M score updates/day (peaks ~5k/s).
* Highly available; scores never lost (persist).
* Scale to 100M+ players in one leaderboard.

## Back-of-the-envelope estimates

* 50M updates/day ≈ 600/s, peak 5k/s — trivial for Redis.
* 25M players in a sorted set: ~25M × (8 B score + 8 B id + skip-list overhead ~70 B) ≈ 2–3 GB → one Redis primary fits; use replicas for reads.
* Relational alternative: `SELECT COUNT(*) WHERE score > ?` per rank query is O(n) → not viable at 10 ms.

## API

```
POST /v1/leaderboards/{lb}/scores   { userId, delta }        → { score, rank }
GET  /v1/leaderboards/{lb}/top?n=10
GET  /v1/leaderboards/{lb}/users/{id}/rank
GET  /v1/leaderboards/{lb}/around/{id}?k=5
```

## Data model

```
Redis ZSET  lb:{leaderboard_id}:{period}  member=user_id  score=points   (ZINCRBY, ZREVRANGE, ZREVRANK)
scores_db   (leaderboard_id, period, user_id, score, updated_at)   -- durable copy, source for rebuilds
users       (user_id, name, avatar)   -- hydration
```

## High-level design

1. **Game/service** posts score changes to the **leaderboard service** (validated server-side; never trust client-reported scores).
2. **Redis sorted set** per leaderboard/period: `ZINCRBY` for updates, `ZREVRANGE 0 9 WITHSCORES` for top-10, `ZREVRANK` for my rank, `ZREVRANGE rank-k rank+k` for neighbours. All O(log n).
3. **Durability**: each update also appended to a DB/Kafka; Redis persistence (AOF everysec) plus replicas; on Redis loss, rebuild the ZSET from the DB.
4. **Periods**: key per period (`:2024-06` monthly); a new period is just a new key; old keys archived to the DB and expired.
5. **Sharding for > ~100M members**: partition by score range (each shard holds a band) or by user hash with a merge for top-N (top-N from each shard, merged). Score-range sharding makes rank = offset within shard + counts of higher shards (kept as small counters).
6. **Read path** through replicas; hydrate user profiles from a cache.

## Architecture diagram

Rendering diagram…

## Deep dives

**Why a skip list (ZSET)**: log-time insert and rank; exactly the operations needed. A B-tree with subtree counts is the disk-based equivalent.

**Ties**: ZSET orders equal scores lexicographically by member; to break ties by time, encode `score * 2^20 + (MAX_TS − ts)` into the numeric score.

**Anti-cheat**: score deltas validated against game events; cap per-match deltas; audit trail in the DB.

**Friends leaderboard**: intersect the friend list with scores on read (`ZSCORE` per friend, sort client-side) — friend lists are small.

## Bottlenecks & mitigations

* Single primary write throughput → far above need; if exceeded, shard as above.
* Top-N hammered by every client → cache the top-100 for 1 s in the service layer.
* Rebuild time after Redis loss (25M ZADDs) → pipeline in batches of 1,000; ~1–2 minutes; serve stale from replica meanwhile.

## Failure modes

* **Redis primary crash**: replica promoted; possible loss of the last second of updates (AOF everysec) — recovered from Kafka/DB replay.
* **DB writer lag**: leaderboard remains correct in Redis; durability window widens — alert.
* **Period rollover bug**: writes to the old key → detect via key naming validation; migrate with `ZUNIONSTORE`.

## Follow-up questions interviewers ask

* How would you compute a percentile rank cheaply for 1B users?
* How would you build a leaderboard that supports score decay over time?
* How would you handle regional leaderboards with global aggregation?

## Further reading

* [Guide: Real-time leaderboardsIllustrated guide on this site](/system-design/learn/leaderboards)

[PreviousPhoto Sharing App (Instagram)](/system-design/photo-sharing-app)[NextDistributed Job Scheduler (cron-as-a-service, Airflow-like)](/system-design/distributed-job-scheduler)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonDream11MicrosoftGoogleZynga

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
