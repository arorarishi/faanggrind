# AI code assistant: completion, chat and agent — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/code-assistant

[AI problems](/ai#problems)

GENAIGenAI systems#11Hard

# AI code assistant: completion, chat and agent

code completionrepository indexingcontext selectioncoding agentsandboxacceptance rate

## Problem statement

Design an AI coding assistant that 50,000 developers use every day inside their editor. It has three modes with very different budgets. Inline completion must show a suggestion within 300 ms. Chat answers questions about a repository in a few seconds. An agent edits several files and runs the tests over several minutes. All three need the right code in the context, and the agent must change a repository without breaking it or leaking it.

## Requirements

### Functional

* Inline completion: suggest the next lines at the cursor as grey text, using the code before and after the cursor, and cancel when the user keeps typing.
* Chat: answer questions about the repository with references to files and line ranges.
* Agent: take an instruction, edit several files on a branch, run tests and linters in a sandbox, fix failures, and return a diff for review.
* Index every repository (symbols, chunks, embeddings) and keep it in sync with edits. Unsaved editor buffers override the index.
* Record telemetry: suggestion shown, accepted, kept after 30 s, chat feedback, agent task outcome.
* Respect repository permissions and an organisation setting that excludes paths, such as secrets files, from any prompt.

### Non-functional

* Completion: first visible text within 300 ms of the request at p95, at 1,740 requests per second at peak.
* Chat: time to first token under 1.5 s at p95. Agent: median task under 6 minutes, hard limits of 30 minutes and 40 steps.
* Index freshness: a pushed change is searchable within 60 s.
* Completion acceptance rate of at least 25%, with at least 80% of accepted characters still in the file after 30 s.
* Average cost under 0.02 USD per chat and under 0.20 USD per agent task.
* The agent never writes to the user's working tree or the default branch, and its sandbox holds no secrets.

## Back-of-the-envelope estimates

**Completion load.** 50,000 developers x 1,000 triggers a day = 50M requests/day, 579/s on average and about 1,740/s at a 3x peak. The client cancels 40% when the user keeps typing, so 1,040/s reach the model. If one GPU replica of a small code model sustains 60 requests/s inside the latency target (an assumption to confirm with a load test), that is 18 replicas, or 23 with 30% headroom.

**Completion latency.** Network 60 ms + client context 15 + queue 15 + prefill of 2,000 tokens with a warm prefix cache 70 + 32 output tokens x 3.5 ms = 112. Total 272 ms.

**Chat.** 50,000 x 12 = 600,000 chats/day, 21/s at peak. Input: 12 chunks x 400 tokens + 2,000 for the open file + 1,200 of instructions and history = 8,000 tokens. Output: 500. At an assumed 1 USD and 5 USD per million tokens: 0.008 + 0.0025 = 0.0105 USD per chat, or 6,300 USD/day.

**Agent.** 10% of developers x 4 tasks = 20,000 tasks/day, 25 steps each. The prefix is 6,000 tokens and each step adds 1,800 (a capped tool result plus the model's output). Input = 25 x 6,000 + 1,800 x (0 + 1 + ... + 24) = 150,000 + 540,000 = 690,000 tokens. Output = 25 x 300 = 7,500. Uncached that is 0.69 + 0.0375 = 0.73 USD per task. Only 6,000 + 24 x 1,800 = 49,200 tokens are new. At an assumed 10% price for the other 640,800, the task costs 0.113 + 0.0375 = 0.15 USD, about 3,000 USD/day.

**Sandboxes.** 20,000 tasks x 6 minutes = 120,000 sandbox-minutes a day: 83 running on average and about 330 at a 4x peak.

**Index.** 40,000 repositories x 5,000 chunks = 200M chunks x 768 dimensions x 4 bytes = 614 GB, or 154 GB as int8.

## API

```
POST /v1/completions
  body:   { repo_id, path, language, prefix, suffix,
            neighbours: [{ path, snippet }], request_seq }
  stream: { completion_id, text, stop_reason }      (client cancels by closing)

POST /v1/completions/events
  body:   { completion_id, event: "shown" | "accepted" | "rejected",
            chars_accepted?, chars_kept_after_30s? }

POST /v1/chat
  body:   { repo_id, commit, messages[], open_files[], selection? }
  stream: tokens, then { references: [{ path, start_line, end_line }] }

POST /v1/agent/tasks
  body:   { repo_id, base_commit, instruction, test_command?, budgets? }
  ->      { task_id }
GET  /v1/agent/tasks/{task_id}/events                (server-sent events)
  plan | edit.applied { path, diff } | command.finished { exit_code } |
  approval.required | done { branch, diff_stats, tests_passed, stop_reason }
POST /v1/agent/tasks/{task_id}/approvals/{approval_id}  { decision }

POST /internal/index/sync
  body:   { repo_id, commit, changed: [{ path, content_hash }], deleted[] }
```

## Data model

```
repos(repo_id PK, org_id, default_branch, indexed_commit, excluded_paths[])

files(repo_id, path, content_hash, language, bytes)
      -- one hash per directory above it, for fast "what changed" sync

symbols(repo_id, name, kind, path, start_line, end_line, signature)
symbol_refs(repo_id, from_symbol, to_symbol)        -- calls and imports

code_chunks(content_hash, chunk_no, symbol, start_line, end_line, text,
            embedding VECTOR(768))                  -- keyed by content, shared by branches
chunk_locations(repo_id, commit, path, content_hash)
keyword_index(chunk, identifiers and trigrams)

completion_events(completion_id PK, user_id, repo_id, language, model_version,
                  latency_ms, shown, accepted, chars_accepted, chars_kept_30s)

agent_tasks(task_id PK, user_id, repo_id, base_commit, branch, status, steps,
            tokens_in, tokens_out, tests_passed, stop_reason)
agent_edits(task_id, step, path, base_hash, diff, applied, checkpoint_commit)
```

## High-level design

**Offline path (indexing)**

1. On save or push, the client sends the hashes of changed files. The server asks only for content it has not seen.
2. A parser builds a syntax tree per file. The indexer extracts symbols and references, and cuts chunks at function and class boundaries.
3. Changed chunks are embedded and written to the vector and keyword indexes. A repo map, a short outline of files and their main symbols in about 2,000 tokens, is rebuilt per commit.

**Completion path**

4. The editor plugin waits for a short pause in typing (about 75 ms), then builds the prompt locally: snippets from open and recently edited files, the code before the cursor and the code after it.
5. A small code model with a prefix cache streams at most 32 tokens. If the user types again, the client closes the stream.
6. A post-filter trims the text to a complete line or block, drops suggestions that repeat the code after the cursor, and logs `shown`.

**Chat path**

7. The retriever runs keyword and embedding search over chunks, adds the definitions of symbols the top hits call, and reranks to 12 chunks. The open file and selection are always included.
8. A large model streams the answer. File and line references are checked against the index before display.

**Agent path**

9. The task starts a sandbox with the repository checked out at `base_commit` on a new branch.
10. The agent loop has tools to search, read line ranges, edit and run commands. It starts from the repo map and loads code as it needs it.
11. Each edit is applied only if its target text still matches, then syntax-checked and committed to the branch as a checkpoint.
12. The agent runs the tests and linters. Failures go back to the model, trimmed. It stops when the tests pass or a budget ends.
13. The user receives a diff with the test results. Merging is a human action.

## Architecture diagram

Rendering diagram…

## Deep dives

### Completion: everything is shaped by 300 ms

The budget rules out a large model and any network retrieval. Five choices make it fit. A small code model trained for fill-in-the-middle, meaning it writes the code between a given prefix and suffix. A prompt whose order changes slowly: neighbour snippets first, then the file prefix, so each keystroke only appends and the server's prefix cache skips most of the prefill. A cap of 32 output tokens, with more only when the cursor is at the start of an empty block. Debounce and cancellation, so 40% of requests never reach a GPU. And a client cache: if the user types the next characters of the suggestion already shown, the client keeps showing the rest and sends nothing. Do not trigger in the middle of a word or when the last suggestion was just rejected at the same position.

### Context selection is different in each mode

Completion uses only what the editor already has: the current file, open tabs, files it imports and recently edited files. Snippets are ranked by token overlap with the lines around the cursor, which takes a few milliseconds on the client. Chat can afford retrieval. Keyword search finds exact identifiers, embeddings find code by meaning ("where do we retry payments"), and the symbol graph adds what the top hits call, because a function is hard to explain without the functions it calls. The agent gets the least up front: the repo map and tools. It searches and reads line ranges as it goes, which keeps 25 steps inside the context. Stuffing 50 files in at the start costs more and leaves less room for test output.

### Indexing that keeps up with edits

Chunks follow the syntax tree, one per function or class, because a fixed-size split cuts functions in half. Embeddings are keyed by the content hash of the chunk, so a branch that changes 3 files embeds only those chunks and shares everything else with the main branch. Sync compares directory hashes from the root down and stops at any directory whose hash matches, so finding the changes costs time in proportion to what changed, not to the repository size. The index always lags the editor by some seconds. The client therefore sends the open and unsaved files itself, and these override indexed chunks from the same paths.

### Applying edits safely

The model does not rewrite whole files. It emits edits as a search block and a replace block. The harness applies an edit only if the search text occurs exactly once in the current file. If not, it returns an error with the current lines, and the model tries again. A whole-file rewrite is allowed only for small files, since long rewrites tend to drop unrelated lines. After each edit the file is parsed, and a syntax error is returned at once without running the full test suite. Every applied edit is a commit on the task branch. That gives undo, a resume point after a crash, and a clean diff. The user's working tree is never touched.

### The sandbox and the test loop

Tests run code that the model has just written, and the repository itself may contain hostile text, such as a README that tells the agent to print environment variables. So the sandbox has no secrets, no network except a package mirror, and CPU, memory and time limits per command. Commands outside an allowlist need approval. Test output is trimmed before it returns to the model: failing tests first, at most 1,500 tokens. One trap needs a rule in code: an agent can make tests pass by editing or deleting them. Changes to test files are flagged in the diff, and the final run uses the original tests as well.

## Evaluation

**Completion, offline.** Take held-out repositories, hide a span of code and ask the model to fill it. Score exact match and edit similarity against the original, and on a subset run the unit tests (pass@1, the share of suggestions that pass on the first try). Always report p95 latency next to quality, because a slower, better model can lose online.

**Completion, online.** Acceptance rate = accepted / shown. On its own it can be gamed: showing only short, safe suggestions raises it. So pair it with the show rate (shown / requests), accepted characters per developer per day, and the share of accepted characters still present after 30 s. Slice by language. A/B test by user, never by request, since a developer adapts to the tool.

**Chat.** A set of 300 questions with the files that answer them. Track retrieval recall@12, answer correctness by an LLM judge checked against human labels, and the share of references that point to real files and lines.

**Agent, offline.** Tasks in the style of SWE-bench: a real issue, the repository at the commit before the fix, and hidden tests that fail before and pass after. Report the resolved rate over 3 runs per task, plus steps, cost, and the count of previously passing tests that now fail.

**Agent, online.** Share of tasks whose diff is merged, lines changed by the human before merge, revert rate within 7 days, cost and time per task, and stop reasons.

**Guardrails.** A secrets scanner on prompts and outputs, the excluded-path filter tested on every release, and an alert if any sandbox opens a connection outside the allowlist.

## Bottlenecks & mitigations

* Completion GPUs: 1,040 requests per second at peak with a hard latency target, so capacity is sized for peak and autoscaling must be early.
* Network distance: 60 ms of the 300 ms budget is the round trip, which forces regional deployment of the completion model.
* First index of a large repository: embedding 100,000 chunks takes minutes, and chat is weaker until it finishes.
* Sandbox start and dependency install: a cold environment can take longer than the agent's first ten steps.
* Test suites: a 10-minute suite makes each agent iteration slow, so the agent runs the affected tests first and the full suite once at the end.

## Failure modes

* **Stale suggestion.** The completion arrives after the user has typed something else. Mitigation: `request_seq` on every request, and the client drops any response that is not for the latest one.
* **Suggestion repeats or breaks the code after the cursor.** Mitigation: send the suffix, use a fill-in-the-middle model, and filter suggestions that duplicate the next lines.
* **Chat cites a function that no longer exists.** The index lags a refactor. Mitigation: unsaved buffers override the index, references are validated before display, and `indexed_commit` is shown when it is behind.
* **Edit does not apply.** The search text matches zero or two places. Mitigation: exact-match rule, an error with the current lines, and a re-read before retry.
* **Agent passes tests by changing the tests.** Mitigation: flag test-file edits, run the original tests at the end, and show both in the review.
* **Agent loops on a failing test.** It retries the same fix. Mitigation: step and cost budgets, a repeated-edit check, and a stop with a summary of what it tried.
* **Secrets leak into a prompt.** An env file sits in the repository. Mitigation: excluded paths enforced in the client and the server, and a secrets scanner before any model call.
* **Hostile repository content.** A comment instructs the agent to exfiltrate code. Mitigation: no secrets and no open network in the sandbox, approval for unlisted commands, and a human-reviewed diff.

## Follow-up questions interviewers ask

* Acceptance rate went up 5 points after a model change, but developers complain. What do you check?
* How would you use one model for all three modes, and why might you not?
* A monorepo has 20 million lines. What changes in indexing and in the agent's context?
* How do you roll out a new completion model without making latency worse?
* The agent needs network access to install a new dependency. How do you allow it safely?
* How would you personalise completions to a team's code style without fine-tuning a model per team?

## Lessons that cover this

* [#17LLM system designShip](/ai/learn/llm-system-design)
* [#20RL fine-tuningLater](/ai/learn/rl-fine-tuning)

## Further reading

* [Evaluating Large Language Models Trained on CodePaperarxiv.org](https://arxiv.org/abs/2107.03374)
* [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?Paperarxiv.org](https://arxiv.org/abs/2310.06770)
* [SWE-agent: Agent-Computer Interfaces Enable Automated Software EngineeringPaperarxiv.org](https://arxiv.org/abs/2405.15793)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousMCP tool platform for internal APIs](/ai/problems/mcp-tool-platform)[NextLoRA fine-tuning pipeline with an adapter registry](/ai/problems/fine-tuning-pipeline)

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
