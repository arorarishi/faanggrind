# Secure container image pipeline: build, scan, sign, SBOM, admission — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/supply-chain-image-pipeline

[DevOps problems](/devops#problems)

DESIGNPlatform design#13Medium

# Secure container image pipeline: build, scan, sign, SBOM, admission

supply-chaincosignslsasbomkyvernoecr

## Problem statement

Eighty services build container images in GitHub Actions and push them to Amazon ECR, from where Argo CD deploys them to EKS. A security review found base images referenced as `node:20` and `python:3.12-slim` with no digest, no vulnerability scanning, third-party actions pinned to `@main`, long-lived AWS keys in repository secrets, and nothing at the cluster stopping any image from running. A compromised action could have pushed anything to production. Design the pipeline so that only images built by the company's own workflows, from approved bases, scanned, signed and with provenance, can run in production.

## Requirements

### Functional

* Every production image is built from one of a small set of approved base images, referenced by digest, and rebuilt weekly.
* Every build produces an SBOM and a signed SLSA provenance attestation, and the image is signed; all three are stored next to the image in ECR.
* A vulnerability scan gates the push: critical findings with a fix available fail the build, with a time-limited exceptions process.
* The cluster refuses to run any image that is not signed by the company's build identity, and rewrites tags to digests on admission.
* Images are promoted from staging to production by digest only, never rebuilt.
* When a CVE drops in a base image, every affected service is rebuilt and redeployed automatically, and the owner can see which services are still exposed.

### Non-functional

* The security steps (scan, SBOM, sign, attest) add under 3 minutes to a typical build at p90.
* Admission verification adds under 500 ms to pod creation at p99 and fails closed if the signature cannot be verified.
* All 80 services can be rebuilt and redeployed for a base image CVE within 4 hours.
* ECR storage stays under 500 GB with a 90-day retention for untagged and non-production images.
* No long-lived cloud credentials anywhere in CI: OIDC federation only, with a token lifetime of 1 hour or less.
* Any image running in production can be traced to a commit, a workflow run and a base image digest within 1 minute.

## Back-of-the-envelope estimates

**Builds.** 80 services at an assumed 5 pushes per day each (PRs plus main) = 400 builds per day, of which about 1.5 per service per day produce a pushed image: 120 pushes per day.

**Scan time.** Trivy with a warm database takes an assumed 30 to 90 seconds per image; at 90 seconds that is 400 x 90 = 36,000 seconds, 10 runner-hours per day, or 30 minutes of wall time on 20 parallel runners. SBOM generation reuses the same filesystem walk and adds under 20 seconds. Signing and attesting are two network round trips to Fulcio and Rekor each, under 10 seconds. Total added: about 2 minutes, inside the 3-minute budget.

**Registry storage.** Layers shared with the base image cost nothing extra; the unique layers of a service image are an assumed 40 MB. 120 pushes x 40 MB = 4.8 GB per day; 90 days of retention is 432 GB, at an assumed 0.10 USD per GB-month about 43 USD. A lifecycle rule that deletes untagged images after 7 days and keeps the last 30 tagged images per repository holds it well under 500 GB.

**Signatures and attestations.** Each push creates 3 Rekor entries (signature, SBOM attestation, provenance attestation): 360 per day, about 10,800 per month, all in the public transparency log unless a private Sigstore instance is used.

**Admission.** About 120 new digests per day reach the cluster; the first pod of each digest costs one registry fetch and one Rekor lookup, an assumed 200 ms, so 24 seconds of verification per day. Kyverno caches results for 60 minutes by default, so later pods of the same digest cost microseconds. The 500 ms budget holds with 10x margin.

**Rebuild for a base CVE.** 80 builds at an assumed 4 minutes each on 20 parallel runners is 16 minutes of CI; rolling them out in waves of 10 services at 6 minutes each is 48 minutes. With review and the staging soak, well under 4 hours.

## API

```
Approved base images (repo platform-base-images, rebuilt weekly by a scheduled workflow):
  base/node:20      FROM public.ecr.aws/docker/library/node:20-bookworm-slim@sha256:<digest>
  base/python:3.12  FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:<digest>
  base/go-static    FROM a distroless static image by digest
  each is scanned, signed and published to ECR as <account>.dkr.ecr.<region>.amazonaws.com/base/<name>:<date>@sha256:...
  Renovate or Dependabot opens a PR in every service repo when a base digest changes

Service Dockerfile rules (checked by a lint step):
  FROM <ecr>/base/node:20@sha256:...   AS build        # digest required, company base required
  FROM <ecr>/base/node:20@sha256:...                   # multi-stage: build tools never ship
  USER 10001                                           # non-root, numeric UID
  no ADD, no curl | sh, no secrets as ARG

Reusable workflow .github/workflows/build-image.yml (called by every service):
  permissions: contents read, id-token write, packages read, attestations write
  steps:
    actions/checkout@<40-char sha>
    aws-actions/configure-aws-credentials@<sha>  role-to-assume arn:aws:iam::<acct>:role/gha-ecr-push, OIDC
    docker/build-push-action@<sha>   provenance true, sbom true, push to ECR, tags sha-<commit>
    trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed --ignorefile .trivyignore.yaml <image>@<digest>
    trivy image --format cyclonedx --output sbom.cdx.json <image>@<digest>
    cosign sign --yes <image>@<digest>                                   # keyless, GitHub OIDC identity
    cosign attest --yes --type cyclonedx --predicate sbom.cdx.json <image>@<digest>
    actions/attest-build-provenance@<sha>  subject-name <image> subject-digest <digest> push-to-registry true
  output: the digest, written to the GitOps repo by a bot PR

Promotion:  argocd app set <app> --parameter image.digest=sha256:...   (prod values reference digest only)
Verify by hand:
  cosign verify <image>@<digest> \
    --certificate-identity-regexp '^https://github.com/<org>/platform-workflows/.github/workflows/build-image.yml@refs/heads/main$' \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Data model

```
ECR (one registry per account, repositories per service and per base)
  repository settings: image tag mutability IMMUTABLE; registry scanning ENHANCED (Amazon Inspector), scan on push and continuous
  lifecycle: untagged > 7 days deleted; keep last 30 tagged per repo; prod digests pinned by a "keep" tag
  OCI referrers next to each image digest: cosign signature, SBOM attestation, provenance attestation

IAM
  role gha-ecr-push     trust: token.actions.githubusercontent.com, sub = repo:<org>/*:ref:refs/heads/main
                        allow: ecr:BatchCheckLayerAvailability, PutImage, InitiateLayerUpload, ... on service repos
  role gha-base-push    trust: sub = repo:<org>/platform-base-images:ref:refs/heads/main only
  no IAM users with access keys; Access Analyzer finding on any new key

Cluster (Kyverno, 3 replicas, webhookConfiguration failurePolicy Fail, timeoutSeconds 15)
  ClusterPolicy verify-build-identity   (one verifyImages rule checks signatures, a second checks attestations)
    match Pod in namespaces with label env=prod
    rule 1 verifyImages:
      imageReferences: ["<acct>.dkr.ecr.<region>.amazonaws.com/*"]
      failureAction: Enforce
      mutateDigest: true   verifyDigest: true   required: true
      attestors: keyless subjectRegExp of the reusable workflow on main,
                 issuer https://token.actions.githubusercontent.com, rekor url https://rekor.sigstore.dev
    rule 2 verifyImages:
      type: SigstoreBundle
      attestations: type https://slsa.dev/provenance/v1, same keyless attestor,
                    conditions: buildDefinition.buildType equals https://actions.github.io/buildtypes/workflow/v1
  ClusterPolicy block-other-registries: any image not from the company ECR is rejected
  ClusterPolicy require-non-root and require-digest for all namespaces

Exceptions (repo platform-security/exceptions/<service>.yaml, rendered into .trivyignore.yaml at build time)
  - id: CVE-2026-XXXXX
    expired_at: 2026-12-15
    statement: "false positive, the vulnerable function is not reachable; tracked in SEC-412"
    approved_by: security-team    # CODEOWNERS enforces the reviewer

Inventory: a nightly job lists running image digests per namespace, joins with SBOMs, writes to a table
  (digest, service, base_digest, commit, workflow_run, first_seen, cves_open)
```

## High-level design

**Bases and Dockerfiles**

1. Create a `platform-base-images` repository with 3 to 5 approved bases, each a Dockerfile that pins the upstream image by digest. A weekly scheduled workflow rebuilds, scans, signs and pushes them with a date tag, then a dependency bot opens a PR in every service repository bumping the base digest.
2. Add a Dockerfile lint step to the reusable workflow: company base by digest, multi-stage, numeric non-root `USER`, no `ADD`. A service that fails lint does not build.

**Workflow hardening**

3. Replace every `uses: x/y@main` with a 40-character commit SHA and let the dependency bot bump them. Set `permissions:` to the minimum at the job level; the default token can only read contents.
4. Remove the AWS keys from repository secrets. The workflow assumes an IAM role through GitHub's OIDC provider; the role's trust policy limits the `sub` claim to the organisation's repositories on the `main` branch, so a fork or a feature branch cannot push to ECR.

**Build, scan, sign, attest**

5. Build with BuildKit, tag with the commit SHA, push, and capture the digest. Everything after this point refers to the digest, never the tag.
6. Run Trivy against the digest: `--exit-code 1 --severity CRITICAL --ignore-unfixed` fails the build on a critical finding that has a fix; the ignore file is generated from the exceptions repository so every skipped CVE has an owner and an expiry date.
7. Generate a CycloneDX SBOM, sign the image with cosign keyless, attach the SBOM as an attestation, and produce SLSA provenance through the GitHub attestation action, pushed to the registry as OCI referrers.

**Registry**

8. ECR repositories are created with `--image-tag-mutability IMMUTABLE`, so a second push to `sha-abc123` fails with `ImageTagAlreadyExistsException`. Enhanced scanning with Amazon Inspector rescans stored images continuously, which is how new CVEs in old images are found after the build.

**Admission and promotion**

9. Kyverno `verifyImages` in enforce mode on production namespaces: the image must come from the company ECR, carry a keyless signature whose certificate identity is the reusable workflow on `main`, and carry a provenance attestation whose builder matches. `mutateDigest` rewrites any tag to its digest so what was verified is what runs.
10. Argo CD values for production hold a digest. Promotion from staging is a PR that copies the digest; nothing is rebuilt.

**CVE response**

11. An Inspector finding of a critical CVE triggers an EventBridge rule that opens a ticket with the list of affected digests from the inventory table. For a base image CVE, the base rebuild runs immediately, the bot PRs are auto-merged for services with passing tests, and the inventory shows the exposed set shrinking.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why tags are not enough and digests are

A tag is a mutable pointer: `node:20` today and `node:20` next week can be different images, and anyone with push access can repoint it. A digest is the SHA-256 of the image manifest, so `@sha256:...` names exactly one set of layers forever. Every control here depends on that. The scan result is tied to a digest; a signature on a tag would cover whatever the tag points at later. Kyverno verifies the signature of a digest and rewrites the pod spec to it so the kubelet cannot pull something else. Promotion by digest means staging and production run the same bytes. ECR immutable tags close the gap at the registry, so even a stolen CI token cannot overwrite `sha-abc123`. The cost is readability: a digest says nothing to a human, which is why the inventory table maps it back to commit, workflow run and base.

### Keyless signing and the trust root

With a key, the problem is the key: where it lives, who rotates it, what happens when the laptop holding it is stolen. Keyless signing removes it. The workflow asks GitHub for an OIDC token that states "I am workflow build-image.yml in org X on branch main". Cosign generates a key pair in memory and sends the public key and the token to Fulcio, Sigstore's certificate authority, which issues a short-lived certificate binding the key to that identity. Cosign signs the digest, records the signature and certificate in Rekor, the public transparency log, and discards the private key. A verifier checks that the signature matches the digest, that the certificate chains to the Sigstore root bundled with cosign and Kyverno, and that the certificate's identity and issuer match the policy. The trust root is GitHub's OIDC issuer plus Sigstore's root, not a secret the company holds. The trade-off: entries in a public log reveal image names and build times; a company that cannot accept that runs a private Sigstore instance or KMS-held keys with the same verify flow.

### SLSA levels and what each buys

SLSA's Build track has four levels. Build L0: no guarantees. Build L1, "provenance exists": the build platform records how the artifact was made, which catches mistakes but is easy to forge. Build L2, "hosted build platform": a hosted platform generated and signed the provenance, so forging it needs an attack on the platform rather than an edited file. Build L3, "hardened builds": builds are isolated from each other and the signing material is out of reach of user-defined steps. GitHub states that artifact attestations alone give Build L2, and that a shared reusable workflow, which isolates the build from the calling workflow, is the path to L3; that is why every service calls one reusable workflow it cannot edit. A self-hosted runner shared between jobs would drop the level. The Source track, new in v1.2, covers how code reaches the branch and is out of scope here.

### The exception process that keeps the gate on

A scan gate with no exit is disabled within a month, usually by someone adding `continue-on-error: true` during an incident. The design gives the exit a shape. Exceptions live in one repository owned by the security team through CODEOWNERS. Each entry names the CVE, a reason, a ticket and an `expired_at` date at most 90 days out; Trivy's `.trivyignore.yaml` format carries `id`, `statement` and `expired_at` natively and stops ignoring the finding when the date passes. A build that needs an exception gets one within a business day, and the rendered ignore file is a build artifact so an audit can see what was skipped for which build. `--ignore-unfixed` keeps the gate honest the other way: a critical with no fix cannot be acted on by the service team, so it is reported, not blocking. The weekly review lists exceptions expiring soon and services with over 3 active ones.

## Evaluation

**Pipeline SLIs.** Share of production pods whose image is signed and has provenance (target 100 percent, measured by a nightly `cosign verify` over the inventory). Added build time for the security steps (p90 under 3 minutes). Admission verification latency from Kyverno metrics (p99 under 500 ms). Time from a base image CVE disclosure to all 80 services redeployed (under 4 hours, measured in a quarterly drill). Number of active exceptions and the oldest one's age.

**Chaos and attack tests before go-live.** Push an unsigned image to ECR with admin credentials and confirm Kyverno rejects a pod using it. Sign an image from a fork workflow and confirm the identity regex rejects it. Re-tag an old image and confirm the immutable repository refuses the push. Make Rekor unreachable from the cluster and confirm admission fails closed, then confirm cached digests still schedule. Add a `@main` action reference and confirm lint fails the PR.

**Cost review.** ECR storage per repository against the lifecycle policy; CI minutes spent on scanning per week; Inspector per-image scan charges.

**Security checks.** Quarterly: IAM Access Analyzer shows no access keys for CI; every workflow uses the reusable workflow at a SHA; Kyverno policies are in Enforce mode with reports showing zero violations; the Sigstore root used by Kyverno is updated; the exceptions repository has no entry past its expiry.

**Weak versus strong answer.** A weak answer adds a scanner to CI. A strong answer explains why the digest is the unit of trust, what identity the cluster verifies, what SLSA level the design reaches and why, and how the exception process keeps the gate from being turned off.

## Bottlenecks & mitigations

* Trivy database download on every runner: cache it or run a database mirror, or scan time doubles.
* Kyverno webhook on the pod creation path: 3 replicas and the verification cache; a Kyverno outage with `failurePolicy: Fail` blocks all production pod creation, which is the chosen trade-off.
* Rekor and Fulcio are external dependencies at build and admission time; a private Sigstore instance or a KMS key removes them.
* One reusable workflow for 80 services: a bad change breaks every build, so it is versioned by tag and rolled out to a canary set of repositories first.
* The dependency bot opens 80 PRs per base rebuild; auto-merge on green tests is required or they rot.

## Failure modes

* **Compromised third-party action.** It runs with the job's token and credentials. Mitigation: SHA pinning, minimal `permissions`, OIDC role limited to pushing images, and admission that would reject an image signed by any other workflow identity.
* **Attacker pushes directly to ECR with stolen AWS credentials.** The image is in the registry but unsigned. Mitigation: Kyverno rejects it; ECR push is limited to the OIDC role; an alert on any push not from that role.
* **Kyverno down during a deploy.** Pods cannot be created in production. Mitigation: 3 replicas across zones, PodDisruptionBudget, and a documented break-glass that switches `failurePolicy` to Ignore for a time-boxed window with an audit log entry.
* **Signature verification passes on the wrong identity.** A regex like `.*` on the subject accepts any GitHub repository. Mitigation: the regex is anchored to the organisation and the reusable workflow; a test pod signed from another repository is part of the drill.
* **Base image rebuild ships a broken base.** 80 services fail at once. Mitigation: the base is promoted only after a canary set of services passes integration tests; bases are tagged by date so the previous one is a one-line rollback.
* **Exception file edited to ignore everything.** Mitigation: CODEOWNERS review by security, expiry required by schema validation, and a weekly report of exception counts.
* **Rekor outage at build time.** Signing fails and builds stop. Mitigation: retries with backoff, and a private Sigstore or KMS fallback decided in advance rather than during the outage.
* **Image runs from a sidecar injected by a mutating webhook after Kyverno.** An unverified image slips in. Mitigation: webhook ordering with Kyverno last, and the nightly inventory verifying every running container, not only what admission saw.

## Follow-up questions interviewers ask

* The company adopts self-hosted runners on EKS to save money. What SLSA level do you have now, and what would it take to get back to the previous one?
* A vendor ships you an image you cannot rebuild. How does it get into production?
* How would you verify the SBOM attestation at admission, not only the signature, and what would you check in it?
* Argo CD deploys Helm charts from a chart registry. How do you sign and verify the chart, not only the image?
* The public Rekor log reveals your service names. What are your options?
* A critical CVE is in glibc, in every base. Walk through the first 4 hours.

## Lessons that cover this

* [#8Containers and DockerBuild and ship](/devops/learn/containers-and-docker)
* [#9CI/CD with GitHub Actions and GitLab CIBuild and ship](/devops/learn/ci-cd-github-actions-gitlab)
* [#23Security and DevSecOps - secrets, least privilege, supply chain, policy as codeOperate](/devops/learn/security-and-devsecops)

## Further reading

* [SLSA: Supply-chain Levels for Software ArtifactsPaperslsa.dev](https://slsa.dev/)
* [Sigstore cosign documentation: Signing overviewGuidedocs.sigstore.dev](https://docs.sigstore.dev/cosign/signing/overview/)
* [Kyverno documentationGuidekyverno.io](https://kyverno.io/docs/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousSLO-based alerting and on-call system](/devops/problems/slo-alerting-oncall)[NextRate limiting, bot and DDoS protection at the edge](/devops/problems/edge-rate-limiting-ddos)

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
