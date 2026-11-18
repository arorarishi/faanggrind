# Evaluation harness for LLM apps and agents — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/llm-eval-harness

[AI problems](/ai#problems)

GENAIGenAI systems#13Medium

# Evaluation harness for LLM apps and agents

evalsllm-as-judgegolden setregression gatecalibrationonline metricsReported at Anthropic, Perplexity

## Problem statement

Design an evaluation platform for a company that runs 30 LLM features: retrieval-based assistants, extraction pipelines and tool-using agents. Every change to a prompt, a model or the code around them must be scored on a golden set (a fixed list of inputs with the expected result) before it merges. 2 million production requests a day must be sampled and scored with the same metrics. The platform also needs a workflow for the hardest failure to catch: answers that are confident and wrong.

## Requirements

### Functional

* Store versioned golden sets per app: inputs, expected outputs or properties, tags, and a split into tuning and held-out cases.
* Score outputs with three scorer types: code checks, LLM judges with a written rubric, and human labels.
* Run a candidate (prompt version, model, commit) on a golden set in CI, the automatic checks on every code change. Compare it with the baseline case by case and return a pass or fail gate.
* Check every judge against human labels, and stop using it when agreement drops.
* Sample production traces (the stored record of one request: prompt, context, tool calls, output), score them with the same judges, and show quality by app, prompt version and model version.
* Queue suspicious traces for human review, and turn labelled failures into new golden cases.

### Non-functional

* A full run of 400 cases finishes in under 10 minutes; a 50-case smoke run in under 2 minutes.
* 150 CI runs per day and a 1% production sample, for under 250 USD per day in model spend.
* A rerun with no change is blocked by the gate in fewer than 5% of runs.
* Each judge agrees with human labels on at least 85% of cases and catches at least 70% of human-labelled failures, rechecked on every judge or rubric change.
* A sampled production trace has its scores within 15 minutes.
* Every score is reproducible: it stores the dataset version, judge version, prompt version, model and commit.

## Back-of-the-envelope estimates

**One CI run.** 400 cases. The app call averages 3,000 input and 400 output tokens: 1.2M and 0.16M tokens. A judge scores the 60% of cases that code cannot check: 240 calls x 2,500 input and 200 output tokens = 0.6M and 0.048M. Total: 1.8M input and 0.208M output. At an assumed 1 USD and 5 USD per million that is 1.80 + 1.04 = 2.84 USD.

**CI per day.** 150 full runs would cost 150 x 2.84 = 426 USD. Run a 50-case smoke subset on every push (2.84 x 50 / 400 = 0.355 USD) and the full set only before merge: 110 x 0.355 + 40 x 2.84 = 39 + 114 = 153 USD per day.

**Run time.** 400 cases x 6 s / 32 in parallel = 75 s. An agent set of 100 tasks x 3 runs x 60 s / 32 = 563 s, about 9.4 minutes.

**Noise.** At an 85% pass rate on 400 cases the standard error is sqrt(0.85 x 0.15 / 400) = 1.8 points. The difference between two such runs has a standard error of 1.8 x 1.41 = 2.5 points, so only a gap above 1.96 x 2.5 = 4.9 points is real. Seeing a 2-point change this way needs 2 x 0.85 x 0.15 x (1.96 / 0.02)^2 = about 2,450 cases.

**Online.** 2M requests x 1% = 20,000 judged traces a day: 50M input and 4M output tokens, so 50 + 20 = 70 USD per day. CI plus online is 223 USD.

**Humans.** One judge calibration is 100 cases x 2 labellers x 2 minutes = 400 minutes, about 6.7 hours.

**Storage.** 110 x 50 + 40 x 400 + 20,000 = 41,500 result rows a day at 8 KB each: 0.33 GB per day, about 121 GB a year.

## API

```
POST /v1/datasets/{app}/versions
  body: { cases: [{ case_id, input, expected?, checks: [], tags: [],
                    split: "tune" | "heldout" }] }     -> { dataset_version }

POST /v1/runs
  body: { app, candidate: { prompt_version, model, commit },
          dataset_version, mode: "smoke" | "full",
          baseline_run_id?, repeats?: 3 }               -> { run_id }
GET  /v1/runs/{run_id}
  -> { status, pass_rate, by_tag, cost_usd, p95_latency_ms,
       vs_baseline: { fixed, broken, net_points, z },
       hard_check_failures, gate: "pass" | "fail" }
GET  /v1/runs/{run_id}/cases?flipped=true
  -> [{ case_id, baseline_output, candidate_output, scores, trace_id }]

POST /v1/online/scores            (async, called by the trace pipeline)
  body: { trace_id, app, sample_reason: "random" | "thumbs_down" | "escalated" }
POST /v1/labels
  body: { target_id, rubric_version, label: "PASS" | "FAIL", cause?, labeller }
GET  /v1/judges/{judge_id}/calibration
  -> { judge_version, cases, agreement, fail_recall, kappa, status }
```

## Data model

```
golden_cases(case_id, dataset_version, app, input, expected, checks[],
             tags[], split, source: handwritten | production | incident)

runs(run_id PK, app, dataset_version, prompt_version, model, commit,
     mode, baseline_run_id, pass_rate, cost_usd, gate, created_at)

results(run_id FK, case_id, repeat, output, trace_id,
        tokens_in, tokens_out, latency_ms, cached BOOL)
scores(run_id FK, case_id, repeat, scorer_id, scorer_version,
       verdict: PASS | FAIL, evidence, reason)

judges(judge_id, judge_version PK, model, rubric_text, status)
calibrations(judge_version FK, cases, agreement, fail_recall, kappa, at)

online_scores(trace_id, app, prompt_version, model, sample_reason,
              scorer_version, verdict, hedged BOOL, scored_at)
labels(target_id, rubric_version, label, cause, labeller, at)
review_queue(trace_id, reason, priority, state)
```

## High-level design

**Offline path (before merge)**

1. A developer changes a prompt, a model or code. CI calls the harness with the candidate and the app's golden set version.
2. The runner sends each case through the app's real entry point, 32 in parallel, with retries on rate limits. It stores the output, trace id, tokens, latency and cost. Outputs are cached by input hash, prompt version, model and commit, so a change to a rubric does not rerun the app.
3. Scorers run on each output: code checks first, then the judge for the cases that need meaning. Agent tasks run 3 times and are scored on the end state.
4. The comparator pairs every case with the baseline result from the main branch and counts fixed and broken cases.
5. The gate fails on any hard check, or on a significant net regression. The pull request shows the broken cases with both outputs side by side.

**Online path (after deploy)**

6. The trace pipeline samples 1% of traffic at random. It also picks every trace with a thumbs-down or an escalation, marked with its reason.
7. The same judges score the sampled traces. Dashboards use only the random sample, split by app, prompt version and model version.
8. A review queue collects flagged traces and confident answers that the judge failed. People label them and note the cause.
9. Labels go two ways: into the next golden set version as new cases, and into judge calibration.

## Architecture diagram

Rendering diagram…

## Deep dives

### Pick the cheapest scorer that is honest

Code checks cost nothing and never drift: exact match on a label, schema validity, a unit test, the database row an agent should have changed. Use them for everything a program can decide. A judge handles meaning: faithfulness, relevance, completeness. Its rubric asks for evidence first and a PASS or FAIL verdict last, never a 1 to 10 score. People are the slowest scorer, so spend them on writing rubrics, calibrating judges and labelling the review queue.

### Check the judge against humans

A judge is a model plus a prompt, so version it and test it. Two people label 100 cases and the judge labels the same 100. Say humans fail 20, and the judge agrees on 76 passes and 14 fails. Agreement is 90%, but it catches only 14 of 20 failures (70%). Cohen's kappa, which removes agreement by chance, is (0.90 - 0.692) / (1 - 0.692) = 0.68. The 6 missed failures are what would reach users, so read them and fix the rubric. Pin the judge model version, because a silent upgrade moves every score.

### The regression gate and noise

Two separate 400-case runs differ by up to 4.9 points by chance, so "the score fell 2 points" cannot block a merge. Pair the cases. If 22 cases broke and 8 were fixed, the net change is 3.5 points down and z = (22 - 8) / sqrt(22 + 8) = 2.6, above 1.96: block. If 12 broke and 9 were fixed, z = 0.65: pass. A case that flips between two runs of the same version is flaky. Run it 3 times and take the majority. Hard checks, such as a permission leak, skip the statistics: one failure blocks.

### Online success metrics for an AI feature

Offline scores say whether to ship. Online metrics say whether users got value. Pick one outcome metric tied to the task: ticket resolved without a human, suggestion accepted and kept, answer not followed by a rephrase. Add guard metrics that must not get worse: thumbs-down rate, escalations, p95 latency, cost per successful task. Do not count messages sent, because a confusing answer produces more of them.

### Investigating confident wrong answers

These answers carry no hedge (words of doubt such as "I think") and no refusal, so users act on them.

1. **Find.** Judge FAIL on correctness with no hedge in the text, thumbs-down, user corrections.
2. **Reproduce.** Rerun the trace 5 times with the same prompt version, model and context. Wrong every time is systematic. Wrong sometimes is sampling noise.
3. **Localise.** Right context missing: retrieval. Context stale or contradictory: data. Context right, answer wrong: prompt or model. Gold label wrong: the eval.
4. **Fix the largest cause**, add the cases to the golden set, and track accuracy on unhedged answers as its own metric.

## Evaluation

The harness is itself a measuring tool, so measure it.

**Judges.** Agreement, failure recall and kappa against 100 human labels per judge version. The ceiling is how often two people agree with each other, so measure that as well.

**Gate false alarms.** Run the same version twice (an A/A run) every night. The gate should block fewer than 5% of these.

**Gate misses.** Seed known regressions: delete an instruction from the prompt, turn retrieval off, swap in a weaker model. The gate must fire on each. A gate that never fails a seeded break is not protecting anyone.

**Offline against online.** For each release, compare the change in offline pass rate with the change in the online outcome metric from a 5% A/B test, randomised by user. If offline goes up while online goes down, the golden set no longer matches production.

**Golden set health.** Share of cases added in the last 90 days, share that came from production failures, coverage by tag, and the number of cases that passed the last 20 runs. Cases that always pass stay as regression checks, but new hard cases must keep arriving.

**Escaped regressions.** Every production incident that the gate passed becomes a golden case, and the count per month is the harness's headline number.

**Guardrails.** PII is masked before a trace enters the review queue. Held-out cases are checked by hash against few-shot prompts and fine-tuning data.

## Bottlenecks & mitigations

* Model and judge rate limits: 32 parallel calls per run across 150 runs a day compete with production unless CI has its own quota.
* Agent tasks: 60 s each, 3 runs per task. They set the 10-minute run time.
* Human labelling: 6.7 hours per calibration, and the review queue fills faster than people can label, so it needs a priority order.
* Online judge cost grows with the sample rate: 1% is 70 USD a day, 10% is 700 USD.
* Agent evals need a sandbox with state reset for every run, which is slower to start than the model call.

## Failure modes

* **Judge drift.** The judge model is updated and every score moves with no app change. Mitigation: pin the version, recalibrate on change, and score a fixed anchor set of 50 labelled cases every night.
* **Stale or overfitted golden set.** Prompts are tuned on the cases they are scored on, so offline rises while users complain. Mitigation: a held-out split, new cases from production failures, and the offline against online comparison.
* **Flaky gate.** Random flips block unrelated changes and developers learn to ignore the gate. Mitigation: paired comparison, repeats for flaky cases, and the nightly A/A check.
* **Judge that passes everything.** 90% agreement hides missed failures. Mitigation: report failure recall and kappa, not only agreement.
* **Biased online sample.** Only thumbs-down traces are scored, so the dashboard shows a quality number that means nothing. Mitigation: metrics from the random sample only; flagged traces go to review.
* **Eval run with real side effects.** An agent task sends a real email or refund. Mitigation: sandboxed tools with fake backends, reset for every run.
* **Golden cases leak into prompts.** A case is copied into few-shot examples and the score becomes a memory test. Mitigation: hash checks between held-out cases and prompt or training data.

## Follow-up questions interviewers ask

* The offline score rose 4 points and the online resolution rate fell. What do you check first?
* The judge agrees with humans on 90% of cases but only 60% of failures. What do you change?
* How do you evaluate an agent when more than one tool sequence is correct?
* How many cases do you need to detect a 1-point regression, and how do you get there cheaply?
* How do you evaluate a feature before launch, when there is no production traffic to sample?
* A team wants to gate on the judge's 1 to 10 quality score. What do you tell them?

## Lessons that cover this

* [#10Fine-tuning a model for a real use caseBuild with LLMs](/ai/learn/fine-tuning-real-use-case)
* [#16Evals, tracing and guardrailsShip](/ai/learn/evals-tracing-guardrails)
* [#20RL fine-tuningLater](/ai/learn/rl-fine-tuning)
* [#23Projects - RAG app, fine-tuned model, agent + evalsLater](/ai/learn/projects)

## Further reading

* [Judging LLM-as-a-Judge with MT-Bench and Chatbot ArenaPaperarxiv.org](https://arxiv.org/abs/2306.05685)
* [G-Eval: NLG Evaluation using GPT-4 with Better Human AlignmentPaperarxiv.org](https://arxiv.org/abs/2303.16634)
* [tau-bench: A Benchmark for Tool-Agent-User InteractionPaperarxiv.org](https://arxiv.org/abs/2406.12045)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousLoRA fine-tuning pipeline with an adapter registry](/ai/problems/fine-tuning-pipeline)[NextPrompt-injection defence for a tool-using agent](/ai/problems/prompt-injection-defence)

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
