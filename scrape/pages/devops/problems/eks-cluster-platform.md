# Production EKS cluster for a 30-engineer startup — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/eks-cluster-platform

[DevOps problems](/devops#problems)

DESIGNPlatform design#4Hard

# Production EKS cluster for a 30-engineer startup

ekskubernetesawskarpentergitopsmulti-tenancy

## Problem statement

A startup with 30 engineers in 6 teams runs 25 services on a handful of EC2 instances started by hand. They want a production Kubernetes platform on AWS within one quarter: teams deploy on their own, nothing is created by clicking in the console, a bad release cannot take the site down, and the whole thing survives the loss of one availability zone. Traffic is 2,000 requests per second at peak. Design the cluster, how it is created, how teams get onto it, and how it is operated.

## Requirements

### Functional

* One production cluster in a dedicated AWS account, plus a staging cluster that is an exact copy at smaller size, both defined in Terraform.
* Each team gets its own namespace with quotas, RBAC and network isolation; teams deploy by merging to Git, never with kubectl against production.
* Every HTTP service is exposed through a shared load balancer with TLS, host-based routing and automatic certificates.
* Pods get AWS permissions (S3, SQS, Secrets Manager) through IAM roles, with no access keys in Secrets.
* Metrics, logs and traces from every workload are collected by default without team configuration.
* Nodes are replaced automatically on scale-up, scale-down, spot interruption and AMI updates.

### Non-functional

* Survive the loss of one availability zone with no manual action; worker nodes spread over 3 zones.
* 99.9 percent monthly availability for the platform's ingress path (43 minutes of allowed downtime).
* Scale from 10 to 60 nodes within 5 minutes of a demand spike.
* Cluster creation from an empty account to "first team deploys" in under 2 hours, repeatable.
* Platform cost under 6,000 USD per month at the stated load, excluding the application's own databases.
* Kubernetes version within 2 minor releases of the latest EKS-supported version at all times; upgrades without downtime.

## Back-of-the-envelope estimates

**Compute.** 25 services, 3 replicas each in production = 75 pods for the apps, plus roughly 40 platform pods (ingress controller, observability agents, Argo CD, cert-manager, external-secrets, CoreDNS). Average app pod requests 0.5 vCPU and 1 GiB. Apps need 37.5 vCPU and 75 GiB; platform adds about 10 vCPU and 20 GiB; total 48 vCPU and 95 GiB. Nodes run at about 70 percent packing, so provision 70 vCPU and 135 GiB. With m6i.xlarge nodes (4 vCPU, 16 GiB, 0.192 USD per hour on-demand in us-east-1, an assumed price) that is 18 nodes, 6 per zone. Spot for the stateless half cuts the price by roughly 60 to 70 percent for those nodes.

**Traffic.** 2,000 requests per second at peak through the ALB that the AWS Load Balancer Controller manages. The ALB scales itself; the only in-cluster hop is the pods themselves, so the number is a capacity question for the services, not for a proxy tier. If a team instead ran an in-cluster proxy such as Envoy Gateway, 3 proxy pods (one per zone) would handle this load with room to spare.

**Pod IPs.** The VPC CNI assigns a VPC IP to every pod. 115 pods plus headroom for surges and daemonsets: plan for 400 pod IPs. With prefix delegation each node reserves /28 blocks, so give the pod subnets at least /22 (1,024 addresses) per zone and keep node subnets separate.

**Cost.** Control plane: 0.10 USD per hour, about 73 USD per month (assumed). 18 m6i.xlarge on-demand: 18 x 0.192 x 730 = 2,523 USD; with half on spot at an assumed 70 percent saving: about 1,640 USD. ALB about 25 USD plus traffic. NAT gateways, 3 x 0.045 x 730 = 99 USD plus data processing. Observability storage about 300 USD. Staging at one third: about 700 USD. Total near 3,000 USD, under the 6,000 USD target with room for growth.

## API

```
Teams interact through Git, not the cluster:

repo platform-infra/        (Terraform, platform team only)
  envs/prod/main.tf          VPC, EKS cluster, node pools, IAM, add-ons
  envs/staging/main.tf

repo platform-gitops/       (Argo CD watches this)
  clusters/prod/
    platform/                aws-load-balancer-controller, cert-manager, external-secrets, otel, karpenter
    tenants/<team>/          Namespace, ResourceQuota, RBAC, NetworkPolicy, AppProject
  clusters/staging/

repo <team>-services/       (one per team)
  deploy/<service>/          Helm values or Kustomize overlay per environment
  .github/workflows/         build, test, push image by digest, bump the GitOps repo

Platform API, as experienced by a team:
  1. Open a PR in platform-gitops adding tenants/<team>/ from a template  -> namespace, quota, roles
  2. Merge a PR in your own repo                                           -> new image tag in GitOps repo
  3. Argo CD syncs; a bad release is held by maxUnavailable: 0 and PDBs
  4. kubectl read-only access through SSO for debugging; writes only via Git
```

## Data model

```
AWS account "prod"
  VPC 10.20.0.0/16, 3 AZs
    public subnets   /24 x3   ALB, NAT gateways
    node subnets     /22 x3   EC2 nodes
    pod subnets      /22 x3   VPC CNI custom networking, prefix delegation
  EKS cluster "prod"  version 1.3x, private endpoint + restricted public endpoint
    access entries:  platform-admin (IAM role), team-<name>-view (IAM role)
    add-ons:         vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver, eks-pod-identity-agent
    node group "system"   managed, on-demand, 3 x m6i.large, taint CriticalAddonsOnly
    Karpenter NodePools:
      general-ondemand   m6i/m5 families, 3 zones, consolidation enabled
      general-spot       same families, capacity-type spot, 3 zones
  IAM roles for pods (Pod Identity): <team>-<service> with least-privilege policies

Kubernetes tenant layout (per team)
  Namespace team-payments
    ResourceQuota        requests.cpu 8, requests.memory 16Gi, pods 60
    LimitRange           default requests 100m / 128Mi
    Role + RoleBinding   team group -> edit in namespace (staging), view (prod)
    NetworkPolicy        default deny ingress from other namespaces; allow from the ALB targets (ip mode) or the proxy namespace
    AppProject (Argo CD) source repos and destination namespace restricted to the team
    ServiceAccounts      one per service, bound to a Pod Identity association
```

## High-level design

**Foundation (Terraform, platform team)**

1. Create the VPC with three subnet tiers per zone and tag subnets so the AWS Load Balancer Controller and Karpenter can discover them.
2. Create the EKS cluster with a private API endpoint (public endpoint limited to the office and CI IP ranges), control plane logging on for audit and authenticator, and encryption of Secrets with a KMS key.
3. Create a small managed node group for system components (CoreDNS, Karpenter itself, the observability collectors) with a taint so application pods never land there.
4. Install the add-ons: VPC CNI with prefix delegation, EBS CSI, Pod Identity agent, and Karpenter with two NodePools (on-demand and spot) across three zones and consolidation turned on.

**Platform layer (Argo CD app-of-apps)**

5. Bootstrap Argo CD from Terraform once; from then on everything in the cluster comes from the `platform-gitops` repo.
6. Install the AWS Load Balancer Controller (it implements Ingress and Gateway API with ALBs and NLBs; ingress-nginx was retired upstream in early 2026, so a new platform should not start on it), cert-manager with a Let's Encrypt or ACM issuer, external-secrets pointing at Secrets Manager, and the OpenTelemetry collector as a DaemonSet shipping metrics, logs and traces.
7. Install Kyverno with policies that every Deployment must set resource requests, a readiness probe, a non-root user and an image from the company registry by digest.

**Tenant onboarding**

8. A team opens a PR that copies the tenant template: Namespace, ResourceQuota, LimitRange, RBAC bound to their SSO group, a default-deny NetworkPolicy and an Argo CD AppProject locked to their repos and namespace.
9. The team's CI builds the image, scans it, pushes it to ECR by digest, and opens a PR that bumps the image in the GitOps repo; a merge is a deploy.

**Operations**

10. Upgrades: EKS control plane first (in staging, then prod), then node AMIs by letting Karpenter drift-replace nodes one at a time under PodDisruptionBudgets.
11. Staging is the same Terraform module with smaller numbers; every change reaches staging first through the same pipelines.

## Architecture diagram

Rendering diagram…

## Deep dives

### Node capacity: Karpenter over the Cluster Autoscaler

The Cluster Autoscaler scales existing Auto Scaling groups, so each instance type and zone combination needs its own group, and it cannot pick a cheaper or better-fitting type on its own. Karpenter watches for unschedulable pods and launches the instance that fits them from a list of allowed families, in the zone the pod needs, and it can consolidate: when pods could fit on fewer or cheaper nodes it drains and replaces them. For a startup this halves the configuration and improves bin-packing. The design uses one small managed node group only for the components that must exist before Karpenter runs (CoreDNS, Karpenter, the collectors), tainted so nothing else lands there, and two Karpenter NodePools. Stateless services tolerate the spot pool; anything with a disk or long connections uses on-demand. Spot interruption gives a 2-minute warning, which Karpenter handles by cordoning and draining under the PodDisruptionBudgets, so a service with 3 replicas and `minAvailable: 2` never loses more than one pod at a time.

### Tenancy: namespaces as the boundary, enforced three ways

Thirty engineers do not justify one cluster per team, so teams share the cluster and the namespace is the unit of ownership. Three mechanisms make it real. RBAC binds each team's SSO group to `edit` in staging and `view` in production, with Argo CD being the only writer in production. ResourceQuota and LimitRange stop one team from starving the others and set sane defaults for teams who forget requests. NetworkPolicy defaults to deny between namespaces and allows traffic from the ingress controller and the observability namespace, so a compromised service cannot reach another team's database. The Argo CD AppProject is the fourth, often forgotten, control: it restricts which repos and which destination namespace a team's Applications may use, otherwise GitOps becomes a way around RBAC.

### Identity: no access keys anywhere

Every service runs with its own ServiceAccount, and EKS Pod Identity (or the older IAM Roles for Service Accounts) associates that ServiceAccount with an IAM role. The AWS SDK inside the pod picks up short-lived credentials from the node agent automatically. Policies are per service and least privilege: the payments service can read one Secrets Manager secret and write to one SQS queue. Humans authenticate to the cluster through EKS access entries mapped to IAM roles that come from SSO, so leaving the company removes cluster access with the IAM user. The same pattern covers CI: GitHub Actions assumes an IAM role through OIDC, with no long-lived AWS keys in repository secrets.

### Surviving a zone failure

The cluster spans three zones at every layer: the managed control plane (AWS does this), the system node group with one node per zone, Karpenter NodePools allowed in all three zones, ingress pods spread by topology spread constraints, and the ALB in three public subnets. When a zone fails, pods there become unreachable, their nodes go NotReady, the node lifecycle controller evicts the pods after the taint timeout, Karpenter launches replacements in the surviving zones, and the ALB stops sending traffic to the dead targets within its health-check interval. The things that break this are single-zone stateful volumes (an EBS volume lives in one zone, so a StatefulSet pod cannot move) and a Deployment whose 3 replicas were all scheduled in one zone; topology spread constraints with `maxSkew: 1` across zones are the fix and Kyverno can require them.

### Upgrades without a maintenance window

EKS supports each Kubernetes version for about 14 months in standard support and charges extended-support pricing after that, so staying within two minor versions is both a security and a cost matter. The order is fixed: read the deprecation notes for the version, upgrade the control plane in staging, run the conformance smoke test, upgrade the add-ons, let Karpenter drift-replace nodes with the new AMI one at a time, then repeat in production a week later. PodDisruptionBudgets on every service with 2 or more replicas are what make node replacement safe, and a Kyverno policy can require them.

## Evaluation

**Platform SLIs.** Ingress availability from an external probe every 30 seconds (target 99.9 percent); time from merge to pods ready (target under 10 minutes at p90); time from pending pod to scheduled when capacity is needed (under 5 minutes); node replacement during upgrades with zero failed requests on the canary service.

**Chaos tests before go-live.** Terminate all nodes in one zone and confirm every service with 2 or more replicas keeps answering; drain a node under load; delete the ingress controller pods one at a time; revoke a Pod Identity association and confirm the service fails closed with a clear error.

**Cost review.** Monthly report per namespace from the Kubernetes cost allocation labels; alert when spot share of general compute drops below 40 percent or when Karpenter consolidation is disabled.

**Security checks.** Kyverno policy violations reported per namespace in audit mode for two weeks, then enforce; image scanning gate in CI; cluster audit logs shipped to the central account; quarterly review of IAM roles with Access Analyzer.

**Team adoption.** Number of teams deploying only through Git (target 6 of 6 within the quarter) and production kubectl write operations by humans (target 0, measured from audit logs).

## Bottlenecks & mitigations

* Pod IP exhaustion in the VPC CNI when subnets are small or prefix delegation is off; the symptom is pods stuck ContainerCreating.
* The AWS Load Balancer Controller is a shared control-plane dependency: if it is down, new Ingress or HTTPRoute objects get no load balancer, although existing ALBs keep serving; run 2 replicas with leader election and keep its config behind the same review as code.
* Argo CD as the only writer in production means an Argo CD outage blocks releases (not traffic); run it with high availability and keep the break-glass procedure written down.
* NAT gateway data processing charges grow with image pulls and external calls; use ECR VPC endpoints and S3 gateway endpoints.
* etcd object count and API server load grow with many small resources; avoid controllers that create thousands of objects per minute.

## Failure modes

* **All replicas in one zone.** A zone loss takes the service down. Mitigation: topology spread constraints required by policy.
* **StatefulSet pinned to a dead zone's EBS volume.** The pod cannot start elsewhere. Mitigation: run stateful services on RDS, ElastiCache or multi-zone operators; for self-run state use per-zone replicas and application-level replication.
* **Karpenter consolidation evicts pods with no PDB during business hours.** Users see errors. Mitigation: PDBs required by policy, and a consolidation schedule if needed.
* **Team Application points at another team's namespace.** RBAC is bypassed through GitOps. Mitigation: AppProject destination restrictions.
* **Hand edits in production.** Argo CD reverts them, confusing an on-call engineer. Mitigation: kubectl write access removed; a documented break-glass role that alerts when assumed.
* **Mutable image tags.** A rebuilt `v1.2` tag changes code without a Git change. Mitigation: deploy by digest; Kyverno rejects tags.
* **Extended support surprise.** The cluster ages past standard support and the control plane bill rises sharply. Mitigation: upgrade cadence with a calendar reminder two months before the end of support.

## Follow-up questions interviewers ask

* The company grows to 300 engineers. When do you split into multiple clusters, and along which lines?
* A team needs GPU nodes for an inference service. What changes in the NodePools, the scheduling and the cost model?
* How would you give teams production kubectl access for debugging without letting them change anything?
* Argo CD is down and a critical fix must go out. What is the break-glass procedure and how do you reconcile afterwards?
* The VPC runs out of IP addresses. What are your options, short term and long term?
* Would EKS Auto Mode or Fargate change this design, and what would you give up?

## Lessons that cover this

* [#12AWS managed platforms - EKS, ECS, Fargate, Lambda, SQS, ElastiCache, CloudFrontCloud and IaC](/devops/learn/aws-managed-platforms-eks-ecs)
* [#13Terraform - infrastructure as codeCloud and IaC](/devops/learn/terraform-infrastructure-as-code)
* [#15Kubernetes architecture and core objectsKubernetes](/devops/learn/kubernetes-architecture-core-objects)
* [#17Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKSKubernetes](/devops/learn/kubernetes-in-production)
* [#19GitOps with Argo CD and progressive deliveryKubernetes](/devops/learn/gitops-argocd-progressive-delivery)
* [#23Security and DevSecOps - secrets, least privilege, supply chain, policy as codeOperate](/devops/learn/security-and-devsecops)
* [#25Kubernetes internals and operators in GoContribute](/devops/learn/kubernetes-internals-operators-go)
* [#27Cloud cost and FinOpsShip](/devops/learn/cloud-cost-and-finops)
* [#28Interview playbook, what is new in 2026, revision sheetShip](/devops/learn/interview-playbook-2026-revision)
* [#29Platform engineering, service mesh and eBPFLater](/devops/learn/platform-engineering-service-mesh-ebpf)
* [#30GPU and ML infrastructure - serving models on KubernetesLater](/devops/learn/gpu-and-ml-infrastructure)
* [#31Projects - pipeline, cluster, observability, operatorLater](/devops/learn/projects)

## Further reading

* [Amazon EKS best practices guideGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html)
* [Karpenter documentationGuidekarpenter.sh](https://karpenter.sh/docs/)
* [Argo CD documentationGuideargo-cd.readthedocs.io](https://argo-cd.readthedocs.io/en/stable/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousMulti-environment Terraform: dev, staging and prod with remote state](/devops/problems/terraform-multi-env)[NextObservability platform for 200 microservices](/devops/problems/observability-platform)

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
