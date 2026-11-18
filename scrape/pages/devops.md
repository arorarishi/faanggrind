# DevOps interview prep: Kubernetes, cloud and SRE roadmap with interview questions · FAANGrind

Source: https://faangrind.vercel.app/devops

DevOps

# DevOps, Kubernetes and cloud.

31 lessons (116.5 h of study) and 42 interview problems: Linux, CI/CD, AWS, Terraform, Kubernetes, observability and SRE.

26 to study, 2 to skim, 3 for later 7 easy, 24 medium, 11 hard

## Roadmap

Read the modules in order. Each lesson has a worked example, runnable code, interview questions and a quiz.

[Jump to problems](#problems)

1

### Foundations

6 lessons · 21.5 h

1. [#1StudyBeginner 2.5 hDevOps, SRE and platform engineering - how software reaches productionDevOps is a way of working that shortens the path from a code commit to a working change in production, and sends what production sees back to the people who wrote the code. This lesson explains what that means in practice, how the DevOps engineer, SRE and platform engineer roles differ, how the four DORA metrics measure delivery, what the 12-factor rules ask of an app, and how one change travels from a pull request to production and, if needed, back.Open lesson](/devops/learn/devops-sre-platform-engineering)
2. [#2StudyBeginner 4 hLinux for operatorsEvery container, every Kubernetes node and almost every CI runner is a Linux machine. This lesson is the operator's view of Linux: where files live, who may touch them, how processes are born and killed, how systemd keeps a service running, where logs go, and how to read disk, memory, CPU and load numbers when something is wrong. It ends with the kernel features (cgroups and namespaces) that containers are made of.Open lesson](/devops/learn/linux-for-operators)
3. [#3StudyBeginner 3.5 hBash scripting and the terminal toolkitThe shell is the operator's first programming language and the glue of every CI job, Dockerfile and runbook. This lesson covers the model (three streams, exit codes, pipes), the text tools you chain together (grep, awk, sed, sort, uniq, cut, jq), how to write a bash script that does not break on a space or a missing variable, scheduling with cron and systemd timers, ssh, rsync and tmux, and the point where you should stop writing bash and switch to Python or Go.Open lesson](/devops/learn/bash-and-terminal-toolkit)
4. [#4StudyBeginner 3.5 hNetworking for DevOps - TCP/IP, DNS, HTTP, TLS, SSHNetworking is the part of DevOps you cannot avoid: every outage ends with a packet that did not arrive, a name that did not resolve, or a certificate nobody renewed. This lesson covers the layers you actually debug (link, IP, TCP, TLS, HTTP), CIDR arithmetic with a real VPC plan, DNS end to end, the HTTP status codes operators care about, where TLS terminates, SSH and bastions, load balancers, security groups, and the eight tools that find the fault.Open lesson](/devops/learn/networking-for-devops)
5. [#5StudyBeginner 3 hGit and trunk-based workflowsGit is the database every DevOps workflow is built on: application code, Terraform, Helm values, Kubernetes manifests and CI pipelines all live in it, and in GitOps a Git commit is the deploy. This lesson covers the Git model (snapshots, the DAG, branches as pointers), merge versus rebase versus squash, trunk-based development versus GitFlow, the pull request workflow, releases and hotfixes, bisect, hooks, monorepos, signed commits, and the ten Git situations that come up on call with the exact command for each.Open lesson](/devops/learn/git-and-trunk-based-workflows)
6. [#6StudyIntermediate 5 hPython and Go for automation and toolingA DevOps engineer needs two languages. Python is for scripts, checks, data and glue between APIs: fast to write, already installed everywhere. Go is for anything that ships as a single binary, does many things at once, or lives in the CNCF world, where Kubernetes, Helm, Argo CD, Prometheus and Terraform are written. This lesson shows the shape of a good Python ops script, the one page of Go a Python person needs, the worker-pool pattern with channels and context, and the mistakes that make Go tools leak.Open lesson](/devops/learn/python-and-go-for-devops)

2

### Build and ship

4 lessons · 13.5 h

1. [#7StudyBeginner 3 hWeb servers, reverse proxies and TLS - Nginx, certificates, process managersThe first real deployment most people do is a Node or Python app on one Linux VM: clone, build, run it under a process manager, and put Nginx in front. This lesson covers why the proxy is there, how an Nginx config is structured, the server block you will copy for years, load balancing across app processes, static files, rate limiting, TLS with Let's Encrypt and certbot, systemd versus PM2, and how to read Nginx logs and status codes.Open lesson](/devops/learn/nginx-reverse-proxy-tls)
2. [#8StudyBeginner 3.5 hContainers and DockerA container is a normal Linux process that the kernel isolates with namespaces and limits with cgroups, started from an image made of read-only layers. This lesson covers images and the build cache, a production multi-stage Dockerfile, base image choices, tags versus digests, registries, the docker run flags that matter, networking and volumes, Compose for local stacks, deploying a monorepo to VMs with Docker and why that stops scaling, container security basics, troubleshooting, and how containerd and the OCI standards fit under Kubernetes.Open lesson](/devops/learn/containers-and-docker)
3. [#9StudyIntermediate 3.5 hCI/CD with GitHub Actions and GitLab CIA CI/CD pipeline is the set of automated jobs that run when code changes: lint, test, build an image, scan it, deploy it, and check that the deploy worked. This lesson teaches the shape of a good pipeline, then GitHub Actions in depth (triggers, matrix, caching, environments, OIDC to AWS, reusable workflows, security), GitLab CI as the equivalent, monorepo pipelines that build only what changed, runners on Kubernetes, and how to make a slow pipeline fast.Open lesson](/devops/learn/ci-cd-github-actions-gitlab)
4. [#10StudyIntermediate 3.5 hDeployment strategies and release engineeringA deployment strategy is the plan for moving user traffic from the running version of a service to a new one without breaking anything. This lesson compares recreate, rolling, blue-green, canary, A/B and shadow, then covers what cannot be rolled back (data), database migrations that stay backward compatible, graceful shutdown, feature flags, release trains and versioning, the deploy checklist, the Friday question, and how DORA measures whether your releases are good.Open lesson](/devops/learn/deployment-strategies-release-engineering)

3

### Cloud and IaC

4 lessons · 15.5 h

1. [#11StudyIntermediate 5 hAWS core - IAM, VPC, EC2, S3, RDS, load balancers, autoscalingAWS is the cloud most Indian DevOps jobs ask for. This lesson covers the services every platform is built from and the one setting people get wrong in each: accounts and IAM (who may do what), VPC (where things live on the network), EC2 and Auto Scaling groups (the machines), load balancers (the front door), S3, RDS and Aurora (data), Route 53, CloudWatch, Systems Manager and Secrets Manager.Open lesson](/devops/learn/aws-core-for-devops)
2. [#12StudyIntermediate 5 hAWS managed platforms - EKS, ECS, Fargate, Lambda, SQS, ElastiCache, CloudFrontAWS offers five ways to run a workload: EC2 with an Auto Scaling group, ECS, EKS, Fargate, and Lambda. This lesson is about choosing between them and about EKS as an AWS product: node groups and Auto Mode, the VPC CNI, Pod Identity, access entries, add-ons and the load balancer controller. It also covers the services that sit beside the cluster: SQS and SNS, ElastiCache, CloudFront, and Secrets Manager through the External Secrets Operator.Open lesson](/devops/learn/aws-managed-platforms-eks-ecs)
3. [#13StudyIntermediate 4 hTerraform - infrastructure as codeInfrastructure as code (IaC) means your VPCs, clusters, databases and IAM roles are written in files, reviewed in pull requests and created by a tool, not clicked together in a console. Terraform is the most common IaC tool. You write HCL, run plan to see the diff, run apply to make it real, and a state file remembers what Terraform owns. This lesson covers the language, state, modules, environments, CI and the moments where Terraform can destroy production.Open lesson](/devops/learn/terraform-infrastructure-as-code)
4. [#14SkimBeginner 1.5 hAnsible and configuration managementConfiguration management is the job of making a fleet of machines match a written description: these packages, this config file, this service running. Ansible does it over SSH with no agent, from YAML playbooks whose tasks are idempotent: run them twice and the second run changes nothing. This lesson covers where Ansible still fits once you have containers and Terraform, its model (inventory, plays, tasks, modules, handlers, roles, vault) and the mistakes that make it dangerous.Open lesson](/devops/learn/ansible-configuration-management)

4

### Kubernetes

5 lessons · 21 h

1. [#15StudyIntermediate 4 hKubernetes architecture and core objectsKubernetes runs containers across a fleet of machines. You describe the state you want in YAML (three copies of this image, reachable on port 80) and a set of control loops makes the cluster match it and keeps it matched when things fail. This lesson covers the control plane, the worker node, the core objects (Pod, Deployment, Service, ConfigMap, Secret, Namespace) and the kubectl commands interviewers expect you to know cold.Open lesson](/devops/learn/kubernetes-architecture-core-objects)
2. [#16StudyIntermediate 4.5 hKubernetes networking and storageLesson 15 said a Service is a stable address for pods. This lesson opens the box: how pods get IPs (the CNI plugin), how a Service's virtual IP is turned into real packets (EndpointSlices and kube-proxy or eBPF), how DNS names are built and why they cost extra queries, how HTTP gets in from outside (Ingress, Gateway API, the AWS Load Balancer Controller), how to restrict traffic (NetworkPolicy), and how disks work (PV, PVC, StorageClass, StatefulSets, EBS and EFS).Open lesson](/devops/learn/kubernetes-networking-storage)
3. [#17StudyAdvanced 5 hKubernetes in production - resources, autoscaling, RBAC, upgrades, EKSRunning Kubernetes in production is a set of decisions that nobody makes for you: how much CPU and memory each pod asks for, which pods die first when a node is full, how probes are timed, where pods may be scheduled, how pods and nodes scale, who may do what, what a pod may not do, and how to upgrade without an outage. This lesson covers each decision with the field names, the defaults and the numbers, and ends with a production checklist.Open lesson](/devops/learn/kubernetes-in-production)
4. [#18StudyIntermediate 3.5 hHelm - charts, templates, values and releasesHelm is the package manager for Kubernetes. A chart is a folder of Go templates plus a values.yaml with defaults; `helm install` merges your values into the templates, sends the resulting manifests to the API server and records the result as a release. This lesson covers the chart layout, the template language, values design, the release lifecycle with upgrades and rollbacks, dependencies, publishing to an OCI registry such as ECR, testing, and how Helm fits with Argo CD.Open lesson](/devops/learn/helm-charts)
5. [#19StudyIntermediate 4 hGitOps with Argo CD and progressive deliveryGitOps means the desired state of a cluster lives in Git, and an agent inside the cluster pulls that state and keeps the cluster matching it. Argo CD is the most used agent. This lesson covers the four GitOps principles, why pull beats push, the Argo CD objects (Application, AppProject, ApplicationSet), sync, drift and self-heal, repository layout and promotion, rollback by revert, secrets with External Secrets, Flux as the alternative, and progressive delivery with Argo Rollouts canaries.Open lesson](/devops/learn/gitops-argocd-progressive-delivery)

5

### Operate

5 lessons · 20.5 h

1. [#20StudyIntermediate 4.5 hObservability - Prometheus, Grafana, OpenTelemetry, logs and alertingObservability is how you find out what a running system is doing from the outside: metrics (numbers over time), logs (events), and traces (one request's path across services). This lesson covers the Prometheus data model and the PromQL queries every on-call engineer writes, Alertmanager, Grafana dashboards, log shipping to Loki, distributed tracing with OpenTelemetry, the collector pipeline, and the arithmetic of what all of this costs.Open lesson](/devops/learn/observability-prometheus-grafana-otel)
2. [#21StudyIntermediate 3.5 hSRE practice - SLOs, error budgets, incidents and postmortemsSite Reliability Engineering is software engineering applied to running services. Its tools are the SLI (what you measure), the SLO (the target), the error budget (how much failure you can afford), burn-rate alerts (how fast you are spending it), a practised incident response with named roles, and blameless postmortems that turn each outage into action items. This lesson gives the definitions, the arithmetic and the checklists interviewers ask for.Open lesson](/devops/learn/sre-slos-incidents-postmortems)
3. [#22StudyIntermediate 4.5 hTroubleshooting playbook - Linux, Docker, Kubernetes, network, pipelinesTroubleshooting is a method, not a list of commands. Scope the damage, protect users before you understand the cause, follow the request path to the first broken contract, test one hypothesis with one command, change one thing at a time, and write down what you did. This lesson gives that method and then five dense playbooks (Linux host, containers, Kubernetes, networking, pipelines) where every row has a symptom, likely causes, a real first command, the evidence that confirms it, and the fix.Open lesson](/devops/learn/troubleshooting-playbook)
4. [#23StudyIntermediate 4 hSecurity and DevSecOps - secrets, least privilege, supply chain, policy as codeDevSecOps means security is a property of the pipeline and the platform, not a review at the end. This lesson covers the controls a DevOps engineer owns: short-lived identity for humans, CI and pods; secrets that never touch Git; a supply chain where every image is scanned, pinned, signed and verified at admission; hardened pods and clusters enforced by policy as code; cloud hardening with private endpoints and audit logs; and the edge controls (TLS, WAF, rate limits, SSRF protection) that stop abuse before it reaches the application.Open lesson](/devops/learn/security-and-devsecops)
5. [#24StudyIntermediate 4 hScaling and resilience - caching, queues, rate limiting, DDoS, DRScaling is making a system handle more load; resilience is making it keep working when parts fail. Both come from the same layered design: stateless replicas behind a load balancer, state pushed into databases, caches, object storage and queues, limits and timeouts at every hop, and a tested plan for losing a zone or a region. This lesson covers each layer with the numbers interviewers expect: cache hit ratios, queue semantics, rate limiter algorithms, retry budgets, connection pools, RPO and RTO.Open lesson](/devops/learn/scaling-and-resilience)

6

### Contribute

2 lessons · 11 h

1. [#25StudyAdvanced 6 hKubernetes internals and operators in GoKubernetes is an API server plus a crowd of control loops. This lesson opens the box: how the API server names and stores objects, what resourceVersion and generation mean, how watches work, and how a controller turns events into a reconcile function that is safe to run again and again. Then you build an operator for a WebApp custom resource with controller-runtime and kubebuilder, test it with envtest, and learn to read the Kubernetes source itself.Open lesson](/devops/learn/kubernetes-internals-operators-go)
2. [#26StudyIntermediate 5 hOpen source - contributing to CNCF projects, LFX and GSoCOpen source contribution is proof of skill that no certificate matches: a merged pull request in Kubernetes, Helm or Prometheus shows you can read a large Go codebase, follow a review process and work with strangers. This lesson explains how CNCF projects are organised, how to pick one and climb its contribution ladder, how LFX Mentorship and GSoC work, and gives a 12-week plan from zero to a first merged PR.Open lesson](/devops/learn/open-source-cncf-lfx-gsoc)

7

### Ship

2 lessons · 6.5 h

1. [#27SkimIntermediate 1.5 hCloud cost and FinOpsFinOps is the practice of treating cloud spend as an engineering signal: measure it, attribute it to teams, and lower it with the same discipline you apply to latency or error rate. This lesson shows where an AWS bill for a Kubernetes platform goes, the levers in order of impact, how to allocate cost to teams, which tools to name, and how to put a cost check into every Terraform pull request.Open lesson](/devops/learn/cloud-cost-and-finops)
2. [#28StudyIntermediate 5 hInterview playbook, what is new in 2026, revision sheetThis is the last stop before an interview. It lists the rounds a DevOps, SRE or platform candidate faces in 2026 and what each one tests, gives a fixed structure for troubleshooting and design answers, a table of what changed recently and a line to say about each, a 42-term revision sheet, the 15 questions Indian service and product companies ask most, how to talk about projects, and a one-week plan.Open lesson](/devops/learn/interview-playbook-2026-revision)

8

### Later

3 lessons · 7 h

1. [#29LaterAdvanced 2.5 hPlatform engineering, service mesh and eBPFPlatform engineering treats the internal tooling that developers use to ship software as a product with customers. This lesson covers what an internal developer platform (IDP) is, golden paths, Backstage and Crossplane, and how to measure a platform. It then covers the two technologies platform teams are asked about most: service meshes (Istio, Linkerd) with their real costs, and eBPF with Cilium, which moves networking, policy and observability into the kernel.Open lesson](/devops/learn/platform-engineering-service-mesh-ebpf)
2. [#30LaterAdvanced 2.5 hGPU and ML infrastructure - serving models on KubernetesPlatform teams now run GPU workloads, mostly large language model (LLM) inference, on the same Kubernetes clusters as everything else. This lesson covers GPU nodes on EKS, how GPUs are scheduled and shared, the serving engines (vLLM, Ray Serve, KServe), the metrics that matter for LLM serving and how to autoscale on them, model storage, GPU observability, the gateway in front of it all, and the basics of MLOps.Open lesson](/devops/learn/gpu-and-ml-infrastructure)
3. [#31LaterIntermediate 2 hProjects - pipeline, cluster, observability, operatorFive portfolio projects that together cover the whole roadmap: a service shipped to a VM by hand and then automated, a complete CI/CD pipeline, a production-shaped Kubernetes platform, an observability stack with a game day, and a Kubernetes operator in Go. Each has a one-to-two-week scope, numbered build steps, a measurable acceptance test, and the mistakes that make it look weak. The lesson ends with how to present a project in two minutes.Open lesson](/devops/learn/projects)

## Interview problems

Each one has requirements, estimates, interfaces, design or diagnosis path, a diagram, deep dives, failure modes and follow-ups. Implement-it problems include a reference solution.

DESIGN

### Platform design

· 20

CI/CD, Kubernetes platforms, multi-region AWS, observability and secrets: the design rounds for DevOps, SRE and platform roles.

1. [1CI/CD pipeline for a 15-service monorepoci-cd · github-actions · monorepo · docker · caching · gitopsHard](/devops/problems/monorepo-ci-pipeline)
2. [2Zero-downtime deployment system with canary analysis and rollbackkubernetes · argo-rollouts · canary · graceful-shutdown · progressive-delivery · eksHard](/devops/problems/zero-downtime-deploys)
3. [3Multi-environment Terraform: dev, staging and prod with remote stateterraform · aws · iac · github-actions · oidc · state-managementInfosys, Wipro, TCSMedium](/devops/problems/terraform-multi-env)
4. [4Production EKS cluster for a 30-engineer startupeks · kubernetes · aws · karpenter · gitops · multi-tenancyHard](/devops/problems/eks-cluster-platform)
5. [5Observability platform for 200 microservicesobservability · opentelemetry · prometheus · grafana · tracing · sloHard](/devops/problems/observability-platform)
6. [6Secrets management across CI, Kubernetes and runtimesecrets · external-secrets · aws-secrets-manager · oidc · rotation · securityMedium](/devops/problems/secrets-management)
7. [7Multi-region disaster recovery with RPO 5 minutes and RTO 30 minutesdisaster-recovery · multi-region · aurora · route53 · argocd · awsHard](/devops/problems/multi-region-dr)
8. [8Autoscaling for a web app: ASG, HPA and cluster autoscalingautoscaling · hpa · keda · karpenter · eks · capacityMedium](/devops/problems/autoscaling-web-app)
9. [9Internal developer platform and golden pathplatform-engineering · backstage · gitops · multi-tenancy · eks · developer-experienceHard](/devops/problems/internal-developer-platform)
10. [10GitOps deployment platform with Argo CD for 50 teamsgitops · argocd · kubernetes · multi-cluster · rbac · eksHard](/devops/problems/gitops-platform-argocd)
11. [11Log pipeline at 1 TB per daylogging · loki · opentelemetry · fluent-bit · s3 · costMedium](/devops/problems/log-pipeline-1tb)
12. [12SLO-based alerting and on-call systemslo · alerting · prometheus · alertmanager · on-call · sreMedium](/devops/problems/slo-alerting-oncall)
13. [13Secure container image pipeline: build, scan, sign, SBOM, admissionsupply-chain · cosign · slsa · sbom · kyverno · ecrMedium](/devops/problems/supply-chain-image-pipeline)
14. [14Rate limiting, bot and DDoS protection at the edgeddos · rate-limiting · waf · cloudfront · edge · abuseMedium](/devops/problems/edge-rate-limiting-ddos)
15. [15Backup and restore for stateful workloads on Kubernetesbackup · velero · postgresql · ebs · disaster-recovery · kubernetesMedium](/devops/problems/stateful-backup-restore)
16. [16Zero-downtime database schema migration and cutoverpostgresql · aurora · schema-migration · expand-contract · ci-cd · feature-flagsHard](/devops/problems/zero-downtime-db-migration)
17. [17Cut the AWS bill by 40 percentfinops · aws · karpenter · spot · savings-plans · cost-allocationMedium](/devops/problems/cloud-cost-reduction)
18. [18GPU inference platform on EKS for OpenAI-compatible LLM servinggpu · vllm · eks · keda · api-gateway · meteringHard](/devops/problems/gpu-inference-platform)
19. [19Uptime monitoring service with global probes and alertingredis-streams · workers · scheduler · time-series · alerting · websocketMedium](/devops/problems/uptime-monitoring-service)
20. [20Autoscaled self-hosted CI runners on Kubernetesgithub-actions · actions-runner-controller · karpenter · buildkit · ci-cd · eksMedium](/devops/problems/self-hosted-ci-runners)

OPS

### Troubleshooting

· 12

Incident scenarios: pods that will not start, DNS failures, full disks, flaky pipelines. Diagnose, fix and prevent.

1. [21Pod stuck in CrashLoopBackOffkubernetes · troubleshooting · crashloopbackoff · probes · kubectlInfosys, WiproEasy](/devops/problems/pod-crashloopbackoff)
2. [22Pods Pending and ImagePullBackOff after a node group changekubernetes · troubleshooting · scheduling · ecr · karpenter · eksInfosys, Wipro, TCSEasy](/devops/problems/pod-pending-imagepullbackoff)
3. [23502 from the ingress while the service works inside the clusterkubernetes · ingress · networking · service · endpointslices · troubleshootingInfosys, CapgeminiMedium](/devops/problems/ingress-502-service-unreachable)
4. [24Disk full on a production server at 3 amlinux · troubleshooting · disk · logrotate · systemd · nginxInfosys, Wipro, TCSEasy](/devops/problems/disk-full-production-server)
5. [25High load average and a process eating memory on a Linux hostlinux · performance · memory-leak · load-average · nodejs · troubleshootingInfosys, Capgemini, AccentureMedium](/devops/problems/high-load-memory-leak-linux)
6. [26Deploy rolled out, users see errors, readiness probes flappingkubernetes · readiness-probe · rollout · argo-rollouts · troubleshooting · deploymentInfosys, WiproMedium](/devops/problems/bad-deploy-readiness-probes)
7. [27TLS certificate expired in productiontls · cert-manager · lets-encrypt · certificates · troubleshooting · kubernetesInfosys, Wipro, CapgeminiEasy](/devops/problems/tls-certificate-expired)
8. [28CI pipeline became slow and flakyci-cd · github-actions · caching · flaky-tests · docker · troubleshootingInfosys, CapgeminiMedium](/devops/problems/slow-flaky-ci-pipeline)
9. [29Intermittent DNS resolution failures in the clusterkubernetes · coredns · dns · networking · conntrack · troubleshootingHard](/devops/problems/intermittent-dns-failures)
10. [30Terraform plan wants to destroy the production databaseterraform · aws · rds · state · moved-block · ci-cdInfosys, Wipro, CapgeminiMedium](/devops/problems/terraform-wants-to-destroy-db)
11. [31OOMKilled pods and an HPA that keeps scaling up and downkubernetes · oomkilled · hpa · autoscaling · resources · troubleshootingInfosys, TCSMedium](/devops/problems/oomkilled-hpa-thrashing)
12. [32Database connections exhausted after a deploypostgresql · connection-pool · pgbouncer · rds · kubernetes · troubleshootingInfosys, Wipro, AccentureMedium](/devops/problems/db-connection-pool-exhausted)

CODE

### Implement it

· 10

Scripts, Dockerfiles, manifests, Terraform, Helm charts and a Go reconcile loop, written the way a reviewer expects.

1. [33Bash: analyse an Nginx access logbash · awk · nginx · logs · text processingInfosys, Wipro, CapgeminiEasy](/devops/problems/bash-log-analyzer)
2. [34Bash: safe deploy script with locking, rollback and trapsbash · deployment · symlink · locking · rollback · linuxInfosys, TCSMedium](/devops/problems/bash-safe-deploy-script)
3. [35Python: concurrent health checker with retries and backoffpython · concurrency · retries · backoff · prometheus · health checksMedium](/devops/problems/python-health-checker)
4. [36Dockerfile: multi-stage build with a non-root userdocker · dockerfile · multi-stage · node.js · security · image sizeInfosys, Wipro, TCSEasy](/devops/problems/multistage-dockerfile)
5. [37GitHub Actions: build, test, cache, push an image and deploygithub actions · ci/cd · oidc · ecr · trivy · gitopsInfosys, CapgeminiMedium](/devops/problems/github-actions-build-push-deploy)
6. [38Kubernetes manifests: Deployment, Service, Ingress and HPA with probes and limitskubernetes · deployment · ingress · hpa · probes · securityInfosys, Wipro, TCSMedium](/devops/problems/kubernetes-manifests-web-app)
7. [39Terraform: VPC and autoscaling group moduleterraform · aws · vpc · autoscaling · alb · modulesInfosys, Capgemini, AccentureMedium](/devops/problems/terraform-vpc-asg-module)
8. [40Helm chart from scratch with values, templates and a testhelm · kubernetes · templates · packaging · oci · ecrInfosys, Wipro, TCSMedium](/devops/problems/helm-chart-from-scratch)
9. [41Go: a Kubernetes-style reconcile loop for a custom resourcego · kubernetes · operators · controllers · concurrency · client-goHard](/devops/problems/go-reconcile-loop)
10. [42Python: SLO error budget and burn-rate alert calculatorpython · slo · error budget · burn rate · prometheus · alertingEasy](/devops/problems/python-slo-burn-rate)
