# CI/CD pipeline for a 15-service monorepo — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/monorepo-ci-pipeline

[DevOps problems](/devops#problems)

DESIGNPlatform design#1Hard

# CI/CD pipeline for a 15-service monorepo

ci-cdgithub-actionsmonorepodockercachinggitops

## Problem statement

A company keeps 15 services (9 in Go, 6 in TypeScript) and 3 shared libraries in one Git repository. 60 engineers merge about 200 pull requests a day. Today every push rebuilds and tests all 15 services in a single 45-minute job, the queue of waiting runs is several hours long, and engineers merge without waiting for green. Design the CI and delivery pipeline: what runs on a pull request, what runs on main, how images reach the cluster, and how the team sees where the time goes.

## Requirements

### Functional

* A change builds and tests only the services it affects, including services that depend on a changed shared library, generated code or a build file.
* Every merge to main produces immutable container images in Amazon ECR, addressed by digest, and one deploy manifest listing the digest of every service at that commit.
* Main is always green: a pull request cannot merge unless the required checks passed on the exact combination of main plus that change.
* Staging is updated automatically after a green main build by a commit to the GitOps repository; production is a separate promotion step.
* Flaky tests are quarantined without blocking merges, and the quarantine list is visible and reviewed.
* Pipeline duration per stage, queue time and cache hit rate are recorded and shown on a dashboard.

### Non-functional

* Pull request checks finish in under 12 minutes at p90 for a change that touches one service (today 45 minutes).
* Queue time (push to first runner picked up) under 2 minutes at p90, today several hours.
* Runner cost under 5,000 USD per month at 800 runs per day, at an assumed 0.008 USD per runner-minute.
* A merge to main reaches staging within 20 minutes at p90.
* No long-lived AWS keys in CI; every AWS call uses a short-lived OIDC credential.
* Cache hit rate above 80 percent for Go module, node\_modules and Docker layer caches on pull request runs.

## Back-of-the-envelope estimates

**Today.** 200 merges plus roughly 600 pull request pushes = 800 runs per day. Each run uses one runner for 45 minutes: 800 x 45 = 36,000 runner-minutes per day. At an assumed 0.008 USD per minute that is 288 USD per day, about 6,050 USD per 21-day month. With 20 runners the pool completes 20 x 60 / 45 = 27 runs per hour against a demand of 80 per hour in a 10-hour working day, so the queue only grows.

**After.** Assume 90 percent of changes touch 3 services or fewer and 10 percent touch everything (a shared library, a lint rule, a base image). A small run is 2 minutes of change detection, 3 parallel service jobs of about 6 minutes each, and 2 minutes for the manifest: 2 + 18 + 2 = 22 runner-minutes, but only about 10 minutes of wall-clock time because the service jobs run side by side. A full run is 2 + 15 x 6 + 2 = 94 runner-minutes. Weighted: 0.9 x 22 + 0.1 x 94 = 29.2 runner-minutes per run, 800 x 29.2 = 23,360 runner-minutes per day, about 187 USD per day and 3,920 USD per month. That is a 35 percent saving in runner-minutes and a 4x drop in wall-clock time; the bigger win is the queue.

**Runners.** 80 runs per hour x 29.2 minutes / 60 = 39 runners busy on average, so size the Kubernetes runner pool for 80 at peak and let it scale to zero at night.

**Caches.** The Go build cache for one service is 300 MB to 1 GB; node\_modules for a TypeScript service about 400 MB; the Docker layer cache per service 500 MB to 2 GB. 15 services x 3 caches x 1 GB is about 45 GB, above the 10 GB default per-repository limit of the GitHub cache, so Docker layers go to ECR as a registry cache and only the language caches stay in the Actions cache.

## API

```
GitHub Actions workflow .github/workflows/ci.yml  (jobs, needs, outputs)

on: pull_request, merge_group, push to main
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true          # false on main, see deep dives

jobs:
  changes            runs-on: ubuntu-latest, 2 min
    outputs: services   JSON list of affected services, e.g. ["payments","ledger"]
             libs        JSON list of changed shared libraries
             full        "true" when infra/, tools/, or a lockfile changed
  build-test         needs: changes
    if: needs.changes.outputs.services != '[]'
    strategy.matrix.service: ${{ fromJSON(needs.changes.outputs.services) }}
    runs-on: [self-hosted, k8s, large]     (4 vCPU, 8 GiB pod)
    steps: restore Go or pnpm cache, unit tests, lint,
           docker buildx build --push (main only) with ECR registry cache
    outputs: digest-<service>  sha256:... written to $GITHUB_OUTPUT
  integration        needs: build-test, only on merge_group and main
    runs: contract tests between affected services and their dependants
  manifest           needs: build-test, integration, only on main
    writes deploy/manifest-<sha>.json: {service: digest} for all 15 services
    (unchanged services keep the digest from the parent commit's manifest)
    commits to platform-gitops: envs/staging/images.yaml
  required checks for the merge queue: changes, build-test (all matrix legs), integration

Promotion:  PR in platform-gitops copies envs/staging/images.yaml -> envs/prod/images.yaml
AWS access: permissions: id-token: write; aws-actions/configure-aws-credentials
            role-to-assume: arn:aws:iam::<ci-account>:role/gha-ecr-push (OIDC, no keys)

GitLab CI equivalent in one sentence: a "changes" job generates a child pipeline
YAML with one job per affected service and runs it through trigger:include, with
rules:changes for path filters, needs for the DAG, interruptible: true for
cancel-on-new-push, cache:key:files for lockfile-keyed caches, and merge trains
in place of the merge queue.
```

## Data model

```
Repository layout
  services/
    payments/     Go      BUILD deps: libs/go-common
    ledger/       Go      BUILD deps: libs/go-common, libs/proto
    web-checkout/ TS      deps: libs/ts-ui, libs/proto
    ... 12 more
  libs/
    go-common/    go-proto/   ts-ui/
  proto/          *.proto, generated into libs/proto by `make generate`, checked in
  infra/          Terraform, Kubernetes base manifests  (change => full run)
  tools/ci/       affected.py, dependency graph  (change => full run)
  go.work, pnpm-workspace.yaml, package.json, pnpm-lock.yaml

Dependency graph (tools/ci/graph.json), rebuilt from go.work and pnpm-workspace:
  { "payments": ["libs/go-common"], "ledger": ["libs/go-common","libs/proto"], ... }
  affected(changed_paths) = services whose own dir changed
                            UNION services whose transitive deps include a changed lib
                            UNION all services when infra/, tools/, lockfiles or Dockerfile.base changed

Cache keys
  Go:      go-${{ runner.os }}-${{ hashFiles('go.work.sum', 'services/payments/go.sum') }}
  pnpm:    pnpm-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
  Docker:  --cache-from type=registry,ref=<acct>.dkr.ecr.<region>.amazonaws.com/payments:cache
           --cache-to   type=registry,ref=...:cache,mode=max,image-manifest=true,oci-mediatypes=true

ECR
  repository per service; tags: sha-<commit>; deploy by digest sha256:...
  lifecycle policy: keep last 50 sha- images, expire untagged after 7 days, keep :cache

Deploy manifest  deploy/manifest-<sha>.json  (also uploaded as a workflow artifact)
  { "commit": "<sha>", "built": "2026-11-03T10:00:00Z",
    "images": { "payments": "<acct>.dkr.ecr.<region>.amazonaws.com/payments@sha256:...", ... } }

platform-gitops repo
  envs/staging/images.yaml   written by CI on every green main build
  envs/prod/images.yaml      written only by a reviewed promotion PR
  Argo CD Application per env reads images.yaml through Kustomize images: overrides

Flaky quarantine  tools/ci/quarantine.yaml
  - test: TestLedgerReconcile   owner: team-ledger   since: 2026-10-20   issue: 4412
```

## High-level design

**Make the work smaller**

1. Build the service dependency graph from `go.work` and `pnpm-workspace.yaml` in a small script that is itself tested, and keep it in the repo so the `changes` job and a developer's laptop give the same answer.
2. In the `changes` job, diff the pull request against its merge base with main (`git diff --name-only origin/main...HEAD`), map paths to services through the graph, add dependants of any changed library, and fall back to the full set when a global file changed. Emit the result as JSON outputs.
3. Generate the `build-test` matrix from that output with `fromJSON`, so three affected services mean three parallel jobs and nothing else runs.

**Make each job faster**

4. Restore the Go module and build cache keyed on the service's `go.sum`, and the pnpm store keyed on `pnpm-lock.yaml`, with `restore-keys` prefixes so a lockfile bump still gets a warm cache.
5. Build images with `docker buildx` using an ECR registry cache per service in `mode=max`, so layers survive across runners; `COPY go.mod go.sum` before the source so dependency layers hit the cache.
6. Run heavy jobs on self-hosted runners in Kubernetes (Actions Runner Controller) with a pod per job, 4 vCPU and 8 GiB, scaling from 0 to 80 pods on queue depth; small jobs stay on hosted runners.
7. Cancel superseded runs with a concurrency group per ref on pull requests; on main every commit's run must finish, so the group there does not cancel.

**Make main safe**

8. Turn on the merge queue with the `changes`, `build-test` and `integration` checks required. The queue tests main plus the queued changes before merging, so main cannot go red because of two pull requests that each passed alone.
9. Quarantine flaky tests through a reviewed YAML list: quarantined tests still run but report separately and do not fail the job; each entry has an owner and an issue, and a weekly job fails if an entry is older than 30 days.

**Build once, deploy by digest**

10. On main, push each affected image to ECR, read back its digest, and write one deploy manifest for the commit; unchanged services inherit their digest from the parent manifest.
11. CI commits the manifest's digests to `envs/staging/images.yaml` in the GitOps repo; Argo CD syncs staging. Production receives the same digests through a pull request that copies the file, reviewed by the owning team.
12. Every AWS call (ECR push, S3 artifact upload) uses the GitHub OIDC provider and a role scoped to the repository and branch; no secrets hold AWS keys.

**See it**

13. Export per-job duration, queue time (`started_at` minus `created_at` from the API), cache hit or miss and matrix size to Prometheus; alert when p90 pull request time passes 12 minutes.

## Architecture diagram

Rendering diagram…

## Deep dives

### Change detection that is correct, not just fast

Path filters alone are wrong in three places. First, shared libraries: a change in `libs/go-common` must rebuild every service that imports it, transitively, so the detector walks the graph from `go.work` and the pnpm workspace rather than a hand-written list that rots. Second, generated code: protobuf output is checked in, so a `.proto` change without regenerated files must fail the `changes` job (`make generate && git diff --exit-code`), otherwise a service compiles against stale stubs. Third, files that affect everything: `infra/`, `tools/ci/`, lockfiles, the base Dockerfile and the CI workflow itself. These trigger the full matrix, and that is fine because they are about 10 percent of changes. The diff is taken against the merge base (`origin/main...HEAD`), not against the previous push, otherwise a rebase hides changes. On main the diff is against the parent commit, which is correct because every parent already produced a manifest. The failure to avoid is false negatives (skipping a service that was affected); false positives only cost minutes.

### Cache keys and invalidation

A cache is only as good as its key. The Go module cache is keyed on the hash of the service's `go.sum`, the pnpm store on `pnpm-lock.yaml`; both include `runner.os` because the artifacts are platform-specific. A `restore-keys` prefix such as `go-Linux-` lets a lockfile bump start from the previous cache instead of empty. The Actions cache evicts entries not used for 7 days and the repository has a 10 GB default limit, so Docker layers do not fit there; they go to ECR with `--cache-to type=registry,mode=max,image-manifest=true,oci-mediatypes=true`, where `mode=max` keeps intermediate stages and the two manifest flags are what ECR needs. Pull request runs may read caches from their base branch but not write ones that main reads, so main warms the caches that pull requests consume. The Dockerfile order matters more than any flag: copy `go.mod` and `go.sum`, run `go mod download`, then copy the source, so a code change only invalidates the last layers.

### Merge queue semantics

Two pull requests can each pass CI against main and still break main together (one renames a function, the other adds a caller). The merge queue fixes this: on a merge request it creates a temporary branch containing main plus the queued pull requests in order, runs the required checks on it through the `merge_group` event, and merges only on green. If one entry fails, the queue drops it and rebuilds the branches of the entries behind it. With 200 merges a day and a 10-minute check, a fully serial queue would allow only 60 merges in a 10-hour day, so the queue runs batches: a group size of 5 gives 5 x 60 = 300 merges per day of capacity with one group at a time, and the queue can test several groups in flight on top of that. The cost is that a failure in a group of 5 re-tests the other four, which is why flaky tests must be quarantined; one flaky test with a 2 percent failure rate in a 5-wide group fails about 10 percent of groups.

### Why build once and deploy by digest

A tag such as `payments:v1.2` can be overwritten; a digest `sha256:...` cannot. Building once on main and promoting the same digest through staging and production means the bytes tested in staging are the bytes that run in production, and a rebuild for production (different base image pull, different dependency resolution) can never introduce a change nobody reviewed. The deploy manifest makes a commit on main a complete description of the system: 15 digests, one file, so rollback is "deploy the previous manifest", and an auditor can answer "what ran at 14:05" from Git alone. Unchanged services inherit their parent's digest instead of being rebuilt, which is what makes the affected-only build safe to deploy from.

## Evaluation

**SLIs.** Pull request check duration at p50 and p90 (target under 12 minutes p90); queue time at p90 (under 2 minutes); merge queue throughput per hour and the share of groups that fail; cache hit rate per cache type (above 80 percent); time from merge to staging sync (under 20 minutes p90); DORA-style deployment frequency and change failure rate per service, computed from the GitOps repo history.

**Correctness tests.** A test suite for `affected.py` with cases: a library change, a proto change without regeneration, a Dockerfile.base change, a rebase that moves the merge base. A weekly "full matrix" run on a schedule compares its results with the affected-only runs of the week and alerts on any service that failed in full but was skipped by detection.

**Chaos and load.** Drain the runner node pool during business hours and check the queue recovers within 5 minutes; delete the ECR cache repository and confirm builds still succeed, only slower; push 50 pull requests in a minute and watch queue time.

**Cost review.** Monthly runner-minutes by job and by team from the exported metrics; alert if the full-matrix share rises above 15 percent, which usually means someone added a global dependency.

**Security.** OIDC role trust policy limited to `repo:org/monorepo:ref:refs/heads/main` for the push role; pull request runs get a read-only role; image scanning gate in `build-test`; the GitOps commit comes from a GitHub App token, not a personal token. A weak answer lists tools; a strong answer explains what makes detection wrong and what the merge queue protects.

## Bottlenecks & mitigations

* The `changes` job is serial and on the critical path; keep it under 2 minutes with a shallow clone plus `fetch-depth: 0` only for the merge base lookup.
* Self-hosted runner scale-up time (pod scheduling plus image pull) adds 30 to 90 seconds; keep a small warm pool during working hours.
* ECR registry cache pulls for large TypeScript images can exceed the time they save on fast runners; measure per service.
* The GitOps commit step is a serialization point: 200 commits a day to one file in one branch means retries on push conflicts; batch or use a bot queue.
* Integration tests between services grow with the dependency graph; keep them to contract tests, not full environments.

## Failure modes

* **Affected set misses a dependant.** A library change ships a service that was never rebuilt against it. Mitigation: graph derived from workspace files, the weekly full run comparison, and a full matrix on any change to the detector itself.
* **Cancel-in-progress on main.** A push cancels the run that was producing the manifest for the previous commit; that commit never reaches staging. Mitigation: the concurrency group cancels only on pull request refs.
* **Flaky test blocks the merge queue.** Groups fail repeatedly, the queue stalls, engineers bypass it. Mitigation: quarantine list with owners, 30-day expiry, and a retry only for quarantined tests.
* **Cache poisoning from a pull request.** A malicious pull request writes a cache that main later restores. Mitigation: pull request caches are scoped to the merge ref by GitHub; never restore caches from a `restore-key` that a fork could write; build-tool caches, not binaries.
* **Mutable tag deployed.** Someone deploys `payments:latest` by hand. Mitigation: ECR tag immutability on, Kyverno rejects images without a digest.
* **OIDC role too broad.** Any branch can push to ECR. Mitigation: trust policy subject condition on `refs/heads/main` for the push role, read-only role for everything else.
* **Runner pool outage.** All jobs queue. Mitigation: hosted runners as a fallback label for small jobs, alert on queue time above 5 minutes.
* **Manifest and GitOps repo diverge.** A hand edit to `images.yaml` points staging at a digest with no manifest. Mitigation: branch protection on the GitOps repo so only the CI app and reviewed PRs can write.

## Follow-up questions interviewers ask

* A team wants a 2-minute "smoke" check before the full pipeline. Where does it go without doubling runner cost?
* How would you handle a database migration that two services in the same commit depend on?
* Explain what happens, step by step, when a merge queue group of 5 fails on the third entry.
* The TypeScript builds are now the slowest leg. What do you try first, and how do you measure it?
* How do you give an auditor "what ran in production at 14:05 last Tuesday" in under a minute?
* Would you split the monorepo? What signal would make you do it?

## Lessons that cover this

* [#1DevOps, SRE and platform engineering - how software reaches productionFoundations](/devops/learn/devops-sre-platform-engineering)
* [#5Git and trunk-based workflowsFoundations](/devops/learn/git-and-trunk-based-workflows)
* [#9CI/CD with GitHub Actions and GitLab CIBuild and ship](/devops/learn/ci-cd-github-actions-gitlab)
* [#31Projects - pipeline, cluster, observability, operatorLater](/devops/learn/projects)

## Further reading

* [GitHub Actions documentationGuidedocs.github.com](https://docs.github.com/en/actions)
* [Continuous Deployment at Facebook and OANDAPaperresearch.facebook.com](https://research.facebook.com/publications/continuous-deployment-at-facebook-and-oanda/)
* [DORA: Research (State of DevOps)Paperdora.dev](https://dora.dev/research/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[NextZero-downtime deployment system with canary analysis and rollback](/devops/problems/zero-downtime-deploys)

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
