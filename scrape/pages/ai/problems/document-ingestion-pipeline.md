# Document ingestion and indexing pipeline for LLM use — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/document-ingestion-pipeline

[AI problems](/ai#problems)

GENAIGenAI systems#20Medium

# Document ingestion and indexing pipeline for LLM use

ingestionparsingocridempotencyincremental indexingaccess controlReported at Databricks

## Problem statement

Design the offline pipeline that turns an enterprise's documents into a search index for LLM applications. It reads 20 million documents from shared drives, wikis, ticket systems and object stores: web pages, office files, PDFs with tables and scanned paper. It must parse them, chunk them, embed them and write them to a vector index and a keyword index. After the first load it keeps the index in step with 400,000 document changes a day, including deletes and permission changes. Query serving is out of scope.

## Requirements

### Functional

* Connect to several source systems and detect new, changed, moved and deleted documents.
* Parse every supported format into clean text with structure: headings, tables, lists and page numbers, with OCR for scanned pages.
* Chunk, embed and index each document, and re-process only the parts that changed.
* Carry each document's permissions into the index and apply permission changes without re-embedding.
* Delete a document and everything derived from it when the source deletes it.
* Run backfills: re-parse, re-chunk or re-embed the whole corpus into a new index version with no downtime.

### Non-functional

* Freshness: a change is searchable within 5 minutes at p95 for text formats, and within 30 minutes for scanned PDFs.
* Throughput: 400,000 changed documents per day, about 4.6 per second on average, with bursts of 46 per second.
* A permission removal takes effect within 60 seconds. A deleted document's derived data is gone within 24 hours.
* Coverage: at least 99.5% of source documents are indexed. Every other document is listed with a reason.
* Processing is at-least-once with idempotent writes: a replayed event creates zero duplicate chunks.
* First load of 20 million documents in under 2 days; a full re-embedding in under 24 hours.

## Back-of-the-envelope estimates

**Corpus.** 20M documents x 2,000 tokens = 40 billion tokens. With 400-token chunks and 15% overlap, each chunk adds 340 new tokens: 40B / 340 = 117.6 million chunks.

**Storage.** Raw files: 20M x 250 KB = 5 TB in object storage. Parsed text: 40B tokens x 4 bytes = 160 GB. Vectors: 117.6M x 1,024 dimensions x 4 bytes = 482 GB as float32.

**Embedding the backfill.** 117.6M chunks x 400 tokens = 47 billion tokens. At an assumed 50,000 tokens per second per GPU, that is 941,000 GPU-seconds, or 261 GPU-hours. With 16 GPUs: 16.3 hours. Through a hosted API at an assumed 0.02 USD per million tokens it would cost 47,059 x 0.02 = 941 USD.

**OCR.** Assume 5% of documents are scans: 1M documents x 8 pages = 8 million pages. At an assumed 1 page per core-second that is 2,222 core-hours, so 11 hours on 200 cores. OCR is slower per document than embedding and needs its own pool.

**Steady state.** 400,000 changed documents / 86,400 s = 4.6 per second. Each document has 2,000 / 340 = 5.88 chunks. Re-embedding whole documents means 400,000 x 5.88 = 2.35 million chunk writes and 941 million tokens per day. If a typical edit changes 30% of a document's chunks, chunk-level hashing cuts that to 706,000 chunks and 282 million tokens. The money is small either way, 19 USD against 6 USD per day at the hosted price. The gain is 70% fewer index writes and less GPU time on the path that sets freshness.

## API

```
POST /v1/sources
  body: { tenant_id, type: "drive" | "wiki" | "tickets" | "object_store",
          credentials_ref, sync: "webhook" | "poll", poll_interval_s? }
POST /v1/sources/{source_id}/sync      body: { mode: "incremental" | "full" }

POST /internal/events                  (from connectors, at-least-once)
  body: { source_id, doc_id, op: "upsert" | "delete" | "acl",
          source_version, acl_groups[], content_uri?, event_time }

GET  /v1/docs/{doc_id}/status
  -> { stage, source_version, indexed_version, chunks, indexed_at, error? }

POST /v1/backfills
  body: { reason: "embedding_model" | "parser" | "chunker",
          target_index, max_docs_per_s }
GET  /v1/backfills/{backfill_id}       -> { total, done, failed, eta_s }

GET  /v1/dead-letters?source_id=       -> [{ event_id, doc_id, stage, error, attempts }]
POST /v1/dead-letters/{event_id}/retry
```

## Data model

```
sources(source_id PK, tenant_id, type, cursor, last_reconciled_at)

documents(doc_id PK, source_id, tenant_id, uri, mime, source_version,
          content_hash, canonical_doc_id, acl_id, status,
          parser_version, indexed_version, indexed_at, deleted_at)
acls(acl_id PK, tenant_id, allow_groups[], updated_at)

parsed_docs(content_hash PK, parser_version, elements_uri,
            pages, ocr_confidence)          -- parsed once per distinct file
chunks(chunk_id PK,                         -- hash(canonical_doc_id, text_hash)
       canonical_doc_id, text_hash, ordinal, heading_path, page,
       text, token_count, acl_ids[], near_dup_group)
embedding_cache(text_hash, model_version) -> VECTOR(1024)

vector_index_v{n}(chunk_id, vector, tenant_id, acl_ids[], metadata)
keyword_index(chunk_id, text, tenant_id, acl_ids[])

events(event_id PK, doc_id, op, source_version, event_time,
       attempts, state)                     -- queue, partitioned by doc_id
backfills(backfill_id PK, reason, target_index, cursor, done, failed, state)
```

## High-level design

1. **Connectors.** One per source type. Each learns about changes in three ways: webhooks where the source offers them, a change feed read with a saved cursor, and a daily full listing that catches missed events and silent deletes. Every change becomes an event with the document id, the source's version and the current permission groups.
2. **Queue.** Events go to a durable queue partitioned by `doc_id`, so two events for one document are processed in order. Delivery is at-least-once.
3. **Fetch and hash.** A worker downloads the file to object storage and hashes the bytes. Same hash as the stored version: stop here. Same hash as another document: link it as a duplicate.
4. **Route.** The file type is read from the content, not the file extension. Text formats go to a fast lane. Scanned pages and very large files go to a slow lane with its own queue and workers, so one 900-page scan cannot delay a wiki edit.
5. **Parse.** Every parser emits the same element list: headings, paragraphs, tables and lists, each with a page number. The list is stored with its parser version.
6. **Chunk.** Split on structure first, then by size (400 tokens, 15% overlap). Keep the heading path with each chunk, keep a table in one piece, and hash each chunk's text.
7. **Diff.** Compare the new chunk ids with the stored ones. Only new ids continue. Ids that disappeared are marked for deletion.
8. **Embed.** Workers form micro-batches of 64 chunks or 200 ms, whichever comes first. They check the embedding cache by text hash, then call the model.
9. **Write.** Upsert the new chunks into the vector index and the keyword index, flip the document's `indexed_version`, then delete the old chunks. A query never sees half a document.
10. **Permission-only events.** These skip steps 3 to 8 and update metadata only.
11. **Deletes.** The document row is tombstoned, then its chunks, parsed text and raw copy are removed.
12. **Backfills.** A scheduler re-reads stored elements or chunks through a low-priority queue into a new index version.

## Architecture diagram

Rendering diagram…

## Deep dives

### Parsing PDFs, tables and scans

A PDF stores characters at positions on a page, not paragraphs. Naive text extraction can read a two-column page straight across both columns, so a layout step must rebuild the reading order. It also drops lines repeated on most pages: headers, footers, page numbers.

Keep each table as one element and write it as Markdown rows. If a long table must be split, repeat the header row in every piece, because a cell without its column name means nothing.

Detect scans per page: a page with an image and fewer than about 50 extracted characters goes to OCR. Store the OCR confidence. Pages below the bar are listed for review, not indexed: garbage text pollutes both indexes.

### Idempotent workers on an at-least-once queue

The queue will deliver some events twice, and workers will crash halfway. So every output is keyed by its content: parsed elements by `content_hash` and parser version, a chunk by the hash of its document id and text, a vector by text hash and model version. A repeated step rewrites the same rows.

Order is protected twice: the queue is partitioned by document, and the writer applies an event only if its `source_version` is newer than the stored one. Failures retry with exponential backoff, and after 5 attempts the event moves to a dead letter queue with its error.

### Updates, deletes and duplicates

* Updates: chunk boundaries follow headings and paragraphs, so an edit to one paragraph re-embeds 1 or 2 chunks. Fixed-size windows would shift every later boundary.
* Deletes: many sources send no delete event. The daily listing compares source ids with the `documents` table, and anything missing is deleted.
* Exact duplicates: the same file in five folders has one content hash. Index it once and attach each copy's document id and ACL, so the top results are not five copies of one passage.
* Near duplicates: group drafts of one file with MinHash over word shingles, and return only the newest of a group.
* Boilerplate: a chunk hash seen in thousands of documents (signatures, disclaimers) is not indexed.

### Permissions travel with the document

Each chunk stores ACL ids, not lists of people. The ACL row holds groups, and group membership is resolved at query time. Adding a person to a group touches zero chunks. Re-sharing a folder of 100,000 documents updates a few ACL rows, not 588,000 chunks. Removals use a priority lane with a 60-second target. If a connector cannot read a document's permissions, the document is not indexed: fail closed.

### Backfills and re-embedding after a model change

Vectors from two embedding models cannot be compared, so a new model needs a new index beside the old one. The backfill reads stored chunks, so nothing is fetched, parsed or run through OCR again: about 16 hours on 16 GPUs. Live changes are written to both indexes while it runs. Then compare chunk counts and golden-set recall, switch the alias, and keep the old index 7 days.

## Evaluation

**Coverage.** After every daily listing, compute indexed documents / source documents per source. Target 99.5%. The rest must sit in the dead letter queue with a reason: too large, encrypted, unsupported format, OCR below the bar.

**Freshness.** For every event measure `indexed_at - event_time`. Report p50 and p95 per source and per lane, and alert when the p95 passes 5 minutes for text or 30 minutes for scans. Track queue depth and the age of the oldest event as leading signals.

**Parse quality.** Sample 200 documents a week, stratified by format. A reviewer compares the parsed elements with the original: reading order, missing text, table structure. For OCR, keep 500 hand-typed pages and track the character error rate against them. Run the same set before any parser upgrade.

**Retrieval impact.** Parsing and chunking are only good if retrieval finds the answer. Keep a golden set of questions with the chunk that answers each, tagged by source format. Report Recall@10 per format. If scanned PDFs score 0.60 and wiki pages 0.90, the parser is the problem, not the embedding model.

**Correctness checks.** A replay test sends every event of a sample twice and expects zero new chunks. A reconciliation job counts chunks per document in the vector index, the keyword index and the `chunks` table, and the three numbers must agree. Canary documents with known permissions are searched by test users on every deploy: a restricted canary must never appear.

**Changing a stage.** For a new parser or chunker, build a shadow index over a 1% sample, run the golden set against both, and promote only if recall does not drop for any format.

**Cost.** GPU-hours and OCR core-hours per 1,000 documents, and the embedding cache hit rate.

## Bottlenecks & mitigations

* OCR: 8 million pages cost 2,222 core-hours, and a single 900-page scan can hold a worker for 15 minutes. It needs a separate lane and autoscaling on queue age.
* Source API rate limits: a full listing of a drive with millions of files is capped by the provider's quota, and that quota often sets the real speed of the first load.
* Embedding GPUs during a backfill: 47 billion tokens take 16 hours on 16 GPUs, and live changes must not wait behind them.
* Index writes: every insert into an HNSW graph is a graph search plus link updates, so loading 117.6 million vectors one by one takes hours of CPU. Build backfill indexes in bulk offline and keep online inserts for live changes.
* Hot partitions: a bulk move of 100,000 files in one tenant floods a few queue partitions.

## Failure modes

* **Poison document.** A corrupt or huge file crashes the parser on every retry and blocks its partition. Mitigation: a time and memory limit per document, 5 attempts, then the dead letter queue with the error.
* **Out-of-order events.** A retry of version 6 arrives after version 7 and overwrites it. Mitigation: per-document partitioning and a version check on every write.
* **Missed delete.** The source deletes a file and sends no event, so the assistant keeps quoting it. Mitigation: the daily listing and a 24-hour limit on orphaned documents.
* **Crash between write and delete.** New chunks are written, the worker dies, and old chunks stay. Mitigation: the delete list comes from the diff, so the replayed event deletes the same ids again, and the reconciliation job removes index entries that have no row in `chunks`.
* **Silent garbage text.** OCR noise or a wrong reading order is indexed with no error. Mitigation: the confidence bar, the weekly parse audit and Recall@10 per format.
* **Stale permissions.** A user is removed from a document and can still retrieve its chunks. Mitigation: the priority lane with a 60-second target, permission canaries, and fail closed when an ACL cannot be read.
* **Connector stalls.** An access token expires or the source throttles, and the cursor stops moving with no failure reported. Mitigation: alert on the time since the last successful sync per source, and back off within the quota.
* **Backfill starves live traffic.** The re-embedding job fills the GPUs and freshness goes from 5 minutes to hours. Mitigation: a separate low-priority queue and a rate limit that yields when live queue age grows.

## Follow-up questions interviewers ask

* One customer uploads 5 million scanned pages in a day. What happens to everyone else's freshness, and how do you protect it?
* A user edits one sentence in a 300-page PDF. Walk through exactly what is recomputed.
* How would you handle documents with images, charts or handwriting that OCR cannot read?
* The chunker changes from 400-token chunks to 800-token chunks. What has to be rebuilt, and what can be reused?
* How do you prove to an auditor that a deleted document is gone from every store?
* Permissions in the source are inherited through ten levels of folders. How do you keep the index correct and fast?

## Lessons that cover this

* [#8Vector DBs and RAGBuild with LLMs](/ai/learn/vector-dbs-rag)

## Further reading

* [Retrieval-Augmented Generation for Knowledge-Intensive NLP TasksPaperarxiv.org](https://arxiv.org/abs/2005.11401)
* [LayoutLM: Pre-training of Text and Layout for Document Image UnderstandingPaperarxiv.org](https://arxiv.org/abs/1912.13318)
* [MTEB: Massive Text Embedding BenchmarkPaperarxiv.org](https://arxiv.org/abs/2210.07316)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousChatGPT-like chat service](/ai/problems/chat-service)[NextReal-time voice AI agent](/ai/problems/realtime-voice-agent)

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
