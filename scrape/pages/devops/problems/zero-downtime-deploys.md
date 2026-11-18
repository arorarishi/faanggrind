# Zero-downtime deployment system with canary analysis and rollback — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/zero-downtime-deploys

[DevOps problems](/devops#problems)

DESIGNPlatform design#2Hard

# Zero-downtime deployment system with canary analysis and rollback

kubernetesargo-rolloutscanarygraceful-shutdownprogressive-deliveryeks

## Problem statement

A payments API runs on EKS as a Deployment of 40 pods behind an Application Load Balancer and serves 1,500 requests per second with a p99 latency of 800 ms. Every deploy causes about 30 seconds of 502 and connection-reset errors, and two of the last quarter's outages were bad releases that reached all 40 pods before anyone noticed. The team deploys twice a day. Design a deployment system where a normal deploy causes zero failed requests, a bad release is stopped automatically while it serves a small share of traffic, and rollback takes under 2 minutes.

## Requirements

### Functional

* A pod shutdown never drops an in-flight request and never receives a new request after it has started shutting down.
* A new version first receives a small share of traffic (5 percent), is judged automatically on error rate and p95 latency from Prometheus, and is promoted or aborted without a human in the loop.
* Rollback is available in two forms: an immediate abort of the rollout, and a Git revert through Argo CD that restores the previous digest.
* Database schema changes ship in a form that both the old and the new version can run against, so an abort never needs a schema rollback.
* Every deploy, promotion and abort appears as a marker on the service's dashboards and in the incident channel.
* Deploys are blocked during a declared freeze and outside the agreed window unless a break-glass label is set.

### Non-functional

* Zero failed requests attributable to a deploy, measured by the ALB 5xx count and the application's own error counter during the rollout window.
* A release with a 1 percent error rate is aborted before it serves more than 5 percent of traffic for more than 5 minutes.
* Abort to 100 percent stable traffic in under 60 seconds; full Git revert in under 2 minutes.
* A full canary rollout completes in under 30 minutes when every analysis step passes.
* At most 10 extra pods (25 percent surge) during a rollout; the cluster must have that headroom.
* The deployment pipeline itself has no long-lived credentials; it changes Git and lets Argo CD do the rest.

## Back-of-the-envelope estimates

**In-flight requests at SIGTERM.** Each pod handles 1,500 / 40 = 37.5 requests per second. With an average latency of 200 ms, Little's law gives 37.5 x 0.2 = 7.5 requests in flight per pod on average. The worst case is bounded by the p99: anything started in the last 800 ms may still be running, so at most about 37.5 x 0.8 = 30 requests. Across the cluster that is 300 in flight on average and up to 1,200 in the p99 window.

**Drain time.** After readiness turns false, the ALB controller must deregister the target and the ALB must stop routing to it, which takes a few seconds. A `preStop` sleep of 15 seconds covers that, then the server has up to 25 seconds to finish in-flight work, then a 5-second margin: `terminationGracePeriodSeconds: 45`. Worst case 15 + 25 + 5 = 45 seconds, usually about 16.

**Cost of the 30-second blip.** 1,500 x 30 = 45,000 failed requests per deploy. At 2 deploys per working day, about 40 per month, that is 1.8 million failed requests and 40 x 30 = 1,200 seconds, or 20 minutes, of errors. A 99.9 percent monthly SLO allows 43 minutes of full outage, so deploys alone burn nearly half the error budget.

**Canary sample size.** To tell a 1 percent error rate from the 0.1 percent baseline with a 5 percent false-alarm rate and 80 percent power, the normal approximation needs n = (1.645 x sqrt(0.001 x 0.999) + 0.84 x sqrt(0.01 x 0.99))^2 / (0.01 - 0.001)^2 = about 227 requests. At 5 percent weight the canary receives 75 requests per second, so it has that many in about 3 seconds. The real limit is the metric path: a Prometheus scrape every 15 seconds and a `rate()` over 2 minutes means each measurement covers 75 x 120 = 9,000 requests, with 9 errors expected at baseline and 90 at 1 percent, which is a very clear signal.

## API

```
How a team ships a change

1. Merge to main           -> CI builds image, pushes to ECR by digest (see problem 1)
2. GitOps PR               -> envs/prod/payments/values.yaml  image.digest: sha256:...
3. Argo CD sync            -> updates the Rollout's pod template
4. Argo Rollouts canary    -> steps below run on their own; Slack gets each transition
5. Watch or walk away      -> kubectl argo rollouts get rollout payments -n payments --watch

Operator commands (RBAC: on-call role only, every call audited)
  kubectl argo rollouts status payments -n payments        # Progressing, Paused, Healthy, Degraded
  kubectl argo rollouts abort payments -n payments         # back to 100 percent stable, under 60 s
  kubectl argo rollouts promote payments -n payments       # skip the current pause
  kubectl argo rollouts promote --full payments -n payments  # skip all steps and analysis (break-glass)
  kubectl argo rollouts undo payments -n payments          # roll back to the previous revision
  git revert <sha> in the GitOps repo                      # the durable rollback; Argo CD syncs it

Rollout strategy (the contract between the service and the platform)
  strategy.canary:
    canaryService: payments-canary      stableService: payments-stable
    trafficRouting.alb: ingress payments, servicePort 80, rootService payments
    steps:
      - setWeight: 5
      - pause: {duration: 5m}           # background analysis running
      - setWeight: 20
      - pause: {duration: 10m}
      - setWeight: 50
      - pause: {duration: 10m}
    analysis: {templates: [error-rate, p95-latency], startingStep: 1}
    abortScaleDownDelaySeconds: 600     # keep the bad canary pods for debugging

Deploy policy (Kyverno or a CI check on the GitOps PR)
  window:  Mon to Thu 10:00 to 16:00 IST; freeze calendar in platform-gitops/freeze.yaml
  bypass:  PR label break-glass + two approvals; posts to #incidents automatically
```

## Data model

```
Rollout payments (namespace payments)
  replicas: 40
  template.spec:
    terminationGracePeriodSeconds: 45
    containers[0]:
      readinessProbe:  httpGet /ready, periodSeconds 5, failureThreshold 1
      livenessProbe:   httpGet /live,  periodSeconds 10, failureThreshold 3
      lifecycle.preStop.sleep.seconds: 15     # sleep action is stable since Kubernetes 1.34; older: exec sleep 15
      env SHUTDOWN_DRAIN_SECONDS: "25"
  strategy.canary: as in api

Services
  payments-stable   selector managed by Rollouts (adds rollouts-pod-template-hash)
  payments-canary   same
Ingress payments (AWS Load Balancer Controller)
  alb.ingress.kubernetes.io/target-type: ip
  alb.ingress.kubernetes.io/healthcheck-path: /ready
  alb.ingress.kubernetes.io/healthcheck-interval-seconds: "5"
  alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30
  rule: host api.example.com -> service payments, port use-annotation
  (Rollouts writes alb.ingress.kubernetes.io/actions.payments with two weighted target groups)

PodDisruptionBudget payments   minAvailable: 36   (90 percent of 40)

AnalysisTemplate error-rate
  metrics[0]: name error-rate, interval 60s, count 5, failureLimit 1
    successCondition: result[0] < 0.005
    provider.prometheus.address: prometheus.monitoring:9090  (in-cluster, plain HTTP)
    query: sum(rate(http_requests_total{app="payments",role="canary",code=~"5.."}[2m]))
           / sum(rate(http_requests_total{app="payments",role="canary"}[2m]))
AnalysisTemplate p95-latency
  successCondition: result[0] < 1.2   (seconds; stable p95 is about 0.6)
  query: histogram_quantile(0.95, sum by (le)
           (rate(http_request_duration_seconds_bucket{app="payments",role="canary"}[2m])))

Migration record  (schema_migrations table, expand and contract)
  version  phase     compatible_with_app_versions
  0412     expand    >= 1.41          add column, nullable, no reads yet
  0413     contract  >= 1.43          drop old column, only after 1.42 is everywhere

Feature flags (ConfigMap or a flag service): payments.new_fx_rounding: {prod: 0 percent}

Deploy markers: Grafana annotation API {tags: [deploy, payments], text: "1.42 canary 5 percent"}
```

## High-level design

**Make one pod stop cleanly (fixes the 30-second blip)**

1. In the application, handle SIGTERM: flip `/ready` to 503, stop accepting new connections, wait for in-flight requests up to `SHUTDOWN_DRAIN_SECONDS`, close idle keep-alive connections, exit 0. Go: `srv.Shutdown(ctx)`; Node: `server.close()` plus tracking of open sockets.
2. Add `preStop` with a 15-second sleep so the ALB has deregistered the target before SIGTERM arrives; set `terminationGracePeriodSeconds` to 45 so the kubelet never SIGKILLs a draining pod.
3. Use `target-type: ip` so the ALB talks to pods directly, a 5-second ALB health check on `/ready`, and a 30-second deregistration delay instead of the 300-second default.
4. Bound the rollout: `maxSurge: 25%` (10 pods), `maxUnavailable: 0`, and a PodDisruptionBudget with `minAvailable: 36` so node drains and deploys together cannot remove more than 4 pods.

**Make a bad release small (fixes the two outages)**

5. Replace the Deployment with an Argo Rollouts `Rollout` using the canary strategy and ALB traffic routing: two Services, two target groups, the weight set by the controller through the ingress action annotation.
6. Define AnalysisTemplates for error rate and p95 latency against Prometheus, run as background analysis from step 1, with `failureLimit: 1` so a single bad minute is tolerated and two are not.
7. Steps: 5 percent for 5 minutes, 20 percent for 10 minutes, 50 percent for 10 minutes, then full. A failed analysis aborts the rollout and routes 100 percent back to stable within seconds.

**Make the change itself safe**

8. Schema changes follow expand and contract: the expand migration ships before the code that uses it and is compatible with the old code; the contract migration ships only after the new code is on every pod and the old column has had no reads for a week.
9. Risky behaviour goes behind a feature flag defaulting to off, so the deploy and the activation are separate events with separate rollbacks.

**Make it operable**

10. Argo CD syncs the Rollout from the GitOps repo. Rollback paths: `abort` for the first minutes, `git revert` for anything durable; `promote --full` only with the break-glass label.
11. The pipeline posts Grafana annotations and a Slack message on every step transition, abort and promotion; the on-call dashboard shows stable and canary as separate series.
12. A policy check on the GitOps PR enforces the deploy window and the freeze calendar.

## Architecture diagram

Rendering diagram…

## Deep dives

### The shutdown sequence, in order and with timings

Pod deletion starts a clock, and two things happen at once. The kubelet starts the `preStop` hook, and the control plane marks the pod's endpoint as `terminating` with `ready: false` in the EndpointSlice. The AWS Load Balancer Controller sees that and deregisters the target; the ALB stops sending new requests to it and drains for up to the deregistration delay (30 seconds here). None of this is instant, which is exactly why the application must not stop on the first signal: SIGTERM is only sent after `preStop` returns. With a 15-second sleep, by the time SIGTERM arrives the pod has had no new requests for about 10 seconds. The application then stops listening, finishes the at most 30 in-flight requests (p99 of 800 ms, so almost all in the first second) and exits. The grace period countdown started before `preStop`, so 15 seconds of sleep plus 25 seconds of drain must fit in 45; if the hook is still running at the deadline the kubelet grants only a 2-second extension before SIGKILL. The 30-second blip today has three causes: the app exits on SIGTERM immediately (resets in-flight requests), the ALB keeps routing to a dead IP until its health check fails (connection refused, 502), and readiness is not tied to shutdown.

### Canary analysis statistics

The numbers show that sample size is not the problem: 227 requests separate 1 percent from 0.1 percent, and the canary sees that in 3 seconds. The problem is noise in short windows and in the metric pipeline. A `rate()` over 2 minutes at 75 requests per second covers 9,000 requests; at the 0.1 percent baseline that is 9 expected errors with a standard deviation of 3, so a threshold of 0.5 percent (45 errors) is 12 standard deviations above baseline and will not fire by chance, while a true 1 percent (90 errors) clears it every time. Compare canary to stable, not to a fixed number, when traffic mix changes by hour: `canary_rate / stable_rate < 3`. Latency is harder: p95 from a histogram with 2 pods and 2 minutes of data is jumpy, so use a wider window or absolute thresholds with margin (1.2 seconds against a 0.6-second normal). `count: 5, failureLimit: 1` means five measurements a minute apart and one may fail; the second failure aborts. Scope every query to the canary pods with a label the Rollout sets, otherwise the stable pods dilute the signal 19 to 1 at 5 percent weight.

### Migrations that are compatible with rollback

An abort moves traffic back to the old code in seconds, but a schema change cannot be undone that fast, so the rule is: every migration that ships must be safe for both the version before it and the version after it. Expand first: add a nullable column, a new table or a new index (concurrently, in PostgreSQL), and deploy code that writes both old and new shapes while reading the old. Then switch reads to the new shape behind a flag. Only when the old shape has had no reads for a week does the contract migration drop it, shipped as its own release. Renames become add, backfill, switch, drop. A migration runs as a Kubernetes Job before the Rollout starts (an Argo CD PreSync hook), with a lock so two deploys cannot run it together, and the Job's image is the same digest as the app. The test is simple to state and worth automating: run the old version's integration suite against the new schema in CI.

### Long-lived connections and WebSockets

A payments API is request and response, but the same team's notification service holds 20,000 WebSocket connections across 10 pods. A rolling deploy there is a reconnection storm: 2,000 clients reconnect every time a pod stops. Three changes make it safe. On SIGTERM the server sends a close frame (code 1001, going away) to a slice of its connections every 100 ms rather than closing everything at once, so the 2,000 clients spread over 20 seconds; the grace period grows to match. Clients reconnect with exponential backoff and jitter, and the remaining pods must have connection headroom for the surge, which means sizing for 12 pods' worth of connections on 10. The ALB idle timeout (60 seconds by default) must be longer than the client ping interval or idle sockets drop mid-deploy anyway. For gRPC and HTTP/2 the same idea applies: send GOAWAY on shutdown so clients open their next stream to a healthy pod. Canary analysis for these services should watch reconnection rate and connection count per pod, not only HTTP error rate.

## Evaluation

**SLIs.** Deploy-attributed failed requests: ALB 5xx plus application errors in the 30 seconds after each pod termination, target 0; rollouts aborted automatically versus aborted by a human (automatic should dominate); time from analysis failure to 100 percent stable (under 60 seconds); canary duration at p50 (about 26 minutes); change failure rate and time to restore per DORA, computed from the GitOps history and the abort events.

**Tests before trusting it.** Deploy a version that returns 500 for 2 percent of requests and confirm the abort fires during the 5 percent step and no page goes out. Deploy a version with 1.5-second p95 and confirm the latency template catches it. Run `kubectl delete pod` on a stable pod under load and count errors (must be 0). Drain a node under load and confirm the PDB holds the line at 36 pods. Kill Prometheus during a rollout: the analysis should go inconclusive and the rollout pause, not promote.

**Game days.** Once a quarter, run a deploy during peak with the on-call engineer practising `abort`, `undo` and the Git revert, and time each.

**Security and policy.** `promote --full` and `abort` are restricted by RBAC to the on-call role and audited; the GitOps PR check rejects deploys in a freeze; the migration Job runs with a database role that can alter schema but not read payment rows.

**What a strong answer adds.** The ordering of readiness, deregistration and SIGTERM with the timings; why the canary comparison must be scoped to canary pods; expand and contract as the reason abort is always safe. A weak answer says "use a canary" and stops.

## Bottlenecks & mitigations

* The ALB weight change and target deregistration are API calls with their own latency; each step transition takes several seconds, and the AWS API rate limits apply when many services roll out at once.
* Prometheus scrape interval and `rate()` window set the floor on detection time; faster needs a shorter window and more noise.
* Surge headroom: 10 extra pods per rollout multiplied by services rolling out together needs cluster capacity or Karpenter time.
* A 26-minute canary limits the team to a few production deploys a day per service; parallel rollouts of different services are fine, two rollouts of the same service are not.
* Migration Jobs that hold table locks block both the old and the new version; keep them short and online.

## Failure modes

* **App exits on SIGTERM immediately.** In-flight requests are reset. Mitigation: the graceful shutdown contract in a shared library for Go and Node, verified by a `kubectl delete pod` test in staging CI.
* **preStop longer than the grace period.** SIGKILL during drain. Mitigation: grace period at least preStop plus drain plus 5 seconds; a Kyverno policy checks the arithmetic.
* **Analysis query matches stable pods too.** The canary signal is diluted and a bad release is promoted. Mitigation: label selectors on the canary ReplicaSet, and the 2 percent-error test release in staging on every change to the templates.
* **Prometheus down during a rollout.** Measurements are inconclusive. Mitigation: inconclusive pauses the rollout; alert on paused rollouts older than 15 minutes.
* **Contract migration shipped too early.** Abort moves traffic to code that reads a dropped column. Mitigation: contract migrations in a separate release with a one-week gap enforced by the migration record.
* **Deploy during peak with no headroom.** Surge pods stay Pending and the rollout stalls at 5 percent. Mitigation: deploy window, Karpenter headroom, and a pre-flight check that 10 pods' worth of capacity is schedulable.
* **Human promotes with --full to "get it over with".** The bad release reaches 100 percent. Mitigation: RBAC on `promote`, audit, and the break-glass label requirement.
* **WebSocket reconnection storm.** Remaining pods overload and fail health checks, cascading. Mitigation: staggered close frames, client backoff with jitter, 20 percent connection headroom.

## Follow-up questions interviewers ask

* The business wants blue-green for a release with a one-way data migration. How does the sequence change, and what do you lose?
* How would you canary a change to a shared library used by 15 services at once?
* The ALB is replaced by the Gateway API with a different controller. What stays and what changes in this design?
* A release passes canary at 5 percent but fails at 50 percent because of a cache stampede. How do you catch that earlier?
* How do you measure "zero failed requests" when the client retries and hides the errors?
* What changes if the service is a Kafka consumer with no HTTP traffic to analyse?

## Lessons that cover this

* [#1DevOps, SRE and platform engineering - how software reaches productionFoundations](/devops/learn/devops-sre-platform-engineering)
* [#10Deployment strategies and release engineeringBuild and ship](/devops/learn/deployment-strategies-release-engineering)
* [#19GitOps with Argo CD and progressive deliveryKubernetes](/devops/learn/gitops-argocd-progressive-delivery)

## Further reading

* [Argo Rollouts documentationGuideargo-rollouts.readthedocs.io](https://argo-rollouts.readthedocs.io/en/stable/)
* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)
* [Continuous Deployment at Facebook and OANDAPaperresearch.facebook.com](https://research.facebook.com/publications/continuous-deployment-at-facebook-and-oanda/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousCI/CD pipeline for a 15-service monorepo](/devops/problems/monorepo-ci-pipeline)[NextMulti-environment Terraform: dev, staging and prod with remote state](/devops/problems/terraform-multi-env)

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
