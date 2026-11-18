# LLMs on cloud - Bedrock, Azure OpenAI, Vertex AI — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/llms-on-cloud

[AI roadmap](/ai)

LaterLesson #24LaterIntermediate 1.5 h

# LLMs on cloud - Bedrock, Azure OpenAI, Vertex AI

Amazon Bedrock, Azure OpenAI and Google Vertex AI each give you one managed API to many models inside your own cloud account. The product names differ, but the ideas are the same: pay per token or reserve capacity, live inside quotas, choose where data is processed, lock access down with cloud identity and private networking, and add managed retrieval, agents, guardrails, tuning and evals. This lesson teaches the shared ideas and when to self-host instead.

cloudamazon bedrockazure openaivertex aiprovisioned throughputrate limitsself-hosting

## Why it matters

Most companies do not call a model lab directly. They buy models through the cloud they already use, because billing, access control and compliance are already set up there. So interviewers ask what someone who has shipped on a cloud would know: on-demand or provisioned throughput, what a 429 means and what you do about it, how you keep data in one region, and when a GPU of your own is cheaper than tokens. You do not need to memorise three product catalogues. You need the six ideas that are common to all three, and one cost calculation you can do on a whiteboard.

Read first: [Inference and serving - KV cache, batching, vLLM](/ai/learn/inference-serving), [Evals, tracing and guardrails](/ai/learn/evals-tracing-guardrails), [LLM system design](/ai/learn/llm-system-design)

## Lesson

### Three clouds, one shape

Each cloud sells the same thing: a managed API, inside your cloud account, to models from several providers, on your normal cloud bill.

* **Amazon Bedrock** is a fully managed service for foundation models from Amazon and from other model companies.
* **Azure OpenAI** is how Azure serves OpenAI models. The documentation now places it inside a wider platform, Microsoft Foundry, and calls it "Azure OpenAI in Microsoft Foundry Models". The same catalogue also holds models from other providers.
* **Vertex AI** is Google Cloud's platform. Its documentation now uses the name Gemini Enterprise Agent Platform, and has a page that maps each old Vertex AI name to the new one. Its Model Garden offers Google's own models such as Gemini, partner models and open models.

Interviewers still say "Azure OpenAI" and "Vertex AI". Know both names, and learn the ideas below, because names change and ideas do not.

### Three ways to pay

1. **On-demand (pay per token).** No commitment, and no cost when there is no traffic. Capacity is shared with other customers, so throughput and latency can vary.
2. **Reserved capacity (provisioned throughput).** You pay a fixed price for a fixed amount of throughput, used or not. You get steadier latency and a predictable bill. Bedrock sizes it in model units billed hourly, Azure in provisioned throughput units (PTUs) billed hourly, Google in generative AI scale units (GSUs) bought for a term such as a week or a month. On Bedrock and Azure a longer commitment lowers the hourly price.
3. **Batch.** You submit a file of requests and collect results later. All three list batch at 50 percent below the on-demand rate, Bedrock for the models that support batch. Azure and Google both state a 24-hour target turnaround, and Azure gives batch its own quota.

Bedrock and Google also offer a cheaper flex tier for work that tolerates slow responses, and a priority tier at a higher price. The usual production design reserves the steady baseline and lets peaks overflow to on-demand. Azure calls this spillover.

![Monthly cost against requests per day for on-demand tokens, batch tokens and two self-hosted GPUs, with the two break-even points marked](/ai/img/cloud-llm-break-even.svg)Monthly cost against requests per day for on-demand tokens, batch tokens and two self-hosted GPUs, with the two break-even points marked

The picture uses the assumed prices from the worked example below. The two token lines rise with volume and the GPU line is flat, so each token line crosses it once.

### Quotas, rate limits and the 429

On-demand capacity is limited per account, in tokens per minute (TPM) and often requests per minute (RPM).

* **Bedrock:** TPM per model, counting input plus output tokens, and a tokens-per-day cap across models. `max_tokens` is deducted from the quota when a request starts and corrected when it ends. For some models one output token counts as several.
* **Azure:** TPM is assigned per subscription, region, model and deployment type, and RPM is set in proportion to it. The TPM check uses an estimate made when the request arrives, and that estimate includes `max_tokens`. RPM is checked over windows of 1 or 10 seconds, so a burst is throttled even when the minute total is fine.
* **Google:** Standard PayGo gives an organisation a TPM threshold that rises with its spend over a rolling 30 days. Traffic above the threshold is served only when the shared pool has spare capacity, and is throttled first when demand is high.

When you pass a limit, or the shared pool is busy, you get HTTP 429. Retry with exponential backoff and random jitter, cap the retries, and obey the wait hint if there is one (Azure sends a `retry-after-ms` header). Then fix the cause: smooth bursts, lower `max_tokens`, request more quota, or reserve capacity. On Bedrock a 429 is your quota and a 503 is service capacity; for the 503 the docs suggest cross-Region inference.

### Regions and data residency

All three offer three routing scopes, and the wider the scope, the more capacity you get.

| Scope | Where inference can run | Named as |
| --- | --- | --- |
| Narrowest | Bedrock: the Region you call. Azure: the Azure geography of your resource. Google: the country or jurisdiction of the region you call | Bedrock without a cross-Region inference profile; Azure Standard; Google locational (regional) endpoint |
| A geography | Any region inside US, EU or a similar zone | Bedrock Geographic cross-Region inference; Azure Data Zone; Google jurisdictional multi-region endpoint |
| Global | Any region the provider chooses | Bedrock Global cross-Region inference; Azure Global Standard; Google global endpoint |

Read the first row carefully. On Azure and Google the narrowest option promises a geography or a country, not one data centre region. If a rule names a single region, check the provider's wording before you promise it.

Separate data at rest from data being processed. Azure and Google keep data at rest in the location you chose whichever scope you call; only processing moves. Google's docs say the global endpoint gives no residency guarantee. Bedrock records the Region that served each cross-Region request in CloudTrail.

### Identity and private networking

Do not ship long-lived API keys. Use the cloud's identity system: IAM roles with temporary credentials on AWS, Microsoft Entra ID with managed identities and role-based access control on Azure, IAM on Google Cloud. Azure's docs say API keys cannot express a user identity and are not recommended for production. Keep traffic off the public internet with an interface VPC endpoint (AWS PrivateLink) or an Azure private endpoint with public network access disabled. On Google Cloud, VPC Service Controls put a perimeter around the API so data cannot leave it.

### The managed building blocks

| Need | Bedrock | Azure OpenAI | Vertex AI |
| --- | --- | --- | --- |
| Pay per token | On-demand | Standard deployment | Standard PayGo |
| Reserved capacity | Provisioned Throughput; Reserved tier | Provisioned deployment (PTUs) | Provisioned Throughput (GSUs) |
| Batch | Batch inference | Global Batch, Data Zone Batch | Batch inference |
| Managed retrieval | Knowledge Bases | Foundry IQ, built on Azure AI Search | RAG Engine |
| Managed agents | AgentCore | Foundry Agent Service | Agent Runtime, Agent Development Kit |
| Guardrails | Guardrails | Guardrails and controls | Model Armor |
| Customisation | Fine-tuning, distillation, Custom Model Import | Fine-tuning | Tuning |
| Evaluation | Evaluations | Evaluations | Evals, formerly Gen AI evaluation service |
| Open model on your own GPUs | SageMaker AI endpoint | Managed compute (preview) | Self-deployed model from Model Garden |

Managed retrieval runs the RAG pipeline for you: ingestion, chunking, embedding, indexing and retrieval with citations. Guardrails check the prompt and the response. Bedrock Guardrails can also be called alone, without invoking a model, and Azure gives a model a default guardrail unless you assign your own. Fine-tuning on all three is supervised first, with preference or reinforcement methods as extras.

### Managed API or self-hosted on cloud GPUs

|  | Managed API | Self-hosted on cloud GPUs |
| --- | --- | --- |
| Billing | Per token; nothing at zero traffic | Per GPU-hour, idle or busy |
| Capacity | Shared pool, quotas, 429s | Fixed by your GPUs; you queue or scale |
| Models | The provider's catalogue, closed models included | Any open weights, your fine-tunes and adapters |
| Control | Provider retires model versions on its schedule | You pin version, quantization and serving engine |
| Operations | Close to none | Autoscaling, upgrades, load tests, on-call |
| Wins when | Volume is low or spiky; you need the strongest models | Volume is steady and high; data rules are strict |

Self-host for three reasons: cost at steady high volume, control, and data rules. Otherwise use the managed API, because an idle GPU still costs money. Google's docs make the same trade: self-deployment can lower the total cost over an application's lifetime, and it needs a greater upfront engineering investment.

## Diagram

Rendering diagram…

## Worked example

**Tokens or a GPU?** A team summarises support tickets with a small model. Each request has 1,500 input tokens and 300 output tokens. Every price below is an assumption for the exercise, not a quote from any cloud.

1. **On-demand cost per request.** At an assumed 0.30 USD per million input tokens and 1.20 USD per million output tokens: 1,500 x 0.30 / 1,000,000 = 0.00045 USD, plus 300 x 1.20 / 1,000,000 = 0.00036 USD. Total 0.00081 USD per request, or 0.81 USD per 1,000 requests.
2. **Self-hosted cost per month.** Two GPUs, so one can fail, at an assumed 1.50 USD per GPU-hour, running all 720 hours of a 30-day month: 2 x 1.50 x 720 = 2,160 USD. This is the same at any volume.
3. **Break-even.** 2,160 / 0.00081 = 2,666,667 requests per month, which is 88,889 per day, about 1 request per second.
4. **Check capacity.** At break-even the output rate is 88,889 x 300 / 86,400 = 309 tokens per second on average. If one GPU sustains an assumed 2,500 output tokens per second, even a peak of three times the average (926) fits on one GPU.
5. **Read the result.** At 20,000 requests a day on-demand costs 20,000 x 30 x 0.00081 = 486 USD a month against 2,160: stay on the API. At 200,000 a day it costs 4,860 USD against 2,160: self-hosting saves 2,700 USD a month.
6. **Add the costs people forget.** Add an assumed 1,000 USD a month of engineering time and the break-even moves to 3,160 / 0.00081 = 3,901,235 requests a month, 130,041 a day. Separately, if the work is not urgent and runs as batch at half price, each request costs 0.000405 USD and the break-even from step 3 doubles: 2,160 / 0.000405 = 5,333,333 requests a month, 177,778 a day.

The answer to say aloud: "Below about 90,000 requests a day the API is cheaper. Above it I would self-host, if an open model passes my eval set."

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""Break-even between on-demand tokens and self-hosted GPUs.

Every price in this file is an assumption. Replace them with the numbers
from your provider's pricing page and from your own load test.
"""

def on_demand_cost_per_request(in_tokens, out_tokens, usd_per_m_in, usd_per_m_out):
    return in_tokens * usd_per_m_in / 1e6 + out_tokens * usd_per_m_out / 1e6

def self_hosted_cost_per_month(gpus, usd_per_gpu_hour, ops_usd_per_month=0.0, hours=720):
    return gpus * usd_per_gpu_hour * hours + ops_usd_per_month

def break_even_requests_per_day(fixed_usd_per_month, usd_per_request, days=30):
    return fixed_usd_per_month / usd_per_request / days

def gpus_needed(requests_per_day, out_tokens, tokens_per_sec_per_gpu, peak_factor=3.0):
    """GPUs to carry the peak output rate, rounded up, plus one spare."""
    peak_tps = requests_per_day * out_tokens / 86_400 * peak_factor
    active = max(1, -(-peak_tps // tokens_per_sec_per_gpu))  # ceiling division
    return int(active) + 1, peak_tps

if __name__ == "__main__":
    IN_TOK, OUT_TOK = 1_500, 300
    USD_PER_M_IN, USD_PER_M_OUT = 0.30, 1.20      # assumed on-demand prices
    USD_PER_GPU_HOUR = 1.50                       # assumed GPU price
    TPS_PER_GPU = 2_500                           # assumed, measure with a load test

    per_req = on_demand_cost_per_request(IN_TOK, OUT_TOK, USD_PER_M_IN, USD_PER_M_OUT)
    fixed = self_hosted_cost_per_month(2, USD_PER_GPU_HOUR)
    fixed_ops = self_hosted_cost_per_month(2, USD_PER_GPU_HOUR, ops_usd_per_month=1_000)

    print(f"on-demand cost per request : {per_req:.5f} USD")
    print(f"two GPUs for a month       : {fixed:,.0f} USD")
    print(f"break-even                 : {break_even_requests_per_day(fixed, per_req):,.0f} requests/day")
    print(f"break-even with ops cost   : {break_even_requests_per_day(fixed_ops, per_req):,.0f} requests/day")
    print(f"break-even against batch   : {break_even_requests_per_day(fixed, per_req / 2):,.0f} requests/day")
    print()
    print(f"{'requests/day':>12} {'API USD/mo':>11} {'GPUs':>5} {'GPU USD/mo':>11}  cheaper")
    for per_day in (20_000, 88_889, 200_000, 1_000_000):
        api = per_day * 30 * per_req
        n, peak = gpus_needed(per_day, OUT_TOK, TPS_PER_GPU)
        gpu = self_hosted_cost_per_month(n, USD_PER_GPU_HOUR)
        winner = "API" if api < gpu else "self-host"
        print(f"{per_day:>12,} {api:>11,.0f} {n:>5} {gpu:>11,.0f}  {winner}")

    assert abs(per_req - 0.00081) < 1e-12
    assert round(break_even_requests_per_day(fixed, per_req)) == 88_889
    assert round(break_even_requests_per_day(fixed_ops, per_req)) == 130_041
    print("checks ok")
```

## Key takeaways

* The three clouds sell the same shape: one managed API to several model families, inside your account and on your cloud bill.
* Three ways to pay: on-demand per token, reserved capacity for steady load, batch at half price for work that can wait.
* Limits are mostly in tokens per minute. Passing one returns 429; back off with jitter, then fix the cause.
* Routing scope is a trade: the narrowest scope for strict residency, a geography such as EU for more capacity, global for the most.
* Use cloud identity with roles, not long-lived keys, and a private endpoint so traffic stays off the public internet.
* Managed retrieval, agents, guardrails, tuning and evals exist on all three. Learn the idea, then look up the name.
* Self-host for cost at steady high volume, for control, or for data rules. Compute the break-even before you decide.

## Common mistakes

* Buying provisioned throughput before measuring traffic, then paying for capacity that sits idle at night.
* Retrying a 429 immediately in a tight loop. On Azure, failed calls still count against the limit, so throttling gets worse.
* Choosing a global deployment for regulated data because it had the highest quota.
* Leaving `max_tokens` at a large default. Azure and Bedrock both count it against the token limit when the request arrives.
* Comparing GPU cost with token cost and forgetting idle hours, the spare replica and engineering time.
* Memorising product names. They change; two of the three platforms were renamed in their own docs.

## Practice

* Take one feature you have built. Measure input and output tokens per request, then run the break-even calculator with prices from one provider's pricing page. Report the break-even in requests per day.
* Write a client wrapper that retries on 429 and 503 with exponential backoff, jitter and a cap of 5 attempts. Test it against a fake server that fails the first 3 calls, and print the wait before each retry.
* For one cloud, find the docs pages for its regional, geography and global options. Write three lines: where prompts can be processed under each.
* Fill in the building-blocks table from memory, then check each cell against the current docs. Note every name that has changed.

## Interview questions (8)

1.On-demand or provisioned throughput?Medium

It depends on how steady the traffic is and how much latency variation I can accept. On-demand is pay per token on shared capacity: no commitment and no cost at zero traffic, but throughput can vary and I can be throttled. Provisioned throughput reserves capacity for a fixed price whether I use it or not, so it only pays off at high utilisation, and it gives steadier latency. I start on-demand, measure tokens per minute for a few weeks, then reserve only the steady baseline and let peaks overflow to on-demand. Anything that is not urgent goes to batch, which all three clouds list at half the on-demand rate.

2.How do you keep data in one region?Medium

First I separate data at rest from where inference runs, because they are controlled differently. Then I choose the routing scope that matches the rule. If the rule names one region, I use the narrowest option, accept a smaller quota, and read the fine print: on Azure and Google that option promises a geography or country, not a single region. If it says EU or US, I use the geography option: Geographic cross-Region inference on Bedrock, a Data Zone deployment on Azure, a multi-region endpoint on Google. I do not use the global option for regulated data, because it can process in any region and Google's docs say it gives no residency guarantee. Last, I prove it: a policy that blocks the global option where the cloud supports one, and logs that record which region served each request.

3.How do you handle a 429 from a model API?Medium

A 429 means I was rate limited or the shared pool is busy. It is not a bug in the request. I retry with exponential backoff and random jitter, cap it at about five attempts, and obey the wait hint if the provider sends one; Azure returns a retry-after-ms header. Retrying at once makes it worse: it adds load, and on Azure failed requests still count toward the limit. Then I fix the cause: smooth bursts with a queue or token bucket in my gateway, set max\_tokens no higher than needed, ask for more quota, move steady load to reserved capacity, and fall back to a second model or region. On Bedrock I also keep 429 apart from 503, which means service capacity, not my quota.

4.When would you self-host?Medium

For three reasons: cost at steady high volume, control, and data rules. A GPU costs the same per hour busy or idle, so I compute the break-even: monthly GPU and operations cost divided by the on-demand cost per request. Below that volume the managed API wins. Control means pinning a model version, serving my own fine-tune or LoRA adapters, and choosing the quantization and the serving engine. Data rules means prompts must stay on machines I operate. Against that I weigh the work: capacity planning, autoscaling, upgrades and on-call. And the open model has to pass my eval set first, or the cost comparison does not matter.

5.What do Bedrock, Azure OpenAI and Vertex AI have in common?Easy

The same shape. Each gives one managed API to models from several providers inside my cloud account, billed with the rest of my cloud usage. Each has pay per token, reserved capacity and discounted batch. Each limits on-demand use in tokens per minute and returns 429 when I pass the limit. Each lets me choose a narrow, geography-wide or global routing scope. Each uses the cloud's own identity system and private networking. And each adds managed retrieval, agents, guardrails, tuning and evaluation on top. The differences are mostly which models are in the catalogue and what the features are called.

6.How do you secure access to a model API on a cloud?Medium

Identity first. The service calls the model with a role or managed identity that has temporary credentials and permission for only the models it needs, not a shared API key, because a key cannot say which user or service made the call. Then the network: a private endpoint so traffic never crosses the public internet, with public access disabled. Then data: encryption keys I manage where required, logging of every call with the caller and the region, and a guardrail on prompts and responses. I also pass the end user's permissions into retrieval, so the model never sees a document the user cannot open.

7.You must summarise two million documents by next week. How do you run it cheaply?Easy

As a batch job, not through the live endpoint. I write the requests to files with a stable id per document, submit them to the batch API, and collect the output when the job finishes. It costs about half the on-demand rate and keeps the load off the live endpoint; Azure, for example, gives batch a separate quota. I test the prompt on a few hundred documents first with an eval, cap output tokens, and make the job safe to rerun: the id lets me skip documents that already have a result. If part of it is urgent, only that part goes on-demand.

8.How do you avoid being locked in to one cloud's LLM platform?Hard

I put a gateway in front: my services call one internal API, and adapters translate to each provider. Prompts, eval sets and traces stay in my own storage, so I can replay the same eval against a second provider before I need it. The sticky parts are the managed ones: a knowledge base, an agent runtime, a guardrail policy. I use them when they save real work, but behind my own interface, and I keep source documents and tool definitions outside them. Full portability costs something too, so for a small team I accept one cloud and keep the exit path tested.

## Quiz

1.Traffic is flat at 40 percent of capacity all day and latency must be predictable. Which pricing fits best?

2.A rule says prompts must be processed inside the EU. Which routing scope do you choose?

3.On Azure, why can a request be rate limited when your billed tokens are below the TPM quota?

4.On-demand costs 0.00081 USD per request and self-hosting costs 2,160 USD per month. What is the break-even?

5.What is the correct first response to an HTTP 429 from a model API?

## Practice these problems

* [GENAILLM gateway with routing, caching and fallbackHard](/ai/problems/llm-gateway)
* [GENAIGuardrails and PII redaction layerMedium](/ai/problems/guardrails-pii-redaction)
* [GENAICut LLM cost by half: model routing and cascadesMedium](/ai/problems/llm-cost-router)
* [MLSDServe an open model to 1,000 concurrent usersHard](/ai/problems/llm-serving-platform)

## Further reading

* [Amazon Bedrock documentationGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/bedrock/)
* [Microsoft Foundry documentation (home of Azure OpenAI)Guidelearn.microsoft.com](https://learn.microsoft.com/azure/ai-services/openai/)
* [Gemini Enterprise Agent Platform documentation (formerly Vertex AI)Guidecloud.google.com](https://cloud.google.com/vertex-ai/docs)
* [Deployment types for Microsoft Foundry ModelsGuidelearn.microsoft.com](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousProjects - RAG app, fine-tuned model, agent + evals](/ai/learn/projects)

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

1. [Three clouds, one shape](#three-clouds-one-shape)
2. [Three ways to pay](#three-ways-to-pay)
3. [Quotas, rate limits and the 429](#quotas-rate-limits-and-the-429)
4. [Regions and data residency](#regions-and-data-residency)
5. [Identity and private networking](#identity-and-private-networking)
6. [The managed building blocks](#the-managed-building-blocks)
7. [Managed API or self-hosted on cloud GPUs](#managed-api-or-self-hosted-on-cloud-gpus)
