# Online Coding Judge (LeetCode / HackerRank) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/online-code-judge

[All system design questions](/system-design)

#31HLDMediumHigh-level design

# Online Coding Judge (LeetCode / HackerRank)

sandboxingqueuecontainersresource limits

## Problem statement

Design a platform where users submit code in many languages against problems with hidden test cases, and get a verdict (Accepted / Wrong Answer / TLE / MLE / RE) within seconds — securely running untrusted code at scale.

## Requirements

### Functional

* Problems with statements and hidden test cases; multiple languages.
* Submit code; receive verdict, runtime and memory per test.
* Run custom input (playground) without judging.
* Contests: fixed window, leaderboard, penalty rules.

### Non-functional

* Verdict within 5–10 s for typical submissions; fairness (same hardware class).
* Security: untrusted code must not access network, other users' data, or the host.
* Scale: 1M submissions/day; contest bursts of 10k submissions/min.
* Reproducible verdicts (same result on re-run).

## Back-of-the-envelope estimates

* 1M/day ≈ 12/s average; contest peak ~170/s.
* Each run: compile 1–5 s + tests (20 × 1 s worst) → budget ~10 s CPU → 170/s × 10 s = 1,700 concurrent sandboxes at peak → ~200–400 worker nodes (8 sandboxes each) — autoscale before contests.
* Submission storage: 1M × 5 KB code + 2 KB result = 7 GB/day.
* Test data: 5k problems × 50 tests × 1 MB = 250 GB in object storage, cached on workers.

## API

```
POST /v1/submissions    { problemId, language, code, contestId? }  → 202 { submissionId }
GET  /v1/submissions/{id}   → { status: queued|running|done, verdict, time, memory, perTest[] }
WS   submission.{id}        → status updates
POST /v1/run                { language, code, stdin }            → { stdout, stderr, time }
GET  /v1/problems/{id}      GET /v1/contests/{id}/leaderboard
```

## Data model

```
problems     (problem_id, title, statement, limits:{timeMs, memoryMb}, languages[], test_bundle_key)
test_cases   (problem_id, idx, input_key, expected_key, is_sample, weight)
submissions  (submission_id, user_id, problem_id, contest_id, language, code_key, status, verdict, time_ms, mem_kb, created_at)
test_results (submission_id, test_idx, verdict, time_ms, mem_kb)
contest_scores(contest_id, user_id, score, penalty, updated_at)  + Redis ZSET for the live leaderboard
```

## High-level design

1. **Submission service** stores code (object storage), inserts `queued`, publishes to a **queue** partitioned by priority (contest > practice > playground).
2. **Judge workers** pull a submission, fetch the language image and the problem's test bundle (locally cached), and run each test in an **isolated sandbox**: a container/gVisor/Firecracker micro-VM with no network, read-only filesystem, seccomp profile, cgroup CPU/memory limits, wall-clock and CPU-time limits, process count limits, and a non-root user.
3. **Verdict**: compile errors short-circuit; tests run in order (stop at first failure for practice; all for contests if scoring is partial); compare output with a checker (exact, token-based, or a special judge program for multiple valid answers).
4. **Results** written to the DB and pushed to the client via WebSocket/polling.
5. **Contest service** updates scores on accepted verdicts and maintains a Redis leaderboard; final standings computed from the DB after the contest.
6. **Autoscaling** of worker pools by queue depth; pre-warmed pools before contests.

## Architecture diagram

Rendering diagram…

## Deep dives

**Sandbox layers**: language runtime image → container with seccomp/cgroups → gVisor or micro-VM for kernel isolation. Never run untrusted code in a plain container as root.

**Fair timing**: measure CPU time, not wall time, and pin sandboxes to dedicated cores; run on a homogeneous instance type.

**Compile once, run many**: compile in the sandbox, then fork per test with fresh limits.

**Checkers**: floating-point tolerance, unordered outputs, and multiple valid answers need a special judge; keep it as a separate program with its own limits.

**Anti-abuse**: rate limits per user; disk quota; fork-bomb protection via pid limits; kill on limit breach.

## Bottlenecks & mitigations

* Contest start burst → pre-scale worker pools; queue with priority; playground runs deprioritised.
* Test bundle downloads → per-worker cache keyed by problem version; warm popular problems.
* Sandbox startup time (~100 ms containers, ~150 ms Firecracker) → pool of pre-created sandboxes.
* DB writes for per-test results → batch per submission.

## Failure modes

* **Worker crash mid-judging**: message not acked → redelivered; judging is idempotent (results overwritten by submission id).
* **Sandbox escape attempt**: kernel isolation + no network + read-only FS; workers hold no secrets; rotate images.
* **Flaky verdict** (timing near the limit): run the failing test again once; report the better result; keep limits generous.
* **Queue outage**: submissions stay `queued` in DB; a replay job re-publishes.

## Follow-up questions interviewers ask

* How would you detect plagiarism across submissions?
* How would you support interactive problems (judge talks to the program)?
* How would you run a 100k-participant contest with < 30 s verdicts?

[PreviousDigital Wallet (Paytm / PhonePe balance & transfers)](/system-design/digital-wallet)[NextCollaborative Document Editing (Google Docs)](/system-design/collaborative-document-editing)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonGoogleAtlassianMicrosoftHackerRank

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
