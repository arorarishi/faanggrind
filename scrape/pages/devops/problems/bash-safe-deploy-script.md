# Bash: safe deploy script with locking, rollback and traps — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/bash-safe-deploy-script

[DevOps problems](/devops#problems)

CODEImplement it#34Medium

# Bash: safe deploy script with locking, rollback and traps

bashdeploymentsymlinklockingrollbacklinuxReported at Infosys, TCS

## Problem statement

A small team runs an API on three EC2 virtual machines with no Kubernetes. Each release is a tarball in S3 with a sha256 file next to it. Today the deploy is a person typing `scp` and `mv` by hand, and last month two engineers deployed at the same time and left a box half-updated. Write `deploy.sh <version> <env>` in bash that downloads and verifies the release, switches an atomic `current` symlink, health-checks the service with retries, rolls back on failure, refuses to run concurrently, cleans up on any exit, logs with timestamps and keeps only the last 5 releases.

## Requirements

### Functional

* Parse `<version> <prod|staging> [--dry-run]`; reject a bad version string or environment with exit 2 and a usage line.
* Keep every release in `releases/<version>/` and run the service from a `current` symlink that is switched atomically.
* Download the tarball and its `.sha256` (faked locally with a copy), verify with `sha256sum -c`, refuse on mismatch with exit 5.
* Health-check after the switch with 3 attempts; on failure point `current` back at the previous release and exit 4.
* Hold a lock so a second deploy started during the first exits 3 without touching anything; a stale lock from a dead process must not block forever.
* Remove temp files and the lock on every exit path (success, error, Ctrl-C) and prune releases older than the newest 5, never the current one.

### Non-functional

* The switch itself is one `rename(2)` call: readers see the old tree or the new one, never a missing `current`, at any instant.
* A failed deploy restores the previous release within 10 seconds of the last failed health attempt.
* Re-running the script with the version that is already current is a no-op that exits 0 in under 1 second.
* The self-test (no arguments) builds its own fixture in `mktemp -d`, runs 14 checks and finishes in under 5 seconds with no network, no sudo.
* `set -euo pipefail`, every variable quoted, `shellcheck` clean; no `rm -rf` on a path built from an unchecked argument.

## API

```
Usage: ./deploy.sh <version> <prod|staging> [--dry-run]
       ./deploy.sh                 # self-test in a temp directory, prints check lines

Environment overrides (defaults in brackets):
  APP_ROOT       [/srv/myapp]            releases/, current, shared/ live here
  ARTIFACT_DIR   [/var/artifacts/myapp]  stands in for "aws s3 cp"
  KEEP_RELEASES  [5]   HEALTH_RETRIES [3]   HEALTH_SLEEP [1]

Functions (one responsibility each):
  acquire_lock          mkdir-based lock, breaks a lock whose pid is dead
  fetch_artifact VER    copy tarball + .sha256 to a temp dir, sha256sum -c
  install_release VER   untar into releases/VER.partial, then mv to releases/VER
  switch_current VER    ln -sfn into current.new, mv -Tf current.new current
  health_check          3 attempts, reads current/health ("ok" = HTTP 200)
  prune_releases N      keep the newest N by version, never the current one
  cleanup               trap EXIT: rm temp dir and lock, keep the exit code

Exit codes: 0 ok or no-op, 1 unexpected error, 2 usage, 3 lock held,
            4 health check failed and rolled back, 5 artifact missing or bad checksum
```

## Data model

```
Artifact store (S3 in real life, a directory here):
  myapp-1.1.0.tar.gz            contents: app.sh, health, VERSION
  myapp-1.1.0.tar.gz.sha256     "<64 hex chars>  myapp-1.1.0.tar.gz" (sha256sum format)

Layout on the VM, APP_ROOT=/srv/myapp:
  .deploy.lock/pid              exists only while a deploy runs; holds the pid
  releases/1.0.0/               never modified after extraction
  releases/1.1.0/ENVIRONMENT    written at install: "prod" or "staging"
  current -> releases/1.1.0     relative symlink; systemd unit runs /srv/myapp/current/app.sh
  shared/                       logs and config that survive releases

Health contract: current/health contains "ok" when the service is healthy.
In production this is replaced by: curl -fsS --max-time 2 localhost:8080/healthz

Log line: 2026-11-03T10:41:07Z [INFO] current -> releases/1.1.0
```

## Approach

1. Parse arguments into `VERSION`, `ENV_NAME`, `DRY_RUN`. Check the version against `^[0-9]+\.[0-9]+\.[0-9]+$` so that nothing like `../..` can become part of a path later.
2. Install the traps before anything is created: `trap cleanup EXIT` and `trap 'on_error $LINENO $?' ERR`. From here on, every exit path (normal return, `exit N`, a `set -e` failure, SIGINT, SIGTERM) runs `cleanup`.
3. Take the lock with `mkdir "$APP_ROOT/.deploy.lock"`. `mkdir` is a single atomic system call that either creates the directory or fails because it exists, so two processes cannot both succeed. Write the pid inside. If the directory exists and its pid is dead (`kill -0` fails), remove it and try once more; otherwise exit 3.
4. Read the previous version with `readlink current`. If it equals the requested version, log "nothing to do" and exit 0: the script is idempotent.
5. Fetch: copy `myapp-VER.tar.gz` and its `.sha256` into `mktemp -d`, then `sha256sum -c --quiet`. A mismatch is exit 5 before any file under `releases/` is touched. With `--dry-run` stop here and report what would happen.
6. Install: extract into `releases/VER.partial`, write `ENVIRONMENT`, then `mv` the directory to `releases/VER`. A crash mid-extract leaves a `.partial` directory that the next run deletes; it never leaves a half-filled `releases/VER`.
7. Switch: `ln -sfn releases/VER current.new` then `mv -Tf current.new current`. The `mv` is `rename(2)`, which replaces the old link in one step.
8. Health-check up to `HEALTH_RETRIES` times with `HEALTH_SLEEP` between them. On success prune and exit 0. On failure switch `current` back to the previous version, re-run the health check so the log says whether the rollback worked, remove the bad release directory, exit 4.
9. Prune: list `releases/` sorted by version descending (`sort -rV`), skip the current one, delete everything after the first `KEEP_RELEASES - 1` others.
10. Run with no arguments: build a fake artifact store with versions 1.0.0 through 2.3.0 (1.2.0 unhealthy, 1.3.0 tampered), run the script as a child for each scenario, print `check ok:` lines and a pass/fail count.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why the symlink switch must be a rename

The obvious code is `rm current; ln -s releases/1.1.0 current`. Between those two commands there is a window, microseconds on an idle box and much longer under load, in which `current` does not exist: a request that arrives then fails, and a systemd restart in that window cannot find the binary. `ln -sfn releases/1.1.0 current` is not guaranteed to be atomic either: POSIX allows `ln -f` to unlink the old name and then create the new one, two system calls, and busybox and the BSD `ln` do exactly that (current GNU coreutils happens to create a temporary link and rename it, which `strace` shows, but a deploy script should not depend on which `ln` is installed). The correct pattern is: create the link under a temporary name, then `mv -Tf current.new current`. `mv` on one file system is a single `rename(2)` call, and POSIX requires that it replaces the old name atomically, so any lookup of `current` sees the old target or the new one, never nothing. `-T` tells GNU `mv` to treat the destination as a file; without it `mv` would move `current.new` inside the directory `current` points to. A relative target keeps the tree movable. One more detail: a process that already opened files from the old release keeps using them, because open descriptors follow inodes, not names. New code runs only after the service restarts, which is why the health check comes after the switch and the restart.

### Locking: mkdir versus flock, and the stale-lock problem

Two deploys at once leave `current` pointing at whichever finished last and an interleaved log. A lock must be one atomic test-and-set. `mkdir` is one on every POSIX file system, including NFS, which is why the script uses it. The alternative is `flock`: `exec 9>/var/lock/deploy.lock; flock -n 9 || exit 3`. The kernel holds that lock on the open descriptor and drops it when the process dies, so a crashed deploy never leaves a stale lock. Its cost: `flock` is a util-linux command, not POSIX, and advisory locks are unreliable on some network file systems. With `mkdir`, a process killed by SIGKILL (which cannot be trapped) leaves the directory behind, so the script stores the pid and checks `kill -0 "$pid"`: signal 0 delivers nothing but reports whether the process exists. Pids are reused after a reboot, so a production script would also compare the process start time, or require a human to delete the lock. Name both options and the trade-off.

### Traps, exit codes and what set -e really does

`set -e` exits on a failing simple command, but not inside `if` conditions, `&&` or `||` chains, or a function called from one. `set -u` turns an unset variable into an error, which catches a typo in `$APP_ROOT` before it becomes `rm -rf /releases`. `pipefail` makes a pipeline fail when any stage fails. The EXIT trap runs for a normal return, for `exit 5`, for a `set -e` failure and after SIGINT or SIGTERM, so cleanup belongs there. Two rules make it safe: read `$?` in the trap's first statement and `exit "$rc"` at its end, so the caller sees the real code; and only remove the lock when this process created it (`HAVE_LOCK=1`), otherwise a run that exited 3 would delete another deploy's lock on its way out. The ERR trap only logs `$LINENO`, which saves minutes at 2 a.m.

### Idempotency and dry runs

Deploy tools get run twice, by nervous people and by retrying automation. The script answers in three places: the version already current is a no-op; an existing release directory is reused; the `.partial` directory is removed before a retry. `--dry-run` goes as far as the checksum, the step most likely to fail for reasons unrelated to this box, then stops before writing under `releases/`. Until the prune step everything is reversible (the symlink) or additive (a new directory), and prune only removes releases that are neither current nor among the newest four others.

## Evaluation

**Tests.** Run `./deploy.sh` with no arguments. The self-test checks, in order: 1.0.0 deploys and `current` points at it; 1.1.0 deploys; a repeat of 1.1.0 exits 0 without changes; `--dry-run` of 2.0.0 leaves `current` and `releases/` untouched; 1.2.0, whose health file says `db connection refused`, is rolled back to 1.1.0 with exit 4 and its directory removed; a tampered 1.3.0 exits 5 and changes nothing; a lock held by a live `sleep` process makes the next deploy exit 3; the same lock with a dead pid is broken and the deploy proceeds; the lock directory is gone afterwards; missing arguments and `v2` exit 2; after 2.1.0, 2.2.0 and 2.3.0 exactly five releases remain and 1.0.0 was pruned; the app root contains only `current`, `releases` and `shared`. Fourteen checks, under 1 second.

**Edge cases.** First deploy on an empty box (no previous release: a health failure exits 4 with a clear message and no rollback target). Version strings with path characters are rejected before use. A `.partial` directory from a killed run is cleaned on the next attempt. `sort -rV` orders 2.10.0 after 2.9.0, which plain `sort` would not.

**What a strong answer adds.** Names `rename(2)` and `-T`; explains the difference between `mkdir` and `flock` locks and why a stale lock needs a pid check; reads `$?` first in the trap; separates "switch" from "restart" and knows open file descriptors keep the old binary alive; keeps the failed release for debugging in a real system; and says what changes for three VMs (run on one host at a time, stop at the first failure, or move to a rolling deploy with the load balancer draining each host).

## Bottlenecks & mitigations

* The health check sleeps between attempts, so a slow-starting service either fails the deploy or needs a longer `HEALTH_SLEEP`; a real script polls with a deadline rather than a fixed count.
* `tar -xzf` of a large release is the slow step and runs while the lock is held; extracting before taking the lock would shorten the critical section but complicates cleanup.
* One host at a time: for three VMs the script is called three times in sequence by an outer loop, so total deploy time grows linearly with fleet size.
* `sha256sum` reads the whole tarball once more after the copy; for a 2 GB artifact that is a few seconds of disk time per host.

## Failure modes

* **Two deploys overlap.** Each thinks it owns `current` and the box ends in a mixed state. Mitigation: the `mkdir` lock; the second run exits 3 without touching anything.
* **Lock left by a SIGKILLed run.** Every later deploy exits 3 forever. Mitigation: store the pid, break the lock when `kill -0` says the process is gone, and log that it happened.
* **Half-extracted release becomes current.** A crash mid-`tar` plus a later run that saw the directory and reused it. Mitigation: extract into `VER.partial` and `mv` only when complete.
* **Rollback target is also unhealthy.** The previous release depends on something that broke since. Mitigation: re-run the health check after rollback and log an explicit "page a human" line; exit non-zero either way.
* **Checksum file missing or stale.** The deploy would proceed on an unverified artifact. Mitigation: `sha256sum -c` on a missing file fails, and `set -e` plus the `||` guard turn that into exit 5.
* **Prune deletes the running release.** Happens when the prune list is sorted by mtime and a reused old directory looks fresh. Mitigation: skip the version `readlink current` reports, and sort by version, not mtime.
* **Trap masks the real exit code.** A command inside `cleanup` succeeds and the script exits 0 after a failed deploy. Mitigation: capture `$?` in the first line of the trap and `exit "$rc"` at its end.

## Reference solution

Bash · runs and prints its own checks

```
#!/usr/bin/env bash
# deploy.sh: safe release switcher for one VM-hosted service.
#
#   ./deploy.sh <version> <environment> [--dry-run]   real use
#   ./deploy.sh                                       self-test in a temp dir
#
# Layout under APP_ROOT:
#   releases/<version>/   one directory per release, never edited after extract
#   current -> releases/<version>   the symlink the service runs from
#   shared/               config and logs that live across releases
#
# Exit codes: 0 ok, 1 unexpected error, 2 usage, 3 lock held, 4 health check
# failed and rolled back, 5 artifact missing or checksum mismatch.
set -euo pipefail

# Settings. The self-test overrides the paths through the environment.
APP_ROOT="${APP_ROOT:-/srv/myapp}"
ARTIFACT_DIR="${ARTIFACT_DIR:-/var/artifacts/myapp}"  # stands in for S3 or a registry
KEEP_RELEASES="${KEEP_RELEASES:-5}"
HEALTH_RETRIES="${HEALTH_RETRIES:-3}"
HEALTH_SLEEP="${HEALTH_SLEEP:-1}"          # seconds between health attempts
LOCK_DIR="$APP_ROOT/.deploy.lock"

VERSION="" ENV_NAME="" DRY_RUN=0
TMP_DIR="" HAVE_LOCK=0 SELF_TEST_ROOT=""

log() { printf '%s [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2"; }
die() { log ERROR "$2"; exit "$1"; }
usage() { echo "usage: $0 <version> <prod|staging> [--dry-run]" >&2; exit 2; }

# ---- cleanup runs on every exit: normal, die, set -e failure, SIGINT, SIGTERM ----
cleanup() {
  local rc=$?
  [ -n "$TMP_DIR" ] && rm -rf "$TMP_DIR"
  if [ "$HAVE_LOCK" -eq 1 ]; then rm -rf "$LOCK_DIR"; log INFO "lock released"; fi
  [ "$rc" -ne 0 ] && log INFO "exit code $rc"
  exit "$rc"          # keep the original exit code, do not let the trap mask it
}
on_error() { log ERROR "failed at line $1 (exit $2)"; }

# ---- locking: mkdir is atomic on every POSIX file system, so it is a safe test-and-set ----
acquire_lock() {
  local attempt holder
  for attempt in 1 2; do
    if mkdir "$LOCK_DIR" 2>/dev/null; then
      echo "$$" > "$LOCK_DIR/pid"; HAVE_LOCK=1; log INFO "lock acquired (pid $$)"; return 0
    fi
    holder="$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "?")"
    if [ "$holder" != "?" ] && ! kill -0 "$holder" 2>/dev/null; then
      log WARN "stale lock from dead pid $holder, breaking it"   # crash without cleanup (kill -9)
      rm -rf "$LOCK_DIR"; continue
    fi
    die 3 "another deploy is running (pid $holder); refusing to overlap"
  done
}

# ---- fetch and verify: a copy stands in for aws s3 cp; sha256sum -c is the real check ----
fetch_artifact() {
  local v="$1" tar="myapp-$1.tar.gz"
  [ -r "$ARTIFACT_DIR/$tar" ] || die 5 "artifact $tar not found in $ARTIFACT_DIR"
  cp "$ARTIFACT_DIR/$tar" "$ARTIFACT_DIR/$tar.sha256" "$TMP_DIR/"
  ( cd "$TMP_DIR" && sha256sum -c --quiet "$tar.sha256" ) \
    || die 5 "checksum mismatch for $tar; refusing to deploy"
  log INFO "artifact $tar verified"
}

# ---- unpack into a temp name, then rename: a half-extracted release is never visible ----
install_release() {
  local v="$1" dest="$APP_ROOT/releases/$1"
  if [ -d "$dest" ]; then log INFO "release $v already unpacked, reusing it"; return 0; fi
  rm -rf "$dest.partial"; mkdir -p "$dest.partial"
  tar -xzf "$TMP_DIR/myapp-$v.tar.gz" -C "$dest.partial"
  echo "$ENV_NAME" > "$dest.partial/ENVIRONMENT"
  mv "$dest.partial" "$dest"
}

# ---- the atomic switch: build the new link beside the old one, then rename over it ----
switch_current() {
  local v="$1"
  ln -sfn "releases/$v" "$APP_ROOT/current.new"
  mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"   # rename(2): readers see old or new, never nothing
  log INFO "current -> releases/$v"
}

current_version() {
  local target
  target="$(readlink "$APP_ROOT/current" 2>/dev/null || true)"
  echo "${target##*/}"
}

# ---- health check: stands in for curl -fsS --max-time 2 localhost:8080/healthz ----
# The release ships a file named health; "ok" means the service answered 200.
health_check() {
  local attempt
  for attempt in $(seq 1 "$HEALTH_RETRIES"); do
    if [ "$(cat "$APP_ROOT/current/health" 2>/dev/null)" = "ok" ]; then
      log INFO "health check passed on attempt $attempt"; return 0
    fi
    log WARN "health check attempt $attempt/$HEALTH_RETRIES failed"
    sleep "$HEALTH_SLEEP"
  done
  return 1
}

# ---- keep the newest N releases by version number, never the one current points to ----
prune_releases() {
  local keep="$1" cur v n=0
  cur="$(current_version)"
  while IFS= read -r v; do
    [ "$v" = "$cur" ] && continue
    n=$((n + 1))
    if [ "$n" -gt "$((keep - 1))" ]; then rm -rf "$APP_ROOT/releases/$v"; log INFO "pruned old release $v"; fi
  done < <(ls -1 "$APP_ROOT/releases" | sort -rV)
}

deploy() {
  local prev
  mkdir -p "$APP_ROOT/releases" "$APP_ROOT/shared"
  acquire_lock
  TMP_DIR="$(mktemp -d)"
  prev="$(current_version)"
  log INFO "deploy $VERSION to $ENV_NAME (current: ${prev:-none}, dry-run: $DRY_RUN)"

  if [ "$prev" = "$VERSION" ]; then
    log INFO "version $VERSION is already current; nothing to do"; return 0   # idempotent
  fi
  fetch_artifact "$VERSION"
  if [ "$DRY_RUN" -eq 1 ]; then
    log INFO "dry-run: would unpack to releases/$VERSION, switch current, health-check, prune"; return 0
  fi
  install_release "$VERSION"
  switch_current "$VERSION"
  if health_check; then
    prune_releases "$KEEP_RELEASES"
    log INFO "deploy of $VERSION succeeded"; return 0
  fi
  if [ -z "$prev" ]; then die 4 "health check failed and there is no previous release to roll back to"; fi
  log ERROR "health check failed; rolling back to $prev"
  switch_current "$prev"
  health_check || log ERROR "previous release $prev is unhealthy too; page a human"
  rm -rf "$APP_ROOT/releases/$VERSION"     # a real system might keep it for forensics
  die 4 "rolled back to $prev"
}

parse_args() {
  local a
  for a in "$@"; do
    case "$a" in
      --dry-run) DRY_RUN=1 ;;
      -h|--help) usage ;;
      -*) echo "unknown flag: $a" >&2; usage ;;
      *) if [ -z "$VERSION" ]; then VERSION="$a"; elif [ -z "$ENV_NAME" ]; then ENV_NAME="$a"; else usage; fi ;;
    esac
  done
  [ -n "$VERSION" ] && [ -n "$ENV_NAME" ] || usage
  [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die 2 "version must look like 1.2.3"
  case "$ENV_NAME" in prod|staging) ;; *) die 2 "environment must be prod or staging" ;; esac
}

# ---- self-test: builds a fake artifact store and app root in a temp dir ----
self_test() {
  local art rc pass=0 fail=0
  SELF_TEST_ROOT="$(mktemp -d)"; art="$SELF_TEST_ROOT/artifacts"; mkdir -p "$art"
  export APP_ROOT="$SELF_TEST_ROOT/srv" ARTIFACT_DIR="$art" HEALTH_SLEEP=0 HEALTH_RETRIES=2
  trap 'rm -rf "$SELF_TEST_ROOT"' EXIT

  make_artifact() {   # $1 version, $2 health content, $3 "corrupt" to break the checksum
    local d; d="$(mktemp -d)"
    echo "echo myapp $1" > "$d/app.sh"; echo "$2" > "$d/health"; echo "$1" > "$d/VERSION"
    tar -czf "$art/myapp-$1.tar.gz" -C "$d" .
    ( cd "$art" && sha256sum "myapp-$1.tar.gz" > "myapp-$1.tar.gz.sha256" )
    [ "${3:-}" = "corrupt" ] && echo "tampered" >> "$art/myapp-$1.tar.gz"
    rm -rf "$d"
  }
  run() { rc=0; bash "$0" "$@" || rc=$?; }
  check() { if [ "$2" = "$3" ]; then echo "check ok: $1"; pass=$((pass + 1)); else echo "CHECK FAILED: $1 (got '$2', want '$3')"; fail=$((fail + 1)); fi; }

  make_artifact 1.0.0 ok; make_artifact 1.1.0 ok; make_artifact 1.2.0 "db connection refused"
  make_artifact 1.3.0 ok corrupt
  for v in 2.0.0 2.1.0 2.2.0 2.3.0; do make_artifact "$v" ok; done

  echo "== first deploy";        run 1.0.0 prod;  check "1.0.0 deployed, exit 0" "$rc/$(current_version)" "0/1.0.0"
  echo "== second deploy";       run 1.1.0 prod;  check "1.1.0 is current" "$rc/$(current_version)" "0/1.1.0"
  echo "== idempotent re-run";   run 1.1.0 prod;  check "same version again is a no-op" "$rc" "0"
  echo "== dry run";             run 2.0.0 prod --dry-run
  check "dry-run leaves current alone" "$rc/$(current_version)/$([ -d "$APP_ROOT/releases/2.0.0" ] && echo dir || echo nodir)" "0/1.1.0/nodir"
  echo "== bad release";         run 1.2.0 prod
  check "1.2.0 fails health, rolled back to 1.1.0, exit 4" "$rc/$(current_version)" "4/1.1.0"
  check "failed release directory removed" "$([ -d "$APP_ROOT/releases/1.2.0" ] && echo kept || echo gone)" "gone"
  echo "== tampered artifact";   run 1.3.0 prod;  check "checksum mismatch exits 5, current unchanged" "$rc/$(current_version)" "5/1.1.0"
  echo "== lock held by a live process"
  sleep 30 & local holder=$!
  mkdir -p "$APP_ROOT/.deploy.lock"; echo "$holder" > "$APP_ROOT/.deploy.lock/pid"
  run 2.0.0 prod;  check "second deploy refused with exit 3" "$rc/$(current_version)" "3/1.1.0"
  kill "$holder"; wait "$holder" 2>/dev/null || true
  echo "== stale lock from a dead pid"
  run 2.0.0 prod;  check "stale lock broken, deploy proceeds" "$rc/$(current_version)" "0/2.0.0"
  check "lock removed after exit" "$([ -d "$APP_ROOT/.deploy.lock" ] && echo held || echo free)" "free"
  echo "== usage errors"
  run 2.1.0;        check "missing environment exits 2" "$rc" "2"
  run v2 prod;      check "bad version string exits 2" "$rc" "2"
  echo "== keep last $KEEP_RELEASES"
  for v in 2.1.0 2.2.0 2.3.0; do run "$v" prod; done
  check "releases on disk" "$(ls -1 "$APP_ROOT/releases" | tr '\n' ' ')" "1.1.0 2.0.0 2.1.0 2.2.0 2.3.0 "
  check "no temp files left behind" "$(ls -1 "$APP_ROOT" | sort | tr '\n' ' ')" "current releases shared "

  echo "self-test: $pass passed, $fail failed"
  [ "$fail" -eq 0 ]
}

main() {
  if [ $# -eq 0 ]; then self_test; exit $?; fi
  trap cleanup EXIT
  trap 'on_error $LINENO $?' ERR
  parse_args "$@"
  deploy
}

main "$@"
```

## Follow-up questions interviewers ask

* The service is a long-running process under systemd. Where does `systemctl restart` go, and what happens to in-flight requests during the switch?
* Convert the single-host script into a rolling deploy over three hosts behind a load balancer. What is the stop condition and where does the lock live now?
* The health check passes but p99 latency doubles after the deploy. How would you add a metric-based check with a 5 minute bake time?
* Replace the mkdir lock with `flock`. What changes when the script is killed with `kill -9`?
* The tarball is 2 GB and the VM has 3 GB of free disk. Order the steps so the deploy never runs out of space, and say what you give up.
* How does this script map onto a Kubernetes Deployment: which lines become the rolling update strategy, the readiness probe, and `kubectl rollout undo`?

## Lessons that cover this

* [#2Linux for operatorsFoundations](/devops/learn/linux-for-operators)
* [#3Bash scripting and the terminal toolkitFoundations](/devops/learn/bash-and-terminal-toolkit)
* [#6Python and Go for automation and toolingFoundations](/devops/learn/python-and-go-for-devops)
* [#14Ansible and configuration managementCloud and IaC](/devops/learn/ansible-configuration-management)

## Further reading

* [Linux man pages online (man7.org)Guideman7.org](https://man7.org/linux/man-pages/)
* [The Missing Semester of Your CS EducationGuidemissing.csail.mit.edu](https://missing.csail.mit.edu)
* [Site Reliability Engineering (the SRE book)Papersre.google](https://sre.google/sre-book/table-of-contents/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousBash: analyse an Nginx access log](/devops/problems/bash-log-analyzer)[NextPython: concurrent health checker with retries and backoff](/devops/problems/python-health-checker)

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
