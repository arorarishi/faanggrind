# Tracing and observability for LLM applications — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/llm-observability

[AI problems](/ai#problems)

GENAIGenAI systems#17Medium

# Tracing and observability for LLM applications

tracingobservabilitycost accountingsamplingpii redactiononline evals

## Problem statement

A company runs 40 LLM features: chat, document Q&A and agents that call tools. Together they handle 10 million requests a day. When an answer is slow, wrong or expensive, engineers cannot say which step caused it, and finance cannot say which team spent the money. Design the tracing and monitoring platform: it records every request as a trace, accounts for tokens and cost, keeps personal data out of logs, checks quality on live traffic and raises the alerts that matter.

## Requirements

### Functional

* Record each request as a trace: a tree of spans, where a span is one timed step such as a model call, a retrieval, a tool call or a guardrail check.
* Attach tokens, cost, latency, model version and prompt version to every model call, and roll cost up by team, feature and user.
* Store prompts and outputs only after personal data is redacted, and only for a sample of traces.
* Search traces by feature, prompt version, model, status, latency or cost, and open one trace as a waterfall (its spans drawn on a timeline).
* Score a sample of live traffic with an LLM judge and attach user feedback to the same trace.
* Alert on quality, reliability, latency, cost and safety, grouped by feature and prompt version.

### Non-functional

* Tracing adds under 1 ms at p95 to a request, and the application keeps working when the trace backend is down.
* Ingest 3,700 spans per second at peak; a finished trace is searchable within 60 seconds.
* Reported cost matches the provider invoices within 1% per month.
* Redaction recall of at least 0.99 on emails, phone numbers and card numbers; payloads expire after 30 days.
* Trace lookup by id under 2 s; dashboard queries under 5 s.

## Back-of-the-envelope estimates

**Traces.** 10,000,000 requests/day / 86,400 = 116 traces per second on average. Plan for 4 times that at peak: 463 per second.

**Spans.** A trace averages 8 spans (root, guardrail, retrieval, 2 model calls, 2 tool calls, output check). 80 million spans/day, 926 per second on average and 3,700 at peak.

**Metadata.** 1 KB per span (ids, timings, token counts, attributes) = 80 GB/day. Assume a columnar store compresses this 8 times: 10 GB/day, 300 GB for 30 days. Small enough to keep for every span.

**Payloads.** One model call carries (3,000 input + 400 output tokens) x 4 bytes = 13.6 KB of text. Two calls plus 4.8 KB of retrieval and tool text = 32 KB per trace. For every trace: 10,000,000 x 32 KB = 320 GB/day. Too much, so sample.

**Sampled payloads.** Keep all flagged traces (errors, guardrail hits, thumbs-down, slowest, costliest), assumed 3% = 300,000. Keep 5% of the other 9,700,000 at random = 485,000. Total 785,000 x 32 KB = 25 GB/day, 6.3 GB after an assumed 4 times compression, 188 GB for 30 days. That is about 13 times less than keeping everything.

**Tail-sampling buffer.** 463 traces/s x 30 s x 32 KB = 444 MB in memory at peak.

**Spend being tracked.** At an assumed 1 USD and 5 USD per million tokens, one model call costs 0.003 + 0.002 = 0.005 USD, a trace with two calls 0.01 USD, a day 100,000 USD. A 1% accounting error is 1,000 USD a day.

**Online judge.** Judge 1% = 100,000 traces/day. Each call reads 3,500 tokens and writes 100, at an assumed 0.30 and 1.50 USD per million: 0.0012 USD, so 120 USD/day.

## API

```
SDK, inside the application:
  with tracer.span("llm.call", kind="llm") as span:
      span.set_attrs(model=..., prompt_id=..., prompt_version=...)
      span.set_io(prompt, output)        # redacted before it leaves the process
      span.set_usage(input_tokens, output_tokens, cached_tokens)
  The trace id travels to other services in a request header.

POST /v1/spans                           (batched, from SDK to collector)
  body: { spans: [{ trace_id, span_id, parent_span_id, name, kind,
                    start_ts, duration_ms, status, attrs, io? }] }

GET  /v1/traces/{trace_id}
GET  /v1/traces?feature=&prompt_version=&model=&status=&min_latency_ms=
                &min_cost_usd=&user_hash=&from=&to=
GET  /v1/metrics?name=cost_usd|ttft_ms|error_rate|judge_pass_rate
                &group_by=team,feature,model,prompt_version&window=
POST /v1/scores
  body: { trace_id, name, value, source: "judge" | "user" | "human",
          rubric_version }
PUT  /v1/alerts/{alert_id}
  body: { metric, group_by, condition, window, min_samples, notify }
DELETE /v1/users/{user_hash}/data        (erase one user's payloads)
```

## Data model

```
spans(trace_id, span_id, parent_span_id, name,
      kind,                       -- root | llm | retrieval | tool | guardrail
      start_ts, duration_ms, status, error_type,
      team, feature, env, user_hash, session_id,
      provider, model, prompt_id, prompt_version,
      input_tokens, output_tokens, cached_tokens, usage_estimated BOOL,
      cost_usd, ttft_ms, stop_reason, retries,
      tool_name, chunk_ids[], guardrail_verdict,
      payload_ref)                -- columnar store, partitioned by day

payloads(payload_ref PK, trace_id, user_hash, redacted_input,
         redacted_output, redaction_counts, keep_reason, expires_at)
         -- object store

prompt_versions(prompt_id, version, template_hash, template, team,
                deployed_at)
price_table(provider, model, valid_from, usd_in_per_m, usd_out_per_m,
            usd_cached_in_per_m)
scores(trace_id, span_id?, name, value, source, rubric_version,
       judge_model, created_at)
rollups_1m(minute, team, feature, model, prompt_version, requests, errors,
           input_tokens, output_tokens, cost_usd, ttft_p50, ttft_p95)
alerts(alert_id PK, metric, group_by, condition, window, min_samples, notify)
```

## High-level design

**Write path**

1. The SDK opens a root span for each request and a child span for every model call, retrieval, tool call and guardrail. The trace id is passed in a header, so spans from other services join the same tree.
2. The SDK puts finished spans in a bounded buffer. A background thread in the same process redacts prompt and output text and exports spans in batches. When the buffer is full the SDK drops spans and counts the drops. It never blocks the request.
3. A collector validates each span, runs a second redaction pass and computes `cost_usd` for model spans from the price table.
4. Spans go to a queue partitioned by trace id, so all spans of one trace reach the same consumer.
5. Three consumers read the queue. A writer stores the metadata of every span. A metrics job builds 1-minute rollups. A tail sampler waits until a trace has been quiet for 30 seconds, then decides whether to keep its payloads.

**Read path**

6. Judge workers take 1% of traces from the random sample, score them with a fixed rubric and write scores keyed by trace id. Thumbs up or down from users land in the same table.
7. The alert engine evaluates rules on rollups and scores every minute.
8. Engineers search traces, open the waterfall and compare prompt versions on dashboards. One click copies a bad trace into the offline golden set.

## Architecture diagram

Rendering diagram…

## Deep dives

### What a span carries, and prompt versions

Every span has a name, start time, duration, parent and status. A model span adds the provider, the model name the provider returned (not your alias), tokens, time to first token, stop reason and retries. A retrieval span adds chunk ids and scores. A tool span adds the tool name and status.

Store each prompt template once, keyed by its hash. The span carries only `prompt_id`, `prompt_version` and the variables. Now "pass rate, cost and latency by prompt version" is one query, and a bad prompt deploy shows up as a step in a chart.

### Token and cost accounting

Take token counts from the provider's response, not from your own tokenizer. In a stream they usually arrive at the end. If the stream is cancelled, estimate from the chunks seen and set `usage_estimated`. Cached input tokens have their own price, so they get their own column. Compute cost at ingest with the price valid on that day and store it on the span, so a later price change does not rewrite history. Count retries, failed calls, embeddings and judge calls too. Compare daily totals with the invoice; a gap above 1% is a bug.

### Sampling: all metadata, some payloads

Head sampling decides when a request starts. It is simple, but it throws away the rare failure before anyone knows it failed. Tail sampling decides after the trace ends. Keep metadata for every span, so cost and latency numbers are exact. Keep payloads for all flagged traces and for 5% at random. The random part matters: quality measured only on flagged traces looks far worse than it is.

### Redacting personal data

Redact twice. The SDK runs patterns and checksums for emails, phone numbers, card numbers and API keys on its background thread, before text leaves the process. The collector runs a named-entity model for names and addresses, off the request path. Values become typed placeholders such as `<EMAIL_1>`. User ids are stored as a keyed hash (a hash computed with a secret key): one user's traces can still be grouped and erased. Log tool arguments from an allow-list of fields. Send synthetic requests with fake card numbers and scan the store for them.

### Online quality checks and the alerts that matter

Judge traces from the random sample only. With 40 features, 100,000 judged traces a day is 2,500 per feature. At a 90% pass rate the 95% range is plus or minus 1.2 points per day, but plus or minus 5.8 points per hour (104 traces). So quality alerts use long windows and a minimum sample count.

Page on: error rate above 2% for 10 minutes, p95 time to first token over target for 10 minutes, tokens per request up 30% in a day, judge pass rate 5 points under its 7-day average, guardrail block rate doubling. Everything else is a dashboard.

## Evaluation

The platform is itself a product, so measure it.

**Coverage.** Share of production requests with a complete trace: a root span, every child present, no orphan spans (spans whose parent is missing). Target 99.5%. Count spans dropped by the SDK buffer.

**Overhead.** Load test one service with tracing on and off. Compare p95 latency and CPU. The target is under 1 ms added.

**Cost accuracy.** Each month, compare summed `cost_usd` with the provider invoices per provider and model. The target is within 1%. Track the share of spans with `usage_estimated`.

**Redaction.** A labelled set of 2,000 payloads with planted values. Report recall and precision per type; structured values must reach 0.99 recall. Names score lower, so report them separately. Synthetic values planted in live traffic must never appear in the payload store.

**Judge calibration.** For each rubric, 100 traces labelled by people. Report agreement, and agreement on the failing cases alone, because most traces pass. Repeat when the judge model or the rubric changes.

**Alert quality.** Run a drill: ship a deliberately worse prompt version to 5% of traffic and measure the time until an alert fires. Each month, count how many pages were real problems.

**Usefulness.** Time from a user complaint to the span that caused it. With a trace this should take minutes.

## Bottlenecks & mitigations

* The tail sampler must hold every open trace in memory (444 MB at peak for a 30-second window); long agent runs make the window and the memory grow.
* Payload volume: 320 GB a day before sampling, and model prompts keep getting longer.
* Queries over fields with millions of distinct values, such as cost per user over 30 days, scan billions of span rows unless they are pre-aggregated.
* The named-entity redaction pass is the slowest stage of ingest and sets how fast a trace becomes searchable.

## Failure modes

* **The trace backend is down or slow.** The SDK buffer fills. Mitigation: export in the background, bound the buffer, drop and count, and never fail a user request because of tracing.
* **Broken traces.** The trace id is lost across a queue or a background task, so spans appear as orphans. Mitigation: pass the context explicitly and alert on the orphan-span rate.
* **Personal data reaches the payload store.** A new field skips the redactor. Mitigation: two redaction passes, synthetic canary values, a 30-day expiry and erase-by-user-hash.
* **Cost numbers are wrong.** A price changed, or cancelled streams reported no usage. Mitigation: a dated price table, estimated usage with a flag, and reconciliation against the invoice.
* **Alert fatigue.** Hourly judge scores on 100 traces swing by several points. Mitigation: minimum sample counts, baselines from the last 7 days and one page per incident, not per feature.
* **Sampling hides a rare failure.** A bug hits 1 request in 10,000. Mitigation: tail rules keep every error and flagged trace, and metadata is kept for all spans.
* **The judge changes.** A new judge model scores differently and the chart shows a drop that never happened. Mitigation: pin the judge, store `rubric_version` and `judge_model` on each score, recalibrate before switching.

## Follow-up questions interviewers ask

* A user says yesterday's answer was wrong. Walk through how you find the cause from the trace.
* An agent run has 200 steps and lasts two hours. What changes in span design and tail sampling?
* The provider updates the model behind the same name. How would your data show it?
* Traffic grows 10 times. Which sampling rates and stores do you change first?
* A customer asks you to delete all their data. Which stores hold it and how do you erase it?
* Which three alerts would you page on at night, and which only go to a dashboard?

## Lessons that cover this

* [#16Evals, tracing and guardrailsShip](/ai/learn/evals-tracing-guardrails)

## Further reading

* [OpenTelemetry documentationGuideopentelemetry.io](https://opentelemetry.io/docs/)
* [Judging LLM-as-a-Judge with MT-Bench and Chatbot ArenaPaperarxiv.org](https://arxiv.org/abs/2306.05685)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousStructured data extraction from documents](/ai/problems/structured-extraction)[NextInsurance claims decision agent with RAG and a token budget](/ai/problems/claims-decision-agent)

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
