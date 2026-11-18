# Internal developer platform and golden path — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/internal-developer-platform

[DevOps problems](/devops#problems)

DESIGNPlatform design#9Hard

# Internal developer platform and golden path

platform-engineeringbackstagegitopsmulti-tenancyeksdeveloper-experience

## Problem statement

A company has 25 product teams (about 150 developers) on one shared EKS platform run by a platform team of 4. Creating a new service takes two weeks of tickets: a namespace, a pipeline, DNS and a certificate, dashboards, alert rules, an IAM role and a secret path, each from a different person. Teams copy an old service and carry its mistakes. Design the internal developer platform (IDP) that turns "new service" into a 30-minute self-service action that produces a deployable, observable, secured service with an owner, without the platform team touching it.

## Requirements

### Functional

* A developer creates a service from a template in a catalog UI or CLI by filling in a short form: name, team, language, exposure (internal or public), data access needed.
* The action produces a repository with a working pipeline, Dockerfile, Helm values and a service manifest, plus a PR to the GitOps repo that creates everything the service needs on the cluster.
* Every service appears in a catalog with its owner, on-call rotation, links to dashboards, logs, runbook and a scorecard.
* Teams can change what the platform generated (resources, routes, alert thresholds) through the manifest, and can leave the golden path where they must, in a visible way.
* Platform APIs (the manifest schema, the template, the generated resources) are versioned, and old services keep working when a new version ships.
* The platform reports its own numbers: services created, time to first deploy, adoption, and ticket volume.

### Non-functional

* Time from "create service" to first successful production deploy under 30 minutes at p90, measured end to end.
* Platform team tickets for new services drop from about 6 per service to under 1 per service within two quarters.
* Platform components (catalog, template service, GitOps controller) available 99.5 percent monthly during working hours; an outage blocks new services and deploys, never running traffic.
* A template change rolls out to all 200 existing services within one week through automated PRs, with no team doing manual work.
* A new service cannot reach another team's namespace, secrets or database by default; isolation is generated, not requested.
* Platform cost under 1,500 USD per month on top of the cluster, excluding people.

## Back-of-the-envelope estimates

**Demand.** 25 teams create about one service every two months each: 25 / 2 = 12.5, call it 12 to 13 services per month, plus about 200 existing services to migrate.

**Platform hours before.** Each new service costs the platform team roughly 8 hours across 6 tickets (namespace and quota 1, pipeline 2, DNS and certificate 1, dashboards and alerts 2, IAM and secrets 2). 12 services x 8 = 96 platform hours per month, more than half of one engineer. Developers wait two weeks each time: 12 x 40 = 480 developer hours a month lost to waiting and copy-paste debugging.

**Platform hours after.** The template does the work; the platform team reviews the generated PR in 30 minutes: 12 x 0.5 = 6 hours per month. Building the platform costs roughly 2 engineers for 3 months: 2 x 3 x 160 = 960 hours, paid back in under a year from platform hours alone and in two months when developer waiting time is counted.

**Components.** Backstage (catalog plus scaffolder) needs 2 pods of 1 vCPU and 2 GiB, about one m6i.large (assumed 0.096 USD per hour): 0.096 x 730 = 70 USD per month, plus a small Postgres on an assumed db.t4g.medium at 0.065 USD per hour: 0.065 x 730 = 47 USD. Argo CD, External Secrets, Kyverno and the observability stack already exist for the cluster. GitHub Actions minutes for 200 services at 5 builds a day of 5 minutes over 22 working days: 200 x 5 x 5 x 22 = 110,000 minutes a month, which is the large cost and the reason to run self-hosted runners (see the CI runners problem). Total new platform cost about 300 to 500 USD per month including runners, well under the 1,500 USD target.

**Ratio.** 4 platform engineers for 150 developers is 1 to 37. Without the IDP the team spends most of its time on tickets; with it, the same 4 can serve 300 developers.

## API

```
How a developer uses the platform:

1. Catalog UI -> Create -> "Backend service (Go)" template
   form: name, team (from SSO group), exposure internal|public, needs: [postgres, s3, queue]
2. Scaffolder runs the template steps:
   fetch:template            -> repo skeleton with Dockerfile, .github/workflows, deploy/values.yaml, service.yaml
   publish:github            -> new repo under the team's org, CODEOWNERS = team
   publish:github:pull-request -> PR to platform-gitops: tenants/<team>/<service>/ generated from service.yaml
   catalog:register          -> catalog-info.yaml so the service appears with owner and links
3. Platform team (or a bot, for standard shapes) approves the GitOps PR; Argo CD syncs
4. First push to main: CI builds, scans, pushes by digest, bumps the image in the GitOps repo
5. Service is live at <name>.<team>.internal.example.com with dashboards and alerts

service.yaml  (the contract; schema version pinned)
  apiVersion: platform.example.com/v1
  kind: Service
  metadata: {name: checkout, team: payments, tier: 2}
  spec:
    runtime: {language: go, port: 8080, replicas: {min: 2, max: 20}, resources: {cpu: 500m, memory: 512Mi}}
    exposure: {type: public, path: /checkout}
    dependencies: [{kind: postgres, name: orders}, {kind: s3, bucket: receipts}]
    slo: {availability: 99.9, latencyP95Ms: 300}
    oncall: payments-primary
    escapeHatches: []        # e.g. [hostNetwork] must be listed, reviewed and expire

Platform CLI (same actions, for scripts):
  plat service create -f service.yaml
  plat service validate -f service.yaml        # schema and policy check, runs in CI too
  plat service render -f service.yaml          # shows the generated Kubernetes and AWS resources
```

## Data model

```
Repositories
  platform-templates/          scaffolder templates, one folder per golden path, semver tagged
    backend-go/  backend-python/  frontend-static/  worker/  cronjob/
  platform-generator/          Go program: service.yaml -> Kubernetes YAML + Terraform; versioned API
  platform-gitops/             Argo CD watches this
    tenants/<team>/<service>/
      namespace.yaml           Namespace team-<team>-<service>, PSS labels restricted
      quota.yaml               ResourceQuota from spec.resources x replicas.max x 1.2
      rbac.yaml                RoleBinding: team SSO group -> view (prod), edit (staging)
      networkpolicy.yaml       default deny; allow from ingress and observability; allow to listed dependencies
      appproject.yaml          AppProject: sourceRepos = team repo, destination = this namespace only
      podidentity.yaml         Pod Identity association -> IAM role <team>-<service> (created by ACK, Crossplane or a Terraform job)
      externalsecret.yaml      ExternalSecret path /<team>/<service>/*
      httproute.yaml           Gateway API HTTPRoute, host from team + name, cert via cert-manager
      dashboard.json           Grafana dashboard from the RED template
      alerts.yaml              PrometheusRule: SLO burn-rate alerts from spec.slo, routed to spec.oncall
      application.yaml         Argo CD Application pointing at the team repo deploy/ folder
  <team>-<service>/            the team's own repo
    service.yaml  Dockerfile  deploy/values.yaml  .github/workflows/ci.yaml  catalog-info.yaml

Catalog (Backstage)
  Component <service>: owner team, system, lifecycle, links, annotations for Argo CD, Grafana, PagerDuty
  Group <team>: members from SSO, on-call rotation
  Scorecard per Component: owner set, on-call set, SLO defined, image signed, no critical CVEs,
                           PDB present, requests set, runbook link resolves, manifest at latest major

Platform metrics (Prometheus)
  platform_service_created_total{template,version}
  platform_time_to_first_deploy_seconds (histogram)
  platform_scorecard_score{service,check}
  platform_tickets_total{category}
```

## High-level design

**The contract**

1. Define `service.yaml` with a JSON Schema and a version. It describes what the service needs (runtime, exposure, dependencies, SLO, on-call), never how the platform builds it. Everything else is generated from it.
2. Write the generator as a small Go program with a `render` command, so the same code runs in the scaffolder, in CI as a validation step, and on a laptop. Tests compare rendered output against golden files for each template version.

**Templates and catalog**

3. Install Backstage with SSO. Register five golden-path templates (Go backend, Python backend, static frontend, worker, cron job). Each template is a `scaffolder.backstage.io/v1beta3` Template with a short parameter form and steps: fetch the skeleton, publish the repo, open the GitOps PR, register in the catalog.
4. The skeleton includes a CI workflow that calls shared reusable workflows (build, test, scan, sign, push by digest, bump image in GitOps). Teams own the tests; the platform owns the workflow versions.

**Generated tenancy**

5. The GitOps PR creates the namespace with Pod Security Standards labels, a ResourceQuota computed from the manifest, RBAC bound to the team's SSO group, a default-deny NetworkPolicy with allows derived from `dependencies`, an Argo CD AppProject locked to the team repo and the one namespace, a Pod Identity association with a least-privilege IAM role built from `dependencies`, an ExternalSecret scoped to the service's secret path, an HTTPRoute and certificate, a Grafana dashboard and SLO burn-rate alerts routed to `oncall`.
6. A bot approves and merges PRs whose diff matches the generator's output for a standard manifest; anything with an escape hatch waits for a platform engineer.

**Lifecycle**

7. Template upgrades ship as a new generator version; a job renders every service with the new version and opens PRs to each repo and the GitOps repo, batched by team, with a two-week window before the old major is unsupported.
8. The scorecard runs nightly and shows red checks on the catalog page; a tier-1 service under a score threshold blocks production sync through a Kyverno policy on the Application.

**Support and what stays manual**

9. Support is a single channel with a rotating platform engineer, a public backlog, and office hours. Requests that recur three times become a template feature. Manual by design: new database clusters, public exposure of a tier-1 service, cross-account IAM, cost over a threshold, and anything in `escapeHatches`.
10. Measure: time to first deploy, services on the latest major, scorecard pass rate, tickets per month, deploy frequency and change failure rate per team (the DORA metrics), all on a platform dashboard that the platform team treats as its own product SLOs.

## Architecture diagram

Rendering diagram…

## Deep dives

### Templates versus abstractions: what to hide, what to expose

A template copies files once; an abstraction generates them every time from a smaller input. Templates are easy to start with and impossible to upgrade: after a year, 200 services carry 200 slightly different pipelines. Abstractions are upgradeable but, taken too far, become a private platform nobody outside the team understands, and developers hit a wall the first time they need something the abstraction does not model. The design uses both on purpose. The repository skeleton is a template (Dockerfile, test layout, workflow call) because teams must own and edit it. The platform resources are an abstraction (rendered from `service.yaml`) because teams should not hand-write NetworkPolicies and IAM policies, and because the platform must be able to regenerate all of them when the standard changes. The rule for what to expose: anything a product team would reasonably want to vary (resources, replicas, routes, SLO targets, dependencies) is a field in the manifest; anything that only exists to satisfy the platform (quota arithmetic, policy labels, AppProject restrictions) is generated and not editable. Escape hatches exist, but each is a named entry in the manifest, visible in the catalog, reviewed by a human and given an expiry date, so leaving the golden path is a decision, not an accident.

### The manifest is the contract, and contracts have versions

`service.yaml` is the API between 25 teams and the platform. It gets the treatment any API gets: a schema that is validated in CI and in the scaffolder, a version in `apiVersion`, a changelog, and a support window. Adding a field is a minor change and old manifests still render. Changing a field's meaning or removing one is a major change: the generator keeps rendering the old major for a published window while a migration job opens PRs that rewrite manifests to the new version. The `render` command is the escape from magic: a developer can see exactly what the platform will create from their manifest before merging. Two things keep the contract honest. Golden-file tests in the generator repo fail when a change alters the output for an existing manifest, which catches accidental breaking changes. And the manifest never contains anything the platform cannot enforce: if the schema says `slo.availability: 99.9`, the generated alerts and the scorecard check that number, so the field means something.

### Multi-tenancy that is generated, not requested

The isolation of 200 services on one cluster depends on every service having the same set of controls, and that only happens when the controls are generated. For each service the generator produces: a namespace with Pod Security Standards set to `restricted`; a ResourceQuota derived from the manifest's resources times the maximum replicas with 20 percent headroom; a default-deny NetworkPolicy with ingress allowed from the gateway and the observability namespace and egress allowed only to the dependencies listed (the Postgres service, the S3 VPC endpoint); an Argo CD AppProject whose `sourceRepos` is exactly the team repository and whose `destinations` is exactly the one namespace, so a team cannot point an Application at another namespace; and a Pod Identity association to an IAM role whose policy lists only the bucket and queue from `dependencies`. The important property is that none of this is a ticket. A developer who lists an S3 bucket gets the IAM statement, the NetworkPolicy egress and the ExternalSecret path in one PR, and a developer who lists nothing gets a service that can talk to nobody. Kyverno enforces the same rules at admission for anything created outside the generator, so the escape hatch cannot silently remove isolation.

### The platform is a product with its own SLOs

A platform that nobody adopts is a cost. Treat it as a product: a roadmap that teams can see, user interviews with the two teams that refuse to migrate (they are usually right about something), and SLOs on the platform's own behaviour. The ones that matter: time from create to first deploy (p90 under 30 minutes), scaffolder success rate (over 99 percent), GitOps PR time to merge for standard shapes (under 10 minutes), catalog availability during working hours, and time to roll a template fix to every service (under one week). Adoption is measured as the share of services on the latest manifest major and the share of deploys that go through the golden path, and the DORA metrics per team (deploy frequency, lead time, change failure rate, time to restore) show whether the platform is helping. The support model is part of the product: one rotating engineer on the channel, every answer that repeats becomes documentation or a template change, and the ticket count per month is on the platform dashboard where everyone can see it fall.

## Evaluation

**Platform SLIs.** Time from scaffolder start to first production deploy (p90 under 30 minutes); scaffolder run success rate; time to merge for bot-approved GitOps PRs; catalog and scaffolder availability (99.5 percent in working hours); template rollout time to all services; scorecard pass rate per team; tickets per new service.

**Adoption.** Services created through the template versus by hand (measured from the catalog and from namespaces without a generator label); share of services on the latest manifest major; number of active escape hatches and their ages; the DORA four metrics per team before and after.

**Security checks.** Every generated namespace fails a cross-namespace connection test from a probe pod; an AppProject test confirms a team Application targeting another namespace is rejected by Argo CD; IAM Access Analyzer finds no role with broader access than its manifest lists; Kyverno audit mode for two weeks, then enforce.

**Chaos and failure tests.** Delete the Backstage pods during a template run and confirm the run can be retried without a half-made repository; break the generator release and confirm golden-file tests block it; simulate a GitHub outage and confirm running services are unaffected.

**Cost review.** Platform component cost per month against the 1,500 USD target; CI minutes per service; cost per namespace from allocation labels shown on each service's catalog page.

**Strong versus weak answer.** A weak answer installs Backstage and calls it a platform. A strong answer names the manifest as the contract, shows what is generated from it, explains how 200 existing services get upgraded, and gives the platform its own SLOs and adoption numbers.

## Bottlenecks & mitigations

* Platform PR review: if every GitOps PR needs a human, the platform team becomes the ticket queue again. The bot must merge standard shapes.
* The generator as a single point of change: every team waits for the platform team to add a field. Keep the manifest extensible with annotations and a documented contribution path.
* GitHub API rate limits when the migration job opens 400 PRs; batch by team and spread over days.
* Backstage catalog ingestion for 200 services with many entity providers can lag; tune the processing interval and watch the queue.
* Argo CD reconciliation time as Applications grow past a few hundred; see the GitOps platform problem for sharding.

## Failure modes

* **Teams copy an old repo instead of using the template.** Drift returns and the catalog is incomplete. Mitigation: Kyverno denies namespaces without the generator label; the scorecard shows unregistered services; the template must be faster than copying.
* **A template bug ships to 200 services at once.** Every pipeline fails on Monday. Mitigation: generator golden tests, canary rollout to 5 services for two days before the fleet, PRs not direct pushes.
* **The manifest grows a field for every request.** It becomes a copy of the Kubernetes API. Mitigation: a field needs three teams asking and a platform owner; everything else is an annotation or an escape hatch.
* **The bot merges a PR that an attacker shaped to look standard.** A team gains another namespace. Mitigation: the bot re-renders from the manifest and merges only when the diff is byte-identical to its own output; AppProject destinations are also checked by policy.
* **Scorecard becomes a compliance theatre.** Teams game checks and nobody reads it. Mitigation: few checks, each tied to a real incident class, and a tier-1 block only for checks that have caused outages.
* **Backstage down during a release week.** Nobody can create services or see on-call. Mitigation: two replicas, Postgres with backups, on-call data also in the paging tool; running services never depend on the catalog.
* **Escape hatches never expire.** The golden path becomes the minority. Mitigation: expiry dates in the manifest, a monthly report of hatches older than 90 days, and a template feature for the three most common ones.

## Follow-up questions interviewers ask

* A team needs a service shape the templates do not cover (a GPU inference server). How do they get it without waiting a quarter?
* How would you migrate the 200 existing services without a freeze, and in what order?
* The company adds a second cluster in another region. What changes in the manifest, the generator and the GitOps layout?
* Where would Crossplane or ACK fit for the AWS resources (buckets, queues, databases) a service declares?
* A team argues the platform is slower than their hand-built setup. What do you measure to decide, and what if they are right?
* How do you version and deprecate a manifest field that 150 services use?

## Lessons that cover this

* [#1DevOps, SRE and platform engineering - how software reaches productionFoundations](/devops/learn/devops-sre-platform-engineering)
* [#29Platform engineering, service mesh and eBPFLater](/devops/learn/platform-engineering-service-mesh-ebpf)

## Further reading

* [Backstage documentation: What is Backstage?Guidebackstage.io](https://backstage.io/docs/overview/what-is-backstage)
* [DORA: Research (State of DevOps)Paperdora.dev](https://dora.dev/research/)
* [Argo CD documentationGuideargo-cd.readthedocs.io](https://argo-cd.readthedocs.io/en/stable/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAutoscaling for a web app: ASG, HPA and cluster autoscaling](/devops/problems/autoscaling-web-app)[NextGitOps deployment platform with Argo CD for 50 teams](/devops/problems/gitops-platform-argocd)

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
