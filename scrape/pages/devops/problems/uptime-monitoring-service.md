# Uptime monitoring service with global probes and alerting — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/uptime-monitoring-service

[DevOps problems](/devops#problems)

DESIGNPlatform design#19Medium

# Uptime monitoring service with global probes and alerting

redis-streamsworkersschedulertime-seriesalertingwebsocket

## Problem statement

Design an uptime monitor like BetterStack. A user registers a URL; the service probes it every 30 seconds from 3 regions (Mumbai, Frankfurt, Virginia), records the result, and sends an alert when the site is down, but only after a second region confirms it. Each monitor has a public status page and 90 days of history, and a live view that updates as checks arrive. The service must scale to 100,000 monitors with a small team running it.

## Requirements

### Functional

* Users create, pause and delete HTTP monitors (URL, method, expected status, timeout, interval fixed at 30 seconds) through a REST API and a web UI.
* Every monitor is probed from 3 regions on schedule; each check records region, status code, latency and an error string.
* A monitor becomes DOWN when 2 of 3 regions fail in the same round and UP again when 2 of 3 succeed; each transition sends exactly one alert per channel (email, Slack webhook, SMS) with retries.
* A public status page per monitor shows the current state, 24-hour latency and 90-day daily uptime, and a WebSocket live view streams new checks to the dashboard.
* Users are tenants: they see only their monitors, and each plan limits monitors and alert channels.

### Non-functional

* A check is executed within 5 seconds of its scheduled time at p99, even with 100,000 monitors.
* Downtime is alerted within 90 seconds of the first failed check (two rounds plus confirmation).
* No alert is lost and no transition sends duplicate alerts, even when a worker or a region crashes mid-round.
* Status pages serve 1,000 requests per second with under 200 ms latency from cache, and keep serving during a database outage.
* 90 days of history for every monitor at under 30 GB of storage for 100,000 monitors.
* Infrastructure cost under 6,000 USD per month at full scale.

## Back-of-the-envelope estimates

**Probe rate.** 100,000 monitors every 30 seconds is 3,333 probes per second per region, 10,000 per second across 3 regions. Assume a probe averages 1.5 seconds including slow sites and timeouts.

**Workers.** Assume one worker pod handles 200 probes per second with 300 requests in flight (200 x 1.5 s). A region needs 3,333 / 200 = 16.7, so 17 workers, 20 with headroom; 60 across the 3 regions. Each is a small pod (0.5 vCPU, 512 MiB): the work is waiting on sockets.

**Redis streams.** Each job entry is about 200 bytes. 3,333 entries per second per region is 0.67 MB per second; with `MAXLEN ~ 600000` the stream keeps 3 minutes of jobs, 120 MB per region. Results flow back at 10,000 entries per second, 2 MB per second in total, well inside what one Redis node handles.

**Storage.** Raw checks: 10,000 per second x 86,400 = 864 million per day. At 60 bytes per row that is 52 GB per day, too much to keep. Keep raw rows for 7 days (363 GB, compressed in a time-series store), then roll up. Hourly rollups: 100,000 monitors x 3 regions x 24 hours = 7.2 million rows per day at 40 bytes = 288 MB per day, 26 GB for 90 days. Daily rollups: 300,000 rows per day, negligible. The 90-day target is met by rollups, not raw data.

**Bandwidth.** Assume 2 KB per probe (request, response headers and a truncated body): 20 MB per second outbound, 160 Mbit per second, about 52 TB per month.

**Cost (assumed prices).** 60 worker pods on 10 small nodes at 0.085 USD per hour each: 620 USD. Redis, a primary plus replica pair per region at 0.2 USD per hour per pair: 3 x 0.2 x 730 = 438 USD. Time-series database, 2 nodes at 0.5 USD per hour: 730 USD. API and scheduler nodes: 219 USD. Egress and load balancers: about 1,500 USD. Total about 3,500 USD per month, under the 6,000 USD target.

## API

```
REST API (per user, JWT from the identity service)
  POST   /v1/monitors            {url, method, expected_status, timeout_ms, regions, channels}
  GET    /v1/monitors/{id}       state, last check per region, uptime_24h, uptime_90d
  PATCH  /v1/monitors/{id}       {paused: true}
  DELETE /v1/monitors/{id}
  GET    /v1/monitors/{id}/checks?from=&to=&region=   raw checks (last 7 days) or hourly rollups
  POST   /v1/channels            {type: email|slack|sms, target}
  GET    /v1/incidents?monitor=  open and closed incidents with the confirming regions

Public
  GET    /status/{slug}          cached HTML or JSON, Cache-Control: max-age=30
  WSS    /v1/live?monitor=       pushes {region, status, latency_ms, at} as checks arrive

Internal streams (Redis, one per region for jobs, one global for results)
  XADD jobs:mumbai MAXLEN ~ 600000 * monitor_id 42 url https://... timeout_ms 10000 scheduled_at 1730630000
  XREADGROUP GROUP probers w-7 COUNT 50 BLOCK 2000 STREAMS jobs:mumbai >
  XACK jobs:mumbai probers <id>
  XAUTOCLAIM jobs:mumbai probers w-7 60000 0-0 COUNT 100      reclaim entries idle over 60 s
  XADD results * monitor_id 42 region mumbai status 503 latency_ms 812 scheduled_at ...
```

## Data model

```
PostgreSQL (control data)
  users(id, plan, monitor_limit, channel_limit)
  monitors(id, user_id, url, method, expected_status, timeout_ms, slot SMALLINT, paused, state ENUM(up, down, pending))
      slot = hash(id) % 30: the second within each 30 s round when this monitor is probed
  channels(id, user_id, type, target)
  incidents(id, monitor_id, started_at, ended_at, confirming_regions TEXT[])
  notifications(id, incident_id, channel_id, kind ENUM(down, up), status ENUM(queued, sent, failed),
                attempts, UNIQUE(incident_id, channel_id, kind))

Time-series store (TimescaleDB hypertable or ClickHouse)
  checks(monitor_id, region, scheduled_at, status, latency_ms, error)   kept 7 days, compressed after 1 day
  checks_hourly(monitor_id, region, hour, total, failed, p50_ms, p95_ms)  kept 90 days
  checks_daily(monitor_id, day, total, failed, uptime_pct)               kept 400 days

Redis (per region)
  jobs:{region}        stream, consumer group "probers", one consumer per worker pod
  results              stream, consumer group "pushers"
  round:{monitor_id}:{scheduled_at}   HASH region -> status, TTL 120 s, used for 2-of-3 confirmation
  status:{slug}        cached status page JSON, TTL 30 s
```

## High-level design

1. **API service** (stateless, 3 replicas behind a load balancer) validates input, enforces the plan limits, writes monitors to PostgreSQL and assigns each a `slot` from 0 to 29 so monitors are spread evenly over the 30-second round.
2. **Scheduler** runs as a single leader (a Kubernetes Lease decides the leader; 2 standby replicas). Every second it loads the monitors whose slot equals the current second from an in-memory copy of the monitors table (refreshed on change through a PostgreSQL `LISTEN` channel) and `XADD`s one job to each region's stream. That is about 3,333 `XADD` calls per region per second, sent in a pipeline.
3. **Regional workers** run in each region's cluster and read their own region's stream with `XREADGROUP` in a consumer group. A worker runs probes concurrently, writes the result to the global results stream and only then `XACK`s the job. Jobs left pending for over 60 seconds, which means a worker died, are taken over by another worker with `XAUTOCLAIM`.
4. **Pusher** (consumer group on the results stream) does three things per result: inserts the row into the time-series store in batches of 500, writes the region's verdict into the round hash `round:{monitor_id}:{scheduled_at}`, and runs the confirmation rule. If 2 of 3 regions have reported failure and the monitor is UP, it opens an incident and inserts one notification row per channel; if 2 of 3 report success and the monitor is DOWN, it closes the incident.
5. **Notifier** polls queued notifications, sends them, and retries with backoff up to 5 times. The unique key on `(incident_id, channel_id, kind)` makes a crash-and-retry safe: a second insert fails, a second send is skipped.
6. **Rollups** run as hourly and daily jobs that aggregate the raw checks and delete raw rows older than 7 days.
7. **Status pages** are rendered from a Redis cache with a 30-second TTL and served through a CDN; the live view is a WebSocket service that subscribes to a Redis pub/sub channel per monitor that the pusher publishes to.

## Architecture diagram

Rendering diagram…

## Deep dives

### The scheduler and the thundering herd at second zero

The naive design is a cron that fires every 30 seconds and enqueues all 100,000 monitors at once. Every region gets a burst of 100,000 jobs, workers idle for 25 seconds and overloaded for 5, Redis memory spikes, and target sites see all three regions at the same instant. The fix is to give each monitor a fixed slot, `hash(id) % 30`, and have the scheduler enqueue only that slot's monitors each second: 3,333 jobs per second, flat. The slot is stored with the monitor so its checks are always 30 seconds apart. A single scheduler leader is enough at this size (3,333 pipelined `XADD` calls per region per second), and the Lease makes failover automatic; a missed second after failover is one skipped check, not an outage. The entry carries `scheduled_at`, and a pusher that sees two results for the same monitor, region and `scheduled_at` keeps the first.

### Redis streams semantics for at-least-once probing

A stream is an append-only log; a consumer group lets many workers share it so each entry is delivered to one consumer. `XREADGROUP GROUP probers w-7 ... STREAMS jobs:mumbai >` returns entries never delivered to anyone and records them in the pending entries list for `w-7`. The worker runs the probe, writes the result, then calls `XACK`, which removes the entry from pending. If the worker dies between read and ack, the entry stays pending; `XPENDING jobs:mumbai probers - + 100` shows it with its idle time and delivery count, and `XAUTOCLAIM jobs:mumbai probers w-3 60000 0-0 COUNT 100` lets `w-3` take over entries idle for more than 60,000 milliseconds. This is at-least-once delivery: a job may run twice, which is harmless as long as the pusher de-duplicates on `(monitor_id, region, scheduled_at)`. A job whose delivery count passes 3 is dropped and logged. `MAXLEN ~ 600000` on `XADD` trims old entries; `~` means approximate trimming, which is faster. `NOACK` would give at-most-once and is wrong here, and a plain list with `BLPOP` loses the entry the moment a crashed worker pops it.

### False positives and regional confirmation

One region failing is often the region's problem: a bad DNS resolver, a routing blip, or the target rate-limiting one source IP. Alerting on a single failure creates noise that users turn off. The rule "down when 2 of 3 regions fail in the same round" cuts most of it, and the round hash in Redis makes it cheap: each region writes its verdict with `HSET round:{id}:{ts} mumbai fail`, and the pusher counts. The decision is taken when the second failure arrives, not when all three have reported, so a dead region cannot delay alerts; the hash has a 120-second TTL. When a whole region is down its stream grows unread; the scheduler notices from `XLEN`, marks the region absent, the rule becomes 2 of the 2 live regions and operators are paged. One immediate retry inside the worker on connection errors (none on a 5xx) removes the last one-off failures without hiding real ones.

### Storing and downsampling 90 days

Raw checks are the biggest table by far, 864 million rows per day, and nobody looks at a 60-day-old individual check. The design keeps raw rows for 7 days in a column-compressed time-series store (TimescaleDB with compression, or ClickHouse), then relies on hourly rollups (total, failed, p50 and p95 latency) for the 90-day views and daily rollups for the uptime percentage. A job runs once per hour for the previous hour and is safe to re-run because it overwrites by `(monitor_id, region, hour)`. Uptime for 90 days is `1 - sum(failed) / sum(total)` over daily rows, 90 rows per monitor rather than 777,600 raw checks. The status page reads only rollups plus the last 24 hours of raw data, so it stays fast while raw inserts are heavy.

## Evaluation

**SLIs.** Scheduling delay: `executed_at - scheduled_at` per check, p99 under 5 seconds. Alert latency: time from first failed check to notification sent, p95 under 90 seconds. Pending backlog: `XPENDING` count and oldest idle time per region, alert when over 10,000 or over 60 seconds. Results lag: age of the oldest unacknowledged results entry. Duplicate alerts per incident (target 0). Status page cache hit ratio above 95 percent.

**Chaos tests.** Kill half the workers in one region under load and confirm pending entries are reclaimed within 90 seconds and no check is lost. Cut the Frankfurt cluster from Redis entirely and confirm the 2-of-2 fallback and the operator alert. Kill the pusher mid-batch and confirm no duplicate rows and no duplicate notifications (unique key). Kill the scheduler leader and measure the gap until the standby takes the Lease. Block a target site for one region only and confirm no user alert is sent.

**Cost review.** Monthly: storage growth per day against the 30 GB budget, egress per region, worker utilisation (target 60 to 70 percent so a burst has headroom).

**Security checks.** Probe workers must not reach internal addresses: resolve the URL first and reject private ranges (SSRF), and run workers in a network that cannot reach the control plane database. Per-user rate limits on the API and on monitor creation. Status page slugs are random, not sequential.

## Bottlenecks & mitigations

* The results stream and the pusher are the single funnel for 10,000 results per second; batch inserts and more pusher consumers are the lever, and the stream's `MAXLEN` must cover a pusher outage.
* The scheduler's in-memory monitor list must stay in sync with PostgreSQL; a stale list keeps probing deleted monitors.
* Raw check inserts dominate database I/O; compression and a short raw retention are what make the time-series store affordable.
* A single Redis per region is a hard dependency for that region's probes; use a replica with automatic failover and alert on replication lag.
* Outbound egress and connection limits per worker node; keep-alive pools per target host and sensible timeouts matter more than CPU.

## Failure modes

* **All monitors fire at second zero.** Workers idle then flooded, targets see synchronized traffic. Mitigation: per-monitor slots spread over the 30-second round.
* **Worker dies after probing but before XACK.** The job is re-delivered and probed twice. Mitigation: accept at-least-once; de-duplicate results on monitor, region and scheduled time.
* **A region loses its network.** Its stream grows and its verdicts stop. Mitigation: scheduler detects the stalled stream, confirmation rule falls back to the live regions, operators are paged.
* **Pusher crash during notification creation.** The same incident alerts twice. Mitigation: unique key on incident, channel and kind; idempotent inserts.
* **Slack webhook is down.** Notifications pile up. Mitigation: retries with backoff and a maximum, per-channel circuit breaker, email as a fallback channel.
* **PostgreSQL outage.** New monitors cannot be created and incident state cannot be written. Mitigation: status pages served from the Redis cache and CDN; workers keep probing from the stream; the pusher buffers incidents in Redis until the database returns.
* **A user registers an internal IP as a target.** Workers become an SSRF proxy. Mitigation: resolve and reject private and link-local ranges before every probe, and egress NetworkPolicy on worker pods.

## Follow-up questions interviewers ask

* A customer wants checks every 10 seconds. What changes in the scheduler, Redis sizing and storage, and what do you charge for it?
* How do you add TCP, DNS and ICMP checks without changing the stream protocol?
* A region's probes show 5 percent failures against one target because the target rate-limits that region's IP. How do you detect and handle it?
* Users want a maintenance window with no alerts. Where in the pipeline does that check belong?
* How would you build the WebSocket live view to handle 20,000 open dashboards across several pods?
* Replace Redis streams with Kafka or SQS. What do you gain and lose for this workload?

## Lessons that cover this

* [#7Web servers, reverse proxies and TLS - Nginx, certificates, process managersBuild and ship](/devops/learn/nginx-reverse-proxy-tls)
* [#20Observability - Prometheus, Grafana, OpenTelemetry, logs and alertingOperate](/devops/learn/observability-prometheus-grafana-otel)
* [#21SRE practice - SLOs, error budgets, incidents and postmortemsOperate](/devops/learn/sre-slos-incidents-postmortems)
* [#24Scaling and resilience - caching, queues, rate limiting, DDoS, DROperate](/devops/learn/scaling-and-resilience)
* [#31Projects - pipeline, cluster, observability, operatorLater](/devops/learn/projects)

## Further reading

* [Redis StreamsGuideredis.io](https://redis.io/docs/latest/develop/data-types/streams/)
* [The Tail at ScalePaperresearch.google](https://research.google/pubs/the-tail-at-scale/)
* [Google SRE Workbook: Chapter 5 - Alerting on SLOsArticlesre.google](https://sre.google/workbook/alerting-on-slos/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousGPU inference platform on EKS for OpenAI-compatible LLM serving](/devops/problems/gpu-inference-platform)[NextAutoscaled self-hosted CI runners on Kubernetes](/devops/problems/self-hosted-ci-runners)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [High-level design](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Evaluation](#evaluation)
10. [Bottlenecks](#bottlenecks)
11. [Failure modes](#failures)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
