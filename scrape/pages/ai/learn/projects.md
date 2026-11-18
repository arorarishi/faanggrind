# Projects - RAG app, fine-tuned model, agent + evals — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/projects

[AI roadmap](/ai)

LaterLesson #23LaterIntermediate 8 h

# Projects - RAG app, fine-tuned model, agent + evals

Three small projects turn the rest of this course into things you can talk about: a RAG app, a fine-tuned model, and an agent with an eval harness. This lesson gives each one a scope, milestones, numbers to measure with targets a student can reach, a README outline, and a way to present it in two minutes: problem, design, trade-offs, numbers.

projectsportfolioragfine-tuningagentsevalsinterview prep

## Why it matters

"Walk me through an LLM project you built" opens most AI engineer interviews, and the follow-ups are fixed: what went wrong, how did you evaluate it, how would you scale it. A candidate who says "Recall@5 went from 19 of 30 to 27 of 30 after I added keyword search and a reranker" is believed. A candidate who recites the definition of hybrid search is asked another question. The projects here are sized for evenings and a free or cheap GPU, and each one ends in a table of numbers, because the table is what you will be asked about.

Read first: [Vector DBs and RAG](/ai/learn/vector-dbs-rag), [Fine-tuning a model for a real use case](/ai/learn/fine-tuning-real-use-case), [Agents from first principles - build a mini framework](/ai/learn/agents-first-principles), [Tools, MCP and memory](/ai/learn/tools-mcp-memory), [Evals, tracing and guardrails](/ai/learn/evals-tracing-guardrails)

## Lesson

### Why three projects

Four weeks at 2 to 3 hours a day covers the whole course. Two weeks works if you skip the projects and only drill the Q&A. Skipping them costs you the third of the three rules that make the difference in interviews:

1. **Say answers aloud.** Reading feels like knowing. Speaking shows the gaps.
2. **Always give the trade-off.** "It depends on X; if A then this, if B then that" beats a one-word answer.
3. **Tie every topic to one project.** "I used QLoRA on a 7B model and saw..." beats any definition.

| Week | Focus | What you should have at the end |
| --- | --- | --- |
| 1 | LLM fundamentals, prompting, context engineering | You can explain attention, tokenization and decoding on a whiteboard |
| 2 | RAG and fine-tuning | One RAG app with eval numbers; one QLoRA fine-tune run on a small model |
| 3 | Inference and serving | One open model served on vLLM, with a load test and latency numbers |
| 4 | Agents, evals, system design, revision | One agent with tools and evals; three system designs practised aloud |

Interviewers expect your own projects in depth, with numbers for latency, cost and quality. So every project below ends in a table, not a demo video.

### The loop every project follows

1. **Pick a narrow problem** with data you can get: your college rule book, one product's help pages, one public API.
2. **Write the eval set first:** about 30 cases with the expected result, before the system exists.
3. **Build the simplest version** and score it. That is your baseline.
4. **Read the failures,** change one thing, score again. Log each change with its number.
5. **Record latency and cost** next to quality.
6. **Write the README** while the numbers are fresh.

The targets below are goals for a student project on your own eval set. They are not benchmarks. Missing one and explaining why is still a good story.

### Project 1: a RAG app

**Build:** question answering over 50 to 200 documents you care about, with citations, and a "not found" reply when the documents have no answer.

1. Ingest and chunk (start at 400 tokens with 15% overlap). Dense retrieval, top 5, answer with citations. Log the retrieved chunk ids for every answer.
2. Eval set: 30 questions with the correct chunk for each, plus 5 whose answer is not in the documents.
3. Add BM25 with RRF fusion, then a reranker over the top 50.
4. Add a faithfulness judge and check its verdicts by hand on all 30.

| Measure | Target |
| --- | --- |
| Recall@5 | 27 of 30 (90%) |
| Faithful answers (every claim supported) | 27 of 30 |
| Unanswerable questions refused | 5 of 5 |
| p95 latency, end to end | under 5 seconds |
| Cost per question | computed from token counts, price labelled as assumed |

### Project 2: a fine-tuned model

**Build:** a QLoRA fine-tune of a small open model for one narrow task with a checkable output, for example turning a support ticket into JSON with intent, product and urgency.

1. Collect 500 to 2,000 clean examples. Hold out 10 to 20% and never train on it.
2. Baseline: the base model with its best prompt and a few examples, scored on the held-out set.
3. Print one formatted training example and check the chat template. Train with r = 16 and alpha = 32.
4. Score the base and the fine-tuned model on the same prompts. Run a regression check on 20 general prompts.
5. Serve it on vLLM, run a load test and record TTFT (time to first token).

| Measure | Target |
| --- | --- |
| Valid JSON rate | 99% |
| Field accuracy on the held-out set | 10 points above the best-prompt baseline |
| General prompts that got worse | at most 2 of 20 |
| Peak GPU memory and training time | recorded |
| p95 TTFT at a stated concurrency | recorded |

If the gain is not clear, do not ship, and say so in the README. "The prompt baseline reached 91% and the fine-tune 93%, so I would not pay to host it" is a strong interview answer.

### Project 3: an agent with evals

Three builds prove agent skill. Do them in order, because each reuses the one before.

1. **Build an agent with no framework:** the loop, four tools, a step limit and tracing.
2. **Build an MCP server for a real API** and use it from a LangGraph agent with checkpoints and a human approval step. MCP is the open standard for exposing tools to any model client. A checkpoint is saved state a run can resume from.
3. **Build an eval harness:** 30 tasks, three runs each, pass rate and cost per task. Show one improvement with before and after numbers.

| Measure | Target |
| --- | --- |
| Pass rate over 90 runs | 72 of 90 (80%) |
| Tasks that pass all 3 runs | 21 of 30 |
| Forbidden actions, such as a write without approval | 0 |
| Steps and cost per task | recorded, price labelled as assumed |
| The one improvement | 10 points or more, because a 90-run score carries at least 8 points of noise |

Grade the end state with code (was the right record changed?), not the final message.

### What goes in the README

```
1. Problem      one sentence: who asks what, over which data
2. Run it       one command, with a sample input and output
3. Design       a diagram and five lines: what is offline, what is online
4. Eval         the dataset (size, source), the metric, the results table
5. Changes      each change with its before and after number, kept or reverted
6. Trade-offs   three decisions, what you rejected and why
7. Failures     one bug: the symptom, how you found it, the fix
8. Cost, speed  tokens per request, p95 latency, assumed prices
9. Next         what you would do with one more week
```

### Talking about it in an interview

Prepare a two-minute answer in four parts: problem, design, trade-offs, numbers. Then prepare your own answer to these five. Each one maps to a README section.

| Question | README section |
| --- | --- |
| Walk me through an LLM project you built: problem, design, trade-offs, numbers. | 1, 3, 6, 4 |
| What went wrong, and how did you debug it? | 7 |
| How did you evaluate it? | 4 |
| How would you scale it to ten times the traffic? | 3 and 8 |
| What would you do differently now? | 9 |

Say each answer aloud and time it. Give counts with percentages ("27 of 30"), name the baseline, and state one trade-off before you are asked.

Rule 3 in practice: each project is the evidence for a group of topics. When a question lands on one of them, answer from the project.

| Project | Its README table shows | A trade-off to have ready | Topics you can answer from it |
| --- | --- | --- | --- |
| RAG app | Recall@5, faithful answers and refusals for each version | Reranker quality against added latency | Chunking, hybrid search, reranking, RAG evals |
| Fine-tuned model | Best-prompt baseline against the fine-tune on held-out data, plus the regression check | Fine-tuning against a longer prompt; QLoRA memory saving against slower training | LoRA rank and alpha, QLoRA, chat templates, serving latency |
| Agent with evals | Pass rate, tasks passing all 3 runs and cost per task, before and after | One agent against several; autonomy against approval steps | Tool design, step limits, MCP, checkpoints, agent evals |

## Diagram

Rendering diagram…

## Worked example

**From a change log to a two-minute answer.** The numbers below are an invented example that shows the shape. Use your own.

A student builds a RAG app over 120 pages of college academic rules. The eval set has 30 answerable questions and 5 with no answer in the pages.

| Version | Change | Recall@5 | Faithful answers | Refused (of 5) |
| --- | --- | --- | --- | --- |
| v1 | Dense only, 400-token chunks | 19/30 (63%) | 20/30 | 1/5 |
| v2 | Add BM25 and RRF | 24/30 (80%) | 23/30 | 1/5 |
| v3 | Add a reranker over the top 50 | 27/30 (90%) | 26/30 | 2/5 |
| v4 | "Answer only from context" plus a score threshold | 27/30 (90%) | 27/30 | 5/5 |

**Reading the table.** One question is worth 1/30 = 3.3 points. v1 to v2 is 5 questions, 16.7 points. All 5 contained course codes such as "CS-204", which dense search blurred and BM25 matched exactly. v3 to v4 changed only the prompt and a threshold, so Recall@5 did not move, as expected.

**Cost per question.** 5 chunks x 400 tokens = 2,000, plus 300 tokens of instructions and 50 for the question: 2,350 input tokens. The answer is 250 output tokens. At an assumed 1 USD per million input tokens and 4 USD per million output tokens: 0.00235 + 0.00100 = 0.00335 USD. At 1,000 questions a day that is 3.35 USD a day.

**The spoken answer.** "I built a question-answering app over 120 pages of my college's academic rules, because students keep asking the office the same questions. It chunks the pages, runs dense and keyword search, fuses the two lists, reranks 50 candidates down to 5 and answers with citations. I wrote 30 questions with the correct chunk before I built anything. Dense search alone found the right chunk for 19 of 30. Adding BM25 took that to 24, because course codes need an exact match, and a reranker took it to 27. The trade-off was latency: the reranker added time to every query, which I accepted because nobody needs this answer in under a second. Faithfulness is 27 of 30 by a judge I checked by hand, and it refuses all 5 unanswerable questions. It costs about a third of a cent per question at the prices I assumed."

That is problem, design, trade-off and numbers in about 145 words, with a baseline named and every claim countable.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""A project eval harness: score two versions of a system on the same cases
and print a before/after table you can paste into a README.

The predictions are hard-coded so this runs anywhere. In a real project they
come from running your RAG app, fine-tuned model or agent on each case.
"""
import json
import math
import re

CASES = [
    {"id": "q01", "tag": "lookup", "scorer": "exact", "expected": "30 days"},
    {"id": "q02", "tag": "lookup", "scorer": "exact", "expected": "E-4012"},
    {"id": "q03", "tag": "lookup", "scorer": "number", "expected": 26},
    {"id": "q04", "tag": "lookup", "scorer": "number", "expected": 1499.0},
    {"id": "q05", "tag": "multi-fact", "scorer": "contains", "expected": ["24 days", "5 days"]},
    {"id": "q06", "tag": "multi-fact", "scorer": "contains", "expected": ["receipt", "30 days"]},
    {"id": "q07", "tag": "multi-fact", "scorer": "contains", "expected": ["IT portal", "certificate"]},
    {"id": "q08", "tag": "extract", "scorer": "json", "expected": {"city": "Pune", "pincode": "411001"}},
    {"id": "q09", "tag": "extract", "scorer": "json", "expected": {"city": "Kochi", "pincode": "682001"}},
    {"id": "q10", "tag": "no-answer", "scorer": "refusal", "expected": None},
    {"id": "q11", "tag": "no-answer", "scorer": "refusal", "expected": None},
    {"id": "q12", "tag": "no-answer", "scorer": "refusal", "expected": None},
]

V1 = {  # baseline: dense retrieval only
    "q01": "30 days.", "q02": "The error code is E-4021", "q03": "You get 26 weeks of paid leave.",
    "q04": "Rs 1,499", "q05": "Annual leave is 24 days.", "q06": "File within 30 days with a receipt.",
    "q07": "Renew it.", "q08": '{"city": "Pune", "pincode": "411001"}',
    "q09": 'Here is the JSON: {"city": "Kochi"}', "q10": "The gym opens at 6 am.",
    "q11": "I could not find this in the documents.", "q12": "Probably yes.",
}
V2 = {  # candidate: hybrid retrieval, a reranker and a "say not found" instruction
    "q01": "30 days", "q02": "E-4012", "q03": "26 weeks", "q04": "The refund is 1499 rupees.",
    "q05": "24 days a year, and up to 5 days carry over.", "q06": "Within 30 days, receipts attached.",
    "q07": "The VPN certificate expired. Renew it from the IT portal.",
    "q08": '{"city": "Pune", "pincode": 411001}', "q09": '{"city": "Kochi", "pincode": "682001"}',
    "q10": "Not found in the documents.", "q11": "I could not find this in the documents.",
    "q12": "Not found in the documents.",
}

def norm(text):
    return re.sub(r"[^a-z0-9 -]", "", text.lower()).strip()

def score(case, output):
    kind, expected = case["scorer"], case["expected"]
    if kind == "exact":
        return norm(output) == norm(expected)
    if kind == "contains":                      # every required fact must appear
        return all(norm(fact) in norm(output) for fact in expected)
    if kind == "number":                        # first number in the output, 1% tolerance
        found = re.search(r"-?\d+(?:\.\d+)?", output.replace(",", ""))
        return bool(found) and math.isclose(float(found.group()), expected, rel_tol=0.01)
    if kind == "json":                          # must parse, and every field must match exactly
        try:
            return json.loads(output) == expected
        except json.JSONDecodeError:
            return False
    if kind == "refusal":                       # the right answer is to say it is not there
        return any(p in output.lower() for p in ("not found", "could not find", "do not know"))
    raise ValueError(f"unknown scorer: {kind}")

def run(predictions):
    return {c["id"]: score(c, predictions[c["id"]]) for c in CASES}

if __name__ == "__main__":
    r1, r2 = run(V1), run(V2)
    n = len(CASES)
    print("| Slice | Cases | v1 baseline | v2 candidate |")
    print("| --- | --- | --- | --- |")
    for tag in dict.fromkeys(c["tag"] for c in CASES):
        ids = [c["id"] for c in CASES if c["tag"] == tag]
        print(f"| {tag} | {len(ids)} | {sum(r1[i] for i in ids)}/{len(ids)} | {sum(r2[i] for i in ids)}/{len(ids)} |")
    s1, s2 = sum(r1.values()), sum(r2.values())
    print(f"| all | {n} | {s1}/{n} ({s1 / n:.0%}) | {s2}/{n} ({s2 / n:.0%}) |")

    fixed = [i for i in r1 if not r1[i] and r2[i]]
    broke = [i for i in r1 if r1[i] and not r2[i]]
    print(f"\nfixed by v2 : {len(fixed)} {fixed}")
    print(f"broken by v2: {len(broke)} {broke}   <- read these before you ship")
    print(f"net change  : {len(fixed) - len(broke):+d} of {n} cases")
    print(f"one case is worth {1 / n:.1%}, so report counts, not only percentages")

    assert score(CASES[3], "Rs 1,499") and not score(CASES[7], '{"city": "Pune", "pincode": 411001}')
    assert not score(CASES[1], "The error code is E-4021")
```

## Key takeaways

* Three projects cover the course: a RAG app, a QLoRA fine-tune of a small open model, and an agent with an eval harness.
* Tie every topic to one project. "I used QLoRA on a 7B model and saw..." beats any definition.
* Write about 30 eval cases before the system exists. The first score is your baseline.
* Change one thing at a time and log the before and after number. The log becomes the README table.
* Report quality, latency and cost together, with prices labelled as assumptions.
* The agent harness: 30 tasks, three runs each, pass rate and cost per task, and one improvement with before and after numbers.
* A negative result with numbers ("the fine-tune did not beat the prompt") is a good interview story.
* Present each project in two minutes: problem, design, trade-offs, numbers. Say it aloud.

## Common mistakes

* Building the app first and the eval set last. Without a baseline, no change can be shown to help.
* Picking a problem that is too wide ("a chatbot for everything"). A narrow task has checkable answers.
* Changing three things at once, then not knowing which one moved the number.
* Reporting only percentages on 30 cases. Say "27 of 30" so the listener knows one case is 3.3 points.
* Comparing a fine-tune with a weak prompt. The honest baseline is the base model with its best prompt.
* A README that lists the tech stack and has no numbers, no trade-offs and no failure.

## Practice

* Write the eval set for project 1 before any code: 30 questions with the correct chunk, plus 5 with no answer. Ask a classmate to answer 10 of the 30 using only the documents. Target: 9 of 10 match your expected answers.
* Build project 1 through three versions and fill a table with Recall@5, faithful answers and refusals for each. Target: at least one change of 3 questions or more that you can explain.
* Run the code example, then fix the regression in q08 without weakening the scorer and add a fifth scorer that checks a regular expression. Target: 12 of 12 for v2 and an empty broken list.
* Record yourself answering the five interview questions for one project. Target: each answer under two minutes, with at least two numbers and one trade-off.

## Interview questions (8)

1.Walk me through an LLM project you built: problem, design, trade-offs, numbers.Medium

I keep it to four parts and under two minutes. Here is the shape, with example numbers. Problem: a support agent that answers order questions and can start a refund, over a mock order API. Design: an agent loop I wrote with no framework, four tools, a step limit of 10 and a trace for every run. Later I moved the tools behind an MCP server and put a human approval step in front of the refund tool. Trade-off: I kept a single agent, because the tasks are short and sub-agents would have multiplied the token cost. Numbers: 30 tasks, three runs each. The pass rate went from 61 of 90 to 76 of 90 after I rewrote two tool descriptions and returned tool errors as readable text. There were zero refunds without approval.

2.What went wrong, and how did you debug it?Medium

A good answer has five steps: the symptom, how I narrowed it down, the cause, the fix, and the number after the fix. An example from a fine-tuning project: my fine-tuned model scored below the base model on valid JSON, 71% against 88%. I first suspected the data, but the training loss looked normal. So I printed one fully formatted training example and one inference prompt as raw text and compared them. The training examples ended with an end-of-turn token and my inference prompt did not use the chat template at all. After I applied the same template at inference, valid JSON went to 99%. What I changed in my process: I now print one formatted example before every training run.

3.How did you evaluate it?Medium

I name five things. The dataset: how many cases, where they came from, and that I wrote them before building. The metric: for my RAG app, Recall@5 for retrieval and faithfulness for the answer, measured separately. The grader: a code check where a program can decide, and an LLM judge for faithfulness that I checked by hand on all 30 cases. The baseline: the simplest version, dense search only. And the noise: with 30 cases one question is 3.3 points, so I only claim changes of several questions, and I list which cases were fixed and which broke.

4.How would you scale it to ten times the traffic?Hard

I start from what I measured. In my RAG app the model call is most of the latency and most of the cost, so that is where ten times the traffic hurts first. For latency I would check the provider's rate limits, or for a self-hosted model run a load test to find what one replica sustains at my p95 target and add replicas from that number. For cost I would cache repeated questions and send easy questions to a smaller model, with my eval set as the gate for both changes. Retrieval is not the bottleneck: a few thousand chunks fit in memory. If the documents grew ten times as well, I would move to an HNSW index and re-check Recall@5.

5.What would you do differently now?Easy

I pick one decision and give the evidence. For example: I would write the eval set on day one. In my first version I spent a week tuning chunk sizes by reading a few answers, and when I finally wrote 30 questions the chunk size made a difference of one question, while adding keyword search fixed five. I would also log traces from the start, because I had to re-run failures to see which chunks had been retrieved. The point of the answer is to show that the numbers changed what I believe, not to list regrets.

6.Why build the agent with no framework before using LangGraph?Medium

Because the loop is small and it is what interviewers probe. Writing it myself forced me to decide how tool errors go back to the model, when the run stops, and what gets logged at each step. After that, a framework is easy to read: I know which of my lines it replaces. Then I used LangGraph for what I did not want to write myself, which is checkpoints, resume after a crash and a human approval step. I can explain both versions and say what the framework gave me and what it hid.

7.Your eval set has only 30 cases. Why should I trust the numbers?Hard

You should trust large differences and not small ones. At 27 of 30 the standard error is the square root of 0.9 times 0.1 over 30, about 5.5 points, so the 95% range is roughly plus or minus 11 points. I do three things about that. I report counts, not only percentages. I compare versions on the same cases and list which ones were fixed and which broke, which is more informative than two averages. And I only claim a gain when it is several questions and I can explain the cause, such as course codes needing exact match. For a decision that matters, I would grow the set from real failures before trusting a 3 point change.

8.Your fine-tune did not beat the prompt baseline. Is the project still worth showing?Medium

Yes, if the numbers are honest. The finding is useful: for this task a good prompt was enough, and hosting a fine-tuned model would not have paid for itself. I show the held-out scores for both, the size and quality of the training data, what I tried (more data, a higher rank, a cleaner format) and what each did. Then I say when I would expect fine-tuning to win: a stricter output format, a smaller and cheaper base model, or far more traffic. An interviewer learns more from that than from a win I cannot explain.

## Quiz

1.What should exist before the first version of any of the three projects?

2.The agent eval harness uses 30 tasks with three runs each. How many runs are graded, and why three?

3.Recall@5 goes from 19 of 30 to 24 of 30 after adding BM25. How large is the change?

4.Which baseline is the fair one for a fine-tuning project?

5.Which line best follows the rule "tie every topic to one project" when asked about hybrid search?

## Practice these problems

* [GENAIRAG pipeline for internal docs Q&AMedium](/ai/problems/rag-pipeline)
* [GENAIMCP tool platform for internal APIsMedium](/ai/problems/mcp-tool-platform)
* [GENAILoRA fine-tuning pipeline with an adapter registryHard](/ai/problems/fine-tuning-pipeline)
* [GENAIEvaluation harness for LLM apps and agentsMedium](/ai/problems/llm-eval-harness)
* [MLCODEAgent loop from scratch with tools and a step limitMedium](/ai/problems/agent-loop-from-scratch)
* [MLCODEMinimal RAG loop: chunk, embed, retrieve, promptEasy](/ai/problems/minimal-rag-loop)

## Further reading

* [Building effective agentsArticleanthropic.com](https://www.anthropic.com/engineering/building-effective-agents)
* [Model Context Protocol documentationGuidemodelcontextprotocol.io](https://modelcontextprotocol.io/)
* [Hugging Face PEFT documentationGuidehuggingface.co](https://huggingface.co/docs/peft)
* [LangGraph overviewGuidedocs.langchain.com](https://docs.langchain.com/oss/python/langgraph/overview)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAdvanced topics](/ai/learn/advanced-topics)[NextLLMs on cloud - Bedrock, Azure OpenAI, Vertex AI](/ai/learn/llms-on-cloud)

## On this page

1. [Lesson](#lesson)
2. [Diagram](#diagram)
3. [Worked example](#example)
4. [Code](#code)
5. [Key takeaways](#takeaways)
6. [Common mistakes](#mistakes)
7. [Practice](#practice)
8. [Interview questions](#interview)
9. [Quiz](#quiz)
10. [Related problems](#problems)
11. [Further reading](#reading)
12. [My notes](#notes)

## In this lesson

1. [Why three projects](#why-three-projects)
2. [The loop every project follows](#the-loop-every-project-follows)
3. [Project 1: a RAG app](#project-1-a-rag-app)
4. [Project 2: a fine-tuned model](#project-2-a-fine-tuned-model)
5. [Project 3: an agent with evals](#project-3-an-agent-with-evals)
6. [What goes in the README](#what-goes-in-the-readme)
7. [Talking about it in an interview](#talking-about-it-in-an-interview)
