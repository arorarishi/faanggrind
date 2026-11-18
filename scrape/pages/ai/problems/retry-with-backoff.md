# Retry with exponential backoff and timeouts — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/retry-with-backoff

[AI problems](/ai#problems)

MLCODEImplement it#40Easy

# Retry with exponential backoff and timeouts

asyncioretriesexponential backoffjittertimeoutsreliabilityReported at Sierra

## Problem statement

Write an async `retry` helper in Python with asyncio, for calls to an unreliable remote service such as an LLM API. It runs one attempt at a time with a per-attempt timeout, waits between attempts using exponential backoff with a cap and full jitter, and stops at a maximum number of attempts or an overall deadline. It retries only errors that may pass on a second try, and it honours a retry-after hint from the server. Sleep, the clock and the random source are injectable, so the tests need no real waiting.

## Requirements

### Functional

* `retry(fn, ...)` awaits `fn()` and returns its result. Each attempt is cancelled after `attempt_timeout` seconds.
* Before the next attempt it sleeps a random time between 0 and `min(cap, base x 2^(attempt - 1))`. This is called full jitter.
* It retries only retryable errors: timeouts, dropped connections, and status 408, 429 and 5xx. Any other error is raised at once, unchanged.
* It stops after `max_attempts` attempts, or when the next sleep would cross the overall `deadline`. Then it raises `RetryError` with the attempt count and the last error.
* If the error carries `retry_after`, the sleep is at least that long.
* `sleep`, `rng` and `clock` are parameters with real defaults.

### Non-functional

* At most `max_attempts` calls to `fn` (default 5). A non-retryable error means exactly 1 call and 0 sleeps.
* With base 0.5 s and cap 30 s, the upper bounds of the sleeps are 0.5, 1, 2, 4, 8, 16, 30, 30 seconds. Every real sleep lies between 0 and its bound.
* No attempt runs longer than `attempt_timeout` (default 10 s), or longer than the time left before the `deadline` (default 60 s).
* The helper never sleeps past the deadline. It gives up before a sleep that would cross it.
* The self-checks run in under 1 second. Backoff sleeps are faked, and only two 20 ms timeouts use real time.

## API

```
class ApiError(Exception):
    def __init__(self, status: int, message: str = "", retry_after: float | None = None): ...

class RetryError(Exception):
    reason: str                # "max_attempts" or "deadline"
    attempts: int              # calls to fn that were made
    last_error: Exception      # also set as __cause__

def is_retryable(exc: Exception) -> bool: ...

def backoff_delay(attempt: int, base: float = 0.5, cap: float = 30.0, rng=random.random) -> float: ...

async def retry(
    fn,                              # zero-argument coroutine function: one attempt
    *,
    max_attempts: int = 5,
    attempt_timeout: float = 10.0,   # seconds for one attempt
    deadline: float = 60.0,          # seconds for the whole call, sleeps included
    base: float = 0.5,
    cap: float = 30.0,
    retryable=is_retryable,
    sleep=asyncio.sleep,
    rng=random.random,               # returns a float in [0, 1)
    clock=time.monotonic,
): ...

# usage
text = await retry(lambda: client.complete(prompt), max_attempts=4, deadline=30.0)
```

## Data model

```
State inside one retry call
  attempt       1, 2, 3, ...                        counts calls to fn
  start         clock() when retry was called
  remaining     deadline - (clock() - start)        seconds left for everything
  last_error    the most recent retryable error

Delay before the next attempt
  bound         min(cap, base * 2^(attempt - 1))    0.5, 1, 2, 4, 8, 16, 30, 30, ...
  delay         rng() * bound                       full jitter: uniform in [0, bound)
  delay         max(delay, retry_after)             only when the server sent a hint

Error classes
  retry          TimeoutError, ConnectionError, ApiError 408 / 429 / 5xx
  raise at once  every other error, for example ApiError 400, 401, 403, 404, 422
  RetryError     reason, attempts, last_error
```

## Approach

1. Decide what is retryable before writing the loop. A timeout, a dropped connection, a 408, a 429 or a 5xx may pass next time. A 400 or a 401 fails the same way every time, so it is raised at once.
2. Write `backoff_delay(attempt)`. The bound doubles on each attempt, `base x 2^(attempt - 1)`, and is capped at `cap`. Multiply the bound by a random number in [0, 1) to get full jitter.
3. In `retry`, record `start = clock()` and loop over attempts 1 to `max_attempts`.
4. Before each attempt compute the time left. Run `fn()` inside `asyncio.wait_for` with a timeout of `min(attempt_timeout, remaining)`, so one attempt cannot outlive the deadline.
5. On success, return the result. On an error that is not retryable, re-raise it unchanged. Otherwise keep it as `last_error`.
6. If that was the final attempt, leave the loop without sleeping.
7. Compute the delay. If the error has `retry_after`, take the larger of the two. If the delay would reach the deadline, raise `RetryError("deadline")` now: sleeping for an attempt that cannot run only wastes the caller's time.
8. Otherwise `await sleep(delay)` and go round again. After the loop, raise `RetryError("max_attempts")` with the attempt count, chained to the last error.
9. For tests, pass a fake clock whose `sleep` only adds to a counter, and an `rng` that returns 1.0, so every delay sits exactly on its bound.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why jitter

Suppose a service fails for a moment and 1,000 clients all retry after exactly 0.5 s, then 1 s, then 2 s. Each wave arrives at the same instant and can knock the service over again. Full jitter picks each delay at random between 0 and the bound, so the same 1,000 retries are spread over the whole window.

### Idempotency

A timeout does not mean the request failed. The server may have finished the work, and only the reply was lost. Retrying a read is safe. Retrying "charge the card" or "send the email" can do it twice. Retry a write only if it is **idempotent**, meaning that repeating it has no extra effect. The usual way is an idempotency key in the request, which lets the server detect the repeat.

### Retry budgets and circuit breakers

Retries multiply load: 3 layers that each try 3 times can send 27 calls for one user request. A retry budget caps retries at a share of normal traffic, for example 10%. A circuit breaker stops calling a service after repeated failures and tests it again later.

### LLM APIs

A rate limit arrives as status 429, often with a retry-after value: wait at least that long. Requests are slow, so set the attempt timeout from measured latency. A stream can fail after half the answer has been shown. A retry generates new and different text, so either buffer the output before showing it, or discard the partial answer and start again.

## Evaluation

**Correctness tests.** All of them use a fake clock, so sleeps are recorded and not waited for.

* Success after two failures: 3 calls, and sleeps of exactly 0.5 s and 1.0 s with `rng` fixed at 1.0.
* A 400 is raised as the original `ApiError` after 1 call and 0 sleeps.
* Classification: a timeout, a dropped connection, 408, 429, 500 and 503 are retryable; 400, 401, 403, 404, 422 and a `ValueError` are not.
* Backoff: with `rng` at 1.0, base 0.5 and cap 4, eight attempts sleep 0.5, 1, 2, 4, 4, 4, 4. That is 7 sleeps, with none after the last attempt. With a seeded random source every sleep lies between 0 and its bound, and the 7 values differ.
* Deadline: delays of 1, 2 and 4 s bring the clock to 7 s. The next delay of 8 s would cross 10 s, so the helper stops after 4 attempts.
* Retry-after: a 7 s hint wins over a 0 s jittered delay, a 0.2 s hint loses to a 0.5 s backoff, and a 120 s hint with a 60 s deadline fails without sleeping.
* Timeout: a hung attempt is cancelled after 20 ms of real time and the second attempt succeeds. The real-time assertion only requires far less than the 5 s hang, so a busy machine cannot fail it.

**Complexity.** O(1) memory and at most `max_attempts` calls. The total wait is bounded by the deadline.

**What a strong answer adds.** Asking whether the call is idempotent before writing any code. An `on_retry` hook for logs and metrics. A little jitter on top of retry-after, because many clients receive the same hint. Pointing out that `CancelledError` is not caught, so cancelling the caller still works.

## Bottlenecks & mitigations

* Retries add load at the moment the service is weakest. Without a retry budget, a short outage can become a long one.
* A caller may wait for the full deadline (60 s by default) before it learns of a failure.
* Every layer that retries multiplies the calls below it. Retry in one layer only.
* `asyncio.wait_for` cancels the local task, but the server may keep working on the abandoned request.

## Failure modes

* **Retrying a client error.** A 400 fails the same way every time, so 5 attempts only waste time and quota. Mitigation: classify errors and raise non-retryable ones at once.
* **No jitter.** All clients retry at the same instants and overload the service again. Mitigation: full jitter.
* **No cap.** At base 0.5 s the tenth delay is 256 s. Mitigation: `min(cap, ...)` and an overall deadline.
* **Retrying a write that is not idempotent.** The first attempt succeeded on the server but timed out on the client, and the retry charges the customer twice. Mitigation: an idempotency key, or no retries for that call.
* **Sleeping after the final attempt.** The caller waits one more delay for nothing. Mitigation: check for the last attempt before computing the delay. The test counts 7 sleeps for 8 attempts.
* **Ignoring retry-after.** The client comes back early and is rejected again. Mitigation: use the hint as a floor under the delay.
* **Swallowing cancellation.** Catching `BaseException` would retry a task that its caller cancelled. Mitigation: catch `Exception` only.
* **Tests that really sleep.** A suite with real backoff takes minutes, so people stop running it. Mitigation: inject `sleep`, `clock` and `rng`.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""Async retry: per-attempt timeout, capped exponential backoff with full jitter,
a maximum number of attempts and an overall deadline.

sleep, rng and clock are parameters, so the self-checks swap in fakes and run
in milliseconds with the same result every time.
"""
import asyncio
import random
import time

class ApiError(Exception):
    """An HTTP-style failure. retry_after is the server's hint in seconds, if it sent one."""

    def __init__(self, status, message="", retry_after=None):
        super().__init__(f"{status} {message}".strip())
        self.status = status
        self.retry_after = retry_after

class RetryError(Exception):
    """Raised when we stop retrying. Carries the attempt count and the last error."""

    def __init__(self, reason, attempts, last_error):
        super().__init__(f"gave up ({reason}) after {attempts} attempts: {last_error!r}")
        self.reason = reason                # "max_attempts" or "deadline"
        self.attempts = attempts
        self.last_error = last_error

def is_retryable(exc):
    """Retry what may pass on a second try. Never retry a client error such as 400, 401 or 404."""
    # asyncio.TimeoutError is the built-in TimeoutError from Python 3.11 on; older versions need both.
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True                         # the attempt timed out or the connection dropped
    if isinstance(exc, ApiError):
        return exc.status in (408, 429) or exc.status >= 500    # timeout, rate limit, server error
    return False

def backoff_delay(attempt, base=0.5, cap=30.0, rng=random.random):
    """Full jitter: uniform between 0 and min(cap, base * 2^(attempt - 1)). attempt starts at 1."""
    return rng() * min(cap, base * 2 ** (attempt - 1))

async def retry(fn, *, max_attempts=5, attempt_timeout=10.0, deadline=60.0, base=0.5, cap=30.0,
                retryable=is_retryable, sleep=asyncio.sleep, rng=random.random, clock=time.monotonic):
    """Call the zero-argument coroutine function fn until it succeeds.

    Returns fn's result. Raises the original error at once if it is not retryable,
    or RetryError when attempts or the deadline run out.
    """
    start = clock()
    last_error = None
    for attempt in range(1, max_attempts + 1):
        remaining = deadline - (clock() - start)
        if remaining <= 0:
            raise RetryError("deadline", attempt - 1, last_error) from last_error
        try:
            # One attempt may use at most attempt_timeout, and never more than the time left.
            return await asyncio.wait_for(fn(), timeout=min(attempt_timeout, remaining))
        except Exception as exc:            # CancelledError is not an Exception, so it passes through
            if not retryable(exc):
                raise                       # a client error will fail the same way every time
            last_error = exc
        if attempt == max_attempts:
            break                           # no sleep after the final attempt
        delay = backoff_delay(attempt, base, cap, rng)
        hint = getattr(last_error, "retry_after", None)
        if hint is not None:
            delay = max(delay, hint)        # the server said when: never come back earlier
        if clock() - start + delay >= deadline:
            raise RetryError("deadline", attempt, last_error) from last_error   # do not sleep past the deadline
        await sleep(delay)
    raise RetryError("max_attempts", max_attempts, last_error) from last_error

# ---- Test doubles ---------------------------------------------------------------
class FakeTime:
    """A clock that only moves when someone sleeps. Records every sleep."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

class Flaky:
    """Raises the scripted errors in order, then returns "ok". Counts its calls."""

    def __init__(self, *errors):
        self.errors = list(errors)
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return "ok"

async def self_checks():
    def fakes(rng=lambda: 1.0):             # rng 1.0 means every delay sits at its upper bound
        t = FakeTime()
        return t, dict(sleep=t.sleep, clock=t.clock, rng=rng)

    # 1. Success after two failures: 3 calls, 2 sleeps, the result comes back.
    t, kw = fakes()
    fn = Flaky(ApiError(503), ApiError(429))
    assert await retry(fn, **kw) == "ok" and fn.calls == 3 and t.sleeps == [0.5, 1.0]
    print("success after two failures ok: 3 calls, sleeps", t.sleeps)

    # 2. A client error is raised at once, unwrapped, with no sleep.
    t, kw = fakes()
    fn = Flaky(ApiError(400, "bad request"), ApiError(503))
    try:
        await retry(fn, **kw)
        raise AssertionError("a 400 must not be retried")
    except ApiError as exc:
        assert exc.status == 400 and fn.calls == 1 and t.sleeps == []
    print("non-retryable ok: 400 raised after 1 call and 0 sleeps")
    retry_these = (asyncio.TimeoutError(), ConnectionResetError(), ApiError(408), ApiError(429),
                   ApiError(500), ApiError(503))
    raise_these = (ApiError(400), ApiError(401), ApiError(403), ApiError(404), ApiError(422), ValueError("a bug"))
    assert all(is_retryable(e) for e in retry_these) and not any(is_retryable(e) for e in raise_these)
    print("classification ok: timeout, dropped connection, 408, 429, 500, 503 retry; 400, 401, 403, 404, 422 do not")

    # 3. Backoff: upper bounds double up to the cap, and jitter stays inside them.
    t, kw = fakes()
    fn = Flaky(*[ApiError(500)] * 20)
    try:
        await retry(fn, max_attempts=8, base=0.5, cap=4.0, deadline=1e9, **kw)
        raise AssertionError("must give up")
    except RetryError as exc:
        assert (exc.reason, exc.attempts, fn.calls) == ("max_attempts", 8, 8)
        assert isinstance(exc.last_error, ApiError) and exc.__cause__ is exc.last_error
    bounds = t.sleeps
    assert bounds == [0.5, 1.0, 2.0, 4.0, 4.0, 4.0, 4.0]           # 7 sleeps for 8 attempts
    t, kw = fakes(rng=random.Random(7).random)
    try:
        await retry(Flaky(*[ApiError(500)] * 20), max_attempts=8, base=0.5, cap=4.0, deadline=1e9, **kw)
    except RetryError:
        pass
    assert len(t.sleeps) == 7 and all(0 <= s <= b for s, b in zip(t.sleeps, bounds))
    assert len(set(t.sleeps)) == 7 and t.sleeps != bounds           # jitter really spreads the delays
    print("backoff ok: bounds", bounds, "| jittered", [round(s, 2) for s in t.sleeps])

    # 4. The deadline stops retries: sleeps 1 + 2 + 4 = 7 s, and the next sleep of 8 s would cross 10 s.
    t, kw = fakes()
    fn = Flaky(*[ApiError(503)] * 20)
    try:
        await retry(fn, max_attempts=10, base=1.0, cap=100.0, deadline=10.0, **kw)
        raise AssertionError("must give up")
    except RetryError as exc:
        assert (exc.reason, exc.attempts, fn.calls) == ("deadline", 4, 4)
        assert t.sleeps == [1.0, 2.0, 4.0] and t.now == 7.0
    print("deadline ok: gave up after 4 attempts at t = 7 s, did not start an 8 s sleep with 3 s left")

    # 5. Retry-after: the hint is a floor under the delay, and a hint past the deadline fails fast.
    t, kw = fakes(rng=lambda: 0.0)          # jitter alone would sleep 0 s
    fn = Flaky(ApiError(429, retry_after=7.0))
    assert await retry(fn, **kw) == "ok" and t.sleeps == [7.0]
    t, kw = fakes()                          # backoff bounds are 0.5 s, then 1 s
    fn = Flaky(ApiError(429, retry_after=0.2), ApiError(429, retry_after=3.0))
    assert await retry(fn, **kw) == "ok" and t.sleeps == [0.5, 3.0]
    t, kw = fakes()
    fn = Flaky(ApiError(429, retry_after=120.0))
    try:
        await retry(fn, deadline=60.0, **kw)
        raise AssertionError("must give up")
    except RetryError as exc:
        assert (exc.reason, exc.attempts) == ("deadline", 1) and t.sleeps == []
    print("retry-after ok: a 7 s hint beat a 0 s jittered delay; a 120 s hint with a 60 s deadline failed at once")

    # 6. Per-attempt timeout (real time, 20 ms): the hung attempt is cancelled and retried.
    state = {"calls": 0, "cancelled": 0}

    async def hangs_once():
        state["calls"] += 1
        if state["calls"] == 1:
            try:
                await asyncio.sleep(5)      # a request that never answers
            except asyncio.CancelledError:
                state["cancelled"] += 1
                raise
        return "ok"

    t, kw = fakes()
    started = time.monotonic()
    assert await retry(hangs_once, attempt_timeout=0.02, **kw) == "ok"
    assert state == {"calls": 2, "cancelled": 1} and time.monotonic() - started < 4.0   # far below the 5 s hang
    print(f"timeout ok: attempt 1 was cancelled after 20 ms, attempt 2 succeeded "
          f"({time.monotonic() - started:.2f} s of real time)")

    # 7. The deadline also caps a single attempt: a 10 s attempt timeout with 20 ms left waits 20 ms.
    async def slow():
        await asyncio.sleep(5)

    t, kw = fakes()
    started = time.monotonic()
    try:
        await retry(slow, max_attempts=1, attempt_timeout=10.0, deadline=0.02, **kw)
        raise AssertionError("must give up")
    except RetryError as exc:
        assert isinstance(exc.last_error, asyncio.TimeoutError) and exc.attempts == 1
        assert time.monotonic() - started < 4.0                 # far below the 5 s hang
    print("deadline caps the attempt ok: a 10 s attempt timeout was cut to the 20 ms left")
    print("all checks passed")

if __name__ == "__main__":
    asyncio.run(self_checks())
```

## Follow-up questions interviewers ask

* Add a circuit breaker in front of `retry`. What are its states, and when does it let a test request through?
* Add a retry budget shared by all callers in the process.
* How do you make a "create order" call safe to retry?
* The call streams tokens and fails after 200 of them were shown to the user. What do you do?
* Compare full jitter with equal jitter and decorrelated jitter.
* A request passes through a client, a gateway and a model server. Which layer should retry?

## Lessons that cover this

* [#12Agents from first principles - build a mini frameworkAgents](/ai/learn/agents-first-principles)

## Further reading

* [Python asyncio documentationGuidedocs.python.org](https://docs.python.org/3/library/asyncio.html)
* [Exponential Backoff And Jitter (AWS Architecture Blog)Articleaws.amazon.com](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
* [Rate limits (Claude Platform documentation)Guideplatform.claude.com](https://platform.claude.com/docs/en/api/rate-limits)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousMinimal RAG loop: chunk, embed, retrieve, prompt](/ai/problems/minimal-rag-loop)

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
