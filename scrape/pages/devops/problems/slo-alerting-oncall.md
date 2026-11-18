# SLO-based alerting and on-call system — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/slo-alerting-oncall

[DevOps problems](/devops#problems)

DESIGNPlatform design#12Medium

# SLO-based alerting and on-call system

sloalertingprometheusalertmanageron-callsre

## Problem statement

A team of 12 engineers runs 20 services on EKS behind an Envoy Gateway (Gateway API) ingress. Their Prometheus sends about 300 alerts a week, most of them CPU, memory and "pod restarted" noise, and in the last quarter two real outages were noticed by customers first. Nobody wants to be on call. Design SLOs, an alerting system and an on-call rotation so that pages mean something, real outages are caught in minutes, and the alert count drops from 300 a week to under 20.

## Requirements

### Functional

* Every service has an availability SLI and a latency SLI measured at the edge, an SLO target tied to its tier, and a documented error budget policy.
* Pages fire only when the error budget is burning fast enough to matter; slow burns open tickets.
* Every alert carries a runbook link, the affected service, the owning team and the current burn rate.
* An on-call rotation covers 24x7 with a primary, a secondary and an escalation path, and every handoff is written down.
* A weekly review deletes or downgrades alerts that did not lead to action.
* Error budget dashboards and a public status page show the state of each service.

### Non-functional

* A full outage of a tier-1 service pages within 5 minutes; a 10 percent error rate pages within 15 minutes.
* Fewer than 20 alerts per week across all 20 services, and fewer than 2 pages per engineer per on-call week on average.
* Fewer than 5 percent of pages are judged "not actionable" at the weekly review.
* Each engineer is on call at most one week in six as primary.
* Alert evaluation adds under 2 seconds of delay; Alertmanager delivers a page within 60 seconds of the rule firing.
* The alerting stack itself has a dead-man's switch that notifies within 10 minutes if Prometheus or Alertmanager stops.

## Back-of-the-envelope estimates

**Budget.** A 99.9 percent monthly SLO at 2,000,000 requests per day: 60,000,000 requests in 30 days, so 0.1 percent = 60,000 allowed bad requests per month, 2,000 per day, 83 per hour. In time, 0.1 percent of 30 days = 43.2 minutes of full outage.

**Burn rates that page.** Burn rate 1 means the budget runs out in exactly 30 days (720 hours). Time to exhaustion = 720 / burn rate. The workbook's table for a 99.9 percent SLO: burn rate 14.4 over 1 hour consumes 14.4 x 1 / 720 = 2 percent of the budget, exhausts it in 50 hours, and pages. Burn rate 6 over 6 hours consumes 6 x 6 / 720 = 5 percent, exhausts it in 5 days, and pages. Burn rate 1 over 3 days consumes 72 / 720 = 10 percent and opens a ticket. In error rates: 14.4 x 0.1 percent = 1.44 percent of requests failing, 6 x 0.1 = 0.6 percent, and 0.1 percent.

**Worked numbers.** 2,000,000 per day is 83,333 requests per hour, so the 1-hour page needs about 1,200 errors in an hour and the 5-minute short window about 100 errors in 6,944 requests. The 6-hour page needs 3,000 errors in 500,000. A full outage produces 83,333 errors per hour, about 69x the threshold, so the alert fires as soon as the `for` duration (2 minutes) passes.

**Pages per month.** A service inside its budget burns at rate 1 or less on average, which never pages. An incident that pages at 14.4 for an hour costs 2 percent of budget, so 50 would exhaust it; a healthy service that spends a third of its budget on incidents sees at most 15 such events a month, in practice 0 to 2.

**Alert volume.** 20 services x 2 SLIs x 3 windows = 120 rules, firing only on real burn: a target of under 20 alerts per week, under 8 of them pages, is about 1 page per on-call engineer per week.

## API

```
SLO definition, one file per service in repo platform-slo/ (rendered into Prometheus rules by CI):
  service: checkout
  tier: 1                         # tier 1: 99.9 availability, p99 latency < 500 ms
  owner: team-payments            # Alertmanager routes by this label
  slis:
    availability:
      good:  sum(rate(envoy_cluster_upstream_rq_xx{envoy_cluster_name=~".*checkout.*", envoy_response_code_class!="5"}[5m]))
      total: sum(rate(envoy_cluster_upstream_rq_completed{envoy_cluster_name=~".*checkout.*"}[5m]))
    latency:
      good:  sum(rate(envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name=~".*checkout.*", le="500"}[5m]))   # Envoy histograms are in ms
      total: sum(rate(envoy_cluster_upstream_rq_time_count{envoy_cluster_name=~".*checkout.*"}[5m]))
  objective: 99.9
  window: 30d
  runbook: https://runbooks.internal/checkout

Generated recording rules (per service, per SLI, per window):
  slo:sli_error:ratio_rate5m   slo:sli_error:ratio_rate30m   slo:sli_error:ratio_rate1h
  slo:sli_error:ratio_rate6h   slo:sli_error:ratio_rate3d
  slo:error_budget:remaining   = 1 - (errors over 30d) / (allowed errors over 30d)

Generated alerts (labels: service, team, severity, slo):
  <Service>HighBurnRate   severity=page    14.4x over 1h and 5m  OR  6x over 6h and 30m
  <Service>SlowBurnRate   severity=ticket  1x over 3d and 6h
  annotations: summary, runbook_url, dashboard_url, burn_rate ({{ $value }})

Alertmanager routing:
  severity=page   -> paging product, escalation policy of the owning team, group_by [service]
  severity=ticket -> ticket tracker, one ticket per service per day
  Watchdog alert always firing -> dead-man's switch in the paging product

On-call: primary + secondary, weekly, handoff Tuesday 11:00 local, escalation after 15 min no-ack
```

## Data model

```
Service tiers and targets (chosen from 90 days of history, see deep dive)
  tier 1  checkout, auth, api-gateway        99.9  avail, p99 < 500 ms   budget 43 min / 30 d
  tier 2  search, catalog, notifications     99.5                        budget 3.6 h / 30 d
  tier 3  admin, reporting, batch endpoints  99.0                        budget 7.2 h / 30 d

Prometheus (kube-prometheus-stack), 2 replicas, 30 d local retention, 15 s scrape
  rule groups: slo-recording (every 30 s), slo-alerts (every 30 s), platform-alerts
  alert labels:   service, team, tier, severity (page|ticket), slo (availability|latency)
  annotations:    summary, description, runbook_url, dashboard_url

Alertmanager, 3 replicas in a cluster
  route tree:
    root receiver ticket-tracker, group_by [service, alertname], group_wait 30s,
         group_interval 5m, repeat_interval 4h
    route severity=page   -> receiver pager-<team> (matched on team label), repeat_interval 1h
    route alertname=Watchdog -> receiver deadman, repeat_interval 1m
  inhibit_rules:
    source severity=page, target severity=ticket, equal [service]
    source alertname=ClusterDown, target any, equal [cluster]

Paging product (by category: on-call scheduling and paging SaaS)
  schedule per team: primary weekly, secondary weekly, offset by half a rotation
  escalation: primary 0 min -> secondary 15 min -> engineering manager 30 min
  override: any engineer can take a shift via the app; handoff note required

Error budget policy (one page, signed by product and engineering)
  budget > 50 % left:  normal releases
  budget 0..50 %:      releases need a reviewer from on-call; feature flags default off
  budget exhausted:    only reliability work and fixes until the 30 d window recovers

Status page: one component per tier-1 service, state driven by the page alert for that service
```

## High-level design

**Measure**

1. Measure SLIs at the gateway, not inside the service. The Envoy metrics (`envoy_cluster_upstream_rq_xx` by response code class and the `envoy_cluster_upstream_rq_time` histogram, one Envoy cluster per backend Service) see what the user sees, including the service being down, which a self-reported metric cannot. For services with no HTTP edge (a queue worker), the SLI is "jobs finished within deadline" from the worker's own metric, with a freshness check.
2. Pick targets from 90 days of history: the availability each service actually delivered at p95 of weekly values, rounded down to a tier. A service that delivered 99.95 percent gets 99.9, not 99.99.
3. Write recording rules for the error ratio at 5m, 30m, 1h, 6h and 3d, so alert expressions are cheap and dashboards use the same series.

**Alert**

4. Generate the three multi-window multi-burn-rate rules per SLI from the SLO file in CI. Page on 14.4x (1h and 5m) or 6x (6h and 30m); ticket on 1x (3d and 6h). The short window is one twelfth of the long one, so an alert stops firing minutes after the problem stops.
5. Delete the cause-based alerts (CPU over 80 percent, pod restarts, disk at 70 percent) as pages. Keep a few as tickets where they predict a future SLO breach (disk full in 24 hours, certificate expiring in 7 days) and leave the rest as dashboard panels.
6. Route in Alertmanager by `severity` and `team`. Group by service so one incident is one page. Inhibit tickets while a page is open for the same service, and inhibit everything while a `ClusterDown` alert fires.
7. Every alert's annotation holds `runbook_url` and `dashboard_url`; CI rejects a rule without them.

**Operate**

8. Rotation: 12 engineers, primary and secondary, weekly, so each engineer is primary one week in six and secondary one week in six. One time zone, so no follow-the-sun; nights are covered by the primary with a 15-minute escalation to the secondary. Handoff is a written note with open incidents and budget state.
9. Declare an incident when a page is acknowledged and not resolved in 30 minutes, or when two tier-1 services page at once; the on-call engineer becomes incident commander until relieved.
10. Weekly 30-minute alert review: every alert from the week is labelled actionable, noisy or missed; noisy ones are deleted or downgraded in the same meeting through a PR.
11. Dashboards per service show remaining budget, burn rate at each window and the page thresholds as lines; the status page flips a component to degraded when the page alert for it fires.

## Architecture diagram

Rendering diagram…

## Deep dives

### Symptom alerts versus cause alerts

A cause alert says "CPU is at 90 percent"; a symptom alert says "users are getting errors". The 300 weekly alerts are almost all causes, and causes have two problems: they fire when nothing is wrong (a batch job uses the CPU it was given) and they stay silent when something is wrong for a reason nobody wrote a rule for. A symptom alert at the edge catches every cause, including the ones not yet imagined, and only when a user is affected. Cause signals move to the dashboard the on-call engineer opens from the runbook link, where they explain the symptom instead of interrupting someone. The few that remain are predictive: a disk that fills in 24 hours, a certificate that expires in a week. Those are tickets, because nobody needs to wake up for them.

### Burn-rate math with a worked example

Burn rate is how fast the service spends its error budget relative to the SLO: at burn rate 1 a 30-day budget lasts 30 days; at 2, 15 days; at 10, 3 days; at 1,000, 43 minutes. The error-rate threshold for an alert is `burn_rate x (1 - SLO)`. For checkout at 99.9 percent, the page rule is:

```
(
  slo:sli_error:ratio_rate1h{service="checkout"} > (14.4 * 0.001)
  and
  slo:sli_error:ratio_rate5m{service="checkout"} > (14.4 * 0.001)
)
or
(
  slo:sli_error:ratio_rate6h{service="checkout"} > (6 * 0.001)
  and
  slo:sli_error:ratio_rate30m{service="checkout"} > (6 * 0.001)
)
```

Walk through a deploy that breaks 5 percent of requests at 14:00. The 5-minute ratio passes 1.44 percent by 14:01. The 1-hour ratio is a moving average, so it reaches 1.44 percent when about 17 minutes of 5 percent errors are in the window (17 / 60 x 5 = 1.4). The page fires at about 14:17, having spent 17 x 83,333 / 60 x 0.05 = 1,180 bad requests, 2 percent of the monthly budget. After a rollback at 14:25 the 5-minute window clears by 14:30 and the alert stops, although the 1-hour window stays above threshold until about 15:08; without the short window the pager would ring for 40 minutes after the fix. A full outage crosses the 1-hour threshold in 52 seconds (1.44 percent of an hour), so detection is limited by the `for` duration and scrape interval, 2 to 3 minutes.

### Choosing SLO targets honestly from historical data

The temptation is to write 99.99 percent because it sounds serious. Then the budget is 4.3 minutes per month, one bad deploy exhausts it, nobody stops releasing, and the SLO becomes a number on a slide. The honest method: compute the SLI for each of the last 13 weeks, take the value the service met in 12 of them, and round down to the nearest tier. If checkout met 99.9 in 12 of 13 weeks, the target is 99.9. A target below what users need is a product conversation about investment; a target above what the system delivers is a lie. Move targets up only after the system has beaten the current one for a full quarter. Latency SLOs follow the same rule on the ingress p99.

### On-call health metrics

The system is working when the people on call say so, and that is measured. Track pages per shift (target under 2), pages outside working hours per shift (under 1), time to acknowledge (p90 under 5 minutes), and the actionable rate from the weekly review (over 95 percent). Track swapped or skipped shifts; a rising number means the rotation is hurting. If pages per shift stay above 2 for a month, the fix is engineering work paid from the error budget policy, not a bigger rotation. Publish these numbers next to the SLOs so service reliability and team health are reviewed together.

## Evaluation

**Alerting SLIs.** Time from injected failure to page (target under 5 minutes for a full outage, under 15 minutes for a 10 percent error rate), measured monthly by a drill that returns 500s from a canary service through the real ingress. Alert precision: share of pages labelled actionable in the weekly review (target over 95 percent). Alert recall: customer-reported incidents with no page (target 0 per quarter). Alerts per week (target under 20) and pages per on-call shift (target under 2).

**Chaos tests before go-live.** Kill all pods of a tier-1 service and time the page. Add 600 ms of latency to one service and confirm the latency SLO pages and the availability SLO does not. Stop Alertmanager and confirm the dead-man's switch fires within 10 minutes. Fire 50 alerts for one service at once and confirm one page arrives, grouped. Page the primary, do not acknowledge, and confirm the secondary is paged at 15 minutes.

**Cost review.** Prometheus series count per rule group (recording rules for 20 services at 5 windows x 2 SLIs is 200 series, trivial); paging product seats (12) and the per-page cost, if any; engineer hours in the weekly review (30 minutes x 12 is the budget).

**Security checks.** Alert annotations contain no secrets or user data; runbook links require SSO; the paging product's webhook from Alertmanager uses a per-team token rotated quarterly; the status page is driven only by the page alert, so a human cannot set "all good" while an alert fires.

**Weak versus strong answer.** A weak answer adds more alerts with better thresholds. A strong answer deletes most of them, pages only on budget burn with two windows, explains why 14.4 and why 1/12, and designs the review that keeps the alert set small.

## Bottlenecks & mitigations

* The gateway is the single measuring point; if a service is reached through another path (gRPC over an internal load balancer) its SLI is missing until a second source is added.
* A 3-day recording rule window makes Prometheus read 3 days of samples each evaluation; use recording rules on recording rules, and a 30-second evaluation interval, not 15.
* Alertmanager grouping by service hides a cluster-wide incident as 20 separate pages unless a `ClusterDown` inhibitor exists.
* The weekly review needs a person with authority to delete alerts; without it the count climbs back.
* Low-traffic services (under 10 requests per minute) produce noisy ratios in a 5-minute window; use longer short windows or a minimum request count in the expression.

## Failure modes

* **Prometheus restarts and loses the 1-hour window.** The page rule sees no data and goes silent. Mitigation: two Prometheus replicas, Alertmanager deduplicates; the Watchdog alert from each replica feeds the dead-man's switch.
* **Deploy introduces errors only for 1 percent of users.** Burn rate is 10x, below the 14.4 page but above the 6x 6-hour page; it pages after about 3.6 hours (0.6 percent of a 6-hour window at 1 percent errors) and 5 percent of budget. Mitigation: that is the design; the slow-burn page catches it, and canary analysis in the deploy pipeline catches it earlier.
* **Ingress counts a client's 4xx storm as fine while the backend is down.** 5xx-based availability misses it. Mitigation: a separate black-box probe SLI (synthetic request every 30 seconds) for tier-1 services.
* **Error budget policy ignored by product.** Releases continue with the budget exhausted and the SLO loses meaning. Mitigation: the policy is signed by product and engineering, and the release pipeline reads the remaining budget and requires an override approval below zero.
* **Pager fatigue from a flapping alert.** An alert just at threshold fires and resolves every few minutes. Mitigation: `for: 2m` plus `keep_firing_for: 10m`, and the short window keeps resets quick but not instant.
* **On-call engineer cannot reach the runbook.** SSO is down with the outage. Mitigation: runbooks mirrored in the repository and in the paging product's notes.
* **Alertmanager cluster splits.** Duplicate pages or missed inhibitions. Mitigation: 3 replicas with gossip across zones, and the drill that checks a page arrives exactly once.

## Follow-up questions interviewers ask

* A new service has 50 requests per hour. How do you alert on its SLO without constant false pages?
* The company opens an office in another time zone. Redesign the rotation as follow-the-sun and state the handoff rules.
* How would you alert on a latency SLO when the ingress histogram buckets do not include your threshold?
* Product asks for 99.99 percent on checkout. What do you need to change in architecture and process, and what does it cost?
* Design the weekly review so that it still happens in six months. What is on the agenda and who can delete an alert?
* Would you buy an SLO product or generate rules from a YAML file in CI? What does each give you?

## Lessons that cover this

* [#1DevOps, SRE and platform engineering - how software reaches productionFoundations](/devops/learn/devops-sre-platform-engineering)
* [#20Observability - Prometheus, Grafana, OpenTelemetry, logs and alertingOperate](/devops/learn/observability-prometheus-grafana-otel)
* [#21SRE practice - SLOs, error budgets, incidents and postmortemsOperate](/devops/learn/sre-slos-incidents-postmortems)
* [#28Interview playbook, what is new in 2026, revision sheetShip](/devops/learn/interview-playbook-2026-revision)

## Further reading

* [Google SRE Workbook: Chapter 5 - Alerting on SLOsArticlesre.google](https://sre.google/workbook/alerting-on-slos/)
* [Google SRE Book: Chapter 4 - Service Level ObjectivesArticlesre.google](https://sre.google/sre-book/service-level-objectives/)
* [Prometheus: alerting rulesGuideprometheus.io](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousLog pipeline at 1 TB per day](/devops/problems/log-pipeline-1tb)[NextSecure container image pipeline: build, scan, sign, SBOM, admission](/devops/problems/supply-chain-image-pipeline)

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
