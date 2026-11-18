# Hybrid retrieval and reranking service — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/hybrid-search-reranking

[AI problems](/ai#problems)

GENAIGenAI systems#2Medium

# Hybrid retrieval and reranking service

hybrid searchbm25reciprocal rank fusioncross-encoderretrieval metrics

## Problem statement

Design a shared retrieval service for a product company. Several teams call it: site search, a support chatbot and an internal RAG assistant. Given a query and filters, it returns the 10 best passages out of 30 million, in under 200 ms. It combines keyword search (BM25) with embedding search, fuses the two result lists and reranks the fused candidates with a cross-encoder. Answer generation is out of scope: this service only finds and orders passages, and it must prove its quality with retrieval metrics.

## Requirements

### Functional

* Return the top k passages (default 10) for a text query, with tenant and metadata filters applied inside both searches.
* Run BM25 and dense search in parallel, fuse the two ranked lists, then rerank the fused candidates.
* Let callers choose a mode per request: `hybrid`, `bm25` or `dense`, with reranking on or off.
* Return a debug view: each passage's rank in every stage and the time each stage took.
* Accept passage upserts and deletes and keep both indexes in step.
* Store relevance judgments and run offline evaluations that report Recall@k, MRR and nDCG for any configuration.

### Non-functional

* End-to-end latency under 200 ms at p95; without reranking under 60 ms at p95.
* 2 million queries per day: about 23 QPS on average, 60 QPS at peak.
* Quality gates on the judged set: Recall@50 of at least 0.95 for the 50 fused candidates, nDCG@10 of at least 0.70 after reranking.
* A new or edited passage is searchable in both indexes within 60 seconds.
* 99.95% availability. If the reranker or one retriever fails, the service still answers in a degraded mode and says so in the response.
* Reranking cost under 0.0005 USD per query.

## Back-of-the-envelope estimates

**Traffic.** 2,000,000 queries / 86,400 s = 23 QPS on average. Plan for 60 QPS at peak.

**Dense index.** 30M passages x 768 dimensions x 4 bytes = 92 GB as float32. HNSW links (M = 32: up to 64 neighbour ids x 4 bytes = 256 bytes per vector) add 30M x 256 bytes = 7.7 GB, so about 100 GB. With 40% headroom for deletes, growth and filter fields that is 140 GB: 3 shards of about 47 GB each, on 64 GB nodes. Scalar quantization to int8 would cut the vectors to 23 GB.

**Keyword index.** 30M passages x 200 tokens x about 4 bytes = 24 GB of text. Plan the inverted index at the same order of size, split over the same 3 shards.

**Latency budget (p95 target 200 ms).**

| Stage | Budget |
| --- | --- |
| Embed the query | 15 ms |
| BM25 and dense search in parallel, top 100 each | 30 ms |
| Fuse the lists, keep 50 | 1 ms |
| Fetch 50 passage texts | 5 ms |
| Cross-encoder reranks 50 pairs | 120 ms |
| Total | 171 ms |

That leaves 29 ms for network and queueing. The reranker takes 120 of the 171 ms (70%), so it is the stage to design around.

**Reranker GPUs.** Peak load is 60 QPS x 50 pairs = 3,000 pairs per second. Assume one GPU scores 50 pairs in 120 ms (confirm with a load test). That is 50 / 0.12 = 417 pairs per second. 3,000 / 417 = 7.2, so 8 GPUs, and 10 with 25% headroom.

**Cost.** At an assumed 1.50 USD per GPU-hour, 10 GPUs x 24 h x 1.50 = 360 USD per day. Divided by 2M queries that is 0.00018 USD per query, inside the 0.0005 USD target.

## API

```
POST /v1/search
  body: { tenant_id, query, k = 10,
          mode = "hybrid" | "bm25" | "dense",
          rerank = true,
          filters?: { source?, lang?, updated_after? },
          debug = false }
  200:  { results: [{ passage_id, doc_id, text, score,
                      ranks?: { bm25, dense, fused, reranked } }],
          degraded: null | "no_rerank" | "bm25_only" | "dense_only",
          timings_ms?: { embed, bm25, dense, fuse, fetch, rerank } }

PUT    /v1/passages/{passage_id}     body: { tenant_id, doc_id, text, metadata }
DELETE /v1/passages/{passage_id}

POST /v1/judgments                   body: { query_id, passage_id, grade: 0..3 }
POST /v1/eval/runs                   body: { query_set, config }
GET  /v1/eval/runs/{run_id}  ->  { recall_at_50, mrr_at_10, ndcg_at_10, by_query_type }
```

## Data model

```
passages(passage_id PK, tenant_id, doc_id, text, token_count,
         metadata JSON, version, updated_at, deleted)

keyword_index(term -> postings[(passage_id, term_freq)])   -- BM25, filter fields stored
vector_index(passage_id, embedding VECTOR(768), tenant_id, metadata)   -- HNSW, cosine

query_log(query_id PK, tenant_id, query, mode, config_version,
          bm25_ids[], dense_ids[], fused_ids[], reranked_ids[],
          clicked_ids[], timings_ms JSON, created_at)

eval_queries(query_id PK, query, query_type)   -- id lookup, keyword, natural language
judgments(query_id, passage_id, grade)         -- graded relevance, 0 to 3
eval_runs(run_id PK, config JSON, recall_at_50, mrr_at_10, ndcg_at_10, created_at)
```

## High-level design

**Offline path (indexing)**

1. Callers upsert passages. An indexer consumes the change stream in order and writes each passage to the keyword index and, after embedding it, to the vector index.
2. Both writes carry `tenant_id`, the filter fields and a `version`, so the two indexes can be compared and repaired. A passage counts as searchable only when both writes have landed.

**Online path (search)**

3. The API validates the request and attaches the tenant filter. A caller cannot remove it.
4. Query analysis normalises the text and detects exact-match signals: quoted phrases, ids such as `E-4012`, version strings. These are kept as they are for BM25.
5. The query embedder (a bi-encoder, which embeds query and passage separately) produces one 768-dimension vector. Popular queries come from an embedding cache.
6. BM25 search and dense search run in parallel, each with the filters applied inside the index, and each returns its top 100.
7. Reciprocal rank fusion merges the two lists into at most 200 unique passages and keeps the best 50.
8. The service fetches the 50 texts and sends 50 query-passage pairs to the cross-encoder pool, truncating each passage to 256 tokens.
9. The reranker's order is final. The service returns the top 10 and, in debug mode, every stage's ranks and timings.
10. Each stage has its own timeout. If the reranker does not answer in 140 ms, the fused order is returned with `degraded: "no_rerank"`.

**Evaluation path**

11. Every request is logged with the ids each stage returned. The eval runner replays a judged query set against any configuration and reports metrics per stage, so a change is measured before it ships.

## Architecture diagram

Rendering diagram…

## Deep dives

### Two retrievers with different mistakes

Dense search matches meaning: "laptop will not switch on" finds "device does not power up". It blurs exact strings, so `E-4012` and `E-4021` land very close together. BM25 scores a passage by how often the query's words occur in it, with more weight for rare words. It finds the exact code and misses every paraphrase. Their errors barely overlap, so the union has higher recall than either list alone.

### Fusion: ranks, not raw scores

The two scores are not comparable. A BM25 score has no upper limit and grows with the number and rarity of the query terms, so 12 is a weak match for one query and a strong match for another. Cosine similarity lies between -1 and 1, and one model's results usually sit in a narrow band such as 0.60 to 0.85. Add them and BM25 decides everything.

A weighted sum works only if each list is rescaled per query (min-max or z-score) and the weight is tuned on labelled data. One outlier stretches the scale, and the weight goes stale when the embedding model changes.

Reciprocal rank fusion (RRF) uses positions only: each passage scores the sum of 1 / (60 + rank) over the lists it appears in. A passage ranked 30th in both lists scores 2/90 = 0.0222. A passage ranked 1st in one list and absent from the other scores 1/61 = 0.0164. Agreement wins and nothing needs tuning. The price: RRF discards margins, so a runaway exact-id hit looks like any other rank 1. That is why the fused list is cut at a generous 50 and the reranker decides the final order.

### The cross-encoder and its budget

A cross-encoder reads the query and one passage together and outputs one score. Nothing can be precomputed, so cost = pairs x tokens per pair. The levers:

* Candidates: 50 pairs fit the budget. 100 pairs take about 240 ms on the same GPU.
* Length: truncate passages to 256 tokens. Halving the tokens at least halves the time.
* Model: a smaller distilled reranker trades some nDCG for speed. Check on the judged set.
* Batching: one batch per query, merged across concurrent queries on the GPU server.

### Reading the metrics

Take one query whose two relevant passages sit at ranks 2 and 5.

* Recall@k: share of relevant passages in the top k. Recall@10 = 2/2 = 1.0.
* MRR (mean reciprocal rank): 1 / rank of the first relevant result, averaged over queries. Here 1/2 = 0.5.
* nDCG@k: each hit is discounted by log2(rank + 1), then divided by the ideal order. DCG = 1/log2(3) + 1/log2(6) = 0.631 + 0.387 = 1.018. Ideal = 1 + 0.631 = 1.631. nDCG = 0.62.

Read them per stage. Low Recall@50 after fusion is a retrieval problem: the reranker cannot return a passage it never received. High recall with low nDCG@10 points at the reranker.

## Evaluation

**Judged set.** Sample 1,000 queries from the log, stratified by type: id lookups, short keyword queries and natural-language questions. For each query, pool the top 20 from BM25, dense and the current production order, and grade every pooled passage from 0 to 3. An LLM judge can do the first pass, checked against 200 human-graded pairs. Pooling matters: if only one system's results are judged, every new system looks worse because its new finds are unlabelled.

**Offline metrics, per stage.** Recall@100 for each retriever alone, Recall@50 after fusion, then nDCG@10 and MRR@10 after reranking. Report each by query type. An average can hide a collapse on id lookups.

**Ablations.** Run the same set with `bm25`, `dense`, hybrid without reranking and the full pipeline. Each stage has to earn its latency.

**Online.** Click-through rate on the top 3, mean reciprocal rank of the first click, zero-click rate, reformulation rate (a new query within 30 seconds) and the share of degraded responses.

**A/B setup.** For ranking changes, interleave: mix the results of the old and new ranker in one list and count which side gets the clicks. It needs far less traffic than a split by user. Change one stage at a time.

**Guardrails.** p95 latency per stage with alerts, a canary set of 50 id queries that must return the exact passage at rank 1, and a tenant-isolation test that runs on every deploy.

## Bottlenecks & mitigations

* The reranker pool: 3,000 pairs per second at peak fills 8 of the 10 GPUs, and reranking is 120 ms of every 171 ms. A slow GPU node shows up at once in p95.
* Dense search with a selective filter: when a tenant owns a tiny share of the 30M passages, the graph walk visits many nodes that fail the filter.
* Fetching 50 passage texts per query: 3,000 point reads per second at peak, so texts need an in-memory cache or a fast key-value store.
* Dual writes: the keyword and vector indexes drift apart when one write fails, and a passage found by one retriever only loses the agreement bonus in RRF.
* Query embedding on a cold cache adds 15 ms to every request and needs its own small GPU or CPU pool.

## Failure modes

* **Reranker pool overloaded or down.** GPU capacity is sized for 60 QPS and a traffic spike or node loss pushes latency past the budget. Mitigation: a 140 ms timeout (the 120 ms budget plus 20 of the 29 ms of slack), return the fused order with `degraded: "no_rerank"`, and shed load by reranking 20 candidates before skipping entirely.
* **Exact-match query answered with near matches.** The embedding model pulls in passages about similar ids and RRF rewards agreement. Mitigation: detect id-like tokens, require the BM25 exact hit to stay in the candidate set, and track the id-lookup slice of the judged set.
* **Index drift.** A passage is deleted from one index and still served by the other. Mitigation: one ordered change stream, a version on every write, and a nightly job that compares id sets and repairs differences.
* **Embedding model changed on one side only.** Queries are embedded with a new model while passages still hold old vectors, and dense recall drops with no error raised. Mitigation: store the model version in the index and reject a query vector whose version does not match.
* **Filter leak across tenants.** A code path searches without the tenant filter. Mitigation: the filter is added by the API layer, never by the caller, and a deploy-time test queries each tenant for another tenant's canary passage.
* **Reranker truncation hides the answer.** The relevant sentence sits after token 256 of a long passage. Mitigation: index shorter passages, or score overlapping windows and keep the best window's score.
* **Metrics look good and users are unhappy.** The judged set has aged and no longer matches live queries. Mitigation: refresh 10% of the set from recent logs every month and watch the online reformulation rate.

## Follow-up questions interviewers ask

* Recall@50 after fusion is 0.97 but nDCG@10 is only 0.55. What do you look at first?
* How would you weight BM25 and dense search differently for different query types, and how would you prove it helps?
* The product team wants p95 under 100 ms. What do you cut or change?
* How does a late-interaction model such as ColBERT compare with a bi-encoder plus a cross-encoder?
* The corpus grows from 30 million to 3 billion passages. Which stage breaks first?
* How do you build relevance judgments when you have no click data yet?

## Lessons that cover this

* [#8Vector DBs and RAGBuild with LLMs](/ai/learn/vector-dbs-rag)

## Further reading

* [Dense Passage Retrieval for Open-Domain Question AnsweringPaperarxiv.org](https://arxiv.org/abs/2004.04906)
* [Sentence-BERTPaperarxiv.org](https://arxiv.org/abs/1908.10084)
* [BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval ModelsPaperarxiv.org](https://arxiv.org/abs/2104.08663)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousRAG pipeline for internal docs Q&A](/ai/problems/rag-pipeline)[NextAgentic research assistant with multi-step retrieval](/ai/problems/agentic-research-assistant)

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
