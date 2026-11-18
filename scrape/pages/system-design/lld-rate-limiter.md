# Rate Limiter (token bucket, sliding window) — LLD — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-rate-limiter

[All system design questions](/system-design)

#55LLDMediumLow-level design

# Rate Limiter (token bucket, sliding window) — LLD

strategyconcurrencyalgorithms

## Problem statement

Implement an in-process rate limiter library supporting multiple algorithms (token bucket, leaky bucket, fixed window, sliding window log, sliding window counter) per client key, with thread safety and a pluggable clock for testing.

## Requirements

### Functional

* `allow(clientKey) → bool` against a configured rule (limit per window / rate + burst).
* Multiple algorithms selectable per rule; multiple rules per key (e.g. 10/s and 1000/h).
* Return retry-after and remaining quota.
* Evict idle client state to bound memory.

### Non-functional

* O(1) per call for counter-based algorithms; thread-safe per key without a global lock.
* Injectable clock for deterministic tests.
* Extensible: new algorithm = new class.

## API

```
Decision allow(String key)                 // true/false + remaining + retryAfterMs
Decision allow(String key, int cost)       // weighted requests
void reset(String key)
RateLimiter RateLimiterFactory.create(Algorithm alg, Rule rule, Clock clock)
CompositeRateLimiter.of(limiter1, limiter2)   // all must allow
```

## Data model

* `RateLimiter` (interface): `Decision allow(String key)`.
* `Rule(limit, windowMs)` or `(ratePerSec, burst)`.
* Per-key state objects: `TokenBucketState(tokens, lastRefill)`, `FixedWindowState(windowStart, count)`, `SlidingLogState(Deque<timestamp>)`, `SlidingCounterState(prevCount, currCount, currWindowStart)`.
* `Clock` (interface) → `SystemClock`, `FakeClock`.
* `Decision(allowed, remaining, retryAfterMs)`.
* `RateLimiterFactory.create(Algorithm, Rule, Clock)`.
* `KeyedLimiter`: `ConcurrentHashMap<key, state>` with per-entry locking and idle eviction.

## Design

1. **Token bucket**: state = tokens (double), lastRefill. On call: `tokens = min(burst, tokens + (now − last) × rate)`; if `tokens ≥ cost` → subtract and allow; else deny with `retryAfter = (cost − tokens)/rate`. Allows bursts up to capacity.
2. **Leaky bucket**: queue-based (requests drain at fixed rate) or 'as a meter' (equivalent to token bucket with different framing). Smooths output.
3. **Fixed window**: `count` resets when `now / window` changes; simple; edge burst issue.
4. **Sliding window log**: deque of timestamps; evict those older than window; allow if size < limit. Exact, O(limit) memory per key.
5. **Sliding window counter**: `weighted = prevCount × (1 − elapsedFraction) + currCount`; allow if `weighted < limit`. Near-exact with 2 ints.
6. **Concurrency**: `ConcurrentHashMap.compute(key, ...)` gives an atomic per-key update without a global lock; or a lock stripe per key.
7. **Composite**: chain limiters; a request is allowed only if all allow — and must refund tokens taken by earlier limiters if a later one denies (or check-all-then-commit).
8. **Eviction**: LRU/idle-time eviction of key states (e.g. Caffeine-style) to bound memory.

## Class diagram

Rendering diagram…

## Deep dives

**Lazy refill** in token bucket avoids a timer thread: tokens are computed on demand from elapsed time.

**Floating-point tokens** allow fractional rates (e.g. 0.5/s); clamp to burst.

**Sliding counter accuracy**: assumes uniform distribution within the previous window; error bounded and usually < 1%.

**Composite refund problem**: check all limiters without consuming, then consume from all — needs a two-phase API (`tryAcquire`/`commit`) or optimistic consume + refund.

## Bottlenecks & mitigations

* Lock per key via `defaultdict(Lock)` grows forever → evict idle keys (LRU) with their locks.
* Sliding log memory for high limits → prefer sliding counter above ~1,000/window.
* Clock reads on every call → cache coarse time if extreme throughput.

## Failure modes

* **Clock jumps backwards** → treat negative elapsed as zero; use a monotonic clock.
* **Cost > burst** → always denied; validate rule vs cost.
* **Composite partial consumption** → two-phase acquire or refund.
* **Key explosion (per-IP under DDoS)** → cap tracked keys; fall back to coarse keys.

## Code skeleton

```
import time, threading
from collections import deque, defaultdict

class Clock:
    def now(self): return time.time()

class TokenBucket:
    def __init__(self, rate, burst, clock=Clock()):
        self.rate, self.burst, self.clock = rate, burst, clock
        self.state, self.locks = {}, defaultdict(threading.Lock)
    def allow(self, key, cost=1):
        with self.locks[key]:
            now = self.clock.now()
            tokens, last = self.state.get(key, (self.burst, now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if tokens >= cost:
                self.state[key] = (tokens - cost, now); return True, int(tokens - cost), 0
            self.state[key] = (tokens, now)
            return False, 0, (cost - tokens) / self.rate

class SlidingWindowCounter:
    def __init__(self, limit, window, clock=Clock()):
        self.limit, self.w, self.clock, self.state, self.locks = limit, window, clock, {}, defaultdict(threading.Lock)
    def allow(self, key):
        with self.locks[key]:
            now = self.clock.now(); cur_start = now - (now % self.w)
            prev, cur, start = self.state.get(key, (0, 0, cur_start))
            if cur_start != start:
                prev, cur = (cur if cur_start - start == self.w else 0), 0; start = cur_start
            weight = 1 - (now - start) / self.w
            est = prev * weight + cur
            if est < self.limit:
                self.state[key] = (prev, cur + 1, start); return True
            self.state[key] = (prev, cur, start); return False

class SlidingWindowLog:
    def __init__(self, limit, window, clock=Clock()):
        self.limit, self.w, self.clock, self.logs, self.locks = limit, window, clock, defaultdict(deque), defaultdict(threading.Lock)
    def allow(self, key):
        with self.locks[key]:
            now, q = self.clock.now(), self.logs[key]
            while q and q[0] <= now - self.w: q.popleft()
            if len(q) < self.limit: q.append(now); return True
            return False

class Composite:
    def __init__(self, *limiters): self.ls = limiters
    def allow(self, key): return all(l.allow(key)[0] if isinstance(l, TokenBucket) else l.allow(key) for l in self.ls)
```

## Follow-up questions interviewers ask

* Make it distributed with Redis Lua (see rate limiter HLD).
* Add a queueing/leaky bucket mode that delays instead of rejects.
* Add hierarchical limits (per user within per tenant).

## Further reading

* [Guide: Rate limitingIllustrated guide on this site](/system-design/learn/rate-limiting)
* [Circuit Breaker pattern (Martin Fowler)Articlemartinfowler.com](https://martinfowler.com/bliki/CircuitBreaker.html)
* [Uber's leaky-bucket rate limiter (Go source)Codegithub.com](https://github.com/uber-go/ratelimit/blob/master/ratelimit.go)

[PreviousIn-memory Pub/Sub Message Queue](/system-design/lld-in-memory-pubsub)[NextText Editor with Undo/Redo (Command pattern)](/system-design/lld-text-editor-undo-redo)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AtlassianUberStripeAmazonMicrosoftSalesforce

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
12. [Further reading](#reading)

## Your notes

Saved

Autosaves to this browser.
