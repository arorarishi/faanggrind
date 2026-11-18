# Autoscaling for a web app: ASG, HPA and cluster autoscaling — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/autoscaling-web-app

[DevOps problems](/devops#problems)

DESIGNPlatform design#8Medium

# Autoscaling for a web app: ASG, HPA and cluster autoscaling

autoscalinghpakedakarpenterekscapacity

## Problem statement

An e-commerce web app runs on EKS. Traffic is a steady 300 requests per second, with a daily peak of 3,000 requests per second for one hour in the evening, and flash sales a few times a month that reach 10,000 requests per second within two minutes of the announcement. The team keeps 40 pods running all day, pays for them at night, and still sees errors and timeouts during sales. Design the autoscaling: pods, nodes, pre-scaling for announced sales, and the protections that keep the app up when demand passes the ceiling.

## Requirements

### Functional

* Scale the number of pods automatically on real demand (CPU and requests per second), not on a fixed count.
* Scale nodes automatically to fit the pods, using on-demand capacity for the base and spot for bursts.
* Pre-scale before an announced sale from a schedule, without a human running kubectl.
* Scale down after the peak without dropping in-flight requests.
* Protect the app when demand exceeds the ceiling: shed load at the edge rather than crash.
* Give the team one dashboard showing demand, replicas, node count and the gap between them.

### Non-functional

* p95 latency under 300 ms at the daily peak of 3,000 requests per second; under 500 ms during a sale.
* Error rate under 0.5 percent during the first five minutes of a sale (the hardest window).
* Scale from steady to sale capacity within 4 minutes of the demand rising, or ahead of time when the sale is announced.
* Compute cost at least 60 percent lower than today's 40 pods running all day.
* No single scale-down event removes more than 25 percent of the pods in one minute.
* Pod startup to Ready under 20 seconds, measured, because every lag number below depends on it.

## Back-of-the-envelope estimates

**Per-pod capacity.** A load test (k6 against one pod, HPA off) shows one pod serves 150 requests per second at 70 percent CPU of a 1 vCPU request, and latency climbs sharply above 180. We target 100 requests per second per pod, leaving a third free for the ramp.

**Pods per phase.** Steady 300 / 100 = 3 pods (minimum 3 for zone spread). Daily peak 3,000 / 100 = 30 pods. Sale 10,000 / 100 = 100 pods. Ceiling (maxReplicas) 120, 20 percent above the largest sale seen.

**Nodes per phase.** Each pod requests 1 vCPU and 1 GiB; an m6i.xlarge (4 vCPU, 16 GiB) fits 3 app pods after daemonsets. Steady: 1 node (2 on-demand for safety). Peak: 10 nodes. Sale: 34 nodes. Ceiling: 40 nodes.

**Reaction time.** The HPA sync period is 15 seconds by default. With the default scale-up policy (double, or add 4 pods, every 15 seconds) 3 to 100 pods takes 6 steps (3, 7, 14, 28, 56, 112, 120), about 90 seconds; with the Pods policy raised to 20 it takes 4 steps (3, 23, 46, 92, 120), 60 seconds. Karpenter needs roughly 60 to 90 seconds from pending pod to Ready node. Add metric scrape delay (15 to 30 seconds) and pod startup (20 seconds). Total about 3 to 4 minutes from first spike to full capacity, longer than the 2 minutes a sale takes to reach 10,000. That is why announced sales are pre-scaled.

**Cost (assumed prices, us-east-1).** m6i.xlarge on-demand 0.192 USD per hour; spot assumed at 70 percent off, 0.0576 USD per hour. Today, 40 pods need 14 nodes all day: 14 x 0.192 x 730 = 1,962 USD per month. Designed: 2 on-demand base nodes, 2 x 0.192 x 730 = 280 USD; 8 extra nodes for one hour a day, 8 x 0.192 x 30 = 46 USD; four sales a month of two hours on 32 spot nodes, 4 x 2 x 32 x 0.0576 = 15 USD. Total about 341 USD, an 83 percent reduction.

## API

```
How the team uses the platform (all through Git):

deploy/web/
  deployment.yaml      requests cpu 1, memory 1Gi; readinessProbe; preStop sleep 10
  pdb.yaml             PodDisruptionBudget minAvailable: 75%
  scaledobject.yaml    KEDA ScaledObject: cpu 70 percent, prometheus rps 100 per pod, cron windows
  ingress.yaml         Ingress via the AWS Load Balancer Controller, with a WAF rate-based rule per client IP

platform/karpenter/
  nodepool-ondemand.yaml   weight 50, limits cpu 16, consolidation WhenEmptyOrUnderutilized
  nodepool-spot.yaml       weight 10, limits cpu 200, capacity-type spot

Sale runbook:
  1. Marketing adds the sale to sales.yaml (start, end, expected rps)
  2. CI renders a KEDA cron trigger: desiredReplicas = expected_rps / 100 * 1.2, start 15 min early
  3. PR merged, Argo CD syncs; the HPA raises the floor; Karpenter adds nodes
  4. After end the floor drops; the HPA scale-down window applies, then consolidation removes nodes

Load test (must be rerun on every change to the hot path):
  k6 run --vus 200 --duration 5m one-pod.js   -> rps at 70 percent CPU, p95 latency
```

## Data model

```
KEDA ScaledObject "web"  (KEDA creates and owns the HPA)
  scaleTargetRef:     Deployment web
  minReplicaCount:    3
  maxReplicaCount:    120
  pollingInterval:    15            seconds; default is 30
  cooldownPeriod:     300           default; only applies when scaling to zero, which this app never does
  triggers:
    - cpu           metricType Utilization, value "70"
    - prometheus    query sum(rate(http_requests_total{app="web"}[1m])), threshold "100", metricType AverageValue
    - cron          timezone Asia/Kolkata, start "45 19 * * *", end "15 21 * * *", desiredReplicas "30"
    - cron          one per announced sale, desiredReplicas "120", rendered from sales.yaml
  advanced.horizontalPodAutoscalerConfig.behavior:
    scaleUp:   stabilizationWindowSeconds 0, policies Percent 100 per 15 s and Pods 20 per 15 s, selectPolicy Max
    scaleDown: stabilizationWindowSeconds 600, policies Percent 25 per 60 s

Karpenter NodePool "web-ondemand"   karpenter.sh/v1
  requirements: capacity-type In [on-demand], instance-category In [m, c], arch amd64, 3 zones
  limits: cpu 16                     the base; never more than 4 nodes
  weight: 50                         preferred while under its limit
  disruption: consolidationPolicy WhenEmptyOrUnderutilized, consolidateAfter 5m, budgets nodes 10%

Karpenter NodePool "web-spot"
  requirements: capacity-type In [spot], instance-category In [m, c], 3 zones
  limits: cpu 200
  weight: 10
  disruption: same, plus budget nodes 0 with schedule during the daily peak

Deployment "web"
  replicas managed by HPA (not set in Git)
  terminationGracePeriodSeconds 30, preStop exec sleep 10
  topologySpreadConstraints: zone, maxSkew 1
  PodDisruptionBudget minAvailable 75%

Prometheus metrics used
  http_requests_total{app,code}           from the app, scraped every 15 s
  kube_horizontalpodautoscaler_status_*   from kube-state-metrics
  karpenter_nodeclaims_*                  from Karpenter
```

## High-level design

**Measure first**

1. Run a load test against one pod with autoscaling off and record requests per second at 70 percent CPU and the latency curve. This gives per-pod capacity (150 here) and the target (100). Repeat for every release that touches the hot path; put it in CI as a nightly job.

**Pod autoscaling**

2. Install KEDA. It creates and manages an HPA for each ScaledObject, so one object holds the CPU trigger, the Prometheus requests-per-second trigger and the cron triggers. The HPA takes the largest replica count across triggers.
3. Set `minReplicaCount: 3` (one pod per zone) and `maxReplicaCount: 120`. Scale-up is immediate: stabilization 0, up to 100 percent or 20 pods every 15 seconds. Scale-down is slow: a 10-minute stabilization window and at most 25 percent per minute.
4. Add a daily cron trigger that raises the floor to 30 pods 15 minutes before the evening peak, and a generated cron trigger for every announced sale that raises it to the ceiling 15 minutes before the sale starts.

**Node autoscaling**

5. Install Karpenter with two NodePools. The on-demand pool has a high weight and a small CPU limit, so the base always lands there. The spot pool has a large limit and takes everything above the base. Both span three zones and allow several instance families so spot capacity is easy to find.
6. Set a disruption budget of zero nodes during the daily peak window so consolidation never removes nodes while traffic is high; outside it, 10 percent of nodes at a time.

**Draining and safety**

7. Every pod has a readiness probe, a `preStop` sleep of 10 seconds and a 30-second termination grace period, so the load balancer stops sending traffic before the process exits. The ALB target group deregistration delay is lowered from the 300-second default to 30 seconds. A PodDisruptionBudget of 75 percent available limits what consolidation and spot interruption can evict at once.
8. Put a CDN in front for static assets and cacheable product pages, and a Redis cache for catalogue reads, so the sale peak that reaches the pods is smaller than the peak at the edge.
9. Move the slow step (order creation writes to the database) behind a queue: the web pod enqueues and returns 202, workers drain the queue at the rate the database allows, and the worker Deployment has its own KEDA trigger on queue length.
10. Rate limit at the ingress per client IP so bots cannot eat the sale capacity, and return 503 with Retry-After when the pods are at the ceiling instead of letting latency climb until everything times out.

## Architecture diagram

Rendering diagram…

## Deep dives

### The HPA formula and what each knob does

The HPA controller runs every 15 seconds (`--horizontal-pod-autoscaler-sync-period`). For each metric it computes `desiredReplicas = ceil(currentReplicas x currentMetricValue / desiredMetricValue)` and takes the largest result across metrics. With 30 pods at 95 percent CPU and a 70 percent target: ceil(30 x 95 / 70) = 41. A ratio within 10 percent of 1.0 (`--horizontal-pod-autoscaler-tolerance`, 0.1 by default) changes nothing, which stops flapping. A pod that is not yet Ready has its CPU set aside during its first 5 minutes (`--horizontal-pod-autoscaler-cpu-initialization-period`), and a pod that became Ready within 30 seconds of starting is still treated as not ready for that window (`--horizontal-pod-autoscaler-initial-readiness-delay`), so fresh pods warming up do not drag the average down and cause an immediate scale-down. The `behavior` field is the tuning surface: the default scale-up policy allows doubling or adding 4 pods every 15 seconds, whichever is larger; we raise the Pods policy to 20 so 100 pods is reached in four steps instead of six. The default scale-down stabilization is 5 minutes; we use 10 minutes and 25 percent per minute, because scaling down too fast after a sale and then scaling up again is the classic thrash. With KEDA they live in `advanced.horizontalPodAutoscalerConfig.behavior`.

### Why CPU alone is a bad signal

CPU works when the app is CPU-bound. This app spends most of each request waiting on the database and Redis, so at 3,000 requests per second CPU might sit at 40 percent while connection pools are full and latency doubles. The HPA sees no reason to scale. Requests per second per pod tracks the thing we measured in the load test, so it is the primary signal, with CPU as a backstop for requests that happen to be expensive. The Prometheus metric arrives through KEDA (or the Prometheus adapter serving the custom metrics API), which means it is 15 to 45 seconds old by the time the HPA reads it: one scrape interval plus one polling interval. Latency is a worse scaling metric: it rises only after saturation, so scaling on it chases the symptom.

### Scaling lag, layer by layer

Add the delays from a demand step to full capacity: metric scrape, up to 15 seconds; KEDA polling, 15 seconds; HPA sync, 15 seconds; pod creation and scheduling, 2 seconds if a node has room; pod start to Ready, 20 seconds. About one minute when nodes exist. When they do not, add Karpenter: it notices pending pods within seconds, calls EC2, and the node joins and reports Ready after 60 to 90 seconds, then image pull and pod start. That path is 3 to 4 minutes. A sale hits 10,000 requests per second in 2 minutes, so reactive scaling alone loses the first minutes of the sale. Three things shorten the gap: pre-scale from the schedule, keep a small headroom (the 100 target against 150 capacity), and make pods start fast (small images, no warm-up work in startup, readiness that turns green as soon as the server listens).

### The floor and the ceiling

The floor (minReplicaCount 3, two on-demand nodes) exists for zone spread and for the first seconds of any spike, not for cost. The ceiling (maxReplicaCount 120, Karpenter CPU limit 216) exists because an app with no ceiling can scale until the database dies or the bill explodes; load that passes it is shed at the ingress with 503s, which is a better experience than timeouts everywhere. The same shape works outside Kubernetes: an EC2 Auto Scaling group with a target tracking policy on `ALBRequestCountPerTarget` set to 100 scales instances the way the HPA scales pods, with a default instance warmup so a booting instance does not count, scheduled actions for the sale instead of cron triggers, and a minimum and maximum size as the floor and ceiling. Its lag is longer, several minutes to boot and pass health checks, so pre-scaling matters more.

## Evaluation

**SLIs.** Requests per second per Ready pod (should hover near the 100 target during the ramp); p95 latency and error rate from the ingress; time from the first minute above 2,000 requests per second to Ready pods matching demand (target under 4 minutes); number of pending pods older than 60 seconds (target 0 outside sale starts); node count by capacity type.

**Load tests.** A step test from 300 to 10,000 requests per second in 2 minutes with no pre-scaling, to measure the real lag and the error rate during it; the same test with the cron trigger active 15 minutes earlier, which must pass the 0.5 percent error budget; a soak at 3,000 for one hour to confirm no scale-down flapping; a scale-down test that confirms no request fails as pods terminate (watch for 502s at the ingress).

**Chaos.** Terminate a spot node during the peak and confirm the PDB keeps 75 percent of pods available and Karpenter replaces the node; delete the KEDA operator and confirm the HPA keeps its last desired count (KEDA fallback can be set with `fallback.replicas`); block Prometheus and confirm the CPU trigger still scales.

**Cost review.** Monthly node-hours by capacity type and by NodePool; alert when the on-demand pool exceeds its limit or when spot share during a sale falls under 70 percent; compare the bill to the 341 USD estimate.

**Strong versus weak answer.** A weak answer sets an HPA on CPU at 80 percent and stops. A strong answer names the per-pod number from a load test, adds the delays per layer, explains why that sum forces pre-scaling, and protects the floor with rate limiting and a queue.

## Bottlenecks & mitigations

* The database: 100 web pods can open more connections than it accepts. Pool per pod, a proxy, and the queue in front of writes.
* Spot capacity in one zone during a sale: Karpenter may find no spot in a family or zone; allow several families and three zones and let the on-demand pool overflow.
* Metrics pipeline delay: a slow Prometheus or a long scrape interval adds directly to the lag.
* Image pull on new nodes: a 1 GB image adds 30 seconds per node; keep images small and use an ECR VPC endpoint.
* The ingress controller itself needs an HPA and its own capacity test, or it becomes the first thing to saturate.

## Failure modes

* **HPA scales on CPU only and never fires.** IO-bound pods sit at 40 percent CPU while latency doubles. Mitigation: requests-per-second trigger as primary, CPU as backstop.
* **Scale-down thrash after the peak.** Pods are removed, latency rises, pods are added, repeat. Mitigation: 10-minute scale-down stabilization, 25 percent per minute, tolerance left at 10 percent.
* **Pods terminated while receiving traffic.** 502s at the ingress during consolidation. Mitigation: preStop sleep, readiness probe, lower ALB deregistration delay, PDB.
* **Sale announced but the cron trigger has the wrong time zone.** The floor rises an hour late. Mitigation: `timezone` set explicitly on the trigger, a test that renders sales.yaml and asserts the window.
* **maxReplicas reached and traffic keeps growing.** Every request slows until everything times out. Mitigation: rate limit at the ingress, 503 with Retry-After, and a cached page for the sale landing route.
* **Karpenter removes a node during the evening peak.** Consolidation drains 3 pods while demand is highest. Mitigation: a disruption budget of 0 nodes during the peak window.
* **Fresh pods drag the CPU average down.** The HPA scales down right after scaling up. Mitigation: readiness probes that are honest, and the default CPU initialization period, which sets aside the CPU of pods that are not yet Ready during their first 5 minutes.
* **Spot interruption takes 5 nodes in one minute.** Capacity drops 15 percent mid-sale. Mitigation: three zones and several families, PDB, interruption queue so Karpenter launches replacements on the 2-minute notice.

## Follow-up questions interviewers ask

* The team wants to scale on p95 latency instead of requests per second. What goes wrong?
* The sale lands on a region where no spot capacity is available. What does Karpenter do, and what do you change?
* Replace Kubernetes with ECS on EC2 or an Auto Scaling group behind an ALB. Which parts of the design change and which stay?
* How would you right-size the pod's CPU request, and what does the Vertical Pod Autoscaler do to the HPA if both run at once?
* The worker Deployment scales on queue length. How do you stop it from overwhelming the database?
* Demand doubles every quarter. At what point does the ceiling move, and what proves the database can follow?

## Lessons that cover this

* [#11AWS core - IAM, VPC, EC2, S3, RDS, load balancers, autoscalingCloud and IaC](/devops/learn/aws-core-for-devops)
* [#12AWS managed platforms - EKS, ECS, Fargate, Lambda, SQS, ElastiCache, CloudFrontCloud and IaC](/devops/learn/aws-managed-platforms-eks-ecs)
* [#17Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKSKubernetes](/devops/learn/kubernetes-in-production)
* [#24Scaling and resilience - caching, queues, rate limiting, DDoS, DROperate](/devops/learn/scaling-and-resilience)
* [#27Cloud cost and FinOpsShip](/devops/learn/cloud-cost-and-finops)
* [#30GPU and ML infrastructure - serving models on KubernetesLater](/devops/learn/gpu-and-ml-infrastructure)

## Further reading

* [Kubernetes documentation: TasksGuidekubernetes.io](https://kubernetes.io/docs/tasks/)
* [KEDA documentationGuidekeda.sh](https://keda.sh/docs/)
* [Autopilot: Workload Autoscaling at Google ScalePaperresearch.google](https://research.google/pubs/autopilot-workload-autoscaling-at-google-scale/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousMulti-region disaster recovery with RPO 5 minutes and RTO 30 minutes](/devops/problems/multi-region-dr)[NextInternal developer platform and golden path](/devops/problems/internal-developer-platform)

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
