# High load average and a process eating memory on a Linux host — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/high-load-memory-leak-linux

[DevOps problems](/devops#problems)

OPSTroubleshooting#25Medium

# High load average and a process eating memory on a Linux host

linuxperformancememory-leakload-averagenodejstroubleshootingReported at Infosys, Capgemini, Accenture

## Problem statement

It is 14:30 on a Monday. The API latency alert fires: p95 went from 120 ms to 4 s over the last hour on `api-2`, a 4-vCPU, 16 GB EC2 host that runs a Node API under PM2 in cluster mode behind Nginx. SSH takes 20 seconds to give you a prompt. `uptime` prints `load average: 24.10, 19.85, 11.02`, `free -m` shows 15,400 MB used and 3,900 MB of 4,096 MB swap in use, and the request queue in Nginx is growing. Find what the load is made of, get latency back under 200 ms, and make sure the host cannot slide into this state again unnoticed.

## Requirements

### Functional

* Say what a load average of 24 on 4 vCPUs means and whether it is CPU, IO wait or both, from `vmstat` and `top`, not from the number alone.
* Find the process or processes responsible, by RSS and by CPU, and say whether they are computing, waiting on IO, or swapping.
* Separate the candidate causes with evidence: a memory leak over days, the OOM killer, swap thrashing, too many worker processes, a fork storm.
* Restore latency now without losing in-flight requests where possible, then fix the leak properly.
* Add alerts on memory trend and limits that stop a leak before it reaches swap.

### Non-functional

* Time to a confident diagnosis under 15 minutes; latency back under 200 ms p95 within 20 minutes of the page.
* Blast radius: one of 3 API hosts behind the load balancer, so about one third of requests are slow, not failed, until the host is drained or fixed.
* The restart must drop fewer than 1 percent of in-flight requests (graceful reload, not kill).
* Memory per worker capped so that 4 workers plus Nginx and the OS fit in 16 GB with 2 GB spare; an alert fires when RSS trend predicts the cap within 24 hours.

## Back-of-the-envelope estimates

**Impact.** Load 24 on 4 vCPUs means 6 runnable or disk-waiting tasks per CPU on average over the last minute: the host is 6 times oversubscribed. The 15-minute average of 11 shows it has been bad for a while and rising. With 3 hosts behind the load balancer and this one answering in 4 s instead of 120 ms, about one third of users wait 30 times longer, and the load balancer's health check (3 s timeout) is about to mark the host unhealthy, which would shift all traffic to 2 hosts at 150 percent of their normal load. Memory: 4 PM2 workers at about 3.5 GB RSS each is 14 GB, leaving 2 GB for Nginx, the OS and page cache on a 16 GB host, so the kernel swaps. The RSS graph in CloudWatch shows each worker growing about 50 MB an hour since the Friday deploy, 66 hours ago: 66 x 50 = 3,300 MB of growth on a 400 MB base per worker, 4 workers, so 4 x 3,700 = 14,800 MB, which with Nginx and the OS is more than 16 GB holds, and that is why swap is at 95 percent today.

## API

```
# 1. Load, and what it is made of. r = runnable, b = blocked on IO, wa = IO wait, si/so = swap in/out per second.
uptime
vmstat 1 5
# procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
#  r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
#  6 18 3993600 118000  2100 310000 18400 21200 19200 21800 9100 15000 11  9  2 78  0
# b=18 and wa=78 with si/so in the tens of thousands of KiB/s: the load is swap IO, not CPU.

# 2. Which disk is saturated, and is it the swap device?
iostat -xz 1 3
# nvme0n1  r/s 3800  w/s 4100  rkB/s 19200  wkB/s 21800  %util 99.8   (root disk holds the swap file)
swapon --show

# 3. Who holds the memory? Sort by RSS; then by CPU.
ps -eo pid,ppid,rss,%mem,%cpu,stat,etime,cmd --sort=-rss | head -n 8
#   PID  PPID     RSS %MEM %CPU STAT   ELAPSED CMD
#  2210  2201 3690000 22.5  9.1 D   2-18:11:02 node /srv/api/server.js
#  2211  2201 3655000 22.3  8.7 D   2-18:11:02 node /srv/api/server.js
#  2212  2201 3602000 22.0  9.4 D   2-18:11:02 node /srv/api/server.js
#  2213  2201 3581000 21.8  8.9 D   2-18:11:02 node /srv/api/server.js
#   912     1   48000  0.3  1.1 S   9-02:40:12 nginx: worker process
ps -eo pid,%cpu,cmd --sort=-%cpu | head -n 5
# STAT D = uninterruptible sleep (waiting on disk): these are swapping, not computing.

# 4. Has the OOM killer already acted? Is this a fork storm or zombies?
dmesg -T | grep -iE "out of memory|oom-kill|killed process" | tail
ps -eo stat | sort | uniq -c            # many Z = zombies; thousands of lines = fork storm
ps -eo ppid --no-headers | sort | uniq -c | sort -rn | head -n 3   # a parent with hundreds of children

# 5. How did it get here? The trend is in the metrics, not on the box.
# CloudWatch: mem_used_percent and procstat rss for the api process, 7 days.
# Prometheus (node exporter): per-host memory trend
#   1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
#   predict_linear(node_memory_MemAvailable_bytes[6h], 24*3600) < 0
# Straight line up since the Friday deploy, flat before it: a leak introduced by that release.

# 6. Fix now: reload workers one at a time under PM2 (graceful), with a memory cap so it cannot recur today.
pm2 reload api --update-env
pm2 restart api --max-memory-restart 2G      # PM2 restarts a worker that exceeds 2 GB
vmstat 1 5                                   # wa and si/so fall within a minute; load follows over 15 minutes
swapoff -a && swapon -a                      # optional, only after RSS is low: forces swapped pages back into RAM

# 7. Find the leak properly on one worker (staging or a drained host), not during the incident.
pm2 restart api --node-args="--heapsnapshot-signal=SIGUSR2 --max-old-space-size=2048"
kill -USR2 "$WORKER_PID"                     # writes a Heap.<date>.<pid>.heapsnapshot file in the cwd; take two, 30 minutes apart
# Load both in Chrome DevTools Memory tab, Comparison view: the retained objects that grew are the leak.
```

## Data model

```
Load average interpretation on a 4-vCPU host (1-minute value)
  load   per CPU   meaning
  2      0.5       half idle, fine
  4      1.0       every CPU busy, no queue: the limit for a CPU-bound host
  8      2.0       one task waiting per running task: latency doubles if CPU-bound
  24     6.0       five tasks waiting per running task, or many tasks in state D on disk: this incident
  Load counts runnable (R) and uninterruptible (D) tasks, so IO wait raises it as much as CPU does.

vmstat columns that decide the cause
  r      runnable tasks           high r with us+sy near 100: CPU-bound
  b      blocked on IO            high b with wa high: IO-bound
  si/so  swap in/out KiB/s        non-zero and sustained: swapping; thousands: thrashing
  us sy  user, system CPU         sy high with low us: kernel work, often reclaim or fork storms
  wa     waiting for IO           78 here
  st     stolen by the hypervisor non-zero on a noisy or burstable instance

ps fields
  rss      resident set, KB      what the process really holds in RAM
  stat     R running, S sleeping, D uninterruptible (disk), Z zombie, T stopped
  etime    elapsed since start   matches the deploy time = growing since the deploy
  ppid     parent                a parent with hundreds of children = fork storm

dmesg lines
  Out of memory: Killed process 2210 (node) total-vm:..., anon-rss:..., file-rss:...   the kernel already chose
  (absent here: swap gave the kernel room, so it thrashed instead of killing)

Memory on the host
  MemTotal 16 GB; used 15.4 GB = 4 workers x ~3.6 GB + nginx 0.2 GB + OS and cache ~0.8 GB; another 3.9 GB sits in swap

PM2 and Node settings that bound a worker
  pm2 start server.js -i 4 --max-memory-restart 2G      restart a worker above 2 GB RSS
  --max-old-space-size=2048                              V8 heap cap in MiB; above it, V8 aborts with a heap out of memory error instead of swapping
  --heapsnapshot-signal=SIGUSR2                          write a heap snapshot on demand
  systemd: MemoryMax=12G on the unit                     OOM-kill inside the unit, not the whole host

Alerts
  predict_linear(process_resident_memory_bytes[6h], 24*3600) > limit_bytes      leak trend
  node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes < 0.5               swapping started
  node_load1 / count(node_cpu_seconds_total{mode="idle"}) > 2 for 10m           load per CPU
```

## Diagnosis and fix

1. **Scope.** One of 3 hosts; the other two are at load 1.5. Mark `api-2` as draining in the load balancer (deregister with the 30-second connection drain) so users stop landing on it while you work.
2. **What is the load made of?** `vmstat 1 5` shows `r` 6, `b` 18, `wa` 78 percent, `si` and `so` around 20 MB/s, `us` 11. The CPUs are mostly waiting for disk, and the disk traffic is swap. `iostat -xz` shows the root NVMe at 99.8 percent utilised, and `swapon --show` says the swap file is on that disk. So the load is 4 CPUs waiting behind one disk doing swap IO: a memory problem wearing a load-average costume.
3. **Who holds the memory?** `ps --sort=-rss` shows 4 `node` workers at 3.6 GB each, all in state D, all started 2 days 18 hours ago, which is the Friday deploy. `dmesg` has no OOM kill: swap gave the kernel room to thrash instead of killing. No zombies, no fork storm.
4. **Why is it growing?** The CloudWatch RSS graph per worker is a straight line up from the deploy, about 50 MB an hour, flat for the week before. Linear growth that tracks time, not load spikes, is a leak per request. The release diff shows a new in-process cache keyed by user plus query string with no size bound and no TTL. Root cause.
5. **Fix now.** `pm2 reload api` restarts the workers one at a time, each finishing its in-flight requests first; RSS drops to 400 MB per worker, `so` goes to 0 within a minute, and the 1-minute load drops under 4 in a few minutes. Add `--max-memory-restart 2G` so a worker is recycled before it can reach swap again today. Re-register the host.
6. **Fix properly.** Revert the cache or give it a bound: an LRU with a maximum of 10,000 entries and a 5-minute TTL. Prove it with two heap snapshots 30 minutes apart on a staging worker: the comparison view shows the cache's Map entries growing. Set `--max-old-space-size=2048` so V8 fails fast with a heap error instead of swapping, and `MemoryMax=12G` on the systemd unit that runs PM2.
7. **Verify.** p95 back at 120 ms, load under 2, swap use under 100 MB after `swapoff -a && swapon -a`, RSS flat for 24 hours on the fixed build.
8. **Prevent.** Three alerts: RSS trend predicted to cross the cap within 24 hours, swap use above 50 percent, load per CPU above 2 for 10 minutes. Canary the next deploy on one host for 24 hours and compare its RSS slope with the others before promoting. Add a 30-minute memory soak test in CI.

## Architecture diagram

Rendering diagram…

## Deep dives

### Load average is a queue length, not a CPU percentage

Linux counts tasks that are runnable (state R) or in uninterruptible sleep (state D, usually waiting for disk) and averages that count over 1, 5 and 15 minutes. Divide by the number of CPUs to get the queue per CPU. Load 4 on 4 vCPUs is every CPU busy with nobody waiting; load 24 is 5 waiting per running task. But the number alone cannot tell you whether those tasks want CPU or disk. That is what `vmstat` is for: `r` versus `b`, and `us` plus `sy` versus `wa`. Here `wa` at 78 percent with `b` at 18 says the CPUs are idle, waiting for a disk, and `si`/`so` say the disk work is swap. A host can show load 24 with 2 percent user CPU, and that is exactly the swap-thrash signature.

### Why swap makes it worse than an OOM kill

Without swap, four workers growing past 16 GB would trigger the OOM killer, one worker would die with a clear `dmesg` line, PM2 would restart it, and latency would dip for a few seconds. With a 4 GB swap file on the root disk, the kernel instead pages out the least recently used pages, which in a leaking cache are the oldest entries, and then pages them back in when the cache is scanned. Every request now touches disk. Swap turned a sharp, self-healing failure into a slow, spreading one, and the load balancer health check timing out would have made it a full outage. The better design is a small swap or none, a hard cap per worker (`--max-memory-restart`, `--max-old-space-size`, `MemoryMax`), and an alert on the trend so the cap is never reached in production.

### Finding the leak instead of guessing

The incident evidence (linear RSS growth from the deploy, no correlation with load) points at a leak, and the release diff points at the cache, but the proof is a heap snapshot comparison. Start one worker with `--heapsnapshot-signal=SIGUSR2`, send the signal twice 30 minutes apart under normal traffic, and load both files in Chrome DevTools. The comparison view sorts constructors by size delta; an unbounded `Map` with tens of thousands of new entries, retained by the module scope, is the answer. For a process that is already dying, `--heapsnapshot-near-heap-limit=3` writes snapshots as V8 approaches the cap. The fix for an in-process cache is always a bound: a maximum entry count with LRU eviction and a TTL, or move the cache to Redis where memory is managed and shared across workers.

### CPU-bound and fork storms look different

If `us` plus `sy` is near 100 and `wa` is near 0, the load is real CPU work: `ps --sort=-%cpu` finds the process, and a Node worker at 100 percent of one core with a growing event loop lag is a hot path to profile, not a memory problem. A fork storm shows `sy` high, process count in the thousands and one parent with hundreds of children in `ps -o ppid`; the fix is to stop the parent and bound it with `TasksMax` in systemd. Zombies (state Z) hold no memory and no CPU, but a parent that never reaps them exhausts the PID table. Saying which signature you see, and which you have ruled out, is what the interviewer wants to hear.

## Evaluation

**Did you find it?** The root cause in one sentence: "the Friday release added an unbounded in-process cache, each Node worker leaks about 50 MB an hour, after 66 hours the 4 workers exceed RAM, the kernel swaps on the root disk and IO wait drives the load average to 24." The evidence chain is `vmstat` (wa 78, si/so high), `iostat` (root disk 99.8 percent with the swap file on it), `ps` (4 workers at 3.6 GB in state D since the deploy), no OOM in `dmesg`, the linear RSS trend in CloudWatch, and the release diff.

**Is it fixed?** After `pm2 reload`: `so` at 0 within a minute, 1-minute load under 4 within 5 minutes, p95 under 200 ms, host re-registered and healthy. After the code fix: RSS flat for 24 hours on the canary host, two heap snapshots with no growth in the cache constructor.

**Is it prevented?** A per-worker cap at three levels (PM2 restart at 2 GB, V8 heap at 2 GB, systemd `MemoryMax`); a trend alert that predicts the cap 24 hours out; a swap alert; a 24-hour canary with RSS slope comparison before a release is promoted; a soak test in CI.

**What a strong answer adds.** The load average table and the distinction between R and D tasks; that swap on the root disk makes the whole host slow, not only the leaking process; graceful `reload` versus `restart`; the heap snapshot comparison method; and why an LRU bound is the real fix and a bigger instance is not.

**What a weak answer does.** "Load is high so add CPUs", "restart the server", or "disable swap" with no diagnosis, and no plan to find the leak.

## Bottlenecks & mitigations

* SSH itself is slow on a thrashing host; keep a `tmux` session open and a `vmstat` running before it gets bad, or use SSM Session Manager.
* A 4 GB swap file on the root disk shares bandwidth with logs, the app and the OS, so one swapping process slows everything.
* Heap snapshots of a 3 GB process take minutes and can themselves push the host over the edge; take them on a drained host or in staging.
* PM2 cluster mode restarts workers one at a time, so the full reload takes 4 x (drain time); with `kill_timeout` at 5 seconds that is 20 seconds of reduced capacity.

## Failure modes

* **Reading load as CPU.** Adding vCPUs to a host that is waiting on swap changes nothing. Mitigation: `vmstat` before any conclusion.
* **Killing the workers instead of reloading.** In-flight requests fail. Mitigation: `pm2 reload`, one worker at a time, with a kill timeout.
* **Restart as the fix.** The leak returns in 66 hours. Mitigation: a memory cap today, the code fix this week, the trend alert forever.
* **Raising the instance size.** The leak fills 32 GB in about 6 days instead of 3. Mitigation: a bound on the cache, not on the host.
* **Swap on the root disk with no alert.** Thrashing takes the whole host down slowly. Mitigation: small or no swap, swap-use alert at 50 percent.
* **Health check marks the host unhealthy mid-investigation.** All traffic goes to 2 hosts. Mitigation: drain deliberately first so you control the timing.
* **Unbounded in-process caches.** Every per-request cache without a size and a TTL is a leak. Mitigation: a code review rule and an LRU library; shared caches go to Redis.

## Follow-up questions interviewers ask

* `vmstat` shows `us` 95, `wa` 0 and the same load. What do you do differently?
* `dmesg` shows the OOM killer picked PostgreSQL instead of the leaking Node worker. Why, and how do you steer it (`oom_score_adj`)?
* The same service runs on Kubernetes with a memory limit. What would you have seen instead, and is that better?
* Explain the difference between RSS, virtual size and the V8 heap, and which one each cap acts on.
* How would you prove the cache is the leak if you could not read the release diff?
* Design the alert so it pages a day before the host would swap, not after.

## Lessons that cover this

* [#2Linux for operatorsFoundations](/devops/learn/linux-for-operators)
* [#14Ansible and configuration managementCloud and IaC](/devops/learn/ansible-configuration-management)
* [#22Troubleshooting playbook - Linux, Docker, Kubernetes, network, pipelinesOperate](/devops/learn/troubleshooting-playbook)

## Further reading

* [Linux man pages online (man7.org)Guideman7.org](https://man7.org/linux/man-pages/)
* [PM2 documentation: Quick StartGuidepm2.keymetrics.io](https://pm2.keymetrics.io/docs/usage/quick-start/)
* [Prometheus documentationGuideprometheus.io](https://prometheus.io/docs/introduction/overview/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousDisk full on a production server at 3 am](/devops/problems/disk-full-production-server)[NextDeploy rolled out, users see errors, readiness probes flapping](/devops/problems/bad-deploy-readiness-probes)

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
