# GitHub Actions: build, test, cache, push an image and deploy — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/github-actions-build-push-deploy

[DevOps problems](/devops#problems)

CODEImplement it#37Medium

# GitHub Actions: build, test, cache, push an image and deploy

github actionsci/cdoidcecrtrivygitopsReported at Infosys, Capgemini

## Problem statement

A team of 8 ships a Node API to EKS in ap-south-1 through Argo CD, which syncs a separate GitOps repository. Today a `deploy.sh` on a laptop builds the image with long-lived AWS keys, tags it `latest` and runs `kubectl set image`. Write one GitHub Actions workflow that tests on a Node matrix with caching, builds once with Buildx and a registry layer cache, logs in to ECR through OIDC, pushes the image tagged with the git SHA, scans it with Trivy, deploys to staging by opening a PR in the GitOps repo with the image digest, and deploys to production only from a `v*` tag after required reviewers approve.

## Requirements

### Functional

* Triggers: push to `main`, pull requests to `main`, and tags matching `v*.*.*`; one concurrency group per ref that cancels superseded PR runs but never a tag run.
* `test` job on a matrix of Node 22 and 24 with the npm cache keyed on `package-lock.json`; `build` waits for it.
* `build` job: Buildx, ECR login through `aws-actions/configure-aws-credentials` with `role-to-assume`, registry cache with `mode=max`, image tagged with `github.sha`, digest exposed as a job output; no push on pull requests.
* `scan` job pulls the image by digest and runs Trivy with `severity: CRITICAL`, `ignore-unfixed: true`, `exit-code: 1`.
* `deploy-staging` on `main` edits the staging overlay in the GitOps repo to `image@sha256:...` and opens a PR; `deploy-prod` does the same for the prod overlay but only on tags and only after the `production` environment's reviewers approve.
* Top-level `permissions: contents: read`; only the jobs that talk to AWS add `id-token: write`; every action pinned to a full commit SHA with the version in a comment.

### Non-functional

* A code-only push to `main` reaches a staging PR in under 8 minutes: tests about 3, build about 2 with a warm registry cache, scan about 1.
* The dependency layers hit the registry cache on at least 90 percent of builds; a cold build is allowed to take up to 10 minutes.
* Zero long-lived cloud credentials in repository secrets; the OIDC session lasts at most 1 hour and is scoped to one role.
* The same digest that passed the scan and ran in staging is what production receives; the image is built exactly once per commit.
* A production deploy cannot start without 1 approval from the environment's required reviewers, and the approval is recorded in the deployment log.

## API

```
File: .github/workflows/ci-cd.yaml

Triggers -> jobs that run:
  pull_request (same repo)   test, build (no push)
  pull_request (fork)        test only
  push main                  test, build, scan, deploy-staging
  push tag v1.4.2            test, build, scan, deploy-prod (pauses for approval)

Job outputs:
  build.outputs.image    123456789012.dkr.ecr.ap-south-1.amazonaws.com/shop/api
  build.outputs.digest   sha256:3f0c...  (from docker/build-push-action outputs.digest)

Action inputs used (checked against each README on 2026-11-03):
  aws-actions/configure-aws-credentials  role-to-assume, aws-region, role-session-name
  aws-actions/amazon-ecr-login           outputs.registry
  docker/build-push-action               context, push, tags, labels, cache-from, cache-to,
                                         provenance; outputs.digest
  aquasecurity/trivy-action              scan-type, image-ref, format, severity,
                                         ignore-unfixed, exit-code
  actions/setup-node                     node-version, cache, cache-dependency-path
  peter-evans/create-pull-request        token, branch, commit-message, title, body

Repository settings the workflow relies on:
  Secret GITOPS_TOKEN        fine-grained PAT or GitHub App token for the gitops repo
  Environment staging        no protection rules
  Environment production     required reviewers (1 of up to 6), deployment rule: tags v*
  IAM role trust policy      token.actions.githubusercontent.com, sub = repo:org/api:ref:refs/heads/main
                             and repo:org/api:ref:refs/tags/v*
```

## Data model

```
Inputs the workflow reads:
  github.sha           40-char commit; the image tag
  github.ref           refs/heads/main | refs/pull/12/merge | refs/tags/v1.4.2
  github.ref_name      main | v1.4.2
  github.event_name    push | pull_request
  secrets.GITOPS_TOKEN scoped to the gitops repo only

ECR repository shop/api after one push to main:
  shop/api:<sha>         the image, also addressable as shop/api@sha256:<digest>
  shop/api:buildcache    BuildKit cache export (mode=max: every stage's layers)

GitOps repo layout Argo CD watches:
  envs/staging/api/deployment.yaml   image: <registry>/shop/api@sha256:<digest>
  envs/prod/api/deployment.yaml      same line, changed only from a tag run

Job graph:
  test (matrix 22, 24) -> build -> scan -> deploy-staging   (main)
                                        -> deploy-prod      (tags, environment gate)
```

## Approach

1. Put `permissions: contents: read` at the top so every job starts with a read-only `GITHUB_TOKEN`; `build` and `scan` add `id-token: write` because only they request an OIDC token.
2. Set `concurrency.group` to workflow plus ref. `cancel-in-progress` is an expression that is true for branches and PRs and false for tags, so a release never dies half way through a push.
3. `test` runs the matrix with `fail-fast: false` so a failure on Node 22 still shows the Node 24 result; `setup-node` with `cache: npm` restores `~/.npm` keyed on the lockfile hash.
4. `build` checks out with `persist-credentials: false`, exchanges the OIDC token for 1-hour AWS credentials, logs in to ECR, and starts a Buildx builder. `build-push-action` builds with `cache-from` and `cache-to` pointing at a `buildcache` tag in the same ECR repository, pushes `shop/api:<sha>` when the event is not a pull request, and writes the content digest to `steps.push.outputs.digest`, which the job re-exports.
5. `scan` logs in again (each job is a fresh runner) and runs Trivy on `image@digest`. `exit-code: 1` with `severity: CRITICAL` and `ignore-unfixed: true` fails the job on critical findings that have a fix, which is the rule most teams can enforce today.
6. `deploy-staging` runs only on `main`, checks out the GitOps repository with a token scoped to it, rewrites the `image:` line in the staging overlay to `image@sha256:...` with `sed`, and opens a PR with `peter-evans/create-pull-request`. Argo CD syncs after merge; the workflow never touches the cluster.
7. `deploy-prod` runs only on `v*` tags and declares `environment: production`. GitHub pauses the job until a required reviewer approves, then the same digest is written to the prod overlay and a PR is opened.
8. Every `uses:` is a full commit SHA with `# vX.Y.Z` after it, read from the action's release page, so a moved tag cannot change what runs.

## Architecture diagram

Rendering diagram…

## Deep dives

### OIDC instead of stored keys

A stored `AWS_ACCESS_KEY_ID` is valid until someone rotates it, readable by anyone with admin on the repository, and shows up in audit logs as a user, not a workflow. With OIDC, each job asks GitHub for a signed JSON Web Token that says which repository, ref and workflow is running, `configure-aws-credentials` sends it to `sts:AssumeRoleWithWebIdentity`, and AWS returns credentials that expire in 1 hour (`role-duration-seconds`, 900 to 43200). The IAM role's trust policy checks the token's `aud` (`sts.amazonaws.com` by default) and `sub`, so you can allow `repo:org/api:ref:refs/heads/main` and `ref:refs/tags/v*` and nothing else, which is why a fork PR cannot push even if the job ran. The workflow needs `id-token: write`, and that is the only permission beyond `contents: read` any job asks for. Secrets in this design: one, the GitOps token, and it is scoped to one repository.

### Build once, deploy by digest

A tag like `latest` or even `v1.4.2` can be re-pushed to point at a different image; a digest is the SHA-256 of the manifest and cannot. The build job exports `outputs.digest`, scan pulls that digest, staging pins that digest, and production pins the same one after approval. Nothing is rebuilt between environments, so "it passed in staging" means the same bytes. The GitOps repo holds `image@sha256:...` lines, which also makes `git log` a complete deployment history and `git revert` a rollback. The registry cache is the other half of "build once": `cache-to` with `mode=max` exports every stage's layers (not only the final stage, which is `min`) to a `buildcache` tag, and `cache-from` on the next build imports it, so a code-only change re-runs only the stages after `COPY src`. When the cache tag does not exist yet the import step fails but the build continues, so the first run is simply cold.

### pull\_request\_target and fork pull requests

`pull_request` from a fork runs with a read-only token and no secrets, which is safe. `pull_request_target` runs in the context of the base repository with secrets and write permission, and if it also checks out the PR's head, the fork author's code runs with your secrets: that is how repositories get their tokens stolen. This workflow uses plain `pull_request`, and the `build` job's `if:` additionally skips fork PRs so the OIDC step never runs for them. If you need to comment on fork PRs with a privileged token, use `workflow_run` after the untrusted workflow finishes, and never check out untrusted code in the privileged one.

### Environments as gates, and the caching strategy

An environment is a named target with its own secrets and protection rules: required reviewers (up to 6, one approval is enough, with an option to block self-review), a wait timer, and a rule restricting which branches or tags may deploy. Declaring `environment: production` on a job pauses it until the rules pass and records who approved. That is the whole production gate: no custom approval logic in YAML. Two caches do different jobs here: `setup-node`'s cache restores `~/.npm` on the test runner so `npm ci` is fast, and the registry cache stores image layers so the Dockerfile's `deps` stage is a hit. `type=gha` cache is the alternative for the second; it is simpler but limited in size per repository and evicted after 7 days of no use, so the ECR-hosted cache is the better fit for a repository that builds daily.

## Evaluation

**Tests.** Push a branch and open a PR: `test` runs twice, `build` runs without push, `scan` and the deploy jobs are skipped. Open the same PR from a fork: only `test` runs. Merge to `main`: a PR appears in the GitOps repo with an `image@sha256:` line, and the ECR repository has `shop/api:<sha>` and `shop/api:buildcache`. Push a second commit to `main` within a minute: the first run is cancelled. Push `v1.4.2`: `deploy-prod` shows "waiting for review" and proceeds only after approval; the digest in the prod PR equals the one in the run's build output. Plant a known-critical package in a test branch and confirm `scan` fails with exit 1.

**Edge cases.** First build with no `buildcache` tag: the cache import warns and the build proceeds cold. A tag pushed on a commit that already built from `main` builds again (different ref, different run); strong answers reuse the digest by looking it up with `aws ecr describe-images` instead. The `sed` edit fails silently if the `image:` line format changes; `git diff --exit-code` after the edit catches a no-op. `GITOPS_TOKEN` expiry breaks both deploy jobs at once; a GitHub App token avoids expiry.

**What a strong answer adds.** Pinning actions by SHA and explaining why; `persist-credentials: false`; reading the Buildx `mode=max` default; `provenance` and SBOM attestations with `cosign` signing of the digest; `timeout-minutes` on every job; and the honest statement that `deploy-prod` here opens a PR rather than merging it, so a second person reviews the diff that Argo CD will apply.

## Bottlenecks & mitigations

* The `test` matrix doubles runner minutes; at 8 engineers pushing 10 times a day that is about 160 test jobs daily, so cache hits matter more than the build.
* The registry cache import and export add 20 to 40 s of network time per build; worth it only when the cold build is minutes.
* Each job logs in to AWS and ECR again because runners are fresh; four jobs means four OIDC exchanges, each a few seconds.
* A single ECR repository in one region: cross-region clusters pull across regions and pay for transfer; replicate the repository or build per region.
* The GitOps PR step waits on a human merge, which is the longest step in the pipeline and the one the team controls least.

## Failure modes

* **Tag moved on an action.** A compromised `v4` tag runs attacker code with your OIDC token. Mitigation: pin by full SHA, bump with Dependabot, review the diff.
* **Fork PR gets secrets.** `pull_request_target` plus checkout of the head ref. Mitigation: use `pull_request`, skip fork PRs in privileged jobs, and keep `permissions` minimal.
* **Production deploys a different image than staging.** A rebuild on the tag produces a new digest. Mitigation: deploy by the digest from the build output, and prefer looking up the existing digest for the commit.
* **Cancelled release.** `cancel-in-progress: true` kills a tag run after the push but before the PR. Mitigation: the expression that disables cancellation for `refs/tags/`.
* **Trivy blocks every deploy.** A critical CVE with no fix in the base image stops all releases. Mitigation: `ignore-unfixed: true`, a `.trivyignore` with an expiry date, and a base image bump.
* **GitOps token with too much scope.** A classic PAT with `repo` on every repository. Mitigation: fine-grained PAT or GitHub App token limited to the gitops repository, contents and pull-requests write only.
* **OIDC trust policy too wide.** `sub` condition of `repo:org/*` lets any repository in the org assume the deploy role. Mitigation: list the exact repository and refs in the condition.
* **Cache poisoning.** A PR run writes layers into the shared `buildcache` tag. Mitigation: only push cache from `main` and tags; PRs read it but do not write.

## Reference solution

YAML · parsed and checked

```
---
# .github/workflows/ci-cd.yaml
# Build once, scan, push by digest, deploy the same digest to staging through a GitOps PR,
# and to production only from a tag after a human approves the environment.
#
# Every action is pinned to a full commit SHA with the release tag in a comment. The SHAs
# below were read from each action's GitHub release page on 2026-11-03. Before using this
# file, open the release page yourself and confirm the SHA matches the tag; a SHA you have
# not checked is just a 40-character string.
name: ci-cd

on:
  push:
    branches: [main]
    tags: ["v*.*.*"]
  pull_request:
    branches: [main]

# Least privilege at the top; jobs that need more raise it for themselves only.
permissions:
  contents: read

# One run per branch or tag at a time. PR and main runs are cancelled when a newer commit
# arrives; a tag run (a production release) must never be cancelled half way, so the
# expression turns cancellation off for refs/tags/*.
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ !startsWith(github.ref, 'refs/tags/') }}

env:
  AWS_REGION: ap-south-1
  ECR_REPOSITORY: shop/api
  # Replace with the role that trusts GitHub's OIDC provider for this repo (no keys stored).
  AWS_ROLE_TO_ASSUME: arn:aws:iam::000000000000:role/github-actions-shop-api
  GITOPS_REPO: example-org/gitops

jobs:
  test:
    name: test (node ${{ matrix.node }})
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    strategy:
      fail-fast: false
      matrix:
        node: [22, 24]
    steps:
      - name: Checkout
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Set up Node with the npm cache keyed on package-lock.json
        uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version: ${{ matrix.node }}
          cache: npm
          cache-dependency-path: package-lock.json
      - run: npm ci --no-audit --no-fund
      - run: npm run lint
      - run: npm test -- --ci

  build:
    name: build and push by digest
    needs: test
    # Pull requests from forks must not get the OIDC token or push to ECR.
    if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    permissions:
      contents: read
      id-token: write # needed to request the OIDC token that AWS exchanges for credentials
    outputs:
      digest: ${{ steps.push.outputs.digest }}
      image: ${{ steps.login.outputs.registry }}/${{ env.ECR_REPOSITORY }}
    steps:
      - name: Checkout
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Configure AWS credentials through OIDC (no access keys in secrets)
        uses: aws-actions/configure-aws-credentials@e1253824e5c10ff9df46874f81ed3ec929e19cfd # v6.3.0
        with:
          role-to-assume: ${{ env.AWS_ROLE_TO_ASSUME }}
          role-session-name: gha-${{ github.run_id }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Log in to Amazon ECR
        id: login
        uses: aws-actions/amazon-ecr-login@d539f0932e70871a027e9d5a9d8fc38589180a64 # v2.1.6

      - name: Set up Docker Buildx (BuildKit builder with cache export support)
        uses: docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069 # v4.4.1

      - name: Build, tag with the git SHA, push, and capture the digest
        id: push
        uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0
        with:
          context: .
          file: Dockerfile
          # Only push from main and tags. A same-repo PR builds to prove the Dockerfile works.
          push: ${{ github.event_name != 'pull_request' }}
          tags: |
            ${{ steps.login.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
          labels: |
            org.opencontainers.image.revision=${{ github.sha }}
            org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
          # Layer cache lives in ECR next to the image; mode=max exports every stage's layers,
          # so the deps stage is a cache hit even when the build stage changed.
          cache-from: type=registry,ref=${{ steps.login.outputs.registry }}/${{ env.ECR_REPOSITORY }}:buildcache
          cache-to: type=registry,ref=${{ steps.login.outputs.registry }}/${{ env.ECR_REPOSITORY }}:buildcache,mode=max,image-manifest=true,oci-mediatypes=true
          provenance: false

      - name: Print the digest (the only identifier later jobs use)
        run: echo "pushed ${{ steps.push.outputs.digest }}"

  scan:
    name: scan the pushed image with Trivy
    needs: build
    if: github.event_name != 'pull_request'
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    permissions:
      contents: read
      id-token: write
    steps:
      - name: Configure AWS credentials through OIDC
        uses: aws-actions/configure-aws-credentials@e1253824e5c10ff9df46874f81ed3ec929e19cfd # v6.3.0
        with:
          role-to-assume: ${{ env.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Log in to Amazon ECR so Trivy can pull by digest
        uses: aws-actions/amazon-ecr-login@d539f0932e70871a027e9d5a9d8fc38589180a64 # v2.1.6
      - name: Trivy, fail on CRITICAL with a fix available
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          scan-type: image
          image-ref: ${{ needs.build.outputs.image }}@${{ needs.build.outputs.digest }}
          format: table
          severity: CRITICAL
          ignore-unfixed: true
          exit-code: "1"

  deploy-staging:
    name: deploy to staging through a GitOps PR
    needs: [build, scan]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    environment:
      name: staging
    steps:
      - name: Checkout the GitOps repo with a token that can open PRs there
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          repository: ${{ env.GITOPS_REPO }}
          # A fine-grained PAT or GitHub App token scoped to the gitops repo (contents and
          # pull-requests: write). The default GITHUB_TOKEN cannot write to another repo.
          token: ${{ secrets.GITOPS_TOKEN }}
          persist-credentials: false
      - name: Pin the staging overlay to the new digest
        env:
          IMAGE: ${{ needs.build.outputs.image }}
          DIGEST: ${{ needs.build.outputs.digest }}
        run: |
          # kustomize edit is one way; sed on a single "image:" line is the simplest.
          sed -i -E "s#^(\s*image:\s*).*shop/api.*#\1${IMAGE}@${DIGEST}#" envs/staging/api/deployment.yaml
          git diff --stat
      - name: Open the pull request Argo CD will sync after merge
        uses: peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          token: ${{ secrets.GITOPS_TOKEN }}
          branch: api/staging-${{ github.sha }}
          commit-message: "staging: shop/api ${{ github.sha }}"
          title: "staging: shop/api ${{ github.sha }}"
          body: |
            Image: ${{ needs.build.outputs.image }}@${{ needs.build.outputs.digest }}
            Source: ${{ github.server_url }}/${{ github.repository }}/commit/${{ github.sha }}
            Scan: Trivy passed with no fixable CRITICAL findings.

  deploy-prod:
    name: deploy to production (tag only, reviewers required)
    needs: [build, scan]
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    # The production environment has required reviewers and a deployment rule that only
    # allows refs matching v*. The job pauses here until someone approves in the GitHub UI.
    environment:
      name: production
      url: https://shop.example.com
    steps:
      - name: Checkout the GitOps repo
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          repository: ${{ env.GITOPS_REPO }}
          token: ${{ secrets.GITOPS_TOKEN }}
          persist-credentials: false
      - name: Pin the production overlay to the digest that staging already ran
        env:
          IMAGE: ${{ needs.build.outputs.image }}
          DIGEST: ${{ needs.build.outputs.digest }}
        run: |
          sed -i -E "s#^(\s*image:\s*).*shop/api.*#\1${IMAGE}@${DIGEST}#" envs/prod/api/deployment.yaml
          git diff --stat
      - name: Open the production PR (a second human merges it)
        uses: peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          token: ${{ secrets.GITOPS_TOKEN }}
          branch: api/prod-${{ github.ref_name }}
          commit-message: "prod: shop/api ${{ github.ref_name }}"
          title: "prod: shop/api ${{ github.ref_name }}"
          body: |
            Image: ${{ needs.build.outputs.image }}@${{ needs.build.outputs.digest }}
            Tag: ${{ github.ref_name }}
            Approved in the production environment by the required reviewers.
```

## Follow-up questions interviewers ask

* Replace the staging PR with an automatic merge and keep the PR for production. What breaks when two commits land on `main` within a minute?
* Add `cosign sign` of the digest with the OIDC identity and have Kyverno reject unsigned images in the cluster. Where in the job graph does signing go?
* Reduce runner minutes: which of the two cache layers would you keep if you could keep only one, and why?
* The team wants the same pipeline in GitLab CI. Map jobs, `needs`, environments and OIDC to their GitLab equivalents.
* A fork PR needs to post a coverage comment. Design it with `workflow_run` so no secret reaches untrusted code.
* How would you add a rollback job that opens a GitOps PR pointing at the previous digest, and what input does it need?

## Lessons that cover this

* [#5Git and trunk-based workflowsFoundations](/devops/learn/git-and-trunk-based-workflows)
* [#8Containers and DockerBuild and ship](/devops/learn/containers-and-docker)
* [#9CI/CD with GitHub Actions and GitLab CIBuild and ship](/devops/learn/ci-cd-github-actions-gitlab)
* [#19GitOps with Argo CD and progressive deliveryKubernetes](/devops/learn/gitops-argocd-progressive-delivery)

## Further reading

* [GitHub Actions documentationGuidedocs.github.com](https://docs.github.com/en/actions)
* [Trivy documentationGuidetrivy.dev](https://trivy.dev/docs/latest/)
* [SLSA: Supply-chain Levels for Software ArtifactsPaperslsa.dev](https://slsa.dev/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousDockerfile: multi-stage build with a non-root user](/devops/problems/multistage-dockerfile)[NextKubernetes manifests: Deployment, Service, Ingress and HPA with probes and limits](/devops/problems/kubernetes-manifests-web-app)

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
