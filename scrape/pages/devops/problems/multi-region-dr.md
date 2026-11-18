# Multi-region disaster recovery with RPO 5 minutes and RTO 30 minutes — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/multi-region-dr

[DevOps problems](/devops#problems)

DESIGNPlatform design#7Hard

# Multi-region disaster recovery with RPO 5 minutes and RTO 30 minutes

disaster-recoverymulti-regionauroraroute53argocdaws

## Problem statement

An e-commerce platform runs in ap-south-1 (Mumbai): an EKS cluster with 60 nodes, Aurora PostgreSQL, ElastiCache for Redis, and S3 for product images and order documents, at 2,000 requests per second. The business has set a recovery point objective (RPO) of 5 minutes and a recovery time objective (RTO) of 30 minutes for the loss of the whole region. Design the second-region setup, the replication of every piece of state, the failover and failback procedure, who decides, and how you prove it works before the day it is needed.

## Requirements

### Functional

* A second region can serve all customer traffic, with reads and writes, after a regional failure of ap-south-1.
* Every stateful component is replicated: Aurora, S3 objects, container images, secrets, and the cache either replicated or rebuilt.
* The standby EKS cluster runs the same application versions as production at all times, deployed from the same GitOps repository.
* A written failover runbook with decision criteria, a named decision maker and a single command or pipeline that executes it.
* Failback to the primary region without data loss once it recovers.
* A DR drill at least quarterly, with the measured RPO and RTO reported to the business.

### Non-functional

* RPO 5 minutes: at most 5 minutes of committed orders lost in the worst case.
* RTO 30 minutes: customers can place orders in the second region within 30 minutes of the decision to fail over, including DNS.
* Standby cost at most 35 percent of the primary region's monthly cost.
* Aurora replication lag alert at 60 seconds, page at 120 seconds, so the RPO is never silently violated.
* Standby cluster scales from 30 percent to 100 percent of primary capacity within 15 minutes.
* No single human is a dependency: two named roles can each start the failover.

## Back-of-the-envelope estimates

**Change rate.** 2,000 requests per second with 15 percent writes = 300 writes per second. At about 2 KB of row and index change each, that is 614 KB per second, 37 MB per minute, and 184 MB inside a 5-minute RPO window. The AWS documentation says Aurora Global Database replicates with latency typically under a second, far below the budget; the alert at 60 seconds and the page at 120 seconds leave 3 minutes to act before the RPO is at risk.

**RTO budget (30 minutes).** Detection by health checks and the on-call engineer: 90 seconds. Confirming it is a regional failure, not an application bug: 5 minutes. The decision call: 5 minutes. Aurora managed failover, which the documentation says completes in the order of minutes: budget 5 minutes. Route 53 failover with a 60-second TTL: 3 failed checks x 30 seconds plus one TTL = 150 seconds, 2.5 minutes. Standby cluster scaling from 18 to 60 nodes with Karpenter: 5 minutes. Smoke test and announcement: 3 minutes. Total 27 minutes, 3 minutes of slack. Every step must be a script.

**Standby size.** 30 percent of 60 m6i.xlarge nodes = 18 nodes. At an assumed 0.192 USD per hour: primary 60 x 0.192 x 730 = 8,410 USD, standby 18 x 0.192 x 730 = 2,523 USD.

**Monthly cost (assumed prices).** Primary: nodes 8,410, Aurora 2 instances at 1.00 USD per hour = 1,460, ElastiCache 2 nodes at 0.25 USD per hour = 365, S3 2 TB at 0.023 USD per GB = 46, EKS control plane 73; total 10,354 USD. Warm standby: nodes 2,523, one Aurora secondary instance 730, one cache node 183, replica S3 plus 200 GB of replication transfer at 0.02 USD per GB = 50, control plane 73; total 3,558 USD, 34 percent of primary. Pilot light (Aurora secondary and S3 only): 853 USD, 8 percent, but RTO grows past an hour. Active-active: about 100 percent plus engineering cost.

**Drills.** Quarterly, each about 2 hours of 6 people.

## API

```
How the platform is operated across regions:

repo platform-gitops/
  clusters/
    prod-mumbai/      values: region ap-south-1, aurora endpoint writer.mumbai, replicas 3, role primary
    prod-singapore/   values: region ap-southeast-1, aurora endpoint writer.singapore, replicas 1, role standby
  apps/<service>/     one chart; region differences come only from the cluster values file
  ApplicationSet with a cluster generator: label region=<r>, role=<primary|standby>

repo platform-infra/  (Terraform, one module, two instantiations)
  module "region" { source = "./modules/region"; region = "ap-south-1";     is_primary = true  }
  module "region" { source = "./modules/region"; region = "ap-southeast-1"; is_primary = false }
  aws_rds_global_cluster, aws_s3_bucket_replication_configuration, aws_ecr_replication_configuration,
  aws_route53_health_check, aws_route53_record (failover PRIMARY and SECONDARY)

Failover pipeline (GitHub Actions, workflow_dispatch, requires two approvals from the DR approvers group)
  inputs: target_region, reason, ticket
  1. aws rds failover-global-cluster --global-cluster-identifier shop-global \
       --target-db-cluster-identifier arn:aws:rds:ap-southeast-1:...:cluster:shop-singapore \
       --allow-data-loss                      # unplanned: do not wait for sync
  2. aws route53 change-resource-record-sets  # flip failover record if health check has not already
  3. kubectl --context singapore scale: Karpenter NodePool limits raised, HPA minReplicas to primary values
  4. promote ElastiCache Global Datastore secondary (or accept an empty cache and warm it)
  5. smoke test: place a test order, read it back from Singapore
  6. post the timeline to the incident channel

Planned switchover (drills, no data loss):
  aws rds switchover-global-cluster --global-cluster-identifier shop-global \
    --target-db-cluster-identifier arn:aws:rds:ap-southeast-1:...:cluster:shop-singapore

Decision criteria (any one is enough to start the call; two of them to fail over):
  - Route 53 health check for the Mumbai ALB failing for 3 minutes
  - AWS Health Dashboard event for ap-south-1 affecting EC2, EKS or RDS
  - Aurora writer unreachable from a second region for 3 minutes
  - Error rate above 50 percent for 5 minutes with no deploy in the last hour
Decides: the on-call incident commander; the head of engineering is informed, not asked.
```

## Data model

```
Region ap-south-1 (primary)                    Region ap-southeast-1 (warm standby)
  EKS prod-mumbai, 60 nodes, 3 AZs              EKS prod-singapore, 18 nodes, 3 AZs, same add-ons
  Aurora PostgreSQL global cluster shop-global
    primary cluster shop-mumbai, writer + 1 reader
                                                 secondary cluster shop-singapore, 1 reader instance
                                                 metric AuroraGlobalDBRPOLag (ms) alarms at 60 s and 120 s
                                                 rds.global_db_rpo left at default in the secondary
  ElastiCache Global Datastore shop-cache
    primary replication group                   secondary replication group, async replication
  S3 shop-media (versioning on)                 S3 shop-media-sg, replication with RTC, 15 min threshold
    orders documents written with the region in the key prefix to avoid replication loops
  ECR private registry, replication rule         ECR same repository names, images replicated on push
    ap-south-1 -> ap-southeast-1
  Secrets Manager prod/* with replica region     replica secrets, same name, rotation follows primary
  Route 53 hosted zone shop.example
    shop.example  failover PRIMARY   alias -> Mumbai ALB,     health check hc-mumbai, evaluate target health
    shop.example  failover SECONDARY alias -> Singapore ALB
    api.shop.example  A record TTL 60 (not alias) so the TTL is ours to set
    hc-mumbai: HTTPS /healthz/deep, interval 30 s (10 s during a drill), failure threshold 3
  Health endpoint /healthz/deep: checks Aurora writer, cache, S3 in-region; returns 503 if the writer is gone

Argo CD (runs in both regions, each watches only its own cluster folder)
  ApplicationSet "apps" cluster generator, label region; values file per cluster
  Application "dr-config" holds region values: endpoints, replica counts, feature flags
Terraform state: S3 bucket in us-west-2 with replication, so state survives either region
```

## High-level design

**Choose the strategy**

1. Pick warm standby: a reduced copy of everything that is always running and always deployed. Pilot light (data only) cannot meet a 30-minute RTO once cluster creation and image pulls are counted. Active-active would need multi-writer data design that this platform does not have.

**Replicate every piece of state**

2. Convert the Aurora cluster to an Aurora Global Database with a secondary cluster in ap-southeast-1, chosen after confirming in the AWS region table that Global Database supports the engine version there. Alarm on `AuroraGlobalDBRPOLag`.
3. Turn on S3 versioning and cross-region replication with Replication Time Control on the media and documents buckets, and alert on the `OperationMissedThreshold` event.
4. Configure ECR private registry replication to the standby region so every image pushed by CI exists in both; deployments reference the regional registry through a value.
5. Replicate production secrets with Secrets Manager multi-Region secrets; the External Secrets Operator in each cluster reads the local replica.
6. Create an ElastiCache Global Datastore, or decide to accept cache loss: sessions are stored in Aurora anyway, so the cache only needs warming. The design keeps a small secondary for the product catalogue cache.

**Keep the standby cluster identical**

7. Create both clusters from the same Terraform module with `is_primary` as the only difference. Argo CD in each region syncs the same applications from the same Git commit; the ApplicationSet cluster generator injects region values such as endpoints and replica counts.

**Make failover a decision plus one pipeline**

8. Route 53 failover records with a deep health check move customer traffic automatically when the Mumbai ALB fails the check. The database and cache promotion are deliberate, run by a GitHub Actions workflow that needs two approvals and executes the steps in order.
9. The runbook names the incident commander as the decision maker and lists the criteria. Drills run the planned `switchover-global-cluster` path, which the documentation describes as zero data loss.

**Failback and prove it**

10. After the primary recovers, Aurora rebuilds it as a secondary; failback is a planned switchover at a quiet hour, then DNS back. Quarterly drill: fail over, serve real traffic from the standby for one hour, fail back, publish measured RPO and RTO.

## Architecture diagram

Rendering diagram…

## Deep dives

### RPO and RTO with the arithmetic

RPO is how much data you may lose, measured in time: with an RPO of 5 minutes, the last committed order you can lose was committed less than 5 minutes before the failure. RTO is how long the service may be unavailable, counted from the failure to customers placing orders again. The two are set by the business, not by engineers, and each costs money. The arithmetic for RPO is replication lag: at 300 writes per second and lag under a second, the lost window is about 300 rows in the normal case, and the alarm at 120 seconds gives time to act if lag grows. Aurora PostgreSQL also has an `rds.global_db_rpo` parameter that blocks commits when every secondary is further behind than the limit; the documentation warns that with only two regions it should stay at the default in the secondary, otherwise a failover could pause transactions. The RTO arithmetic is a sum of steps with slack, 27 minutes against 30, which is why the design refuses manual steps: a 10-minute search for the right runbook page breaks the budget on its own.

### Aurora Global Database failover and promotion

There are two operations and they must not be confused. Switchover (the older name was managed planned failover) is for a healthy global database: Aurora waits until the secondary is fully synchronised, then swaps roles, and the documentation states the RPO is 0 and the read/write recovery is typically under 30 seconds on qualifying engine versions. Drills and failback use it. Failover is for the outage case: `failover-global-cluster --allow-data-loss` promotes the chosen secondary without waiting, so the documentation says the RPO is typically a non-zero value measured in seconds, and the RTO is in the order of minutes. If managed failover is impossible, for example when engine versions differ, the manual path is to detach the secondary, which promotes it to a standalone cluster, point writes at it, and later add the old region back. After an unplanned failover Aurora rebuilds the old primary as a secondary and tries to snapshot its storage; that snapshot is how a reconciliation job can find orders committed in Mumbai in the last seconds that never reached Singapore.

### DNS failover and client caching

Route 53 health checkers in many locations call the deep health endpoint every 30 seconds; with a failure threshold of 3 the record flips about 90 seconds after the endpoint dies. Then every resolver on the internet must notice. A resolver caches the answer for the TTL, so a 60-second TTL bounds the delay to about 2.5 minutes in total. Three things break this. Alias records to an ALB cannot set a TTL; the Elastic Load Balancing documentation says the load balancer's DNS entry uses 60 seconds, which is acceptable, but a plain A record is used for the API name so the value is ours. Some corporate resolvers and some mobile apps ignore TTLs and cache for hours, so the mobile client has a retry rule: on connection failure, re-resolve and try again. Long-lived connections (WebSockets, HTTP/2 keep-alive) never re-resolve, so the Mumbai ALB must be deleted or its listeners disabled when it is unreachable anyway, and the health endpoint returns 503 the moment the writer is gone, which also prevents the split brain: a Mumbai cluster that is alive but cut off from its database must not accept orders.

### Why not active-active

Active-active means both regions take writes all the time. It would remove the failover decision and the standby cost, but it needs a data layer that accepts writes in two places: either a multi-writer database with conflict rules (which Aurora Global Database does not offer for PostgreSQL), or application-level partitioning where each customer or order is pinned to one region and the other region only forwards, or a write-through design on DynamoDB global tables with last-writer-wins conflicts. For an order system, last-writer-wins can lose a payment confirmation. It also doubles the compute bill and every schema change must be safe in two regions at once. The honest trade: warm standby costs 34 percent of primary and a few minutes of lost orders in a real disaster, active-active costs 100 percent plus a re-architecture. The business chose the 30-minute RTO, so warm standby is the design, with a note that the catalogue (read-only) could be served from both regions today.

## Evaluation

**SLIs.** Replication lag: `AuroraGlobalDBRPOLag` p99 per hour, target under 5 seconds, alarm at 60 seconds. S3 replication: objects past the 15-minute threshold per day, target 0. Image parity: a nightly job lists image digests in both registries and alerts on any missing. Deployment parity: Argo CD reports both clusters synced to the same commit; alert if they differ for more than 15 minutes. Secret parity: a nightly comparison of secret version ids across regions.

**DR drill plan.** Quarterly, announced one week ahead, in the lowest-traffic hour. Step 1: freeze deploys. Step 2: run the planned switchover pipeline and start a stopwatch. Step 3: measure time to first successful order in Singapore (the RTO) and compare the last Mumbai order id with the first Singapore read (the RPO, expected 0 for a switchover). Step 4: serve real traffic for 60 minutes and watch error rate and latency, which will be higher for Indian customers because of the extra distance. Step 5: switch back. Step 6: publish the two numbers to the business. Once a year, run an unplanned drill: block the Mumbai ALB with a security group and let the on-call engineer find out through alerts.

**Chaos tests.** Stop the Aurora writer instance and confirm the deep health check fails within 60 seconds. Delete the Argo CD pods in Singapore and confirm the cluster keeps serving. Replace the Mumbai ECR with an empty repository in a test account and confirm Singapore pulls still work.

**Cost review.** Monthly standby cost as a percentage of primary, target under 35; alert if standby nodes stay at the scaled-up size after a drill.

**Security checks.** The failover workflow needs two approvers; IAM roles for the pipeline exist in both regions; KMS keys for Secrets Manager replicas and Aurora are multi-Region keys reviewed each quarter.

## Bottlenecks & mitigations

* Aurora failover is the longest serial step and cannot be parallelised with scaling; start the cluster scale-up before the promotion completes.
* Karpenter scaling 18 to 60 nodes depends on EC2 capacity in the standby region at that moment; keep On-Demand Capacity Reservations for the first 20 extra nodes.
* Image pull storms on new nodes; use a large base image cache or pre-pulled AMIs.
* DNS TTL is bounded below by resolvers that ignore it; the client retry rule matters more than the TTL.
* The decision step is human; a vague criteria list turns 5 minutes into 30.

## Failure modes

* **Split brain.** Mumbai comes back and its old writer accepts orders that Singapore never sees. Mitigation: the deep health check returns 503 when the cluster is not the global primary, Aurora fencing on failover, and a reconciliation job that reads the post-failover snapshot.
* **Standby is stale.** A config change was applied by hand in Mumbai only. Mitigation: no manual changes, Argo CD parity alert, drills that would expose it.
* **Replication lag grows silently.** A bulk import pushes lag past the RPO. Mitigation: alarm at 60 seconds, page at 120 seconds, bulk jobs throttled.
* **Secrets missing in the standby.** A new secret was created without the replica region. Mitigation: the platform CLI always adds the replica; nightly parity check.
* **Images missing in the standby.** Replication was configured after the images were pushed. Mitigation: ECR replication backfill once, nightly digest comparison.
* **Standby cannot get capacity.** EC2 insufficient capacity in ap-southeast-1 during the failover. Mitigation: capacity reservations, multiple instance families in the NodePool, 3 AZs.
* **Drill never happens.** The quarter is busy and the standby decays. Mitigation: the drill is a calendar event owned by the SRE lead and the RTO number is reported to the board.
* **Failback loses data.** Someone fails back with an unplanned failover instead of a switchover. Mitigation: the failback pipeline only offers `switchover-global-cluster`.

## Follow-up questions interviewers ask

* The business lowers the RPO to zero. What changes, and what does it cost in write latency?
* How would you serve Indian customers from Mumbai and Singapore at the same time for reads only?
* Route 53 itself is a global service, but what if the health checks are flapping? How do you stop a DNS ping-pong?
* Design the reconciliation job that finds orders committed in Mumbai in the last seconds before the failover.
* The company adds a Kafka cluster in Mumbai. How does the DR design change?
* How does Application Recovery Controller change the failover decision, and would you use it?

## Lessons that cover this

* [#11AWS core - IAM, VPC, EC2, S3, RDS, load balancers, autoscalingCloud and IaC](/devops/learn/aws-core-for-devops)
* [#24Scaling and resilience - caching, queues, rate limiting, DDoS, DROperate](/devops/learn/scaling-and-resilience)

## Further reading

* [AWS Well-Architected FrameworkGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
* [Argo CD documentationGuideargo-cd.readthedocs.io](https://argo-cd.readthedocs.io/en/stable/)
* [Chaos EngineeringPaperarxiv.org](https://arxiv.org/abs/1702.05843)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousSecrets management across CI, Kubernetes and runtime](/devops/problems/secrets-management)[NextAutoscaling for a web app: ASG, HPA and cluster autoscaling](/devops/problems/autoscaling-web-app)

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
