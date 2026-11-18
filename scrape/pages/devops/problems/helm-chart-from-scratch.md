# Helm chart from scratch with values, templates and a test — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/helm-chart-from-scratch

[DevOps problems](/devops#problems)

CODEImplement it#40Medium

# Helm chart from scratch with values, templates and a test

helmkubernetestemplatespackagingociecrReported at Infosys, Wipro, TCS

## Problem statement

Package the orders-api web service (port 8080, config from a ConfigMap, secrets from an External Secrets Operator Secret, TLS through cert-manager) as a Helm chart that a platform team can install in dev, staging and prod from one set of templates. The chart must default the image tag to `appVersion`, restart pods when the ConfigMap changes, put Ingress, HPA and PDB behind flags, keep the Deployment selector stable across releases, validate values with a JSON schema, print useful NOTES, ship a `helm test` pod, and be pushed to Amazon ECR as an OCI artifact.

## Requirements

### Functional

* `Chart.yaml`, `values.yaml` with documented defaults, a `values-prod.yaml` example and a `values.schema.json` that rejects a missing image repository or `existingSecret`.
* `templates/_helpers.tpl` with `name`, `fullname`, `chart`, `labels`, `selectorLabels` and `serviceAccountName` helpers used by every template through `include` and `nindent`.
* `templates/deployment.yaml` with a `checksum/config` annotation, resources, three probes, pod and container security context and the preStop sleep, all driven by values.
* `templates/service.yaml`, `templates/ingress.yaml` (flag), `templates/hpa.yaml` (flag, and then no `replicas` in the Deployment), `templates/pdb.yaml` (flag), `templates/serviceaccount.yaml` with annotations.
* `templates/NOTES.txt` and `templates/tests/test-connection.yaml` that `helm test` runs against the readiness path.

### Non-functional

* `helm lint --strict` and `helm template` with both values files produce 0 errors and 0 warnings.
* A config-only change (`LOG_LEVEL` info to warn) triggers a rolling restart with `maxUnavailable: 0`, so 0 requests fail.
* `helm upgrade --install ... --wait --rollback-on-failure --timeout 5m` returns to the previous release within 5 minutes when the new pods never become ready.
* Rendered names fit the 63-character DNS label limit for any release name up to 40 characters.
* Chart version bumps follow SemVer independently of the app version; `helm history` shows both for every revision.

## API

```
# Local test loop (Helm 4)
helm lint ./orders-api --strict -f values-prod.yaml
helm template orders-api ./orders-api -n orders -f values-prod.yaml > rendered.yaml
kubeconform -strict rendered.yaml                       # schema check of the rendered output
helm template orders-api ./orders-api --show-only templates/deployment.yaml
helm install orders-api ./orders-api -n orders --dry-run=server -f values-prod.yaml

# Install / upgrade / test / roll back
helm upgrade --install orders-api ./orders-api -n orders --create-namespace \
  -f values-prod.yaml --wait --rollback-on-failure --timeout 5m
helm test orders-api -n orders            # runs templates/tests/, pod deleted on success
helm history orders-api -n orders         # revision, chart version, app version, status
helm rollback orders-api 3 -n orders

# Package and push to ECR as OCI
helm package ./orders-api                 # -> orders-api-1.3.0.tgz (name and version from Chart.yaml)
aws ecr get-login-password --region ap-south-1 | helm registry login --username AWS \
  --password-stdin 111122223333.dkr.ecr.ap-south-1.amazonaws.com
helm push orders-api-1.3.0.tgz oci://111122223333.dkr.ecr.ap-south-1.amazonaws.com/charts
helm install orders-api oci://111122223333.dkr.ecr.ap-south-1.amazonaws.com/charts/orders-api --version 1.3.0

# Value overrides at install time
--set image.tag=2.4.2            # overrides the appVersion default
--set autoscaling.enabled=true   # renders the HPA and removes spec.replicas
```

## Data model

```
orders-api/
  Chart.yaml            version 1.3.0 (chart), appVersion "2.4.1" (image tag default)
  values.yaml           defaults; values.schema.json validates them on lint, template, install, upgrade
  values-prod.yaml      overrides merged on top with -f
  templates/
    _helpers.tpl        define: name, fullname, chart, labels, selectorLabels, serviceAccountName
    configmap.yaml      data from .Values.config  --sha256sum-->  Deployment pod annotation
    serviceaccount.yaml if .Values.serviceAccount.create; annotations from values (IRSA)
    deployment.yaml     selector = selectorLabels (immutable); labels = labels (may change)
    service.yaml        selector = selectorLabels; port .Values.service.port -> targetPort http
    ingress.yaml        if .Values.ingress.enabled; backend = fullname : service.port
    hpa.yaml            if .Values.autoscaling.enabled; scaleTargetRef = fullname
    pdb.yaml            if .Values.podDisruptionBudget.enabled; selector = selectorLabels
    NOTES.txt           printed after install; rendered with the same values
    tests/test-connection.yaml   helm.sh/hook: test; wget fullname:port/readyz

Render context (.) = { Values, Chart, Release{Name, Namespace, Service}, Capabilities, Template }
$ is the root context; needed inside range and with blocks.
```

## Approach

1. `Chart.yaml`: `apiVersion: v2`, `version` for the chart, `appVersion` quoted, `kubeVersion` constraint so an old cluster fails at install, not at runtime.
2. `values.yaml` holds production-safe defaults with a comment per block. Every toggle is a boolean under its own key (`ingress.enabled`, `autoscaling.enabled`, `podDisruptionBudget.enabled`). `image.tag` is empty on purpose.
3. `_helpers.tpl` defines the names once. `fullname` is `<release>-<chart>` truncated to 63 and stripped of a trailing hyphen. `selectorLabels` has only name and instance; `labels` adds chart, version and managed-by.
4. `configmap.yaml` ranges over `.Values.config` and quotes every value, so a number in values does not become an integer in the ConfigMap, where only strings are allowed.
5. `deployment.yaml`: `replicas` only when autoscaling is off; `checksum/config` from `include (print $.Template.BasePath "/configmap.yaml") . | sha256sum`; image `repository:tag | default .Chart.AppVersion`; `required` on `existingSecret`; `toYaml | nindent` for resources and security contexts; probes from values; the preStop sleep.
6. `service.yaml` and `ingress.yaml` join on `fullname` and `service.port`. Inside the Ingress `range`, `$` reaches the root for `include` and `.Values`.
7. `hpa.yaml` targets the Deployment by `fullname` with the same scale-down policy as the raw manifests. `pdb.yaml` adds `unhealthyPodEvictionPolicy`.
8. `NOTES.txt` prints the rollout command, the URL when the Ingress is on and a port-forward otherwise, and the test command.
9. `tests/test-connection.yaml`: a busybox pod with the `helm.sh/hook: test` annotation that fetches the readiness path through the Service and is deleted on success.
10. `values.schema.json` makes `image.repository`, `existingSecret` and `containerPort` required with types and ranges; Helm applies it on lint, template, install and upgrade.
11. Test loop: `helm lint --strict`, `helm template` piped to kubeconform, `--dry-run=server`, then `helm upgrade --install --wait --rollback-on-failure` and `helm test` on a kind cluster; chart-testing (`ct lint`, `ct install`) does the same in CI for every changed chart.
12. Release: `helm package`, `helm registry login` with an ECR token, `helm push` to `oci://.../charts`; consumers pin `--version`.

## Architecture diagram

Rendering diagram…

## Deep dives

### helm template and helm lint as the test loop

`helm lint --strict` loads the chart, applies `values.schema.json`, renders every template and reports YAML that does not parse, plus warnings such as a missing icon; `--strict` makes warnings fail. It does not know Kubernetes schemas, so the second step is `helm template ... | kubeconform -strict`, which catches a wrong field name in a probe or an HPA. `--show-only templates/deployment.yaml` prints one file when debugging indentation. `--dry-run=server` sends the rendered objects to the API server so admission webhooks and Pod Security run. Run the loop with every values file, because a template that renders with defaults can fail with `ingress.enabled=true`. In CI, chart-testing lints and installs only the charts whose version changed, which enforces the version bump.

### nindent and whitespace

Helm templates are text, not YAML, until the end. `include "orders-api.labels" .` returns a multi-line string with no indentation; `nindent 4` adds a newline and four spaces before every line, so the result lands under `labels:` at the right depth. `indent` without the leading newline forces you to write `{{ include ... | indent 4 }}` on the same line as the key, which reads badly. `{{-` eats the whitespace and the newline to its left, `-}}` to its right. A missing dash leaves a blank line inside a list, which YAML tolerates, while an extra `-}}` can glue two keys onto one line, which it does not. The rule: `{{-` on the left of every control statement, `nindent` for every block, and never `-}}` unless you know what follows.

### The checksum annotation

A Deployment only rolls when its pod template changes, and a ConfigMap is not part of the template. The annotation `checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}` renders the ConfigMap template and hashes the result into the pod template; any change to `.Values.config` changes the hash, the template, and so the pods. The cost is that an unrelated chart-wide change to the ConfigMap template also restarts pods, which is usually what you want. Secrets from External Secrets are outside the chart, so their rotation needs the operator's reloader annotation or a restart in the app.

### Immutable selector labels

`spec.selector` on a Deployment cannot be changed after creation; an upgrade that adds `app.kubernetes.io/version` to it fails with "field is immutable". That is why the chart has two helpers: `selectorLabels` (name and instance, stable across releases) and `labels` (plus chart and version, which change every release). The selector, the Service selector and the PDB selector use the first; metadata uses the second.

### Chart version against app version, and OCI on ECR

`version` is the chart's SemVer and changes when a template or default changes. `appVersion` is the image tag and changes when the app ships. A fix to the Ingress template is chart 1.3.1 with the same appVersion; a new app build is appVersion 2.4.2 with the chart version bumped too, because Chart.yaml changed. `helm package` names the file from both fields, and `helm push` sends it to `oci://<account>.dkr.ecr.<region>.amazonaws.com/charts`, where the ECR repository `charts/orders-api` must exist and the tag is the chart version. The push reference must not contain the chart name or a tag; install and pull references do. The same ECR token login works for images and charts, which is why teams keep both in one registry.

## Evaluation

**Static checks.** `helm lint --strict` with `values.yaml` and with `values-prod.yaml`; `helm template` for both, piped to `kubeconform -strict`; a `values.schema.json` negative test: `--set existingSecret=""` must fail with the schema message and `--set image.repository=""` likewise. `helm template --show-only templates/deployment.yaml` with `autoscaling.enabled=true` must not contain `replicas:`.

**Behaviour tests on kind.** Install with `--wait`; `helm test` must pass. Change `config.LOG_LEVEL` and upgrade: `kubectl get pods -w` shows a rolling restart and the `checksum/config` annotation differs between the two ReplicaSets. Change only `image.tag` and confirm `helm history` records the new app version. Set `probes.readiness.path=/nope` and upgrade with `--rollback-on-failure --timeout 2m`: the release must return to the previous revision with status "deployed" and the old pods still serving. Rename the release and confirm names stay under 63 characters.

**Edge cases.** `fullnameOverride` set; a release name that already contains the chart name; `ingress.tls` empty; `serviceAccount.create=false` with an existing account; a config value that is a number must still render quoted.

**What a strong answer adds.** `selectorLabels` separate from `labels` and why; the `$` root inside `range`; `required` for the Secret name; a schema; `--rollback-on-failure` and `--wait` semantics; chart-testing in CI; OCI push to ECR and pinning `--version` in Argo CD or the pipeline.

## Bottlenecks & mitigations

* `helm upgrade --wait` blocks for the full rollout, so a 12-pod deployment with 150 s startup can take several minutes; the CI job needs a matching timeout.
* Every chart change, even a comment, requires a version bump for chart-testing, which adds a commit to small fixes.
* One chart serving many environments grows a large values surface; a `values.schema.json` that lags behind lets bad keys through silently.
* `helm template` cannot evaluate `lookup`, so templates that read cluster state render differently in CI and on the cluster.
* Helm stores release history as Secrets in the namespace; with `--history-max` at the default of 10 per release, a namespace with 50 releases holds 500 Secrets.

## Failure modes

* **"field is immutable" on upgrade.** A label that changes per release was added to `selectorLabels`. Mitigation: keep the selector helper to name and instance; if already wrong, delete and recreate the Deployment in a maintenance window.
* **Pods do not restart after a config change.** The checksum annotation is missing or hashes the wrong path. Mitigation: `helm template --show-only templates/deployment.yaml` before and after the change and diff the annotation.
* **YAML parse error with a line number in the rendered output.** A `toYaml` without `nindent`, or an `include` under the wrong indentation. Mitigation: `helm template --debug` prints the broken text; fix the `nindent` depth.
* **Release stuck in "pending-upgrade".** A previous `helm upgrade` was killed mid-way. Mitigation: `helm rollback` to the last deployed revision, then retry; use `--rollback-on-failure` so this does not recur.
* **"Error: INSTALLATION FAILED: ... is forbidden" from Pod Security.** The test pod lacked the security context. Mitigation: the test pod carries the same restricted settings as the app.
* **`helm push` rejected by ECR.** The ECR repository `charts/orders-api` does not exist or the token expired (12 hours). Mitigation: create the repository with Terraform; log in at the start of the job.
* **HPA and Deployment fight over replicas.** `replicas` is rendered while autoscaling is on, so every upgrade resets the count. Mitigation: the `if not .Values.autoscaling.enabled` guard around `replicas`.
* **Chart installs but the app has no secrets.** `existingSecret` points at a name the operator did not create in this namespace. Mitigation: `required` makes the name explicit; the test pod would fail on readiness, which shows it early.

## Reference solution

Helm chart templates

```
# file: Chart.yaml
apiVersion: v2
name: orders-api
description: Stateless HTTP API for orders. Deployment, Service, Ingress, HPA, PDB and a connection test.
type: application
version: 1.3.0        # chart version: bump on every template or default change (SemVer)
appVersion: "2.4.1"   # app image tag; quoted so YAML keeps it a string
kubeVersion: ">=1.30.0-0"   # the preStop sleep hook is on by default from 1.30
keywords: [api, orders]
maintainers:
  - name: platform-team
    email: platform@example.com

# file: values.yaml
# Defaults are the production-safe choice. Override per environment with -f values-<env>.yaml.
replicaCount: 3

image:
  repository: 111122223333.dkr.ecr.ap-south-1.amazonaws.com/orders-api
  pullPolicy: IfNotPresent
  # Empty means "use .Chart.AppVersion" so a chart release pins the app version.
  tag: ""

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  # IRSA: eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/orders-api
  # With EKS Pod Identity leave this empty and create the association outside the chart.
  annotations: {}
  automountToken: false

# Rendered into a ConfigMap and loaded with envFrom. Changing a value here
# changes the checksum annotation and restarts the pods.
config:
  LOG_LEVEL: info
  HTTP_PORT: "8080"
  CACHE_TTL_SECONDS: "30"

# Name of an existing Secret (created by External Secrets Operator) whose keys
# become environment variables. Required: the chart refuses to render without it.
existingSecret: orders-api-secrets

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  fsGroup: 10001
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]

containerPort: 8080

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false
  className: nginx
  annotations: {}
  # cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.orders.example.com
      paths:
        - path: /
          pathType: Prefix
  tls: []
  # - secretName: orders-api-tls
  #   hosts: [api.orders.example.com]

resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    memory: 512Mi   # equal to the request on purpose; no CPU limit

probes:
  startup:
    path: /healthz
    periodSeconds: 5
    failureThreshold: 30
  readiness:
    path: /readyz
    periodSeconds: 5
    timeoutSeconds: 2
    failureThreshold: 3
  liveness:
    path: /healthz
    periodSeconds: 10
    timeoutSeconds: 2
    failureThreshold: 3

terminationGracePeriodSeconds: 30
preStopSleepSeconds: 10

autoscaling:
  enabled: false
  minReplicas: 3
  maxReplicas: 12
  targetCPUUtilizationPercentage: 60

podDisruptionBudget:
  enabled: true
  minAvailable: 2

topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule

nodeSelector: {}
tolerations: []

# file: values-prod.yaml
# helm upgrade --install orders-api oci://111122223333.dkr.ecr.ap-south-1.amazonaws.com/charts/orders-api \
#   --version 1.3.0 -n orders --create-namespace -f values-prod.yaml --wait --rollback-on-failure
replicaCount: 3

serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/orders-api

config:
  LOG_LEVEL: warn
  DB_HOST: orders-db.cluster-abc.ap-south-1.rds.amazonaws.com

ingress:
  enabled: true
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.orders.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: orders-api-tls
      hosts:
        - api.orders.example.com

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 12

# file: values.schema.json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image", "existingSecret", "containerPort"],
  "properties": {
    "replicaCount": { "type": "integer", "minimum": 1 },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": { "type": "string", "minLength": 1 },
        "tag": { "type": "string" },
        "pullPolicy": { "type": "string", "enum": ["Always", "IfNotPresent", "Never"] }
      }
    },
    "existingSecret": { "type": "string", "minLength": 1 },
    "containerPort": { "type": "integer", "minimum": 1, "maximum": 65535 },
    "autoscaling": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean" },
        "minReplicas": { "type": "integer", "minimum": 1 },
        "maxReplicas": { "type": "integer", "minimum": 1 },
        "targetCPUUtilizationPercentage": { "type": "integer", "minimum": 1, "maximum": 100 }
      }
    },
    "resources": {
      "type": "object",
      "required": ["requests"],
      "properties": {
        "requests": {
          "type": "object",
          "required": ["cpu", "memory"]
        }
      }
    }
  }
}

# file: templates/_helpers.tpl
{{/*
Chart name, overridable, truncated to 63 chars (DNS label limit).
*/}}
{{- define "orders-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name: <release>-<chart> unless the release already contains the chart name.
*/}}
{{- define "orders-api.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "orders-api.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Selector labels: ONLY name and instance. A Deployment selector is immutable,
so nothing that changes between releases (version, chart) may appear here.
*/}}
{{- define "orders-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "orders-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Common labels: selector labels plus the ones that may change per release.
*/}}
{{- define "orders-api.labels" -}}
helm.sh/chart: {{ include "orders-api.chart" . }}
{{ include "orders-api.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | default .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "orders-api.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "orders-api.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

# file: templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "orders-api.fullname" . }}
  labels:
    {{- include "orders-api.labels" . | nindent 4 }}
data:
  {{- range $key, $value := .Values.config }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}

# file: templates/serviceaccount.yaml
{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "orders-api.serviceAccountName" . }}
  labels:
    {{- include "orders-api.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
automountServiceAccountToken: {{ .Values.serviceAccount.automountToken }}
{{- end }}

# file: templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "orders-api.fullname" . }}
  labels:
    {{- include "orders-api.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      {{- include "orders-api.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "orders-api.labels" . | nindent 8 }}
      annotations:
        # Hash of the rendered ConfigMap: any config change changes the pod
        # template, which triggers a rolling restart.
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "orders-api.serviceAccountName" . }}
      automountServiceAccountToken: {{ .Values.serviceAccount.automountToken }}
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      {{- with .Values.topologySpreadConstraints }}
      topologySpreadConstraints:
        {{- range . }}
        - maxSkew: {{ .maxSkew }}
          topologyKey: {{ .topologyKey }}
          whenUnsatisfiable: {{ .whenUnsatisfiable }}
          labelSelector:
            matchLabels:
              {{- include "orders-api.selectorLabels" $ | nindent 14 }}
        {{- end }}
      {{- end }}
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.containerPort }}
              protocol: TCP
          envFrom:
            - configMapRef:
                name: {{ include "orders-api.fullname" . }}
            - secretRef:
                name: {{ required "existingSecret must name the Secret created by External Secrets" .Values.existingSecret }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          startupProbe:
            httpGet:
              path: {{ .Values.probes.startup.path }}
              port: http
            periodSeconds: {{ .Values.probes.startup.periodSeconds }}
            failureThreshold: {{ .Values.probes.startup.failureThreshold }}
          readinessProbe:
            httpGet:
              path: {{ .Values.probes.readiness.path }}
              port: http
            periodSeconds: {{ .Values.probes.readiness.periodSeconds }}
            timeoutSeconds: {{ .Values.probes.readiness.timeoutSeconds }}
            failureThreshold: {{ .Values.probes.readiness.failureThreshold }}
          livenessProbe:
            httpGet:
              path: {{ .Values.probes.liveness.path }}
              port: http
            periodSeconds: {{ .Values.probes.liveness.periodSeconds }}
            timeoutSeconds: {{ .Values.probes.liveness.timeoutSeconds }}
            failureThreshold: {{ .Values.probes.liveness.failureThreshold }}
          lifecycle:
            preStop:
              sleep:
                seconds: {{ .Values.preStopSleepSeconds }}
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 64Mi
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}

# file: templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "orders-api.fullname" . }}
  labels:
    {{- include "orders-api.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  selector:
    {{- include "orders-api.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP

# file: templates/ingress.yaml
{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "orders-api.fullname" . }}
  labels:
    {{- include "orders-api.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  {{- with .Values.ingress.tls }}
  tls:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "orders-api.fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}

# file: templates/hpa.yaml
{{- if .Values.autoscaling.enabled -}}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "orders-api.fullname" . }}
  labels:
    {{- include "orders-api.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "orders-api.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60
{{- end }}

# file: templates/pdb.yaml
{{- if .Values.podDisruptionBudget.enabled -}}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "orders-api.fullname" . }}
  labels:
    {{- include "orders-api.labels" . | nindent 4 }}
spec:
  minAvailable: {{ .Values.podDisruptionBudget.minAvailable }}
  selector:
    matchLabels:
      {{- include "orders-api.selectorLabels" . | nindent 6 }}
  unhealthyPodEvictionPolicy: AlwaysAllow
{{- end }}

# file: templates/NOTES.txt
{{ .Chart.Name }} {{ .Chart.Version }} (app {{ .Values.image.tag | default .Chart.AppVersion }}) installed as release {{ .Release.Name }} in namespace {{ .Release.Namespace }}.

Check the rollout:
  kubectl -n {{ .Release.Namespace }} rollout status deploy/{{ include "orders-api.fullname" . }}

{{- if .Values.ingress.enabled }}
{{- range .Values.ingress.hosts }}
URL: https://{{ .host }}
{{- end }}
{{- else }}
No Ingress. Port-forward to try it:
  kubectl -n {{ .Release.Namespace }} port-forward svc/{{ include "orders-api.fullname" . }} 8080:{{ .Values.service.port }}
{{- end }}

Run the connection test:
  helm test {{ .Release.Name }} -n {{ .Release.Namespace }}

# file: templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "orders-api.fullname" . }}-test-connection"
  labels:
    {{- include "orders-api.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": test
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: wget
      image: busybox:1.37
      command: ["wget"]
      args: ["-q", "-O", "-", "{{ include "orders-api.fullname" . }}:{{ .Values.service.port }}{{ .Values.probes.readiness.path }}"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          memory: 16Mi
```

## Follow-up questions interviewers ask

* Make the chart a library chart that three services share. What moves into `_helpers.tpl` and what stays per service?
* Add a `ServiceMonitor` behind a flag only when the Prometheus Operator CRD exists. Which Helm function checks that?
* Argo CD deploys this chart from ECR. How does Argo CD discover a new chart version and how do you pin it?
* A values key was renamed from `ingress.class` to `ingress.className`. How do you keep old values files working for one release cycle?
* Add a pre-upgrade hook Job that runs database migrations. What hook weight and delete policy do you use, and what happens on failure?
* Sign the chart and verify the signature at install. What does Helm support and what does the ECR side need?

## Lessons that cover this

* [#18Helm - charts, templates, values and releasesKubernetes](/devops/learn/helm-charts)
* [#25Kubernetes internals and operators in GoContribute](/devops/learn/kubernetes-internals-operators-go)
* [#26Open source - contributing to CNCF projects, LFX and GSoCContribute](/devops/learn/open-source-cncf-lfx-gsoc)
* [#31Projects - pipeline, cluster, observability, operatorLater](/devops/learn/projects)

## Further reading

* [Helm documentationGuidehelm.sh](https://helm.sh/docs/)
* [Helm chart best practicesGuidehelm.sh](https://helm.sh/docs/chart_best_practices/)
* [cert-manager documentationGuidecert-manager.io](https://cert-manager.io/docs/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousTerraform: VPC and autoscaling group module](/devops/problems/terraform-vpc-asg-module)[NextGo: a Kubernetes-style reconcile loop for a custom resource](/devops/problems/go-reconcile-loop)

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
