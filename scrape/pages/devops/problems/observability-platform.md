# Observability platform for 200 microservices — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/observability-platform

[DevOps problems](/devops#problems)

DESIGNPlatform design#5Hard

# Observability platform for 200 microservices

observabilityopentelemetryprometheusgrafanatracingslo

## Problem statement

A company runs 200 microservices on 3 EKS clusters, owned by 12 teams, serving 5,000 requests per second in total. Each team built its own dashboards with its own agent, metric names differ from service to service, and nobody can follow one slow checkout request across the 8 services it touches. Design one observability platform: how telemetry is produced, collected, stored and queried; how teams get dashboards and alerts without building them; and how the platform stays within a budget as 200 services grow to 400.

## Requirements

### Functional

* Every service emits metrics, logs and traces in one format (OpenTelemetry) with the same resource attributes: service name, team, cluster, environment, version.
* A request can be followed across services: one trace id in every log line and span, and a jump from a metric spike to example traces.
* Each team gets a Grafana folder with a generated RED dashboard (rate, errors, duration) per service and an alert route to their on-call rotation.
* SLOs are defined in Git as recording rules and burn-rate alerts, one file per service.
* All three clusters are queried from one Grafana; a team sees only its own logs and traces.
* Cardinality, log volume and trace sampling are enforced by the platform, not by goodwill.

### Non-functional

* Metrics queryable within 60 seconds of being scraped; dashboard p95 query time under 3 seconds for a 24-hour range.
* Retention: raw metrics 30 days, and 13 months for the small set of recording-rule aggregates (Mimir does not downsample raw blocks), logs 30 days, traces 7 days.
* Loss of one cluster's collectors or one availability zone drops no more than 5 minutes of telemetry from the other clusters.
* Platform cost under 5,000 USD per month at the stated load, excluding the Grafana licence if any.
* Active series capped at 2 million across all clusters; a single service cannot create more than 50,000.
* Alert delivered to the right team's pager within 2 minutes of the condition becoming true.

## Back-of-the-envelope estimates

**Series.** 200 services x 4 replicas = 800 application pods. A pod with the OpenTelemetry SDK exports about 1,500 series: an HTTP duration histogram with 15 buckets x 20 routes x 4 status classes alone is 1,200. 800 x 1,500 = 1.2 million. Infrastructure metrics (kube-state-metrics, node exporter, cAdvisor) add about 3,000 per node on 100 nodes = 300,000. Total 1.5 million active series, under the 2 million cap only if relabeling holds.

**Samples.** 1.5 million series scraped every 15 seconds = 100,000 samples per second. Prometheus stores an average of 1 to 2 bytes per sample. At 2 bytes: 200 KB per second, 17.3 GB per day, 518 GB for 30 days.

**Logs.** 5,000 requests per second x 2 log lines per request = 10,000 lines per second. At 300 bytes per line that is 3 MB per second, 259 GB per day raw. Loki compresses chunks about 8x (assumed), so 32 GB per day and about 970 GB for 30 days.

**Traces.** With 10 percent sampling, 500 traces per second x 12 spans x 500 bytes = 3 MB per second, 259 GB per day; 7 days is 1.8 TB raw, about 450 GB at an assumed 4x compression. Before sampling the gateway tier receives 60,000 spans per second. Tail sampling holds every trace for the 30-second decision window: 5,000 x 30 = 150,000 traces, about 0.9 GB of memory.

**Collector CPU.** Assume 10,000 spans per second per vCPU. The gateway needs 6 vCPU for spans plus 1 for logs; run 6 replicas of 2 vCPU across 3 clusters. Node agents at 0.2 vCPU x 100 nodes = 20 vCPU.

**Cost (assumed prices).** Mimir, Loki and Tempo on 8 m6i.2xlarge at 0.384 USD per hour: 8 x 0.384 x 730 = 2,243 USD. Agents 20 vCPU plus gateways 12 vCPU at 0.048 USD per vCPU-hour: 32 x 0.048 x 730 = 1,121 USD. S3 for 518 + 970 + 450 GB at 0.023 USD per GB: 45 USD. Total near 3,400 USD per month.

## API

```
How a team uses the platform (everything is a file in Git):

repo platform-observability/   (platform team)
  collectors/
    node-agent.yaml             OTel Collector DaemonSet: receivers otlp + filelog + kubeletstats
    gateway.yaml                OTel Collector Deployment: loadbalancing exporter by traceID,
                                tail_sampling, k8sattributes, memory_limiter, exporters to
                                Mimir, Loki, Tempo
  rules/<team>/<service>.yaml   SLO recording rules and burn-rate alerts (generated from slo.yaml)
  dashboards/                   RED dashboard template rendered per service by a job
  alertmanager/routes.yaml      route: match team=<team> -> receiver <team>-pager

repo <team>-services/<service>/
  observability/slo.yaml        service: checkout, team: payments
                                objective: 99.9, window: 30d
                                sli: http_server_request_duration_seconds, success: code!~"5.."
  deploy/values.yaml            podAnnotations for scrape; env OTEL_RESOURCE_ATTRIBUTES

Runtime contract for every pod:
  OTEL_EXPORTER_OTLP_ENDPOINT points at $(NODE_IP):4317   send to the node agent, not the gateway
  OTEL_RESOURCE_ATTRIBUTES=service.name=checkout,team=payments,deployment.environment=prod
  log lines are JSON with keys ts, level, msg, trace_id, span_id
  Java, Python, Node and .NET get auto-instrumentation from the OTel Operator (Instrumentation CR);
  Go services use the SDK directly

Query surfaces:
  Grafana  https://grafana.internal    folders: /payments, /search, ... ; SSO group -> folder editor
  Mimir    PromQL through Grafana; direct API only for the platform team
  Loki     {team="payments", service="checkout"} |= "trace_id=abc"
  Tempo    trace id lookup; TraceQL { resource.service.name="checkout" && duration > 2s }
```

## Data model

```
Per cluster (3 clusters: prod-a, prod-b, prod-c)
  namespace observability
    DaemonSet  otel-agent            1 per node, hostPort 4317/4318, 200m CPU / 512Mi
    Deployment otel-gateway          2 replicas, 2 CPU / 4Gi, tail_sampling decision_wait 30s
    Deployment prometheus-agent      scrapes /metrics every 15s, remote_write to Mimir,
                                     external_labels: cluster=prod-a
    kube-state-metrics, node-exporter

Central cluster (observability account)
  Mimir      distributor, ingester x3 (replication factor 3), store-gateway, compactor, querier
             tenant = team label; per-tenant limits: max_global_series_per_user 300000,
             ingestion_rate 20000 samples/s
  Loki       write and read paths, chunks in S3; tenant = team; per-tenant ingestion 5 MB/s
  Tempo      distributor, ingester, compactor; blocks in S3; retention 7d
  Grafana    data sources: Mimir, Loki, Tempo (with trace-to-logs and exemplars enabled)
             folders per team, Team sync from SSO groups
  Alertmanager  HA pair; routes by label team; receivers: PagerDuty per team, Slack per team

Required labels on every series (relabeling drops everything else at the agent):
  cluster, namespace, team, service, pod_template_hash is dropped, pod is dropped for app metrics
Allowed high-cardinality attributes: none. user_id, order_id, request_id are rejected
  by the attributes processor (action: delete) and allowed only on spans and logs.

S3 buckets: obs-mimir-blocks, obs-loki-chunks, obs-tempo-blocks
  lifecycle: raw metrics 30d (tenant retention); recording-rule aggregates written by the ruler
             to a separate long-term tenant with 400d retention; logs 30d; traces 7d
```

## High-level design

**Instrumentation (teams own this, with help)**

1. Install the OpenTelemetry Operator in each cluster and create one `Instrumentation` resource per language. A pod annotated with `instrumentation.opentelemetry.io/inject-java: "true"` gets the agent injected at admission; Go services add the SDK in code. Both read the same `OTEL_RESOURCE_ATTRIBUTES` so every signal carries service, team, cluster and version.
2. Make the logging library write JSON with `trace_id` and `span_id` taken from the active span context. This is the single most useful line in the whole design.

**Collection (platform team)**

3. Run an OpenTelemetry Collector as a DaemonSet. Pods send OTLP to the node's IP, so a gateway outage buffers locally and no pod needs to know a central address. The agent adds Kubernetes metadata with the `k8sattributes` processor, tails container logs with `filelog`, and forwards to the gateway.
4. Run a gateway Deployment per cluster in two tiers: tier one uses the `loadbalancing` exporter with `routing_key: traceID` so all spans of one trace land on the same tier-two collector, which runs `tail_sampling` and exports to Tempo. Logs go to Loki, metrics from the OTLP path to Mimir.
5. Run Prometheus in agent mode per cluster for pull-based `/metrics` scraping of infrastructure and legacy services, with `remote_write` to Mimir and `external_labels` for the cluster name.

**Storage and query**

6. Mimir for metrics, Loki for logs, Tempo for traces, all with S3 as the only durable store and a 3-way replicated ingest path. Tenancy is the `team` label: the gateway sets the `X-Scope-OrgID` header from it.
7. One Grafana with a folder per team, data sources with exemplars and trace-to-logs enabled, and a job that renders the RED dashboard for every service found in the service catalogue.

**Alerting and SLOs**

8. Each service has an `slo.yaml`; a CI job generates recording rules (`service:request_errors:ratio_rate5m`) and multi-window burn-rate alerts, and opens a PR to the rules repo. Alertmanager routes on the `team` label to that team's pager.

**Controls**

9. Relabeling at the agent enforces the allowed label list; Mimir per-tenant series limits reject the rest with a visible error. Loki per-tenant rate limits and Tempo per-tenant ingestion limits do the same for logs and traces.
10. A monthly cost report per team is itself a Grafana dashboard built from `cortex_ingester_active_series` and Loki `loki_distributor_bytes_received_total` by tenant.

## Architecture diagram

Rendering diagram…

## Deep dives

### Cardinality is the number one failure

A time series is one unique set of label values. Memory, index size and query cost in Prometheus and Mimir grow with the number of active series, not with the number of samples. One developer adding `user_id` to an HTTP counter with 100,000 users turns 1,200 series into 120 million and takes the ingester down for every team. The Monarch paper describes the same problem at Google and the same answer: schemas, fixed label sets and limits per user. The design enforces this in three layers. The agent's `attributes` processor deletes known-bad keys (`user_id`, `order_id`, `request_id`, raw URL paths) and `metric_relabel_configs` keep only the allowed list; a `path` label is only allowed after route templating, so `/orders/123` becomes `/orders/{id}`. Mimir's `max_global_series_per_user` rejects a tenant at 300,000 series with a 429 that shows up in the team's own dashboard, so the blast radius is one team. A weekly job lists the top 20 metrics by series count from the Mimir cardinality API and posts it to the team. Histograms deserve special attention: 15 buckets x routes x codes multiplies fast, and native histograms cut that to one series per route and code where the SDK supports them.

### Tail sampling versus head sampling

Head sampling decides at the start of a trace, in the first service, by rolling a dice on the trace id. It is cheap and needs no state, but it keeps 10 percent of boring requests and drops 90 percent of the failures you wanted. Tail sampling decides after the whole trace has arrived: keep every trace with an error status or latency over 2 seconds, keep 10 percent of the rest, and rate-limit any single service that floods. The cost is state: every span of a trace must reach the same collector, which is why tier one routes by trace id, and the collector holds traces in memory for `decision_wait` (30 seconds by default) with `num_traces` bounding memory. If a tier-two collector restarts, the traces in its buffer are lost; that is accepted and alerted on. Dapper used a low uniform head rate at Google scale and argued that was enough; at 5,000 requests per second, 10 percent is affordable and the error-biased tail policy is what makes traces useful on call.

### Keeping the three signals correlated

A trace is only useful if you can get to it from a metric and from a log. Three mechanisms do that. First, the logging library injects `trace_id` and `span_id` into every structured log line, and Loki's derived field turns that string into a link to Tempo. Second, exemplars: the OpenTelemetry SDK attaches the current trace id to histogram observations, Prometheus and Mimir store them next to the bucket, and Grafana shows them as dots on the latency panel, so a p99 spike is one click from a slow trace. Third, resource attributes are identical on all three signals, so `service.name` from a span selects the same service's logs and metrics. Context propagation across services uses the W3C `traceparent` header; a service that strips headers (a proxy, a queue consumer) breaks the chain, and the design requires the message broker client libraries to carry it in message metadata.

### Multi-cluster and multi-tenant isolation

Three clusters feed one storage backend. Each cluster's agent sets `cluster` as an external label so identical series from two clusters never collide. Tenancy is the `team` label mapped to `X-Scope-OrgID`: Mimir, Loki and Tempo store, limit and query per tenant, and Grafana data sources pass the header based on the user's SSO group, so the search team cannot read payments logs. Per-tenant limits turn a noisy team into a 429 for that team instead of an outage for all. The platform team queries across tenants through a federated tenant setting for global dashboards. Losing the central cluster stops queries but not collection: agents and gateways buffer for minutes, and Prometheus agent mode keeps its write-ahead log and replays on reconnect, so the 5-minute loss budget holds for short outages.

## Evaluation

**Platform SLIs.** Ingest freshness: time from scrape to queryable, target under 60 seconds at p99, measured by a canary series written with the current timestamp. Query latency: Grafana data-source p95 under 3 seconds for the generated RED dashboard at 24 hours. Alert delivery: synthetic alert rule that fires every hour and must reach a test pager within 2 minutes. Trace completeness: percentage of sampled traces with the expected root span, target above 99 percent. Collection availability per cluster: fraction of nodes whose agent exported in the last minute.

**Chaos tests.** Kill a tier-two gateway under load and measure spans lost. Partition one cluster from the central backend for 10 minutes and confirm the agent buffers and Prometheus agent WAL replay fill the gap. Push a service with a `user_id` label and confirm the agent drops it and the tenant limit holds. Delete the Mimir ingesters one at a time and confirm no sample loss with replication factor 3.

**Cost review.** Monthly series, log bytes and span counts per team from the backends' own metrics; alert when any tenant exceeds 70 percent of its limit; quarterly review of retention tiers against who actually queries old data (most logs older than 7 days are never read).

**Security checks.** No telemetry crosses tenants in a query test matrix of 12 teams; S3 buckets private with bucket policies; agents run without privileged mode except the `filelog` hostPath read; secrets for PagerDuty keys come from the secrets platform.

**Adoption.** 200 of 200 services with a generated RED dashboard, 150 with an `slo.yaml` in the first quarter, and the time to find the slow service in a cross-service incident measured in game days before and after.

## Bottlenecks & mitigations

* Mimir ingesters: memory grows with active series; one bad label set from one team hits the shared tier before per-tenant limits were tuned.
* Tier-two gateway memory during the tail-sampling window; a latency incident that makes every trace slow doubles the held spans.
* Loki ingestion rate per tenant when a service logs at debug level in production; the quota protects the backend but the team loses its own logs.
* Grafana as a single query front end: a dashboard with 40 panels over 30 days fans out to hundreds of store-gateway reads.
* S3 request costs from many small blocks if the compactor falls behind.

## Failure modes

* **A new label explodes series.** One deploy adds a user id to a counter. Mitigation: agent relabeling allow-list, per-tenant series limit, weekly top-20 cardinality report.
* **Trace spans split across collectors.** Tier one routes by service instead of trace id, so tail sampling sees partial traces and drops them. Mitigation: `routing_key: traceID`, trace completeness SLI.
* **Logs without trace ids.** A team uses a plain text logger. Mitigation: the logging library wrapper is part of the service template; a Loki query for lines missing `trace_id` by service is a dashboard panel.
* **Alert goes to nobody.** A service has no `team` label and the route falls to the default receiver. Mitigation: Kyverno requires the `team` label on every Deployment; the default receiver pages the platform team and is reported weekly.
* **Central backend down.** Collection continues, queries fail. Mitigation: agents buffer with `sending_queue` on disk, Prometheus agent WAL, runbook to query the per-cluster Prometheus agent's last 2 hours directly.
* **Retention costs balloon.** Someone sets trace sampling to 100 percent during an incident and forgets. Mitigation: sampling is a Git change with an expiry comment; cost dashboard alert at 70 percent of budget.
* **Clock skew breaks trace ordering.** Node clocks differ by seconds. Mitigation: chrony on every node, alert on `node_timex_offset_seconds`.

## Follow-up questions interviewers ask

* A team wants 1-second scrape resolution for a trading service. What does that cost and how do you isolate it?
* The company adds a fourth cluster in another region with 200 ms of latency to the backend. What changes?
* How would you add profiling (continuous CPU profiles) as a fourth signal?
* A regulator requires logs to be kept for 7 years. How do you change the retention tiers and the query path?
* Replace tail sampling with head sampling and explain exactly what you lose during an incident.
* How do you migrate 200 services from their existing StatsD and plain-text logs without a big bang?

## Lessons that cover this

* [#20Observability - Prometheus, Grafana, OpenTelemetry, logs and alertingOperate](/devops/learn/observability-prometheus-grafana-otel)
* [#21SRE practice - SLOs, error budgets, incidents and postmortemsOperate](/devops/learn/sre-slos-incidents-postmortems)
* [#26Open source - contributing to CNCF projects, LFX and GSoCContribute](/devops/learn/open-source-cncf-lfx-gsoc)
* [#31Projects - pipeline, cluster, observability, operatorLater](/devops/learn/projects)

## Further reading

* [OpenTelemetry documentationGuideopentelemetry.io](https://opentelemetry.io/docs/)
* [Dapper, a Large-Scale Distributed Systems Tracing InfrastructurePaperresearch.google](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/)
* [Monarch: Google's Planet-Scale In-Memory Time Series DatabasePaperresearch.google](https://research.google/pubs/monarch-googles-planet-scale-in-memory-time-series-database/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousProduction EKS cluster for a 30-engineer startup](/devops/problems/eks-cluster-platform)[NextSecrets management across CI, Kubernetes and runtime](/devops/problems/secrets-management)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [High-level design](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Evaluation](#evaluation)
10. [Bottlenecks](#bottlenecks)
11. [Failure modes](#failures)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
