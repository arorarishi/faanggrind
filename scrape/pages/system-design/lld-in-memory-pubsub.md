# In-memory Pub/Sub Message Queue — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-in-memory-pubsub

[All system design questions](/system-design)

#54LLDMediumLow-level design

# In-memory Pub/Sub Message Queue

producer-consumerconcurrencyoffsetsobserver

## Problem statement

Design an in-process publish-subscribe system: producers publish messages to topics; multiple subscribers each receive every message of a topic in order, at their own pace, with the ability to replay from an offset and with bounded memory.

## Requirements

### Functional

* Create topics; publish messages; subscribe/unsubscribe.
* Each subscriber receives all messages of its topics in order (per topic).
* Independent consumption progress (offsets) per subscriber; replay from offset.
* Retention by count/time; optional message acknowledgement and retry.

### Non-functional

* Thread-safe publish/consume; a slow subscriber must not block producers or other subscribers.
* Non-blocking publish; bounded memory via retention.
* Pluggable delivery (push via callbacks or pull).

## API

```
void  Broker.createTopic(name)
long  Broker.publish(topic, payload)                 // returns offset
void  Broker.subscribe(topic, Subscriber, fromOffset=latest)
void  Broker.unsubscribe(topic, subscriberId)
void  Broker.resetOffset(topic, subscriberId, offset)
List<Message> Broker.poll(topic, subscriberId, max)  // pull mode
```

## Data model

* `Broker`: `Map<String, Topic>`.
* `Topic(name,` List<Message>`log, retention,`Map<subscriberId, Subscription>`)`.
* `Message(id, offset, payload, timestamp, headers)`.
* `Subscriber` (interface): `onMessage(Message)`; `Subscription(subscriber, topic, offset, executor)`.
* `Publisher(broker)`.
* `RetentionPolicy`, `RetryPolicy`.

## Design

1. **Topic as an append-only log** (`ArrayList` under a `ReentrantReadWriteLock`, or a lock-free ring buffer). Publish = append + assign offset; O(1).
2. **Per-subscriber offset**: each `Subscription` tracks the next offset to deliver; subscribers are independent — one slow subscriber just has a lower offset.
3. **Push delivery**: each subscription owns a single-threaded executor (or a dedicated thread) that loops: read next message ≥ offset, call `onMessage`, advance offset. Ordering per subscriber is preserved because one thread per subscription. Publish only signals (`Condition.signalAll`) — never calls subscribers inline.
4. **Pull delivery**: `poll` returns a batch from the subscriber's offset and advances it on ack.
5. **Retention**: trim the log head when size > N or age > T; a subscriber with an offset below the head is reset to the head (with a warning) — like Kafka's earliest.
6. **Retry**: if `onMessage` throws, retry with backoff up to `RetryPolicy`, then move to a dead-letter topic and advance.

## Class diagram

Rendering diagram…

## Deep dives

**Why producers never invoke subscribers**: an exception or slowness in a subscriber would leak into the publisher; decoupling via per-subscription threads is the whole point.

**Ordering guarantee** is per topic per subscriber, achieved by single-threaded delivery per subscription; parallelism comes from multiple subscribers or partitions.

**Backpressure**: with unbounded logs a slow subscriber grows memory; retention caps it and reset-to-head makes the loss explicit.

**Exactly-once** is not possible here without idempotent subscribers; offer at-least-once with retries.

## Bottlenecks & mitigations

* Global topic lock for publish and read → RW lock; ring buffer with sequence numbers (Disruptor) for lock-free.
* Thread per subscription → thread pool with per-subscription serial executors.
* Memory with large payloads → store references; retention by bytes.

## Failure modes

* **Subscriber throws repeatedly** → retry policy then dead-letter; never stall the topic.
* **Unsubscribe while delivering** → flag checked between messages; join the thread on shutdown.
* **Offset beyond retention** → reset to head and surface a `MessagesSkipped` event.
* **Process crash** → all lost (in-memory); persistence is the HLD's job (see Kafka design).

## Code skeleton

```
import threading, time
from collections import deque

class Message:
    def __init__(self, offset, payload): self.offset, self.payload, self.ts = offset, payload, time.time()

class Topic:
    def __init__(self, name, max_size=10000):
        self.name, self.log, self.head, self.max = name, deque(), 0, max_size
        self.cond, self.subs = threading.Condition(), {}
    def append(self, payload):
        with self.cond:
            off = self.head + len(self.log); self.log.append(Message(off, payload))
            if len(self.log) > self.max: self.log.popleft(); self.head += 1
            self.cond.notify_all(); return off
    def read(self, offset):     # blocks until available; returns message and next offset
        with self.cond:
            while self.head + len(self.log) <= offset: self.cond.wait()
            if offset < self.head: offset = self.head            # retention reset
            return self.log[offset - self.head], offset + 1

class Subscription(threading.Thread):
    def __init__(self, topic, subscriber, offset, retries=3):
        super().__init__(daemon=True); self.t, self.s, self.off, self.retries, self.running = topic, subscriber, offset, retries, True
    def run(self):
        while self.running:
            msg, nxt = self.t.read(self.off)
            for attempt in range(self.retries):
                try: self.s(msg); break
                except Exception: time.sleep(0.01 * 2 ** attempt)
            else: print(f"dead-letter {msg.offset}")
            self.off = nxt

class Broker:
    def __init__(self): self.topics, self.lock = {}, threading.Lock()
    def create_topic(self, name):
        with self.lock: self.topics.setdefault(name, Topic(name))
    def publish(self, name, payload): return self.topics[name].append(payload)
    def subscribe(self, name, sid, callback, from_offset=None):
        t = self.topics[name]
        off = from_offset if from_offset is not None else t.head + len(t.log)
        sub = Subscription(t, callback, off); t.subs[sid] = sub; sub.start()
    def unsubscribe(self, name, sid):
        sub = self.topics[name].subs.pop(sid, None)
        if sub: sub.running = False
```

## Follow-up questions interviewers ask

* Add partitions with key-based routing.
* Add consumer groups (load-balanced consumption).
* Persist the log to disk with an index.

[PreviousLogging Framework (like Log4j)](/system-design/lld-logging-framework)[NextRate Limiter (token bucket, sliding window) — LLD](/system-design/lld-rate-limiter)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AtlassianAmazonUberMicrosoftFlipkart

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
