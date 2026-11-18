# Email Service (Gmail-like) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/email-service

[All system design questions](/system-design)

#28HLDHardHigh-level design

# Email Service (Gmail-like)

SMTPstoragesearchspamattachments

## Problem statement

Design a web email service: receive mail via SMTP from the internet, store it durably, let users read/search/organise mail in a web/mobile client, send outbound mail, and filter spam.

## Requirements

### Functional

* Receive inbound mail (SMTP); deliver to the right mailbox; handle attachments.
* Send outbound mail with retries and bounce handling.
* Read, list (threaded), label/folder, star, delete; sync across devices.
* Full-text search over a user's mail.
* Spam/phishing filtering.

### Non-functional

* Durability: mail never lost once accepted (SMTP 250 OK = committed).
* Inbox list < 300 ms; search < 1 s.
* 1B users, 100B emails/day incl. spam; 15 GB quota each.
* Privacy and per-user isolation; encryption at rest.

## Back-of-the-envelope estimates

* 100B emails/day inbound (≈ 80% spam rejected early); 20B stored × 50 KB avg = 1 PB/day → object storage with dedup for attachments/bodies.
* Metadata per email ~1 KB → 20 TB/day in a sharded DB (by user).
* Search index: ~30% of body size → 300 TB/day; per-user indexes sharded.
* SMTP ingress: 100B/86,400 ≈ 1.2M connections/s at peak — many stateless MTA nodes behind DNS/MX load balancing.

## API

```
Protocols: SMTP (25/587) inbound & outbound; IMAP/POP optional; JMAP/REST for clients.
GET  /v1/mailboxes/{id}/threads?label=INBOX&cursor=
GET  /v1/threads/{id}                → messages with bodies (lazy attachments)
POST /v1/messages/send               { to[], cc[], subject, body, attachmentIds[] }
PUT  /v1/messages/{id}/labels        { add[], remove[] }
GET  /v1/search?q=from:alice has:attachment "invoice"
GET  /v1/attachments/{id}            → presigned URL
```

## Data model

```
users       (user_id, email, quota, ...)
messages    (user_id, message_id, thread_id, from, to[], subject, snippet, labels[], flags, size, received_at, body_ref)  -- sharded by user_id
threads     (user_id, thread_id, subject_norm, last_msg_at, participants[])
attachments (attachment_id, content_hash, size, storage_key, mime)    -- content-addressed, deduped
Object storage: bodies and attachments by hash
Search: per-user inverted index (Lucene-style shard per user group)
```

## High-level design

1. **Inbound MTA cluster** (MX records → many nodes): accepts SMTP, checks SPF/DKIM/DMARC, runs a fast spam pre-filter (reputation, rate limits), and writes the raw message to a durable **queue/journal** before replying `250 OK`.
2. **Delivery workers** parse the message, run the full **spam/phishing classifier**, extract attachments (store content-addressed), write metadata to the user's shard, assign to a thread (by `In-Reply-To`/`References` + subject), update labels, emit `mail.received` for search indexing and push notifications.
3. **Storage**: metadata in a sharded relational/wide-column DB by user; bodies/attachments in object storage encrypted per user; quota enforced at delivery.
4. **Client API** serves threaded lists from the metadata shard with pagination; bodies fetched lazily.
5. **Search**: an indexer consumes `mail.received` and updates the user's index; query service supports operators (from:, has:, dates).
6. **Outbound**: send API writes to `Sent`, enqueues; **outbound MTAs** deliver via SMTP with retries/backoff, DKIM signing, bounce processing, and IP-reputation-aware sending pools.
7. **Sync**: change sequence per mailbox so clients fetch deltas; push via notification service.

## Architecture diagram

Rendering diagram…

## Deep dives

**Accept-then-process**: the SMTP `250 OK` is a durability promise, so journal first; everything else (spam, indexing) can be retried.

**Threading**: use `Message-ID`/`In-Reply-To`/`References` headers; fall back to normalised subject + participants within a time window.

**Dedup**: attachments and bodies are content-addressed; a 10 MB attachment sent to 1,000 people is stored once.

**Spam**: layered — connection-level reputation (cheap) → header/auth checks → ML classifier on content; user feedback loops retrain.

**Deliverability**: warm IP pools, DKIM/DMARC, bounce handling, feedback loops with big providers.

## Bottlenecks & mitigations

* Spam floods on the MTA tier → reject at connection time by reputation; autoscale MTAs; never let spam reach delivery workers unfiltered.
* Hot users (mailing lists receiving 1M/day) → separate shard or rate-limit per mailbox.
* Search index writes → batch per user; near-real-time (≤ 1 min) is enough.
* Attachment egress → CDN-style presigned URLs, range requests.

## Failure modes

* **Delivery worker crash**: message remains in the journal; redelivered; dedupe by `Message-ID` + user.
* **Metadata shard outage**: inbound mail still journaled (250 OK given); delivery to that shard's users delayed; other users unaffected.
* **Outbound recipient server down**: retry with backoff for up to 2–3 days, then bounce to sender.
* **Index corruption**: rebuild a user's index from metadata + bodies.
* **Quota exceeded**: reject with a temporary SMTP error (4xx) so senders retry, or bounce (5xx) per policy.

## Follow-up questions interviewers ask

* How would you implement 'undo send'?
* How would you build server-side filters/rules efficiently?
* How would you support end-to-end encrypted mail?

## Further reading

* [Guide: Email at scaleIllustrated guide on this site](/system-design/learn/email)

[PreviousDistributed Job Scheduler (cron-as-a-service, Airflow-like)](/system-design/distributed-job-scheduler)[NextLog Aggregation & Search (ELK / Splunk-like)](/system-design/log-aggregation-and-search)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleMicrosoftAmazonZohoSalesforce

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
