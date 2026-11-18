# Kubernetes manifests: Deployment, Service, Ingress and HPA with probes and limits — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/kubernetes-manifests-web-app

[DevOps problems](/devops#problems)

CODEImplement it#38Medium

# Kubernetes manifests: Deployment, Service, Ingress and HPA with probes and limits

kubernetesdeploymentingresshpaprobessecurityReported at Infosys, Wipro, TCS

## Problem statement

Write the complete set of Kubernetes manifests to run a stateless HTTP API called orders-api on an EKS cluster. It listens on port 8080, needs a database password from AWS Secrets Manager, and must be reachable at `api.orders.example.com` over TLS. The reviewer will check the file as if it were going to production: rolling updates with no dropped requests, probes with explained timings, resource limits, a restricted security context, spreading across 3 availability zones, autoscaling on CPU, a disruption budget, and a network policy that only lets the ingress controller in.

## Requirements

### Functional

* A Namespace, ServiceAccount, ConfigMap, Deployment, Service, Ingress, HorizontalPodAutoscaler, PodDisruptionBudget and NetworkPolicy, all in one multi-document YAML file that `kubectl apply -f` accepts.
* Non-secret settings come from the ConfigMap with `envFrom`; secret values are referenced with `secretKeyRef` from a Secret that External Secrets Operator creates, never written in the file.
* The ServiceAccount carries the IAM role binding (IRSA annotation) so the pod can read Secrets Manager without access keys.
* The Ingress terminates TLS with a certificate that cert-manager issues from the annotation.
* The HPA scales between 3 and 12 replicas on CPU, and the scale-down rate is limited.

### Non-functional

* Zero failed requests during a rollout: maxUnavailable 0, readiness gating, and a preStop delay of 10 s before SIGTERM.
* Each pod requests 250m CPU and 512Mi memory with a memory limit equal to the request; 12 pods at most use 6 Gi of memory.
* A slow start of up to 150 s is tolerated without restarts; a hung process is restarted within 30 s; an unready pod leaves the Service within 15 s.
* The pod passes the Pod Security Standards "restricted" profile: non-root, read-only root filesystem, no capabilities, RuntimeDefault seccomp.
* Losing one availability zone leaves at least 2 of 3 replicas running, and a node drain never takes more than 1 replica at a time.

## API

```
# Apply and verify
kubectl apply -f orders-api.yaml                      # creates all 9 objects; Namespace first
kubectl -n orders rollout status deploy/orders-api    # waits until 3 pods are Ready
kubectl -n orders get pods -o wide                    # one pod per zone (check the NODE column)
kubectl -n orders get hpa,pdb,netpol,ingress          # HPA shows TARGETS like 12%/60%

# Validate before applying
kubeconform -strict -summary orders-api.yaml          # schema check, no cluster needed
kubectl apply --dry-run=server -f orders-api.yaml     # admission webhooks and PSS checks run

# Inputs the manifests expect to exist
ClusterIssuer letsencrypt-prod           (cert-manager)
IngressClass nginx in namespace ingress-nginx
Secret orders/orders-api-secrets         (External Secrets Operator)
IAM role orders-api with a trust policy for the cluster OIDC provider (IRSA)

# The app must serve
GET /healthz  -> 200 when the process is alive
GET /readyz   -> 200 only when the DB pool is open and warm-up is done
GET /metrics  -> Prometheus text format
```

## Data model

```
Namespace orders (PSS restricted)
 |- ServiceAccount orders-api  --annotation-->  IAM role (IRSA) or Pod Identity association
 |- ConfigMap orders-api-config  --envFrom-->  Deployment
 |- Secret orders-api-secrets  (External Secrets Operator writes it)  --secretKeyRef-->  Deployment
 |- Deployment orders-api  (selector app.kubernetes.io/name=orders-api)
 |     |- ReplicaSet  -> 3..12 Pods, one per zone (topologySpreadConstraints)
 |- Service orders-api  (ClusterIP :80 -> targetPort http=8080)  selects the same label
 |     |- EndpointSlices  <- readiness decides membership
 |- Ingress orders-api  (host api.orders.example.com, tls secret orders-api-tls)  -> Service :80
 |     ^ cert-manager reads the annotation, creates Certificate, fills the tls Secret
 |- HorizontalPodAutoscaler  scaleTargetRef Deployment, cpu 60 percent of request
 |- PodDisruptionBudget  minAvailable 2 over the same selector
 |- NetworkPolicy  podSelector same label; ingress only from namespace ingress-nginx and monitoring

Label app.kubernetes.io/name=orders-api is the join key for Deployment, Service, PDB,
NetworkPolicy and the spread constraints. Change it and every link breaks.
```

## Approach

1. Namespace with the Pod Security Standards `restricted` label, so a pod that forgets `runAsNonRoot` is rejected at admission instead of being found in a security review.
2. ServiceAccount with `eks.amazonaws.com/role-arn` (IRSA). With Pod Identity the annotation goes away and the link lives in an EKS association; the manifest comment shows both. `automountServiceAccountToken: false` because the app never calls the Kubernetes API.
3. ConfigMap for non-secret settings. The Secret is referenced by name only; External Secrets Operator syncs it from Secrets Manager.
4. Deployment: 3 replicas, `maxSurge: 1`, `maxUnavailable: 0`, so a rollout runs 4 pods and never fewer than 3 ready. Requests 250m/512Mi, memory limit 512Mi, no CPU limit.
5. Three probes on two paths: `startupProbe` on `/healthz` every 5 s with failureThreshold 30 (150 s budget), `readinessProbe` on `/readyz` every 5 s, `livenessProbe` on `/healthz` every 10 s. Liveness and readiness do not run until startup succeeds.
6. Graceful stop: `preStop.sleep.seconds: 10` then SIGTERM, inside `terminationGracePeriodSeconds: 30`. The sleep covers the delay between pod deletion and the moment every kube-proxy and the ingress controller stop sending traffic.
7. Placement: a hard zone spread (`maxSkew: 1`, `DoNotSchedule`), a soft node spread, and a preferred pod anti-affinity on hostname.
8. Security context at pod level (`runAsNonRoot`, uid 10001, `fsGroup`, seccomp `RuntimeDefault`) and container level (`readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, drop `ALL`). An `emptyDir` on `/tmp` is the only writable path.
9. Service of type ClusterIP on port 80 to the named port `http`; Ingress with `ingressClassName: nginx`, a `tls` block and the `cert-manager.io/cluster-issuer` annotation.
10. HPA `autoscaling/v2`: CPU utilization target 60 percent, fast scale-up (100 percent or 4 pods per 30 s, `selectPolicy: Max`), slow scale-down (1 pod per 60 s after a 300 s stabilization window, `selectPolicy: Min`).
11. PDB `minAvailable: 2` with `unhealthyPodEvictionPolicy: AlwaysAllow`; NetworkPolicy that allows TCP 8080 only from the `ingress-nginx` and `monitoring` namespaces, matched on the `kubernetes.io/metadata.name` label.

## Architecture diagram

Rendering diagram…

## Deep dives

### Probe timings as a timeline

Take one pod from `kubectl apply` to serving. t=0: container starts. The startup probe hits `/healthz` every 5 s and may fail 30 times, so the app has 150 s to load its JIT, open the DB pool and warm caches; during that window liveness and readiness are not run at all, so a slow start can never cause a restart loop. Suppose startup passes at t=40. From then readiness hits `/readyz` every 5 s with a 2 s timeout; the first success puts the pod into the EndpointSlice, and from that moment the rolling update may remove an old pod. Liveness hits `/healthz` every 10 s; 3 failures in a row (30 s) restart the container. Readiness needs 3 failures (15 s) to pull the pod out of the Service, and one success to put it back. The two paths matter: `/healthz` answers "process alive" with no dependencies, `/readyz` answers "can take traffic now". If liveness checked the database, a database outage would restart every pod, which only makes it worse. Shutdown: `kubectl delete` marks the pod Terminating, the EndpointSlice controller removes it, the kubelet runs `preStop` (sleep 10 s), sends SIGTERM, and kills at 30 s. The grace countdown starts before the hook, so 10 s sleep plus a 15 s drain still fits in 30 s.

### Why the memory limit equals the request

Memory is not compressible: when a container passes its limit the kernel OOM-kills it, and when a node runs out, the kubelet evicts pods that use more than they requested. Setting `limits.memory` equal to `requests.memory` makes the two numbers the same, so the scheduler reserves exactly what the pod can use and the pod is never evicted for using memory the node did not plan for. CPU is different: it is throttled, not killed, so a CPU limit only adds latency when a pod has a short burst and the node has spare cycles. This file sets a CPU request for scheduling and the HPA, and no CPU limit. The resulting QoS class is Burstable (because CPU has no limit), but memory behaves as Guaranteed. Pick the request from a load test: the p99 RSS plus 20 percent headroom, here 512Mi.

### Spread across zones and anti-affinity

`topologySpreadConstraints` with `topologyKey: topology.kubernetes.io/zone`, `maxSkew: 1` and `DoNotSchedule` means that with 3 replicas every zone holds exactly one pod; with 7 replicas the split is 3-2-2, never 4-2-1. The second constraint on `kubernetes.io/hostname` uses `ScheduleAnyway`, so it is only a preference and does not leave pods Pending when the cluster has fewer nodes than replicas. The preferred `podAntiAffinity` on hostname says the same thing in an older vocabulary; keeping both is common because some older admission policies look for anti-affinity. Never make the hostname rule required: during a rollout `maxSurge: 1` needs a fourth pod, and a required rule with only 3 nodes blocks it.

### Ingress controller choice in 2026

The `IngressClass` here is `nginx` because most existing clusters still run ingress-nginx. Say that it was retired upstream in early 2026 and the Ingress API is frozen: a new platform uses Gateway API (`Gateway` plus `HTTPRoute`) through the AWS Load Balancer Controller, Envoy Gateway or Cilium. With the ALB in `ip` target mode the NetworkPolicy `from` becomes an `ipBlock` for the ALB subnets.

### HPA behaviour fields

`behavior` replaces the old fixed cooldown. Each direction has policies, each policy is "at most `value` (pods or percent) per `periodSeconds`", and `selectPolicy` picks `Max` or `Min` among them. Scale-up here: from 3 pods, 100 percent adds 3 and 4 pods adds 4; `Max` chooses 7, so a spike goes 3, 7, 12 within a minute. Scale-down: `stabilizationWindowSeconds: 300` means the controller uses the highest replica recommendation of the last 5 minutes, and the single policy of 1 pod per 60 s makes a fall from 12 to 3 take 9 minutes. The defaults are 0 s up, 300 s down, 100 percent per 15 s down, and a 10 percent tolerance around the target before any change. The target `averageUtilization: 60` is 60 percent of the 250m request, so 150m per pod: at 220m across 3 pods the desired count is ceil(3 x 220 / 150) = 5.

## Evaluation

**Static checks.** `kubeconform -strict -summary orders-api.yaml` validates every document against the API schema, including the HPA `behavior` fields, which plain YAML parsing would not catch. `kubectl apply --dry-run=server` runs admission: the PSS `restricted` label on the Namespace rejects the Deployment if any security field is missing. `kube-linter` or `polaris` flag a missing probe, a missing limit or a `latest` tag.

**Behaviour tests on a kind or EKS cluster.** Rollout: run a load generator at 100 RPS, then `kubectl set image` to a new tag; expect 0 non-2xx responses and `kubectl get pods -w` to show 4 pods at the peak and never fewer than 3 Ready. Probes: break `/readyz` in one pod (`kubectl exec` to touch a file the app checks) and confirm it leaves the EndpointSlice within 15 s and traffic continues. Spread: `kubectl get pods -o custom-columns` with the node's zone label shows three different zones. PDB: `kubectl drain` one node evicts one pod and waits for the replacement before the next. NetworkPolicy: `kubectl run` a curl pod in `default` and show the connection to 8080 times out, then the same from `ingress-nginx` succeeds. HPA: `kubectl autoscale` is not used; instead run CPU load and watch `kubectl get hpa -w` climb to 7 then 12.

**What a strong answer adds.** Two health paths with different meanings; no CPU limit and the reason; `unhealthyPodEvictionPolicy`; the Gateway API `HTTPRoute` equivalent of the Ingress (`parentRefs` to a shared Gateway, `hostnames`, `backendRefs`); `kubernetes.io/metadata.name` for namespace selection; and the Pod Identity alternative to the IRSA annotation. A weak answer has one probe path, `latest` tags, a root container, and an HPA with no `behavior`.

## Bottlenecks & mitigations

* The HPA reacts to CPU averaged over the metrics-server scrape interval, so a spike shorter than about a minute is served by the existing 3 pods or not at all.
* A 150 s startup budget means a scale-up event takes up to 2.5 minutes to add capacity; a faster-starting image or a smaller startup `failureThreshold` shortens it.
* `maxSurge: 1` makes a 12-pod rollout take 12 rounds of start, ready, and stop; raise it to 25 percent when cluster capacity allows.
* The ingress controller namespace is a single choke point for every request and the NetworkPolicy ties the app to that namespace name.
* One ClusterIssuer rate limit (Let's Encrypt allows 50 certificates per registered domain per week) is shared by every Ingress in the cluster.

## Failure modes

* **Pods Pending with "didn't match pod topology spread constraints".** The cluster has fewer than 3 zones or a zone is full. Mitigation: keep the zone rule `DoNotSchedule` only when the node pool spans 3 zones; use Karpenter or Cluster Autoscaler so a full zone adds a node.
* **Readiness flaps and pods leave the Service in waves.** `/readyz` checks the database and the database is slow. Mitigation: readiness checks only local state; add a circuit breaker so a slow dependency returns degraded responses, not failed probes.
* **Liveness restarts a healthy but busy pod.** `timeoutSeconds: 2` is shorter than the handler under GC pause or CPU starvation. Mitigation: a dedicated lightweight handler, a higher timeout, or no CPU limit so the handler is not throttled.
* **502s during rollout.** No preStop sleep, so the ingress still sends traffic to a pod that already received SIGTERM. Mitigation: the 10 s sleep plus the app draining in-flight requests after SIGTERM.
* **OOMKilled under load.** The memory request was chosen from idle usage. Mitigation: load-test, set the request from p99 RSS plus headroom, and alert on `container_memory_working_set_bytes` above 85 percent of the limit.
* **Ingress has no address and the TLS Secret never appears.** The `ingressClassName` or ClusterIssuer name is wrong. Mitigation: `kubectl describe certificate` and `kubectl get challenges` in the namespace; check the controller logs.
* **A drain hangs.** PDB `minAvailable: 2` and only 2 pods are healthy. Mitigation: `unhealthyPodEvictionPolicy: AlwaysAllow` lets the unhealthy one go; fix the root cause of the unhealthy pod.
* **Prometheus cannot scrape.** NetworkPolicy allowed only the ingress namespace. Mitigation: the second rule for the `monitoring` namespace, and a test that scrapes `/metrics` after every policy change.

## Reference solution

YAML · parsed and checked

```
# Production manifests for the "orders-api" web API. Apply in one go:
#   kubectl apply -f orders-api.yaml
# Order inside the file matters only for the Namespace, which must exist first.
---
apiVersion: v1
kind: Namespace
metadata:
  name: orders
  labels:
    # Pod Security Standards: reject any Pod that is not "restricted".
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api
  namespace: orders
  annotations:
    # IRSA: the pod gets this IAM role through the cluster OIDC provider.
    # With EKS Pod Identity you drop this annotation and instead run
    #   aws eks create-pod-identity-association --namespace orders --service-account orders-api --role-arn ...
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/orders-api
automountServiceAccountToken: false  # the app never talks to the Kubernetes API
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: orders-api-config
  namespace: orders
data:
  LOG_LEVEL: "info"
  HTTP_PORT: "8080"
  DB_HOST: "orders-db.cluster-abc.ap-south-1.rds.amazonaws.com"
  CACHE_TTL_SECONDS: "30"
# The Secret "orders-api-secrets" (keys DB_PASSWORD, API_SIGNING_KEY) is NOT in
# this file. External Secrets Operator creates it from AWS Secrets Manager, so
# no credential is ever committed to git.
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orders-api
  namespace: orders
  labels:
    app.kubernetes.io/name: orders-api
    app.kubernetes.io/version: "2.4.1"
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1          # at most 4 pods during a rollout
      maxUnavailable: 0    # never below 3 ready pods
  selector:
    matchLabels:
      app.kubernetes.io/name: orders-api   # immutable after creation
  template:
    metadata:
      labels:
        app.kubernetes.io/name: orders-api
        app.kubernetes.io/version: "2.4.1"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: orders-api
      automountServiceAccountToken: false
      # 10 s preStop sleep + up to 15 s of in-flight requests + margin.
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule   # 3 replicas => one per zone
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: orders-api
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway  # prefer, do not block, node spread
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: orders-api
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                topologyKey: kubernetes.io/hostname
                labelSelector:
                  matchLabels:
                    app.kubernetes.io/name: orders-api
      containers:
        - name: api
          image: 111122223333.dkr.ecr.ap-south-1.amazonaws.com/orders-api:2.4.1
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          envFrom:
            - configMapRef:
                name: orders-api-config
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: orders-api-secrets   # created by External Secrets Operator
                  key: DB_PASSWORD
            - name: API_SIGNING_KEY
              valueFrom:
                secretKeyRef:
                  name: orders-api-secrets
                  key: API_SIGNING_KEY
            - name: POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              memory: 512Mi    # equal to the request: Guaranteed for memory, no throttling on CPU
          # Startup: up to 30 x 5 s = 150 s for JIT warm-up and DB pool;
          # liveness and readiness are paused until it succeeds.
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 5
            failureThreshold: 30
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            periodSeconds: 5
            timeoutSeconds: 2
            failureThreshold: 3   # out of the Service after 15 s of failures
            successThreshold: 1
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 10
            timeoutSeconds: 2
            failureThreshold: 3   # restart after 30 s of failures
          lifecycle:
            preStop:
              sleep:
                seconds: 10   # let EndpointSlice updates reach every kube-proxy and the ingress first
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            capabilities:
              drop: ["ALL"]
            seccompProfile:
              type: RuntimeDefault
          volumeMounts:
            - name: tmp
              mountPath: /tmp   # the only writable path
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 64Mi
---
apiVersion: v1
kind: Service
metadata:
  name: orders-api
  namespace: orders
  labels:
    app.kubernetes.io/name: orders-api
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: orders-api
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: orders-api
  namespace: orders
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod   # cert-manager fills the tls Secret
    nginx.ingress.kubernetes.io/proxy-body-size: 2m
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.orders.example.com
      secretName: orders-api-tls
  rules:
    - host: api.orders.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: orders-api
                port:
                  number: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orders-api
  namespace: orders
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orders-api
  minReplicas: 3
  maxReplicas: 12
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60   # percent of the 250m request, so 150m per pod
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      selectPolicy: Max
      policies:
        - type: Percent
          value: 100     # double at most every 30 s
          periodSeconds: 30
        - type: Pods
          value: 4       # ...or add 4 pods, whichever is larger
          periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 300   # use the highest recommendation of the last 5 min
      selectPolicy: Min
      policies:
        - type: Pods
          value: 1       # remove at most 1 pod per minute
          periodSeconds: 60
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: orders-api
  namespace: orders
spec:
  minAvailable: 2    # node drains may take one pod at a time
  selector:
    matchLabels:
      app.kubernetes.io/name: orders-api
  unhealthyPodEvictionPolicy: AlwaysAllow   # a crash-looping pod must not block a drain
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orders-api
  namespace: orders
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: orders-api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx   # only the ingress controller namespace
      ports:
        - protocol: TCP
          port: 8080
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring       # Prometheus scrapes /metrics
      ports:
        - protocol: TCP
          port: 8080
```

## Follow-up questions interviewers ask

* Replace the Ingress with Gateway API: what are the `Gateway`, `HTTPRoute` and `parentRefs` objects, and who owns each?
* The API now needs a 2 GB model file at start. Which probe values change, and would you use an init container or a PersistentVolume?
* Scale on requests per second instead of CPU. What has to be installed, and what does the metric block look like?
* Two teams share the cluster. How do you stop the second team's pods from reaching orders-api's database port?
* Convert this to a Helm chart. Which values become parameters and which stay fixed?
* The app is now a WebSocket server with 1-hour connections. Which of these settings are wrong?

## Lessons that cover this

* [#15Kubernetes architecture and core objectsKubernetes](/devops/learn/kubernetes-architecture-core-objects)
* [#16Kubernetes networking and storageKubernetes](/devops/learn/kubernetes-networking-storage)
* [#18Helm - charts, templates, values and releasesKubernetes](/devops/learn/helm-charts)
* [#25Kubernetes internals and operators in GoContribute](/devops/learn/kubernetes-internals-operators-go)

## Further reading

* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)
* [Kubernetes: Gateway APIGuidegateway-api.sigs.k8s.io](https://gateway-api.sigs.k8s.io/)
* [Google Cloud: Kubernetes best practices: Resource requests and limitsArticlecloud.google.com](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-resource-requests-and-limits)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousGitHub Actions: build, test, cache, push an image and deploy](/devops/problems/github-actions-build-push-deploy)[NextTerraform: VPC and autoscaling group module](/devops/problems/terraform-vpc-asg-module)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Approach](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Evaluation](#evaluation)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Reference solution](#code)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
