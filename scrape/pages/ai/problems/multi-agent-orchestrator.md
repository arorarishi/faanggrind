# Multi-agent orchestrator for deep research — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/multi-agent-orchestrator

[AI problems](/ai#problems)

GENAIGenAI systems#9Hard

# Multi-agent orchestrator for deep research

multi-agentorchestrator and workerssub-agentscost controltracingdeep research

## Problem statement

Design a deep-research service. A user asks a broad question, such as "compare eight payment vendors on price, security and support". A lead agent splits it into independent sub-questions, worker agents research them in parallel with their own context and search tools, and the lead writes one cited report. The service produces 20,000 reports a day and must finish each in under 10 minutes. It must also decide, per request, whether one agent is enough, because several agents cost about three times as much.

## Requirements

### Functional

* Accept a research question and return a cited report, with streamed progress for each sub-question.
* Triage every request: one agent for a narrow question, a lead agent with workers for a broad one.
* The lead plans the sub-questions. Workers run in parallel, each with its own context, read-only tools and budget.
* Workers return structured findings (claim, source URL, quote), not transcripts. The lead may run one more round to fill gaps.
* A failed or slow worker must not fail the report. The report states what could not be answered.
* Every claim in the report traces back to a finding, to the worker that produced it and to the page it came from.

### Non-functional

* 20,000 reports per day; about 500 agent loops running at the same time at peak.
* Report ready in under 3 minutes at p50 and under 10 minutes at p95; first progress event within 2 s.
* Average cost under 1 USD per multi-agent report, with a hard cap per task (default 3 USD) enforced in code.
* Citation precision of at least 0.95: 95% of cited claims are supported by the quoted source.
* At most 8 workers per task, 2 rounds, and depth 1: a worker cannot start workers.
* 99.5% of tasks end with a report or a clearly marked partial report.

## Back-of-the-envelope estimates

**Mix.** 20,000 reports/day: triage sends 12,000 (60%) to one agent and 8,000 (40%) to the orchestrator.

**Single agent.** 15 steps. The prefix is 2,500 tokens, and each step adds a 2,000-token search result and 200 output tokens. Input = 15 x 2,500 + 2,200 x (0 + 1 + ... + 14) = 37,500 + 231,000 = 268,500 tokens. Output = 15 x 200 + a 1,500-token report = 4,500.

**Multi-agent.** 6 workers x 10 steps. One worker: 10 x 2,500 + 2,200 x 45 = 124,000 input tokens. Six workers: 744,000. The lead's 4 calls (plan, gap check, synthesis, revision) average 8,000 input tokens: 32,000. Total 776,000, 2.9 times the single agent. Output: 6 x (10 x 200 + 1,500 of findings) + 4,000 for the lead = 25,000.

**One agent, 60 steps?** 60 x 2,500 + 2,200 x 1,770 = 4,044,000 input tokens, 5.2 times the multi-agent run, and the last step carries 132,300 tokens. Separate contexts reset the quadratic growth.

**Cost.** At an assumed 1 USD and 5 USD per million input and output tokens: single = 0.2685 + 0.0225 = 0.29 USD; multi = 0.776 + 0.125 = 0.90 USD. Per day: 12,000 x 0.291 + 8,000 x 0.901 = 3,492 + 7,208 = 10,700 USD. Six workers for every request would cost 20,000 x 0.901 = 18,020 USD, so triage saves about 7,300 USD a day.

**Latency.** A step takes about 8 s (5 s model, 3 s search and fetch), so a worker needs 10 x 8 = 80 s. Six in parallel take 80 s, not 480 s. Add 60 s for the lead and 10 s for the citation check: about 150 s.

**Concurrency.** Multi: 8,000 / 86,400 x 5 (peak) = 0.46 tasks/s x 150 s = 69 tasks, or 417 worker loops. Single: 0.69 tasks/s x 120 s = 83 loops. About 500 in total.

## API

```
POST /v1/research
  body: { question, mode?: "auto" | "single" | "multi", max_usd?, sources? }
  ->    { task_id }

GET  /v1/research/{task_id}/events                 (server-sent events)
  triage.done { mode } | plan.created { subquestions[] } |
  worker.started { worker_id, subquestion_id } | worker.finished { status } |
  report.delta | done { report_id, cost_usd, unanswered[] }

GET  /v1/research/{task_id}/report
  -> { markdown, claims: [{ claim_id, finding_ids[] }], unanswered[] }
GET  /v1/research/{task_id}/trace       -> span tree for the whole task
POST /v1/research/{task_id}/cancel

Lead-to-worker contract (a tool the lead calls; executed by orchestrator code)
spawn_workers([{ subquestion, why_it_matters, out_of_scope[], covered_by_others[],
                 output_schema, budget: { steps, tokens, seconds } }])
  -> [{ worker_id, status: "done" | "partial" | "failed",
        findings: [{ claim, source_url, quote, confidence }], gaps[], tokens_used }]
```

## Data model

```
tasks(task_id PK, user_id, question, mode: single | multi, status,
      budget_usd, spent_usd, created_at, finished_at)

plans(task_id, round, subquestions: [{ id, text, out_of_scope[], depends_on[] }],
      created_by_span)

agent_runs(run_id PK, task_id, parent_run_id, role: lead | worker | verifier,
           subquestion_id, model, status, steps, tokens_in, tokens_out, stop_reason)

findings(finding_id PK, task_id, run_id, subquestion_id, claim, source_url,
         quote, page_hash, confidence, created_at)
         -- shared and append-only: workers write, the lead reads

pages(page_hash PK, task_id, url, fetched_at, text_uri)   -- fetch cache per task

report_claims(task_id, claim_id, text, finding_ids[], verified: bool)

spans(trace_id = task_id, span_id PK, parent_span_id, run_id,
      kind: model | tool | spawn | decision, input_ref, output_ref,
      tokens, latency_ms, started_at)
```

## High-level design

1. **Triage.** One small-model call lists the sub-questions it sees in the request and marks whether each depends on another. A rule in code picks the path: at least 3 independent sub-questions go to the orchestrator, everything else to a single agent loop.
2. **Plan.** The lead agent writes 3 to 8 sub-questions. Each has a scope, an out-of-scope list and an output schema. The plan is stored and shown to the user as progress.
3. **Spawn.** The lead calls `spawn_workers`. Plain orchestrator code, not a model, starts one worker run per sub-question, splits the task budget and sets a deadline.
4. **Research.** Each worker runs its own loop of about 10 steps with two read-only tools, search and fetch. It sees only its brief, never the lead's history or another worker's context.
5. **Write findings.** A worker stores each finding with the claim, the URL and the exact quote. Fetched pages go into a per-task cache keyed by URL, so no page is fetched twice.
6. **Return.** A worker returns at most 1,500 tokens: its findings, its gaps and a status. A worker that hits its budget returns what it has as `partial`.
7. **Gap check.** The lead reads the results. If a sub-question has no supported answer, it may start one more round with narrower briefs. Two rounds is the limit.
8. **Synthesis.** The lead writes the report from the findings only. Each claim lists the finding ids that support it.
9. **Verify.** A verifier call with no tools checks each claim against its quotes. Unsupported claims are removed or marked, and unanswered sub-questions are listed.
10. **Trace.** Every model call, tool call, spawn and decision is a span with a parent id, stored under the task id.

## Architecture diagram

Rendering diagram…

## Deep dives

### One agent or several: decide per request

Several agents pay off only when the sub-questions are independent, can run in parallel, and are each large enough to fill a context. "Compare eight vendors" fits: nothing learned about vendor A changes the search for vendor B. "Why did our churn rise in March" does not fit. Each finding decides the next query, so one loop that sees everything is better, and it costs a third as much. The triage call only lists sub-questions and their dependencies. The decision itself is a rule in code, so it can be tested and tuned. Misroutes are handled in both directions. A single agent that reaches 70% of its context can hand the task to the orchestrator with its notes, and a lead that plans fewer than 3 sub-questions falls back to the single loop.

### Orchestrator and workers, not handoffs

In a handoff, agent A passes the conversation and control to agent B and leaves. That suits support flows with separate departments. In research nobody would own the final report, and each transfer loses context. Here control always returns to the lead, and plain code does the spawning, so worker limits, budgets and deadlines do not depend on a model following instructions.

Three kinds of state are kept apart. Passed down: a brief with the sub-question, why it matters, what is out of scope, what the other workers cover, the output schema and the budget. The lead's history is not passed. Passed up: at most 1,500 tokens of structured findings, never the transcript. Shared: the append-only findings store and the page cache. Workers never read each other's contexts or edit each other's findings, so there are no write conflicts to resolve. Most duplicated work comes from a vague brief, which is why the brief names what the others cover.

### Cost multiplies, so cap it in code

Each worker pays its own prefix on every call and has its own quadratic growth. The estimate above gives 2.9 times a single run, and a lead that starts 8 workers for a simple question wastes most of that. Four controls keep it bounded. The task budget is split before spawning: 20% is reserved for the lead and the rest is divided among the workers. A worker that reaches its share stops and returns partial findings. Workers can run on a smaller, cheaper model than the lead: they send 744,000 of the 776,000 input tokens, so that is where the price matters. Tool results are capped at 2,000 tokens. Report cost per report next to quality, split into lead and workers.

### Failure isolation

A worker can time out, loop, or hit a site that blocks it. Each worker is a separate run with its own step, token and time limits, so it can only spend its own share. The orchestrator waits until every worker has finished or a 4-minute deadline passes, then continues with what exists. A failed worker returns `failed` with its gaps. The lead may retry it once with a narrower brief, never more. The report lists unanswered sub-questions and does not guess. Isolation also limits prompt injection: workers read untrusted pages but hold only read tools, and the lead sees schema-checked findings, never raw pages.

### Tracing who decided what

The task id is the trace id, and every model call, tool call and spawn is a span with a parent. A claim in the report points to findings, a finding to a worker run, and the run to the fetch span and the page hash. When a report is wrong, walk back through four questions. Was the page wrong? Did the worker extract it wrongly? Did the lead drop or distort a correct finding? Did the plan never ask? Each answer needs a different fix: source ranking, the worker prompt, the synthesis prompt or the planner. Without parent ids, all four look like "the model made it up".

## Evaluation

**Offline set.** 150 research questions, each with a checklist of facts a correct report must contain. Half are broad (many independent entities), half are narrow, so both paths are tested. Benchmarks such as GAIA are useful for comparison, but the checklist set is what gates a release.

**Quality metrics.** Fact recall: the share of checklist facts present in the report. Citation precision: the share of cited claims that the quoted text supports, scored by an LLM judge that is checked against 100 human-labelled claims each release. Unanswered sub-questions reported honestly count as correct behaviour; a confident unsupported claim is the worst outcome.

**Single against multi.** Run both paths on the same questions and plot fact recall against cost. The orchestrator must beat the single agent by a clear margin on broad questions to justify 2.9 times the tokens. On narrow questions it should not be used at all, which is the test for triage: measure routing accuracy against the labelled half.

**Trajectory metrics.** Workers per task, duplicate fetches across workers, overlap between sub-questions, share of workers that end `partial` or `failed`, and share of tasks that need round 2.

**Repeat runs.** Agents are not deterministic. Run each question 3 times and report the pass rate and its spread.

**Online.** Report rating, citation click rate, cost per report split by lead and workers, time to report at p50 and p95, share of traffic routed to multi, and partial-report rate.

**A/B setup.** Randomise by user and change one thing: the triage threshold, the worker model or the brief template.

**Guardrails.** Hard caps on workers, rounds and USD per task, checked in orchestrator code. Alert when any task exceeds its cap.

## Bottlenecks & mitigations

* Provider rate limits in tokens per minute: about 420 worker loops at peak each send a growing context every 8 s.
* Web search and fetch: slow or blocked sites set the worker's latency, and six workers hit the search API at once.
* Synthesis: the lead must read all findings in one context, which caps how many workers a task can usefully have.
* The verifier adds a full pass over the report; it runs after the user already waited for the workers.
* Trace volume: a multi-agent task writes roughly 130 spans (60 worker model calls, 60 tool calls, 6 spawns, the lead's 4 calls and the verifier).

## Failure modes

* **Workers duplicate each other.** Two briefs overlap, so both research the same vendor. Mitigation: briefs that name what the others cover, a shared page cache, and an overlap metric on plans.
* **A summary drops the detail the lead needed.** The worker found the number but returned only a conclusion. Mitigation: findings with exact quotes and an output schema, not free-text summaries.
* **The lead over-spawns.** Eight workers for a question that needed one search. Mitigation: triage before planning, a worker cap, and a budget that is split before spawning.
* **One worker hangs.** The report waits for the slowest worker. Mitigation: per-worker deadlines, a task deadline of 4 minutes for the worker phase, and partial reports.
* **Contradicting findings.** Two workers report different prices from different pages. Mitigation: the lead must show both with sources and dates, and the verifier flags claims whose findings disagree.
* **Injected instructions in a page.** A page tells the worker to add a false claim. Mitigation: read-only workers, findings that need a matching quote, and a verifier that checks claim against quote.
* **Retry storm.** The lead keeps respawning a failing sub-question. Mitigation: one retry per sub-question and two rounds per task, enforced by the orchestrator.
* **Nobody can explain a wrong report.** Mitigation: parent ids on every span and claim-to-finding links stored with the report.

## Follow-up questions interviewers ask

* A user says the report missed an obvious competitor. Walk through the trace to find which agent was responsible.
* When would you let workers talk to each other directly, and what would that cost?
* How would you run the same design with handoffs, and what would break?
* The lead's synthesis context overflows with 8 workers. What do you change?
* How do you cut cost per report by half without lowering fact recall?
* How would you add a worker that queries private company data without creating a path for data to leak to the web?

## Lessons that cover this

* [#13Agent frameworks - LangChain, LangGraphAgents](/ai/learn/agent-frameworks-langchain-langgraph)
* [#15Agents in depth - patterns, reliability, securityAgents](/ai/learn/agents-in-depth)
* [#22Advanced topicsLater](/ai/learn/advanced-topics)

## Further reading

* [Building effective agentsArticleanthropic.com](https://www.anthropic.com/engineering/building-effective-agents)
* [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent ConversationPaperarxiv.org](https://arxiv.org/abs/2308.08155)
* [GAIA: a benchmark for General AI AssistantsPaperarxiv.org](https://arxiv.org/abs/2311.12983)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAgent runtime: loop, tools, checkpoints and budgets](/ai/problems/agent-runtime-harness)[NextMCP tool platform for internal APIs](/ai/problems/mcp-tool-platform)

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
