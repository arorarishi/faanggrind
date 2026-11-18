# Database connections exhausted after a deploy — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/db-connection-pool-exhausted

[DevOps problems](/devops#problems)

OPSTroubleshooting#32Medium

# Database connections exhausted after a deploy

postgresqlconnection-poolpgbouncerrdskubernetestroubleshootingReported at Infosys, Wipro, Accenture

## Problem statement

It is 18:05, four minutes after the evening deploy of `orders-api`. The error rate is 38 percent. The API logs show `FATAL: sorry, too many clients already` from PostgreSQL on new connections and `timeout acquiring connection from pool (10000 ms)` on the rest. The RDS console shows `DatabaseConnections` flat at 400, which is the instance's `max_connections`. The deploy changed only two things: the image tag and `replicas: 10` to `replicas: 30` "for the sale tonight". Restore the service, then make sure nobody can deploy a replica count the database cannot serve.

## Requirements

### Functional

* Do the arithmetic: replicas times pool size per replica against `max_connections` minus the reserved and admin slots, before and after the deploy.
* Show in `pg_stat_activity` who holds the 400 connections, by application and by state, and tell a full pool apart from a leak or long transactions.
* Recover within 10 minutes with the least risky action, and say why the other recovery options were not chosen.
* Rule out, with evidence, a connection leak on error paths, idle-in-transaction sessions, and a slow database that makes every query hold its connection longer.
* Design the proper fix: a pool sizing rule, a proxy pool in transaction mode, and a CI check that rejects a replica count the database cannot serve.

### Non-functional

* Time to recovery under 10 minutes from the page; the service has a 99.9 percent monthly target (43 minutes of full outage) and 38 percent errors for 4 minutes has already spent about 1.5 minutes of it.
* Blast radius of the recovery: the `orders-api` Deployment only; no database restart, no parameter change that needs a reboot during the sale.
* After the fix: database connections under 80 percent of `max_connections` at peak, pool wait time p99 under 50 ms, zero `too many clients` errors.
* The sizing rule is checked in CI in under 5 seconds for every environment.
* The 3 superuser slots are never consumed by the application, so the on-call can always connect.

## Back-of-the-envelope estimates

**The arithmetic.** `max_connections` is 400 and `superuser_reserved_connections` is 3, so applications can hold 397. Before the deploy: 10 replicas x 20 connections per pool = 200, half the limit. After: 30 x 20 = 600 wanted, 397 available, so 203 connection attempts fail outright and every pod that got fewer than 20 queues requests on its pool until the 10-second acquire timeout. Two migration jobs and the monitoring agent hold about 17 connections, so the safe budget for the application is 397 minus 17 = 380. The sizing rule: pool size per replica equals floor(380 / replicas); at 30 replicas that is 12, at 10 replicas 38. Each PostgreSQL backend costs a few MB of memory, so 400 connections on a db.r6g.large with 16 GiB is affordable; raising `max_connections` to 800 would need more RAM and a reboot, which is why the proxy is the right place to absorb replica growth. With PgBouncer in transaction mode, 30 x 20 = 600 client connections share a server pool of 40, and the database sees 40.

## API

```
# 1. What the API says: which error, how many, since when.
kubectl logs -n orders deploy/orders-api --since=10m | grep -cE "too many clients|timeout acquiring"
#   4,812
kubectl rollout history deploy/orders-api -n orders | tail -3
#   41  replicas 10 -> 30, image 3.8.0     (18:01)

# 2. Who holds the connections? Use the admin role: the 3 superuser slots are reserved for exactly this.
psql "$ADMIN_DSN" -c "
SELECT application_name, usename, state, count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1, 2, 3 ORDER BY 4 DESC;"
#  orders-api | orders | idle                | 311
#  orders-api | orders | active              |  69
#  migrate    | orders | idle in transaction |   2
#  datadog    | monitor| idle                |  15
# 397 client backends plus your own admin session: the pool is full of idle connections, not stuck ones.

# 3. Is anything holding a connection for a long time? Leaks and long transactions show up here.
psql "$ADMIN_DSN" -c "
SELECT pid, application_name, state, now() - xact_start AS xact_age, now() - state_change AS in_state, left(query, 60)
FROM pg_stat_activity
WHERE backend_type = 'client backend' AND state <> 'idle'
ORDER BY xact_start NULLS LAST LIMIT 10;"
#  active rows: xact_age under 300 ms; the 2 'idle in transaction' are the migration job, 40 min old.

# 4. The limits on the server side.
psql "$ADMIN_DSN" -c "SHOW max_connections; SHOW superuser_reserved_connections; SHOW reserved_connections;"
#  400 | 3 | 0

# 5. The pool size the app uses, from the running config.
kubectl get deploy -n orders orders-api -o jsonpath='{.spec.replicas} {.spec.template.spec.containers[0].env[?(@.name=="DB_POOL_SIZE")].value}{"\n"}'
#  30 20

# 6. Recover: scale down first, it is reversible in one command and needs no database change.
kubectl scale deploy/orders-api -n orders --replicas=15
kubectl rollout status deploy/orders-api -n orders
#  15 x 20 = 300 connections, under the limit; errors stop within a minute.

# 7. Free what should not be held: the two idle-in-transaction migration sessions.
psql "$ADMIN_DSN" -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE application_name = 'migrate' AND state = 'idle in transaction' AND now() - state_change > interval '10 minutes';"

# 8. Verify.
psql "$ADMIN_DSN" -c "SELECT count(*) FROM pg_stat_activity WHERE backend_type = 'client backend';"
#  316   (300 orders-api, 15 datadog, your own session; the 2 migrate sessions are gone)
```

## Data model

```
PostgreSQL settings (SHOW name; need a restart to change max_connections)
  max_connections                 400   hard limit on concurrent backends; RDS default is memory-based
  superuser_reserved_connections  3     last slots, superusers only
  reserved_connections            0     slots for the pg_use_reserved_connections role
  idle_in_transaction_session_timeout   0 = off; kills sessions idle inside a transaction
  idle_session_timeout                  0 = off; kills idle sessions outside a transaction
  statement_timeout                     0 = off

pg_stat_activity columns that decide it
  backend_type        'client backend' vs autovacuum, walsender, etc.
  application_name    set by the client DSN: application_name=orders-api
  usename, datname, client_addr
  state               active | idle | idle in transaction | idle in transaction (aborted)
  xact_start, query_start, state_change, wait_event_type, wait_event, query

Errors
  SQLSTATE 53300 too_many_connections   "sorry, too many clients already"
                                        "remaining connection slots are reserved for roles with the SUPERUSER attribute"
  app side: pool acquire timeout, the pool is full of connections the DB accepted

Application pool (per replica)
  DB_POOL_SIZE 20   max connections per process
  min idle, max lifetime, acquire timeout 10 s, idle timeout
  total = replicas x DB_POOL_SIZE x processes per pod

Proxy pool (PgBouncer or RDS Proxy)
  pool_mode transaction          server connection returned after each transaction
  default_pool_size 40           server connections per user/database pair
  max_client_conn 2000           client sockets accepted
  server_idle_timeout 600 s
  RDS Proxy: MaxConnectionsPercent, pinning on session state (SET, prepared statements)

Metrics and alerts
  pg_stat_activity count by application_name, pushed by postgres_exporter
  RDS CloudWatch DatabaseConnections; alert at 80 percent of max_connections
  pool wait time and pool exhausted counters from the app
```

## Diagnosis and fix

1. **Scope.** The errors began at 18:01 with the rollout and `DatabaseConnections` is pinned at the limit; other services on the same instance also cannot connect, which raises the urgency. Say so in the channel and take the deploy lock.
2. **Do the arithmetic first.** 30 replicas x 20 pool size = 600 against 397 usable (commands 5 and 4). That alone explains the symptom. The log counts (command 1) show both error types: pods that could not connect, and pods whose pool is full and queueing.
3. **Confirm in pg\_stat\_activity.** 397 client backends, 380 of them `orders-api`, 311 of those `idle` (command 2). A leak would show `idle` rows with old `state_change` growing over hours at flat load; long transactions would show old `xact_start`. Active queries are under 300 ms (command 3). The pool is simply oversubscribed. The two `idle in transaction` migration sessions are wasteful but not the cause.
4. **Recover with the safest action.** Scale to 15 replicas (command 6): 300 connections, errors stop in a minute, reversible. Not chosen: raising `max_connections`, which needs a reboot and more memory during a sale; killing application connections, which the pools reopen instantly; a rollback, which drops an image that was not the cause. Terminate the two 40-minute idle-in-transaction sessions (command 7) because they hold locks.
5. **Root cause, one sentence.** The deploy tripled the replica count while every replica kept a 20-connection pool, so the application asked for 600 connections from a database that allows 397.
6. **Fix properly.** Put PgBouncer (or RDS Proxy) between the app and the database in transaction mode: the pods keep their pools, the proxy keeps 40 server connections, and the database sees 40 plus admin. Set `application_name` in every DSN so `pg_stat_activity` names the caller. Set `idle_in_transaction_session_timeout = 5min` on the application role so a stuck migration cannot hold a slot for an hour. Write the sizing rule into the Helm chart: `poolSize = floor(budget / replicas)` with `budget` a value per environment, and fail the render when `replicas x poolSize > budget`.
7. **Verify.** Connections at peak under 320 (80 percent of 400); pool wait p99 under 50 ms; zero `53300` errors for 24 hours; the HPA on `orders-api` can scale to 30 with the database holding at 40 server connections.
8. **Prevent.** A CI job renders every environment and computes `replicas x poolSize` (and `maxReplicas x poolSize` where an HPA exists) against the database budget; it fails the PR with the numbers. Alerts: `DatabaseConnections` over 80 percent of `max_connections` for 5 minutes, any session `idle in transaction` for more than 5 minutes, and pool wait p99 over 100 ms.

## Architecture diagram

Rendering diagram…

## Deep dives

### The arithmetic, and where the pool should live

Every application process keeps its own pool, and PostgreSQL spends one backend process per connection, so the database sees the sum of all pools whether the connections are busy or idle. The sizing rule is `replicas x processes per pod x pool size <= max_connections - superuser_reserved_connections - reserved_connections - admin and job headroom`. The trap is that the two sides are owned by different teams and changed in different files: the replica count in a Helm values file, the pool size in an environment variable, the limit in an RDS parameter group. Scaling is the normal thing to do before a sale, and nothing in the deploy path knew the sum. A proxy pool moves the sum to one place: PgBouncer in transaction mode hands a server connection to a client only for the length of a transaction, so 600 client connections that are mostly idle share 40 server connections. The cost is that session state does not survive between transactions: `SET` settings, advisory locks, `LISTEN`, and SQL-level `PREPARE` break unless the proxy tracks them, and RDS Proxy "pins" such a session to one connection, which brings back the original problem for that client. The rule is: transaction mode for stateless request handlers, session mode or a direct connection for migrations and anything that needs session state.

### Full pool, leak, or long transactions

Three causes produce the same `too many clients` error and need three different fixes, and `pg_stat_activity` tells them apart in one query. An oversubscribed pool shows connections grouped by `application_name` whose count equals `replicas x pool size`, mostly `idle`, appearing at the moment of a deploy or a scale-up. A leak shows a count that grows over hours at constant load, connections `idle` with an old `state_change`, usually from an error path that returns early without releasing the connection; the fix is in code (`defer rows.Close()`, context managers, `finally`), with a pool `max lifetime` as a safety net. Long transactions show `idle in transaction` rows with an old `xact_start`, often an ORM that opened a transaction and then called an external API, or a migration waiting on a lock; `idle_in_transaction_session_timeout` on the application role kills these, and `statement_timeout` bounds the active ones. A slow database is the fourth shape: all rows `active`, `wait_event_type` set, queries older than usual, and the pool fills because each query holds its connection longer; the fix is the query or the index, not the pool.

### Recovering now without making it worse

The order of recovery actions is by reversibility and blast radius. Scaling the Deployment down is one command, takes a minute, and can be undone; it costs capacity you might need, so pick the largest replica count that fits. `pg_terminate_backend` on idle sessions frees slots immediately, but application pools reconnect within seconds, so it only helps for sessions that will not come back: stuck jobs, idle admin shells, or a crashed pod's leftovers. Raising `max_connections` requires a restart on PostgreSQL, which on RDS is a reboot with a failover if Multi-AZ, and each backend costs memory, so it is the last option and only when the instance has headroom. Using the 3 superuser slots is what they are for: the on-call must be able to run `pg_stat_activity` during the incident, so the application role must never be a superuser.

### The CI check that would have caught it

The check is small: render the Helm chart for the target environment, read `replicas` (and the HPA's `maxReplicas` if present), read the pool size from the environment, multiply, and compare with a per-environment budget that the database owner maintains next to the parameter group. Print the equation in the failure message: `30 replicas x 20 pool = 600 > budget 380 (max_connections 400 - 3 reserved - 17 headroom)`. It runs in seconds and it turns the incident into a failed PR. Once the proxy is in place the budget moves to PgBouncer's `max_client_conn` and `default_pool_size`, and the same check compares against those.

## Evaluation

**Did you find it?** The write-up says: "The deploy raised replicas from 10 to 30 with a 20-connection pool per replica: 600 connections requested against 397 usable. `pg_stat_activity` shows 380 `orders-api` backends, 311 idle, active queries under 300 ms; no leak, no long transactions, no slow queries." The two idle-in-transaction migration sessions are named as a separate, smaller problem.

**Is it fixed?** After scaling to 15: `53300` errors stop within a minute, `DatabaseConnections` at about 316, error rate back to baseline. After the proxy: the database holds about 40 server connections while 30 replicas run, pool wait p99 under 50 ms, 24 hours with no connection errors.

**Is it prevented?** The chart computes the pool size from a per-environment budget and fails to render when the product exceeds it; CI prints the equation; alerts at 80 percent of `max_connections`, on idle-in-transaction sessions over 5 minutes, and on pool wait time; `application_name` is set everywhere so the next incident is attributable in one query.

**What a strong answer adds.** The exact rule with reserved slots and headroom; transaction versus session pooling and what breaks in transaction mode; the three shapes in `pg_stat_activity`; why terminating application connections does not help; why `max_connections` is the last option on RDS; and the point that the HPA's `maxReplicas` is part of the arithmetic.

**What a weak answer does.** Raises `max_connections` to 1,000, restarts the database during the sale, or rolls back the image without noticing that the replica count was the change.

## Bottlenecks & mitigations

* One backend process per connection: PostgreSQL's limit is memory and process count, so the budget is small and fixed between reboots.
* Pool size and replica count live in different files owned by different people, and nothing computes their product.
* Shared instance: three services share the 400 slots, so one team's scale-up takes another team down.
* Migrations with session state cannot go through transaction pooling, so there are always two paths to the database.
* `max_connections` on RDS changes only with a reboot, and Multi-AZ reboots fail over.

## Failure modes

* **Replica change without a pool change.** The product exceeds the limit on the next scale-up. Mitigation: pool size derived from a budget in the chart, CI check on the product including `maxReplicas`.
* **Connection leak on error paths.** Connections never return to the pool and the count grows at constant load. Mitigation: release in `finally` or `defer`, pool `max lifetime`, an alert on connection count growth at flat traffic.
* **Idle in transaction.** A job opens a transaction and waits on an external call or a lock for an hour. Mitigation: `idle_in_transaction_session_timeout` on the application role, migrations outside transaction pooling.
* **Application role is a superuser.** The app eats the reserved slots and the on-call cannot connect. Mitigation: a non-superuser application role; the 3 reserved slots stay free.
* **Transaction pooling with session state.** `SET`, advisory locks or prepared statements behave differently or pin the session. Mitigation: session mode or direct connections for those clients, `max_prepared_statements` configured.
* **Raising max\_connections in the incident.** A reboot in peak traffic, and more memory per backend than the instance has. Mitigation: scale the client side first; change the limit in a maintenance window with a sizing note.
* **No application\_name.** Every connection looks the same in `pg_stat_activity`. Mitigation: `application_name` in every DSN, checked by a test.
* **Alert only on errors.** The first signal is the outage. Mitigation: alert at 80 percent of `max_connections` and on pool wait time.

## Follow-up questions interviewers ask

* The count grows by 30 connections an hour at flat traffic. Walk through finding the leak in a Go service and the pool setting that limits the damage.
* Why does PgBouncer in transaction mode break `SET search_path` and SQL-level `PREPARE`, and what do you do for a service that needs them?
* RDS Proxy pins a session. What triggers pinning, how do you see it in the metrics, and how is it different from PgBouncer?
* The database is shared by three services. How do you divide the budget and enforce it per service?
* Write the CI check as a 25-line script: inputs, the equation it prints, and how it handles an HPA.
* A migration needs an exclusive lock and sits `idle in transaction` behind a long read. What does `lock_timeout` change and how do you order the two?

## Lessons that cover this

* [#22Troubleshooting playbook - Linux, Docker, Kubernetes, network, pipelinesOperate](/devops/learn/troubleshooting-playbook)
* [#24Scaling and resilience - caching, queues, rate limiting, DDoS, DROperate](/devops/learn/scaling-and-resilience)

## Further reading

* [PostgreSQL documentation: the cumulative statistics system (pg\_stat\_activity)Guidepostgresql.org](https://www.postgresql.org/docs/current/monitoring-stats.html)
* [PostgreSQL documentation: connections and authentication (max\_connections)Guidepostgresql.org](https://www.postgresql.org/docs/current/runtime-config-connection.html)
* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousOOMKilled pods and an HPA that keeps scaling up and down](/devops/problems/oomkilled-hpa-thrashing)[NextBash: analyse an Nginx access log](/devops/problems/bash-log-analyzer)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [Diagnosis and fix](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Evaluation](#evaluation)
10. [Bottlenecks](#bottlenecks)
11. [Failure modes](#failures)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
