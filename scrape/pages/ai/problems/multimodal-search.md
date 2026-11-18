# Multimodal search over images and text — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/multimodal-search

[AI problems](/ai#problems)

MLSDML system design#30Medium

# Multimodal search over images and text

multimodalcontrastive embeddingsimage searchvector searchhybrid searchreranking

## Problem statement

Design search for a marketplace catalogue of 100 million product images. A user can type a query ("red scooter with a basket"), upload a photo to find similar items, or do both, and can narrow the results with filters such as category and price. Many images have only a short title, so matching words is not enough: the system must match what the picture shows. It serves 20 million searches a day and must make a new image searchable within minutes.

## Requirements

### Functional

* Text-to-image search: return the images that best match a text query.
* Image-to-image search: return the images most similar to an uploaded photo or to an existing catalogue image.
* Apply metadata filters (category, price range, licence, colour) and still return a full page when enough matching images exist.
* Match exact words such as brand names and product codes through titles, tags, captions and text read from the image.
* Add, update and delete images continuously, and collapse near-duplicate images in the results.
* Rerank the top results with a vision-language model (VLM) for queries that need a closer look.

### Non-functional

* p95 latency of 200 ms for text queries and 300 ms for image queries, without the VLM reranker.
* 20 million searches per day: 231 QPS on average and 1,000 QPS at peak.
* Freshness: a new or changed image is searchable within 10 minutes.
* Approximate search finds at least 95% of the exact top 100 (Recall@100 of 0.95 against brute force).
* VLM reranking runs on at most 5% of queries, and its spend stays under 2,500 USD per day at the assumed price below.
* 99.9% availability. If the encoders are down, text queries still work through keyword search.

## Back-of-the-envelope estimates

**Traffic.** 20M searches/day = 231 QPS on average. Plan for 1,000 QPS at peak, about 800 text and 200 image queries per second.

**Vectors.** 100M images x 512 dimensions x 4 bytes = 204.8 GB as float32. Stored as int8 (1 byte per dimension) they take 51.2 GB. HNSW graph links (64 neighbour ids x 4 bytes = 256 bytes per vector) add 25.6 GB. RAM per replica: 51.2 + 25.6 = 76.8 GB. The float32 vectors stay on SSD and are used to rescore the top 200.

**Backfill.** Model time: at an assumed 1,000 images per second per GPU, 100M images take 100,000 GPU-seconds = 27.8 GPU-hours, about 56 USD at an assumed 2 USD per GPU-hour. Download, decode and resize: at an assumed 100 images per second per CPU core, 1M core-seconds = 278 core-hours. With 64 cores the pipeline runs at 6,400 images per second and finishes in 4.3 hours, and 7 GPUs keep up. The CPUs set the pace, not the GPUs.

**Daily updates.** 1M new or changed images per day = 11.6 per second, about 1% of one GPU.

**Keyword index.** 100M x 200 bytes of title, tags and caption = 20 GB of text.

**VLM rerank.** 20 thumbnails x 196 image tokens (224 px image, 16 px patches) = 3,920 tokens, plus 200 for the prompt = 4,120 input tokens. At an assumed 0.50 USD per million input tokens that is 0.00206 USD per query. The output is a short list of ids and is left out. For all 20M queries: 41,200 USD/day. For 5% of them: 2,060 USD/day.

**Latency budget, text query (p95).** Text encoder 10 ms, vector and keyword search in parallel 40 ms, rescore 15 ms, fusion 5 ms, metadata fetch 20 ms: 90 ms.

## API

```
POST /v1/search
  body: { query_text?, query_image?: { upload_id } | { image_id },
          filters?: { category?, price_min?, price_max?, licence?, colour? },
          k = 40, cursor?, rerank = "auto" | "off" | "vlm" }
  200:  { query_id,
          results: [{ image_id, thumbnail_url, title, score,
                      matched_by: ["vector", "keyword"] }],
          next_cursor, model_version, reranked, took_ms }

POST /v1/uploads                 -> { upload_id }     (query photo, deleted after 1 hour)
POST /v1/feedback                body: { query_id, image_id, action: click | save | purchase }

POST   /internal/images          (async) body: { image_id, image_uri, title, tags[], metadata }
DELETE /internal/images/{image_id}
POST   /internal/reindex         body: { model_version }   -- backfill into a new index
POST   /internal/alias           body: { serve: model_version }
```

## Data model

```
images(image_id PK, image_uri, thumbnail_uri, title, tags[],
       caption, caption_source: human | generated, ocr_text,
       category, price, licence, dominant_colour,
       content_hash, phash, dup_cluster_id, status, updated_at)

image_vectors(image_id, model_version, vec float32[512])   -- SSD, used for rescoring
ann_index[model_version]
    int8[512] per image + HNSW links                        -- RAM, 76.8 GB per replica
    filter fields: category, licence, price bucket, colour
keyword_index(image_id, title, tags, caption, ocr_text)    -- inverted index, BM25

query_log(query_id, user_id, type: text | image | both, query_text, upload_id,
          filters, model_version, result_ids[], reranked, latency_ms, ts)
feedback(query_id, image_id, action, position, ts)
golden_set(query_id, type, query, judged: [{ image_id, grade 0..3 }])
```

## High-level design

**Offline path (embedding pipeline)**

1. An ingest event with the image location, title, tags and metadata lands on a queue. A content hash skips images that have not changed.
2. CPU workers download and decode the image, resize it to the encoder's input size (224 px), make a thumbnail and compute a perceptual hash, which is a short fingerprint that stays almost the same after resizing or recompression.
3. GPU workers run the image encoder in batches of 256, scale each vector to length 1 and write it to the vector store with its `model_version`.
4. For images with very little text, a captioning model writes one sentence, and OCR reads any text printed in the image. Title, tags, caption and OCR text go to the keyword index.
5. The indexer adds the int8 vector and the filter fields to the HNSW index. Images whose hash and vector are almost identical share a `dup_cluster_id`.

**Online path (query)**

6. The gateway validates the request and looks at what it contains: text, an image or both.
7. Text goes through the text encoder. A query image goes through the same preprocessing code as step 2 and then the image encoder. Both produce a 512-dimension vector in the same space.
8. Vector search returns the top 200 with the filters applied inside the search, then rescores them with the float32 vectors. A request with both text and an image runs one search per vector, and both lists go to step 10.
9. For text queries, a BM25 keyword search with the same filters runs in parallel and returns its own top 200.
10. All the lists are fused with reciprocal rank fusion (RRF). Near-duplicates are collapsed to one result per cluster and 40 are kept.
11. If the query needs it, a VLM reads the query and the top 20 thumbnails and returns a new order.
12. The service returns the results and logs the query, the result ids and the model version.

## Architecture diagram

Rendering diagram…

## Deep dives

### One vector space, two encoders

A contrastive image-text model has an image encoder and a text encoder. It is trained on image and caption pairs: in a batch of N pairs, the N matching pairs are pushed toward high cosine similarity and the N x N - N mismatched ones toward low. After training, the text "red scooter" lands near photos of red scooters, so one index of image vectors serves both text queries and image queries.

Two limits follow. First, text vectors and image vectors do not fully overlap: an image query scores much higher against its matches than a text query does. Never use one score threshold for both query types, and fuse lists by rank, not by raw score. Second, one vector keeps the gist of an image and loses detail: counts, small printed text and relations such as "left of". The keyword path and the reranker exist for those.

### Vectors, keywords and filters in one query

Embeddings blur exact strings. A search for the code "KX-450" returns things that look alike. BM25 over titles, tags, captions and OCR text finds the exact match. Cosine and BM25 scores are on different scales, so fuse by rank: each image scores the sum of 1 / (60 + rank) over the lists it appears in.

Filters must run inside the vector search. If a filter passes 1% of the catalogue, filtering afterwards leaves 200 x 0.01 = 2 results. When a filter passes under 0.1% (100,000 images), skip the graph and score those vectors exactly: 100,000 x 512 = 51.2M multiply-adds, a few milliseconds.

### The embedding pipeline and model versions

Preprocessing must be the same code offline and online. If the pipeline centre-crops and the query path pads, the same photo gives two different vectors and image search quietly gets worse. Ship it as one versioned library.

Vectors from two models cannot be compared, even when both have 512 dimensions. A new model means embedding all 100M images again into a second index, checking it on the golden set and switching the alias. The query encoders switch in the same step.

### When to pay for a VLM reranker

A VLM reads the query and the candidate images together, so it can check "two dogs" or "a sign that says SALE". At the assumed price it costs 0.00206 USD per query and adds a second or more, against 90 ms for the whole retrieval path. Gate it: run it when the query has a number, a spatial word or quoted text, or when the user asks to refine. It can only reorder what retrieval found, so track Recall@20 before reranking. If the right image is not in the top 20, a better reranker changes nothing.

## Evaluation

**Golden set.** 2,000 text queries sampled from the logs in fixed groups: frequent, rare, attribute ("wooden", "red"), brand or code, compositional ("two cups on a tray") and non-English. Add 500 image queries. Human graders score the pooled top results of several systems from 0 to 3.

**Offline metrics.**

* Recall@200 for the vector path and for the keyword path, each alone. This shows which path is weak for which group.
* nDCG@10 after fusion, and again after the VLM reranker.
* ANN recall: on 10,000 queries, compare the index with exact brute-force search. It must stay at or above 0.95. This separates "the index lost it" from "the model never ranked it".

**Image-query test.** Take 1,000 catalogue images, crop, resize and recompress each one, and search with the copy. The original must come back in the top 5 for at least 95% of them. This test also catches a preprocessing mismatch.

**VLM as a judge.** A VLM can grade (query, image) pairs to grow the golden set cheaply. Check it against 300 human-graded pairs first and re-check on every model change.

**Online.** Click-through rate on the first page, zero-result rate, reformulation rate (a new query within 30 seconds and no click), saves and purchases per search, p95 latency per query type and VLM spend per day.

**A/B setup.** Randomise by user and change one thing at a time: encoder, fusion, rerank gate. A new encoder must pass the golden set before it gets any traffic.

**Guardrails.** Images that fail the safety check at ingestion never enter either index. Uploaded query photos are deleted after 1 hour. A deleted listing must disappear from results within the 10-minute freshness target.

## Bottlenecks & mitigations

* Decoding and resizing images: 278 core-hours for a backfill. CPU, not GPU, sets how long a model change takes.
* RAM for the ANN index: 76.8 GB per replica, growing in step with the catalogue.
* Filtered vector search when a filter passes only a small share of the catalogue.
* The VLM reranker: a second or more and 0.00206 USD per query, so it cannot run on every query.
* The image-query path: upload, decode and encode all happen before search starts.

## Failure modes

* **Preprocessing mismatch.** Offline and online code resize or crop differently, and image search degrades with no error. Mitigation: one shared, versioned preprocessing library and the image-query test on every release.
* **Two model versions in one index.** A half-finished backfill mixes vectors that cannot be compared. Mitigation: `model_version` on every vector, one index per version and an alias switch.
* **Exact strings missed.** A product code returns lookalike items. Mitigation: the keyword path with RRF, and a code-query group in the golden set.
* **Near-duplicates fill the page.** Thirty sellers use the same stock photo. Mitigation: collapse by `dup_cluster_id`.
* **A filter empties the results.** Filtering after the vector search throws away most of the top 200. Mitigation: filter inside the search and switch to exact scoring for very selective filters.
* **Text printed in an image hijacks it.** A picture with the word "scooter" written on it can rank for "scooter". Mitigation: the reranker for top results and seller-quality signals in the final score.
* **Encoder pool down.** Mitigation: text queries fall back to keyword search only, vectors of frequent text queries are cached, and image queries return a clear retry message.
* **VLM timeout.** Mitigation: a hard deadline, after which the fused order is returned and `reranked` is false.

## Follow-up questions interviewers ask

* A user uploads a photo and types "same style but in blue". How do you combine the image and the text in one query?
* The catalogue grows to 5 billion images. What changes in the index, the memory and the cost?
* How would you fine-tune the encoders on your own click logs, and what can go wrong?
* Most captions are in English. How do you support queries in Hindi or Tamil?
* How would you extend this to video search? What do you embed?
* How do you roll out a new embedding model with no downtime and no mixed results?

## Lessons that cover this

* [#3RNNs, LSTMs, CNNsFoundations](/ai/learn/rnns-lstms-cnns)
* [#21Computer use and multimodal agentsLater](/ai/learn/computer-use-multimodal-agents)

## Further reading

* [Learning Transferable Visual Models From Natural Language Supervision (CLIP)Paperarxiv.org](https://arxiv.org/abs/2103.00020)
* [Sigmoid Loss for Language Image Pre-TrainingPaperarxiv.org](https://arxiv.org/abs/2303.15343)
* [Efficient and robust approximate nearest neighbor search using HNSW graphsPaperarxiv.org](https://arxiv.org/abs/1603.09320)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousContent moderation with classifiers and LLM review](/ai/problems/content-moderation)[NextSelf-attention from scratch](/ai/problems/attention-from-scratch)

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
