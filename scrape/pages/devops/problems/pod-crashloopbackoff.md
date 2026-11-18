# Pod stuck in CrashLoopBackOff — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/pod-crashloopbackoff

[DevOps problems](/devops#problems)

OPSTroubleshooting#21Easy

# Pod stuck in CrashLoopBackOff

kubernetestroubleshootingcrashloopbackoffprobeskubectlReported at Infosys, Wipro

## Problem statement

It is 10:40 on a Tuesday. A developer pings you: "I deployed payments-api to staging and the pod keeps restarting." `kubectl get pods -n payments` shows `payments-api-5b7d9c6f4-qx2lm 0/1 CrashLoopBackOff 7 (2m ago) 14m`. The previous version is still serving production. Find the cause, get the pod healthy, and make sure the same mistake cannot reach production unnoticed. Talk the interviewer through every command and what each output would tell you.

## Requirements

### Functional

* Identify why the container exits, from evidence, within 10 minutes.
* Distinguish the four root-cause families: application crash, bad config or secret, failed liveness probe, resource limit.
* Restore a healthy pod in staging without guessing at fixes.
* Explain how the same failure would be caught before production in future.

### Non-functional

* Time to diagnosis under 10 minutes using only kubectl and the pod's logs.
* No change to production during the investigation; blast radius is 1 namespace in staging.
* The fix is applied through the normal pipeline (Git plus CI), not a hand-edited live object, unless the hand edit is explicitly a temporary test.
* The write-up names the root cause in 1 sentence and the prevention in 2.

## Back-of-the-envelope estimates

**Impact.** Staging only, 1 pod of 1 replica, 0 users affected, but the release to production is blocked. The CrashLoopBackOff delay doubles on every restart from 10 s up to a cap of 300 s, so after 7 restarts the pod waits 5 minutes between attempts: fixing the cause and deleting the pod is faster than waiting for the next automatic retry. The Deployment has `maxUnavailable: 0`, so if this image had gone to production the old ReplicaSet would have stayed up and users would not have noticed; the risk is a release stuck for hours, not an outage.

## API

```
# 1. What does the cluster say happened? Events at the bottom are the key output.
kubectl describe pod payments-api-5b7d9c6f4-qx2lm -n payments

# 2. Why did the LAST container exit? The current one may have logged nothing yet.
kubectl logs payments-api-5b7d9c6f4-qx2lm -n payments --previous

# 3. Exit code and reason without reading the whole describe output.
kubectl get pod payments-api-5b7d9c6f4-qx2lm -n payments \
  -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}{" "}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'

# 4. What changed? Compare the rollout revisions.
kubectl rollout history deployment/payments-api -n payments
kubectl rollout history deployment/payments-api -n payments --revision=12

# 5. Does the config the pod expects exist?
kubectl get configmap,secret -n payments
kubectl get deployment payments-api -n payments -o yaml | grep -A3 -E "envFrom|secretKeyRef|configMapKeyRef"

# 6. Run the container without its entrypoint to test the environment by hand.
kubectl debug payments-api-5b7d9c6f4-qx2lm -n payments -it --copy-to=debug-api \
  --container=payments-api -- sh
```

## Data model

```
Pod status fields that decide the diagnosis
  status.containerStatuses[0].restartCount        7
  status.containerStatuses[0].state               waiting: CrashLoopBackOff
  status.containerStatuses[0].lastState.terminated
      exitCode   1    -> app error (read the log)
      exitCode   137  -> SIGKILL: OOMKilled or liveness failure (check reason)
      exitCode   143  -> SIGTERM: something asked it to stop
      exitCode   126/127 -> command not found or not executable: wrong image or entrypoint
      reason     Error | OOMKilled | Completed

Deployment fields that usually cause it
  spec.template.spec.containers[0].image            tag, registry
  spec.template.spec.containers[0].command / args   entrypoint override
  spec.template.spec.containers[0].env, envFrom     missing ConfigMap or Secret key
  spec.template.spec.containers[0].resources.limits memory too low
  spec.template.spec.containers[0].livenessProbe    initialDelaySeconds, timeoutSeconds, path

Events (kubectl describe, bottom)
  Warning  BackOff    Back-off restarting failed container
  Warning  Unhealthy  Liveness probe failed: HTTP probe failed with statuscode: 500
  Normal   Killing    Container payments-api failed liveness probe, will be restarted
```

## Diagnosis and fix

1. **Scope first.** Confirm it is one pod in staging and production is untouched: `kubectl get pods -n payments -l app=payments-api` in both clusters. Tell the developer you are on it. Nothing else is at risk, so no need to page anyone.
2. **Read the events.** `kubectl describe pod` and look at the last 10 events. Three patterns point to three different causes: `Back-off restarting failed container` with nothing else means the process exits by itself; `Liveness probe failed` followed by `Killing` means the app is alive but the probe is wrong or the app is slow; an `OOMKilled` reason in last state means the memory limit.
3. **Read the exit code.** From `lastState.terminated`: 1 is an application error, 137 is a SIGKILL (OOM or liveness), 126 or 127 is a broken command or entrypoint, 0 means the process finished on purpose, which for a server means the main process is wrong (for example the container runs a migration script and exits).
4. **Read the previous container's logs.** `kubectl logs --previous`. For an exit code 1 this almost always names the cause: a stack trace, `KeyError: 'DATABASE_URL'`, `connection refused` to a dependency, `address already in use`. In this scenario the log ends with `Error: required env PAYMENT_PROVIDER_KEY is not set`.
5. **Find what changed.** `kubectl rollout history` shows revision 12 was created 14 minutes ago by the developer's pipeline. The diff against revision 11 shows the new code reads `PAYMENT_PROVIDER_KEY` from a Secret named `payments-provider`, and `kubectl get secret -n payments` shows that Secret exists in production but was never created in staging.
6. **Fix through the proper path.** The Secret is managed by the External Secrets Operator from AWS Secrets Manager. Add the staging `ExternalSecret` manifest to the environment repo and let Argo CD sync it. For a 5-minute confirmation you may create the Secret by hand in staging, but delete it after the proper one syncs so the two cannot drift.
7. **Restart and verify.** Delete the pod (or wait); confirm `1/1 Running`, restarts no longer increase for 10 minutes, the readiness probe passes and the pod is in the EndpointSlice. Run one request through the Service.
8. **Prevent.** Add a startup validation that lists every missing required variable at once and exits with a clear message. Add a pipeline check that every `secretKeyRef` and `configMapKeyRef` in the manifests resolves in the target environment (a 20-line script against the rendered manifests). Add a `startupProbe` so a slow start is not confused with a crash. Write the 3-line incident note.

## Architecture diagram

Rendering diagram…

## Deep dives

### The exit code is the fastest fork in the road

Kubernetes keeps the last terminated state of a container even after it restarts, so you do not have to catch the crash live. Exit code 1 (or any small number) comes from the application and the log explains it. Exit code 137 is 128 + 9, meaning the kernel or kubelet sent SIGKILL: either the memory limit was hit (the reason field says OOMKilled) or a liveness probe failed and kubelet killed the container after the grace period. Exit code 143 is 128 + 15, SIGTERM, usually a graceful stop from a rollout or a node drain, which is not a crash at all. Codes 126 and 127 mean the shell could not run the command: a typo in `command`, a binary missing from a slimmer base image, or a script without execute permission. Saying these numbers out loud is what interviewers listen for.

### Liveness probes cause more crash loops than bugs do

The second most common cause is a liveness probe that is stricter than the application. A Java or Node service that takes 40 seconds to warm up, probed with `initialDelaySeconds: 10` and `failureThreshold: 3`, is killed at second 40 every time and never finishes starting. The events show `Unhealthy` then `Killing`, the exit code is 137 and the log shows a normal startup cut short. The fix is a `startupProbe` with a generous `failureThreshold` (for example 30 checks at 5 seconds, allowing 150 seconds), after which the normal liveness probe takes over. The deeper rule: liveness should only check that the process is responsive, never a database or another service, because then a slow dependency restarts every pod and turns a slowdown into an outage.

### Missing configuration should fail fast and loud

The scenario's root cause, a Secret that exists in one environment but not another, is the most common cause of exit code 1 in a crash loop. The app should check every required setting at startup and print all missing names at once, so the second attempt does not reveal a third missing key. The environment should be managed as code: an `ExternalSecret` per environment in the same repo as the Deployment, so a reviewer can see that staging and production have the same keys. A pipeline step that renders the manifests and checks every `secretKeyRef` against the target namespace catches this before the pod ever starts.

### Why not just edit the live Deployment

Patching the running Deployment with `kubectl set env` fixes the pod in one minute and causes the next incident. With GitOps the controller reverts the hand edit on the next sync, and without GitOps the fix lives only in the cluster, so the next pipeline run or cluster rebuild silently removes it. The rule is: hand edits only to prove a hypothesis, time-boxed, followed by the same change through Git.

## Evaluation

**Did you find it?** The root cause is stated as "revision 12 reads `PAYMENT_PROVIDER_KEY` from Secret `payments-provider`, which was never created in staging", with the evidence chain: event, exit code 1, the log line, the rollout diff, the missing Secret.

**Is it fixed?** After the ExternalSecret syncs and the pod restarts: `restartCount` stops increasing for 10 minutes, `kubectl get pod` shows `1/1 Running`, the pod appears in the EndpointSlice, and one request through the Service returns 200.

**Is it prevented?** Three items in the write-up: the app validates required configuration at startup and exits with a list; the pipeline renders manifests and checks every Secret and ConfigMap key exists in the target environment; a startupProbe is added so slow starts are not mistaken for crashes.

**What a strong answer adds.** The exit code table from memory; the difference between readiness and liveness and why the old version kept serving; the note that CrashLoopBackOff delay caps at 5 minutes so deleting the pod after a fix is faster; and the point that `kubectl logs --previous` exists because the current container may have no logs yet.

**What a weak answer does.** "I would restart the pod" or "I would increase the memory" without reading the events or the exit code.

## Bottlenecks & mitigations

* The back-off timer: after several failures the pod waits up to 5 minutes between attempts, so verification is slow unless you delete the pod.
* Log retention: if the container crashes before logging is initialised, `--previous` is empty and you need `kubectl debug` to run the command by hand.
* Secrets managed outside Git: when nobody can see which keys exist per environment, every new key is a guess.
* Shared staging namespace: if several teams deploy here, the rollout history is the only reliable record of what changed.

## Failure modes

* **Guessing a fix before reading evidence.** Raising the memory limit when the exit code was 1 wastes a rollout and teaches nothing. Mitigation: events, exit code, previous logs, in that order, every time.
* **Fixing the live object by hand.** The next sync or pipeline run removes the fix. Mitigation: time-boxed hand edits only, then the change through Git.
* **Liveness probe that checks dependencies.** A slow database restarts every pod. Mitigation: liveness checks the process only; readiness may check dependencies.
* **A startup script that exits 0.** The container "completes" and is restarted forever with no error in the log. Mitigation: the main process must be the server; run migrations in an init container or a Job.
* **Missing a second missing key.** The app fails on the first missing variable, so a fix reveals a second crash. Mitigation: validate all required settings at once at startup.
* **Image pulled by mutable tag.** `staging` tag was rebuilt and the "same" image now has different code. Mitigation: deploy by digest or immutable version tags.

## Follow-up questions interviewers ask

* The exit code is 137 and the reason is OOMKilled. What do you check next, and how do you choose a new limit?
* The events show Liveness probe failed every 10 seconds but the logs look normal. What is wrong and what is the fix?
* `kubectl logs --previous` prints nothing. How do you find out what the container did?
* This happened in production with 10 replicas and maxUnavailable 0. What did users see, and how would you roll back?
* The pod is a CronJob that runs a database migration. How does the diagnosis change?
* How would you write the pipeline check that catches a missing Secret key before deployment?

## Lessons that cover this

* [#15Kubernetes architecture and core objectsKubernetes](/devops/learn/kubernetes-architecture-core-objects)
* [#22Troubleshooting playbook - Linux, Docker, Kubernetes, network, pipelinesOperate](/devops/learn/troubleshooting-playbook)
* [#28Interview playbook, what is new in 2026, revision sheetShip](/devops/learn/interview-playbook-2026-revision)

## Further reading

* [Kubernetes: Debug PodsGuidekubernetes.io](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAutoscaled self-hosted CI runners on Kubernetes](/devops/problems/self-hosted-ci-runners)[NextPods Pending and ImagePullBackOff after a node group change](/devops/problems/pod-pending-imagepullbackoff)

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
