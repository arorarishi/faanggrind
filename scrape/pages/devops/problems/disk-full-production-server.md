# Disk full on a production server at 3 am — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/disk-full-production-server

[DevOps problems](/devops#problems)

OPSTroubleshooting#24Easy

# Disk full on a production server at 3 am

linuxtroubleshootingdisklogrotatesystemdnginxReported at Infosys, Wipro, TCS

## Problem statement

It is 03:04. CloudWatch pages: `disk_used_percent / = 100` on `web-1`, a single EC2 host that runs Nginx in front of a Node app managed by systemd. The app log shows `Error: ENOSPC: no space left on device, write` and Nginx answers 500 to every request because the app cannot write its session file. `df -h /` says 80 GB used of 80 GB, but `du -sh /var/log` says 1.2 GB and nothing else looks large. Find the space, free it without losing data or making the night worse, and make sure the disk never fills silently again.

## Requirements

### Functional

* Find what holds the space when `df` and `du` disagree, with the exact command that proves it.
* Rule out the other candidates with one command each: journald, Docker images and logs, core dumps, inodes, tmp files, a runaway application log.
* Free the space without `rm` on a file a process still holds, and without a blind reboot.
* Restore Nginx 200s and the app's writes within 15 minutes of the page.
* Leave the host with log rotation that works, a size-bounded journal, and an alert that fires before 100 percent.

### Non-functional

* Time from page to space freed under 15 minutes.
* Blast radius: 1 host, all of its users (this is the only web server, about 2,000 sessions overnight).
* Disk alerts at 80 percent and 90 percent with a 24-hour forecast, so the next time there is a day of warning, not 0 minutes.
* Log rotation keeps 7 days or 2 GB, whichever is smaller; the journal is capped at 1 GB.
* Nothing deleted that cannot be regenerated: logs are shipped before rotation removes them.

## Back-of-the-envelope estimates

**Impact.** One host serves the site, so a full disk is a full outage: at 3 am about 2,000 sessions an hour, so every 15 minutes of outage costs about 500 failed sessions. The numbers that point to the cause: `df` shows 80 GB used, `du` of the whole filesystem finds 40 GB, so 40 GB is used by something `du` cannot see, which is almost always an open file that has been unlinked. The app's `app.log` was rotated by logrotate at 00:00 the previous night, 27 hours ago, and had grown at about 1.5 GB an hour since (a debug flag left on in the last deploy): 27 x 1.5 is about 40 GB, so the deleted file alone explains the gap. Truncating it returns the 40 GB in under a second.

## API

```
# 1. Confirm the symptom and which filesystem. Also check inodes: a full inode table gives the same ENOSPC.
df -hT /
df -i /
# /dev/nvme0n1p1 ext4 80G 80G 0 100% /      (inodes: 9% used, so not inode exhaustion)

# 2. What does du see? If df and du disagree by tens of GB, a deleted file is still open.
sudo du -xsh / 2>/dev/null
sudo du -xh --max-depth=2 / 2>/dev/null | sort -rh | head -n 15
# 40G total: /var/lib/docker 0 (no Docker here), /var/log 1.2G, /home 0.9G, /usr 6G ...

# 3. Find open files that have been unlinked (link count 0). This is the proof.
sudo lsof +L1 | sort -k7 -n -r | head
# COMMAND  PID   USER FD   TYPE DEVICE  SIZE/OFF   NLINK NODE    NAME
# node     1842  app  12w  REG  259,1  42949672960  0   524301  /var/log/app/app.log.1 (deleted)

# 4. Same thing without lsof: the fd symlink says (deleted) and ls -l shows the size.
sudo ls -l /proc/1842/fd | grep deleted
# l-wx------ 1 app app 64 Nov  3 03:06 12 -> /var/log/app/app.log.1 (deleted)

# 5. Free the space safely: truncate through the open descriptor. Never rm; the file is already unlinked.
sudo truncate -s 0 /proc/1842/fd/12
df -h /
# 40G used, 40G free

# 6. Or make the app reopen its logs, if it supports a signal (Nginx: USR1 reopens; many apps use HUP or USR2).
sudo kill -USR1 "$(cat /run/nginx.pid)"

# 7. The other candidates, one command each.
sudo journalctl --disk-usage                      # journald: "Archived and active journals take up 3.9G"
sudo du -sh /var/lib/docker 2>/dev/null           # Docker images, layers and json-file logs, if Docker is present
docker system df 2>/dev/null                      # and what docker thinks it owns
sudo ls -lh /var/lib/systemd/coredump /var/crash 2>/dev/null   # core dumps
sudo find / -xdev -type f -size +1G 2>/dev/null   # any single file over 1 GB
sudo du -sh /tmp /var/tmp                         # tmp files that never got cleaned

# 8. Verify the service and the cause.
sudo systemctl status app nginx
curl -s -o /dev/null -w "%{http_code}\n" https://127.0.0.1/health --insecure
sudo journalctl -u app --since "-10m" | grep -c ENOSPC   # should be 0 now
cat /etc/logrotate.d/app                            # the rotate config that produced the orphan
```

## Data model

```
What the numbers mean
  df -h  Used 80G Avail 0           blocks the filesystem has handed out (includes unlinked open files)
  du -xsh /  40G                    bytes reachable through a path (cannot see unlinked files)
  difference 40G                    held by open descriptors to deleted files, or by a mount hiding a directory
  df -i  IUse% 9%                   inode table; 100% here means millions of small files, df -h can still show space

lsof +L1 columns that decide it
  FD       12w       descriptor 12, open for write
  SIZE/OFF 42949672960   bytes the file holds right now
  NLINK    0         no directory entry points at it: deleted
  NAME     ... (deleted)

The logrotate config that caused it (/etc/logrotate.d/app)
  /var/log/app/app.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
  }                                 # no copytruncate and no postrotate signal: the app keeps writing to the renamed inode

The fix (choose one)
  copytruncate                      logrotate copies then truncates in place; the app never notices; a few lines may be lost in the copy window
  postrotate  kill -USR2 $(cat /run/app.pid)  endscript   app reopens its log on the signal (needs app support)
  or let systemd own stdout: StandardOutput=journal and set journald limits

journald limits (/etc/systemd/journald.conf)
  SystemMaxUse=1G                   default is 10% of the filesystem capped at 4G
  SystemKeepFree=2G                 default is 15% of the filesystem capped at 4G
  SystemMaxFileSize=128M            default is one eighth of SystemMaxUse capped at 128M

Alert
  disk_used_percent{path="/"} > 80 for 10m          warning
  predict_linear(node_filesystem_avail_bytes[6h], 24*3600) < 0   page: full within a day
```

## Diagnosis and fix

1. **Scope and safety.** One host, full outage. Say in the channel that you are on it and that you will not reboot. Run `df -hT /` and `df -i /`: blocks are at 100 percent, inodes at 9 percent, so this is bytes, not inode exhaustion.
2. **Compare df with du.** `du -xsh /` finds 40 GB on an 80 GB filesystem. A 40 GB gap means space that no path reaches. Two things do that: a file that was deleted while a process still has it open, or a directory with data under it that a later mount hides. The second is rare and `findmnt` rules it out in one look.
3. **Prove it.** `lsof +L1` lists open files with link count under 1. One line: `node` PID 1842, descriptor 12 open for write, 42,949,672,960 bytes, `/var/log/app/app.log.1 (deleted)`. `ls -l /proc/1842/fd` shows the same `(deleted)` target. That is the root cause: at the previous midnight logrotate renamed `app.log` to `app.log.1`, compressed it to `app.log.1.gz` and removed the `.1` file, but the app never reopened its log, so it kept writing to the unlinked inode until the disk filled.
4. **Free the space without losing the process.** `truncate -s 0 /proc/1842/fd/12`. The descriptor stays valid, the app keeps running, and `df` shows 40 GB free at once. Do not `rm` anything: the file has no name, so there is nothing to remove, and killing the app would free the space but also drop in-flight requests and lose the evidence.
5. **Restore and check the others.** `curl` the health endpoint, 200. `journalctl -u app` shows no new `ENOSPC`. Then spend 2 minutes on the other candidates so the morning has a full picture: journal at 3.9 GB (worth capping), no Docker, no core dumps, nothing over 1 GB, `/tmp` small.
6. **Fix the cause properly.** Two parts. The debug flag that made the log grow at 1.5 GB an hour is reverted in Git and deployed in the morning. The rotation is fixed now: add `copytruncate` to `/etc/logrotate.d/app` (or a `postrotate` that sends the app its reopen signal), add `maxsize 500M` so size, not only the daily schedule, triggers a rotation, and run `logrotate -d /etc/logrotate.d/app` to dry-run it.
7. **Bound the rest.** Set `SystemMaxUse=1G` in `journald.conf` and `journalctl --vacuum-size=1G` now. Ship logs to CloudWatch Logs or Loki with the agent so rotation can delete freely.
8. **Prevent.** Alerts at 80 and 90 percent plus a `predict_linear` forecast, so a day of growth pages before the disk is full. A per-service log size check in the deploy pipeline. Write the 3-line incident note: cause, fix, follow-ups.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why df and du disagree

`du` walks directories and adds up the files it can name. `df` asks the filesystem how many blocks are allocated. When a process has a file open and someone deletes the name, the kernel keeps the inode and its blocks alive until the last descriptor closes. The blocks still count for `df`, but `du` cannot reach them because no path exists. Log rotation without a reopen is the classic way to make such a file: `mv app.log app.log.1` does not change the inode the process is writing to, and when the rotated file is later compressed and removed, the process writes into a ghost. The fix is through `/proc/PID/fd/N`, which is a live handle to that inode: `truncate -s 0` on it frees the blocks instantly while the process keeps its descriptor. The one other cause of a gap is a mount over a non-empty directory; `findmnt` shows it.

### What not to do at 3 am

Do not reboot: the space comes back because the process dies, and you have no idea why, so it will happen again. Do not `rm` files you do not understand: a `.1` log that is still open gives back nothing, and deleting `/var/lib/apt/lists` or a database WAL to "make room" causes a second incident. Do not kill the app before truncating: you lose in-flight requests and the evidence in `lsof`. The rule is: measure, prove, free the specific thing, then verify.

### Rotation that the app survives

Logrotate has three ways to rotate a file a process holds open. `copytruncate` copies the file and then truncates the original in place, so the process keeps its descriptor; the cost is that lines written between the copy and the truncate are lost, and the copy of a 40 GB file takes a while. A `postrotate` script that sends the process its reopen signal (`USR1` for Nginx, whatever the app documents) is clean but needs app support. Or let the app write to stdout and have systemd capture it in the journal, which rotates itself within `SystemMaxUse`. Whichever you pick, add `maxsize` so a burst rotates before the daily timer, and ship the logs off the host so that deleting old files is safe.

### Inodes, journald and Docker are the other usual suspects

`df -i` at 100 percent with free bytes means millions of tiny files, usually a session or cache directory that nothing cleans; `find /var -xdev -type d -size +1M` finds the fat directory. journald defaults to 10 percent of the filesystem capped at 4 GB, which is fine, but a host with a small root disk and verbose services should set `SystemMaxUse` lower. On a Docker host, `docker system df` shows images, build cache and volumes, and container logs under `/var/lib/docker/containers/*/*-json.log` grow without limit unless `max-size` is set in the logging driver options.

## Evaluation

**Did you find it?** The root cause is one sentence: "the app's log was rotated at midnight but the process kept writing to the unlinked inode, 40 GB that `du` cannot see, because the logrotate config has neither `copytruncate` nor a reopen signal." The evidence chain is `df` versus `du`, the `lsof +L1` line with NLINK 0 and the size, the `(deleted)` fd target, and the rotate config.

**Is it fixed?** `df -h /` shows 40 GB free a second after the truncate, the app logs no `ENOSPC` for 10 minutes, Nginx returns 200, and the journal and logrotate changes are in place and dry-run clean.

**Is it prevented?** Four items: `copytruncate` or a reopen signal plus `maxsize` in the rotate config; `SystemMaxUse=1G` for the journal; logs shipped off the host; alerts at 80 and 90 percent with a 24-hour `predict_linear` forecast.

**What a strong answer adds.** The exact mechanism of an unlinked open file, `/proc/PID/fd` as the way in, why `truncate` and not `rm`, the inode check as a separate failure, the trade-off of `copytruncate` (a few lost lines) against a reopen signal, and the "what not to do" list said out loud.

**What a weak answer does.** Reboots, deletes random files in `/var/log`, or runs `rm` on the `.1` file and is surprised that `df` does not change.

## Bottlenecks & mitigations

* `du` over a full 80 GB disk takes minutes; `lsof +L1` answers in seconds, so run it first when the gap is large.
* `copytruncate` on a very large file is slow and can itself fill the disk during the copy; `maxsize` keeps files small enough.
* A single host with no second disk has nowhere to move data; the only levers are truncate and delete.
* Log shipping needs network and an agent; without it, rotation must keep files longer and the disk fills sooner.

## Failure modes

* **Rebooting to free space.** It works once and hides the cause. Mitigation: `lsof +L1` first; reboot only after the cause is known.
* **Deleting a rotated file that is still open.** `df` does not move. Mitigation: truncate through `/proc/PID/fd/N` or send the reopen signal.
* **Inode exhaustion read as a byte problem.** `df -h` shows free space, writes still fail. Mitigation: `df -i` in the first minute.
* **Journal unbounded on a small disk.** 4 GB default cap is half of a 10 GB root. Mitigation: `SystemMaxUse` set per host size.
* **Docker json-file logs without limits.** One chatty container fills the host. Mitigation: `max-size` and `max-file` in the daemon logging options.
* **Alert only at 100 percent.** Zero minutes of warning. Mitigation: 80 and 90 percent thresholds plus a forecast alert.
* **Debug logging left on in production.** 1.5 GB an hour. Mitigation: log level from config, reviewed in the deploy diff, and a size alert per log file.

## Follow-up questions interviewers ask

* `df -h` shows 30 percent used but every write fails with ENOSPC. What is going on and how do you prove it?
* The process holding the deleted file is a database, not an app log. Does the truncate trick still apply?
* The host runs the app in Docker. Where does the space go and what are the three commands you run?
* How would you set up the alert so you get a day of warning rather than a page at 100 percent?
* Why is `copytruncate` lossy, and when would you choose a reopen signal instead?
* A junior engineer proposes a cron that deletes everything in `/var/log` older than 1 day. What is wrong with that and what would you do instead?

## Lessons that cover this

* [#2Linux for operatorsFoundations](/devops/learn/linux-for-operators)
* [#3Bash scripting and the terminal toolkitFoundations](/devops/learn/bash-and-terminal-toolkit)

## Further reading

* [Linux man pages online (man7.org)Guideman7.org](https://man7.org/linux/man-pages/)
* [NGINX documentationGuidenginx.org](https://nginx.org/en/docs/)
* [systemd System and Service ManagerGuidefreedesktop.org](https://www.freedesktop.org/wiki/Software/systemd/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[Previous502 from the ingress while the service works inside the cluster](/devops/problems/ingress-502-service-unreachable)[NextHigh load average and a process eating memory on a Linux host](/devops/problems/high-load-memory-leak-linux)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [Diagnosis and fix](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Evaluation](#evaluation)
10. [Bottlenecks](#bottlenecks)
11. [Failure modes](#failures)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
