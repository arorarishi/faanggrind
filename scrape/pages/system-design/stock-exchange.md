# Stock Exchange / Order Matching Engine — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/stock-exchange

[All system design questions](/system-design)

#21HLDHardHigh-level design

# Stock Exchange / Order Matching Engine

order bookmatchinglow latencysequencingdeterministic replay

## Problem statement

Design an exchange that accepts buy/sell orders for securities, matches them by price-time priority in an order book, publishes executions and market data, and never loses or mis-sequences an order.

## Requirements

### Functional

* Place, modify, cancel limit and market orders.
* Match by price-time priority; partial fills.
* Publish executions to clients and market data (L1/L2 book) to everyone.
* Risk checks before an order enters the book (position limits, margin).
* End-of-day settlement and audit trail.

### Non-functional

* Order-to-ack latency in the tens of microseconds (co-located) to low ms.
* Deterministic: replaying the input sequence reproduces the exact state.
* Zero data loss; strict FIFO fairness.
* Throughput: 1M+ orders/s across all symbols.

## Back-of-the-envelope estimates

* 1M orders/s, 100 B each → 100 MB/s input; the sequencer must log at that rate (append-only, batched fsync or replicated in-memory).
* Order book per symbol in memory: 10k active orders × 64 B = 640 KB; 5,000 symbols → 3 GB — fits one box; shard symbols across matching engines for throughput and isolation.
* Market data fan-out: every book change to thousands of subscribers → multicast/UDP or a pub-sub tier, ~10M msgs/s aggregate.

## API

```
newOrder(clientOrderId, symbol, side, type: LIMIT|MARKET, price, qty, tif)  → ack(orderId, seq)
cancelOrder(orderId)   /  replaceOrder(orderId, newPrice, newQty)
Events out: OrderAccepted, OrderRejected, Fill(orderId, price, qty, tradeId), OrderCancelled
Market data: BookUpdate(symbol, side, price, qtyDelta), Trade(symbol, price, qty)
```

Binary protocol (FIX/SBE) over TCP or multicast; REST only for account/history.

## Data model

In-memory order book per symbol: two price levels maps (bids descending, asks ascending), each price level a FIFO queue of orders (linked list) with an index `orderId → node` for O(1) cancel. Persistent: `sequenced_input_log` (seq, order message), `trades`, `orders` (final state), `positions`, `accounts`. Market data snapshots periodically.

## High-level design

1. **Gateway**: validates session/auth, normalises messages, applies **pre-trade risk** (limits, credit), assigns a client sequence, forwards to the sequencer.
2. **Sequencer**: single logical stream that stamps a global sequence number on every input and persists it (replicated log). This is the source of truth; everything downstream is a deterministic function of it.
3. **Matching engines**: one single-threaded engine per symbol shard consuming the sequenced stream; applies price-time matching; emits fills and book updates. Single-threaded = no locks, deterministic.
4. **Market data publisher**: consumes engine output, builds L2 book views, publishes via multicast plus a TCP recovery/snapshot service.
5. **Post-trade**: trade capture → clearing/settlement, positions, reports — asynchronous, off the hot path.
6. **Hot standby**: a second engine replays the same sequenced stream in lockstep; on failure it takes over at the same sequence with identical state.

## Architecture diagram

Rendering diagram…

## Deep dives

**Determinism** is the design centre: no wall-clock, no randomness, no threads inside the engine; all inputs come through the sequenced log. Failover and audits become replays.

**Price-time priority**: better price first; at the same price, earlier sequence first. Modifications that reduce qty keep priority; price changes or qty increases lose it.

**Market orders** walk the opposite book until filled or the book is empty (then reject/cancel the remainder).

**Latency tricks**: kernel bypass NICs, pinned cores, pre-allocated objects, lock-free ring buffers (LMAX Disruptor pattern), no GC languages or GC-tuned JVM.

**Risk checks** happen before sequencing so rejected orders never consume book capacity.

## Bottlenecks & mitigations

* Sequencer throughput → batching, RDMA/multicast replication, or per-symbol-group sequencers with independent streams.
* One symbol's storm (meme stock) → symbol isolation per engine; other symbols unaffected.
* Market data fan-out → multicast; conflation for slow consumers; snapshot + incremental recovery.
* Post-trade DB writes → async, batched; the engine never waits on a DB.

## Failure modes

* **Engine crash**: standby takes over from the last processed sequence; clients see a brief pause, no lost orders.
* **Sequencer failure**: replicated log with leader election; in-flight unsequenced orders are retried by gateways with the same clientOrderId (idempotent).
* **Gateway crash**: clients reconnect and resync via `orderStatus` requests; sequenced orders are unaffected.
* **Slow market-data subscriber**: dropped to snapshot recovery; never allowed to backpressure the engine.
* **Bad tick / fat finger**: price bands and circuit breakers at the gateway and engine.

## Follow-up questions interviewers ask

* How would you implement stop and iceberg orders?
* How would you design the clearing and settlement (T+1) pipeline?
* How do you provide fair access when clients co-locate?

## Further reading

* [Guide: Stock exchangeIllustrated guide on this site](/system-design/learn/exchange)

[PreviousHotel Reservation System (Airbnb / Booking.com)](/system-design/hotel-reservation-system)[NextMetrics Monitoring & Alerting System (Datadog / Prometheus)](/system-design/metrics-monitoring-alerting)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

Goldman SachsJPMorgan ChaseZerodhaMorgan StanleyBloomberg

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
