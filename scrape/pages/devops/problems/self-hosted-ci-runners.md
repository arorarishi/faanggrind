# Autoscaled self-hosted CI runners on Kubernetes — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/self-hosted-ci-runners

[DevOps problems](/devops#problems)

DESIGNPlatform design#20Medium

# Autoscaled self-hosted CI runners on Kubernetes

github-actionsactions-runner-controllerkarpenterbuildkitci-cdeks

## Problem statement

A company of 60 engineers runs about 2,000 GitHub Actions jobs a day, many of them Docker image builds. GitHub-hosted runners are the largest line on the GitHub bill, and they cannot reach the private package registry, the staging database or the internal Terraform state. Design self-hosted runners on the company's EKS cluster that scale with the job queue, build images without privileged containers, keep secrets out of the runner, never run untrusted code from forks, and cost less than the hosted runners they replace.

## Requirements

### Functional

* Workflows switch by changing `runs-on` to the self-hosted label; no other workflow changes for ordinary jobs.
* Runners appear within a minute of a job being queued and disappear after the job, one job per runner, nothing left behind.
* Docker image builds run inside the cluster without `privileged: true`, with a layer cache that survives across jobs.
* Jobs can reach private services (registry, staging database, internal APIs) and get AWS permissions through short-lived credentials, with no long-lived keys in GitHub secrets.
* Release jobs run on on-demand capacity; everything else may run on spot and be retried if interrupted.
* The platform team sees queue wait time, job duration, runner count and cost per day.

### Non-functional

* Queue wait (job queued to job started) under 60 seconds at p90 during working hours, under 3 minutes at p99.
* 2,000 jobs per day with bursts of 40 concurrent jobs without manual scaling.
* Compute cost per job under one third of the GitHub-hosted 4-core price.
* No job can read another job's workspace, secrets or Docker daemon; a compromised job cannot reach the Kubernetes API or the node.
* Runner image and runner binary updated within 2 weeks of a release, with a rollback path.
* The cluster's production workloads are unaffected: runners live on their own node pool with their own quotas.

## Back-of-the-envelope estimates

**Load.** 2,000 jobs per day, with 70 percent inside an 8-hour working window: 1,400 / 8 = 175 jobs per hour at peak. Assume an average job of 6 minutes. Concurrent runners at peak = 175 x 6 / 60 = 17.5; plan for bursts of 2x, so 35 runners, with `maxRunners: 60`.

**Nodes.** Give each runner pod 2 vCPU and 8 GiB (Docker builds are memory hungry). An m6i.4xlarge node has 16 vCPU and 64 GiB; after system reservations it packs 7 runners (56 GiB). 35 runners need 5 nodes at peak, 1 to 2 at night, 0 if `minRunners: 0`.

**Cost.** Job-minutes per month: 2,000 x 22 days x 6 minutes = 264,000. GitHub-hosted Linux 4-core runners cost 0.012 USD per minute (from the GitHub pricing page), so the hosted bill is about 3,168 USD per month. Self-hosted: node-minutes = job-minutes / 7 per node / 0.7 utilisation = 53,878, about 898 node-hours. With 85 percent on spot at an assumed 0.31 USD per hour and 15 percent on-demand at 0.768 USD: 898 x (0.85 x 0.31 + 0.15 x 0.768) = 340 USD. Add a small system node (73 USD) and NAT (99 USD): about 512 USD per month. Per job: 0.072 USD hosted against about 0.012 USD self-hosted, 6 times cheaper, well under the one-third target.

**Cache effect.** A typical job spends 3 of its 6 minutes in `docker build`. With a registry layer cache a hit rebuilds only the changed layers, about 1 minute, so the job drops to 4 minutes: 2 x 44,000 = 88,000 runner-minutes saved per month and a 33 percent shorter wait for engineers.

**Scaling lag.** A warm node starts a runner pod in 10 to 20 seconds (image already pulled). A cold node through Karpenter takes 60 to 120 seconds plus the runner image pull. Keeping `minRunners: 3` during working hours absorbs most bursts without a cold start.

## API

```
How a team uses the platform (workflow side)

  jobs:
    build:
      runs-on: arc-runner-set            # ephemeral runner from the scale set
      permissions:
        id-token: write                  # OIDC token for AWS
        contents: read
      steps:
        - uses: actions/checkout@v7          # pin to a commit SHA in real workflows
        - uses: aws-actions/configure-aws-credentials@v6
          with:
            role-to-assume: arn:aws:iam::<account>:role/ci-build-<repo>
            aws-region: ap-south-1
        - run: |
            docker buildx build --builder remote \
              --cache-from type=registry,ref=<ecr>/app:cache \
              --cache-to type=registry,ref=<ecr>/app:cache,mode=max \
              --push -t <ecr>/app:${GITHUB_SHA} .
    release:
      runs-on: arc-runner-set-ondemand   # second scale set on on-demand nodes
      environment: production

Platform side (Helm, OCI charts)

  helm install arc -n arc-systems --create-namespace \
    oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller
  helm install arc-runner-set -n arc-runners --create-namespace \
    --set githubConfigUrl=https://github.com/<org> \
    --set githubConfigSecret=arc-github-app \
    -f values-spot.yaml \
    oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set
```

## Data model

```
GitHub
  GitHub App installed on the org: permissions for self-hosted runners; its id and key in a
      Kubernetes Secret "arc-github-app" (never a personal access token in production)
  Runner groups: "ci-spot" and "ci-ondemand", restricted to the org's private repositories

EKS cluster
  Namespace arc-systems   controller Deployment (gha-rs-controller), listener pods
  Namespace arc-runners   AutoscalingRunnerSet -> EphemeralRunnerSet -> EphemeralRunner pods
      values-spot.yaml:     runnerScaleSetName arc-runner-set,         minRunners 3, maxRunners 60
      values-ondemand.yaml: runnerScaleSetName arc-runner-set-ondemand, minRunners 0, maxRunners 10
      containerMode.type: kubernetes  (or no containerMode and a remote BuildKit builder)
      template.spec: image ghcr.io/actions/actions-runner:<pinned version>,
                     resources 2 vCPU / 8Gi, nodeSelector workload=ci, toleration workload=ci
      ResourceQuota  pods 80, requests.cpu 160, requests.memory 640Gi
      NetworkPolicy  egress: GitHub, ECR, internal registry, staging DB, BuildKit service; deny node and API server
  Namespace buildkit      Deployment buildkitd (rootless), Service buildkit:1234, mTLS, 2 to 6 replicas
  Karpenter NodePools
      ci-spot      m6i and m6a 4xlarge, capacity-type spot, taint workload=ci:NoSchedule,
                   consolidationPolicy WhenEmpty, consolidateAfter 2m, limits cpu 400
      ci-ondemand  same families, capacity-type on-demand, limits cpu 80

AWS IAM
  role ci-build-<repo>  trust: GitHub OIDC provider, condition sub = repo:<org>/<repo>:ref:refs/heads/main
                         or sub = repo:<org>/<repo>:environment:production for release jobs
  ECR repositories with lifecycle rule: cache tags expire after 14 days
```

## High-level design

1. **Node pool.** Create two Karpenter NodePools for CI with a `workload=ci` taint so production pods never land there: spot for ordinary jobs, on-demand for releases. `consolidationPolicy: WhenEmpty` means a node is removed only when no runner is on it, so a running job is never evicted by consolidation.
2. **Controller.** Install the Actions Runner Controller from the OCI chart `gha-runner-scale-set-controller` into `arc-systems`, authenticated with a GitHub App stored as a Kubernetes Secret.
3. **Scale sets.** Install the `gha-runner-scale-set` chart twice into `arc-runners`: `arc-runner-set` (spot, `minRunners: 3`, `maxRunners: 60`) and `arc-runner-set-ondemand`. Each creates a listener pod that long-polls GitHub for queued jobs and sets the replica count of its EphemeralRunnerSet; each runner pod registers, runs exactly one job and is deleted.
4. **Builds.** Run a rootless BuildKit Deployment as a shared build service with mTLS; jobs call `docker buildx build --builder remote` and push layer cache to ECR with `type=registry,mode=max`. No runner pod is privileged and no Docker daemon runs on nodes for CI.
5. **Identity.** Workflows request an OIDC token (`permissions: id-token: write`) and assume a per-repository IAM role whose trust policy checks the `sub` claim, so a `main`-branch job and a release environment get different roles. Runner pods have a Kubernetes ServiceAccount with no RBAC and `automountServiceAccountToken: false`.
6. **Network.** A NetworkPolicy on the runner namespace allows egress to GitHub, ECR, the private registry, the staging database and the BuildKit service, and denies the node, the Kubernetes API and the instance metadata endpoint.
7. **Fork safety.** Runner groups allow only the org's private repositories; public repositories keep GitHub-hosted runners; private-repo fork pull requests require approval before workflows run, and `pull_request_target` is banned by a policy check.
8. **Observability.** Turn on the chart's `metrics` values so the controller and listener expose Prometheus metrics (`gha_assigned_jobs`, `gha_running_jobs`, `gha_job_startup_duration_seconds`, `gha_job_execution_duration_seconds`); dashboards show queue wait p90, runner count against `maxRunners`, spot interruptions and cost per day from the node pool labels.
9. **Upgrades.** Pin the runner image tag in values, bump it in a pull request every two weeks, roll out to the spot set first; rollback is the previous tag.

## Architecture diagram

Rendering diagram…

## Deep dives

### Ephemeral runners and why

A persistent self-hosted runner keeps its workspace, its Docker layer cache and whatever the last job left in `/tmp` or `~/.npmrc`. The next job, maybe from another team, inherits all of it. GitHub's guidance is that self-hosted runners have no guarantee of a clean machine, and the only way to get close is one job per runner: ARC's scale sets request a just-in-time configuration for each runner pod, the pod runs one job and the controller deletes it. The cost is a cold start per job (pod scheduling and runner registration, 10 to 20 seconds on a warm node) and the loss of on-disk caches, which is why caching must move out of the runner: layer cache in the registry, dependency cache through `actions/cache` or an S3-backed cache. `minRunners` keeps a few idle runners registered to hide the start-up time during the day; set it to 0 at night with a scheduled values change.

### Docker-in-Docker, rootless BuildKit, or a remote builder

Three honest options. **Docker-in-Docker** (`containerMode.type: dind`) runs a Docker daemon sidecar in every runner pod; it works with any `docker` command but the sidecar needs `privileged: true`, so a job that escapes the container owns the node, and every job starts with an empty layer cache. **Rootless BuildKit inside the pod** (`docker buildx create --driver kubernetes --driver-opt rootless=true`, or a rootless `buildkitd` sidecar) needs no privileged flag, but it needs user namespaces enabled on the node, a seccomp and AppArmor profile that allows `unshare` and `mount`, and a kernel new enough for rootless overlayfs (5.11 or later, otherwise the slower fuse-overlayfs); it is the right choice when teams must keep building inside their own pod. **A remote BuildKit service** (this design): a rootless `buildkitd` Deployment with mTLS that runners talk to with `--builder remote`. Builds share a warm local cache on the builder's volume plus the registry cache, no runner is privileged, and the builder can run on bigger nodes than the runners. The trade-off is a shared service with its own capacity and a multi-tenancy concern: a build can read another build's cache on the same builder, which is acceptable for one company and not for untrusted code. Kaniko was the common fourth option but its repository is archived, so prefer BuildKit.

### Fork pull requests

A pull request from a fork carries arbitrary code. On GitHub-hosted runners it runs in a throwaway VM with a read-only token and no secrets. On a self-hosted runner inside the VPC it can scan the network, hit the staging database and try the instance metadata endpoint. GitHub's security guidance says self-hosted runners should almost never be used for public repositories. The design therefore restricts runner groups to private repositories, keeps public repositories on hosted runners, turns on "Require approval for fork pull request workflows" for private repositories, and treats `pull_request_target` as a code-review blocker because it runs with the base branch's secrets. The NetworkPolicy, the metadata block and the missing ServiceAccount token are the second layer for the day someone gets this wrong.

### Scaling lag and warm pools

The listener reacts within seconds, but a runner pod on a node that does not exist yet waits for Karpenter: EC2 launch, bootstrap, join and image pull, 60 to 120 seconds or more. Three things cut it: a `minRunners` floor during working hours (3 runners of 2 vCPU, about 1 USD per hour), a small over-provisioning Deployment of low-priority pause pods on the CI pool that get evicted by runner pods and make Karpenter keep one spare node, and a slim runner image with the tools jobs need preinstalled and pulled by a DaemonSet so the pull is not on the critical path. Spot interruptions give 2 minutes of notice; the job fails and is retried on a fresh runner, which is why release jobs sit on the on-demand set.

## Evaluation

**SLIs.** Queue wait from "job queued" to "job started" (p90 under 60 seconds, p99 under 3 minutes); job success rate excluding test failures (above 99 percent; a runner-side failure is a platform incident); runner pods at `maxRunners` for more than 5 minutes (alert); spot interruption count per day; cost per job from node hours divided by jobs.

**Load and chaos tests.** Queue 60 jobs at once and measure how long until all are running and how many nodes Karpenter adds; terminate a spot node under load and confirm the jobs are retried, not lost, and that no release job was on it; delete the listener pod and confirm queued jobs still start after it restarts; run a job that tries to reach the Kubernetes API, the node's metadata endpoint and another namespace, and confirm all three are blocked.

**Security checks.** No `privileged` pod in `arc-runners` (Kyverno policy); runner ServiceAccount has no RoleBinding and no mounted token; the GitHub App key rotates yearly; IAM trust policies name a repository and branch or environment in `sub`, never the org wildcard; runner groups show only private repositories; a weekly check that no workflow uses `pull_request_target` with a checkout of the head ref.

**Cost review.** Monthly: node hours by capacity type, cache hit ratio from BuildKit logs, hosted-runner minutes that remain (should trend to the public repositories only), and the comparison against the 3,168 USD hosted baseline.

## Bottlenecks & mitigations

* The shared BuildKit service becomes the hot spot at 9 a.m.; size it by concurrent builds and give it fast NVMe for the local cache.
* Image pulls of the runner image on every new node; a DaemonSet pre-pull or a smaller image keeps scaling fast.
* ECR push and pull bandwidth through NAT; use an ECR VPC endpoint and keep cache tags from growing without a lifecycle rule.
* One listener per scale set is a single point of scheduling; it recovers on restart but a stuck listener looks like "nothing is scaling".
* GitHub API rate limits for the controller when many scale sets exist; keep the number of scale sets small (two here).

## Failure modes

* **Spot node reclaimed mid-build.** The job fails. Mitigation: `WhenEmpty` consolidation only, workflow-level retry for the spot set, release jobs on on-demand.
* **A job runs `privileged` Docker-in-Docker and escapes to the node.** Other jobs' data and the node credentials are exposed. Mitigation: no privileged pods by policy, remote rootless BuildKit, node IAM role with no permissions beyond the node's needs.
* **Fork pull request from an outside contributor runs on a self-hosted runner.** The VPC is probed. Mitigation: runner groups restricted to private repositories, approval required for fork workflows, NetworkPolicy and metadata block.
* **Listener pod dies or loses its GitHub session.** Jobs queue and nothing scales. Mitigation: alert on queued jobs with zero running for 2 minutes; the controller recreates the listener.
* **Registry cache tag explodes to hundreds of GB.** ECR bill climbs. Mitigation: lifecycle rule on cache tags, `mode=max` only for the main branch cache.
* **Runner image pinned to an old version.** A security fix is missed and jobs start failing on GitHub API changes. Mitigation: a two-week bump cadence, a dashboard showing the runner version against the latest release.
* **Jobs saturate the CI pool and starve each other.** p99 queue wait explodes. Mitigation: `maxRunners` and NodePool limits sized above the burst, a separate on-demand set so releases are never queued behind tests.

## Follow-up questions interviewers ask

* The same cluster is to host GitLab CI for an acquired team. How does GitLab Runner with the Kubernetes executor fit next to ARC, and what do they share?
* A team needs arm64 images. How do you build them: QEMU emulation on the builder, or an arm64 node pool with a second BuildKit service?
* Jobs need a database for integration tests. Do you run it as a service container in the runner pod or a shared staging instance, and what does NetworkPolicy look like for each?
* How would you prove to an auditor that a release image was built from a reviewed commit on this platform (provenance and SLSA)?
* Developers complain that `minRunners: 3` is wasted money at night. How do you schedule it, and what is the cost of a cold start at 8 a.m.?
* What would make you keep some jobs on GitHub-hosted runners even after this platform works?

## Lessons that cover this

* [#9CI/CD with GitHub Actions and GitLab CIBuild and ship](/devops/learn/ci-cd-github-actions-gitlab)

## Further reading

* [GitHub Actions documentationGuidedocs.github.com](https://docs.github.com/en/actions)
* [Karpenter documentationGuidekarpenter.sh](https://karpenter.sh/docs/)
* [SLSA: Supply-chain Levels for Software ArtifactsPaperslsa.dev](https://slsa.dev/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousUptime monitoring service with global probes and alerting](/devops/problems/uptime-monitoring-service)[NextPod stuck in CrashLoopBackOff](/devops/problems/pod-crashloopbackoff)

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
