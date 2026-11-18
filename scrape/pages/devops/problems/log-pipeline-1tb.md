# Log pipeline at 1 TB per day — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/log-pipeline-1tb

[DevOps problems](/devops#problems)

DESIGNPlatform design#11Medium

# Log pipeline at 1 TB per day

logginglokiopentelemetryfluent-bits3cost

## Problem statement

A company produces 1 TB of logs per day from 150 services on EKS and 200 EC2 instances. Engineers need 30 days of searchable logs and a 1-year archive for audit. A query over the last hour must return in under 5 seconds. The current self-managed ELK cluster costs more than the application servers it watches and still loses logs during traffic spikes. Design the pipeline from the application's print statement to the archive bucket: the log format, the agents, the buffer, the store, the tiers, retention, access control and cost controls.

## Requirements

### Functional

* Every service and host emits structured JSON logs with a fixed set of required fields; the pipeline rejects nothing but tags lines that break the standard.
* Logs are searchable by service, environment, namespace, level and free text for 30 days, and are restorable from the archive for 1 year.
* Each team sees only its own logs in Grafana; the platform team sees everything.
* Personal data (email addresses, phone numbers, card numbers, bearer tokens) is masked before it leaves the node.
* Alerts can be defined on log patterns (for example, more than 10 "payment declined" lines per minute per service).
* Debug-level logs can be sampled or dropped per service in production without a redeploy.

### Non-functional

* Ingest 1 TB per day sustained, with 3x peaks (35 MB per second) for 30 minutes without drops.
* A query over the last hour for one service returns in under 5 seconds at p95; a 7-day query returns in under 60 seconds.
* A backend outage of 1 hour loses no logs; a longer outage loses only debug-level lines first.
* Total monthly cost for the pipeline and storage under 5,000 USD, under half of the current ELK bill.
* End-to-end delay from print statement to searchable under 30 seconds at p99.
* The agent uses under 0.5 vCPU and 256 MiB on any node.

## Back-of-the-envelope estimates

**Rate.** 1 TB per day is 1,000,000,000,000 / 86,400 = 11.6 MB per second on average; with an assumed 3x peak, 35 MB per second. At an assumed 500 bytes per JSON line, 2 billion lines per day, or 23,000 lines per second.

**Compression.** JSON with repeated keys compresses well; assume 8x in Loki chunks. 1 TB per day becomes 125 GB per day stored. 30 days: 3.75 TB. One year: 365 x 125 GB = 45.6 TB.

**Storage cost.** 30 days in S3 Standard at an assumed 0.023 USD per GB-month: 3,750 x 0.023 = 86 USD. The other 335 days in Glacier Instant Retrieval at an assumed 0.004 USD: 41,875 x 0.004 = 168 USD. Storage is cheap; compute is the cost.

**Agents.** 60 EKS nodes plus 200 EC2 hosts = 260 agents. Each sees 11.6 MB / 260 = 45 KB per second on average, 134 KB at peak. A 1-hour outage needs 45 x 3,600 = 160 MB of disk buffer on average, 480 MB at peak, so 1 GB per node covers it. Assume JSON parsing costs 0.1 vCPU per MB per second: under 0.05 vCPU at peak; request 100m, limit 500m.

**Buffer.** Kinesis at 1 MB per second per shard needs 12 shards on average, 35 at peak; 35 shards at an assumed 0.015 USD per shard-hour is 383 USD per month.

**Compute, Loki.** 10 x m6i.2xlarge (an assumed 0.384 USD per hour): 10 x 0.384 x 730 = 2,803 USD. With S3, about 3,100 USD per month.

**Compute, OpenSearch.** Indexed JSON with one replica is about 2x raw on disk: 2 TB per day. 7 hot days = 14 TB at 70 percent fill = 20 TB: 3 x im4gn.4xlarge (7.5 TB NVMe, an assumed 1.37 USD per hour) = 3,000 USD, plus 46 TB warm at an assumed 0.024 USD per GB-month = 1,104 USD, warm nodes 347 USD, masters 298 USD: about 4,750 USD. All 30 days hot, as the current ELK does, needs 12 hot nodes: 12,000 USD.

## API

```
Log line standard (one JSON object per line on stdout, no multi-line):
  {"ts":"2026-11-03T10:15:42.123Z","level":"info","service":"checkout",
   "env":"prod","msg":"order placed","trace_id":"4bf9...","request_id":"a1b2",
   "user_id":"u_8831","duration_ms":42}
  required: ts (RFC 3339, UTC), level (debug|info|warn|error), service, env, msg
  optional: trace_id, request_id, any flat key; nested objects discouraged
  class label set by the agent: app | access | audit | debug

Agent (Fluent Bit DaemonSet on EKS, systemd unit on EC2):
  tail /var/log/containers/*.log  -> kubernetes filter adds namespace, pod, container
  parser json                     -> fields; lines that fail parsing get class=unparsed
  filter: redact PII, drop level=debug unless service has debug=on, sample
  output: Loki push over HTTPS, tenant header from namespace -> team mapping
  buffer: storage.type filesystem, 1 GB per node, oldest chunk dropped when full

Query (Grafana Explore, LogQL):
  {env="prod", service="checkout"} | json | level="error"         last 1 h
  {env="prod", namespace="payments"} |= "card declined" | json | duration_ms > 500
  sum by (service) (rate({env="prod"} | json | level="error" [5m]))

Alert (Loki ruler -> Alertmanager):
  expr: sum by (service) (count_over_time({env="prod"} | json | msg=~"payment declined.*" [1m])) > 10

Archive restore (platform team):
  aws s3 cp s3://logs-archive/loki/<tenant>/<date>/ ... ; replay into a restore tenant with retention 7d
```

## Data model

```
Loki (microservices mode, TSDB index, schema v13) on EKS, namespace "logging"
  distributor      x3   validates, rate-limits per tenant, hashes streams to ingesters
  ingester         x6   holds the last 1 to 2 h in memory and on local disk, flushes chunks to S3
  querier          x6   HPA 3..12, reads recent data from ingesters and old chunks from S3
  query-frontend   x2   splits a query by time, shards it, caches results
  compactor        x1   merges index files, applies retention, serves deletes
  ruler            x2   runs alert rules, sends to Alertmanager
  memcached        chunks 3 x 8 GiB, results 2 x 2 GiB, index 2 x 2 GiB
  S3 bucket logs-loki       chunks and index, SSE-KMS, versioning off
    lifecycle: STANDARD 0..30 d -> GLACIER_IR 30..365 d -> expire at 400 d
  S3 bucket logs-archive    audit class copies, Object Lock in compliance mode 365 d

Labels (indexed, low cardinality):   cluster, env, namespace, service, class, level
Structured metadata (not indexed):   pod, container, host, trace_id, request_id
Log line (JSON, parsed at query time): everything else
Streams: about 150 services x 4 levels x 4 classes = under 2,500 active streams

Tenants: one per team (X-Scope-OrgID = team name), set by the agent, never by the app
  limits per tenant: ingestion_rate_mb, max_global_streams_per_user, retention_period
  retention_stream:  class=debug 72h, class=app 720h, class=access 720h, class=audit 8760h
Grafana: one Loki data source per team with the tenant header; platform source with all tenants
```

## High-level design

**Format and agent**

1. Publish the JSON log standard with a library per language that sets `ts`, `level`, `service`, `env` and `trace_id` from the OpenTelemetry context, so logs join traces for free. Lines that are not JSON are wrapped as `{"msg": "<raw>"}` and tagged `class=unparsed`, which gives a dashboard of who is not compliant.
2. Run Fluent Bit as a DaemonSet on EKS and as a systemd service on EC2. It tails container logs, adds namespace, pod and container from the kubelet, parses JSON, masks PII with regex rules in a ConfigMap, drops `debug` for services not on the allow list, and maps namespace to team for the tenant header.
3. Turn on filesystem buffering: `storage.type filesystem` on the input, `storage.total_limit_size 1G` on the Loki output and `retry_limit false` so chunks wait on disk until the backend is back. When the disk limit is reached Fluent Bit discards the oldest chunk; a separate output for `class=audit` with its own limit means audit lines survive longest.

**Buffer decision**

4. Do not add Kafka or Kinesis in version one. Node disks already give a 1-hour buffer, Loki distributors accept writes directly, and 35 Kinesis shards would cost about 383 USD per month for no consumer that needs a stream. Revisit when a second consumer appears (a SIEM, a warehouse) or the required outage tolerance exceeds what node disks hold.

**Store and tiers**

5. Run Loki in microservices mode with S3 as the only long-term store. The hot tier is the ingesters' memory and local disk (last 1 to 2 hours), which is exactly what the 5-second last-hour query reads. The warm tier is S3 Standard with the TSDB index and chunk cache in memcached. The archive is an S3 lifecycle rule moving objects to Glacier Instant Retrieval after 30 days and expiring them after 400 days.
6. Set retention per log class with `retention_stream` rules: debug 3 days, app and access 30 days, audit 365 days. Copy `class=audit` chunks to a second bucket with Object Lock so nobody, including the platform team, can delete them early.

**Access, cost, alerting**

7. One Loki tenant per team. Each team's Grafana data source sends its own `X-Scope-OrgID`; the platform data source queries all tenants. Per-tenant limits (`ingestion_rate_mb`, `max_global_streams_per_user`, `retention_period`) are the quota system; a team over its rate sees 429s in its own dashboard rather than slowing everyone.
8. The Loki ruler evaluates LogQL metric rules and sends alerts to the existing Alertmanager. Teams add rules through the GitOps repo, at most 20 per tenant.
9. Publish a monthly cost report per tenant from bytes ingested, which Loki exposes as metrics, so every gigabyte has an owner.

## Architecture diagram

Rendering diagram…

## Deep dives

### Label design and cardinality in Loki

Loki indexes only labels; the log line itself is compressed and scanned at query time. Every unique combination of label values is a stream with its own chunks, so a high-cardinality label such as `request_id` turns one service's logs into millions of tiny streams, blows up the index and makes queries slower, not faster. The Loki docs' example of a `requestId` label with 24,653 values is exactly this mistake. The rule here: labels are things you filter on first and that have at most tens of values per service (`cluster`, `env`, `namespace`, `service`, `class`, `level`). Values that are high cardinality but still useful as filters (`pod`, `trace_id`, `request_id`) go in structured metadata, which the TSDB index with schema v13 stores alongside the line without indexing it, and which LogQL filters with `| trace_id="..."`. Everything else stays in the JSON line and is parsed with `| json` only when a query needs it. With this design the deployment has under 2,500 active streams, far below the 100,000 per-tenant guidance.

### Buffering and loss during backend outages

The honest answer to "what do we lose" is a ranked list, not "nothing". The agent's filesystem buffer holds one hour at peak on every node. If Loki is down longer, Fluent Bit drops the oldest chunks first. Because audit lines go through their own output with their own `storage.total_limit_size`, they are dropped last. Debug lines were never buffered at all in production unless a service turned them on. The remaining risk is a node dying with unsent chunks on its disk, which loses at most that node's share of one hour. Kafka would move that risk off the node at the cost of a cluster to run, and would still have a retention limit. For a team whose ELK loses logs on every spike, a node-local buffer with a clear priority order is a large step up at near zero cost; the design states the acceptable loss (debug first, then app, audit never within 24 hours) and measures it.

### PII and compliance

Masking must happen at the agent, before the line leaves the node, because every later hop (buffer, S3, Grafana, backups) becomes a copy of the data. Fluent Bit applies regex replacements for email addresses, 16-digit numbers, `Authorization: Bearer` values and known field names (`password`, `card_number`) and replaces them with `[redacted]`; the OpenTelemetry collector can do the same with its transform processor. Regex catches the common cases only; the second control is the logging library, which refuses to serialize fields on a deny list. The audit class gets a separate bucket with S3 Object Lock in compliance mode for 365 days, so a deletion request from a compromised account fails. Loki's compactor supports delete requests for the "delete this user's logs" case under privacy law, which is why the chosen store must support deletes by label and time range, not only retention by age.

### Cost per GB and where it goes

Storage is the small part: 3.75 TB hot plus 42 TB archived is about 250 USD per month; ingest and query compute is 10x that. The levers are fewer bytes and cheaper scans, not cheaper disks: drop debug in prod (often 40 to 60 percent of volume), sample noisy access logs at the agent, keep queries narrow with label selectors so the query frontend scans one service's chunks and not the whole hour, and cache chunks and results in memcached. OpenSearch is the other way round: the index is the product, so storage doubles and the hot nodes must hold whatever window you want to be fast. That is why the ELK bill at 30 hot days reached 12,000 USD and why Loki plus S3 lands near 3,100 USD, with the trade-off that a free-text search over 7 days of all services is slower on Loki.

## Evaluation

**Pipeline SLIs.** Ingest delay from stdout to searchable (target under 30 seconds at p99), measured by a canary pod that logs a timestamp every 10 seconds and a query that reads it back. Loss rate: Fluent Bit output retries and dropped chunks per node (target 0 dropped chunks per week outside declared outages). Query latency from Grafana for a last-hour, single-service query (target under 5 seconds at p95) and a 7-day query (under 60 seconds).

**Chaos tests before go-live.** Stop all ingesters for 45 minutes at peak load and confirm no lines are missing afterwards. Fill a node's buffer disk and confirm audit lines are the last to be dropped. Send a 10x burst from one tenant and confirm it receives 429s while other tenants are unaffected. Delete the memcached pods during a 7-day query and confirm it completes, slower.

**Cost review.** Monthly bytes ingested per tenant from Loki's distributor metrics, compared with the quota; the top 5 streams by bytes; the share of debug lines in prod (target under 5 percent). Alert when the S3 lifecycle rule stops moving objects or when the compactor has not run for 24 hours.

**Security checks.** A weekly job pushes 100 synthetic lines containing fake emails, card numbers and bearer tokens, then queries for them; any hit is a failed check. Object Lock status on the audit bucket, IAM access to the buckets limited to the Loki role and the restore role, Grafana data sources verified to carry the right tenant header.

**Adoption.** Share of lines tagged `class=unparsed` per team (target under 1 percent after one quarter), and the number of teams with at least one log-based alert.

## Bottlenecks & mitigations

* The ingester ring: a stream is owned by a few ingesters, so one very hot stream (a service logging 5 MB per second) hits per-stream rate limits; shard it with an extra label or raise `per_stream_rate_limit` for that tenant.
* The query frontend serialises large queries into many sub-queries; a 7-day free-text search over all services scans every chunk and needs enough queriers, which is what the HPA is for.
* The Fluent Bit kubelet lookup adds latency and API load on nodes with hundreds of pods; use the kubelet endpoint rather than the API server.
* S3 request costs: millions of small chunk reads per day from queriers; the chunk cache and larger chunk target sizes keep this down.
* One compactor instance: if it falls behind, retention and deletes stop; alert on its last-run age.

## Failure modes

* **Someone adds `request_id` as a label.** Streams explode, the index grows, writes get slower for every tenant. Mitigation: `max_label_names_per_series` and a stream limit per tenant, plus a weekly `logcli series --analyze-labels` report.
* **Loki is down for 3 hours.** Node buffers fill after one hour and drop the oldest chunks. Mitigation: priority outputs so audit lines survive; alert at 50 percent buffer fill so the on-call engineer knows what is being lost.
* **A deploy switches a service to multi-line stack traces.** Lines fail to parse and arrive as `unparsed`, searchable only by text. Mitigation: the standard requires single-line JSON; the unparsed dashboard shows it within minutes.
* **PII regex misses a new field.** Personal data lands in S3. Mitigation: the synthetic-PII weekly check, the library deny list, and the compactor delete API to purge by time range.
* **One team's burst starves the others.** Mitigation: per-tenant ingestion limits at the distributor; the burst gets 429s, which Fluent Bit retries from disk.
* **Archive lifecycle rule points at the wrong prefix.** Hot data is moved to Glacier early or never expires, and the bill climbs. Mitigation: Terraform-managed lifecycle rules with a test that lists object storage classes by age.
* **Grafana data source with the wrong tenant header.** A team sees another team's logs. Mitigation: data sources created by Terraform from the team list; a daily check queries each source for a canary line owned by another tenant and expects zero results.

## Follow-up questions interviewers ask

* A SIEM team now needs a copy of every audit line in near real time. Where does Kafka fit, and what changes at the agent?
* Volume grows to 10 TB per day. What breaks first in this design and what would you change?
* A legal request asks you to delete every log line for one user across 30 days. Walk through it.
* Would you move the agent to the OpenTelemetry collector? What do you gain and what do you lose against Fluent Bit?
* Loki's free-text search over 7 days is too slow for the security team. What are your options short of switching to OpenSearch?
* How do you prove to an auditor that audit logs were not altered?

## Lessons that cover this

* [#20Observability - Prometheus, Grafana, OpenTelemetry, logs and alertingOperate](/devops/learn/observability-prometheus-grafana-otel)
* [#27Cloud cost and FinOpsShip](/devops/learn/cloud-cost-and-finops)

## Further reading

* [Grafana Loki documentationGuidegrafana.com](https://grafana.com/docs/loki/latest/)
* [OpenTelemetry documentationGuideopentelemetry.io](https://opentelemetry.io/docs/)
* [The Twelve-Factor AppPaper12factor.net](https://12factor.net/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousGitOps deployment platform with Argo CD for 50 teams](/devops/problems/gitops-platform-argocd)[NextSLO-based alerting and on-call system](/devops/problems/slo-alerting-oncall)

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
