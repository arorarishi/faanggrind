# CI pipeline became slow and flaky — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/slow-flaky-ci-pipeline

[DevOps problems](/devops#problems)

OPSTroubleshooting#28Medium

# CI pipeline became slow and flaky

ci-cdgithub-actionscachingflaky-testsdockertroubleshootingReported at Infosys, Capgemini

## Problem statement

It is Monday 09:30. The backend team lead writes: "The `ci.yml` workflow on `main` took 12 minutes in August and now takes 35. About 1 in 5 runs fails on `test_order_refund` and passes on re-run, so people re-run until green." `gh run list --workflow ci.yml --limit 20 --json conclusion,startedAt,updatedAt` shows 4 failures out of 20 and durations between 31 and 38 minutes. Nobody changed the workflow file in two months. Find what made it slow, what makes it flaky, fix both through the normal review path, and make sure the next regression is noticed in a day, not two months.

## Requirements

### Functional

* Break the 35 minutes into queue time and per-job wall time from the workflow run data, and name the jobs that grew.
* Show with evidence whether the dependency cache is hit or missed on every run, and why.
* Find why `test_order_refund` fails 1 in 5 times and separate "flaky test" from "flaky infrastructure".
* Rule out, with a number each, the other candidates: runner contention, a slow package mirror, Docker layer cache, superseded runs not being cancelled.
* Bring the pipeline back under 15 minutes and the failure rate under 1 percent, through reviewed changes to the workflow.
* Add a measurement that alerts when the p50 duration regresses by more than 20 percent week over week.

### Non-functional

* Diagnosis from existing run data within 1 hour, without re-running the pipeline 20 times to "see what happens".
* Target: p50 under 15 minutes on `main`, failure rate under 1 percent, cache hit rate over 90 percent.
* No change to production or to the test database schema used by other teams during the fix; blast radius is the CI workflow of one repository.
* Flaky tests are quarantined for at most 14 days with a named owner, never deleted silently.
* The cost of the fix is visible: runner minutes per day before and after, from the same run data.

## Back-of-the-envelope estimates

**Impact.** 14 engineers push about 40 runs a day on this repository. At 35 minutes a run that is 40 x 35 = 1,400 runner minutes a day; at 12 minutes it was 480. The extra 920 minutes a day on a 4-vCPU hosted runner is a cost line, but the bigger loss is wait: a 20 percent failure rate means 8 runs a day are re-run, and each re-run is another 35 minutes before merge, so the median change waits about 35 x 1.2 = 42 minutes for CI instead of 12. Over a 22-day month that is 8 x 35 x 22 = 6,160 wasted runner minutes from retries alone, and roughly 14 x 30 = 420 engineer minutes a day spent waiting or re-running.

## API

```
# 1. Duration and queue time per run, from the run data, not from memory.
#    startedAt minus createdAt is queue time; updatedAt minus startedAt is wall time.
gh run list --workflow ci.yml --branch main --limit 50 \
  --json databaseId,conclusion,createdAt,startedAt,updatedAt \
  --jq '.[] | [.databaseId, .conclusion,
        ((.startedAt|fromdate) - (.createdAt|fromdate)),
        ((.updatedAt|fromdate) - (.startedAt|fromdate))] | @tsv'
# 1234567  success  31   2102      <- queue 31 s, wall 35 min: the queue is not the problem

# 2. Per-job and per-step durations for one slow run and one fast run from August.
gh run view 1234567 --json jobs \
  --jq '.jobs[] | {name, started_at: .startedAt, completed_at: .completedAt,
        steps: [.steps[] | {name, startedAt, completedAt}]}'
# job "build": step "Install dependencies" 9 min 40 s (August run: 25 s)
# job "test":  step "Run integration tests" 14 min (August: 7 min)

# 3. Did the cache hit? Look at the actions/cache output and the key it computed.
gh run view 1234567 --log | grep -E "Cache (restored|not found|saved)|Cache Size|cache-hit"
#   Cache restored from key: npm-       <- the hash part of the key is empty: a stale entry from 1 September
#   (no "Cache saved" line: an exact hit never saves a new entry)

# 4. What caches exist, and what keys do they have?
gh cache list --limit 20 --json key,sizeInBytes,lastAccessedAt,ref --sort last_accessed_at
#   npm-  0.9 GB  refs/heads/main  ...   one entry, created on 1 September, restored on every run since

# 5. What changed in the repo around the date the duration jumped?
git log --since=2026-08-25 --until=2026-09-10 --name-status --oneline -- package-lock.json \
  '**/package-lock.json' .github/workflows/ci.yml
#   M  .github/workflows/ci.yml   (no change)
#   R100  package-lock.json -> services/api/package-lock.json   "chore: move api into services/"

# 6. The flaky test: how often, and does it fail alone or only with others?
gh run list --workflow ci.yml --branch main --limit 100 --json conclusion --jq \
  'map(.conclusion) | group_by(.) | map({(.[0]): length}) | add'
# {"failure": 19, "success": 81}
gh run view 1234568 --log-failed | grep -B2 -A6 "test_order_refund"
#   AssertionError: expected refund status 'issued', got 'pending'   order_id=1001
#   (the test next to it in the log, test_order_cancel, also uses order_id=1001)
```

## Data model

```
Run and job fields (gh run list / gh run view --json, REST workflow runs and jobs)
  run.createdAt, run.startedAt, run.updatedAt   queue time = startedAt - createdAt
  run.conclusion                                 success | failure | cancelled
  run.attempt                                    > 1 means somebody re-ran it
  job.startedAt, job.completedAt, job.runner_name, job.labels
  job.steps[].name, startedAt, completedAt       the step that grew is the evidence

Cache (actions/cache, actions/setup-node)
  with.key          npm-${{ hashFiles('package-lock.json') }}
                    hashFiles returns "" when no file matches  -> key "npm-"
  with.restore-keys npm-                      prefix match, newest cache wins
  outputs.cache-hit "true" only on an exact key match; "" on a miss
  with.cache-dependency-path (setup-node)    services/api/package-lock.json
  repo cache limit 10 GB by default; entries unused for 7 days are evicted

Workflow fields that decide the other candidates
  concurrency.group, concurrency.cancel-in-progress   superseded runs
  strategy.matrix, strategy.max-parallel               test parallelism
  jobs.<id>.runs-on                                    hosted vs self-hosted labels
  docker/build-push-action with.cache-from, with.cache-to   type=registry,mode=max
  .npmrc registry=                                     which mirror is used

Test evidence
  the failing assertion, the fixture ids it uses, and which other test shares them
  whether the test passes when run alone (pytest -k test_order_refund)
```

## Diagnosis and fix

1. **Scope.** One repository's CI, not production. Ask the team to stop blind re-runs for an hour so the data stays clean. Pull 50 runs from `main` (command 1). Queue time is 20 to 40 seconds on every run, so runner contention is out. Wall time is 31 to 38 minutes on every run, so this is not noise.
2. **Find the step that grew.** Compare an August run with today's (command 2). "Install dependencies" went from 25 seconds to 9 minutes 40 seconds; "Run integration tests" from 7 to 14 minutes. That is 17 of the 23 extra minutes. The Docker build grew by 2 minutes; the rest is unchanged.
3. **Explain the install step.** The log says `Cache restored from key: npm-` and never `Cache saved`. The key is `npm-${{ hashFiles('package-lock.json') }}` and `hashFiles` returns an empty string when nothing matches. `git log` (command 5) shows the lockfile moved to `services/api/package-lock.json` on 1 September, the day the duration jumped. Every run since computes the constant key `npm-`, restores a stale entry for the old path, and runs a full `npm ci` in `services/api`. That is the 10 minutes.
4. **Explain the flaky test.** 19 failures in 100 runs, always `test_order_refund`, always `got 'pending'`. It asserts on `order_id=1001` in the shared staging database; `test_order_cancel` in another parallel worker uses the same row. Run alone 50 times it passes 50 times, so this is a shared-state race, not infrastructure. The rest of the test growth is the same cause: deadlock retries.
5. **Rule out the rest with a number.** Mirror: `npm ci` downloads at 40 MB/s from the default registry, no mirror in `.npmrc`. Docker cache: `type=gha` with 60 percent hits, 2 minutes lost, not the cause. Superseded runs: no `concurrency` block, so extra runs waste minutes but do not slow any one run.
6. **Fix through the review path.** One PR to `ci.yml`: key on `hashFiles('**/package-lock.json')` with `restore-keys: npm-` (or `setup-node` with `cache: npm` and `cache-dependency-path`); `concurrency` with `cancel-in-progress: true` on pull requests; Docker cache `type=registry,mode=max`. One PR to the tests: a schema per worker with generated ids, and `test_order_refund` marked quarantine with an owner and a date 14 days out.
7. **Verify.** Next 20 runs: `cache-hit: true`, install under 40 seconds, p50 13 minutes, 0 failures. `gh cache list` shows one key per lockfile hash.
8. **Prevent.** A nightly job computes p50, p90 and failure rate per job from the run data, pushes them to Prometheus and alerts on a 20 percent week-over-week p50 rise or a test failing more than 2 percent of the time. A lint step fails the workflow when a `hashFiles` call evaluates to an empty string.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why a moved lockfile silently breaks the cache

`hashFiles('package-lock.json')` is evaluated relative to the workspace root, and when the pattern matches no file it returns an empty string rather than failing. The key becomes `npm-`, which is a valid key, so the first run after the move saved a cache under it. Every later run gets an exact hit on that same stale entry, and an exact hit never saves a new one, so the entry is frozen on the day of the move and holds packages for the old path. The result is a cache that is downloaded, ignored and rebuilt by a full `npm ci`, and the entry is never evicted because it is accessed every run. Nothing fails, so nobody looks. The two defences are to key on `**/package-lock.json` (a glob that follows the file) and to add a check that fails the job when the computed hash is empty: `if [ -z "${{ hashFiles('**/package-lock.json') }}" ]; then exit 1; fi`. `restore-keys: npm-` is the fallback for a changed lockfile: the newest prefix match is restored and `npm ci` only fetches the difference.

### Flaky test or flaky infrastructure

A failure that passes on re-run has three possible homes: the test (order dependence, shared fixtures, time or randomness), the runner (out of memory, a slow disk, a network blip) or the system under test (a real race in the code). The cheapest discriminator is to run the test alone many times: `pytest -k test_order_refund --count 50` with a repeat plugin, or a shell loop. 50 passes alone and 1 in 5 failures in the suite means shared state. Then read the failing assertion for the identifier it touched and search the suite for that identifier. Here two tests used `order_id=1001` in the same staging database while running in parallel workers. The fix is isolation, not retries: each worker creates its own schema and the fixtures create fresh rows with generated ids. Retrying a flaky test hides a bug once and a real regression forever.

### Quarantine with an owner and a deadline

Deleting a flaky test loses coverage; leaving it in blocks everyone. Quarantine means the test still runs, its result is recorded, but it does not fail the pipeline. Each quarantined test carries a marker with an owner and an expiry date, and a CI check fails the build when a quarantine entry is past its date. Two weeks is enough to fix a fixture; if the owner cannot, the test is either fixed in a dedicated change or removed with a written reason. The list of quarantined tests is reported in the nightly metrics so it cannot grow quietly.

### Docker layer cache across runners

Hosted runners start clean, so a `docker build` on a runner never sees the layers built on another runner. `type=gha` stores layers in the Actions cache, which shares the repository's 10 GB with the dependency caches and is evicted by last access. `type=registry` pushes the cache to an image tag in the same registry as the output; with `mode=max` every stage's layers are exported, not only the final stage, which is what makes multi-stage builds hit. The cost is a push of a few hundred MB per build and one more tag to clean up. For a build that runs 40 times a day the saving of 2 minutes a run is worth it.

### Concurrency groups and superseded runs

A developer who pushes three commits to a PR in five minutes starts three full runs. Only the last one matters. `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }` cancels the earlier runs of the same branch. On `main` set `cancel-in-progress: false`, because a cancelled deploy run is worse than a slow one. This does not make a single run faster, which is why it was ruled out as the cause, but it frees runners, so queue time stays low as the team grows.

## Evaluation

**Did you find it?** The write-up names two causes with evidence: "the lockfile moved to `services/api/` on 1 September, `hashFiles` returns an empty string, the key is `npm-`, every run rebuilds dependencies: plus 10 minutes" and "`test_order_refund` and `test_order_cancel` share `order_id=1001` in the staging database and run in parallel workers: 19 percent failure rate." Each ruled-out candidate has a number: queue 30 seconds, mirror 40 MB/s, Docker cache 60 percent hits, no concurrency group.

**Is it fixed?** Twenty runs after the change: `cache-hit: true`, install step under 40 seconds, p50 wall time 13 minutes, p90 under 16, zero failures, and the quarantine list contains one test with an owner and a date.

**Is it prevented?** The nightly job publishes p50, p90 and failure rate per job and alerts on a 20 percent week-over-week regression. A lint step fails when a cache key hashes nothing. Quarantine entries expire and fail the build when overdue.

**What a strong answer adds.** Queue time versus wall time as the first split; `hashFiles` returning an empty string rather than failing; the "run it alone 50 times" discriminator; why retries hide bugs; `mode=max` for multi-stage builds; `cancel-in-progress: false` on the deploy branch; and the point that a slow pipeline is a DORA lead-time problem, not a cost problem.

**What a weak answer does.** "Add retries to the flaky test and use a bigger runner." It never reads the per-step durations or the cache log, and it treats a 20 percent failure rate as weather.

## Bottlenecks & mitigations

* The Actions cache limit: 10 GB per repository by default and eviction by last access, so one bad key that saves 1 GB per run evicts every other cache within a day.
* Shared staging database: every parallel worker and every PR touches the same rows, so isolation has to be built before parallelism helps.
* Log retention: run logs and caches are kept for a limited time, so the August baseline must come from stored metrics, not from old runs.
* Hosted runner start-up: every job pays checkout, cache download and tool install again; splitting into more jobs can make the total slower.
* One workflow file for everyone: a change to the cache key or concurrency affects every branch, so it needs the same review as code.

## Failure modes

* **Cache key hashes nothing.** `hashFiles` returns an empty string and the key is a constant. Mitigation: glob paths, a lint step that fails on an empty hash, and the `cache-hit` output checked in a later step.
* **Retrying flaky tests.** The suite goes green and the race in the fixtures stays. Mitigation: isolation per test and a quarantine list with owners and expiry.
* **Superseded runs not cancelled.** Three pushes, three full runs, the queue grows. Mitigation: concurrency groups keyed on the ref, cancel on pull requests only.
* **Docker layers rebuilt on every runner.** Hosted runners start clean. Mitigation: a registry cache with `mode=max`.
* **Parallel tests against one database.** Workers overwrite each other's rows. Mitigation: a schema per worker, generated ids, no fixed primary keys in fixtures.
* **Cancelling the deploy run.** `cancel-in-progress: true` on `main` stops a deploy half way. Mitigation: a separate concurrency group for `main` with cancel off.
* **Nobody owns the pipeline.** Duration doubles over two months and no alert fires. Mitigation: pipeline duration and failure rate as metrics with a regression alert.
* **Fixing it with a hand-edited runner.** A pre-warmed self-hosted runner hides the cache bug until the runner is replaced. Mitigation: fixes go in the workflow file through review.

## Follow-up questions interviewers ask

* Queue time is 8 minutes, not 30 seconds. What are the three most likely causes and how do you confirm each from the run data?
* The flaky test passes alone 50 times and still fails 1 in 5 in the suite after you isolated the database. What else is shared?
* How would you compute per-job p50 and p90 for the last 30 days with the REST API and a 30-line script?
* GitLab CI instead of GitHub Actions: where are the equivalents of cache keys, `cache-hit` and concurrency groups?
* The team wants to split the test job into 8 parallel shards. When does that make the total slower, and how do you balance the shards?
* A dependency mirror in another region is the bottleneck. How do you prove it and what are the options?

## Lessons that cover this

* [#9CI/CD with GitHub Actions and GitLab CIBuild and ship](/devops/learn/ci-cd-github-actions-gitlab)

## Further reading

* [GitHub Actions documentationGuidedocs.github.com](https://docs.github.com/en/actions)
* [Docker build best practicesGuidedocs.docker.com](https://docs.docker.com/build/building/best-practices/)
* [DORA: Research (State of DevOps)Paperdora.dev](https://dora.dev/research/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousTLS certificate expired in production](/devops/problems/tls-certificate-expired)[NextIntermittent DNS resolution failures in the cluster](/devops/problems/intermittent-dns-failures)

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
