# Troubleshooting playbook - Linux, Docker, Kubernetes, network, pipelines — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/troubleshooting-playbook

[DevOps roadmap](/devops)

OperateLesson #22StudyIntermediate 4.5 h

# Troubleshooting playbook - Linux, Docker, Kubernetes, network, pipelines

Troubleshooting is a method, not a list of commands. Scope the damage, protect users before you understand the cause, follow the request path to the first broken contract, test one hypothesis with one command, change one thing at a time, and write down what you did. This lesson gives that method and then five dense playbooks (Linux host, containers, Kubernetes, networking, pipelines) where every row has a symptom, likely causes, a real first command, the evidence that confirms it, and the fix.

troubleshootingkuberneteslinuxnetworkingkubectl debugincidentson-call

## Why it matters

Every DevOps and SRE interview has a "something is broken, what do you do" round, and the interviewer is not scoring whether you know the answer. They are scoring whether you ask who is affected before touching anything, whether you roll back before you debug, whether your next command follows from the last output, and whether you can say "I would check X because Y" instead of "I would restart it". The same habits decide whether a real 02:00 page lasts ten minutes or three hours. Candidates from service companies are asked the Kubernetes rows of this lesson directly: CrashLoopBackOff, ImagePullBackOff, Pending, a Service with no endpoints.

Read first: [Linux for operators](/devops/learn/linux-for-operators), [Networking for DevOps - TCP/IP, DNS, HTTP, TLS, SSH](/devops/learn/networking-for-devops), [Containers and Docker](/devops/learn/containers-and-docker), [Kubernetes networking and storage](/devops/learn/kubernetes-networking-storage), [Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKS](/devops/learn/kubernetes-in-production), [Observability - Prometheus, Grafana, OpenTelemetry, logs and alerting](/devops/learn/observability-prometheus-grafana-otel)

## Lesson

### The method: six moves, in order

1. **Scope the impact.** Who, how many, since when, getting worse? One dashboard answers this: error rate and latency per service, split by region and version. "Since when" is the most useful fact you will get, because it narrows "what changed" to a window.
2. **Protect users before you diagnose.** If a rollback, failover, scale-up or feature flag can stop the bleeding, do it now and study the broken version afterwards with no traffic on it. A rollback that does not help is evidence too.
3. **Follow the request path to the first broken contract.** Every hop promises something to the next: DNS returns an IP, the load balancer has healthy targets, the Service has endpoints, the pod is Ready, the app returns 200, the database accepts connections. Stop at the first hop that breaks its promise. Everything after it is a symptom.
4. **One hypothesis, one command.** "The pod is not Ready because the readiness path needs the database and the database is full." Test: `kubectl describe pod` shows the probe failing with that error. A hypothesis you cannot test with a command is a guess.
5. **Change one thing at a time**, with a five-minute timer; if the change has not helped, undo it.
6. **Write it down as you go.** Timestamps, commands, outputs, decisions. This becomes the incident note.

![The request path from DNS through edge, load balancer, ingress, Service, pod and application to the database, with what the user sees and the first command to run when each hop is broken](/devops/img/request-path-failure-signatures.svg)The request path from DNS through edge, load balancer, ingress, Service, pod and application to the database, with what the user sees and the first command to run when each hop is broken

### Two triage frames: USE for resources, RED for services

**USE** is for resources (CPU, memory, disk, network, pools): **U**tilization (how busy), **S**aturation (how much work is queued), **E**rrors. A CPU at 70 percent with a run queue of 40 is saturated. **RED** is for services: **R**ate, **E**rrors, **D**uration (p50 and p99). Run RED along the request path; the first hop whose errors or duration jumped is the suspect. Run USE on that hop's host to see what it ran out of.

| Frame | Apply to | Prometheus examples |
| --- | --- | --- |
| USE | hosts, nodes, pools, queues | `node_load1`, `node_memory_MemAvailable_bytes`, `node_disk_io_time_seconds_total` |
| RED | every service and hop | `rate(http_requests_total[5m])`, the same with `{code=~"5.."}`, `histogram_quantile(0.99, ...)` |

### The Kubernetes loop: describe, logs, previous, events, exec

```
P=api-7d9f6b7c5-x2k4p
kubectl describe pod $P -n shop                    # state, last state, restarts, probes, Events at the bottom
kubectl logs $P -n shop -c api --tail=200          # what the app said
kubectl logs $P -n shop -c api --previous          # the container that crashed; the current one may be silent
kubectl get events -n shop --sort-by=.metadata.creationTimestamp   # what the cluster did, in time order
kubectl events -n shop --for pod/$P --types=Warning                # newer form: one object, warnings only
kubectl exec -it $P -n shop -c api -- sh -c 'env | sort; wget -qO- localhost:8080/healthz'
kubectl get pod $P -n shop -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}'
```

**kubectl debug and ephemeral containers.** Production images are distroless, so `exec` finds no shell. An ephemeral container is a temporary container added to a running pod. It shares the pod's network namespace, and with `--target` the app's process namespace, so a toolbox image sees the app's processes and sockets.

```
# add a debug container; --target shares the app's process namespace (ps, netstat -tlnp, wget localhost)
kubectl debug -it $P -n shop --image=busybox:1.36 --target=api -- sh
# a pod that crashes before you can attach: copy it with a shell as the command, same env and mounts
kubectl debug $P -n shop -it --copy-to=api-dbg --container=api -- sh
# --profile=netadmin allows tcpdump; --profile=restricted passes a restricted Pod Security namespace
# a node problem: a pod on that node with the host filesystem at /host
kubectl debug node/ip-10-0-3-41.ap-south-1.compute.internal -it --image=busybox:1.36 -- chroot /host journalctl -u kubelet -n 100
kubectl delete pod api-dbg -n shop   # copies must be deleted by hand; ephemeral containers go with the pod
```

### Playbook A: Linux host

| Symptom | Likely causes | First commands | Confirming evidence | Fix |
| --- | --- | --- | --- | --- |
| High load average | more runnable threads than cores, or processes stuck in disk wait (state D) | `uptime; vmstat 1 5; top -o %CPU` | vmstat `r` above core count: CPU; `b` and high `wa`: I/O | find the process; `iostat -x 1` for I/O; move the job or add capacity |
| High memory, OOM kills | a leak, too many workers; page cache is not a problem | `free -h; ps -eo pid,rss,cmd --sort=-rss | head; dmesg -T | grep -i 'killed process'` | `available` is low; dmesg names the victim | restart the leaker, lower worker count, set a cgroup limit, profile the heap |
| Disk full | logs, old images, a deleted file still open, inodes | `df -h; df -i; du -xsh /var/* | sort -h; lsof +L1` | `df` says 100 percent but `du` finds less: a deleted file is held open | truncate it (`: > /proc/PID/fd/N`), rotate logs, `crictl rmi --prune` |
| Too many open files | fd leak, limit too low | `ulimit -n; ls /proc/PID/fd | wc -l; lsof -p PID` | the count grows every minute, mostly sockets in CLOSE\_WAIT | raise `LimitNOFILE` in the unit for now; fix the code that never closes |
| Port not listening | app crashed, bound to 127.0.0.1, wrong port, port taken | `ss -ltnp; systemctl status api; journalctl -u api -n 50` | nothing on the port, or `127.0.0.1:8080`, or `address already in use` | fix bind address or port, restart with systemd |
| Process will not die | state D (uninterruptible I/O, often NFS), zombie, ignores SIGTERM | `ps -o pid,stat,wchan:20,cmd -p PID` | `D` with a filesystem wchan; `Z` is a zombie | D cannot be killed: fix the I/O or reboot; zombies: restart the parent |
| Time drift | NTP not running, VM paused | `timedatectl; chronyc tracking` | `System clock synchronized: no` | start chrony; drift breaks TLS, JWTs and log order |

### Playbook B: containers

| Symptom | Likely causes | First commands | Confirming evidence | Fix |
| --- | --- | --- | --- | --- |
| Exits at once | wrong command, missing file, app error, one-shot entrypoint (exit 0) | `docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}}' NAME; docker logs NAME` | 1 plus a stack trace; 126 or 127: command missing; 0: entrypoint finished | fix entrypoint or config; a server must run in the foreground |
| OOMKilled, exit 137 | limit below real use; JVM or Go not aware of the cgroup limit | `docker stats --no-stream NAME` | usage climbs to the limit, then restart | raise the limit after measuring; set `GOMEMLIMIT` or JVM container flags; fix the leak |
| Image pull fails | typo, private registry, rate limit, expired ECR token | `docker pull IMAGE; aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.ap-south-1.amazonaws.com` | `manifest unknown`, `unauthorized`, `toomanyrequests` | fix the tag; refresh credentials; mirror public images into ECR |
| Permission denied on a volume | host path owned by root, container runs as UID 1000; SELinux; read-only mount | `docker run --rm -v /data:/data IMAGE id; ls -ln /data` | UID inside differs from the owner outside | `chown 1000:1000` the path, or `--user`, or `:z` on SELinux hosts |
| DNS fails inside | host `resolv.conf` points at 127.0.0.53 (systemd-resolved), VPN | `docker exec NAME cat /etc/resolv.conf; docker exec NAME nslookup api.internal` | nameserver `127.0.0.53`: the host's loopback, unreachable from inside | `--dns 10.0.0.2` or `dns` in the daemon config |

Exit codes above 128 are 128 plus the signal: 137 is SIGKILL (OOM or a hard kill), 143 is SIGTERM, 139 is SIGSEGV.

### Playbook C: Kubernetes

| Symptom | Likely causes | First commands | Confirming evidence | Fix |
| --- | --- | --- | --- | --- |
| Pending | no node fits the requests, taints without tolerations, affinity matches nothing, PVC unbound | `kubectl describe pod POD | tail -20; kubectl top nodes` | `0/6 nodes are available: 3 Insufficient cpu, 3 node(s) had untolerated taint` | lower requests, ask why Karpenter did not add a node, add a toleration, fix the PVC |
| CrashLoopBackOff | app exits on start, missing env or Secret, failing liveness probe, OOM | `kubectl logs POD --previous; kubectl get pod POD -o jsonpath='{.status.containerStatuses[0].lastState.terminated}'` | exit code plus the last log lines; back-off doubles from 10 s to 5 min | fix the cause in Git; delete the pod to skip the back-off |
| ImagePullBackOff | wrong tag, private registry, missing `imagePullSecrets`, node role lacks ECR permission | `kubectl describe pod POD | grep -A2 -i 'failed to pull'` | `manifest for api:1.5.0 not found` or `401 Unauthorized` | fix the tag; on EKS give the node role `AmazonEC2ContainerRegistryPullOnly`; else add `imagePullSecrets` |
| Running, not Ready | readiness probe fails: wrong path or port, dependency down, slow start | `kubectl describe pod POD | grep -A3 Readiness; kubectl exec POD -- wget -qO- localhost:8080/healthz` | `Readiness probe failed: HTTP probe failed with statuscode: 503` | fix the probe or the dependency; add a `startupProbe` |
| Service, no endpoints | selector does not match pod labels, no Ready pod | `kubectl get endpointslices -n NS -l kubernetes.io/service-name=api; kubectl get pods -n NS --show-labels` | the EndpointSlice has no addresses | make the selector match; fix the probe |
| Ingress or Gateway 502 or 504 | 502: backend refused or spoke the wrong protocol; 504: backend slower than the proxy timeout | `kubectl describe ingress api -n NS` (or `httproute`); the proxy log, here on the retired ingress-nginx: `kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --tail=100 | grep ' 50[24] '` | `connect() failed (111: Connection refused) while connecting to upstream` or `upstream timed out` | 502: fix the port chain; 504: fix the slow handler before raising the timeout |
| PVC Pending | StorageClass missing, CSI driver not installed, `WaitForFirstConsumer` (normal until a pod uses it), zone mismatch | `kubectl describe pvc data-0 -n NS; kubectl get storageclass; kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver` | `no persistent volumes available` or `waiting for first consumer` | install the EBS CSI add-on, fix the class name, schedule in the volume's zone |
| Node NotReady | kubelet stopped, disk or memory pressure, CNI down, instance gone | `kubectl describe node NODE | grep -A8 Conditions`; then `kubectl debug node/NODE` and `journalctl -u kubelet` | `DiskPressure=True` or `kubelet stopped posting node status` | free disk, restart kubelet; let Karpenter replace a dead instance; cordon and drain a flapping one |
| Evictions | node pressure: kubelet evicts BestEffort, then Burstable pods | `kubectl get pods -A --field-selector=status.phase=Failed; kubectl get pod POD -o jsonpath='{.status.message}'` | `The node was low on resource: ephemeral-storage` | requests equal to limits for important pods (Guaranteed class), log to stdout not disk, add nodes |
| HPA not scaling | metrics-server missing, no CPU requests, `maxReplicas` reached, scale-down window (5 min default) | `kubectl describe hpa api -n NS; kubectl top pods -n NS` | `unable to get metrics`, `<unknown>/70%`, or `ScalingLimited` | install metrics-server, set requests, raise `maxReplicas`, or wait |
| RBAC forbidden | no Role for that verb and resource, RoleBinding in the wrong namespace | `kubectl auth can-i list pods --as=system:serviceaccount:shop:api -n shop` | `no`; the error names user, verb, resource, namespace | add a Role and RoleBinding with only the verbs needed |
| Webhook timeouts block every deploy | an admission webhook is down and has `failurePolicy: Fail` | `kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations; kubectl get pods -n kyverno` | `failed calling webhook ... context deadline exceeded` on every apply | fix the webhook pods; break-glass: `failurePolicy: Ignore` for that one; exclude `kube-system` with a `namespaceSelector` |

### Playbook D: networking

| Symptom | Likely causes | First commands | Confirming evidence | Fix |
| --- | --- | --- | --- | --- |
| Connection refused | nothing listens on that IP and port | `nc -zv 10.0.3.41 8080`; on the target `ss -ltnp` | an immediate RST: the path is fine | start the service, fix port or bind address |
| Connection timeout | security group, NACL, NetworkPolicy, firewall or route drops packets; wrong IP | `nc -zv -w 3 HOST 443; traceroute -T -p 443 HOST; aws ec2 describe-security-groups --group-ids sg-...` | silence for the whole timeout while another port on the host answers | open the rule, fix the policy or route |
| Connection reset | idle timeout on a load balancer (ALB default 60 s), app crashed mid-request, keepalive mismatch | `ss -tni; kubectl logs POD --previous` | resets line up with a timer or with restarts | app keepalive below the LB idle timeout; fix the crash |
| Intermittent DNS | `ndots:5` tries four cluster suffixes before an external name, CoreDNS overloaded, UDP conntrack race | `kubectl exec POD -- cat /etc/resolv.conf; kubectl -n kube-system logs deploy/coredns --tail=100; kubectl -n kube-system top pods -l k8s-app=kube-dns` | `options ndots:5`, SERVFAIL in logs, CoreDNS at its CPU limit | trailing-dot FQDNs, `dnsConfig` with `ndots:2`, more CoreDNS replicas, NodeLocal DNSCache |
| TLS handshake errors | expired or wrong-host certificate, unknown CA, missing SNI | `openssl s_client -connect api.example.com:443 -servername api.example.com 2>/dev/null | openssl x509 -noout -dates -subject` | `notAfter` in the past, or `unable to get local issuer certificate` | renew (`kubectl describe certificate` with cert-manager), fix the chain; alert 14 days before expiry |
| MTU problems | small requests work, large ones hang: VPN or overlay mismatch, PMTUD blocked | `ping -M do -s 1472 HOST` (1500 minus 28 bytes of headers) | 1472 fails, 1400 works | lower the MTU on the interface or overlay, or allow ICMP fragmentation-needed |
| Security group vs NetworkPolicy | security groups filter at the ENI; NetworkPolicy filters in the cluster, only if the CNI enforces it | `aws ec2 describe-security-groups --filters Name=group-name,Values=eks-node-*; kubectl get networkpolicy -A` | pod to RDS times out: the RDS security group does not allow the node security group | allow the source SG on the destination SG; NetworkPolicy needs a CNI that enforces it |

**Refused**: nothing listens. **Timeout**: something drops packets. **Reset**: a connection existed and someone closed it.

### Playbook E: pipelines and deploys

| Symptom | Likely causes | First commands | Confirming evidence | Fix |
| --- | --- | --- | --- | --- |
| Slow builds | no dependency or layer cache, serial tests, huge Docker context | the job timeline in the CI UI; `time docker build .`; `du -sh .` | one step is 80 percent of the time; `COPY . .` before `npm ci` breaks the cache | `actions/cache` or BuildKit cache mounts, reorder layers, split tests across runners |
| Flaky tests | shared state, timing assumptions, real network calls | `go test -run TestX -count=20 ./...` | fails 2 of 20 with no code change | quarantine with a ticket, fix the shared state |
| Passed CI, fails in prod | different config, a rebuilt image instead of a promoted one, a migration run only in staging, lower limits | `kubectl get deploy api -o jsonpath='{.spec.template.spec.containers[0].image}'` in both; `diff <(kubectl get cm api -oyaml -n staging) <(kubectl get cm api -oyaml -n prod)` | different digests, or a key missing in prod | promote one digest through environments; render and diff environments in CI |
| Config drift | `kubectl edit` or a console change by hand | `argocd app diff api; terraform plan -detailed-exitcode` | OutOfSync; a plan with a change nobody made | sync from Git, enable self-heal, alert on a nightly plan |
| Secret missing in one environment | ExternalSecret added for staging only, no value in Secrets Manager for prod | `kubectl describe externalsecret api -n prod | tail -5` | `SecretSyncedError: secret not found` | add the entry and manifest for every environment; CI check that every `secretKeyRef` resolves |

### Traces and metrics: finding the slow hop

Latency problems are not errors, so the path walk uses duration. In a slow OpenTelemetry trace, find the longest span with no long children: that span is doing the waiting. If it is `SELECT ... FROM orders` at 2 s with nothing beneath, the database is slow; if it is a client span waiting on `inventory-svc`, go there and repeat. A gap between a parent span and its first child is time spent in a queue or a connection pool. Without traces, the slow hop is the first whose p99 rose while its downstream did not.

### Writing the incident note

Under ten lines, in this order: impact in numbers (who, how many, from when to when), what users saw, timeline of detection, mitigation and resolution, root cause in one sentence, the trigger, the fix, follow-ups with owners. It names services and commands, not people: the cause is a condition in the system, such as "the pipeline allowed a port change without a matching Service change".

## Diagram

Rendering diagram…

## Worked example

**A 502 storm after a deploy.** At 14:02 Argo CD syncs `checkout-api` revision 31. At 14:05 the SLO alert fires: 5xx ratio 18 percent. Traffic is 12,000 requests per minute.

Step 1, scope. The error panel split by version shows all 5xx come from the ingress, and started at 14:02:40. One service, one region, every user who hits checkout. Since when: the deploy. That alone makes rollback the right first move.

Step 2, protect. `kubectl rollout undo deployment/checkout-api -n shop` at 14:08. The old ReplicaSet still exists, so the pods are Ready in 40 seconds. Errors fall to zero at 14:11. Nine minutes at 18 percent of 12,000 per minute is 12,000 x 9 x 0.18 = 19,440 failed requests. With a 99.9 percent monthly SLO on about 518 million requests (12,000 x 60 x 24 x 30), the monthly error budget is 518,400 requests, so this incident spent 19,440 / 518,400 = 3.75 percent of the budget.

Step 3, follow the path on the broken revision, kept running as a separate Deployment with no traffic. DNS, edge and load balancer are fine (the old version works through them). `kubectl describe ingress checkout` routes to Service `checkout-api` port 80. `kubectl get endpointslices -l kubernetes.io/service-name=checkout-api` lists the new pods, so the Service has endpoints and the pods are Ready. First broken contract must be after the Service: the controller log says `connect() failed (111: Connection refused) while connecting to upstream 10.0.4.17:8080`.

Step 4, hypothesis: the new image listens on a different port. One command: `kubectl debug -it POD --image=busybox:1.36 --target=checkout -- netstat -tlnp`. Output: `0.0.0.0:8081`. Confirmed. The Service `targetPort` is 8080. The readiness probe was `tcpSocket` on 8081 inside the container, so the pods were Ready while the Service pointed at a closed port: refused, hence 502.

Step 5, one change: the port in the Deployment template back to 8080, through Git. Step 6, the note: impact 19,440 requests over 9 minutes; cause: port change in the app without a matching Service change; trigger: revision 31; fix: rollback then corrected port; follow-ups: a CI check that `containerPort`, `targetPort` and the readiness probe port agree, and an HTTP readiness probe instead of a TCP one.

## Runnable code

Python · runs and prints its own checks

```
"""A decision-tree diagnoser for Kubernetes pod states.

Give it a pod status in the same shape kubectl returns (phase, container
statuses with waiting reasons and last terminated exit codes, conditions,
events) and it walks the same tree an on-call engineer walks: Pending first,
then image problems, then crashes, then readiness, then 'healthy'. For each
pod it prints a diagnosis and the one command to run next. No cluster needed.
"""

def diagnose(pod):
    """Return (diagnosis, next_command) for one pod status dict."""
    name = pod["name"]
    phase = pod["phase"]
    statuses = pod.get("containerStatuses", [])
    conditions = {c["type"]: c for c in pod.get("conditions", [])}
    events = pod.get("events", [])
    reasons = [e["reason"] for e in events]

    # Branch 1: Pending means no node yet, or the node cannot start it.
    if phase == "Pending":
        sched = conditions.get("PodScheduled", {})
        if sched.get("status") == "False":
            msg = sched.get("message", "")
            if "Insufficient" in msg:
                return ("Pending: no node has room (" + msg + ")",
                        f"kubectl describe pod {name} | grep -A3 Events; kubectl top nodes")
            if "taint" in msg:
                return ("Pending: every node is tainted and the pod has no toleration",
                        "kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints")
            if "volume" in msg or "pvc" in msg.lower():
                return ("Pending: the PVC is not bound (missing StorageClass or zone mismatch)",
                        f"kubectl get pvc -n {pod['namespace']}; kubectl describe pvc")
            return ("Pending: unschedulable for another reason: " + msg,
                    f"kubectl describe pod {name}")
        for s in statuses:
            waiting = s.get("state", {}).get("waiting", {})
            if waiting.get("reason") in ("ImagePullBackOff", "ErrImagePull"):
                return ("Image pull failed: wrong name, tag, or missing registry credentials",
                        f"kubectl describe pod {name} | grep -iE 'pull|unauthorized|not found'")
            if waiting.get("reason") == "ContainerCreating":
                if "FailedMount" in reasons:
                    return ("Stuck in ContainerCreating: a volume, ConfigMap or Secret failed to mount",
                            f"kubectl get events --field-selector involvedObject.name={name} --sort-by=.lastTimestamp")
                return ("ContainerCreating: image is still pulling or the CNI is slow",
                        f"kubectl get events --field-selector involvedObject.name={name} --sort-by=.lastTimestamp")
        return ("Pending with a node assigned but no container status yet",
                f"kubectl describe pod {name}")

    # Branch 2: Running, but is each container alive and ready?
    for s in statuses:
        waiting = s.get("state", {}).get("waiting", {})
        last = s.get("lastState", {}).get("terminated", {})
        if waiting.get("reason") == "CrashLoopBackOff" or s.get("restartCount", 0) >= 3:
            code = last.get("exitCode")
            if last.get("reason") == "OOMKilled":
                return (f"OOMKilled after {s['restartCount']} restarts: memory limit is below real usage or there is a leak",
                        f"kubectl top pod {name} --containers; check resources.limits.memory")
            if code == 137 and "Unhealthy" in reasons:
                return ("Killed by a failing liveness probe: the probe is wrong or the app starts slowly",
                        f"kubectl describe pod {name} | grep -A2 Liveness; add a startupProbe")
            if code in (126, 127):
                return (f"Exit code {code}: the command or entrypoint does not exist in the image",
                        f"kubectl debug {name} -it --copy-to=dbg --container={s['name']} -- sh")
            if code == 0:
                return ("Exit code 0 in a loop: the main process finishes on purpose; wrong command for a server",
                        f"kubectl get pod {name} -o jsonpath='{{.spec.containers[0].command}}'")
            return (f"CrashLoopBackOff with exit code {code}: the application itself is failing on start",
                    f"kubectl logs {name} -c {s['name']} --previous")

    ready = conditions.get("Ready", {}).get("status")
    if phase == "Running" and ready != "True":
        if "Unhealthy" in reasons:
            return ("Running but not Ready: the readiness probe fails, so the pod is out of the Service",
                    f"kubectl describe pod {name} | grep -A3 Readiness; kubectl exec {name} -- wget -qO- localhost:8080/healthz")
        return ("Running but not Ready: no probe failure logged, check that a readiness probe exists",
                f"kubectl get pod {name} -o jsonpath='{{.spec.containers[0].readinessProbe}}'")

    if phase == "Running" and ready == "True":
        return ("Healthy: Running and Ready. If users still see errors, the fault is upstream (Service, ingress) or downstream (DB)",
                "kubectl get endpointslices -l kubernetes.io/service-name=<svc>; then walk the request path")

    if phase in ("Failed", "Succeeded"):
        return (f"Phase {phase}: a finished Job or an evicted pod; read the reason",
                f"kubectl get pod {name} -o jsonpath='{{.status.reason}} {{.status.message}}'")
    return ("Unknown state", f"kubectl describe pod {name}")

SAMPLES = [
    {"name": "api-1", "namespace": "shop", "phase": "Pending", "containerStatuses": [],
     "conditions": [{"type": "PodScheduled", "status": "False",
                     "message": "0/6 nodes are available: 6 Insufficient cpu."}], "events": []},
    {"name": "api-2", "namespace": "shop", "phase": "Pending",
     "containerStatuses": [{"name": "api", "restartCount": 0,
                            "state": {"waiting": {"reason": "ImagePullBackOff"}}}],
     "conditions": [{"type": "PodScheduled", "status": "True"}],
     "events": [{"reason": "Failed", "message": "manifest for api:1.5.0 not found"}]},
    {"name": "api-3", "namespace": "shop", "phase": "Running",
     "containerStatuses": [{"name": "api", "restartCount": 7,
                            "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                            "lastState": {"terminated": {"exitCode": 1, "reason": "Error"}}}],
     "conditions": [{"type": "Ready", "status": "False"}],
     "events": [{"reason": "BackOff", "message": "Back-off restarting failed container"}]},
    {"name": "worker-4", "namespace": "shop", "phase": "Running",
     "containerStatuses": [{"name": "worker", "restartCount": 4,
                            "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                            "lastState": {"terminated": {"exitCode": 137, "reason": "OOMKilled"}}}],
     "conditions": [{"type": "Ready", "status": "False"}], "events": []},
    {"name": "api-5", "namespace": "shop", "phase": "Running",
     "containerStatuses": [{"name": "api", "restartCount": 0, "state": {"running": {}}}],
     "conditions": [{"type": "Ready", "status": "False"}],
     "events": [{"reason": "Unhealthy", "message": "Readiness probe failed: HTTP 503"}]},
    {"name": "api-6", "namespace": "shop", "phase": "Running",
     "containerStatuses": [{"name": "api", "restartCount": 0, "state": {"running": {}}}],
     "conditions": [{"type": "Ready", "status": "True"}], "events": []},
]

EXPECTED = ["no node has room", "Image pull failed", "exit code 1", "OOMKilled",
            "readiness probe fails", "Healthy"]

if __name__ == "__main__":
    for pod, expect in zip(SAMPLES, EXPECTED):
        diag, cmd = diagnose(pod)
        print(f"{pod['name']:<9} {pod['phase']:<8} -> {diag}")
        print(f"{'':<21}next: {cmd}")
        assert expect in diag, (pod["name"], diag)
    print(f"\n{len(SAMPLES)} sample pods diagnosed, all matched the expected branch")
```

## Key takeaways

* Scope first: who, how many, since when. "Since when" points at what changed.
* Protect users before you understand the cause: rollback, failover, scale, flag. A rollback that does not help is evidence too.
* Walk the request path in order and stop at the first hop that breaks its promise; everything after it is a symptom.
* One hypothesis, one command, one change at a time, with a timer. Negative results are worth writing down.
* Refused means nothing listens, timeout means something drops packets, reset means someone closed an open connection.
* The Kubernetes loop is describe, logs, previous, events, exec; use `kubectl debug` with `--target` when the image has no shell.
* For latency, find the longest span with no long children; without traces, the first hop whose p99 rose while its downstream did not.
* The incident note has impact in numbers, a timeline, one-sentence cause, trigger, fix and owned follow-ups.

## Common mistakes

* Restarting things before scoping. The restart destroys the evidence and the problem comes back.
* Debugging the code for twenty minutes while a rollback was available in twenty seconds.
* Changing three things at once and declaring whichever one came last as the fix.
* Reading `kubectl get pods` and never `kubectl describe` Events, or never `--previous` on a crashing container.
* Treating a timeout and a refused connection as the same problem; they point at different layers.
* Raising a timeout or a limit to make a symptom disappear without finding what got slower or bigger.

## Practice

* On kind, deploy a web app, then break it five ways one at a time: wrong image tag, Service targetPort off by one, readiness path 404, memory limit of 20Mi, and a Role without the `list pods` verb. For each, write the symptom, the single command that confirmed it, and the fix, before you look at the answer.
* Use a distroless image (any `gcr.io/distroless` sample) and prove that `kubectl exec` fails, then attach an ephemeral container with `--target` and show the app's listening port with netstat.
* On a Linux VM, fill the disk with a file, delete it while a process holds it open (`sleep 1000 < bigfile &`), confirm that `df` and `du` disagree, find it with `lsof +L1`, and free the space without killing the process.
* Write an incident note for one of the breaks above in the order given in this lesson, under ten lines, with the impact in numbers from `kubectl get --raw /metrics` or your load generator.

## Interview questions (10)

1.Users report the site is slow. What do you check first?Medium

I scope before I touch anything: is it every user or some, every endpoint or one, every region or one, and since when. The RED panel per service shows me rate, errors and p99 split by version and region, and "since when" lines up with a deploy, a traffic change or a dependency incident. Then I protect: if it started with a deploy I roll back right away; if traffic doubled I scale. Only then do I follow the path with traces to the longest span with no long children, and on that hop I run USE on the host or pool to see what it ran out of. Along the way I write timestamps and commands, because this becomes the incident note.

2.A pod is Running but the Service returns 502. Walk me through it.Medium

Running only means a process started. First I check the pod is Ready and in the EndpointSlice: `kubectl get endpointslices -l kubernetes.io/service-name=api`. If there are no addresses, the selector does not match the pod labels or the readiness probe is failing, and `describe pod` shows which. If the addresses are there, 502 means the proxy connected to the pod and got refused or garbage, so I check the port chain: Ingress backend port, Service `port` and `targetPort`, and what the container actually listens on with `kubectl debug --target` and `netstat -tlnp`. The usual causes are a `targetPort` that differs from the listening port, or TLS expected on one side only. A 504 instead would send me to a slow backend and the proxy timeout.

3.What is the difference between connection refused, timeout and reset, and what does each tell you?Easy

Refused means the packet reached the host and the kernel answered with a reset because nothing listens on that port: the service is down, on another port, or bound to loopback only; the network path is fine. Timeout means nobody answered at all, so something drops packets: a security group, NACL, NetworkPolicy, firewall or a wrong route or IP. Reset means a connection existed and one side closed it: an idle timeout on a load balancer, a crashed process, or a keepalive mismatch. Each word points at a different layer, so I never treat them as one problem.

4.A deploy passed every CI check and fails in production. Where do you look?Medium

Something differs between the environments, so I diff them. First the image: is production running the same digest that CI tested, or was it rebuilt. Then configuration: ConfigMaps, Secrets and ExternalSecrets in both namespaces, and environment variables in the rendered manifests. Then resources: a lower memory limit in prod produces OOMKilled that staging never saw. Then data: a migration applied in staging but not prod, or a dataset size that makes a query slow. The prevention is to promote one immutable artifact through environments and to render and diff environment manifests in CI so the difference is visible before the deploy.

5.Every kubectl apply in the cluster fails with "context deadline exceeded calling webhook". What happened and what do you do?Hard

An admission webhook is unreachable and is configured with `failurePolicy: Fail`, so the API server refuses every matching request until the webhook answers. The webhook is usually a policy engine or a sidecar injector whose pods are down, and if the webhook also matches `kube-system` it can block the very pods it needs to come back. I list the webhook configurations, find the one named in the error, and check its pods. If they cannot recover on their own I set that one webhook to `failurePolicy: Ignore` as a break-glass step, record it, bring the pods back, and restore `Fail`. The prevention is a `namespaceSelector` that excludes `kube-system`, replicas and a PodDisruptionBudget for the webhook, and alerting on its latency.

6.Disk is at 100 percent on a node but du cannot find the files. Why, and how do you fix it?Easy

A process is holding a deleted file open. The directory entry is gone, so `du` cannot see it, but the blocks stay allocated until the last file descriptor closes. `lsof +L1` lists open files with a link count of zero and the process holding them; it is almost always a log file that was deleted instead of rotated. I truncate it through the file descriptor path, for example `: > /proc/PID/fd/N`, or restart the process, which releases the space immediately. The prevention is logrotate with copytruncate, or sending logs to stdout so the container runtime manages them.

7.How do you debug a pod whose image has no shell?Medium

I attach an ephemeral container with `kubectl debug -it POD --image=busybox:1.36 --target=app`. It shares the pod's network namespace, so I can test the app on localhost, and `--target` shares the process namespace so I can see the app's processes and sockets with ps and netstat. For a pod that crashes before I can attach, I use `--copy-to` with a different command so the copy starts with the same env and mounts but runs a shell. For node problems, `kubectl debug node/NAME` runs a pod with the host filesystem at /host. In a namespace with the restricted Pod Security profile, `--profile=restricted` makes the debug container pass admission.

8.What is in a good incident note and when do you write it?Easy

I write it during the incident, as a running log of timestamps, commands and decisions, and tidy it within an hour of resolution while I still remember. It contains impact in numbers (who, how many requests or users, from when to when), what users saw, the timeline of detection, mitigation and resolution, the root cause in one sentence, the trigger that exposed it, what fixed it, and follow-ups with owners. It names services and commands, not people, because the cause is a condition in the system. The note is the input to the postmortem and the first thing the next on-call reads when the same alert fires.

9.DNS inside the cluster fails about one request in a hundred. What do you check?Hard

Intermittent DNS has three usual causes. First, `ndots:5`: a name like `api.example.com` has two dots, so the resolver tries four cluster suffixes first, which multiplies CoreDNS load by five and makes a single dropped UDP packet into a visible failure; I check `/etc/resolv.conf` in the pod and fix with a trailing dot or `dnsConfig` with `ndots:2`. Second, CoreDNS itself: its CPU usage against its limit, its logs for SERVFAIL, and whether it has enough replicas and the autoscaler. Third, the conntrack race on UDP, where two parallel A and AAAA queries collide; NodeLocal DNSCache avoids it. I measure with the CoreDNS request duration and error metrics before and after each change.

10.HPA shows unknown for the CPU target and never scales. Why?Easy

`<unknown>` means the HPA cannot compute utilization. Either metrics-server is not installed or not healthy, so there are no pod metrics, or the pods have no CPU requests, because utilization is measured as a percentage of the request and a percentage of nothing is undefined. `kubectl describe hpa` names the condition. I install or fix metrics-server, set CPU requests from measurement, and then check the other reasons a healthy HPA still does not move: `maxReplicas` already reached, or the scale-down stabilization window, which is five minutes by default.

## Quiz

1.An on-call engineer sees 5xx errors starting right after a deploy. What is the correct first action?

2.`nc -zv db.internal 5432` returns "Connection refused" immediately. What does that tell you?

3.`kubectl get endpointslices -l kubernetes.io/service-name=api` shows no addresses. Which is NOT a likely cause?

4.Which exit code in lastState.terminated means the container was killed by SIGKILL, for example by the OOM killer?

5.A pod's image has no shell. Which command gives you a shell with a view of the app's processes?

## Practice these problems

* [OPSPod stuck in CrashLoopBackOffEasy](/devops/problems/pod-crashloopbackoff)
* [OPSPods Pending and ImagePullBackOff after a node group changeEasy](/devops/problems/pod-pending-imagepullbackoff)
* [OPS502 from the ingress while the service works inside the clusterMedium](/devops/problems/ingress-502-service-unreachable)
* [OPSHigh load average and a process eating memory on a Linux hostMedium](/devops/problems/high-load-memory-leak-linux)
* [OPSIntermittent DNS resolution failures in the clusterHard](/devops/problems/intermittent-dns-failures)
* [OPSDatabase connections exhausted after a deployMedium](/devops/problems/db-connection-pool-exhausted)

## Further reading

* [Kubernetes: Debug PodsGuidekubernetes.io](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
* [Google SRE Book: Chapter 12 - Effective TroubleshootingArticlesre.google](https://sre.google/sre-book/effective-troubleshooting/)
* [How Complex Systems FailPaperhow.complexsystems.fail](https://how.complexsystems.fail/)
* [Linux man pages online (man7.org)Guideman7.org](https://man7.org/linux/man-pages/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousSRE practice - SLOs, error budgets, incidents and postmortems](/devops/learn/sre-slos-incidents-postmortems)[NextSecurity and DevSecOps - secrets, least privilege, supply chain, policy as code](/devops/learn/security-and-devsecops)

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

1. [The method: six moves, in order](#the-method-six-moves-in-order)
2. [Two triage frames: USE for resources, RED for services](#two-triage-frames-use-for-resources-red-for-services)
3. [The Kubernetes loop: describe, logs, previous, events, exec](#the-kubernetes-loop-describe-logs-previous-events-exec)
4. [Playbook A: Linux host](#playbook-a-linux-host)
5. [Playbook B: containers](#playbook-b-containers)
6. [Playbook C: Kubernetes](#playbook-c-kubernetes)
7. [Playbook D: networking](#playbook-d-networking)
8. [Playbook E: pipelines and deploys](#playbook-e-pipelines-and-deploys)
9. [Traces and metrics: finding the slow hop](#traces-and-metrics-finding-the-slow-hop)
10. [Writing the incident note](#writing-the-incident-note)
