# Cloud cost and FinOps — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/cloud-cost-and-finops

[DevOps roadmap](/devops)

ShipLesson #27SkimIntermediate 1.5 h

# Cloud cost and FinOps

FinOps is the practice of treating cloud spend as an engineering signal: measure it, attribute it to teams, and lower it with the same discipline you apply to latency or error rate. This lesson shows where an AWS bill for a Kubernetes platform goes, the levers in order of impact, how to allocate cost to teams, which tools to name, and how to put a cost check into every Terraform pull request.

finopsaws costspotsavings planskarpenterright-sizingunit economics

## Why it matters

Cost questions now appear in platform and SRE interviews as often as scaling questions: "the bill doubled, what do you look at first", "spot or savings plan", "how would you charge teams for a shared cluster". At work, the engineer who can show a chart of cost per request and a plan to cut 30 percent gets trusted with bigger systems. The arithmetic is simple. What interviewers test is whether you know the levers, their order, and what each one commits you to.

Read first: [AWS core - IAM, VPC, EC2, S3, RDS, load balancers, autoscaling](/devops/learn/aws-core-for-devops), [Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKS](/devops/learn/kubernetes-in-production), [Terraform - infrastructure as code](/devops/learn/terraform-infrastructure-as-code)

## Lesson

### Cost is a signal, not an invoice

The FinOps Foundation framework describes three phases that repeat: **Inform** (see the spend, allocate it, forecast it), **Optimize** (right-size, commit, remove waste) and **Operate** (make it routine: budgets, reviews, policies). The idea an interviewer wants to hear is that cost moves with usage, so it must be watched like a metric: a budget alert is an alert, a cost spike has a root cause, and a postmortem can be written for a 40 percent overrun just as for an outage.

### Where the bill goes for a Kubernetes platform

A typical EKS platform bill, with assumed shares for a mid-sized team, looks like this:

| Line | Assumed share | What drives it |
| --- | --- | --- |
| EC2 compute (nodes) | 45% | Node count and size, on-demand vs spot vs committed |
| Managed databases (RDS, Aurora, ElastiCache) | 18% | Instance class, Multi-AZ, storage, backups |
| Data transfer and NAT | 10% | NAT Gateway per GB processed, cross-AZ traffic, internet egress |
| Observability ingest (CloudWatch, Prometheus storage, log vendor) | 9% | Log volume in GB per day, metric cardinality, retention |
| Storage (EBS, S3, snapshots) | 8% | Orphaned volumes, old snapshots, S3 without lifecycle rules |
| Load balancers (ALB, NLB) | 5% | Hourly charge per balancer plus capacity units |
| EKS control plane, Secrets Manager, KMS, misc | 5% | Flat fees and per-call charges |

Compute is the largest line, so it gets attention first, but the three "quiet" lines (NAT, logs, snapshots) are the ones that grow without anyone deciding to grow them.

### The levers, in order of impact

1. **Right-size from measured usage.** Compare `kubectl top` and Prometheus `container_cpu_usage_seconds_total` with requests. Nodes are sized by the sum of requests, so over-requested pods waste whole nodes. Aim for 60 to 70 percent average utilisation.
2. **Autoscale, and scale non-prod to zero.** HPA on pods, Karpenter or Cluster Autoscaler on nodes, and a CronJob or Karpenter NodePool limits that scale dev and staging to zero at night and on weekends. A dev cluster idle 128 of 168 hours a week costs 76 percent for nothing.
3. **Spot and commitments.** Spot gives up to 90 percent off on-demand (AWS's stated maximum) with a two-minute interruption notice; use it for stateless, replicated workloads. A **Compute Savings Plan** commits to a spend per hour for 1 or 3 years and applies across instance family, size, Region, OS and Fargate and Lambda (AWS states up to 66 percent off). An **EC2 Instance Savings Plan** commits to one instance family in one Region for up to 72 percent. **Reserved Instances** commit to a specific instance type and are the oldest and least flexible option. Commit only to the baseline you are sure of; never commit to peak.
4. **Consolidate with Karpenter.** A NodePool with `consolidationPolicy: WhenEmptyOrUnderutilized` (the default) moves pods off underused nodes and terminates them, and picks the cheapest instance that fits from a list of allowed types.
5. **Storage lifecycle and snapshot cleanup.** S3 lifecycle rules to Infrequent Access and Glacier, EBS snapshot expiry, and a weekly job to delete unattached volumes.
6. **Cut NAT and cross-AZ traffic.** Gateway VPC endpoints for S3 and DynamoDB are free and remove that traffic from NAT. Interface endpoints for ECR, STS and CloudWatch cost per hour but usually beat NAT per-GB charges. Enable topology-aware routing (`service.kubernetes.io/topology-mode: Auto` on the Service) so pods prefer same-zone endpoints.
7. **Control log and metric volume.** Sample debug logs, drop high-cardinality labels, shorten retention for noisy namespaces.
8. **Delete idle resources.** Load balancers with no targets, stopped instances with attached EBS, unused Elastic IPs, old AMIs.

### Allocation: who pays for what

Allocation turns one bill into a per-team view. On AWS, **cost allocation tags** (both AWS-generated and user-defined) must be activated in the Billing console before they appear in Cost Explorer or the cost allocation report, a CSV that groups charges by tag and includes untagged resources so gaps are visible. Terraform's `default_tags` on the provider applies `team`, `env` and `service` to every resource. Inside a shared cluster, tags do not exist, so allocation uses Kubernetes **namespaces and labels**: OpenCost (a CNCF incubating project) and Kubecost compute each namespace's share from its requests and the node price, and produce **showback** (a report per team, no money moves) or **chargeback** (the team's budget is debited).

```
# Every resource created by this provider gets these tags, so Cost Explorer can group by them.
provider "aws" {
  region = "ap-south-1"
  default_tags {
    tags = {
      team    = "payments"
      env     = "prod"
      service = "checkout-api"
    }
  }
}
```

### Tooling and FinOps in the pipeline

**Cost Explorer** answers "what changed" with group-by on service, tag or account. **AWS Budgets** sends an alert at a threshold (for example 80 percent of the monthly budget forecast). **Infracost** runs in CI: its GitHub Actions integration runs `infracost-ci diff --base-path base --head-path head` on every pull request and posts a comment with the cost difference, so a reviewer sees "+412 USD per month" next to a change that makes an RDS instance Multi-AZ. The rule to state in an interview: every Terraform PR carries a cost diff, and a diff above an agreed amount needs a second approval.

### Unit economics

Total spend is hard to judge. **Cost per unit** is easy: cost per 1,000 requests, per active tenant, per GB ingested. Compute it from two numbers for the same period:

Formula

cost\_per\_1k\_requests=monthly\_requests/1000monthly\_cost\_of\_the\_service​

If cost grows 20 percent and requests grow 50 percent, unit cost fell and the platform is getting more efficient. If both grow at the same rate, you have no economies of scale and should ask why.

### Common waste and the fix

| Waste | How you spot it | Fix |
| --- | --- | --- |
| Requests 3x actual usage | utilisation 25 to 35 percent in Prometheus | Lower requests from the p95 of usage, Vertical Pod Autoscaler in recommend mode |
| Dev clusters running at night | nodes flat across 24 hours | Scale to zero on a schedule, Karpenter NodePool limits |
| NAT per-GB charge from image pulls and S3 | NAT line grows with deploys | Gateway endpoint for S3, interface endpoint for ECR |
| Orphaned EBS volumes and snapshots | volumes in state available | Weekly cleanup job, snapshot lifecycle policy |
| Debug logs in production | log GB per day per namespace | Log level by environment, sampling, shorter retention |
| Oversized RDS "just in case" | CPU under 10 percent | Smaller class, Aurora Serverless v2 for spiky load |
| Idle load balancers | zero healthy targets | Delete, share one ALB with an Ingress or Gateway |

## Diagram

Rendering diagram…

## Worked example

**Cluster of 20 on-demand m6i.xlarge nodes at 35 percent average utilisation.** Assume an on-demand price of 0.192 USD per hour and 730 hours per month (both are assumptions for the arithmetic; check current prices for your Region).

Step 1, the baseline. One node costs 0.192 x 730 = 140.16 USD per month. Twenty nodes: 20 x 140.16 = **2,803.20 USD per month**.

Step 2, right-size to 12 nodes. The work actually used is 20 x 0.35 = 7 nodes' worth of CPU. Twelve nodes carry that at 7 / 12 = 58 percent utilisation, which leaves headroom for a node failure and a rollout surge. Cost: 12 x 140.16 = **1,681.92 USD**. Saving so far: 2,803.20 - 1,681.92 = 1,121.28 USD, which is 40 percent.

Step 3, move 50 percent to spot at an assumed 70 percent discount. Six nodes go to spot at 0.192 x 0.30 = 0.0576 USD per hour: 6 x 0.0576 x 730 = **252.29 USD**. The same six on-demand would have cost 840.96, so this step saves 588.67 USD. Spot is only acceptable because the workloads are stateless replicas behind a Service with a PodDisruptionBudget, and Karpenter replaces an interrupted node within the two-minute notice window.

Step 4, a 1-year Compute Savings Plan on the remaining 6 at an assumed 30 percent discount. 6 x 0.192 x 0.70 x 730 = **588.67 USD**, saving 252.29 USD against on-demand. The plan commits to an hourly spend for 12 months, so it covers only the 6 nodes that run all day, every day.

Step 5, the result. New monthly cost: 252.29 + 588.67 = **840.96 USD**. Saving: 2,803.20 - 840.96 = 1,962.24 USD, which is **70 percent**. Note the order: right-sizing came first because every later discount is applied to a smaller base. Committing to 20 nodes before right-sizing would have locked in the waste for a year.

## Runnable code

Python · runs and prints its own checks

```
"""Right-size a fake node fleet and estimate the saving from spot and a savings plan.

All prices are ASSUMPTIONS for the arithmetic, labelled as such.
No network. Prints the before and after monthly cost and asserts the saving
lands in the range from the worked example (60 to 75 percent).
"""

HOURS_PER_MONTH = 730
ON_DEMAND_USD_PER_HOUR = 0.192     # assumption: m6i.xlarge on-demand
SPOT_DISCOUNT = 0.70               # assumption: spot price is 30 percent of on-demand
SAVINGS_PLAN_DISCOUNT = 0.30       # assumption: 1-year Compute Savings Plan
NODE_CPU = 4.0                     # vCPU per m6i.xlarge
NODE_MEM_GIB = 16.0
TARGET_UTIL = 0.60                 # size the new fleet so usage is about 60 percent
SPOT_SHARE = 0.50                  # half the right-sized fleet goes to spot

def fake_fleet(n):
    """Twenty nodes: pods request 3.0 vCPU and 12 GiB each, but use about 35 percent."""
    nodes = []
    for i in range(n):
        used_cpu = round(NODE_CPU * (0.30 + 0.01 * (i % 10)), 2)  # 1.20 to 1.56 vCPU
        used_mem = round(NODE_MEM_GIB * (0.30 + 0.01 * (i % 10)), 2)
        nodes.append({"name": f"ip-10-0-1-{10 + i}", "req_cpu": 3.0, "req_mem": 12.0,
                      "used_cpu": used_cpu, "used_mem": used_mem})
    return nodes

def utilisation(nodes):
    cpu = sum(n["used_cpu"] for n in nodes) / (NODE_CPU * len(nodes))
    mem = sum(n["used_mem"] for n in nodes) / (NODE_MEM_GIB * len(nodes))
    return cpu, mem

def recommend(nodes):
    """How many nodes carry the measured usage at TARGET_UTIL (the 40 percent left is the headroom)."""
    cpu_used = sum(n["used_cpu"] for n in nodes)
    mem_used = sum(n["used_mem"] for n in nodes)
    need_cpu = cpu_used / (NODE_CPU * TARGET_UTIL)
    need_mem = mem_used / (NODE_MEM_GIB * TARGET_UTIL)
    count = max(2, -(-max(need_cpu, need_mem) // 1))  # ceil, never below 2 nodes
    spot = int(count * SPOT_SHARE)
    return int(count), spot, int(count) - spot

def monthly(on_demand=0, spot=0, plan=0):
    p = ON_DEMAND_USD_PER_HOUR * HOURS_PER_MONTH
    return on_demand * p + spot * p * (1 - SPOT_DISCOUNT) + plan * p * (1 - SAVINGS_PLAN_DISCOUNT)

if __name__ == "__main__":
    fleet = fake_fleet(20)
    cpu_u, mem_u = utilisation(fleet)
    before = monthly(on_demand=len(fleet))
    print(f"fleet: {len(fleet)} nodes, cpu util {cpu_u:.0%}, mem util {mem_u:.0%}")
    print(f"before: {len(fleet)} on-demand nodes = {before:,.2f} USD/month (assumed prices)")

    total, spot, plan = recommend(fleet)
    after_rightsize = monthly(on_demand=total)
    after = monthly(spot=spot, plan=plan)
    print(f"right-size: {total} nodes on-demand = {after_rightsize:,.2f} USD/month "
          f"({(before - after_rightsize) / before:.0%} saved)")
    print(f"split: {spot} spot at {SPOT_DISCOUNT:.0%} off, {plan} on a savings plan at "
          f"{SAVINGS_PLAN_DISCOUNT:.0%} off")
    saved = (before - after) / before
    print(f"after: {after:,.2f} USD/month, {saved:.0%} saved")
    print(f"new utilisation if usage is unchanged: {cpu_u * len(fleet) / total:.0%}")

    assert 0.60 <= saved <= 0.75, f"saving {saved:.0%} outside the worked example range"
    assert total < len(fleet) and spot + plan == total
    print("checks passed: fewer nodes, spot plus plan equals the fleet, saving in 60 to 75 percent")
```

## Key takeaways

* Cost is a metric with an owner, a budget alert and a postmortem, not a monthly surprise. The FinOps phases are Inform, Optimize, Operate.
* Right-size first; every discount after that applies to a smaller base.
* Spot commits to nothing and can be interrupted with two minutes' notice; a Compute Savings Plan commits to hourly spend for 1 or 3 years across families and Regions; an EC2 Instance Savings Plan commits to one family in one Region for a larger discount.
* Karpenter consolidation and scale-to-zero for non-prod are the cheapest wins on a Kubernetes platform.
* NAT per-GB, cross-AZ traffic, log ingest and old snapshots grow silently: VPC endpoints, topology-aware routing, sampling and lifecycle rules stop them.
* Allocation needs tags on AWS resources and namespaces or labels inside the cluster; OpenCost or Kubecost turn those into showback per team.
* Put Infracost on every Terraform pull request so cost is reviewed with the code.
* Report cost per request or per tenant, not just total spend.

## Common mistakes

* Buying a savings plan or reserved capacity for the whole fleet before right-sizing, which locks in the waste for a year.
* Putting stateful pods or singletons on spot nodes with no PodDisruptionBudget.
* Comparing cost month to month without normalising by traffic, so growth looks like waste or waste looks like growth.
* Forgetting that tags must be activated as cost allocation tags before Cost Explorer can group by them.
* Treating NAT Gateway as free plumbing while every image pull and S3 read pays per GB.
* Right-sizing from requests instead of from measured usage.

## Practice

* In a kind cluster, install metrics-server, deploy a few pods with requests 3x their real usage, and write a script that reads `kubectl top pods` and prints requested vs used CPU per namespace with a utilisation percentage.
* Install OpenCost on the same cluster with a fixed on-demand price configured, and produce a showback table of cost per namespace for one day.
* In a free-tier AWS account, write Terraform for one small instance with `default_tags`, run Infracost locally on the plan JSON, then change the instance type and compare the two estimates.
* Write a Python or Bash script that lists EBS volumes in state available and snapshots older than 30 days (fake the AWS calls with sample JSON) and prints what it would delete and the monthly saving at an assumed price.

## Interview questions (6)

1.The AWS bill doubled this month. What do you look at first?Medium

I open Cost Explorer grouped by service and compare this month to last, then group the top service by tag or linked account to find which team or environment grew. The usual suspects in order: a new node group or autoscaler that scaled up and never scaled down, a NAT Gateway per-GB spike from image pulls or a data job, a logging change that multiplied ingest, or snapshots and volumes nobody deleted. I also check whether traffic doubled too; if requests doubled, unit cost is unchanged and the right fix is capacity planning, not cutting. Then I set a budget alert so the next jump is caught at 20 percent, not 100.

2.Spot instances, savings plans or reserved instances: when do you use each?Medium

Spot for stateless, replicated, interruption-tolerant work: web replicas, CI runners, batch jobs. It commits to nothing and can be reclaimed with a two-minute notice, so I pair it with a PodDisruptionBudget and Karpenter to replace nodes. A Compute Savings Plan for the steady baseline I am sure will run all year: it commits to an hourly spend for one or three years but stays flexible across instance family, size, Region, and even Fargate and Lambda. An EC2 Instance Savings Plan or a Reserved Instance when I know the exact family and Region and want the larger discount. I only ever commit to the baseline after right-sizing, never to peak.

3.How do you charge teams for a shared EKS cluster?Medium

Tags work for AWS resources but not for pods, so inside the cluster I allocate by namespace and labels. One namespace per team, a `team` label on every workload enforced by an admission policy, and OpenCost or Kubecost reading requests and node prices to compute each namespace's share, with idle capacity split by an agreed rule. I start with showback, a monthly report each team can see, before any chargeback, because the first reaction to a bill is to argue about the method. Shared services like monitoring and ingress are a platform cost line, allocated in proportion to usage.

4.What is Karpenter consolidation and how does it save money?Easy

Karpenter launches nodes sized for the pending pods instead of picking from a fixed node group. Consolidation is its disruption behaviour: with the default consolidationPolicy WhenEmptyOrUnderutilized it looks for nodes that are empty or whose pods would fit on other nodes, or that could be replaced by a cheaper instance, and it drains and removes them while respecting PodDisruptionBudgets. The saving comes from fewer, fuller, cheaper nodes, and from picking spot or the cheapest instance type from the list the NodePool allows.

5.How would you put cost into the deployment pipeline?Easy

I add Infracost to the Terraform pull request workflow. It compares the base and head branches and posts a comment with the monthly cost difference per resource, so a reviewer sees that enabling Multi-AZ on an RDS instance adds a known amount before it is merged. A policy marks diffs above an agreed threshold as needing a second approval. On the Kubernetes side, Kyverno policies require requests and a team label on every pod, so nothing unallocated reaches the cluster.

6.What is cost per request and why report it instead of total spend?Easy

Cost per request is the service's monthly cost divided by its monthly requests, usually quoted per thousand. Total spend rises when the business grows, which is fine; unit cost rising is the real warning. If spend grows 20 percent while requests grow 50 percent, the platform got more efficient. The same idea works per tenant or per GB ingested. It also gives finance a number they can price against, and it turns a vague "reduce costs" goal into a target like "under 0.02 USD per thousand requests".

## Quiz

1.Which lever should come first in a cost reduction plan?

2.What does a Compute Savings Plan commit you to?

3.A NAT Gateway line is growing every month. What is the cheapest first fix?

4.Why do tags alone not allocate cost inside a shared Kubernetes cluster?

5.In the worked example, 20 nodes at 35 percent utilisation were cut to 12. What is the new utilisation if usage is unchanged?

## Practice these problems

* [DESIGNProduction EKS cluster for a 30-engineer startupHard](/devops/problems/eks-cluster-platform)
* [DESIGNAutoscaling for a web app: ASG, HPA and cluster autoscalingMedium](/devops/problems/autoscaling-web-app)
* [DESIGNLog pipeline at 1 TB per dayMedium](/devops/problems/log-pipeline-1tb)
* [DESIGNCut the AWS bill by 40 percentMedium](/devops/problems/cloud-cost-reduction)

## Further reading

* [FinOps Framework OverviewGuidefinops.org](https://www.finops.org/framework/)
* [Infracost documentation: Get startedGuideinfracost.io](https://www.infracost.io/docs/)
* [Karpenter documentationGuidekarpenter.sh](https://karpenter.sh/docs/)
* [OpenCost documentation: OverviewGuideopencost.io](https://www.opencost.io/docs/)
* [AWS Billing: Using cost allocation tagsGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousOpen source - contributing to CNCF projects, LFX and GSoC](/devops/learn/open-source-cncf-lfx-gsoc)[NextInterview playbook, what is new in 2026, revision sheet](/devops/learn/interview-playbook-2026-revision)

## On this page

1. [Lesson](#lesson)
2. [Diagram](#diagram)
3. [Worked example](#example)
4. [Code](#code)
5. [Key takeaways](#takeaways)
6. [Common mistakes](#mistakes)
7. [Practice](#practice)
8. [Interview questions](#interview)
9. [Quiz](#quiz)
10. [Related problems](#problems)
11. [Further reading](#reading)
12. [My notes](#notes)

## In this lesson

1. [Cost is a signal, not an invoice](#cost-is-a-signal-not-an-invoice)
2. [Where the bill goes for a Kubernetes platform](#where-the-bill-goes-for-a-kubernetes-platform)
3. [The levers, in order of impact](#the-levers-in-order-of-impact)
4. [Allocation: who pays for what](#allocation-who-pays-for-what)
5. [Tooling and FinOps in the pipeline](#tooling-and-finops-in-the-pipeline)
6. [Unit economics](#unit-economics)
7. [Common waste and the fix](#common-waste-and-the-fix)
