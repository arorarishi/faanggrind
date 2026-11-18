# Notification System (push, SMS, email) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/notification-system

[All system design questions](/system-design)

#4HLDMediumHigh-level design

# Notification System (push, SMS, email)

fan-outqueuesidempotencythird-party integration

## Problem statement

Design a service that lets internal teams send notifications to users over push (iOS/Android), SMS and email, with templates, user preferences, rate limits and delivery tracking.

## Requirements

### Functional

* Send a notification to one user or a segment over one or more channels.
* Respect user preferences (opt-outs, quiet hours) and per-channel rate limits.
* Templates with variables; localisation.
* Track delivery status and retries; expose history to the user.
* Priority levels (OTP = critical, marketing = low).

### Non-functional

* Critical notifications (OTP) delivered within seconds; marketing can lag minutes.
* At-least-once delivery with deduplication so users never get duplicates.
* Scale to 100M notifications/day with bursts (e.g. sale launch).
* Third-party providers (APNs, FCM, Twilio, SES) can fail — the system must not.

## Back-of-the-envelope estimates

* 100M/day ≈ 1,200/s average; bursts of 50k/s during campaigns.
* Message size ~1 KB → 100 GB/day of event data; keep 30 days hot → 3 TB.
* Provider throughput: FCM/APNs handle 10k+/s per connection pool; SMS providers often cap at hundreds/s per account → SMS needs its own queue with its own rate limiting.
* Device tokens: 200M devices × 200 B = 40 GB, sharded by user id.

## API

```
POST /v1/notifications
{
  "idempotencyKey": "order-123-shipped",
  "recipients": { "userIds": [..] } | { "segmentId": "..." },
  "channels": ["push","sms"],
  "priority": "high",
  "template": "order_shipped", "params": { "orderId": 123 },
  "scheduleAt": null
}
→ 202 { "notificationId": "n_abc" }

GET /v1/notifications/{id}/status → per-recipient, per-channel status
PUT /v1/users/{id}/preferences   { push: true, sms: false, quietHours: {...} }
```

## Data model

```
notifications(id, idempotency_key UNIQUE, template, params, priority, created_at)
deliveries(id, notification_id, user_id, channel, status, attempts, provider_msg_id, updated_at)
user_preferences(user_id, channel, enabled, quiet_start, quiet_end)
device_tokens(user_id, platform, token, updated_at)
templates(name, locale, channel, body)
```

`deliveries` is the high-volume table — partition by day, index on (user\_id, updated\_at).

## High-level design

1. **Notification API** validates, deduplicates on `idempotencyKey`, persists, and publishes to Kafka topics **per priority × channel** (e.g. `push.high`, `sms.low`).
2. **Segment expansion**: for segment sends, a resolver streams user ids from the user service into per-user messages (fan-out happens here, not in the API).
3. **Channel workers** consume, apply preferences and rate limits, render templates, and call the provider. Each channel has its own worker pool and concurrency so a slow SMS provider never starves push.
4. **Provider adapters** with circuit breakers, per-provider retries with backoff, and failover to a secondary provider (Twilio → SNS).
5. **Delivery status**: provider webhooks/callbacks update `deliveries`; a reconciliation job handles missing callbacks.
6. **Scheduling**: `scheduleAt` messages go to a delayed queue / scheduler service that republishes at the right time.

## Architecture diagram

Rendering diagram…

## Deep dives

**Exactly-once feel**: at-least-once from Kafka + idempotency at two levels — the API key (caller retries) and a `(notification_id, user_id, channel)` unique constraint on `deliveries` (worker retries).

**Priority isolation**: separate topics and worker pools; scale high-priority workers independently and cap low-priority throughput during bursts.

**Preference checks late**: evaluate opt-outs and quiet hours in the worker right before sending — a user may opt out between enqueue and send.

**Batching**: FCM supports multicast to 500 tokens per call; batch by template to cut provider calls 100×.

## Bottlenecks & mitigations

* SMS provider rate caps → dedicated queue, token-bucket per provider, multiple provider accounts.
* Segment fan-out of 50M users in one API call → stream and chunk; never load the whole segment into memory.
* Delivery table write rate → partitioned, append-only; aggregate for reporting asynchronously.
* Template rendering CPU during bursts → pre-render per locale when params are shared.

## Failure modes

* **Provider outage**: circuit breaker opens, traffic fails over to the secondary provider; if none, messages stay in Kafka (retention ≥ 24 h) and drain later.
* **Worker crash mid-send**: message not acked → redelivered → dedupe key prevents a second send if the first actually reached the provider.
* **Stale device tokens**: provider returns 'unregistered' → delete the token immediately to avoid wasting quota.
* **Kafka lag during a campaign**: dashboards on consumer lag per topic; auto-scale workers on lag.

## Follow-up questions interviewers ask

* How would you build a digest (batch 10 notifications into one) feature?
* How would you A/B test notification copy?
* How do you guarantee an OTP is not delayed behind marketing traffic?

## Further reading

* [Guide: Notification deliveryIllustrated guide on this site](/system-design/learn/notifications)

[PreviousDistributed Cache (Redis / Memcached)](/system-design/distributed-cache)[NextChat / Messaging System (WhatsApp, Slack)](/system-design/chat-messaging-system)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonSwiggyFlipkartUberAtlassianPayPal

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [High-level design](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Follow-ups](#follow-ups)
12. [Further reading](#reading)

## Your notes

Saved

Autosaves to this browser.
