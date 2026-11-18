# S3-like Object Storage — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/object-storage

[All system design questions](/system-design)

#42HLDHardHigh-level design

# S3-like Object Storage

blob storagereplicationerasure codingmetadata

## Problem statement

Design a highly durable object store in the style of Amazon S3: users create **buckets**, upload immutable **objects** (any size from bytes to terabytes) identified by a key, download them, list keys in a bucket, and optionally keep versions. Objects are written once and read many times; the store must survive disk, host and rack failures without losing data.

## Requirements

### Functional

* Create buckets; upload, download and delete objects by `(bucket, key)`.
* List objects in a bucket with prefix filtering and pagination.
* Object versioning per bucket (optional); uploads of large objects in parts (multipart).
* Objects are immutable: an update is a new version, never an in-place edit.

### Non-functional

* Durability of 99.999999999% (11 nines): no object lost even with concurrent disk/host failures.
* Availability 99.99% for reads; writes may degrade before reads do.
* Scale to hundreds of petabytes and billions of objects; throughput limited by disks/network, not by metadata.
* Strong read-after-write consistency for new objects and for overwrites.

## Back-of-the-envelope estimates

* Assume **100 PB** of data and object sizes bimodal: 20% < 1 MB (metadata-heavy), 60% 1–64 MB, 20% > 64 MB.
* Average object ≈ 10 MB → **~10 billion objects** → metadata at ~1 KB/object (key, version, size, checksum, placement) ≈ **10 TB** of metadata → must be sharded; a single DB cannot hold it.
* Durability math: 3-way replication costs 3× raw storage (300 PB); **erasure coding** 8+4 (12 chunks, any 8 recover) costs 1.5× (150 PB) and tolerates 4 simultaneous chunk losses — the main cost lever.
* Writes: 10k objects/s × 10 MB = **100 GB/s** ingest at peak → thousands of data nodes with ~1 GB/s each of disk+network.
* Disks fail at ~1–2% per year; with 100k disks that is ~5 failures/day → repair/re-replication must be continuous and automatic.

## API

HTTP/REST, S3-compatible:

```
PUT    /{bucket}                              create bucket
PUT    /{bucket}/{key}            body=bytes  upload (returns ETag = checksum, version-id)
GET    /{bucket}/{key}[?versionId=]           download; supports Range: bytes=0-1048575
DELETE /{bucket}/{key}                        delete (adds a delete-marker when versioning is on)
GET    /{bucket}?prefix=photos/2024/&max-keys=1000&continuation-token=…   list

Multipart:
POST   /{bucket}/{key}?uploads                → uploadId
PUT    /{bucket}/{key}?uploadId=&partNumber=N → part ETag
POST   /{bucket}/{key}?uploadId=  { parts }   complete (assembles, returns final ETag)
```

Authentication via signed requests (HMAC of the canonical request with the user's secret key); authorisation via bucket policies / ACLs checked by the API service.

## Data model

**Metadata store** (sharded, strongly consistent — e.g. a distributed SQL / key-value store):

```
bucket   (bucket_id PK, owner_id, name UNIQUE, versioning bool, created_at)
object   (bucket_id, object_name, version_id, object_id, size, checksum, content_type,
          created_at, is_delete_marker)          PK (bucket_id, object_name, version_id DESC)
```

Shard `object` by `hash(bucket_id, object_name)` so one bucket's hot keys do not pile onto one shard; listing a prefix fans out to all shards and merges.

**Data store** (append-only):

```
object_id (UUID) → placement { data_nodes/chunks, offsets }
On a data node: large append-only files ("extents", ~GBs); small objects are packed into an extent,
and a local index maps object_id → (extent_file, offset, length, checksum)
```

Small objects go into shared extents to avoid one-file-per-object overhead; large objects are split into fixed chunks (e.g. 64 MB) each placed independently.

## High-level design

**Separate metadata from data.** Bytes are large, immutable and streamed; metadata is small, mutable and queried. The two scale on different axes and use different stores.

**Services**

* **API service** — stateless front door: auth (signed requests), bucket policies, rate limits, request routing, multipart orchestration.
* **Metadata service** — stores buckets and object records; the only place that knows which `object_id` is current for a key.
* **Data service** — placement service + data nodes. The *placement service* (Paxos/Raft-replicated, with a heartbeat view of every node) decides where an object's chunks go and tracks replica health. *Data nodes* store the bytes on local disks.

**Upload**: client → API (auth) → data service streams the bytes to the primary data node chosen by placement → primary replicates to secondaries (or erasure-codes into chunks) → returns `object_id` once the durability target is met → API writes the metadata row `{bucket, key, version, object_id, checksum}` → 200 OK. Write the data first, then metadata, so a crash never leaves a key pointing at missing bytes (an orphaned blob is garbage-collected later).

**Download**: API → metadata lookup (bucket, key[, version]) → `object_id` + placement → stream from a healthy data node (or reconstruct from any `k` of `n` erasure-coded chunks) → verify checksum → client.

**Listing**: a prefix query against the metadata shards, merged and paginated with a continuation token (the last key seen).

**Versioning**: every PUT inserts a new row with a new `version_id`; GET without a version returns the newest. DELETE inserts a *delete marker* row; the data is only freed by lifecycle rules or when the version is explicitly deleted.

## Architecture diagram

Rendering diagram…

## Deep dives

**Durability: replication vs erasure coding.** 3× replication is simple and fast to read (any copy) but costs 3× storage. Erasure coding (e.g. Reed–Solomon 8+4) splits an object into 8 data chunks and 4 parity chunks spread over 12 nodes/racks: survives any 4 losses at 1.5× cost, at the price of CPU on write and reconstruction reads when a chunk is missing. Typical choice: replicate small/hot objects, erasure-code large/cold ones; place chunks across failure domains (disk → host → rack → zone).

**Checksums everywhere.** Compute a checksum (CRC32C / MD5) on upload, store it in metadata and next to every chunk, verify on every read and in a background scrubber. Bit rot is real at petabyte scale; the scrubber re-replicates corrupted chunks automatically.

**Data node layout.** Writing one file per object kills the filesystem with inodes and seeks. Instead append objects into large sequential *extents* and keep a small on-disk index; deletes just mark space in the extent, and a compactor rewrites extents whose live ratio drops below a threshold (log-structured storage, like Haystack / Ambry).

**Metadata scaling.** Billions of rows → shard by `hash(bucket, key)`. Listing a prefix then has to query every shard — acceptable because listing is rare relative to GET/PUT; cache hot prefixes. Keep strong consistency on this store so read-after-write holds.

**Multipart upload.** Parts (5 MB–5 GB) upload in parallel to the data service as independent objects; `complete` writes a single metadata row that points at the ordered list of part `object_id`s (a manifest). Abandoned uploads are garbage-collected after N days.

**Garbage collection.** Sources of garbage: orphaned data from failed uploads (bytes written, metadata never committed), deleted versions, aborted multipart parts, compacted extents. A GC job walks metadata vs placement tables and reclaims blobs that nothing references, with a grace period to avoid racing with in-flight writes.

**Placement service availability.** It is on the write path, so run it as a small Raft/Paxos group with the placement map cached in API servers; reads must not depend on it (placement is stored in metadata or resolvable from the object id).

## Bottlenecks & mitigations

* Metadata store on every request → shard it, cache hot object rows in the API tier, and keep placement in the row so reads need one lookup.
* Hot bucket / hot key (one object downloaded millions of times) → serve through a CDN / edge cache and allow many replicas for hot objects.
* Reconstruction storms when a node with erasure-coded chunks dies → throttle repair bandwidth, prioritise chunks with the fewest surviving replicas.
* Small-object overhead (billions of tiny files) → pack into extents; batch metadata writes.

## Failure modes

* **Data node dies mid-upload**: the primary's ack never comes; the API retries placement with a new set and the half-written chunks are orphaned → GC. The client sees a retry, not a lost object.
* **Metadata write fails after data is stored**: object is unreachable but bytes exist → GC reclaims; the client gets an error and retries (safe because objects are immutable and keyed by content checksum).
* **Disk/rack loss**: scrubber + placement service notice missing replicas via heartbeats and re-replicate from survivors; with 8+4 coding up to 4 chunk losses per object are tolerated during repair.
* **Silent corruption**: detected by checksum on read or scrub; the bad chunk is rebuilt and the client is served from a good copy.
* **Placement service unavailable**: reads continue (placement cached in metadata); writes fail fast with 503 — availability of writes is the first thing sacrificed.

## Follow-up questions interviewers ask

* How would you implement bucket lifecycle rules (move to cold storage after 90 days, delete after a year)?
* How does erasure coding change read latency, and when would you still choose replication?
* How would you add cross-region replication with eventual consistency?
* How do you guarantee read-after-write consistency while sharding metadata?
* What does the garbage collector have to be careful about to never delete live data?

## Further reading

* [Guide: Object storage internalsIllustrated guide on this site](/system-design/learn/object-storage-internals)

[PreviousNearby Friends (Live Location Sharing)](/system-design/nearby-friends)[NextParking Lot](/system-design/lld-parking-lot)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftGoogleNutanixDropboxRubrik

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
