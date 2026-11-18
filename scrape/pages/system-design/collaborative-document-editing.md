# Collaborative Document Editing (Google Docs) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/collaborative-document-editing

[All system design questions](/system-design)

#32HLDHardHigh-level design

# Collaborative Document Editing (Google Docs)

OTCRDTwebsocketsversioningconsistency

## Problem statement

Design a document editor where many users edit the same document simultaneously, see each other's cursors and changes in real time, never lose edits, and can view history.

## Requirements

### Functional

* Create/open documents; rich text.
* Concurrent editing by many users with real-time propagation.
* Cursor/presence; comments.
* Version history; offline editing that merges on reconnect.
* Sharing and permissions.

### Non-functional

* Edit propagation < 100 ms in-region.
* Convergence: all clients end with the same document state.
* Durability: every accepted operation persisted.
* 100 concurrent editors per doc; millions of docs.

## Back-of-the-envelope estimates

* Ops: a typing user emits ~5 ops/s; 100 editors → 500 ops/s per doc; 1M active docs × avg 2 editors ≈ 10M ops/s globally — partition by document.
* Op size ~50 B; op log per doc grows ~1 MB/hour of active editing; snapshot every N ops to bound replay.
* Connections: 10M concurrent WebSockets → ~20 servers per 1M with sticky routing per doc.

## API

```
WS  /v1/docs/{docId}/collab
  → { type:"op", clientId, baseVersion, ops:[{retain:5},{insert:"hi"},{delete:2}] }
  ← { type:"ack", version }
  ← { type:"op", version, ops:[...], author }      (others' transformed ops)
  → { type:"cursor", position }
REST:
GET  /v1/docs/{id}            → snapshot + version
GET  /v1/docs/{id}/history?from=&to=
POST /v1/docs/{id}/share
```

## Data model

```
documents  (doc_id, owner, title, current_version, snapshot_ref, updated_at)
ops        (doc_id, version, op JSON, author, ts)     PK(doc_id, version)   -- append-only op log
snapshots  (doc_id, version, content_ref)             -- every ~1000 ops
presence   Redis: doc:{id}:users → {user: cursor, ts} TTL 30s
acl        (doc_id, user_id, role)
```

## High-level design

1. **Client** holds the doc state and a pending op buffer; edits apply locally immediately (optimistic), then send to the server with the version they were based on.
2. **Collab server (one leader per doc)**: all ops for a document route to one server (consistent hashing on `doc_id`). It serialises ops: for an incoming op based on version `v` while the server is at `v+k`, it **transforms** the op against the `k` newer ops (**Operational Transformation**), appends it as version `v+k+1` to the op log, acks the author, and broadcasts the transformed op to other clients — who transform it against their own pending ops.
3. **Persistence**: op log in a DB partitioned by doc; periodic **snapshots** so loading a doc = latest snapshot + replay of the tail.
4. **Presence** in Redis with TTL; cursor updates broadcast at most every 50–100 ms.
5. **History**: any version = snapshot + ops replay; named versions stored as snapshots.
6. **Offline**: client queues ops; on reconnect, sends them with its base version; server transforms as usual (long divergence may produce odd merges but converges).
7. **CRDT alternative**: each character gets a unique position id; ops commute, no central transform needed, better for peer-to-peer/offline; cost is metadata size and tombstones. OT with a central server is simpler and what Docs uses.

## Architecture diagram

Rendering diagram…

## Deep dives

**Why one leader per doc**: OT needs a total order of ops; a single serialiser per document gives it without distributed consensus. Failover re-hashes the doc to another server that loads the snapshot + log.

**OT correctness**: transform functions must satisfy TP1 (convergence with a central server). Keep the op model minimal (retain/insert/delete + attributes) to make transforms tractable.

**Client-side**: ops are applied locally before ack (no lag), and every incoming remote op is transformed against the unacked local ops.

**Rich text** as attributes on ranges within the same op model; embedded objects (images, tables) as atomic inserts with ids.

## Bottlenecks & mitigations

* Very popular doc (thousands of viewers) → viewers get a read-only broadcast fan-out via a pub-sub tier, not per-viewer OT.
* Op log replay on open → frequent snapshots; cap tail length.
* Server hot-spot for a few huge docs → docs are the partition unit; isolate large docs on dedicated servers.
* Presence chatter → throttle cursor updates; drop presence for viewers beyond N.

## Failure modes

* **Collab server crash**: clients reconnect; router assigns a new leader that loads snapshot + log; clients resend unacked ops with base version → transformed normally.
* **Op log write failure**: no ack → client keeps the op pending and retries; server must not broadcast before persisting.
* **Divergence bug**: periodic hash of state from clients vs server; on mismatch, client reloads from server state.
* **Network partition with offline edits**: merged on reconnect via OT; conflicting edits to the same span produce a deterministic (if imperfect) result.

## Follow-up questions interviewers ask

* When would you choose CRDT over OT?
* How would you implement comments anchored to text that keeps moving?
* How would you add spreadsheet-style formulas with dependency recalculation?

[PreviousOnline Coding Judge (LeetCode / HackerRank)](/system-design/online-code-judge)[NextMaps & Navigation (routing, ETA)](/system-design/google-maps-navigation)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleMicrosoftAtlassianNotionAmazon

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [High-level design](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Follow-ups](#follow-ups)

## Your notes

Saved

Autosaves to this browser.
