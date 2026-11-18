# Cut the AWS bill by 40 percent — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/cloud-cost-reduction

[DevOps problems](/devops#problems)

DESIGNPlatform design#17Medium

# Cut the AWS bill by 40 percent

finopsawskarpenterspotsavings-planscost-allocation

## Problem statement

A product company pays 90,000 USD per month to AWS: three EKS clusters (prod, staging, dev), RDS PostgreSQL, S3, data transfer, CloudWatch and the usual extras. Revenue is flat and leadership wants the bill down by 40 percent within one quarter, with no visible slowdown for users and no reliability incident caused by the savings. Nobody knows today which team or service spends what. Design the programme: how to measure, which levers to pull in which order, the arithmetic that reaches 40 percent, the governance that stops the bill from creeping back, and the risk of each lever.

## Requirements

### Functional

* Every dollar is attributed to a service, a team and an environment within the first two weeks, including shared Kubernetes nodes split per namespace.
* A ranked list of levers with the estimated saving, the effort and the reliability risk of each, approved by the platform and product leads.
* Compute, database, transfer, storage and observability levers applied in a sequence that never removes capacity before the data says it is unused.
* Commitment discounts (savings plans, reserved instances) bought only for the base that remains after right-sizing.
* Guardrails: budgets with alerts, cost estimates in every infrastructure pull request, a monthly showback per team.
* A report each week with the run-rate against the 54,000 USD target.

### Non-functional

* Monthly run-rate at or under 54,000 USD by the end of week 12 (40 percent of 90,000).
* No increase in p99 latency of the main API above 10 percent of today's value, measured weekly.
* No availability incident attributed to a cost change; error budget consumption stays under today's rate.
* Dev and staging environments available within 5 minutes when someone needs them outside working hours.
* Spot interruptions cause no failed user requests: only workloads with 3 or more replicas and PodDisruptionBudgets run on spot.
* Committed spend never exceeds 70 percent of the measured steady base, for at most 1 year.

## Back-of-the-envelope estimates

**Assumed breakdown of 90,000 USD.** EC2 for EKS nodes 40 percent = 36,000; RDS 18 percent = 16,200; data transfer and NAT 10 percent = 9,000; CloudWatch 7 percent = 6,300; S3 6 percent = 5,400; EBS volumes and snapshots 4 percent = 3,600; load balancers 3 percent = 2,700; ElastiCache, MSK and other 8 percent = 7,200; EKS control planes 1 percent = 900; support 3 percent = 2,700.

**Compute, in order, each applied to what is left.** Right-sizing requests from utilisation data: an assumed 20 percent of 36,000 = 7,200, leaving 28,800. Karpenter consolidation: 10 percent of 28,800 = 2,880, leaving 25,920. Spot for the stateless half, 12,960, at an assumed 60 percent discount: 7,776, leaving 18,144. Dev and staging are 25 percent of that, 4,536, and switching them off nights and weekends removes 60 percent of their hours: 2,722, leaving 15,422. A compute savings plan on 70 percent of what remains, 10,796, at an assumed 30 percent discount: 3,239. Compute saving: 7,200 + 2,880 + 7,776 + 2,722 + 3,239 = 23,817.

**Database.** Right-sizing two oversized instances and moving io1 to gp3: 25 percent of 16,200 = 4,050. Reserved instances on the remaining 12,150 at an assumed 35 percent: 4,253.

**The rest.** VPC endpoints and same-zone routing: 50 percent of 9,000 = 4,500. CloudWatch retention to 30 days plus dropping debug logs: 50 percent of 6,300 = 3,150. S3 lifecycle and intelligent tiering: 40 percent of 5,400 = 2,160. Unattached volumes and snapshots older than 90 days: 30 percent of 3,600 = 1,080. Idle load balancers: 30 percent of 2,700 = 810.

**Total.** 23,817 + 4,050 + 4,253 + 4,500 + 3,150 + 2,160 + 1,080 + 810 = 43,820 USD, 48.7 percent. The target is 36,000; the 7,820 of headroom covers levers that disappoint. Every percentage is an assumption until Cost Explorer and OpenCost replace it in week 2.

## API

```
Week 1 to 2: measure
  Cost Explorer grouped by service, then by tag team / env / service  (activate cost allocation tags)
  AWS Cost and Usage Report -> Athena for per-resource queries
  OpenCost (or Kubecost) in each cluster: cost per namespace = node cost x share of requests
  Prometheus: container_cpu_usage vs kube_pod_container_resource_requests, 14-day p95
  Output: a sheet with one row per service: monthly cost, p95 CPU and memory use vs requests, owner

Levers, as pull requests in the infra and GitOps repos
  right-size:        Helm values requests.cpu / requests.memory set to p95 use x 1.3
  consolidation:     Karpenter NodePool spec.disruption.consolidationPolicy: WhenEmptyOrUnderutilized
                     consolidateAfter: 1m; budgets: nodes "10%" always, "0" with schedule "30 3 * * 1-5" duration 9h
                     (cron is UTC: 09:00 to 18:00 IST) on prod
  spot:              NodePool general-spot, karpenter.sh/capacity-type: ["spot"], only for Deployments with
                     replicas >= 3, a PDB, and no local state; others carry nodeSelector on-demand
  scale-to-zero:     CronJob 20:00 IST scales dev and staging Deployments to 0 and NodePool limits to 0,
                     07:00 scales back; a Slack command runs the "up" job on demand (5 minutes)
  savings plan:      Compute Savings Plan, 1 year, no upfront, hourly commitment = 70% of the lowest
                     hourly on-demand spend observed in the 30 days after right-sizing
  rds:               instance class down one size where p95 CPU < 30%; io1 -> gp3; 1-year reserved
  transfer:          VPC gateway endpoint for S3, interface endpoints for ECR, STS, CloudWatch;
                     Service spec.trafficDistribution: PreferSameZone; pods and nodes in the same AZ as RDS
  cloudwatch:        retention 30 days (prod), 7 days (dev); drop DEBUG at the OTel collector; delete
                     unused metric filters and custom metrics
  s3:                lifecycle: STANDARD -> INTELLIGENT_TIERING at 30 days, expire incomplete uploads
  cleanup:           script lists EBS volumes with state available and snapshots older than 90 days
                     without a tag keep=true; ALBs with zero healthy targets for 14 days

Governance
  AWS Budgets: per account, alert at 80% and 100% of 54,000 and forecast
  Infracost in GitHub Actions: cost diff comment on every Terraform PR; fail if monthly delta > 500 USD
  Kyverno: every Deployment needs requests and the labels team, service, env
  Showback: monthly OpenCost report per team posted to their channel; review meeting on the first Monday
```

## Data model

```
Cost allocation
  tags on every AWS resource     team, service, env, cost-center   (enforced by a Config rule and tagging policy)
  Kubernetes labels               team, service, env on every namespace and Deployment (Kyverno enforced)
  OpenCost mapping                namespace -> team; shared costs (ingress, observability) split by request share

Cluster layout after the programme (prod)
  NodePool system          on-demand, 3 x m6i.large, taint CriticalAddonsOnly
  NodePool general-od      on-demand, m6i/m6a/c6i, consolidation on, budget 10%, covered by savings plan
  NodePool general-spot    spot, same families plus m5/c5 for diversity, consolidation on
  Workload rules           spot-eligible: replicas >= 3, PDB minAvailable 2, no PVC, startup under 60 s
                           on-demand only: StatefulSets, Jobs over 10 min, anything with a PVC

Levers and risk register
  lever                        est. saving   risk to latency or reliability            guard
  right-sizing requests        7,200         OOMKills if memory set too low              p95 x 1.3, limits unchanged, alert on OOM
  Karpenter consolidation      2,880         pods evicted during peak                    budgets 0 in business hours, PDBs
  spot for stateless           7,776         interruptions, capacity gaps in one type    6 families, 3 AZs, PDBs, on-demand fallback
  dev and staging off-hours    2,722         someone works late                          one-command "up", 5 min
  compute savings plan         3,239         over-commit after further shrink            70% of base, 1 year, no upfront
  RDS right-size and gp3       4,050         CPU spikes on the smaller class             do it on the replica first, watch 2 weeks
  RDS reserved                 4,253         locked to a class                           after the right-size, 1 year
  endpoints and PreferSameZone   4,500         imbalanced load across AZs                  watch per-AZ error rates
  CloudWatch retention         3,150         logs missing for an old incident            archive to S3 before expiry
  S3 lifecycle                 2,160         retrieval cost on cold data                 intelligent tiering, not Glacier, first
  volumes, snapshots, ALBs     1,890         deleting something in use                   tag keep=true, 14-day quarantine

Monthly review table  cost_review(month, team, cost_usd, delta_pct, top_3_services, action_owner)
```

## High-level design

**Weeks 1 to 2: measure before touching anything**

1. Activate cost allocation tags and a tagging policy; tag everything that exists with a script and a Config rule that flags untagged resources. Pull Cost Explorer by service and by tag; load the Cost and Usage Report into Athena for per-resource questions.
2. Install OpenCost in each cluster and map namespaces to teams. Build the sheet of every service with cost and 14-day p95 use against requests. Publish the first showback: most teams have never seen their number.

**Weeks 3 to 5: the safe levers**

3. Delete unattached EBS volumes, snapshots older than 90 days without a keep tag, and load balancers with no healthy targets, each after a 14-day quarantine (tag, wait, delete).
4. Set CloudWatch log retention, drop debug logs at the OpenTelemetry collector, remove dead metric filters; add S3 lifecycle rules; add the S3 gateway endpoint and ECR interface endpoints, which also remove a reliability dependency on NAT.
5. Right-size requests from the sheet, team by team, one PR per service, limits unchanged, with an OOMKill alert on.

**Weeks 6 to 8: compute shape**

6. Turn on Karpenter consolidation with `WhenEmptyOrUnderutilized`, budgets that allow 10 percent of nodes to be disrupted and 0 percent during business hours in prod. Require PDBs by policy first.
7. Move eligible stateless services to the spot NodePool with six instance families across three zones and `karpenter.sh/do-not-disrupt` on the few pods that must not move; Karpenter drains on the two-minute interruption notice.
8. Schedule dev and staging to zero at night and weekends with a one-command "up"; set `trafficDistribution: PreferSameZone` on chatty services and pin latency-sensitive pods to the database's zone.

**Weeks 9 to 10: database**

9. Downsize the RDS replica first, watch two weeks of p95 CPU and latency, then the primary in a maintenance window; convert io1 to gp3.

**Weeks 11 to 12: commit to what is left**

10. Only now buy a one-year, no-upfront compute savings plan for 70 percent of the lowest observed hourly on-demand spend, and reserved instances for the right-sized RDS classes.
11. Switch on the guardrails: budgets with alerts at 80 and 100 percent of 54,000, Infracost comments on every Terraform PR with a failure above a 500 USD monthly delta, Kyverno requiring labels and requests, and a monthly review where each team explains its delta.

## Architecture diagram

Rendering diagram…

## Deep dives

### Commitment discounts and the risk of over-committing

A savings plan is a promise to spend a fixed number of dollars per hour on compute for one or three years; AWS discounts the usage that fits inside the promise and bills the rest at on-demand. The discount is real only while the promise is used. Buy it in week 1 for today's 36,000 USD of nodes, then right-size and move to spot, and half the commitment pays for nothing. That is why commitments come last in the sequence and cover only 70 percent of the lowest hourly on-demand spend observed after every other lever, for one year, no upfront. Spot usage is not covered by savings plans, so the commitment is sized on the on-demand pools alone. RDS reserved instances are tied to an instance class and engine, so the right-sizing must finish before they are bought. The review each quarter checks utilisation of the commitment; below 90 percent means the next purchase waits.

### Spot interruptions and what can tolerate them

Spot capacity is spare capacity sold at a discount that AWS reclaims with a two-minute warning. The discount is large, often more than half, and the interruption is the price. A workload tolerates it when losing one pod is routine: three or more replicas, a PodDisruptionBudget that keeps two available, no local state, start-up under a minute, and idempotent work. Karpenter watches the interruption queue, cordons and drains the node on the warning, and launches a replacement; with six instance families across three zones a shortage in one pool is covered by another. What does not belong on spot: StatefulSets, databases, Kafka brokers, long Jobs without checkpoints, and anything with one replica. The first week of spot runs with a canary namespace while the dashboard shows interruption rate, pod restart count and p99; if interruptions cluster in one family, that family leaves the pool.

### Data transfer, the hidden line

Transfer is rarely a budget line anyone owns, which is why it is 10 percent here. Three sources dominate: NAT gateway data processing for every byte that leaves the VPC, including image pulls from ECR and writes to S3; cross-zone traffic between pods in different zones and between pods and the database; and traffic to the internet. A gateway endpoint for S3 is free and moves S3 traffic off NAT; interface endpoints for ECR, STS and CloudWatch cost a little per hour and per GB but far less than NAT. `trafficDistribution: PreferSameZone` on a Service keeps calls inside the zone when healthy endpoints exist there; pinning the chattiest consumers to the database's zone removes the largest cross-zone flow at the cost of zone balance. The Cost and Usage Report with `usage_type` filtered on `DataTransfer-Regional-Bytes` and `NatGateway-Bytes` tells you which it is before you guess.

### Keeping the savings from eroding

Every cost programme without guardrails returns to its old bill within a year: new services ship with generous requests, somebody turns consolidation off after a scary eviction, logs grow back. The guardrails make the default cheap. Kyverno refuses a Deployment without requests and labels, so nothing lands untagged or unbounded. Infracost puts the monthly cost of every Terraform change in the pull request and fails it above a threshold, so the reviewer sees the number before approval. Budgets alert at 80 percent of the target with a forecast. The monthly showback gives each team its own number and its delta; the review meeting asks only one question per team: what changed. And the platform team keeps one dashboard: run-rate, spot share, savings plan utilisation, untagged spend, each with a threshold and an owner.

## Evaluation

**Cost SLIs.** Monthly run-rate against 54,000 USD, reported weekly; untagged spend under 2 percent; spot share of general compute above 40 percent; savings plan utilisation above 90 percent; cost per 1,000 requests, which is the number that should fall while traffic stays flat.

**Reliability SLIs checked against each lever.** p99 latency of the main API within 10 percent of the baseline; error budget burn rate unchanged; OOMKills per day (rises after right-sizing mean a request was cut too far); spot interruptions per day and pods failing readiness after a move; per-zone error rate after `PreferSameZone`.

**Tests.** Before the spot move, kill a spot node under load and confirm no failed requests. After consolidation is on, run a peak-hour load test and confirm no evictions. After scale-to-zero, time the "up" command from Slack to ready pods (under 5 minutes). After the RDS downsize, replay a day of production queries against the replica.

**Security checks.** The cleanup script runs in dry-run first and deletes only resources with the quarantine tag older than 14 days; VPC endpoints carry policies limited to the company's buckets and registries; retention changes archive logs to S3 before expiry so an audit can still be answered.

**What a strong answer adds.** The candidate measures first, orders levers by risk, refuses to buy commitments before shrinking, knows what cannot go on spot, names transfer as a real line and ends with guardrails. A weak answer starts with a three-year savings plan.

## Bottlenecks & mitigations

* Tagging coverage: until the sheet attributes more than 95 percent of spend, every saving estimate is a guess and showback has no credibility.
* Team capacity: right-sizing is one PR per service and the platform team cannot write 60 of them; the sheet and a template make it a team task.
* Business-hours consolidation budget of 0 means nodes freed during the day are reclaimed only at night, delaying the saving by hours.
* Spot capacity for large instance types in one region is limited; too few families in the NodePool means fallback to on-demand and a smaller saving.
* Log retention cuts are capped by compliance: audit and access logs may need a year, so they move to S3 instead of being deleted.

## Failure modes

* **Savings plan bought on the pre-shrink base.** Half of it is unused for a year. Mitigation: commitments last, 70 percent of the measured base, one year.
* **Right-sizing memory too low.** OOMKills in production at peak. Mitigation: p95 x 1.3 with limits unchanged, OOMKill alert, one service at a time.
* **Consolidation evicts pods at peak.** Users see errors. Mitigation: disruption budgets of 0 in business hours, PDBs required.
* **A spot family runs out across all zones.** Pods pending. Mitigation: six families, on-demand NodePool as fallback with a lower weight, alert on pending pods over 2 minutes.
* **Staging is off when an incident needs a repro at 23:00.** Mitigation: one-command "up" in 5 minutes, documented in the on-call runbook.
* **Cleanup deletes a volume somebody needed.** Data lost. Mitigation: quarantine tag and 14-day wait, snapshot before delete, keep tag honoured.
* **RDS downsized, then month-end batch jobs spike CPU.** Reports fail. Mitigation: downsize the replica first, watch a full month including the batch window.
* **Logs needed for an old incident were expired.** Mitigation: export to S3 with lifecycle to cold storage before shortening retention.

## Follow-up questions interviewers ask

* Traffic doubles next year. Which savings scale with it and which are one-off?
* The company has three AWS accounts and shared services. How do you split the ingress, observability and NAT cost fairly?
* Leadership now wants 60 percent. Which levers are left and what would you have to give up?
* A team refuses to move to spot. How do you decide if they are right?
* How would you design a unit cost metric (cost per order, per active user) and what does it tell you that the total does not?
* Would you consider Graviton (ARM) nodes, and what does the migration cost in engineering time?

## Lessons that cover this

* [#11AWS core - IAM, VPC, EC2, S3, RDS, load balancers, autoscalingCloud and IaC](/devops/learn/aws-core-for-devops)
* [#12AWS managed platforms - EKS, ECS, Fargate, Lambda, SQS, ElastiCache, CloudFrontCloud and IaC](/devops/learn/aws-managed-platforms-eks-ecs)
* [#27Cloud cost and FinOpsShip](/devops/learn/cloud-cost-and-finops)

## Further reading

* [FinOps Framework OverviewGuidefinops.org](https://www.finops.org/framework/)
* [Infracost documentation: Get startedGuideinfracost.io](https://www.infracost.io/docs/)
* [AWS Well-Architected FrameworkGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousZero-downtime database schema migration and cutover](/devops/problems/zero-downtime-db-migration)[NextGPU inference platform on EKS for OpenAI-compatible LLM serving](/devops/problems/gpu-inference-platform)

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
