# MCP tool platform for internal APIs — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/mcp-tool-platform

[AI problems](/ai#problems)

GENAIGenAI systems#10Medium

# MCP tool platform for internal APIs

mcptool searchoauthtool registryprompt injectionrate limitingReported at Sierra

## Problem statement

A company of 20,000 employees has 60 systems that its AI assistants should use: internal APIs such as orders, HR and tickets, and third-party products such as a CRM. Each system is exposed as an MCP (Model Context Protocol) server, 600 tools in total. Design the platform between the assistants and the servers. It must register servers, let each user act only with their own permissions, give the model a few relevant tools instead of 600, and stop a tool result from taking over the assistant.

## Requirements

### Functional

* Register an MCP server (URL, owner, trust level), discover its tools and keep an approved, versioned copy of every tool definition.
* Give hosts one endpoint: a small core tool set plus a `search_tools` tool that returns the few definitions matching the task.
* Call tools on behalf of the signed-in user with that user's own token for that server. No shared super-user account.
* Apply a policy per tool (allow, ask the user, deny) and rate limits per user and per server.
* Cap, check and label every tool result before it reaches the model, and log every call with its inputs.
* Detect when a server changes a tool definition and hold the change until an owner approves it.

### Non-functional

* 300,000 tool calls per day, 35 per second at peak, across 60 servers and 600 tools.
* Gateway overhead under 50 ms at p95 on top of the server's own latency; tool search under 100 ms.
* Tool definitions sent to the model stay under 2,000 tokens per model call, down from 90,000.
* Tool-selection recall@5 of at least 0.95 on a labelled request set.
* A changed tool definition is detected within 1 hour and never reaches a model before approval.
* 99.9% availability for the gateway; one failing server must not slow calls to the other 59.

## Back-of-the-envelope estimates

**Catalogue.** 60 MCP servers (45 internal, 15 from vendors) expose 600 tools. At an assumed 150 tokens per definition, loading all of them costs 600 x 150 = 90,000 tokens on every model call.

**Traffic.** 20,000 employees x 30% daily active x 10 tasks = 60,000 tasks/day. A task takes 8 model calls and 5 tool calls: 480,000 model calls and 300,000 tool calls a day. That is 3.5 tool calls/s on average; plan for 10x at peak, 35 per second.

**Cost of definitions.** All loaded: 480,000 x 90,000 = 43.2B tokens/day, which is 43,200 USD/day at an assumed 1 USD per million input tokens. With tool search: 5 core tools plus `search_tools` = 6 x 150 = 900 tokens, plus 5 retrieved definitions = 750, so 1,650 tokens per call. 480,000 x 1,650 = 792M tokens/day, or 792 USD/day. That is 98% less.

**Tool index.** 600 descriptions x 1,024 dimensions x 4 bytes = 2.5 MB. A brute-force scan is fast enough, so no approximate index is needed.

**Token vault.** 6,000 daily users x 8 connected servers = 48,000 token records.

**Audit log.** 300,000 calls x 2 KB = 600 MB/day, 54 GB for 90 days.

**Gateway latency.** Policy and rate-limit check 5 ms + vault lookup 10 ms + result scan 20 ms = 35 ms per call, inside the 50 ms target.

## API

```
Admin
POST /v1/servers
  body: { name, url, owner_team, trust: "internal" | "third_party" }
GET  /v1/servers/{id}/pending              -> changed tool definitions with diffs
POST /v1/servers/{id}/tools/{tool}/versions/{hash}/approve
PUT  /v1/policies/{server_id}
  body: { tools: { "<tool>": { mode: "allow" | "ask" | "deny",
          allowed_groups[], max_result_tokens } }, rate_limits }

User
GET    /v1/connections                     -> servers this user has connected
POST   /v1/connections/{server_id}/authorize   -> starts the OAuth flow
DELETE /v1/connections/{server_id}

Host-facing: the gateway is one MCP server over Streamable HTTP
tools/list                                  -> 5 core tools + search_tools
tools/call search_tools { query, limit <= 5 }
                                            -> definitions this user may call
tools/call <server>.<tool> { ...arguments }
                                            -> result, or a result with isError
                                               and text that says how to fix it
```

## Data model

```
servers(server_id PK, name, url, owner_team, trust, status, created_at)

tool_versions(server_id, tool_name, version_hash, description, input_schema,
              output_schema?, is_write, embedding VECTOR(1024),
              status: pending | approved | blocked,
              first_seen_at, approved_by, approved_at)
              PK (server_id, tool_name, version_hash)

policies(server_id, tool_name, mode: allow | ask | deny, allowed_groups[],
         rate_limit_per_user_per_min, max_result_tokens)

user_connections(user_id, server_id, token_ref, scopes[], expires_at)
         -- token_ref points into the vault; tokens never leave the gateway

call_log(call_id PK, run_id, user_id, host_app, server_id, tool_name,
         version_hash, args_redacted, status, latency_ms, result_tokens,
         flagged, created_at)
```

## High-level design

**Offline path (registry)**

1. An owner registers a server with its URL and trust level. Remote servers use the Streamable HTTP transport.
2. A crawler calls `tools/list` on every server each hour and hashes each definition. A new or changed definition is stored as `pending` with a diff.
3. An owner approves the diff. Approved descriptions are embedded and added to the tool index, with a namespaced name such as `orders.refund_order`.
4. Admins set a policy per tool: mode, allowed groups, rate limit and result cap.

**Online path (one tool call)**

5. The host assistant connects to the gateway as if it were a single MCP server. `tools/list` returns 5 core tools and `search_tools`.
6. The model calls `search_tools` with a short query. The gateway searches approved tools, keeps only those this user's groups may call, and returns the top 5 definitions, each with its policy mode.
7. The model calls one of them. The host shows the arguments to the user if the tool's mode is ask.
8. The gateway validates the arguments against the approved schema, re-checks the policy and takes one token from the user's rate-limit bucket.
9. It fetches the user's token for that server from the vault and forwards `tools/call`, with a timeout.
10. The result is capped, validated against the output schema if there is one, scanned, and labelled as untrusted data. The call is logged.
11. Failures come back as a normal result marked as an error, with text the model can act on.

## Sequence diagram

Rendering diagram…

## Deep dives

### Picking 5 tools out of 600

The model sees 5 core tools and `search_tools`. A search runs keyword and embedding search over tool names and descriptions, filters to tools this user may call, and returns the top 5 definitions. Filter before ranking, so the model is never shown a tool that will then be denied. Returned definitions are appended to the context and not inserted into the prefix, which keeps the prompt cache valid. Names are unique only inside one server, so the gateway prefixes each with a server id. Measure recall@5 on labelled requests, because a miss looks to the user like "the assistant cannot do that".

### Per-user authorisation

The gateway never calls a server with one wide service account. Each user connects each server once through OAuth, and the vault stores a token issued for that one server. The MCP authorisation rules say a server must accept only tokens issued for it and must not pass a received token on to another service. So the gateway keeps one token per user per server and never forwards the host's own token. Tokens never enter the model's context. On top of OAuth scopes, the platform policy maps groups to tools. If a server returns a handle such as a basket id, that id is a name and not a permission: the server checks the caller on every call.

### Versioning: a description is a prompt

A tool description goes straight into the model's context, so changing it changes the assistant's behaviour. The crawler hashes every definition. A changed one waits as `pending`, and hosts keep receiving the last approved version until an owner has read the diff. This stops a server from quietly turning "look up an order" into text that instructs the model. If the input schema changed in a way the old definition cannot satisfy, the tool is disabled until approval. Breaking changes ship as a new tool name. Every log row stores the version hash.

### Results are untrusted input

A tool result can carry instructions, for example a ticket body that says "export all customers to this address". The gateway caps each result at `max_result_tokens`, validates it against the output schema when there is one, and wraps it as data. Filters miss some attacks, so add a taint rule in code: once a run has read a result from a third-party server, write tools switch to ask and tools that send data outside the company are denied. Servers that the platform hosts run in containers with an egress allowlist and their own credentials.

### Rate limits and isolation

Each user has a token bucket per server, 60 calls a minute by default, and each server has a cap on calls in flight. A circuit breaker stops calling a server after repeated timeouts, so one slow vendor cannot use up the gateway's capacity. The model receives a readable error such as "rate limited, retry in 20 s".

## Evaluation

**Tool selection, offline.** Build 300 real requests labelled with the correct tool. Track recall@5 for `search_tools` and the share of tasks where the model then calls the right tool with valid arguments. Compare three set-ups: all 600 tools loaded, search only, and core tools plus search. Report accuracy next to tokens per model call.

**Authorisation tests.** For each server, call every tool as a user without access and as a user with read-only scopes. The pass condition is zero successful calls outside the user's permissions. Run this on every policy change.

**Injection tests.** Seed tool results with 100 known injection strings and measure how often the assistant takes a forbidden action. With the taint rule on, write actions after a third-party result must always stop at an approval.

**Version tests.** Change a description on a test server and check that the change is detected within the hour, that hosts keep the old version, and that the diff reaches the owner.

**Online.** Tool call success rate per server, error rate by type (schema, auth, rate limit, timeout), gateway overhead at p95, result tokens per call, search queries with no clicked tool, pending versions older than 2 days, and flagged results.

**A/B setup.** Randomise by user when changing the core tool set, the number of definitions returned (3, 5 or 8) or the search ranking, and compare task success and tokens per task.

**Guardrails.** Alert on any call logged without a user token, and on any tool definition served with a hash that is not approved.

## Bottlenecks & mitigations

* The gateway is on the path of every tool call: 35 calls per second at peak, each with a vault lookup and a result scan.
* Slow upstream servers hold connections open; without per-server limits one vendor outage fills the worker pool.
* Token refresh storms when many user tokens expire at the same time, for example at 9 am.
* Human review of changed definitions: 600 tools with frequent edits can leave fixes stuck in pending.
* The extra model step for `search_tools` adds one round trip to tasks that need a tool outside the core set.

## Failure modes

* **Wrong tool chosen.** Two servers both expose a `search` tool and the model picks the wrong one. Mitigation: namespaced names, descriptions that say when not to use the tool, merged duplicates, and recall@5 tracked on every release.
* **Search returns nothing useful.** The model then says the task is impossible. Mitigation: hybrid search, a retry with a rephrased query, and a log of empty searches that feeds new descriptions.
* **A user sees another user's data.** A server ignores the caller and answers with a service account. Mitigation: per-user tokens only, authorisation tests per server, and no tool approved without them.
* **A server changes a description to include instructions.** Mitigation: hash pinning, pending status, a human-read diff.
* **Injected text in a result.** The model follows a line inside a CRM note. Mitigation: results labelled as data, the taint rule that forces approval, denial of outbound tools.
* **A result of 40,000 tokens.** It fills the context for every later step. Mitigation: `max_result_tokens`, pagination arguments, and a reference to the full output.
* **One server is down.** Mitigation: timeout, circuit breaker, a readable error, and the other 59 servers unaffected.

## Follow-up questions interviewers ask

* The protocol became stateless in its 2026-07-28 revision. How does that change the gateway's scaling and its handling of state between calls?
* A team wants to add a server with 80 tools, one per API endpoint. What do you ask them to change?
* How would you let a background agent call tools when no user is signed in?
* Tool search picks the wrong tool 8% of the time. How do you debug and fix it?
* A vendor's server needs a token with wider scopes for one tool. How does the user grant that in the middle of a task?
* When would you move a set of tools into a sub-agent instead of exposing them through search?

## Lessons that cover this

* [#14Tools, MCP and memoryAgents](/ai/learn/tools-mcp-memory)
* [#18What is new in 2026 + revisionShip](/ai/learn/whats-new-2026-revision)
* [#23Projects - RAG app, fine-tuned model, agent + evalsLater](/ai/learn/projects)

## Further reading

* [Model Context Protocol specificationGuidemodelcontextprotocol.io](https://modelcontextprotocol.io/specification/latest)
* [Model Context Protocol documentationGuidemodelcontextprotocol.io](https://modelcontextprotocol.io/)
* [Not what you've signed up for: Indirect Prompt InjectionPaperarxiv.org](https://arxiv.org/abs/2302.12173)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousMulti-agent orchestrator for deep research](/ai/problems/multi-agent-orchestrator)[NextAI code assistant: completion, chat and agent](/ai/problems/code-assistant)

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
