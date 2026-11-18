# LoRA fine-tuning pipeline with an adapter registry — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/fine-tuning-pipeline

[AI problems](/ai#problems)

GENAIGenAI systems#12Hard

# LoRA fine-tuning pipeline with an adapter registry

fine-tuningloraqloragpu schedulingevaluation gateadapter registryReported at OpenAI

## Problem statement

Design a fine-tuning platform for a company where 120 product teams adapt two open base models, a 7B and a 70B model, to their own tasks. A team uploads a dataset and gets back a LoRA adapter: a small set of trained weights added to a frozen base model. The platform validates the data, runs about 40 training jobs a day on a shared GPU pool, proves each adapter beats the base model before promotion, and rolls back in under a minute. It must also say when fine-tuning is the wrong tool.

## Requirements

### Functional

* Upload a versioned dataset of chat examples and get a validation report with a verdict: train, fix the data, or do not fine-tune.
* Submit a LoRA or QLoRA job (QLoRA is LoRA on a base model stored in 4 bits) with safe default hyperparameters, see the cost estimate, queue position and loss curve, and cancel it.
* Resume a job from its latest checkpoint after a GPU is taken away.
* Score every finished adapter against the base model on a held-out split and a general regression set. Only passing adapters can be promoted.
* Keep each adapter in a registry with its lineage: base model hash, dataset version, hyperparameters, eval scores and owner.
* Deploy an adapter behind a stable alias with a canary, and roll back to the previous adapter with one call.

### Non-functional

* 40 jobs per day on average and 100 per day at peak; p95 queue wait under 30 minutes for jobs under 2 GPU-hours.
* A preempted job (its GPU was taken back by the provider) loses at most 10 minutes of training work.
* Promotion gate: at least 3 points better than the base model with its best prompt on the held-out split, proven at 95% confidence, and at most 1 point worse on the general regression set.
* Rollback completes in under 60 seconds with no model reload.
* A standard 7B job costs under 10 USD including evaluation, and the estimate is shown before the job starts.
* A team's datasets and adapters are readable only by that team, and every promotion is written to an audit log.

## Back-of-the-envelope estimates

**A standard job.** 5,000 examples with 10% held out leave 4,500 x 800 tokens = 3.6M tokens. 3 epochs = 10.8M training tokens. At batch size 16 that is 4,500 x 3 / 16 = 844 steps.

**Memory.** 7B in 16-bit is 14 GB, so LoRA fits on one 80 GB GPU. 70B in 16-bit is 140 GB and does not fit. In 4-bit it is 35 GB, so 70B jobs use QLoRA.

**GPU time.** Assume 3,000 training tokens per second on the 7B base and 300 on the 70B. Training takes 10.8M / 3,000 = 3,600 s (1 hour) or 10.8M / 300 = 36,000 s (10 hours). Adding model load and evaluation, budget 1.5 and 12 GPU-hours.

**Fleet.** Average day: 36 small x 1.5 + 4 large x 12 = 102 GPU-hours, 4.25 GPUs busy. Peak day: 90 x 1.5 + 10 x 12 = 255 GPU-hours, 10.6 GPUs. Reserve 6 GPUs (144 GPU-hours, 71% used on an average day) and burst to 16 with preemptible GPUs (384 GPU-hours, 66% used at peak).

**Cost.** At an assumed 2.5 USD per GPU-hour, a small job costs 3.75 USD, a large one 30 USD. The eval gate judges 500 held-out cases for both models and 300 regression prompts for the adapter only (base scores are cached): 1,300 calls of 1,200 input and 100 output tokens, 1.56M and 0.13M tokens. At an assumed 1 USD and 5 USD per million: 1.56 + 0.65 = 2.21 USD, 60% of a small job's GPU cost.

**Storage.** A rank-16 adapter on the attention and MLP layers of the 7B model has about 40M values: 80 MB in 16-bit. A checkpoint stores each weight plus two Adam optimiser values in 32-bit: 40M x 12 bytes = 480 MB.

**Checkpoint interval.** 100 steps x 16 examples x 800 tokens = 1.28M tokens: 7 minutes on the 7B base, 71 on the 70B. So checkpoint every 100 steps or 10 minutes, whichever is first.

## API

```
POST /v1/datasets
  body: { team, task, format: "chat_jsonl" }        -> { dataset_id, upload_url }
POST /v1/datasets/{dataset_id}/validate
  -> { dataset_version, report: { examples, duplicates, template_errors,
       too_long, pii_hits, baseline_score },
       verdict: "train" | "fix_data" | "do_not_finetune", reasons: [] }

POST /v1/jobs
  body: { dataset_version, base_model, method?: "lora" | "qlora",
          hyperparams?: { rank, alpha, learning_rate, epochs },
          eval_suite_id, target_metric }
  -> { job_id, estimated_gpu_hours, estimated_cost_usd, queue_position }
GET  /v1/jobs/{job_id}
  -> { state, step, total_steps, train_loss, val_loss, preemptions, eta }
POST /v1/jobs/{job_id}/cancel
GET  /v1/jobs/{job_id}/eval
  -> { baseline, tuned, fixed_cases, broken_cases, z, regression_delta,
       gate: "pass" | "fail" | "not_proven" }

GET  /v1/adapters?team=&task=
POST /v1/aliases/{alias}/deploy     body: { adapter_id, canary_percent }
POST /v1/aliases/{alias}/promote
POST /v1/aliases/{alias}/rollback
```

## Data model

```
dataset_versions(dataset_version PK, dataset_id, team, content_hash,
                 examples, train_uri, heldout_uri, report_json,
                 verdict, created_at, deleted_at)

jobs(job_id PK, team, dataset_version FK, base_model_hash, method,
     rank, alpha, learning_rate, epochs, state, priority,
     est_gpu_hours, used_gpu_hours, preemptions, created_at)

checkpoints(job_id FK, step, uri, epoch, data_position, data_seed,
            complete BOOL, created_at)       -- adapter + optimiser state

eval_runs(eval_id PK, job_id FK, suite_version, judge_version,
          baseline_score, tuned_score, fixed, broken, z,
          regression_delta, gate, report_uri)

adapters(adapter_id PK, job_id FK, team, task, base_model_hash,
         dataset_version, rank, size_bytes, weights_uri,
         stage: candidate | canary | production | retired)

aliases(alias PK, team, current_adapter_id, previous_adapter_id,
        canary_adapter_id, canary_percent, updated_by, updated_at)
audit_log(id PK, actor, action, alias, adapter_id, at)
```

## High-level design

**Offline path (data to adapter)**

1. **Upload.** A team uploads chat examples as JSONL. The platform stores an immutable dataset version keyed by a content hash.
2. **Validate.** The validator checks the schema and roles, renders each example with the base model's chat template (the exact text format, with special tokens, that marks each turn), counts tokens, removes duplicates, scans for PII (personal data such as names and phone numbers), and then splits 90/10 into train and held-out.
3. **Advise.** The advisor runs the base model with the team's best prompt on the held-out split and returns a verdict: train, fix the data, or do not fine-tune.
4. **Queue.** A job gets a cost estimate and enters a fair-share queue. Defaults are rank 16, alpha 32 and 3 epochs.
5. **Schedule.** The scheduler picks a GPU. It uses LoRA when the 16-bit base fits with room to train, and QLoRA (a 4-bit base) when it does not.
6. **Train.** The trainer updates only the adapter, logs train and validation loss, and writes a checkpoint every 100 steps or 10 minutes. A preempted job goes back to the queue with a resume flag.
7. **Gate.** The eval runner scores the base model and the adapter on the held-out split and the regression set, case by case.
8. **Register.** A passing adapter enters the registry with its lineage. A failing one is kept 7 days for debugging and cannot be promoted.

**Online path (adapter to traffic)**

9. **Deploy.** Serving replicas keep the base model in memory and load the adapter beside it. An alias such as `support/triage:prod` sends 5% of its traffic to the new adapter first. This small first step is the canary.
10. **Watch.** The platform compares canary and current traffic on the team's online metric, then promotes or rolls back by changing the alias.
11. **Feed back.** Labelled production failures become examples in the next dataset version.

## Architecture diagram

Rendering diagram…

## Deep dives

### Validation, and when to say "do not fine-tune"

Most failed fine-tunes are data problems. The validator renders every example through the base model's chat template and rejects the upload if special tokens are missing, because a wrong template is the most frequent cause of an adapter that scores below the base. It removes exact and near duplicates before splitting, so no held-out example copies a training example. It flags over-long examples, empty outputs, and identical inputs with different labels.

The advisor then returns "do not fine-tune" when:

* there are fewer than about 500 clean examples;
* the task needs facts that change, such as prices or policies. That is knowledge, and retrieval supplies it without retraining;
* the base model with the team's best prompt already meets the target on the held-out split;
* the task definition is still changing, since every change means a new dataset;
* the only gain is a shorter prompt and traffic is low. Saving 1,700 prompt tokens on 1,000 requests a day is 1.7M tokens, or 1.70 USD a day at an assumed 1 USD per million.

Each verdict carries its evidence: the baseline score and the rejected examples.

### Scheduling GPUs: fair share, short jobs and preemption

Large jobs are 10% of the count and 47% of the GPU-hours on an average day (48 of 102). A first-in-first-out queue lets one 12-hour job block many 1.5-hour jobs. Two rules fix this. Fair share: each team has a weight, and the scheduler serves the team furthest below its share. Short jobs first inside a team, using the estimated GPU-hours. Reserved GPUs run jobs to completion. Burst GPUs can be taken away, so every job on them must be resumable.

A checkpoint holds the adapter weights, the optimiser state, the learning-rate schedule step, the data-order seed and the position in the epoch. Without the last two, a resumed job repeats or skips examples. Write the checkpoint under a temporary name and rename it when complete, so a preemption mid-write cannot leave half a file as "latest". After two preemptions, move the job to a reserved GPU.

### The evaluation gate

The gate asks one question: is this adapter better than what the team could ship without it? So the baseline is the base model with the team's best prompt, not a weak prompt. Three checks run:

1. **Held-out split.** Code checks where a program can decide (an exact label, valid JSON), and an LLM judge with a fixed rubric otherwise.
2. **General regression set.** 300 prompts per base model on general instruction following and safety refusals. This catches catastrophic forgetting: the model gains the new task and loses old skills.
3. **Memorisation probe.** Unrelated prompts must not return training examples word for word.

500 held-out cases are noisy. At 80% accuracy the standard error is sqrt(0.8 x 0.2 / 500) = 1.8 points, so two separate scores can differ by 3 points by chance. Compare both models on the same cases and count flips. If the adapter fixes 60 cases and breaks 30, the net gain is 6 points and z = (60 - 30) / sqrt(60 + 30) = 3.2, above the 1.96 needed for 95% confidence. If it fixes 20 and breaks 12, z = 1.4 and the gate says "not proven". The report lists the broken cases: they show what the adapter unlearned.

### Registry, deployment and rollback

An adapter only makes sense with the exact base weights it was trained on. The registry stores the base model's content hash, and serving refuses to load an adapter onto any other hash. A new base version means retraining every adapter, so the registry keeps each dataset version and job spec to make a retrain one call.

Deploy adapters unmerged on the shared base. Merging adds the adapter into the base weights and removes the small per-request overhead, but costs a 14 GB copy per adapter. Reserve it for a team whose traffic fills dedicated replicas.

Rollback is an alias change. The previous adapter stays loaded for 24 hours after a promotion, so flipping the alias back needs no reload. Lineage also handles deletion: when a dataset must be removed, the registry finds and retires every adapter trained on it.

## Evaluation

**Per adapter, offline.** The gate above: task metric on the 10% held-out split against the base model with its best prompt, a 300-prompt regression set, and a memorisation probe. Results are paired case by case, and the gate needs a net gain of 3 points with z above 1.96.

**Judge quality.** When an LLM judge scores the task, label 100 held-out outputs by hand and report agreement with the judge, including agreement on the failing cases alone. Recheck when the judge model or rubric changes.

**Per adapter, online.** The canary is an A/B test: 5% of the alias's traffic, randomised by user, compared on the team's own outcome metric (ticket resolved, edit accepted), thumbs-down rate, latency and tokens per request. Low-traffic aliases stay in canary until they have enough requests, not for a fixed number of hours.

**The platform itself.** p95 queue wait, job success rate, failures split by cause (data, out of memory, preemption), GPU utilisation, and time from upload to a promotable adapter. Two numbers show whether the checks are honest. Escaped regressions: adapters rolled back after promotion. Advisor precision: when a team overrides "do not fine-tune", how often does the adapter then pass the gate?

**Guardrails.** PII scan before training, base hash check before loading, and an audit log entry for every promotion and rollback.

## Bottlenecks & mitigations

* 70B QLoRA jobs: 10% of jobs and 47% of GPU-hours on an average day. They set the fleet size and the worst queue waits.
* Evaluation: 800 prompts generated per adapter plus 1,300 judge calls. Judge rate limits cap how many gates run at once, so cache base model outputs per dataset version.
* Loading base weights at job start: 14 GB or 35 GB per job unless each node keeps the bases on local disk.
* Canary duration for low-traffic adapters, which can need days to collect enough requests for a decision.
* Human labelling for judge calibration, which does not scale with GPU count.

## Failure modes

* **The adapter scores below the base model.** Usually a wrong chat template, a learning rate that is too high, or too many epochs on small data. Mitigation: template rendering in the validator, safe defaults, and the gate blocks promotion.
* **Held-out leak.** Near duplicates on both sides of the split inflate the score. Mitigation: remove duplicates before splitting, and split by group (customer or thread) when examples are related.
* **Out of memory mid-run.** One very long example lands in a batch. Mitigation: a token cap in the validator, batches grouped by length, and a smaller batch with gradient accumulation.
* **Preemption loop.** A job on burst GPUs is interrupted again and again. Mitigation: checkpoints every 10 minutes, and a move to reserved GPUs after two preemptions.
* **Catastrophic forgetting.** The adapter wins on the task and loses general skills. Mitigation: the regression set, fewer epochs, a lower learning rate, or general examples mixed into the data.
* **Adapter loaded on the wrong base version.** Outputs degrade with no error. Mitigation: the base hash check in the registry and in serving.
* **Passes the gate, fails in production.** The training data does not look like real inputs. Mitigation: canary with rollback, and production samples added to the next held-out split.
* **Private data memorised.** A customer's details appear in outputs for another user. Mitigation: PII scan at upload, the memorisation probe, and per-team isolation of adapters.

## Follow-up questions interviewers ask

* A team has 200 examples and insists on fine-tuning. What do you tell them, and what do you offer?
* The base model gets a new version. How do you move 300 adapters to it?
* Training loss falls but the eval score does not move. How do you debug it?
* How would you add preference tuning with DPO, or distillation from a larger model, as job types?
* When is a hyperparameter sweep worth its GPU cost, and how would the scheduler treat it?
* Two teams want one adapter for two related tasks. One adapter or two, and how do you decide?

## Lessons that cover this

* [#6Hugging Face end to endFoundations](/ai/learn/hugging-face-end-to-end)
* [#9What is fine-tuning - LoRA, QLoRA, DoRABuild with LLMs](/ai/learn/fine-tuning-lora-qlora-dora)
* [#10Fine-tuning a model for a real use caseBuild with LLMs](/ai/learn/fine-tuning-real-use-case)
* [#18What is new in 2026 + revisionShip](/ai/learn/whats-new-2026-revision)
* [#20RL fine-tuningLater](/ai/learn/rl-fine-tuning)
* [#23Projects - RAG app, fine-tuned model, agent + evalsLater](/ai/learn/projects)

## Further reading

* [LoRA: Low-Rank Adaptation of Large Language ModelsPaperarxiv.org](https://arxiv.org/abs/2106.09685)
* [QLoRA: Efficient Finetuning of Quantized LLMsPaperarxiv.org](https://arxiv.org/abs/2305.14314)
* [Hugging Face PEFT documentationGuidehuggingface.co](https://huggingface.co/docs/peft)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAI code assistant: completion, chat and agent](/ai/problems/code-assistant)[NextEvaluation harness for LLM apps and agents](/ai/problems/llm-eval-harness)

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
