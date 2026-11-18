# System design interview questions: System Design (HLD + LLD) · FAANGrind

Source: https://faangrind.vercel.app/system-design

[Dashboard](/dashboard)

![](/logos/system-design.svg)

# System Design (HLD + LLD)

Set Curated practice set

Problems
:   60

Types
:   2

Topics
:   6

## Learn the fundamentals

28 illustrated guides, about 5 hours of reading. Start with the three foundations, then dip into a building block or a worked design whenever a question needs it.

[Open the full guide](/system-design/learn)

1. [1Foundation · 8 minScaling a web app from one server to millions of usersLoad balancers, replication, caching, CDNs, stateless tiers, queues and sharding: the building blocks every design reuses.](/system-design/learn/scaling-to-millions)
2. [2Foundation · 3 minCapacity estimation in your headPowers of two, latency numbers, availability nines and a worked QPS and storage estimate.](/system-design/learn/capacity-estimation)
3. [3Foundation · 3 minThe system design interview playbookA four-step flow (scope, high-level design, deep dive, wrap-up), what to say, what to avoid, and how to split 45 minutes.](/system-design/learn/interview-playbook)

### Building blocks

* [Rate limiting](/system-design/learn/rate-limiting)
* [Consistent hashing](/system-design/learn/consistent-hashing-explained)
* [Distributed key-value stores](/system-design/learn/key-value-stores)
* [Unique IDs at scale](/system-design/learn/unique-ids)

### Worked designs

* [URL shortening](/system-design/learn/url-shortening)
* [Web crawling](/system-design/learn/web-crawling)
* [Notification delivery](/system-design/learn/notifications)
* [News feeds](/system-design/learn/feeds)
* [Chat and messaging](/system-design/learn/chat)
* [Search autocomplete](/system-design/learn/autocomplete)
* [Video streaming platform](/system-design/learn/video-platform)
* [Cloud file storage and sync](/system-design/learn/file-sync)
* [Proximity search](/system-design/learn/proximity)
* [Live location sharing](/system-design/learn/live-location)
* [Maps and navigation](/system-design/learn/maps)
* [Distributed message queues](/system-design/learn/message-queues)
* [Metrics, monitoring and alerting](/system-design/learn/monitoring)
* [Click event aggregation](/system-design/learn/event-aggregation)
* [Hotel reservations](/system-design/learn/reservations)
* [Email at scale](/system-design/learn/email)
* [Object storage internals](/system-design/learn/object-storage-internals)
* [Real-time leaderboards](/system-design/learn/leaderboards)
* [Payments](/system-design/learn/payments)
* [Digital wallets](/system-design/learn/wallets)
* [Stock exchange](/system-design/learn/exchange)

[Random](/problems/random?companies=system-design)

60 problems

TopicsLinks

1

[1.URL Shortener (TinyURL / bit.ly)](/system-design/url-shortener)

Easy1 co.

Easy

[caching](/topics?open=system-design-caching#system-design-caching)[hashing](/topics?open=system-design-hashing#system-design-hashing)+2

also at 0 more

[Note](/system-design/url-shortener&focus=notes)

2

[2.Distributed Rate Limiter](/system-design/rate-limiter)

Medium1 co.

Medium

[middleware](/topics?open=system-design-middleware#system-design-middleware)[redis](/topics?open=system-design-redis#system-design-redis)+2

also at 0 more

[Note](/system-design/rate-limiter&focus=notes)

3

[3.Distributed Cache (Redis / Memcached)](/system-design/distributed-cache)

Medium1 co.

Medium

[LRU](/topics?open=system-design-lru#system-design-lru)[consistent hashing](/topics?open=system-design-consistent-hashing#system-design-consistent-hashing)+2

also at 0 more

[Note](/system-design/distributed-cache&focus=notes)

4

[4.Notification System (push, SMS, email)](/system-design/notification-system)

Medium1 co.

Medium

[fan-out](/topics?open=system-design-fan-out#system-design-fan-out)[idempotency](/topics?open=system-design-idempotency#system-design-idempotency)+2

also at 0 more

[Note](/system-design/notification-system&focus=notes)

5

[5.Chat / Messaging System (WhatsApp, Slack)](/system-design/chat-messaging-system)

Hard1 co.

Hard

[fan-out](/topics?open=system-design-fan-out#system-design-fan-out)[message ordering](/topics?open=system-design-message-ordering#system-design-message-ordering)+2

also at 0 more

[Note](/system-design/chat-messaging-system&focus=notes)

6

[6.News Feed (Facebook / Instagram / LinkedIn feed)](/system-design/news-feed)

Hard1 co.

Hard

[caching](/topics?open=system-design-caching#system-design-caching)[fan-out on read](/topics?open=system-design-fan-out-on-read#system-design-fan-out-on-read)+2

also at 0 more

[Note](/system-design/news-feed&focus=notes)

7

[7.Video Streaming Platform (YouTube / Netflix)](/system-design/video-streaming-platform)

Hard1 co.

Hard

[CDN](/topics?open=system-design-cdn#system-design-cdn)[adaptive bitrate](/topics?open=system-design-adaptive-bitrate#system-design-adaptive-bitrate)+2

also at 0 more

[Note](/system-design/video-streaming-platform&focus=notes)

8

[8.Web Crawler](/system-design/web-crawler)

Hard1 co.

Hard

[BFS](/topics?open=system-design-bfs#system-design-bfs)[dedup](/topics?open=system-design-dedup#system-design-dedup)+2

also at 0 more

[Note](/system-design/web-crawler&focus=notes)

9

[9.Search Autocomplete / Typeahead](/system-design/search-autocomplete)

Medium1 co.

Medium

[caching](/topics?open=system-design-caching#system-design-caching)[offline aggregation](/topics?open=system-design-offline-aggregation#system-design-offline-aggregation)+2

also at 0 more

[Note](/system-design/search-autocomplete&focus=notes)

10

[10.Ride-Sharing Service (Uber / Ola)](/system-design/ride-sharing)

Hard1 co.

Hard

[geospatial](/topics?open=system-design-geospatial#system-design-geospatial)[matching](/topics?open=system-design-matching#system-design-matching)+2

also at 0 more

[Note](/system-design/ride-sharing&focus=notes)

11

[11.Food Delivery Platform (Swiggy / Zomato)](/system-design/food-delivery-platform)

Hard1 co.

Hard

[dispatch](/topics?open=system-design-dispatch#system-design-dispatch)[geospatial](/topics?open=system-design-geospatial#system-design-geospatial)+2

also at 0 more

[Note](/system-design/food-delivery-platform&focus=notes)

12

[12.E-commerce Platform & Flash Sale (Flipkart Big Billion Day)](/system-design/ecommerce-flash-sale)

Hard1 co.

Hard

[caching](/topics?open=system-design-caching#system-design-caching)[idempotency](/topics?open=system-design-idempotency#system-design-idempotency)+3

also at 0 more

[Note](/system-design/ecommerce-flash-sale&focus=notes)

13

[13.Payment System (Stripe / Razorpay)](/system-design/payment-system)

Hard1 co.

Hard

[PSP integration](/topics?open=system-design-psp-integration#system-design-psp-integration)[exactly-once](/topics?open=system-design-exactly-once#system-design-exactly-once)+3

also at 0 more

[Note](/system-design/payment-system&focus=notes)

14

[14.Distributed Unique ID Generator (Snowflake)](/system-design/distributed-id-generator)

Easy1 co.

Easy

[clock](/topics?open=system-design-clock#system-design-clock)[sharding](/topics?open=system-design-sharding#system-design-sharding)+1

also at 0 more

[Note](/system-design/distributed-id-generator&focus=notes)

15

[15.Distributed Key-Value Store (Dynamo / Cassandra)](/system-design/key-value-store)

Hard1 co.

Hard

[LSM tree](/topics?open=system-design-lsm-tree#system-design-lsm-tree)[consistent hashing](/topics?open=system-design-consistent-hashing#system-design-consistent-hashing)+3

also at 0 more

[Note](/system-design/key-value-store&focus=notes)

16

[16.Distributed Message Queue (Kafka)](/system-design/distributed-message-queue)

Hard1 co.

Hard

[consumer groups](/topics?open=system-design-consumer-groups#system-design-consumer-groups)[log](/topics?open=system-design-log#system-design-log)+3

also at 0 more

[Note](/system-design/distributed-message-queue&focus=notes)

17

[17.Cloud File Storage & Sync (Google Drive / Dropbox)](/system-design/cloud-file-storage)

Hard1 co.

Hard

[chunking](/topics?open=system-design-chunking#system-design-chunking)[deduplication](/topics?open=system-design-deduplication#system-design-deduplication)+3

also at 0 more

[Note](/system-design/cloud-file-storage&focus=notes)

18

[18.Proximity / Nearby Places Service (Yelp, Google Maps 'near me')](/system-design/proximity-service)

Medium1 co.

Medium

[geohash](/topics?open=system-design-geohash#system-design-geohash)[quadtree](/topics?open=system-design-quadtree#system-design-quadtree)+2

also at 0 more

[Note](/system-design/proximity-service&focus=notes)

19

[19.Movie / Event Ticket Booking (BookMyShow)](/system-design/ticket-booking-system)

Hard1 co.

Hard

[concurrency](/topics?open=system-design-concurrency#system-design-concurrency)[high contention](/topics?open=system-design-high-contention#system-design-high-contention)+2

also at 0 more

[Note](/system-design/ticket-booking-system&focus=notes)

20

[20.Hotel Reservation System (Airbnb / Booking.com)](/system-design/hotel-reservation-system)

Medium1 co.

Medium

[consistency](/topics?open=system-design-consistency#system-design-consistency)[inventory by date](/topics?open=system-design-inventory-by-date#system-design-inventory-by-date)+2

also at 0 more

[Note](/system-design/hotel-reservation-system&focus=notes)

21

[21.Stock Exchange / Order Matching Engine](/system-design/stock-exchange)

Hard1 co.

Hard

[deterministic replay](/topics?open=system-design-deterministic-replay#system-design-deterministic-replay)[low latency](/topics?open=system-design-low-latency#system-design-low-latency)+3

also at 0 more

[Note](/system-design/stock-exchange&focus=notes)

22

[22.Metrics Monitoring & Alerting System (Datadog / Prometheus)](/system-design/metrics-monitoring-alerting)

Hard1 co.

Hard

[aggregation](/topics?open=system-design-aggregation#system-design-aggregation)[downsampling](/topics?open=system-design-downsampling#system-design-downsampling)+2

also at 0 more

[Note](/system-design/metrics-monitoring-alerting&focus=notes)

23

[23.Ad Click Event Aggregation](/system-design/ad-click-aggregation)

Hard1 co.

Hard

[exactly-once](/topics?open=system-design-exactly-once#system-design-exactly-once)[lambda vs kappa](/topics?open=system-design-lambda-vs-kappa#system-design-lambda-vs-kappa)+2

also at 0 more

[Note](/system-design/ad-click-aggregation&focus=notes)

24

[24.Twitter / X (tweets, timeline, search)](/system-design/twitter-timeline-and-search)

Hard1 co.

Hard

[fan-out](/topics?open=system-design-fan-out#system-design-fan-out)[inverted index](/topics?open=system-design-inverted-index#system-design-inverted-index)+2

also at 0 more

[Note](/system-design/twitter-timeline-and-search&focus=notes)

25

[25.Photo Sharing App (Instagram)](/system-design/photo-sharing-app)

Medium1 co.

Medium

[CDN](/topics?open=system-design-cdn#system-design-cdn)[feed](/topics?open=system-design-feed#system-design-feed)+2

also at 0 more

[Note](/system-design/photo-sharing-app&focus=notes)

26

[26.Real-time Gaming Leaderboard](/system-design/realtime-leaderboard)

Medium1 co.

Medium

[ranking](/topics?open=system-design-ranking#system-design-ranking)[redis](/topics?open=system-design-redis#system-design-redis)+2

also at 0 more

[Note](/system-design/realtime-leaderboard&focus=notes)

27

[27.Distributed Job Scheduler (cron-as-a-service, Airflow-like)](/system-design/distributed-job-scheduler)

Hard1 co.

Hard

[DAG](/topics?open=system-design-dag#system-design-dag)[at-least-once](/topics?open=system-design-at-least-once#system-design-at-least-once)+2

also at 0 more

[Note](/system-design/distributed-job-scheduler&focus=notes)

28

[28.Email Service (Gmail-like)](/system-design/email-service)

Hard1 co.

Hard

[SMTP](/topics?open=system-design-smtp#system-design-smtp)[attachments](/topics?open=system-design-attachments#system-design-attachments)+3

also at 0 more

[Note](/system-design/email-service&focus=notes)

29

[29.Log Aggregation & Search (ELK / Splunk-like)](/system-design/log-aggregation-and-search)

Medium1 co.

Medium

[hot-warm-cold](/topics?open=system-design-hot-warm-cold#system-design-hot-warm-cold)[ingestion pipeline](/topics?open=system-design-ingestion-pipeline#system-design-ingestion-pipeline)+2

also at 0 more

[Note](/system-design/log-aggregation-and-search&focus=notes)

30

[30.Digital Wallet (Paytm / PhonePe balance & transfers)](/system-design/digital-wallet)

Hard1 co.

Hard

[ACID](/topics?open=system-design-acid#system-design-acid)[consistency](/topics?open=system-design-consistency#system-design-consistency)+3

also at 0 more

[Note](/system-design/digital-wallet&focus=notes)

31

[31.Online Coding Judge (LeetCode / HackerRank)](/system-design/online-code-judge)

Medium1 co.

Medium

[containers](/topics?open=system-design-containers#system-design-containers)[queue](/topics?open=system-design-queue#system-design-queue)+2

also at 0 more

[Note](/system-design/online-code-judge&focus=notes)

32

[32.Collaborative Document Editing (Google Docs)](/system-design/collaborative-document-editing)

Hard1 co.

Hard

[CRDT](/topics?open=system-design-crdt#system-design-crdt)[OT](/topics?open=system-design-ot#system-design-ot)+3

also at 0 more

[Note](/system-design/collaborative-document-editing&focus=notes)

33

[33.Maps & Navigation (routing, ETA)](/system-design/google-maps-navigation)

Hard1 co.

Hard

[geospatial](/topics?open=system-design-geospatial#system-design-geospatial)[graph](/topics?open=system-design-graph#system-design-graph)+2

also at 0 more

[Note](/system-design/google-maps-navigation&focus=notes)

34

[34.Live Video Streaming (Twitch / Hotstar live match)](/system-design/live-streaming-platform)

Hard1 co.

Hard

[CDN](/topics?open=system-design-cdn#system-design-cdn)[HLS](/topics?open=system-design-hls#system-design-hls)+3

also at 0 more

[Note](/system-design/live-streaming-platform&focus=notes)

35

[35.Distributed Lock / Coordination Service (ZooKeeper-like)](/system-design/distributed-lock-service)

Hard1 co.

Hard

[consensus](/topics?open=system-design-consensus#system-design-consensus)[fencing tokens](/topics?open=system-design-fencing-tokens#system-design-fencing-tokens)+3

also at 0 more

[Note](/system-design/distributed-lock-service&focus=notes)

36

[36.Pastebin / Text Sharing Service](/system-design/pastebin)

Easy1 co.

Easy

[expiry](/topics?open=system-design-expiry#system-design-expiry)[key generation](/topics?open=system-design-key-generation#system-design-key-generation)+2

also at 0 more

[Note](/system-design/pastebin&focus=notes)

37

[37.E-commerce Product Search (Amazon / Flipkart search)](/system-design/ecommerce-search)

Hard1 co.

Hard

[facets](/topics?open=system-design-facets#system-design-facets)[indexing pipeline](/topics?open=system-design-indexing-pipeline#system-design-indexing-pipeline)+2

also at 0 more

[Note](/system-design/ecommerce-search&focus=notes)

38

[38.API Gateway (auth, routing, rate limiting, observability)](/system-design/api-gateway)

Medium1 co.

Medium

[authentication](/topics?open=system-design-authentication#system-design-authentication)[resilience](/topics?open=system-design-resilience#system-design-resilience)+2

also at 0 more

[Note](/system-design/api-gateway&focus=notes)

39

[39.Recommendation System (product / video recommendations)](/system-design/recommendation-system)

Hard1 co.

Hard

[candidate generation](/topics?open=system-design-candidate-generation#system-design-candidate-generation)[feature store](/topics?open=system-design-feature-store#system-design-feature-store)+2

also at 0 more

[Note](/system-design/recommendation-system&focus=notes)

40

[40.Consistent Hashing (Data Partitioning)](/system-design/consistent-hashing)

Medium1 co.

Medium

[hashing](/topics?open=system-design-hashing#system-design-hashing)[load balancing](/topics?open=system-design-load-balancing#system-design-load-balancing)+2

also at 0 more

[Note](/system-design/consistent-hashing&focus=notes)

41

[41.Nearby Friends (Live Location Sharing)](/system-design/nearby-friends)

Hard1 co.

Hard

[geospatial](/topics?open=system-design-geospatial#system-design-geospatial)[pub/sub](/topics?open=system-design-pub-sub#system-design-pub-sub)+2

also at 0 more

[Note](/system-design/nearby-friends&focus=notes)

42

[42.S3-like Object Storage](/system-design/object-storage)

Hard1 co.

Hard

[blob storage](/topics?open=system-design-blob-storage#system-design-blob-storage)[erasure coding](/topics?open=system-design-erasure-coding#system-design-erasure-coding)+2

also at 0 more

[Note](/system-design/object-storage&focus=notes)

43

[43.Parking Lot](/system-design/lld-parking-lot)

Easy1 co.

Easy

[OOP](/topics?open=system-design-oop#system-design-oop)[factory](/topics?open=system-design-factory#system-design-factory)+2

also at 0 more

[Note](/system-design/lld-parking-lot&focus=notes)

44

[44.Elevator System](/system-design/lld-elevator-system)

Medium1 co.

Medium

[observer](/topics?open=system-design-observer#system-design-observer)[scheduling](/topics?open=system-design-scheduling#system-design-scheduling)+2

also at 0 more

[Note](/system-design/lld-elevator-system&focus=notes)

45

[45.LRU / LFU Cache](/system-design/lld-lru-cache)

Easy1 co.

Easy

[doubly linked list](/topics?open=system-design-doubly-linked-list#system-design-doubly-linked-list)[eviction](/topics?open=system-design-eviction#system-design-eviction)+2

also at 0 more

[Note](/system-design/lld-lru-cache&focus=notes)

46

[46.Splitwise (expense sharing)](/system-design/lld-splitwise)

Medium1 co.

Medium

[OOP](/topics?open=system-design-oop#system-design-oop)[debt simplification](/topics?open=system-design-debt-simplification#system-design-debt-simplification)+2

also at 0 more

[Note](/system-design/lld-splitwise&focus=notes)

47

[47.Movie Ticket Booking (BookMyShow) — LLD](/system-design/lld-movie-ticket-booking)

Medium1 co.

Medium

[OOP](/topics?open=system-design-oop#system-design-oop)[concurrency](/topics?open=system-design-concurrency#system-design-concurrency)+2

also at 0 more

[Note](/system-design/lld-movie-ticket-booking&focus=notes)

48

[48.Board Games: Tic-Tac-Toe / Snake & Ladder](/system-design/lld-tic-tac-toe-snake-ladder)

Easy1 co.

Easy

[OOP](/topics?open=system-design-oop#system-design-oop)[extensibility](/topics?open=system-design-extensibility#system-design-extensibility)+2

also at 0 more

[Note](/system-design/lld-tic-tac-toe-snake-ladder&focus=notes)

49

[49.Chess](/system-design/lld-chess)

Hard1 co.

Hard

[OOP](/topics?open=system-design-oop#system-design-oop)[command](/topics?open=system-design-command#system-design-command)+2

also at 0 more

[Note](/system-design/lld-chess&focus=notes)

50

[50.Vending Machine (State pattern)](/system-design/lld-vending-machine)

Easy1 co.

Easy

[OOP](/topics?open=system-design-oop#system-design-oop)[inventory](/topics?open=system-design-inventory#system-design-inventory)+1

also at 0 more

[Note](/system-design/lld-vending-machine&focus=notes)

Showing 1–50 of 60

### Difficulty split

* Easy8(13%)
* Medium24(40%)
* Hard28(47%)

### By type

* HLD42
* LLD18

### Top topics

* OOP12
* state7
* observer5
* strategy5
* caching4
* concurrency4
