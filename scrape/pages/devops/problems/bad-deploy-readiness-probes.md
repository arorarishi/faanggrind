# Deploy rolled out, users see errors, readiness probes flapping — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/bad-deploy-readiness-probes

[DevOps problems](/devops#problems)

OPSTroubleshooting#26Medium

# Deploy rolled out, users see errors, readiness probes flapping

kubernetesreadiness-proberolloutargo-rolloutstroubleshootingdeploymentReported at Infosys, Wipro

## Problem statement

It is 16:42. The pipeline posted "checkout-api v3.8.0 rolled out to production" at 16:30 and `kubectl rollout status` had exited 0. Since 16:35 the error-rate alert fires: 6 to 9 percent of requests through the Envoy Gateway ingress get 503, in waves about every 30 seconds. `kubectl get pods -n checkout -w` shows the 10 pods flipping between `1/1` and `0/1` Ready with 0 restarts. Find why pods that are running keep leaving the Service, stop the errors within 10 minutes, and make sure the next bad release stops at the canary.

## Requirements

### Functional

* Explain why a Deployment that reports complete can still be serving errors, in terms of readiness, `minReadySeconds` and `maxUnavailable`.
* Read the probe failure from the Events and the probe definition, and say which part of the probe is wrong.
* Separate the candidates: a slow dependency inside the readiness check, a timeout that is too short, a start-up that is slower than `initialDelaySeconds`, a real crash (ruled out by 0 restarts), an overloaded pod.
* Roll back within 10 minutes with the right tool (`kubectl rollout undo` or a Git revert under GitOps) and verify.
* Redesign the probe and the rollout so a release that flaps is caught at 5 percent of traffic.

### Non-functional

* Time to rollback decision under 5 minutes, errors gone within 10 minutes of the decision.
* The SLO is 99.9 percent success over 30 days; 7 percent errors for 12 minutes costs 0.84 minutes of full-outage-equivalent budget, so the 43.2-minute budget drains at about 1 minute of budget for every 14 minutes of incident.
* The rollback itself causes 0 additional errors: the old ReplicaSet is still there and its pods pass readiness in under 10 seconds.
* Next release: a canary at 5 percent for at least 10 minutes with automatic abort when the 503 rate exceeds 1 percent.

## Back-of-the-envelope estimates

**Impact.** 10 pods, each out of the Service for about 10 seconds in every 30-second cycle when its readiness check misses, so on average 3 of 10 pods are absent at any moment. The ingress returns 503 only when a request arrives in the window between a pod being removed from the EndpointSlice and the proxy's own retry; measured, that is 6 to 9 percent of requests. At 300 requests per second that is 18 to 27 failed requests per second, 1,100 to 1,600 per minute. Twelve minutes so far: about 16,000 failed requests. The error budget for 30 days at 99.9 percent is 43.2 minutes of total outage; 7 percent errors for 12 minutes equals 0.84 minutes of total outage, about 2 percent of the budget, with the burn continuing at 0.07 minutes per minute until rolled back.

## API

```
# 1. Scope: which pods, how often, any restarts? 0 restarts rules out crashes and liveness kills.
kubectl get pods -n checkout -l app=checkout-api -w
# checkout-api-6f8d9c7b5-2kq9x   1/1   Running   0   12m
# checkout-api-6f8d9c7b5-2kq9x   0/1   Running   0   12m
# checkout-api-6f8d9c7b5-2kq9x   1/1   Running   0   12m

# 2. The Events say what the probe saw.
kubectl describe pod -n checkout checkout-api-6f8d9c7b5-2kq9x | grep -A2 -E "Readiness|Unhealthy" | tail -n 6
# Warning  Unhealthy  kubelet  Readiness probe failed: Get "10.0.21.14:8080/ready" (scheme omitted here): context deadline exceeded
#   (Client.Timeout exceeded while awaiting headers)

# 3. The probe definition. timeoutSeconds 1 is the default; periodSeconds 10 and failureThreshold 3 too.
kubectl get deploy -n checkout checkout-api -o jsonpath='{.spec.template.spec.containers[0].readinessProbe}{"\n"}'
# {"failureThreshold":1,"httpGet":{"path":"/ready","port":8080},"periodSeconds":10,"timeoutSeconds":1}

# 4. What does /ready do in v3.8.0? Compare with the previous revision.
kubectl rollout history deploy/checkout-api -n checkout
kubectl rollout history deploy/checkout-api -n checkout --revision=47 | grep -A8 -i readiness
# v3.7.2: readiness /healthz, checks the process only
# v3.8.0: readiness /ready, which calls inventory-service GET /stock/ping with a 1 s timeout

# 5. Is the dependency slow? Its latency from the gateway metrics (Envoy histograms are in milliseconds).
# histogram_quantile(0.99, sum by (le) (rate(envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name=~".*inventory-service.*"}[5m])))
# p99 = 1.5 s under the afternoon load; p50 = 0.3 s. One probe in three or four exceeds 1 s.

# 6. Confirm the probe is the only thing leaving: EndpointSlice ready counts over time.
kubectl get endpointslices -n checkout -l kubernetes.io/service-name=checkout-api -o json \
  | jq '[.items[].endpoints[]] | map(.conditions.ready) | group_by(.) | map({ready: .[0], n: length})'
# [{"ready":false,"n":3},{"ready":true,"n":7}]

# 7. Why the rollout said complete: the Deployment settings.
kubectl get deploy -n checkout checkout-api -o jsonpath='{.spec.strategy}{" minReadySeconds="}{.spec.minReadySeconds}{"\n"}'
# {"rollingUpdate":{"maxSurge":"25%","maxUnavailable":"25%"},"type":"RollingUpdate"} minReadySeconds=

# 8. Roll back now. GitOps: revert the commit and let Argo CD sync; otherwise undo in place.
git revert --no-edit a1b2c3d && git push          # Argo CD syncs in about 3 minutes, or press Sync
kubectl rollout undo deploy/checkout-api -n checkout   # if the cluster is not GitOps-managed, or as a 1-minute bridge
kubectl rollout status deploy/checkout-api -n checkout

# 9. Verify.
kubectl get pods -n checkout -l app=checkout-api -o custom-columns=NAME:.metadata.name,READY:.status.conditions[?\(@.type==\"Ready\"\)].status,IMG:.spec.containers[0].image
# Envoy Gateway metrics, one Envoy cluster per backend Service; 503 ratio must return to 0:
# sum(rate(envoy_cluster_upstream_rq_xx{envoy_cluster_name=~".*checkout-api.*",envoy_response_code_class="5"}[1m])) / sum(rate(envoy_cluster_upstream_rq_completed{envoy_cluster_name=~".*checkout-api.*"}[1m]))  -> 0
```

## Data model

```
Pod and probe fields that decide it
  status.conditions[type=Ready].status            True | False, flipping every 10 to 30 s
  status.containerStatuses[0].restartCount        0   -> not a crash, not a liveness kill
  readinessProbe.httpGet.path                     /ready   (new in v3.8.0)
  readinessProbe.timeoutSeconds                   1   (default 1)
  readinessProbe.periodSeconds                    10  (default 10)
  readinessProbe.failureThreshold                 1   (default 3; set to 1 here: one slow answer removes the pod)
  readinessProbe.successThreshold                 1   (default 1)
  readinessProbe.initialDelaySeconds              0   (default 0; start-up is covered by startupProbe, not relevant here)
  startupProbe                                    absent

What a failing readiness probe does (and does not do)
  EndpointSlice endpoints[].conditions.ready -> false   the EndpointSlice controller removes the pod IP from Service traffic
  container keeps running, no restart                  (a liveness failure would restart it)
  Pod Ready=false counts against the Deployment's availableReplicas

Deployment fields that let the rollout "complete"
  spec.strategy.rollingUpdate.maxSurge          25%   up to 13 pods during the rollout
  spec.strategy.rollingUpdate.maxUnavailable    25%   up to 3 of 10 may be unavailable at any time
  spec.minReadySeconds                          0     a pod counts as available the second it is Ready, even if it flaps a second later
  spec.progressDeadlineSeconds                  600   the rollout only fails if no progress for 10 min
  complete = all replicas updated, all available, no old replicas running   (true for an instant, so status exited 0)

Events
  Warning  Unhealthy  Readiness probe failed: Get ".../ready": context deadline exceeded
  (no Killing, no BackOff, no OOMKilled)

Dependency latency
  inventory-service  p50 0.3 s   p99 1.5 s   probe timeout 1 s   -> roughly 1 in 4 probes fails under load

Argo Rollouts pieces for next time
  Rollout.spec.strategy.canary.steps      setWeight 5, pause 10m, setWeight 25, pause 10m, setWeight 100
  AnalysisTemplate.spec.metrics[].successCondition   result[0] < 0.01   (5xx ratio from envoy_cluster_upstream_rq_xx at the gateway)
  AnalysisTemplate.spec.metrics[].failureLimit       1
  failed analysis -> rollout aborted, canary weight set back to 0, stable serves 100%
```

## Diagnosis and fix

1. **Scope.** All 10 pods of one Deployment, 0 restarts, Ready flipping in waves, started 5 minutes after the rollout. Say in the incident channel that a rollback is the likely action.
2. **Read the Events.** `Readiness probe failed: ... context deadline exceeded` on every pod. A deadline is a timeout, not a refusal or a 500: the probe endpoint is slow, not broken. No `Killing`, no `BackOff`, so liveness and crashes are out. Overload is out: CPU per pod is 40 percent.
3. **Read the probe.** `timeoutSeconds: 1`, `failureThreshold: 1`, `periodSeconds: 10`. One slow answer removes the pod from the Service for at least one period. The rollout history shows v3.8.0 changed the readiness path from `/healthz` (process only) to `/ready`, which calls `inventory-service` with a 1-second timeout.
4. **Read the dependency.** `inventory-service` p99 is 1.5 seconds in the afternoon, p50 0.3 seconds. About one probe in four exceeds the 1-second deadline. Ten pods failing probes at random gives the waves and 3 pods out on average. Root cause: a readiness check that depends on a downstream service's tail latency with a timeout shorter than that tail.
5. **Why the rollout completed.** `minReadySeconds` is 0, so each new pod counted as available the instant its first probe passed, before the dependency's tail latency had a chance to fail one. `maxUnavailable: 25%` let the rollout go on while up to 3 pods were out. `rollout status` saw all 10 available at one moment and exited 0.
6. **Roll back now.** The cluster is GitOps-managed, so `git revert` the image bump and sync Argo CD; it takes 3 minutes and leaves the history honest. `kubectl rollout undo` in the same minute is an acceptable bridge if the channel agrees, knowing Argo CD will reconcile to Git. The old ReplicaSet is scaled back up, its pods pass `/healthz` in seconds, the 503 rate goes to 0.
7. **Verify.** All 10 pods on v3.7.2, Ready stable for 10 minutes, EndpointSlice shows 10 ready, ingress 503 ratio 0, alert resolved.
8. **Fix the probe and the rollout.** Readiness checks local health (the process can accept a request, config loaded, listeners up) plus a cached dependency status refreshed in the background every 10 seconds, never a live call. `timeoutSeconds: 3`, `failureThreshold: 3`, `successThreshold: 2`. `minReadySeconds: 30` so a pod must stay Ready for 30 seconds before the rollout counts it. Move the Deployment to an Argo Rollouts canary: 5 percent for 10 minutes with an AnalysisTemplate on the ingress 503 ratio, `successCondition: result[0] < 0.01`, `failureLimit: 1`, so a flapping release is aborted at 1 pod and 5 percent of traffic.

## Architecture diagram

Rendering diagram…

## Deep dives

### What readiness is for, and what it must never do

A readiness probe answers one question: can this pod take a request right now? When it fails, the EndpointSlice controller removes the pod from Service traffic, and nothing else happens: the container keeps running. That makes readiness the right place for "config loaded, listening, warm cache", and the wrong place for "my database answers in under a second". If every pod asks the same slow dependency, every pod leaves the Service at the same time, and a slowdown in one service becomes an outage in another; the dependency gets no less traffic, because the probes keep hitting it. The honest design is to report dependency health from a background check with a cache, so the probe itself is a memory read that takes microseconds, and to let the application return a fast 503 for the specific requests that need the dependency, which the load balancer can retry on another pod.

### Timeouts, thresholds and the arithmetic of flapping

`timeoutSeconds` defaults to 1, `periodSeconds` to 10, `failureThreshold` to 3 and `successThreshold` to 1. With the defaults, a pod leaves the Service after 3 consecutive slow answers (30 seconds of bad luck) and returns after 1 good one. This release set `failureThreshold: 1`, so one slow answer, a 1-in-4 event under load, removes the pod for a period. Ten pods and a 25 percent miss rate means about 2 or 3 are out at any moment, which matches the observed 6 to 9 percent 503s once proxy retries are counted. `initialDelaySeconds` is about start-up and did not matter here; a slow start belongs to a `startupProbe` so it is not confused with a readiness problem later in life. The tail, not the median, decides whether a probe flaps: compare `timeoutSeconds` with the dependency's p99, never its p50.

### Why "rollout complete" is a weak signal

A Deployment is complete when every replica is updated and available and no old replicas remain, and available means Ready for at least `minReadySeconds`, which defaults to 0. A pod that is Ready for one second counts. With `maxUnavailable: 25%` the rollout keeps going while 3 of 10 pods are flapping, and `rollout status` exits 0 at the first instant everything lines up. Two settings change this: `minReadySeconds: 30` makes a pod prove itself before it counts, and `maxUnavailable: 0` means a single NotReady pod stalls the rollout, which then fails at `progressDeadlineSeconds` (default 600) instead of completing. Neither looks at user errors, which is what Argo Rollouts analysis adds.

### Rolling back under GitOps

`kubectl rollout undo` is instant and precise, but if Argo CD manages the Deployment it will see the live spec drift from Git and, with self-heal on, put v3.8.0 back within minutes. The correct rollback is a revert commit; Argo CD syncs it and the history shows what happened. In an emergency you can do both in the same minute: undo for the bridge, revert for the record, and say so in the channel. With Argo Rollouts the question disappears: a failed analysis aborts the rollout on its own and the stable ReplicaSet never stopped serving 95 percent of traffic.

## Evaluation

**Did you find it?** One sentence: "v3.8.0 changed the readiness probe to call `inventory-service` with a 1-second timeout and `failureThreshold: 1`, and that service's p99 is 1.5 seconds under load, so one probe in four fails and pods leave the Service in waves." Evidence: the `context deadline exceeded` event on every pod with 0 restarts, the probe spec diff between revisions 47 and 48, the dependency's p99 from the metrics, and the EndpointSlice showing 3 of 10 not ready.

**Is it fixed?** After the revert syncs: 10 of 10 pods Ready without a flip for 10 minutes, the EndpointSlice lists 10 ready addresses, the ingress 503 ratio is 0, the alert resolves, and the error budget burn stops at under 4 percent of the month (about 22 minutes at 7 percent errors is 1.5 minutes of the 43.2).

**Is it prevented?** The probe checks local health plus a cached dependency status with `timeoutSeconds: 3` and `failureThreshold: 3`; `minReadySeconds: 30` and `maxUnavailable: 0` on the workload; an Argo Rollouts canary at 5 percent for 10 minutes with an AnalysisTemplate on the ingress 503 ratio that aborts above 1 percent; a review rule that a readiness probe may not make a network call.

**What a strong answer adds.** The default probe values from memory and the arithmetic of the flapping rate; the difference between readiness (traffic) and liveness (restart); why `minReadySeconds: 0` makes "complete" meaningless; the GitOps rollback subtlety; and that the fix is the probe design, not a longer timeout, because a 3-second timeout still fails whenever the dependency has a bad minute.

**What a weak answer does.** Raises `timeoutSeconds` to 10 and calls it done, deletes the pods, or removes the readiness probe entirely.

## Bottlenecks & mitigations

* Argo CD sync latency: a revert takes about 3 minutes to reach the cluster; a manual Sync click shortens it, `rollout undo` bridges it.
* Metrics resolution: a 503 ratio over 1-minute windows lags the flap by a minute, which is why the alert fired at 16:35 for a rollout that finished at 16:30.
* The dependency's tail latency is outside this team's control; the probe design must assume it will be slow sometimes.
* Analysis needs a metric that reflects users: the ingress 503 ratio works, pod CPU does not.

## Failure modes

* **Readiness probe calls a dependency.** A slow dependency removes every pod. Mitigation: local checks plus a cached background dependency status.
* **Timeout below the dependency's p99.** Flapping proportional to the tail. Mitigation: compare timeouts with p99, and do not make the call in the probe at all.
* **failureThreshold 1.** One slow answer removes a pod. Mitigation: default 3, successThreshold 2 for readiness.
* **minReadySeconds 0 with maxUnavailable 25%.** The rollout completes while pods flap. Mitigation: `minReadySeconds: 30`, `maxUnavailable: 0`.
* **Rollback by kubectl under GitOps.** Self-heal reapplies the bad version. Mitigation: revert in Git; use undo only as a declared bridge.
* **Liveness probe copied from readiness.** The same slow call now restarts pods, turning flapping into crash loops. Mitigation: liveness checks the process only.
* **Alert only on pod restarts.** Flapping has 0 restarts. Mitigation: alert on the Service's ready endpoint ratio and on the ingress error rate.
* **Canary without analysis.** 5 percent of users see the flap until a human notices. Mitigation: an AnalysisTemplate with a failureLimit that aborts automatically.

## Follow-up questions interviewers ask

* The dependency really is required to serve any request. How do you report its health without making every pod leave the Service at once?
* Write the Argo Rollouts canary steps and the AnalysisTemplate query for a 503 ratio over the last 5 minutes.
* The same probe is also the liveness probe. What would you have seen instead, and how much worse is it?
* `maxUnavailable: 0` and `minReadySeconds: 30` are set. Walk through what the rollout of v3.8.0 would have looked like.
* How does a startupProbe differ from `initialDelaySeconds`, and when do you need one?
* The service is behind an ALB with its own target health checks. How do the two health checks interact during the flap?

## Lessons that cover this

* [#10Deployment strategies and release engineeringBuild and ship](/devops/learn/deployment-strategies-release-engineering)
* [#15Kubernetes architecture and core objectsKubernetes](/devops/learn/kubernetes-architecture-core-objects)
* [#17Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKSKubernetes](/devops/learn/kubernetes-in-production)
* [#28Interview playbook, what is new in 2026, revision sheetShip](/devops/learn/interview-playbook-2026-revision)

## Further reading

* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)
* [Argo Rollouts documentationGuideargo-rollouts.readthedocs.io](https://argo-rollouts.readthedocs.io/en/stable/)
* [Google SRE Workbook: Chapter 5 - Alerting on SLOsArticlesre.google](https://sre.google/workbook/alerting-on-slos/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousHigh load average and a process eating memory on a Linux host](/devops/problems/high-load-memory-leak-linux)[NextTLS certificate expired in production](/devops/problems/tls-certificate-expired)

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
