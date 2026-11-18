# AI interview prep: GenAI roadmap and ML system design questions · FAANGrind

Source: https://faangrind.vercel.app/ai

AI

# GenAI, agents and ML systems.

24 lessons (70.5 h of study) and 40 interview problems: RAG, agents, LLM serving, ML system design and implement-it coding.

16 to study, 2 to skim, 6 for later 6 easy, 18 medium, 16 hard

## Roadmap

Read the modules in order. Each lesson has a worked example, runnable code, interview questions and a quiz.

[Jump to problems](#problems)

1

### Foundations

6 lessons · 14 h

1. [#1SkimBeginner 45 minHistory - how AI got to transformersAI did not jump straight to LLMs (large language models). Each generation of methods hit a wall, and the next idea was built to get past it: hand-written rules, then learning from data, then deep networks on GPUs, then attention, then transformers pretrained on huge amounts of text. This lesson walks that chain in order, so you can explain why a transformer looks the way it does and which problem each part solves.Open lesson](/ai/learn/history-ai-to-transformers)
2. [#2StudyBeginner 3.5 hNeural networks and backpropA neural network is a stack of simple units. Each unit multiplies its inputs by weights, adds a bias and applies a non-linear function. Training means finding weights that make a loss number small. Backpropagation computes how much each weight contributed to the loss, and gradient descent moves each weight a small step in the direction that lowers it. This lesson covers both, plus the basics interviewers check: activations, losses, optimisers, regularisation, normalisation and metrics.Open lesson](/ai/learn/neural-networks-backprop)
3. [#3SkimBeginner 1 hRNNs, LSTMs, CNNsRNNs, LSTMs and CNNs are the three network designs that came before the transformer. An RNN reads a sequence one step at a time and carries a memory vector forward. An LSTM is an RNN with gates that protect that memory. A CNN slides small filters over an image. This lesson explains what each one solved, the limit each one hit, and which parts are still inside the models you use today.Open lesson](/ai/learn/rnns-lstms-cnns)
4. [#4StudyBeginner 3 hLLM fundamentals - tokens, embeddings, decodingAn LLM (large language model) is a neural network trained to do one thing: predict the next token. This lesson follows a piece of text through the whole machine. Text becomes tokens, tokens become vectors, a stack of transformer blocks mixes those vectors, and a decoding rule picks the next token from the output probabilities. You will work each stage with small numbers.Open lesson](/ai/learn/llm-fundamentals)
5. [#5StudyIntermediate 2.5 hCoding simple attentionSelf-attention lets every token update its vector using the other tokens in the sequence. This lesson builds it in small steps: measure similarity with a dot product, turn the scores into weights with softmax, and take a weighted sum. Then it adds the three things a real layer needs: the scaling by the square root of d\_k, the causal mask and multiple heads. Every step is worked with numbers you can check by hand.Open lesson](/ai/learn/coding-simple-attention)
6. [#6StudyBeginner 3 hHugging Face end to endHugging Face is where open models live and the set of Python libraries used to run them. This lesson follows one path from start to finish: find a model on the Hub, read its card and licence, load the tokenizer and the weights, format a chat with the model's template, generate text, measure the output, and save or push your own version. Every step names the object you get back.Open lesson](/ai/learn/hugging-face-end-to-end)

2

### Build with LLMs

4 lessons · 13.5 h

1. [#7StudyBeginner 2.5 hPrompting and context engineeringPrompt engineering is writing a good instruction. Context engineering is deciding everything that enters the context window: instructions, examples, retrieved data, tool definitions and history. This lesson covers both: the parts of a prompt, when to use few-shot examples or step-by-step reasoning, how to get valid JSON every time, how to keep a long conversation inside a token budget, and how to prove a prompt change helped.Open lesson](/ai/learn/prompting-context-engineering)
2. [#8StudyIntermediate 4 hVector DBs and RAGRAG (retrieval-augmented generation) fetches relevant text at query time and puts it in the prompt, so a model answers from your data without being retrained. A vector database makes the fetching fast: it stores an embedding for every chunk of text and finds the nearest ones to a query in milliseconds. This lesson covers both, from chunking to evaluation.Open lesson](/ai/learn/vector-dbs-rag)
3. [#9StudyIntermediate 3 hWhat is fine-tuning - LoRA, QLoRA, DoRAFine-tuning changes how a model behaves by updating its weights on your examples. Updating every weight of a large model is expensive, so the LoRA family freezes the base model and trains a small add-on called an adapter, usually under 1% of the parameters. This lesson explains LoRA from the formula up, then QLoRA, DoRA and rsLoRA, and how to choose between them.Open lesson](/ai/learn/fine-tuning-lora-qlora-dora)
4. [#10StudyIntermediate 4 hFine-tuning a model for a real use caseThis lesson takes one real task, a model that sorts support tickets and drafts a reply, and walks the whole fine-tuning job from start to finish. You decide whether to fine-tune at all, build and clean the dataset, format it with the chat template, split it, train a QLoRA adapter, read the loss curves, compare with the base model, serve the adapter, and debug a run that made things worse.Open lesson](/ai/learn/fine-tuning-real-use-case)

3

### Serving

1 lessons · 3.5 h

1. [#11StudyIntermediate 3.5 hInference and serving - KV cache, batching, vLLMInference is running a trained model to produce output. Serving is doing that for many users at once, fast and cheaply. This lesson follows one request through an LLM server: the prefill and decode phases, the KV cache that makes decode fast, batching that keeps the GPU busy, quantization that shrinks the model, and the metrics and engines you use to run it in production.Open lesson](/ai/learn/inference-serving)

4

### Agents

4 lessons · 15.5 h

1. [#12StudyIntermediate 4 hAgents from first principles - build a mini frameworkAn agent is an LLM running in a loop with tools: it chooses an action, sees the result, and repeats until the goal is met. A chatbot answers; an agent acts. This lesson builds a small agent framework piece by piece (message list, tools, registry, loop, error handling, limits), so you can explain what any agent framework is doing underneath.Open lesson](/ai/learn/agents-first-principles)
2. [#13StudyIntermediate 4 hAgent frameworks - LangChain, LangGraphAn agent framework gives you the loop, the state and the tool plumbing from the previous lesson as ready-made parts. This lesson names the eight frameworks interviewers expect you to recognise, then teaches you to read LangChain and LangGraph code line by line: tools, `create\_agent`, state, reducers, nodes, conditional edges, checkpointers and interrupts.Open lesson](/ai/learn/agent-frameworks-langchain-langgraph)
3. [#14StudyIntermediate 3.5 hTools, MCP and memoryA tool is a function your application offers to a model: a name, a description and a schema for the arguments. MCP (Model Context Protocol) is an open standard for packaging tools and data so any compatible AI application can use them. Memory is how an agent keeps facts beyond one context window. This lesson covers how to design all three, and what each one costs in tokens.Open lesson](/ai/learn/tools-mcp-memory)
4. [#15StudyAdvanced 4 hAgents in depth - patterns, reliability, securityThis lesson is about agents in production. It covers the seven architecture patterns and how each one fails, why long tasks fail more often than short ones, how to manage context over hours, how to make actions safe to retry with idempotency keys and checkpoints, how to evaluate an agent, and how to keep it from leaking data. It ends with a full design of a customer support agent.Open lesson](/ai/learn/agents-in-depth)

5

### Ship

3 lessons · 9 h

1. [#16StudyIntermediate 3.5 hEvals, tracing and guardrailsAn eval is a repeatable test that tells you whether a change made an LLM system better or worse. A trace is the record of one request: every prompt, retrieval, tool call, token count, latency and cost. A guardrail is a check on what goes into the model or comes out of it. This lesson shows how to build all three, with the numbers and the wording interviewers expect.Open lesson](/ai/learn/evals-tracing-guardrails)
2. [#17StudyIntermediate 3 hLLM system designLLM system design is the interview round where you design a whole product around a model: a chat service, document Q&A, a support agent or a serving platform. Almost every answer uses the same five layers and the same seven steps. This lesson gives you the layers, the steps, the arithmetic for capacity, cost and latency, and the points each common question expects.Open lesson](/ai/learn/llm-system-design)
3. [#18StudyIntermediate 2.5 hWhat is new in 2026 + revisionThis is the last stop before the interview. It lists the eleven 2026 trends an interviewer may probe, each with what it is, why it matters to someone who builds systems, and a line you can say. It then gives the 37-term revision sheet for the rapid-fire round, and a structure for answering "what have you been following lately?" in two minutes.Open lesson](/ai/learn/whats-new-2026-revision)

6

### Later

6 lessons · 15.5 h

1. [#19LaterAdvanced 1.5 hAttention variations - GQA, MLAStandard multi-head attention stores a key and a value for every head, every layer and every past token. That store, the KV cache, is the main memory cost of serving besides the weights. This lesson covers the variants that shrink it: multi-query attention, grouped-query attention (GQA) and multi-head latent attention (MLA). It also places FlashAttention and sliding-window attention, which solve different problems.Open lesson](/ai/learn/attention-variations-gqa-mla)
2. [#20LaterAdvanced 1.5 hRL fine-tuningSupervised fine-tuning needs the right answer written out for every example. Reinforcement learning (RL) fine-tuning needs only a score: which of two answers a person preferred, or whether a program accepted the answer. This lesson explains policy, reward and policy gradient in plain words, then the three methods used on LLMs: RLHF with PPO, DPO and GRPO, with what each needs and how each fails.Open lesson](/ai/learn/rl-fine-tuning)
3. [#21LaterAdvanced 1.5 hComputer use and multimodal agentsA multimodal model reads images and audio as well as text, by turning each of them into tokens. A multimodal agent uses that ability to act: answer from documents with charts, hold a voice call, or operate a computer by looking at screenshots and clicking. This lesson explains how an image becomes tokens, how voice and computer-use agents are built, why they are slow and easy to break, and how to test and secure them.Open lesson](/ai/learn/computer-use-multimodal-agents)
4. [#22LaterAdvanced 1.5 hAdvanced topicsThis lesson is a map of what to study after the core roadmap. It covers ten topics that sit one level below the basics: reasoning models, mixture of experts, distillation, constrained decoding, speculative decoding, long-running agents, harness engineering, open-weight models, the small tuned model plus RAG pattern, and GraphRAG. For each one you get what it is, why a system builder cares, and what to learn first.Open lesson](/ai/learn/advanced-topics)
5. [#23LaterIntermediate 8 hProjects - RAG app, fine-tuned model, agent + evalsThree small projects turn the rest of this course into things you can talk about: a RAG app, a fine-tuned model, and an agent with an eval harness. This lesson gives each one a scope, milestones, numbers to measure with targets a student can reach, a README outline, and a way to present it in two minutes: problem, design, trade-offs, numbers.Open lesson](/ai/learn/projects)
6. [#24LaterIntermediate 1.5 hLLMs on cloud - Bedrock, Azure OpenAI, Vertex AIAmazon Bedrock, Azure OpenAI and Google Vertex AI each give you one managed API to many models inside your own cloud account. The product names differ, but the ideas are the same: pay per token or reserve capacity, live inside quotas, choose where data is processed, lock access down with cloud identity and private networking, and add managed retrieval, agents, guardrails, tuning and evals. This lesson teaches the shared ideas and when to self-host instead.Open lesson](/ai/learn/llms-on-cloud)

## Interview problems

Each one has requirements, estimates, API, data model, design, diagram, deep dives, evaluation, failure modes and follow-ups.

GENAI

### GenAI systems

· 22

RAG, agents, gateways, guardrails and evals: the questions asked for LLM application roles.

1. [1RAG pipeline for internal docs Q&Aretrieval · embeddings · vector db · chunking · rerankingSierraMedium](/ai/problems/rag-pipeline)
2. [2Hybrid retrieval and reranking servicehybrid search · bm25 · reciprocal rank fusion · cross-encoder · retrieval metricsMedium](/ai/problems/hybrid-search-reranking)
3. [3Agentic research assistant with multi-step retrievaldeep research · plan and execute · citations · token budget · long-running jobsHard](/ai/problems/agentic-research-assistant)
4. [4LLM gateway with routing, caching and fallbackgateway · rate limiting · fallback · streaming · budgets · redactionHard](/ai/problems/llm-gateway)
5. [5Semantic cache for LLM responsescaching · embeddings · cost · multi-tenant · invalidationMedium](/ai/problems/semantic-cache)
6. [6Chatbot with long-term memoryagent memory · conversation summary · personalisation · privacy · deletionMedium](/ai/problems/chatbot-with-memory)
7. [7Customer support agent with tools and approvalsagents · tool calling · human approval · idempotency · escalation · prompt injectionSierraHard](/ai/problems/customer-support-agent)
8. [8Agent runtime: loop, tools, checkpoints and budgetsagent harness · checkpoints · sandbox · human approval · context compaction · budgetsGleanHard](/ai/problems/agent-runtime-harness)
9. [9Multi-agent orchestrator for deep researchmulti-agent · orchestrator and workers · sub-agents · cost control · tracing · deep researchHard](/ai/problems/multi-agent-orchestrator)
10. [10MCP tool platform for internal APIsmcp · tool search · oauth · tool registry · prompt injection · rate limitingSierraMedium](/ai/problems/mcp-tool-platform)
11. [11AI code assistant: completion, chat and agentcode completion · repository indexing · context selection · coding agent · sandbox · acceptance rateHard](/ai/problems/code-assistant)
12. [12LoRA fine-tuning pipeline with an adapter registryfine-tuning · lora · qlora · gpu scheduling · evaluation gate · adapter registryOpenAIHard](/ai/problems/fine-tuning-pipeline)
13. [13Evaluation harness for LLM apps and agentsevals · llm-as-judge · golden set · regression gate · calibration · online metricsAnthropic, PerplexityMedium](/ai/problems/llm-eval-harness)
14. [14Prompt-injection defence for a tool-using agentprompt injection · agent security · least privilege · taint tracking · human approval · red teamingAnthropic, GoogleHard](/ai/problems/prompt-injection-defence)
15. [15Guardrails and PII redaction layerguardrails · pii · safety classifier · streaming · policy · audit logOpenAI, Anthropic, GoogleMedium](/ai/problems/guardrails-pii-redaction)
16. [16Structured data extraction from documentsstructured output · json schema · constrained decoding · validation · human reviewEasy](/ai/problems/structured-extraction)
17. [17Tracing and observability for LLM applicationstracing · observability · cost accounting · sampling · pii redaction · online evalsMedium](/ai/problems/llm-observability)
18. [18Insurance claims decision agent with RAG and a token budgetagents · rag · token budget · human review · audit trail · rules engineScale AIHard](/ai/problems/claims-decision-agent)
19. [19ChatGPT-like chat servicestreaming · conversation storage · context management · file uploads · multimodalxAIHard](/ai/problems/chat-service)
20. [20Document ingestion and indexing pipeline for LLM useingestion · parsing · ocr · idempotency · incremental indexing · access controlDatabricksMedium](/ai/problems/document-ingestion-pipeline)
21. [21Real-time voice AI agentvoice agent · speech-to-text · text-to-speech · streaming · turn detection · latency budgetHard](/ai/problems/realtime-voice-agent)
22. [22Cut LLM cost by half: model routing and cascadesmodel routing · cascade · cost · classifier · quality monitoringMedium](/ai/problems/llm-cost-router)

MLSD

### ML system design

· 8

Serving, batching, vector search, recommendations and moderation at scale.

1. [23Inference batching system for one GPUcontinuous batching · kv cache · scheduling · streaming · gpu inference · admission controlAnthropicHard](/ai/problems/llm-inference-batching)
2. [24Serve an open model to 1,000 concurrent usersmodel serving · autoscaling · routing · quantization · multi-tenant · rolloutAnthropic, Scale AIHard](/ai/problems/llm-serving-platform)
3. [25Multi-tenant LoRA adapter servinglora · multi-tenant · inference serving · adapter cache · batching · routingMedium](/ai/problems/multi-lora-serving)
4. [26Embedding service at scaleembeddings · dynamic batching · length bucketing · caching · model versioning · gpu inferenceMedium](/ai/problems/embedding-service)
5. [27Vector search at billion scaleann · hnsw · ivf-pq · quantization · sharding · filtered searchHard](/ai/problems/vector-search-at-scale)
6. [28Recommendation feedrecommender systems · two-tower · multi-task ranking · feature store · cold start · a/b testingMeta, TikTok, Netflix, PinterestHard](/ai/problems/recommendation-feed)
7. [29Content moderation with classifiers and LLM reviewclassification · model cascade · precision and recall · human review · active learning · adversarial driftMedium](/ai/problems/content-moderation)
8. [30Multimodal search over images and textmultimodal · contrastive embeddings · image search · vector search · hybrid search · rerankingMedium](/ai/problems/multimodal-search)

MLCODE

### Implement it

· 10

Attention, tokenizers, sampling, LoRA and agent loops written from scratch in Python.

1. [31Self-attention from scratchattention · transformer · numpy · causal mask · multi-headMedium](/ai/problems/attention-from-scratch)
2. [32BPE tokenizer: train, encode, decodetokenization · bpe · utf-8 · bytes · pythonMedium](/ai/problems/bpe-tokenizer)
3. [33Decoder with a KV cachekv cache · transformer · decoding · inference · numpy · causal maskHard](/ai/problems/kv-cache-decoding)
4. [34Temperature, top-k and top-p samplingsampling · decoding · temperature · top-p · numpyEasy](/ai/problems/top-k-top-p-sampling)
5. [35Brute-force cosine top-k searchcosine similarity · nearest neighbour · numpy · top-k · embeddingsEasy](/ai/problems/cosine-top-k-search)
6. [36LoRA layer: forward, train and mergelora · fine-tuning · peft · numpy · backpropagationMedium](/ai/problems/lora-layer)
7. [37Logistic regression with SGDlogistic regression · sgd · cross-entropy · gradient check · numpy · regularisationEasy](/ai/problems/logistic-regression-sgd)
8. [38Agent loop from scratch with tools and a step limitagents · agent loop · tool calling · harness · testingMedium](/ai/problems/agent-loop-from-scratch)
9. [39Minimal RAG loop: chunk, embed, retrieve, promptrag · chunking · embeddings · cosine similarity · citations · numpyEasy](/ai/problems/minimal-rag-loop)
10. [40Retry with exponential backoff and timeoutsasyncio · retries · exponential backoff · jitter · timeouts · reliabilitySierraEasy](/ai/problems/retry-with-backoff)
