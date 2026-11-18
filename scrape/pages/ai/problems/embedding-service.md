# Embedding service at scale — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/embedding-service

[AI problems](/ai#problems)

MLSDML system design#26Medium

# Embedding service at scale

embeddingsdynamic batchinglength bucketingcachingmodel versioninggpu inference

## Problem statement

Design an embedding service: one API that turns text into vectors for every search and RAG system in a company. It runs a 110-million-parameter encoder with 768 output dimensions and a 512-token input limit. Two kinds of load arrive. Online search queries come at 2,000 per second and need an answer within tens of milliseconds. Bulk jobs embed or re-embed a corpus of 125 million chunks, 50 billion tokens, within a day. Every vector must be reproducible and labelled with the model version that made it.

## Requirements

### Functional

* A synchronous endpoint: 1 to 32 texts in, one vector per text out.
* Bulk jobs that read input files from object storage, write vector files, can resume after a failure and have a deadline.
* A cache keyed by content hash, so the same text is not embedded twice under the same model version.
* Several model versions served at once, with the version returned beside every vector.
* An explicit truncation policy: an input over 512 tokens is rejected or truncated, and the response says which.
* Per-team quotas and usage counted in tokens.

### Non-functional

* Online lane: 2,000 queries per second at peak, p99 latency under 50 ms for a single input of up to 128 tokens.
* Bulk lane: 50 billion tokens in 24 hours. A failed worker loses at most one shard, about 200 seconds of GPU work.
* 99.95% availability online. The bulk lane may pause, and it must never slow the online lane.
* The same text and version give the same vector, cosine similarity of at least 0.9999, whatever the batch, lane or replica.
* Padding wastes under 10% of the tokens computed in the bulk lane.
* A full re-embed of the corpus costs under 200 USD of GPU time at the assumed price.

## Back-of-the-envelope estimates

**Model.** 110 million parameters x 2 bytes (FP16) = 0.22 GB. Memory is not the limit. GPU time is.

**Speed (assumption, to be measured).** One 24 GB GPU computes 100,000 tokens per second, padding included. A pass of 1,024 tokens takes about 10 ms. A pass of 16,384 tokens takes 164 ms.

**Bulk lane.** 125 million chunks x 400 tokens = 50 billion tokens. 50 billion / 100,000 = 500,000 GPU-seconds = 139 GPU-hours. With 10% lost to padding: 139 / 0.9 = 154 GPU-hours. To finish in 24 hours: 154 / 24 = 6.4, so 7 GPUs. At an assumed 1 USD per GPU-hour that is 154 USD.

**Online lane.** 2,000 queries x 20 tokens = 40,000 tokens per second, under half of one GPU. Latency and availability size this lane, not throughput. A full online pass holds 32 queries padded to 32 tokens, 1,024 tokens, so one GPU tops out near 32 / 0.010 = 3,200 queries per second. Use 3 GPUs in 3 zones: 667 queries per second each, and any 2 can carry the peak at 1,000 each.

**Latency budget.** Tokenize and cache lookup 2 ms, batching wait up to 5 ms, wait for the pass already running up to 10 ms, own pass 10 ms, network 5 ms: 32 ms in the worst case.

**Why two lanes.** One bulk pass takes 164 ms. An online query stuck behind it has already used 3 times its 50 ms budget.

**Always-on cost.** 3 GPUs x 1 USD x 720 hours = 2,160 USD per month, 14 times the cost of one full backfill.

**Outputs.** 125 million x 768 x 4 bytes = 384 GB of float32 vectors. One cache entry is 768 x 4 = 3,072 bytes, so 10 million cached queries take 30.7 GB.

## API

```
POST /v1/embeddings                          online lane
  body: { model: "text-embed" | "text-embed@v3",
          input: [text, ...],                1 to 32 texts
          input_type: "query" | "document",
          truncate: "error" | "end" }
  ->    { model_version: "text-embed@v3", dimensions: 768,
          data: [{ index, embedding[768], token_count, truncated, cached }],
          usage: { tokens } }
  errors: 400  an input is over 512 tokens and truncate is "error"
          413  more than 32 inputs; use a bulk job
          429  team is over its token quota; Retry-After

POST /v1/embedding-jobs                      bulk lane
  body: { model_version, input_uri, output_uri, input_type, truncate, deadline }
  ->    { job_id }
GET    /v1/embedding-jobs/{job_id}
  ->    { state, shards_done, shards_total, tokens_done, truncated_count, eta }
DELETE /v1/embedding-jobs/{job_id}

GET /v1/models/text-embed
  ->    { default_version, versions: [{ version, dimensions, max_tokens, status }] }
```

## Data model

```
model_versions(version PK, weights_hash, tokenizer_hash, pooling: mean,
               normalise: l2, query_prefix, document_prefix,
               max_tokens: 512, dimensions: 768, precision: fp16,
               status: shadow | live | retiring)

cache:   key   = sha256(version | input_type | normalised text)
         value = float32[768]            3,072 bytes, 30-day expiry

jobs(job_id PK, team, model_version, input_uri, output_uri, deadline,
     state, tokens_total, tokens_done)
shards(job_id, shard_id, input_range, state: pending | leased | done,
       lease_expires_at, worker_id, output_uri, row_count, truncated_count)
output file per shard: rows of (text_id, content_hash, model_version, vector)

One forward pass:
  input_ids [B, L]    attention_mask [B, L]     L = longest text in the batch
  hidden    [B, L, 768]
  embedding [B, 768] = l2_normalise( sum(hidden * mask) / sum(mask) )

Owned by the vector store:  index_id -> model_version, dimensions
```

## High-level design

**Online path (one query)**

1. The gateway authenticates the team and checks its token quota.
2. A CPU worker normalises the text, adds the query or document prefix that the model version defines, tokenizes and counts tokens. An input over 512 tokens is rejected or truncated, as the request asked.
3. The worker looks up the content hash in the cache. A hit returns at once.
4. A miss joins one of three queues by length: up to 32, up to 128 or up to 512 tokens.
5. Each queue has a dynamic batcher. It fires when the padded batch reaches 1,024 tokens or the oldest text has waited 5 ms, pads to the longest text in the batch, and runs one forward pass.
6. The server averages the hidden states of the real tokens only (mean pooling), scales the vector to length 1, writes it to the cache and returns it with the model version.

**Bulk path (one job)**

7. A job names its input files, a model version and a deadline. A planner cuts the input into shards of 50,000 chunks. One shard is 20 million tokens, 200 seconds of one GPU, and the full corpus is 2,500 shards.
8. A worker leases a shard, drops texts whose hash already has a vector, tokenizes the rest and sorts them by length. It cuts batches under a budget of 16,384 padded tokens: 32 texts of 512 tokens, or 512 texts of 32.
9. The worker writes one output file for the shard and marks it done. A shard whose lease expires is given to another worker, and writing the same file twice is harmless.
10. An autoscaler sets the bulk GPU count to tokens left / (100,000 x seconds left), on cheaper preemptible machines, and scales to zero when no job is running.
11. A loader writes the vectors into an index that is tagged with the model version.

## Architecture diagram

Rendering diagram…

## Deep dives

### Dynamic batching with length buckets

Dynamic batching fires a batch when it is full or when the oldest request has waited a maximum window. It fits embeddings because every text needs exactly one forward pass, so nothing joins or leaves halfway. The window is the latency-throughput dial. Under load it stops mattering: whatever arrived during the last 10 ms pass forms the next batch. Padding is the waste. Texts of 20, 50, 100 and 500 tokens padded to 500 compute 2,000 positions for 670 real tokens, two thirds wasted. So cap batches by padded tokens, not by count. Online, three length queues keep a 500-token document from padding 31 short queries. In bulk, sorting a whole shard by length before cutting batches brings waste under 10%.

### Two lanes, two pools

The lanes are sized by different things. Online is sized by latency and redundancy: 3 GPUs that are mostly idle. Bulk is sized by throughput: 7 GPUs for a day, then none. One shared pool would save the idle GPUs, but a single 164 ms bulk pass breaks the online p99. Keep the pools apart, and run bulk on preemptible GPUs, because losing one costs a single 200-second shard.

### Cache by content hash

The key is a hash of everything that changes the vector: model version, input type and the normalised text. Matches are exact only. Search queries repeat, so at an assumed 30% hit rate the online GPUs compute 1,400 of the 2,000 queries per second. In bulk, the hash check skips chunks that did not change since the last crawl. Normalise only what the tokenizer ignores anyway, such as Unicode form and outer whitespace. Because the version is in the key, a new version starts with an empty cache.

### Vectors from two versions must never mix

Each model version defines its own vector space. Two versions can both output 768 numbers, and the cosine between a v2 query and a v3 document is still a number, but it means nothing. No error is raised. Search quality just falls. So a version is immutable and covers weights, tokenizer, pooling, prefixes, token limit and precision. Every response, cache key and output file carries it, and an index accepts one version only. To migrate, the bulk lane builds a second index under v3 while new documents are written to both. When recall on a golden set passes, the index and its query traffic switch together. The online lane serves v2 until the last index has moved.

### Truncation

The model reads 512 tokens. A 3,000-token document that is truncated silently is embedded from its first 17%, and search never finds the rest. Default to `truncate: "error"` for documents, since chunking is the caller's job, and return `token_count` and `truncated` for every input. Queries may be cut at the end.

## Evaluation

**Correctness.** Embed 1,000 texts one at a time, then again in batches mixed with much longer texts. Every pair must have cosine similarity of at least 0.9999. This catches pooling that includes padding. Run the same check across the two lanes, across replicas, and between a cache hit and a fresh computation.

**Precision changes.** A compiled engine or a move between FP32 and FP16 shifts vectors slightly. Compare against reference vectors. If cosine similarity stays at 0.9999 or above and recall on the golden set is unchanged, keep the version. Otherwise register a new version.

**Quality of a new version.** Before a version goes live, measure Recall@10 and nDCG@10 on the company's own golden set of queries with known relevant chunks, against the current version. Public benchmarks such as MTEB are for shortlisting models, not for the final decision.

**Online load test.** Send requests at fixed arrival rates of 500, 1,000, 2,000 and 4,000 per second with the real length mix. Record p50 and p99 latency per length queue, queue wait, and the histogram of batch sizes. Sweep the wait window over 0, 2, 5 and 10 ms. With GPUs this idle, a window near 0 may win.

**Bulk test.** Measure tokens per second per GPU, the padding ratio (padded tokens divided by real tokens), shard retries, and projected finish time against the deadline. This replaces the assumed 100,000 tokens per second.

**Migration.** Compare recall of the new index with the old one on the golden set, and mirror a sample of live queries to the new index before the switch.

**Online metrics.** p99 latency per queue, cache hit rate per lane, truncation rate per team, writes rejected for a version mismatch, and the bulk lane's estimated finish time.

## Bottlenecks & mitigations

* Tokenizing on the CPU. The bulk lane needs 7 x 100,000 = 700,000 tokens per second tokenized, and GPUs sit idle if the workers have too few cores.
* Padding. Mixed lengths in one batch can waste two thirds of a pass.
* Writes downstream. 700,000 / 400 = 1,750 vectors per second arrive at the vector index, which may ingest more slowly than the GPUs produce.
* The online tail. A query can wait for a running pass and then for its own, 20 ms of the 50 ms budget.
* Response encoding. 768 floats as JSON text are several times larger than the 3,072 bytes of raw float32.

## Failure modes

* **Vectors from two versions land in one index.** A client embeds queries with v3 against a v2 index, or a backfill is half done when traffic switches. Mitigation: the version is stored on the index, writes with another version are rejected, and the query path reads the version from the index.
* **Silent truncation.** Long documents are cut at 512 tokens and no one is told. Mitigation: `truncate: "error"` by default for documents, per-input flags, a truncated count per job and an alert on the truncation rate.
* **Padding leaks into pooling.** The mean includes padded positions, so a vector changes with its batch neighbours. Mitigation: mask before averaging, and the batch-invariance test in CI and as a production probe.
* **A backfill starves online queries.** Both share GPUs or a queue. Mitigation: separate pools, and quotas on the bulk lane.
* **A preemptible GPU disappears mid-shard.** Mitigation: leases with expiry, one output file per shard, and writes that are safe to repeat.
* **The cache returns the wrong vector.** The key leaves out input type or version, so a document gets a query-prefixed vector. Mitigation: the full key, and a probe that compares cache hits with fresh results.
* **An online GPU or zone is lost.** Mitigation: 3 zones, health checks, and the remaining 2 GPUs carry the peak at 1,000 queries per second each.
* **An oversized input stalls a worker.** A 10 MB string reaches the tokenizer. Mitigation: a byte limit per input before tokenizing.

## Follow-up questions interviewers ask

* The next model version outputs 1,024 dimensions. Walk through the migration with no downtime.
* 384 GB of float32 vectors is too much for the search cluster's memory. What are your options, and what does each cost in recall?
* A re-embed must finish in 2 hours, not 24. What breaks first?
* Teams want one vector for an 8,000-token document. What changes in the model choice, the batching and GPU memory?
* When would you run the online lane on CPUs?
* A second model, tuned for code search, is added. How do you avoid doubling the fleet?

## Further reading

* [Sentence-BERTPaperarxiv.org](https://arxiv.org/abs/1908.10084)
* [MTEB: Massive Text Embedding BenchmarkPaperarxiv.org](https://arxiv.org/abs/2210.07316)
* [NVIDIA Triton Inference Server: BatchersGuidedocs.nvidia.com](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/batcher.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousMulti-tenant LoRA adapter serving](/ai/problems/multi-lora-serving)[NextVector search at billion scale](/ai/problems/vector-search-at-scale)

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
13. [Further reading](#reading)
14. [My notes](#notes)
