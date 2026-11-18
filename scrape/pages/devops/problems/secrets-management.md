# Secrets management across CI, Kubernetes and runtime — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/secrets-management

[DevOps problems](/devops#problems)

DESIGNPlatform design#6Medium

# Secrets management across CI, Kubernetes and runtime

secretsexternal-secretsaws-secrets-manageroidcrotationsecurity

## Problem statement

A company runs 40 services on EKS across 3 environments (dev, staging, prod) with GitHub Actions pipelines. Today database passwords live in Kubernetes Secret manifests committed to Git in base64, and in GitHub repository secrets that engineers copy by hand between repos. Last month a leaked API key took a full day to rotate because nobody knew every place it was used. Design how secrets are stored, delivered to pods and pipelines, rotated and audited, so that no secret is in Git, every secret has one owner, and a leaked key can be rotated in under 15 minutes.

## Requirements

### Functional

* One source of truth for secrets with versioning, access policies per environment and an audit log of every read.
* Pods receive secrets without a human copying values; each team can read only its own secrets in its own namespaces.
* GitHub Actions gets cloud access without long-lived keys and reads secrets at run time, not from repository settings.
* Database credentials rotate automatically; applications pick up the new value without an outage.
* Git history and pull requests are scanned so a secret cannot be committed by accident.
* A documented break-glass path and an emergency rotation runbook that one on-call engineer can run.

### Non-functional

* Time to rotate a leaked key across all consumers under 15 minutes, measured in a quarterly drill.
* A new secret value reaches running pods within 5 minutes of being written to the store.
* The operator's credentials, if stolen, expose at most one team's secrets in one environment.
* Secrets Manager API cost under 50 USD per month at 540 secrets; the full platform under 300 USD per month.
* Zero secrets in Git, verified by a scanner that runs on every push and on the full history weekly.
* Every read of a production secret is attributable to a service or a person in CloudTrail within 15 minutes.

## Back-of-the-envelope estimates

**Count.** 40 services x 3 environments x about 4 secrets each (database, cache, a third-party API key, a signing key) = 480 application secrets. Shared platform secrets (registry, pager, SMTP, 20 of them x 3 environments) add 60. Total 540 secrets at an assumed 0.40 USD per secret per month = 216 USD.

**Sync calls.** The External Secrets Operator makes about one `GetSecretValue` call per ExternalSecret per refresh. With 480 ExternalSecrets at a 1-hour `refreshInterval`: 480 calls per hour, 350,400 per month, at an assumed 0.05 USD per 10,000 calls = 1.75 USD. At 15 minutes: 1,920 per hour, 1.4 million per month, 7 USD. At 5 minutes: 5,760 per hour, 4.2 million per month, 21 USD. The 5-minute delivery target is met by a 5-minute interval for 21 USD, or by a 1-hour interval plus a forced refresh during rotation. The design uses 15 minutes for prod and the forced refresh.

**CI calls.** 200 pipeline runs per day x 3 jobs x 22 days = 13,200 OIDC role assumptions and secret reads per month, under 0.10 USD.

**Rotation blast radius.** One Aurora cluster with a single app user shared by 8 services: a rotation restarts 8 Deployments. With one database user per service, a rotation touches 1 Deployment of 3 replicas, about 90 seconds of rolling restart.

**Time to rotate, before.** Find every place the key lives (grep 40 repos, 3 GitHub organisations, 3 clusters): 4 hours. Edit base64 in 12 manifests, open 12 PRs, wait for review and deploy: 3 hours. Discover a cron job nobody updated: 1 more hour. Total about 8 working hours, matching the day lost last month.

**Time to rotate, after.** Rotate in Secrets Manager: 1 minute. Force-sync the ExternalSecrets: 1 minute. Reloader rolls the 3 consuming Deployments: 3 minutes. Verify from the audit log that no consumer reads the old version: 5 minutes. Total 10 minutes, within the 15-minute target.

## API

```
How a team uses the platform:

1. Create a secret (platform CLI wraps the AWS call, enforces the name scheme and tags)
   aws secretsmanager create-secret \
     --name prod/payments/checkout/db \
     --secret-string '{"username":"checkout_app","password":"...","host":"...","port":"5432"}' \
     --tags Key=team,Value=payments Key=env,Value=prod
   Naming: <env>/<team>/<service>/<purpose>; the IAM policy is written against this prefix.

2. Declare it in the service's Helm values (no value appears anywhere in Git)
   externalSecrets:
     - name: checkout-db
       remoteKey: prod/payments/checkout/db
       refreshInterval: 15m
   The chart renders an ExternalSecret whose target Secret is mounted at /var/run/secrets/app/.

3. Read it in the application
   Mounted files: /var/run/secrets/app/password; re-read on change (the kubelet updates the
   file; fsnotify or re-read per connection open). Env vars only for values that never rotate.

4. In GitHub Actions (no AWS keys in repository secrets)
   permissions:
     id-token: write
     contents: read
   steps:
     - uses: aws-actions/configure-aws-credentials@v6
       with:
         role-to-assume: arn:aws:iam::111122223333:role/gha-payments-prod
         aws-region: ap-south-1
     - run: |
         SECRET=$(aws secretsmanager get-secret-value --secret-id prod/payments/checkout/db \
                  --query SecretString --output text)
         echo "::add-mask::$SECRET"

5. Rotate (automatic) or rotate now (emergency)
   aws secretsmanager rotate-secret --secret-id prod/payments/checkout/db
   kubectl annotate externalsecret checkout-db -n payments force-sync=$(date +%s) --overwrite

6. Bootstrap only (SOPS, encrypted with a KMS key, committed): the Argo CD repo credential,
   the ESO Pod Identity association is IAM not a secret, nothing else.
```

## Data model

```
AWS account per environment: dev (111..), staging (222..), prod (333..)
  Secrets Manager
    <env>/<team>/<service>/<purpose>        JSON value, tags team and env, KMS key per env
    rotation: Aurora master user -> managed rotation (no Lambda), rate(30 days)
              application DB users -> Lambda rotation function, alternating-users strategy
              third-party API keys -> manual, with a calendar reminder and an owner tag
    replica to ap-southeast-1 for prod secrets used by the DR region
  IAM
    role eso-<team>                 trust: pods.eks.amazonaws.com (Pod Identity)
                                    allow secretsmanager:GetSecretValue, DescribeSecret
                                    on arn:...:secret:<env>/<team>/*
                                    condition aws:ResourceTag/team = <team>
    role gha-<team>-<env>           trust: token.actions.githubusercontent.com OIDC
                                    sub = repo:acme/<team>-*:environment:<env>
    role breakglass-secrets-admin   trust: SSO permission set, MFA, 1 hour max session
  CloudTrail -> S3 + CloudWatch Logs; EventBridge rule on GetSecretValue by a human principal
  KMS key per environment; secret values encrypted with it; key policy denies dev roles in prod

EKS cluster per environment
  namespace external-secrets
    Deployment external-secrets (3 replicas), webhook, cert-controller
  namespace <team>  (one per team)
    ServiceAccount eso-<team>       Pod Identity association -> role eso-<team>
    SecretStore aws-<team>          provider.aws.service SecretsManager, region ap-south-1,
                                    no auth block: credentials come from Pod Identity
    ExternalSecret <service>-<purpose>
      refreshInterval 15m, secretStoreRef aws-<team>,
      target.name <service>-<purpose>, dataFrom.extract.key <env>/<team>/<service>/<purpose>
    Secret <service>-<purpose>      created and owned by ESO; never in Git
    Deployment <service>            annotation reloader.stakater.com/auto: "true"
                                    volume from Secret, mounted at /var/run/secrets/app
  Kyverno policies
    deny Secret objects from Argo CD applications except ESO-owned and SOPS bootstrap
    require the reloader annotation on any Deployment that mounts a Secret
```

## High-level design

**Source of truth**

1. Choose AWS Secrets Manager: the company is on EKS and AWS, it gives versioning, KMS encryption, resource policies, CloudTrail and managed rotation for RDS and Aurora. Vault is the right answer when secrets must span clouds or when dynamic short-lived database credentials are needed; the same operator supports both, so the choice is reversible.
2. One AWS account per environment and a naming scheme `<env>/<team>/<service>/<purpose>`. IAM policies and resource tags are written against that prefix, so the access policy is the name.

**Delivery to pods**

3. Install the External Secrets Operator in every cluster. Each team namespace gets a ServiceAccount with a Pod Identity association to `eso-<team>`, a `SecretStore` that uses it, and ExternalSecrets rendered by the service's Helm chart. The operator writes an ordinary Kubernetes Secret; the application mounts it as files.
4. Install Reloader. A Deployment with `reloader.stakater.com/auto: "true"` is rolled when its Secret changes; services that re-read files on change do not need it.

**Delivery to CI**

5. Add the GitHub OIDC provider to each AWS account. Each team gets `gha-<team>-<env>` roles whose trust policy limits the `sub` claim to the team's repositories and the GitHub environment. Workflows request `id-token: write`, assume the role and read secrets at run time with the AWS CLI, masking the output.

**Removing secrets from Git**

6. Rotate every secret that exists in Git history, because history is forever. Migrate manifests to ExternalSecrets, then delete the Secret manifests. The only encrypted file left is the SOPS bootstrap set.
7. Pre-commit hook and a CI job run gitleaks on every push; a weekly job scans the full history of all repositories and the GitHub secret scanning push protection is enabled at the organisation level.

**Rotation**

8. Aurora master credentials use managed rotation every 30 days. Application database users use the alternating-users rotation function so the old password stays valid while pods roll. Third-party API keys have an owner tag and a 90-day reminder.

**Audit and emergencies**

9. CloudTrail events for `GetSecretValue` go to CloudWatch Logs; an EventBridge rule pages the platform team when a human principal reads a production secret. The break-glass role requires MFA, lasts one hour and alerts on assumption.
10. The emergency runbook is a script: rotate, force-sync, wait for rollouts, verify no reads of the previous version, record the incident.

## Architecture diagram

Rendering diagram…

## Deep dives

### Why base64 in Git is a leak, not encryption

Base64 is an encoding: `echo cGFzc3dvcmQ= | base64 -d` prints the password. A Secret manifest in Git is a plain-text password readable by anyone with read access to the repository, every CI runner that clones it, every laptop with a checkout, and every fork. Git history makes it worse: deleting the file later leaves the value in every clone forever. The only fix for a value that was ever committed is rotation. Kubernetes itself does not help: the documentation states Secrets are stored unencrypted in etcd by default unless encryption at rest is turned on, which EKS does with a KMS key when configured. So the design has two rules: a Kubernetes Secret may exist in the cluster, created by the operator at run time, but never in Git; and the small bootstrap set is encrypted with SOPS and a KMS key, so the repository holds ciphertext and the key policy decides who can decrypt.

### Environment variables versus mounted files for rotation

An environment variable is read once, when the container starts. The Kubernetes documentation says ConfigMaps consumed as environment variables are not updated automatically and require a pod restart, and Secrets behave the same way. A Secret mounted as a volume is different: the kubelet updates the files after a delay that can be as long as the kubelet sync period plus the cache propagation delay, so a rotated value arrives without a restart. Two traps: a `subPath` mount never receives updates, and the application must re-read the file, for example when it opens a new database connection. For services that cannot re-read, Reloader does a rolling restart of the Deployment, which is safe because the alternating-users strategy keeps the old password valid until the next rotation. The twelve-factor advice to put config in environment variables was about separating config from code, not about rotation; files give both.

### Least privilege for the operator

An operator that can read every secret is the most valuable target in the cluster. The design splits it. The operator's own pod has no AWS credentials. Each team namespace has its own ServiceAccount with a Pod Identity association to a role that can call `GetSecretValue` and `DescribeSecret` only on `arn:aws:secretsmanager:ap-south-1:333...:secret:prod/payments/*`, with a condition on the `team` resource tag. A namespaced `SecretStore`, not a `ClusterSecretStore`, references that ServiceAccount, so an ExternalSecret in the search namespace cannot use the payments store. The result: a stolen token from one namespace exposes one team's secrets in one environment, and CloudTrail shows the role that read them. Vault reaches the same shape with a Kubernetes auth role per namespace and a policy per path.

### A leaked key, minute by minute

T+0: a developer pastes a production API key in a public Slack channel. T+1: they run the runbook script with the secret name. The script calls `rotate-secret` (for a third-party key it calls the provider's API to issue a new key and `put-secret-value`), which creates a new version labelled `AWSCURRENT` and moves the old one to `AWSPREVIOUS`. T+2: the script annotates every ExternalSecret that references that key with `force-sync`, found by a label the chart sets; the operator fetches the new version within seconds. T+3 to T+6: Reloader rolls the consuming Deployments; a `kubectl rollout status` loop waits. T+7: the script revokes the old key at the provider (for a database user, the alternating-users strategy makes this automatic at the next rotation; for an emergency it changes the old user's password now). T+8 to T+12: a CloudWatch Logs Insights query over CloudTrail confirms no `GetSecretValue` for `AWSPREVIOUS` in the last 5 minutes and the provider dashboard shows no calls with the old key. T+13: the incident ticket is opened with the timeline. Compare with the old world, where step one, finding where the key lived, took four hours.

## Evaluation

**SLIs.** Rotation drill time: quarterly, one engineer rotates a randomly chosen production secret end to end, target under 15 minutes. Propagation time: a canary secret is rewritten hourly and a canary pod reports when it sees the new value, target under 5 minutes at p99. Secrets in Git: gitleaks findings per week, target 0, with the weekly full-history scan as the second measure. Unattributed reads: production `GetSecretValue` events whose principal is not a known service role or a break-glass session, target 0.

**Tests.** Chaos: delete the operator pods and confirm pods keep running with their last synced Secret and the propagation SLI alerts. Revoke one team's Pod Identity association and confirm only that team's ExternalSecrets go to `SecretSyncedError`. Try to read a payments secret from a search namespace ServiceAccount and confirm an AccessDenied in CloudTrail. Commit a fake AWS key in a test repository and confirm push protection blocks it.

**Cost review.** Monthly Secrets Manager bill by the `team` tag; alert if API calls exceed 5 million per month, which means a refresh interval was set too low.

**Security checks.** Quarterly IAM Access Analyzer review of every `eso-*` and `gha-*` role; CloudTrail delivery monitored; KMS key policies reviewed when a team joins or leaves; break-glass assumptions listed in the monthly security review with a reason for each.

**A strong answer** names the trust policy `sub` condition, explains why files beat environment variables for rotation, and has a runbook with times. A weak answer says "use Vault" and stops.

## Bottlenecks & mitigations

* Secrets Manager API rate limits when hundreds of ExternalSecrets refresh at the same second after an operator restart; stagger with jitter and keep the interval at 15 minutes.
* Reloader rolling many Deployments at once after a shared secret rotates; split shared secrets per service.
* The operator's webhook as a dependency for creating ExternalSecrets: with it down, new services cannot start, existing ones are unaffected.
* CloudTrail delivery delay of up to 15 minutes bounds how fast the audit question can be answered.
* One Lambda rotation function per database engine and strategy; its failures are silent unless alerted.

## Failure modes

* **Secret committed to Git.** A developer pastes a token into a values file. Mitigation: push protection, pre-commit gitleaks, weekly history scan, and rotation as the only cure.
* **Rotation breaks the app.** Single-user rotation changes the password while pods still hold the old one. Mitigation: alternating-users strategy, Reloader, connection retry on auth failure.
* **ExternalSecret points at the wrong environment.** A copied manifest references a dev key in prod. Mitigation: the key prefix must equal the cluster environment, enforced by a Kyverno policy on `remoteRef.key`.
* **Operator role too broad.** One `ClusterSecretStore` with a `secretsmanager:*` role. Mitigation: namespaced stores, per-team roles, resource tag conditions, Access Analyzer review.
* **CI role trust too wide.** The `sub` condition uses a wildcard that matches any branch or a fork. Mitigation: environment-scoped `sub`, required reviewers on the prod environment.
* **Secret deleted by accident.** A `kubectl delete secret` or a deleted ExternalSecret with a `Delete` deletion policy. Mitigation: `deletionPolicy: Retain` on ExternalSecrets, Secrets Manager 30-day recovery window, no `forceDeleteWithoutRecovery` in prod.
* **Break-glass used quietly.** Someone reads a production secret through the admin role during an incident. Mitigation: EventBridge alert on human reads, one-hour sessions, mandatory ticket reference in the session name.

## Follow-up questions interviewers ask

* When would you choose Vault over Secrets Manager, and what changes in the design?
* How do you give a pod a database credential that lives for 1 hour and is never stored anywhere?
* The DR region needs the same secrets. How are they replicated and what about the KMS key?
* How would you use the Secrets Store CSI driver instead of the operator, and what do you gain and lose?
* An auditor asks who read the payments database password in the last 90 days. Show the query.
* How do you handle a secret that 15 services share, such as a payment gateway key, during rotation?

## Lessons that cover this

* [#12AWS managed platforms - EKS, ECS, Fargate, Lambda, SQS, ElastiCache, CloudFrontCloud and IaC](/devops/learn/aws-managed-platforms-eks-ecs)
* [#19GitOps with Argo CD and progressive deliveryKubernetes](/devops/learn/gitops-argocd-progressive-delivery)
* [#23Security and DevSecOps - secrets, least privilege, supply chain, policy as codeOperate](/devops/learn/security-and-devsecops)

## Further reading

* [External Secrets Operator documentationGuideexternal-secrets.io](https://external-secrets.io/latest/)
* [HashiCorp Vault documentationGuidedeveloper.hashicorp.com](https://developer.hashicorp.com/vault/docs)
* [The Twelve-Factor AppPaper12factor.net](https://12factor.net/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousObservability platform for 200 microservices](/devops/problems/observability-platform)[NextMulti-region disaster recovery with RPO 5 minutes and RTO 30 minutes](/devops/problems/multi-region-dr)

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
