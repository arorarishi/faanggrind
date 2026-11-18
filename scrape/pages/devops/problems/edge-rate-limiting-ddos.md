# Rate limiting, bot and DDoS protection at the edge — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/edge-rate-limiting-ddos

[DevOps problems](/devops#problems)

DESIGNPlatform design#14Medium

# Rate limiting, bot and DDoS protection at the edge

ddosrate-limitingwafcloudfrontedgeabuse

## Problem statement

A company runs a public JSON API and a web app on EKS behind an Application Load Balancer in AWS. Normal traffic is 5,000 requests per second. Last week two things happened in one day: a layer-7 HTTP flood of 400,000 requests per second from about 20,000 IP addresses took the site down for 40 minutes, and a scraper hammered the `/search` endpoint with 300 requests per second from one API key, filling the database connection pool. Design the edge protection: CDN, WAF, DDoS absorption, rate limits, bot controls, quotas and the runbook for the next attack.

## Requirements

### Functional

* Volumetric layer 3 and 4 floods (SYN, UDP reflection) never reach the origin; layer 7 floods are filtered before the ALB.
* Rate limits exist per IP, per API key or user, and per endpoint, with different limits for `/search`, `/login` and the rest.
* Known bad bots are blocked and suspicious clients get a challenge; real users almost never see a captcha.
* Paid API customers have daily quotas and get `429` with `Retry-After` instead of a silent block.
* The origin accepts traffic only from the edge; a direct hit on the ALB's address gets `403`.
* Operators can turn on stricter protection during an attack with one change, and see what each layer is blocking.

### Non-functional

* Survive a 400,000 requests per second layer-7 flood with the origin never above 70 percent of its capacity.
* Added latency from the edge, WAF and rate limiter under 5 ms at p50 for cache misses.
* False positives (real users blocked) under 0.1 percent of requests in normal operation.
* Edge and WAF cost under 6,000 USD per month at normal traffic, with a known cost per attack hour.
* A rate-limit rule change takes effect in under 2 minutes everywhere.
* Edge logs available for query within 5 minutes and kept for 90 days.

## Back-of-the-envelope estimates

**Origin capacity.** 20 API pods, each comfortable at 500 requests per second, give 10,000 requests per second at the origin. The flood of 400,000 requests per second is 40 times that; nothing at the origin can fix this, so blocking must happen at the edge.

**Per layer.** 400,000 requests per second from 20,000 IPs is 20 requests per second, or 1,200 per minute, per IP. A rate-based rule of 300 requests per 5 minutes per IP (1 per second) and the managed rule sets together block an assumed 95 percent once the counters warm up: 20,000 requests per second leak, mostly from IPs that rotate. A challenge (JavaScript proof then captcha) fails an assumed 90 percent of the rest: 2,000 requests per second. Add the 5,000 normal and 7,000 requests per second reach the cache. Static assets and repeated searches hit the cache an assumed 35 percent of the time, so the origin sees 7,000 x 0.65 = 4,550 requests per second, under half its capacity.

**Cost of an attack hour (assumed prices).** 400,000 x 3,600 = 1.44 billion edge requests. CloudFront at 0.0075 USD per 10,000 HTTPS requests: 1,080 USD. WAF at 0.60 USD per million requests evaluated: 864 USD. One flood hour costs about 1,950 USD, which is why Shield Advanced's cost protection matters for a company attacked often.

**Normal month.** Average 2,000 requests per second x 2,628,000 seconds (730 hours) = 5.26 billion requests: CloudFront 3,942 USD, WAF 3,154 USD, about 7,100 USD. Meeting the 6,000 USD target needs negotiated CloudFront pricing or a cheaper per-request edge.

**Central rate limiter.** 5,000 requests per second x 2 Redis commands (increment and expire in one Lua script) = 10,000 operations per second; one Redis node handles well over 100,000. Counters: 200,000 active clients x 100 bytes per key = 20 MB.

## API

```
Edge layer (CloudFront distribution + WAF web ACL, Terraform)
  origin: ALB, custom header X-Origin-Verify: <random 32 bytes> (from Secrets Manager)
  cache behaviours:
    /static/*     cache 1 day, no WAF rate rule
    /search       cache 60 s keyed on query string, rate rule: 60 req / 5 min per IP
    /api/*        no cache, rate rule 300 req / 5 min per IP, 100 req / 5 min per API key header
    /login        rate rule 20 req / 5 min per IP, action CAPTCHA above the limit

WAF web ACL rule order (first match wins):
  1. allow-list: health checkers, partners (IP set)
  2. block-list: IP set with TTL managed by the abuse job
  3. AWSManagedRulesAmazonIpReputationList, AWSManagedRulesKnownBadInputsRuleSet, Common rule set
  4. Bot Control managed rule group (common level; targeted level only during attacks)
  5. rate-based rules per path (above)
  6. "attack mode" rule, default action COUNT, switched to CHALLENGE by a Terraform variable

Gateway (API gateway service in EKS, Go)
  GET /api/v1/search?q=...        429 + Retry-After when the per-user token bucket is empty
  response headers on every call: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
  per-endpoint buckets in Redis:  key rl:{user}:{endpoint}, refill 10/s, burst 50
  daily quota:                    key quota:{apikey}:{yyyymmdd}, limit from the plan table

Runbook switches (one PR each, Argo CD syncs in under 2 minutes):
  attack_mode = true   -> challenge every request without a good bot score
  search_cache_ttl     -> raise from 60 s to 600 s
  anonymous_search     -> false (API key required for /search)
```

## Data model

```
AWS
  CloudFront distribution      origin = internet-facing ALB, TLS to origin, origin shield on
  WAF web ACL (CLOUDFRONT scope) rules above, logging to S3 via Kinesis Firehose
  Shield Standard              on by default for CloudFront, ALB and Route 53
  Shield Advanced (optional)   cost protection, layer 7 detection, response team access
  ALB security group           inbound 443 only from prefix list
                               com.amazonaws.global.cloudfront.origin-facing
  ALB listener rules           header X-Origin-Verify == secret -> forward; default -> 403
  Secrets Manager              origin-verify secret, rotated monthly, two values during rotation
  S3 bucket waf-logs           90-day lifecycle; Athena table for queries

Kubernetes
  Namespace edge
    Deployment gateway         3+ replicas, HPA on CPU and on requests per second
    ElastiCache Redis          cluster mode off, 2 nodes, rate counters and block list
    ConfigMap rate-limits      per endpoint: refill rate, burst, per-key or per-user
    CronJob abuse-scanner      reads Athena, writes IP set entries with a 24 h TTL label

Tables (PostgreSQL)
  api_keys(key_hash, customer_id, plan, status)
  plans(plan, daily_quota, rps_limit, burst)
  abuse_events(ip, apikey, reason, first_seen, last_seen, blocked_until)
```

## High-level design

**Put an edge in front of everything**

1. Move DNS for the site and the API to a CloudFront distribution (a Cloudflare-style edge works the same way). Public traffic now ends on the edge's anycast network, which has far more bandwidth than one VPC and absorbs layer 3 and 4 floods before any packet reaches the origin.
2. Lock the origin down. The ALB security group allows 443 only from the managed prefix list `com.amazonaws.global.cloudfront.origin-facing`, and a listener rule forwards only requests carrying the secret `X-Origin-Verify` header that CloudFront adds; the default rule returns a fixed 403.

**Filter at the edge**

3. Attach a WAF web ACL with the managed rule sets (IP reputation, known bad inputs, common rules) in COUNT mode for one week, read the logs, then switch to BLOCK.
4. Add rate-based rules per path. A web ACL on CloudFront sees the client IP directly; a web ACL on the ALB behind the edge must aggregate on the forwarded IP header, or every request counts against the edge's IP. Login gets CAPTCHA above the limit, search gets BLOCK.
5. Turn on Bot Control at the common level, which labels known good bots (search engines, monitors) and blocks obvious bad ones by signature. Keep the targeted level, with device fingerprinting and challenges, behind the attack-mode flag because it costs more and adds friction.

**Limit again at the gateway**

6. The API gateway in EKS applies a token bucket per user and per endpoint, counters in Redis through one Lua script so increment and expiry are atomic. It returns 429 with `Retry-After` and the `X-RateLimit-*` headers.
7. Each backend service sets its own concurrency limit (a semaphore of, say, 64 in-flight requests per pod) and a database connection pool cap, so a client that passes every outer check still cannot pin the database.

**Quotas and abuse**

8. Paid keys carry a plan with a daily quota; a nightly job resets counters and a second job scans WAF logs for IPs that tripped rules more than 50 times in an hour and writes them to the block-list IP set with a 24 hour expiry.

**Cache and scale**

9. Cache search results for 60 seconds at the edge keyed on the normalised query string, cache static assets for a day, and enable origin shield so one edge miss is one origin request.
10. The HPA scales gateway and API pods on requests per second, and Karpenter adds nodes, but this is the last line, not the plan: autoscaling takes minutes and costs money, the edge blocks in milliseconds.

**Observe and rehearse**

11. Ship WAF and CloudFront logs to S3, dashboard requests blocked per rule, cache hit ratio, 429 rate per endpoint and origin latency, and load test the switches every quarter.

## Architecture diagram

Rendering diagram…

## Deep dives

### Token bucket or sliding window, local or central

A token bucket holds up to `burst` tokens and refills at `rate` per second; a request takes one token or gets a 429. A sliding window counts requests in the last N seconds. The bucket allows short bursts, which real clients need (a page loads 20 API calls at once); the window gives a flat ceiling, which protects a fragile endpoint better. This design uses buckets at the gateway (burst 50, refill 10 per second per user) and WAF's window counting at the edge. Where the counter lives matters more than the algorithm. A local in-memory counter per gateway pod is fast and has no dependency, but with 6 pods behind a load balancer a client gets roughly 6 times the limit. A central Redis counter is exact and costs one round trip, around 0.5 ms inside a zone. The usual answer is both: a loose local limit as a safety valve if Redis is down, the exact one in Redis. The Lua script does `INCR` and sets `EXPIRE` on the first hit in one call, so the counter cannot leak when a pod dies between the two commands.

### Captcha friction against protection

A captcha stops almost every simple flood, and it also makes some real users leave: login and checkout conversions drop measurably when a challenge appears. So challenges are applied by category, not everywhere. Known good bots (verified by Bot Control's signature and reverse DNS) are never challenged. Browsers first get a silent JavaScript challenge that a headless script fails without a human noticing. Only clients that fail that, or that cross a rate limit on `/login`, see a captcha. API clients cannot solve a captcha at all, so for `/api/*` the answer is an API key, a quota and a 429, never a challenge. Attack mode flips the default for anonymous web traffic to "challenge first" for the duration of the attack, and the dashboard shows the challenge solve rate so operators know how many real users are being hurt.

### Layer 3 and 4 against layer 7, and who absorbs what

A SYN flood or a UDP reflection attack is measured in gigabits per second and packets per second; it does not care what the application does. The edge network and Shield Standard absorb these because they are spread over many points of presence with far more capacity than any one VPC, and because a TCP handshake that never completes never leaves the edge. A layer 7 flood is different: each request is a valid HTTP call that costs the origin CPU, a database query, maybe a cache miss. The only defence is to decide, per request, whether to serve it, and that decision must happen where capacity is cheap: WAF rules, rate counters and challenges at the edge. The origin's own defences (concurrency caps, timeouts) exist so that whatever leaks through degrades gracefully instead of taking the database down with it.

### Origin lockdown

An edge is worthless if the attacker finds the ALB's own hostname in old DNS records or certificate transparency logs and sends the flood there. Two controls, both needed. The security group allows 443 only from the CloudFront managed prefix list, which blocks everything else at layer 4 and costs 55 of the 60 default rule slots, so put nothing else in that group. The listener rule requires the secret header that CloudFront injects, which stops traffic that comes through another CloudFront distribution owned by someone else, because the prefix list is shared by every CloudFront customer. The header secret rotates through Secrets Manager with two values valid during rotation so a deploy never breaks the path.

## Evaluation

**SLIs.** Origin requests per second as a fraction of capacity (alert at 70 percent); edge block rate per rule; 429 rate per endpoint (a jump without an attack means a bad limit); challenge solve rate (under 70 percent for browsers means real users are being blocked); cache hit ratio for `/search`; p50 and p99 latency added by the edge measured from synthetic probes in three regions.

**Attack rehearsal.** Twice a year, run a 50,000 requests per second layer-7 test from a load generator in another cloud against staging with production rules: confirm the rate rules block within 2 minutes, attack mode switches in under 2 minutes, and the origin stays below 70 percent. Separately hit the ALB hostname directly and confirm a 403.

**False positive review.** Weekly query over WAF logs: top blocked IPs, top blocked API keys, blocks by rule. Any paying customer in the top 20 means a limit is wrong or the customer needs a higher plan.

**Cost review.** Monthly: CloudFront and WAF requests, Bot Control hours, Shield Advanced fee against the cost of the last attack hour.

**Security checks.** The origin-verify secret rotated in the last 30 days; the block-list job removes entries after their TTL; WAF logs do not contain full request bodies with credentials.

**What a strong answer adds.** The candidate separates the three layers and the three kinds of limit, says where the counters live and why, knows that layer 3 and 4 floods are absorbed and layer 7 is filtered, and has a runbook with an order: cache up, attack mode on, anonymous search off, block list, then scale.

## Bottlenecks & mitigations

* One Redis node for the central counters: at 10,000 operations per second it is far from its limit, but a Redis outage must fail open at the gateway with the local limit, or every request becomes a 500.
* The `/search` endpoint's database cost: caching and the per-endpoint bucket exist because one scraper can exhaust the connection pool before any IP limit trips.
* WAF rule capacity: Bot Control and several rate rules with custom keys use many web ACL capacity units; order rules so cheap blocks run first.
* The ALB security group: the prefix list uses 55 rule slots, so a second prefix list or extra CIDRs needs a quota increase.
* Rate-based rules are approximate and take time to warm up, so the first minute of a flood leaks; the cache and concurrency caps cover that minute.

## Failure modes

* **Attacker hits the ALB hostname directly.** The edge is bypassed. Mitigation: prefix list on the security group plus the secret header rule; alert on any non-edge request reaching the ALB.
* **Rate limit keyed on the wrong IP.** A WAF attached to the ALB behind the edge sees the edge's IP and one rule blocks everyone. Mitigation: aggregate on the forwarded IP header for regional web ACLs, and test from two home connections before enabling BLOCK.
* **Redis down.** Gateway cannot count. Mitigation: fail open to the local per-pod limit, alert, and keep the edge rules as the hard ceiling.
* **A partner's crawler is blocked.** Revenue stops. Mitigation: allow-list IP set evaluated first, per-key plans with higher limits, 429 with `Retry-After` instead of silent drops.
* **Attack mode left on for a week.** Conversions fall and nobody notices. Mitigation: the flag has an expiry annotation and a daily reminder; challenge solve rate on the dashboard.
* **Cache serves a personalised search to the wrong user.** Mitigation: cache only anonymous `/search` with `Vary` on the auth header disabled by never caching authenticated responses; cache key includes the normalised query only.
* **Origin-verify secret rotated with one value.** Every request gets 403 for the deploy window. Mitigation: two valid values during rotation, rotation tested in staging.
* **Autoscaling is the plan.** The HPA scales to 200 pods, the database falls over, the bill triples. Mitigation: concurrency caps, pool caps, and max replicas sized to the database, not to the flood.

## Follow-up questions interviewers ask

* The attacker switches to 50,000 distinct residential IPs sending 2 requests per second each, under every rate limit. What do you change?
* How do you rate limit WebSocket connections, where one connection carries thousands of messages?
* A mobile app with no JavaScript cannot solve a challenge. How do you tell it apart from a bot?
* Would you put the rate limiter in a service mesh sidecar or in the gateway, and why?
* How does the design change if the company must serve users in India with under 50 ms latency from the edge?
* Shield Advanced costs a fixed monthly fee. When is it worth it, and what does cost protection actually refund?

## Lessons that cover this

* [#4Networking for DevOps - TCP/IP, DNS, HTTP, TLS, SSHFoundations](/devops/learn/networking-for-devops)
* [#7Web servers, reverse proxies and TLS - Nginx, certificates, process managersBuild and ship](/devops/learn/nginx-reverse-proxy-tls)
* [#23Security and DevSecOps - secrets, least privilege, supply chain, policy as codeOperate](/devops/learn/security-and-devsecops)
* [#24Scaling and resilience - caching, queues, rate limiting, DDoS, DROperate](/devops/learn/scaling-and-resilience)
* [#30GPU and ML infrastructure - serving models on KubernetesLater](/devops/learn/gpu-and-ml-infrastructure)

## Further reading

* [Cloudflare: What is a DDoS attack?Articlecloudflare.com](https://www.cloudflare.com/learning/ddos/what-is-a-ddos-attack/)
* [AWS WAF developer guide: rate-based rule statementGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based.html)
* [The Tail at ScalePaperresearch.google](https://research.google/pubs/the-tail-at-scale/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousSecure container image pipeline: build, scan, sign, SBOM, admission](/devops/problems/supply-chain-image-pipeline)[NextBackup and restore for stateful workloads on Kubernetes](/devops/problems/stateful-backup-restore)

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
