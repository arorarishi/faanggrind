# Payment System (Stripe / Razorpay) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/payment-system

[All system design questions](/system-design)

#13HLDHardHigh-level design

# Payment System (Stripe / Razorpay)

idempotencyledgerreconciliationexactly-oncePSP integration

## Problem statement

Design a payment service for an e-commerce platform that accepts a customer's payment, moves money via external payment service providers (PSPs), records an auditable ledger, pays out to merchants, and never double-charges or loses a cent.

## Requirements

### Functional

* Pay-in: charge a customer for an order via card/UPI/wallet through a PSP.
* Pay-out: settle funds to merchants on a schedule.
* Refunds, partial refunds, chargebacks.
* Ledger with every money movement; reconciliation with PSP reports.
* Idempotent APIs; webhook handling.

### Non-functional

* Correctness over availability: it is better to fail a payment than to double-charge.
* Exactly-once effect for each payment (at-least-once delivery + idempotency).
* Durable, append-only, auditable records; PCI-DSS scope minimised (never store raw card data).
* Scale: 10M payments/day; p99 < 2 s excluding PSP time.

## Back-of-the-envelope estimates

* 10M payments/day ≈ 115/s, peak 1–2k/s (sales). Modest throughput — the difficulty is correctness, not scale.
* Ledger: each payment ≈ 4–6 double-entry rows × 200 B → ~10 GB/day; 7-year retention ≈ 25 TB → partitioned relational DB + cold archive.
* PSP latency 1–5 s and success ~95%; retries must be safe.
* Reconciliation: PSP settlement files daily, millions of rows — batch job.

## API

```
POST /v1/payments
  headers: Idempotency-Key: <uuid>
  { orderId, amount:{value:49900,currency:"INR"}, method:{type:"card", token:"tok_..."}, customerId }
  → 201 { paymentId, status:"pending|succeeded|failed", pspRef }

GET  /v1/payments/{id}
POST /v1/payments/{id}/refunds  { amount, reason }  (Idempotency-Key)
POST /v1/webhooks/{psp}         (signed; returns 200 fast, processes async)
GET  /v1/merchants/{id}/balance
POST /v1/payouts                { merchantId, amount }
```

Amounts are integers in minor units; never floats.

## Data model

```
payment_orders (id, order_id UNIQUE, customer_id, amount, currency, status, created_at)
payment_attempts(id, payment_order_id, psp, psp_ref, idempotency_key UNIQUE, status, response, created_at)
ledger_entries (id, txn_id, account_id, debit, credit, currency, created_at)   -- append-only, double-entry
accounts       (id, type: customer|merchant|psp_receivable|platform_fee|..., currency)
refunds        (id, payment_order_id, amount, status, idempotency_key UNIQUE)
webhook_events (id, psp, event_id UNIQUE, payload, processed_at)
```

Invariant: for every `txn_id`, `SUM(debit) = SUM(credit)`.

## High-level design

1. **Payment service** receives the request, checks the idempotency key (stored with the response — a replay returns the same result), writes a `payment_order` in `pending`, and creates a `payment_attempt`.
2. **PSP adapter** calls the PSP with the PSP's own idempotency key = our attempt id. The result (or timeout) updates the attempt. On timeout the status stays `pending`, never assumed failed.
3. **Webhooks** from the PSP are verified (signature), deduplicated by `event_id`, enqueued, and processed to finalise status. Webhooks are the source of truth over synchronous responses.
4. **Ledger service**: every state change that moves money writes balanced double-entry rows in the same DB transaction as the status update (or via transactional outbox → ledger). Balances are computed from the ledger, never stored as mutable numbers without a ledger trail.
5. **Reconciliation**: daily job compares PSP settlement reports with `payment_attempts` + ledger; mismatches raise cases for ops.
6. **Payouts**: scheduled job aggregates merchant balances and sends transfers through the PSP with the same idempotent pattern.
7. **Retries**: a scheduler re-queries PSP status for attempts stuck in `pending` beyond a threshold (using the PSP's status API), instead of re-charging.

## Architecture diagram

Rendering diagram…

## Deep dives

**Idempotency, three layers**: client → our API (Idempotency-Key, stored with the response, 24 h TTL); our service → PSP (PSP idempotency key = attempt id); PSP → us (webhook `event_id` unique).

**Timeouts are not failures**: a timed-out charge may have succeeded at the PSP. Query status before any retry. This is the single most important rule.

**Double-entry ledger**: debit customer receivable / credit merchant payable; fees as separate entries; balances derived by aggregation (with periodic snapshots for speed). Enables audit and makes bugs visible as unbalanced transactions.

**Transactional outbox**: write the event to an outbox table in the same transaction as the status change; a relay publishes to Kafka. Avoids the dual-write problem.

**Card data**: tokenise at the PSP/vault; our system never sees PANs → minimal PCI scope.

## Bottlenecks & mitigations

* PSP rate limits and latency → connection pools, circuit breakers, multiple PSPs with routing by method/success rate.
* Ledger write contention on hot accounts (platform fee account) → partition by currency/day; use append-only rows, never `UPDATE balance`.
* Webhook bursts after a PSP outage → queue with backpressure; processors idempotent.
* Reconciliation over millions of rows → bulk load PSP reports into a staging table and join in the DB.

## Failure modes

* **PSP down**: circuit breaker opens; new payments fail fast with a retryable error; pending ones are resolved later via status polling and webhooks.
* **Our DB commit fails after PSP success**: the attempt id is stored before the PSP call; recovery job finds attempts without a final status and reconciles via PSP status API.
* **Duplicate webhook**: `event_id` unique constraint → ignored.
* **Partial refund exceeding paid amount**: enforce in the same transaction as the ledger write.
* **Currency/rounding**: integers in minor units; explicit rounding rules for fees; test with cents that do not divide evenly.

## Follow-up questions interviewers ask

* How would you support multi-currency and FX?
* How would you design the chargeback/dispute workflow?
* How would you route between multiple PSPs to maximise success rate?

## Further reading

* [Guide: PaymentsIllustrated guide on this site](/system-design/learn/payments)

[PreviousE-commerce Platform & Flash Sale (Flipkart Big Billion Day)](/system-design/ecommerce-flash-sale)[NextDistributed Unique ID Generator (Snowflake)](/system-design/distributed-id-generator)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

StripePayPalRazorpayAmazonGoldman SachsJPMorgan ChasePhonePe

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
