# Kubernetes internals and operators in Go — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/kubernetes-internals-operators-go

[DevOps roadmap](/devops)

ContributeLesson #25StudyAdvanced 6 h

# Kubernetes internals and operators in Go

Kubernetes is an API server plus a crowd of control loops. This lesson opens the box: how the API server names and stores objects, what resourceVersion and generation mean, how watches work, and how a controller turns events into a reconcile function that is safe to run again and again. Then you build an operator for a WebApp custom resource with controller-runtime and kubebuilder, test it with envtest, and learn to read the Kubernetes source itself.

kubernetesoperatorscontroller-runtimekubebuilderclient-gocrdgo

## Why it matters

Every CNCF project written in Go (Argo CD, cert-manager, Karpenter, KEDA, Cilium's operator, Flux) is a set of controllers built from the same pieces: client-go, informers, work queues and a reconcile function. LFX Mentorship and GSoC tasks on these projects assume you can read that code. In platform engineering interviews, "write an operator" or "what happens when two controllers update the same object" is the question that separates people who have run Kubernetes from people who can extend it. This lesson gives you the vocabulary and one complete, working operator.

Read first: [Python and Go for automation and tooling](/devops/learn/python-and-go-for-devops), [Kubernetes architecture and core objects](/devops/learn/kubernetes-architecture-core-objects), [Kubernetes in production - resources, autoscaling, RBAC, upgrades, EKS](/devops/learn/kubernetes-in-production), [Helm - charts, templates, values and releases](/devops/learn/helm-charts)

## Lesson

### The API server: groups, versions, kinds and resources

The API server is an HTTP server with a database behind it (etcd). Everything it stores is addressed by four names. A **group** is a family of APIs (`apps`, `batch`, `networking.k8s.io`, or your own `webapp.example.com`); the original core group has no name and lives under `/api/v1`. A **version** (`v1alpha1`, `v1beta1`, `v1`) says how stable the schema is. A **kind** is the Go type of one object (`Deployment`). A **resource** is the plural, lower-case name in the URL (`deployments`). The pair of group, version and resource is called a GVR, and group, version and kind is a GVK; `kubectl api-resources` lists them all.

| Request | Path | Scope |
| --- | --- | --- |
| All pods in the cluster | `GET /api/v1/pods` | cluster-wide list of a namespaced resource |
| One deployment | `GET /apis/apps/v1/namespaces/shop/deployments/api` | namespaced |
| Only its status | `PUT /apis/apps/v1/namespaces/shop/deployments/api/status` | subresource |
| A node | `GET /api/v1/nodes/ip-10-0-1-7` | cluster-scoped, no namespace in the path |
| Your CRD's objects | `GET /apis/webapp.example.com/v1/namespaces/shop/webapps` | namespaced custom resource |

Two more endpoints matter. **Discovery** (`/apis` and `/apis/apps/v1`) tells clients which groups, versions and resources exist; kubectl reads it to turn `kubectl get deploy` into the right URL. **OpenAPI** (`/openapi/v3`) publishes the schema of every type, used by `kubectl explain` and client-side validation. The **aggregation layer** mounts a separate API server (metrics-server is the common one) under `/apis/metrics.k8s.io`, so one endpoint serves both.

### An object on the wire

Every object has the same shape. `apiVersion` and `kind` identify the type. `metadata` carries the name, namespace, labels, annotations and the fields the system owns. `spec` is what you want; `status` is what the controller observed. The fields in metadata that a controller author must know:

* `resourceVersion`: an opaque string that changes on every write. Clients must pass it back unmodified; it is the key to concurrency control and to watches.
* `generation`: an integer the server increments only when `spec` changes. A controller copies it into `status.observedGeneration` so a reader can tell whether the status is about the current spec.
* `uid`: unique for the life of the object; a new object with the same name gets a new uid.
* `ownerReferences`: the list of objects that own this one, with `controller: true` on the one managing it. When the owner is deleted, the garbage collector deletes the children.
* `finalizers`: a list of strings. While it is non-empty, a delete only sets `deletionTimestamp`; the object stays until every controller removes its own entry.

### Optimistic concurrency, watches and admission

The API server has no locks. An update carries the `resourceVersion` the client last read; if the stored object has moved on, the server answers `409 Conflict` and the client must read again, re-apply its change and retry. `retry.RetryOnConflict(retry.DefaultRetry, fn)` in client-go does exactly that, with 5 tries 10 ms apart. Two controllers can therefore write the same object safely as long as both retry.

A **watch** is a long HTTP request (`?watch=1&resourceVersion=10245`) that streams `ADDED`, `MODIFIED` and `DELETED` events after that version. etcd keeps about 5 minutes of history, so a client that reconnects too late gets `410 Gone` and must list again and watch from the new version. With `allowWatchBookmarks=true` the server sends occasional `BOOKMARK` events carrying only a resourceVersion, so the client can restart from a fresh point. This list-then-watch cycle is what an informer does for you.

Before a write reaches etcd it passes the **admission chain**: mutating admission (built-in plugins, then mutating webhooks, which may change the object), schema validation, then validating admission (built-in plugins, ValidatingAdmissionPolicy written in CEL, and validating webhooks). An admission webhook is an HTTPS server you run; the API server calls it with an `AdmissionReview` and waits for allow or deny.

### The controller pattern, precisely

A controller is a loop that moves the actual state toward the desired state. The rules below are the ones the Kubernetes contributor guide states for every controller in the tree.

* **Level-based, not edge-based.** The reconcile function never looks at the event ("replicas went from 2 to 3"). It reads the current state ("the WebApp says 3, the Deployment has 2") and fixes the difference. If the controller was down for an hour, it catches up on restart because the level is still there; an edge would have been missed.
* **One key at a time.** Events are turned into keys (`namespace/name`) on a work queue. The queue dedupes, so 50 events for one object become one reconcile, and it guarantees no two workers handle the same key at once.
* **Idempotent.** Running reconcile twice must produce the same result as running it once. Create only what is missing; update only what differs.
* **Requeue with backoff.** Return an error and the key goes back on the queue through `AddRateLimited`: the default controller rate limiter starts at 5 ms per item, doubles on each failure up to 1000 s, and also caps the whole controller at 10 retries per second with a burst of 100. Return success and the failure count is forgotten.
* **Report through status.** Set `status.conditions` (type, status, reason, message, lastTransitionTime, observedGeneration) rather than logging. `Ready=True` with `observedGeneration` equal to `metadata.generation` is how a user or Argo CD knows the object is done.
* **Own what you create.** Set an owner reference on every child. Garbage collection then deletes the Deployment when the WebApp goes, and the informer on Deployments can map a child event back to the owner key.
* **Finalizers for external cleanup.** If the controller created something outside the cluster (an S3 bucket, a DNS record), add a finalizer, delete the external thing when `deletionTimestamp` is set, then remove the finalizer.
* **Leader election.** Run two or three replicas but let only one reconcile, by holding a `Lease` object in the cluster. controller-runtime defaults are a 15 s lease, a 10 s renew deadline and a 2 s retry period.

The informer also **resyncs**: periodically it replays every cached object through the update handler (controller-runtime defaults to 10 hours), so a reconcile that silently failed to requeue still gets another chance.

![The controller loop: informer and cache on the left feeding a work queue and Reconcile, the API server and a WebApp custom resource owning a Deployment and a Service on the right, with resourceVersion, requeue and 409 Conflict marked](/devops/img/operator-reconcile-loop.svg)The controller loop: informer and cache on the left feeding a work queue and Reconcile, the API server and a WebApp custom resource owning a Deployment and a Service on the right, with resourceVersion, requeue and 409 Conflict marked

### CustomResourceDefinitions

A CRD adds a new resource to the API server without any code. The server stores, validates and serves it exactly like a built-in type. The schema is OpenAPI v3; `x-kubernetes-validations` adds CEL rules such as `self.replicas <= 10`. A CRD may serve several versions; exactly one has `storage: true`, and conversion between versions is either `strategy: None` (same fields, only `apiVersion` changes) or `strategy: Webhook` (your code converts). Two subresources matter: `status`, which makes `/status` a separate endpoint so a controller can update status without touching spec and users cannot change status through a normal update, and `scale`, which lets `kubectl scale` and the HorizontalPodAutoscaler work on your type by pointing at `.spec.replicas` and `.status.replicas`.

```
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.webapp.example.com
spec:
  group: webapp.example.com
  names: {kind: WebApp, plural: webapps, singular: webapp, shortNames: [wa]}
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      subresources:
        status: {}
        scale: {specReplicasPath: .spec.replicas, statusReplicasPath: .status.replicas}
      additionalPrinterColumns:     # what kubectl get webapps shows
        - {name: Replicas, type: integer, jsonPath: .spec.replicas}
        - {name: Ready, type: integer, jsonPath: .status.readyReplicas}
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: [image]
              properties:
                image: {type: string}
                replicas: {type: integer, minimum: 1, maximum: 50, default: 1}
                port: {type: integer, default: 8080}
            status:
              type: object
              properties:
                readyReplicas: {type: integer}
                observedGeneration: {type: integer}
```

With kubebuilder you never write this file; it is generated from Go struct tags and markers.

### client-go: clientset, informers and listers

`k8s.io/client-go` is the Go library every controller uses. The **clientset** is the typed client: `clientset.AppsV1().Deployments("shop").Get(ctx, "api", metav1.GetOptions{})` returns a `*appsv1.Deployment`. The **dynamic client** works on `unstructured.Unstructured` maps for types it does not know at compile time, which is what tools like Argo CD and kubectl use. Polling the API server from every controller would not scale, so client-go provides the **informer**: a reflector that lists then watches one resource, a local cache (the indexer), and event handlers. A **lister** is a read-only view of that cache, so `Get` and `List` in a reconcile never hit the network. The **shared informer factory** gives every controller in a process one informer per resource instead of one watch each. Cache reads can be slightly stale; that is fine, because a write from stale data fails with a 409 and the retry reads fresh data.

### controller-runtime and kubebuilder

`sigs.k8s.io/controller-runtime` wraps client-go into three ideas. The **Manager** holds the shared cache, the client, leader election, metrics and health endpoints, and starts every controller. A **Reconciler** implements `Reconcile(ctx, req) (Result, error)`. The **builder** wires watches: `For(&WebApp{})` makes the controller reconcile WebApps; `Owns(&Deployment{})` watches Deployments and enqueues the owner on any change; `Watches(...)` with a map function handles anything else. The client is one `client.Client` for every type, reading from the cache and writing to the server; `r.Status().Update` writes the status subresource.

**kubebuilder** scaffolds all of this and generates the boring parts with `controller-gen` from markers (comments that start with `+kubebuilder:`):

```
kubebuilder init --domain example.com --repo example.com/webapp-operator
kubebuilder create api --group webapp --version v1 --kind WebApp   # answer y to resource and controller
make manifests   # CRD YAML, RBAC ClusterRole and webhook config from markers -> config/
make generate    # zz_generated.deepcopy.go: DeepCopy methods every runtime.Object needs
make install     # kubectl apply the CRDs into the current cluster
make run         # run the manager on your laptop against the cluster in ~/.kube/config
make test        # envtest: a real kube-apiserver and etcd, no kubelet or controllers
make docker-build docker-push IMG=registry.example.com/webapp-operator:0.1.0
make deploy IMG=registry.example.com/webapp-operator:0.1.0
```

The generated tree is `api/v1/webapp_types.go` (the structs), `internal/controller/webapp_controller.go` (the reconciler), `cmd/main.go` (the manager), `config/` (kustomize bases for CRD, RBAC, manager, samples). The Operator SDK is a framework from the Operator Framework project that builds on the same controller-runtime library and adds Helm and Ansible operator types plus packaging for OLM; a Go operator from either tool looks the same.

### The WebApp operator, end to end

The types file. Markers drive the CRD above: validation, printer columns, the status subresource.

```
// needs: sigs.k8s.io/controller-runtime
package v1

import metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

type WebAppSpec struct {
	Image string `json:"image"`
	// +kubebuilder:validation:Minimum=1
	// +kubebuilder:validation:Maximum=50
	// +kubebuilder:default=1
	Replicas int32 `json:"replicas,omitempty"`
	// +kubebuilder:default=8080
	Port int32 `json:"port,omitempty"`
}

type WebAppStatus struct {
	ReadyReplicas      int32              `json:"readyReplicas,omitempty"`
	ObservedGeneration int64              `json:"observedGeneration,omitempty"`
	Conditions         []metav1.Condition `json:"conditions,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:subresource:scale:specpath=.spec.replicas,statuspath=.status.readyReplicas
// +kubebuilder:printcolumn:name="Replicas",type=integer,JSONPath=`.spec.replicas`
// +kubebuilder:printcolumn:name="Ready",type=integer,JSONPath=`.status.readyReplicas`
type WebApp struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              WebAppSpec   `json:"spec,omitempty"`
	Status            WebAppStatus `json:"status,omitempty"`
}
```

The reconciler. Read the four numbered steps; everything else is plumbing.

```
// needs: sigs.k8s.io/controller-runtime
package controller

// +kubebuilder:rbac:groups=webapp.example.com,resources=webapps,verbs=get;list;watch;update;patch
// +kubebuilder:rbac:groups=webapp.example.com,resources=webapps/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services,verbs=get;list;watch;create;update;patch;delete

func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	// 1. Read the object from the cache. Gone means deleted: nothing to do, GC removes the children.
	var app webappv1.WebApp
	if err := r.Get(ctx, req.NamespacedName, &app); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// 2. Deployment: create it if missing, otherwise bring replicas and image in line.
	dep := &appsv1.Deployment{ObjectMeta: metav1.ObjectMeta{Name: app.Name, Namespace: app.Namespace}}
	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, dep, func() error {
		labels := map[string]string{"app": app.Name}
		dep.Spec.Replicas = &app.Spec.Replicas
		dep.Spec.Selector = &metav1.LabelSelector{MatchLabels: labels}
		dep.Spec.Template.ObjectMeta.Labels = labels
		dep.Spec.Template.Spec.Containers = []corev1.Container{{
			Name: "web", Image: app.Spec.Image,
			Ports: []corev1.ContainerPort{{ContainerPort: app.Spec.Port}},
		}}
		return controllerutil.SetControllerReference(&app, dep, r.Scheme) // ownerReference, controller=true
	})
	if err != nil {
		return ctrl.Result{}, err // a 409 Conflict lands here and is requeued with backoff
	}

	// 3. Service: same pattern. Owned, so deleting the WebApp deletes it too.
	svc := &corev1.Service{ObjectMeta: metav1.ObjectMeta{Name: app.Name, Namespace: app.Namespace}}
	if _, err := controllerutil.CreateOrUpdate(ctx, r.Client, svc, func() error {
		svc.Spec.Selector = map[string]string{"app": app.Name}
		svc.Spec.Ports = []corev1.ServicePort{{Port: 80, TargetPort: intstr.FromInt32(app.Spec.Port)}}
		return controllerutil.SetControllerReference(&app, svc, r.Scheme)
	}); err != nil {
		return ctrl.Result{}, err
	}

	// 4. Status: report what the Deployment observed, through the status subresource.
	app.Status.ReadyReplicas = dep.Status.ReadyReplicas
	app.Status.ObservedGeneration = app.Generation
	ready := dep.Status.ReadyReplicas == app.Spec.Replicas
	meta.SetStatusCondition(&app.Status.Conditions, metav1.Condition{
		Type: "Ready", Status: boolToCondition(ready), Reason: "Reconciled",
		Message: fmt.Sprintf("%d/%d replicas ready", dep.Status.ReadyReplicas, app.Spec.Replicas),
		ObservedGeneration: app.Generation,
	})
	return ctrl.Result{}, r.Status().Update(ctx, &app)
}

func (r *WebAppReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&webappv1.WebApp{}).
		Owns(&appsv1.Deployment{}). // Deployment events enqueue the owning WebApp
		Owns(&corev1.Service{}).
		Complete(r)
}
```

There is no finalizer here because every child is in the cluster and owner references are enough. Add one only for resources outside Kubernetes.

### Testing, packaging and admission webhooks

**envtest** starts a real `kube-apiserver` and `etcd` binary on your laptop (fetched by `setup-envtest`, pointed to by `KUBEBUILDER_ASSETS`), with no kubelet, scheduler or built-in controllers. Your test creates a WebApp, runs the manager, and asserts that a Deployment with the right replica count appears. Because no controllers run, `dep.Status.ReadyReplicas` stays 0 and garbage collection never happens; tests must set status by hand or not depend on it. For an end-to-end check, `kind create cluster`, `make install`, `make run` and `kubectl apply -f config/samples/`.

**Packaging** is an image (the scaffold's Dockerfile builds a distroless, non-root manager), the generated RBAC (a ClusterRole with exactly the verbs in the markers, a ServiceAccount, a binding), the CRDs, and a Deployment with `--leader-elect`. Teams ship this as a Helm chart with the CRDs in the chart's `crds/` directory, where Helm installs them once and never upgrades them, which is why CRD changes need their own release step.

**Admission webhooks** in Go: `kubebuilder create webhook --group webapp --version v1 --kind WebApp --defaulting --programmatic-validation` scaffolds a `CustomDefaulter` (`Default`) and a `CustomValidator` (`ValidateCreate`, `ValidateUpdate`, `ValidateDelete`) registered through `ctrl.NewWebhookManagedBy(mgr, &WebApp{}).WithDefaulter(...).WithValidator(...).Complete()`. Two gotchas cost people days. First, the API server only speaks HTTPS to webhooks and verifies the certificate against `caBundle` in the webhook configuration; the scaffold uses cert-manager to issue the serving certificate and inject the CA with the `cert-manager.io/inject-ca-from` annotation, so a missing or expired certificate makes every create fail. Second, `failurePolicy` defaults to `Fail`: if your webhook pod is down or slower than `timeoutSeconds` (default 10 s, maximum 30 s), every matching request in the cluster is rejected, including the one that would restart your webhook. Scope the webhook with `namespaceSelector` and `objectSelector`, keep the timeout short, and use `Ignore` for anything that is not a security control.

### Where the design came from, and how to read the source

The design is described in the paper "Borg, Omega, and Kubernetes": Borg had a central master with per-job state machines; Omega replaced it with a shared, transactional store that many independent schedulers watched optimistically; Kubernetes kept Omega's shared store idea but put an API server in front of it, so that every component is a client that watches and writes through one audited door. The 409 conflict you handle in a controller is the direct descendant of Omega's optimistic transactions.

The `kubernetes/kubernetes` repository: `cmd/` holds the binaries (`cmd/kube-apiserver`, `cmd/kube-controller-manager`, `cmd/kubelet`); `pkg/` holds their implementation; `staging/src/k8s.io/` holds the libraries that are published as separate modules (`client-go`, `apimachinery`, `api`) and are developed here first. The Deployment controller is `pkg/controller/deployment/deployment_controller.go`; `syncDeployment` is its reconcile function and `sync.go` holds the scaling logic. To run one test:

```
make test WHAT=./pkg/controller/deployment                     # one package
go test ./pkg/controller/deployment -run ^TestSyncDeploymentCreatesReplicaSet$ -v
```

Start from `main`, follow the flags into the options struct, then into `Run`; the tests next to each file are the best documentation of what a function promises.

## Diagram

Rendering diagram…

## Worked example

**One reconcile, step by step: the user scales the WebApp `shop` from 2 to 3.**

Before: WebApp `shop` has `spec.replicas: 2`, `resourceVersion: 5`, `generation: 1`, `status.readyReplicas: 2`. Its Deployment `shop` has `replicas: 2`, `resourceVersion: 4`, 2 ready pods.

1. `kubectl patch webapp shop --type merge -p '{"spec":{"replicas":3}}'`. The API server runs admission, the schema allows 3 (maximum 50), writes the object with `resourceVersion: 6` and bumps `generation` to 2 because spec changed.
2. The WebApp informer in the operator receives `MODIFIED` with rv 6, replaces the cached copy, and the event handler adds the key `shop/shop` to the work queue. If the user had patched three times in a second there would still be one item in the queue.
3. A worker takes the key and calls `Reconcile`. It reads the WebApp (rv 6, replicas 3) and the Deployment (rv 4, replicas 2) from the cache: no network calls.
4. `CreateOrUpdate` sees the Deployment differs and sends `PUT .../deployments/shop` carrying rv 4. Meanwhile the Deployment controller in kube-controller-manager has just written `status.observedGeneration` on the same Deployment, so the stored rv is 7. The API server answers `409 Conflict`.
5. Reconcile returns the error. The queue calls `AddRateLimited`: the first failure waits 5 ms (next ones would be 10, 20, 40 ms and so on), then the key is back in the queue.
6. The informer has by now received the Deployment's `MODIFIED` at rv 7 (the `Owns` watch), so the second reconcile reads a fresh copy and sends the update with rv 7. The server stores rv 8. The reconcile sets `status.readyReplicas` to 2 (still what the Deployment reports), `observedGeneration: 2`, `Ready=False` with message `2/3 replicas ready`, and returns nil; the queue forgets the failure count.
7. The ReplicaSet controller creates a third pod. When it passes readiness, the Deployment's `status.readyReplicas` becomes 3, which is a Deployment `MODIFIED` event, which enqueues the owner `shop/shop` again.
8. That reconcile finds nothing to change in the Deployment, writes `status.readyReplicas: 3` and `Ready=True`. Count the status writes: two, and the Deployment writes: one successful plus one rejected. Count the reconciles: three for one user action, each cheap because reads come from the cache.

The two numbers an interviewer listens for: the controller made zero API reads (all cache), and the only retry was driven by a real conflict, not by a timer.

## Runnable code

Go · gofmt and go vet clean · runs and prints its own checks

```
// The controller pattern in miniature, standard library only.
//
// An in-memory "API server" stores objects with a resourceVersion and
// rejects stale updates (409 Conflict). A watch channel delivers events.
// A work queue dedupes keys and requeues failures with exponential backoff.
// One reconcile function keeps a Deployment in step with a WebApp and
// writes readyReplicas into the WebApp status. A finalizer cleans up the
// Deployment before the WebApp is allowed to disappear.
//
// Problem 41 (go-reconcile-loop) is the full exercise; this is the sketch.
package main

import (
	"errors"
	"fmt"
	"os"
	"sort"
	"strings"
	"sync"
	"time"
)

// ---------- objects on the wire ----------

type Object struct {
	Kind            string
	Name            string
	ResourceVersion int      // set by the server, bumped on every write
	Generation      int      // bumped only when Spec changes
	Spec            int      // desired replicas
	StatusReady     int      // observed ready replicas
	Finalizers      []string // must be empty before the object is removed
	Deleting        bool     // deletionTimestamp is set
	Owner           string   // key of the owning object, if any
}

func key(kind, name string) string { return kind + "/" + name }

type Event struct {
	Type string // ADDED, MODIFIED, DELETED
	Obj  Object
}

// ---------- the in-memory API server ----------

var errConflict = errors.New("409 Conflict: resourceVersion is stale")
var errNotFound = errors.New("404 NotFound")

type APIServer struct {
	mu            sync.Mutex
	rv            int
	store         map[string]Object
	watchers      []chan Event
	log           []string
	conflictOnKey string // simulate another writer touching this key once
}

func NewAPIServer() *APIServer { return &APIServer{store: map[string]Object{}} }

func (s *APIServer) logf(format string, a ...any) {
	s.log = append(s.log, fmt.Sprintf(format, a...))
}

func (s *APIServer) emit(ev Event) {
	for _, w := range s.watchers {
		w <- ev
	}
}

func (s *APIServer) Watch() <-chan Event {
	s.mu.Lock()
	defer s.mu.Unlock()
	ch := make(chan Event, 64)
	s.watchers = append(s.watchers, ch)
	return ch
}

func (s *APIServer) Get(kind, name string) (Object, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	o, ok := s.store[key(kind, name)]
	if !ok {
		return Object{}, errNotFound
	}
	return o, nil
}

func (s *APIServer) Create(o Object) (Object, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	k := key(o.Kind, o.Name)
	if _, ok := s.store[k]; ok {
		return o, fmt.Errorf("409 AlreadyExists: %s", k)
	}
	s.rv++
	o.ResourceVersion, o.Generation = s.rv, 1
	s.store[k] = o
	s.logf("server: CREATE %s rv=%d spec=%d", k, o.ResourceVersion, o.Spec)
	s.emit(Event{"ADDED", o})
	return o, nil
}

// Update is optimistic concurrency: the caller's resourceVersion must equal
// the stored one, otherwise someone else wrote in between and we refuse.
func (s *APIServer) Update(o Object) (Object, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	k := key(o.Kind, o.Name)
	cur, ok := s.store[k]
	if !ok {
		return o, errNotFound
	}
	if s.conflictOnKey == k { // another client slipped in a write
		s.conflictOnKey = ""
		s.rv++
		cur.ResourceVersion = s.rv
		s.store[k] = cur
		s.logf("server: another client wrote %s, rv is now %d", k, s.rv)
	}
	if o.ResourceVersion != cur.ResourceVersion {
		s.logf("server: REJECT update of %s (sent rv=%d, stored rv=%d)", k, o.ResourceVersion, cur.ResourceVersion)
		return o, errConflict
	}
	s.rv++
	o.ResourceVersion = s.rv
	o.Generation = cur.Generation
	if o.Spec != cur.Spec {
		o.Generation++
	}
	o.Deleting = cur.Deleting
	// A deleting object with no finalizers left is removed for real.
	if o.Deleting && len(o.Finalizers) == 0 {
		delete(s.store, k)
		s.logf("server: finalizers empty, %s removed from storage", k)
		s.emit(Event{"DELETED", o})
		return o, nil
	}
	s.store[k] = o
	s.logf("server: UPDATE %s rv=%d gen=%d spec=%d ready=%d fin=%v", k, o.ResourceVersion, o.Generation, o.Spec, o.StatusReady, o.Finalizers)
	s.emit(Event{"MODIFIED", o})
	return o, nil
}

// Delete sets deletionTimestamp when finalizers exist, otherwise removes now.
func (s *APIServer) Delete(kind, name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	k := key(kind, name)
	o, ok := s.store[k]
	if !ok {
		return errNotFound
	}
	if len(o.Finalizers) > 0 {
		s.rv++
		o.ResourceVersion, o.Deleting = s.rv, true
		s.store[k] = o
		s.logf("server: DELETE %s has finalizers %v, set deletionTimestamp rv=%d", k, o.Finalizers, o.ResourceVersion)
		s.emit(Event{"MODIFIED", o})
		return nil
	}
	delete(s.store, k)
	s.logf("server: DELETE %s removed", k)
	s.emit(Event{"DELETED", o})
	return nil
}

func (s *APIServer) Count() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.store)
}

// ---------- the work queue ----------

type Queue struct {
	mu       sync.Mutex
	items    []string
	queued   map[string]bool
	failures map[string]int
	wake     chan struct{}
}

func NewQueue() *Queue {
	return &Queue{queued: map[string]bool{}, failures: map[string]int{}, wake: make(chan struct{}, 1)}
}

func (q *Queue) Add(k string) {
	q.mu.Lock()
	if !q.queued[k] { // dedupe: ten events for one key become one item
		q.queued[k] = true
		q.items = append(q.items, k)
	}
	q.mu.Unlock()
	select {
	case q.wake <- struct{}{}:
	default:
	}
}

// AddRateLimited waits 5 ms * 2^failures before putting the key back.
func (q *Queue) AddRateLimited(k string) time.Duration {
	q.mu.Lock()
	n := q.failures[k]
	q.failures[k] = n + 1
	q.mu.Unlock()
	delay := 5 * time.Millisecond << uint(n)
	if delay > time.Second {
		delay = time.Second
	}
	time.AfterFunc(delay, func() { q.Add(k) })
	return delay
}

func (q *Queue) Forget(k string) { q.mu.Lock(); delete(q.failures, k); q.mu.Unlock() }

func (q *Queue) Get() string {
	for {
		q.mu.Lock()
		if len(q.items) > 0 {
			k := q.items[0]
			q.items = q.items[1:]
			delete(q.queued, k)
			q.mu.Unlock()
			return k
		}
		q.mu.Unlock()
		<-q.wake
	}
}

// ---------- the WebApp controller ----------

const finalizer = "webapp.example.com/cleanup"

type Controller struct {
	api *APIServer
	q   *Queue
	log *[]string
}

func (c *Controller) logf(format string, a ...any) {
	c.api.mu.Lock()
	*c.log = append(*c.log, fmt.Sprintf(format, a...))
	c.api.mu.Unlock()
}

// Reconcile is level-based: it never looks at the event, only at the
// current state, and it is safe to call any number of times.
func (c *Controller) Reconcile(name string) error {
	app, err := c.api.Get("WebApp", name)
	if errors.Is(err, errNotFound) {
		c.logf("reconcile %s: gone, nothing to do", name)
		return nil
	}
	// 1. Deletion path: clean up the child, then drop our finalizer.
	if app.Deleting {
		if _, err := c.api.Get("Deployment", name); err == nil {
			c.logf("reconcile %s: deleting, removing child Deployment first", name)
			if err := c.api.Delete("Deployment", name); err != nil {
				return err
			}
		}
		app.Finalizers = remove(app.Finalizers, finalizer)
		_, err := c.api.Update(app)
		if err == nil {
			c.logf("reconcile %s: finalizer removed, object can go", name)
		}
		return err
	}
	// 2. Make sure our finalizer is present before we create anything.
	if !contains(app.Finalizers, finalizer) {
		app.Finalizers = append(app.Finalizers, finalizer)
		_, err := c.api.Update(app) // the MODIFIED event will requeue us
		return err
	}
	// 3. Ensure the owned Deployment exists and has the right size.
	dep, err := c.api.Get("Deployment", name)
	if errors.Is(err, errNotFound) {
		dep = Object{Kind: "Deployment", Name: name, Spec: app.Spec, Owner: key("WebApp", name)}
		if _, err := c.api.Create(dep); err != nil {
			return err
		}
		c.logf("reconcile %s: created Deployment with %d replicas", name, app.Spec)
		return nil
	}
	if dep.Spec != app.Spec {
		c.logf("reconcile %s: Deployment has %d replicas, want %d, updating with rv=%d", name, dep.Spec, app.Spec, dep.ResourceVersion)
		dep.Spec = app.Spec
		if _, err := c.api.Update(dep); err != nil {
			c.logf("reconcile %s: update failed: %v", name, err)
			return err
		}
		return nil
	}
	// 4. Report what we observe in status.
	if app.StatusReady != dep.StatusReady {
		app.StatusReady = dep.StatusReady
		if _, err := c.api.Update(app); err != nil {
			return err
		}
		c.logf("reconcile %s: status.readyReplicas=%d", name, dep.StatusReady)
	}
	return nil
}

// Run is the informer plus worker loop: watch events become queue keys,
// keys are reconciled one at a time, failures are requeued with backoff.
func (c *Controller) Run(events <-chan Event, stop <-chan struct{}) {
	go func() {
		for ev := range events {
			switch {
			case ev.Obj.Kind == "WebApp":
				c.q.Add(ev.Obj.Name)
			case ev.Obj.Owner != "": // an owned child changed: enqueue the owner
				c.q.Add(strings.TrimPrefix(ev.Obj.Owner, "WebApp/"))
			}
		}
	}()
	go func() {
		for {
			k := c.q.Get()
			if err := c.Reconcile(k); err != nil {
				d := c.q.AddRateLimited(k)
				c.logf("queue: requeue %s after %v (%v)", k, d, err)
			} else {
				c.q.Forget(k)
			}
		}
	}()
	<-stop
}

// fakeKubelet marks Deployments ready a little after their spec changes,
// the way real pods come up after the ReplicaSet controller creates them.
func fakeKubelet(api *APIServer, events <-chan Event) {
	for ev := range events {
		if ev.Obj.Kind != "Deployment" || ev.Type == "DELETED" || ev.Obj.StatusReady == ev.Obj.Spec {
			continue
		}
		o := ev.Obj
		time.AfterFunc(10*time.Millisecond, func() {
			cur, err := api.Get("Deployment", o.Name)
			if err != nil || cur.ResourceVersion != o.ResourceVersion {
				return // stale: a newer event will handle it
			}
			cur.StatusReady = cur.Spec
			api.Update(cur)
		})
	}
}

// ---------- helpers ----------

func contains(xs []string, s string) bool {
	for _, x := range xs {
		if x == s {
			return true
		}
	}
	return false
}

func remove(xs []string, s string) []string {
	out := xs[:0:0]
	for _, x := range xs {
		if x != s {
			out = append(out, x)
		}
	}
	return out
}

func waitFor(what string, cond func() bool) {
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if cond() {
			return
		}
		time.Sleep(2 * time.Millisecond)
	}
	fmt.Println("FAIL: timed out waiting for", what)
	os.Exit(1)
}

func check(ok bool, msg string) {
	if ok {
		fmt.Println("PASS:", msg)
		return
	}
	fmt.Println("FAIL:", msg)
	os.Exit(1)
}

func main() {
	api := NewAPIServer()
	ctl := &Controller{api: api, q: NewQueue(), log: &api.log}
	// Register both watches before anything is created, so no event is missed.
	go fakeKubelet(api, api.Watch())
	stop := make(chan struct{})
	go ctl.Run(api.Watch(), stop)

	// Scenario 1: a user creates a WebApp with 2 replicas.
	api.Create(Object{Kind: "WebApp", Name: "shop", Spec: 2})
	waitFor("status ready=2", func() bool {
		a, err := api.Get("WebApp", "shop")
		return err == nil && a.StatusReady == 2
	})
	app, _ := api.Get("WebApp", "shop")
	check(contains(app.Finalizers, finalizer), "finalizer was added before the child was created")
	dep, _ := api.Get("Deployment", "shop")
	check(dep.Spec == 2 && dep.Owner == "WebApp/shop", "Deployment exists with 2 replicas and an owner reference")

	// Scenario 2: the user scales to 3 while another client touches the
	// Deployment at the same moment, so the controller's first update is stale.
	api.mu.Lock()
	api.conflictOnKey = "Deployment/shop"
	api.mu.Unlock()
	app, _ = api.Get("WebApp", "shop")
	app.Spec = 3
	api.Update(app)
	waitFor("status ready=3", func() bool {
		a, err := api.Get("WebApp", "shop")
		return err == nil && a.StatusReady == 3 && a.Generation == 2
	})
	dep, _ = api.Get("Deployment", "shop")
	check(dep.Spec == 3 && dep.StatusReady == 3, "Deployment resized to 3 after the conflict was retried")

	// Scenario 3: delete the WebApp; the finalizer must remove the child first.
	api.Delete("WebApp", "shop")
	waitFor("both objects gone", func() bool { return api.Count() == 0 })
	check(api.Count() == 0, "finalizer removed the Deployment, then the WebApp was removed")

	// Stop the worker and print the event log in server order.
	close(stop)
	api.mu.Lock()
	lines := append([]string(nil), api.log...)
	api.mu.Unlock()
	fmt.Println("\nevent log:")
	for i, l := range lines {
		fmt.Printf("%3d  %s\n", i+1, l)
	}
	conflicts, requeues := 0, 0
	for _, l := range lines {
		if strings.Contains(l, "REJECT") {
			conflicts++
		}
		if strings.Contains(l, "requeue") {
			requeues++
		}
	}
	check(conflicts == 1 && requeues >= 1, fmt.Sprintf("exactly one 409 conflict (%d) and at least one rate-limited requeue (%d)", conflicts, requeues))
	kinds := map[string]bool{}
	for _, l := range lines {
		for _, w := range strings.Fields(l) {
			if strings.HasPrefix(w, "WebApp/") || strings.HasPrefix(w, "Deployment/") {
				kinds[strings.Split(w, "/")[0]] = true
			}
		}
	}
	ks := make([]string, 0, len(kinds))
	for k := range kinds {
		ks = append(ks, k)
	}
	sort.Strings(ks)
	fmt.Println("kinds seen:", strings.Join(ks, ", "))
}
```

## Key takeaways

* The API server addresses everything by group, version and resource; discovery and OpenAPI let clients find and validate types without hard-coding them.
* resourceVersion is an opaque write counter used for optimistic concurrency and watches; generation counts spec changes and status.observedGeneration says which one the controller has seen.
* A controller is level-based: it reads current state and fixes the difference, which is why it survives restarts and why reconcile must be idempotent.
* Reads come from the informer cache, writes go to the API server, and a 409 Conflict is normal: return the error and let the rate-limited queue retry.
* Owner references give you garbage collection and child-to-parent event routing; finalizers are only for cleanup outside the cluster.
* A CRD is a schema plus subresources; kubebuilder generates the CRD YAML, RBAC and DeepCopy code from markers in Go comments.
* envtest tests against a real API server with no controllers; kind tests the whole thing; both belong in CI.
* Webhooks need a valid TLS certificate and fail closed by default, so a down webhook can lock a cluster.

## Common mistakes

* Reacting to the event payload ("old replicas was 2") instead of reading the current state; the controller then misses changes that happened while it was down.
* Calling the API server directly for reads inside Reconcile, which turns a cheap cache lookup into thousands of requests on a busy cluster.
* Updating status with a normal Update instead of the status subresource, which can overwrite a user's spec change with a stale copy.
* Forgetting SetControllerReference on children, so deleting the custom resource leaves orphaned Deployments and the controller never hears about child changes.
* Returning nil after a failed write "to avoid noise", which silently drops the work; return the error and let backoff handle the noise.
* Shipping a validating webhook with failurePolicy Fail and no cert-manager, then being unable to create any pod, including the webhook's own, after the certificate expires.

## Practice

* Install kubebuilder, scaffold the WebApp API from this lesson, add the markers, run `make manifests` and confirm the generated CRD under `config/crd/bases/` has the printer columns and the status subresource. Measure: `kubectl get webapps` shows Replicas and Ready columns in a kind cluster.
* Implement the reconciler, run it with `make run`, create a WebApp with replicas 2, then scale it with `kubectl scale webapp shop --replicas=3` and watch `kubectl get deploy -w`. Measure: the Deployment follows within 2 seconds and status.readyReplicas reaches 3.
* Write an envtest test that creates a WebApp and asserts the Deployment exists with the right image and replicas; then set the Deployment's status.readyReplicas by hand and assert the WebApp's Ready condition becomes True. Measure: `make test` passes in under 60 seconds.
* Clone kubernetes/kubernetes, run `go test ./pkg/controller/deployment -run ^TestSyncDeploymentCreatesReplicaSet$ -v`, then read syncDeployment and write down, in five lines, the order of checks it makes before scaling anything.

## Interview questions (10)

1.What is the difference between a kind and a resource, and why does kubectl need discovery?Easy

A kind is the type name inside an object, like Deployment, and a resource is the plural, lower-case name in the URL path, like deployments. They usually map one to one, but the mapping is not fixed by rule, and custom types add new ones at runtime. kubectl asks the discovery endpoints under /apis which groups, versions and resources this cluster serves, and uses that to turn "kubectl get deploy" into GET /apis/apps/v1/namespaces/x/deployments. That is also how kubectl knows short names and whether a resource is namespaced.

2.Two controllers update the same object at the same time. What happens?Medium

Each update carries the resourceVersion the client last read. The first write succeeds and bumps the resourceVersion. The second arrives with the old value, so the API server rejects it with 409 Conflict and nothing is lost. The losing client must read the object again, apply its change on top of the fresh copy and retry; client-go's retry.RetryOnConflict does that loop, and in controller-runtime you simply return the error so the work queue requeues the key with backoff. The important point is that there are no locks: correctness comes from the version check plus a retry.

3.Explain level-based versus edge-based, and why Kubernetes chose level-based.Medium

Edge-based means acting on the transition: "replicas changed from 2 to 3, so add one pod". Level-based means acting on the state: "the spec says 3 and I see 2, so add one". Kubernetes controllers are level-based because events can be missed, duplicated or delivered late: a controller may be down, a watch may drop and relist, an informer may resync. With level-based logic none of that matters, because every reconcile recomputes the full difference from current state. The cost is that reconcile must be idempotent and cheap, which is why reads come from a cache.

4.What do informers and listers give you that polling or a plain watch does not?Medium

A plain watch gives a stream of events but no state; polling gives state but hammers the API server. An informer does one list, then watches, and keeps a local cache that is updated by the stream, so the controller has the full current state in memory and every Get or List in Reconcile is a map lookup. It handles reconnects and 410 Gone by relisting, periodically resyncs so nothing is lost, and runs event handlers that enqueue keys. A lister is the typed read interface to that cache. With a shared informer factory, ten controllers in one process share one watch per resource.

5.When do you need a finalizer and when are owner references enough?Medium

Owner references are enough when every child lives in the cluster. The garbage collector deletes the Deployment and Service when the WebApp is deleted, with no code. A finalizer is needed when deleting the object must trigger work that the garbage collector cannot do: removing an S3 bucket, a DNS record, a row in an external database, or deregistering from a load balancer. The controller adds the finalizer before creating the external thing, and on seeing deletionTimestamp it cleans up and then removes the finalizer. A finalizer that is never removed leaves the object stuck in Terminating, which is a common on-call page.

6.You deployed a validating webhook and now no pods can be created anywhere. What happened and how do you recover?Hard

The webhook is matching every pod create, its failurePolicy is Fail, and the API server cannot reach it, usually because the webhook pod is down, the certificate does not match the caBundle, or the call exceeds timeoutSeconds. Because pods include the webhook's own pod, the cluster cannot heal itself. Recovery is to edit or delete the ValidatingWebhookConfiguration, or set failurePolicy to Ignore, which does not go through the webhook. Prevention is to scope the webhook with namespaceSelector so kube-system and the webhook's namespace are excluded, keep timeoutSeconds short, use cert-manager for the certificate, and only use Fail for true security controls.

7.What does the status subresource change, and why does kubebuilder enable it?Easy

With the status subresource enabled, a normal update to the object ignores the status field, and a PUT to /status ignores everything except status. That means a user editing spec cannot accidentally wipe the status the controller wrote, and the controller writing status cannot overwrite a spec change it has not seen yet. It also lets RBAC separate who may change spec from who may change status. kubebuilder's marker +kubebuilder:subresource:status enables it, and controller-runtime's r.Status().Update targets that endpoint.

8.Walk me through what envtest runs and what it does not.Medium

envtest downloads and starts real kube-apiserver and etcd binaries on the test machine, pointed to by KUBEBUILDER\_ASSETS, installs your CRDs, and gives your test a rest config. You then start your manager against it and create objects with the client. It does not run kubelet, the scheduler, or any built-in controller, so pods never run, Deployments never get ready replicas, and owner-based garbage collection never happens. Tests therefore assert that the controller created the right objects with the right fields, and set child status by hand to test the status path. For the full behaviour you run the operator in a kind cluster.

9.How would you find the code that decides when a Deployment is marked Progressing or Complete?Medium

I would clone kubernetes/kubernetes and go to pkg/controller/deployment, because controllers for built-in types live under pkg/controller by resource name. deployment\_controller.go holds the queue and the syncDeployment function, which is the reconcile; the rollout logic is in sync.go and rolling.go, and the condition logic lives in the util package next to them. I would grep for the condition reason strings, read the test file next to the code to see the cases the authors cared about, and run one test with go test ./pkg/controller/deployment -run TestName -v to confirm I understood it.

10.Why does a controller return an error instead of sleeping and retrying inside Reconcile?Easy

Because the work queue already implements retry correctly and globally. Returning the error puts the key back with per-item exponential backoff and an overall rate limit, while the worker goroutine is free to handle other keys. Sleeping inside Reconcile would block a worker, hide the retry from metrics, and let the same key be worked on twice when a new event arrives. If you need a timed re-check rather than a retry, return Result with RequeueAfter set and no error.

## Quiz

1.Which metadata field changes only when the spec changes?

2.A reconcile returns a non-nil error. What does controller-runtime do?

3.Which builder call makes Deployment events enqueue the owning WebApp?

4.What does envtest run?

5.Your webhook pod is down and failurePolicy is Fail. What happens to matching requests?

## Practice these problems

* [DESIGNProduction EKS cluster for a 30-engineer startupHard](/devops/problems/eks-cluster-platform)
* [CODEKubernetes manifests: Deployment, Service, Ingress and HPA with probes and limitsMedium](/devops/problems/kubernetes-manifests-web-app)
* [CODEHelm chart from scratch with values, templates and a testMedium](/devops/problems/helm-chart-from-scratch)
* [CODEGo: a Kubernetes-style reconcile loop for a custom resourceHard](/devops/problems/go-reconcile-loop)

## Further reading

* [The Kubebuilder BookGuidebook.kubebuilder.io](https://book.kubebuilder.io/)
* [Operator patternGuidekubernetes.io](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
* [kubernetes/client-go: Go client for KubernetesCodegithub.com](https://github.com/kubernetes/client-go)
* [Borg, Omega, and KubernetesPaperresearch.google](https://research.google/pubs/pub44843/)
* [kubernetes/kubernetesCodegithub.com](https://github.com/kubernetes/kubernetes)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousScaling and resilience - caching, queues, rate limiting, DDoS, DR](/devops/learn/scaling-and-resilience)[NextOpen source - contributing to CNCF projects, LFX and GSoC](/devops/learn/open-source-cncf-lfx-gsoc)

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

1. [The API server: groups, versions, kinds and resources](#the-api-server-groups-versions-kinds-and-resources)
2. [An object on the wire](#an-object-on-the-wire)
3. [Optimistic concurrency, watches and admission](#optimistic-concurrency-watches-and-admission)
4. [The controller pattern, precisely](#the-controller-pattern-precisely)
5. [CustomResourceDefinitions](#customresourcedefinitions)
6. [client-go: clientset, informers and listers](#client-go-clientset-informers-and-listers)
7. [controller-runtime and kubebuilder](#controller-runtime-and-kubebuilder)
8. [The WebApp operator, end to end](#the-webapp-operator-end-to-end)
9. [Testing, packaging and admission webhooks](#testing-packaging-and-admission-webhooks)
10. [Where the design came from, and how to read the source](#where-the-design-came-from-and-how-to-read-the-source)
