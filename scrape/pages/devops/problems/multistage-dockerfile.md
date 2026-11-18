# Dockerfile: multi-stage build with a non-root user — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/multistage-dockerfile

[DevOps problems](/devops#problems)

CODEImplement it#36Easy

# Dockerfile: multi-stage build with a non-root user

dockerdockerfilemulti-stagenode.jssecurityimage sizeReported at Infosys, Wipro, TCS

## Problem statement

A TypeScript API (Express, compiled with `tsc` to `dist/`) ships today as a single-stage image built `FROM node:24` with `npm install` and `CMD npm start`: 1.2 GB, runs as root, and a Trivy scan lists 180 findings. Write a multi-stage Dockerfile that installs dependencies with a cached package manager, compiles in a build stage, and produces a production image on a slim pinned base with only production dependencies, a non-root user, a HEALTHCHECK, labels, and an entrypoint that forwards SIGTERM to Node so Kubernetes can stop it cleanly.

## Requirements

### Functional

* Three stages: `deps` (install all dependencies with the npm cache mounted), `build` (compile TypeScript, then prune to production dependencies), `runtime` (copy only `dist/`, `node_modules` and `package.json`).
* Pinned base tags, no `latest`; `COPY` not `ADD`; `COPY --chown` so the app files are owned by the runtime user.
* Run as the built-in `node` user (uid 1000); `WORKDIR /app`; `EXPOSE 3000`.
* `HEALTHCHECK` that calls `/healthz` with Node itself (the slim image has no curl) and exits 1 on anything but 200.
* Exec-form `ENTRYPOINT ["node", "dist/server.js"]` so Node is PID 1 and receives SIGTERM; explain when to add tini.
* OCI labels (`org.opencontainers.image.source`, `revision`, `created`) filled from build args, and a `.dockerignore` that keeps `node_modules`, `.git` and `.env` out of the context.

### Non-functional

* Final image under 300 MB (assumed: about 200 MB base plus 60 MB of production dependencies plus 2 MB of `dist/`).
* A code-only change rebuilds in under 60 s because the dependency layers are cached; a `package-lock.json` change re-runs `npm ci` with the cache mount in under 2 minutes.
* `trivy image --severity CRITICAL --exit-code 1` passes on the result; the slim base typically cuts findings by 5 to 10 times compared with the full image.
* `docker stop` finishes in under 10 s: Node receives SIGTERM, closes the listener, drains in-flight requests, exits 0.
* Reproducible: same lockfile and same base digest give the same `node_modules`; `npm ci`, never `npm install`, in the image.

## API

```
Build:
  docker build -t api:1.4.2 \
    --build-arg GIT_SHA=$(git rev-parse HEAD) \
    --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) .

Run and verify:
  docker run -d --name api -p 3000:3000 api:1.4.2
  docker inspect --format '{{.State.Health.Status}}' api     # starting -> healthy
  docker exec api id                                          # uid=1000(node) gid=1000(node)
  docker image inspect api:1.4.2 --format '{{.Size}}'         # bytes; expect well under 300 MB
  docker history api:1.4.2                                    # one line per layer with its size
  time docker stop api                                        # under 10 s means SIGTERM reached Node

Scan:
  trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 api:1.4.2

Stage targets (useful in CI):
  docker build --target build -t api:test .   # run unit tests from this stage
```

## Data model

```
Repository layout (the build context):
  package.json  package-lock.json  tsconfig.json
  src/server.ts  src/healthz.ts       -> compiled to dist/server.js, dist/healthz.js
  Dockerfile  .dockerignore

.dockerignore (what never enters the build context):
  node_modules      # 400 MB that would be sent to the daemon and then thrown away
  dist              # built inside the image, not copied from a laptop
  .git              # history and possibly credentials
  .env  .env.*      # secrets
  *.md  .github     # not needed at runtime
  coverage  .nyc_output

Stages and what each contains:
  deps     node:24-bookworm-slim + all node_modules (dev + prod)      about 600 MB, discarded
  build    deps + src + dist/, then npm prune --omit=dev               discarded
  runtime  node:24-bookworm-slim + dist/ + pruned node_modules          about 260 MB, shipped

Layer order in runtime (least to most frequently changed):
  FROM base -> ENV, WORKDIR, labels -> COPY node_modules -> COPY dist -> USER, HEALTHCHECK, ENTRYPOINT
```

## Approach

1. Declare `ARG NODE_VERSION=24` before the first `FROM`, the only place an `ARG` may come before `FROM`, so one line bumps every stage together.
2. `deps` stage: copy only `package.json` and `package-lock.json`, then `RUN --mount=type=cache,target=/root/.npm npm ci`. The cache mount keeps the npm download cache on the builder between builds, outside the image, so a lockfile change re-downloads only what changed. Copying the lockfile alone means source edits do not invalidate this layer.
3. `build` stage from `deps`: copy `tsconfig.json` and `src/`, run `npm run build` to produce `dist/`, then `npm prune --omit=dev` so `node_modules` shrinks to production packages. Dev tools (`typescript`, test runners) never reach the runtime stage.
4. `runtime` stage from `node:24-bookworm-slim`: set `NODE_ENV=production`, `WORKDIR /app`, and copy three things from `build` with `--chown=node:node`: `package.json`, `node_modules`, `dist`. Nothing else, so no compilers, no source, no `.git`.
5. Switch to `USER node`, the uid 1000 account the official image ships, so a container escape lands as an unprivileged user and a read-only root filesystem works.
6. `HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3` runs a one-line Node script that requests `/healthz` and exits 1 on non-200. `start-period` gives the app time to boot before failures count.
7. `ENTRYPOINT ["node", "dist/server.js"]` in exec form, so Node is PID 1 and `docker stop` delivers SIGTERM straight to it. The app handles SIGTERM by closing the server. `npm start` would receive the signal and not forward it.
8. Labels from build args record the source repository, git SHA and build time, which Trivy reports and an SBOM tool can read.

## Architecture diagram

Rendering diagram…

## Deep dives

### Layer order decides the cache hit rate

BuildKit rebuilds a layer when its instruction or any file it copies changed, and every layer after it. Copy the lockfile first and install, then copy source: a source edit keeps the install layer cached. Copy `src/` before `npm ci` and every commit pays a full install. The cache mount is a separate idea: `RUN --mount=type=cache,target=/root/.npm` gives npm a persistent download directory on the builder that is not part of any layer, so even a lockfile change downloads only the new packages. `sharing=locked` serialises parallel builds that share the mount; the default `shared` is fine for npm.

### Size before and after, assumed numbers

Single stage on `node:24-bookworm`: about 1 GB base plus 400 MB `node_modules` with dev dependencies plus source, roughly 1.2 GB. Multi-stage on `node:24-bookworm-slim`: about 200 MB base, 60 MB production `node_modules`, 2 MB `dist/`: about 260 MB, a 4 to 5 times reduction. Alpine (`node:24-alpine`) would be about 150 MB total but uses musl libc instead of glibc: packages with native add-ons (`bcrypt`, `sharp`, `prisma` engines) may need a rebuild or ship no musl binary, and musl's DNS resolver behaves differently under load. Choose slim Debian unless you have measured that alpine works for your dependency set. Measure your own numbers with `docker history` and `docker image inspect`; the ones above are assumptions for the arithmetic.

### Signals: why not npm start, and when to add tini

PID 1 in a container does not get default signal handlers from the kernel, so a process that ignores SIGTERM waits for the 10 s grace period and is killed. Shell form (`CMD node dist/server.js`) makes `/bin/sh -c` PID 1 and sh does not forward signals; `npm start` has the same problem. Exec form with Node as PID 1 works as long as the app calls `server.close()` on SIGTERM. Add tini (`ENTRYPOINT ["tini", "--", "node", "dist/server.js"]`, or `docker run --init`) when the app spawns child processes that could become zombies, because Node does not reap orphans.

### The same idea for Go: distroless and a static binary

```
FROM golang:1.27-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/server ./cmd/server

FROM gcr.io/distroless/static-debian13:nonroot
COPY --from=build /out/server /server
USER nonroot
EXPOSE 8080
ENTRYPOINT ["/server"]
```

`CGO_ENABLED=0` makes the binary static, so the runtime image needs no libc: `static-debian13` ships only CA certificates, tzdata and a `nonroot` user (uid 65532). Image size is the binary, about 10 to 15 MB. No shell exists, so `HEALTHCHECK` with curl is impossible; expose `/healthz` and let the Kubernetes probe call it, or compile a `-healthcheck` flag into the binary. Scan both images with `trivy image --severity HIGH,CRITICAL --exit-code 1 <image>`; the distroless result is usually empty.

## Evaluation

**Tests.** Build with the stage target `build` and run `npm test` inside it; build the full image and check `docker image inspect --format '{{.Size}}'` is under 300 MB; `docker run` then poll `docker inspect --format '{{.State.Health.Status}}'` until `healthy` within 40 s (10 s start period plus one 30 s interval); `docker exec api id` prints uid 1000; `time docker stop api` is under 10 s and the container exit code is 0; `trivy image --severity CRITICAL --exit-code 1` returns 0.

**Edge cases.** A dependency with a native add-on fails on alpine but works on slim: the reason the base is Debian. `npm ci` fails when `package-lock.json` is missing or out of sync with `package.json`, which is the correct behaviour in CI. The health check must use `127.0.0.1`, not the service name, because it runs inside the container's network namespace. A read-only root filesystem (`securityContext.readOnlyRootFilesystem: true`) works because the app writes nothing under `/app`; if it needs a temp dir, mount an `emptyDir` at `/tmp`.

**What a strong answer adds.** Pins the base by digest (`node:24-bookworm-slim@sha256:...`) and lets Renovate or Dependabot bump it; adds `--platform=$BUILDPLATFORM` and `TARGETARCH` for arm64 Graviton nodes; moves the health check out of the Dockerfile for Kubernetes (the kubelet probe replaces it) and keeps it for Compose; knows `npm ci --omit=dev` in a separate stage is an alternative to `npm prune`; and shows the distroless Node variant (`gcr.io/distroless/nodejs24-debian13:nonroot`) as the next step down in size and attack surface.

## Bottlenecks & mitigations

* `npm ci` on a cold cache is the slowest step, minutes for a large tree; the cache mount and the lockfile-first copy are what make the second build fast.
* Sending a context that includes `node_modules` or `.git` adds hundreds of MB to every build; `.dockerignore` is the fix.
* `tsc` is single-threaded and CPU-bound; on a 2 vCPU CI runner it dominates the build stage.
* Image pull time on a new node scales with the compressed size of layers that changed; keeping `node_modules` in its own layer means a code-only release pulls about 2 MB.

## Failure modes

* **Runs as root.** A container escape or a writable mount gives root on the node. Mitigation: `USER node`, `--chown` on copies, and a Pod Security Standard that rejects root.
* **SIGTERM ignored.** Pods take the full 30 s grace period to stop and rolling updates crawl. Mitigation: exec-form `ENTRYPOINT` with Node as PID 1 and a `server.close()` handler; tini when children are spawned.
* **Dev dependencies in production.** Image is 3 times larger and the scanner reports test tooling CVEs. Mitigation: `npm prune --omit=dev` in the build stage, copy only the pruned tree.
* **Floating base tag.** `node:24` silently changes under you and a build that passed on Monday fails on Tuesday. Mitigation: pin at least the full tag, better the digest, and update on purpose.
* **Secrets baked into a layer.** An `.env` file copied in a stage stays in the history even if deleted later. Mitigation: `.dockerignore`, and `RUN --mount=type=secret` for build-time tokens.
* **Health check without a start period.** The container is marked unhealthy during a 15 s boot and restarted in a loop. Mitigation: `--start-period` longer than the boot time.
* **Alpine surprise.** A native module segfaults or DNS lookups fail under load on musl. Mitigation: slim Debian by default; alpine only after testing the full dependency set.

## Reference solution

Dockerfile · pinned base, multi-stage, non-root

```
# syntax=docker/dockerfile:1
# Multi-stage build for a TypeScript API. Three stages: deps, build, runtime.

# One ARG before the first FROM: bump every stage's Node version in one place.
ARG NODE_VERSION=24

# ---------- deps: install every dependency once, with the npm cache mounted ----------
FROM node:${NODE_VERSION}-bookworm-slim AS deps
WORKDIR /app
# Copy only the manifests, so a source edit does not invalidate the install layer.
COPY package.json package-lock.json ./
# The cache mount lives on the builder, not in the image; npm ci stays reproducible.
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

# ---------- build: compile TypeScript, then drop dev dependencies ----------
FROM deps AS build
COPY tsconfig.json ./
COPY src ./src
# tsc writes dist/; the test runner can also run here with: docker build --target build
RUN npm run build \
    && npm prune --omit=dev

# ---------- runtime: slim base, production files only, non-root ----------
FROM node:${NODE_VERSION}-bookworm-slim AS runtime
ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown
# OCI labels: where it came from, which commit, when. Scanners and SBOM tools read these.
LABEL org.opencontainers.image.source="https://github.com/example/api" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.title="api"
ENV NODE_ENV=production \
    PORT=3000
WORKDIR /app
# --chown so the node user owns the files; nothing from the build toolchain comes along.
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/dist ./dist
# The official image ships a "node" user with uid 1000. Never run as root.
USER node
EXPOSE 3000
# No curl in the slim image, so the check is a Node one-liner. Exit 1 = unhealthy.
# start-period lets the app boot before failures count; 3 failures in a row = unhealthy.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["node", "-e", "require('http').get({host: '127.0.0.1', port: 3000, path: '/healthz'}, r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"]
# Exec form: node is PID 1 and receives SIGTERM directly. npm start would swallow it.
# If the app spawns child processes, prefix with tini: ["tini", "--", "node", "dist/server.js"].
ENTRYPOINT ["node", "dist/server.js"]
```

## Follow-up questions interviewers ask

* The team moves to Kubernetes. Which lines of this Dockerfile become redundant, and which Pod fields replace them?
* Show how to build for both amd64 and arm64 in one `docker buildx build` and push a manifest list.
* Add a stage that runs `npm audit` or Trivy against the build stage so CI fails before the image is pushed.
* The app needs a private npm registry token at build time. Show the `--mount=type=secret` form and explain why a build arg is wrong.
* Convert the Node image to `gcr.io/distroless/nodejs24-debian13`. What do you lose and how do you debug it in production?
* How would you prove, with `docker history`, that no secret and no source file is in any layer of the final image?

## Lessons that cover this

* [#8Containers and DockerBuild and ship](/devops/learn/containers-and-docker)
* [#23Security and DevSecOps - secrets, least privilege, supply chain, policy as codeOperate](/devops/learn/security-and-devsecops)

## Further reading

* [Dockerfile referenceGuidedocs.docker.com](https://docs.docker.com/reference/dockerfile/)
* [Docker build best practicesGuidedocs.docker.com](https://docs.docker.com/build/building/best-practices/)
* [Trivy documentationGuidetrivy.dev](https://trivy.dev/docs/latest/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousPython: concurrent health checker with retries and backoff](/devops/problems/python-health-checker)[NextGitHub Actions: build, test, cache, push an image and deploy](/devops/problems/github-actions-build-push-deploy)

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
