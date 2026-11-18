# Platform engineering, service mesh and eBPF — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/platform-engineering-service-mesh-ebpf

[DevOps roadmap](/devops)

LaterLesson #29LaterAdvanced 2.5 h

# Platform engineering, service mesh and eBPF

Platform engineering treats the internal tooling that developers use to ship software as a product with customers. This lesson covers what an internal developer platform (IDP) is, golden paths, Backstage and Crossplane, and how to measure a platform. It then covers the two technologies platform teams are asked about most: service meshes (Istio, Linkerd) with their real costs, and eBPF with Cilium, which moves networking, policy and observability into the kernel.

platform engineeringbackstagecrossplaneistiociliumebpfservice mesh

## Why it matters

"Platform engineer" is now a job title at most companies that run more than a few teams on Kubernetes, and the interview for it is different from a DevOps interview. You are asked how you would reduce the work a developer does to ship a service, how you would decide whether a mesh is worth its cost, and what eBPF changes about networking and security. These are judgment questions with numbers behind them. A candidate who can say "a sidecar per pod costs about this much, and here is when I would not pay it" stands out from one who only lists tool names.

Read first: [Kubernetes networking and storage](/devops/learn/kubernetes-networking-storage), [Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKS](/devops/learn/kubernetes-in-production), [GitOps with Argo CD and progressive delivery](/devops/learn/gitops-argocd-progressive-delivery)

## Lesson

### Platform engineering is a product discipline

A platform team builds and runs the internal developer platform (IDP): the set of tools, templates and services that a product team uses to build, deploy and operate software. The difference from a traditional operations team is the stance. The platform team's customers are the developers. The platform is a product with a roadmap, documentation, support hours and a measure of success. Nobody is forced to use it; it wins by being the easiest way to do things right.

The problem it solves is cognitive load. A developer who wants to ship one small service today must know Dockerfiles, Helm, Argo CD, IAM, alert rules, dashboards, secrets, network policies and cost tags. Each is learnable. All of them together, for every team, is a tax paid again and again. The platform's job is to take that load off the developer without taking away control.

The tool for that is the **golden path** (also called a paved road): a supported, documented, opinionated way to do a common task, from "create a new Go service" to "get a Postgres database". You can leave the path, but then you own the result. A good platform API hides the parts that are the same for everyone and exposes only the decisions that belong to the team.

What the API looks like in practice: a developer opens one pull request that adds a short service manifest to a repository. Merging it creates a namespace with quotas and a NetworkPolicy, a CI pipeline, a Grafana dashboard with the RED panels, alert rules against the team's SLO, an IAM role for the pod, and an Argo CD Application that watches the service's own repository. The developer never wrote any of those objects.

```
# service.yaml: everything the developer decides. Everything else comes from the template.
apiVersion: platform.example.org/v1
kind: Service
metadata:
  name: orders-api
spec:
  team: payments            # owner, on-call rotation, cost tag
  language: go              # picks the pipeline and the base image
  tier: 2                   # picks the SLO target, 99.9 for tier 2
  database: postgres        # provisions a database through Crossplane
  publicIngress: true
```

### The tools: Backstage, Port, Crossplane, Score

| Tool | What it is | What it gives the platform |
| --- | --- | --- |
| Backstage | Open source developer portal from Spotify, a CNCF Incubation project | Software Catalog (every service with owner, docs, links), Software Templates (scaffold a repository from a form), TechDocs (docs-as-code next to the code), plugins |
| Port | A commercial developer portal with the same catalog and self-service ideas | Faster to set up than Backstage, less to run |
| Crossplane | A CNCF control plane framework that provisions cloud resources through Kubernetes APIs | A team asks for a database as a Kubernetes object; the platform decides what that means in AWS |
| Score | A CNCF Sandbox workload specification | Describe a workload once, render it to Compose for a laptop or to Kubernetes for production |
| Argo CD | GitOps delivery (lesson 19) | The reconciler that applies everything the template generated |

Crossplane deserves one more paragraph because interviewers compare it with Terraform. In Crossplane, a provider installs managed resources (an RDS instance, an IAM role) as Kubernetes custom resources. A **Composition** describes how a high-level object such as `PostgresDatabase` is built from managed resources, and a composition function (written in Go or Python) can compute that build. A **composite resource** (XR) is an instance of that high-level type; since Crossplane v2 an XR is namespaced by default, and a composition can compose any Kubernetes resource, a Deployment as much as an RDS instance. **Claims**, the namespaced hand-off object of Crossplane v1, exist only for legacy cluster-scoped XRs. The difference from Terraform is not the resources, it is the loop: Terraform runs plan and apply when someone runs it and stores state in a file; Crossplane reconciles forever, so a security group changed by hand in the console is put back within minutes, and access is Kubernetes RBAC rather than a pipeline's credentials. Many platforms use both: Terraform for the cluster and the account, Crossplane for what teams ask for day to day.

### Measuring a platform

A platform without measurement becomes a tooling team that ships features nobody asked for. Four numbers tell you whether it works.

| Metric | How to measure | What a good number looks like |
| --- | --- | --- |
| Adoption | Share of services created through the golden path | Rising; teams choosing the path without being told |
| Time to first deploy | Minutes from "new service" to the first production deploy | Under one hour on the path, days off it |
| DORA metrics per team | Deploy frequency, lead time, change fail rate, failed deployment recovery time | Teams on the platform beat teams off it |
| Cognitive load | A survey, plus the number of tools a developer must touch to ship | Falling release over release |

Report these per team, because the platform's job is to make the median team fast, not to make the best team faster.

### Service mesh: what it solves and what it costs

A service mesh puts a proxy in the path of every service-to-service call and controls those proxies from one place. That gives you mutual TLS (mTLS, both sides present certificates) between all pods without touching the code, retries and timeouts set by policy, traffic shifting for canaries (send 5 percent of calls to v2), and uniform telemetry: latency, error rate and a trace span for every hop.

The cost is real. In the classic sidecar mode, every pod gets an Envoy proxy container, so every request crosses two extra proxies. Istio's own performance page reports, measured with Istio 1.24 at 1000 requests per second with 1 KB payloads, about 0.20 vCPU and 60 MB of memory per sidecar with 2 worker threads. Multiply by pods. Add the latency of two proxy hops per call, the YAML of VirtualService and DestinationRule objects, and the upgrade of a proxy inside every pod when the mesh version changes.

![Three data paths for a request between two pods: a sidecar proxy in every pod, a per-node ztunnel with an optional waypoint, and eBPF programs in the kernel](/devops/img/mesh-sidecar-ambient-ebpf.svg)Three data paths for a request between two pods: a sidecar proxy in every pod, a per-node ztunnel with an optional waypoint, and eBPF programs in the kernel

**Istio ambient mode** removes the sidecar. A per-node Rust proxy called **ztunnel** handles the Layer 4 work: mTLS, L4 authorization and telemetry, without parsing HTTP. Where a team needs Layer 7 features (retries, header routing, traffic shifting) it adds a **waypoint**, an Envoy deployment that runs per namespace, outside the application pods, and is scaled and upgraded on its own. Istio's feature status page, as of its 1.31 release, lists both ztunnel core and waypoints core as Stable. The same Istio page reports a ztunnel at about 0.06 vCPU and 12 MB under the test above, and that is per node, not per pod. Installation is `istioctl install --set profile=ambient` and a namespace joins the mesh with the label `istio.io/dataplane-mode=ambient`. Sidecar and ambient workloads can share one mesh, so migration can be gradual.

**Linkerd** is the other common mesh: a CNCF graduated project with a small, purpose-built Rust proxy (linkerd2-proxy) as the sidecar, fewer features than Istio and much less configuration.

When should a team not adopt a mesh? When it has under about ten services, when it only needs mTLS (Cilium can encrypt node-to-node traffic and a cert-manager-issued certificate at the ingress may be enough), when nobody on the team has run Envoy before, or when the main pressure is cost. Retries and timeouts can live in the client library; metrics can come from OpenTelemetry. A mesh pays off when many teams need the same traffic policy, security policy and telemetry and you cannot change every codebase.

### eBPF and Cilium

**eBPF** lets you run small programs inside the Linux kernel, attached to events such as a packet arriving, a system call, or a function being entered, without changing the kernel or loading a module. A verifier checks each program before it loads (bounded loops, memory access only through checked helpers, a size limit), so a bad program is rejected instead of crashing the machine. The programs are then JIT-compiled and run at native speed.

**Cilium** is the CNI plugin built on eBPF and the usual answer when an interviewer asks what eBPF changes in Kubernetes:

* **Networking without kube-proxy.** With the Helm value `kubeProxyReplacement=true`, Cilium implements ClusterIP, NodePort and LoadBalancer Services in eBPF, at the socket level for pod-originated traffic, so there are no iptables chains to walk and no kube-proxy DaemonSet.
* **NetworkPolicy and more.** Standard NetworkPolicy plus CiliumNetworkPolicy with identity-aware rules at L3 to L7, including DNS-name and HTTP-path rules.
* **Hubble observability.** Flow logs, service maps and drop reasons for every connection, exported to Prometheus, with no change to the application.
* **Mesh-like features without sidecars.** Transparent encryption between nodes (WireGuard or IPsec), L7 policy, and Gateway API support, with an Envoy proxy only where L7 handling is required.

```
# Install Cilium on a cluster that was created without kube-proxy
helm install cilium cilium/cilium --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=${API_SERVER_IP} \
  --set k8sServicePort=${API_SERVER_PORT}
cilium status                                 # agent, operator and Hubble health
hubble observe --namespace payments --verdict DROPPED   # who is being blocked and why
```

Two other eBPF tools to know by name: **Pixie** (CNCF Sandbox) collects request-level telemetry from Kubernetes applications with no instrumentation, and **Falco** (CNCF graduated) watches system calls through an eBPF probe and raises an alert when a container does something it should not, such as spawning a shell or reading `/etc/shadow`.

### Multi-cluster and multi-region in one paragraph

Past a certain size you run a fleet of clusters, not one: one per region, per environment, or per blast-radius boundary. The fleet is managed the same way as the services on it. Terraform or Crossplane creates each cluster from the same module, Argo CD registers every cluster and an ApplicationSet with the cluster generator stamps the platform add-ons and each team's applications onto every cluster whose Secret carries the right labels. A global load balancer (Route 53 latency or failover records, or Cloudflare in front of regional load balancers) sends users to the nearest healthy region, and a service mesh or Cilium cluster mesh lets services find each other across clusters when they must. The rule that makes this work: no cluster is special, so any cluster can be rebuilt from Git.

## Diagram

Rendering diagram…

## Worked example

**What a sidecar mesh costs for 300 pods, against ambient and eBPF.** Every price and size here is an assumption for the arithmetic; replace them with your own.

Assume 300 application pods and a sidecar that reserves 0.1 vCPU and 128 MiB per pod. The mesh adds 300 x 0.1 = 30 vCPU and 300 x 128 MiB = 38,400 MiB = 37.5 GiB of memory that must come from somewhere.

Assume the cluster runs 4 vCPU, 16 GiB nodes and that, after the kubelet, the CNI agent and the system reservation, each node has 3.6 vCPU and 14 GiB allocatable. CPU needs 30 / 3.6 = 8.33, so 9 extra nodes. Memory needs 37.5 / 14 = 2.68, so 3 nodes. CPU is the binding constraint: 9 nodes. At an assumed 0.192 USD per node-hour and 730 hours a month, that is 9 x 0.192 x 730 = 1,261 USD a month, before the latency of two proxy hops on every call.

Now the ambient alternative. The 300 pods at about 8 pods per node sit on about 38 nodes; call it 40. A ztunnel runs once per node. Assume it reserves the same 0.1 vCPU and 128 MiB: 40 x 0.1 = 4 vCPU and 40 x 128 MiB = 5 GiB, which is 4 / 3.6 = 1.1 nodes, so 2 nodes, or 2 x 0.192 x 730 = 280 USD a month. Add waypoints only for namespaces that need L7 features: assume 8 such namespaces with one 0.5 vCPU waypoint each, 4 vCPU, another 2 nodes and 280 USD. Ambient total: about 560 USD, less than half of sidecar, and most pods have no proxy to upgrade.

The eBPF alternative, Cilium with encryption and Hubble: the Cilium agent already runs on every node as the CNI, so the L4 work adds CPU inside an existing DaemonSet rather than new pods. Assume 0.05 vCPU extra per node: 2 vCPU, which fits in the headroom of the existing nodes, so about 0 extra nodes. You give up Istio's L7 traffic policy unless you add Cilium's Envoy for those services.

| Option | Extra vCPU | Extra nodes | Assumed monthly cost | What you lose |
| --- | --- | --- | --- | --- |
| Sidecar | 30 | 9 | 1,261 USD | Nothing in features; latency and upgrade pain |
| Ambient | 8 | 4 | 560 USD | Per-pod L7 only where a waypoint exists |
| eBPF (Cilium) | 2 | 0 | about 0 USD | Istio's L7 policy model, unless Envoy is added |

The interview point: 300 pods is small. At 3,000 pods the sidecar line is 300 vCPU, 84 nodes and 11,773 USD a month, and the ambient line barely moves, because ztunnel scales with nodes, not pods.

## Runnable code

Python · runs and prints its own checks

```
"""A golden-path template in 120 lines, with no network.

Input: a service manifest, the only thing a developer writes.
Output: the platform objects a merge would create (namespace, pipeline,
dashboard, alert rules, IAM role, optional database request), as dicts,
each validated against a small schema before it is printed.

The point: the developer decides 5 things; the template decides the other 40.
"""
import json

SERVICE_SCHEMA = {
    "name": {"type": str, "pattern": "kebab"},
    "team": {"type": str},
    "language": {"type": str, "enum": ["go", "python", "node"]},
    "tier": {"type": int, "enum": [1, 2, 3]},
    "database": {"type": bool},
}

# SLO targets and alert windows the platform owns; a team only picks a tier.
TIER_SLO = {1: 99.95, 2: 99.9, 3: 99.5}
LANG_IMAGE = {"go": "golang:1.25-alpine", "python": "python:3.13-slim", "node": "node:22-alpine"}

def validate(obj, schema, label):
    """Reject anything that would fail later in a cluster, at PR time instead."""
    errors = []
    for key, rule in schema.items():
        if key not in obj:
            errors.append(f"{label}: missing field {key}")
            continue
        val = obj[key]
        if not isinstance(val, rule["type"]) or isinstance(val, bool) and rule["type"] is int:
            errors.append(f"{label}: {key} must be {rule['type'].__name__}")
        if "enum" in rule and val not in rule["enum"]:
            errors.append(f"{label}: {key} must be one of {rule['enum']}, got {val!r}")
        if rule.get("pattern") == "kebab" and not all(c.islower() or c.isdigit() or c == "-" for c in val):
            errors.append(f"{label}: {key} must be kebab-case, got {val!r}")
    extra = set(obj) - set(schema)
    if extra:
        errors.append(f"{label}: unknown fields {sorted(extra)}")
    return errors

def render(svc):
    """Turn one validated manifest into the set of platform objects."""
    name, team, tier = svc["name"], svc["team"], svc["tier"]
    slo = TIER_SLO[tier]
    error_budget = round(100 - slo, 3)
    objects = {
        "namespace": {
            "kind": "Namespace", "name": name,
            "labels": {"team": team, "tier": str(tier), "cost-center": team},
            "quota": {"cpu": "8", "memory": "16Gi"} if tier == 1 else {"cpu": "4", "memory": "8Gi"},
            "networkPolicy": "default-deny-ingress-except-ingress-controller",
        },
        "pipeline": {
            "kind": "Workflow", "name": f"{name}-ci",
            "baseImage": LANG_IMAGE[svc["language"]],
            "steps": ["test", "build", "trivy-scan", "cosign-sign", "push-ecr", "bump-gitops-tag"],
            "ecrRepository": f"platform/{team}/{name}",
        },
        "dashboard": {
            "kind": "GrafanaDashboard", "name": f"{name}-red",
            "panels": ["rate", "errors", "duration p50 p95 p99", "saturation cpu memory"],
            "datasource": "prometheus",
        },
        "alerts": {
            "kind": "PrometheusRule", "name": f"{name}-slo",
            "sloTarget": slo, "errorBudgetPercent": error_budget,
            "rules": [
                {"name": "FastBurn", "burnRate": 14.4, "window": "1h", "severity": "page"},
                {"name": "SlowBurn", "burnRate": 3.0, "window": "6h", "severity": "ticket"},
            ],
        },
        "iamRole": {
            "kind": "PodIdentityAssociation", "name": f"{name}-role",
            "serviceAccount": f"{name}/{name}",
            "policies": ["AllowReadOwnSecrets", "AllowWriteOwnLogs"]
            + (["AllowConnectOwnRds"] if svc["database"] else []),
        },
    }
    if svc["database"]:
        objects["database"] = {
            "kind": "PostgresDatabase", "apiVersion": "platform.example.org/v1alpha1",
            "name": f"{name}-db", "namespace": name,
            "size": "small" if tier == 3 else "medium", "multiAz": tier == 1,
        }
    return objects

OBJECT_SCHEMA = {"kind": {"type": str}, "name": {"type": str, "pattern": "kebab"}}

if __name__ == "__main__":
    good = {"name": "orders-api", "team": "payments", "language": "go", "tier": 2, "database": True}
    bad = {"name": "Orders_API", "team": "payments", "language": "rust", "tier": 2, "database": "yes", "region": "x"}

    print("validating bad manifest:")
    errs = validate(bad, SERVICE_SCHEMA, "service")
    for e in errs:
        print("  reject:", e)
    assert len(errs) == 4, errs

    print("\nvalidating good manifest:", validate(good, SERVICE_SCHEMA, "service") or "ok")
    objs = render(good)
    for key, obj in objs.items():
        problems = validate({"kind": obj["kind"], "name": obj["name"]}, OBJECT_SCHEMA, key)
        assert not problems, problems
    print(f"generated {len(objs)} platform objects from 5 developer decisions:\n")
    print(json.dumps(objs, indent=2))

    # Self-checks: tier drives SLO and budget; database flag drives IAM and the XR.
    assert objs["alerts"]["sloTarget"] == 99.9 and objs["alerts"]["errorBudgetPercent"] == 0.1
    assert "AllowConnectOwnRds" in objs["iamRole"]["policies"] and "database" in objs
    no_db = render({**good, "database": False, "tier": 1})
    assert "database" not in no_db and no_db["alerts"]["sloTarget"] == 99.95
    print("\nself-checks passed: tier 2 gives 99.9 SLO, database flag adds the XR and the IAM policy")
```

## Key takeaways

* A platform is a product: its customers are developers, its metric is cognitive load, and adoption is voluntary.
* A golden path turns one short manifest into every object a service needs; the developer decides only what belongs to the team.
* Backstage gives the catalog, templates and docs; Crossplane provisions cloud resources through Kubernetes APIs with a loop that never stops reconciling, unlike Terraform's plan and apply.
* Measure a platform with adoption, time to first deploy and DORA metrics per team.
* A sidecar mesh costs a proxy per pod; Istio ambient costs a ztunnel per node plus waypoints only where L7 is needed; Cilium does L4 in the kernel with no proxy.
* Do not adopt a mesh for a handful of services or for mTLS alone; adopt it when many teams need the same traffic and security policy.
* eBPF runs verified programs in the kernel; Cilium uses it to replace kube-proxy, enforce identity-aware policy and observe every flow with Hubble.

## Common mistakes

* Building a platform nobody asked for: shipping a portal before the golden path for the most common task exists.
* Treating Crossplane as "Terraform in YAML" and missing the real difference, the continuous reconcile loop and Kubernetes RBAC.
* Adopting Istio in sidecar mode for ten services, then paying a proxy per pod and an upgrade per pod for a feature set the team never uses.
* Saying ambient mode "has no proxies": it has one ztunnel per node and an Envoy waypoint wherever L7 features are turned on.
* Describing eBPF as "a kernel module": it is verified, sandboxed bytecode attached to kernel hooks, and that is why it is safe to run in production.
* Reporting platform success as features shipped instead of time to first deploy and DORA numbers per team.

## Practice

* On a kind cluster created with `kubeProxyMode: none` in the kind config, install Cilium with `kubeProxyReplacement=true`, confirm no kube-proxy pods exist, and use `hubble observe` to watch a request between two pods and then a request blocked by a default-deny CiliumNetworkPolicy.
* Install Istio with the ambient profile on kind, label a namespace `istio.io/dataplane-mode=ambient`, and compare `kubectl top pods` for the application pods before and after: there should be no new container in them. Then add a waypoint for one namespace and measure its CPU.
* Write the golden-path generator from this lesson as a GitHub Actions job: on a PR that adds `services/*.yaml`, render the objects into a `generated/` folder and post a comment listing what will be created. Time how long a new service takes from PR to a running pod on your cluster.
* Install Backstage locally with the create-app scaffold, register one of your repositories in the Software Catalog with a `catalog-info.yaml`, and add a TechDocs page. Note how many steps a new teammate would skip because the catalog answers "who owns this".

## Interview questions (8)

1.What is an internal developer platform, and how is a platform team different from an operations team?Easy

An internal developer platform is the set of tools, templates and services a product team uses to build, deploy and run software: the portal, the golden-path templates, the GitOps repo, the clusters and the observability stack behind them. The difference is the stance. An operations team receives tickets and does work for teams. A platform team ships a product whose customers are developers, measures adoption and time to first deploy, and wins by being the easiest way to do things right rather than by being mandatory. The metric it optimises is the cognitive load a developer carries to ship one service.

2.Describe a golden path for creating a new service. What does the developer write and what does the platform generate?Medium

The developer writes one short manifest: service name, owning team, language, tier and whether it needs a database. That goes in a pull request to the platform repository. On merge, a template renders everything else: a namespace with quota, RBAC and a default-deny NetworkPolicy; a CI workflow for that language with scanning and signing; an ECR repository; a Grafana dashboard with RED panels; SLO burn-rate alerts set from the tier; an IAM role bound to the service account through Pod Identity; a Crossplane composite resource for the database; and an Argo CD Application watching the service repo. The developer then pushes code and the first deploy happens without a ticket.

3.How does Crossplane differ from Terraform, and when would you use each?Medium

Both create cloud resources from declarations. Terraform runs when someone runs it, in a pipeline, and keeps state in a file; drift is found at the next plan. Crossplane runs as a controller inside Kubernetes: managed resources are custom resources, a Composition defines how a high-level type like PostgresDatabase is built from them, and the controller reconciles forever, so a hand-made change in the console is reverted automatically. Access is Kubernetes RBAC rather than pipeline credentials, so a team can request a database by applying a namespaced object. I would use Terraform for the account, VPC and cluster, and Crossplane for the resources teams request day to day on top of that cluster.

4.What problems does a service mesh solve, and what does it cost?Medium

It puts a proxy in every service-to-service call and controls the proxies centrally, which gives mTLS between all pods without code changes, retries and timeouts by policy, traffic shifting for canaries, and uniform latency, error and trace telemetry per hop. The cost in sidecar mode is a proxy per pod: Istio's own measurements put a sidecar at roughly a fifth of a vCPU and 60 MB at 1000 requests per second, plus two proxy hops of latency on every call, a lot of routing YAML, and a proxy upgrade inside every pod. Ambient mode moves the L4 work to one per-node ztunnel and keeps Envoy only as per-namespace waypoints for L7 features, which cuts the cost most teams actually feel.

5.A team with eight microservices asks you to install Istio so they get mTLS. What do you say?Hard

I ask what they actually need. If it is only encryption in transit, a mesh is the expensive answer: Cilium can encrypt node-to-node traffic with WireGuard, and TLS at the ingress plus NetworkPolicy may already meet the requirement. If they also need retries, timeouts and canary traffic shifting across all eight services and cannot change the code, a mesh starts to make sense, and I would propose Istio ambient or Linkerd rather than sidecars, so they pay per node rather than per pod. I would also check whether anyone has run Envoy before, because the operational cost of a mesh is the on-call cost when it misbehaves. For eight services run by one team, client-side retries and OpenTelemetry usually win.

6.What is eBPF and what does Cilium do with it in a Kubernetes cluster?Medium

eBPF lets you attach small programs to events inside the Linux kernel, such as a packet arriving or a system call, without a kernel module. A verifier checks every program before it loads, so it cannot loop forever or read arbitrary memory, and it is then JIT-compiled to run at native speed. Cilium uses it as the CNI: with kubeProxyReplacement it implements Services in eBPF at the socket level and removes kube-proxy and its iptables chains; it enforces NetworkPolicy and identity-aware L3 to L7 rules; Hubble exports every flow and drop reason for observability; and it can encrypt and apply L7 policy without a sidecar in each pod.

7.How would you measure whether your platform is succeeding?Easy

Four numbers, reported per team. Adoption: the share of new services created through the golden path, which should rise without anyone being forced. Time to first deploy: minutes from "new service" to the first production deployment, which should be under an hour on the path. DORA metrics: deploy frequency, lead time, change fail rate and failed deployment recovery time, where teams on the platform should beat teams off it. And cognitive load: a short survey plus a count of the tools a developer must touch to ship, which should fall every release. If adoption is flat, the path is wrong, not the developers.

8.What changes operationally when you go from one cluster to a fleet of clusters across regions?Hard

The clusters themselves become cattle. Every cluster comes from the same Terraform module or Crossplane composition, so any one can be rebuilt from Git. Argo CD registers each cluster, and an ApplicationSet with the cluster generator stamps the platform add-ons and team applications onto every cluster whose Secret has the matching labels, so adding a region is adding a labelled cluster. Traffic is steered by a global layer, Route 53 latency or failover records or Cloudflare, in front of regional load balancers, and health checks remove a bad region. Cross-cluster service discovery, if you need it, comes from a mesh or Cilium cluster mesh. The hard parts are data, because databases do not fail over as easily as stateless pods, and keeping the fleet on the same versions.

## Quiz

1.In Istio ambient mode, which component handles mTLS at Layer 4 for every pod on a node?

2.What is the main difference between Crossplane and Terraform?

3.Which Cilium Helm value lets Cilium replace kube-proxy entirely?

4.A platform team reports it shipped 40 features this quarter. Which metric would tell you whether the platform is actually working?

5.Why is an eBPF program safe to run inside the kernel?

## Practice these problems

* [DESIGNProduction EKS cluster for a 30-engineer startupHard](/devops/problems/eks-cluster-platform)
* [DESIGNInternal developer platform and golden pathHard](/devops/problems/internal-developer-platform)
* [DESIGNGitOps deployment platform with Argo CD for 50 teamsHard](/devops/problems/gitops-platform-argocd)

## Further reading

* [Backstage documentation: What is Backstage?Guidebackstage.io](https://backstage.io/docs/overview/what-is-backstage)
* [Crossplane documentationGuidedocs.crossplane.io](https://docs.crossplane.io/)
* [Istio documentationGuideistio.io](https://istio.io/latest/docs/)
* [Cilium documentationGuidedocs.cilium.io](https://docs.cilium.io/en/stable/)
* [What is eBPF? An Introduction and Deep Dive into the eBPF TechnologyGuideebpf.io](https://ebpf.io/what-is-ebpf/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousInterview playbook, what is new in 2026, revision sheet](/devops/learn/interview-playbook-2026-revision)[NextGPU and ML infrastructure - serving models on Kubernetes](/devops/learn/gpu-and-ml-infrastructure)

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

1. [Platform engineering is a product discipline](#platform-engineering-is-a-product-discipline)
2. [The tools: Backstage, Port, Crossplane, Score](#the-tools-backstage-port-crossplane-score)
3. [Measuring a platform](#measuring-a-platform)
4. [Service mesh: what it solves and what it costs](#service-mesh-what-it-solves-and-what-it-costs)
5. [eBPF and Cilium](#ebpf-and-cilium)
6. [Multi-cluster and multi-region in one paragraph](#multi-cluster-and-multi-region-in-one-paragraph)
