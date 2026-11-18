# Bash: analyse an Nginx access log — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/bash-log-analyzer

[DevOps problems](/devops#problems)

CODEImplement it#33Easy

# Bash: analyse an Nginx access log

bashawknginxlogstext processingReported at Infosys, Wipro, Capgemini

## Problem statement

You are given an Nginx access log in the default combined format, 2 GB for one day. In a bash script, using only standard Unix tools (awk, sort, uniq, grep, cut), report: total requests, requests per status class (2xx, 3xx, 4xx, 5xx), the top 10 client IPs by request count, the top 10 paths returning 5xx, the 95th percentile response size, and the busiest minute. The script must be safe to run on production logs and fast enough to finish in under a minute on a laptop.

## Requirements

### Functional

* Accept the log path as the first argument and print a usage line and exit 2 when it is missing.
* Print total requests and a count and percentage per status class.
* Print the top 10 IPs by request count and the top 10 paths that returned 5xx.
* Print the busiest minute (as it appears in the log timestamp) and its request count.
* Print the 95th percentile of the response size in bytes.

### Non-functional

* Stream the file: 0 lines held in memory except what sort needs; no reading the whole file into a variable.
* Each section is one pass with awk or one pipeline; at most 6 passes over the file in total.
* Finish 2 GB (about 10 million lines) in under 60 seconds on a laptop.
* Exit non-zero with a clear message on a missing, empty or unreadable file; `set -euo pipefail` at the top.
* Works on GNU and BSD userlands: no GNU-only flags such as `sort -h` or `grep -P`.

## API

```
Usage: ./access_report.sh <access.log>

Output sections, in this order:
  1. Total requests
  2. Status classes:   class  count  percent
  3. Top 10 IPs:       count  ip
  4. Top 10 5xx paths: count  path
  5. Busiest minute:   dd/Mon/yyyy:HH:MM  count
  6. p95 bytes

Exit codes: 0 ok, 2 usage, 1 file missing or empty
```

## Data model

```
Nginx combined log format, one request per line:

192.168.4.21 - - [03/Nov/2026:10:41:07 +0530] "GET /api/orders?id=42 HTTP/1.1" 200 5123 "https://shop.example/cart" "Mozilla/5.0 ..."
|            | | |                           |                                 |   |    |                            |
$1 remote_addr    $4 [time (strip the [)   $6 method $7 path $8 proto     $9 status  $10 bytes   $11 referer   $12+ user agent

Fields split on whitespace with awk. The request line is quoted, so $6 begins with a quote
and $7 is the path. Status is $9 and bytes is $10 (a dash when nothing was sent).
Minute key = substr($4, 2, 17)  -> 03/Nov/2026:10:41
```

## Approach

1. Validate input: one argument, file exists, is readable and non-empty; otherwise print usage to stderr and exit 2 or 1.
2. Total and status classes in one awk pass: take the first character of `$9`, count into an array, print with percentages at END.
3. Top IPs: `awk '{print $1}' | sort | uniq -c | sort -rn | head -10`. The sort is the expensive step; `LC_ALL=C` makes it several times faster because it compares bytes, not locale-aware characters.
4. Top 5xx paths: filter in awk (`$9 ~ /^5/`), print `$7` with the query string removed (`split($7, a, "?")`), then the same sort and uniq pipeline.
5. Busiest minute: awk extracts `substr($4, 2, 17)`, counts per key, and at END keeps the maximum; no sort needed.
6. p95 bytes: awk prints `$10` when it is numeric, `sort -n`, then pick the line at index `ceil(0.95 * n)` with awk reading the sorted stream and the count passed in.
7. Wrap the sections in functions, give each a header, and make the script create a small sample log when run with `--demo` so it can be tested without a real file.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why awk and not a loop

A `while read line` loop in bash runs the shell's interpreter once per line, with a fork for every `cut` or `grep` you call inside it; on 10 million lines that is hours. awk reads the file once in C, splits fields for you, and keeps counts in associative arrays, so a full pass is a few seconds. The rule interviewers want to hear: bash orchestrates, awk and sort do the work. The one place bash loops are fine is over the handful of result lines at the end.

### sort is the bottleneck, so help it

`sort | uniq -c | sort -rn` sorts the whole column once and the counts once more. Two things change its speed by a large factor. `LC_ALL=C` switches to byte comparison, which is often 3 to 10 times faster than a UTF-8 locale. `sort -S 50%` (GNU) lets it use memory instead of temp files; leave it out for portability but mention it. For the top-N question there is also a pure-awk answer that never sorts: count into an array, then at END loop to find the top 10, which is O(n) instead of O(n log n). Show both; the sorted pipeline is what most people write, the awk-only version is what shows you understand cost.

### Percentiles need all the values, or an approximation

A true p95 needs the sorted list of all 10 million sizes, which is why the script sorts numerically and indexes into the stream at position `ceil(0.95 * n)`. Reading the count from the first pass avoids a second `wc -l`. For a live system you would not do this on raw logs at all: a histogram metric in Prometheus gives p95 from a few buckets with constant memory. Saying "for one-off analysis sort; for monitoring use histogram buckets" is the complete answer.

### Safety on production logs

The script only reads. It never writes next to the log, never uses `sed -i`, and never follows a path from an untrusted variable without quoting. `set -euo pipefail` makes a failing stage in a pipeline fail the script, which matters because `awk ... | sort | head` would otherwise hide an unreadable file behind head's success. One exception to know: `head` closing the pipe early can make `sort` receive SIGPIPE, which `pipefail` reports as a failure; the script handles that by sorting into a variable only for the top-N sections, or by tolerating exit 141. Keep the log on the machine: copying 2 GB over the network to analyse it on a laptop is slower than running the script in place.

## Evaluation

**Correctness tests.** Run with `--demo`, which writes a 2,000-line sample log with known counts (for example exactly 120 5xx lines, one IP that appears 300 times, and a minute with 300 requests), and assert each section matches. Check that a line with `-` for bytes is skipped in the percentile but counted in totals. Check a path with a query string collapses to its base path in the 5xx table.

**Edge cases.** Missing argument exits 2; missing file exits 1; empty file prints "0 requests" and exits 1; a log with no 5xx prints an empty table, not an error; IPv6 clients work because `$1` is still the first field.

**Performance.** Time the script on a 1 million line file; the sort sections dominate, and `LC_ALL=C` should show a visible difference. State the complexity: O(n) for the awk passes, O(n log n) for the sorts.

**What a strong answer adds.** Field numbers from memory for the combined format; the `LC_ALL=C` trick; the awk-only top-N; knowing that p95 from logs is a one-off and histograms are the production answer; and `--previous`-style thinking: run the report on the rotated file, not the live one, when exact day boundaries matter.

## Bottlenecks & mitigations

* Two full sorts for each top-N section; on 10 million lines this is where the minute goes.
* Locale-aware comparison in sort when LC\_ALL is not set.
* Disk read speed on the log host, which is shared with Nginx itself; run with `nice` and `ionice` when the box is busy.
* Temp space for sort on a nearly full disk, which is exactly the situation during an incident.

## Failure modes

* **Wrong field numbers.** A custom log format shifts every column and the report is silently wrong. Mitigation: print one parsed line at the start as a sanity check.
* **Query strings in paths.** `/api/orders?id=1` and `?id=2` look like different paths. Mitigation: split on `?` before counting.
* **Dash in the bytes column.** `sort -n` puts `-` first and the percentile is off by the number of such lines. Mitigation: filter numeric values in awk.
* **SIGPIPE from head under pipefail.** The script exits 141 after printing the right answer. Mitigation: let sort finish into a variable, or handle exit 141 for that pipeline.
* **Reading the live file during rotation.** Counts straddle two files. Mitigation: analyse the rotated file or pass both.
* **Running on a laptop after scp of 2 GB.** Slower than running in place. Mitigation: run on the host with nice and ionice.

## Reference solution

Bash · runs and prints its own checks

```
#!/usr/bin/env bash
# access_report.sh: one-day Nginx access log report with standard Unix tools.
# Usage: ./access_report.sh <access.log>   or   ./access_report.sh --demo
set -euo pipefail
export LC_ALL=C   # byte-wise sort and awk: several times faster than a UTF-8 locale

usage() { echo "usage: $0 <access.log> | --demo" >&2; exit 2; }

make_demo_log() {
  # 2,000 lines with known counts so the report can be checked:
  #   IP 10.0.0.9 appears 300 times and so does minute 10:41; 120 lines are 5xx
  #   (all on /api/pay, with query strings); bytes are 100..1999 plus 20 dashes.
  awk 'BEGIN {
    srand(7)
    for (i = 1; i <= 2000; i++) {
      ip = (i <= 300) ? "10.0.0.9" : sprintf("192.168.%d.%d", (i % 20) + 1, (i % 200) + 1)
      min = (i <= 300) ? "10:41" : sprintf("10:%02d", 42 + (i % 15))
      if (i > 300 && i <= 420) { st = 500 + (i % 4); path = "/api/pay?order=" i }
      else if (i % 10 == 0) { st = 404; path = "/missing/" (i % 7) }
      else { st = 200; path = "/api/orders?id=" (i % 50) }
      bytes = (i % 100 == 0) ? "-" : 100 + (i % 1900)
      printf "%s - - [03/Nov/2026:%s:%02d +0530] \"GET %s HTTP/1.1\" %d %s \"-\" \"demo\"\n",
        ip, min, i % 60, path, st, bytes
    }
  }'
}

status_classes() {
  awk '{ c[substr($9, 1, 1)]++; n++ }
       END {
         printf "total requests: %d\n", n
         for (k = 2; k <= 5; k++)
           printf "  %dxx  %7d  %5.1f%%\n", k, c[k], (n ? 100 * c[k] / n : 0)
       }' "$1"
}

top_ips() {
  # Pure awk top-N: one pass, no sort of 10 million lines.
  awk '{ c[$1]++ }
       END {
         for (r = 1; r <= 10; r++) {
           best = ""; bc = -1
           for (ip in c) if (c[ip] > bc) { bc = c[ip]; best = ip }
           if (bc < 0) break
           printf "  %7d  %s\n", bc, best; delete c[best]
         }
       }' "$1"
}

top_5xx_paths() {
  # The classic pipeline. head may close the pipe early; tolerate sort's exit 141.
  { awk '$9 ~ /^5/ { split($7, a, "?"); print a[1] }' "$1" | sort | uniq -c | sort -rn | head -10; } \
    || [ $? -eq 141 ]
}

busiest_minute() {
  awk '{ m = substr($4, 2, 17); c[m]++ }
       END { for (k in c) if (c[k] > best) { best = c[k]; bk = k }
             printf "  %s  %d requests\n", bk, best }' "$1"
}

p95_bytes() {
  local n
  n=$(awk '$10 ~ /^[0-9]+$/ { n++ } END { print n + 0 }' "$1")
  if [ "$n" -eq 0 ]; then echo "  no numeric byte values"; return; fi
  # index = ceil(0.95 * n); awk reads the sorted stream and prints that line.
  awk '$10 ~ /^[0-9]+$/ { print $10 }' "$1" | sort -n \
    | awk -v n="$n" 'BEGIN { idx = int(0.95 * n); if (idx < 0.95 * n) idx++ }
                     NR == idx { printf "  p95 bytes: %d (of %d sized responses)\n", $1, n; exit }'
}

main() {
  [ $# -eq 1 ] || usage
  local log="$1"
  if [ "$log" = "--demo" ]; then
    log="$(mktemp)"; make_demo_log > "$log"
    echo "demo log written: $(wc -l < "$log") lines"
  fi
  [ -r "$log" ] || { echo "error: cannot read $log" >&2; exit 1; }
  [ -s "$log" ] || { echo "error: $log is empty (0 requests)" >&2; exit 1; }

  echo "== status classes";  status_classes "$log"
  echo "== top 10 IPs";      top_ips "$log"
  echo "== top 10 5xx paths"; top_5xx_paths "$log"
  echo "== busiest minute";  busiest_minute "$log"
  echo "== response size";   p95_bytes "$log"

  if [ "$1" = "--demo" ]; then
    # Self-checks against the known counts in the demo log.
    check() { local msg="$1"; shift; if "$@"; then echo "check ok: $msg"; else echo "check FAILED: $msg" >&2; exit 1; fi; }
    check "120 lines are 5xx"              [ "$(awk '$9 ~ /^5/' "$log" | wc -l)" -eq 120 ]
    check "10.0.0.9 appears 300 times"     [ "$(awk '$1 == "10.0.0.9"' "$log" | wc -l)" -eq 300 ]
    check "busiest minute is 10:41 with 300" grep -q "10:41  300 requests" <(busiest_minute "$log")
    check "query strings collapsed to /api/pay" grep -q "120 /api/pay" <(top_5xx_paths "$log")
    check "p95 of 1980 sizes is 1899"      grep -q "p95 bytes: 1899" <(p95_bytes "$log")
    rm -f "$log"
  fi
}

# No arguments: run the demo. Otherwise pass everything through so extra arguments hit usage.
if [ $# -eq 0 ]; then main --demo; else main "$@"; fi
```

## Follow-up questions interviewers ask

* The log is gzipped and rotated hourly into 24 files. Change the script to handle all of them in one run.
* Make the top-10 IPs section run in one pass without sort.
* The team wants this every hour in Grafana instead. What replaces the script, and what do you lose or gain?
* An IP sends 40 percent of all requests. What do you check before calling it an attack?
* Rewrite the status-class section in Python and compare memory use and speed with awk.
* How would you add the median and p99 latency if the log format included `$request_time`?

## Lessons that cover this

* [#3Bash scripting and the terminal toolkitFoundations](/devops/learn/bash-and-terminal-toolkit)

## Further reading

* [The Missing Semester of Your CS EducationGuidemissing.csail.mit.edu](https://missing.csail.mit.edu)
* [Linux man pages (man7.org)Guideman7.org](https://man7.org/linux/man-pages/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousDatabase connections exhausted after a deploy](/devops/problems/db-connection-pool-exhausted)[NextBash: safe deploy script with locking, rollback and traps](/devops/problems/bash-safe-deploy-script)

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
