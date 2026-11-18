# ChatGPT-like chat service — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/chat-service

[AI problems](/ai#problems)

GENAIGenAI systems#19Hard

# ChatGPT-like chat service

streamingconversation storagecontext managementfile uploadsmultimodalReported at xAI

## Problem statement

Design the backend of a consumer chat assistant with 10 million daily users. A user sends a message and the answer streams back token by token. If the phone loses its connection, the stream resumes where it stopped. Conversations are saved, and they can grow far beyond what the model's context holds. Users also attach images, PDFs and spreadsheets, which must be processed and placed into the model's context. Model serving exists as an internal endpoint; you own everything in front of it.

## Requirements

### Functional

* Send a message and receive the answer as a token stream; stop a running answer on request.
* Resume a broken stream after a reconnect with no missing and no repeated text.
* Save every conversation, list a user's conversations, and page through old messages.
* Keep long conversations working by trimming and summarising history to fit a token budget.
* Upload images, PDFs and spreadsheets, show a processing status, and let the model answer questions about them.
* Enforce per-user message and token limits, and moderate inputs and outputs.

### Non-functional

* Time to first token under 1 s at p95 for a text message.
* 3,500 messages per second at peak and about 26,000 streams open at once.
* A client that reconnects within 5 minutes continues its stream with zero lost or duplicated tokens.
* No acknowledged message is lost; 99.95% availability for sending a message.
* Files up to 50 MB, 10 per message. An image is ready in 2 s and a 20-page PDF in 10 s at p95.
* The context sent to the model never exceeds a 24,000-token working budget; average cost stays under 0.003 USD per message at the assumed prices.

## Back-of-the-envelope estimates

**Traffic.** 10,000,000 daily users x 10 messages = 100 million messages/day = 1,157 per second on average. Plan for 3 times that at peak: 3,500 per second.

**Open streams.** One answer lasts 0.5 s to first token + 350 tokens x 20 ms = 7.5 s. 3,500 x 7.5 = 26,250 streams open at once.

**Model load.** 3,500 x 350 = 1,225,000 output tokens per second at peak. At an assumed 2,500 tokens per second per replica that is 490 replicas, 637 with 30% headroom. GPUs dominate the cost, so the backend must keep prompts short and cache-friendly.

**Tokens and cost.** An average request has 3,000 input tokens (system prompt, history, files). Per day: 300 billion input and 35 billion output tokens. At an assumed 0.50 and 1.50 USD per million: 150,000 + 52,500 = 202,500 USD/day, 0.002 USD per message.

**Messages.** 200 million rows/day (user plus assistant) x 1.2 KB = 240 GB/day, 88 TB/year before replication. 2,315 writes per second on average, about 7,000 at peak.

**Files.** 5% of messages carry a file: 5 million files/day x 2 MB = 10 TB/day, 300 TB if originals are kept for 30 days. Peak: 174 uploads per second. If 30% are PDFs and each needs 4 s of CPU (20 pages x 0.2 s), that is 52 x 4 = 208 cores busy.

**Stream buffer.** Streams started in 5 minutes at peak: 3,500 x 300 = 1,050,000, at about 4 KB each = 4.2 GB. Writing every token on its own would be 1,225,000 writes per second. Batching tokens every 100 ms gives 26,250 x 10 = 262,500.

## API

```
POST /v1/conversations                          -> { conversation_id }
GET  /v1/conversations?cursor=                  -> titles, newest first
GET  /v1/conversations/{id}/messages?cursor=    -> one page of history

POST /v1/conversations/{id}/messages
  headers: Idempotency-Key: <uuid>
  body:    { parent_message_id, content, file_ids?: [] }
  returns: 202 { user_message_id, assistant_message_id, stream_id }

GET  /v1/streams/{stream_id}                    (server-sent events)
  headers: Last-Event-ID: <seq>                 (sent by the client on reconnect)
  events:  id: <seq>   data: { delta }
           id: <seq>   data: { done, usage } | { error }
  410 when the buffer has expired: read the saved message

POST /v1/streams/{stream_id}/cancel

POST /v1/files            { name, bytes, sha256 } -> { file_id, upload_url }
POST /v1/files/{file_id}/complete               -> processing starts
GET  /v1/files/{file_id}
  returns: { status: "uploading" | "scanning" | "processing" | "ready" | "failed",
             kind, pages?, tokens?, error? }
```

## Data model

```
conversations(user_id, conversation_id, title, summary, summary_upto_seq,
              updated_at)
              PK (user_id, conversation_id); index (user_id, updated_at)

messages(conversation_id, seq, message_id, parent_message_id,
         role,                      -- user | assistant
         content, file_ids[], tokens, model,
         status,                    -- streaming | complete | cancelled | error
         created_at)
         PK (conversation_id, seq)  -- one partition per conversation

stream:{stream_id}                  -- in-memory store, expires 5 min after done
  entries: (seq, delta)             -- append only
  meta:    assistant_message_id, state, worker_id, heartbeat_at

files(file_id PK, user_id, conversation_id, kind,   -- image | pdf | sheet
      bytes, sha256, status, object_uri, pages, error, expires_at)

file_artifacts(file_id, part_no,
      kind,                         -- page_text | page_image | image
                                    -- | sheet_profile | chunk | outline
      text_uri, image_uri, tokens, embedding VECTOR(1024))

usage(user_id, day, messages, tokens_in, tokens_out, files)
```

## High-level design

**Upload path (before the message is sent)**

1. The client asks for a `file_id` and a pre-signed URL (a short-lived URL that allows one upload straight to object storage), then uploads in resumable parts. API servers never carry file bodies.
2. `complete` puts a job on a queue. A file worker checks the real type from the file's first bytes, enforces size and page limits, and runs a malware scan.
3. A parser in a sandbox (an isolated process with no network access and with CPU, memory and time limits) turns the file into artifacts: a resized image, text per PDF page, with OCR (optical character recognition) for scanned pages, or a profile of each sheet. Each artifact is stored with its token count, and the file becomes `ready`.

**Chat path (every message)**

4. The chat service authenticates the user and checks the per-user message and token limits.
5. The chat service saves the user message and an empty assistant message with status `streaming`, creates a stream buffer, and returns `stream_id`. The idempotency key makes a repeated send return the same ids.
6. The context builder assembles the prompt inside the 24,000-token budget: system prompt, conversation summary, earlier turns with their file content, then the new message. Input moderation runs in parallel.
7. A generation worker calls model serving and appends batches of tokens, each with a sequence number, to the stream buffer. Output moderation checks the text as it grows.
8. A stream edge node holds the client's connection, reads the buffer and sends server-sent events (SSE), a one-way HTTP stream from server to client. On reconnect it replays from the last sequence number the client saw.
9. When generation ends, the worker saves the full assistant message, marks it `complete` and records usage.

**Background**

10. Jobs write the conversation title, update the summary when history passes its limit, and delete expired files.

## Architecture diagram

Rendering diagram…

## Deep dives

### Resumable token streams

A stream breaks if generation is tied to one connection. So split them. The generation worker owns the model call and appends `(seq, delta)` entries to a per-stream log in an in-memory store. Stream edge nodes only read that log and write server-sent events with `id: seq`.

When a connection drops, the browser reconnects by itself and sends the last id it received in the `Last-Event-ID` header. Any edge node can serve it: replay every entry after that id, then follow the live log. The client ignores any `seq` it has already shown, so text is never repeated.

A disconnect is not a cancel. The worker finishes the answer and saves it, so the user finds it when the app reopens. Only the cancel call stops the model and frees its GPU slot. The log expires 5 minutes after the answer ends; later requests get a 410 and load the saved message.

### Conversation storage

The main read is "the latest messages of one conversation". Partition `messages` by `conversation_id` and sort by `seq`, so that read touches one partition. The sidebar reads a second table keyed by user and sorted by `updated_at`. Nothing queries across users, so the store shards cleanly and the 88 TB a year spreads evenly.

The user message is written before the model is called, so an acknowledged message survives a crash. Regenerate and edit do not overwrite. They add a message with the same `parent_message_id`, which turns the conversation into a tree. The context builder walks from the newest message back to the root.

### Fitting a long conversation into the context

Cost and time to first token grow with input, so the service uses a working budget smaller than the model's window: system prompt 1,000 tokens, summary 1,000, files 8,000, recent turns 12,000, reply 2,000. Total 24,000.

Recent turns stay word for word. When they pass 12,000 tokens, a small model folds the oldest 6,000 into the running summary, and `summary_upto_seq` moves forward. Cut only between turns.

Summarise in large steps, not a little every turn. Prefix caching reuses the model's work only while the start of the prompt is identical. Dropping one old message per turn changes the prompt right after the summary on every turn, so the whole history is prefilled again each time. One 6,000-token step keeps the prefix unchanged for about 13 turns of 450 tokens. Put nothing that changes per request, such as the time, at the top.

Summaries lose detail. Keep the raw messages, and search them when the user refers to something old.

### File uploads: from bytes to context

**Process once, by type.**

* **Image.** Decode, strip metadata such as location, shrink to the model's largest input size and store it. It enters the context as an image block, an assumed 1,000 tokens.
* **PDF.** Read the text layer page by page, an assumed 500 tokens a page. A page with no text is a scan: run OCR. Keep a rendered image of pages with charts or tables, because the text layer loses their layout.
* **Spreadsheet.** Never paste the rows. 100,000 rows x 10 columns is millions of tokens, and models add up raw numbers badly. Store a profile per sheet: column names, types, row count, the first 20 rows and basic statistics. For real calculations the model writes code that runs in a sandbox on the full file.

**Then fit the file budget.** A 12-page PDF is 6,000 tokens and goes inline, at the turn where it was attached, so the prefix stays cacheable. A 200-page report is 100,000 tokens. It is split into chunks and embedded into an index for that conversation. Each question retrieves the best chunks, and a short outline of the file stays in context so the model knows what else exists.

**Treat files as hostile.** Parsers run only inside the sandbox, because an .xlsx file is a zip archive that can expand to gigabytes. Text inside a file is data, never instructions. The same `sha256` from the same user reuses the stored artifacts.

## Evaluation

**Offline, context policy.** Build 200 long test conversations in which a fact stated early (turn 3 of 60) is needed at the end. Measure the share answered correctly under each trimming policy, and the average input tokens it costs. Score summaries for faithfulness with an LLM judge checked against 100 human labels.

**Offline, files.** A file question set per type: 100 PDFs (text and scanned), 100 images, 100 spreadsheets, each with questions that have known answers, such as "what is the total on page 14" or "which month had the highest revenue". Report answer accuracy per type, and the parser's own numbers: character error rate of OCR, share of tables extracted with the right cells, share of files that fail.

**Offline, streaming.** A chaos test opens 10,000 streams, cuts connections at random points and kills workers. Assert that every reassembled answer equals the saved message exactly: no gap, no repeat.

**Load test.** Replay real prompt lengths at 3,500 messages per second. Record p95 time to first token, time per output token and the prefix-cache hit rate.

**Online.** Time to first token, stream completion rate, reconnect success rate, regenerate rate and thumbs-down rate (both signal a bad answer), file processing time and failure rate by type, share of requests where history was trimmed, cost per message and moderation block rate.

**A/B setup.** Randomise by user. Test one change at a time, for example a 16,000-token against a 24,000-token budget, and compare regenerate rate and cost per message.

**Guardrails.** Moderation on input text, on extracted file text and on the output stream. A hard check that the prompt is inside the budget before every model call.

## Bottlenecks & mitigations

* GPU capacity: 1,225,000 output tokens per second at peak is the largest cost and the first thing to saturate.
* 26,000 long-lived connections at the edge; a deploy must drain or hand over streams, not cut them.
* The stream buffer takes 262,500 writes per second even after batching, so it needs several shards.
* OCR of scanned PDFs: a 200-page scan takes minutes and backs up the file queue at peak.
* Large inline files are prefilled again whenever the prefix cache misses, which lifts time to first token for every turn of that conversation.

## Failure modes

* **The client loses its connection mid-answer.** Mobile networks drop often. Mitigation: the sequence-numbered buffer and replay after `Last-Event-ID`.
* **A generation worker dies mid-answer.** The stream stops with no end event. Mitigation: worker heartbeats, an error event from the edge, the partial text saved as `error`, and a retry button.
* **The same message is sent twice.** The client retries a send whose response was lost. Mitigation: the idempotency key returns the first `stream_id`.
* **The prompt exceeds the context.** A big file plus long history. Mitigation: token counts stored per message and per artifact, a hard budget in the context builder, and a note to the user when a file was only partly used.
* **The summary drops a fact.** The user asks about something from 80 turns ago. Mitigation: keep raw messages, retrieve from old turns, and measure recall on the long-conversation set.
* **A malicious file.** Malware, a zip bomb (a small archive that expands to gigabytes), or hidden text that says "ignore your instructions". Mitigation: scan, sandbox with limits, mark file text as data, and give no file-driven access to tools that change anything.
* **A parser hangs or fails.** A damaged or unusual PDF. Mitigation: a time limit per page, fallback from text layer to OCR to page images, and `failed` with a reason the user can read.
* **The stream buffer is lost.** A shard restarts. Mitigation: the edge returns an error, the client polls the saved message, and nothing durable depended on the buffer.

## Follow-up questions interviewers ask

* A user uploads a 500-page PDF and asks for a full summary. What runs, and how long does the user wait?
* How do "regenerate" and "edit an earlier message" change storage and the context builder?
* How would you add memory that carries across conversations?
* A region fails at peak. What do users with open streams see, and what is lost?
* Free and paid users share one GPU pool. How do you keep paid latency steady?
* Users now upload audio and video. Which parts of the file pipeline change?

## Lessons that cover this

* [#17LLM system designShip](/ai/learn/llm-system-design)

## Further reading

* [HTML Standard: Server-sent eventsGuidehtml.spec.whatwg.org](https://html.spec.whatwg.org/multipage/server-sent-events.html)
* [Lost in the Middle: How Language Models Use Long ContextsPaperarxiv.org](https://arxiv.org/abs/2307.03172)
* [vLLM documentationGuidedocs.vllm.ai](https://docs.vllm.ai/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousInsurance claims decision agent with RAG and a token budget](/ai/problems/claims-decision-agent)[NextDocument ingestion and indexing pipeline for LLM use](/ai/problems/document-ingestion-pipeline)

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
