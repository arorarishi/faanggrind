# Go: a Kubernetes-style reconcile loop for a custom resource — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/go-reconcile-loop

[DevOps problems](/devops#problems)

CODEImplement it#41Hard

# Go: a Kubernetes-style reconcile loop for a custom resource

gokubernetesoperatorscontrollersconcurrencyclient-go

## Problem statement

Implement, in a single Go file with no external dependencies, a Kubernetes-style controller for a custom resource `WebApp{Name, Replicas, Image}` that owns a `Deployment{Name, Replicas, Image, ReadyReplicas, Owner}`. Build the pieces a real controller has: an in-memory API store with optimistic concurrency and watch, an informer-like cache, a work queue with deduplication and rate-limited requeue, a reconcile function, a finalizer, retry on Conflict, and graceful shutdown. The `main` function must run a scripted scenario, print an event log, and assert each stage, including proof that no goroutine leaks after shutdown.

## Requirements

### Functional

* `Store[T]` with `Create`, `Get`, `Update`, `Delete` and `Watch`. Every object has a `ResourceVersion`; an `Update` whose version is not the stored one returns `ErrConflict` and changes nothing.
* `Watch` returns a channel of `Added`, `Modified`, `Deleted` events; an informer goroutine consumes it to keep a `Cache` current and to enqueue keys.
* `Queue` deduplicates keys, never hands the same key to two workers at once, and `AddRateLimited` requeues with exponential backoff per key, capped at a maximum, with `Forget` on success.
* `Reconcile(ctx, key)`: read the WebApp from the cache; if it is being deleted, delete the owned Deployment and remove the finalizer; otherwise add the finalizer, create or update the Deployment to match the spec, copy `ReadyReplicas` into the WebApp status, and return a requeue instruction while the rollout is incomplete.
* A kubelet goroutine marks one more replica ready every 30 ms so status changes over time.
* The scenario: create with 2 replicas, scale to 3, inject one concurrent write that causes a Conflict and a retry, inject a transient error that triggers backoff, delete and prove the Deployment is gone and the finalizer cleared; cancel the context, wait on a `WaitGroup`, and print goroutine counts before and after.

### Non-functional

* Standard library only, `gofmt` clean, `go vet` clean, and no data race under `go run -race`.
* The whole scenario finishes in under 2 s; every wait has a 5 s timeout so a bug fails the run instead of hanging it.
* Every write that can conflict (status, finalizer, Deployment spec) is wrapped in `RetryOnConflict` with at most 5 attempts, and each attempt re-reads the object.
* Backoff starts at 5 ms and doubles per failure to a cap of 1 s, the same shape as client-go's default item rate limiter (5 ms to 1000 s).
* Goroutine count after `cancel()` and `wg.Wait()` equals the count before start; watch channels are buffered (1024) and the store counts dropped events, which must be 0.

## API

```
// Build and run: go vet . && go run -race .   (prints "all checks passed", exit 1 on any failed check)

// API server stand-in, generic over the object type
func NewStore[T Object[T]](kind string) *Store[T]
func (s *Store[T]) Create(obj T) (T, error)          // ErrAlreadyExists
func (s *Store[T]) Get(name string) (T, error)       // ErrNotFound; returns a deep copy
func (s *Store[T]) Update(obj T) (T, error)          // ErrConflict when obj.ResourceVersion is stale
func (s *Store[T]) Delete(name string) error         // sets DeletionTimestamp if finalizers exist, else removes
func (s *Store[T]) Watch() (<-chan Event[T], func()) // replays current objects as ADDED, then streams; stop func
func RetryOnConflict(attempts int, fn func() error) error

// Informer and cache
func RunInformer[T Object[T]](ctx context.Context, store *Store[T], cache *Cache[T], handle func(T))
func (c *Cache[T]) Get(name string) (T, bool)

// Work queue (client-go workqueue shape)
func NewQueue(base, max time.Duration) *Queue
func (q *Queue) Add(key string)
func (q *Queue) AddAfter(key string, d time.Duration)
func (q *Queue) AddRateLimited(key string) time.Duration // returns the delay used
func (q *Queue) Forget(key string)
func (q *Queue) Get() (key string, shutdown bool)        // blocks
func (q *Queue) Done(key string)
func (q *Queue) ShutDown()

// Controller
func (r *Reconciler) Reconcile(ctx context.Context, key string) (Result, error)
func (c *Controller) Run(ctx context.Context, wg *sync.WaitGroup)
```

## Data model

```
type Meta struct {
    Name              string
    ResourceVersion   int64             // bumped on every successful write
    Finalizers        []string          // while non-empty, Delete only sets DeletionTimestamp
    DeletionTimestamp *time.Time
    Annotations       map[string]string // what the "other client" writes to force a Conflict
}

type WebApp struct {                  // the custom resource
    Meta
    Replicas, ReadyReplicas int       // Replicas is spec, ReadyReplicas is status
    Image                   string
}

type Deployment struct {              // the owned child
    Meta
    Owner                   string    // plays the role of an ownerReference
    Replicas, ReadyReplicas int       // ReadyReplicas is written by the kubelet goroutine
    Image                   string
}

type Event[T any] struct { Type EventType; Object T }   // ADDED, MODIFIED, DELETED
type Result struct { RequeueAfter time.Duration }       // zero means done

Queue state: order []string (FIFO), dirty map (waiting keys), processing map (keys a
worker holds), failures map (per-key failure count for backoff), timers for AddAfter.
```

## Approach

1. Define `Meta`, `WebApp` and `Deployment` with `DeepCopy` methods. The store always stores and returns copies, so a caller can never change the stored object without going through `Update`.
2. Implement `Store[T]` with one mutex. `commit` bumps `ResourceVersion`, stores the copy and sends the event to every watcher with a non-blocking send; a full watcher channel counts as a dropped event, which a real informer would recover from by relisting. `Update` compares versions first and returns `ErrConflict` on mismatch. `Delete` only sets `DeletionTimestamp` when finalizers exist; `Update` removes the object once the last finalizer is cleared.
3. `Watch` replays the current objects as `ADDED` (the list part of list-then-watch), then registers the channel. `RunInformer` reads it, updates the cache under a lock, and calls a handler that puts a key on the queue: WebApp events enqueue their own name, Deployment events enqueue their `Owner`.
4. The queue uses a `sync.Cond`. `Add` ignores a key that is already waiting; if a worker is processing it, the key is marked dirty and re-added on `Done`, so an event that arrives during a reconcile is never lost. `AddRateLimited` computes `base << (failures-1)` capped at `max` and schedules `Add` with `time.AfterFunc`; `Forget` resets the count.
5. `Reconcile` is level-based: it compares the WebApp in the cache with the Deployment in the cache and fixes the difference. Order: deletion path, finalizer, injected fault, create or update child, copy status, requeue after 200 ms while `ReadyReplicas != Replicas`. Every write goes through `RetryOnConflict` with a closure that re-reads the latest object.
6. `Controller.Run` starts two informers, two workers and a goroutine that calls `queue.ShutDown()` when the context ends, all registered on the caller's `WaitGroup`. A worker loop is `Get`, `Reconcile`, then `AddRateLimited`, `AddAfter` or `Forget`, then `Done`.
7. The kubelet goroutine ticks every 30 ms and increments `ReadyReplicas` on every Deployment that is behind, through `RetryOnConflict`, because the controller may be writing the same object.
8. `main` runs the five stages, uses a `waitFor` helper with a 5 s deadline, injects the concurrent write through a `BeforeWrite` hook on the WebApp store (the way a fake client reactor does in client-go tests), prints the event log and the goroutine counts, and exits 1 if any check failed.

## Architecture diagram

Rendering diagram…

## Deep dives

### Level-based reconciliation and idempotency

The reconcile function never looks at the event. It receives a key, reads the WebApp and the Deployment from the cache, and fixes the difference. That is why the scenario works when the finalizer write, the scale to 3 and the image change all land on the queue as the same key: the queue collapses them and one pass sees the final spec. It is also why a Deployment event enqueues the owner, not the child: the parent reconcile recomputes everything. Idempotency follows from the structure: create only when the cache has no child, update only when a field differs, write status only when the value changed. Run `Reconcile` twice in a row and the second run performs zero writes. The one subtle case is `ErrAlreadyExists` on create: the controller created the Deployment a moment ago and the Deployment informer has not delivered the event yet. The code treats it as "read the truth and continue", which is exactly what controller-runtime's `Create` followed by `Get` does.

### Optimistic concurrency, and why controllers re-read instead of retrying blindly

The API server has no locks. `Update` carries the `ResourceVersion` the client read; if the stored version moved on, the server answers 409 Conflict. The scenario forces this with `BeforeWrite`: just before the controller writes status, another client writes an annotation, so the controller's version is stale. Retrying the same `Update` with the same object would fail forever, and worse, retrying with `latest.ResourceVersion = stored` would silently overwrite the annotation. The correct loop is the one in `RetryOnConflict`: re-read, apply your change to the fresh copy, write. client-go's `retry.RetryOnConflict(retry.DefaultRetry, fn)` is this with 5 tries and 10 ms steps. Note the two writers on `Deployment` in this program: the controller (spec) and the kubelet (status); in a real cluster the status subresource exists so that these two never conflict on the same fields.

### The work queue and rate limiting

`workqueue` in client-go has three guarantees that this `Queue` reproduces: a key is in the queue at most once (`dirty`), a key is processed by at most one worker at a time (`processing`), and a key added while it is being processed is re-added when `Done` is called, so no update is lost. `AddRateLimited` uses a per-item exponential backoff; the real `DefaultTypedControllerRateLimiter` combines that (5 ms doubling to 1000 s) with a token bucket of 10 per second with burst 100 for the whole queue. The scenario asserts the first delay is 5 ms and that `NumRequeues` is 0 after success, which is what `Forget` is for: a key that failed once a week ago must not start its next failure at the top of the curve. `AddAfter` is the other path, used for "look again in 200 ms" when the rollout is not done; it is not a failure, so it does not count.

### Finalizers and ownership

A delete of an object with finalizers only sets `deletionTimestamp`. The object stays visible, the informer delivers a `MODIFIED` event, and the reconciler sees the deletion path: delete the Deployment, then remove its finalizer entry with a re-read. When the last finalizer goes, the store removes the object and emits `DELETED`. The ordering matters: cleanup first, finalizer removal second, so a crash between the two leaves the finalizer in place and the next reconcile repeats the cleanup. In a real cluster the Deployment would carry an `ownerReference` and the garbage collector would delete it without a finalizer; you add a finalizer when the cleanup is outside the cluster (a DNS record, an S3 bucket) or must happen in a specific order.

### How this maps to client-go, controller-runtime and kubebuilder

`Store` is the API server plus etcd. `Watch` is the HTTP watch stream. `RunInformer` plus `Cache` is a `SharedIndexInformer` with its `Indexer`; `Cache.Get` is the `Lister`. `Queue` is `workqueue.TypedRateLimitingInterface[reconcile.Request]`. `Reconciler.Reconcile(ctx, key)` is `reconcile.Reconciler` with `ctrl.Result{RequeueAfter}`. `Controller.Run` is what `ctrl.NewControllerManagedBy(mgr).For(&WebApp{}).Owns(&appsv1.Deployment{}).Complete(r)` builds: the `For` informer enqueues the object's key, the `Owns` informer maps a child event to its owner through the ownerReference. The `Manager` adds leader election, metrics and a shared cache. kubebuilder generates the types, the CRD YAML and this wiring; what you write by hand is the body of `Reconcile`, which is why the interviewer wants to see it written here without the framework.

## Evaluation

**Correctness tests.** The scenario itself is the test suite: 17 checks printed as `check ok` or `CHECK FAILED`, exit 1 on any failure. Run it under `go run -race .` and 15 times in a loop; a controller that passes once and hangs on the second run has a lost-wakeup bug in the queue. Unit tests a strong candidate would add: `Update` with a stale version returns `ErrConflict` and leaves the object unchanged; `Queue.Add` of a processing key re-adds it on `Done`; `RetryOnConflict` stops after 5 attempts; `Reconcile` called twice performs no second write.

**Edge cases.** Delete of a WebApp with no Deployment (cleanup must tolerate `ErrNotFound`); a WebApp event arriving after the object is gone (the cache miss path deletes any orphan); `ErrAlreadyExists` on create when the child informer lags; shutdown while a timer from `AddAfter` is pending (`ShutDown` stops timers and `Add` is a no-op after shutdown).

**Complexity.** `Store` operations are O(1) with a lock; `Watch` replay is O(n). The queue's `Add`, `Get` and `Done` are O(1) amortised. Memory is one copy per object per cache plus the channel buffers.

**What a strong answer adds.** Deep copies everywhere, so a cache read can never corrupt the store; a non-blocking send to watchers with a dropped-event counter and the words "a real informer relists after 410 Gone"; the `dirty` set that saves an event delivered during a reconcile; `Forget` on success; the two-goroutine-counts proof; and a clear statement of what the code leaves out: leader election, status conditions with `observedGeneration`, the status subresource, and resync.

## Bottlenecks & mitigations

* One mutex per store; every read and write serialises. The real API server scales by sharding on resource type and relying on etcd, and informers exist so that reads never hit it.
* Watch channel buffer of 1024 per watcher; a slow informer drops events. The real fix is relist on `410 Gone`, not a bigger buffer.
* Two workers; a reconcile that blocks on a slow write stalls half the capacity. controller-runtime's `MaxConcurrentReconciles` is the same knob.
* The kubelet ticker lists every Deployment every 30 ms under the store lock; at thousands of objects this would starve the controller.

## Failure modes

* **Retrying an Update without re-reading.** The same stale version fails forever, or a forced version overwrites another client's change. Mitigation: `RetryOnConflict` with a closure that does `Get` then mutate then `Update`.
* **Lost event during reconcile.** An update arrives while a worker holds the key and a naive queue drops it. Mitigation: the `dirty` set and re-add on `Done`.
* **Finalizer removed before cleanup.** A crash between the two leaves an orphan Deployment. Mitigation: delete the child first; remove the finalizer only after `Delete` returned nil or `ErrNotFound`.
* **Goroutine leak at shutdown.** A worker blocked in `Get` never sees the cancelled context. Mitigation: a goroutine that calls `queue.ShutDown()` on `ctx.Done()`, and `cond.Broadcast()` inside it; the before and after goroutine counts prove it.
* **Backoff never reset.** A key that failed last week starts its next failure at 1 s. Mitigation: `Forget` on every successful reconcile.
* **Hot loop on a permanent error.** An invalid spec fails every time and burns a worker. Mitigation: exponential backoff caps the rate; in a real controller write a `Ready=False` condition and stop requeueing for errors the user must fix.
* **Cache lag after your own write.** Create succeeds, the cache still says "no child", the next pass tries to create again. Mitigation: treat `ErrAlreadyExists` as "read it and continue".

## Reference solution

Go · gofmt and go vet clean · runs and prints its own checks

```
package main

// reconcile.go: a Kubernetes-style controller in one file, standard library only.
// Pieces, in the order an interviewer reads them: API objects, an in-memory API
// server (Store) with optimistic concurrency and watch, an informer-like Cache,
// a rate-limited work queue, the Reconciler, the Controller that wires them,
// a fake kubelet, and a scripted scenario in main that asserts every stage.

import (
	"context"
	"errors"
	"fmt"
	"maps"
	"os"
	"runtime"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// ---------- API objects (what metav1.ObjectMeta and the CRD types give you) ----------

const finalizerName = "webapp.example.com/cleanup"

// Meta is the part of every object the API server owns: name, version, finalizers, deletion.
type Meta struct {
	Name              string
	ResourceVersion   int64 // bumped on every write; an Update must carry the version it read
	Finalizers        []string
	DeletionTimestamp *time.Time // set by Delete while finalizers remain; the object is gone only when they are cleared
	Annotations       map[string]string
}

func (m *Meta) GetMeta() *Meta { return m }

// Object is what the generic Store needs: metadata access and a deep copy of the concrete type.
type Object[T any] interface {
	GetMeta() *Meta
	DeepCopy() T
}

// WebApp is the custom resource. Replicas and Image are spec; ReadyReplicas is status.
type WebApp struct {
	Meta
	Replicas      int
	Image         string
	ReadyReplicas int
}

// Deployment is the owned child. Owner plays the role of an ownerReference.
type Deployment struct {
	Meta
	Owner         string
	Replicas      int
	Image         string
	ReadyReplicas int // written by the kubelet goroutine, read by the controller
}

func copyMeta(m Meta) Meta {
	m.Finalizers = append([]string(nil), m.Finalizers...)
	m.Annotations = maps.Clone(m.Annotations)
	if m.DeletionTimestamp != nil {
		t := *m.DeletionTimestamp
		m.DeletionTimestamp = &t
	}
	return m
}

func (w *WebApp) DeepCopy() *WebApp {
	c := *w
	c.Meta = copyMeta(w.Meta)
	return &c
}

func (d *Deployment) DeepCopy() *Deployment {
	c := *d
	c.Meta = copyMeta(d.Meta)
	return &c
}

var (
	ErrNotFound      = errors.New("not found")
	ErrAlreadyExists = errors.New("already exists")
	ErrConflict      = errors.New("conflict: object was modified; re-read and apply your change again")
)

// ---------- Store: the API server for one resource, with optimistic concurrency and watch ----------

type EventType string

const (
	Added    EventType = "ADDED"
	Modified EventType = "MODIFIED"
	Deleted  EventType = "DELETED"
)

type Event[T any] struct {
	Type   EventType
	Object T
}

type Store[T Object[T]] struct {
	kind        string
	mu          sync.Mutex
	items       map[string]T
	nextRV      int64
	watchers    map[int]chan Event[T]
	nextWatcher int
	Conflicts   int    // how many Updates were rejected with ErrConflict (read through Stats)
	Dropped     int    // events a slow watcher missed (a real informer would relist)
	BeforeWrite func() // test hook: runs once, before the next Update, like a fake client reactor
}

// SetBeforeWrite installs the one-shot hook under the lock; Update takes and clears it.
func (s *Store[T]) SetBeforeWrite(fn func()) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.BeforeWrite = fn
}

func NewStore[T Object[T]](kind string) *Store[T] {
	return &Store[T]{kind: kind, items: map[string]T{}, watchers: map[int]chan Event[T]{}}
}

// commit stores a copy with a fresh ResourceVersion and tells every watcher. Caller holds mu.
func (s *Store[T]) commit(obj T, typ EventType) T {
	s.nextRV++
	obj.GetMeta().ResourceVersion = s.nextRV
	s.items[obj.GetMeta().Name] = obj
	s.emit(Event[T]{Type: typ, Object: obj.DeepCopy()})
	return obj.DeepCopy()
}

func (s *Store[T]) emit(ev Event[T]) {
	for _, ch := range s.watchers {
		select {
		case ch <- ev:
		default:
			s.Dropped++
		}
	}
}

func (s *Store[T]) Create(obj T) (T, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var zero T
	if _, ok := s.items[obj.GetMeta().Name]; ok {
		return zero, fmt.Errorf("%s %q: %w", s.kind, obj.GetMeta().Name, ErrAlreadyExists)
	}
	return s.commit(obj.DeepCopy(), Added), nil
}

func (s *Store[T]) Get(name string) (T, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	cur, ok := s.items[name]
	if !ok {
		var zero T
		return zero, fmt.Errorf("%s %q: %w", s.kind, name, ErrNotFound)
	}
	return cur.DeepCopy(), nil
}

// Update is optimistic concurrency: the ResourceVersion on obj must equal the stored one.
// If finalizers are now empty on an object marked for deletion, the object is removed.
func (s *Store[T]) Update(obj T) (T, error) {
	s.mu.Lock()
	hook := s.BeforeWrite
	s.BeforeWrite = nil
	s.mu.Unlock()
	if hook != nil {
		hook() // simulates another client writing between our read and our write
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	var zero T
	name := obj.GetMeta().Name
	cur, ok := s.items[name]
	if !ok {
		return zero, fmt.Errorf("%s %q: %w", s.kind, name, ErrNotFound)
	}
	if cur.GetMeta().ResourceVersion != obj.GetMeta().ResourceVersion {
		s.Conflicts++
		return zero, fmt.Errorf("%s %q (sent rv=%d, stored rv=%d): %w", s.kind, name,
			obj.GetMeta().ResourceVersion, cur.GetMeta().ResourceVersion, ErrConflict)
	}
	c := obj.DeepCopy()
	if c.GetMeta().DeletionTimestamp != nil && len(c.GetMeta().Finalizers) == 0 {
		delete(s.items, name)
		s.emit(Event[T]{Type: Deleted, Object: c})
		return c, nil
	}
	return s.commit(c, Modified), nil
}

// Delete removes the object, or only marks it when finalizers are present (the API server rule).
func (s *Store[T]) Delete(name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	cur, ok := s.items[name]
	if !ok {
		return fmt.Errorf("%s %q: %w", s.kind, name, ErrNotFound)
	}
	m := cur.GetMeta()
	if len(m.Finalizers) > 0 && m.DeletionTimestamp == nil {
		c := cur.DeepCopy()
		now := time.Now()
		c.GetMeta().DeletionTimestamp = &now
		s.commit(c, Modified)
		return nil
	}
	delete(s.items, name)
	s.emit(Event[T]{Type: Deleted, Object: cur.DeepCopy()})
	return nil
}

// Watch returns a channel that first replays every current object as ADDED (the "list"),
// then streams later changes. stop unregisters the watcher and closes the channel.
func (s *Store[T]) Watch() (<-chan Event[T], func()) {
	s.mu.Lock()
	defer s.mu.Unlock()
	ch := make(chan Event[T], 1024)
	names := make([]string, 0, len(s.items))
	for n := range s.items {
		names = append(names, n)
	}
	sort.Strings(names)
	for _, n := range names {
		ch <- Event[T]{Type: Added, Object: s.items[n].DeepCopy()}
	}
	id := s.nextWatcher
	s.nextWatcher++
	s.watchers[id] = ch
	stop := func() {
		s.mu.Lock()
		defer s.mu.Unlock()
		if _, ok := s.watchers[id]; ok {
			delete(s.watchers, id)
			close(ch)
		}
	}
	return ch, stop
}

// Stats returns the conflict and dropped-event counters under the lock, so a test can read
// them while informers and the kubelet are still writing.
func (s *Store[T]) Stats() (conflicts, dropped int) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.Conflicts, s.Dropped
}

// RetryOnConflict re-runs fn while it fails with ErrConflict. fn must re-read the object
// itself, so each attempt applies the change to the latest version (client-go retry.RetryOnConflict).
func RetryOnConflict(attempts int, fn func() error) error {
	var err error
	for i := 0; i < attempts; i++ {
		if err = fn(); !errors.Is(err, ErrConflict) {
			return err
		}
	}
	return err
}

// ---------- Cache: the informer's local copy (Lister) ----------

type Cache[T Object[T]] struct {
	mu    sync.RWMutex
	items map[string]T
}

func NewCache[T Object[T]]() *Cache[T] { return &Cache[T]{items: map[string]T{}} }

func (c *Cache[T]) Get(name string) (T, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	obj, ok := c.items[name]
	return obj, ok
}

// RunInformer keeps cache current from a watch and calls handle for every event until ctx ends.
func RunInformer[T Object[T]](ctx context.Context, store *Store[T], cache *Cache[T], handle func(T)) {
	ch, stop := store.Watch()
	defer stop()
	for {
		select {
		case <-ctx.Done():
			return
		case ev, ok := <-ch:
			if !ok {
				return
			}
			cache.mu.Lock()
			if ev.Type == Deleted {
				delete(cache.items, ev.Object.GetMeta().Name)
			} else {
				cache.items[ev.Object.GetMeta().Name] = ev.Object
			}
			cache.mu.Unlock()
			handle(ev.Object)
		}
	}
}

// ---------- Work queue: dedup, one worker per key, exponential backoff (client-go workqueue) ----------

type Queue struct {
	mu         sync.Mutex
	cond       *sync.Cond
	order      []string
	dirty      map[string]bool // keys waiting; Add of a waiting key is a no-op
	processing map[string]bool // keys a worker holds; Add while processing re-adds on Done
	failures   map[string]int
	timers     []*time.Timer
	down       bool
	base, max  time.Duration
	Backoffs   []time.Duration // every delay handed out, for the scenario to check
}

func NewQueue(base, max time.Duration) *Queue {
	q := &Queue{dirty: map[string]bool{}, processing: map[string]bool{}, failures: map[string]int{}, base: base, max: max}
	q.cond = sync.NewCond(&q.mu)
	return q
}

func (q *Queue) Add(key string) {
	q.mu.Lock()
	defer q.mu.Unlock()
	if q.down || q.dirty[key] {
		return
	}
	q.dirty[key] = true
	if q.processing[key] {
		return
	}
	q.order = append(q.order, key)
	q.cond.Signal()
}

func (q *Queue) AddAfter(key string, d time.Duration) {
	q.mu.Lock()
	defer q.mu.Unlock()
	if q.down {
		return
	}
	q.timers = append(q.timers, time.AfterFunc(d, func() { q.Add(key) }))
}

// AddRateLimited requeues with delay base * 2^(failures-1), capped at max.
func (q *Queue) AddRateLimited(key string) time.Duration {
	q.mu.Lock()
	q.failures[key]++
	d := q.base << (q.failures[key] - 1)
	if d > q.max || d <= 0 {
		d = q.max
	}
	q.Backoffs = append(q.Backoffs, d)
	q.mu.Unlock()
	q.AddAfter(key, d)
	return d
}

func (q *Queue) Forget(key string) {
	q.mu.Lock()
	defer q.mu.Unlock()
	delete(q.failures, key)
}

func (q *Queue) NumRequeues(key string) int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return q.failures[key]
}

// Get blocks until a key is available or the queue is shut down.
func (q *Queue) Get() (string, bool) {
	q.mu.Lock()
	defer q.mu.Unlock()
	for len(q.order) == 0 && !q.down {
		q.cond.Wait()
	}
	if len(q.order) == 0 {
		return "", true
	}
	key := q.order[0]
	q.order = q.order[1:]
	delete(q.dirty, key)
	q.processing[key] = true
	return key, false
}

func (q *Queue) Done(key string) {
	q.mu.Lock()
	defer q.mu.Unlock()
	delete(q.processing, key)
	if q.dirty[key] {
		q.order = append(q.order, key)
		q.cond.Signal()
	}
}

func (q *Queue) ShutDown() {
	q.mu.Lock()
	defer q.mu.Unlock()
	q.down = true
	for _, t := range q.timers {
		t.Stop()
	}
	q.cond.Broadcast()
}

// ---------- Event log and fault injection ----------

type Log struct {
	mu      sync.Mutex
	start   time.Time
	entries []string
}

func (l *Log) Printf(format string, a ...any) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.entries = append(l.entries, fmt.Sprintf("%6dms  ", time.Since(l.start).Milliseconds())+fmt.Sprintf(format, a...))
}

func (l *Log) Contains(sub string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	for _, e := range l.entries {
		if strings.Contains(e, sub) {
			return true
		}
	}
	return false
}

// Faults holds one-shot errors the scenario injects into Reconcile, keyed by object name.
type Faults struct {
	mu   sync.Mutex
	once map[string]error
}

func (f *Faults) Set(key string, err error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.once[key] = err
}

func (f *Faults) Take(key string) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	err := f.once[key]
	delete(f.once, key)
	return err
}

// ---------- Reconciler: level-based, idempotent, reads from caches, writes with re-read ----------

type Result struct {
	RequeueAfter time.Duration
}

type Reconciler struct {
	apps     *Store[*WebApp]
	deps     *Store[*Deployment]
	appCache *Cache[*WebApp]
	depCache *Cache[*Deployment]
	faults   *Faults
	log      *Log
}

func (r *Reconciler) Reconcile(ctx context.Context, key string) (Result, error) {
	app, ok := r.appCache.Get(key)
	if !ok {
		// Object is gone. Idempotent cleanup in case the finalizer path was skipped.
		if err := r.deps.Delete(key); err == nil {
			r.log.Printf("reconcile %s: webapp gone, deleted orphan deployment", key)
		}
		return Result{}, nil
	}

	if app.DeletionTimestamp != nil {
		switch err := r.deps.Delete(key); {
		case err == nil:
			r.log.Printf("reconcile %s: deleting, owned deployment removed", key)
		case !errors.Is(err, ErrNotFound):
			return Result{}, err
		}
		err := RetryOnConflict(5, func() error {
			latest, err := r.apps.Get(key)
			if err != nil {
				return err
			}
			latest.Finalizers = remove(latest.Finalizers, finalizerName)
			_, err = r.apps.Update(latest)
			return err
		})
		if errors.Is(err, ErrNotFound) {
			r.log.Printf("reconcile %s: already gone; nothing to do (idempotent)", key)
			return Result{}, nil
		}
		if err != nil {
			return Result{}, err
		}
		r.log.Printf("reconcile %s: finalizer removed, object can go", key)
		return Result{}, nil
	}

	if !contains(app.Finalizers, finalizerName) {
		err := RetryOnConflict(5, func() error {
			latest, err := r.apps.Get(key)
			if err != nil {
				return err
			}
			latest.Finalizers = append(latest.Finalizers, finalizerName)
			_, err = r.apps.Update(latest)
			return err
		})
		if err != nil {
			return Result{}, err
		}
		r.log.Printf("reconcile %s: finalizer added", key)
		return Result{}, nil // the Update triggers a new event; next pass continues with fresh data
	}

	if err := r.faults.Take(key); err != nil {
		return Result{}, err
	}

	// Child: create if missing, update if different. Compare desired with observed, never with the event.
	dep, ok := r.depCache.Get(key)
	if !ok {
		created, err := r.deps.Create(&Deployment{Meta: Meta{Name: key}, Owner: key, Replicas: app.Replicas, Image: app.Image})
		if errors.Is(err, ErrAlreadyExists) {
			// Cache lagged behind our own earlier write; read the truth and continue.
			if created, err = r.deps.Get(key); err != nil {
				return Result{}, err
			}
		} else if err != nil {
			return Result{}, err
		} else {
			r.log.Printf("reconcile %s: created deployment replicas=%d image=%s", key, created.Replicas, created.Image)
		}
		dep = created
	}
	if dep.Replicas != app.Replicas || dep.Image != app.Image {
		err := RetryOnConflict(5, func() error {
			latest, err := r.deps.Get(key)
			if err != nil {
				return err
			}
			latest.Replicas, latest.Image = app.Replicas, app.Image
			_, err = r.deps.Update(latest)
			return err
		})
		if err != nil {
			return Result{}, err
		}
		r.log.Printf("reconcile %s: updated deployment to replicas=%d image=%s", key, app.Replicas, app.Image)
	}

	// Status: copy what the child reports. The user may be writing spec at the same time, so re-read.
	if app.ReadyReplicas != dep.ReadyReplicas {
		err := RetryOnConflict(5, func() error {
			latest, err := r.apps.Get(key)
			if err != nil {
				return err
			}
			latest.ReadyReplicas = dep.ReadyReplicas
			if _, err = r.apps.Update(latest); errors.Is(err, ErrConflict) {
				r.log.Printf("reconcile %s: status update hit %v; re-reading and retrying", key, ErrConflict)
			}
			return err
		})
		if err != nil {
			return Result{}, err
		}
		r.log.Printf("reconcile %s: status readyReplicas=%d", key, dep.ReadyReplicas)
	}
	if dep.ReadyReplicas != dep.Replicas {
		return Result{RequeueAfter: 200 * time.Millisecond}, nil // rollout in progress: look again soon
	}
	return Result{}, nil
}

func contains(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

func remove(list []string, s string) []string {
	out := list[:0]
	for _, x := range list {
		if x != s {
			out = append(out, x)
		}
	}
	return out
}

// ---------- Controller: informers feed the queue, workers call Reconcile, clean shutdown ----------

type Controller struct {
	r       *Reconciler
	queue   *Queue
	workers int
}

func (c *Controller) Run(ctx context.Context, wg *sync.WaitGroup) {
	// Watch WebApps by name and Deployments by owner: a child event enqueues its parent.
	wg.Add(2 + c.workers)
	go func() {
		defer wg.Done()
		RunInformer(ctx, c.r.apps, c.r.appCache, func(a *WebApp) { c.queue.Add(a.Name) })
	}()
	go func() {
		defer wg.Done()
		RunInformer(ctx, c.r.deps, c.r.depCache, func(d *Deployment) { c.queue.Add(d.Owner) })
	}()
	for i := 0; i < c.workers; i++ {
		go func() {
			defer wg.Done()
			c.worker(ctx)
		}()
	}
	wg.Add(1)
	go func() {
		defer wg.Done()
		<-ctx.Done()
		c.queue.ShutDown() // wakes every worker blocked in Get
	}()
}

func (c *Controller) worker(ctx context.Context) {
	for {
		key, down := c.queue.Get()
		if down {
			return
		}
		res, err := c.r.Reconcile(ctx, key)
		switch {
		case err != nil:
			d := c.queue.AddRateLimited(key)
			c.r.log.Printf("reconcile %s failed: %v; requeue in %v (failure %d)", key, err, d, c.queue.NumRequeues(key))
		case res.RequeueAfter > 0:
			c.queue.Forget(key)
			c.queue.AddAfter(key, res.RequeueAfter)
		default:
			c.queue.Forget(key)
		}
		c.queue.Done(key)
	}
}

// ---------- Fake kubelet: moves ReadyReplicas toward Replicas, one pod per tick ----------

func runKubelet(ctx context.Context, deps *Store[*Deployment], log *Log) {
	tick := time.NewTicker(30 * time.Millisecond)
	defer tick.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-tick.C:
			deps.mu.Lock()
			names := make([]string, 0, len(deps.items))
			for n := range deps.items {
				names = append(names, n)
			}
			deps.mu.Unlock()
			for _, n := range names {
				_ = RetryOnConflict(5, func() error {
					d, err := deps.Get(n)
					if err != nil || d.ReadyReplicas == d.Replicas {
						return nil
					}
					if d.ReadyReplicas < d.Replicas {
						d.ReadyReplicas++
					} else {
						d.ReadyReplicas = d.Replicas
					}
					if _, err = deps.Update(d); err == nil {
						log.Printf("kubelet: deployment %s readyReplicas=%d/%d", n, d.ReadyReplicas, d.Replicas)
					}
					return err
				})
			}
		}
	}
}

// ---------- Scenario ----------

var failures []string

func check(ok bool, what string) {
	if ok {
		fmt.Println("check ok:", what)
	} else {
		failures = append(failures, what)
		fmt.Println("CHECK FAILED:", what)
	}
}

func waitFor(what string, cond func() bool) bool {
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if cond() {
			return true
		}
		time.Sleep(5 * time.Millisecond)
	}
	fmt.Println("timeout waiting for:", what)
	return false
}

func main() {
	before := runtime.NumGoroutine()
	log := &Log{start: time.Now()}
	apps, deps := NewStore[*WebApp]("webapp"), NewStore[*Deployment]("deployment")
	r := &Reconciler{apps: apps, deps: deps, appCache: NewCache[*WebApp](), depCache: NewCache[*Deployment](),
		faults: &Faults{once: map[string]error{}}, log: log}
	ctrl := &Controller{r: r, queue: NewQueue(5*time.Millisecond, time.Second), workers: 2}

	ctx, cancel := context.WithCancel(context.Background())
	var wg sync.WaitGroup
	ctrl.Run(ctx, &wg)
	wg.Add(1)
	go func() {
		defer wg.Done()
		runKubelet(ctx, deps, log)
	}()

	// Stage 1: create a WebApp with 2 replicas; expect a Deployment, a finalizer and status 2/2.
	_, err := apps.Create(&WebApp{Meta: Meta{Name: "shop"}, Replicas: 2, Image: "shop:v1"})
	check(err == nil, "stage 1: webapp shop created")
	ready := func(n int, image string) bool {
		a, err1 := apps.Get("shop")
		d, err2 := deps.Get("shop")
		return err1 == nil && err2 == nil && d.Owner == "shop" && d.Replicas == n && d.Image == image &&
			d.ReadyReplicas == n && a.ReadyReplicas == n
	}
	check(waitFor("stage 1", func() bool { return ready(2, "shop:v1") }), "stage 1: deployment shop has 2/2 ready and webapp status says 2")
	a, _ := apps.Get("shop")
	check(contains(a.Finalizers, finalizerName), "stage 1: finalizer "+finalizerName+" is set")

	// Stage 2: scale to 3. Then make another client touch the WebApp right before the controller's
	// status write, so that write gets a Conflict and must re-read.
	err = RetryOnConflict(5, func() error {
		latest, err := apps.Get("shop")
		if err != nil {
			return err
		}
		latest.Replicas = 3
		_, err = apps.Update(latest)
		return err
	})
	check(err == nil, "stage 2: user scaled webapp to 3 replicas")
	var injected atomic.Int32
	apps.SetBeforeWrite(func() {
		latest, _ := apps.Get("shop")
		latest.Annotations = map[string]string{"touched-by": "another-client"}
		if _, err := apps.Update(latest); err == nil {
			injected.Add(1)
			log.Printf("other client: wrote annotation on webapp shop (rv now %d)", latest.ResourceVersion+1)
		}
	})
	check(waitFor("stage 2", func() bool { return ready(3, "shop:v1") }), "stage 2: deployment scaled to 3/3 and status says 3")
	appConflicts, _ := apps.Stats()
	check(injected.Load() == 1 && appConflicts >= 1, fmt.Sprintf("stage 2: injected 1 concurrent write, store rejected %d update(s) with Conflict", appConflicts))
	check(log.Contains("re-reading and retrying"), "stage 2: controller re-read after the Conflict and the retry succeeded")

	// Stage 3: a transient error on the next reconcile; expect a rate-limited requeue, then success.
	r.faults.Set("shop", errors.New("simulated API timeout"))
	err = RetryOnConflict(5, func() error {
		latest, err := apps.Get("shop")
		if err != nil {
			return err
		}
		latest.Image = "shop:v2"
		_, err = apps.Update(latest)
		return err
	})
	check(err == nil, "stage 3: user changed image to shop:v2")
	check(waitFor("stage 3", func() bool { return ready(3, "shop:v2") }), "stage 3: deployment rolled to shop:v2 after the transient error")
	check(len(ctrl.queue.Backoffs) == 1 && ctrl.queue.Backoffs[0] == 5*time.Millisecond,
		fmt.Sprintf("stage 3: exactly one backoff requeue, delay %v", ctrl.queue.Backoffs))
	check(ctrl.queue.NumRequeues("shop") == 0, "stage 3: failure count forgotten after the successful reconcile")

	// Stage 4: delete. The finalizer holds the object until the Deployment is gone.
	check(apps.Delete("shop") == nil, "stage 4: delete requested")
	check(waitFor("stage 4", func() bool {
		_, e1 := apps.Get("shop")
		_, e2 := deps.Get("shop")
		return errors.Is(e1, ErrNotFound) && errors.Is(e2, ErrNotFound)
	}), "stage 4: deployment removed first, then finalizer cleared and webapp gone")
	check(log.Contains("finalizer removed"), "stage 4: event log shows the finalizer being removed")

	// Stage 5: shutdown. Cancel the context, wait for every goroutine, compare goroutine counts.
	running := runtime.NumGoroutine()
	cancel()
	wg.Wait()
	time.Sleep(20 * time.Millisecond) // let any timer callback that fired during shutdown return
	after := runtime.NumGoroutine()
	appConflicts, appDropped := apps.Stats()
	depConflicts, depDropped := deps.Stats()
	check(appDropped == 0 && depDropped == 0, "no watch events were dropped")
	check(after == before, fmt.Sprintf("goroutines: %d before start, %d while running, %d after shutdown", before, running, after))

	fmt.Println("\nevent log:")
	for _, e := range log.entries {
		fmt.Println(" ", e)
	}
	fmt.Printf("\nstore conflicts: webapp=%d deployment=%d (the deployment ones are natural races with the kubelet)\n", appConflicts, depConflicts)
	if len(failures) > 0 {
		fmt.Printf("%d check(s) failed\n", len(failures))
		os.Exit(1)
	}
	fmt.Println("all checks passed")
}
```

## Follow-up questions interviewers ask

* Add `status.conditions` with `type`, `status`, `reason`, `message`, `lastTransitionTime` and `observedGeneration`. How does a user know the controller has seen the latest spec?
* Two replicas of this controller run at once. Add leader election with a `Lease`, and explain what happens during the 15 s lease transition.
* How would you test the real version with envtest, which starts a kube-apiserver and etcd but no kubelet? What does your test assert instead of ReadyReplicas?
* Move `ReadyReplicas` to a status subresource. Which conflicts disappear and why?
* The Deployment is edited by hand to 10 replicas. What does the controller do, and how fast? What if the controller was down for an hour?
* Replace the single `Store` lock with per-key versions and a relist on `410 Gone`. What changes in the informer?

## Lessons that cover this

* [#6Python and Go for automation and toolingFoundations](/devops/learn/python-and-go-for-devops)
* [#25Kubernetes internals and operators in GoContribute](/devops/learn/kubernetes-internals-operators-go)
* [#26Open source - contributing to CNCF projects, LFX and GSoCContribute](/devops/learn/open-source-cncf-lfx-gsoc)
* [#31Projects - pipeline, cluster, observability, operatorLater](/devops/learn/projects)

## Further reading

* [Operator patternGuidekubernetes.io](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
* [The Kubebuilder BookGuidebook.kubebuilder.io](https://book.kubebuilder.io/)
* [Borg, Omega, and KubernetesPaperresearch.google](https://research.google/pubs/pub44843/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousHelm chart from scratch with values, templates and a test](/devops/problems/helm-chart-from-scratch)[NextPython: SLO error budget and burn-rate alert calculator](/devops/problems/python-slo-burn-rate)

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
