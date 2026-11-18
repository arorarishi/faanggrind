# Digital Wallet (Paytm / PhonePe balance & transfers) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/digital-wallet

[All system design questions](/system-design)

#30HLDHardHigh-level design

# Digital Wallet (Paytm / PhonePe balance & transfers)

ACIDledgeridempotencyshardingconsistency

## Problem statement

Design a wallet service where users hold a balance, top up from a bank, pay merchants, and transfer to other users — with balances that are always exactly right, even across shards and failures.

## Requirements

### Functional

* Get balance; top-up; transfer wallet→wallet; pay merchant; withdraw to bank.
* Transaction history with statements.
* Limits (per txn, daily) and KYC tiers.
* Reversals/refunds.

### Non-functional

* Strong consistency for balances (no negative balances, no lost money).
* Exactly-once effect of each transfer; idempotent APIs.
* 1M transfers/day with peaks of 5k/s (festivals, cashback).
* Full audit trail; regulatory reporting.

## Back-of-the-envelope estimates

* 5k transfers/s peak; each = 2 balance updates + ledger rows + txn row ≈ 5 writes → 25k writes/s → a single Postgres primary is at its limit; shard wallets by user id.
* Ledger growth: 1M/day × 4 rows × 200 B = 800 MB/day; 10 years ≈ 3 TB.
* Cross-shard transfers: with 10 shards, ~90% of transfers cross shards → need a cross-shard protocol (2PC or saga).

## API

```
GET  /v1/wallets/{id}/balance
POST /v1/transfers      Idempotency-Key: <uuid>   { fromWalletId, toWalletId, amount, currency, note }
                        → 201 { transferId, status: "completed" | "pending" | "failed" }
POST /v1/topups         Idempotency-Key           { walletId, amount, paymentMethodId }
POST /v1/withdrawals    Idempotency-Key           { walletId, amount, bankAccountId }
GET  /v1/wallets/{id}/transactions?cursor=
POST /v1/transfers/{id}/reverse
```

Amounts as integers in paise/cents.

## Data model

```
wallets      (wallet_id, user_id, currency, balance, version, status)        -- sharded by wallet_id
ledger       (entry_id, txn_id, wallet_id, amount (+/-), balance_after, type, created_at)   -- append-only, same shard as wallet
transactions (txn_id, type, from_wallet, to_wallet, amount, status, idempotency_key UNIQUE, created_at, updated_at)
txn_steps    (txn_id, step, status)     -- for cross-shard sagas
limits       (wallet_id, daily_used, daily_cap, per_txn_cap)
```

Invariant per wallet: `balance == SUM(ledger.amount)`; checked by a nightly job.

## High-level design

1. **Wallet API** validates, checks idempotency (returns stored response on replay), enforces limits/KYC, creates a `transactions` row `pending`.
2. **Same-shard transfer**: one DB transaction: `UPDATE wallets SET balance = balance - X WHERE wallet_id=? AND balance >= X` (row lock + non-negative predicate) → credit row → two ledger rows → mark txn `completed`. Row count 0 on the debit means insufficient funds.
3. **Cross-shard transfer (saga)**: step 1 debit on shard A (`pending_debit` ledger entry, txn step recorded); step 2 credit on shard B; step 3 finalise. If step 2 fails permanently, compensate by crediting back on A. A **saga orchestrator** drives steps with persisted state so a crash resumes, never restarts. Alternative: 2PC across shards — stronger but blocks on coordinator failure; most wallets use sagas with a short 'pending' window.
4. **Top-ups/withdrawals** go through the payment service (bank/UPI); wallet credit happens only on confirmed webhook; withdrawals debit first (hold), release on failure.
5. **History** read from ledger by wallet; statements generated from ledger.
6. **Reconciliation** jobs: ledger vs balance per wallet; wallet totals vs bank settlement; stuck sagas older than N minutes escalated.

## Architecture diagram

Rendering diagram…

## Deep dives

**Never compute balance in the app and write it back**; always `balance = balance - X` with a predicate, or derive from ledger. This eliminates lost-update races.

**Idempotency** stored *with* the final response so a retried request after a timeout gets the identical result.

**Saga pending state**: the sender sees the amount deducted immediately and a 'processing' status for ≤ seconds; the recipient sees it after step 2; failures refund automatically. Users tolerate this; they don't tolerate money vanishing.

**Hot wallets** (a big merchant receiving 1k credits/s): row-lock contention → split into sub-wallets (buckets) credited round-robin and summed on read, or batch credits.

**Money is integers**; currency per wallet; FX handled by a separate service with explicit rates recorded on the transaction.

## Bottlenecks & mitigations

* Single primary write limit → shard by wallet id; keep shard transactions small.
* Merchant hot wallet contention → bucketed sub-wallets.
* Saga orchestrator throughput → partition by txn id; stateless workers with persisted step state.
* Ledger reads for history → index (wallet\_id, created\_at DESC); paginate; cache first page.

## Failure modes

* **Crash after debit, before credit**: saga state shows step 1 done; orchestrator resumes step 2 on restart; if B is down for long, compensate.
* **Duplicate request** (client retry): idempotency key returns the original response; no double debit.
* **Shard failover**: synchronous replication (or semi-sync) so an acknowledged debit survives; in-flight transactions retried by the orchestrator.
* **Webhook lost** for a top-up: reconciliation with the bank/PSP report credits the wallet later; user sees 'pending'.
* **Negative balance via concurrent debits**: impossible with the `balance >= X` predicate under row locks.

## Follow-up questions interviewers ask

* How would you support scheduled/auto-pay and mandates?
* How would you design interest/cashback accrual?
* How would you handle a regulatory freeze on a wallet mid-transfer?

## Further reading

* [Guide: Digital walletsIllustrated guide on this site](/system-design/learn/wallets)

[PreviousLog Aggregation & Search (ELK / Splunk-like)](/system-design/log-aggregation-and-search)[NextOnline Coding Judge (LeetCode / HackerRank)](/system-design/online-code-judge)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

PhonePePaytmPayPalAmazonGoldman SachsJPMorgan Chase

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
