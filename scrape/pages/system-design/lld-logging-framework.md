# Logging Framework (like Log4j) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-logging-framework

[All system design questions](/system-design)

#53LLDMediumLow-level design

# Logging Framework (like Log4j)

chain of responsibilityobserversingletonasync

## Problem statement

Design a logging library: loggers with levels (DEBUG < INFO < WARN < ERROR), multiple appenders (console, file, remote), formatters, hierarchical logger configuration, and asynchronous non-blocking logging.

## Requirements

### Functional

* `logger.info(msg)`, etc.; per-logger level thresholds; hierarchical names (`com.app.db` inherits from `com.app`).
* Appenders: console, rolling file, network; multiple per logger.
* Formatters/layouts (pattern, JSON).
* Async mode with a bounded queue; configurable at runtime.

### Non-functional

* Minimal overhead when a level is disabled (check level before formatting).
* Thread-safe; no lost logs on normal shutdown (flush).
* Extensible appenders/formatters without modifying core.

## API

```
Logger LogManager.getLogger(String name)
void   Logger.log(Level, String msg, Object... args)   // + debug/info/warn/error helpers
void   Logger.setLevel(Level) ; void Logger.addAppender(Appender)
void   LogManager.configure(Config)   // levels, appenders, formatters
void   LogManager.shutdown()          // flush & close
```

## Data model

* `LogManager` (singleton): registry of loggers, config.
* `Logger(name, level, List<Appender>, parent, additivity)`.
* `LogEvent(level, loggerName, message, timestamp, threadName, throwable, context)`.
* `Appender` (interface): `append(LogEvent)`, `flush`, `close` → `ConsoleAppender`, `FileAppender`, `RollingFileAppender`, `AsyncAppender(wraps another)`.
* `Formatter` (interface): `format(LogEvent) → String` → `PatternFormatter`, `JsonFormatter`.
* `Filter` (interface) chain per appender: `accept(LogEvent)` → `LevelFilter`, `RegexFilter`.
* `Level` enum with ordinal comparison.

## Design

1. **Level check first**: `if (!isEnabled(level)) return;` before building the message — the main performance rule. Support lazy message suppliers.
2. **Hierarchy**: logger `a.b.c` resolves its effective level by walking parents until one is set; appenders are inherited if `additivity` is true (so root appenders catch everything).
3. **Chain of responsibility**: `LogEvent` passes through the logger's filters, then each appender's filters, then the formatter, then the sink.
4. **Async**: `AsyncAppender` puts events on a bounded `BlockingQueue`; a background thread drains to the delegate appender. Policy on full queue: block, drop with a counter, or discard low levels.
5. **Rolling file**: rotate by size/time; write through a buffered writer; flush on a timer and on shutdown; a lock per file.
6. **Config** loaded from a file, hot-reloadable; `LogManager` uses a read-write lock for config swaps.

## Class diagram

Rendering diagram…

## Deep dives

**Decorator for Async**: `AsyncAppender` wraps any appender — no special-casing in `Logger`.

**Context (MDC)**: thread-local map (request id, user id) merged into each event so distributed tracing works.

**Guaranteed delivery vs throughput**: sync file logging is safe but slow; async with a large queue is fast but can drop on crash — expose the choice.

**Formatting cost**: format once per event even with many appenders (cache the formatted string per formatter).

## Bottlenecks & mitigations

* Lock contention on a shared file appender → async appender with a single writer thread; batch writes.
* String formatting for disabled levels → level check + lazy suppliers.
* Queue overflow under log storms → bounded queue with drop policy and a dropped-counter metric.

## Failure modes

* **Disk full** → file appender switches to error mode, console fallback, alert; never throw into application code.
* **Crash with pending async events** → accept loss or use a sync appender for ERROR level.
* **Config reload with a bad file** → keep the old config; log the error.
* **Recursive logging** (appender logs via the same logger) → reentrancy guard.

## Code skeleton

```
import threading, queue, time, sys, json
from enum import IntEnum

class Level(IntEnum): DEBUG=10; INFO=20; WARN=30; ERROR=40

class LogEvent:
    def __init__(self, level, name, msg):
        self.level, self.name, self.msg, self.ts, self.thread = level, name, msg, time.time(), threading.current_thread().name

class PatternFormatter:
    def format(self, e): return f"{time.strftime('%H:%M:%S', time.localtime(e.ts))} [{e.thread}] {e.level.name} {e.name} - {e.msg}"
class JsonFormatter:
    def format(self, e): return json.dumps({"ts": e.ts, "level": e.level.name, "logger": e.name, "msg": e.msg})

class ConsoleAppender:
    def __init__(self, fmt=PatternFormatter()): self.fmt, self.lock = fmt, threading.Lock()
    def append(self, e):
        with self.lock: sys.stdout.write(self.fmt.format(e) + "\n")
    def flush(self): sys.stdout.flush()
    def close(self): self.flush()

class AsyncAppender:
    def __init__(self, delegate, maxsize=10000):
        self.d, self.q, self.dropped = delegate, queue.Queue(maxsize), 0
        self.t = threading.Thread(target=self._run, daemon=True); self.t.start()
    def _run(self):
        while True:
            e = self.q.get()
            if e is None: break
            self.d.append(e)
    def append(self, e):
        try: self.q.put_nowait(e)
        except queue.Full: self.dropped += 1
    def flush(self): self.q.join() if hasattr(self.q, "join") else None
    def close(self): self.q.put(None); self.t.join(); self.d.close()

class Logger:
    def __init__(self, name, parent=None):
        self.name, self.parent, self.level, self.appenders, self.additivity = name, parent, None, [], True
    def effective_level(self):
        l = self
        while l and l.level is None: l = l.parent
        return l.level if l else Level.INFO
    def enabled(self, level): return level >= self.effective_level()
    def log(self, level, msg, *args):
        if not self.enabled(level): return
        e = LogEvent(level, self.name, msg % args if args else msg)
        l = self
        while l:
            for a in l.appenders: a.append(e)
            l = l.parent if l.additivity else None
    def info(self, m, *a): self.log(Level.INFO, m, *a)
    def error(self, m, *a): self.log(Level.ERROR, m, *a)

class LogManager:
    _root = Logger("root"); _loggers = {}; _lock = threading.RLock()   # reentrant: get_logger recurses for parents
    @classmethod
    def get_logger(cls, name):
        with cls._lock:
            if name not in cls._loggers:
                parent = cls.get_logger(name.rsplit(".", 1)[0]) if "." in name else cls._root
                cls._loggers[name] = Logger(name, parent)
            return cls._loggers[name]
```

## Follow-up questions interviewers ask

* Add structured logging with key-value fields.
* Add sampling for high-volume DEBUG logs.
* How would you ship logs to a central system (see log aggregation HLD)?

[PreviousLibrary Management System](/system-design/lld-library-management)[NextIn-memory Pub/Sub Message Queue](/system-design/lld-in-memory-pubsub)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AtlassianAmazonMicrosoftSalesforceAdobe

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
