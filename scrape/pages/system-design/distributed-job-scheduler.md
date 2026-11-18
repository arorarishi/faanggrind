# Distributed Job Scheduler (cron-as-a-service, Airflow-like) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/distributed-job-scheduler

[All system design questions](/system-design)

#27HLDHardHigh-level design

# Distributed Job Scheduler (cron-as-a-service, Airflow-like)

schedulingleader electionat-least-onceDAG

## Problem statement

Design a service where teams register jobs (one-off at time T, or recurring by cron), which run on a worker fleet with retries, timeouts, dependencies and observability — with no job run twice or silently dropped.

## Requirements

### Functional

* Create/update/delete jobs: cron schedule or run-once; payload/command.
* Execute on time (within seconds); retries with backoff; timeouts.
* Job dependencies (DAG) and concurrency limits.
* Run history, logs, status API, manual trigger.

### Non-functional

* At-least-once execution with idempotency guidance; no duplicate concurrent runs of the same job.
* Scale: 10M scheduled runs/day; 100k jobs.
* Scheduler highly available (no single point).
* Precise to ~1 s; tolerant of clock skew.

## Back-of-the-envelope estimates

* 10M runs/day ≈ 115/s average; bursts at :00 minutes can be 10k/s (everyone schedules on the hour) → the dispatcher must handle spikes via a queue.
* Job table 100k rows; run history 10M rows/day × 1 KB = 10 GB/day → partition by day, retain 30 days hot.
* Due-job scan: index on `next_run_at`; a poll every second reads the next few thousand rows.

## API

```
POST /v1/jobs   { name, schedule: "0 2 * * *" | { runAt }, command|payload, timeoutSec, retries, maxConcurrency, dependsOn[] }
GET  /v1/jobs/{id}  /  PUT  /  DELETE
POST /v1/jobs/{id}/trigger
GET  /v1/jobs/{id}/runs?status=&limit=
GET  /v1/runs/{runId}/logs
```

## Data model

```
jobs      (job_id, owner, schedule, payload, timeout_sec, max_retries, max_concurrency, next_run_at, enabled)
runs      (run_id, job_id, scheduled_for, started_at, finished_at, status, attempt, worker_id, output_ref)
           UNIQUE (job_id, scheduled_for)     -- prevents duplicate runs of the same tick
deps      (job_id, depends_on_job_id)
locks     (job_id, lease_until, holder)     -- or use the runs table + DB row locks
```

## High-level design

1. **API/Job service** persists jobs and computes `next_run_at` from the cron expression.
2. **Scheduler (dispatcher)**: a small set of replicas; **leader** (via ZooKeeper/etcd lease or DB advisory lock) polls `jobs WHERE next_run_at <= now() AND enabled` every second, and for each: inserts a `runs` row `(job_id, scheduled_for)` (unique constraint = exactly one run per tick), advances `next_run_at`, and publishes the run to a **queue**. Alternatively partition jobs by hash across several active schedulers, each owning a range — removes the single leader bottleneck.
3. **Queue** (Kafka/SQS) buffers spikes; priority topics.
4. **Workers** pull runs, claim with a lease (`started_at`, `worker_id`, heartbeat), execute with the timeout, stream logs to object storage, mark `succeeded`/`failed`. On failure, re-enqueue with backoff up to `max_retries`.
5. **Dependencies**: a run is enqueued only when upstream runs for the same logical date succeeded; a DAG evaluator checks on each completion event.
6. **Watchdog**: reaps runs whose lease expired (worker died) and re-queues them.
7. **UI/observability**: run history, DAG view, alerts on failure/SLA miss.

## Architecture diagram

Rendering diagram…

## Deep dives

**Exactly one run per tick**: the unique `(job_id, scheduled_for)` insert is the guard; two schedulers racing still yield one row.

**Misfires**: if the scheduler was down and ticks were missed, policy per job: run once (coalesce) or run all missed ticks.

**Time zones/DST**: store schedules with an explicit tz; compute next\_run in that tz.

**Idempotency**: at-least-once is inherent (worker may die after doing the work but before marking success); job owners must make jobs idempotent; provide the `run_id` in the payload to help.

**Concurrency limits**: check running count for the job before dispatch; skip or queue.

## Bottlenecks & mitigations

* Top-of-the-hour stampede → queue absorbs; workers autoscale; encourage jitter in schedules.
* Single scheduler leader → partition jobs across schedulers by hash range.
* Runs table growth → partition by day; archive.
* Log volume → stream to object storage, keep only pointers in the DB.

## Failure modes

* **Scheduler leader dies**: lease expires; another replica takes over within seconds; missed ticks handled by misfire policy.
* **Worker dies mid-run**: heartbeat stops; watchdog re-queues after the lease; job runs again (idempotency required).
* **Queue outage**: scheduler keeps creating run rows with `queued` status; a replay job publishes them when the queue returns.
* **Clock skew between schedulers**: use DB time (`now()`) for due checks, not local clocks.
* **Poison job** (always fails): retries exhausted → `dead` status + alert; never blocks other jobs.

## Follow-up questions interviewers ask

* How would you support millions of user-defined reminders (one-off, high volume)?
* How would you implement fair scheduling across tenants?
* How would you do rolling upgrades of workers without killing long runs?

[PreviousReal-time Gaming Leaderboard](/system-design/realtime-leaderboard)[NextEmail Service (Gmail-like)](/system-design/email-service)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonAirbnbAtlassianMicrosoftUberSalesforce

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

## Your notes

Saved

Autosaves to this browser.
