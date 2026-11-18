# Food Delivery Platform (Swiggy / Zomato) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/food-delivery-platform

[All system design questions](/system-design)

#11HLDHardHigh-level design

# Food Delivery Platform (Swiggy / Zomato)

geospatialorder state machinedispatchreal-time tracking

## Problem statement

Design a three-sided marketplace where customers order from nearby restaurants, restaurants accept and prepare orders, and delivery partners are assigned and tracked to the customer's door.

## Requirements

### Functional

* Browse/search restaurants and menus that deliver to the customer's location.
* Cart, checkout, payment; order status updates in real time.
* Restaurant accepts/rejects, marks food ready.
* Assign a delivery partner; live tracking; ETA.
* Ratings, offers/coupons, order history.

### Non-functional

* Order placement p99 < 1 s; status updates within seconds.
* Strong consistency for order state and payment; eventual consistency for menus/search.
* Peak load: dinner rush 5× average; festival days 10×.
* Restaurant/partner availability must be accurate to avoid failed orders.

## Back-of-the-envelope estimates

* 5M orders/day ≈ 60/s average, ~600/s at peak, festival ~1,500/s.
* Restaurant search: 50M DAU × 5 searches = 250M/day ≈ 3k/s, peak 15k/s — read-heavy, cacheable.
* Delivery partner locations: 500k active × every 5 s = 100k updates/s → in-memory geo index.
* Order record + events ≈ 5 KB → 25 GB/day; 2 years hot ≈ 18 TB in a sharded relational store.

## API

```
GET  /v1/restaurants?lat&lng&cuisine&sort            → paginated, serviceable restaurants
GET  /v1/restaurants/{id}/menu
POST /v1/cart/items  /  PUT /v1/cart
POST /v1/orders   { cartId, address, paymentMethod, couponCode }  → { orderId, status }
GET  /v1/orders/{id}        WS order.{id} events
POST /v1/restaurant/orders/{id}/accept | reject | ready      (merchant app)
POST /v1/partner/orders/{id}/accept | pickedUp | delivered   (partner app)
POST /v1/partner/location { lat, lng }
```

## Data model

```
restaurants (id, name, geo (lat,lng), delivery_radius, is_open, avg_prep_time)
menu_items  (id, restaurant_id, name, price, is_available)
orders      (id, customer_id, restaurant_id, partner_id, status, amount, address, created_at)   -- sharded by customer/city
order_items (order_id, item_id, qty, price)
order_events(order_id, status, ts, actor)
partners    (id, status, current_order_id, rating)   + Redis GEO for live positions
inventory/availability flags cached in Redis per restaurant
```

## High-level design

1. **Discovery**: restaurants indexed in Elasticsearch with geo-point; a query = geo filter (within delivery radius, accounting for restaurant's polygon) + open-now + ranking (rating, ETA, promo). Results cached per (geohash-6, filters) for ~60 s.
2. **Order service**: transactional creation of order + items in Postgres; validates item availability against Redis flags; reserves the coupon; calls **payment service** (idempotent). Publishes `order.created`.
3. **Order state machine**: `created → paid → accepted → preparing → ready → picked_up → delivered` with `cancelled`/`rejected` branches; every transition is a conditional update on the current status to prevent illegal jumps.
4. **Merchant service**: pushes new orders to the restaurant tablet (WebSocket + push fallback); auto-reject if not accepted in N minutes.
5. **Dispatch service**: when an order is `accepted`, estimate ready time and pick a partner so pickup ≈ ready time: candidates from the geo index near the restaurant, scored by distance, current load (batching two orders on one route), and acceptance rate. Offers with timeouts, same CAS pattern as ride-sharing.
6. **Tracking**: partner locations → geo index → customer app via WebSocket; ETA from the routing service.
7. **Notifications** and **analytics** consume the event stream.

## Architecture diagram

Rendering diagram…

## Deep dives

**Serviceability**: a restaurant's delivery zone is a polygon, not a circle; store polygons and use point-in-polygon at search time (ES geo\_shape) so the cart never fails at checkout.

**Batching deliveries**: dispatch can attach a second order to a partner if the second restaurant is on the route and both ETAs stay within SLA; this is the main lever for unit economics.

**Prep-time prediction**: per-restaurant ML model from historical accept→ready times, by time of day and cart size; drives dispatch timing.

**Menu availability**: restaurants toggle items; write to Redis immediately, ES asynchronously; the order service checks Redis at placement.

## Bottlenecks & mitigations

* Search at dinner peak → cache per geohash, pre-compute open/closed by schedule, limit radius.
* Orders DB write hot-spot during festivals → shard by city; keep the order row small and events in a separate append-only table.
* Dispatch scoring across thousands of partners → restrict to nearest cells; pre-scored partner pools per zone refreshed every 30 s.
* Merchant tablets offline → push + SMS fallback; auto-reject timer protects the customer.

## Failure modes

* **Payment succeeded but order write failed**: payment is created with `order_id` idempotency key; a reconciliation job refunds orphaned payments.
* **Restaurant never responds**: auto-cancel with full refund and partner un-assignment.
* **Partner app crashes mid-delivery**: order stays `picked_up`; ops dashboard flags stale orders; customer support can reassign.
* **ES cluster degraded**: fall back to a cached 'popular restaurants in your zone' list.
* **Kafka lag**: order placement still succeeds (DB is source of truth); downstream (merchant push, dispatch) delayed — alert on lag > 30 s.

## Follow-up questions interviewers ask

* How would you design surge/rain-mode pricing for delivery fees?
* How would you support scheduled orders?
* How do you prevent fraud (fake delivered, repeated refunds)?

[PreviousRide-Sharing Service (Uber / Ola)](/system-design/ride-sharing)[NextE-commerce Platform & Flash Sale (Flipkart Big Billion Day)](/system-design/ecommerce-flash-sale)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

SwiggyZomatoFlipkartAmazonUber

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
