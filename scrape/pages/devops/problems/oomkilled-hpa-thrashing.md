# OOMKilled pods and an HPA that keeps scaling up and down — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/oomkilled-hpa-thrashing

[DevOps problems](/devops#problems)

OPSTroubleshooting#31Medium

# OOMKilled pods and an HPA that keeps scaling up and down

kubernetesoomkilledhpaautoscalingresourcestroubleshootingReported at Infosys, TCS

## Problem statement

It is 11:15. The catalog team pages: p99 latency on `catalog-api` is 4 seconds instead of 200 ms and the error rate is 3 percent. `kubectl get pods -n catalog` shows 17 pods, 6 of them with `RESTARTS` between 3 and 9 and two in `CrashLoopBackOff`. `kubectl get hpa -n catalog` shows `catalog-api Deployment/catalog-api cpu: 184%/60% 4 20 17 31m`, and the HPA events show it scaled to 20 and back to 5 three times in half an hour. A release went out at 10:40. Find why the pods die, why the autoscaler is thrashing, stabilise the service, and stop both from recurring.

## Requirements

### Functional

* Read the termination reason, exit code and memory limit from the pod status and say which of the three memory stories fits: a leak, a limit that was always too low, or a change in the release or the traffic.
* Explain the feedback loop between OOM restarts, CPU usage and the HPA, with the numbers from the HPA status.
* Rule out, with evidence, kubelet eviction, a node out of memory, a traffic spike and a runtime heap setting.
* Restore p99 under 300 ms and zero restarts within 20 minutes, with a rollback or a measured limit change through the pipeline.
* Set HPA behaviour so a restart storm cannot drive it, and alert on OOMKilled restarts before users notice.

### Non-functional

* Diagnosis under 15 minutes with kubectl, metrics-server and the cluster's Prometheus.
* Recovery under 20 minutes from the page: the service has a 99.9 percent monthly target, which is 43 minutes of full outage, and 3 percent errors for 35 minutes has already spent about 1 minute of it.
* Blast radius during the fix is the `catalog` namespace; no node-level or cluster-level changes.
* After the fix: `OOMKilled` restarts 0 for 24 hours, HPA replica count changes at most once per 5 minutes, memory usage p99 under 80 percent of the limit.
* The new limit is derived from measured usage with at least 30 percent headroom, written in the PR with the measurement.

## Back-of-the-envelope estimates

**Memory.** Before the release a pod used about 360 MiB at p99: 120 MiB base heap, a 180 MiB in-memory product cache, 60 MiB runtime and native overhead. The release doubled the cache to 360 MiB, so the same pod needs about 120 + 360 + 60 = 540 MiB, above the 512 MiB limit; it is killed as soon as the cache fills, which under load takes 2 to 4 minutes. **CPU loop.** 4 pods serve 1,200 requests a second, 300 each, at about 300m CPU against a 500m request. A restarting pod spends 20 seconds at 900m (JIT, cache warm-up, retries from clients), and the HPA sees 184 percent of request on average; `ceil(4 x 184 / 60) = 13` replicas, then more as the new pods also restart, up to the `maxReplicas` of 20. When the storm pauses, usage is about 13 percent of request and with a 60-second scale-down window the HPA goes to `ceil(20 x 13 / 60) = 5` within two minutes. The new limit: measured p99 560 MiB x 1.3 = 728 MiB, rounded to 768 MiB.

## API

```
# 1. Why did the containers die? Reason, exit code, and how many times.
kubectl get pods -n catalog -l app=catalog-api -o custom-columns=\
'NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount,REASON:.status.containerStatuses[0].lastState.terminated.reason,EXIT:.status.containerStatuses[0].lastState.terminated.exitCode,NODE:.spec.nodeName'
# catalog-api-7c9d4-abcde   9   OOMKilled   137   ip-10-0-14-22
# catalog-api-7c9d4-fghij   0   <none>      <none> ip-10-0-15-8       <- the young ones have not filled the cache yet

# 2. The limit and request, and the QoS class that follows from them.
kubectl get deploy -n catalog catalog-api -o jsonpath='{.spec.template.spec.containers[0].resources}{"\n"}'
# {"limits":{"cpu":"1","memory":"512Mi"},"requests":{"cpu":"500m","memory":"256Mi"}}
kubectl get pod -n catalog catalog-api-7c9d4-abcde -o jsonpath='{.status.qosClass}{"\n"}'
# Burstable

# 3. Live memory now, pod by pod: the old pods sit at the limit, the new ones climb.
kubectl top pods -n catalog -l app=catalog-api --sort-by=memory | head -5
# catalog-api-7c9d4-abcde   412m   509Mi
# PromQL for the trend (working set, by pod, last 2 hours):
#   max by (pod) (container_memory_working_set_bytes{namespace="catalog",container="catalog-api"})
#   -> a sawtooth: climbs to 512Mi in 3 minutes, drops to 130Mi, repeats. Not a slow leak.

# 4. What the HPA sees and why it moves.
kubectl describe hpa -n catalog catalog-api | sed -n '/Metrics/,/Events/p'
# Metrics: resource cpu on pods (as a percentage of request): 184% (920m) / 60%
# Min replicas: 4   Max replicas: 20
# Behavior: scaleDown stabilizationWindowSeconds: 60, policies: Percent 100 / 15s
# Events: SuccessfulRescale  New size: 13; reason: cpu resource utilization above target
#         SuccessfulRescale  New size: 20; ...   SuccessfulRescale  New size: 5; reason: All metrics below target

# 5. Rule out the node and the kubelet: was it the kernel OOM killer in the container cgroup, or eviction?
kubectl get events -n catalog --field-selector reason=Evicted | head
# (none)
kubectl describe node ip-10-0-14-22 | grep -A5 "Conditions:" | grep MemoryPressure
# MemoryPressure   False
kubectl get events -A --field-selector reason=SystemOOM | head
# (none: the kill happened inside the container's cgroup, not at node level)

# 6. What changed in the release.
kubectl rollout history deploy/catalog-api -n catalog
kubectl rollout history deploy/catalog-api -n catalog --revision=41 | grep -E "Image|CACHE"
# Image: registry/catalog-api:2.14.0      CACHE_MAX_ENTRIES=200000   (revision 40: 100000)

# 7. Traffic: did the load change at 10:40?
#   sum(rate(http_requests_total{service="catalog-api"}[5m]))  -> flat at 1,200/s since 09:00

# 8. Roll back now, fix properly after.
kubectl rollout undo deploy/catalog-api -n catalog --to-revision=40
kubectl rollout status deploy/catalog-api -n catalog
```

## Data model

```
Pod status fields
  status.containerStatuses[0].restartCount
  status.containerStatuses[0].lastState.terminated.reason     OOMKilled | Error | Completed
  status.containerStatuses[0].lastState.terminated.exitCode   137 = 128 + 9, SIGKILL from the kernel OOM killer
  status.qosClass                     Guaranteed (requests == limits) | Burstable | BestEffort
  status.phase Failed + reason Evicted   kubelet node-pressure eviction, a different mechanism

Deployment fields
  resources.limits.memory    512Mi   the cgroup memory.max; exceeding it kills the process
  resources.requests.memory  256Mi   what the scheduler reserves; below the limit means Burstable
  env CACHE_MAX_ENTRIES      the release change that doubled memory
  JVM: -XX:MaxRAMPercentage (default 25 percent of the container limit); Node: --max-old-space-size

HPA fields (autoscaling/v2)
  spec.minReplicas 4, spec.maxReplicas 20
  spec.metrics[0].resource.target.averageUtilization 60     percent of CPU request, not of limit
  spec.behavior.scaleDown.stabilizationWindowSeconds        default 300; set to 60 here
  spec.behavior.scaleDown.policies                          default Percent 100 per 15 s
  spec.behavior.scaleUp.stabilizationWindowSeconds          default 0
  status.currentMetrics, status.desiredReplicas, conditions
  controller: sync every 15 s, tolerance 0.1, not-ready pods count as 0 percent on scale-up
  formula: desired = ceil(current x usage / target)

Metrics that decide it
  kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}
  kube_pod_container_status_restarts_total
  container_memory_working_set_bytes vs kube_pod_container_resource_limits{resource="memory"}
  kube_horizontalpodautoscaler_status_desired_replicas, _current_replicas
  VPA recommendation: status.recommendation.containerRecommendations[].target, upperBound
```

## Diagnosis and fix

1. **Scope.** One Deployment in one namespace, no node condition, nobody else paging. Say in the channel that the first action will be a rollback.
2. **Read the terminations.** Reason `OOMKilled`, exit code 137, on every pod older than 4 minutes (command 1). Limit 512Mi, request 256Mi, so Burstable, and the kill is the kernel enforcing the container's cgroup limit (command 2). No `Evicted` events, no `MemoryPressure`, no `SystemOOM` (command 5): not the kubelet, not the node.
3. **Which memory story?** The working-set graph is a sawtooth that reaches 512Mi in 3 minutes on every pod and resets on restart (command 3). A leak climbs over hours; a limit that was always too low would have restarted pods before 10:40, and the counter was 0 for 11 days. The step coincides with revision 41, which doubled `CACHE_MAX_ENTRIES` (command 6), and traffic is flat (command 7). The release doubled the cache and the pod now needs about 540 MiB against 512.
4. **Explain the HPA.** Target: 60 percent of the 500m CPU request. A restarting pod burns 900m for 20 seconds rebuilding its cache while clients retry, so the average is 184 percent and the HPA computes `ceil(4 x 184 / 60) = 13`, then 20. New pods fill their cache, die, and keep CPU high. When the kills line up and usage drops, the 60-second scale-down window with a 100 percent policy goes to 5 in two cycles, and the survivors are overloaded: the 4-second p99. The HPA is doing arithmetic on a symptom.
5. **Stabilise.** Roll back to revision 40 (command 8); within 3 minutes restarts stop and the HPA settles at 4. Rollback beats a live limit change because the new cache's memory need was never measured.
6. **Fix through the pipeline.** Measure the release in staging under replayed load: p99 working set 560 MiB. Set `limits.memory: 768Mi` and `requests.memory: 768Mi` (Guaranteed for memory: the scheduler reserves what the pod uses and it is last in line for eviction). HPA: `scaleDown.stabilizationWindowSeconds: 300`, `scaleDown.policies: Percent 25 per 60 s`, `scaleUp.policies: Pods 4 per 60 s`, `maxReplicas: 12` (twice the peak need). Add a VPA in `updateMode: "Off"` for a recommendation on record. Re-release 2.14.0 with those values.
7. **Verify.** 24 hours with `kube_pod_container_status_restarts_total` flat, working set p99 under 80 percent of 768Mi, at most one HPA change per 5 minutes, p99 latency 200 ms.
8. **Prevent.** Page on 2 `OOMKilled` restarts in 10 minutes, from `kube_pod_container_status_restarts_total` joined with `kube_pod_container_status_last_terminated_reason`. The canary step watches restarts and working set for 10 minutes before promotion. A CI check fails a PR that raises a cache or heap setting without a matching `resources` change.

## Architecture diagram

Rendering diagram…

## Deep dives

### Kernel OOM killer, kubelet eviction, and which one you are looking at

Two different things kill pods for memory. The kernel OOM killer acts inside the container's cgroup when the container exceeds its own `limits.memory`: the process gets SIGKILL, the container reports exit code 137 and reason `OOMKilled`, and the kubelet restarts it under `restartPolicy`. The node is fine; only this container was over its line. Kubelet eviction acts when the node as a whole runs short (`memory.available` under the threshold, 100Mi by default): the kubelet marks the pod `Failed` with reason `Evicted`, ranks victims by whether they exceed their requests and then by priority, and the pod is not restarted in place. The signatures differ: `OOMKilled` with a restart count versus `Evicted` with `MemoryPressure: True` on the node. QoS matters for the second case, not the first: a Guaranteed pod can still be OOM-killed by its own limit, but it gets `oom_score_adj` -997 so the kernel prefers other processes if the node itself runs out. Setting memory requests equal to limits makes the scheduler reserve what the pod will actually use, which stops the node from overcommitting memory, and it moves the pod to the back of the eviction queue.

### Container limit versus runtime heap

The 512Mi limit is the whole container: heap, non-heap, native buffers, threads, the page cache the kernel counts against the cgroup. A JVM by default takes 25 percent of the container limit as the maximum heap (`MaxRAMPercentage`), which is safe but wastes memory; teams set 70 to 75 percent and must leave the rest for metaspace, threads and off-heap. A Node process needs `--max-old-space-size` set a safe distance under the limit or V8 will grow past it. The failure in this problem is older than both: an in-memory cache sized in entries, not bytes, doubled by an environment variable with no change to `resources`. The rule that prevents it is boring and works: any setting that changes memory use (cache sizes, heap flags, worker counts) lives next to `resources` in the same values file and is reviewed together, and a canary measures working set at 90 percent of the limit before promotion.

### How a restart storm drives a CPU-based HPA

The HPA computes `desired = ceil(current x usage / target)` every 15 seconds on the average CPU across pods as a fraction of the request. Three details make a crash loop look like load. First, a pod that just started burns CPU rebuilding its cache and warming its JIT, far above its steady state. Second, a container that was killed loses all in-flight requests, which clients retry, so the surviving pods see a burst. Third, the controller treats pods that are not yet ready as 0 percent usage on scale-up, which blunts the effect a little but cannot cancel a 184 percent average. Scale-down is the mirror: the default stabilization window is 300 seconds, meaning the controller uses the highest recommendation of the last 5 minutes, which would have held the count up; this team set it to 60 and kept the default policy of 100 percent per 15 seconds, so one quiet minute collapses 20 pods to 5. The fix is a window of 300 seconds and a policy of 25 percent per minute, a scale-up policy of 4 pods per minute, and a `maxReplicas` that matches real capacity, because an HPA that can go to 20 will go to 20 the moment something is wrong.

### Leak, low limit, or change: three shapes on one graph

The working-set graph answers it before any heap dump. A leak climbs slowly, starts well after the pod started, and the kill arrives after hours or days; the restart count grows by one a day and the fix is in the code. A limit that was always too low shows restarts on every revision, usually at peak traffic, and the sawtooth matches the daily traffic curve; the fix is a measured limit, and VPA's `upperBound` is a good first number. A change in the release or the traffic shows a step: restarts begin at the rollout time or when the request rate jumps, every pod reaches the limit in the same few minutes regardless of age, and the rollout history or the traffic graph names the cause. Only the third case is fixed by a rollback.

## Evaluation

**Did you find it?** The note says: "Revision 41 doubled `CACHE_MAX_ENTRIES`; each pod now needs about 540 MiB against a 512 MiB limit and is OOM-killed within 3 minutes of filling the cache. The restart storm raises CPU to 184 percent of request, the HPA scales to 20, and a 60-second scale-down window with a 100 percent policy drops it to 5, which overloads the survivors." Evicted, node pressure, traffic change and a slow leak are each ruled out with a command.

**Is it fixed?** After the rollback, restarts stop within 3 minutes and the HPA holds 4. After the re-release with 768Mi requests and limits and the new HPA behaviour: 24 hours of zero `OOMKilled`, working set p99 under 80 percent of the limit, at most one replica change per 5 minutes, p99 latency 200 ms.

**Is it prevented?** An alert on `OOMKilled` restarts; a canary step that fails on any restart or working set above 90 percent of the limit; a CI check that ties memory-affecting settings to `resources`; a VPA in `Off` mode so the next limit change is based on a recommendation, not a guess.

**What a strong answer adds.** 137 is 128 plus SIGKILL; the difference between the cgroup OOM kill and kubelet eviction, and which events prove which; QoS and `oom_score_adj`; the HPA formula with the 184 percent plugged in; the 300-second default window this team overrode; `MaxRAMPercentage` and `--max-old-space-size`; and why rollback beats a live limit change when the need was never measured.

**What a weak answer does.** Raises the limit to 1Gi and `maxReplicas` to 40 without a graph, or deletes the HPA, and cannot say why CPU went up when the problem was memory.

## Bottlenecks & mitigations

* The memory limit is the only real capacity number for this service, and it was set once, two years ago, from a guess.
* The HPA's single signal: CPU percent of request measures restarts and retries as faithfully as it measures load.
* Scale-down policy: 100 percent per 15 seconds with a 60-second window can halve capacity in one controller cycle.
* Cache warm-up: every restart costs 20 seconds of 900m CPU and a burst of client retries on the neighbours.
* `kubectl top` shows now; without `container_memory_working_set_bytes` in Prometheus the shape of the growth is invisible.

## Failure modes

* **Cache size changed without a resources change.** The pod outgrows its limit on the first busy minute. Mitigation: memory-affecting settings reviewed next to `resources`; canary watches working set at 90 percent.
* **Memory request far below the limit.** The node is overcommitted and this pod is an eviction candidate too. Mitigation: requests equal limits for memory on serving workloads.
* **HPA with a short scale-down window and a 100 percent policy.** Capacity collapses in two cycles. Mitigation: 300-second window, 25 percent per minute, scale-up by pods per minute.
* **maxReplicas set from hope.** A fault scales to the maximum and multiplies the restart storm. Mitigation: `maxReplicas` from measured per-pod capacity, around twice the peak need.
* **Runtime heap larger than the container.** A JVM at 100 percent heap or Node with no `--max-old-space-size` is killed before it can garbage-collect. Mitigation: heap at 70 to 75 percent of the limit, documented beside it.
* **Treating OOMKilled as Evicted.** The on-call resizes nodes while the container limit is the problem. Mitigation: read `lastState.terminated.reason` and the node conditions, in that order.
* **Raising the limit live instead of rolling back.** The need is unknown and the hand edit is lost on the next sync. Mitigation: rollback first, measure in staging, change through the pipeline.
* **No alert on restarts.** The first signal is the latency page 35 minutes later. Mitigation: page on 2 `OOMKilled` restarts in 10 minutes.

## Follow-up questions interviewers ask

* The graph is a slow climb over 3 days instead of a sawtooth. How does the investigation change, and what do you do tonight versus this week?
* Memory usage is at 95 percent of the limit but nothing is killed. What is the kernel doing and why is the service slow?
* The HPA scales on a custom metric (requests per second per pod) instead of CPU. Would the thrashing still happen?
* Explain `oom_score_adj` for the three QoS classes and what it changes when the node, not the container, runs out of memory.
* The team wants VPA in `Auto` mode together with the HPA on CPU. What goes wrong?
* Write the canary analysis rule: which three metrics, which thresholds, and how long before promotion.

## Lessons that cover this

* [#17Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKSKubernetes](/devops/learn/kubernetes-in-production)

## Further reading

* [Kubernetes: Debug PodsGuidekubernetes.io](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
* [Google Cloud: Kubernetes best practices: Resource requests and limitsArticlecloud.google.com](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-resource-requests-and-limits)
* [Autopilot: Workload Autoscaling at Google ScalePaperresearch.google](https://research.google/pubs/autopilot-workload-autoscaling-at-google-scale/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousTerraform plan wants to destroy the production database](/devops/problems/terraform-wants-to-destroy-db)[NextDatabase connections exhausted after a deploy](/devops/problems/db-connection-pool-exhausted)

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
