# Vector DBs and RAG — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/vector-dbs-rag

[AI roadmap](/ai)

Build with LLMsLesson #8StudyIntermediate 4 h

# Vector DBs and RAG

RAG (retrieval-augmented generation) fetches relevant text at query time and puts it in the prompt, so a model answers from your data without being retrained. A vector database makes the fetching fast: it stores an embedding for every chunk of text and finds the nearest ones to a query in milliseconds. This lesson covers both, from chunking to evaluation.

ragvector databaseembeddingshnswhybrid searchreranking

## Why it matters

RAG is the most asked applied topic in GenAI interviews, and it is the first thing most companies build with an LLM. Interviewers do not want the definition. They want to hear how you choose a chunk size, why you would add keyword search to vector search, what a reranker buys you, and how you debug a wrong answer. Each of those has a concrete answer, and this lesson gives you all of them with numbers you can say aloud.

Read first: [LLM fundamentals - tokens, embeddings, decoding](/ai/learn/llm-fundamentals), [Prompting and context engineering](/ai/learn/prompting-context-engineering)

## Lesson

### The problem RAG solves

An LLM knows only what was in its training data. It has never seen your company wiki, and it does not know what changed yesterday. You have three ways to give it knowledge: put everything in the prompt (expensive, slow, and quality drops as the window fills), fine-tune it (slow to update, and it still invents details), or retrieve only the relevant passages for each question. The third is RAG. It gives you fresh answers, access control and citations, and updating knowledge is just re-indexing a document.

### Embeddings and similarity

An embedding model turns a piece of text into a vector, typically 384 to 3,072 numbers. Texts with similar meaning land close together, so "time off for a new baby" sits near "parental leave policy" even though they share no words. Closeness is measured with one of three functions.

| Metric | Formula idea | Use it when |
| --- | --- | --- |
| Cosine similarity | Angle between the vectors | The default for text; ignores vector length |
| Dot product | Cosine times both lengths | The model was trained for it; fastest to compute |
| Euclidean (L2) | Straight-line distance | Image or classic ML features |

If the vectors are normalised to length 1, all three give the same ranking. Most systems normalise once at indexing time and then use the dot product.

### What a vector database does

Comparing a query against every stored vector is exact but costs O(N x d) per query. That is fine up to a few hundred thousand vectors. Beyond that you need approximate nearest neighbour (ANN) search, which trades a little recall for a large speed-up. A vector database is an ANN index plus the things a real system needs: metadata filters, inserts and deletes, persistence and replication. It can be a library inside your process, an extension to a relational database, or a dedicated service.

| Index | How it works | Strength | Cost |
| --- | --- | --- | --- |
| Flat (brute force) | Compare with every vector | Exact; no build step | Slow past about 1 million vectors |
| HNSW | Layered graph; walk toward the query | High recall at low latency | Memory heavy; slow to build |
| IVF (inverted file) | Cluster vectors into cells; search only the nearest cells | Less memory; fast build | Recall depends on how many cells you probe |
| PQ (product quantization) | Compress each vector into a short code | 10 to 50 times smaller | Lossy; rescore the top results with full vectors |

![HNSW search moving from a sparse top layer down to the dense bottom layer](/ai/img/hnsw-layers.svg)HNSW search moving from a sparse top layer down to the dense bottom layer

HNSW (hierarchical navigable small world) is the common default. Search starts in a sparse top layer and moves down to denser layers, which gives fast lookups with high recall. Three knobs control it: `M` (links per node), `efConstruction` (build effort) and `efSearch` (candidates kept per query). Raising any of them improves recall and costs memory or time.

### The RAG pipeline

1. **Ingest:** load, parse and clean documents (PDFs, HTML, tables).
2. **Chunk:** split into pieces, usually a few hundred tokens with some overlap. Split on structure (headings, paragraphs) where you can.
3. **Embed and index:** an embedding model turns each chunk into a vector, stored in a vector database with an ANN index such as HNSW. Keep a keyword index (BM25) too.
4. **Retrieve:** embed the query and fetch the top-k chunks by cosine similarity. Hybrid search combines dense and keyword results, often with reciprocal rank fusion.
5. **Rerank:** a cross-encoder scores each query-chunk pair and keeps the best few.
6. **Generate:** the LLM answers using only the retrieved context, with citations.
7. **Evaluate:** measure retrieval and generation separately.

Steps 1 to 3 run offline whenever documents change. Steps 4 to 6 run on every question.

### Chunking

Chunk size is the first decision and the one with the largest effect. Small chunks retrieve precisely but lose the surrounding context. Large chunks keep context but add noise and cost. Start around 300 to 500 tokens with 10 to 20 percent overlap, then tune on a retrieval eval set. Structure-aware splitting usually beats fixed sizes: a table cut in half answers nothing. Store the heading path with each chunk ("Leave policy > Parental leave") so a paragraph still makes sense on its own.

### Dense, sparse and hybrid retrieval

Dense retrieval (embeddings) matches meaning and handles paraphrases. Sparse retrieval (BM25) matches exact words such as product codes, names and error strings, which embeddings tend to blur. BM25 is the standard keyword-scoring formula: a chunk scores higher when a query word appears in it more often, and rare words count for more than common ones. It is called sparse because a text is represented by word counts over the whole vocabulary, almost all of them zero. Hybrid search runs both and is the safer default. The usual way to merge the two ranked lists is reciprocal rank fusion (RRF): each document scores the sum of 1 / (k + rank) over the lists it appears in, with k = 60. A document ranked well by both retrievers rises to the top, and no score calibration is needed.

Formula

RRF(d)=r∈rankers∑​k+rankr​(d)1​,k=60

### Reranking: bi-encoder versus cross-encoder

A bi-encoder embeds the query and the document separately, so it is fast and searchable: document vectors are computed once. A cross-encoder reads the query and the document together, so it is accurate but slow, because nothing can be precomputed. Use both: retrieve about 50 candidates with the bi-encoder, then rerank them with the cross-encoder and keep the best 5 to 8.

### Beyond the basic pipeline

* **Query transformation:** rewrite the query, generate several variants, or generate a hypothetical answer and search with that (HyDE).
* **Metadata filtering:** filter by user, date, department or document type before or during search. This is also how access control is enforced.
* **Agentic RAG:** the model decides when to search, what to search, and whether to search again, instead of one fixed retrieval step.
* **GraphRAG:** build a knowledge graph of entities and relations from the documents, then retrieve over the graph. It helps with questions that need facts joined across many documents.

### Measuring a RAG system

Retrieval and generation fail independently, so measure them separately.

| Stage | Metric | What it tells you |
| --- | --- | --- |
| Retrieval | Recall@k | Did the right chunk appear in the top k? |
| Retrieval | Precision@k | How much of the top k is relevant? |
| Retrieval | MRR, nDCG | Is the right chunk ranked near the top? |
| Generation | Faithfulness (groundedness) | Is every claim supported by the retrieved context? |
| Generation | Answer relevance | Does the answer address the question? |
| End to end | Correctness vs a gold answer | Is the final answer right? |

MRR (mean reciprocal rank) is the average over all questions of 1 / rank of the first relevant chunk: rank 1 scores 1, rank 4 scores 0.25. nDCG (normalised discounted cumulative gain) also counts relevant chunks further down the list, with less weight the lower they sit. Faithfulness and answer relevance are usually scored by a judge model, which splits the answer into claims and checks each one against the retrieved chunks.

### RAG, fine-tuning or a long context

RAG gives the model knowledge: fresh, private or frequently changing facts. Fine-tuning changes behaviour: output format, tone, domain vocabulary, tool-call style. Start with prompting, add RAG for knowledge, and fine-tune only when you have a stable task, a real eval and roughly 500 or more good examples. They combine well. Large context windows change the design (bigger chunks, whole documents) but not the need to select, because sending everything costs more, is slower, and quality drops as the window fills.

## Diagram

Rendering diagram…

## Worked example

**Sizing an index.** A team has 200,000 documents of about 1,500 tokens each, so 300 million tokens. With 400-token chunks and 15% overlap, each chunk adds 340 new tokens: 300M / 340 = about 882,000 chunks. (The short last chunk of each document pushes the real count toward 1 million, which does not change the conclusion.) With a 768-dimension embedding in float32, one vector is 768 x 4 = 3,072 bytes, so the vectors take 882,000 x 3,072 = 2.7 GB. The HNSW links add little at this dimension: with M = 32 the bottom layer keeps up to 64 neighbour ids x 4 bytes = 256 bytes per vector, about 0.23 GB, so plan for about 3 GB in total. That fits on one machine, so a library or a database extension is enough; a distributed vector service is not needed yet.

**Fusing two rankings with RRF (k = 60).** A question returns these lists:

| Rank | Dense search | BM25 |
| --- | --- | --- |
| 1 | A | C |
| 2 | B | E |
| 3 | C | A |
| 4 | D | B |

Scores: A = 1/61 + 1/63 = 0.03227. C = 1/63 + 1/61 = 0.03227. B = 1/62 + 1/64 = 0.03175. E = 1/62 = 0.01613. D = 1/64 = 0.01563. The fused order is A and C (tied), then B, E, D. Chunks found by both retrievers beat a chunk that only one ranked highly, which is exactly the behaviour you want before the reranker makes the final call.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""Hybrid retrieval in miniature: BM25 + cosine similarity, fused with RRF.

The "embedding" here is a toy (hashed character trigrams). It stands in for a
real embedding model so the mechanics run with NumPy alone.
"""
import math
import re
import zlib
from collections import Counter

import numpy as np

DOCS = {
    "leave-1": "Parental leave: employees get 26 weeks of paid leave after 6 months of service.",
    "leave-2": "Annual leave is 24 days per year. Up to 5 unused days carry over.",
    "it-1": "Error E-4012 means the VPN certificate expired. Renew it from the IT portal.",
    "it-2": "To reset a laptop password, open the IT portal and choose account recovery.",
    "exp-1": "Travel expenses must be filed within 30 days with receipts attached.",
}

def tokenize(text):
    return re.findall(r"[a-z0-9-]+", text.lower())

def bm25_ranking(query, docs, k1=1.5, b=0.75):
    toks = {d: tokenize(t) for d, t in docs.items()}
    avg_len = sum(len(t) for t in toks.values()) / len(toks)
    df = Counter(term for t in toks.values() for term in set(t))
    scores = {}
    for d, t in toks.items():
        tf = Counter(t)
        s = 0.0
        for term in tokenize(query):
            if term not in tf:
                continue
            idf = math.log(1 + (len(toks) - df[term] + 0.5) / (df[term] + 0.5))
            s += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(t) / avg_len))
        if s > 0:                                  # a keyword index returns only chunks that match
            scores[d] = s
    return sorted(scores, key=scores.get, reverse=True)

def embed(text, dim=512):
    v = np.zeros(dim)
    padded = " " + " ".join(tokenize(text)) + " "
    for i in range(len(padded) - 2):
        v[zlib.crc32(padded[i:i + 3].encode()) % dim] += 1.0
    norm = np.linalg.norm(v)
    return v / norm if norm else v

def dense_ranking(query, docs):
    ids = list(docs)
    matrix = np.stack([embed(docs[d]) for d in ids])      # (N, dim), unit length
    sims = matrix @ embed(query)                          # cosine, because both are normalised
    return [ids[i] for i in np.argsort(-sims)]

def rrf(rankings, k=60):
    scores = Counter()
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: -kv[1])

if __name__ == "__main__":
    for query in ["what does error E-4012 mean", "parental leaves for employee"]:
        sparse = bm25_ranking(query, DOCS)
        dense = dense_ranking(query, DOCS)
        fused = rrf([sparse, dense])
        print("query :", query)
        print("  bm25 :", sparse[:3])
        print("  dense:", dense[:3])
        print("  fused:", [(d, round(s, 4)) for d, s in fused[:3]])
    assert rrf([["a", "b"], ["b", "a"]])[0][1] == rrf([["a", "b"], ["b", "a"]])[1][1]
    print("rrf tie check ok")
```

## Key takeaways

* RAG gives a model knowledge at query time; fine-tuning changes behaviour. Start with RAG for facts.
* The pipeline is ingest, chunk, embed and index, retrieve, rerank, generate, evaluate. The first three are offline.
* Chunk size is the biggest quality lever: start at 300 to 500 tokens with 10 to 20% overlap and tune on an eval set.
* Hybrid search (dense plus BM25, fused with RRF) is the safe default, because embeddings blur exact strings.
* Retrieve many with a bi-encoder, then rerank a few with a cross-encoder.
* HNSW is the default ANN index: high recall, low latency, memory heavy.
* Measure retrieval (Recall@k, MRR, nDCG) and generation (faithfulness, relevance) separately.

## Common mistakes

* Tuning the prompt when the right chunk was never retrieved. Check retrieval first.
* Fixed-size chunking that cuts tables, lists and procedures in half.
* Dense-only search for a corpus full of ids, codes and names.
* Filtering by permission after retrieval, which leaks restricted text into the prompt.
* Changing the embedding model without re-embedding the whole corpus; vectors from two models are not comparable.
* Judging quality by a few hand-picked questions with no fixed eval set.

## Practice

* Build a RAG app over 50 to 200 documents you care about. Log the retrieved chunk ids for every answer.
* Write a 30-question eval set with the correct chunk for each question. Report Recall@5 for chunk sizes 200, 400 and 800.
* Add BM25 and RRF to a dense-only retriever and measure the change in Recall@5 on questions that contain ids or names.
* Add a cross-encoder reranker over the top 50 and report MRR before and after.

## Interview questions (12)

1.RAG or fine-tuning?Easy

RAG gives the model knowledge: fresh, private or frequently changing facts. Fine-tuning changes behaviour: output format, tone, domain vocabulary, tool-call style. Start with prompting, add RAG for knowledge, and fine-tune only when you have a stable task, a real eval and roughly 500 or more good examples. They combine well: a small fine-tuned model with good retrieval is a common cost-for-quality choice.

2.How do you choose chunk size?Medium

Small chunks retrieve precisely but lose surrounding context. Large chunks keep context but add noise and cost. Start around 300 to 500 tokens with 10 to 20 percent overlap, then tune on a retrieval eval set by watching Recall@k. Structure-aware splitting on headings and paragraphs usually beats fixed sizes, and storing the heading path with each chunk keeps short chunks understandable.

3.Dense vs sparse vs hybrid retrieval?Medium

Dense retrieval (embeddings) matches meaning and handles paraphrases. Sparse retrieval (BM25) matches exact words such as product codes, names and error strings. Hybrid uses both and is the safer default. Merge the two ranked lists with reciprocal rank fusion, which needs no score calibration, then rerank the fused candidates.

4.What is HNSW?Medium

A layered graph index for approximate nearest neighbour search. Search starts in a sparse top layer and moves down to denser layers, which gives fast lookups with high recall. The trade-off is memory and build time. Three parameters control it: M (links per node), efConstruction (build effort) and efSearch (candidates kept per query). Raising efSearch improves recall at the cost of latency.

5.Your RAG system gives wrong answers. How do you debug it?Hard

First split the problem. Check whether the right chunk was retrieved. If not, fix retrieval: chunking, embedding model, hybrid search, reranking, query rewriting. If it was retrieved and the answer is still wrong, fix generation: the prompt, the order of chunks in the context, too many chunks, or the model itself. A trace that stores the retrieved chunk ids for every answer makes this a five-minute check.

6.How do you reduce hallucination in RAG?Medium

Instruct the model to answer only from context and to say when the context is not enough. Require citations, rerank to cut noisy chunks, and track faithfulness in evals. Add a score threshold: if the best reranked chunk is weak, return "not found" and do not generate. Keep a set of unanswerable questions in the eval set so false answers are counted.

7.Context windows are huge now. Is RAG dead?Medium

No. Sending everything costs more, is slower, and quality drops as the window fills. RAG also gives freshness, access control and citations. Long context changes the design (larger chunks, whole documents) but not the need to select. A corpus of millions of documents does not fit in any window anyway.

8.How do you keep the index up to date?Medium

Re-embed only changed documents, track document versions and hashes, delete stale chunks, and re-index fully when you change the embedding model, because vectors from different models are not comparable. Write the new version's chunks before deleting the old ones so a query never sees half a document.

9.How do you evaluate a RAG system?Medium

In two parts, because retrieval and generation fail independently. I build an eval set of 50 to 200 real questions, each with the chunk that answers it and a gold answer, plus some questions the corpus cannot answer. For retrieval I report Recall@k and MRR. For generation a judge model scores faithfulness, meaning every claim is supported by the retrieved context, and answer relevance, and I compare the final answer with the gold answer. I rerun the set on every change to chunking, the embedding model, the reranker or the prompt, and I sample live traffic for the same scores.

10.Cosine similarity or dot product?Easy

Cosine compares direction only; the dot product also rewards longer vectors. If the vectors are normalised to length 1 the two give identical rankings, so most systems normalise at indexing time and use the dot product because it is cheaper. Use whichever metric the embedding model was trained with; mixing them quietly lowers recall.

11.Should a permission filter run before or after the vector search?Hard

Inside or before it. Filtering after the search has two problems: the top k may contain nothing the user can see, so results come back empty, and a restricted chunk that reached the prompt has already leaked. Store the permission groups on every chunk and pass the filter into the index query. When a filter matches very few vectors, graph search slows down, so fall back to an exact scan over the allowed subset.

12.Why use a cross-encoder reranker if you already have embeddings?Medium

A bi-encoder compresses each text into one vector before it ever sees the query, so fine distinctions are lost. A cross-encoder reads the query and the chunk together and can tell "how to reset a password" from "password reset is disabled". It is too slow to run over the whole corpus, so it reranks only the top 50 or so candidates.

## Quiz

1.A corpus contains many error codes such as E-4012. Which retrieval setup is the safest default?

2.The correct chunk is in the top 50 but rarely in the top 5. What is the most direct fix?

3.You change the embedding model. What must happen to the index?

4.With k = 60, a chunk is ranked 1st by dense search and 3rd by BM25. What is its RRF score?

5.Which metric tells you whether every claim in the answer is supported by the retrieved chunks?

## Practice these problems

* [GENAIRAG pipeline for internal docs Q&AMedium](/ai/problems/rag-pipeline)
* [GENAIHybrid retrieval and reranking serviceMedium](/ai/problems/hybrid-search-reranking)
* [GENAIDocument ingestion and indexing pipeline for LLM useMedium](/ai/problems/document-ingestion-pipeline)
* [MLSDVector search at billion scaleHard](/ai/problems/vector-search-at-scale)
* [MLCODEBrute-force cosine top-k searchEasy](/ai/problems/cosine-top-k-search)
* [MLCODEMinimal RAG loop: chunk, embed, retrieve, promptEasy](/ai/problems/minimal-rag-loop)

## Further reading

* [Retrieval-Augmented Generation for Knowledge-Intensive NLP TasksPaperarxiv.org](https://arxiv.org/abs/2005.11401)
* [Efficient and robust approximate nearest neighbor search using HNSW graphsPaperarxiv.org](https://arxiv.org/abs/1603.09320)
* [Dense Passage Retrieval for Open-Domain Question AnsweringPaperarxiv.org](https://arxiv.org/abs/2004.04906)
* [RAGAS: Automated Evaluation of Retrieval Augmented GenerationPaperarxiv.org](https://arxiv.org/abs/2309.15217)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousPrompting and context engineering](/ai/learn/prompting-context-engineering)[NextWhat is fine-tuning - LoRA, QLoRA, DoRA](/ai/learn/fine-tuning-lora-qlora-dora)

## On this page

1. [Lesson](#lesson)
2. [Diagram](#diagram)
3. [Worked example](#example)
4. [Code](#code)
5. [Key takeaways](#takeaways)
6. [Common mistakes](#mistakes)
7. [Practice](#practice)
8. [Interview questions](#interview)
9. [Quiz](#quiz)
10. [Related problems](#problems)
11. [Further reading](#reading)
12. [My notes](#notes)

## In this lesson

1. [The problem RAG solves](#the-problem-rag-solves)
2. [Embeddings and similarity](#embeddings-and-similarity)
3. [What a vector database does](#what-a-vector-database-does)
4. [The RAG pipeline](#the-rag-pipeline)
5. [Chunking](#chunking)
6. [Dense, sparse and hybrid retrieval](#dense-sparse-and-hybrid-retrieval)
7. [Reranking: bi-encoder versus cross-encoder](#reranking-bi-encoder-versus-cross-encoder)
8. [Beyond the basic pipeline](#beyond-the-basic-pipeline)
9. [Measuring a RAG system](#measuring-a-rag-system)
10. [RAG, fine-tuning or a long context](#rag-fine-tuning-or-a-long-context)
