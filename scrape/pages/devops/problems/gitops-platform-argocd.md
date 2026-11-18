# GitOps deployment platform with Argo CD for 50 teams — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/gitops-platform-argocd

[DevOps problems](/devops#problems)

DESIGNPlatform design#10Hard

# GitOps deployment platform with Argo CD for 50 teams

gitopsargocdkubernetesmulti-clusterrbaceks

## Problem statement

A company has 50 teams and 400 applications running on 4 EKS clusters: two production regions (eu-west-1 and ap-south-1), one staging and one dev. Deploys today are kubectl and Helm from laptops and CI runners with cluster-admin credentials; nobody can say what is running where, and rollbacks take an hour. Design the GitOps deployment platform on Argo CD: topology, repositories, how an image gets from CI to production, how teams are isolated, how production is protected, and how the platform itself scales and recovers.

## Requirements

### Functional

* Every change to any cluster goes through a Git commit that is reviewed, and Argo CD applies it; no human or CI credential can write to production directly.
* CI publishes images by digest and a bot opens the PR that changes the deployed version; promotion from dev to staging to production is a PR with required approvals.
* Each team can only deploy its own applications to its own namespaces, enforced by Argo CD, not by convention.
* Production syncs happen only in allowed windows, with a documented break-glass path for incidents.
* Teams see sync status, health and diff in one UI with SSO, and get notified on failed syncs and degraded health.
* Secrets never live in Git; External Secrets pulls them from AWS Secrets Manager at sync time.

### Non-functional

* Time from merge to the change applied on the target cluster under 5 minutes at p90 (3-minute reconciliation plus sync).
* A fleet-wide change (one commit touching all 400 applications) fully synced within 15 minutes per cluster.
* Argo CD available 99.9 percent monthly for sync and UI; an Argo CD outage never affects running workloads.
* Blast radius of a stolen Argo CD credential limited to one environment class: a non-production compromise cannot reach production.
* Argo CD itself restored from scratch in under 30 minutes after a management cluster loss.
* Platform cost under 1,000 USD per month on top of the four clusters.

## Back-of-the-envelope estimates

**Applications.** 400 applications x 4 environments = 1,600 Argo CD Application objects: 800 on the non-production instance (dev plus staging), 400 on each production instance.

**Reconciliations.** Argo CD re-checks Git about every 3 minutes by default (`timeout.reconciliation`). 800 / 3 = 267 reconciliations per minute on the non-production instance, 400 / 3 = 133 per minute on each production instance. A reconciliation is a cached revision check plus a diff against live state, so this is controller CPU, not Git traffic: with one environments repository the repo server runs one `git ls-remote` per interval, 20 per hour.

**Repo-server CPU.** A Helm render costs about 1 to 2 CPU-seconds (measure yours). A fleet-wide change re-renders 400 applications per instance: 400 x 1.5 = 600 CPU-seconds. Four repo-server replicas of 2 vCPU give 8 vCPU, so about 75 seconds. Without the `manifest-generate-paths` annotation every commit re-renders all 400, so that annotation is the most important setting in a monorepo.

**Sync time.** `--operation-processors` defaults to 10; set it to 25. At about 10 seconds per sync, 400 / 25 x 10 = 160 seconds, plus wave delays: well under the 15-minute target.

**Git API calls.** 400 applications averaging 2 deploys a day is 800 bot PRs a day, 33 per hour, each 4 API calls (branch, commit, PR, merge): 133 calls per hour, 400 at a 3x peak. The GitHub App limit of at least 5,000 requests per hour is fine, but the secondary limit on content-creating requests (80 per minute, 500 per hour) is close at peak, so the bot batches one PR per team per environment every 10 minutes.

**Controller shards.** Sharding is by cluster: one shard per production instance, two for the non-production instance.

**Cost (assumed).** Management cluster: 3 m6i.large at 0.096 USD per hour, 3 x 0.096 x 730 = 210 USD, plus the EKS control plane at 0.10 USD per hour, 73 USD, total 283 USD. Production instances run inside their own clusters on about 4 vCPU and 8 GiB each, roughly 2 x 70 = 140 USD. Total about 425 USD per month.

## API

```
Repositories
  platform-gitops/              platform team; Argo CD config, ApplicationSets, AppProjects, cluster add-ons
    argocd/<instance>/          nonprod, prod-eu, prod-ap: argocd-cm, rbac, notifications, projects
    applicationsets/            one ApplicationSet per environment, git generator over environments/
    addons/<cluster>/           ingress, cert-manager, external-secrets, kyverno, observability
  environments/                 the single deployment repo; CODEOWNERS maps apps/<team>/ to the team
    apps/<team>/<app>/
      base/                     Helm chart reference or Kustomize base
      overlays/dev/             values + kustomization; image digest written by the bot
      overlays/staging/
      overlays/prod-eu/
      overlays/prod-ap/
  <team>-<app>/                 application code and Dockerfile; CI only, no manifests for clusters

Flow of one change
  1. Merge to main in <team>-<app>            -> CI builds, tests, scans, signs, pushes image by digest
  2. CI calls the promote bot                 -> PR to environments/ overlays/dev with the new digest, auto-merged
  3. Argo CD nonprod syncs dev within 3 min   -> smoke tests run as a PostSync hook
  4. Developer opens promotion PR dev->staging (bot copies the digest); one team approval
  5. Promotion PR staging->prod-eu, then prod-ap; two approvals incl. a CODEOWNER; merge allowed any time
  6. Argo CD prod syncs only inside the sync window (Mon-Thu 09:00-17:00 local) unless break-glass

Platform API for a team
  argocd app list -p <team>                   # read, via SSO group -> role
  argocd app sync <team>-<app>-dev            # allowed in dev, denied in prod outside windows
  argocd app diff / history / rollback        # rollback = revert PR in environments/ (prod)
  kubectl: read-only in prod through EKS access entries; writes are impossible by RBAC
```

## Data model

```
Argo CD instances
  nonprod      on cluster mgmt (eu-west-1); manages dev and staging clusters via cluster secrets
  prod-eu      inside prod-eu cluster; manages only itself (in-cluster, no external credential)
  prod-ap      inside prod-ap cluster; manages only itself

Cluster secret (nonprod instance, one per managed cluster)
  label argocd.argoproj.io/secret-type: cluster
  name: staging   server: https://<eks-endpoint>
  config: {awsAuthConfig: {clusterName: staging, roleARN: arn:aws:iam::<acct>:role/argocd-nonprod-deployer}}
  the IAM role maps to an EKS access entry with a namespaced policy, not cluster-admin

AppProject per team (rendered from a template, one per instance)
  name: team-payments
  sourceRepos: [https://github.com/example/environments.git]
  destinations: [{server: https://kubernetes.default.svc, namespace: payments-*}]
  clusterResourceWhitelist: []              teams create no cluster-scoped resources
  namespaceResourceBlacklist: [{group: '', kind: ResourceQuota}, {group: '', kind: LimitRange},
                               {group: networking.k8s.io, kind: NetworkPolicy}]
  roles: [{name: deployer, groups: [sso:payments], policies:
           ["p, proj:team-payments:deployer, applications, sync, team-payments/*, allow"]}]
  syncWindows (prod only): allow, schedule '0 9 * * 1-4', duration 8h, timeZone Europe/Dublin,
                           applications ['*'], manualSync false

ApplicationSet "prod-eu-apps"
  generators: git files: repoURL environments, revision main, files apps/*/*/overlays/prod-eu/app.yaml
  template: name '{{.team}}-{{.app}}-prod-eu', project 'team-{{.team}}',
            source path 'apps/{{.team}}/{{.app}}/overlays/prod-eu',
            destination namespace '{{.team}}-{{.app}}',
            syncPolicy automated {prune: true, selfHeal: true}; no CreateNamespace, namespaces come from the platform
            annotations argocd.argoproj.io/manifest-generate-paths: '.;../../base'

Ordering
  sync-wave -5: CRDs and namespaces (platform)    wave 0: ConfigMaps, Secrets, Services
  wave 1: Deployments                              wave 2: HTTPRoutes, PrometheusRules
  hooks: PreSync migration Job, PostSync smoke test Job with hook-delete-policy

Argo CD state (what disaster recovery must restore)
  Application, AppProject, ApplicationSet objects   -> all in platform-gitops, regenerated
  cluster secrets, repo credentials                 -> External Secrets from Secrets Manager
  argocd-cm, argocd-rbac-cm, notifications cm       -> in platform-gitops
  redis                                             -> cache only, rebuilt on start
```

## High-level design

**Topology**

1. Run three Argo CD instances: one non-production instance on a small management cluster that manages dev and staging through cluster secrets, and one inside each production cluster managing only itself. Production holds no credential for any other cluster, and losing the management cluster stops non-production deploys only.
2. Install each instance from the HA manifests through Terraform once, then let it manage itself from `platform-gitops`: 3 API-server replicas, Redis in HA mode across 3 nodes, 4 repo-server replicas, controller sharded by cluster.

**Repositories and isolation**

3. One `environments` repository holds every overlay for every application, with CODEOWNERS per team folder and branch protection on main. Code lives in team repositories that contain no cluster manifests.
4. The platform team owns every Application object: an ApplicationSet per environment uses the Git files generator over `apps/*/*/overlays/<env>/app.yaml`, so a team gets an Application by adding a file in its own folder, and the project and destination namespace are templated from the path, never typed by the team.
5. An AppProject per team per instance restricts the source to the environments repository and the destination to the team's namespaces, denies cluster-scoped resources, and blacklists quota, LimitRange and NetworkPolicy.

**Promotion**

6. CI pushes images by digest and signs them. A bot with a GitHub App token writes the digest into the dev overlay and auto-merges; dev syncs and runs a PostSync smoke test.
7. Promotion is a PR that copies the digest to the next overlay. Staging needs one team approval; production needs two, one from a CODEOWNER. Rollback in production is a revert PR, which keeps history honest.
8. Production AppProjects carry an allow sync window for working hours; outside it, merged changes wait. Break-glass: a platform engineer assumes an audited IAM role and sets `manualSync` through a Git change to the project; the notification channel sees it.

**Operations**

9. SSO through OIDC; `policy.default: role:readonly`; team roles bound to SSO groups with sync rights in their project only. Notifications on sync failed and health degraded to the team's channel, and on any sync outside a window to the platform channel.
10. Drift: `selfHeal: true` reverts manual changes within seconds; a Prometheus alert fires when `argocd_app_info` reports OutOfSync for more than 10 minutes, meaning a change is waiting or self-heal is fighting someone.
11. Scale settings per instance: `timeout.reconciliation` 3 minutes plus GitHub webhooks for immediate refresh, `--status-processors` 50, `--operation-processors` 25, repo-server `--parallelismlimit` set so renders do not exhaust memory, and `manifest-generate-paths` on every Application.
12. Disaster recovery: nothing in Argo CD is a source of truth. Rebuild from Terraform plus `platform-gitops`, restore cluster and repo secrets through External Secrets, and the ApplicationSets regenerate all 1,600 Applications; `argocd admin export` runs nightly as a safety net.

## Architecture diagram

Rendering diagram…

## Deep dives

### Pull versus push, and what the credential is worth

In a push model, CI holds a credential that can write to production, and every runner, every workflow file and every third-party action is inside the trust boundary of production. In the pull model Argo CD runs inside or next to the cluster, reads Git with a read-only deploy key, and nothing outside the cluster holds a write credential. The OpenGitOps principles name the rest: desired state is declarative, versioned and immutable in Git, pulled automatically, and continuously reconciled, so drift is corrected instead of accumulating. The important consequence for security is that the review on a PR is the production change control, which is why branch protection, CODEOWNERS and signed commits matter more than any Argo CD setting. The remaining credential of value is the one Argo CD itself holds. For the production instances this design keeps it in-cluster: the controller talks to `https://kubernetes.default.svc` with its own ServiceAccount, so there is no secret that can be copied to a laptop. The non-production hub does hold cluster secrets for dev and staging, with an IAM role mapped to an EKS access entry that allows only the namespaces and kinds Argo CD needs, so even that credential is not cluster-admin.

### Hub blast radius and multi-cluster credentials

One central Argo CD for all four clusters is simpler: one UI, one RBAC file, one upgrade. It also means one compromise or one bad upgrade reaches every production region at once, and a hub outage in eu-west-1 stops deploys to ap-south-1 during the one event (a regional failure) when you most need to deploy there. The design therefore splits by environment class and keeps production per cluster. The cost is two more instances to upgrade and a UI per instance, which SSO and a shared Grafana dashboard make bearable; the ApplicationSets and AppProjects are rendered from one template, so the configuration is identical by construction. If one UI matters more than that, argocd-agent (a multi-cluster agent for Argo CD, still in active development) keeps the pull model with a central control plane, and is the thing to evaluate before building a hub. Whatever the topology, the cluster credential is an IAM role with an EKS access entry, rotated by AWS, never a long-lived bearer token in a Secret.

### Ordering and dependencies across applications

Inside one Application, Argo CD orders resources by phase (PreSync, Sync, PostSync), then by `argocd.argoproj.io/sync-wave` (lower first, default 0, 2 seconds between waves), then by kind (namespaces first, then other Kubernetes resources, then custom resources), then by name. That solves CRD-before-CR and migration-before-Deployment inside one application. Across applications there is no dependency graph: an app-of-apps with waves on the child Applications orders their creation, and since the built-in health check for the Application kind was removed in Argo CD 1.8, the `resource.customizations.health.argoproj.io_Application` Lua check must be restored for waves to wait on child health. The platform uses this for add-ons (CRDs and External Secrets in wave -5, cert-manager in -4, ingress in -3) and refuses to use it for team applications: a service that cannot start until another service is deployed is a design fault to fix with retries and readiness, not a deployment order to maintain forever.

### Preventing GitOps from bypassing RBAC

Kubernetes RBAC stops a developer from creating a Deployment in another namespace; it does nothing about a developer committing an Application whose destination is another namespace, because Argo CD applies it with Argo CD's own permissions. Four controls close that hole. Teams never write Application objects: ApplicationSets owned by the platform generate them with project and destination derived from the folder path, so the only way to target `payments-api` is to commit inside `apps/payments/`, which CODEOWNERS protects. The AppProject's `destinations` and `sourceRepos` are the hard boundary that Argo CD checks on every sync, and the default project is emptied so nothing falls through. `clusterResourceWhitelist` is empty for team projects and `namespaceResourceBlacklist` names the isolation objects, so a team's folder cannot carry a ClusterRoleBinding or delete its NetworkPolicy. And Argo CD's own RBAC gives `sync` only inside the team's project and `override` to nobody, so the UI cannot be used to apply a live manifest that was never in Git.

## Evaluation

**Platform SLIs.** Merge-to-applied time per environment from the webhook timestamp to the Application's `operationState.finishedAt` (p90 under 5 minutes); fleet-wide sync time measured monthly with a labels-only change; Argo CD API availability from a probe (99.9 percent); `argocd_app_reconcile` latency histograms; `argocd_app_sync_total` by phase and result; `argocd_git_request_duration_seconds` and `argocd_repo_pending_request_total` for repo-server saturation; share of Applications OutOfSync for over 10 minutes (target under 1 percent).

**Security tests.** A team Application committed with another team's namespace is rejected by the AppProject (a CI test applies such an Application to the nonprod instance and expects the error); a developer SSO account cannot sync a production application outside its project; a cluster credential from the nonprod instance cannot reach a production API server (network and IAM both deny); a commit without the required approvals cannot reach main (branch protection audit).

**Chaos tests.** Delete the management cluster and rebuild from Terraform and Git within 30 minutes, confirm all 800 Applications regenerate and report Synced with no changes to the clusters; kill the production controller during a sync and confirm the sync resumes; make GitHub unreachable and confirm clusters keep running and Argo CD reports Unknown instead of pruning.

**Cost review.** Instance footprint per month against the 1,000 USD target; repo-server CPU per render; Git API calls by the bot per hour against the limits.

**Strong versus weak answer.** A weak answer installs one Argo CD, points it at four clusters and calls it GitOps. A strong answer chooses a topology for blast radius, explains who may create Application objects and why, shows the promotion path with approvals and windows, and knows the reconciliation and render arithmetic.

## Bottlenecks & mitigations

* The single environments repository: every commit refreshes every Application unless `manifest-generate-paths` is set; and GitHub's content-creation limit caps bot PRs per hour.
* Repo-server renders during a fleet-wide change; add replicas and memory before adding applications, and watch pending requests.
* Application controller memory grows with the number of resources in the managed clusters; a cluster with hundreds of thousands of objects needs its own shard and more memory.
* Sync windows concentrate production syncs into working hours; the first hour of the window on Monday is the busiest moment of the week.
* The PR review queue in large teams: 800 promotion PRs a day need bot auto-merge for dev and a merge queue for staging.

## Failure modes

* **Prune deletes a namespace's resources after a bad refactor moves them.** A folder rename makes 20 resources disappear from the rendered output and `prune: true` removes them. Mitigation: `Prune=false` sync option on tier-1 applications, a CI diff that fails on deletions over a threshold, and resource-level `argocd.argoproj.io/sync-options: Prune=false` on PVCs.
* **Self-heal fights an operator.** An HPA or operator changes replicas and Argo CD reverts it every few seconds. Mitigation: `ignoreDifferences` on the fields the operator owns, and HPAs own `replicas` with the field left out of Git.
* **Fleet-wide chart bump breaks 400 applications at once.** A shared base changes and every overlay renders differently. Mitigation: chart versions pinned per overlay, a rollout job that bumps dev first, staging a day later, production per team with a canary application.
* **Argo CD upgrade changes a default and reorders waves.** Syncs fail across the fleet. Mitigation: upgrade the nonprod instance first, soak for a week, read the upgrade notes, pin the chart version in Git.
* **Bot token leaks.** An attacker can open PRs with a different digest. Mitigation: the bot cannot approve or merge in staging or production; production requires human CODEOWNER approval and an admission policy that verifies the image signature.
* **Management cluster lost.** Dev and staging deploys stop. Mitigation: Terraform plus Git rebuild under 30 minutes, tested quarterly; production unaffected by design.
* **Secrets Manager outage during a sync.** ExternalSecrets fail and new pods cannot start. Mitigation: ExternalSecret refresh keeps the last Secret in the cluster; syncs that need new secrets wait, running pods are unaffected.
* **Sync window blocks a security fix at 2 am.** Mitigation: documented break-glass through a Git change to `manualSync`, an audited IAM role, and a notification to the platform channel.

## Follow-up questions interviewers ask

* A team wants progressive delivery (canary with automatic rollback). Where do Argo Rollouts or the Gateway API fit, and what changes in the promotion flow?
* The company grows to 2,000 applications. What breaks first in this design and how do you shard?
* Would you choose Flux instead for any part of this, and what would the trade-off be?
* An operator keeps a resource perpetually OutOfSync. How do you find and fix it without disabling self-heal?
* How would you handle a database migration that must run exactly once before the new version serves traffic, across two production regions?
* Show the exact AppProject and RBAC lines that let a team sync in staging but only view in production.

## Lessons that cover this

* [#5Git and trunk-based workflowsFoundations](/devops/learn/git-and-trunk-based-workflows)
* [#10Deployment strategies and release engineeringBuild and ship](/devops/learn/deployment-strategies-release-engineering)
* [#18Helm - charts, templates, values and releasesKubernetes](/devops/learn/helm-charts)
* [#19GitOps with Argo CD and progressive deliveryKubernetes](/devops/learn/gitops-argocd-progressive-delivery)
* [#29Platform engineering, service mesh and eBPFLater](/devops/learn/platform-engineering-service-mesh-ebpf)

## Further reading

* [Argo CD documentationGuideargo-cd.readthedocs.io](https://argo-cd.readthedocs.io/en/stable/)
* [OpenGitOps principlesGuideopengitops.dev](https://opengitops.dev/)
* [DORA: Research (State of DevOps)Paperdora.dev](https://dora.dev/research/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousInternal developer platform and golden path](/devops/problems/internal-developer-platform)[NextLog pipeline at 1 TB per day](/devops/problems/log-pipeline-1tb)

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
