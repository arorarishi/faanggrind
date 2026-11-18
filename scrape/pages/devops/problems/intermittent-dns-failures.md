# Intermittent DNS resolution failures in the cluster — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/intermittent-dns-failures

[DevOps problems](/devops#problems)

OPSTroubleshooting#29Hard

# Intermittent DNS resolution failures in the cluster

kubernetescorednsdnsnetworkingconntracktroubleshooting

## Problem statement

It is 14:20. The checkout team pages: about 2 percent of calls from `checkout-api` to `payments.payments.svc.cluster.local` and to `api.stripe.com` fail with `getaddrinfo EAI_AGAIN` or take exactly 5 seconds and then succeed. Their error log shows `Error: getaddrinfo EAI_AGAIN api.stripe.com` 1,840 times in the last hour. Nothing in the service changed. The platform team grew the cluster from 120 to 400 nodes over the last two weeks for a new batch workload. Find what is failing in the DNS path, fix it, and make the cluster's DNS safe at 400 nodes and beyond.

## Requirements

### Functional

* Explain the DNS path from a pod to an answer: the pod's resolv.conf, the search list and ndots, the kube-dns Service, kube-proxy, CoreDNS, the upstream resolver.
* Measure, not guess: query rate, error rate and latency from CoreDNS metrics, CPU throttling of the CoreDNS pods, conntrack insert failures on nodes, and the exact query pattern from a packet capture inside one pod.
* Name one root cause the evidence leads to, and rule out the other candidates with a number each.
* Restore the failure rate to under 0.01 percent and p99 lookup latency under 20 ms without restarting application pods.
* Make DNS capacity follow cluster size automatically and alert before it is exhausted again.

### Non-functional

* Time to a confirmed cause under 45 minutes using metrics, one packet capture and kubectl.
* The 5-second stalls hit 2 percent of 300 requests per second, so about 6 user requests a second are slow or failing; the error budget for checkout is 0.05 percent per 30 days and it is burning 40 times faster than allowed.
* No change to application code or pod restarts during the fix; blast radius of each step is the `kube-system` DNS deployment, rolled with `maxUnavailable: 1`.
* After the fix: CoreDNS CPU throttling under 1 percent of periods, p99 latency under 20 ms, SERVFAIL rate under 0.01 percent.
* Capacity rule written down: DNS replicas scale with nodes and cores, and an alert fires at 70 percent of measured capacity.

## Back-of-the-envelope estimates

**Query volume.** 400 nodes run about 6,000 pods; the average pod does 1 name lookup a second, so 6,000 lookups a second. With `ndots:5` an external name like `api.stripe.com` (2 dots, fewer than 5) is tried with each of the 4 search suffixes before it is tried as written: 5 names, and glibc and Node send A and AAAA for each, so 10 packets. A short in-cluster name like `payments` hits on the first suffix: 2 packets. If 40 percent of lookups are external: 2,400 x 10 + 3,600 x 2 = 31,200 DNS queries a second. Two CoreDNS replicas share that: 15,600 each. Two weeks ago at 120 nodes and 1,800 pods it was 1,800 x (0.4 x 10 + 0.6 x 2) = 9,360 a second, 4,680 per replica. With `ndots:2` the external names stop expanding and the total drops to 2,400 x 2 + 7,200 = 12,000 a second. The cluster-proportional rule of 1 replica per 16 nodes gives 400 / 16 = 25 replicas, not 2.

## API

```
# 1. What is the DNS path from inside the pod? The search list and ndots decide the query count.
kubectl exec -n checkout deploy/checkout-api -- cat /etc/resolv.conf
# search checkout.svc.cluster.local svc.cluster.local cluster.local ec2.internal
# nameserver 10.100.0.10
# options ndots:5

# 2. Is the cluster DNS Service healthy and how many backends does it have?
kubectl get svc -n kube-system kube-dns -o wide
kubectl get endpointslice -n kube-system -l kubernetes.io/service-name=kube-dns
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide
# coredns-7d5b8c6f9-abc12  1/1 Running  ...  2 replicas for 400 nodes

# 3. What do the CoreDNS pods ask for and what are they allowed?
kubectl get deploy -n kube-system coredns -o jsonpath='{.spec.template.spec.containers[0].resources}{"\n"}'
# {"limits":{"cpu":"100m","memory":"170Mi"},"requests":{"cpu":"100m","memory":"70Mi"}}

# 4. Are they throttled? cAdvisor counters through the kubelet, or the same PromQL in Grafana.
#    rate(container_cpu_cfs_throttled_periods_total{container="coredns"}[5m])
#      / rate(container_cpu_cfs_periods_total{container="coredns"}[5m])
#    -> 0.71   (71 percent of 100 ms periods are throttled)

# 5. CoreDNS metrics: rate, errors, latency. Port 9153 on the pod.
kubectl port-forward -n kube-system deploy/coredns 9153:9153 &
curl -s localhost:9153/metrics | grep -E '^coredns_dns_(requests|responses)_total|^coredns_dns_request_duration_seconds_count'
#   sum(rate(coredns_dns_requests_total[5m]))                       31k/s
#   sum(rate(coredns_dns_responses_total{rcode="SERVFAIL"}[5m]))      40/s
#   histogram_quantile(0.99, sum(rate(coredns_dns_request_duration_seconds_bucket[5m])) by (le))   1.9 s

# 6. Conntrack on the node that runs the pod: insert failures mean the UDP race.
NODE=$(kubectl get pod -n checkout -l app=checkout-api -o jsonpath='{.items[0].spec.nodeName}')
kubectl debug node/$NODE -it --image=busybox --profile=sysadmin -- \
  sh -c 'cat /proc/sys/net/netfilter/nf_conntrack_count /proc/sys/net/netfilter/nf_conntrack_max; cat /proc/net/stat/nf_conntrack | head -2'
# 61240  262144
# entries ... insert_failed 0000001a ...   <- 26 total since boot: real but small

# 7. The exact query pattern: capture inside the pod's network namespace.
kubectl debug -n checkout checkout-api-6f9d7c8b5-x2k4p -it --image=nicolaka/netshoot \
  --target=checkout-api --profile=netadmin -- tcpdump -ni any udp port 53 -c 40
# 14:31:02.101 IP 10.0.14.7.41022 > 10.100.0.10.53: A? api.stripe.com.checkout.svc.cluster.local.
# 14:31:02.101 IP 10.0.14.7.41022 > 10.100.0.10.53: AAAA? api.stripe.com.checkout.svc.cluster.local.
# ... svc.cluster.local, cluster.local, ec2.internal, then api.stripe.com.
# 14:31:07.103 IP 10.0.14.7.41022 > 10.100.0.10.53: A? api.stripe.com.cluster.local.   <- retransmit after 5 s
```

## Data model

```
Pod side (decides how many queries one lookup makes)
  /etc/resolv.conf   search <ns>.svc.cluster.local svc.cluster.local cluster.local <vpc suffix>
                     options ndots:5         names with < 5 dots try every suffix first
                     glibc timeout default 5 s, attempts default 2, A and AAAA in parallel
  pod.spec.dnsPolicy       ClusterFirst (default) | Default | None | ClusterFirstWithHostNet
  pod.spec.dnsConfig.options   [{name: ndots, value: "2"}]   per-pod override

Cluster DNS
  Service kube-dns (kube-system)   ClusterIP 10.100.0.10, ports 53/UDP, 53/TCP, 9153/TCP metrics
  EndpointSlice for kube-dns      the CoreDNS pod IPs; how many backends there are
  Deployment coredns              replicas, resources.limits.cpu, Corefile ConfigMap "coredns"
  Corefile plugins                kubernetes (ttl), cache, forward (to /etc/resolv.conf), prometheus :9153,
                                  autopath @kubernetes (needs pods verified), log for debugging

Metrics that decide the diagnosis
  coredns_dns_requests_total{proto,type}                     rate; split udp/tcp and A/AAAA
  coredns_dns_responses_total{rcode}                         SERVFAIL, NXDOMAIN share
  coredns_dns_request_duration_seconds_bucket                p99 latency
  coredns_forward_max_concurrent_rejects_total               upstream concurrency cap hit
  coredns_proxy_request_duration_seconds{to}                 upstream resolver latency
  container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total   CPU limit throttling
  node_nf_conntrack_entries / node_nf_conntrack_entries_limit, node_nf_conntrack_stat_insert_failed

Node
  /proc/net/stat/nf_conntrack   insert_failed column: the UDP DNAT race
  nf_conntrack_max, nf_conntrack_udp_timeout (30 s default)
```

## Diagnosis and fix

1. **Scope.** The CoreDNS SERVFAIL rate and p99 latency (command 5) are cluster-wide, so this is everyone, and checkout noticed first because it calls an external API on every request. Say so in the incident channel before other teams page.
2. **Read the pod's resolv.conf.** `ndots:5` and a 4-entry search list (command 1). The capture (command 7) shows what that means: one lookup of `api.stripe.com` sends 10 packets, 8 answered NXDOMAIN, and a retransmit exactly 5 seconds after an unanswered query. The 5 seconds is the resolver timeout, not a slow server.
3. **Check the server side.** Two CoreDNS replicas (command 2) with a `100m` CPU limit (command 3) serve 31,000 queries a second. Throttling is 71 percent of CFS periods (command 4). p99 is 1.9 seconds and SERVFAIL is 40 a second, mostly the `forward` plugin timing out because the throttled process cannot read upstream replies in time.
4. **Rule out the rest with numbers.** Conntrack: 61,000 of 262,144 entries and 26 `insert_failed` since boot on the busiest node; the UDP race exists but cannot explain 1,840 errors an hour. Upstream: `coredns_proxy_request_duration_seconds` p99 to the VPC resolver is 4 ms when unthrottled, and the resolver's 1,024 packets per second limit is far away because CoreDNS caches external answers. kube-proxy: both pods in the EndpointSlice, both DNAT targets in `iptables-save`. Application: no change, and the capture shows a correct resolver with a bad configuration.
5. **Root cause.** CoreDNS is CPU-throttled by a 100m limit on 2 replicas after the node count grew 3.3 times, and `ndots:5` multiplies every external lookup by 5; queries dropped under throttling become 5-second client timeouts and `EAI_AGAIN`.
6. **Fix through the proper path.** First, the CoreDNS add-on values in the platform repo: `replicas: 6`, CPU limit removed (request stays `100m`), rolled with `maxUnavailable: 1`; throttling and SERVFAIL drop to 0 within 5 minutes. Second, enable the add-on's autoscaling (`autoScaling.enabled: true`, `minReplicas: 4`, `maxReplicas: 30`) so replicas follow nodes and cores. Third, NodeLocal DNSCache as a DaemonSet on `169.254.20.10`: each node answers from its own cache and forwards misses over TCP, which removes the UDP race and most cross-node DNS traffic. Fourth, in the checkout chart, `dnsConfig.options: ndots: "2"` and a trailing dot on known external hosts (`api.stripe.com.`).
7. **Verify.** `EAI_AGAIN` count 0 for 15 minutes; 2 packets per external lookup in a capture; CoreDNS p99 under 10 ms; throttled periods under 1 percent; `insert_failed` not increasing.
8. **Prevent.** Alerts on CoreDNS p99 over 100 ms for 5 minutes, SERVFAIL over 0.1 percent, throttling over 5 percent, conntrack over 70 percent of the limit. A platform rule: cluster-wide add-ons are autoscaled by node count and carry no CPU limit.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why one lookup becomes ten packets

The kubelet writes a `resolv.conf` into every `ClusterFirst` pod with a search list of the namespace, `svc.cluster.local`, `cluster.local` and the node's own suffixes, plus `options ndots:5`. The resolver rule is: if the name has fewer than `ndots` dots, try it with each search suffix appended first, and only then as written. `api.stripe.com` has 2 dots, so it is tried as `api.stripe.com.checkout.svc.cluster.local`, then `.svc.cluster.local`, `.cluster.local`, `.ec2.internal`, and finally `api.stripe.com`. glibc and Node send an A and an AAAA query for each, in parallel on the same socket: 10 packets, 8 NXDOMAIN answers, and every one of them is work for CoreDNS. The design makes `payments` resolve from inside the `payments` namespace in one try, which is the point of `ndots:5`, and it is the right default for in-cluster names. It is the wrong default for a service that calls external APIs. `ndots:2` in `dnsConfig` makes any name with 2 or more dots go out as written; a trailing dot (`api.stripe.com.`) marks a fully qualified name and skips the search list no matter what `ndots` says. CoreDNS's `autopath` plugin does the same expansion on the server side in one round trip, but it needs `pods verified`, which watches every pod and costs memory, so it is a second choice.

### The 5-second stall and the UDP conntrack race

DNS over UDP has no acknowledgement. The glibc default is `timeout:5` and `attempts:2`: send, wait 5 seconds, send again, and after both fail return `EAI_AGAIN`. A single dropped packet therefore costs exactly 5 seconds, which is why "exactly 5 seconds" in a bug report means a lost UDP packet, not a slow server. Packets get lost in two places. The first is a busy CoreDNS pod whose socket buffer overflows while it is throttled. The second is the kernel: the kube-dns ClusterIP is a DNAT rule, and when the A and AAAA queries leave the same socket in the same microsecond, two conntrack entries race for the same tuple and one insert fails, which drops the packet. `insert_failed` in `/proc/net/stat/nf_conntrack` counts exactly that. The classic workarounds, `single-request-reopen` in `resolv.conf` or forcing TCP, fix the race in the client; NodeLocal DNSCache fixes it for everyone by answering on a link-local address on the same node without DNAT, and by forwarding misses to CoreDNS over TCP, where conntrack entries close with the connection. In this incident `insert_failed` was 26 since boot, so the race was real but not the cause; it would have become the cause after the throttling was fixed, which is why NodeLocal DNSCache is still in the fix list.

### CPU limits on a latency-critical daemon

A CPU limit of `100m` is a CFS quota of 10 ms per 100 ms period. When CoreDNS needs 70 ms of CPU in a period it runs for 10 ms, is paused for 90 ms, and every query that arrived in the pause waits. Throttling does not show up as errors in CoreDNS's own log; it shows up as latency, then as full UDP buffers, then as the `forward` plugin timing out on upstream replies it could not read in time, which is the SERVFAIL. The counter pair `container_cpu_cfs_throttled_periods_total` and `container_cpu_cfs_periods_total` is the direct evidence; a ratio over 20 percent on any serving container is a problem, and 71 percent is an outage. The fix is to keep the request (so the scheduler reserves the cores) and drop or raise the limit well above the measured need, then let the replica count, not the per-pod ceiling, provide capacity. The cluster-proportional autoscaler and the EKS add-on's `autoScaling` both compute replicas as the larger of nodes divided by 16 and cores divided by 256, which would have given 25 replicas here.

### Symptoms and the cause each one points to

| Symptom | Most likely cause | Confirming evidence |
| --- | --- | --- |
| Exactly 5 s delay, then success | A dropped UDP packet and the resolver timeout | Retransmit 5 s later in the pod capture |
| `EAI_AGAIN` or `SERVFAIL` after 10 s | Both attempts dropped, or CoreDNS forward timeout | `coredns_dns_responses_total{rcode="SERVFAIL"}` rising |
| Only external names slow | ndots expansion, or the upstream resolver | 10 packets per lookup in the capture; `coredns_proxy_request_duration_seconds` |
| Only one node's pods affected | Conntrack table full or the DNAT race on that node | `nf_conntrack_count` near `nf_conntrack_max`, `insert_failed` increasing |
| Everything slow after cluster growth | CoreDNS under-provisioned or throttled | Throttled-period ratio, p99 from CoreDNS, replica count vs nodes |
| NXDOMAIN for a real Service | Wrong namespace or search list, `dnsPolicy: Default` | `resolv.conf` in the pod, `nslookup payments.payments` |
| Works with IP, fails with name, hostNetwork pod | `ClusterFirst` on host network uses the node's resolver | `dnsPolicy: ClusterFirstWithHostNet` |

## Evaluation

**Did you find it?** The write-up says: "CoreDNS is throttled at 71 percent of CFS periods under a 100m limit on 2 replicas after the cluster grew from 120 to 400 nodes, and `ndots:5` turns every external lookup into 10 queries; dropped queries become 5-second resolver timeouts and `EAI_AGAIN`." Each other candidate has its number: 26 conntrack insert failures since boot, 4 ms upstream p99, both kube-dns endpoints present, no application change.

**Is it fixed?** Fifteen minutes after the CoreDNS rollout: throttled ratio under 1 percent, p99 under 10 ms, SERVFAIL 0, and `checkout-api` logs 0 `EAI_AGAIN`. After the `ndots` change a capture shows 2 packets per external lookup. After NodeLocal DNSCache, `coredns_dns_requests_total` on the central pods drops by more than half and node `insert_failed` stops increasing.

**Is it prevented?** DNS replicas follow node count through the autoscaler; alerts on CoreDNS p99, SERVFAIL, throttling and conntrack usage; a written rule that cluster-wide add-ons carry no CPU limit; the `ndots:2` setting in the base Helm chart for services that call external APIs.

**What a strong answer adds.** The ten-packet arithmetic for `ndots:5`; "exactly 5 seconds means a lost UDP packet"; the A and AAAA conntrack race and why NodeLocal DNSCache forwards over TCP; throttling as latency rather than errors; the 1 replica per 16 nodes rule; `autopath` and its `pods verified` cost; the trailing dot; and the point that the batch workload that grew the cluster also multiplied lookups.

**What a weak answer does.** Restarts CoreDNS, raises the limit to 200m without measuring, or tells the checkout team to add retries, and never captures a packet to see what the resolver is actually sending.

## Bottlenecks & mitigations

* Two CoreDNS replicas for 400 nodes: the central DNS path is the one shared dependency every pod has, and it was sized for a cluster a third the size.
* `ndots:5` with a four-entry search list: four wasted round trips per external name, multiplied by every pod that talks to the internet.
* UDP through DNAT: the conntrack race and the 5-second timeout make a 0.1 percent drop rate visible to users.
* The VPC resolver's 1,024 packets per second per interface limit: a node with many external lookups and a short cache can hit it, and the failure looks the same as a CoreDNS problem.
* Distroless application images: no `dig`, `nslookup` or `tcpdump`, so every capture needs an ephemeral container with `--target`.

## Failure modes

* **CoreDNS CPU limit too low after growth.** Throttling turns into latency, then dropped packets. Mitigation: no CPU limit on cluster-wide daemons, an autoscaler keyed on node count, a throttling alert.
* **ndots:5 for an internet-facing service.** Five names per lookup, most of them NXDOMAIN. Mitigation: `ndots:2` in `dnsConfig`, trailing dots on known hosts, or `autopath`.
* **UDP conntrack race.** A and AAAA on the same socket collide in DNAT and one is dropped. Mitigation: NodeLocal DNSCache, which skips DNAT locally and uses TCP upstream.
* **Conntrack table full.** New flows are dropped on the whole node, not only DNS. Mitigation: alert at 70 percent of `nf_conntrack_max`, raise it on large nodes, shorter UDP timeouts.
* **CoreDNS rollout with all pods unavailable.** A bad Corefile or a rollout with `maxUnavailable: 100%` takes down DNS for everyone. Mitigation: `maxUnavailable: 1`, a PodDisruptionBudget, `lameduck` in the health plugin, `kubectl rollout status` before the next step.
* **Upstream resolver limit.** Many external names with short TTLs exceed the VPC resolver packet limit per interface. Mitigation: `cache` with a sensible TTL, NodeLocal cache, fewer unique names.
* **Application retries without a timeout.** A 5-second DNS stall times out the request before the retry starts. Mitigation: connection pools that reuse resolved addresses, resolver timeouts shorter than the request timeout.
* **Debugging by restarting CoreDNS.** The restart empties the cache and doubles the load for a minute. Mitigation: metrics first; restart only to pick up a verified configuration change.

## Follow-up questions interviewers ask

* The throttling ratio is 0 and p99 is 5 ms, but one node's pods still see 5-second stalls. What do you check on that node and what fixes it?
* A pod uses `hostNetwork: true` and cannot resolve Services. Why, and which field fixes it?
* After NodeLocal DNSCache is deployed, how does a pod find the local cache, and what happens when the DaemonSet pod on that node restarts?
* The team wants `autopath` instead of `ndots:2`. What does it cost and when would you refuse?
* External lookups fail only on the nodes running the batch workload. How does the VPC resolver limit show up and how do you confirm it?
* Write the four alerting rules in PromQL, with thresholds and `for` durations, and say who gets paged for each.

## Lessons that cover this

* [#4Networking for DevOps - TCP/IP, DNS, HTTP, TLS, SSHFoundations](/devops/learn/networking-for-devops)
* [#16Kubernetes networking and storageKubernetes](/devops/learn/kubernetes-networking-storage)
* [#22Troubleshooting playbook - Linux, Docker, Kubernetes, network, pipelinesOperate](/devops/learn/troubleshooting-playbook)

## Further reading

* [Kubernetes: Debug PodsGuidekubernetes.io](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)
* [The Tail at ScalePaperresearch.google](https://research.google/pubs/the-tail-at-scale/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousCI pipeline became slow and flaky](/devops/problems/slow-flaky-ci-pipeline)[NextTerraform plan wants to destroy the production database](/devops/problems/terraform-wants-to-destroy-db)

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
