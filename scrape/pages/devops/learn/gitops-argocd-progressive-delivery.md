# GitOps with Argo CD and progressive delivery — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/gitops-argocd-progressive-delivery

[DevOps roadmap](/devops)

KubernetesLesson #19StudyIntermediate 4 h

# GitOps with Argo CD and progressive delivery

GitOps means the desired state of a cluster lives in Git, and an agent inside the cluster pulls that state and keeps the cluster matching it. Argo CD is the most used agent. This lesson covers the four GitOps principles, why pull beats push, the Argo CD objects (Application, AppProject, ApplicationSet), sync, drift and self-heal, repository layout and promotion, rollback by revert, secrets with External Secrets, Flux as the alternative, and progressive delivery with Argo Rollouts canaries.

gitopsargo cdargo rolloutscanaryfluxexternal secretseks

## Why it matters

"How does code get from a merged pull request to production" is the question every DevOps interview asks in some form, and in 2026 the expected answer is a GitOps pipeline: CI builds an image, a commit changes the desired state, Argo CD applies it. Platform teams are hired to run exactly this for dozens of product teams, so the follow-ups go deep: multi-tenancy, drift, rollbacks, secrets, and how a canary gets judged. The 100xDevs cohort covers Argo CD in week 37.2; this lesson takes that material to the level a platform interview expects.

Read first: [Git and trunk-based workflows](/devops/learn/git-and-trunk-based-workflows), [CI/CD with GitHub Actions and GitLab CI](/devops/learn/ci-cd-github-actions-gitlab), [Deployment strategies and release engineering](/devops/learn/deployment-strategies-release-engineering), [Kubernetes architecture and core objects](/devops/learn/kubernetes-architecture-core-objects), [Helm - charts, templates, values and releases](/devops/learn/helm-charts)

## Lesson

### What GitOps is

The OpenGitOps project (a CNCF working group) defines GitOps with four principles (version 1.0.0):

1. **Declarative.** The desired state is expressed declaratively: Kubernetes manifests, Helm values, Kustomize overlays, not scripts of commands.
2. **Versioned and immutable.** The desired state is stored in a way that enforces immutability and versioning and keeps a complete history. Git is the usual store, hence the name, but an OCI registry also qualifies.
3. **Pulled automatically.** Software agents pull the desired state from the source. Nobody pushes to the cluster.
4. **Continuously reconciled.** The agents keep observing the actual state and applying the desired state, not only when a commit lands.

The last two principles separate GitOps from "CI runs kubectl apply": only GitOps keeps correcting the cluster after the merge.

### Push versus pull

|  | Push (CI runs kubectl or helm) | Pull (an agent in the cluster) |
| --- | --- | --- |
| Who holds cluster credentials | The CI system, for every cluster it deploys to | Nobody outside; the agent uses a ServiceAccount inside the cluster |
| Network | CI must reach the API server, so the API endpoint is exposed or CI runners sit in the VPC | Only outbound HTTPS from the cluster to Git and the registry |
| Drift | Nothing notices a kubectl edit until the next pipeline run | The agent reports OutOfSync within minutes and can revert it |
| Audit | Pipeline logs, which expire | The Git log: who changed what, reviewed by whom, when |
| Rebuilding a cluster | Re-run every pipeline | Point a new cluster at the same repo |

In an interview, give the credential argument first: a compromised CI runner in a push model has admin on production; in a pull model it can at most push a commit, which is reviewed and visible.

### Argo CD architecture

![GitOps flow from a developer pull request through CI, ECR and a GitOps repo pull request to Argo CD pulling and syncing inside the EKS cluster, with rollback shown as a git revert](/devops/img/gitops-flow-argocd.svg)GitOps flow from a developer pull request through CI, ECR and a GitOps repo pull request to Argo CD pulling and syncing inside the EKS cluster, with rollback shown as a git revert

Argo CD is a CNCF graduated project that runs in the `argocd` namespace as a few Deployments:

| Component | Job | If it is down |
| --- | --- | --- |
| argocd-server | The API server behind the UI and the `argocd` CLI: authentication, SSO, RBAC, Git webhooks | No UI or CLI; syncs continue |
| argocd-repo-server | Clones repositories and renders manifests with `helm template`, `kustomize build` or plain files; caches the result | Nothing new is rendered; last cache is used |
| argocd-application-controller | The reconciliation loop: per Application, compare rendered manifests with live objects, report Synced or OutOfSync, run syncs and hooks | No syncs, no drift detection; workloads unaffected |
| argocd-applicationset-controller | Expands ApplicationSets into Applications | New apps from generators are not created |
| argocd-redis | A cache of manifests and cluster state; disposable | Slower, rebuilt automatically |
| argocd-dex-server | Optional OIDC connector for SSO (GitHub, Google, LDAP) | Logins fail; existing tokens work |

The controller re-checks Git every 3 minutes by default (`timeout.reconciliation` in the `argocd-cm` ConfigMap), at once on a webhook from GitHub or GitLab, and sees a cluster change within seconds through the watch API.

### The Application resource

An Application is the unit of GitOps: one source, one destination, one sync policy.

```
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: shop-api-prod
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io   # deleting the Application deletes its objects
spec:
  project: shop-team
  source:
    repoURL: https://github.com/example/gitops
    targetRevision: main
    path: charts/api                 # a Helm chart in the repo
    helm:
      valueFiles:
        - ../../envs/prod/api-values.yaml
  destination:
    server: https://kubernetes.default.svc   # the cluster Argo CD runs in
    namespace: shop
  syncPolicy:
    automated:
      prune: true       # delete objects removed from Git (default false)
      selfHeal: true    # revert changes made outside Git (default false)
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    retry:
      limit: 3
      backoff:
        duration: 30s
        factor: 2
        maxDuration: 5m
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas       # the HPA owns this field
```

Each Application has two statuses. **Sync status** compares Git with the cluster: Synced or OutOfSync. **Health status** reads the objects themselves: Healthy, Progressing, Degraded, Missing, Suspended. A Deployment with a crash-looping new ReplicaSet is Synced and Degraded at once.

Without `automated`, Argo CD only reports OutOfSync and a human clicks Sync. Without `prune`, an object deleted from Git stays in the cluster. Without `selfHeal`, a `kubectl edit` is reported, not reverted. Production usually runs all three.

### AppProject: limits for teams

An AppProject is the multi-tenancy boundary: which repositories an Application may use, which clusters and namespaces it may deploy to, and which kinds it may create.

```
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: shop-team
  namespace: argocd
spec:
  sourceRepos:
    - https://github.com/example/gitops
  destinations:
    - server: https://kubernetes.default.svc
      namespace: shop
    - server: https://kubernetes.default.svc
      namespace: shop-*
  clusterResourceWhitelist: []          # no cluster-scoped objects at all
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota               # only the platform team sets quotas
  syncWindows:
    - kind: deny
      schedule: "0 18 * * 5"            # cron: Fridays 18:00
      duration: 62h                     # until Monday 08:00
      timeZone: Asia/Kolkata
      applications: ["*-prod"]
      manualSync: true                  # a human can still sync in an emergency
  roles:
    - name: deployer
      policies:
        - p, proj:shop-team:deployer, applications, sync, shop-team/*, allow
      groups:
        - shop-team-engineers
```

An Application whose destination is outside its project's list is refused before any sync, so a team cannot write `namespace: kube-system` into its own Application.

### Many apps: app-of-apps and ApplicationSets

With 50 teams nobody writes Applications by hand. Two patterns:

* **App-of-apps.** One root Application points at a folder of Application manifests. Syncing the root creates the children; the repo becomes the list of what is installed. Simple, and still common for bootstrapping a cluster (ingress controller, cert-manager, External Secrets, monitoring).
* **ApplicationSet.** A template plus a generator that produces Applications. Generators: `list` (a fixed list of environments), `clusters` (every cluster Argo CD knows, filtered by labels), `git` (one Application per directory or per file in a repo), `pullRequest` (one preview environment per open pull request, torn down on merge), and `matrix` and `merge` to combine them. The Argo CD docs recommend ApplicationSets over app-of-apps.

```
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: shop-services
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/example/gitops
        revision: main
        directories:
          - path: envs/prod/*          # one Application per service folder
  template:
    metadata:
      name: "{{path.basename}}-prod"
    spec:
      project: shop-team
      source:
        repoURL: https://github.com/example/gitops
        targetRevision: main
        path: "{{path}}"
      destination:
        server: https://kubernetes.default.svc
        namespace: shop
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

Adding a service is adding a folder; removing the folder removes the Application and, with prune, its objects.

### Sync waves, hooks, health and diffs

* **Sync waves.** The annotation `argocd.argoproj.io/sync-wave: "-1"` orders objects: lower waves first, with a 2 second gap and a health check between waves. Namespaces and CRDs in wave -1, a database in wave 0, the app in 1.
* **Hooks.** `argocd.argoproj.io/hook: PreSync` runs a Job before the apply (migrations), `PostSync` after it is healthy (smoke tests), `SyncFail` for cleanup. `argocd.argoproj.io/hook-delete-policy: HookSucceeded` removes the finished Job. Helm `pre-install` and `pre-upgrade` hooks map to PreSync automatically.
* **Health checks.** Argo CD judges built-in kinds and many CRDs (Rollout, Certificate); for your own CRD you add a Lua health script to `argocd-cm`.
* **ignoreDifferences.** Some fields are rightly changed by controllers after apply: `replicas` by an HPA, `caBundle` in a webhook by cert-manager, injected sidecars. Listing them with `jsonPointers` or `jqPathExpressions` keeps the app Synced while the controller does its job. Add `RespectIgnoreDifferences=true` to syncOptions so a sync does not overwrite them.
* **Sync options.** `CreateNamespace=true`, `ServerSideApply=true` for large objects and shared ownership, `PruneLast=true` to delete old objects only after new ones are healthy, `Replace=true` for a rare immutable-field change (delete and recreate, with downtime).

### RBAC, SSO and notifications

Users log in through SSO (an OIDC provider, or Dex in front of GitHub or LDAP). Permissions are rules in the `argocd-rbac-cm` ConfigMap: `p, role:shop-deployer, applications, sync, shop-team/*, allow` grants, and `g, shop-team-engineers, role:shop-deployer` binds an SSO group. `policy.default: role:readonly` lets everyone see and nobody change. The notifications controller sends events to Slack or a webhook on triggers such as `on-sync-failed` and `on-health-degraded`, so a failed production sync pings the owning team.

### From CI to the cluster

The split of responsibilities is the core of the design:

1. A developer merges a pull request to the application repo.
2. CI (GitHub Actions) builds the image, scans it, pushes it to ECR and reads back the digest `sha256:...`. Tags are mutable, digests are not, so the GitOps repo pins the digest.
3. CI checks out the GitOps repo, changes one line in `envs/staging/api-values.yaml` (`image.digest: sha256:...`) and opens a pull request. For staging the PR can auto-merge; for prod a human approves.
4. Argo CD sees the commit (webhook or next poll), renders the chart with the new values, finds the Deployment OutOfSync, applies it, and reports Healthy once the rollout finishes.

CI never holds a kubeconfig. Argo CD Image Updater is an alternative to step 3: it watches ECR for new tags matching a rule (semver, digest, newest build) and commits the change itself, which skips the review, so most teams use it only for dev.

### Repository layout and promotion

| Layout | Structure | Fits |
| --- | --- | --- |
| One GitOps repo, folder per environment | `charts/api/`, `envs/dev/`, `envs/staging/`, `envs/prod/`, `platform/` | A company under about 20 teams; one place to review everything |
| One GitOps repo per team | Each team owns its repo; the platform repo holds AppProjects and ApplicationSets pointing at them | Many teams with different release rules; AppProject restricts each repo to its namespaces |
| Branch per environment | `dev`, `staging`, `prod` branches | Looks natural and goes wrong: merges carry unrelated changes between environments |

What goes where: application code and its Dockerfile in the app repo; the chart or Kustomize base and per-environment values in the GitOps repo; add-ons and AppProjects in a platform folder only the platform team can merge to. Promotion is a pull request copying the digest from `envs/staging` to `envs/prod`, which CI can open after staging has been healthy for an hour. Git history then answers "what is in prod and since when".

### Rollback the GitOps way

`kubectl rollout undo` and `helm rollback` are wrong answers in a GitOps interview, because self-heal would put the bad version straight back. The right answer: `git revert <merge commit>` on the GitOps repo, merge it, and Argo CD syncs the previous digest the same way it synced the bad one. For a faster emergency revert, Argo CD's UI and `argocd app rollback` re-apply an earlier synced revision, but only when auto-sync is off for that app, and the revert commit must still follow. Neither path reverts a database migration, which is why migrations must be backwards compatible with the previous version.

### Secrets in a GitOps repo

Git must never hold a plaintext secret, and Argo CD does not solve that by itself. Three options:

| Option | How | Trade-off |
| --- | --- | --- |
| SOPS | Encrypt the values of a YAML file with a KMS key; a plugin decrypts at render time | Secrets are in Git, encrypted; key rotation re-encrypts every file; needs a repo-server plugin |
| Sealed Secrets | A controller holds a private key; you commit a SealedSecret only that cluster can open | Simple; tied to one cluster's key; the value still originates on a laptop |
| External Secrets Operator (ESO) | Commit an ExternalSecret that names an entry in AWS Secrets Manager; ESO creates and refreshes the Secret | Nothing secret in Git at all; rotation happens in Secrets Manager; needs IAM for ESO |

ESO is the default on EKS: one source of truth with IAM audit, rotation as a Secrets Manager feature, and a GitOps repo that is safe to make public. ESO authenticates with IRSA or Pod Identity, so no AWS key exists in the cluster.

```
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: api-db
  namespace: shop
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: api-db                       # the Kubernetes Secret ESO creates
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: prod/shop/api             # the Secrets Manager entry
        property: url
```

### Flux: the other CNCF option

Flux is the other CNCF graduated GitOps tool: controllers driven by custom resources, with no UI.

|  | Argo CD | Flux |
| --- | --- | --- |
| Model | Application objects, a UI and an API server, one install can manage many clusters | Controllers (source, kustomize, helm, notification, image automation) and CRDs: GitRepository, Kustomization, HelmRelease |
| Helm | Renders with `helm template` and applies itself | HelmRelease runs real Helm installs with release history |
| Multi-tenancy | AppProject plus its own RBAC and SSO | Kubernetes RBAC and namespaces; impersonation per Kustomization |
| Image automation | Separate Image Updater project | Built in: ImageRepository, ImagePolicy, ImageUpdateAutomation |
| UI | Yes, with sync and diff views | None; CLI and third-party dashboards |
| Pick when | Many teams need self-service and a visual diff | Platform engineers want a Kubernetes-native, headless tool |

### Progressive delivery with Argo Rollouts

A rolling update only checks readiness probes. Progressive delivery sends a small share of real traffic to the new version, measures it, and advances or aborts on the numbers. Argo Rollouts does this with a Rollout resource that replaces Deployment (same pod template, a different `strategy`).

```
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: api
  namespace: shop
spec:
  replicas: 10
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: 123456789012.dkr.ecr.ap-south-1.amazonaws.com/api@sha256:2222222222222222222222222222222222222222222222222222222222222222
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
  strategy:
    canary:
      canaryService: api-canary        # two Services you create; the controller patches their selectors
      stableService: api-stable
      trafficRouting:
        alb:
          ingress: api                  # an Ingress whose backend is api-stable with port name use-annotation
          servicePort: 80               # the controller writes a weighted actions annotation on it
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 1
        args:
          - name: service
            value: api-canary
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 25
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 10m}
        - pause: {}                      # wait for a human: kubectl argo rollouts promote api
```

```
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: shop
spec:
  args:
    - name: service
  metrics:
    - name: success-rate
      interval: 1m
      failureLimit: 3                  # three failed measurements are tolerated; the fourth aborts the rollout
      successCondition: result[0] >= 0.99
      provider:
        prometheus:
          address: https://prometheus.monitoring.svc:9090
          query: |
            sum(rate(http_requests_total{service="{{args.service}}", code!~"5.."}[2m]))
            /
            sum(rate(http_requests_total{service="{{args.service}}"}[2m]))
```

Without `trafficRouting`, the controller approximates the percentage with pod counts (1 canary pod of 10 is 10 percent). With `trafficRouting` through the AWS Load Balancer Controller (the Rollout controller writes an `alb.ingress.kubernetes.io/actions.api-stable` annotation and the ALB splits traffic between the `api-stable` and `api-canary` target groups), Istio or Gateway API, the stable set stays at full size and the proxy splits requests exactly. `failureLimit` is the number of failed measurements tolerated, so `failureLimit: 3` aborts on the fourth failure. A failed analysis aborts the rollout, sets the canary weight to 0 and marks it Degraded; a fixed commit starts a new rollout.

Blue-green is the other strategy: `activeService` and `previewService`, the new ReplicaSet comes up at full size behind preview, `prePromotionAnalysis` runs on it, and promotion (manual with `autoPromotionEnabled: false`, or after `autoPromotionSeconds`) switches the active Service's selector to the new hash. The old set stays for `scaleDownDelaySeconds` (default 30) so an instant switch back is possible. Flagger, from the Flux family, does the same job with a Canary resource wrapping a normal Deployment.

Argo CD syncs the Rollout from Git and reports Progressing while the canary runs, Degraded if the analysis fails.

### When Argo CD is down: break-glass

Argo CD being down does not take workloads down; it only stops changes. For a change that cannot wait:

1. Declare it in the incident channel and name the person applying.
2. Make the change in Git first, on a branch, so the intended state exists.
3. Apply it by hand from that branch with `kubectl apply -k envs/prod/api` or `helm template ... | kubectl apply -f -`, using a break-glass IAM role whose use is logged to CloudTrail and alerts the platform team.
4. Merge the branch. When Argo CD returns it finds the cluster already matches Git and reports Synced; if the manual change differed, self-heal corrects it to Git, which is what you want.
5. Write the postmortem item: why Argo CD was down and why the change could not wait.

Git first, then cluster, so self-heal cannot undo the fix.

## Diagram

Rendering diagram…

## Worked example

**A canary that fails analysis, with the blast radius in numbers.** The shop API serves 2,000 requests per second with 10 replicas. The Rollout above runs steps 10 percent for 5 minutes, 25 percent for 5 minutes, 50 percent for 10 minutes, then a manual promote. Analysis starts at step 1 and measures success rate every minute; `failureLimit: 3` tolerates three failed measurements, so the fourth aborts.

A new image has a bug that returns HTTP 500 for 3 percent of requests.

Step 1 (minute 0 to 5): weight 10. The canary receives 2,000 x 0.10 = 200 requests per second. Over 5 minutes that would be 200 x 300 = 60,000 requests. The success rate measured each minute is 0.97, below the 0.99 condition, so measurements at minutes 1, 2, 3 and 4 fail. The fourth failure passes `failureLimit: 3` at minute 4.

That is faster than the step: the rollout aborts during step 1, not after it. The canary weight goes back to 0 at minute 4, the ALB action annotation sends 100 percent to `api-stable`, and the Rollout is Degraded. Total exposure: 200 x 240 = 48,000 requests to the canary, of which 3 percent, 1,440, failed.

Compare with a plain Deployment rolling update at `maxSurge: 25%`: within about 2 minutes all 10 pods are new and every request hits the bug. In 4 minutes that is 2,000 x 240 = 480,000 requests and 14,400 errors, ten times more, and nothing stops it until a human notices a dashboard.

Put it against the error budget. At 99.9 percent monthly availability and 2,000 rps, the monthly request count is 2,000 x 30 x 86,400 = 5,184,000,000 and the budget is 0.1 percent of that, 5,184,000 failed requests. The canary spent 1,440 of them, 0.03 percent of the budget. The plain rollout spent 14,400, and it would keep spending until rolled back.

What happens next in GitOps terms: Argo CD shows the Application Synced (Git and cluster agree on the Rollout spec) but Degraded (the Rollout reports the abort). The notifications controller fires `on-health-degraded` to the team's Slack channel. The developer opens a fix, CI pushes a new digest, the GitOps PR is merged, and the next Rollout starts at weight 10 again. No revert is needed because the canary never became stable; if the bug had been found after promotion, the fix would be `git revert` of the promotion commit, and Argo CD would roll the stable set back through the same canary steps unless the Rollout's steps are skipped with `kubectl argo rollouts promote --full`.

## Runnable code

Python · runs and prints its own checks

```
"""A toy Argo CD application controller, to make the reconciliation loop concrete.

No network, no cluster. A 'Git repo' is a dict of commits, each holding the
desired manifests for an Application. A 'cluster' is a dict of live objects
keyed by (kind, namespace, name). Each reconcile cycle does what the real
application controller does:

  1. check the Application against its AppProject (sources and destinations)
  2. render desired state from the commit at targetRevision
  3. compare desired with live, object by object: Synced or OutOfSync
  4. if sync is automated: apply the diff, prune extras (prune: true),
     and overwrite manual edits (selfHeal: true)

Run it and read the cycle log. The asserts at the end are the self-checks.
"""
import copy

# ---------- the fake world ----------

def manifest(kind, name, namespace, **spec):
    return {"kind": kind, "metadata": {"name": name, "namespace": namespace}, "spec": spec}

def key(obj):
    return (obj["kind"], obj["metadata"]["namespace"], obj["metadata"]["name"])

# A GitOps repo: commit sha -> list of manifests under apps/shop/
GIT = {
    "a1f2c3": [
        manifest("Deployment", "api", "shop", image="api@sha256:1111", replicas=3),
        manifest("Service", "api", "shop", port=80, targetPort=8080),
        manifest("ConfigMap", "api-config", "shop", data={"LOG_LEVEL": "info"}),
    ],
    # CI committed a new digest and someone deleted the ConfigMap in the same PR
    "b7e9d0": [
        manifest("Deployment", "api", "shop", image="api@sha256:2222", replicas=3),
        manifest("Service", "api", "shop", port=80, targetPort=8080),
    ],
}

# Fields that a controller in the cluster is allowed to change; Argo CD
# ignores them when diffing (spec.ignoreDifferences in the real Application).
IGNORE = {("Deployment", "spec", "replicas")}

# ---------- AppProject and Application ----------

PROJECTS = {
    "shop-team": {
        "sourceRepos": ["https://github.com/example/gitops"],
        "destinations": [{"server": "https://kubernetes.default.svc", "namespace": "shop"}],
    }
}

def project_allows(app):
    """Argo CD refuses to sync an app whose source or destination is outside its project."""
    proj = PROJECTS[app["project"]]
    if app["source"]["repoURL"] not in proj["sourceRepos"]:
        return False, f"repo {app['source']['repoURL']} not in project sourceRepos"
    for d in proj["destinations"]:
        if d["server"] == app["destination"]["server"] and d["namespace"] in ("*", app["destination"]["namespace"]):
            return True, ""
    return False, f"namespace {app['destination']['namespace']} is not a permitted destination of project {app['project']}"

def desired_state(app):
    """What the repo-server does: render the manifests at targetRevision."""
    return {key(m): copy.deepcopy(m) for m in GIT[app["source"]["targetRevision"]]}

# ---------- the controller ----------

def strip_ignored(obj):
    """Drop bookkeeping keys and ignored fields before comparing, like Argo CD's diff normaliser."""
    o = {k: copy.deepcopy(v) for k, v in obj.items() if not k.startswith("_")}
    for kind, section, field in IGNORE:
        if o["kind"] == kind:
            o.get(section, {}).pop(field, None)
    return o

def diff(desired, live, namespace):
    """Return (status, to_apply, to_prune). Only objects in the app's namespace count."""
    to_apply, to_prune = [], []
    for k, want in desired.items():
        have = live.get(k)
        if have is None or strip_ignored(have) != strip_ignored(want):
            to_apply.append(k)
    for k, have in live.items():
        if k[1] == namespace and k not in desired and have.get("_managed_by") == "argocd":
            to_prune.append(k)
    status = "Synced" if not to_apply and not to_prune else "OutOfSync"
    return status, to_apply, to_prune

def reconcile(cycle, app, live):
    print(f"\n=== cycle {cycle}: app={app['name']} revision={app['source']['targetRevision']} ===")
    ok, why = project_allows(app)
    if not ok:
        print(f"  REFUSED by AppProject: {why}")
        return "Unknown"
    desired = desired_state(app)
    status, to_apply, to_prune = diff(desired, live, app["destination"]["namespace"])
    print(f"  compare: {len(desired)} desired, {sum(1 for k in live if k[1] == app['destination']['namespace'])} live in ns -> {status}")
    for k in to_apply:
        reason = "missing" if k not in live else "differs"
        print(f"    OutOfSync {k[0]}/{k[2]}: {reason}")
    for k in to_prune:
        print(f"    extra     {k[0]}/{k[2]}: in cluster, not in Git")
    auto = app["syncPolicy"].get("automated")
    if status == "OutOfSync" and auto:
        for k in to_apply:
            if k in live and not auto.get("selfHeal") and live[k].get("_edited_by_hand"):
                print(f"    skip      {k[0]}/{k[2]}: drifted by hand, selfHeal is false")
                continue
            obj = copy.deepcopy(desired[k])
            obj["_managed_by"] = "argocd"
            # keep the live value of ignored fields (the HPA owns replicas)
            if k in live:
                for kind, section, field in IGNORE:
                    if k[0] == kind and field in live[k].get(section, {}):
                        obj[section][field] = live[k][section][field]
            live[k] = obj
            print(f"    apply     {k[0]}/{k[2]}")
        for k in to_prune:
            if auto.get("prune"):
                del live[k]
                print(f"    prune     {k[0]}/{k[2]}")
            else:
                print(f"    keep      {k[0]}/{k[2]}: prune is false, stays OutOfSync")
        status, _, _ = diff(desired, live, app["destination"]["namespace"])
        print(f"  after sync: {status}")
    return status

def kubectl_edit(live, kind, ns, name, **changes):
    """Someone with cluster access changes a field directly: drift."""
    obj = live[(kind, ns, name)]
    obj["spec"].update(changes)
    obj["_edited_by_hand"] = True
    print(f"\n  [kubectl edit] {kind}/{name}: {changes}")

if __name__ == "__main__":
    app = {
        "name": "shop-api",
        "project": "shop-team",
        "source": {"repoURL": "https://github.com/example/gitops", "path": "apps/shop", "targetRevision": "a1f2c3"},
        "destination": {"server": "https://kubernetes.default.svc", "namespace": "shop"},
        "syncPolicy": {"automated": {"prune": True, "selfHeal": True}},
    }
    cluster = {}

    # 1. first sync: everything is missing, everything is applied
    s = reconcile(1, app, cluster)
    assert s == "Synced" and len(cluster) == 3

    # 2. nothing changed: a no-op cycle (this runs every 3 minutes by default)
    s = reconcile(2, app, cluster)
    assert s == "Synced"

    # 3. the HPA scales replicas 3 -> 6: ignored field, still Synced
    cluster[("Deployment", "shop", "api")]["spec"]["replicas"] = 6
    s = reconcile(3, app, cluster)
    assert s == "Synced", "replicas is in ignoreDifferences, the HPA owns it"

    # 4. someone kubectl-edits the image to a hotfix: drift, self-heal puts Git back
    kubectl_edit(cluster, "Deployment", "shop", "api", image="api@sha256:hotfix")
    s = reconcile(4, app, cluster)
    assert s == "Synced" and cluster[("Deployment", "shop", "api")]["spec"]["image"] == "api@sha256:1111"
    assert cluster[("Deployment", "shop", "api")]["spec"]["replicas"] == 6, "self-heal must not reset the HPA's replicas"

    # 5. new commit: CI bumped the digest and the ConfigMap was removed -> apply + prune
    app["source"]["targetRevision"] = "b7e9d0"
    s = reconcile(5, app, cluster)
    assert s == "Synced"
    assert cluster[("Deployment", "shop", "api")]["spec"]["image"] == "api@sha256:2222"
    assert ("ConfigMap", "shop", "api-config") not in cluster, "prune: true removed it"

    # 6. rollback the GitOps way: git revert = point at the old commit again
    app["source"]["targetRevision"] = "a1f2c3"
    s = reconcile(6, app, cluster)
    assert s == "Synced" and ("ConfigMap", "shop", "api-config") in cluster

    # 7. a team tries to deploy into kube-system through the same project: refused
    bad = copy.deepcopy(app)
    bad["name"] = "shop-sneaky"
    bad["destination"]["namespace"] = "kube-system"
    s = reconcile(7, bad, cluster)
    assert s == "Unknown" and not any(k[1] == "kube-system" for k in cluster)

    # 8. same drift without selfHeal: Argo reports OutOfSync but does not touch it
    app["syncPolicy"]["automated"]["selfHeal"] = False
    kubectl_edit(cluster, "Deployment", "shop", "api", image="api@sha256:hotfix")
    s = reconcile(8, app, cluster)
    assert s == "OutOfSync" and cluster[("Deployment", "shop", "api")]["spec"]["image"] == "api@sha256:hotfix"

    print("\nself-check OK: synced, ignored HPA replicas, self-healed drift, applied+pruned a new commit,"
          " rolled back by revision, refused a bad destination, and left drift alone without selfHeal")
```

## Key takeaways

* GitOps is four principles: declarative, versioned and immutable, pulled automatically, continuously reconciled. The last two separate it from CI running kubectl.
* Pull is safer than push because cluster credentials never leave the cluster; CI only pushes images and commits.
* An Application has a sync status (Git vs cluster) and a health status (are the objects working); Synced and Degraded can be true at once.
* `automated` with `prune: true` and `selfHeal: true` is the production setting; `ignoreDifferences` keeps fields that controllers own, such as HPA replicas, from showing as drift.
* AppProject is the tenancy boundary: allowed repos, clusters, namespaces, kinds, sync windows and roles.
* CI pushes by digest and commits the digest to the GitOps repo; promotion is a pull request; rollback is `git revert`, never kubectl.
* Secrets never sit in Git: an ExternalSecret in the repo, the value in AWS Secrets Manager, ESO in between.
* Argo Rollouts turns a release into measured steps: setWeight, pause, Prometheus analysis, abort on failure; the blast radius is the canary's share of traffic for the time until one more failure than failureLimit.

## Common mistakes

* Saying "rollback with kubectl rollout undo" in a GitOps setup: self-heal reverts it within minutes; the fix is a revert commit.
* Enabling self-heal without `ignoreDifferences` for HPA-managed replicas, so Argo CD and the HPA fight each other on every poll.
* One branch per environment in the GitOps repo, which makes promotion a merge that drags unrelated changes along.
* Giving every team the `default` AppProject, which allows any repo, any cluster and any namespace.
* Committing a base64 Secret because "it looks encrypted". It is encoding; use External Secrets.
* Treating a Synced application as a successful deploy without looking at health, so a crash-looping canary goes unnoticed.

## Practice

* Install Argo CD on a kind cluster, create an AppProject limited to one namespace, and an Application in it that points at a folder in a public fork of your own. Prove with `argocd app get` that pointing the destination at kube-system is refused.
* Enable automated sync with selfHeal, run `kubectl scale deployment api --replicas=5`, and time how long until Argo CD puts it back. Then add ignoreDifferences for /spec/replicas and show the scale now sticks.
* Write a GitHub Actions workflow that builds an image, pushes to a local registry by digest, and opens a pull request on your GitOps repo changing one values line. Merge it and watch the Application go OutOfSync then Synced.
* Install Argo Rollouts, convert the Deployment to a Rollout with steps 20, pause 1m, 50, pause, and an AnalysisTemplate against a local Prometheus. Deploy an image that returns 500 for 5 percent of requests and record at which minute the rollout aborts.

## Interview questions (11)

1.What is GitOps, and how is it different from a CI pipeline that runs kubectl apply?Easy

GitOps is defined by four principles from the OpenGitOps project: the desired state is declarative, it is stored versioned and immutable, usually in Git, agents pull it automatically, and they continuously reconcile the live system toward it. A pipeline that runs kubectl apply satisfies the first two: YAML in Git, applied on merge. It fails the last two. The pipeline pushes with credentials it holds, and after it finishes nothing watches the cluster, so a manual edit or a deleted object stays until the next run. With Argo CD inside the cluster, the agent pulls on a schedule or webhook, detects drift within seconds through the Kubernetes watch API, and either reports or reverts it. The practical difference shows up on the day someone kubectl-edits production.

2.Why is pull-based deployment safer than push-based?Easy

In a push model the CI system holds a kubeconfig or an IAM role with write access to every cluster it deploys to, and it is reachable from the internet because it runs on pull requests. A compromised runner or a leaked secret is admin on production. In a pull model nothing outside the cluster has cluster credentials. Argo CD runs inside with a ServiceAccount, makes only outbound HTTPS connections to Git and the registry, and the API server endpoint can stay private. The most a compromised CI runner can do is push an image and open a commit, both of which are reviewed and logged. The second benefit is that a new cluster is bootstrapped by pointing it at the same repository, with no pipeline re-runs.

3.Walk me through how a merged pull request ends up running in production.Medium

The developer merges to the app repo. GitHub Actions builds the image, scans it, pushes it to ECR and reads the digest back. The workflow then checks out the GitOps repo and changes one line in the staging values file, the image digest, and opens a pull request that auto-merges for staging. Argo CD receives the webhook, the repo server renders the chart with the new values, the application controller sees the Deployment is OutOfSync and applies it, and the health check turns Healthy once the rollout completes. Promotion to prod is a second pull request copying the digest into the prod values file, which a human approves, possibly after an automated soak time. Argo CD syncs prod the same way, and if the service uses Argo Rollouts the sync starts a canary rather than a plain rolling update. At no point does CI talk to the cluster.

4.An Application shows Synced but Degraded. What does that mean and what do you do?Medium

Synced means the rendered manifests in Git match the live objects, so Argo CD did its job. Degraded is health, which is read from the objects themselves: a Deployment with a crash-looping new ReplicaSet, a Rollout whose analysis failed, a PVC that cannot bind. So the deploy happened and the thing deployed is not working. I open the Application, find the resource that is Degraded, and read its events and pod logs exactly as I would with kubectl. If the cause is the new version, the fix is a revert commit in the GitOps repo, after which Argo CD syncs the previous digest. If it is an environmental problem, say a Secret that External Secrets could not fetch, I fix that source. What I do not do is edit the object in the cluster, because self-heal would undo it.

5.Someone ran kubectl edit on a production Deployment. What happens with Argo CD, and how do you design around legitimate changes by controllers?Medium

The application controller watches the Kubernetes API, so within seconds the live object differs from the rendered manifest and the Application goes OutOfSync. With selfHeal enabled it re-applies the Git version after the self-heal timeout, 5 seconds by default, and the manual change disappears; without selfHeal it stays OutOfSync and shows the diff until someone syncs. The design problem is fields that are supposed to change outside Git: replicas owned by an HPA, a caBundle injected by cert-manager, a sidecar added by a mutating webhook. Those go into ignoreDifferences on the Application, with jsonPointers such as /spec/replicas or a jqPathExpression for injected containers, plus the RespectIgnoreDifferences sync option so a sync does not overwrite them. Then self-heal corrects humans and leaves controllers alone.

6.How do you run Argo CD for 50 teams on shared clusters without one team breaking another?Hard

One AppProject per team is the boundary. It lists the team's repositories in sourceRepos, their namespaces in destinations, an empty clusterResourceWhitelist so they cannot create ClusterRoles or CRDs, and a namespaceResourceBlacklist for ResourceQuota and NetworkPolicy, which the platform owns. An Application outside those limits is refused before any sync. Applications are generated by an ApplicationSet with a git directory generator over each team's folder, so teams add services by adding folders and never write Application objects, which would otherwise need admin rights. RBAC in argocd-rbac-cm maps each team's SSO group to a role that can sync and view only its own project, with policy.default set to readonly. Sync windows deny automated prod syncs over the weekend with manualSync for emergencies. Notifications route a team's failures to that team's channel. The platform team's own apps, ingress and cert-manager and External Secrets, sit in a separate project that only they can merge to.

7.How do you handle secrets in a GitOps repository?Medium

Nothing secret goes in the repository, not even base64. On EKS I use the External Secrets Operator: the repo holds an ExternalSecret that names an entry in AWS Secrets Manager and the Kubernetes Secret to create, and ESO, authenticated with Pod Identity or IRSA, fetches the value and refreshes it on an interval. The secret then has one source of truth with IAM audit, rotation is a Secrets Manager feature, and the GitOps repo is safe to make public. The alternatives are SOPS, which encrypts values in the repo with a KMS key and needs a decrypt plugin in the Argo CD repo server, and Sealed Secrets, which encrypts for one cluster's key. Both keep encrypted secrets in Git, which is acceptable, but rotation and multi-cluster are harder than with ESO.

8.How does a canary release with Argo Rollouts decide whether to continue?Medium

The Rollout replaces the Deployment and lists steps: setWeight 10, pause 5 minutes, setWeight 25, and so on. With traffic routing through the AWS Load Balancer Controller, Istio or Gateway API, the controller writes the weight into the Ingress or route so the proxy splits requests exactly; without it, the weight is approximated by pod counts. An AnalysisTemplate runs in the background from a chosen step: every interval it runs a Prometheus query, such as the ratio of non-5xx to all requests for the canary service, and checks a successCondition like result[0] >= 0.99. failureLimit is the number of failed measurements tolerated; one more than that aborts the rollout, the weight goes back to 0 and the Rollout is Degraded. An indefinite pause step waits for a human to run kubectl argo rollouts promote. Argo CD syncs the Rollout from Git and reports its health, so a failed canary shows up as Synced and Degraded.

9.Argo CD is down and a critical fix must go to production now. What do you do?Hard

First, Argo CD being down does not affect running workloads, so I confirm the change truly cannot wait. If it cannot, I follow the break-glass procedure: announce it in the incident channel, make the change in Git on a branch first so the intended state exists, then apply that exact rendered state by hand with kubectl apply from the branch, using a break-glass IAM role whose use raises an alert and is in CloudTrail. Then I merge the branch. When Argo CD recovers it compares Git with the cluster, finds them equal and reports Synced, or finds a small difference and self-heals to Git, which is correct because Git is what I reviewed. The order matters: cluster first and Git later would let self-heal undo the fix. The postmortem covers why Argo CD was down and why the change could not wait.

10.Argo CD or Flux: how would you choose?Easy

Both are CNCF graduated and implement the same four principles. Argo CD gives you Application objects, a UI with visual diffs, its own API server with SSO and RBAC, and AppProjects for multi-tenancy, which is why platform teams serving many product teams usually pick it: self-service through a UI matters. Flux is a set of controllers driven by CRDs, GitRepository, Kustomization and HelmRelease, with no UI; it runs real Helm installs with release history and has image automation built in. Teams of platform engineers who want a Kubernetes-native, headless tool and are comfortable with kubectl pick Flux. Flagger, from the same family, provides canaries for Flux the way Argo Rollouts does for Argo CD. The wrong answer is to pick based on popularity alone; the right one names the tenancy and UI needs.

11.What is an ApplicationSet and when would you use the pull request generator?Medium

An ApplicationSet is a template for Applications plus a generator that produces the parameters. The git directory generator makes one Application per folder, the cluster generator one per registered cluster filtered by labels, the list generator a fixed set, and matrix combines two. The pull request generator queries GitHub or GitLab for open pull requests on a repository and creates an Application for each, with the branch name and PR number available in the template, so every PR gets its own preview environment in its own namespace, and when the PR closes the Application is deleted and its resources pruned. That gives reviewers a running copy of the change without anyone writing manifests, which is the kind of self-service a platform team is measured on.

## Quiz

1.Which pair of principles distinguishes GitOps from "CI runs kubectl apply on merge"?

2.An Application has automated sync with prune false and selfHeal false. A Deployment is deleted from Git. What happens?

3.Where does rollback happen in a GitOps workflow?

4.What does ignoreDifferences on /spec/replicas achieve?

5.In an Argo Rollouts canary with failureLimit 3 and a 1 minute interval, when does a bad version get aborted?

6.Which component of Argo CD renders Helm charts and Kustomize overlays into manifests?

## Practice these problems

* [DESIGNZero-downtime deployment system with canary analysis and rollbackHard](/devops/problems/zero-downtime-deploys)
* [DESIGNProduction EKS cluster for a 30-engineer startupHard](/devops/problems/eks-cluster-platform)
* [DESIGNSecrets management across CI, Kubernetes and runtimeMedium](/devops/problems/secrets-management)
* [DESIGNGitOps deployment platform with Argo CD for 50 teamsHard](/devops/problems/gitops-platform-argocd)
* [CODEGitHub Actions: build, test, cache, push an image and deployMedium](/devops/problems/github-actions-build-push-deploy)

## Further reading

* [OpenGitOps principlesGuideopengitops.dev](https://opengitops.dev/)
* [Argo CD documentationGuideargo-cd.readthedocs.io](https://argo-cd.readthedocs.io/en/stable/)
* [Argo Rollouts documentationGuideargo-rollouts.readthedocs.io](https://argo-rollouts.readthedocs.io/en/stable/)
* [External Secrets Operator documentationGuideexternal-secrets.io](https://external-secrets.io/latest/)
* [Continuous Deployment at Facebook and OANDAPaperresearch.facebook.com](https://research.facebook.com/publications/continuous-deployment-at-facebook-and-oanda/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousHelm - charts, templates, values and releases](/devops/learn/helm-charts)[NextObservability - Prometheus, Grafana, OpenTelemetry, logs and alerting](/devops/learn/observability-prometheus-grafana-otel)

## On this page

1. [Lesson](#lesson)
2. [Diagram](#diagram)
3. [Worked example](#example)
4. [Code](#code)
5. [Key takeaways](#takeaways)
6. [Common mistakes](#mistakes)
7. [Practice](#practice)
8. [Interview questions](#interview)
9. [Quiz](#quiz)
10. [Related problems](#problems)
11. [Further reading](#reading)
12. [My notes](#notes)

## In this lesson

1. [What GitOps is](#what-gitops-is)
2. [Push versus pull](#push-versus-pull)
3. [Argo CD architecture](#argo-cd-architecture)
4. [The Application resource](#the-application-resource)
5. [AppProject: limits for teams](#appproject-limits-for-teams)
6. [Many apps: app-of-apps and ApplicationSets](#many-apps-app-of-apps-and-applicationsets)
7. [Sync waves, hooks, health and diffs](#sync-waves-hooks-health-and-diffs)
8. [RBAC, SSO and notifications](#rbac-sso-and-notifications)
9. [From CI to the cluster](#from-ci-to-the-cluster)
10. [Repository layout and promotion](#repository-layout-and-promotion)
11. [Rollback the GitOps way](#rollback-the-gitops-way)
12. [Secrets in a GitOps repo](#secrets-in-a-gitops-repo)
13. [Flux: the other CNCF option](#flux-the-other-cncf-option)
14. [Progressive delivery with Argo Rollouts](#progressive-delivery-with-argo-rollouts)
15. [When Argo CD is down: break-glass](#when-argo-cd-is-down-break-glass)
