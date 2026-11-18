# Agentic research assistant with multi-step retrieval — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/agentic-research-assistant

[AI problems](/ai#problems)

GENAIGenAI systems#3Hard

# Agentic research assistant with multi-step retrieval

deep researchplan and executecitationstoken budgetlong-running jobs

## Problem statement

Design a research assistant that answers open questions such as "compare the battery suppliers of the five largest electric car makers". One run takes minutes, not seconds: the system plans, searches the web many times, reads about 30 pages and returns a report of about 2,000 words in which every claim carries a citation the user can check. Plan for 20,000 reports per day. A run must stay inside a token, time and money budget, and it must survive a crashed server without starting again.

## Requirements

### Functional

* Accept a question, return a job id at once, and stream progress: the plan, each search, each source read, each section drafted.
* Break the question into sub-questions, search for each in parallel, and run a second round when the first leaves gaps.
* Read full pages, not only search snippets, and keep each useful fact with the exact quote and URL it came from.
* Write a structured report where every factual sentence links to at least one quoted source, and say what could not be found.
* Let the user cancel a run, and resume a run after a failure from the last finished step.
* Stop cleanly when a budget runs out and still deliver a report from what was gathered.

### Non-functional

* Median run under 5 minutes; hard limit of 15 minutes per run.
* 20,000 reports per day, about 70 runs in progress on average and 280 at peak.
* Budget per run: 600,000 tokens and 1 USD, counted by the job runner, never by the model.
* Citation precision of at least 95%: the cited quote exists in the stored page and supports the sentence.
* A crashed run resumes within 60 seconds and repeats at most one step.
* Average cost under 0.50 USD per report, search fees included.

## Back-of-the-envelope estimates

**Load.** 20,000 reports/day x 300 s average = 6,000,000 run-seconds. Over 86,400 s that is 69 runs in progress; plan for 4 times that, 278.

**Reading.** 6 sub-questions (4 in round one, 2 after the gap check) x 5 pages = 30 pages. At 6,000 tokens per cleaned page: 180,000 raw tokens. A reader turns each page into a 300-token note, so the lead sees 30 x 300 = 9,000 tokens, 20 times less.

**Small-model tokens.** Readers: 30 x (6,000 + 300 prompt) = 189,000 in, 9,000 out. Search workers: 6 x 6 calls x 4,000 = 144,000 in, 5,400 out. Citation checks: 40 claims x 600 = 24,000 in, 800 out. Total 357,000 in, 15,200 out.

**Large-model tokens.** Plan 2,000 in, gap check 10,000 in, writer 9,000 notes + 1,500 outline = 10,500 in: 22,500 in. Output 500 + 500 + 3,000 = 4,000.

**Cost.** Small model at an assumed 0.25 and 1.25 USD per million tokens (in, out): 0.089 + 0.019 = 0.108 USD. Large model at an assumed 3 and 15 USD: 0.0675 + 0.06 = 0.1275 USD. LLM total 0.236 USD. Search: 6 workers x 4 queries = 24 queries at an assumed 0.005 USD = 0.12 USD. Total: 0.356 USD per report, about 7,100 USD per day.

**Why compress.** The 180,000 raw tokens sent once to the large model cost 0.54 USD, more than the whole run.

**Time.** Plan 10 s, round one in parallel 90 s, gap check 15 s, round two 90 s, writing 3,000 tokens at an assumed 50 tokens/s = 60 s, citation checks 10 s: 275 s. In sequence, six workers alone take 6 x 90 = 540 s.

**Provider rate.** Peak arrivals are 4 x 20,000 / 86,400 = 0.93 runs/s. Each run sends 379,500 input tokens, so the peak is about 351,000 tokens/s, 21 million per minute.

## API

```
POST /v1/research
  body: { question, depth?: "quick" | "deep", sources?: ["web", "uploads"],
          budget?: { max_minutes, max_usd } }
  -> 202 { job_id, status: "planning" }

GET  /v1/research/{job_id}
  -> { status, plan: [{ sq_id, text, status }],
       progress: { sources_read, tokens_used, usd_used, seconds_elapsed },
       report?: { sections: [{ heading, sentences: [{ text, citations: [note_id] }] }],
                  sources: [{ source_id, url, title, fetched_at }],
                  not_found: [text], stopped_reason? } }

GET  /v1/research/{job_id}/events      (server-sent events)
  plan_ready | search | source_read | gap_found | section_drafted |
  claim_checked | budget_warning | done | failed

POST /v1/research/{job_id}/plan        body: { approve: true } | { edited_plan }
POST /v1/research/{job_id}/cancel
```

## Data model

```
jobs(job_id PK, user_id, question, status, round, budget_tokens, budget_usd,
     deadline_at, tokens_used, usd_used, lease_owner, lease_expires_at,
     prompt_version, created_at)

subquestions(sq_id PK, job_id FK, round, text, status, summary, not_found)

steps(job_id, seq, kind, sq_id, step_key UNIQUE, output_ref, model,
      tokens_in, tokens_out, usd, created_at)
      -- append-only log; this is the checkpoint
      -- kind: plan | search | fetch | read | gap_check | write | check

sources(source_id PK, job_id FK, url, url_hash, domain, title, published_at,
        fetched_at, content_ref, quality)        -- UNIQUE(job_id, url_hash)

notes(note_id PK, job_id FK, sq_id, source_id, claim, quote,
      char_start, char_end)                      -- quote is copied, not rewritten

report_claims(claim_id PK, job_id FK, section, sentence, note_ids[],
              verdict: supported | partial | unsupported)

page_cache(url_hash PK, content_ref, fetched_at, expires_at)
```

## High-level design

1. The API writes a `jobs` row with its budgets and deadline, puts the job id on a queue and returns 202. The client follows the event stream.
2. A job runner takes a lease on the job (a lock with an expiry that it renews every 10 s). The runner is plain code. It calls models and tools, and it owns the budgets.
3. **Plan.** The large model writes 4 to 8 sub-questions that do not overlap, plus a report outline. The plan is saved to `subquestions`, not kept only in a prompt.
4. **Search workers.** The runner starts one worker per sub-question, at most 6 at a time. A worker is a small agent loop with its own context: write a query, call search, pick results, fetch pages, repeat up to 6 model calls.
5. **Read and compress.** Each fetched page is cleaned and stored. A small model reads one page against one sub-question and returns notes: a claim, the exact quote and its position. Only notes go back to the worker.
6. The worker returns a short summary, its note ids and what it could not find.
7. **Gap check.** The large model reads the summaries against the outline and either names new sub-questions for a second round or says the evidence is enough. Two rounds is the limit.
8. **Write.** The writer sees the outline and the notes only. Every sentence it writes carries note ids.
9. **Check citations.** Code confirms that each quote is in the stored page. A small model judges whether the quote supports the sentence. Unsupported sentences are rewritten once or removed.
10. Every step is appended to `steps` before the next one starts. The runner checks the budgets before every model call, and switches to writing early when they run low.

## Architecture diagram

Rendering diagram…

## Deep dives

### Multi-step retrieval: when to search again

One search rarely answers a sub-question. The first query for a car maker's battery suppliers returns news pages, and the supplier names in those pages are what the second query needs. So each worker is a small loop, not one retrieval call. On each of its 6 model calls it sees the sub-question, the queries already sent and the notes so far, and it decides what to do next: which results to fetch, what to search for, or to stop. A good rewrite uses a name, date or term from the notes. Code rejects a query this job has already sent, and workers share a per-job set of fetched URLs, so nothing is searched or read twice. A worker stops when its notes answer the sub-question, or at 6 calls, and reports what it could not find.

Workers keep separate contexts because 30 pages are 180,000 tokens, and one loop that resends its history on every step would fill the window.

The gap check is the outer loop and the only place where the plan changes. Its stop rule is in code: at most two rounds, and no second round when less than 30% of the budget is left. Without one, a research agent always finds one more thing to look up.

### Reading and compressing sources

The reader decides the quality ceiling. It reads one page against one sub-question and returns up to 5 notes, each with a claim and a quote copied character for character, plus the quote's position. Asking for the quote does two jobs: it forces the model to find the evidence, and it lets code verify the note later without another model call. The raw page stays in object storage with a `content_ref`. This is just-in-time loading: the writer holds 9,000 tokens of notes, and it can ask for the 500 characters around a quote when a note is too thin. What compression loses is anything the sub-question did not ask about, so the reader also returns one line of "other findings" that the gap check may turn into a new sub-question.

### Citations that can be checked

A citation is only useful if it survives a check. The check has two stages. Stage one is code: is the quote an exact substring of the stored page? This catches invented quotes at zero token cost. Stage two is a small-model judge that sees one sentence and its quotes and answers supported, partial or unsupported. An unsupported sentence goes back to the writer once with the verdict as feedback, then it is dropped. Key numbers need two independent domains, and when sources disagree the report states both figures with dates. Web pages are untrusted text. The reader has no tools and returns a fixed structure, so an injected instruction has nothing to act with. If private uploads are in scope, the workers that read them get no web search, because a search query is a way to send data out.

### Budgets and a resumable job

The runner counts tokens, seconds and money after every call. A typical run uses about 399,000 tokens, so the 600,000 cap leaves 50% headroom for hard questions and stops anything beyond that. It reserves 60,000 tokens and 120 seconds for writing and checking, which need about 38,300 tokens (13,500 for the writer, 24,800 for the checks) and 70 seconds, so a run that overspends on search still ends with a report. At 70% of any budget no new searches start. Resuming rests on the `steps` log. Each step has a key built from the job id, sub-question, kind and a counter. A runner renews its lease every 10 s. If it dies, the lease expires after 30 s, another runner takes the job, reads the log, and skips every step whose key is present. The one step that was in flight runs again. That is safe because steps only read the web and write rows under their own key, and the page cache makes a repeated fetch free. A repeated model call does cost its tokens once more, which is one reason to keep each step small.

## Evaluation

**Citation quality.** On every run, compute citation precision (share of cited sentences whose quote exists and supports them) and citation coverage (share of factual sentences that have a citation). Precision is a release gate at 95%.

**Report quality.** Build a set of 150 questions. For each, experts list the 8 to 12 points a good report must contain. An LLM judge scores how many are present and whether any statement contradicts the reference. Check the judge against 100 human-graded reports before trusting it.

**Known-answer tasks.** Add questions with one checkable answer that needs several hops, in the style of GAIA, and score exact correctness. A fluent report can hide a wrong number; these tasks cannot.

**Trajectory.** Searches per run, pages read, share of duplicate fetches, rounds used, share of notes that reach the report, tokens, cost and seconds.

**Repeat runs.** Run each question 3 times. Report the mean score and the spread, because one good run proves little for a non-deterministic system.

**Online.** Share of runs that finish, share that stop on a budget, citation click rate, follow-up questions that ask for something the report missed, and thumbs up or down per report.

**A/B setup.** Randomise by user and change one thing at a time: planner prompt, pages per worker, reader model. Compare quality and cost per report together, since more tokens nearly always buy more coverage.

**Guardrail.** No sentence ships with an unsupported verdict, and resume is tested by killing the runner at every step kind.

## Bottlenecks & mitigations

* Provider rate limits: about 21 million input tokens per minute at peak, most of it on the small model. The queue must admit new runs only when capacity is free.
* Page fetching: 600,000 fetches per day, with slow sites, bot blocks and per-domain politeness limits. One slow page should not hold a worker past its 20 s timeout.
* The writer is sequential: 3,000 output tokens take about 60 s and cannot be made parallel without splitting the report into sections.
* The search API: 24 queries per run is 480,000 per day, a third of the cost and a single point of failure.
* The gap check reads every worker summary, so it is the first prompt to overflow when depth is raised from 6 to 30 sub-questions.

## Failure modes

* **A sentence cites a source that does not say it.** The writer blends two notes or adds its own knowledge. Mitigation: exact-quote check in code, then the support judge, then rewrite once or drop.
* **A worker circles.** It sends near-identical queries and gets the same results back. Mitigation: code rejects a query the job has already sent, the shared set of fetched URLs skips pages already read, and the worker ends at 6 calls.
* **The run never converges.** Each round finds new gaps. Mitigation: two rounds at most, budgets enforced by the runner, and writing starts early when 70% is spent.
* **A web page contains instructions.** Hidden text tells the agent to praise a product or to leak data. Mitigation: readers have no tools and return fixed fields; the lead never sees raw pages; workers with private data have no web access.
* **The runner crashes mid-run.** Mitigation: lease with expiry, append-only steps log, step keys so finished work is skipped on resume.
* **Low-quality sources dominate.** Content farms rank well in search. Mitigation: a domain quality score, a preference for primary sources, two independent domains for key numbers, and publication dates shown in the report.
* **The search provider is down or rate-limited.** Mitigation: retry with backoff, a second provider, and a report that says which sub-questions could not be researched.
* **The plan is wrong from the start.** The planner misreads an ambiguous question. Mitigation: show the plan in the first 10 seconds and let the user edit it before workers start.

## Follow-up questions interviewers ask

* A "deep" mode should read 200 sources in 30 minutes. What breaks first, and what do you change?
* Two good sources give different numbers for the same fact. What does the report say?
* The runner dies while the writer is halfway through. What exactly happens on resume?
* How would you cut the cost per report by half without lowering citation precision?
* How do you add a company's internal documents, with permissions, next to web search?
* How do you know the LLM judge that scores reports can be trusted?

## Further reading

* [How we built our multi-agent research systemArticleanthropic.com](https://www.anthropic.com/engineering/multi-agent-research-system)
* [Effective context engineering for AI agentsArticleanthropic.com](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
* [GAIA: a benchmark for General AI AssistantsPaperarxiv.org](https://arxiv.org/abs/2311.12983)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousHybrid retrieval and reranking service](/ai/problems/hybrid-search-reranking)[NextLLM gateway with routing, caching and fallback](/ai/problems/llm-gateway)

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
13. [Further reading](#reading)
14. [My notes](#notes)
