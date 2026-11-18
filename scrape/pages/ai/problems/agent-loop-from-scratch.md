# Agent loop from scratch with tools and a step limit — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/agent-loop-from-scratch

[AI problems](/ai#problems)

MLCODEImplement it#38Medium

# Agent loop from scratch with tools and a step limit

agentsagent looptool callingharnesstesting

## Problem statement

Implement an agent loop in plain Python with no agent framework. An agent is a language model in a loop with tools: the model asks for a tool call, your code runs it and feeds the result back, and this repeats until the model gives a final answer. No real model is available in the interview, so the model is a function that you script. The interviewer wants to see what your code does between one model call and the next, and how the loop is forced to stop.

## Requirements

### Functional

* A message list with the roles `system`, `user`, `assistant` and `tool`. It holds the whole state of a run.
* A tool registry. Each tool has a name, a description, a JSON-style argument schema and a function. `specs()` returns the part the model may see.
* A model interface `model(messages, tool_specs) -> ModelReply`. A reply is final text, or a list of tool calls that each carry an id.
* The loop: call the model, run every requested tool call, append one result per call, and repeat until a reply has no tool calls.
* Arguments are validated against the schema before any function runs. An unknown tool, bad arguments and a tool that raises all go back to the model as `ERROR: ...` results.
* A step limit and a token budget, each with its own status in the result.

### Non-functional

* At most `max_steps` model calls per run (default 8), however the model behaves.
* No model call is made if the tokens spent so far plus the next prompt would exceed `token_budget` (default 4,000, estimated at 4 characters per token).
* 0 exceptions escape from tool problems: all 3 failure kinds (unknown tool, invalid arguments, tool raised) become strings.
* Every tool call id gets exactly 1 `tool` message, in the order the model asked.
* All self-checks run offline in under 1 second, with a scripted model and no randomness.

## API

```
@dataclass
class ToolCall:
    id: str
    name: str
    args: dict

@dataclass
class ModelReply:
    content: str = ""            # the final answer when tool_calls is empty
    tool_calls: list[ToolCall] = field(default_factory=list)

# The model interface: any callable with this shape, real or scripted.
Model = Callable[[list[dict], list[dict]], ModelReply]     # (messages, tool_specs) -> reply

def validate_args(args: dict, schema: dict) -> str | None: ...   # None = valid, else what is wrong

class ToolRegistry:
    def register(self, name: str, description: str, parameters: dict, fn: Callable) -> None: ...
    def specs(self) -> list[dict]: ...                # name, description, parameters; never fn
    def execute(self, name: str, args: dict) -> str: ...   # JSON result or "ERROR: ..."; never raises

@dataclass
class AgentResult:
    status: str                  # "done" | "step_limit" | "token_budget"
    answer: str | None
    steps: int                   # model calls made
    tokens: int                  # estimated tokens spent
    messages: list[dict]         # the trace

def run_agent(task: str, model: Model, registry: ToolRegistry, system: str = "...",
              max_steps: int = 8, token_budget: int = 4000) -> AgentResult: ...

class ScriptedModel:             # the fake used in tests
    def __init__(self, replies: list[ModelReply]): ...
    def __call__(self, messages: list[dict], specs: list[dict]) -> ModelReply: ...
```

## Data model

```
messages: list of dicts, appended to and never edited
  {"role": "system",    "content": str}
  {"role": "user",      "content": str}
  {"role": "assistant", "content": str, "tool_calls": [{"id", "name", "args"}]}
  {"role": "tool",      "tool_call_id": str, "name": str, "content": str}
                        content is the JSON result, or "ERROR: ..."

registry: dict name -> {"description": str, "parameters": schema, "fn": callable}
  schema = {"type": "object",
            "properties": {arg_name: {"type": "string" | "integer" | "number" | "boolean"}},
            "required": [arg_name, ...]}

tool spec sent to the model: {"name", "description", "parameters"}

counters kept by the loop
  step            0 .. max_steps - 1, one per model call
  prompt_tokens   tokens of the tool specs + the whole message list
  spent           running total of prompt and reply tokens
```

## Approach

1. Fix the data shapes first: the four message roles, `ToolCall(id, name, args)` and `ModelReply(content, tool_calls)`. A reply with no tool calls is the final answer. Everything else follows from this rule.
2. Write `validate_args(args, schema)`. It returns `None`, or one sentence: a required argument is missing, an argument is not in the schema, or a value has the wrong type.
3. Write the registry. `register` stores a tool, after checking that its schema uses only the supported types. `specs()` returns the name, description and schema without the function. `execute(name, args)` makes three checks in order: is the name registered, do the arguments pass the schema, does the function return without raising. Each failure returns a string that starts with `ERROR:` and says how to fix the call.
4. Write the loop. Start the list with the system message and the user's task. On each step, estimate the prompt tokens and stop with status `token_budget` if the call does not fit. Otherwise call the model and append its reply as an assistant message.
5. If the reply has no tool calls, return status `done` with its text. If it has some, execute each one and append a `tool` message that carries the same call id, then go round again.
6. If the `for` loop ends without a final answer, return status `step_limit`. A stopped run still returns the message list, so the caller can see how far it got.
7. Write `ScriptedModel`. It returns replies from a fixed list and records a copy of the message list on every call. Tests assert on the final list, on what the model was shown, and on which functions really ran.
8. Test every exit and every error path on its own: the happy path, two calls in one reply, an unknown tool, bad arguments, a tool that raises, the step limit and the budget.

## Architecture diagram

Rendering diagram…

## Deep dives

### The model decides, the harness acts

The model only returns data: a tool name and arguments. It runs nothing. The **harness**, which is the code around the model, validates the call and executes it. This split is why the registry is also the allow-list: a name that is not registered cannot run, whatever the model writes. It is also why the model can be a plain function `(messages, tool_specs) -> ModelReply`. Swap the scripted fake for a real API client and the loop does not change.

### Three failures, one channel

An unknown tool, arguments that fail the schema and a function that raises are three different bugs. The loop treats them the same way: the result, called the **observation**, is a string that starts with `ERROR:`. The model reads it on the next call and can repair its request, so the text must say what was wrong and what a valid call looks like. A stack trace does not help it. Exceptions are kept for problems the model cannot fix, such as a bug in the harness or the model API being down.

### Validate before anything runs

The order is name, then arguments, then run. The validator covers the part of JSON Schema that most tools need: required keys, no unknown keys, and four scalar types. Two details catch people. Unknown keys must be rejected, or `fn(**args)` raises a `TypeError` that looks like a bug in the tool. And `isinstance(True, int)` is true in Python, so a boolean passes as a number unless you test for `bool` first.

### Two limits, checked in different places

The step limit is the `for` loop itself. One step is one model call, so a model that never finishes is cut off after `max_steps` calls. The token budget is checked before each call, not after, so the call that would overspend is never made. The budget matters because the whole list is sent again on every call. If each step adds 500 tokens to a 1,000-token start, 8 steps send 8 x 1,000 + 500 x 28 = 22,000 input tokens, not 8,000. A real harness reads token counts from the API response and also reserves the maximum reply size.

### Why a scripted model is the right test

A real model is slow, costs money and gives different output on each run. When a test fails, you cannot tell whether the loop or the model was wrong. The scripted model removes that doubt. It replays fixed replies, records the message list it was shown, and fails loudly if the loop calls it more often than the script allows.

## Evaluation

**Correctness tests.**

* Happy path: status `done`, the exact answer, 3 model calls, and roles in the order system, user, assistant, tool, assistant, tool, assistant. The first reply carries text and a tool call together, which proves that "has text" is not read as "finished".
* The model sees its observations: the list it is shown has 2, then 4, then 6 messages, and from the second call on the last message is a tool result.
* Two calls in one reply give two tool messages with matching ids, in order.
* An unknown tool, four kinds of bad arguments and a tool that raises each produce the expected `ERROR:` text. The run still ends with `done`, and a log of real executions shows that no function ran for an invalid call.
* Schema edge cases: a tool with no arguments runs and rejects an extra argument, and a schema with an unsupported type fails at registration, not in the middle of a run.
* Step limit: with `max_steps=5`, a model that always asks for a tool is called exactly 5 times.
* Token budget: half the cost of a full run stops early with `token_budget`. Exactly the full cost finishes.

**Complexity.** Validation is O(number of arguments) and a registry lookup is O(1). With S steps and about r tokens added per step, the tokens sent grow as O(S^2 x r), because every call re-sends the list. Model calls never exceed `max_steps`.

**What a strong answer adds.** Listing the exits aloud before writing the loop. Detecting the same call with the same arguments three times in a row. A timeout on each tool. Cutting long tool results before they enter the list. An approval flag on risky tools. Saving the message list as a trace for debugging.

## Bottlenecks & mitigations

* Input tokens grow with the square of the step count, because the whole message list is sent on every call.
* The tool calls of one reply run one after another. Independent read-only calls could run concurrently.
* `count_tokens` serialises the whole list on every step. A running total per message avoids the repeated work.
* A slow tool blocks the loop, because there is no timeout on a tool call.
* A large tool result stays in the list for the rest of the run and is paid for again on every later call.

## Failure modes

* **The model names a tool that does not exist.** It guessed a name, or remembered one from another prompt. Mitigation: the registry is the allow-list; return `ERROR: unknown tool` with the list of real tool names.
* **Arguments have the wrong shape.** A missing key, an extra key, or a string where a number is needed. Mitigation: validate against the schema before the function runs, and put the expected arguments in the error.
* **A tool raises.** Bad input, a network error or a bug. Mitigation: `try` and `except` around the function, with the exception type and message returned as the observation.
* **The model never finishes.** It repeats a failing call or keeps exploring. Mitigation: the step limit, plus repeated-call detection in a fuller harness.
* **Text is mistaken for a final answer.** One reply can hold a thought and a tool call together. Mitigation: the stop condition is "no tool calls", never "has content".
* **A tool call gets no result, or the wrong one.** With several calls in one reply, results are mixed up or one is dropped, and provider APIs typically reject the next request. Mitigation: append exactly one tool message per call, in order, each with its `tool_call_id`.
* **The budget is checked after the call.** The tokens are already spent. Mitigation: estimate the prompt and check before calling the model.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""Agent loop with no framework: message list, tool registry, model interface, limits.

The model is any function (messages, tool_specs) -> ModelReply. Here it is a
scripted fake that returns a fixed list of replies. That is also how you unit
test a real agent: no network, no randomness, and every assertion is about
what the harness did with the model's requests.
"""
import json
from dataclasses import dataclass, field

# ---- What the model returns ---------------------------------------------------
@dataclass
class ToolCall:
    id: str                 # lets the harness match each result to its request
    name: str
    args: dict

@dataclass
class ModelReply:
    content: str = ""       # the final answer when tool_calls is empty
    tool_calls: list = field(default_factory=list)

# ---- Tools: schema check and registry -----------------------------------------
JSON_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool}

def validate_args(args, schema):
    """Return None if args match the schema, else one sentence the model can act on."""
    if not isinstance(args, dict):
        return "arguments must be a JSON object"
    props = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in args:
            return f"missing required argument '{key}'"
    for key, value in args.items():
        if key not in props:
            return f"unexpected argument '{key}'"
        want = props[key]["type"]
        is_bool = isinstance(value, bool)       # bool is a subclass of int in Python
        if (is_bool and want != "boolean") or not isinstance(value, JSON_TYPES[want]):
            return f"argument '{key}' must be of type {want}"
    return None

class ToolRegistry:
    """Name -> tool. It is the tool list shown to the model and also the allow-list."""

    def __init__(self):
        self.tools = {}

    def register(self, name, description, parameters, fn):
        for arg, spec in parameters.get("properties", {}).items():   # reject a bad schema now, not mid-run
            assert spec.get("type") in JSON_TYPES, f"{name}.{arg}: unsupported type {spec.get('type')!r}"
        self.tools[name] = {"description": description, "parameters": parameters, "fn": fn}

    def specs(self):
        """What the model sees: name, description and schema. Never the function."""
        return [{"name": n, "description": t["description"], "parameters": t["parameters"]}
                for n, t in self.tools.items()]

    def execute(self, name, args):
        """Run one tool call. Never raises: every failure becomes an ERROR string."""
        tool = self.tools.get(name)
        if tool is None:
            return f"ERROR: unknown tool '{name}'. Available tools: {sorted(self.tools)}"
        problem = validate_args(args, tool["parameters"])
        if problem:
            return f"ERROR: {problem}. {name} expects {json.dumps(tool['parameters'].get('properties', {}))}"
        try:
            return json.dumps(tool["fn"](**args))
        except Exception as exc:                # a tool crash must not crash the loop
            return f"ERROR: {name} failed: {type(exc).__name__}: {exc}"

# ---- The loop -----------------------------------------------------------------
def count_tokens(obj):
    """Rough estimate, about 4 characters per token. A real harness reads the API's usage numbers."""
    return max(1, len(json.dumps(obj)) // 4)

@dataclass
class AgentResult:
    status: str             # "done", "step_limit" or "token_budget"
    answer: str | None
    steps: int              # model calls made
    tokens: int             # estimated tokens spent, input plus output
    messages: list          # the whole message list, which is also the trace

def run_agent(task, model, registry, system="Use the tools to answer the user.",
              max_steps=8, token_budget=4000):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": task}]
    specs = registry.specs()
    spent = 0
    for step in range(max_steps):                               # exit 1: step limit
        prompt_tokens = count_tokens(specs) + count_tokens(messages)   # the whole list is sent again
        if spent + prompt_tokens > token_budget:                # exit 2: budget, checked BEFORE the call
            return AgentResult("token_budget", None, step, spent, messages)
        reply = model(messages, specs)                          # the model decides
        calls = [{"id": c.id, "name": c.name, "args": c.args} for c in reply.tool_calls]
        assistant = {"role": "assistant", "content": reply.content, "tool_calls": calls}
        messages.append(assistant)
        spent += prompt_tokens + count_tokens(assistant)
        if not calls:                                           # exit 3: final answer
            return AgentResult("done", reply.content, step + 1, spent, messages)
        for call in calls:                                      # the harness acts
            observation = registry.execute(call["name"], call["args"])
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "name": call["name"], "content": observation})
    return AgentResult("step_limit", None, max_steps, spent, messages)

# ---- A scripted fake model ----------------------------------------------------
class ScriptedModel:
    """Returns a fixed list of replies and records the message list it was shown each time."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def __call__(self, messages, specs):
        assert len(self.seen) < len(self.replies), "script ran out: the loop called the model too often"
        self.seen.append(json.loads(json.dumps(messages)))     # a copy; also proves the list is JSON
        return self.replies[len(self.seen) - 1]

def call(call_id, name, **args):
    return ToolCall(call_id, name, args)

def asks(*tool_calls):
    return ModelReply(tool_calls=list(tool_calls))

def final(text):
    return ModelReply(content=text)

# ---- Demo tools ---------------------------------------------------------------
TEMPERATURES_C = {"Pune": 30, "Delhi": 35}
RUNS = []                   # every real tool execution is logged here

def get_weather(city):
    RUNS.append(("get_weather", city))
    return {"city": city, "celsius": TEMPERATURES_C[city]}     # KeyError for an unknown city

def c_to_f(celsius):
    RUNS.append(("c_to_f", celsius))
    return celsius * 9 / 5 + 32

def make_registry():
    registry = ToolRegistry()
    registry.register("get_weather", "Current temperature of one city in Celsius. Use it before any weather answer.",
                      {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
                      get_weather)
    registry.register("c_to_f", "Convert Celsius to Fahrenheit. Use it for every conversion.",
                      {"type": "object", "properties": {"celsius": {"type": "number"}}, "required": ["celsius"]},
                      c_to_f)
    return registry

if __name__ == "__main__":
    registry = make_registry()
    task = "How hot is Pune in Fahrenheit?"
    happy_script = [ModelReply("I will look up Pune first.", [call("c1", "get_weather", city="Pune")]),
                    asks(call("c2", "c_to_f", celsius=30)),
                    final("It is 86.0 F in Pune.")]

    # 1. Happy path: two tool steps, then a final answer. Reply 1 has text AND a tool call,
    #    so "has text" must not be mistaken for "finished".
    model = ScriptedModel(happy_script)
    r = run_agent(task, model, registry)
    assert (r.status, r.answer, r.steps) == ("done", "It is 86.0 F in Pune.", 3)
    assert [m["role"] for m in r.messages] == ["system", "user", "assistant", "tool", "assistant", "tool", "assistant"]
    assert r.messages[3]["tool_call_id"] == "c1" and json.loads(r.messages[3]["content"]) == {"city": "Pune", "celsius": 30}
    assert r.messages[5]["tool_call_id"] == "c2" and r.messages[5]["content"] == "86.0"
    assert [len(s) for s in model.seen] == [2, 4, 6]           # each call saw the whole list so far
    assert model.seen[1][-1]["content"] == r.messages[3]["content"]
    assert RUNS == [("get_weather", "Pune"), ("c_to_f", 30)]
    assert all("fn" not in spec for spec in registry.specs())
    print(f"happy path ok: done in {r.steps} model calls, {r.tokens} tokens, answer = {r.answer!r}")
    full_tokens = r.tokens

    # 2. Two tool calls in one reply: one result per call id, in the order requested.
    model = ScriptedModel([asks(call("a", "get_weather", city="Pune"), call("b", "get_weather", city="Delhi")),
                           final("Delhi is hotter.")])
    r = run_agent("Which is hotter, Pune or Delhi?", model, registry)
    tool_msgs = [m for m in r.messages if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["a", "b"] and '"celsius": 35' in tool_msgs[1]["content"]
    assert r.status == "done" and r.steps == 2
    print("parallel calls ok: 2 calls in one reply gave 2 results matched by id")

    # 3. Unknown tool: nothing runs, the error names the real tools, the loop continues.
    RUNS.clear()
    model = ScriptedModel([asks(call("c1", "get_forecast", city="Pune")), final("I could not look that up.")])
    r = run_agent(task, model, registry)
    assert r.messages[3]["content"] == "ERROR: unknown tool 'get_forecast'. Available tools: ['c_to_f', 'get_weather']"
    assert r.status == "done" and RUNS == []
    print("unknown tool ok:", r.messages[3]["content"])

    # 4. Bad arguments: four different mistakes, none of them reaches a function.
    model = ScriptedModel([asks(call("m1", "get_weather"),                       # required argument missing
                                call("m2", "c_to_f", celsius="30"),              # string where a number is needed
                                call("m3", "get_weather", city="Pune", unit="F"),  # argument not in the schema
                                call("m4", "c_to_f", celsius=True)),             # bool is not a number
                           final("Giving up.")])
    r = run_agent(task, model, registry)
    errors = [m["content"] for m in r.messages if m["role"] == "tool"]
    assert errors[0].startswith("ERROR: missing required argument 'city'")
    assert errors[1].startswith("ERROR: argument 'celsius' must be of type number")
    assert errors[2].startswith("ERROR: unexpected argument 'unit'")
    assert errors[3].startswith("ERROR: argument 'celsius' must be of type number")
    assert errors[0].endswith('get_weather expects {"city": {"type": "string"}}')
    assert RUNS == [] and r.status == "done"
    print("bad arguments ok: 4 invalid calls, 0 functions run. First error:", errors[0])
    bare = ToolRegistry()                   # a tool with no arguments and no "properties" key in its schema
    bare.register("ping", "Health check. Takes no arguments.", {"type": "object"}, lambda: "pong")
    assert bare.execute("ping", {}) == '"pong"'
    assert bare.execute("ping", {"x": 1}) == "ERROR: unexpected argument 'x'. ping expects {}"
    try:
        bare.register("bad", "Schema with a type the validator does not know.",
                      {"type": "object", "properties": {"items": {"type": "array"}}}, lambda items: items)
        raise AssertionError("an unsupported schema type must be rejected at registration")
    except AssertionError as exc:
        assert "unsupported type 'array'" in str(exc)
    print("schema edge cases ok: a no-argument tool runs, and an unsupported type is rejected at registration")

    # 5. A tool that raises: the exception becomes an observation and the model recovers.
    model = ScriptedModel([asks(call("c1", "get_weather", city="Atlantis")),
                           asks(call("c2", "get_weather", city="Pune")),
                           final("Pune is at 30 C.")])
    r = run_agent("How hot is Atlantis? If unknown, use Pune.", model, registry)
    assert r.messages[3]["content"] == "ERROR: get_weather failed: KeyError: 'Atlantis'"
    assert r.status == "done" and r.answer == "Pune is at 30 C." and r.steps == 3
    print("tool error ok:", r.messages[3]["content"])

    # 6. Step limit: a model that never finishes is stopped after exactly max_steps calls.
    model_calls = []

    def never_finishes(messages, specs):
        model_calls.append(len(messages))
        return asks(call(f"c{len(model_calls)}", "get_weather", city="Pune"))

    r = run_agent(task, never_finishes, registry, max_steps=5, token_budget=10**9)
    assert (r.status, r.answer, r.steps) == ("step_limit", None, 5) and len(model_calls) == 5
    assert model_calls == [2, 4, 6, 8, 10]                     # the list grows by 2 messages per step
    print(f"step limit ok: stopped after {len(model_calls)} model calls with status {r.status!r}")

    # 7. Token budget: the same happy script, but the budget runs out before the last call.
    model = ScriptedModel(happy_script)
    r = run_agent(task, model, registry, token_budget=full_tokens // 2)
    assert r.status == "token_budget" and r.answer is None
    assert r.steps == len(model.seen) < 3 and r.tokens <= full_tokens // 2
    r_exact = run_agent(task, ScriptedModel(happy_script), registry, token_budget=full_tokens)
    assert r_exact.status == "done"                             # a budget of exactly the cost is enough
    print(f"token budget ok: a full run costs {full_tokens} tokens; with a budget of {full_tokens // 2} "
          f"it stopped after {r.steps} of 3 model calls, at {r.tokens} tokens")
    print("all checks passed")
```

## Follow-up questions interviewers ask

* Add detection of the same tool call with the same arguments three times. What should the harness do then?
* One tool needs human approval. How do you pause the run and resume it hours later?
* Run the tool calls of one reply concurrently. Which tools are safe to run in parallel, and how do you keep the results in order?
* The message list no longer fits in the context window. What do you trim or summarise, and what must stay?
* Extend the validator to enums, arrays and nested objects.
* How would you test this loop against a real model, whose replies change between runs?

## Lessons that cover this

* [#12Agents from first principles - build a mini frameworkAgents](/ai/learn/agents-first-principles)
* [#13Agent frameworks - LangChain, LangGraphAgents](/ai/learn/agent-frameworks-langchain-langgraph)
* [#23Projects - RAG app, fine-tuned model, agent + evalsLater](/ai/learn/projects)

## Further reading

* [Building effective agentsArticleanthropic.com](https://www.anthropic.com/engineering/building-effective-agents)
* [ReAct: Synergizing Reasoning and Acting in Language ModelsPaperarxiv.org](https://arxiv.org/abs/2210.03629)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousLogistic regression with SGD](/ai/problems/logistic-regression-sgd)[NextMinimal RAG loop: chunk, embed, retrieve, prompt](/ai/problems/minimal-rag-loop)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Approach](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Evaluation](#evaluation)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Reference solution](#code)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
