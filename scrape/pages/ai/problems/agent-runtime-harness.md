# Agent runtime: loop, tools, checkpoints and budgets — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/agent-runtime-harness

[AI problems](/ai#problems)

GENAIGenAI systems#8Hard

# Agent runtime: loop, tools, checkpoints and budgets

agent harnesscheckpointssandboxhuman approvalcontext compactionbudgetsReported at Glean

## Problem statement

Design the runtime that executes LLM agents for a company's AI platform. Product teams register an agent as a prompt, a tool list and limits. The runtime, also called the harness, does everything else: it runs the loop, assembles the context, executes tools in a sandbox, asks people for approval and streams progress to clients. It must handle 200,000 runs a day, runs that pause for days waiting on a person, and worker crashes at any moment without losing a run or repeating a side effect.

## Requirements

### Functional

* Start a run for a registered agent version and stream its events (model text, tool calls, results, status). A client that reconnects continues from the last event it saw.
* Run the loop: assemble the context, call the model, validate and execute the tool calls (in parallel when the model asks for several), and feed the results back.
* Check every tool call against a permission policy: allow, ask a person, or deny. A run that waits for approval holds no worker and can wait for days.
* Checkpoint after every step, so a run resumes on another worker after a crash without repeating a finished write.
* Enforce budgets per run (steps, tokens, wall-clock time, money) and stop cleanly with a reason.
* Support hooks (team code that runs before and after model and tool calls), sub-agents with their own context, cancel, and user messages sent in the middle of a run.

### Non-functional

* 200,000 runs per day at 12 model calls per run on average; about 1,040 concurrent runs at peak.
* Harness overhead under 50 ms per step at p95, not counting model and tool time; first streamed event within 1 s.
* A crashed run resumes within 30 s, with zero duplicated write actions.
* A run never overspends: the budget is checked before each model call and the call's maximum output is reserved first.
* 99.9% availability for starting runs and reading events; a paused run stays resumable for 7 days.
* A sandbox starts in under 500 ms at p95 from a warm pool, with no credentials and no network by default.

## Back-of-the-envelope estimates

**Load.** 200,000 runs/day = 2.3 runs/s on average. Plan for 5x at peak: 11.6 runs/s. At 12 model calls per run that is 2.4 million model calls a day, 28 per second on average and 139 per second at peak.

**Concurrency.** A step takes about 5 s of model time and 2.5 s of tool time, so a run lasts 12 x 7.5 = 90 s. Peak concurrency = 11.6 x 90 = about 1,040 runs. Workers mostly wait on I/O. At 50 runs each that is 21 workers, 28 with 30% headroom.

**Tokens per run.** The stable prefix (system prompt and tool definitions) is 3,000 tokens and the task is 200. Each step adds 150 output tokens and a 700-token tool result, 850 in total. Step n sends 3,200 + 850 x (n - 1) tokens. Over 12 steps: 12 x 3,200 + 850 x 66 = 94,500 input tokens, plus 12 x 150 = 1,800 output tokens.

**Cost.** Per day: 18.9B input and 360M output tokens. At an assumed 1 USD and 5 USD per million tokens that is 18,900 + 1,800 = 20,700 USD/day, or 0.104 USD per run.

**With prompt caching.** Only the task and the newest 850 tokens of each later step are new: 200 + 11 x 850 = 9,550 tokens. The other 84,950 were sent before. At an assumed 10% price for cached input, the input costs 9,550 + 8,495 = 18,045 token-equivalents. A run then costs 0.018 + 0.009 = 0.027 USD and a day about 5,400 USD. Keeping the context append-only is worth about 15,000 USD a day.

**Checkpoints.** One batch of events per step, about 5 KB: 2.4M x 5 KB = 12 GB/day, 360 GB for 30 days.

**Sandboxes.** If 30% of runs execute code, the peak is 1,040 x 0.3 = about 310 sandboxes. At 0.5 vCPU and 0.5 GB each: about 155 vCPU and 155 GB.

## API

```
POST /v1/runs
  body: { agent_id, agent_version?, input, user_token, idempotency_key,
          budgets?: { max_steps, max_tokens, max_seconds, max_usd } }
  ->    { run_id, status: "queued" }

GET  /v1/runs/{run_id}/events?after={seq}        (server-sent events)
  run.started | model.delta | tool.requested | approval.required |
  tool.result | context.compacted | subagent.started | subagent.finished |
  budget.warning | run.paused | run.finished { stop_reason }

POST /v1/runs/{run_id}/approvals/{approval_id}
  body: { decision: "approve" | "reject", edited_args?, comment? }
POST /v1/runs/{run_id}/messages    body: { content }     (steer a live run)
POST /v1/runs/{run_id}/cancel
GET  /v1/runs/{run_id}  -> { status, step, budgets_used, pending_approval?, result? }

Hook contract (registered per agent version, called by the harness)
  pre_model(context) | pre_tool(call) -> allow | deny(reason) | rewrite(args)
  post_tool(call, result) -> result   | on_stop(run, stop_reason)
```

## Data model

```
agent_versions(agent_id, version, model, system_prompt, tool_ids[],
               permission_policy, budgets, hooks[], created_at)   -- immutable

runs(run_id PK, agent_id, agent_version, user_id, parent_run_id?, status,
     step, lease_owner, lease_version, lease_expires_at,
     tokens_in, tokens_out, cost_usd, deadline_at, stop_reason)

run_events(run_id, seq, type, payload, lease_version, created_at)
     PK (run_id, seq)            -- append-only; the source of truth

snapshots(run_id, at_seq, summary, notes)
     -- written at compaction, so a resume does not replay the whole log
workspace_snapshots(run_id, at_seq, uri)   -- sandbox files after a step

tool_calls(run_id, step, call_id, tool, args_hash, idempotency_key,
           status: planned | running | done | failed, result_ref)

approvals(approval_id PK, run_id, call_id, args_hash, requested_at,
          expires_at, decided_by, decision, decided_at)

artifacts(artifact_id PK, run_id, uri, bytes)   -- large tool outputs
```

## High-level design

**Offline path (defining an agent)**

1. A team registers an agent version: model, system prompt, tools, permission policy, budgets and hooks. Versions are immutable, so prompt, tools and model roll back as one unit.
2. The version runs against the team's eval set before it can serve traffic.

**Online path (one run)**

3. The run API stores the run with its idempotency key, writes `run.started` and puts the run id on a queue.
4. A worker claims the run by taking a 30 s lease, which it renews every 10 s.
5. The worker builds the context from the event log: system prompt, tool definitions, the latest compaction summary, then the steps since that summary.
6. Before each model call it checks the four budgets. If one is used up, the run stops with a reason and a short report of what was finished.
7. The model call is streamed. Text deltas go to the event stream, so the client sees progress in under a second.
8. If the reply is a final answer, the run finishes. If it holds tool calls, each call is validated against its schema, passed through pre-tool hooks and matched against the permission policy.
9. Deny returns a readable error as the tool result. Ask writes `approval.required`, saves the pending call and releases the lease; the decision puts the run back on the queue.
10. An allowed call is first recorded as `planned` with an idempotency key. Code and shell tools run in the run's sandbox; API tools run in connector workers with the user's token. Every call has a timeout.
11. Results are capped in size, passed through post-tool hooks and appended to the event log in one transaction with the token counts. That append is the checkpoint.
12. When the context passes 70% of the window, the worker compacts it and writes a snapshot. Then the loop returns to step 5.
13. A `spawn_agent` tool starts a child run with its own context and a share of the parent's budget. The child's final message comes back as the tool result.

## Architecture diagram

Rendering diagram…

## Deep dives

### The event log is the checkpoint

Each step appends its events to `run_events` in one transaction: the model reply, every tool result and the token counts. The context is always rebuilt from the log, so there is no separate save call that someone can forget. A worker owns a run through its lease. If the worker dies, the lease expires within 30 s and another worker loads the log and continues at the next step. Every append carries the lease version. A slow old worker that wakes up holds an outdated version, so its write is rejected and it cannot corrupt a run it no longer owns.

The hard case is a crash after a tool changed something and before the result was logged. That is why the harness writes a `planned` row with an idempotency key (run id, step, call id) before it executes. On resume, a planned call with no result is sent again with the same key, and the tool returns its stored result without acting twice. A tool that cannot take a key is marked non-retryable: the harness asks the tool for the call's status, or parks the run for a person.

### Context assembly: append-only, then compact

The context has a fixed order: system prompt, tool definitions, compaction summary, then the steps since the summary. Nothing in the middle is edited between steps, so the provider's prompt cache keeps hitting. The numbers above show that this is almost a 4x difference in cost. Three rules limit growth. Tool results are capped at 2,000 tokens; a larger output goes to the artifact store and the model gets a reference it can read in slices. Past 70% of the window the harness compacts: one model call writes a summary of decisions, open items and key facts, and the raw steps leave the context but stay in the log. Compaction rewrites the context, so it breaks the cache once. Do it rarely and in one large cut, never a little on every step. Long tasks also get a notes file that survives compaction.

### Permissions and approval live in code

A policy rule matches on tool name and arguments and returns allow, ask or deny. The first match wins, and write tools default to ask. A denied call becomes a readable tool result, so the model can choose another path. An ask saves the pending call and frees the worker, which is why a run can wait for days at no cost. The approval is bound to a hash of the exact arguments. If the person edits them, the edited version runs, and the model cannot change them afterwards. An approval that expires counts as a rejection. Hooks use the same interception point: a pre-tool hook can block or rewrite a call, and a post-tool hook can redact a result. Each hook has a 200 ms timeout, and a security hook that fails blocks the call.

### Sandboxed tool execution

Model-written code is untrusted code. Each run that needs one gets a sandbox, a micro-VM or container taken from a warm pool. It has no credentials, a CPU, memory and time limit per command, and no network beyond an allowlist. Tools that call internal APIs run outside it, in connector workers that use the user's own token, so the agent never has more access than the person it acts for. The sandbox's files are not in the event log. So after each step that changed files, the harness takes a copy-on-write snapshot of the workspace and stores its id in the same checkpoint. A resumed run restores that snapshot in a fresh sandbox.

### Budgets and sub-agents

The harness, not the model, counts steps, tokens, seconds and money. Before each model call it reserves that call's `max_tokens`, so the output cannot overshoot. Time is a deadline stored on the run, not a timer inside a worker, so it survives a crash. Three identical tool calls in a row also stop the run. A sub-agent is a child run with its own context and a budget taken from what the parent has left. Depth is limited to 1, and cancelling a parent cancels its children.

## Evaluation

**Crash tests.** This is the test that matters most for a harness. Take 50 recorded runs and, for each one, kill the worker at every step boundary and in the middle of every tool call. After resume, the end state must equal the uncrashed run and the count of duplicated side effects must be 0. Run it on every release.

**Replay tests.** Record real runs with their model replies and tool results. Replay them against a new harness build with the model mocked, and diff the event logs. This makes harness changes testable without model randomness.

**Agent quality.** A fixed set of 200 tasks, 3 runs each. Report the pass rate on the end state and on the trajectory: right tools, valid arguments, no forbidden action, step count.

**Compaction.** After a forced compaction, ask 30 questions about facts from before the cut. Track recall, and compare the task pass rate with compaction on and off.

**Online.** Run success rate, the mix of stop reasons (final answer, step limit, budget, repeated call, cancelled), steps and cost per run, prompt-cache hit rate, harness overhead per step at p95, resume count, approval wait time, sandbox start time and hook timeouts.

**Rollout.** A run stays on the agent version and harness version it started with. A new harness build takes 5% of new runs first, compared on success rate and cost per run.

**Guardrails.** Alert on any duplicated idempotency key that executed twice, any run over budget and any write tool that ran without an allow or an approval record.

## Bottlenecks & mitigations

* Provider rate limits: 139 model calls per second at peak, with contexts that grow each step. Admission control must queue new runs before running ones starve.
* The event log write is on the hot path of every step. It needs a store with low-latency appends, partitioned by run id.
* Sandbox cold starts when the warm pool is empty, and workspace snapshots for large repositories.
* Rebuilding the context of a long run from thousands of events; snapshots keep this bounded.
* Thousands of open event streams, each of which must support reconnect from a sequence number.

## Failure modes

* **Worker dies in the middle of a step.** The lease expires and the run looks stuck for up to 30 s. Mitigation: lease renewal every 10 s, automatic takeover, and resume from the last appended event.
* **Crash between a side effect and its checkpoint.** The tool ran, but the log does not show it. Mitigation: a `planned` row with an idempotency key before execution, and a status check for tools that cannot take a key.
* **Two workers run the same run.** A paused worker wakes up after its lease was taken. Mitigation: every append carries the lease version, and stale versions are rejected.
* **Compaction drops a needed fact.** The agent repeats work or contradicts an earlier decision. Mitigation: a summary template with decisions, open items and key facts, a notes file outside the context, and the compaction eval.
* **Approval never arrives.** The run waits forever and holds a sandbox. Mitigation: an expiry that counts as rejection, sandbox snapshot and release on pause, a reminder to the approver.
* **Runaway loop.** The model repeats a failing call until the money is gone. Mitigation: step and money budgets checked in code, the three-identical-calls rule, and tool errors that say how to fix the call.
* **Hook hangs or throws.** Team code blocks every step. Mitigation: a 200 ms timeout, fail closed for security hooks and fail open for logging hooks, and a per-hook error rate alert.
* **Client disconnects during a run.** The run must not die with the connection. Mitigation: runs are decoupled from streams, and the client reconnects with `after={seq}`.

## Follow-up questions interviewers ask

* A tool has no idempotency support and the worker crashed while calling it. What exactly happens on resume?
* How would you let a user edit an earlier step and continue the run from there?
* Compaction made the agent forget a constraint the user gave at the start. How do you prevent that?
* How do you share one provider rate limit fairly across 300 teams and their agents?
* When would you give a sub-agent a different model or a different tool set from its parent?
* How do you upgrade the harness while 1,000 runs are in flight and some are paused for days?

## Lessons that cover this

* [#12Agents from first principles - build a mini frameworkAgents](/ai/learn/agents-first-principles)
* [#13Agent frameworks - LangChain, LangGraphAgents](/ai/learn/agent-frameworks-langchain-langgraph)
* [#14Tools, MCP and memoryAgents](/ai/learn/tools-mcp-memory)
* [#15Agents in depth - patterns, reliability, securityAgents](/ai/learn/agents-in-depth)
* [#18What is new in 2026 + revisionShip](/ai/learn/whats-new-2026-revision)
* [#22Advanced topicsLater](/ai/learn/advanced-topics)

## Further reading

* [Effective context engineering for AI agentsArticleanthropic.com](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
* [Building effective agentsArticleanthropic.com](https://www.anthropic.com/engineering/building-effective-agents)
* [LangGraph CheckpointersGuidedocs.langchain.com](https://docs.langchain.com/oss/python/langgraph/checkpointers)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousCustomer support agent with tools and approvals](/ai/problems/customer-support-agent)[NextMulti-agent orchestrator for deep research](/ai/problems/multi-agent-orchestrator)

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
