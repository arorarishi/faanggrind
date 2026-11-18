# E-commerce Platform & Flash Sale (Flipkart Big Billion Day) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/ecommerce-flash-sale

[All system design questions](/system-design)

#12HLDHardHigh-level design

# E-commerce Platform & Flash Sale (Flipkart Big Billion Day)

inventoryqueueingidempotencycachingoverselling

## Problem statement

Design the product catalogue, cart, inventory and checkout for an e-commerce platform, and make it survive a flash sale where 5M users try to buy 10k units of a phone at the same second without overselling.

## Requirements

### Functional

* Product catalogue with search and product pages.
* Cart, checkout, order creation, payment.
* Inventory management — no overselling.
* Flash sale: limited stock, fixed start time, fair access.
* Order tracking and cancellation.

### Non-functional

* Product pages served at 1M+ RPS during sale via cache/CDN.
* Inventory decrement strongly consistent; checkout idempotent.
* Graceful degradation: queue users instead of crashing.
* Payment reliability: exactly-one charge per order.

## Back-of-the-envelope estimates

* Normal: 100k orders/hour. Sale: 5M users hitting 'Buy' within 60 s → 80k+ attempts/s for 10k units.
* Product page: 1M RPS × 50 KB = 50 GB/s → CDN + edge cache mandatory; origin must see < 1% of that.
* Inventory hot row: one SKU row receiving 80k decrements/s is impossible in a relational DB (~5–10k row updates/s with contention) → need Redis atomic decrements or a queue.
* Orders: 10k successful orders in a minute — trivial; the problem is rejecting the other 4.99M cheaply.

## API

```
GET  /v1/products/{id}                    (CDN-cached, ETag)
GET  /v1/products/{id}/availability       (short TTL, from Redis)
POST /v1/cart/items
POST /v1/checkout        { cartId, addressId, paymentMethod, idempotencyKey } → { orderId, status }
GET  /v1/orders/{id}
POST /v1/sale/{saleId}/enter  → { token, position }   (virtual waiting room)
```

## Data model

```
products   (sku, title, description, price, media, category)         -- catalogue DB + search index
inventory  (sku, warehouse_id, available, reserved)                   -- Postgres, plus Redis stock:{sku} counter for sales
carts      Redis hash cart:{user_id}   TTL 7 days
orders     (order_id, user_id, status, total, idempotency_key UNIQUE, created_at)
order_items(order_id, sku, qty, price)
reservations(reservation_id, sku, qty, order_id, expires_at)
payments   (payment_id, order_id UNIQUE, gateway_ref, status)
```

## High-level design

1. **Catalogue**: read-only, heavily cached: CDN for product pages/images, Redis for product JSON, Elasticsearch for search. Price and stock are fetched separately with short TTLs so the page itself is cacheable for hours.
2. **Cart** in Redis; merged with the DB on login.
3. **Checkout flow**: `reserve inventory → create order (pending) → charge payment → confirm order → release/commit reservation`. Reservation has a TTL (10 min) and a background job releases expired ones.
4. **Inventory**: normal mode uses Postgres with `UPDATE … WHERE available >= qty` (atomic, no overselling). Sale mode uses a **Redis counter per SKU** with a Lua `DECRBY if >= qty` — 100k ops/s on one key — and asynchronously syncs to the DB.
5. **Flash-sale gate**: a **virtual waiting room** in front of checkout — users get a token and a queue position; only N tokens/second are admitted to the checkout path. Everyone else sees a countdown, and the backend never sees 5M concurrent checkouts.
6. **Payment service** with idempotency keys; gateway webhooks confirm; reconciliation job for mismatches.
7. **Order events** to Kafka → fulfilment, notifications, analytics.

## Architecture diagram

Rendering diagram…

## Deep dives

**No overselling** = one atomic decrement per sale, wherever it lives. Redis Lua gives atomicity and throughput; the DB stays the ledger, reconciled from Redis + order records.

**Fairness**: the waiting room hands out tokens FIFO (or randomised to defeat bots), enforces one token per user, and rate-limits admission to what checkout can handle.

**Bots**: CAPTCHA/device attestation at token issuance; per-user and per-payment-instrument purchase caps.

**Pre-warming**: load product pages into CDN, stock counters into Redis, and scale checkout pods 30 minutes before the sale.

## Bottlenecks & mitigations

* Single hot SKU counter → still fine in Redis (100k/s); if beyond, pre-split stock into K counters and route users round-robin.
* Payment gateway throughput (often 1–2k TPS) → this is usually the real cap; admission rate should match it.
* Orders DB during sale → writes only for successful orders (10k), not attempts; keep rejected attempts out of the DB entirely.
* Search/product-page thundering herd → cache stampede protection; stale-while-revalidate.

## Failure modes

* **Payment timeout after inventory reserved**: reservation TTL releases stock; order stays `pending` until the webhook or reconciliation resolves it.
* **Redis stock counter lost**: rebuild from `available − reserved − confirmed_orders` in the DB; pause the sale for a few seconds while rebuilding.
* **Double charge on retry**: idempotency key on checkout + unique `order_id` on payments.
* **Waiting room failure**: fail closed for the sale (show 'try again') rather than letting 5M users through.

## Follow-up questions interviewers ask

* How would you handle multi-warehouse inventory and nearest-warehouse allocation?
* How would you design price drops and coupons without cache inconsistency?
* How would you build the order-cancellation and refund flow?

[PreviousFood Delivery Platform (Swiggy / Zomato)](/system-design/food-delivery-platform)[NextPayment System (Stripe / Razorpay)](/system-design/payment-system)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

FlipkartAmazonWalmartMyntraMeesho

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

## Your notes

Saved

Autosaves to this browser.
