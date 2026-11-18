# 502 from the ingress while the service works inside the cluster — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/ingress-502-service-unreachable

[DevOps problems](/devops#problems)

OPSTroubleshooting#23Medium

# 502 from the ingress while the service works inside the cluster

kubernetesingressnetworkingserviceendpointslicestroubleshootingReported at Infosys, Capgemini

## Problem statement

It is 15:05. The uptime monitor pages: `https://api.example.com/orders/health` returns `502 Bad Gateway` from the ingress-nginx controller, 100 percent of requests for 4 minutes. Other hosts on the same ingress are fine. `kubectl get pods -n orders` shows `orders-api` 3/3 `Running` and `1/1` ready, and `kubectl port-forward -n orders deploy/orders-api 3000:3000` followed by `curl localhost:3000/health` returns 200. A deploy of `orders-api` finished at 15:00. Find where the path from the ingress to the pod breaks, restore the service, and stop this class of mistake.

## Requirements

### Functional

* Walk the request path in order: ingress controller, Ingress rule, Service, EndpointSlice, pod port, network policy, and name the hop that fails.
* Tell 502, 503 and 504 apart and say what each one implies about the hop.
* Rule out, with evidence, the candidates that are not the cause: selector mismatch, empty EndpointSlices from readiness, NetworkPolicy, localhost binding, load balancer target type.
* Restore 200 responses through the normal pipeline, with a time-boxed hand edit only to prove the hypothesis.
* Add a check that catches a Service port that no longer matches the container.

### Non-functional

* Time to diagnosis under 10 minutes with kubectl and the controller logs.
* Rollback or fix live within 15 minutes of the page; the error budget for this service is 0.1 percent per 30 days and 4 minutes of 100 percent errors has already used about 10 percent of it.
* No change to other namespaces or to the ingress controller itself during the investigation.
* The fix is a Git change reviewed and applied by the pipeline; the hand patch, if used, is reverted within 60 minutes.

## Back-of-the-envelope estimates

**Impact.** `orders-api` takes about 40 requests per second in the afternoon. At 100 percent 502 for 4 minutes that is 4 x 60 x 40 = 9,600 failed requests before the page, and 2,400 more for every minute of investigation. The 30-day budget at 99.9 percent availability is 0.001 x 30 x 24 x 60 = 43.2 minutes of full outage. Four minutes is 9.3 percent of it; a 15-minute fix would spend 35 percent. Blast radius is one host on the ingress: the controller is shared with 12 other services, which keep working because their Services point at the right ports.

## API

```
# 1. What does the ingress controller say? One line per failed request names the upstream it tried.
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --since=10m | grep -E "orders|upstream" | tail -n 5
# 2026/11/05 15:01:12 [error] 31#31: *88214 connect() failed (111: Connection refused) while connecting to upstream,
#   client: 10.0.3.14, server: api.example.com, request: "GET /orders/health HTTP/1.1",
#   upstream: "10.0.12.45:8080/orders/health" (scheme omitted here), host: "api.example.com"

# 2. Does the Ingress rule point at the Service and port you think it does?
kubectl get ingress -n orders orders-api -o yaml | grep -A6 -E "host:|path:|service:"
kubectl describe ingress -n orders orders-api | grep -A3 "Rules"
#   api.example.com  /orders  orders-api:80 (10.0.12.45:8080,10.0.12.61:8080,10.0.13.9:8080)

# 3. Service: selector, port and targetPort.
kubectl get svc -n orders orders-api -o jsonpath='{.spec.selector}{"\n"}{.spec.ports}{"\n"}'
# {"app":"orders-api"}
# [{"name":"http","port":80,"protocol":"TCP","targetPort":8080}]

# 4. Do the pods carry that label, and are they ready? Does the EndpointSlice list them?
kubectl get pods -n orders -l app=orders-api -o wide
kubectl get endpointslices -n orders -l kubernetes.io/service-name=orders-api
# NAME               ADDRESSTYPE   PORTS   ENDPOINTS
# orders-api-x7k2p   IPv4          8080    10.0.12.45,10.0.12.61,10.0.13.9

# 5. Which port does the container actually listen on? Compare containerPort and the process.
kubectl get deploy -n orders orders-api -o jsonpath='{.spec.template.spec.containers[0].ports}{"\n"}'
# [{"containerPort":3000,"name":"http","protocol":"TCP"}]
kubectl exec -n orders deploy/orders-api -- sh -c 'cat /proc/net/tcp | awk "NR>1 {print \$2}"'
# 00000000:0BB8   -> 0x0BB8 = 3000 on 0.0.0.0; 0100007F:... would mean 127.0.0.1 only

# 6. Prove the hop from inside the cluster: Service DNS on port 80, then the pod IP on both ports.
kubectl run -n orders probe --rm -it --image=curlimages/curl --restart=Never -- \
  sh -c 'curl -s -o /dev/null -w "%{http_code}\n" orders-api.orders.svc/health; \
         curl -s -o /dev/null -w "%{http_code}\n" 10.0.12.45:8080/health; \
         curl -s -o /dev/null -w "%{http_code}\n" 10.0.12.45:3000/health'
# 502 / 000 (refused) / 200

# 7. What changed at 15:00?
kubectl rollout history deploy/orders-api -n orders
kubectl rollout history deploy/orders-api -n orders --revision=31 | grep -E "Image|Port"

# 8. Rule out NetworkPolicy: does any policy select these pods and does it allow the ingress namespace?
kubectl get networkpolicy -n orders -o yaml | grep -B2 -A12 "podSelector"
```

## Data model

```
Hop by hop: the field at each hop that must agree with the next one
  Ingress.spec.rules[].host                      api.example.com   (must match the request Host header)
  Ingress.spec.rules[].http.paths[].path         /orders           (pathType Prefix)
  Ingress.spec.rules[].http.paths[].backend.service.name   orders-api
  Ingress.spec.rules[].http.paths[].backend.service.port.number   80   -> must be a Service port
  Service.spec.selector                          app=orders-api    -> must match pod labels
  Service.spec.ports[].port                      80                (what the Ingress calls)
  Service.spec.ports[].targetPort                8080              (what the pod must listen on)  <- wrong
  EndpointSlice.endpoints[].addresses            pod IPs with conditions.ready true
  EndpointSlice.ports[].port                     8080              (copied from targetPort)
  Deployment ...containers[].ports[].containerPort   3000          <- the app moved here in revision 31
  process listen address                         0.0.0.0:3000      (127.0.0.1 would refuse pod-IP traffic)
  NetworkPolicy.spec.ingress[].from              namespaceSelector for ingress-nginx, port 3000
  readinessProbe.httpGet.port                    3000              (passes, so the pod is Ready and in the slice)

What the ingress status code means
  502 Bad Gateway      the controller reached an endpoint and got refused, reset or garbage: wrong port, app not listening, TLS mismatch
  503 Service Unavailable   the controller has no endpoint to send to: empty EndpointSlice, Service missing, all pods NotReady
  504 Gateway Timeout  the endpoint accepted the connection but did not answer in proxy-read-timeout: slow app or dependency

Controller log fields
  upstream: "10.0.12.45:8080/..."          the exact IP:port it tried, compare with the pod's listen port
  connect() failed (111: Connection refused)   nothing listens there -> 502
  upstream timed out (110)                      -> 504
  "Service orders/orders-api does not have any active Endpoint"   -> 503
```

## Diagnosis and fix

1. **Scope.** One host, one Service, started at the deploy time. Other services on the controller return 200, so the controller and the load balancer are healthy. Tell the channel you are on it and that the rollback is one command away.
2. **Read the controller log.** The error line says `connect() failed (111: Connection refused) while connecting to upstream ... upstream: "10.0.12.45:8080/..."`. Two facts: the controller has an endpoint (so this is 502, not 503), and port 8080 on the pod refuses connections. A refusal is a port with no listener, not a network policy (that would time out) and not a crash (the pod is Running and Ready).
3. **Walk the chain.** Ingress backend is `orders-api:80`, the Service has port 80 with `targetPort: 8080`, the selector `app=orders-api` matches 3 Ready pods, the EndpointSlice lists 3 addresses on port 8080. Everything agrees with itself. Now the pod: the Deployment's `containerPort` is 3000 and `/proc/net/tcp` shows a listener on `00000000:0BB8`, 0.0.0.0:3000. The curl from a probe pod confirms it: pod IP on 8080 is refused, on 3000 returns 200.
4. **Find what changed.** `rollout history --revision=31` shows the image went to `v4.0.0` and `containerPort` moved from 8080 to 3000. The port-forward in the page used 3000, which is why it "worked". The Service manifest lives in the same Helm chart but `service.targetPort` is a separate value that nobody updated.
5. **Root cause.** Revision 31 changed the container's listen port from 8080 to 3000, and the Service's `targetPort` still says 8080, so every endpoint the ingress tries refuses the connection.
6. **Fix now.** Two safe options; pick the faster. `kubectl rollout undo deploy/orders-api -n orders` returns the pods to 8080 in under a minute. Or patch the Service: `kubectl patch svc orders-api -n orders -p '{"spec":{"ports":[{"name":"http","port":80,"targetPort":3000}]}}'`. The patch is instant and keeps the new version, so use it, then open the Git change immediately. Argo CD will show the Service as OutOfSync until that merges.
7. **Verify.** Controller log shows 200s for `/orders/health`; `curl -s -o /dev/null -w "%{http_code}" https://api.example.com/orders/health` from outside returns 200 three times in a row; the uptime monitor clears. Revert the hand patch once the pipeline applies the same value.
8. **Prevent.** Make the port one value: `targetPort: http` in the Service and `name: http` on the containerPort, so the Service follows the container by name. Add a CI check that renders the chart and fails if any Service `targetPort` number does not match a `containerPort` in the selected pods. Make the readiness probe use the named port too. Add a synthetic check through the ingress to the deploy pipeline so a rollout is not "done" until the public URL returns 200.

## Architecture diagram

Rendering diagram…

## Deep dives

### 502, 503 and 504 are three different hops

Many clusters still run ingress-nginx even though the project was retired upstream in early 2026; the diagnosis below is the same for any Ingress controller or Gateway implementation, only the log lines differ. The controller is a reverse proxy, and its status code tells you how far the request got. 503 means the controller had nowhere to send the request: the Service has no ready endpoints, so the EndpointSlice is empty, the selector does not match, or every pod is NotReady; ingress-nginx logs `does not have any active Endpoint`. 502 means it picked an endpoint and the TCP connection was refused or reset, or the response was not valid HTTP: a wrong port, a process that died between readiness checks, or plain HTTP sent to a TLS-only port. 504 means the connection opened and the app did not answer within the proxy timeout, which points at the application or a dependency, or at a NetworkPolicy that silently drops packets (drops time out, they are not refused). Saying "502 means the pod is down" is the common mistake: the pod was up the whole time here.

### Why port-forward lied

`kubectl port-forward` talks to the pod through the API server and the kubelet, straight to the port you name. It skips the Service, the EndpointSlice, kube-proxy and the ingress. It proves the process works on that port, which is a useful fact, and nothing more. The probe pod test is the honest one: curl the Service DNS name on the Service port, then the pod IP on the Service's targetPort. The first failing step is the broken hop. The same logic applies to NetworkPolicy, which a port-forward also bypasses.

### Named ports remove this whole class

A Service with `targetPort: 8080` and a container with `containerPort: 3000` are two numbers in two files that must agree, and nothing enforces it. With `ports: [{name: http, containerPort: 3000}]` on the container and `targetPort: http` on the Service, the EndpointSlice controller resolves the name per pod, so a port change in the Deployment flows through on the next rollout. During a rolling update the slice even carries old pods on 8080 and new pods on 3000 at the same time, correctly. Use the same name in the readiness probe. The remaining risk is a typo in the name, which the CI render check catches.

### The AWS Load Balancer Controller path

On EKS with an ALB Ingress the hops change. With `alb.ingress.kubernetes.io/target-type: ip` the ALB sends traffic straight to pod IPs on the Service's targetPort, so the same mismatch shows as unhealthy targets in the target group and the ALB returns 502. With `target-type: instance` the ALB sends to the NodePort, so the Service must be `NodePort` or `LoadBalancer`, and a `ClusterIP` Service gives a controller error, not a 502. The security group on the nodes or pods must allow the ALB's security group on the target port; if the controller does not manage that rule you see health checks failing with a timeout. The diagnosis order is the same, with `aws elbv2 describe-target-health` in place of the controller log.

### Readiness and the empty slice

If the pods had been failing readiness, the EndpointSlice would have `ready: false` for every address and the controller would return 503 with no endpoints. Here the probe hits port 3000, the same port the app moved to, so the pods were Ready and the slice was full. A probe on a number that no longer matches would have made every pod NotReady and turned the symptom into 503, which is arguably better, because a Deployment with `maxUnavailable: 0` would then have refused to finish the rollout. That is a reason to probe the named port the Service uses.

## Evaluation

**Did you find it?** The root cause is one sentence: "revision 31 moved the container's listen port from 8080 to 3000 and the Service's `targetPort` still says 8080, so the ingress connects to a port with no listener and returns 502." The evidence chain is the controller log line with the upstream IP:port and `Connection refused`, the EndpointSlice on 8080, `/proc/net/tcp` showing 0.0.0.0:3000, the probe pod curl on both ports, and the rollout diff.

**Is it fixed?** The public URL returns 200 on three consecutive checks, the controller log shows no 502 for the host for 10 minutes, the uptime monitor is green, the Git change with `targetPort: http` is merged and applied, and the hand patch is gone (Argo CD shows Synced).

**Is it prevented?** Named ports in the chart; a CI step that renders the chart and compares every Service targetPort with the selected pods' containerPorts; the readiness probe on the same named port; a synthetic request through the ingress as the last step of the deploy job.

**What a strong answer adds.** The 502 versus 503 versus 504 table from memory, the point that a refused connection rules out NetworkPolicy (drops time out), why port-forward proves less than it seems, the `/proc/net/tcp` trick when the image has no `ss` or `netstat`, and the ALB target-type variant.

**What a weak answer does.** Restarts the ingress controller, restarts the pods, or rolls back without reading the controller log, and cannot say why port-forward worked.

## Bottlenecks & mitigations

* The controller log is shared by every host: without `grep` on the host or upstream it is thousands of lines a minute.
* Distroless images: no `curl`, `ss` or `netstat` inside the pod, so you need `/proc/net/tcp` or an ephemeral debug container.
* Two sources of truth for one port, in two files or two Helm values, with nothing that checks they agree.
* The error budget: at 40 requests per second, each minute of investigation costs 2,400 requests and 2.3 percent of the monthly budget.

## Failure modes

* **Reading the symptom instead of the controller log.** "502" alone does not say which hop failed. Mitigation: the log line with `upstream:` and the error text is the first command, every time.
* **Trusting port-forward.** It bypasses Service, EndpointSlice and NetworkPolicy. Mitigation: test from a probe pod through the Service DNS name and the pod IP.
* **Numeric ports in two places.** A port change in the Deployment does not reach the Service. Mitigation: named ports and a CI render check.
* **App bound to 127.0.0.1.** Works in port-forward, refused from the pod IP. Mitigation: bind 0.0.0.0 (or `::`) in the container; make it a startup assertion.
* **NetworkPolicy added for the namespace without the ingress namespace.** All hosts in that namespace time out at once. Mitigation: a policy template that always allows from the ingress controller's namespace on the named port.
* **Readiness probe on a stale number.** Every pod NotReady, 503 everywhere. Mitigation: probe the same named port.
* **Hand patch left in place.** The next sync reverts it and the outage returns. Mitigation: open the Git change in the same minute, and watch for OutOfSync.
* **ALB target type mismatch.** `ClusterIP` Service with `target-type: instance` never registers targets. Mitigation: `target-type: ip` with the VPC CNI, documented in the chart.

## Follow-up questions interviewers ask

* The log says `upstream timed out (110)` instead of refused. What changes in your diagnosis and which three things do you check?
* The EndpointSlice is empty but the pods are Running. List the reasons and the command for each.
* The same symptom on an ALB Ingress with target-type ip. Where is the equivalent of the controller log?
* How does Gateway API (HTTPRoute, backendRefs) change the hops, and where would the same mistake appear?
* A NetworkPolicy exists in the namespace. Write the rule that allows the ingress controller and nothing else to reach port http.
* Write the CI check that compares Service targetPort with containerPort across a rendered Helm chart.

## Lessons that cover this

* [#4Networking for DevOps - TCP/IP, DNS, HTTP, TLS, SSHFoundations](/devops/learn/networking-for-devops)
* [#7Web servers, reverse proxies and TLS - Nginx, certificates, process managersBuild and ship](/devops/learn/nginx-reverse-proxy-tls)
* [#16Kubernetes networking and storageKubernetes](/devops/learn/kubernetes-networking-storage)
* [#22Troubleshooting playbook - Linux, Docker, Kubernetes, network, pipelinesOperate](/devops/learn/troubleshooting-playbook)

## Further reading

* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)
* [Kubernetes: Debug PodsGuidekubernetes.io](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
* [NGINX documentationGuidenginx.org](https://nginx.org/en/docs/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousPods Pending and ImagePullBackOff after a node group change](/devops/problems/pod-pending-imagepullbackoff)[NextDisk full on a production server at 3 am](/devops/problems/disk-full-production-server)

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
