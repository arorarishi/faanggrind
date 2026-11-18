# Rate limiting — system design fundamentals · FAANGrind

Source: https://faangrind.vercel.app/system-design/learn/rate-limiting

[All guides](/system-design/learn)

Building blocksGuide #4 4 min read 8 figures

# Rate limiting

Token bucket, leaky bucket, fixed and sliding windows, and where the limiter lives.

## Introduction

This guide explores the design and implementation of a rate limiter—a system component used to control traffic rates sent by clients or services. Rate limiters are crucial for preventing abuse, reducing costs, and ensuring the stability of server resources. Examples of their use include limiting posts, account creations, and reward claims.

## Benefits of Rate Limiting

* **Preventing DoS Attacks:** Blocking excess calls to avoid resource starvation.
* **Cost Reduction:** Limiting unnecessary requests to reduce server expenses.
* **Preventing Overloads:** Filtering out excessive requests to stabilize server performance.

## Step 1: Understanding the Problem

### Key Features

* Server-side API rate limiter.
* Support for multiple throttle rules.
* Handle large-scale systems in distributed environments.
* Option for a standalone service or application-level code.
* Inform users when throttled.

### Requirements

* Accurate request throttling.
* Minimal latency.
* Low memory usage.
* Distributed capability.
* Clear exception handling.
* High fault tolerance.

## Step 2: High-Level Design

### Placement Options

![Rate Limiting Middleware Architecture](/fundamentals/rate-limiting/rate_limiter_architecture.webp)Rate Limiting Middleware Architecture

1. **Client-Side Implementation:** Unreliable due to potential misuse.
2. **Server-Side Implementation:** Preferred for control and reliability.
3. **Middleware (API Gateway):** A flexible option for integrated rate limiting.

### Guidelines for Placement

* Evaluate current tech stack and choose efficient options.
* Select appropriate algorithms based on business needs.
* Use an API gateway if microservices are employed.
* Opt for commercial solutions if resources are limited.

## Step 3: Rate Limiting Algorithms

### 1. Token Bucket

![Token Bucket Algorithm](/fundamentals/rate-limiting/token-bucket.webp)Token Bucket Algorithm

* **Description:** Tokens are added to a bucket at a fixed rate; each request consumes a token.
* **Parameters:** Bucket size and refill rate.
* **Pros:** Easy to implement, memory-efficient, supports traffic bursts.
* **Cons:** Requires careful parameter tuning.

### 2. Leaking Bucket

![Leaking Bucket Algorithm](/fundamentals/rate-limiting/leaking-bucket.webp)Leaking Bucket Algorithm

* **Description:** Processes requests at a fixed rate using a FIFO queue.
* **Pros:** Memory-efficient, stable outflow rate.
* **Cons:** Traffic bursts may delay recent requests.

  Example: <https://github.com/uber-go/ratelimit>

### 3. Fixed Window Counter

![Fixed Window Counter](/fundamentals/rate-limiting/fixed-window-counter.webp)Fixed Window Counter

* **Description:** Divides time into fixed intervals and uses counters to limit requests.
* **Pros:** Simple, efficient for specific use cases.
* **Cons:** Traffic spikes at window edges can exceed limits.
* Sudden burst of traffic at the edges of time windows
  could cause more requests than allowed quota to go through.

![Fixed Window Issue](/fundamentals/rate-limiting/fixed-window-issue.webp)Fixed Window Issue

### 4. Sliding Window Log

![Sliding Window Log](/fundamentals/rate-limiting/sliding-window-log.webp)Sliding Window Log

* **Description:** Tracks timestamps to allow a rolling time window.
* **Pros:** Accurate rate limiting.
* **Cons:** High memory consumption.

### 5. Sliding Window Counter

![Fixed Window Counter](/fundamentals/rate-limiting/sliding-window-counter.webp)Fixed Window Counter

* **Description:** Combines fixed window and sliding log methods for smoothing spikes.
* **Pros:** Memory-efficient, handles traffic bursts.
* **Cons:** Approximation may not be perfectly strict.

## High-Level Architecture

![Architecture](/fundamentals/rate-limiting/architecture.webp)Architecture

* **Data Storage:** Use in-memory caching (e.g., Redis) for fast counter operations.
* **Steps:**
  1. Client sends request to middleware.
  2. Middleware checks counters in Redis.
  3. Request is processed or rejected based on limits.

## Advanced Considerations

### Distributed Environments

* **Challenges:** Race conditions, synchronization issues.
* **Solutions:** Use locks, Lua scripts, or sorted sets in Redis. Employ centralized data stores for synchronization.

### Performance Optimizations

* Multi-data center setups for reduced latency.
* Eventual consistency models for synchronization.

### Monitoring

* Regular analytics to ensure algorithm effectiveness and adjust rules as needed.

[PreviousThe system design interview playbook](/system-design/learn/interview-playbook)[NextConsistent hashing](/system-design/learn/consistent-hashing-explained)

## Practice this

Questions in the bank that use this guide.

* [Rate Limiter (token bucket, sliding window) — LLDLLDMedium](/system-design/lld-rate-limiter)
* [Distributed Rate LimiterHLDMedium](/system-design/rate-limiter)

## On this page

1. [Introduction](#introduction)
2. [Benefits of Rate Limiting](#benefits-of-rate-limiting)
3. [Step 1: Understanding the Problem](#step-1-understanding-the-problem)
4. [Step 2: High-Level Design](#step-2-high-level-design)
5. [Step 3: Rate Limiting Algorithms](#step-3-rate-limiting-algorithms)
6. [High-Level Architecture](#high-level-architecture)
7. [Advanced Considerations](#advanced-considerations)
