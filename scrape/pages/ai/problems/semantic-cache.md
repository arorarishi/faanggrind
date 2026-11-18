# Semantic cache for LLM responses — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/semantic-cache

[AI problems](/ai#problems)

GENAIGenAI systems#5Medium

# Semantic cache for LLM responses

cachingembeddingscostmulti-tenantinvalidation

## Problem statement

A help-assistant platform serves 500 business tenants and answers 3 million end-user questions per day with a hosted LLM. Many questions repeat in different words: "how do I reset my password" and "forgot my password, what now". Design a semantic cache: it stores answers, finds a stored answer for a new question by embedding similarity, and returns it without calling the LLM. It must cut cost and latency without serving a wrong, stale or private answer, and it must never share anything between tenants.

## Requirements

### Functional

* Look up a question and return a stored answer when a close enough question was answered before, first by exact match and then by embedding similarity.
* Decide per request whether it may use the cache at all: personal, time-dependent and action requests bypass it.
* Store a fresh answer after a miss only if it passes a write check, with a time to live and the ids of the documents it was built from.
* Invalidate entries when a source document changes, when the prompt or model version changes, and when a user reports a bad answer.
* Keep every tenant's entries in a separate partition with per-tenant size limits.
* Report hit rate, false-hit rate and money saved, per tenant and in total.

### Non-functional

* Lookup adds at most 30 ms at p95 to a miss; a hit is fully returned in under 100 ms.
* 3 million requests per day: 35 QPS on average, 100 QPS at peak.
* False hits (a returned answer that does not fit the new question) under 0.5% of hits, measured by a continuous audit.
* Zero cross-tenant hits, enforced by design and tested on every deploy.
* A changed source document invalidates the entries built from it within 60 seconds.
* Overall hit rate of at least 20%, so the cache pays for its risk.

## Back-of-the-envelope estimates

**Traffic.** 3,000,000 / 86,400 s = 35 QPS on average; plan for 100 QPS at peak.

**Cost with no cache.** Each request sends 1,500 input tokens (instructions, retrieved context, question) and gets 300 output tokens. At an assumed 1 USD and 5 USD per million tokens: 0.0015 + 0.0015 = 0.003 USD per request, so 3M x 0.003 = 9,000 USD per day.

**Hit rate.** Assume 60% of requests are eligible: 1.8M per day. Assume 35% of those find a match: 630,000 hits. Overall hit rate = 0.60 x 0.35 = 21%.

**Saving.** 630,000 x 0.003 = 1,890 USD per day. The cache costs little: 1.8M lookups x 30 tokens = 54M embedding tokens, about 1 USD at an assumed 0.02 USD per million, plus 3 nodes x 24 h x an assumed 0.50 USD = 36 USD. Net saving is about 1,853 USD per day, 20.6% of spend.

**Latency.** A lookup is 15 ms to embed plus 10 ms to search = 25 ms. A full answer takes 600 ms to the first token plus 300 tokens at an assumed 60 tokens per second = 5.6 s.

**Storage.** 1.8M - 0.63M = 1.17M new entries per day. With an average life of 3 days, 3.51M entries are live. One entry is a 768 x 4 = 3,072-byte vector plus about 1,700 bytes of text and metadata, 4,772 bytes. Total: 3.51M x 4,772 = 17 GB, which fits in memory on one node, replicated three times.

**The price of a loose threshold.** The 35% above assumes a strict threshold with 0.3% false hits: 630,000 x 0.003 = 1,890 wrong answers per day. Suppose a looser threshold gives a 45% match rate and 2% false hits: 810,000 hits, 16,200 wrong answers, 2,430 USD saved. The strict setting gives up 540 USD per day to avoid 14,310 wrong answers, about 0.04 USD each. Keep the strict setting.

## API

```
POST /v1/cache/lookup
  body: { tenant_id, scope, question, locale, model, prompt_version }
  200:  { hit: true, entry_id, answer, tier: "exact" | "semantic" | "verified",
          similarity, age_s }
      | { hit: false, reason: "ineligible" | "no_match" | "verifier_rejected",
          lookup_token }

POST /v1/cache/store               (after a miss, when the answer is complete)
  body: { lookup_token, answer, source_doc_ids[], used_user_data,
          tools_called[], ttl_class: "static" | "product" | "volatile" }
  200:  { stored: true, entry_id } | { stored: false, reason }

POST /v1/cache/invalidate
  body: { tenant_id, doc_ids?: [], entry_id?, namespace? }

POST /v1/cache/feedback            body: { entry_id, rating: "up" | "down" }
GET  /v1/cache/stats?tenant_id=    -> { hit_rate, false_hit_rate, usd_saved, entries }
```

## Data model

```
cache_entries(entry_id PK, tenant_id, scope_hash, namespace,
              question, embedding VECTOR(768), answer,
              source_doc_ids[], ttl_class, created_at, expires_at,
              hit_count, last_hit_at, down_votes)
  -- namespace = model + prompt_version + embedding_model_version
  -- scope_hash = audience of the answer: anonymous, plan tier, role

exact_index:   hash(tenant_id, scope_hash, namespace, locale,
                    normalised question) -> entry_id        -- key-value, with TTL
vector_index:  one partition per tenant_id, HNSW, cosine;
               filter on scope_hash, namespace, locale
doc_to_entries(tenant_id, doc_id) -> entry_id[]              -- reverse index

lookup_log(lookup_id, tenant_id, tier, similarity, entry_id,
           verifier_result, audit_verdict, created_at)
labelled_pairs(question_a, question_b, similarity, same_answer)   -- threshold tuning
```

## High-level design

**Read path**

1. The cache sits in the LLM gateway, in front of retrieval and generation. A follow-up such as "and for the annual plan?" is first rewritten into a standalone question. If that is not possible, the request bypasses the cache.
2. An eligibility gate runs rules and a small classifier. Personal requests ("where is my order"), time-dependent requests ("is the service down right now"), requests that trigger an action and creative requests bypass the cache. When in doubt, bypass.
3. Exact tier: normalise the question (lower case, trimmed spaces and punctuation), hash it with tenant, scope, namespace and locale, and read a key-value store. This takes about 1 ms and can never return another question's answer.
4. Semantic tier: embed the question and search the tenant's partition for the 5 nearest stored questions, filtered by scope, namespace and locale.
5. Decide on the best candidate's cosine similarity. At 0.97 or more it is a hit. Between 0.90 and 0.97 a verifier checks the pair. Below 0.90 it is a miss. These values belong to one embedding model and are tuned on labelled pairs.
6. On a hit, return the stored answer in streamed pieces so the client behaves the same, and mark the trace as cached.

**Write path**

7. On a miss, the normal pipeline answers. When the answer is complete, a write gate reads the trace. It stores the answer only if no user-specific data or tool was used, no guardrail fired, the answer is not a refusal or an error, and the stream finished.
8. The entry is written with its expiry time, its source document ids and a reverse-index row per document.

**Invalidation and audit**

9. Document-change events delete dependent entries through the reverse index. A new prompt, model or embedding model changes the namespace, so old entries are never read again. A thumbs-down evicts the entry.
10. An auditor regenerates 1% of hits in the background and a judge model compares the two answers. This gives the live false-hit rate.

## Architecture diagram

Rendering diagram…

## Deep dives

### The threshold and false hits

Similar wording is not the same question. "How do I cancel my order?" and "How do I cancel my subscription?" differ by one word and have different answers. So do "can I return it within 30 days" and "can I return it after 30 days". Sentence embeddings place both pairs very close, because they capture topic better than negation, numbers and names.

Three defences, in order:

* Tune the threshold on labelled pairs from your own traffic, for a precision target (99.5% here), never for hit rate.
* In the grey band, run a verifier: a cross-encoder that reads both questions together, about 20 ms. It only runs on near matches.
* An entity guard: numbers, product names and negation words must be the same in both questions, or it is a miss.

A false hit costs more than a miss: a miss costs 0.003 USD, a wrong refund answer costs a support ticket.

### What must never be cached

Do not try to list bad questions. Decide at write time from the trace of how the answer was made. If the pipeline read an account record, called a tool, or retrieved a document that only this user can open, the answer is personal and is not stored. Answers that depend on the clock (prices, stock, outages, "today") get the `volatile` class, which is not stored at all. Refusals, errors, guardrail blocks and cut-off streams are not stored either, or one bad answer gets replayed thousands of times.

### Invalidation and TTL

Three mechanisms cover different causes of staleness.

* TTL by class: 7 days for static policy answers, 24 hours for product information.
* Events: every entry lists its source documents. When one changes, the reverse index finds and deletes its entries within seconds. Without this, an edited refund policy stays wrong until the TTL runs out.
* Namespaces: the key includes the model, prompt version and embedding model version. A change makes every old entry unreachable in one step, with no mass delete.

### Tenant isolation

Each tenant has its own partition, and the lookup code takes the tenant id from the authenticated session, never from the request body. A shared pool is tempting because "reset password" looks generic, but every tenant's answer differs, and it leaks through timing: a 30 ms answer reveals that someone already asked this. Inside a tenant, the scope hash separates audiences, so an admin-only answer never reaches an anonymous visitor.

### Three caches that are often confused

| Cache | Matches on | What it skips | Risk |
| --- | --- | --- | --- |
| Exact-match | Hash of the normalised request | The whole LLM call | None, if the key holds every input |
| Semantic | Embedding similarity above a threshold | The whole LLM call | False hits |
| Provider prompt cache | An identical prompt prefix | Re-processing the prefix; the output is still generated | None |

They stack. A semantic miss still gets cheaper input tokens from the prompt cache when the stable instructions come first in the prompt.

## Evaluation

**Offline: tune the threshold.** Sample 10,000 question pairs from the logs, spread evenly across similarity bands from 0.80 to 1.00. Label each pair: would the first question's answer be acceptable for the second? Use human labels for 1,000 pairs and a judge model for the rest, checked against the human labels. For each candidate threshold report precision (the share of hits that are correct) and match rate. Pick the lowest threshold that meets 99.5% precision. Report by tenant and by language, because one global threshold hides weak segments.

**Shadow mode.** Before serving a single cached answer, run the cache in shadow for one week: do the lookup, still call the LLM, and let a judge compare the cached answer with the fresh one. This measures the false-hit rate on live traffic with no user impact.

**Online A/B.** Randomise by user within a tenant. Compare cost per request, p50 and p95 latency, thumbs-down rate, re-ask rate (the same user asks again within 2 minutes) and escalation to a human agent. Compare hits against misses directly: a higher thumbs-down rate on hits means the threshold is too loose.

**Continuous audit.** Regenerate 1% of hits and judge them. Alert when the false-hit rate passes 0.5%, and lower the affected tenant's hit band automatically.

**Guardrails.** A deploy test plants a canary question in tenant A and checks that tenant B never gets it back. Track the hit rate per entry: one entry serving a sudden large share of traffic gets a human look.

## Bottlenecks & mitigations

* The embedding call is on the path of every eligible request, hit or miss. It needs its own low-latency pool and a small exact cache of recent query embeddings.
* A low hit rate: below about 10% the saving no longer covers the engineering and the risk. Measure it in shadow mode before building further.
* Write volume: 1.17 million new entries per day, most of them never read again. Admit an entry only on the second sighting of a question, and evict by least recent use within each tenant's quota.
* Invalidation fan-out: one popular policy document can have tens of thousands of dependent entries to delete at once.
* The verifier runs on every grey-band candidate and needs its own capacity at peak.

## Failure modes

* **False hit.** A stored answer is returned for a question that only looks similar. Mitigation: a precision-tuned threshold, the verifier, the entity guard, and the 1% audit with an alert.
* **Stale answer.** The source document changed and the entry lives on. Mitigation: event invalidation through the reverse index, short TTLs for product information, and the answer's age in the trace.
* **Private answer stored.** A reply that contains one user's order status is cached and shown to another user. Mitigation: the write gate reads the trace and refuses anything that touched user data or tools. A PII scan on the answer text is the second check.
* **Cross-tenant leak.** A bug searches the wrong partition. Mitigation: the tenant comes from the session, partitions are physically separate, and a canary test runs on every deploy.
* **Poisoned entry.** A wrong, refused or manipulated answer is stored and replayed to thousands of users. Mitigation: store only answers that passed guardrails, evict on thumbs-down, and cap how long any entry can live.
* **Cache stampede.** A popular entry expires and 200 identical requests all miss at once. Mitigation: one request regenerates while the others wait for it, and a little random jitter is added to each TTL.
* **Version mix.** The prompt changes tone or policy and old answers are still served. Mitigation: the prompt and model versions are part of the namespace.
* **Cache store down.** Mitigation: the lookup has a 50 ms timeout and fails open to the LLM. Cost rises, answers stay correct.

## Follow-up questions interviewers ask

* Your hit rate is 6%. How do you find out whether to raise it or to remove the cache?
* How would you cache answers in a multi-turn conversation, where the same words mean different things in different chats?
* Two tenants have identical public FAQs. Would you ever share entries between them?
* How do you choose the threshold again after changing the embedding model?
* Could you return a cached answer and still personalise it, for example with the user's name or plan?
* How does this change if answers come from an agent that calls tools?

## Lessons that cover this

* [#7Prompting and context engineeringBuild with LLMs](/ai/learn/prompting-context-engineering)

## Further reading

* [FrugalGPT: How to Use Large Language Models While Reducing CostPaperarxiv.org](https://arxiv.org/abs/2305.05176)
* [Sentence-BERTPaperarxiv.org](https://arxiv.org/abs/1908.10084)
* [Prompt caching (Claude Platform documentation)Guideplatform.claude.com](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousLLM gateway with routing, caching and fallback](/ai/problems/llm-gateway)[NextChatbot with long-term memory](/ai/problems/chatbot-with-memory)

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
