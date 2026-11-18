# Cut LLM cost by half: model routing and cascades — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/llm-cost-router

[AI problems](/ai#problems)

GENAIGenAI systems#22Medium

# Cut LLM cost by half: model routing and cascades

model routingcascadecostclassifierquality monitoring

## Problem statement

An assistant feature sends 2 million requests a day to one large model and the bill is 18,000 USD a day. Many requests are easy: greetings, lookups, short rewrites. Design the routing layer that sends each request to the cheapest model that is good enough, so that spend falls by at least half while answer quality stays within 1 point of today's pass rate (the share of answers a judge marks as acceptable). Two models are available: the large one and a small one that costs a tenth as much.

## Requirements

### Functional

* Choose a model for every request: small, large, or small first with escalation to large.
* Check a small-model answer before the user sees it when the router was not sure, and escalate if the check fails.
* Support a policy per feature: thresholds, intents that always go to the large model, and a kill switch that sends everything to large.
* Keep a random holdout that always uses the large model, so quality and saving can be measured without bias.
* Log every decision with its score, the model used, tokens, cost and the outcome, and use these logs to retrain the router.

### Non-functional

* LLM spend at least 50% below the all-large baseline, measured against the holdout.
* Pass rate on the golden set (a fixed list of test requests with known good answers) and on sampled live traffic no more than 1 point below all-large.
* The routing decision takes under 20 ms at p95.
* 2 million requests a day: 23 QPS on average, 80 QPS at peak.
* A one-day quality gap above 2 points on a feature switches that feature back to all-large automatically.

## Back-of-the-envelope estimates

All prices are assumptions: large model 3 USD per million input tokens and 15 USD per million output tokens; small model 0.30 and 1.50.

**Baseline.** A request has 1,500 input and 300 output tokens. Large: (1,500 x 3 + 300 x 15) / 1,000,000 = 0.009 USD. Small: 0.0009 USD. All-large: 2,000,000 x 0.009 = 18,000 USD/day.

**Classifier routing.** If a share f goes to small, cost per request = 0.009 - f x 0.0081. Half price needs f = 0.0045 / 0.0081 = 0.56. At f = 0.65: 0.65 x 0.0009 + 0.35 x 0.009 = 0.003735 USD, a 58.5% saving, 10,530 USD/day.

**Cascade.** Every request pays for small, plus a check, plus large when it escalates. A verifier call on the small model reads 1,800 tokens and writes 20: 0.00057 USD. With 30% escalation: 0.0009 + 0.00057 + 0.30 x 0.009 = 0.00417 USD, a 53.7% saving. Half price needs escalation under 34%.

**Both.** Classifier sends 55% straight to small and 25% straight to large. The unsure 20% run the cascade and 40% of them escalate: 0.55 x 0.0009 + 0.25 x 0.009 + 0.20 x (0.0009 + 0.00057 + 0.40 x 0.009) = 0.003759 USD, a 58.2% saving, with small serving 67% of traffic.

**Quality.** Loss in pass rate = share served by small x gap between large and small on those requests. For a 1-point loss at f = 0.65 the gap must stay under 1 / 0.65 = 1.5 points.

**Latency.** An escalated request waits for the small answer first: 300 tokens x 10 ms = 3 s before the large model starts.

**Labels.** 20,000 sampled requests answered by both models and judged: 20,000 x 0.0009 = 18 USD of small calls. A judge call on the large model reads 2,000 tokens and writes 100, so 0.0075 USD; 40,000 of them cost 300 USD.

## API

```
POST /v1/route                         (called in process or as a sidecar)
  body:    { request_id, feature, messages, max_tokens,
             metadata?: { intent, language, conversation_id } }
  returns: { decision_id, plan: "small" | "large" | "small_then_check",
             score, thresholds: { low, high }, arm: "routed" | "holdout",
             policy_version, router_version }

POST /v1/check                         (cascade only)
  body:    { decision_id, answer }
  returns: { accept: true | false, check_score, failed_checks[] }

POST /v1/outcomes
  body:    { decision_id, model_used, escalated, tokens_in, tokens_out,
             cost_usd, ttft_ms, user_feedback? }

PUT  /admin/policies/{feature}
  body:    { mode: "classifier" | "cascade" | "hybrid" | "all_large",
             low, high, holdout_pct, forced_large_intents[],
             max_escalation_rate }
GET  /admin/report?feature=&from=&to=
  returns: { share_small, escalation_rate, saving_pct, pass_rate_routed,
             pass_rate_holdout, gap }
```

## Data model

```
routing_policies(feature PK, mode, low, high, holdout_pct,
                 forced_large_intents[], max_escalation_rate,
                 router_version, policy_version, updated_at)

decisions(decision_id PK, request_id, feature, arm, policy_version,
          router_version, score, plan, model_used, escalated,
          check_score, tokens_in, tokens_out, cost_usd, ttft_ms,
          created_at)

labels(request_id PK, small_answer_ref, large_answer_ref,
       small_pass BOOL, large_pass BOOL, judge_version,
       human_checked BOOL)
       -- target for training: small_is_enough = small_pass OR NOT large_pass

router_models(router_version PK, trained_on, features[],
              cost_quality_curve, status)

router input features: request embedding (384 dims), token count,
  intent, language, turn number, has_code, has_table,
  number of retrieved chunks
```

## High-level design

**Offline path (build the router)**

1. Sample 20,000 real requests. Each already has a large-model answer; generate the small-model answer too.
2. A judge model with a fixed rubric marks each answer pass or fail. The judge is checked against 100 human labels first.
3. Label each request `small_is_enough`: true when the small answer passes, or when both fail (the large model would not have helped).
4. Train a small classifier on the request embedding and a few cheap features. It outputs a score from 0 to 1: the chance that small is enough.
5. On a held-out part of the labels, compute the cost-quality curve and pick two thresholds, `low` and `high`.

**Online path (every request)**

6. Policy first: forced-large intents and the kill switch go to the large model. A random 2% holdout also goes to large.
7. The classifier scores the request in a few milliseconds.
8. Score above `high`: the small model answers and streams to the user.
9. Score below `low`: the large model answers.
10. In between: the small model answers, the answer is held back, and the checks run. Pass: the user gets it. Fail: the same prompt goes to the large model.
11. The decision and its outcome are logged.

**Feedback loop**

12. A nightly job judges a sample from the routed arm and from the holdout, reports the gap and the saving per feature, and adds the new labels to the training set. The router is retrained weekly and its thresholds are re-picked.

## Architecture diagram

Rendering diagram…

## Deep dives

### Classifier before, or cascade after

A classifier decides before any generation. It costs a few milliseconds, the chosen model streams at once, and each request pays for one model. Its weakness is that it guesses difficulty from the question alone: "is this refund allowed?" looks easy and may not be.

A cascade decides after seeing the small model's answer, so it has more evidence. It pays for the small model on every request and for both on escalated ones, and an escalated user waits about 3 seconds longer. The small answer cannot stream until it has been checked, so time to first token gets worse for the whole cascade path.

Use both. The classifier handles the confident ends, and the cascade handles only the unsure middle, which keeps its latency cost to about 20% of traffic.

### Was the cheap answer good enough?

The checks, cheapest first:

* **Code checks.** Valid JSON, required fields, cited ids that exist, no "I am not sure" phrasing. Free.
* **Token probabilities.** A low average log-probability on a short answer, such as a label or an extracted value, signals doubt. It is weak for long free text.
* **A verifier.** A small model reads the question and the answer and scores it. This is the 0.00057 USD check.

Do not trust the small model's own confidence rating without measuring it against labels. Treat every check as a classifier and score it on the labelled set. A false accept (a bad answer let through) is lost quality. A false reject is wasted money.

### Picking the thresholds

Sort the held-out labels by router score. For each threshold, compute the share sent to small and the pass rate of the mix. This gives a cost-quality curve. Choose the point with the largest saving whose loss is under 1 point. Compare it with random routing at the same share: a router that is no better than random is not worth running. For example, the curve may show that `high` = 0.8 sends 55% to small for a 0.6-point loss, while 0.6 sends 70% for a 1.8-point loss. Only the first meets the bar. Redo this whenever a model, a price or the prompt changes.

### Keeping quality from drifting

The router only sees outcomes for the model it chose, so its own logs are biased. The 2% holdout fixes that: it gives an all-large pass rate on the same day's traffic. It costs little: savings are multiplied by 0.98, so 58.2% becomes 57.1%. Each night, judge 5,000 answers from each arm. Alert when the 7-day gap passes 1 point, when the share sent to small jumps, or when the score distribution shifts. Switch the feature to all-large when one day shows a 2-point gap. Pin both model versions, and re-run the label set before accepting a new one.

## Evaluation

**Offline, the router.** The metric is the cost-quality curve on held-out labels, not classifier accuracy. Report the saving at a 1-point loss. Two reference lines make it readable: random routing at the same share, and an oracle that sends every request the small model can handle to small. If small passes on 80% of requests, the oracle saves 72%, so a router at 58% has room left.

**Offline, the check.** On labelled small-model answers, measure the false-accept rate and the false-reject rate of the cascade check at its threshold.

**The judge.** Every number above depends on it. Compare the judge with 100 human labels, report agreement on the failing cases separately, and repeat when the judge model or rubric changes.

**Online A/B.** The holdout is the control. Per arm, track judged pass rate, thumbs-down rate, rephrase rate (a rephrase right after an answer signals a miss), p95 time to first token, escalation rate and cost per request. With 5,000 judged answers per arm per day at a 92% pass rate, the 95% range on the gap is about plus or minus 1.1 points, so one day can show a 2-point gap but not a 1-point one. Seven days narrow it to plus or minus 0.4 points. The daily judging costs 10,000 x 0.0075 = 75 USD.

**Guardrails.** Automatic switch to all-large on a 2-point daily gap or when escalation passes the policy's maximum. High-risk intents (complaints, legal, payments) never go to the small model.

## Bottlenecks & mitigations

* Labels: every new model, prompt or price needs both models' answers on the sample, judged again, before thresholds can be trusted.
* The cascade path: about 3 seconds of extra wait on escalated requests, and no streaming until the check has passed.
* The classifier runs on every request and needs an embedding; it has to stay inside the 20 ms budget at 80 QPS.
* Switching models between turns of one conversation loses the prefix cache on both, so route per conversation where possible.

## Failure modes

* **Hard requests routed to the small model.** They look easy on the surface. Mitigation: forced-large intents, the cascade check for the unsure band, and the holdout gap as the alarm.
* **Traffic shifts.** A new feature or language arrives that the router never saw, and its scores mean nothing there. Mitigation: watch the score distribution, send inputs unlike the training data to large, retrain weekly.
* **Escalation storm.** A strict check or a weaker small-model version escalates most requests. Above 84% escalation the cascade costs more than all-large. Mitigation: alert on escalation rate and fall back to classifier-only mode.
* **A model changes under a fixed name.** The provider updates the small model and its pass rate drops. Mitigation: pin versions and re-run the label set before any switch.
* **The judge drifts.** A new judge version scores more strictly, which looks like a quality drop. Mitigation: store `judge_version` with every label and recalibrate against human labels.
* **Uneven experience.** One user gets a strong answer and then a weak one in the same chat. Mitigation: sticky routing per conversation, and escalate only upward.

## Follow-up questions interviewers ask

* A third, medium-priced model is added. How do the thresholds and the cascade change?
* The large model's price drops by half. What do you recompute, and is the router still worth running?
* An agent makes 20 model calls per task. Do you route per call or per task?
* When is fine-tuning the small model on the large model's answers better than routing?
* How would you route a feature whose quality cannot be judged automatically?
* What would you try before routing to cut the bill: prompt trimming, caching, batch pricing?

## Lessons that cover this

* [#7Prompting and context engineeringBuild with LLMs](/ai/learn/prompting-context-engineering)
* [#17LLM system designShip](/ai/learn/llm-system-design)
* [#22Advanced topicsLater](/ai/learn/advanced-topics)
* [#24LLMs on cloud - Bedrock, Azure OpenAI, Vertex AILater](/ai/learn/llms-on-cloud)

## Further reading

* [FrugalGPT: How to Use Large Language Models While Reducing CostPaperarxiv.org](https://arxiv.org/abs/2305.05176)
* [RouteLLM: Learning to Route LLMs with Preference DataPaperarxiv.org](https://arxiv.org/abs/2406.18665)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousReal-time voice AI agent](/ai/problems/realtime-voice-agent)[NextInference batching system for one GPU](/ai/problems/llm-inference-batching)

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
