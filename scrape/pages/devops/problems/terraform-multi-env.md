# Multi-environment Terraform: dev, staging and prod with remote state — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/terraform-multi-env

[DevOps problems](/devops#problems)

DESIGNPlatform design#3Medium

# Multi-environment Terraform: dev, staging and prod with remote state

terraformawsiacgithub-actionsoidcstate-managementReported at Infosys, Wipro, TCS

## Problem statement

A 12-engineer team manages the AWS setup for one product (VPC, EKS, RDS, IAM, S3, about 900 resources) in a single Terraform directory. The directory uses Terraform workspaces named dev, staging and prod, one S3 bucket holds all the state, and everyone runs `terraform apply` from a laptop with their own admin keys. Last month an engineer thought they were in the dev workspace, applied, and changed a production security group; the site was down for 40 minutes. Design the repository layout, state, identity and pipeline so this cannot happen again and a change still reaches production the same day.

## Requirements

### Functional

* Dev, staging and prod live in separate AWS accounts; no single credential can write to more than one.
* Each environment and each stack (network, cluster, data, identity) has its own state file with locking.
* A pull request produces a plan, a policy check and a cost diff as comments; `apply` happens only from CI after merge, never from a laptop.
* A change is promoted dev to staging to prod as separate pull requests that change only a version number or variable.
* Drift between state and reality is detected daily and reported, not silently applied.
* A documented break-glass path exists for an outage, and state surgery (import, move, remove) follows a written procedure through the same pipeline.

### Non-functional

* Blast radius of one apply: one environment, one stack, at most about 60 resources, never 900 across 3 environments.
* Plan on a pull request completes in under 5 minutes; apply of a normal change in under 10.
* Mean time from merged dev change to production under 1 working day, with two human approvals on the prod PR.
* CI cost for Terraform under 100 USD per month at 40 pull requests per week, at an assumed 0.008 USD per runner-minute.
* No static AWS access keys anywhere: laptops use SSO with read-only roles, CI uses OIDC.
* State files encrypted at rest, versioned, and recoverable to any point in the last 90 days.

## Back-of-the-envelope estimates

**State files.** 3 environments x 5 stacks (network, eks, data, iam, observability) = 15 state files instead of 1. Each holds about 60 resources instead of 900.

**Plan time.** Terraform refreshes resources with up to 10 parallel API calls by default. At roughly 0.5 seconds per read, 900 resources take 900 x 0.5 / 10 = 45 seconds of refresh alone, plus provider start-up and the graph; a 60-resource stack refreshes in 60 x 0.5 / 10 = 3 seconds. The 5-minute plan budget is easily met per stack, and the real time goes into runner start-up, `terraform init` and provider downloads, which a cached `.terraform` directory cuts to under a minute.

**Apply frequency.** 40 pull requests per week, each planned about twice (first push plus a fix) = 80 plans per week, 40 applies. Each plan job takes about 4 minutes plus 2 minutes of checkov, tflint and Infracost; each apply about 6 minutes.

**CI minutes.** Plans: 80 x (4 + 2) = 480 minutes. Applies: 40 x 6 = 240. Drift detection: 15 stacks x 3 minutes x 7 days = 315. Total about 1,035 minutes per week, about 4,480 per month, at 0.008 USD = about 36 USD per month, well under the 100 USD budget. Doubling pull request traffic still fits.

**Blast radius.** One state, three workspaces: a wrong-workspace apply can touch any of 900 resources in any of 3 environments, and a corrupted state file loses all of them. Per environment and per stack: a wrong apply can touch at most 60 resources in one account, and the OIDC role of the dev pipeline cannot even call the prod account. That is a 15x smaller blast radius before any human care is applied, and a corrupted state file costs one stack of one environment.

**Cost diff.** Infracost on a PR that changes an RDS instance class from db.r6g.large to db.r6g.xlarge shows roughly a doubling of that line (assumed on-demand prices), which a reviewer sees before approving.

## API

```
Repo infra-live/                        one root module per account and stack
  envs/
    dev/      account 111111111111
      network/   main.tf  backend.tf  terraform.tfvars   (module version v1.4.0)
      eks/       ...
      data/      ...
    staging/  account 222222222222   same stacks
    prod/     account 333333333333   same stacks
  .github/workflows/
    plan.yml     on: pull_request   matrix from changed envs/*/* directories
    apply.yml    on: push to main   same matrix, environment: prod needs 2 reviewers
    drift.yml    on: schedule 03:10 UTC daily   plan -detailed-exitcode on every stack

Repo infra-modules/                     reusable modules, semver Git tags
  modules/vpc/   modules/eks-cluster/   modules/rds-postgres/
  each: variables.tf (typed, described), outputs.tf, README, examples/, tests/

Root module usage (envs/prod/network/main.tf)
  module "vpc" {
    source = "git::https://github.com/org/infra-modules.git//modules/vpc?ref=v1.4.0"
    cidr   = var.cidr
    azs    = 3
  }

Pipeline per changed stack
  init  -> terraform init -backend-config=env/prod.s3.tfbackend
  plan  -> terraform plan -out=tfplan -lock-timeout=120s -detailed-exitcode
  check -> tflint; checkov -d .; infracost-ci diff --base-path base --head-path head
           (Infracost compares a base and a head checkout and posts the cost comment)
  post  -> plan summary, policy result and cost table as one PR comment
  apply -> only on main, only from the same saved tfplan after a re-plan shows no diff

Promotion
  1. PR to envs/dev/eks     bumps ref=v1.4.0 -> v1.5.0, merged, applied
  2. PR to envs/staging/eks same one-line change, soak 1 day
  3. PR to envs/prod/eks    same change, 2 approvals, applied in the deploy window

Break-glass
  AWS SSO permission set "infra-breakglass" on prod, 1 hour session, requires MFA,
  CloudTrail alert on AssumeRole; afterwards run the pipeline plan to reconcile state.
```

## Data model

```
AWS accounts (AWS Organizations)
  shared-services  CI OIDC provider, infra-modules artifacts
  dev              111111111111   role terraform-apply-dev    trust: repo:org/infra-live:ref:refs/heads/main
                                   role terraform-plan-dev     trust: repo:org/infra-live:pull_request (read-only)
  staging          222222222222   same pair
  prod             333333333333   same pair, apply role also requires environment:prod claim

State (one bucket per account, in that account)
  s3://org-tfstate-prod/   versioning on, SSE-KMS, bucket policy denies deletes, 90-day noncurrent retention
    network/terraform.tfstate     + network/terraform.tfstate.tflock while locked
    eks/terraform.tfstate
    data/terraform.tfstate
  backend "s3" {
    bucket       = "org-tfstate-prod"
    key          = "eks/terraform.tfstate"
    region       = "ap-south-1"
    use_lockfile = true          # S3 native locking; dynamodb_table is deprecated
    encrypt      = true
    kms_key_id   = "arn:aws:kms:ap-south-1:333333333333:key/..."
  }

Cross-stack references: data "terraform_remote_state" or, better, SSM parameters
  /infra/prod/network/vpc_id, /infra/prod/network/private_subnet_ids   written by network outputs

Module interface (infra-modules/modules/eks-cluster)
  variables: name (string), kubernetes_version (string), vpc_id (string),
             subnet_ids (list(string)), node_pools (map(object({instance_types, min, max})))
             tags (map(string))
  outputs:   cluster_name, cluster_endpoint, oidc_provider_arn, node_role_arn
  constraints: required_providers aws ~> 6.0, required_version >= 1.10
  no provider block inside the module; no hard-coded account ids or regions

Secrets: never in tfvars. RDS password: manage_master_user_password = true (Secrets Manager);
  app secrets through External Secrets Operator; CI has no secrets except the OIDC token.

GitOps boundary: Terraform owns accounts, VPC, EKS, IAM, RDS, S3 and the Argo CD bootstrap;
  everything inside the cluster (namespaces, Helm releases, policies) is in platform-gitops and Argo CD.
```

## High-level design

**Separate the environments**

1. Create three AWS accounts under AWS Organizations plus a shared-services account, with SSO permission sets that give engineers read-only access to prod and `PowerUser` in dev by default.
2. Create one state bucket per account, in that account, with versioning, KMS encryption, a bucket policy that denies `DeleteObject`, and lifecycle retention of noncurrent versions for 90 days.
3. In each account, create a GitHub OIDC provider and two IAM roles: a plan role with read-only access, and an apply role whose trust policy only accepts tokens from the `main` branch of `infra-live` (and, for prod, the `prod` GitHub environment claim).

**Split the code**

4. Replace the single directory and its workspaces with `envs/<env>/<stack>/` root modules, each with its own `backend.tf` pointing at its account's bucket and its own `terraform.tfvars`. Workspaces are dropped entirely.
5. Move reusable code into `infra-modules`, one module per building block, with typed variables, descriptions, outputs and an `examples/` directory that doubles as a test. Tag releases with semver; root modules pin `?ref=vX.Y.Z`.
6. Pass values between stacks through SSM parameters written as outputs, so the `eks` stack never reads the `network` state directly and the two can be applied by different people.

**Move apply into CI**

7. `plan.yml` finds changed `envs/*/*` directories, assumes the plan role of that account through OIDC, runs `init`, `plan -out`, converts the plan to JSON, runs tflint and checkov on it, runs the Infracost diff between the base and head checkouts, and posts one comment with the resource summary, policy findings and cost change.
8. `apply.yml` runs on merge to `main`, assumes the apply role, re-plans and applies with `-lock-timeout=120s`. The prod job uses a GitHub environment that requires two reviewers; the whole job for a stack runs under a concurrency group so two merges cannot apply at once.
9. `drift.yml` runs every night with `plan -detailed-exitcode` on all 15 stacks; exit code 2 opens or updates an issue with the diff and pages nobody.

**Promote, recover, bound**

10. A change is a module version bump or a variable change in dev first; the same one-line diff is opened against staging and then prod as separate PRs with the plan output attached.
11. State surgery goes through the pipeline too: `moved` blocks for renames, `import` blocks for adopting hand-made resources, `removed` blocks for leaving the state without destroying; `force-unlock` only with the lock ID from the error and after confirming the holder is dead.
12. Terraform stops at the cluster boundary: it installs Argo CD once, and everything inside Kubernetes is managed by Git and Argo CD.

## Architecture diagram

Rendering diagram…

## Deep dives

### Workspaces versus directories

Workspaces give several state files to one configuration and one backend, and that is the wrong tool here for three reasons. All workspaces share one backend block, so one bucket and one set of credentials: the person who can apply dev can apply prod, and the Terraform docs say workspaces are not appropriate where you need separate credentials and access controls. The current workspace is invisible in the code; it lives in a local file, which is how the wrong-workspace apply happened. And environments drift apart (prod has a bigger RDS, staging has no WAF), which turns the code into `var.env == "prod" ? ... : ...` conditionals. A directory per environment puts the environment in the path, lets each directory point at its own account and bucket, and lets prod lag a module version behind dev on purpose. The cost is repetition, which modules absorb: a root module is 30 lines of module calls, not a copy of the resources. Workspaces remain fine for short-lived copies, such as a per-branch dev stack.

### State locking and corruption

Two applies on the same state at the same time can both read version N and both write version N+1, and the loser's resources exist in AWS with no record in state. Locking prevents the race: the S3 backend writes `<key>.tflock` next to the state when `use_lockfile = true`, and the DynamoDB table method is deprecated. A stuck lock (a runner killed mid-apply) shows up as a lock error with an ID; `terraform force-unlock <id>` clears it, and the rule is to confirm in the Actions UI that the job is dead first. Corruption comes from elsewhere: a partial write, a manual edit, a provider upgrade that rewrote the schema. Bucket versioning is the recovery path (copy the previous version back), which is why the bucket policy denies deletes and keeps 90 days of versions. `-lock-timeout=120s` lets two merges to the same stack wait instead of failing.

### How a dev change cannot reach prod

Three independent walls. Accounts: a security group in dev and one in prod have different ARNs in different accounts, and the dev account's IAM has no path to prod. Roles: the plan role in each account is read-only and trusted by pull request tokens; the apply role is trusted only by tokens whose subject is `repo:org/infra-live:ref:refs/heads/main`, and the prod apply role additionally requires the `environment:prod` claim, which GitHub only issues after the environment's reviewers approve. A laptop has no apply role at all, only SSO read-only in prod. Pipelines: the matrix is computed from the changed directory, so a PR that touches `envs/dev/eks` plans and applies dev only; touching prod requires editing a file whose path says `prod`, with a plan comment that says `prod` and two approvers. None of these walls depends on anyone remembering which workspace they are in.

### Module interface design

A module is an API, and the rules are the same as for code. Inputs are typed (`list(string)`, `map(object({...}))`) with descriptions and sensible defaults, so a wrong shape fails at plan time rather than in AWS. Outputs expose IDs and ARNs that callers need, never whole resources. The module has no `provider` block and no hard-coded region or account; callers configure providers. It pins `required_providers` with `~>` so a major provider release cannot change behaviour under a patch bump. Each module has an `examples/` directory that CI applies in the dev account and destroys, which is both documentation and a test. Versions are semver Git tags; a breaking change (renaming a variable, changing a resource address) is a major bump with a `moved` block inside the module so callers upgrade without destroy and recreate. Keep modules at the level of a thing with a lifecycle (a VPC, a cluster, a database), not a wrapper for one resource and not the whole environment.

## Evaluation

**SLIs.** Time from PR open to plan comment (under 5 minutes at p90); time from merge to applied (under 10); share of applies run outside CI, from CloudTrail `AssumeRole` events on apply roles by non-CI principals (target 0); drift issues opened per week and their age; lead time from dev merge to prod merge (under 1 working day at p50).

**Tests.** A module's `examples/` applied and destroyed in dev on every tag. A deliberately bad PR (public S3 bucket, 0.0.0.0/0 on port 22) must be blocked by checkov. A PR that touches `envs/prod/network` from a fork must fail to assume any role. Kill a runner mid-apply and confirm the next run reports the lock, and that `force-unlock` with the reported ID recovers it. Restore a state file from a previous S3 version in dev and run a plan that shows no changes.

**Cost review.** Infracost monthly total per environment posted to the team channel; a PR whose cost delta exceeds 500 USD per month (assumed threshold) needs a comment from the owner explaining why.

**Security checks.** Quarterly review of the three apply roles' trust policies; IAM Access Analyzer on the state buckets; no `AWS_ACCESS_KEY_ID` in any repository secret, enforced by a secret scan.

**Strong versus weak answers.** A weak answer says "use workspaces per environment and a DynamoDB lock table". A strong answer separates accounts, explains why the plan role is read-only and the apply role is branch-bound, keeps the saved plan, and describes drift detection as reporting, not auto-apply.

## Bottlenecks & mitigations

* The prod environment gate with two reviewers is a queue; a dozen small PRs in a day wait on the same two people, so promote in batches or rotate approvers.
* Large stacks (the `data` stack with many RDS and parameter group resources) refresh slowly; split again when a plan passes 3 minutes.
* Provider downloads on every runner start; cache the plugin directory or use a runner image with providers baked in.
* Nightly drift across 15 stacks is 15 role assumptions and plans; fine at this size, but a 100-stack organisation needs sharding.
* SSM parameters for cross-stack values add a step; stacks must be applied in dependency order on first creation.

## Failure modes

* **Apply from a laptop with a leftover admin key.** Bypasses every control. Mitigation: no apply roles for humans, keys rotated out, CloudTrail alert on apply-role assumption by a non-CI principal.
* **Plan reviewed is not the plan applied.** A merge after another merge applies something nobody saw. Mitigation: apply re-plans and compares with the saved plan; if different, it stops and asks for a fresh review.
* **Stuck state lock after a killed runner.** All applies to that stack fail. Mitigation: runbook with `force-unlock` and the job-is-dead check; alert on lock errors.
* **Drift auto-applied overnight.** A hand-made emergency change is reverted while the on-call engineer sleeps. Mitigation: drift job only reports; reconcile the next morning through a PR.
* **Module major bump destroys and recreates a database.** Mitigation: `moved` blocks in the module, `prevent_destroy` on stateful resources, plan comments highlight any destroy.
* **Secrets in tfvars committed to Git.** Mitigation: `manage_master_user_password`, External Secrets, pre-commit secret scanning, `.tfvars` with sensitive values forbidden by policy.
* **Prod OIDC trust policy too broad.** Any branch or fork can apply. Mitigation: subject condition on the branch and environment, reviewed quarterly, tested by the fork PR test.

## Follow-up questions interviewers ask

* A second product team wants to reuse your modules but in a different AWS region and organisation. What changes in the module and in the pipeline?
* How would you adopt 200 resources that someone created by hand in prod, without downtime?
* Would you use Terragrunt, OpenTofu, or Terraform Cloud or HCP Terraform here, and what would each buy you?
* The nightly drift job shows the same 3 resources every night. Walk through the possible causes.
* How does the Terraform and Argo CD boundary handle something that both could manage, such as a Kubernetes namespace or an IAM role for a service account?
* A prod apply is half done when the runner dies. What is the state of the world and what do you do, in order?

## Lessons that cover this

* [#13Terraform - infrastructure as codeCloud and IaC](/devops/learn/terraform-infrastructure-as-code)
* [#28Interview playbook, what is new in 2026, revision sheetShip](/devops/learn/interview-playbook-2026-revision)

## Further reading

* [Terraform documentationGuidedeveloper.hashicorp.com](https://developer.hashicorp.com/terraform/docs)
* [Infracost documentation: Get startedGuideinfracost.io](https://www.infracost.io/docs/)
* [DORA: Research (State of DevOps)Paperdora.dev](https://dora.dev/research/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousZero-downtime deployment system with canary analysis and rollback](/devops/problems/zero-downtime-deploys)[NextProduction EKS cluster for a 30-engineer startup](/devops/problems/eks-cluster-platform)

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
