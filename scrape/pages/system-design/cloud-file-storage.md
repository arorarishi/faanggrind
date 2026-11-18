# Cloud File Storage & Sync (Google Drive / Dropbox) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/cloud-file-storage

[All system design questions](/system-design)

#17HLDHardHigh-level design

# Cloud File Storage & Sync (Google Drive / Dropbox)

chunkingdeduplicationsyncmetadataobject storage

## Problem statement

Design a service where users upload files, access them from any device, share them with others, and have changes synced across devices efficiently with version history.

## Requirements

### Functional

* Upload/download files and folders from web, desktop and mobile.
* Automatic sync: edits on one device propagate to others.
* Sharing with permissions; links.
* Version history and restore; trash.
* Offline edits merged on reconnect.

### Non-functional

* Durability 11 nines for file content.
* Bandwidth-efficient sync (only changed parts are transferred).
* Consistency: a user sees their own writes immediately; others within seconds.
* Scale: 1B files, 10 PB, 100M users.

## Back-of-the-envelope estimates

* 100M users × 10 GB average = 1 EB nominal; dedup + compression + real usage ≈ 100–200 PB.
* Uploads: 10M files/day × 5 MB = 50 TB/day.
* Chunk size 4 MB → 1B files ≈ 3B chunks; chunk metadata (hash 32 B + refs) ≈ 200 GB — a sharded relational/KV store.
* Sync notifications: 100M devices long-polling/WebSocket; change events ~1k/s average.

## API

```
POST /v1/files/upload/init     { path, size, chunkHashes[] }  → { fileId, missingChunks[] }
PUT  /v1/chunks/{hash}         (upload only chunks the server doesn't have)
POST /v1/files/upload/commit   { fileId, version }
GET  /v1/files/{id}/download   → presigned URL(s)
GET  /v1/changes?cursor=       → list of metadata changes since cursor (long-poll)
POST /v1/shares                { fileId, userId|link, role }
GET  /v1/files/{id}/versions
```

## Data model

```
files      (file_id, owner_id, parent_id, name, current_version, is_deleted, modified_at)
versions   (file_id, version, size, chunk_list [hash...], created_by, created_at)
chunks     (chunk_hash PK, size, storage_key, ref_count)
shares     (file_id, grantee_id, role)
device_cursors (device_id, last_cursor)
change_log (user_id, cursor SEQ, file_id, change_type, version)
Blob storage: chunks stored by content hash (S3-style), encrypted at rest.
```

## High-level design

1. **Client**: watches the local folder; on change, splits the file into chunks (fixed 4 MB, or content-defined chunking for insert-resilient dedup), hashes each (SHA-256), and asks the server which chunks are missing. Uploads only those, then commits a new version referencing the full chunk list.
2. **Block/chunk service**: stores chunks in object storage keyed by hash → global deduplication across users; reference counting for GC.
3. **Metadata service**: relational DB (sharded by user) holding the file tree and versions; every commit appends to the user's `change_log` with a monotonically increasing cursor.
4. **Sync/notification service**: devices keep a long-poll/WebSocket; on a new change\_log entry for a user, subscribers are notified and fetch changes since their cursor, then download only missing chunks.
5. **Sharing**: ACL rows; shared files appear in the grantee's change log too (via fan-out on share/commit).
6. **Versioning**: a version is just a chunk list; old versions cost only the chunks that differ.
7. **Conflicts**: optimistic concurrency on `current_version`; a stale commit creates a 'conflicted copy' rather than overwriting.

## Architecture diagram

Rendering diagram…

## Deep dives

**Delta sync**: content-defined chunking (Rabin fingerprints) keeps chunk boundaries stable when bytes are inserted mid-file, so a 1-byte edit re-uploads ~1 chunk, not the whole tail.

**Dedup safety**: hash collisions are cryptographically negligible; still verify chunk size + hash on upload. Privacy: cross-user dedup means the server can tell two users have the same file — acceptable for most, encrypt-per-user if not.

**Consistency model**: metadata DB is the source of truth; a device's view is 'metadata as of cursor N', which makes sync resumable and idempotent.

**Large folders**: change log per user, not per file, so moving a folder with 10k files is one metadata change with a subtree update done server-side.

## Bottlenecks & mitigations

* Metadata DB hot users (huge shared drives) → shard by owner; cache directory listings.
* Notification fan-out for a file shared with 100k users → batch/fan-out asynchronously; recipients poll on open if not yet notified.
* Chunk GC across billions of refs → periodic mark-and-sweep with ref counts; never delete synchronously.
* Small-file overhead (1 KB files still cost a chunk + metadata) → pack small files into container chunks.

## Failure modes

* **Upload interrupted**: chunks are idempotent by hash; resume by re-asking which are missing.
* **Commit fails after chunks uploaded**: orphan chunks reclaimed by GC; client retries commit.
* **Concurrent edits on two devices**: version mismatch → conflicted copy; user resolves.
* **Object storage region outage**: cross-region replication; reads fail over; writes queue client-side.
* **Metadata corruption/bug**: versions are immutable, so any file can be restored to a prior version.

## Follow-up questions interviewers ask

* How would you implement real-time collaborative editing on top of this?
* How would you do client-side end-to-end encryption and still dedup?
* How do you enforce storage quotas efficiently?

## Further reading

* [Guide: Cloud file storage and syncIllustrated guide on this site](/system-design/learn/file-sync)
* [Differential synchronization (Neil Fraser)Articleneil.fraser.name](https://neil.fraser.name/writing/sync/)
* [Differential synchronization (Google tech talk)Videoyoutube.com](https://www.youtube.com/watch?v=S2Hp_1jqpY8)
* [How we've scaled DropboxVideoyoutube.com](https://www.youtube.com/watch?v=PE4gwstWhmc)

[PreviousDistributed Message Queue (Kafka)](/system-design/distributed-message-queue)[NextProximity / Nearby Places Service (Yelp, Google Maps 'near me')](/system-design/proximity-service)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

GoogleDropboxMicrosoftAmazonAppleAtlassian

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
12. [Further reading](#reading)

## Your notes

Saved

Autosaves to this browser.
