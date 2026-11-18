# Projects - pipeline, cluster, observability, operator — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/projects

[DevOps roadmap](/devops)

LaterLesson #31LaterIntermediate 2 h

# Projects - pipeline, cluster, observability, operator

Five portfolio projects that together cover the whole roadmap: a service shipped to a VM by hand and then automated, a complete CI/CD pipeline, a production-shaped Kubernetes platform, an observability stack with a game day, and a Kubernetes operator in Go. Each has a one-to-two-week scope, numbered build steps, a measurable acceptance test, and the mistakes that make it look weak. The lesson ends with how to present a project in two minutes.

projectsportfolioci/cdkubernetesobservabilityoperatorinterview

## Why it matters

Early-career DevOps interviews in India are mostly conversations about what you have built. A certificate says you watched a course; a repository with a README, a diagram and numbers says you can do the job. Interviewers ask "tell me about a project" and then push: why that choice, what broke, what would you change. A project built the way this lesson describes gives you an answer to every one of those, and the numbers in the README are what separate "I deployed an app" from "I cut the pipeline from 14 to 6 minutes and deployed 14 times a week".

Read first: [CI/CD with GitHub Actions and GitLab CI](/devops/learn/ci-cd-github-actions-gitlab), [GitOps with Argo CD and progressive delivery](/devops/learn/gitops-argocd-progressive-delivery), [Observability - Prometheus, Grafana, OpenTelemetry, logs and alerting](/devops/learn/observability-prometheus-grafana-otel), [Kubernetes internals and operators in Go](/devops/learn/kubernetes-internals-operators-go)

## Lesson

### How to pick a problem that is yours

Pick something you will actually use or that annoys you: a tool for your college club, a bot, a status page for a friend's site. Ownership shows in interviews because you know the details. Keep each project to one or two weeks of evenings; a finished small project beats an unfinished large one. Every project must end with a number you measured, a diagram you drew, and a README written for someone who has never seen the repo. The five projects below build on each other; do them in order if you can.

| Project | Proves which skill | The number to report |
| --- | --- | --- |
| 1. Ship to a VM, then automate it | Linux, Nginx, TLS, systemd, Docker Compose, GitHub Actions | Deploy time by hand vs by pipeline; TLS grade; uptime over a week |
| 2. CI/CD for a monorepo | Change detection, caching, scanning, signing, deploy by digest | Pipeline minutes before and after; images blocked by the scanner |
| 3. Production-shaped Kubernetes platform | Terraform, Argo CD, ingress, secrets, policy, HPA, PDB, canary | Time to rebuild the cluster from Git; canary abort time on a bad release |
| 4. Observability stack and game day | Prometheus, Loki, Tempo, OpenTelemetry, SLOs, postmortem | Time to detect and time to diagnose in the game day |
| 5. Operator in Go | kubebuilder, reconcile loop, envtest, Helm packaging, open source | Test coverage of the reconciler; the merged upstream PR |

### Project 1: ship a service to a VM the manual way, then automate it

**Goal.** Understand everything a platform hides by doing it once by hand: a small API (any language) on one Linux VM, reachable over HTTPS, surviving a reboot, deployed by a pipeline.

**Scope.** One free-tier EC2 instance or any small VM, one domain or a free subdomain, one service with a `/healthz` endpoint.

1. Create the VM, lock SSH to key auth, open only ports 22, 80 and 443 in the security group.
2. Run the service under systemd (or PM2 for Node) with `Restart=always`; confirm it comes back after `sudo reboot`.
3. Put Nginx in front as a reverse proxy; get a certificate from Let's Encrypt with certbot and confirm auto-renewal with `certbot renew --dry-run`.
4. Write a GitHub Actions workflow that, on push to main, builds, copies the artifact over SSH, restarts the unit and curls `/healthz`. Time it.
5. Repeat the deploy with Docker Compose: the service plus Nginx as containers, the certificate in a volume. Compare the two.

**Acceptance test.** `curl -I https://your.domain/healthz` returns 200 with a valid certificate; the service is back within 30 seconds of a reboot; a push to main is live in under 3 minutes with no manual step.

**What to show.** A README with the two deploy times, the SSL Labs grade, the systemd unit and the Nginx config, and a diagram of the request path (DNS, Nginx, service).

**Weak signs.** Secrets in the repo; a service started by hand in a tmux session; HTTP only; no rollback step in the pipeline.

### Project 2: a complete CI/CD pipeline for a small monorepo

**Goal.** A pipeline a reviewer would trust: only changed services build, every image is scanned and signed, and deploys use digests, never tags.

**Scope.** Two or three services in one repo, GitHub Actions, GHCR or ECR, a target from project 1 or 3.

1. Add path-based change detection so a commit touching only `services/api` builds only that service.
2. Cache dependencies and Docker layers; measure the pipeline before and after.
3. Scan each image with Trivy and fail the job on critical findings; record what was blocked.
4. Sign each image with cosign keyless and verify the signature before deploy.
5. Deploy by digest (`image@sha256:...`) by updating a manifest or a Helm value in a commit, and keep `main` protected behind required checks.

**Acceptance test.** A commit touching one service builds only that service; a deliberately vulnerable base image is blocked; an unsigned image is refused at deploy; the pipeline runs in under 6 minutes for a one-service change.

**What to show.** Pipeline duration before and after caching, the scanner's finding count, a signed-image verification log, and a flowchart of the stages.

**Weak signs.** `latest` tags; a workflow that rebuilds everything on every push; secrets printed in logs; no branch protection.

### Project 3: a production-shaped Kubernetes platform

**Goal.** A cluster that looks like the one in the design problems: created from code, configured from Git, with the guardrails a real team needs.

**Scope.** kind on a laptop, or a small EKS cluster you destroy at night. Terraform for the cluster, Argo CD for everything on it.

1. Terraform the cluster (kind provider or the EKS module), with a remote state backend if on AWS.
2. Install Argo CD and an app-of-apps that installs: the AWS Load Balancer Controller on EKS (or Envoy Gateway on kind; ingress-nginx is retired, so do not start on it), cert-manager with TLS, external-secrets backed by AWS Secrets Manager or a local secret store, Kyverno, metrics-server.
3. Add Kyverno policies: no `latest` tags, resources required, Pod Security Standards baseline. Show a denied deploy.
4. Deploy the monorepo services with an HPA, a PodDisruptionBudget, and an Argo Rollouts canary (`setWeight` 10, pause, 50, pause, 100) with an analysis that aborts on a 5xx rate.
5. Destroy and rebuild the whole thing from Git. Time it.

**Acceptance test.** `terraform destroy` then `terraform apply` plus one Argo CD sync brings every application to Healthy in under 20 minutes; a release with a failing readiness probe is aborted by the canary with no user-facing errors; `kubectl drain` of a node does not take the service below its PDB.

**What to show.** The rebuild time, the Argo CD application tree, the Kyverno denial, the Rollouts timeline of an aborted canary, and a diagram of the platform layers.

**Weak signs.** Manifests applied with kubectl by hand; secrets in Git; an HPA with no resource requests; no PDB; canary with no analysis.

### Project 4: an observability stack and a game day

**Goal.** Metrics, logs and traces through one pipeline, dashboards someone else can read, alerts that page on SLO burn, and a written postmortem of a failure you caused.

**Scope.** On the cluster from project 3: Prometheus, Grafana, Loki, Tempo, and the OpenTelemetry Collector in front of all three.

1. Instrument one service with the OpenTelemetry SDK; send traces, metrics and logs to a Collector; route them to Tempo, Prometheus and Loki.
2. Build a RED dashboard (rate, errors, duration) per service, plus a saturation row.
3. Define an SLO (99.9 percent of requests under 300 ms) and write multi-window burn-rate alerts (14.4x over 1 hour, 6x over 6 hours).
4. Run a game day: inject a fault (kill the database, add 500 ms latency with a sidecar or `tc`, fill a disk) without telling your future self the time. Note when the alert fired and when you found the cause from the dashboard, logs and a trace.
5. Write a blameless postmortem: timeline, impact, root cause, what went well, action items.

**Acceptance test.** A trace from the ingress to the database is visible in Tempo with the matching log lines in Loki by trace id; the fast-burn alert fires within 5 minutes of the fault; time to diagnose from the dashboard is under 15 minutes.

**What to show.** Time to detect and time to diagnose, the dashboard screenshot, the alert rules, the postmortem, and a diagram of the telemetry pipeline.

**Weak signs.** Dashboards nobody could read without you; alerts on CPU instead of the SLO; a postmortem that blames a person; no action items.

### Project 5: a Kubernetes operator in Go, and a first open source PR

**Goal.** The WebApp CRD from lesson 25 built for real: a controller that turns one custom object into a Deployment, a Service and an Ingress, tested, packaged, and a first contribution to a CNCF project.

**Scope.** kubebuilder, envtest, a Helm chart, one small upstream PR.

1. Scaffold with `kubebuilder init` and `kubebuilder create api`; define `WebApp` with image, replicas, host and a status with ready replicas and conditions.
2. Write the reconcile loop: create or update the three owned objects, set owner references, update status, requeue on error with backoff.
3. Test the reconciler with envtest: a WebApp creates its objects, changing replicas updates the Deployment, deleting the WebApp garbage-collects everything.
4. Package the CRD and controller as a Helm chart with a `templates/tests/` check; install it on the project 3 cluster through Argo CD.
5. Find a `good first issue` in a CNCF project (Kubernetes, Argo CD, Helm, Cilium, Kyverno), fix it, and get the PR merged. Link it in the README.

**Acceptance test.** `go test ./...` passes with envtest at over 70 percent coverage of the controller package; `helm install` on a fresh cluster followed by `kubectl apply` of a WebApp yields a reachable site within 60 seconds; one upstream PR is merged.

**What to show.** Coverage, the reconcile diagram, the CRD YAML, the chart, and the merged PR.

**Weak signs.** A controller with no tests; status never updated; objects without owner references, so they leak; a PR that only fixes a typo.

### Optional project 6: an uptime monitor

A BetterStack-style monitor from the 100xDevs cohort: users register URLs; probe workers in two or three regions check them every minute; results flow through Redis Streams from the API to the workers and on to "pusher" processes that alert and update a public status page. It proves async design with queues, consumer groups and a public page under load. The number to report: probes per minute sustained and the time from a site going down to the alert.

### How to present a project in two minutes

Problem (15 seconds): who needed what. Design (30 seconds): the diagram in words, three components, the data flow. Trade-offs (30 seconds): two choices you made and what you gave up. Numbers (20 seconds): before and after. What broke (15 seconds): one real failure and how you found it. What you would change (10 seconds): one honest improvement. Practise it aloud, timed. The interviewer will interrupt; that is good, it means they are interested.

## Diagram

Rendering diagram…

## Worked example

**A README skeleton for project 2, filled with illustrative numbers.** The numbers are examples, not measurements; yours will differ.

```
# orders-monorepo pipeline

## What it does
Builds, scans, signs and deploys three services (api, worker, web) from one repo
with GitHub Actions. Only changed services build. Deploys use image digests.

## Numbers (example values)
| Metric                              | Before   | After    | Change        |
| ----------------------------------- | -------- | -------- | ------------- |
| Pipeline time, one-service change   | 14.2 min | 6.1 min  | -8.1 min, -57% |
| Deploys per week                    | 3        | 14       | +11, +367%     |
| Images blocked by Trivy (4 weeks)   | 0 (no scan) | 7     | new control    |
| Unsigned images that reached deploy | n/a      | 0        | verified       |

## Design
[diagram: push -> change detection -> build matrix -> trivy -> cosign -> push -> bump digest in gitops repo -> Argo CD]

## Trade-offs
- Keyless cosign signing needs an OIDC identity in CI; simpler than key management, but
  the verify step must pin the issuer and the workflow identity or it proves nothing.
- Change detection by path misses a shared library change; the fix is to map library
  paths to every dependent service, which is in paths-filter.yaml.

## What broke
- The first digest bump committed to the gitops repo from CI triggered the pipeline
  again (a loop). Fixed by ignoring the gitops path and using a bot identity.

## What I would change
- Move to a merge queue so two digest bumps cannot race.
```

How those example numbers were produced, so you can reproduce yours. Pipeline time: run the same one-file change ten times before and after caching and take the median; 14.2 to 6.1 minutes is an 8.1 minute cut, and 8.1 / 14.2 = 57 percent. Deploys per week: count merged pull requests that reached production; 3 to 14 is plus 11, and 11 / 3 = 367 percent. Blocked images: the count of pipeline runs failed by the scanner over four weeks, which is a new control so there is no "before". The interviewer's follow-up will be "why did deploys go up": because the pipeline got fast enough that people stopped batching changes, which is the DORA argument in one sentence.

## Runnable code

Python · runs and prints its own checks

```
"""Before and after comparison for a project README.

Give it two dictionaries of metrics and it prints a table with absolute and
relative change, marking whether the change is an improvement. For some metrics
lower is better (pipeline minutes, p95 latency, cost, time to restore); for
others higher is better (deploys per week, coverage). The direction is declared
per metric so the script never guesses.
"""

# metric name -> (unit, lower_is_better)
METRICS = {
    "pipeline_minutes": ("min", True),
    "deploys_per_week": ("/wk", False),
    "p95_latency_ms": ("ms", True),
    "monthly_cost_usd": ("USD", True),
    "time_to_restore_min": ("min", True),
    "test_coverage_pct": ("%", False),
}

def compare(before, after):
    """Return rows of (metric, before, after, abs_change, rel_change_pct, verdict)."""
    rows = []
    for name, (unit, lower_better) in METRICS.items():
        if name not in before or name not in after:
            continue
        b, a = before[name], after[name]
        delta = a - b
        rel = (delta / b * 100) if b else float("inf")
        improved = delta < 0 if lower_better else delta > 0
        verdict = "better" if improved else ("same" if delta == 0 else "worse")
        rows.append((name, b, a, unit, delta, rel, verdict))
    return rows

def fmt(x):
    return f"{x:.1f}" if isinstance(x, float) and not x.is_integer() else f"{int(x)}"

def print_table(rows):
    print(f"{'metric':<22} {'before':>8} {'after':>8} {'unit':<5} {'change':>10} {'relative':>9}  verdict")
    for name, b, a, unit, delta, rel, verdict in rows:
        sign = "+" if delta > 0 else ""
        rel_s = "n/a" if rel == float("inf") else f"{sign}{rel:.0f}%"
        print(f"{name:<22} {fmt(b):>8} {fmt(a):>8} {unit:<5} {sign}{fmt(delta):>9} {rel_s:>9}  {verdict}")

if __name__ == "__main__":
    before = {"pipeline_minutes": 14.2, "deploys_per_week": 3, "p95_latency_ms": 820,
              "monthly_cost_usd": 212, "time_to_restore_min": 48, "test_coverage_pct": 41}
    after = {"pipeline_minutes": 6.1, "deploys_per_week": 14, "p95_latency_ms": 410,
             "monthly_cost_usd": 148, "time_to_restore_min": 9, "test_coverage_pct": 72}
    rows = compare(before, after)
    print_table(rows)

    # Self-checks against hand-computed values.
    by_name = {r[0]: r for r in rows}
    assert round(by_name["pipeline_minutes"][5]) == -57
    assert round(by_name["deploys_per_week"][5]) == 367
    assert round(by_name["p95_latency_ms"][5]) == -50
    assert round(by_name["monthly_cost_usd"][5]) == -30
    assert all(r[6] == "better" for r in rows)
    # A regression must be called out, not hidden.
    worse = compare({"p95_latency_ms": 400}, {"p95_latency_ms": 520})
    assert worse[0][6] == "worse" and round(worse[0][5]) == 30
    print("\nself-checks passed: directions respected, a regression is reported as worse")
```

## Key takeaways

* A project counts when it has a README with measured numbers, a diagram and a story of what broke.
* Build in order: ship by hand, automate the pipeline, build the platform, observe it, extend it with an operator.
* Every project needs an acceptance test you can run in front of someone: a rebuild time, a blocked image, an aborted canary, an alert that fired.
* Weak projects share the same signs: secrets in Git, latest tags, no tests, no rollback, no numbers.
* Two minutes, six beats: problem, design, trade-offs, numbers, what broke, what you would change.
* A merged upstream PR, however small, is the strongest line on an early-career resume.

## Common mistakes

* Ten half-finished repos instead of two finished ones with numbers.
* A README that lists technologies ("Docker, Kubernetes, Terraform") without saying what the project does or what was measured.
* Copying a tutorial exactly, so the first "why did you choose X" question has no answer.
* Leaving the cluster running and paying for it, then having no cost number because the bill was a surprise.
* Presenting only successes; interviewers trust the candidate who describes the deploy loop they caused and how they found it.

## Practice

* Pick project 1 and finish it this week: a VM, HTTPS, a systemd unit and a pipeline. Record the by-hand deploy time and the pipeline deploy time in the README.
* Take any repository you already have and write its README in the skeleton from the worked example, with real measured numbers; run the comparison script on them.
* Record yourself presenting one project in two minutes, then answer three follow-up questions a friend asks. Cut anything that is not problem, design, trade-off, number, failure or change.
* Find one `good first issue` in a CNCF Go project, reproduce it locally, and post a comment with your reproduction before writing the fix.

## Interview questions (7)

1.Tell me about a project you built. You have two minutes.Easy

I built a CI/CD pipeline for a three-service monorepo. The problem was that every push rebuilt everything and took fourteen minutes, so people batched changes. The design: GitHub Actions with path-based change detection, a build matrix per changed service, Trivy scanning, cosign keyless signing, and a digest bump into a GitOps repo that Argo CD syncs. Trade-offs: path filters miss shared-library changes, so I map library paths to dependents; keyless signing needs the verify step to pin the OIDC issuer. Numbers: a one-service change went from 14 to 6 minutes and deploys rose from 3 to 14 a week. What broke: the digest-bump commit retriggered the pipeline in a loop; I fixed it with a path ignore and a bot identity. Next I would add a merge queue.

2.Why do you deploy by image digest instead of by tag?Medium

A tag is a mutable pointer: `api:1.4.2` can be re-pushed and point at different bytes tomorrow, and `latest` changes constantly, so a rollback by tag may not restore what was running. A digest is the content hash of the image; `api@sha256:...` is exactly one set of layers forever. Deploying by digest makes the GitOps repo a true record of what ran, makes rollback a revert, and is what the cosign signature actually covers, so the verify step at deploy time proves the exact image was signed by the pipeline. The cost is readability, which I solve by keeping the tag in a comment next to the digest.

3.What did your game day find, and what did you change afterwards?Medium

I added 500 ms of latency to the database connection with tc on the database pod. The fast-burn alert fired after about four minutes: with every request now over the 300 ms threshold the 1-hour window crosses 14.4x in about a minute, and the rest was scrape interval and the rule's `for` duration. Diagnosis took longer than I wanted: the RED dashboard showed duration up and errors flat, so it looked like the service itself; only the trace showed the time was inside the database span. Afterwards I added a dependency-latency row to the dashboard, a log line with the trace id on slow queries so Loki and Tempo link, and an action item to set a client-side timeout so slowness becomes a fast error rather than a pile-up. The postmortem is in the repo.

4.How does your operator avoid leaking objects when a WebApp is deleted?Medium

Every Deployment, Service and Ingress the controller creates gets an owner reference pointing at the WebApp, set with controllerutil.SetControllerReference. When the WebApp is deleted, the Kubernetes garbage collector deletes everything owned by it; the controller does not need to run. The envtest suite checks this: create a WebApp, assert the three objects exist, delete it, assert they are gone. For anything outside the cluster, say a DNS record, owner references cannot help, so I would add a finalizer that cleans up and then removes itself, and test that the object is not deleted while the finalizer is present.

5.How would you rebuild your platform from scratch if the cluster was lost?Medium

Everything is in two repositories. Terraform recreates the cluster, the node pool and the IAM pieces; that is one apply. Then I install Argo CD and apply the single app-of-apps Application; Argo CD pulls the rest from Git: ingress, cert-manager, external-secrets, Kyverno, and the team applications. Secrets come back from AWS Secrets Manager through external-secrets, so nothing secret was in the cluster alone. In my test the full rebuild to every application Healthy took under twenty minutes, and the only manual step was the Argo CD bootstrap. The thing that would not come back is stateful data, which is why the database lives outside the cluster or has Velero backups.

6.What is the smallest useful open source contribution, and how did you find yours?Easy

The smallest useful one fixes something a maintainer has already marked as wanted: a `good first issue` or `help wanted` label. I filtered a CNCF project's issues by those labels, picked one touching code rather than only docs, read the contributor guide, reproduced the bug locally, wrote a test that failed, fixed it, ran the project's own lint and test commands, and opened a PR that linked the issue and explained the change in three sentences. Then I answered review comments quickly. A typo fix counts but proves little; a test plus a fix proves you can work in a large Go codebase.

7.Your pipeline got faster but deploys went up fivefold. Why does that matter to a hiring manager?Hard

Because deploy frequency and lead time are two of the four DORA metrics, and they move together with change failure rate and time to restore when batches get smaller. A fourteen-minute pipeline made people bundle several changes into one deploy, so each failure was bigger and harder to bisect. At six minutes, people shipped one change at a time; failures were smaller, rollback was a one-commit revert, and time to restore fell from 48 to 9 minutes in my measurements. A hiring manager hears that I understand the pipeline is not the goal, the delivery performance is, and that I measured the thing that matters rather than only the thing I changed.

## Quiz

1.Which item makes a portfolio project credible in an interview?

2.In project 2, what does deploying by digest protect against?

3.What is the acceptance test for the canary in project 3?

4.Which alert design belongs in project 4?

5.What ensures the operator's child objects are removed when the WebApp is deleted?

## Practice these problems

* [DESIGNCI/CD pipeline for a 15-service monorepoHard](/devops/problems/monorepo-ci-pipeline)
* [DESIGNProduction EKS cluster for a 30-engineer startupHard](/devops/problems/eks-cluster-platform)
* [DESIGNObservability platform for 200 microservicesHard](/devops/problems/observability-platform)
* [DESIGNUptime monitoring service with global probes and alertingMedium](/devops/problems/uptime-monitoring-service)
* [CODEHelm chart from scratch with values, templates and a testMedium](/devops/problems/helm-chart-from-scratch)
* [CODEGo: a Kubernetes-style reconcile loop for a custom resourceHard](/devops/problems/go-reconcile-loop)

## Further reading

* [roadmap.sh DevOps projectsGuideroadmap.sh](https://roadmap.sh/devops/projects)
* [NotHarshhaa/DevOps-ProjectsArticlegithub.com](https://github.com/NotHarshhaa/DevOps-Projects)
* [techiescamp/devops-projectsArticlegithub.com](https://github.com/techiescamp/devops-projects)
* [The Kubebuilder BookGuidebook.kubebuilder.io](https://book.kubebuilder.io/)
* [DORA: Research (State of DevOps)Paperdora.dev](https://dora.dev/research/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousGPU and ML infrastructure - serving models on Kubernetes](/devops/learn/gpu-and-ml-infrastructure)

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

1. [How to pick a problem that is yours](#how-to-pick-a-problem-that-is-yours)
2. [Project 1: ship a service to a VM the manual way, then automate it](#project-1-ship-a-service-to-a-vm-the-manual-way-then-automate-it)
3. [Project 2: a complete CI/CD pipeline for a small monorepo](#project-2-a-complete-ci-cd-pipeline-for-a-small-monorepo)
4. [Project 3: a production-shaped Kubernetes platform](#project-3-a-production-shaped-kubernetes-platform)
5. [Project 4: an observability stack and a game day](#project-4-an-observability-stack-and-a-game-day)
6. [Project 5: a Kubernetes operator in Go, and a first open source PR](#project-5-a-kubernetes-operator-in-go-and-a-first-open-source-pr)
7. [Optional project 6: an uptime monitor](#optional-project-6-an-uptime-monitor)
8. [How to present a project in two minutes](#how-to-present-a-project-in-two-minutes)
