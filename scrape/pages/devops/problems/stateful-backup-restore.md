# Backup and restore for stateful workloads on Kubernetes — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/stateful-backup-restore

[DevOps problems](/devops#problems)

DESIGNPlatform design#15Medium

# Backup and restore for stateful workloads on Kubernetes

backupveleropostgresqlebsdisaster-recoverykubernetes

## Problem statement

A company runs PostgreSQL (400 GB), Redis and a 3-broker Kafka cluster as StatefulSets inside EKS on EBS volumes, next to 40 stateless services. Last month an engineer ran `kubectl delete namespace orders` against production by mistake. The PersistentVolumeClaims went with the namespace, the EBS volumes were deleted by the reclaim policy, and the only backup was a 6-hour-old database dump on a laptop. Design backup and restore for every kind of state in this cluster, with restores that are tested, and controls that make the same mistake impossible.

## Requirements

### Functional

* Classify every piece of state (databases, caches, queues, object storage, Kubernetes objects) and decide what moves to a managed service and what stays in the cluster.
* Kubernetes objects and volumes are backed up on a schedule with Velero; databases get application-consistent backups with point-in-time recovery.
* Backups are encrypted, copied to a second region, and kept for a defined retention per data class.
* A restore into a scratch namespace runs monthly and verifies row counts and checksums; the result is recorded.
* Deleting a production namespace, PVC or backup bucket requires an explicit extra step; a plain `kubectl delete` is refused.
* Runbooks exist for: restore one table, restore the database to a time, restore a whole namespace, rebuild the cluster in another region.

### Non-functional

* PostgreSQL: RPO 5 minutes, RTO 1 hour for a 400 GB database.
* Kubernetes objects and Kafka topic data: RPO 6 hours, RTO 2 hours; Redis cache: RPO not required, RTO 10 minutes (rebuild from source).
* Backup cost under 400 USD per month for 30-day retention.
* Backup jobs add under 10 percent extra I/O load on the database during the backup window.
* Cross-region copy lands within 1 hour of the backup finishing.
* Monthly restore test finishes in under 2 hours and is fully automated.

## Back-of-the-envelope estimates

**Database size and change.** 400 GB with an assumed 5 percent of pages changing per day: 20 GB of changed data daily.

**WAL volume.** An assumed 300 writes per second averaging 1,500 bytes of WAL each (full-page writes included): 300 x 1,500 x 3,600 = 1.62 GB per hour, 39 GB per day. WAL segments are 16 MB, so about 101 segments per hour, one every 36 seconds. With `archive_timeout = 60s` a segment is shipped at least once a minute, so the RPO is about 1 minute even when writes are slow, well inside the 5 minute target.

**Base backup window.** `pg_basebackup` streaming to S3 at an assumed 100 MB per second: 400,000 MB / 100 = 4,000 seconds, about 67 minutes, run weekly at 02:00 on a replica so the primary is not touched.

**Storage for 30 days (assumed prices).** EBS snapshots for Kafka and the database volumes: a 400 GB full plus 30 daily incrementals of 20 GB = 1,000 GB at 0.05 USD per GB-month = 50 USD. S3 for base backups and WAL: 4 weekly base backups x 400 GB = 1,600 GB plus 30 x 39 GB of WAL = 1,170 GB, total 2,770 GB at 0.023 USD = 64 USD, and a cross-region copy doubles it to about 128 USD plus transfer at 0.02 USD per GB x 2,770 = 55 USD. Velero object backups are a few MB. Total about 235 USD, under the 400 USD target.

**Restore time.** Download 400 GB from S3 at an assumed 200 MB per second: 2,000 seconds, 33 minutes. Replaying up to 6 hours of WAL (9.7 GB) at 50 MB per second: about 3 minutes. Add volume provisioning, pod start and verification: a restore to any point in the last 7 days takes about 45 minutes, under the 1 hour RTO. A 6-hour-old dump restored with `pg_restore` would take longer than the base backup and lose 6 hours, which is the whole lesson.

## API

```
Velero (runs in namespace velero, bucket s3://company-backups/velero, region ap-south-1)
  velero schedule create platform-objects --schedule="0 */6 * * *" --ttl 720h \
      --include-namespaces '*' --exclude-namespaces kube-system \
      --snapshot-volumes=false                      # objects only, every 6 hours
  velero schedule create kafka-volumes --schedule="0 3 * * *" --ttl 720h \
      --include-namespaces kafka --snapshot-move-data   # CSI snapshot, data copied to S3
  velero backup describe <name> --details
  velero restore create --from-backup platform-objects-20261103020000 \
      --include-namespaces orders --namespace-mappings orders:orders-restore-test

PostgreSQL (StatefulSet pg, primary + 1 replica; backup tool runs as a sidecar)
  weekly:  pg_basebackup from the replica -> s3://company-backups/pg/base/<date>/
  always:  archive_command ships each 16 MB WAL segment -> s3://company-backups/pg/wal/
  restore: pull base, set restore_command and recovery_target_time, touch recovery.signal

Admission control (ValidatingAdmissionPolicy, operations DELETE)
  apiVersion: admissionregistration.k8s.io/v1
  kind: ValidatingAdmissionPolicy
  spec.matchConstraints.resourceRules:
    - apiGroups [""]   resources [persistentvolumeclaims, namespaces]   operations [DELETE]
  spec.validations:
    - expression: "has(oldObject.metadata.annotations) &&
                   'backup.company.io/allow-delete' in oldObject.metadata.annotations"
      message: "Add the allow-delete annotation (needs the sre-breakglass role) before deleting"
  binding: validationActions [Deny], namespaces labelled env=prod

Monthly restore test (CronJob restore-test, first Sunday 04:00)
  1. velero restore into namespace orders-restore-test
  2. restore PostgreSQL to now minus 1 hour into pg-restore-test
  3. run SELECT count(*) per table, compare with the production count from the same time
  4. write the result to the restore-tests table and post to #sre; delete the scratch namespace
```

## Data model

```
State classes and where they live after the redesign
  class                      store                    RPO     RTO     method
  orders, users (relational)  PostgreSQL in EKS        5 min   1 h     base backup + WAL to S3
                              (or RDS: PITR built in)
  sessions, rate counters     Redis in EKS             n/a     10 min  no backup; rebuild from source
  events (queue)              Kafka in EKS 3 brokers   6 h     2 h     EBS snapshots via Velero + CSI
                              (or MSK: managed)
  uploads, reports            S3                       0       0       versioning + replication + object lock
  Kubernetes objects          etcd (EKS managed)       6 h     2 h     Velero to S3

AWS
  S3 bucket company-backups          SSE-KMS, versioning on, Object Lock compliance 35 days
                                     lifecycle: STANDARD -> STANDARD_IA at 7 days, expire at 35 days
  S3 bucket company-backups-dr       replication target in a second region, same lock
  KMS key backups                    separate key, key policy denies delete to everyone but security
  IAM role velero                    Pod Identity; s3:PutObject, GetObject, ListBucket, ec2:CreateSnapshot
  EBS snapshots                      tagged backup=velero, copied by Data Lifecycle Manager cross-region

Kubernetes
  StorageClass gp3-retain            reclaimPolicy Retain, allowVolumeExpansion true
  VolumeSnapshotClass ebs-csi        driver ebs.csi.aws.com, deletionPolicy Retain,
                                     label velero.io/csi-volumesnapshot-class: "true"
  Pod annotations (postgres)         pre.hook.backup.velero.io/command: pg_backup_start wrapper
                                     post.hook.backup.velero.io/command: pg_backup_stop wrapper
  Table restore_tests                (date, backup_name, namespace, tables_checked, rows_matched, ok)
```

## High-level design

**Classify and move what should move**

1. List every PVC and every bucket, assign each to a class with an RPO and RTO, and decide: PostgreSQL moves to RDS or Aurora within the year (point-in-time recovery, snapshots and cross-region copies come built in; retention up to 35 days), Kafka moves to MSK, Redis stays because it holds nothing worth backing up. Until the moves happen, the design below protects what is in the cluster.

**Stop the next accident**

2. Change the StorageClass to `reclaimPolicy: Retain` so deleting a PVC leaves the EBS volume behind.
3. Add a ValidatingAdmissionPolicy that denies DELETE on namespaces and PVCs in `env=prod` unless an allow-delete annotation is present, and give the right to add that annotation to a break-glass role that pages when used.
4. Enable versioning and Object Lock on the backup bucket so a stolen credential or an angry script cannot erase history.

**Back up Kubernetes objects and volumes**

5. Install Velero with `--features=EnableCSI --use-node-agent`, with Pod Identity for S3 and EC2 access. Schedule an objects-only backup of every namespace every 6 hours and a daily volume backup of Kafka with `--snapshot-move-data`, which copies the snapshot content into S3 so it survives the loss of the EBS region.

**Back up the database properly**

6. Run a sidecar that ships every WAL segment to S3 with `archive_mode = on`, `wal_level = replica` and `archive_timeout = 60s`, and a weekly `pg_basebackup` from the replica. This gives point-in-time recovery to any minute in the last 35 days.
7. Add Velero pre and post hooks on the PostgreSQL pod that call `pg_backup_start` and `pg_backup_stop`, so the daily EBS snapshot of the data volume is also usable as a base backup.

**Copy, encrypt, expire**

8. Replicate the backup bucket to a second region; copy EBS snapshots with Data Lifecycle Manager. Everything is encrypted with a dedicated KMS key. Retention: 35 days for database and volume data, 90 days for the objects backups.

**Prove it works**

9. A monthly CronJob restores the last objects backup into a scratch namespace and the database to one hour ago, compares row counts and a checksum per table with production, writes the result to a table and posts it. A failed test pages the owner.
10. Write four runbooks (one table, point in time, whole namespace, region rebuild), each with the exact commands, and run the region rebuild once a year as a game day.

## Architecture diagram

Rendering diagram…

## Deep dives

### Crash-consistent against application-consistent

An EBS snapshot copies the blocks of a volume at one instant. If the database is writing, the snapshot looks like a machine that lost power: pages half-written, the WAL ahead of the data files. PostgreSQL recovers from exactly this on start, so a crash-consistent snapshot of a single volume usually works, but "usually" is not a policy, and it fails outright when data and WAL sit on different volumes snapshotted at different moments. Application-consistent means the application was told first. For PostgreSQL that is `pg_backup_start()` before the snapshot and `pg_backup_stop()` after, which forces a checkpoint and records the WAL position the restore must replay from. Velero's `pre.hook.backup.velero.io/command` and `post.hook.backup.velero.io/command` annotations run those calls inside the pod around the snapshot. Kafka has no such call; its segments are append-only files and brokers rebuild from replicas, so a crash-consistent snapshot per broker plus the replication factor of 3 is accepted. For a plain filesystem, `fsfreeze --freeze` in the pre hook flushes pending I/O.

### Point-in-time recovery

A dump is a photo of one moment. Base backup plus WAL archive is a video: restore the base, then replay WAL until `recovery_target_time`, and you land on any second between the end of the base backup and the last archived segment. This is what turns "we lost 6 hours" into "we lost 1 minute". The settings on the primary are `wal_level = replica`, `archive_mode = on` and an `archive_command` that uploads `%p` to S3 as `%f` and returns zero only on success; PostgreSQL deletes a segment only after that zero. On restore, `restore_command` fetches segments back, `recovery_target_time` sets the stop point, and the file `recovery.signal` in the data directory tells the server to recover. The trap: the target must be after the base backup finished, so keep at least two base backups and never delete WAL that a kept base backup needs. RDS and Aurora do the same thing for you, with transaction logs shipped continuously and retention up to 35 days, which is the strongest argument for moving the database out of the cluster.

### A backup nobody restored is not a backup

The SRE book's chapter on data integrity says it plainly: nobody wants backups, people want restores. Every failure in this story was a restore failure: the dump existed but was old, on one laptop, and had never been loaded anywhere. The monthly test is the design's most important piece. It restores into a scratch namespace with `--namespace-mappings`, so a mistake in the test cannot touch production, and it compares something concrete: `count(*)` per table against production at the same timestamp, and a checksum of the orders table for the last day. It records the time taken against the RTO, and a dashboard shows the age of the last successful test with an alert at 35 days. A test that only checks "the pod started" proves nothing.

### What Velero does and does not capture

Velero reads objects through the Kubernetes API and writes them as JSON to S3; on restore it recreates them in order (namespaces, then CRDs, then the rest). It captures Deployments, Services, ConfigMaps, Secrets, PVCs and custom resources. It does not capture the data inside a volume unless asked: with CSI it creates a VolumeSnapshot through the EBS CSI driver, and by default only the snapshot reference goes to S3, not the blocks, so the backup is only as safe as the EBS snapshot in that region. `--snapshot-move-data` copies the blocks through the node agent into S3 and then deletes the CSI snapshot. It also does not capture what lives outside the cluster: the RDS instance, bucket contents, IAM roles, DNS records. Those need Terraform for the definitions and S3 replication for the content. And Velero cannot make a database consistent on its own; the hooks do that.

## Evaluation

**SLIs.** Age of the last successful backup per class (alert when it passes 2 x the schedule); age of the newest archived WAL segment (alert at 5 minutes); replication lag of the DR bucket (alert at 1 hour); last restore test result and its duration against RTO; storage cost per class per month.

**Tests.** Monthly automated restore to a scratch namespace with row-count and checksum comparison. Quarterly: delete a non-production namespace on purpose and restore it from Velero, timed. Yearly game day: rebuild the stateful tier in the second region from the replicated bucket, with the primary region's credentials revoked for the exercise.

**Security checks.** Backup bucket has Object Lock, versioning and a bucket policy that denies `s3:DeleteObject` outside the lifecycle rule; the KMS key policy is reviewed quarterly; the break-glass annotation role appears in audit logs with a page every time it is used; backups contain Secrets, so the Velero bucket is as restricted as the cluster itself.

**Cost review.** Monthly: snapshot count and age (orphaned snapshots from failed backups are the usual leak), S3 size per prefix, cross-region transfer.

**What a strong answer adds.** The candidate separates crash-consistent and application-consistent, knows base backup plus WAL beats a dump, puts the restore test and the delete guard at the centre, and says which state should not be in the cluster at all.

## Bottlenecks & mitigations

* The weekly base backup at 100 MB per second runs for over an hour; run it from the replica and throttle with `--max-rate` so the replica keeps up with the primary.
* WAL archiving from one primary is serial: if S3 uploads stall, segments pile up on the volume and can fill it; alert on `pg_stat_archiver` failures and keep 20 percent free space.
* The restore test downloads 400 GB every month; use a VPC gateway endpoint for S3 so it is free of NAT charges.
* Velero backs up all namespaces in one run; thousands of objects per namespace make a run slow, so split schedules per namespace group.
* One Kafka broker snapshot at a time keeps the cluster available but makes the backup window 3 times longer.

## Failure modes

* **Namespace deleted again.** Mitigation: `Retain` reclaim policy so volumes survive, admission policy that denies the delete, Velero objects backup every 6 hours for the rest.
* **Backups deleted by the same credential that writes them.** A ransomware-style wipe. Mitigation: Object Lock in compliance mode, replication to a bucket in a separate account, Velero role without `s3:DeleteObject` beyond its own expiry.
* **WAL archiving silently failing.** The base backup is fine but the RPO is days. Mitigation: alert on `pg_stat_archiver.last_failed_time` and on newest archived segment age.
* **Restore works in the test but production needs a different version.** Mitigation: the scratch restore uses the same image digest as production, pinned in the backup metadata.
* **Snapshot taken while PostgreSQL has data and WAL on different volumes.** Inconsistent restore that fails to start. Mitigation: hooks around the snapshot, or keep both on one volume, or rely on WAL archiving rather than snapshots for the database.
* **Cross-region copy never tested.** The KMS key is regional and the DR bucket cannot be decrypted. Mitigation: multi-region KMS key or re-encryption on replication, tested in the yearly game day.
* **Velero restore recreates a Service with the old LoadBalancer status.** Traffic goes nowhere. Mitigation: restore into a scratch namespace first, and know that Velero restores status for only some resource types.
* **Retention expires the base backup a kept WAL chain needs.** Point-in-time recovery breaks for the oldest window. Mitigation: lifecycle rules that keep base backups 7 days longer than WAL.

## Follow-up questions interviewers ask

* The database grows to 4 TB. Which parts of the design stop working and what replaces them?
* How would you restore a single deleted row without restoring the whole 400 GB database?
* Kafka consumers must not reprocess 6 hours of events after a restore. How do offsets and the restored topics line up?
* Move PostgreSQL to Aurora. What in this design disappears, and what new thing do you have to back up?
* How do you back up Secrets without the backup bucket becoming the easiest place to steal them?
* The second region must take over in 30 minutes. What changes between "backup" and "disaster recovery" here?

## Lessons that cover this

* [#16Kubernetes networking and storageKubernetes](/devops/learn/kubernetes-networking-storage)
* [#24Scaling and resilience - caching, queues, rate limiting, DDoS, DROperate](/devops/learn/scaling-and-resilience)

## Further reading

* [Velero documentationGuidevelero.io](https://velero.io/docs/)
* [PostgreSQL documentation: continuous archiving and point-in-time recoveryGuidepostgresql.org](https://www.postgresql.org/docs/current/continuous-archiving.html)
* [Google SRE Book: Chapter 26 - Data Integrity: What You Read Is What You WrotePapersre.google](https://sre.google/sre-book/data-integrity/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousRate limiting, bot and DDoS protection at the edge](/devops/problems/edge-rate-limiting-ddos)[NextZero-downtime database schema migration and cutover](/devops/problems/zero-downtime-db-migration)

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
