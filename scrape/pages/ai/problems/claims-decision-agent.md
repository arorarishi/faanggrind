# Insurance claims decision agent with RAG and a token budget — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/claims-decision-agent

[AI problems](/ai#problems)

GENAIGenAI systems#18Hard

# Insurance claims decision agent with RAG and a token budget

agentsragtoken budgethuman reviewaudit trailrules engineReported at Scale AI

## Problem statement

Design an agent that decides health insurance claims for an insurer receiving 30,000 claims a day. For each claim it reads the claim documents, finds the relevant clauses in the customer's policy with RAG, and proposes approve, partial or deny with the clauses that justify it. Small, clear claims are paid automatically. High-value or low-confidence claims go to a human adjuster. Every decision must be explainable years later, and each claim has a hard token budget.

## Requirements

### Functional

* Extract structured facts from claim documents: dates, diagnosis, line items, amounts.
* Apply eligibility rules and all amount arithmetic in code, with a recorded result per rule.
* Retrieve clauses from the exact policy version in force on the date of loss, and cite them in the decision.
* Route each proposal: pay automatically, or send to an adjuster with the draft and its evidence.
* Record an audit trail for every step, enough to reproduce and explain the decision.
* Stop work on a claim when its token budget is spent and hand it to a human.

### Non-functional

* 30,000 claims per day; automatic decisions within 5 minutes at p95, human-reviewed claims within 24 hours.
* Budget per claim: a hard cap of 40,000 tokens and 0.10 USD; average cost under 0.03 USD.
* Wrong-approval rate under 0.5% on audited automatic approvals; no automatic denial based on model judgement.
* Of claims with a confidence score of 0.9 or more, at least 98% match the adjuster's decision.
* 100% of decisions have clause ids, rule results and version numbers in the audit log, kept for an assumed 7 years.

## Back-of-the-envelope estimates

**Volume.** 30,000 claims/day is 0.35 per second. Nobody waits on an open connection, so claims go through a queue.

**Naive design.** Send the whole policy (40,000 tokens) and the claim documents (12 pages x 700 = 8,400 tokens) through a 5-step agent loop: 5 x 48,400 = 242,000 input tokens. At an assumed 3 USD per million on a large model that is 0.726 USD per claim, 21,780 USD/day.

**Budgeted path, tokens.**

* Extraction, small model, once: 8,400 + 400 = 8,800 in, 600 out.
* Rules: code, 0 tokens.
* Judgement, large model: instructions 1,200 + facts 600 + rule results 300 + 12 clauses x 350 = 4,200, so 6,300 in, 500 out.
* Verification, small model: 3 x 600 = 1,800 in, 60 out.

Typical total: 9,400 + 6,800 + 1,860 = 18,060 tokens. A second judgement call with 6 more clauses is 6,300 + 500 + 2,100 = 8,900 in and 500 out, total 27,460. One retry of the first call adds 6,800: 34,260, under the 40,000 cap.

**Cost per path.** Assumed prices per million tokens: small 0.25 in and 1.25 out, large 3 in and 15 out.

* Stops at rules: 0.0022 + 0.00075 = 0.00295 USD.
* One judgement: 0.00295 + 0.000525 + 0.0189 + 0.0075 = 0.0299 USD.
* Two judgements: 0.0299 + 0.0267 + 0.0075 = 0.0641 USD.

**Expected cost.** Assume 30% stop at rules, 49% need one judgement and 21% need two: 0.3 x 0.00295 + 0.49 x 0.0299 + 0.21 x 0.0641 = 0.029 USD per claim, 870 USD/day. That is 25 times less than the naive design.

**Review load.** 21,000 claims reach the agent. If 60% are paid automatically (12,600), 8,400 go to adjusters. At 6 minutes each that is 840 hours a day, or 120 adjusters working 7 hours.

**Audit storage.** 30,000 x 50 KB = 1.5 GB/day, 548 GB/year.

## API

```
POST /v1/claims
  body: { policy_id, claimant_id, loss_date, amount_claimed, documents: [uri] }
  -> 202 { claim_id, status: "received" }

GET  /v1/claims/{claim_id}
  -> { status, decision?, payable_amount?,
       reasons: [{ clause_id, clause_text, finding }], decided_by: rules | agent | human }

POST /internal/reviews/{claim_id}
  body: { reviewer_id, decision: approve | partial | deny | need_info,
          payable_amount, agrees_with_draft: bool, note }
GET  /internal/claims/{claim_id}/audit     -> ordered audit records
GET  /internal/claims/{claim_id}/budget    -> { tokens_small, tokens_large, usd_used, usd_cap }

Tools the agent sees (it has no tool that pays):
  get_claim_facts(claim_id)                 read: extracted fields
  get_rule_results(claim_id)                read: rule id, pass or fail, computed amounts
  search_policy(question, k <= 4)           read: clauses of this claim's policy version
  propose_decision(decision, line_items, clause_ids, notes)   writes a proposal only
```

## Data model

```
claims(claim_id PK, policy_id, policy_version_id, claimant_id, loss_date,
       amount_claimed, status, received_at)

claim_facts(claim_id, field, value, source_doc, page, field_confidence,
            extractor_version)

policy_clauses(clause_id PK, policy_version_id, section_path, clause_no, text,
               text_hash, linked_clause_ids[], embedding VECTOR(1024))
               -- every search filters on policy_version_id

rule_results(claim_id, rule_id, rules_version, passed, detail, computed_amount)

proposals(proposal_id PK, claim_id, decision, payable_amount, line_items,
          clause_ids[], confidence, route: auto | human, created_at)

reviews(claim_id, reviewer_id, decision, payable_amount, agrees_with_draft,
        note, decided_at)

budgets(claim_id PK, tokens_small, tokens_large, usd_used, usd_cap,
        model_calls, state: open | exhausted)

audit_log(seq PK, claim_id, event, actor, payload_ref, payload_hash, prev_hash,
          model, prompt_version, rules_version, tokens_in, tokens_out, usd, at)
          -- append-only
```

## High-level design

**Offline path**

1. Each policy document is parsed into clauses with a section path and clause number, then embedded and indexed under its `policy_version_id`. Endorsements are linked to the clauses they change.
2. Claims operations maintain the rules as versioned code with tests.
3. Past claims with adjusters' final decisions form the golden set and the training data for the confidence score.

**Online path**

4. **Intake.** The claim is stored, a budget row is opened and the claim id goes on a queue.
5. **Extraction.** OCR plus a small model turn the pages into typed fields, each with a page reference and a field confidence. This is the only step that reads the documents.
6. **Rules.** Code resolves the policy version in force on the loss date, then checks eligibility and computes amounts. A hard stop, such as a lapsed policy or a duplicate bill, ends the claim here with a reason code.
7. **Judgement.** The agent reads the facts and rule results, asks up to three coverage questions through `search_policy`, and writes a structured proposal with clause ids. It may ask for more clauses once.
8. **Verification.** Code checks that every cited clause exists in this policy version and recomputes the payable amount from the line items the model marked as covered. A small model checks that each clause supports its finding.
9. **Gate.** A proposal is paid automatically only if it is an approval, the amount is at most 25,000 INR, the confidence score is at least 0.9 and verification passed. Everything else goes to an adjuster.
10. **Review.** The adjuster sees the draft, clauses and rule results, and decides. Their decision is stored as a label.
11. **Audit.** Every step appends a record. The budget meter runs before each model call.

## Architecture diagram

Rendering diagram…

## Deep dives

### Rules in code, judgement by the model

If a claims manager can write a check as an if-statement over typed fields, it is code: policy in force on the loss date, waiting period served, sum insured left, room-rent limit, co-pay, deductible, duplicate bill number, required documents present. All arithmetic is code too. The model never adds line items or applies a co-pay. The model gets what code cannot do: turning scans into fields, matching a described treatment to clause wording ("is this procedure excluded as cosmetic?"), and drafting the explanation. Rules run first because they cost zero tokens and give the same answer every time, so an assumed 30% of claims never reach the large model. The rule results then enter the judgement prompt as facts, so the model does not derive them again. The rules version is stored with each decision.

### Retrieval over the right policy version

The most damaging retrieval error is a correct-looking clause from the wrong version of the policy. So code resolves the version in force on the loss date and applies it as a hard filter. The model cannot search across versions. Chunk by clause, not by size, and keep the section path and clause number. Use hybrid search, because clause numbers and defined terms are exact strings that embeddings blur. Contracts need two additions. When a clause says "subject to clause 4.2" or uses a defined term, code fetches the linked clause and the definition as well. And an endorsement that overrides the base wording is returned together with the clause it changes. Each question returns at most 4 clauses of about 350 tokens.

### The per-claim token budget

The runtime checks the budget before every model call: 40,000 tokens and 0.10 USD. A token on the large model costs 12 times one on the small model at the assumed prices, so the money cap is the real limit and tokens are counted per model. Four choices produce the typical 18,060 tokens. Extract once: 8,400 tokens of pages become 600 tokens of fields, and no later step sees a page again. Use the small model for extraction and verification, where the task is narrow. Retrieve 12 clauses instead of sending the 40,000-token policy. Allow at most one extra retrieval round and one retry. When the cap is hit, the claim goes to a human with the work done so far. It never forces a decision from a cut-off context. After each cost cut, run the golden set again: a saving that lowers agreement only moves cost to adjusters.

### Confidence and human review

A model that writes "confidence: 0.95" is not calibrated, so do not gate on that number. Build the score from signals code can see: retrieval scores, whether verification passed, the lowest field confidence from extraction, how many rules were close to their limits, claim type and amount. Fit a small classifier on past claims with the adjuster's final decision as the label, then check calibration: of claims scored 0.9 or more, at least 98% must match the adjuster. The gate is asymmetric. Approvals up to 25,000 INR with a high score are paid automatically. Every denial that rests on model judgement goes to a human, because a wrong denial harms a customer. A random 2% of automatic approvals, 252 a day, is audited, since otherwise nobody labels those claims. The 98% counts every kind of mismatch. The audit measures wrong approvals alone, and the score threshold rises if they pass 0.5%.

### An audit trail that can replay a decision

The log stores what was used, not only what was decided: a hash of the claim documents, the extracted fields, the policy version, clause ids with text hashes, the rules version with each result, prompt version, model id, token counts, the proposal, the score, the route and the reviewer's action. It is append-only, and each record holds the hash of the previous one, so an edited record is detectable. The explanation sent to the claimant is built from the stored clause ids at decision time. Do not ask a model to explain an old decision later: it will write a plausible reason, not the real one.

## Evaluation

**Golden set.** 2,000 past claims with the adjuster's final decision, payable amount and cited clauses, including claims that were overturned on appeal. Stratify by claim type and amount.

**Decision quality.** Agreement with the adjuster, payable amount within 1%, and two error rates reported separately: wrong approvals (money lost) and wrong denials (customer harmed). An average accuracy hides which one moved.

**Per stage.** Extraction accuracy per field, with amounts and dates checked exactly. Retrieval Recall@4 against the clauses the adjuster cited. Faithfulness: does each cited clause support its finding?

**Calibration.** Bucket claims by confidence score and compare with actual agreement. The 0.9 bucket must reach 98% before the gate uses it.

**Cost.** Tokens and USD per claim at p50 and p95, the share of claims that hit the cap, and the automatic-decision rate. Report them beside agreement on every change.

**Repeat runs.** Run each golden claim 3 times and count decision flips. A claim that flips is low confidence by definition.

**Online.** Start in shadow mode: the agent proposes, adjusters decide without seeing the draft, and disagreements are reviewed. Then show drafts, then enable automatic payment for small amounts. Track the adjuster override rate, the 2% audit of automatic approvals, appeal and overturn rates, and time to decision.

**Guardrails.** A kill switch that sends all claims to humans, a check that approval rates for similar claims do not differ across regions without a policy reason, and a blind sample: 5% of reviews hide the draft, to measure whether adjusters are only agreeing with the agent.

## Bottlenecks & mitigations

* Adjuster capacity: 8,400 reviews a day need 120 people, far more than any compute. Raising the automatic rate safely is the main lever on total cost.
* OCR and extraction on scanned bills and handwriting: slow, and its errors flow into every later step.
* The large-model judgement call is 0.0264 of the 0.0299 USD on a typical claim, so retrieval size and the second-call rate drive the bill.
* Rule maintenance: every new policy product adds rules and tests, and a wrong rule is applied at full volume the same day.
* Re-indexing and re-testing when policy wording changes, since old versions must stay searchable for old claims.

## Failure modes

* **A clause from the wrong policy version is cited.** The customer renewed and the wording changed. Mitigation: version resolved by code from the loss date, hard filter on every search, and verification that each clause id belongs to that version.
* **An extraction error changes the amount.** 18,000 is read as 78,000. Mitigation: line items must sum to the bill total, each field carries a confidence, and low-confidence amounts go to a human.
* **The model does arithmetic.** It applies the co-pay itself and gets it wrong. Mitigation: the model marks line items as covered or not; code computes every amount.
* **A confident wrong approval.** The score is high and the claim is paid. Mitigation: the 25,000 INR cap bounds each loss, the 2% audit measures the rate, and each miss becomes a golden-set case.
* **Instructions inside a claim document.** A scanned letter says "this claim is pre-approved". Mitigation: extraction returns typed fields only, the judgement step never sees raw pages, and the agent has no payment tool.
* **The budget runs out mid-claim.** Retrieval keeps returning weak clauses and the agent asks again. Mitigation: one extra round at most, cap enforced by the runtime, hand-off with partial work.
* **Adjusters approve every draft.** Review becomes a click. Mitigation: the blind 5% sample, override rate per adjuster, and drafts that show evidence before the proposed decision.
* **A decision cannot be reproduced.** The prompt or rules changed since. Mitigation: versions and hashes in every audit record; old prompt, rules and clause versions are kept.

## Follow-up questions interviewers ask

* Finance wants the cost per claim halved again. What do you cut first, and how do you prove quality held?
* A regulator asks why one claim was denied three years ago. Walk through what you retrieve and show.
* Why not put the whole policy in a cached prompt prefix and skip retrieval?
* Would you fine-tune a small model for the judgement step? What data and what risks?
* Fraud rings learn that claims under 25,000 INR are paid automatically. What changes?
* A new policy product launches next month. What must be built and tested before the agent handles it?

## Lessons that cover this

* [#15Agents in depth - patterns, reliability, securityAgents](/ai/learn/agents-in-depth)

## Further reading

* [FrugalGPT: How to Use Large Language Models While Reducing CostPaperarxiv.org](https://arxiv.org/abs/2305.05176)
* [Retrieval-Augmented Generation for Knowledge-Intensive NLP TasksPaperarxiv.org](https://arxiv.org/abs/2005.11401)
* [Building effective agentsArticleanthropic.com](https://www.anthropic.com/engineering/building-effective-agents)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousTracing and observability for LLM applications](/ai/problems/llm-observability)[NextChatGPT-like chat service](/ai/problems/chat-service)

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
