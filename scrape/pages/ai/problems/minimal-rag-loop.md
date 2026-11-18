# Minimal RAG loop: chunk, embed, retrieve, prompt — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/minimal-rag-loop

[AI problems](/ai#problems)

MLCODEImplement it#39Easy

# Minimal RAG loop: chunk, embed, retrieve, prompt

ragchunkingembeddingscosine similaritycitationsnumpy

## Problem statement

Implement retrieval-augmented generation (RAG) end to end in one Python file. RAG means: find the passages that are relevant to a question, put them in the prompt, and tell the model to answer only from them. Your code must split documents into overlapping pieces called chunks, turn each chunk into a vector (embed it), retrieve the top k chunks by cosine similarity, build a prompt with numbered chunks, and return an answer with citations. The corpus is 3 short help-centre documents. A simple deterministic embedder and a stub generator stand in for the embedding model and the LLM.

## Requirements

### Functional

* `chunk_words(text, size, overlap)` splits a document into windows of `size` words, where neighbours share `overlap` words.
* A deterministic embedder with `fit(texts)` and `embed(text)` that returns vectors of length 1.
* `retrieve(question, index, k, min_score)` returns the top k chunks by cosine similarity, best first, and drops any chunk that scores below `min_score`.
* `build_prompt(question, hits)` numbers the chunks `[1]` to `[k]` in rank order and tells the model to answer only from them.
* `answer(question, index)` returns the answer text, the ids of the cited chunks and the prompt. When no chunk passes the threshold it returns `not found` and does not call the generator.

### Non-functional

* Deterministic: no randomness and no network, so the same documents and question give the same prompt on every run.
* Every chunk has at most `size` words (default 30), and neighbours share exactly `overlap` words (default 10).
* Every chunk vector has length 1 within 1e-9, so one matrix-vector product gives all the cosine scores.
* The prompt holds at most k chunks (default 3), each with a score of at least `min_score` (default 0.2).
* Retrieval is exact brute force, O(N x V) for N chunks and V vocabulary words. That is fine up to a few hundred thousand vectors.
* All self-checks finish in under 1 second.

## API

```
def chunk_words(text: str, size: int = 30, overlap: int = 10) -> list[str]: ...

class TfidfEmbedder:
    def fit(self, texts: list[str]) -> "TfidfEmbedder": ...   # learn the vocabulary and IDF weights
    def embed(self, text: str) -> np.ndarray: ...             # (V,), length 1, or all zeros

def build_index(docs: dict[str, str], size: int = 30, overlap: int = 10) -> Index: ...

def retrieve(question: str, index: Index, k: int = 3,
             min_score: float = 0.2) -> list[tuple[Chunk, float]]: ...   # best first

def build_prompt(question: str, hits: list[tuple[Chunk, float]]) -> str: ...

def stub_generator(prompt: str) -> str: ...                   # stands in for the LLM

def answer(question: str, index: Index, generate=stub_generator,
           k: int = 3, min_score: float = 0.2) -> dict: ...
# {"answer": str, "citations": list[str], "prompt": str | None}
```

## Data model

```
docs      dict doc_id -> text                3 documents
Chunk     id "returns#0", doc_id, text       8 chunks at size 30, overlap 10
vocab     word -> column number              V = 97 words
idf       (V,)   log(N / df)                 0 for a word that is in every chunk
matrix    (N, V) = (8, 97) float64           one row of length 1 per chunk
query     (V,)                               same embedder, same vocabulary
scores    (N,) = matrix @ query              cosine similarity, from 0 to 1
hits      [(Chunk, score), ...]              top k, best first, score >= min_score
prompt    instruction, lines "[n] chunk text", question
result    {"answer": str, "citations": [chunk ids], "prompt": str or None}
```

## Approach

1. **Offline, chunk.** Split each document into windows of `size` words. Each window starts `size - overlap` words after the previous one. Give every chunk an id such as `returns#0`, which becomes the citation.
2. **Offline, fit the embedder.** The embedder is TF-IDF: a vector has one position per vocabulary word, and its value is the word's count in the text (term frequency) times a weight for how rare the word is (inverse document frequency, IDF). Build the vocabulary from all chunks and compute `idf = log(N / df)`, where `df` is the number of chunks that contain the word.
3. **Offline, embed and stack.** Turn each chunk into a TF-IDF vector, scale it to length 1, and stack the vectors into an `(N, V)` matrix. Steps 1 to 3 run again only when a document changes.
4. **Online, embed the question** with the same embedder. Words that are not in the vocabulary are ignored.
5. **Online, retrieve.** `scores = matrix @ query` gives the cosine similarity with every chunk. Sort, keep the top k, and drop any chunk below `min_score`.
6. **Online, the "not found" exit.** If nothing is left, return `not found` straight away. The generator is not called, so no tokens are spent and nothing can be invented.
7. **Online, build the prompt.** First the instruction to use only the numbered context and to cite it. Then the chunks as `[1]`, `[2]`, `[3]` in score order. The question goes last.
8. **Online, generate and cite.** Call the generator, read the `[n]` markers out of its text, and map each number to a chunk id. Numbers that were never in the prompt are dropped.

## Architecture diagram

Rendering diagram…

## Deep dives

### Overlap arithmetic

Each window starts `size - overlap` words after the previous one. With 100 words, size 40 and overlap 10, the step is 30 and the windows start at words 0, 30 and 60. For a text of n words, longer than `size`, the count is ceil((n - overlap) / (size - overlap)). Overlap exists so that a sentence cut by one boundary is whole in the next chunk. It costs storage: here each chunk adds 30 new words but stores 40.

### Normalise once, then cosine is a dot product

Cosine similarity is the dot product divided by both vector lengths. If every vector is scaled to length 1 at indexing time, the division disappears, and all N scores come from one `matrix @ query`.

### The threshold is the "not found" path

Top k always returns k chunks, even for a question about cricket. Without a minimum score the model receives unrelated text and may answer from it. The value 0.2 was read off this data: the right chunks score 0.42 to 0.69 and the off-topic question scores 0.05. It must be tuned again for every embedder.

### What the stand-ins hide

TF-IDF matches exact words only, so "refund" does not match "money back". A learned embedding model fixes that behind the same `embed` interface. The stub generator copies one sentence. A real LLM can ignore the context or cite a chunk number that does not exist, which is why citations are checked in code.

## Evaluation

**Correctness tests.**

* Chunking: 100 numbered words with size 40 and overlap 10 give windows that start at w0, w30 and w60. Neighbours share 10 words, removing the overlaps rebuilds the original text, and the chunk count matches the closed form for 9 lengths from 1 to 250 words.
* Index: 8 chunks, and every row has length 1. On two tiny texts the IDF matches a hand calculation: 0 for a word in both, ln 2 for a word in one. This catches counting word occurrences where chunks should be counted.
* Retrieval: each of 3 known questions puts the chunk that holds the fact at rank 1, with scores in falling order.
* Prompt: exactly the top 3 chunks, numbered 1 to 3 in score order, no text from any other chunk, instruction first and question last.
* Not found: an off-topic question scores under the threshold and returns `not found`. A generator that raises proves the LLM was never called.
* Citations: a generator that cites `[0]` and `[7]` when 2 chunks were shown has both numbers dropped.

**Complexity.** Indexing is O(total words) to count, plus O(N x V) to fill the dense matrix. A question costs O(N x V) for the scores plus O(N log N) for the sort. Memory is N x V floats, and most of them are 0. Real TF-IDF stores sparse rows, and learned embeddings use a few hundred to a few thousand dense dimensions.

**What a strong answer adds.** Measuring recall@k on a small set of question and chunk pairs before touching the prompt. Splitting on sentences or headings, not on fixed word counts. Storing the document title with each chunk. Saying that retrieval and generation fail separately and should be measured separately.

## Bottlenecks & mitigations

* Brute-force scoring costs O(N x V) per question. Past a few hundred thousand chunks an approximate nearest neighbour index is needed.
* `argsort` sorts all N scores to find 3 of them. `np.argpartition` finds the top k in O(N).
* The N x V matrix is mostly zeros, and its width grows with the vocabulary.
* The vocabulary and IDF weights are fitted on the corpus, so adding documents means refitting and re-embedding every chunk.

## Failure modes

* **Overlap equal to or larger than size.** The step is 0 or negative and the windows never advance. Mitigation: assert `0 <= overlap < size`.
* **A tiny tail chunk.** Without the stop check, the last window is a few words that the previous chunk already holds. A short chunk puts all its weight on few words and can outrank the full one. Mitigation: stop once a window reaches the end of the text.
* **Vectors are not normalised.** The dot product then favours long chunks. Mitigation: divide by the norm inside `embed` and test that rows have length 1.
* **The question is embedded differently from the chunks.** A different tokenizer, vocabulary or model makes the scores meaningless. Mitigation: one embedder object for both paths.
* **No threshold.** An off-topic question still gets k chunks and the model answers from them. Mitigation: `min_score`, and return `not found` before generation.
* **The model cites a chunk that was not shown.** Mitigation: keep only citation numbers from 1 to the number of chunks in the prompt.
* **Paraphrase misses.** A word-matching embedder cannot link "money back" to "refund". Mitigation: a learned embedding model, or hybrid search with a reranker.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""Minimal RAG loop in one file: chunk, embed, retrieve, build the prompt, answer with citations.

The embedder is TF-IDF in NumPy and the generator is a stub, so everything runs
offline and gives the same result every time. A real system swaps in a learned
embedding model and an LLM behind the same two interfaces.
"""
import math
import re
from dataclasses import dataclass

import numpy as np

NOT_FOUND = "not found"

def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())

# ---- 1. Chunk -----------------------------------------------------------------
def chunk_words(text, size=30, overlap=10):
    """Windows of `size` words. Each window starts `size - overlap` words after the last one."""
    assert 0 <= overlap < size, "overlap must be smaller than size"
    words = text.split()
    step = size - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):          # this window reached the end: stop, no tiny tail chunk
            break
    return chunks

def expected_chunks(n_words, size, overlap):
    """Closed form for the number of chunks, used to check the loop above."""
    return 1 if n_words <= size else math.ceil((n_words - overlap) / (size - overlap))

# ---- 2. Embed -----------------------------------------------------------------
class TfidfEmbedder:
    """Text -> unit vector with one dimension per vocabulary word, weighted by TF x IDF."""

    def fit(self, texts):
        docs = [set(tokenize(t)) for t in texts]
        self.index = {word: i for i, word in enumerate(sorted(set().union(*docs)))}
        df = np.zeros(len(self.index))          # in how many chunks does each word appear
        for doc in docs:
            for word in doc:
                df[self.index[word]] += 1
        self.idf = np.log(len(docs) / df)       # a word found in every chunk gets weight 0
        return self

    def embed(self, text):
        v = np.zeros(len(self.index))
        for word in tokenize(text):
            if word in self.index:              # words never seen at indexing time are ignored
                v[self.index[word]] += 1.0
        v *= self.idf
        norm = np.linalg.norm(v)
        return v / norm if norm else v          # unit length, so a dot product is the cosine

# ---- 3. Index and retrieve ----------------------------------------------------
@dataclass
class Chunk:
    id: str             # "doc_id#position", used as the citation
    doc_id: str
    text: str

@dataclass
class Index:
    chunks: list
    embedder: TfidfEmbedder
    matrix: np.ndarray  # (n_chunks, vocabulary), every row has length 1

def build_index(docs, size=30, overlap=10):
    """Offline path: runs once, and again whenever a document changes."""
    chunks = [Chunk(f"{doc_id}#{i}", doc_id, text)
              for doc_id, body in docs.items()
              for i, text in enumerate(chunk_words(body, size, overlap))]
    embedder = TfidfEmbedder().fit([c.text for c in chunks])
    matrix = np.stack([embedder.embed(c.text) for c in chunks])
    return Index(chunks, embedder, matrix)

def retrieve(question, index, k=3, min_score=0.2):
    """Top k chunks by cosine similarity, best first. Chunks under min_score are dropped."""
    scores = index.matrix @ index.embedder.embed(question)      # (n_chunks,)
    best = np.argsort(-scores, kind="stable")[:k]
    return [(index.chunks[i], float(scores[i])) for i in best if scores[i] >= min_score]

# ---- 4. Prompt, generate, cite ------------------------------------------------
def build_prompt(question, hits):
    lines = ["Answer the question using only the numbered context below.",
             "Cite the chunks you used like [1].",
             f"If the context does not contain the answer, reply exactly: {NOT_FOUND}",
             "",
             "Context:"]
    lines += [f"[{n}] {chunk.text}" for n, (chunk, _) in enumerate(hits, start=1)]
    lines += ["", f"Question: {question}", "Answer:"]
    return "\n".join(lines)

def stub_generator(prompt):
    """Stands in for the LLM: copies the context sentence that shares the most words
    with the question and cites its chunk number."""
    question = set(tokenize(prompt.split("\nQuestion: ")[1].split("\n")[0]))
    best = (0, "", 0)
    for number, text in re.findall(r"(?m)^\[(\d+)\] (.*)$", prompt):
        for sentence in re.split(r"(?<=[.?!])\s+", text):
            shared = len(question & set(tokenize(sentence)))
            if shared > best[0]:
                best = (shared, sentence, int(number))
    return f"{best[1]} [{best[2]}]" if best[0] else NOT_FOUND

def answer(question, index, generate=stub_generator, k=3, min_score=0.2):
    """Online path: runs for every question."""
    hits = retrieve(question, index, k, min_score)
    if not hits:                                # nothing relevant: do not call the LLM at all
        return {"answer": NOT_FOUND, "citations": [], "prompt": None}
    prompt = build_prompt(question, hits)
    text = generate(prompt)
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})
    citations = [hits[n - 1][0].id for n in cited if 1 <= n <= len(hits)]   # drop numbers we never showed
    return {"answer": text, "citations": citations, "prompt": prompt}

DOCS = {
    "returns": "You can return most items within 30 days of delivery for a full refund. "
               "The item must be unused and in its original box. Refunds reach your bank "
               "account in 5 to 7 working days after we receive the item. Sale items can be "
               "exchanged but not refunded. To start a return, open your orders page and "
               "choose the return option next to the item.",
    "shipping": "Standard delivery takes 3 to 5 working days. Delivery is free for orders "
                "above 500 rupees. Orders below 500 rupees pay a delivery charge of 40 rupees. "
                "Express delivery reaches metro cities the next day and costs 99 rupees. You "
                "can track a parcel from the orders page using its tracking number.",
    "account": "To reset your password, open the login page and choose the forgot password "
               "link. We send a reset code to your registered email address. The code expires "
               "in 15 minutes. If you no longer use that email address, contact support with "
               "your phone number to update it.",
}

if __name__ == "__main__":
    # 1. Overlap arithmetic on 100 numbered words: size 40, overlap 10, so the step is 30.
    words = [f"w{i}" for i in range(100)]
    chunks = [c.split() for c in chunk_words(" ".join(words), size=40, overlap=10)]
    assert [c[0] for c in chunks] == ["w0", "w30", "w60"] and [len(c) for c in chunks] == [40, 40, 40]
    assert all(a[-10:] == b[:10] for a, b in zip(chunks, chunks[1:]))       # neighbours share 10 words
    assert chunks[0] + [w for c in chunks[1:] for w in c[10:]] == words     # no word lost or repeated
    for n in (1, 39, 40, 41, 70, 71, 100, 101, 250):
        assert len(chunk_words(" ".join(["w"] * n), 40, 10)) == expected_chunks(n, 40, 10)
    assert len(chunk_words(" ".join(words[:71]), 40, 10)) == 3              # 71 words: starts 0, 30, 60
    print("chunking ok: 100 words, size 40, overlap 10 -> starts w0, w30, w60; neighbours share 10 words")

    # 2. Index: every row is a unit vector, so matrix @ query is the cosine.
    index = build_index(DOCS)
    assert index.matrix.shape[0] == len(index.chunks) == 8
    assert np.allclose(np.linalg.norm(index.matrix, axis=1), 1.0, atol=1e-9)
    print(f"index ok: {len(index.chunks)} chunks x {index.matrix.shape[1]} vocabulary words, rows have length 1")
    tiny = TfidfEmbedder().fit(["red red apple", "red pear"])               # IDF by hand: N = 2 texts
    assert tiny.idf[tiny.index["red"]] == 0.0 and np.isclose(tiny.idf[tiny.index["apple"]], np.log(2))
    assert np.allclose(tiny.embed("red red apple"), tiny.embed("apple"))    # "red" is in both texts: weight 0
    print("idf ok: a word in every text gets weight 0, a word in 1 of 2 texts gets ln 2")

    # 3. Known questions retrieve the chunk that holds the answer, and cite it.
    known = [("How many days do I have to return an item for a refund?", "returns", "within 30 days"),
             ("What delivery charge do orders below 500 rupees pay?", "shipping", "charge of 40 rupees"),
             ("How do I reset my password?", "account", "forgot password")]
    for question, doc_id, fact in known:
        hits = retrieve(question, index)
        scores = [s for _, s in hits]
        assert hits[0][0].doc_id == doc_id and fact in hits[0][0].text
        assert scores == sorted(scores, reverse=True) and len(hits) <= 3
        out = answer(question, index)
        assert fact in out["answer"] and out["citations"] == [hits[0][0].id]
        print(f"retrieval ok: {question!r} -> {hits[0][0].id} (score {scores[0]:.2f}) | {out['answer']}")

    # 4. The prompt holds exactly the top k chunks, numbered 1..k in score order, and nothing else.
    question = known[1][0]
    hits = retrieve(question, index, k=3, min_score=0.0)       # threshold off, to test k on its own
    prompt = build_prompt(question, hits)
    in_prompt = re.findall(r"(?m)^\[(\d+)\] (.*)$", prompt)
    assert len(hits) == 3 and [int(n) for n, _ in in_prompt] == [1, 2, 3]
    assert [text for _, text in in_prompt] == [chunk.text for chunk, _ in hits]
    top_ids = {chunk.id for chunk, _ in hits}
    assert all(c.text not in prompt for c in index.chunks if c.id not in top_ids)
    assert "using only the numbered context" in prompt and prompt.endswith(f"Question: {question}\nAnswer:")
    assert [c.id for c, _ in retrieve(question, index, k=1)] == [hits[0][0].id]
    assert len(retrieve(question, index, k=3)) == 2            # default threshold drops the weak third chunk
    print(f"prompt ok: 3 chunks numbered 1 to 3 in score order {[round(s, 2) for _, s in hits]}; "
          "the 0.2 threshold would keep 2")

    # 5. No relevant chunk: every score is under the threshold, so the LLM is never called.
    def must_not_run(prompt):
        raise AssertionError("the generator was called without context")

    off_topic = "Which team won the cricket world cup?"
    best_off_topic = float(np.max(index.matrix @ index.embedder.embed(off_topic)))
    out = answer(off_topic, index, generate=must_not_run)
    assert out == {"answer": NOT_FOUND, "citations": [], "prompt": None} and 0 < best_off_topic < 0.2
    assert answer("zxqv blorp", index, generate=must_not_run)["answer"] == NOT_FOUND   # no known word at all
    print(f"not found ok: best off-topic score {best_off_topic:.2f} is under the 0.2 threshold")

    # 6. Citations are checked in code: a number the prompt never contained is dropped.
    out = answer(known[0][0], index, generate=lambda prompt: "30 days [0] [1] [7]")
    assert out["citations"] == [retrieve(known[0][0], index)[0][0].id]
    print("citations ok: [0] and [7] were not in the prompt, so only [1] is kept ->", out["citations"])
    print("all checks passed")
```

## Follow-up questions interviewers ask

* Replace the TF-IDF embedder with a learned embedding model. What changes in the code, and what must be recomputed?
* Add hybrid search: BM25 next to the vectors, fused with reciprocal rank fusion.
* Add a reranker between retrieval and the prompt. How many candidates do you fetch, and how many do you keep?
* How would you choose `size`, `overlap`, `k` and `min_score` with data, not by eye?
* One document is edited. How do you update the index without rebuilding everything?
* Each user may see only some documents. Where does the permission filter go?

## Lessons that cover this

* [#8Vector DBs and RAGBuild with LLMs](/ai/learn/vector-dbs-rag)
* [#23Projects - RAG app, fine-tuned model, agent + evalsLater](/ai/learn/projects)

## Further reading

* [Retrieval-Augmented Generation for Knowledge-Intensive NLP TasksPaperarxiv.org](https://arxiv.org/abs/2005.11401)
* [NumPy documentationGuidenumpy.org](https://numpy.org/doc/stable/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAgent loop from scratch with tools and a step limit](/ai/problems/agent-loop-from-scratch)[NextRetry with exponential backoff and timeouts](/ai/problems/retry-with-backoff)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Approach](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Evaluation](#evaluation)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Reference solution](#code)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
