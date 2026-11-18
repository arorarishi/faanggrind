# Zero-downtime database schema migration and cutover — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/zero-downtime-db-migration

[DevOps problems](/devops#problems)

DESIGNPlatform design#16Hard

# Zero-downtime database schema migration and cutover

postgresqlauroraschema-migrationexpand-contractci-cdfeature-flags

## Problem statement

The `orders` table in Aurora PostgreSQL has 800 million rows and takes 2,000 writes per second around the clock. Three changes are needed: a new `NOT NULL` column `fulfilment_region` whose value is computed from the existing `shipping_country` column, the column `cust_ref` renamed to `customer_id`, and a new index on `(customer_id, created_at)`. The order service deploys twice a day with rolling updates and rollbacks, from a GitHub Actions pipeline into EKS. Design the migration so that no request fails, no lock stalls traffic, and any deploy during the migration can be rolled back.

## Requirements

### Functional

* Add `fulfilment_region` as `NOT NULL` with the computed value present for all 800 million rows.
* Rename `cust_ref` to `customer_id` without any deploy that reads a column the database does not have.
* Build the index on `(customer_id, created_at)` while writes continue.
* Migrations run from the pipeline as versioned files, and every deploy is compatible with the schema one step behind and one step ahead.
* A dry run on a clone of production proves timing and lock behaviour before the real run.
* Verification before anything is dropped: counts, samples and a checksum.

### Non-functional

* No write or read fails during the migration; p99 write latency stays under 50 ms (today 20 ms).
* No DDL statement waits for or holds a lock on `orders` for more than 2 seconds.
* Backfill adds no more than 5 times the normal WAL rate and replica lag stays under 1 second.
* The whole programme finishes within 2 weeks of calendar time across the normal twice-daily deploys.
* Any deploy can be rolled back within 5 minutes at any step without a database change.
* Extra storage during the migration under 200 GB (new index plus bloat before vacuum).

## Back-of-the-envelope estimates

**Backfill.** 800,000,000 rows in batches of 10,000 = 80,000 batches. One batch is an `UPDATE ... WHERE id BETWEEN` on an indexed range, assumed 250 ms, followed by a 750 ms sleep: one batch per second, 10,000 rows per second, so 80,000 seconds, about 22 hours. That is 5 times the normal 2,000 writes per second, which is the budget in the requirements. Shrinking the sleep to 250 ms halves the time but doubles the extra load.

**Write amplification.** Each updated row writes a new tuple version plus WAL: an assumed 300 bytes of WAL per row, 800 million x 300 = 240 GB of WAL over 22 hours, 10.8 GB per hour against a normal 2,000 x 300 x 3,600 = 2.16 GB per hour, again 5 times. The old tuple versions are dead until vacuum: an assumed 150 bytes per row x 800 million = 120 GB of bloat if autovacuum cannot keep up, so the backfill runs with autovacuum tuned up on this table and is paused if dead tuples pass 100 million.

**Index.** A B-tree entry for a bigint plus a timestamp with overhead is about 40 bytes: 800 million x 40 = 32 GB. `CREATE INDEX CONCURRENTLY` scans the 120 GB table (800 million x 150 bytes) twice; at an assumed 100 MB per second each scan takes 20 minutes, so about 40 minutes plus the sort, under 2 hours in practice on Aurora, with normal writes continuing.

**Replica lag.** Aurora replicas share the storage volume, so lag is page-cache lag, usually under 100 ms; a 5x WAL rate is tolerated but the `ReplicaLag` metric is the throttle input: above 500 ms the backfill doubles its sleep.

**Verification.** A 1-in-1,000 sample is 800,000 rows, checked against a recomputed value in a read-only query taking minutes, plus `count(*) WHERE fulfilment_region IS NULL`, which must be zero before the constraint is validated.

## API

```
Migration files (repo order-service/db/migrations, run by a Kubernetes Job before the rollout)
  0041_add_fulfilment_region.sql            ADD COLUMN fulfilment_region text NULL      (deploy 1)
  0042_add_customer_id.sql                  ADD COLUMN customer_id bigint NULL           (deploy 1)
  0043_backfill.sql                         marked "long-running": executed by the backfill Job, not the pre-deploy Job
  0044_check_not_null_not_valid.sql         ADD CONSTRAINT ... CHECK (fulfilment_region IS NOT NULL) NOT VALID
  0045_validate.sql                         VALIDATE CONSTRAINT, then SET NOT NULL, DROP the check   (deploy 3)
  0046_index_concurrently.sql               CREATE INDEX CONCURRENTLY, outside a transaction (deploy 3)
  0047_drop_cust_ref.sql                    DROP COLUMN cust_ref                        (deploy 5, after verification)

Every migration session starts with:
  SET lock_timeout = '2s';
  SET statement_timeout = '10s';     -- except backfill batches (30s) and CONCURRENTLY builds (0)

Pre-deploy Job (GitHub Actions -> kubectl apply of a Job, waits for completion)
  image: order-service:<digest> ; command: migrate up --to <version from this release>
  fails the deploy if a migration errors; a lock_timeout error retries 5 times with backoff

Backfill Job (separate, resumable, one replica)
  state table: migration_progress(name, last_id, updated_at)
  loop: UPDATE orders SET fulfilment_region = region_for(shipping_country),
                          customer_id = cust_ref
        WHERE id > $last_id AND id <= $last_id + 10000
          AND (fulfilment_region IS NULL OR customer_id IS NULL);
        sleep 750 ms; if ReplicaLag > 500 ms or p99 write latency > 40 ms: sleep x2

Application flags (ConfigMap, read every 30 s)
  write_new_columns   true from deploy 2:  INSERT and UPDATE write both old and new columns
  read_new_columns    true from deploy 4:  reads use fulfilment_region and customer_id
  write_old_columns   false from deploy 5: stop writing cust_ref

Rollback rule: a release may only be rolled back to the previous release, and the schema
at every step is compatible with both. A migration file never contains a step that the
previous release cannot run against.
```

## Data model

```
orders (Aurora PostgreSQL, 800 M rows, about 120 GB, 2,000 writes per second)
  before   id bigint PK, cust_ref bigint, shipping_country char(2), created_at timestamptz, ...
  during   + fulfilment_region text NULL, + customer_id bigint NULL
           + CHECK (fulfilment_region IS NOT NULL) NOT VALID      (then validated)
           + trigger orders_sync_cols BEFORE INSERT OR UPDATE: copies cust_ref <-> customer_id
             (safety net for any writer that is not the service, removed at deploy 5)
  after    id, customer_id bigint NOT NULL, shipping_country, fulfilment_region text NOT NULL,
           created_at, index orders_customer_id_created_at_idx (customer_id, created_at)

Deploy timeline (two deploys a day)
  deploy 1  schema: add both nullable columns              code: unchanged
  deploy 2  schema: none                                    code: write both old and new columns
  backfill  22 hours, resumable, throttled on ReplicaLag and p99
  deploy 3  schema: NOT VALID check, validate, SET NOT NULL, index CONCURRENTLY   code: unchanged
  deploy 4  schema: none                                    code: read new columns (flag)
  verify    counts, 800,000-row sample, checksum old vs new column, 2 days of soak
  deploy 5  schema: drop trigger, drop cust_ref             code: stop writing old column

Lock classes that matter (from the PostgreSQL docs)
  ACCESS EXCLUSIVE        most ALTER TABLE forms, DROP COLUMN, RENAME: blocks even SELECT
  SHARE                   CREATE INDEX without CONCURRENTLY: blocks INSERT, UPDATE, DELETE
  SHARE UPDATE EXCLUSIVE  CREATE INDEX CONCURRENTLY, VALIDATE CONSTRAINT: does not block writes
  ROW EXCLUSIVE           normal INSERT, UPDATE, DELETE

Monitoring during the migration
  pg_stat_activity (wait_event_type = Lock), pg_locks, pg_stat_progress_create_index
  CloudWatch: ReplicaLag, WriteLatency, FreeableMemory, VolumeBytesUsed
  Service: p99 write latency, error rate, rows per second from the backfill Job
```

## High-level design

**Expand**

1. Deploy 1 runs `ALTER TABLE orders ADD COLUMN fulfilment_region text, ADD COLUMN customer_id bigint` with no default. Adding a nullable column without a volatile default only touches the catalogue, so the `ACCESS EXCLUSIVE` lock is held for milliseconds. `lock_timeout = '2s'` makes the statement give up rather than queue behind a long transaction and block every query behind it. The pipeline retries.
2. Deploy 2 ships code that writes both old and new columns on every insert and update, behind the `write_new_columns` flag, plus a trigger that copies `cust_ref` into `customer_id` for any writer the team forgot (reports, scripts). The old code path still works, so rolling back deploy 2 is safe.

**Backfill**

3. A separate resumable Job walks the primary key in batches of 10,000, computes `fulfilment_region` from `shipping_country` and copies `cust_ref` into `customer_id`, records `last_id` after each batch, sleeps 750 ms, and doubles the sleep when `ReplicaLag` or p99 write latency crosses its threshold. It runs for about 22 hours and can be stopped and restarted at any point.

**Constrain and index**

4. Deploy 3 adds `CHECK (fulfilment_region IS NOT NULL) NOT VALID`, which skips the table scan, then `VALIDATE CONSTRAINT`, which scans under `SHARE UPDATE EXCLUSIVE` and does not block writes. With a valid check in place, `SET NOT NULL` skips its own full scan. Then `CREATE INDEX CONCURRENTLY orders_customer_id_created_at_idx ON orders (customer_id, created_at)` outside a transaction with `statement_timeout = 0`.

**Switch reads**

5. Deploy 4 flips `read_new_columns`; the query planner now uses the new index. Watch p99 for two deploys. The flag can flip back without a deploy.

**Verify, then contract**

6. Run the verification: `count(*) WHERE fulfilment_region IS NULL` is 0, `count(*) WHERE customer_id IS DISTINCT FROM cust_ref` is 0, a 1-in-1,000 sample recomputes the region in SQL and matches, and a daily checksum of `(id, customer_id)` matches `(id, cust_ref)`. Soak for 2 days.
7. Deploy 5 ships code that no longer writes `cust_ref`, drops the trigger and runs `ALTER TABLE orders DROP COLUMN cust_ref`, which is a catalogue change that does not rewrite the table. The space is reclaimed slowly by vacuum.

**Across the whole programme**

8. Every migration file is numbered and idempotent; a pre-deploy Job runs the files up to the release's version; the backfill is marked long-running and excluded from that Job. The same files run first against a clone of production restored from a snapshot, with timing recorded, and a dashboard of locks, lag and latency stays open during each step.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why "rename column" is a multi-deploy operation

`ALTER TABLE orders RENAME COLUMN cust_ref TO customer_id` is instant and takes an `ACCESS EXCLUSIVE` lock for a moment; the problem is not the lock, it is the code. During a rolling update, old pods and new pods run at the same time for minutes, and after a rollback the old code runs again for hours. Whatever the column is called at any instant, one of those versions is selecting or inserting a name that does not exist, and every such request fails. So the rename is rebuilt as add, dual-write, backfill, switch reads, stop writing, drop: five deploys where each release works with the schema before it and after it. A view named `orders` exposing both names is an alternative when the writers are many and unknown, but views complicate inserts and the planner, so this design uses dual columns plus a trigger as the safety net for writers outside the service.

### Locks in PostgreSQL DDL and what blocks what

The table-level lock rules from the docs decide everything here. `ACCESS EXCLUSIVE` conflicts with every other mode, including `ACCESS SHARE`, which plain `SELECT` takes, so an `ALTER TABLE` that waits for a lock is worse than one that holds it: while it waits behind one long transaction, every new query on `orders` queues behind the `ALTER`, and the site appears down. `lock_timeout = '2s'` turns that into a quick failure the pipeline retries. The commands that touch data without stopping writes are the ones that take `SHARE UPDATE EXCLUSIVE`: `CREATE INDEX CONCURRENTLY`, `VALIDATE CONSTRAINT`, `VACUUM`, `ANALYZE`; it does not conflict with `ROW EXCLUSIVE`, the lock of `INSERT`, `UPDATE` and `DELETE`. A plain `CREATE INDEX` takes `SHARE`, which does conflict with `ROW EXCLUSIVE`, so writes stop for the whole build. Adding a column with a non-volatile default stores the default in the catalogue and does not rewrite the table, but a volatile default (a function like `clock_timestamp()`) rewrites all 800 million rows under `ACCESS EXCLUSIVE`, which is why the computed value here is written by the backfill, not by a default. `DROP COLUMN` is a catalogue change that hides the column; space comes back only through a later rewrite or vacuum.

### CREATE INDEX CONCURRENTLY and its failure modes

The concurrent build does two scans of the table and, before each, waits for every transaction that could modify the table to finish, then waits again for transactions whose snapshots predate the second scan. A long-running report or an idle-in-transaction session therefore makes the build hang, which is why `idle_in_transaction_session_timeout` is set on the application role. It cannot run inside a transaction block, so the migration tool must run that file in autocommit mode, and `statement_timeout` must be 0 for that session or the 40-minute build is killed. If it fails (deadlock, a cancelled session, a uniqueness violation on a unique build), it leaves an `INVALID` index that queries ignore but writes still maintain; the fix is `DROP INDEX` and run again, or `REINDEX INDEX CONCURRENTLY`. The runbook checks `pg_index.indisvalid` after the build and `pg_stat_progress_create_index` during it.

### Backfill throttling and lag

A backfill that updates 800 million rows as fast as it can doubles or triples the WAL rate, fills the replicas' page caches with changes, bloats the table with dead tuples and competes for I/O with the 2,000 writes per second that pay the bills. Batches keep each transaction short so locks on rows are held for milliseconds and vacuum can clean behind. The sleep between batches sets the rate; the control loop adjusts it from two signals: Aurora `ReplicaLag` and the service's own p99 write latency. The job records progress in a table so a pod restart resumes rather than restarts, and the `WHERE ... IS NULL` guard makes a repeated batch harmless. The dry run on a snapshot clone gives the real batch time and the real WAL rate before anyone touches production.

### Verifying before dropping anything

The contract step is the only irreversible one, so it is gated on evidence, not confidence: a zero count of nulls in the new column, a zero count of rows where the new and old columns differ, an 800,000-row random sample recomputed in SQL, a daily checksum over `(id, customer_id)` against `(id, cust_ref)`, and two days with reads on the new column while the old one is still written. Only then does deploy 5 stop writing the old column and drop it. If the checksum ever differs, the read flag goes back, the backfill reruns on the affected id range, and nothing has been lost because the old column is still being written.

## Evaluation

**SLIs during the migration.** Error rate of the order service (target 0 migration-caused errors); p99 write latency (under 50 ms); longest lock wait on `orders` from `pg_stat_activity` (under 2 seconds); `ReplicaLag` (under 1 second); backfill rows per second and estimated time remaining; dead tuples on `orders` from `pg_stat_user_tables`.

**Tests before production.** The full sequence on a clone restored from a snapshot with a replayed write load of 2,000 per second: measure each DDL's lock hold time, the backfill rate, the index build time and the disk growth. Deliberately open an idle transaction and confirm the `ALTER` fails after 2 seconds instead of stalling traffic. Roll back each deploy in the sequence and confirm the previous release passes its integration tests against the current schema.

**Rollback drills.** During the real run, roll back deploy 2 and deploy 4 on purpose in staging to prove the compatibility rule holds.

**Data checks.** The four verification queries, automated as a Job whose output is attached to the deploy 5 pull request.

**What a strong answer adds.** The candidate names the lock modes and which ones block writes, says why the default cannot be used for the computed value, knows `CONCURRENTLY` cannot run in a transaction and can leave an invalid index, has a throttle with a measured signal, and refuses to drop the column without the checksum. A weak answer runs one `ALTER TABLE` with `NOT NULL DEFAULT` at 3 am and hopes.

## Bottlenecks & mitigations

* The backfill's write rate is bounded by the WAL and replica lag budget, not by CPU: 22 hours is the cost of 5x normal load; faster means more lag.
* Autovacuum on `orders` must keep up with 800 million dead tuples or the table doubles in size; raise `autovacuum_vacuum_cost_limit` for this table during the backfill.
* Long transactions from reporting queries block both the `ALTER` lock and the `CONCURRENTLY` build's waits; move reports to a reader instance.
* The pre-deploy migration Job is on the deploy's critical path; a retrying `lock_timeout` adds minutes to every release during the programme.
* Twice-daily deploys set the pace: five schema-related deploys plus soak time is why the programme takes two weeks, not two hours.

## Failure modes

* **ALTER queues behind a long transaction.** Every query on `orders` waits behind it; the site stalls. Mitigation: `lock_timeout = '2s'`, retry with backoff, `idle_in_transaction_session_timeout` on application roles.
* **NOT NULL DEFAULT with a volatile function.** Full table rewrite under `ACCESS EXCLUSIVE` for an hour. Mitigation: nullable column plus backfill plus validated constraint.
* **Rollback to code that does not know the new column.** Inserts set `fulfilment_region` to null and the constraint fails. Mitigation: the constraint is added only after two deploys have been writing the column; the compatibility rule is enforced by running the previous release's tests against the new schema in CI.
* **CONCURRENTLY build left an invalid index.** Queries still slow, writes pay for maintenance. Mitigation: check `indisvalid` in the migration, drop and rerun.
* **Backfill restarted from zero after a pod eviction.** 22 hours lost. Mitigation: progress table, `IS NULL` guard, a PodDisruptionBudget and `karpenter.sh/do-not-disrupt` on the Job pod.
* **A writer outside the service keeps writing only cust\_ref.** New column diverges. Mitigation: the sync trigger during the dual-write period, and the diff count in verification.
* **Replica lag grows past 1 second during the backfill.** Reads on replicas return stale orders. Mitigation: the throttle loop doubles the sleep and pauses above 2 seconds.
* **Disk fills with WAL and dead tuples.** Aurora storage grows, bloat slows every query. Mitigation: vacuum tuned per table, backfill paused when dead tuples pass 100 million, storage alarm.

## Follow-up questions interviewers ask

* The column type must change from `int` to `bigint` on the same table. Which steps change, and why is this harder than a rename?
* The table is partitioned by month. How does the backfill and the index build change?
* How do you make the pipeline refuse a migration file that contains an unsafe statement, such as `ADD COLUMN ... NOT NULL DEFAULT now()`?
* A foreign key must be added from `orders` to a new `customers` table. Which lock does it take and how do you add it without blocking?
* How would you run this with MySQL on RDS, where online DDL and tools like gh-ost or pt-online-schema-change exist?
* The team wants the whole thing done in one night with a 30-minute maintenance window. What would you say?

## Lessons that cover this

* [#10Deployment strategies and release engineeringBuild and ship](/devops/learn/deployment-strategies-release-engineering)

## Further reading

* [PostgreSQL documentation: ALTER TABLEGuidepostgresql.org](https://www.postgresql.org/docs/current/sql-altertable.html)
* [PostgreSQL documentation: explicit locking (table-level lock modes)Guidepostgresql.org](https://www.postgresql.org/docs/current/explicit-locking.html)
* [PostgreSQL documentation: CREATE INDEX (building indexes concurrently)Guidepostgresql.org](https://www.postgresql.org/docs/current/sql-createindex.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousBackup and restore for stateful workloads on Kubernetes](/devops/problems/stateful-backup-restore)[NextCut the AWS bill by 40 percent](/devops/problems/cloud-cost-reduction)

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
