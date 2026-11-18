# RAG pipeline for internal docs Q&A — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/rag-pipeline

[AI problems](/ai#problems)

GENAIGenAI systems#1Medium

# RAG pipeline for internal docs Q&A

retrievalembeddingsvector dbchunkingrerankingReported at Sierra

## Problem statement

Design a question-answering assistant for a company of 50,000 employees. It answers questions from internal documents: wiki pages, shared drives, tickets and policy PDFs. Every answer must cite the passages it used, respect each employee's document permissions, and reflect a document edit within minutes. The model itself is a hosted LLM that has never seen this data.

## Requirements

### Functional

* Answer a natural-language question with a streamed response and clickable citations to the source passages.
* Ingest documents from several sources and keep the index in sync when a document is edited, moved or deleted.
* Enforce access control: a user only ever retrieves chunks from documents they may open.
* Say "I could not find this" when the retrieved context does not contain the answer.
* Support follow-up questions inside a conversation.
* Collect thumbs up/down feedback and log every answer with the chunks that produced it.

### Non-functional

* Time to first token under 1.5 s at p95; retrieval plus reranking under 300 ms at p95.
* 80,000 questions per day, about 1 QPS average and 10 QPS at peak.
* Freshness: an edited document is searchable within 5 minutes.
* Faithfulness of at least 0.9 on the golden set; no answer may cite a document the user cannot open.
* LLM spend under 0.01 USD per question on average.
* 99.9% availability for the ask endpoint; ingestion may lag without taking answers down.

## Back-of-the-envelope estimates

**Traffic.** 50,000 employees x 20% daily active x 8 questions = 80,000 questions/day. That is 0.93 QPS on average; plan for 10 QPS at peak.

**Corpus.** 2 million documents x 2,000 tokens = 4 billion tokens. With 400-token chunks and 15% overlap, each chunk adds 340 new tokens, so 4B / 340 = about 11.8 million chunks.

**Vector storage.** 11.8M chunks x 1,024 dimensions x 4 bytes = 48 GB as float32. HNSW links (M = 32: up to 64 neighbour ids x 4 bytes = 256 bytes per vector) add about 3 GB, so about 51 GB in memory. Scalar quantization to int8 cuts the vectors to 12 GB.

**Embedding cost.** One full pass embeds about 4.7B tokens (overlap included). At an assumed 0.02 USD per million tokens that is about 94 USD, so re-embedding is cheap; re-indexing time is the real cost.

**Generation cost.** Each question sends 6 chunks x 400 tokens + 400 tokens of instructions and question = 2,800 input tokens, and gets 300 output tokens. Per day: 224M input and 24M output tokens. At an assumed 1 USD and 5 USD per million, that is 224 + 120 = 344 USD/day, or 0.0043 USD per question.

**Latency budget.** Query rewrite 150 ms (skipped for first turns), hybrid retrieval 80 ms, rerank of 50 candidates 120 ms, LLM time to first token 600 ms.

## API

```
POST /v1/ask
  body:   { question, conversation_id?, filters?: { source?, updated_after? } }
  stream: token events, then
          { answer_id, citations: [{ doc_id, chunk_id, title, url, quote }] }

POST /v1/feedback
  body:   { answer_id, rating: "up" | "down", comment? }

POST /internal/ingest            (async, called by connectors)
  body:   { source, doc_id, version, acl_groups, content_uri }
DELETE /internal/docs/{doc_id}
GET  /internal/docs/{doc_id}/status   -> { version, chunks, indexed_at }
```

## Data model

```
documents(doc_id PK, source, title, url, acl_groups[], version,
          content_hash, updated_at, status)

chunks(chunk_id PK, doc_id FK, doc_version, ordinal, heading_path,
       text, token_count, acl_groups[],
       embedding VECTOR(1024))          -- HNSW index, cosine
keyword_index(chunk_id, text)           -- inverted index, BM25

conversations(conversation_id PK, user_id, summary, updated_at)
answers(answer_id PK, conversation_id, user_id, question, rewritten_query,
        retrieved_chunk_ids[], cited_chunk_ids[], model, prompt_version,
        tokens_in, tokens_out, latency_ms, created_at)
feedback(answer_id FK, rating, comment, created_at)
```

## High-level design

**Offline path (ingestion)**

1. Connectors watch each source through webhooks or change feeds and publish `doc changed` events with the document's permission groups.
2. A parser turns each file into clean text plus structure: headings, tables, page numbers.
3. The chunker splits on structure first, then by size (400 tokens, 15% overlap), and stores the heading path with every chunk.
4. Embedding workers batch chunks through the embedding model and write the vectors to the vector index. The chunker writes the same chunk text to the BM25 index. Both carry `acl_groups` and `doc_version`.
5. A content hash per document skips unchanged files. Old chunk versions are deleted only after the new version is fully written.

**Online path (answering)**

6. The gateway authenticates the user and resolves their groups.
7. For follow-ups, a small model rewrites the question into a standalone query using the conversation summary.
8. The hybrid retriever runs dense and BM25 search in parallel, each filtered by the user's groups, and fuses the two lists with reciprocal rank fusion.
9. A cross-encoder reranks the top 50 and keeps the best 6.
10. The prompt builder places instructions first, then the chunks with ids, then the question. The LLM streams an answer that cites chunk ids.
11. A post-check maps citations back to documents, drops any citation the model invented, and logs the trace.

## Architecture diagram

Rendering diagram…

## Deep dives

### Chunking decides the ceiling on quality

The model can only answer from what a chunk contains. Fixed-size splits cut tables and procedures in half, so split on headings and paragraphs first and fall back to size. Store the heading path ("Leave policy > Parental leave > Eligibility") with each chunk and prepend it at embedding time, because a paragraph that says "this applies after 6 months" is useless without its title. Start at 300 to 500 tokens with 10 to 20% overlap and tune on a retrieval eval set, not by eye.

### Hybrid retrieval, then a reranker

Dense search handles paraphrase ("time off for a new baby" finds "parental leave"). BM25 handles exact strings that embeddings blur: ticket ids, error codes, product names. Run both, fuse with reciprocal rank fusion, and let a cross-encoder rerank about 50 candidates down to 6. The reranker reads query and chunk together, so it is far more precise than either retriever, and 50 pairs fit the 120 ms budget on one GPU (an assumption to load-test).

### Access control belongs inside retrieval

Filtering after retrieval fails in two ways: the top k can come back empty once forbidden chunks are removed, and a filter that runs after the prompt is built is too late, because the model has already read the forbidden chunk. Store `acl_groups` on every chunk and apply the filter inside the vector and keyword queries. Permission changes must flow through the same ingestion path as content changes, and they need the same 5-minute target.

### Freshness without full re-indexing

Hash each document and re-embed only what changed. Write the new version's chunks first, flip the document's `version`, then delete the old chunks, so a query never sees half a document. Changing the embedding model is the one case that needs a full rebuild: build a second index beside the first and switch traffic when it passes the eval set.

### Grounding and refusal

Tell the model to answer only from the supplied chunks, to cite a chunk id after each claim, and to say when the context is not enough. If the best reranker score is below a threshold, skip generation and return "not found" with the closest documents. Put the strongest chunks at the start and end of the context, because models use the middle of a long prompt least.

## Evaluation

**Offline, retrieval.** Build a golden set of 300 to 500 real questions with the chunk that answers each. Track Recall@6 (is the right chunk in the prompt?), MRR and nDCG@10. Recall@50 before reranking shows whether the retrievers or the reranker is the weak part.

**Offline, generation.** Score faithfulness (is every claim supported by the cited chunk?), answer relevance, and correctness against a gold answer. Use an LLM judge with a fixed rubric, and check the judge against 100 human-labelled answers every release.

**Refusals.** Keep 50 questions that the corpus cannot answer. The correct output is "not found"; count false answers separately because they are the most damaging failure.

**Online.** Thumbs-up rate, citation click rate, follow-up rate (a rephrase right after an answer signals a miss), share of "not found", time to first token and cost per question.

**A/B setup.** Randomise by user, change one thing at a time (chunk size, reranker, prompt version), and require the offline set to pass before any online test.

**Guardrails.** A hard check that every cited document is in the user's permission set; alert on any violation.

## Bottlenecks & mitigations

* Reranking: a cross-encoder over 50 candidates per query is the largest fixed latency cost and needs a GPU pool sized for peak QPS.
* LLM time to first token dominates what the user feels; prompt length drives it.
* Re-indexing after an embedding model change: 11.8M chunks must be re-embedded and the graph rebuilt.
* Filtered vector search slows down when a user's groups match a tiny share of the corpus.
* Parsing scanned PDFs and tables is slow and is where ingestion lag builds up.

## Failure modes

* **Right document, wrong chunk retrieved.** Recall is fine at document level but the answer sits in the next chunk. Mitigation: overlap, heading paths, and fetching neighbouring chunks of a hit.
* **Stale answer after an edit.** The index lags the source. Mitigation: change feeds, a per-document `indexed_at`, and an alert when lag passes 5 minutes.
* **Permission leak.** A chunk keeps old `acl_groups`. Mitigation: treat permission changes as ingestion events and run the hard citation check on every answer.
* **Confident answer with no support.** The model fills a gap from its own knowledge. Mitigation: score threshold before generation, "answer only from context" instruction, faithfulness tracked on every release.
* **Prompt injection inside a document.** A wiki page says "ignore your instructions". Mitigation: wrap chunks as quoted data, never as instructions, and give this assistant no write tools.
* **Vector index or reranker down.** Mitigation: fall back to BM25-only retrieval and say that results may be less precise.

## Follow-up questions interviewers ask

* The right chunk is in the top 50 but not in the top 6. What do you change?
* How would you support questions that need facts from ten documents at once?
* Suppose the model's context window holds a million tokens. Why not send the whole wiki?
* How do you roll out a new embedding model with no downtime?
* A user says an answer is wrong. Walk through how you debug it from the trace.
* How would the design change for 50 million documents and 500 QPS?

## Lessons that cover this

* [#8Vector DBs and RAGBuild with LLMs](/ai/learn/vector-dbs-rag)
* [#17LLM system designShip](/ai/learn/llm-system-design)
* [#23Projects - RAG app, fine-tuned model, agent + evalsLater](/ai/learn/projects)

## Further reading

* [Retrieval-Augmented Generation for Knowledge-Intensive NLP TasksPaperarxiv.org](https://arxiv.org/abs/2005.11401)
* [Lost in the Middle: How Language Models Use Long ContextsPaperarxiv.org](https://arxiv.org/abs/2307.03172)
* [RAGAS: Automated Evaluation of Retrieval Augmented GenerationPaperarxiv.org](https://arxiv.org/abs/2309.15217)

## My notes

## Your notes

Saved

Autosaves to this browser.

[NextHybrid retrieval and reranking service](/ai/problems/hybrid-search-reranking)

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
