# Guardrails and PII redaction layer — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/guardrails-pii-redaction

[AI problems](/ai#problems)

GENAIGenAI systems#15Medium

# Guardrails and PII redaction layer

guardrailspiisafety classifierstreamingpolicyaudit logReported at OpenAI, Anthropic, Google

## Problem statement

Design the guardrail layer that sits between users and the LLM for a consumer company with three chat products: a general assistant, a homework helper for teenagers and a support bot. Together they handle 40 million messages a day. The layer masks personal data (PII) before it reaches the model or the logs, blocks unsafe and off-topic requests, checks the answer while it streams, and lets each product set its own policy. Users should not feel the delay.

## Requirements

### Functional

* Detect PII in each user message and replace every value with a typed placeholder that can be restored in the reply.
* Score each input for safety categories (self-harm, sexual content, violence, hate, prompt injection) and for off-topic requests, then act as the product's policy says.
* Check the model's output while it streams, and stop or replace an answer that fails.
* Store one policy per product: categories, thresholds, actions, PII types and stream mode, versioned and changeable without a deploy.
* Write an audit event for every verdict, with scores and versions and no raw PII.
* Let users report a wrong block, and feed those reports into labelling.

### Non-functional

* Input checks add under 40 ms at p95 before the model call.
* Output checks delay the first visible text by under 350 ms in strict mode and by 0 ms in optimistic mode.
* 40 million messages a day: 463 per second on average, 1,389 at peak.
* PII recall of at least 99% for structured types (card, phone, email, national id) and 95% for names and addresses.
* Safety: at least 90% recall per category with under 0.2% of normal messages blocked.
* Guardrail compute under 1% of LLM spend; a policy change is live within 60 seconds.

## Back-of-the-envelope estimates

**Traffic.** 5 million daily users x 8 messages = 40 million messages/day: 463 per second on average and 1,389 at a 3x peak.

**Input checks.** A message averages 120 tokens. A small encoder model on one GPU handles an assumed 48,000 tokens per second, so 400 messages per second. Peak needs 1,389 / 400 = 3.5, so 4 GPUs for the name-and-address model and 4 for the safety classifier.

**Output checks.** An answer averages 300 tokens. One check every 50 tokens, reading the last 100: 6 checks per answer, 240 million a day, 8,333 per second at peak. A GPU does 48,000 / 100 = 480 checks per second, so 18 GPUs.

**Cost.** 26 GPUs x 24 h x an assumed 1.5 USD per GPU-hour = 936 USD/day. The LLM uses 1,500 input and 300 output tokens per message. At an assumed 1 and 5 USD per million that is 0.0030 USD per message, 120,000 USD/day. The guardrails add 0.78%.

**Errors at one threshold.** Assume 0.5% of messages break policy: 200,000 a day. At 90% recall, 180,000 are caught and 20,000 are missed. A 0.2% false-block rate on 40 million is about 80,000 normal messages blocked. Precision is 180,000 / 260,000 = 69%, so about 1 block in 3 hits an innocent user.

**Grey band.** Send the 1% of messages with middle scores to a larger model: 400,000 a day, 4.6 per second. At 600 tokens each and an assumed 1 USD per million, that is 240 USD/day.

**Storage.** 8% of messages hold PII, 1.5 values each: 4.8 million vault entries a day x 200 bytes = 0.96 GB, 29 GB for 30 days. Audit: 2 events per message (one input verdict, one output verdict) = 80 million events x 300 bytes = 24 GB/day, 2.16 TB for 90 days.

## API

```
POST /v1/guard/input
  body: { product_id, conversation_id, message_id, text, locale }
  resp: { action: "allow" | "block" | "safe_reply" | "redirect"
                  | "second_check",
          masked_text,
          entities: [{ type, placeholder, start, end }],
          verdicts: [{ category, score, low, high }],
          policy_version, latency_ms }

STREAM /v1/guard/output/{message_id}
  in:   model tokens
  out:  { event: "release", text }            (placeholders restored)
        { event: "retract", category, fallback_text }

PUT  /admin/policies/{product_id}             (new version, reviewed)
POST /admin/policies/{product_id}/replay
  body: { candidate_policy, from, to }
  resp: { blocks_now, blocks_candidate, changed_examples[] }

GET  /admin/audit?product_id=&category=&action=&from=&to=
POST /v1/guard/reports   { message_id, reason: "wrong_block" }
```

## Data model

```
policies(product_id, version, created_by, live_from,
  pii:        { CARD: "mask", PHONE: "mask", EMAIL: "mask",
                NATIONAL_ID: "mask", PERSON: "mask", PINCODE: "pass" },
  categories: { self_harm: { low: 0.20, high: 0.60, action: "safe_reply" },
                hate:      { low: 0.50, high: 0.90, action: "block" },
                off_topic: { low: 0.70, high: 0.95, action: "redirect" } },
  stream_mode: "strict" | "optimistic")

pii_vault(conversation_id, placeholder, type, value_encrypted,
          expires_at)                 -- PK (conversation_id, placeholder)

audit_events(event_id PK, ts, product_id, conversation_id, message_id,
             direction: "input" | "output", check, category, score,
             low, high, action, policy_version, model_version,
             latency_ms, masked_text_ref)        -- never a raw value

labels(message_id, category, human_label, labeller_id, source:
       "sample" | "user_report" | "grey_band")
```

## High-level design

**Offline path**

1. Policy store. Each product owns a policy document. A new version is reviewed, replayed against last week's logged scores, then pushed to every gateway within 60 seconds.
2. Labelled sets. People label sampled traffic (masked), user reports and grey-band cases. The sets train the classifiers and give the precision and recall curves that thresholds are picked from.
3. A new classifier or policy runs in shadow mode on live traffic before it decides anything.

**Online path**

4. The gateway receives a message and reads the product's policy from memory.
5. Three input checks run in parallel: a pattern detector with checksums for structured PII, a named-entity model for names and addresses, and a multi-label safety classifier. The wait is the slowest of the three, about 25 ms.
6. The policy turns scores into an action. Above the high threshold: block, or send a safe reply (a self-harm message gets a supportive reply with helpline details). Between the thresholds: a larger model reads the message with the policy text. Below: allow.
7. Each PII value is replaced by a typed placeholder such as `<PHONE_1>`, and the mapping is saved in the vault for this conversation.
8. The masked prompt goes to the LLM, with one system line: copy placeholders exactly.
9. The output stream passes through the output guard: a pattern scan on a rolling buffer, and the classifier every 50 tokens. Strict mode holds each chunk until it passes. Optimistic mode releases at once and retracts on failure.
10. Placeholders are restored at the last hop, just before text leaves for the user. Traces and logs keep the masked text.
11. Each message writes two audit events: its input verdict and its output verdict. A sample goes to labelling, which closes the loop to step 2.

## Sequence diagram

Rendering diagram…

## Deep dives

### Reversible placeholders

Replace each value with a typed, numbered placeholder: `<PHONE_1>`, `<PERSON_2>`. The same value gets the same placeholder for the whole conversation, so the model can still reason: "send it to `<EMAIL_1>`, the address `<PERSON_1>` gave". The type keeps the sentence meaningful; a bare `[REDACTED]` does not. A one-shot request can keep the mapping in memory. A chat needs it on every later turn, so it lives in a vault: encrypted, keyed by conversation, expiring after 30 days. Restoring happens at the last hop, so the model provider and the trace store never hold the raw value.

Two limits. The model cannot compute on a masked value ("which city has this PIN code?"), so the policy lists types that pass unmasked per product. And a stream can split a placeholder across tokens, so the gateway holds text from an open `<` until the closing `>` arrives.

### Latency before and during the stream

Before the model call, checks run in parallel, so the cost is the slowest check (25 ms) and not the sum. Masking must finish before the prompt leaves, because a raw value sent to the model cannot be taken back. Safety scoring has no such limit. The 300 ms second check runs alongside the model call, and the answer is cancelled if the check fails.

During the stream, strict mode holds a chunk until it is checked. At an assumed 50 tokens per second a 50-token chunk appears 1 s late, so the first chunk is cut to 15 tokens: 0.3 s plus a 25 ms check. Optimistic mode shows tokens at once and checks behind them; on a failure it stops and replaces the message, and the user may already have read up to 50 tokens. The teen product runs strict. The general assistant runs optimistic.

### False blocks against misses

One threshold gives 80,000 false blocks and 20,000 misses a day. The two errors cost differently by category and product. A missed self-harm message in the teen product is far worse than a wrong block. A blocked medical question in the general assistant loses a user. So each category has its own thresholds per product, read from that product's precision and recall curve.

Use three bands. Below `low`: allow. Above `high`: act. Between: the second check by a larger model, which costs 240 USD/day because only 1% of traffic reaches it. PII is different: a wrongly masked order number is restored correctly anyway, so a false positive costs almost nothing. Tune PII detection for recall.

### Policy as data, and the audit trail

A policy is a versioned document, not code. Every audit event stores the score, both thresholds, the action, the policy version and the classifier version, so "why was this blocked in March" has an answer. Because scores are logged, a threshold change can be replayed over last week's events to predict the new block count before it ships, with no model run.

## Evaluation

**PII detection.** A labelled set of 5,000 messages with marked spans. Report span-level recall and precision per type. Include local formats (12-digit Aadhaar numbers with their checksum, 10-character PAN, UPI ids), Hindi-English mixed text, digits written as words, and names that are also common words.

**Leak test.** Send canary values through the whole pipeline, then search the model request log and the trace store. The count must be zero.

**Round trip.** Share of answers where every placeholder is restored exactly. Track how often the model changes one (`<PERSON 1>`); target under 0.1%.

**Safety classifiers.** For each category and product: recall on the harm and attack set, and false-block rate on 50,000 sampled normal messages, both at the live thresholds. Slice by language.

**Latency.** p50, p95 and p99 added by input checks, and time to first visible text in strict mode, under a load test at 1,389 messages per second.

**Human review.** Each week, label 500 blocked and 500 allowed messages per product. Misses are about 0.05% of traffic, so a random sample of allowed messages finds almost none: also sample just under the low threshold, where misses concentrate.

**Online.** Block rate by category and product, with an alert when it doubles. Wrong-block reports per 1,000 blocks, retractions per day in optimistic mode, grey-band volume and PII found in outputs.

**Rollout.** Shadow first and compare decisions with the live version. Then an A/B test on user outcomes: sessions abandoned right after a block, and session length.

## Bottlenecks & mitigations

* Output checks: 8,333 per second at peak use 18 of the 26 GPUs. One shared encoder with two heads (PII spans and safety labels) would cut the input side from 8 GPUs to 4.
* Vault reads on every released chunk. Cache the conversation's mapping in gateway memory for the life of the stream.
* Long pasted documents: a 6,000-token paste costs the name model as much as 50 average messages. Split it into windows, batch them and cap the size.
* The grey-band model takes about 300 ms. If an attack wave grows the band tenfold, queue depth explodes, so fall back to the stricter threshold.
* Audit volume of 24 GB a day needs partitioning by day and product.

## Failure modes

* **PII slips past detection.** A name that is a common word, or a phone number spelled out in words. Mitigation: normalise spelled digits, tune for recall, and scan the output side as a second chance.
* **The model changes a placeholder.** `<PERSON_1>` comes back as `<Person 1>` and cannot be restored. Mitigation: a tolerant restore pattern, the system instruction, and an alert on the mangle rate.
* **A user types a placeholder.** Text such as `<EMAIL_1>` in the input could be restored to a stored value. Mitigation: escape placeholder-shaped text on input; the vault is per conversation, so it holds only that user's data.
* **Retraction comes too late.** In optimistic mode harmful text is on screen before the check fails. Mitigation: strict mode for high-risk products, and a shorter check interval for severe categories.
* **A request split over turns.** Each message alone looks harmless. Mitigation: the classifier reads the last few turns, not only the newest message.
* **The guard service is down.** Mitigation: strict products fail closed with an apology; others fall back to pattern checks only and raise an alert.
* **A policy change spikes false blocks.** Mitigation: replay before release, roll out to 5% first, and roll back within 60 seconds.
* **The audit log becomes a PII store.** Mitigation: masked text and hashes only, access control, and 90-day retention.

## Follow-up questions interviewers ask

* A user asks for a letter that includes their own address. What does the model see, and what does the user see?
* The product must show the first word within 300 ms. Which stream mode do you choose, and what do you give up?
* Legal demands at most 1% misses for one category. What happens to false blocks, and how do you show the trade-off?
* How do you support 12 languages, including Hindi-English mixed text?
* The model provider already offers a moderation endpoint. Do you still need this layer?
* How does the design change for voice or image input?

## Lessons that cover this

* [#16Evals, tracing and guardrailsShip](/ai/learn/evals-tracing-guardrails)
* [#24LLMs on cloud - Bedrock, Azure OpenAI, Vertex AILater](/ai/learn/llms-on-cloud)

## Further reading

* [Llama Guard: LLM-based Input-Output SafeguardPaperarxiv.org](https://arxiv.org/abs/2312.06674)
* [OWASP Top 10 for Large Language Model ApplicationsGuideowasp.org](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousPrompt-injection defence for a tool-using agent](/ai/problems/prompt-injection-defence)[NextStructured data extraction from documents](/ai/problems/structured-extraction)

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
