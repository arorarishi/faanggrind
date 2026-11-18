# Vector search at billion scale — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/vector-search-at-scale

[AI problems](/ai#problems)

MLSDML system design#27Hard

# Vector search at billion scale

annhnswivf-pqquantizationshardingfiltered search

## Problem statement

Design the vector search layer for a large marketplace. It holds 1 billion item embeddings of 768 dimensions and returns the 10 nearest items to a query vector, with optional filters such as category, seller or date. It serves 2,000 queries per second at peak with a p99 under 50 ms, and it must find at least 95% of the true nearest neighbours. Ten million items are added, changed or removed every day. Producing the embeddings is out of scope: design the index, its memory, its shards and its updates.

## Requirements

### Functional

* Return the top k nearest vectors (default 10) for a query vector, by cosine similarity on normalised vectors.
* Apply metadata filters inside the search, so a filtered query still returns k results when k matching items exist.
* Accept upserts and deletes continuously and make them visible to search within seconds.
* Build a new index version offline and switch to it with no downtime, for example after an embedding model change.
* Expose the recall and latency knobs per query, and report how many shards answered.
* Measure recall against exact search on a schedule and publish the result.

### Non-functional

* p99 latency under 50 ms at 2,000 QPS peak (40 million queries per day, about 460 QPS on average).
* Recall@10 of at least 0.95 against exact search, measured weekly on 10,000 real queries and every 5 minutes on a small canary set.
* Freshness: an upsert or delete is visible in search within 10 seconds.
* 10 million writes per day, about 116 per second.
* 99.95% availability. Losing one node per shard must not break the latency target.
* Memory and storage under 10,000 USD per month at the assumed prices below.

## Back-of-the-envelope estimates

**Raw vectors.** 1B x 768 x 4 bytes = 3,072 GB.

**Four ways to hold them, per replica.** Assume 4 USD per GB-month for RAM and 0.10 USD for NVMe SSD.

| Index | RAM | SSD | USD per month |
| --- | --- | --- | --- |
| HNSW, float32 | 3,072 + 256 = 3,328 GB | 0 | 13,312 |
| HNSW, int8 vectors | 768 + 256 = 1,024 GB | 3,072 GB | 4,403 |
| IVF-PQ, 96-byte codes | 104 GB | 3,072 GB | 723 |
| Disk graph, 64-byte codes | 64 GB | 4,096 GB | 666 |

* HNSW links: with M = 32, the bottom layer keeps 64 neighbour ids x 4 bytes = 256 bytes per vector, 256 GB.
* PQ: 96 one-byte codes plus an 8-byte id = 104 bytes per vector, 104 GB. Centroids add 65,536 x 768 x 4 bytes = 0.2 GB.
* Disk graph: a 3,072-byte vector plus 64 neighbour ids = 3,328 bytes, stored in a 4 KB block.

**Chosen layout.** IVF-PQ in 8 shards of 125M vectors: 13 GB of codes in RAM and 384 GB of full vectors on NVMe per shard. Three replicas each, on nodes with 64 GB RAM and 1 TB NVMe: 24 nodes, or 24 x 64 x 4 + 24 x 1,000 x 0.10 = 6,144 + 2,400 = 8,544 USD per month.

**Scan work.** 1B / 65,536 lists = 15,259 vectors per list, 1,907 per shard. Probing 64 lists scans 64 x 1,907 = 122,000 codes per shard, 0.1% of it. Each code costs 96 table lookups: 11.7M lookups, or 11.7 ms of one core at an assumed 1 ns each. A node serves 2,000 / 3 = 667 QPS, so 667 x 11.7 ms = 7.8 of its 16 cores are busy.

**Rescoring reads.** 667 QPS x 100 vectors = 66,700 random reads per second per node, 22% of an assumed 300,000 IOPS.

## API

```
POST /v1/collections/{name}/search
  body: { vector: float32[768], k = 10,
          filter?: { category?: [], seller_id?, created_after? },
          params?: { nprobe = 64, rescore_depth = 100 },
          min_log_offset? }                    -- read your own writes
  200:  { hits: [{ id, distance, metadata }],
          shards_ok: 8, shards_total: 8, took_ms }

POST /v1/collections/{name}/upsert   body: { items: [{ id, vector, metadata }] }
POST /v1/collections/{name}/delete   body: { ids: [] }
  200:  { log_offset }

POST /v1/collections/{name}/indexes            (offline build)
  body: { nlist = 65536, pq_bytes = 96, train_sample = 10000000 }
  202:  { index_version }
POST /v1/collections/{name}/alias    body: { serve: index_version }

GET  /v1/collections/{name}/recall
  -> { recall_at_10, p50_ms, p99_ms, nprobe, rescore_depth, measured_at }
```

## Data model

```
vector_store        id -> float32[768], metadata, version
                    -- object storage, the source of truth, 3,072 GB
write_log           (shard = hash(id) mod 8, offset, op, id, vector, metadata)

Per shard replica (125M vectors):
  centroids         float32[65,536 x 768]      201 MB, identical on every shard
  centroid_graph    HNSW over the centroids    finds the nearest lists in under 1 ms
  pq_codebook       96 sub-quantizers x 256 entries x 8 dims
  inverted_lists    list_id -> [(slot, code[96 bytes])]   RAM, append-only segments
  full_vectors      slot -> float32[768]                  NVMe, 3,072 bytes each, packed
  id_map            id -> (list_id, slot)
  tombstones        bitmap over slots
  filter_index      field value -> compressed bitmap over slots
  applied_offset    last write_log offset applied

index_versions(version, nlist, pq_bytes, built_from_offset, recall_at_10, state)
ground_truth(query_id, vector, exact_top10_ids[], snapshot_offset)
```

## High-level design

**Build path (offline)**

1. Sample 10 million vectors, 1% of the corpus. Run k-means on GPUs to get 65,536 centroids. That is 153 training points per centroid.
2. Train the product quantizer on the residuals (each vector minus its centroid): 96 sub-vectors of 8 dimensions, with 256 learned values for each.
3. Encode every vector in parallel: find its nearest centroid, store its 96-byte code in that centroid's list, and write the full vector to the NVMe file. One global set of centroids and one codebook is used by all shards, so adding a shard never needs retraining.
4. Publish the result as an immutable index version, with the write-log offset it was built from.

**Write path**

5. Upserts and deletes are appended to an ordered log, partitioned by `hash(id) mod 8`. The caller gets the offset back, and a writer copies each change into the vector store.
6. Every replica of a shard consumes its partition. An upsert picks the nearest list, encodes the vector and appends the code. A delete sets a tombstone bit. An update is a delete plus an append.
7. A background job compacts lists that hold many tombstones.

**Query path**

8. The coordinator finds the 64 nearest centroids once, using a small HNSW graph over the centroids, and sends the query, the list ids and the filter to one replica of each shard.
9. Each shard estimates how selective the filter is, then scans the 64 lists. Vectors are normalised, so the score of a code is an inner product: the sum of 96 lookups in a small table built once per query, plus the query's dot product with the list's centroid. Tombstoned and filtered slots are skipped. The shard keeps its best 100.
10. The shard reads those 100 full vectors from NVMe, computes exact distances and returns its top 10.
11. The coordinator merges 8 x 10 results. The distances are exact, so the merge is correct. If a shard has not answered after 15 ms, the request is sent to a second replica (a hedged request). At the deadline the coordinator returns what it has, with `shards_ok`.

## Architecture diagram

Rendering diagram…

## Deep dives

### What the memory arithmetic decides

**HNSW** is a layered graph. A query walks from node to node toward its target, and every hop reads a full vector at a random address, so the vectors must sit in RAM: 3.3 TB per replica. It gives the best recall for a given latency, but a build costs one graph search per insert and deletes leave holes.

**IVF-PQ** combines two ideas. IVF (inverted file) clusters the vectors into 65,536 cells and searches only the cells nearest the query. PQ (product quantization) cuts each vector into 96 pieces and replaces each piece with the id of the closest of 256 learned values: 96 bytes in place of 3,072, 32 times smaller. Code distances are approximate, so the best 100 are rescored with full vectors.

**A disk graph** keeps the graph on SSD. Each 4 KB block holds one vector and its neighbour list, and small codes in RAM steer the walk. RAM is lowest and recall is high, but every hop is an SSD read and updates are hardest.

Choose IVF-PQ with rescoring. At the table's prices, three replicas cost 2,169 USD per month against 39,936 for float32 HNSW, 18 times less. It builds in hours, writes are appends, and filters degrade gently. If the target were 0.99 recall at 10 ms, pay for a graph: a disk graph first, then HNSW over int8 vectors.

### Recall against latency, and how to measure it

Recall@10 is the share of the exact top 10 that the index returns, averaged over queries. Ground truth comes from brute force: 10,000 real queries x 1B vectors = 10^13 distance computations, or 2.8 GPU-hours at an assumed 10^9 per second per GPU.

Recall leaks in three places:

* The true neighbour's list was not probed. Fix: raise `nprobe`.
* PQ error pushed it out of the best 100 before rescoring. Fix: raise `rescore_depth` or use longer codes.
* A filter, a tombstone or an unapplied write hid it.

Sweep `nprobe` from 8 to 256 and `rescore_depth` from 50 to 500 at full load and plot recall against p99. Scan cost is linear in `nprobe` while the recall gain flattens, so take the cheapest point above 0.95.

A query also waits for the slowest of 8 shards. If each shard answers within 30 ms 99% of the time, all 8 do so only 0.99^8 = 92% of the time. Hedged requests bring the tail back.

### Filtered search

Let s be the share of vectors that pass the filter.

* Filtering after the search fails quickly. At s = 1% you need 10 / 0.01 = 1,000 results to keep 10.
* Filtering inside the scan suits IVF: check the bitmap before computing a distance. At s = 1%, 122,000 x 0.01 = 1,220 codes survive per shard, enough for a top 100. At s = 0.1% only 122 survive, so the planner raises `nprobe` in proportion to 1/s. A graph is more fragile here: when most neighbours fail the filter, the walk gets stranded.
* Below about s = 0.01% (100,000 matching vectors), skip the index. Score only the slots in the bitmap: 100,000 x 96 = 9.6M lookups, about 10 ms of one core across all shards, with no match skipped.

A seller with a large share of all items gets its own collection, because that filter is a partition.

### Build, updates and drift

Encoding is the long part of a build: at an assumed 5,000 vectors per second per node, 24 nodes encode 120,000 per second, so 1B takes 2.3 hours. The 116 writes per second are appends. Lists with more than 20% tombstones are compacted.

The slow danger is drift. Centroids were trained on old data. New items crowd into a few cells, those lists grow, and scan time and recall both worsen with no error. Watch the ratio of the longest list to the mean, and the recall canary. The fix is a new index version: retrain on a fresh sample, encode from the vector store, replay the log from the recorded offset, then switch the alias. A new embedding model takes the same path, and queries must switch model in the same step.

## Evaluation

**Offline recall.** Report Recall@10 and Recall@100 on the 10,000-query ground-truth set for every index version and every parameter change. Slice the result, because an average hides the weak spots: filtered queries at 10%, 1% and 0.1% selectivity, queries whose neighbours were written in the last hour, and queries from rare categories.

**Offline latency.** Run a load test that replays real queries at 2,000 QPS against a full-size shard, with writes flowing at 116 per second. Report p50, p99 and p99.9 per shard and end to end. Then stop one replica per shard and repeat: the latency target must still hold.

**Recall canary (online).** Keep 200 queries with known exact neighbours and run them against production every 5 minutes. Alert below 0.93. This catches drift, a bad compaction or a replica serving the wrong version within minutes, not at the weekly run.

**Shadow traffic.** Before switching the alias, mirror 5% of live queries to the new index version. Compare the overlap of the two top-10 lists, and latency. A drop in overlap needs an explanation before the switch.

**Downstream A/B.** ANN recall is a proxy. Randomise by user and compare the product metric (click-through on results, or answer quality for a RAG caller) between `nprobe` settings. If 0.95 and 0.99 recall give the same click-through, serve 0.95 and keep the latency.

**Guardrails.** Share of responses with `shards_ok` below 8 (under 0.1%), log lag per replica (under 10 seconds), tombstone share per shard, and the longest-list ratio. Every query records the embedding model version, and a mismatch with the index is rejected.

## Bottlenecks & mitigations

* List scans: 11.7 ms of one core per query per shard, linear in `nprobe`. The 64 is a planning value. If the recall sweep demands 128, the scan doubles to 23.4 ms and the CPU pool must double with it.
* Fan-out tail: every query waits for the slowest of 8 shards, so one node in a long garbage-collection or compaction pause sets the p99.
* Rescoring I/O: 66,700 random NVMe reads per second per node, and after a restart the page cache is cold.
* Rebuilds: a new version needs a second copy on every node, 2 x 384 = 768 GB of each 1 TB disk, plus 2.3 hours of encoding.
* Very selective filters: cost moves from the index to bitmap work and brute-force scoring.

## Failure modes

* **Recall decays with no error.** Data drifts away from the trained centroids. Mitigation: the 5-minute recall canary, the longest-list alert, and a scheduled rebuild.
* **Slow or dead shard replica.** One shard's answer is late and the top 10 misses its items. Mitigation: hedged requests after 15 ms, three replicas, and `shards_ok` in every response so callers can retry or accept.
* **Replica behind the log.** It serves deleted items and misses new ones. Mitigation: each replica reports its applied offset, and the coordinator routes around any replica more than 10 seconds behind.
* **Query and index use different embedding models.** Distances become meaningless and every result looks plausible. Mitigation: store the model version in the collection and reject mismatched queries.
* **Tombstone build-up.** After a mass delete, scans spend their time skipping dead codes. Mitigation: compaction at 20% dead, and tombstone share as a metric.
* **Hot cell.** Millions of near-identical vectors, such as one product listed by many sellers, land in one list. Mitigation: deduplicate at write time, cap the codes scanned per list, and split oversized cells at the next rebuild.
* **Filter returns fewer than k.** `nprobe` was not raised enough for a selective filter. Mitigation: if fewer than k results survive, fall back to exact scoring over the bitmap.
* **Cold node after restart.** Loading 13 GB of codes and warming NVMe takes minutes, and early queries time out. Mitigation: replay recent queries against the node before it joins the pool.

## Follow-up questions interviewers ask

* The recall target moves from 0.95 to 0.99 at the same latency. What do you change, and what does it cost?
* How would you cut memory further: fewer dimensions, binary codes, or both? How do you check what each does to recall?
* The corpus grows to 10 billion vectors. Do you add shards, or change the index?
* There are 100,000 tenants, and the largest owns 30% of all vectors. How do you lay out the data?
* Walk through switching to a new embedding model with zero downtime and a rollback path.
* Why does a hash-sharded cluster query every shard, and when would you shard by cluster and query only a few?

## Lessons that cover this

* [#8Vector DBs and RAGBuild with LLMs](/ai/learn/vector-dbs-rag)

## Further reading

* [Efficient and robust approximate nearest neighbor search using HNSW graphsPaperarxiv.org](https://arxiv.org/abs/1603.09320)
* [Billion-scale similarity search with GPUsPaperarxiv.org](https://arxiv.org/abs/1702.08734)
* [Accelerating Large-Scale Inference with Anisotropic Vector QuantizationPaperarxiv.org](https://arxiv.org/abs/1908.10396)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousEmbedding service at scale](/ai/problems/embedding-service)[NextRecommendation feed](/ai/problems/recommendation-feed)

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
