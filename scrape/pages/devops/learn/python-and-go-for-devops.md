# Python and Go for automation and tooling — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/python-and-go-for-devops

[DevOps roadmap](/devops)

FoundationsLesson #6StudyIntermediate 5 h

# Python and Go for automation and tooling

A DevOps engineer needs two languages. Python is for scripts, checks, data and glue between APIs: fast to write, already installed everywhere. Go is for anything that ships as a single binary, does many things at once, or lives in the CNCF world, where Kubernetes, Helm, Argo CD, Prometheus and Terraform are written. This lesson shows the shape of a good Python ops script, the one page of Go a Python person needs, the worker-pool pattern with channels and context, and the mistakes that make Go tools leak.

pythongoautomationcliconcurrencytestingcncf

## Why it matters

Interviews for DevOps and SRE roles now include a coding round. The common tasks are "write a health checker with retries", "parse these logs and find the top errors", "call this API with pagination and summarise". Python answers them fastest. Platform and CNCF-adjacent roles add Go: "write a worker pool", "what is a goroutine leak", "how would you read client-go". LFX Mentorship and GSoC projects in Kubernetes, Argo, Prometheus or Cilium require Go on day one. Knowing which language to reach for, and the standard shape of a program in each, is what the interviewer is checking.

Read first: [Linux for operators](/devops/learn/linux-for-operators), [Bash scripting and the terminal toolkit](/devops/learn/bash-and-terminal-toolkit), [Networking for DevOps - TCP/IP, DNS, HTTP, TLS, SSH](/devops/learn/networking-for-devops)

## Lesson

### Why two languages

|  | Python | Go |
| --- | --- | --- |
| Best at | Scripts, checks, data, glue between APIs, quick CLIs | Services, operators, CLIs shipped as binaries, concurrent tools |
| Startup time | Tens of milliseconds for the interpreter plus imports | Single-digit milliseconds |
| Shipping | Needs an interpreter and a virtualenv or a container | One static binary, cross-compiled from any machine |
| Binary size | Not applicable; a container image is often 100 MB or more | Typically 5 to 15 MB, a scratch or distroless image of about the same |
| Concurrency | Threads limited by the GIL for CPU work; asyncio for I/O | Goroutines and channels, parallel across all cores |
| Typing | Dynamic, optional hints checked by mypy | Static, compiler-enforced |
| Error handling | Exceptions | Errors as return values |
| Ecosystem for us | boto3, requests, PyYAML, pytest, Ansible modules | client-go, controller-runtime, cobra, Prometheus client, Terraform providers |
| Where it wins | Anything you will write in an hour and run from a laptop or a CronJob | Anything others will install, that runs for months, or that talks to the Kubernetes API in volume |

The honest division of labour: write the health check, the cost report and the log parser in Python. Write the controller, the admission webhook, the kubectl plugin and the agent in Go. If a Python script grows a long-running loop and a concurrency problem, that is the signal to rewrite it in Go.

### The shape of a good Python ops script

Every ops script you write in Python should have the same skeleton: `argparse` for flags including `--dry-run`, `logging` to stderr so stdout stays parseable, `subprocess.run` with `check=True` and a `timeout`, HTTP calls with retries and backoff, `pathlib` for files, and explicit exit codes. The reader of your script is the on-call engineer at 3 a.m., and the shape tells them where to look.

```
#!/usr/bin/env python3
"""Drain a node safely: cordon, wait for pods to leave, with dry-run and timeouts."""
import argparse
import json
import logging
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

log = logging.getLogger("drain")

def run(cmd, timeout=30, dry_run=False):
    """Run a command; raise on non-zero exit; never hang forever."""
    log.info("run: %s", " ".join(cmd))
    if dry_run:
        return ""
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout

def get_json(url, retries=3, backoff=0.5, timeout=5):
    """GET with retries and exponential backoff; retry only on 5xx and network errors."""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise  # 4xx is our bug, do not retry
            log.warning("attempt %d: HTTP %d", attempt + 1, e.code)
        except (urllib.error.URLError, TimeoutError) as e:
            log.warning("attempt %d: %s", attempt + 1, e)
        time.sleep(backoff * 2 ** attempt)
    raise RuntimeError(f"gave up on {url} after {retries} attempts")

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("node")
    p.add_argument("--timeout", type=int, default=300, help="seconds to wait for pods to leave")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    try:
        run(["kubectl", "cordon", args.node], dry_run=args.dry_run)
        run(["kubectl", "drain", args.node, "--ignore-daemonsets", "--delete-emptydir-data",
             f"--timeout={args.timeout}s"], timeout=args.timeout + 10, dry_run=args.dry_run)
    except subprocess.CalledProcessError as e:
        log.error("command failed (%d): %s", e.returncode, e.stderr.strip())
        return 2
    except subprocess.TimeoutExpired:
        log.error("drain did not finish in %d s", args.timeout)
        return 3
    Path("/tmp/last-drained").write_text(args.node)
    print(json.dumps({"node": args.node, "drained": not args.dry_run}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Things to notice. `check=True` turns a failed command into an exception instead of a silent zero. `timeout` means a hung `kubectl` cannot hang your CronJob. The retry loop retries only on 5xx and network errors, because retrying a 403 just wastes time. Logs go to stderr and the one line of real output goes to stdout as JSON, so the next tool in the pipe can read it. Exit codes are distinct, so the caller can tell "command failed" from "timed out". For YAML, `import yaml` and `yaml.safe_load` (never `yaml.load` without a Loader) cover Kubernetes manifests and Helm values; `requests` with a `Session` and a `Retry` adapter is the usual upgrade from `urllib` when the package is available.

### Calling cloud APIs from Python

boto3 is the AWS SDK. Three rules. First, never put keys in code or in the repository: boto3 reads credentials from the environment, then from the pod's web identity token (IRSA on EKS), then from an SSO session, then from `~/.aws/credentials`, and last from the container or instance role (Pod Identity on EKS, an EC2 instance profile), in that order. Second, every list call is paginated and the default page hides the rest, so use a paginator. Third, pass a region explicitly in tooling that runs in CI.

```
import boto3

ec2 = boto3.client("ec2", region_name="ap-south-1")
paginator = ec2.get_paginator("describe_instances")
untagged = []
for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
    for reservation in page["Reservations"]:
        for inst in reservation["Instances"]:
            tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
            if "owner" not in tags:
                untagged.append(inst["InstanceId"])
print(len(untagged), "running instances have no owner tag")
```

Testing scripts like these is where most candidates stop, and where you can stand out. `pytest` plus `unittest.mock` lets you test the logic without a cluster:

```
from unittest.mock import patch
import subprocess
import drain  # the script above, importable because the logic is in main()

def test_dry_run_does_not_call_kubectl():
    with patch("drain.subprocess.run") as fake:
        assert drain.main(["node-1", "--dry-run"]) == 0
        fake.assert_not_called()

def test_failed_drain_returns_2():
    err = subprocess.CalledProcessError(1, ["kubectl"], stderr="node not found")
    with patch("drain.subprocess.run", side_effect=err):
        assert drain.main(["node-1"]) == 2
```

Mock the boundary (subprocess, HTTP, boto3 client), not your own functions. For boto3, `botocore.stub.Stubber` replays canned responses.

### Contracts first: OpenAPI specs and generated clients

An **OpenAPI spec** is a YAML or JSON document that describes an HTTP API: every path, method, parameter, request body, response schema and status code. It is the contract between the team that owns the service and everyone who calls it. Ops tooling should not hand-write `requests.get(f"{base}/v1/nodes/{name}")` calls against such an API. Generate a client from the spec instead: `oapi-codegen` produces Go client code, server stubs and typed models from an OpenAPI 3.0 or 3.1 document, and `openapi-python-client` produces a typed Python package with one function per endpoint and a class per schema. A generated client gives you the field names, the types and the enum values at compile time or in your editor, and when the service changes its spec, regenerating the client shows you every call that broke, instead of a 400 at runtime. The same spec is what an API gateway or a middleware validates incoming requests against: a body with a missing required field is rejected at the edge, before your handler runs. Keep the spec in the repo, lint it in CI and treat a spec change like a schema migration.

### Go in one page for a Python person

Go is small. Everything you need for ops tooling fits in one page of differences.

```
package main

import (
	"errors"
	"fmt"
	"os"
)

// A struct is a typed record. Fields that start with a capital letter are exported.
type Target struct {
	Name string
	URL  string
	Tags map[string]string // maps must be made before use: make(map[string]string)
}

// Methods attach to a type. The receiver (t Target) is like self.
func (t Target) String() string { return t.Name + " -> " + t.URL }

// An interface is satisfied by any type that has the methods. No "implements" keyword.
type Checker interface {
	Check(t Target) error
}

// Errors are values. The caller must look at them; nothing is thrown.
var ErrNoURL = errors.New("target has no URL")

func validate(t Target) error {
	if t.URL == "" {
		return fmt.Errorf("validate %s: %w", t.Name, ErrNoURL) // %w wraps, errors.Is can find it
	}
	return nil
}

func main() {
	targets := []Target{{Name: "api", URL: "https://api.example.com"}, {Name: "bad"}} // a slice
	targets = append(targets, Target{Name: "db", URL: "tcp://db:5432"})

	f, err := os.CreateTemp("", "report")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer os.Remove(f.Name()) // defer runs when main returns, in reverse order
	defer f.Close()

	for i, t := range targets { // range gives index and copy of the value
		if err := validate(t); err != nil {
			if errors.Is(err, ErrNoURL) {
				fmt.Printf("%d: skipped: %v\n", i, err)
			}
			continue
		}
		fmt.Fprintln(f, t) // uses String() because Target satisfies fmt.Stringer
	}
}
```

The translation table: `list` is a slice (`[]T`, grows with `append`), `dict` is a map (`map[K]V`, must be `make`d), `class` is a struct plus methods, duck typing is an interface (satisfied implicitly), `try/except` is `if err != nil`, `with` is `defer`, and `None` is `nil`. Unused imports and variables are compile errors, `gofmt` decides the formatting, and there are no exceptions, no inheritance and no generics tricks you need for tooling. Go has had generics since 1.18, and you will see `[T any]` in library code, but ops tools rarely need to write them.

### Goroutines, channels, context and the worker pool

![A Go worker pool: a producer sends jobs into a channel, four worker goroutines read them, each check honours a context deadline, results flow through a buffered channel to the main goroutine which waits on a WaitGroup](/devops/img/go-worker-pool-channels-context.svg)A Go worker pool: a producer sends jobs into a channel, four worker goroutines read them, each check honours a context deadline, results flow through a buffered channel to the main goroutine which waits on a WaitGroup

A **goroutine** is a function running concurrently, started with the keyword `go`. It costs a few kilobytes, so ten thousand of them are fine. A **channel** is a typed queue that goroutines use to hand values to each other; sending on an unbuffered channel blocks until someone receives. A **WaitGroup** counts running goroutines so `main` can wait for them. A **context** carries a deadline and a cancel signal down every call; every function that might block takes `ctx context.Context` as its first argument and gives up when `ctx.Done()` fires.

The worker pool is the pattern you will write most: N workers read jobs from one channel and write results to another. It bounds concurrency (you do not open 10000 connections to the API server), it collects results without locks, and with a context it has a hard deadline. The code example implements it with four workers over twelve checks, and the standard library `net/http` client takes the same context through `http.NewRequestWithContext`, so a real version is a small change.

### The standard library, modules and building

Go's standard library covers most of an ops tool: `net/http` for clients and servers (`http.ListenAndServe` and `http.HandleFunc` give you a `/healthz` endpoint in five lines), `encoding/json`, `os/exec` for running commands with a context (`exec.CommandContext`), `flag` for simple flags, `log/slog` for structured logs, `time`, `sync`. A **module** is a directory with a `go.mod` file naming the module path and the Go version; `go mod tidy` records every dependency with its exact version and hash in `go.sum`, so builds are reproducible.

```
go mod init github.com/you/checker        # creates go.mod
go build -o checker .                     # a static binary for this OS and CPU
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o checker-linux-arm64 .   # cross-compile, stripped
go vet ./... && go test ./...             # the two commands every CI job runs
```

`CGO_ENABLED=0` makes the binary fully static, which is what lets it run `FROM scratch` or distroless in a container. A real CLI with sub-commands, help text and shell completion is usually built with the `cobra` library (the one behind `kubectl`, `helm` and `gh`): a root command, `AddCommand` for each sub-command, flags bound to variables, and a `RunE` function that returns an error. You do not need it for a single-purpose tool; `flag` is enough.

### Measure before you argue: benchmarking languages

"Go is faster than Python" is a claim, not a number. Write the same hello handler (return `{"ok":true}` with a 200) in Node, Python and Go, run each on the same machine, and point one load generator at them in turn: `wrk -t4 -c100 -d30s --latency` against the local port prints requests per second and a latency distribution, and k6 reports `http_req_duration` with a threshold such as `p(99)<300`. Record requests per second and the p99 for each, with the CPU count, the framework and the flags used. Any number you quote in an interview or a design doc is from your own run and labelled as such ("on my 4-core laptop, Go stdlib served N requests per second"). Numbers copied from a blog post describe someone else's machine.

### Table-driven tests

Go tests live in `_test.go` files, use the `testing` package, and are run with `go test`. The idiom is a slice of cases and one loop:

```
func TestParseCIDR(t *testing.T) {
	cases := []struct {
		name    string
		in      string
		wantN   int
		wantErr bool
	}{
		{"slash24", "10.0.0.0/24", 256, false},
		{"slash28", "10.0.0.0/28", 16, false},
		{"garbage", "not-a-cidr", 0, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			n, err := countAddresses(tc.in)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr %v", err, tc.wantErr)
			}
			if n != tc.wantN {
				t.Errorf("got %d, want %d", n, tc.wantN)
			}
		})
	}
}
```

`go test -race ./...` runs the race detector, which finds the data races that only show up under load in production. Use it in CI for anything with goroutines.

### Common Go mistakes in ops tools

| Mistake | What goes wrong | Fix |
| --- | --- | --- |
| Goroutine leak | A worker blocks forever on a channel nobody reads or closes; memory and goroutine count climb for weeks | Close the jobs channel; buffer the results channel to the number of jobs; select on `ctx.Done()`; watch `runtime.NumGoroutine()` or the Go runtime metrics in Prometheus |
| Unbounded channels or goroutines | `go check(x)` in a loop over 50000 items opens 50000 connections | Worker pool with a fixed N; or a semaphore channel of size N |
| Ignoring errors | `resp, _ := client.Do(req)` then a nil-pointer panic at 3 a.m. | Handle every `err`; `errcheck` and `go vet` in CI |
| No context timeout | An HTTP call to a dead endpoint blocks forever; the whole tool hangs | `context.WithTimeout` on every outbound call, `http.Client{Timeout: ...}` as a backstop |
| Not closing `resp.Body` | Connections are never returned to the pool; file descriptors run out | `defer resp.Body.Close()` right after checking `err` |
| Shared map from goroutines | "concurrent map writes" fatal error | A mutex, or collect through a channel |
| Capturing the loop variable in a goroutine | All goroutines see the last value (Go before 1.22) | Pass it as an argument; Go 1.22 and later give each iteration its own variable |

### Reading client-go

Kubernetes controllers in Go all look the same once you know the shape: a `clientset` (or a controller-runtime `Client`) talks to the API server, an **informer** keeps a local cache of objects and calls your handler on add, update and delete, a **work queue** holds the keys of objects to reconcile, and a **reconcile** function reads the current object, compares it with the desired state, and makes one change. The reconcile function must be idempotent, because the same key is delivered again after errors and on every resync. The `go-reconcile-loop` problem has you write that function without client-go; lesson 25 shows the real thing with controller-runtime and Kubebuilder.

## Diagram

Rendering diagram…

## Worked example

**Sizing a worker pool for a health checker.** You must check 1200 endpoints every minute from one pod. Each check is an HTTP GET with a p50 of 150 ms and a p99 of 2 s, and 3 percent of endpoints are down and take the full timeout.

Step 1, serial time. 1200 checks at an average of about 200 ms (the mean sits above the median because of the slow tail) is 240 s. A 60 s cycle is impossible serially; you need at least 4 times parallelism just to break even.

Step 2, choose the timeout. The p99 is 2 s, so a 3 s context timeout loses almost nothing. The 36 down endpoints (3 percent of 1200) will each take 3 s.

Step 3, workers. With N workers the cycle takes roughly (total work) / N. Total work is 1164 x 0.2 s plus 36 x 3 s, which is 232.8 s plus 108 s, which is 340.8 s. For a 30 s cycle (half the budget, leaving room for jitter) N must be at least 340.8 / 30, which is 11.4, so 12 workers. Choose 16 for headroom.

Step 4, the channels. The jobs channel can be unbuffered: the producer blocks until a worker is free, which is the back-pressure you want. The results channel is buffered to 1200, so a worker never blocks on sending while `main` is still feeding jobs; a deadlock here is the classic leak. One WaitGroup counts 16 workers; `main` closes jobs after the last send, waits on the group, then closes results and reads them.

Step 5, memory and connections. 16 goroutines at about 8 KB each is trivial. 16 in-flight HTTP connections is fine for any target. If the targets share a few hosts, set `http.Transport.MaxConnsPerHost` so you do not become the DDoS.

Step 6, the Python comparison. The same design in Python uses `concurrent.futures.ThreadPoolExecutor(max_workers=16)`, which works because the checks are I/O bound and release the GIL. It is a fine choice if the checker runs as a CronJob. It becomes the wrong choice when the checker also exposes `/metrics`, keeps state across cycles and runs for months: then the Go version's static binary, race detector and goroutine metrics pay for themselves. The code example runs the Go design at small scale and proves the goroutine count returns to its starting value.

## Runnable code

Go · gofmt and go vet clean · runs and prints its own checks

```
// A worker pool that checks 12 fake endpoints with 4 goroutines, a context
// timeout, a results channel and a leak check. Standard library only.
//
// The shape is the one you will see in real ops tools: a bounded number of
// workers read jobs from a channel, every check takes a context so it can be
// cancelled, results flow back through one channel, and the main goroutine
// waits for everything to finish before it prints a summary.
package main

import (
	"context"
	"errors"
	"fmt"
	"math/rand"
	"runtime"
	"sort"
	"sync"
	"time"
)

// result is what one check produces. Err is nil when the endpoint was healthy.
type result struct {
	name    string
	latency time.Duration
	err     error
}

// endpoint is a fake HTTP check: it sleeps for a while and sometimes fails.
// A real tool would call http.Client.Do with a request built from ctx.
type endpoint struct {
	name    string
	latency time.Duration
	fails   bool
}

var errUnhealthy = errors.New("status 503")

// check honours the context: if the deadline passes before the fake latency
// elapses, it returns ctx.Err() instead of blocking the worker forever.
func check(ctx context.Context, ep endpoint) result {
	start := time.Now()
	select {
	case <-time.After(ep.latency):
	case <-ctx.Done():
		return result{name: ep.name, latency: time.Since(start), err: ctx.Err()}
	}
	if ep.fails {
		return result{name: ep.name, latency: time.Since(start), err: errUnhealthy}
	}
	return result{name: ep.name, latency: time.Since(start)}
}

// runPool starts `workers` goroutines that pull endpoints from a channel and
// push results to another. It returns when every endpoint has a result.
func runPool(ctx context.Context, endpoints []endpoint, workers int) []result {
	jobs := make(chan endpoint)                  // unbuffered: workers pull at their own pace
	results := make(chan result, len(endpoints)) // buffered: workers never block on send
	var wg sync.WaitGroup

	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			for ep := range jobs { // exits when jobs is closed
				results <- check(ctx, ep)
			}
		}(w)
	}

	// Feed the jobs, then close the channel so the workers' range loops end.
	// If the context is cancelled mid-way we still send every job: the
	// workers return ctx.Err() immediately, so nothing blocks.
	for _, ep := range endpoints {
		jobs <- ep
	}
	close(jobs)

	wg.Wait()      // every worker has returned
	close(results) // safe: no more senders

	var out []result
	for r := range results {
		out = append(out, r)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].name < out[j].name })
	return out
}

func makeEndpoints(n int, seed int64) []endpoint {
	rng := rand.New(rand.NewSource(seed)) // fixed seed: same "random" failures every run
	eps := make([]endpoint, 0, n)
	for i := 0; i < n; i++ {
		eps = append(eps, endpoint{
			name:    fmt.Sprintf("svc-%02d", i+1),
			latency: time.Duration(50+rng.Intn(400)) * time.Millisecond, // 50 to 449 ms
			fails:   rng.Intn(4) == 0,                                   // about 1 in 4
		})
	}
	return eps
}

func main() {
	const workers, n = 4, 12
	endpoints := makeEndpoints(n, 42)

	before := runtime.NumGoroutine()
	fmt.Printf("goroutines before: %d\n", before)

	// Run 1: a generous timeout, every check finishes.
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	start := time.Now()
	res := runPool(ctx, endpoints, workers)
	cancel() // always call cancel, even after success, to free the timer
	elapsed := time.Since(start)

	var ok, failed, timedOut int
	for _, r := range res {
		status := "ok"
		switch {
		case errors.Is(r.err, context.DeadlineExceeded):
			status = "timeout"
			timedOut++
		case r.err != nil:
			status = "FAIL " + r.err.Error()
			failed++
		default:
			ok++
		}
		fmt.Printf("  %-7s %4d ms  %s\n", r.name, r.latency.Milliseconds(), status)
	}
	var serial time.Duration
	for _, ep := range endpoints {
		serial += ep.latency
	}
	fmt.Printf("run 1: %d checks, %d ok, %d failed, %d timed out, wall %d ms "+
		"(serial would be %d ms)\n", len(res), ok, failed, timedOut,
		elapsed.Milliseconds(), serial.Milliseconds())

	// Run 2: a timeout shorter than most latencies, to show cancellation.
	ctx2, cancel2 := context.WithTimeout(context.Background(), 120*time.Millisecond)
	res2 := runPool(ctx2, endpoints, workers)
	cancel2()
	timedOut2 := 0
	for _, r := range res2 {
		if errors.Is(r.err, context.DeadlineExceeded) {
			timedOut2++
		}
	}
	fmt.Printf("run 2: 120 ms budget, %d of %d checks returned context deadline exceeded\n",
		timedOut2, len(res2))

	// Leak check: after both pools have drained, the goroutine count must be
	// back where it started. A forgotten close(jobs) or a worker stuck on an
	// unbuffered results channel would show up here.
	time.Sleep(20 * time.Millisecond) // let timers from time.After settle
	after := runtime.NumGoroutine()
	fmt.Printf("goroutines after: %d\n", after)

	// Self-checks.
	if len(res) != n {
		panic(fmt.Sprintf("expected %d results, got %d", n, len(res)))
	}
	if failed == 0 || ok == 0 {
		panic("the fixed seed should give a mix of healthy and failing endpoints")
	}
	if timedOut != 0 {
		panic("nothing should time out with a 5 s budget")
	}
	if elapsed >= serial {
		panic("the pool should be faster than running the checks one by one")
	}
	if timedOut2 == 0 {
		panic("the 120 ms budget should cancel the slow checks")
	}
	if after != before {
		panic(fmt.Sprintf("goroutine leak: %d before, %d after", before, after))
	}
	fmt.Println("self-checks passed: all results collected, pool faster than serial, " +
		"timeouts honoured, no goroutine leak")
}
```

## Key takeaways

* Python for scripts, checks, data and glue; Go for binaries, long-running tools, concurrency and anything in the CNCF ecosystem.
* A good Python ops script has argparse with a dry-run flag, logging to stderr, subprocess with check=True and a timeout, retries with backoff only on retryable errors, and distinct exit codes.
* Never hard-code cloud keys; let the SDK find credentials from the environment or the pod identity, and always paginate list calls.
* Test scripts by mocking the boundary (subprocess, HTTP, the boto3 client), not your own logic.
* Go basics for ops: structs, slices, maps, errors as values with %w and errors.Is, defer, implicit interfaces.
* The worker pool: a jobs channel, N goroutines, a buffered results channel, a WaitGroup, and one context carrying the deadline.
* Every outbound call in Go gets a context timeout; every goroutine has a known way to exit; every resp.Body is closed.
* CGO\_ENABLED=0 go build gives a static binary for a scratch image; go vet and go test -race belong in CI.

## Common mistakes

* Writing a 400-line Bash script that should have been a 100-line Python script with argparse and tests.
* `subprocess.run` without `check=True`, so a failed kubectl is reported as success, or without `timeout`, so a hung command hangs the job.
* Retrying every HTTP error, including 401 and 403, which turns a config bug into a slow config bug.
* Starting a goroutine per item in a loop with no bound, no context and no way to stop it, then wondering why memory grows for a week.
* Forgetting `close(jobs)` or using an unbuffered results channel, so workers block forever and `wg.Wait()` never returns.
* Ignoring the error from `client.Do` or `json.Unmarshal` because "it always works".

## Practice

* Turn the Python skeleton in this lesson into a real script that lists pods with more than 5 restarts across all namespaces, with `--dry-run`, JSON output and a pytest that mocks `subprocess.run`. Run it against a kind cluster.
* Run the Go code example, then remove `close(jobs)` and run it with `timeout 10s go run .` to see the hang; restore it, make the results channel unbuffered, and observe the second deadlock. Explain both in one sentence each.
* Replace the fake `check` with a real `http.Get` using `http.NewRequestWithContext` against 12 public URLs, add `-race` to the run, and confirm the goroutine count still returns to its starting value.
* Build the Go tool with `CGO_ENABLED=0 GOOS=linux GOARCH=arm64`, put it in a `FROM scratch` image, and record the image size next to a Python image doing the same job.

## Interview questions (10)

1.When would you write a tool in Python and when in Go?Easy

Python when the tool is a script someone runs from a laptop or a CronJob, is mostly I/O and text, and will be written in an afternoon: health checks, reports, log parsing, calling AWS and the Kubernetes API through boto3 or the client. Go when the tool ships to other people as a binary, runs for months, needs real concurrency, or lives in the Kubernetes ecosystem: controllers, admission webhooks, kubectl plugins, agents, anything that would contribute to a CNCF project. The tell for a rewrite is a Python script that has grown a long-running loop and a concurrency bug.

2.What does a well-structured Python ops script look like?Easy

argparse for flags, including `--dry-run` and `--verbose`; logging configured to stderr so stdout stays machine-readable; `subprocess.run` with `check=True`, `capture_output=True`, `text=True` and a `timeout`; HTTP calls through a function that retries with exponential backoff only on 5xx and network errors; `pathlib` for files; `yaml.safe_load` for manifests; a `main(argv)` function that returns an exit code so tests can call it; and distinct exit codes for distinct failures. Credentials come from the environment or the pod identity, never from the file.

3.Explain goroutines and channels to someone who knows Python threads.Medium

A goroutine is a function started with `go f()`; the Go runtime multiplexes thousands of them over a few OS threads, and unlike Python threads they run in parallel on all cores. A channel is a typed, thread-safe queue: `ch <- v` sends, `v := <-ch` receives, and an unbuffered channel blocks the sender until a receiver is ready, which gives you back-pressure for free. `sync.WaitGroup` is how `main` waits for goroutines to finish. Instead of sharing a list protected by a lock, you send results through a channel. The closest Python analogue is `ThreadPoolExecutor` with a `queue.Queue`, but Go's version is cheaper and parallel.

4.What is a goroutine leak and how do you find one?Medium

A goroutine that can never exit: usually blocked sending on a channel nobody reads, receiving from a channel nobody closes, or waiting on an HTTP call with no timeout. Each one holds its stack and whatever it references, so memory and the goroutine count climb slowly until the pod is OOM-killed. I find it with `runtime.NumGoroutine()` in a test before and after the work, the `go_goroutines` metric in Prometheus trending up, or the `/debug/pprof/goroutine` endpoint, which shows exactly which line each goroutine is stuck on. The fixes are closing the jobs channel, buffering the results channel, selecting on `ctx.Done()`, and a context timeout on every outbound call.

5.Why does every Go function in an ops tool take a context as its first argument?Medium

Context carries a deadline, a cancel signal and request-scoped values down the call chain. When the top-level operation has a 30 s budget, every HTTP call, exec and database query under it inherits that budget through `context.WithTimeout`, and when the caller cancels, every goroutine below sees `ctx.Done()` and stops. Without it, a tool that calls a dead endpoint blocks forever and all its workers pile up behind it. The convention is `func Do(ctx context.Context, ...)`, always first, never stored in a struct, and always with `defer cancel()` after creating one so the timer is released.

6.How do you make sure a Python script that calls kubectl is tested without a cluster?Medium

I keep the logic in functions that take arguments and return values, with `main(argv)` returning an exit code, and I put every external call behind a small function like `run(cmd)`. In pytest I patch `subprocess.run` with `unittest.mock.patch`: `assert_not_called()` proves that `--dry-run` runs nothing, `side_effect=CalledProcessError(...)` proves the script returns the right exit code when kubectl fails, and `return_value` with a canned `stdout` tests the parsing. For boto3 I use `botocore.stub.Stubber` to replay responses. The rule is to mock the boundary, not my own functions, so the test still exercises the real logic.

7.Describe the worker-pool pattern and the two channel mistakes that deadlock it.Hard

One producer sends jobs into a channel, N worker goroutines range over it and send results into a second channel, a WaitGroup counts the workers, and main closes the jobs channel after the last send, waits on the group, then closes and drains results. The first deadlock is forgetting to close the jobs channel: the workers' `range` loops never end, `wg.Wait()` never returns. The second is an unbuffered results channel with main not reading until after `wg.Wait()`: every worker blocks on its first send, nobody finishes, main waits forever. The fix is a results buffer of at least the number of jobs, or a separate goroutine that drains results while the workers run. I also give every check a context so a slow endpoint cannot hold a worker.

8.How do you build and ship a Go tool so it runs in a minimal container?Easy

`CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o tool .` produces a static binary with no libc dependency and the symbol table stripped, usually under 15 MB. The Dockerfile is a two-stage build: a Go image compiles it, then `FROM gcr.io/distroless/static` or `FROM scratch` copies in the binary and CA certificates and runs as a non-root user. Cross-compiling for arm64 is just `GOARCH=arm64`, which matters for Graviton nodes. `go mod tidy` and the committed `go.sum` make the build reproducible, and CI runs `go vet`, `go test -race` and a linter before the image is pushed.

9.What does reading a Kubernetes controller in Go look like, at a high level?Medium

Every controller has the same parts. A client (clientset or controller-runtime Client) talks to the API server. An informer watches one resource type, keeps a cached copy of every object, and calls handlers on add, update and delete; the handlers do nothing except push the object's namespace-and-name key onto a work queue. Workers pop keys and call Reconcile, which reads the current object from the cache, reads whatever it owns, compares with the desired state, and makes one change through the client, then returns an error to be retried with backoff. Reconcile must be idempotent because the same key arrives many times. Once you see that shape, client-go code stops looking mysterious.

10.Compare Python's concurrency options with Go's for an I/O-heavy checker.Medium

In Python, threads work well for I/O because the GIL is released during network waits, so `ThreadPoolExecutor(max_workers=16)` gives a fine health checker; asyncio with `aiohttp` scales further for thousands of connections but forces every library to be async. CPU-bound work needs multiprocessing. In Go, goroutines handle both I/O and CPU in parallel, the worker pool is a few lines, context gives cancellation everywhere, and the race detector finds shared-state bugs in tests. For a CronJob that checks 1200 endpoints once a minute, Python is enough. For a service that checks continuously, exposes metrics and runs for months, Go is the better long-term choice.

## Quiz

1.Which combination makes subprocess.run safe for an ops script?

2.In a Go worker pool, what happens if main never closes the jobs channel?

3.Which build command produces a static Linux binary for a scratch image?

4.How does boto3 find credentials in a pod on EKS without any keys in the code?

5.Which Go idiom lets a caller check for a specific wrapped error?

## Practice these problems

* [CODEBash: safe deploy script with locking, rollback and trapsMedium](/devops/problems/bash-safe-deploy-script)
* [CODEPython: concurrent health checker with retries and backoffMedium](/devops/problems/python-health-checker)
* [CODEGo: a Kubernetes-style reconcile loop for a custom resourceHard](/devops/problems/go-reconcile-loop)
* [CODEPython: SLO error budget and burn-rate alert calculatorEasy](/devops/problems/python-slo-burn-rate)

## Further reading

* [A Tour of GoGuidego.dev](https://go.dev/tour/)
* [Effective GoGuidego.dev](https://go.dev/doc/effective_go)
* [Go by ExampleGuidegobyexample.com](https://gobyexample.com/)
* [Python for EverybodyGuidepy4e.com](https://py4e.com)
* [kubernetes/client-go: Go client for KubernetesGuidegithub.com](https://github.com/kubernetes/client-go)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousGit and trunk-based workflows](/devops/learn/git-and-trunk-based-workflows)[NextWeb servers, reverse proxies and TLS - Nginx, certificates, process managers](/devops/learn/nginx-reverse-proxy-tls)

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

1. [Why two languages](#why-two-languages)
2. [The shape of a good Python ops script](#the-shape-of-a-good-python-ops-script)
3. [Calling cloud APIs from Python](#calling-cloud-apis-from-python)
4. [Contracts first: OpenAPI specs and generated clients](#contracts-first-openapi-specs-and-generated-clients)
5. [Go in one page for a Python person](#go-in-one-page-for-a-python-person)
6. [Goroutines, channels, context and the worker pool](#goroutines-channels-context-and-the-worker-pool)
7. [The standard library, modules and building](#the-standard-library-modules-and-building)
8. [Measure before you argue: benchmarking languages](#measure-before-you-argue-benchmarking-languages)
9. [Table-driven tests](#table-driven-tests)
10. [Common Go mistakes in ops tools](#common-go-mistakes-in-ops-tools)
11. [Reading client-go](#reading-client-go)
