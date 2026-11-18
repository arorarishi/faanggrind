# Python: concurrent health checker with retries and backoff — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/python-health-checker

[DevOps problems](/devops#problems)

CODEImplement it#35Medium

# Python: concurrent health checker with retries and backoff

pythonconcurrencyretriesbackoffprometheushealth checks

## Problem statement

Your team runs 40 internal services and wants a script that the on-call engineer and a cron job can both run: it reads a list of targets (name, URL, expected status, timeout, critical flag), checks them all in parallel, retries transient failures with exponential backoff and jitter, never runs longer than a global deadline, prints a report with healthy, degraded and down counts plus p50 and p95 latency, writes Prometheus text-format metrics, and exits non-zero when any critical target is down. Standard library only, and it must be testable without a network.

## Requirements

### Functional

* Load targets from a JSON file; each has `name`, `url`, `expected_status` (default 200), `timeout_s` (default 2.0) and `critical` (default true).
* Check all targets concurrently with a thread pool of configurable size; results come back in input order.
* Retry on timeouts, connection errors and 5xx with exponential backoff and full jitter, up to 3 retries; never retry a 4xx.
* Classify each target as healthy (first attempt ok), degraded (ok after retries) or down; record every attempt's status and latency.
* Print a summary with counts, p50 and p95 latency of the last attempts, and total retries; write Prometheus text metrics (`healthcheck_up`, `healthcheck_latency_ms`, `healthcheck_attempts_total`) to a file or string.
* Exit 0 when every critical target is healthy or degraded, 2 when any critical target is down, 2 on bad arguments.

### Non-functional

* A global deadline (default 20 s) bounds the whole run: no attempt starts after it, and a backoff sleep that would cross it is skipped.
* Per-target timeout (default 2 s) bounds one attempt; the worst case for one target is 4 attempts of 2 s plus 1.4 s of backoff, 9.4 s.
* 40 targets with 8 workers finish in under 10 s when all are healthy with 50 ms latency: 5 rounds of 50 ms is 0.25 s plus thread start-up.
* The HTTP call is an injectable function so the self-checks run with a fake server and a fake clock in under 1 s with no network.
* Memory stays small: one `Result` per target with at most 4 `Attempt` records, no response bodies kept.

## API

```
Usage: python3 healthcheck.py targets.json [--deadline 20] [--workers 8] [--metrics out.prom]
       python3 healthcheck.py            # self-checks with a fake server, no network

Library:
  check_target(target, http, *, max_retries=3, deadline, sleep, clock, rng) -> Result
  run_checks(targets, http, *, workers=8, deadline_s=20.0, max_retries=3, ...) -> list[Result]
  summarize(results) -> dict        healthy, degraded, down, total, critical_down,
                                    p50_ms, p95_ms, total_retries
  prometheus_text(results) -> str   text exposition format
  backoff_delay(attempt, base_s=0.2, cap_s=5.0, rng) -> float   full jitter
  is_transient(status) -> bool      None (transport error) or 5xx

Injected HTTP contract:
  http(url: str, timeout_s: float) -> int     returns the status code
                                              raises TimeoutError_ on timeout
                                              raises anything else on connection failure
  http_get is the real one (urllib); FakeServer is the scripted one for tests.

Exit codes: 0 all critical targets up, 2 a critical target is down or bad arguments
```

## Data model

```
targets.json
[
  {"name": "api",   "url": "https://api.internal/healthz"},
  {"name": "auth",  "url": "https://auth.internal/healthz", "timeout_s": 1.0},
  {"name": "docs",  "url": "https://docs.internal/", "expected_status": 200, "critical": false}
]

Target(name, url, expected_status=200, timeout_s=2.0, critical=True)   frozen dataclass
Attempt(status: int | None, latency_ms: float, error: str)            one HTTP call
Result(target, attempts: list[Attempt], outcome, reason)              outcome: healthy | degraded | down

Decision table for one attempt (expected 200):
  status 200            -> stop: healthy if attempt 0, else degraded
  status 404 or any 4xx -> stop: down, "not retried"
  status 503 or any 5xx -> transient, retry if budget and deadline allow
  timeout / refused     -> status None, transient, same rule

Prometheus text written by prometheus_text():
  # TYPE healthcheck_up gauge
  healthcheck_up{target="api"} 1
  healthcheck_latency_ms{target="api"} 12.400
  healthcheck_attempts_total{target="api"} 1
```

## Approach

1. Parse the targets file into frozen `Target` dataclasses so a typo in a field name fails loudly at load time, not at 3 a.m.
2. Compute one absolute deadline, `clock() + deadline_s`, before submitting anything. Every worker reads the same number, so "20 seconds" means 20 seconds for the whole run, not per target.
3. Submit one `check_target` call per target to a `ThreadPoolExecutor`. Each check spends almost all of its time blocked in a socket read, during which the interpreter releases the GIL, so 8 threads give close to 8 times the throughput of a loop.
4. Inside `check_target`, loop over attempts. Before each one, stop if the deadline has passed. Clip the per-attempt timeout to `min(target.timeout_s, deadline - now)` so a single slow target cannot push the run past the deadline.
5. Call the injected `http(url, timeout)`. Map its three outcomes to an `Attempt`: a status code, a `TimeoutError_`, or any other exception (connection refused, DNS). Record latency from a monotonic clock, never wall-clock time.
6. Decide: expected status means stop with healthy or degraded; a 4xx means stop with down and no retry; a 5xx or transport error means retry if `attempt < max_retries`. Before sleeping, compute the full-jitter delay and skip the sleep (and the retry) if it would cross the deadline.
7. Collect results with `as_completed` into a dict keyed by name, then reorder to match the input so the output is stable across runs.
8. `summarize` counts outcomes, lists critical targets that are down, and computes nearest-rank p50 and p95 over the last attempt's latency for targets that got any response.
9. `prometheus_text` emits one gauge per target for up and latency and one counter for attempts, with `# HELP` and `# TYPE` lines, ready for a textfile collector or a pushgateway.
10. The self-checks replace the HTTP function with `FakeServer`, whose scripts say what each URL returns on each call, and replace `time.monotonic` and `time.sleep` with a `FakeClock` that advances only when told, so backoff costs no real time and latencies are exact.

## Architecture diagram

Rendering diagram…

## Deep dives

### Backoff and jitter: the arithmetic

Plain exponential backoff sleeps `base * 2^attempt`: with base 0.2 s that is 0.2, 0.4, 0.8, 1.6 s. The cap stops the sequence growing past 5 s. The problem with plain backoff is synchronisation: if 200 checkers all see a 503 at the same instant, they all retry at exactly 0.2 s, then 0.4 s, and the struggling server gets the same spike four times. Full jitter fixes that by sleeping a uniform random amount in `[0, min(cap, base * 2^attempt)]`. The average sleep halves and the retries spread over the window, so the server sees a trickle instead of spikes. The script's self-check draws 1,600 samples and asserts every one is inside the bound. Two more numbers an interviewer wants: the worst-case time for one target is the attempts plus the sleeps, here 4 × 2 s + (0.2 + 0.4 + 0.8) s = 9.4 s, which is why the global deadline must be larger than that or some targets can never exhaust their retries; and the expected sleep with full jitter is half the bound, so about 0.7 s across three retries.

### Why 4xx is never retried

A retry is a bet that the same request will get a different answer. A 503 or a timeout says "the server could not answer right now", and a second later it may. A 404, 401 or 400 says "this request is wrong": the path moved, the token expired, the body is malformed. Sending it again cannot succeed and costs the server work; worse, retrying a 429 (rate limited) makes the rate limiting worse. The script therefore treats any 4xx as final after one attempt and the self-check asserts the fake server saw exactly one call for the 404 target. The one nuance to mention: 408 Request Timeout and 429 Too Many Requests are 4xx codes that some clients do retry, the second one only after honouring `Retry-After`. Keep that as an explicit allow-list, not a widening of the rule.

### Threads versus asyncio for IO-bound checks

Each check is a socket write, then a long wait, then a small read. While a thread waits on the socket, CPython releases the GIL, so other threads run; the GIL only limits CPU-bound work, which this is not. A pool of 8 to 32 workers handles hundreds of targets with code that reads like a loop. `asyncio` with `aiohttp` scales to tens of thousands of concurrent connections with one thread and less memory, but it needs an async HTTP client (the standard library has none), every blocking call must be avoided, and tracebacks are harder to read. For a 40-target checker, threads are the right size. The one real trap with threads here is shared state: the `FakeServer` guards its scripts with a lock because two workers can call it at the same time, and the `FakeClock` keeps a separate timeline per thread, otherwise one worker's backoff sleep would inflate the latency another worker measures.

### Two timeouts: per attempt and per run

A per-target timeout bounds one socket operation; without it a half-open connection waits for the kernel's TCP timeout, minutes. A global deadline bounds the whole run; without it, 40 targets that each take the worst case 9.4 s with 8 workers take 47 s, and a cron job scheduled every minute starts overlapping itself. The script enforces the deadline in three places: before an attempt starts, by clipping the attempt timeout to the time left, and before a backoff sleep. The self-check gives a timing-out target a 1 s timeout and a 2 s deadline and asserts it stopped after at most 3 attempts with the reason "deadline". Timeouts should be short enough to detect trouble and long enough to clear a p99: set them from the latency histogram, not from a guess.

## Evaluation

**Tests.** Run with no arguments. The fake server scripts six targets: `api` returns 200; `auth` returns 503, 502, then 200; `db` returns 500 forever; `cache` times out forever; `old` returns 404; `slow` answers after 350 ms. The checks assert: `api` healthy with 0 retries; `auth` degraded with exactly 2 retries; `db` down after 4 attempts; `cache` down with 4 attempts all status `None`; `old` down after exactly 1 call to the fake server; `slow` healthy with latency of at least 349 ms; the report reads 2 healthy, 1 degraded, 3 down, `critical_down` is `["db", "cache"]` (the 404 target is non-critical), total retries 8, p50 10 ms and p95 350 ms; the Prometheus text contains `healthcheck_up{target="auth"} 1` and `healthcheck_attempts_total{target="old"} 1`; 1,600 backoff samples stay within bounds; and a 2 s deadline with a 1 s timeout cuts the run short with a "deadline" reason.

**Edge cases.** Empty target list: counts are zero, p50 and p95 are 0.0, exit 0. All targets down: p50 and p95 computed only over attempts that received a status, so a run where everything timed out reports 0.0 rather than crashing. Duplicate names collide in the result dict; a strong answer keys by index. A target with `expected_status: 302` must not follow redirects, which `urllib` does by default; pass a handler that does not.

**Complexity.** O(targets × attempts) HTTP calls, O(targets log targets) for the percentile sort, O(targets / workers) rounds of wall time.

**What a strong answer adds.** Injecting the clock as well as the HTTP call; clipping the attempt timeout to the deadline; naming full jitter and the 429 `Retry-After` exception; knowing that p95 over 6 samples is a weak number and that histograms in Prometheus are the production answer; and separating "degraded" from "healthy" so a flapping dependency is visible before it is down.

## Bottlenecks & mitigations

* The slowest target decides the run time: with 8 workers and one target that burns 9.4 s, the pool finishes no sooner than that.
* Thread start-up and the GIL hand-off cost about a millisecond per task; at thousands of targets, asyncio or a larger pool wins.
* `urllib` opens a new TCP and TLS connection per attempt; a `http.client` connection reuse or a session object would halve the latency on retries.
* The percentile needs all latencies in memory and a sort; fine for thousands, wrong for a long-running daemon, which should export a histogram instead.
* Backoff sleeps hold a worker thread idle; with 8 workers and 8 retrying targets nothing else runs, which is the argument for a larger pool or asyncio.

## Failure modes

* **Retrying a 4xx.** Hammering a server with a request that can never succeed, and turning a 429 into a longer ban. Mitigation: `is_transient` returns false for 4xx; test that the fake server saw one call.
* **Backoff without jitter.** Retries from many checkers land on the same instant and knock the recovering server over again. Mitigation: full jitter, bound asserted in the self-check.
* **No global deadline.** A cron run overlaps the next one and the box fills with checker processes. Mitigation: one absolute deadline checked before every attempt and every sleep.
* **Measuring latency with wall-clock time.** NTP steps the clock and a check reports negative or huge latency. Mitigation: `time.monotonic`, injected so tests can fake it.
* **Thread-unsafe shared state.** Two workers pop from the same script list and a test flakes once in fifty runs. Mitigation: a lock around the fake server's state and per-thread clocks.
* **Exit 0 on failure.** The cron job never pages anyone. Mitigation: exit 2 when `critical_down` is non-empty, and test the exit code, not just the printout.
* **Following redirects.** A 301 to a login page counts as healthy. Mitigation: disable redirects in the HTTP function and compare against `expected_status`.

## Reference solution

Python · runs and prints its own checks

```
#!/usr/bin/env python3
"""healthcheck.py: concurrent HTTP health checker with retries, backoff and a report.

Usage (library):
    results = run_checks(targets, http=my_http_function, deadline_s=20)
    report  = summarize(results)
    text    = prometheus_text(results)
    exit_code = 2 if report["critical_down"] else 0

The HTTP call is injected so the checker can be tested without a network.
Standard library only.
"""
from __future__ import annotations

import json
import random
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# ---------------------------------------------------------------- data model

@dataclass(frozen=True)
class Target:
    name: str
    url: str
    expected_status: int = 200
    timeout_s: float = 2.0
    critical: bool = True

@dataclass
class Attempt:
    status: int | None      # None when the call raised (timeout, connection error)
    latency_ms: float
    error: str = ""

@dataclass
class Result:
    target: Target
    attempts: list[Attempt] = field(default_factory=list)
    outcome: str = "down"    # healthy | degraded | down
    reason: str = ""

    @property
    def retries(self) -> int:
        return max(0, len(self.attempts) - 1)

    @property
    def last(self) -> Attempt | None:
        return self.attempts[-1] if self.attempts else None

class TimeoutError_(Exception):
    """Raised by the injected HTTP function when the per-target timeout is hit."""

# ---------------------------------------------------------------- real HTTP (not used by the self-checks)

def http_get(url: str, timeout_s: float) -> int:
    """Default HTTP function: returns the status code, raises TimeoutError_ on timeout.
    urllib raises HTTPError for 4xx and 5xx; we want the code, not an exception."""
    req = urllib.request.Request(url, headers={"User-Agent": "healthcheck/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (socket.timeout, TimeoutError) as e:
        raise TimeoutError_(str(e) or "timed out") from e
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            raise TimeoutError_(str(e.reason) or "timed out") from e
        raise

def load_targets(path: str) -> list[Target]:
    """targets.json: [{"name": "api", "url": "...", "expected_status": 200,
                       "timeout_s": 2.0, "critical": true}, ...]"""
    with open(path, encoding="utf-8") as f:
        return [Target(**row) for row in json.load(f)]

# ---------------------------------------------------------------- retry policy

def is_transient(status: int | None) -> bool:
    """5xx and transport errors may succeed on retry; 4xx is the caller's fault and will not."""
    return status is None or 500 <= status <= 599

def backoff_delay(attempt: int, base_s: float = 0.2, cap_s: float = 5.0, rng=random.random) -> float:
    """Full jitter: sleep a uniform random amount between 0 and min(cap, base * 2**attempt).

    attempt 0 -> up to 0.2 s, attempt 1 -> up to 0.4 s, attempt 2 -> up to 0.8 s, ...
    Random spread stops many checkers from retrying in lock step against a struggling server.
    """
    return rng() * min(cap_s, base_s * (2 ** attempt))

# ---------------------------------------------------------------- one target

def check_target(target: Target, http, *, max_retries: int = 3, deadline: float,
                 sleep=time.sleep, clock=time.monotonic, rng=random.random) -> Result:
    """Call http(url, timeout_s) -> status code; retry transient failures until success,
    the retry budget is spent, or the global deadline would be crossed."""
    res = Result(target)
    attempt = 0
    while True:
        if clock() >= deadline:
            res.outcome, res.reason = "down", "global deadline reached before the check ran"
            return res
        # Per-target timeout is also clipped to what is left of the global deadline.
        timeout = min(target.timeout_s, max(0.0, deadline - clock()))
        t0 = clock()
        try:
            status = http(target.url, timeout)
            att = Attempt(status, (clock() - t0) * 1000)
        except TimeoutError_ as e:
            att = Attempt(None, (clock() - t0) * 1000, f"timeout: {e}")
        except Exception as e:  # connection refused, DNS failure, ...
            att = Attempt(None, (clock() - t0) * 1000, f"{type(e).__name__}: {e}")
        res.attempts.append(att)

        if att.status == target.expected_status:
            res.outcome = "degraded" if attempt > 0 else "healthy"
            res.reason = f"ok after {attempt} retries" if attempt else "ok"
            return res
        if not is_transient(att.status):
            res.outcome, res.reason = "down", f"status {att.status}, not retried"
            return res
        if attempt >= max_retries:
            res.outcome, res.reason = "down", f"still failing after {attempt} retries ({att.error or att.status})"
            return res
        delay = backoff_delay(attempt, rng=rng)
        if clock() + delay >= deadline:
            res.outcome, res.reason = "down", "global deadline reached while backing off"
            return res
        sleep(delay)
        attempt += 1

# ---------------------------------------------------------------- all targets

def run_checks(targets: list[Target], http, *, workers: int = 8, deadline_s: float = 20.0,
               max_retries: int = 3, sleep=time.sleep, clock=time.monotonic,
               rng=random.random) -> list[Result]:
    """Check every target in a thread pool. Each check is IO-bound (waiting on a socket),
    so threads work well despite the GIL. Results keep the input order."""
    deadline = clock() + deadline_s
    results: dict[str, Result] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(check_target, t, http, max_retries=max_retries, deadline=deadline,
                               sleep=sleep, clock=clock, rng=rng): t for t in targets}
        for f in as_completed(futures):
            results[futures[f].name] = f.result()
    return [results[t.name] for t in targets]

def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile: the value at index ceil(p/100 * n) in the sorted list."""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(1, int(-(-p * len(s) // 100)))   # ceil without importing math
    return s[k - 1]

def summarize(results: list[Result]) -> dict:
    counts = {"healthy": 0, "degraded": 0, "down": 0}
    for r in results:
        counts[r.outcome] += 1
    lat = [r.last.latency_ms for r in results if r.last is not None and r.last.status is not None]
    return {
        **counts,
        "total": len(results),
        "critical_down": [r.target.name for r in results if r.outcome == "down" and r.target.critical],
        "p50_ms": round(percentile(lat, 50), 1),
        "p95_ms": round(percentile(lat, 95), 1),
        "total_retries": sum(r.retries for r in results),
    }

def prometheus_text(results: list[Result]) -> str:
    """Prometheus text exposition: one gauge per target plus attempt counters."""
    out = [
        "# HELP healthcheck_up 1 if the last attempt returned the expected status.",
        "# TYPE healthcheck_up gauge",
    ]
    for r in results:
        up = 1 if r.outcome in ("healthy", "degraded") else 0
        out.append(f'healthcheck_up{{target="{r.target.name}"}} {up}')
    out += ["# HELP healthcheck_latency_ms Latency of the last attempt in milliseconds.",
            "# TYPE healthcheck_latency_ms gauge"]
    for r in results:
        if r.last is not None:
            out.append(f'healthcheck_latency_ms{{target="{r.target.name}"}} {r.last.latency_ms:.3f}')
    out += ["# HELP healthcheck_attempts_total Attempts made in this run, including retries.",
            "# TYPE healthcheck_attempts_total counter"]
    for r in results:
        out.append(f'healthcheck_attempts_total{{target="{r.target.name}"}} {len(r.attempts)}')
    return "\n".join(out) + "\n"

# ---------------------------------------------------------------- self-checks

class FakeServer:
    """Scripted responses per URL. Each call pops the next item: an int status,
    "timeout", or a float meaning "sleep this long on the fake clock, then 200".
    The last item repeats forever. Thread-safe."""

    def __init__(self, scripts: dict[str, list], clock):
        self.scripts = {k: list(v) for k, v in scripts.items()}
        self.calls = {k: 0 for k in scripts}
        self.clock = clock
        self.lock = threading.Lock()

    def __call__(self, url: str, timeout_s: float) -> int:
        with self.lock:
            self.calls[url] += 1
            script = self.scripts[url]
            item = script.pop(0) if len(script) > 1 else script[0]
        if item == "timeout":
            self.clock.advance(timeout_s)
            raise TimeoutError_(f"no response within {timeout_s:.1f}s")
        if isinstance(item, float):
            self.clock.advance(item)
            return 200
        self.clock.advance(0.01)   # a normal response costs 10 ms
        return item

class FakeClock:
    """Monotonic clock the tests move by hand, so backoff sleeps cost no real time.
    Each thread has its own timeline (threading.local), so one worker's sleep cannot
    inflate the latency another worker measures; that keeps the checks deterministic."""

    def __init__(self):
        self.local = threading.local()

    def _state(self):
        if not hasattr(self.local, "t"):
            self.local.t = 1000.0
        return self.local

    def __call__(self) -> float:
        return self._state().t

    def advance(self, s: float) -> None:
        self._state().t += s

    def sleep(self, s: float) -> None:
        self.advance(s)

def _self_checks() -> None:
    clock = FakeClock()
    rng = random.Random(7).random
    fake = FakeServer({
        "https://api.internal/healthz":   [200],
        "https://auth.internal/healthz":  [503, 502, 200],      # transient, recovers
        "https://db.internal/healthz":    [500],                # permanent 5xx
        "https://cache.internal/healthz": ["timeout"],          # never answers
        "https://old.internal/healthz":   [404],                # 4xx, must not retry
        "https://slow.internal/healthz":  [0.35, 200],          # slow first reply, then fast
    }, clock)
    targets = [
        Target("api", "https://api.internal/healthz"),
        Target("auth", "https://auth.internal/healthz"),
        Target("db", "https://db.internal/healthz"),
        Target("cache", "https://cache.internal/healthz", timeout_s=1.0),
        Target("old", "https://old.internal/healthz", critical=False),
        Target("slow", "https://slow.internal/healthz"),
    ]
    results = run_checks(targets, fake, workers=4, deadline_s=30, max_retries=3,
                         sleep=clock.sleep, clock=clock, rng=rng)
    by = {r.target.name: r for r in results}

    def check(cond: bool, msg: str) -> None:
        if not cond:
            raise AssertionError(msg)
        print(f"check ok: {msg}")

    check(by["api"].outcome == "healthy" and by["api"].retries == 0, "api healthy on first attempt")
    check(by["auth"].outcome == "degraded" and by["auth"].retries == 2, "auth needed 2 retries, so degraded")
    check(by["db"].outcome == "down" and len(by["db"].attempts) == 4, "db 500 retried 3 times then down")
    check(by["cache"].outcome == "down" and all(a.status is None for a in by["cache"].attempts)
          and len(by["cache"].attempts) == 4, "cache timed out on all 4 attempts")
    check(by["old"].outcome == "down" and len(by["old"].attempts) == 1, "404 marked down after 1 attempt, no retry")
    check(fake.calls["https://old.internal/healthz"] == 1, "fake server saw exactly one call for the 404 target")
    check(by["slow"].outcome == "healthy" and by["slow"].last.latency_ms >= 349, "slow target healthy, latency recorded")

    rep = summarize(results)
    check(rep["healthy"] == 2 and rep["degraded"] == 1 and rep["down"] == 3, f"report counts {rep}")
    check(rep["critical_down"] == ["db", "cache"], "critical_down lists db and cache but not the non-critical 404")
    check(rep["total_retries"] == 2 + 3 + 3, "total retries = 8")
    check(rep["p50_ms"] == 10.0 and rep["p95_ms"] == 350.0, f"p50 {rep['p50_ms']} ms, p95 {rep['p95_ms']} ms")

    text = prometheus_text(results)
    check('healthcheck_up{target="auth"} 1' in text and 'healthcheck_up{target="db"} 0' in text,
          "prometheus text has up gauges")
    check('healthcheck_attempts_total{target="old"} 1' in text, "prometheus text has attempt counters")

    # Backoff math: full jitter never exceeds min(cap, base * 2**attempt).
    for attempt in range(8):
        for _ in range(200):
            d = backoff_delay(attempt, base_s=0.2, cap_s=5.0, rng=rng)
            assert 0 <= d <= min(5.0, 0.2 * 2 ** attempt)
    check(True, "backoff stays within 0 and min(cap, base * 2^attempt) over 1600 samples")
    check(not is_transient(404) and is_transient(503) and is_transient(None), "transient classification")

    # Global deadline: a 2 s budget cannot fit a 1 s timeout retried 4 times.
    clock2 = FakeClock()
    fake2 = FakeServer({"https://x.internal": ["timeout"]}, clock2)
    r2 = run_checks([Target("x", "https://x.internal", timeout_s=1.0)], fake2, deadline_s=2.0,
                    sleep=clock2.sleep, clock=clock2, rng=rng)[0]
    check(r2.outcome == "down" and "deadline" in r2.reason and len(r2.attempts) <= 3,
          f"global deadline cut retries short: {len(r2.attempts)} attempts, reason '{r2.reason}'")
    check(clock2() - 1000.0 <= 2.0 + 1e-9, "no attempt started after the deadline")

    exit_code = 2 if rep["critical_down"] else 0
    print(f"report: {rep}")
    print(f"exit code would be {exit_code} (critical targets down: {rep['critical_down']})")
    print("all self-checks passed")

def main(argv: list[str]) -> int:
    """healthcheck.py targets.json [--deadline 20] [--workers 8] [--metrics out.prom]"""
    if not argv:
        _self_checks()
        return 0
    path, deadline_s, workers, metrics = argv[0], 20.0, 8, ""
    i = 1
    try:
        while i < len(argv):
            if argv[i] == "--deadline":
                deadline_s = float(argv[i + 1]); i += 2
            elif argv[i] == "--workers":
                workers = int(argv[i + 1]); i += 2
            elif argv[i] == "--metrics":
                metrics = argv[i + 1]; i += 2
            else:
                print(f"unknown argument {argv[i]}", file=sys.stderr)
                return 2
    except (IndexError, ValueError) as e:   # flag without a value, or a value that is not a number
        print(f"bad arguments: {e}", file=sys.stderr)
        return 2
    results = run_checks(load_targets(path), http_get, workers=workers, deadline_s=deadline_s)
    for r in results:
        last = r.last
        lat = f"{last.latency_ms:.0f} ms" if last else "-"
        print(f"{r.outcome:8} {r.target.name:20} {lat:>8}  attempts={len(r.attempts)}  {r.reason}")
    rep = summarize(results)
    print(f"healthy={rep['healthy']} degraded={rep['degraded']} down={rep['down']} "
          f"p50={rep['p50_ms']}ms p95={rep['p95_ms']}ms retries={rep['total_retries']}")
    if metrics:
        with open(metrics, "w", encoding="utf-8") as f:
            f.write(prometheus_text(results))
    return 2 if rep["critical_down"] else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

## Follow-up questions interviewers ask

* The team wants this to run forever and scrape it with Prometheus instead of writing a file. What changes: the loop, the metric types, and how you avoid retries inflating the latency histogram?
* Add a circuit breaker so a target that has been down for 10 minutes is checked once a minute instead of every run. Where does the state live between runs?
* Rewrite `run_checks` with asyncio. What do you gain at 5,000 targets and what do you lose in debuggability?
* How would you honour `Retry-After` on a 429 or 503 without breaking the global deadline?
* A healthy target returns 200 in 20 ms but with a body that says `{"db": "disconnected"}`. Extend the target definition to cover it.
* Compare this script with a Kubernetes readiness probe: which of these concerns does the kubelet already handle, and which does it not?

## Lessons that cover this

* [#6Python and Go for automation and toolingFoundations](/devops/learn/python-and-go-for-devops)
* [#21SRE practice - SLOs, error budgets, incidents and postmortemsOperate](/devops/learn/sre-slos-incidents-postmortems)

## Further reading

* [Prometheus documentationGuideprometheus.io](https://prometheus.io/docs/introduction/overview/)
* [AWS Builders' Library (AWS Builder Center)Articlebuilder.aws.com](https://builder.aws.com/learn/topics/builders-library)
* [The Tail at ScalePaperresearch.google](https://research.google/pubs/the-tail-at-scale/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousBash: safe deploy script with locking, rollback and traps](/devops/problems/bash-safe-deploy-script)[NextDockerfile: multi-stage build with a non-root user](/devops/problems/multistage-dockerfile)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Approach](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Evaluation](#evaluation)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Reference solution](#code)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
