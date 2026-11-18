# Pods Pending and ImagePullBackOff after a node group change — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/pod-pending-imagepullbackoff

[DevOps problems](/devops#problems)

OPSTroubleshooting#22Easy

# Pods Pending and ImagePullBackOff after a node group change

kubernetestroubleshootingschedulingecrkarpentereksReported at Infosys, Wipro, TCS

## Problem statement

It is 11:20 on a Thursday. The platform team announces in Slack that they have replaced the general node group on the production EKS cluster with a Karpenter NodePool. Ten minutes later the checkout team pages you: `kubectl get pods -n checkout` shows the 8 replicas of `checkout-api` as 3 `Pending` for 9 minutes, 3 `ImagePullBackOff`, and 2 `Running` on the last old node, which are the only ones serving. Find out why each half of the new pods is stuck, get the service back to 8 ready pods, and make sure the next node group change cannot do this again.

## Requirements

### Functional

* Explain the Pending half from the scheduler's own message, not from a guess.
* Explain the ImagePullBackOff half from the kubelet's pull error and the node's identity.
* Separate the candidate causes: resources, taints, nodeSelector or affinity, zone-bound volumes for Pending; registry permission, missing tag, missing imagePullSecret, rate limit for pulls.
* Restore 8 ready pods through the proper path (Terraform for IAM, Git for manifests), not a hand edit that disappears.
* State one root cause in one sentence and the prevention in two.

### Non-functional

* Diagnosis in under 10 minutes with kubectl, the AWS CLI and the Karpenter logs.
* Service keeps serving on the 2 remaining pods during the investigation; no new rollout until the cause is known.
* Blast radius is 1 namespace to start with, but any pod that lands on a new node is affected, so the fix is cluster-wide and urgent.
* Fix lands through Terraform within 20 minutes; the write-up is 5 lines.

## Back-of-the-envelope estimates

**Impact.** `checkout-api` normally runs 8 pods at about 90 requests per second each, 720 total. Two pods remain, so capacity is 180 requests per second against a midday load of around 500: about 2 in 3 checkout requests are queued or time out until the fix lands. Every other Deployment whose pods move to a new node will hit the same pull error, so the longer the old node stays drained the wider it spreads. The kubelet's image pull back-off doubles from 10 seconds to a cap of 300 seconds, so after the IAM fix a stuck pod may wait up to 5 minutes for its next attempt; deleting the 3 ImagePullBackOff pods makes recovery immediate.

## API

```
# 1. Which pod is on which node, and which nodes are new? AGE and the node name tell you.
kubectl get pods -n checkout -l app=checkout-api -o wide
kubectl get nodes -L karpenter.sh/nodepool -L eks.amazonaws.com/nodegroup

# 2. Pending half: the scheduler writes its reason in the Events.
kubectl describe pod checkout-api-7c9d4f8b6-k2xqv -n checkout | tail -n 15
# Warning  FailedScheduling  default-scheduler  0/7 nodes are available: 1 node(s) were unschedulable,
#   3 Insufficient cpu, 3 node(s) had untolerated taint {workload: batch}. preemption: 0/7 nodes are available: ...

# 3. ImagePullBackOff half: the kubelet writes the registry's answer in the Events.
kubectl describe pod checkout-api-7c9d4f8b6-p8s2m -n checkout | tail -n 15
# Warning  Failed   kubelet  Failed to pull image "123456789012.dkr.ecr.ap-south-1.amazonaws.com/checkout-api:v2.14.0":
#   ... pulling from host 123456789012.dkr.ecr.ap-south-1.amazonaws.com failed with status code [manifests v2.14.0]: 401 Unauthorized
# Warning  Failed   kubelet  Error: ImagePullBackOff

# 4. Rule out the tag: does v2.14.0 exist in ECR? (It does; 401 is about identity, not the tag.)
aws ecr describe-images --repository-name checkout-api --image-ids imageTag=v2.14.0

# 5. Which IAM role do the new nodes run with, and what can it do?
kubectl get nodeclaims
kubectl get ec2nodeclass default -o jsonpath='{.spec.role}{"\n"}'
aws iam list-attached-role-policies --role-name KarpenterNodeRole-prod

# 6. Confirm on the node itself: the kubelet's ECR credential plugin was refused.
kubectl debug node/ip-10-0-41-7.ap-south-1.compute.internal -it --image=busybox -- \
  chroot /host journalctl -u kubelet --since "15 min ago" | grep -i ecr

# 7. Why is Karpenter not adding capacity for the Pending pods? Read its log.
kubectl logs -n karpenter deploy/karpenter --since=15m | grep -iE "nodepool|limit|launched"

# 8. After the IAM fix: retry the pulls now instead of waiting out the back-off.
kubectl delete pod -n checkout -l app=checkout-api --field-selector=status.phase=Pending
```

## Data model

```
Pod status fields that decide the diagnosis
  status.phase                                   Pending   (never scheduled) vs Running/Pending with a container Waiting
  status.conditions[type=PodScheduled].reason    Unschedulable
  status.containerStatuses[0].state.waiting
      reason   ImagePullBackOff | ErrImagePull   -> read the message
      message  ... 401 Unauthorized              -> identity (node role, imagePullSecret)
               ... manifest unknown / not found  -> tag or repository does not exist
               ... toomanyrequests               -> public registry rate limit
  spec.nodeName                                  set = scheduled; empty = scheduler has not placed it

Scheduler message parts (one count per node, they add up to the node total)
  N Insufficient cpu | Insufficient memory       requests do not fit on N nodes
  N node(s) had untolerated taint {key: value}   taint without a matching toleration
  N node(s) didn't match Pod's node affinity/selector
  N node(s) had volume node affinity conflict    PVC is bound to an EBS volume in another zone

Pod spec fields to check against the nodes
  spec.containers[].resources.requests           cpu, memory
  spec.tolerations[]                             key, operator, value, effect
  spec.nodeSelector, spec.affinity.nodeAffinity  labels that no new node carries
  spec.volumes[].persistentVolumeClaim           zone of the bound PV

Node and Karpenter fields that matter
  node.spec.taints[]                             {key: workload, value: batch, effect: NoSchedule}
  node.status.allocatable.cpu                    minus the sum of requests = free
  NodePool.spec.template.spec.taints             taints every new node gets
  NodePool.spec.limits.cpu                       Karpenter stops adding nodes at this total
  EC2NodeClass.spec.role                         IAM role the nodes assume (instance profile is derived)
  IAM role attachments                           AmazonEKSWorkerNodePolicy, AmazonEC2ContainerRegistryPullOnly, AmazonEKS_CNI_Policy
  EC2NodeClass.spec.amiSelectorTerms, subnetSelectorTerms, securityGroupSelectorTerms

Events (kubectl describe, bottom)
  Warning  FailedScheduling  0/7 nodes are available: ...
  Normal   Pulling           Pulling image "..."
  Warning  Failed            Failed to pull image "...": ... 401 Unauthorized
  Warning  Failed            Error: ImagePullBackOff
  Normal   BackOff           Back-off pulling image "..."
```

## Diagnosis and fix

1. **Scope.** `kubectl get pods -o wide` shows the 3 ImagePullBackOff pods on nodes aged 11 minutes with the `karpenter.sh/nodepool=general` label, the 3 Pending pods with no node, and the 2 serving pods on the one old node not yet drained. Ask the platform team to pause that drain: it is the only capacity you have.
2. **Read the scheduler.** The Pending event says `0/7 nodes are available: 1 node(s) were unschedulable, 3 Insufficient cpu, 3 node(s) had untolerated taint {workload: batch}`. The unschedulable node is the cordoned old node. Three nodes are the batch pool, tainted on purpose. The other three are the new general nodes, and they are full: every pod placed there, including the three stuck pulling, still holds its CPU request. So Pending is a capacity queue, not a second bug. One look at the Deployment rules out the rest: no `nodeSelector`, no affinity, no PVC.
3. **Read the kubelet.** The ImagePullBackOff event says the registry answered `401 Unauthorized` for `manifests v2.14.0`. A missing tag gives `not found` or `manifest unknown`, a public registry rate limit gives `toomanyrequests`, so this is identity. The Deployment has no `imagePullSecrets` because EKS nodes pull from ECR with the node role. `aws ecr describe-images` confirms the tag exists.
4. **Find the identity.** `kubectl get ec2nodeclass default -o jsonpath='{.spec.role}'` prints `KarpenterNodeRole-prod`, created this morning in Terraform. `aws iam list-attached-role-policies` shows `AmazonEKSWorkerNodePolicy` and `AmazonEKS_CNI_Policy` only: `AmazonEC2ContainerRegistryPullOnly` is missing. The kubelet journal on a new node confirms the ECR credential provider was refused `ecr:GetAuthorizationToken`.
5. **Why Karpenter does not help.** Its log shows a NodeClaim launched for the Pending pods, so capacity is coming, but any pod placed on it will fail the same pull. Fix IAM first.
6. **Fix through the proper path.** Add the `aws_iam_role_policy_attachment` for `arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly` to the node role module, plan, apply. No node restart: role permissions change in place and the next pull gets a token.
7. **Verify.** Delete the ImagePullBackOff pods so the kubelet retries now instead of waiting out a 5-minute back-off; watch them reach `1/1 Running`. The Pending pods schedule when the new NodeClaim registers. `kubectl get endpointslices -n checkout -l kubernetes.io/service-name=checkout-api` lists 8 ready addresses. Let the drain finish.
8. **Prevent.** The node role module attaches all three policies with no option to drop one, and a plan-time check fails if `ecr:GetAuthorizationToken` is not allowed. The node change runbook pulls an ECR image on one new node before the old group is drained. Alert on `kube_pod_container_status_waiting_reason{reason="ImagePullBackOff"} > 0` for 5 minutes.

## Architecture diagram

Rendering diagram…

## Deep dives

### Pending and ImagePullBackOff are two different machines talking

A Pending pod with no node name has never left the scheduler. Its event is written by `default-scheduler` and the counts in it are a histogram over all nodes: `1 unschedulable, 3 Insufficient cpu, 3 untolerated taint` means every one of the 7 nodes rejected the pod for exactly one reason, and the taint is printed as `{key: value}` so you can match it against `spec.tolerations`. An ImagePullBackOff pod has already been scheduled; the event comes from the kubelet on that node and the message is the container runtime's error, which includes the HTTP status the registry returned. Saying which component wrote each event, and reading the status code instead of the word ImagePullBackOff, is what separates a guess from a diagnosis.

### Why pods that never ran still fill a node

The scheduler reserves `resources.requests` the moment it binds a pod to a node. A pod whose image never pulls holds that reservation forever. Three stuck `checkout-api` pods at 1 CPU each, plus the other services that moved, fill the 3 new nodes, and that is why the remaining replicas see `Insufficient cpu`. The trap is to fix only the Pending half by adding nodes: each new node receives pods, those pods fail the same pull, and the cluster grows while serving nothing. Fix the pull first, then let capacity catch up.

### Where the node's registry identity comes from

An EKS node has no Docker login. The kubelet runs the ECR credential provider plugin, which calls `ecr:GetAuthorizationToken` with the instance's IAM role and returns a short-lived token for images matching the ECR host pattern. The EKS docs name two required policies for the node role: `AmazonEKSWorkerNodePolicy` and `AmazonEC2ContainerRegistryPullOnly`. With Karpenter, `EC2NodeClass.spec.role` names that role and Karpenter builds the instance profile from it, so a new EC2NodeClass with a new role is exactly where a policy goes missing. A private registry outside AWS is the other case: there the pod needs `imagePullSecrets` pointing at a `kubernetes.io/dockerconfigjson` Secret, and a 401 means the Secret is missing, in the wrong namespace, or expired.

### Why the fix is Terraform and not a console click

Attaching the policy in the console fixes the cluster in a minute and the next `terraform apply` on the IAM module removes it again, because the attachment is not in state. Role permissions apply to running instances immediately, so there is no speed gained by clicking. Make the change in the module, apply, and then make the module unable to produce a node role without the ECR policy.

## Evaluation

**Did you find it?** The root cause is stated as "the Karpenter EC2NodeClass points at a new node role that lacks `AmazonEC2ContainerRegistryPullOnly`, so the kubelet's ECR credential provider cannot get a token and every pull on a new node gets 401", with the evidence chain: pods on new nodes only, the 401 in the kubelet event, the tag confirmed in ECR, the role's attached policies, the credential provider error in the kubelet journal. The Pending half is explained as a consequence: full nodes plus a batch taint, not a second bug.

**Is it fixed?** After the apply: the deleted pods pull and reach `1/1 Running` within a minute, the Pending pods schedule when the new NodeClaim registers, the EndpointSlice has 8 ready addresses, and the ImagePullBackOff count across all namespaces is 0 for 10 minutes.

**Is it prevented?** The node role module always attaches the three policies; a plan-time check fails if `ecr:GetAuthorizationToken` is not allowed; the node group change runbook pulls an ECR image on one new node before draining the old group; an alert fires on any pod waiting in ImagePullBackOff for 5 minutes.

**What a strong answer adds.** Reading the taint from the scheduler message and matching it to tolerations; knowing that requests of stuck pods still count; the image pull back-off cap of 5 minutes and why deleting the pod is faster; the difference between 401 (identity), 404 or manifest unknown (tag) and toomanyrequests (rate limit); and that `EC2NodeClass.spec.role` is where Karpenter's node identity lives.

**What a weak answer does.** "Add nodes" for the Pending pods, "re-push the image" for the pull errors, or attaching `AdministratorAccess` to the node role to make the error go away.

## Bottlenecks & mitigations

* The image pull back-off: up to 5 minutes between attempts, so a fixed cluster can look broken unless you delete the stuck pods.
* Capacity during the incident: 2 pods on one old node carry the service, and draining that node ends it.
* Karpenter adds nodes for Pending pods, which spreads the pull failure to more nodes until IAM is fixed.
* IAM changes made outside Terraform are reverted by the next apply, so the console shortcut costs a second incident.

## Failure modes

* **Treating Pending and ImagePullBackOff as one problem.** Different components, different evidence. Mitigation: read the scheduler event for Pending and the kubelet event for pulls, every time.
* **Adding nodes before fixing the pull.** Every new node fills with pods that cannot start. Mitigation: fix the registry identity first, then capacity.
* **Draining the last old node.** The two serving pods die and the outage becomes total. Mitigation: pause the drain until 8 pods are ready on new nodes.
* **Missing taint tolerations after a pool change.** A NodePool with a taint rejects every pod that does not tolerate it. Mitigation: review `NodePool.spec.template.spec.taints` and the workloads that must land there in the same change.
* **A PVC bound to the wrong zone.** The old node's zone is gone and the EBS volume cannot follow. Mitigation: `volumeBindingMode: WaitForFirstConsumer` on the StorageClass and new nodes in all three zones.
* **Mutable tag or wrong account.** A `401` from a repository in another account looks the same as a missing policy. Mitigation: the registry host in the image reference must be the cluster's own account; cross-account pulls need a repository policy.
* **Fixing IAM in the console.** The next Terraform apply removes it. Mitigation: all IAM through the module; a drift check in CI.

## Follow-up questions interviewers ask

* The pull error says `toomanyrequests` from Docker Hub instead of 401. What is happening and what are the two fixes?
* The Pending message says `3 node(s) had volume node affinity conflict`. What does that mean and how do you fix it without losing data?
* The nodes are a managed node group, not Karpenter. Where do you look for the node role and what else can the launch template break?
* The image is in a private registry outside AWS. How do pods authenticate and how do you rotate that secret?
* How would you write the runbook smoke test that pulls an image on one new node before the old group is drained?
* Karpenter keeps launching nodes while pods are stuck. Which NodePool fields limit the damage?

## Lessons that cover this

* [#8Containers and DockerBuild and ship](/devops/learn/containers-and-docker)
* [#15Kubernetes architecture and core objectsKubernetes](/devops/learn/kubernetes-architecture-core-objects)
* [#16Kubernetes networking and storageKubernetes](/devops/learn/kubernetes-networking-storage)
* [#17Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKSKubernetes](/devops/learn/kubernetes-in-production)
* [#22Troubleshooting playbook - Linux, Docker, Kubernetes, network, pipelinesOperate](/devops/learn/troubleshooting-playbook)

## Further reading

* [Kubernetes: Debug PodsGuidekubernetes.io](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
* [Karpenter documentationGuidekarpenter.sh](https://karpenter.sh/docs/)
* [Amazon EKS documentation: What is Amazon EKS?Guidedocs.aws.amazon.com](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousPod stuck in CrashLoopBackOff](/devops/problems/pod-crashloopbackoff)[Next502 from the ingress while the service works inside the cluster](/devops/problems/ingress-502-service-unreachable)

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
