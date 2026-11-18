# Kubernetes networking and storage — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/kubernetes-networking-storage

[DevOps roadmap](/devops)

KubernetesLesson #16StudyIntermediate 4.5 h

# Kubernetes networking and storage

Lesson 15 said a Service is a stable address for pods. This lesson opens the box: how pods get IPs (the CNI plugin), how a Service's virtual IP is turned into real packets (EndpointSlices and kube-proxy or eBPF), how DNS names are built and why they cost extra queries, how HTTP gets in from outside (Ingress, Gateway API, the AWS Load Balancer Controller), how to restrict traffic (NetworkPolicy), and how disks work (PV, PVC, StorageClass, StatefulSets, EBS and EFS).

kubernetesnetworkingcniingressgateway apinetwork policystorage

## Why it matters

Most Kubernetes incidents are networking or storage incidents wearing a different name: a 502 from the ingress, a pod that cannot reach a Service, DNS lookups that fail one time in fifty, a PVC that stays Pending because the only free node is in the wrong zone. Interviewers test this layer because it separates people who can deploy to Kubernetes from people who can run it. On EKS the questions get specific: why nodes run out of pod IPs, why an EBS volume pins a pod to one availability zone, and when you should not run the database in the cluster at all.

Read first: [Networking for DevOps - TCP/IP, DNS, HTTP, TLS, SSH](/devops/learn/networking-for-devops), [Kubernetes architecture and core objects](/devops/learn/kubernetes-architecture-core-objects), [AWS managed platforms - EKS, ECS, Fargate, Lambda, SQS, ElastiCache, CloudFront](/devops/learn/aws-managed-platforms-eks-ecs)

## Lesson

### The networking model and the CNI plugin

Kubernetes makes three promises about the network. Every pod gets its own IP address. Every pod can talk to every other pod, on any node, using that IP, with no NAT in between. Agents on a node can talk to every pod on it. A **CNI plugin** (Container Network Interface) delivers them: when kubelet creates a pod, it calls the plugin, which creates the pod's network interface, assigns the IP and programs whatever routes or tunnels make the three promises true.

| Plugin | How pods get IPs | What else it does | Watch out for |
| --- | --- | --- | --- |
| Amazon VPC CNI (EKS default) | Real VPC IPs from secondary IPs on the node's ENIs, so a pod is addressable from anywhere in the VPC, including by an ALB | Optional NetworkPolicy enforcement (`enableNetworkPolicy: "true"` in the add-on configuration values) | Pods per node is capped by ENI limits; IPv4 exhaustion in small subnets |
| Cilium | Its own pod CIDR, or VPC IPs in ENI mode | eBPF datapath that can replace kube-proxy, L3 to L7 network policy, Hubble flow observability | Needs a recent kernel; a second policy engine next to it causes confusion, run one |

The VPC CNI pod limit is the number interviewers ask for: `(number of ENIs x (IPs per ENI - 1)) + 2`. An m5.large has 3 ENIs and 10 IPs per ENI, so `3 x 9 + 2 = 29` pods. **Prefix delegation** (`ENABLE_PREFIX_DELEGATION=true`) assigns a /28 prefix (16 addresses) to each ENI slot instead of one IP, which raises the limit far above 29; EKS caps managed node groups at 110 pods for instances with fewer than 30 vCPUs. Each /28 must be a contiguous free block in the subnet, so a fragmented subnet gives `InsufficientCidrBlocks` errors. When the VPC runs out of IPv4, the options are custom networking with a secondary CIDR (pods in 100.64.0.0/10) or an IPv6 cluster, which AWS recommends.

### Services under the hood

A ClusterIP is a **virtual IP**: no interface anywhere has it. The API server allocates it from the Service CIDR.

The **EndpointSlice controller** watches pods matching the Service selector and writes their IPs into EndpointSlice objects (up to 100 endpoints per slice by default), labelled `kubernetes.io/service-name`. Each endpoint carries conditions: `serving` (the pod passes readiness), `terminating` (it has a deletion timestamp) and `ready` (serving and not terminating). A pod that fails readiness drops out of the slice within one sync; the Service object never changes.

**kube-proxy** on every node watches EndpointSlices and programs the kernel so that packets to `10.100.21.7:80` are rewritten to one of the ready pod IPs. In `iptables` mode (the Linux default today, with `nftables` planned as the future default) this is a chain of rules with random selection; with tens of thousands of endpoints the rule updates get slow. `ipvs` mode uses a kernel hash table and offers schedulers such as `rr`, `lc` and `mh` but is marked deprecated. Cilium replaces kube-proxy entirely: its eBPF socket load balancer rewrites the destination at `connect()` time, so the packet leaves the pod already addressed to the backend.

![An HTTP request travelling from a client through Route 53, an ALB, and node-level Service rules to pods with VPC IPs on two nodes, with the EndpointSlice feeding both the ALB targets and the node rules](/devops/img/k8s-ingress-traffic-path.svg)An HTTP request travelling from a client through Route 53, an ALB, and node-level Service rules to pods with VPC IPs on two nodes, with the EndpointSlice feeding both the ALB targets and the node rules

* `sessionAffinity: ClientIP` pins a client IP to one pod for `sessionAffinityConfig.clientIP.timeoutSeconds` (default 10800, three hours). Cookies need an ingress proxy.
* `externalTrafficPolicy: Local` on a NodePort or LoadBalancer Service sends traffic only to pods on the receiving node and preserves the client source IP; nodes without a pod fail the health check.
* `trafficDistribution: PreferSameZone` asks kube-proxy to prefer endpoints in the caller's zone, which cuts cross-AZ data transfer charges.
* A **headless Service** (`clusterIP: None`) gets no virtual IP; DNS returns every pod IP, and kube-proxy ignores it. StatefulSets need one.

### DNS: how a name becomes an address

CoreDNS runs as a Deployment in `kube-system` behind the Service `kube-dns`. Every Service gets `name.namespace.svc.cluster.local` (an A or AAAA record for ClusterIP Services, the pod IPs for headless ones), and every port gets an SRV record. A pod in namespace `payments` gets this `/etc/resolv.conf` with the default `dnsPolicy: ClusterFirst`:

```
nameserver 10.100.0.10
search payments.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

The `ndots:5` line causes a famous class of incidents. The resolver counts the dots in the name. If there are fewer than 5, it tries every search suffix first and the bare name last. `api` becomes `api.payments.svc.cluster.local` on the first try: one query. `db.example.com` has 2 dots, so the resolver tries `db.example.com.payments.svc.cluster.local`, then `.svc.cluster.local`, then `.cluster.local`, gets NXDOMAIN three times, and only then asks for `db.example.com`: four queries, each doubled into A and AAAA. On EKS the node's VPC suffix (`ec2.internal` or `<region>.compute.internal`) is a fourth search entry, so one external lookup is five names, ten packets when the resolver also asks AAAA for each. A trailing dot (`db.example.com.`) marks the name absolute and skips the search list. The fixes: fully qualified names with a trailing dot for external hosts, or a lower ndots for that pod:

```
spec:
  dnsConfig:
    options:
      - name: ndots
        value: "2"
```

The CoreDNS config is a ConfigMap called `coredns` holding a **Corefile**. The default server block is `.:53 { errors; health; ready; kubernetes cluster.local in-addr.arpa ip6.arpa { pods insecure; fallthrough in-addr.arpa ip6.arpa; ttl 30 }; prometheus :9153; forward . /etc/resolv.conf; cache 30; loop; reload; loadbalance }`. The `kubernetes` plugin answers cluster names, `forward` sends everything else to the node's resolvers (on EKS, the VPC resolver), `cache 30` caches for 30 seconds. A second block such as `corp.internal:53 { forward . 10.20.0.2 }` sends one domain elsewhere.

**NodeLocal DNSCache** runs a caching agent as a DaemonSet on every node. Pods keep asking the same `kube-dns` IP, but the node agent answers from its cache and talks to CoreDNS over TCP. This removes the cross-node hop and a UDP conntrack race that causes the "one lookup in a thousand times out after 5 seconds" symptom (the `intermittent-dns-failures` problem).

### Exposing HTTP: Ingress, Gateway API and the AWS Load Balancer Controller

An **Ingress** says "for host X and path Y, send to Service Z". It does nothing by itself; an **ingress controller**, chosen with `ingressClassName`, watches Ingress objects and configures a proxy.

```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  namespace: shop
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing   # default is internal
    alb.ingress.kubernetes.io/target-type: ip           # pods as targets; default is instance
    alb.ingress.kubernetes.io/group.name: shop-public   # Ingresses with this name share one ALB
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
spec:
  ingressClassName: alb
  tls:
    - hosts: [shop.example.com]  # the ALB controller finds a matching ACM cert from these hosts
      secretName: shop-tls       # used by in-cluster proxies only: tls.crt and tls.key, filled by cert-manager
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /
            pathType: Prefix     # Exact, Prefix or ImplementationSpecific
            backend:
              service:
                name: web
                port:
                  number: 80
```

Two facts changed the answer in 2026. The Kubernetes docs now state that the Ingress API is frozen and recommend Gateway API instead. And ingress-nginx, the controller most tutorials use, was retired by the Kubernetes project: best-effort maintenance ended in March 2026 with no security fixes after that. Existing installs keep working, but do not start a new platform on it. On EKS the common choices are the **AWS Load Balancer Controller** (an ALB per Ingress, or one ALB shared by every Ingress with the same `group.name`; `target-type: ip` registers pod IPs directly, `instance` goes through a NodePort and needs a NodePort Service) or an in-cluster proxy behind an NLB (Envoy Gateway, Cilium, Traefik, NGINX Gateway Fabric). TLS certificates come from ACM when the ALB terminates TLS (`certificate-arn` annotation) or from **cert-manager** when the proxy does: a ClusterIssuer for Let's Encrypt plus the annotation `cert-manager.io/cluster-issuer: letsencrypt`, and the Secret is created and renewed for you.

**Gateway API** is the replacement, and its core resources (GatewayClass, Gateway, HTTPRoute) have been GA (`v1`) in the Standard channel since release v1.0. It splits the job by role: the infrastructure provider supplies a **GatewayClass** (which controller), the cluster operator creates a **Gateway** (listeners, ports, TLS, which namespaces may attach through `allowedRoutes`), and application teams create **HTTPRoute** objects in their own namespaces. Things that needed vendor annotations on Ingress are typed fields: header matches, weighted `backendRefs` for canaries, `RequestHeaderModifier`, `RequestRedirect` and `URLRewrite` filters. The AWS Load Balancer Controller implements it too (HTTPRoute on ALB, TCP and UDP routes on NLB), and `ingress2gateway` converts existing Ingress objects.

```
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shop
  namespace: shop
spec:
  parentRefs:
    - name: public-gw          # a Gateway owned by the platform team
      namespace: infra
  hostnames: [shop.example.com]
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: api
          port: 80
          weight: 90
        - name: api-canary
          port: 80
          weight: 10
```

### NetworkPolicy: who may talk to whom

By default every pod accepts traffic from every pod in the cluster and can reach anything. A **NetworkPolicy** selects pods and lists what may reach them (ingress) and what they may reach (egress). It only works if the CNI enforces it (VPC CNI with network policy enabled, Cilium, Calico); without that the object is accepted and ignored. Rules in one `from` list item with both `namespaceSelector` and `podSelector` are ANDed; separate items are ORed. The EKS best practices guide says to start every namespace with deny-all and add rules one at a time.

```
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: payments
spec:
  podSelector: {}                 # every pod in the namespace
  policyTypes: [Ingress, Egress]  # isolate both directions
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: payments
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: payments
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: checkout   # callers in one namespace
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: infra
          podSelector:
            matchLabels:
              app.kubernetes.io/name: envoy-gateway   # the ingress proxy, both labels required
      ports:
        - protocol: TCP
          port: 8080
```

An egress rule has the same shape with `egress` and `to`; for a database outside the cluster use `ipBlock: {cidr: 10.50.0.0/16}` with port 5432.

People forget to pair deny-all with `allow-dns`: without it nothing resolves and every call times out instead of being refused. With the ALB in `ip` mode the "ingress controller" is the ALB itself, so the allow rule is an `ipBlock` for the ALB subnets.

A **service mesh** (Istio, Linkerd, Cilium's mesh mode) adds mutual TLS, retries, timeouts and per-request metrics between services through a proxy next to each pod or in the node's eBPF datapath. Lesson 29 covers when it is worth the complexity.

### Storage: from emptyDir to EBS

| Volume type | Lives | Survives pod restart | Survives pod deletion | Use |
| --- | --- | --- | --- | --- |
| emptyDir | On the node's disk (or RAM with `medium: Memory`) | Yes | No | Scratch space, sharing files between containers in a pod |
| hostPath | A path on the node | Yes | Yes, on that node only | Node agents only; a pod that lands on another node sees different data, and it is a security hole |
| PersistentVolumeClaim | A cloud disk or file system | Yes | Yes | Anything that must outlive the pod |

A **PersistentVolume** (PV) is a piece of storage in the cluster; a **PersistentVolumeClaim** (PVC) is a request for storage by size and access mode that a pod mounts; a **StorageClass** says how to make a PV when a PVC asks for one (**dynamic provisioning**), through a CSI driver. On EKS the EBS CSI driver (`ebs.csi.aws.com`) is the usual one.

```
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3                     # the driver default; iops and throughput are tunable
  encrypted: "true"
  csi.storage.k8s.io/fstype: xfs
reclaimPolicy: Delete           # Retain keeps the EBS volume after the PVC is deleted
allowVolumeExpansion: true      # edit spec.resources.requests.storage on the PVC to grow it
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pg-data
  namespace: payments
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: gp3-encrypted
  resources:
    requests:
      storage: 100Gi
```

**Access modes.** ReadWriteOnce (RWO) means one node at a time, which is what a block device like EBS can do; many pods on that node can share it, and ReadWriteOncePod restricts it to one pod. ReadWriteMany (RWX) means many nodes at once, which needs a shared file system: on AWS that is EFS through the EFS CSI driver, slower and priced per GB stored, but the only answer when three replicas must share uploads. A PVC asking for RWX from an EBS StorageClass stays Pending forever.

**Zones.** An EBS volume exists in one availability zone and can only attach to instances in that zone. With `volumeBindingMode: Immediate` the volume would be created when the PVC is created, in whatever zone the provisioner picks, and the pod would then be forced into that zone, possibly one with no free node. `WaitForFirstConsumer` delays provisioning until the scheduler has placed the pod, then creates the volume in that zone. From then on the pod is pinned: if the zone's nodes are full, the pod is Pending with "volume node affinity conflict". Snapshots (`VolumeSnapshot` in `snapshot.storage.k8s.io/v1`, from a PVC; restore by creating a PVC with `dataSource` pointing at the snapshot) are how you move data across zones. Expansion is online for EBS; shrinking is not supported. `reclaimPolicy` decides what happens to the volume when the PVC is deleted: `Delete` (the default for dynamic PVs) removes the disk, `Retain` leaves it as a Released PV for a human to deal with.

### StatefulSets and the database question

A **StatefulSet** is for pods that need identity: stable names (`pg-0`, `pg-1`), a stable DNS entry each (`pg-0.pg.payments.svc.cluster.local` through the headless Service named in `serviceName`), their own PVC each from `volumeClaimTemplates`, and ordered operations: pod N is created only after pod N-1 is Running and Ready, rollouts go from the highest ordinal down, and scale-down removes the highest first. PVCs are kept when pods are deleted or the set is scaled down, so `pg-1` gets its old disk back (`persistentVolumeClaimRetentionPolicy` can change that). `podManagementPolicy: Parallel` turns off the ordering.

Run a database in Kubernetes when an operator handles failover, backups and upgrades (CloudNativePG for PostgreSQL, Strimzi for Kafka), when the team will own those procedures, and when the workload is many small databases or dev environments. Use RDS or Aurora when the database is the business-critical one or the team is small. The cost difference is real but smaller than the operational difference; the `stateful-backup-restore` problem puts numbers on it.

### Symptom to layer to command

| Symptom | Layer to suspect | Command |
| --- | --- | --- |
| Pod cannot reach a Service: connection refused | No ready endpoints: selector does not match labels, or readiness failing | `kubectl get endpointslices -l kubernetes.io/service-name=api -o wide` |
| Pod cannot reach a Service: timeout | NetworkPolicy, or targetPort wrong, or kube-proxy rules stale | `kubectl describe networkpolicy -n ns`; `kubectl get svc api -o yaml` (targetPort); `kubectl logs -n kube-system -l k8s-app=kube-proxy` |
| DNS fails or is slow, sometimes | ndots search churn, CoreDNS overloaded, UDP conntrack race | `kubectl exec POD -- cat /etc/resolv.conf`; `kubectl top pods -n kube-system -l k8s-app=kube-dns`; CoreDNS metrics `coredns_dns_request_duration_seconds` |
| Ingress returns 502 or 503 | Ingress backend name or port wrong, ALB targets unhealthy, pods not ready | `kubectl describe ingress shop` (events, address); `kubectl get svc,endpointslices -n shop`; ALB target group health in the AWS console |
| Ingress returns 404 | Host or path rule mismatch, wrong ingressClassName, two Ingresses claim the host | `kubectl get ingress -A`; `kubectl describe ingress shop` |
| PVC stays Pending | No default StorageClass, RWX asked from EBS, WaitForFirstConsumer waiting for a pod, subnet or zone has no capacity | `kubectl describe pvc pg-data` (events); `kubectl get storageclass` |
| Pod Pending with volume node affinity conflict | EBS volume is in a zone with no schedulable node | `kubectl get pv PV -o jsonpath='{.spec.nodeAffinity}'`; `kubectl get nodes -L topology.kubernetes.io/zone` |
| New pods stuck ContainerCreating, CNI error in events | Node out of ENI IPs | `kubectl describe node NODE` (allocatable pods); `aws-node` logs; enable prefix delegation |

## Diagram

Rendering diagram…

## Worked example

**Sizing pod IPs for an EKS node group and seeing why prefix delegation matters.** A team plans a node group of m5.large instances for 300 pods of a web application plus the usual DaemonSets (VPC CNI, kube-proxy, a log agent, a metrics agent: 4 per node).

Step 1, the limit without prefix delegation. An m5.large supports 3 ENIs with 10 IPv4 addresses each. The EKS formula is `(3 x (10 - 1)) + 2 = 29` pods per node. Two of those are the CNI and kube-proxy, which use the node's own IP, so 27 pods get pod IPs, and 2 of those 27 are the log and metrics agents. That leaves 25 application pods per node, and `300 / 25 = 12` nodes.

Step 2, what those nodes actually carry. An m5.large has 2 vCPU and 8 GiB. If each web pod requests 100m CPU and 128 MiB, 25 pods need 2.5 vCPU and 3.1 GiB. The CPU requests already exceed what the node has, so IPs are not the real limit here; CPU is. Pick 20 pods per node for CPU, so 15 nodes, and the IP cap of 29 never binds.

Step 3, change the pod to a small worker. Now each pod requests 50m CPU and 64 MiB. 25 pods need 1.25 vCPU and 1.6 GiB, so the node is less than half used and the IP cap of 29 is what stops us. 12 nodes run at about 60 percent CPU and 20 percent memory, paid for in full. This is the case for prefix delegation.

Step 4, with prefix delegation. Each ENI slot now holds a /28 (16 addresses), so one ENI slot gives what used to need 16 slots. The node is no longer IP-limited and EKS allows up to 110 pods on this instance size. With 110 pods per node, 300 pods need `ceil(300 / 110) = 3` nodes for IPs, but CPU would be `110 x 50m = 5.5` vCPU on a 2 vCPU node, so pick about 36 pods per node (`36 x 50m = 1.8` vCPU), which is `ceil(300 / 36) = 9` nodes instead of 12. The saving is 3 of 12 nodes, 25 percent of the node group, at the cost of needing contiguous /28 blocks in each subnet.

Step 5, the subnet. 9 nodes, each eventually holding up to 3 ENIs, each ENI with a handful of /28 prefixes. If the CNI keeps one spare prefix per ENI (`WARM_PREFIX_TARGET`, set to 1 in the add-on and Helm defaults), a node with 36 pods holds 3 prefixes in use plus 1 spare, 64 addresses, and 9 nodes consume 576 addresses plus 9 node IPs. A /24 subnet (251 usable addresses after the 5 AWS reserves) per zone is too small; a /22 (1019 usable) per zone leaves room for the node group to double. Subnet size is the decision people get wrong first and fix last, because changing it means new subnets and new nodes.

## Runnable code

Python · runs and prints its own checks

```
"""Two models of Kubernetes networking behaviour you cannot see from kubectl.

Part 1: how the resolver in a pod expands a name. A pod's /etc/resolv.conf has
a search list and 'options ndots:5'. The glibc resolver counts the dots in the
name: fewer than ndots means "try every search suffix first, then the name as
written". That is why 'db.example.com' costs four lookups from inside a pod.

Part 2: what the EndpointSlice controller does when a pod fails readiness.
kube-proxy only ever sees the slice, so a pod that fails its probe stops
receiving traffic within one controller sync, with no change to the Service.
"""

SEARCH = ["payments.svc.cluster.local", "svc.cluster.local", "cluster.local"]

def resolver_queries(name, search, ndots):
    """Return the ordered list of absolute names the resolver tries.

    A trailing dot means "this name is absolute, do not search". Otherwise,
    if the name has fewer than ndots dots, every search suffix is appended
    first and the bare name is tried last. With ndots or more dots the bare
    name goes first and the suffixes only follow if it fails.
    """
    if name.endswith("."):
        return [name]
    with_suffixes = [f"{name}.{s}." for s in search]
    if name.count(".") < ndots:
        return with_suffixes + [name + "."]
    return [name + "."] + with_suffixes

def queries_until_answer(name, search, ndots, exists):
    """Walk the list and stop at the first name that exists (NXDOMAIN otherwise)."""
    tried = []
    for q in resolver_queries(name, search, ndots):
        tried.append(q)
        if q in exists:
            return tried, q
    return tried, None

def show_table(ndots, names, exists):
    print(f"\nndots:{ndots}  search: {' '.join(SEARCH)}")
    print(f"{'name typed by the app':<34}{'queries':>8}  first query -> answer")
    for n in names:
        tried, hit = queries_until_answer(n, SEARCH, ndots, exists)
        first = tried[0]
        print(f"{n:<34}{len(tried):>8}  {first} -> {hit or 'NXDOMAIN after all suffixes'}")

def endpointslice_sync(pods):
    """Rebuild the slice the way the controller does: ready pods only, sorted."""
    return sorted(p["ip"] for p in pods if p["ready"] and not p["terminating"])

if __name__ == "__main__":
    # Names that really exist in DNS (fully qualified, with trailing dot).
    exists = {
        "api.payments.svc.cluster.local.",
        "db.example.com.",
    }
    names = ["api", "api.payments", "api.payments.svc.cluster.local.", "db.example.com"]

    show_table(5, names, exists)
    # Self-checks for the facts the lesson states.
    t, hit = queries_until_answer("api", SEARCH, 5, exists)
    assert len(t) == 1 and hit == "api.payments.svc.cluster.local."
    t, hit = queries_until_answer("db.example.com", SEARCH, 5, exists)
    assert len(t) == 4 and hit == "db.example.com."          # 3 wasted NXDOMAINs
    t, hit = queries_until_answer("db.example.com.", SEARCH, 5, exists)
    assert len(t) == 1                                        # trailing dot: no search

    print("\nthe same names with a trailing dot (absolute):")
    show_table(5, [n if n.endswith(".") else n + "." for n in names], exists)

    show_table(2, names, exists)
    t, hit = queries_until_answer("db.example.com", SEARCH, 2, exists)
    assert len(t) == 1                                        # 2 dots >= ndots:2
    t, hit = queries_until_answer("api.payments", SEARCH, 2, exists)
    assert len(t) == 2 and hit == "api.payments.svc.cluster.local."  # 1 dot < 2: search list first, second suffix hits
    print("\nwith ndots:2 an external name is one query; cluster names still resolve")
    print("note: each lookup above is doubled in practice (A and AAAA), so 4 becomes 8 packets")

    # ---- Part 2: EndpointSlice reacts to readiness ----
    print("\nEndpointSlice for Service payments/api as pods change readiness")
    pods = [
        {"name": "api-7d9f-a1", "ip": "10.0.1.11", "ready": True, "terminating": False},
        {"name": "api-7d9f-b2", "ip": "10.0.2.12", "ready": True, "terminating": False},
        {"name": "api-7d9f-c3", "ip": "10.0.1.13", "ready": True, "terminating": False},
    ]
    print("t=0s  all ready            ->", endpointslice_sync(pods))
    assert endpointslice_sync(pods) == ["10.0.1.11", "10.0.1.13", "10.0.2.12"]

    pods[1]["ready"] = False  # readiness probe failed 3 times (failureThreshold 3)
    print("t=30s b2 fails readiness   ->", endpointslice_sync(pods), "(kube-proxy drops 10.0.2.12 from its rules)")
    assert "10.0.2.12" not in endpointslice_sync(pods)

    pods[1]["ready"] = True
    print("t=45s b2 passes again      ->", endpointslice_sync(pods))

    pods[2]["terminating"] = True  # rollout deleted it: deletionTimestamp set, still Running
    print("t=60s c3 is terminating    ->", endpointslice_sync(pods), "(terminating endpoints get no new traffic)")
    assert endpointslice_sync(pods) == ["10.0.1.11", "10.0.2.12"]

    for p in pods:
        p["ready"] = False
    print("t=90s nobody ready         ->", endpointslice_sync(pods), "(empty slice: clients see connection refused)")
    assert endpointslice_sync(pods) == []
    print("\nall checks passed: the Service never changed; only the slice did")
```

## Key takeaways

* Every pod has its own IP and pods talk without NAT; the CNI plugin makes that true. On EKS the VPC CNI hands out real VPC IPs, which caps pods per node by ENI limits unless prefix delegation is on.
* A ClusterIP is a virtual IP that exists only as rules on every node, built by kube-proxy (or Cilium eBPF) from EndpointSlices, which contain only pods that pass readiness.
* Cluster DNS is `name.namespace.svc.cluster.local`; with `ndots:5` an external name costs four lookups, so use trailing dots or lower ndots, and run NodeLocal DNSCache.
* The Ingress API is frozen and ingress-nginx is retired; new platforms use Gateway API (GatewayClass, Gateway, HTTPRoute) or the AWS Load Balancer Controller, which supports both.
* NetworkPolicy only works when the CNI enforces it; start with deny-all plus an allow-DNS rule, then add specific ingress and egress rules.
* EBS is ReadWriteOnce and lives in one zone; use `WaitForFirstConsumer` so the volume follows the pod, and EFS when many nodes must write the same files.
* StatefulSets give stable names, ordered rollout and one PVC per pod through a headless Service; run a database there only with a mature operator and a team that will own it, otherwise use RDS.

## Common mistakes

* Applying a default-deny NetworkPolicy without an allow rule for DNS to kube-system, which makes every connection time out instead of being refused and sends people to look at the wrong layer.
* Asking for `ReadWriteMany` from an EBS StorageClass and waiting for a Pending PVC that will never bind.
* Using `volumeBindingMode: Immediate` with EBS, so the volume lands in a zone before the pod is scheduled and the pod cannot be placed.
* Starting a new platform on ingress-nginx in 2026, after the project was retired without further security fixes.
* Expecting a NetworkPolicy to do something on a cluster whose CNI does not enforce it; the object is accepted silently.
* Debugging "Service unreachable" by restarting pods instead of checking whether the EndpointSlice is empty and why.

## Practice

* On kind or minikube, create a Deployment with a readiness probe that checks a file, and a Service for it. Watch `kubectl get endpointslices -w` while you create and delete the file in one pod with `kubectl exec`; time how long the IP takes to leave and return.
* Run `kubectl exec POD -- cat /etc/resolv.conf`, then use `kubectl exec POD -- nslookup -debug db.example.com` (busybox) or `dig +search` and count the queries; set `dnsConfig.options ndots: "2"` on the pod and count again.
* Apply the four NetworkPolicies from this lesson to a namespace with two pods and prove with curl from a debug pod which paths work; then delete `allow-dns` and observe timeouts instead of refusals.
* With the EBS CSI driver on a small EKS cluster (or the local-path provisioner on kind), create the StorageClass and PVC from the lesson, mount it in a StatefulSet of 2 replicas, write a file in `pg-1`, delete the pod and confirm the file is still there when `pg-1` returns.

## Interview questions (11)

1.What happens, step by step, when a pod sends a request to a ClusterIP Service?Medium

The application resolves the Service name through CoreDNS and gets the ClusterIP, which is a virtual address that no interface owns. The packet leaves the pod and hits the node's kube-proxy rules, iptables or IPVS, or Cilium's eBPF program at the socket level. Those rules were built from the Service's EndpointSlices, which list the pod IPs that currently pass readiness. One backend is picked, the destination is rewritten to that pod IP and targetPort, and the packet is routed to the pod, on the same node or across the CNI network, with no source NAT. The reply comes back the same way with the rewrite undone. So if the EndpointSlice is empty, the connection is refused, and if a NetworkPolicy blocks the path, it times out.

2.A pod can resolve external names but every call to them is slow. What is going on?Medium

Almost certainly ndots. The pod's resolv.conf has `ndots:5` and three search suffixes, so a name like `api.stripe.com`, with only two dots, is first tried as `api.stripe.com.payments.svc.cluster.local`, then with the other two suffixes, and only then as itself. That is four lookups, eight with AAAA, each a round trip to CoreDNS, and under load some of them time out. The fixes are to use fully qualified names with a trailing dot, to set `dnsConfig.options ndots: "2"` for that workload, and to run NodeLocal DNSCache so lookups are answered on the node over TCP. I would confirm with `cat /etc/resolv.conf` in the pod and the CoreDNS request duration metrics.

3.What does a CNI plugin do, and why does the VPC CNI limit pods per node?Medium

When kubelet creates a pod it calls the CNI plugin to create the pod's network interface, assign an IP and set up routing so the pod can reach every other pod without NAT. The VPC CNI assigns real VPC addresses from the node's ENIs, which makes pods first-class in the VPC, so an ALB can target them directly and security groups and flow logs understand them. The cost is that an instance type has a fixed number of ENIs and IPs per ENI; the formula is ENIs times IPs-per-ENI minus one, plus two. An m5.large gets 29. Prefix delegation assigns a /28 per ENI slot instead of one IP and raises that to the EKS cap of 110 for small instances, as long as the subnet has contiguous free blocks.

4.Compare Ingress and Gateway API. Which would you pick for a new platform?Medium

Ingress is one object per application that maps host and path to a Service, with everything else, timeouts, rewrites, canaries, done through controller-specific annotations. The Ingress API is now frozen and ingress-nginx was retired in early 2026, so the Kubernetes project recommends Gateway API. Gateway API splits the roles: the platform team owns the GatewayClass and the Gateway with its listeners and TLS, and application teams attach HTTPRoutes from their own namespaces, with typed fields for header matching, weighted backends and filters. GatewayClass, Gateway and HTTPRoute have been GA for years and the AWS Load Balancer Controller, Cilium and Envoy Gateway implement it. For a new platform I would pick Gateway API and keep Ingress only for applications that already ship one.

5.An Ingress returns 502. What do you check, in order?Hard

A 502 means the proxy or ALB reached the backend and got a bad response or no connection. First `kubectl describe ingress`: does it have an address, do the events show the controller accepted it, does the backend name and port match a Service in the same namespace. Then `kubectl get endpointslices` for that Service: if it is empty, the pods are not ready or the selector is wrong, and I look at the readiness probe and the pod logs. If endpoints exist, I check that the Service targetPort is the port the container listens on and that it binds to 0.0.0.0, by curling a pod IP from a debug pod. With the ALB in ip mode I check the target group health in AWS; unhealthy targets usually mean the health check path or a security group on the node. Last, NetworkPolicy: a deny-all without an allow from the ALB subnets gives exactly this.

6.Why does an EBS-backed pod get stuck Pending after a node failure, and how do you design around it?Hard

An EBS volume lives in one availability zone and the PV carries a node affinity for that zone. When the node dies, the replacement pod must land in the same zone; if that zone has no node with room, or the autoscaler brings up a node elsewhere, the pod stays Pending with a volume node affinity conflict. The volume may also still be attached to the dead instance, giving a Multi-Attach error until it is detached. To design around it: use `WaitForFirstConsumer` so the first placement is sane, keep spare capacity or a node group in every zone where you have volumes, take regular VolumeSnapshots so data can be restored in another zone, use topology spread so replicas of a StatefulSet sit in different zones with their own volumes, and for truly critical data prefer a managed service that replicates across zones for you.

7.When would you run a database in Kubernetes and when would you use RDS?Medium

I run it in the cluster when there is a mature operator such as CloudNativePG or Strimzi that does failover, backups, point-in-time recovery and upgrades, when the team is willing to own those procedures and test restores, and when the use case is many small databases, preview environments or something RDS does not offer. I use RDS or Aurora when the database is the business-critical system, when the team is small or has no database experience, and when the cost difference is smaller than the on-call cost of running it. The honest answer is that storage in Kubernetes is reliable now, but the operational work does not disappear; it moves to you.

8.Write a NetworkPolicy strategy for a namespace from scratch.Medium

Start with a deny-all policy that selects every pod and lists both Ingress and Egress in policyTypes, so nothing is allowed by default. Immediately add an egress rule to kube-dns in kube-system on port 53 UDP and TCP, otherwise nothing resolves. Then one ingress rule per application: allow from the namespaces that call it, and from the ingress proxy's pods or the ALB subnet CIDR if the ALB targets pods directly. Then egress rules for what each app needs: the database CIDR on 5432, another namespace's Service, and a 0.0.0.0/0 rule only for the pods that genuinely call the internet. Verify with a debug pod on both sides, and remember the CNI must enforce policies, which on EKS means enabling it on the VPC CNI or running Cilium.

9.What is a headless Service and why does a StatefulSet need one?Easy

A headless Service has `clusterIP: None`. It gets no virtual IP and kube-proxy ignores it; instead DNS for the Service name returns the IPs of all the pods behind it, and each pod gets its own stable record, like `pg-0.pg.payments.svc.cluster.local`. A StatefulSet names that Service in `serviceName` so each ordinal pod has an address that survives restarts, which is how database replicas find the primary and each other. A normal Service would hide the individual pods behind one load-balanced IP, which is exactly what replication and leader election cannot use.

10.What is the difference between a PV, a PVC and a StorageClass?Easy

A PersistentVolume is a piece of storage the cluster knows about, like a 100 GiB EBS volume, with a capacity, access modes and a reclaim policy. A PersistentVolumeClaim is a request from a namespace for storage of a size and access mode; a pod mounts the claim, not the volume. A StorageClass is the recipe for creating a volume when a claim has no matching PV: it names the CSI driver, such as ebs.csi.aws.com, and parameters like type gp3 and encryption, and it sets reclaim policy, expansion and binding mode. The claim stays Pending until a volume binds to it, and the reclaim policy decides whether the volume is deleted or kept when the claim goes away.

11.What does kube-proxy do and what does Cilium change?Medium

kube-proxy runs on every node, watches Services and EndpointSlices, and writes kernel rules so that a packet to a ClusterIP is rewritten to one ready pod IP. In iptables mode that is a chain of rules per Service with random selection, which is fine for most clusters but slow to update with tens of thousands of endpoints; IPVS mode uses a hash table and real schedulers but is deprecated; nftables mode is the planned future default. Cilium removes kube-proxy and does the same job in eBPF, usually at the socket layer, so the application's connect call is pointed at the backend pod directly and no packet rewrite is needed. It also gives network policy up to layer 7 and Hubble flow logs, which is why it is the common choice when teams outgrow the default plugin.

## Quiz

1.A pod in namespace payments calls db.example.com with the default resolv.conf. How many DNS lookups happen before the right answer, ignoring AAAA?

2.Which access mode can an EBS volume provide?

3.You apply a NetworkPolicy and nothing changes; all traffic still flows. What is the most likely reason?

4.Why is volumeBindingMode WaitForFirstConsumer recommended for EBS StorageClasses?

5.In 2026, which statement about exposing HTTP on a new cluster is correct?

## Practice these problems

* [DESIGNBackup and restore for stateful workloads on KubernetesMedium](/devops/problems/stateful-backup-restore)
* [OPSPods Pending and ImagePullBackOff after a node group changeEasy](/devops/problems/pod-pending-imagepullbackoff)
* [OPS502 from the ingress while the service works inside the clusterMedium](/devops/problems/ingress-502-service-unreachable)
* [OPSIntermittent DNS resolution failures in the clusterHard](/devops/problems/intermittent-dns-failures)
* [CODEKubernetes manifests: Deployment, Service, Ingress and HPA with probes and limitsMedium](/devops/problems/kubernetes-manifests-web-app)

## Further reading

* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)
* [Kubernetes: Gateway APIGuidegateway-api.sigs.k8s.io](https://gateway-api.sigs.k8s.io/)
* [Amazon EKS best practices guideGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html)
* [Cilium documentationGuidedocs.cilium.io](https://docs.cilium.io/en/stable/)
* [Design Patterns for Container-based Distributed SystemsPaperusenix.org](https://www.usenix.org/conference/hotcloud16/workshop-program/presentation/burns)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousKubernetes architecture and core objects](/devops/learn/kubernetes-architecture-core-objects)[NextKubernetes in production - resources, autoscaling, RBAC, upgrades, EKS](/devops/learn/kubernetes-in-production)

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

1. [The networking model and the CNI plugin](#the-networking-model-and-the-cni-plugin)
2. [Services under the hood](#services-under-the-hood)
3. [DNS: how a name becomes an address](#dns-how-a-name-becomes-an-address)
4. [Exposing HTTP: Ingress, Gateway API and the AWS Load Balancer Controller](#exposing-http-ingress-gateway-api-and-the-aws-load-balancer-controller)
5. [NetworkPolicy: who may talk to whom](#networkpolicy-who-may-talk-to-whom)
6. [Storage: from emptyDir to EBS](#storage-from-emptydir-to-ebs)
7. [StatefulSets and the database question](#statefulsets-and-the-database-question)
8. [Symptom to layer to command](#symptom-to-layer-to-command)
