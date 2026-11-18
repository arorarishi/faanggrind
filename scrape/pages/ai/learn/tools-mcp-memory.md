# Tools, MCP and memory — AI roadmap · FAANGrind

Source: https://faangrind.vercel.app/ai/learn/tools-mcp-memory

[AI roadmap](/ai)

AgentsLesson #14StudyIntermediate 3.5 h

# Tools, MCP and memory

A tool is a function your application offers to a model: a name, a description and a schema for the arguments. MCP (Model Context Protocol) is an open standard for packaging tools and data so any compatible AI application can use them. Memory is how an agent keeps facts beyond one context window. This lesson covers how to design all three, and what each one costs in tokens.

tool callingmcpa2aagent memoryjson schemacontext tokens

## Why it matters

An agent is only as good as its tools and what it remembers. Interviewers ask "how does tool calling work", "explain MCP's architecture", "an agent has 200 tools, what breaks" and "design memory for an assistant" because each has a concrete engineering answer. In real work, most agent bugs are not model bugs. They are a vague tool description, a tool that returns 5,000 tokens of raw JSON, an error message the model cannot act on, or a memory store that returns an old address. This lesson gives you the vocabulary and the numbers to answer all four questions aloud.

Read first: [Prompting and context engineering](/ai/learn/prompting-context-engineering), [Agents from first principles - build a mini framework](/ai/learn/agents-first-principles)

## Lesson

### What a tool is, and the flow of one call

A tool is a function your application offers to the model. Each tool has a name, a description and a JSON schema for its arguments. The model cannot run anything. It only writes text, so a "tool call" is the model writing a tool name and JSON arguments in a structured format. Your code does the rest.

One tool call takes four steps:

1. **Request.** The application sends the conversation plus the tool definitions.
2. **Tool call.** The model replies with a call, not an answer: `get_order` with `{"order_id": "A1042"}`.
3. **Execution.** The application validates the arguments, runs the function and appends the output to the conversation as a tool-result message.
4. **Answer.** The application calls the model again. The model now sees the result and either answers or asks for another tool.

After those four steps the conversation holds four messages (simplified; field names differ between providers):

```
[
  {"role": "user", "content": "Where is order A1042?"},
  {"role": "assistant", "tool_call": {"id": "call_1", "name": "get_order", "arguments": {"order_id": "A1042"}}},
  {"role": "tool", "tool_call_id": "call_1", "content": "shipped, arrives Friday, total 1200 INR"},
  {"role": "assistant", "content": "Your order has shipped and arrives on Friday."}
]
```

The call id ties each result to its call, which matters when the model asks for several tools in one turn. One tool use costs two model calls, and the result stays in the context for the rest of the conversation.

### What a good tool definition looks like

The model never sees your code. It sees only the definition, so the definition is a prompt. A good tool does one clear job and gets five parts right.

| Part | Weak | Strong |
| --- | --- | --- |
| Name | `api_v2_post` | `create_return` |
| Description | "Handles orders." | "Look up one order by its id. Use it when the user asks about status or delivery date. Do not use it to search by customer name." |
| Arguments | `data: string` | `order_id: string, the letter A then 4 digits`; `reason: one of damaged, wrong_item, late` |
| Result | The whole database row as raw JSON | The few fields the model needs: status, delivery date, amount |
| Error | `500 Internal Server Error` | "order\_id must look like A1042. You sent 1042. Add the letter prefix and call again." |

```
{
  "name": "get_order",
  "description": "Look up one order by its id. Use it when the user asks about status or delivery date. Do not use it to search by customer name.",
  "input_schema": {
    "type": "object",
    "properties": {
      "order_id": {"type": "string", "pattern": "^A[0-9]{4}$", "description": "Order id, for example A1042"}
    },
    "required": ["order_id"]
  }
}
```

The description says when to use the tool and when not to. Typed arguments (patterns, enums, ranges) let your code reject a bad call before it runs. Short results save context. An error that says how to fix the call lets the model correct itself in the next step, where a bare status code makes it guess or loop. The exact field name for the schema differs between providers, but the three parts are always there.

Design tools around what the user wants, not around your API. If answering "where is my order" needs three endpoints (order, shipment, courier), one `get_order_status` tool that calls all three is better than three tools the model must chain correctly. Keep read tools and write tools separate, so that approval rules can apply to the writes only.

### Every tool definition costs context tokens

Tool definitions travel with every request. Assume one definition is about 150 tokens. Ten tools cost 1,500 tokens per model call, which is fine. Two hundred tools cost 30,000 tokens per call before the user has said a word. Two things break: the context and the bill fill up, and the model picks the wrong tool when many look alike.

The fixes:

* **Many tools:** load tool definitions on demand through a tool search step, not all at the start. Keep a small core set always loaded, plus one `search_tools` tool that returns the few definitions that match the current task.
* Group and namespace tools (`orders.get`, `orders.refund`) so related ones are easy to tell apart.
* Merge overlapping tools, and move specialised sets into sub-agents.

### MCP: build a tool once, use it everywhere

MCP (Model Context Protocol) is an open standard for connecting models to tools and data. A server exposes tools, resources and prompts; any compatible client can use them. Build a tool once, reuse it across models and frameworks.

Function calling and MCP solve different problems. Function calling is how one model asks for one tool inside one app. MCP is a standard way to package and expose tools so any client can discover and use them. MCP sits on top of function calling; it does not replace it. Without a standard, 5 applications and 20 internal systems need up to 100 custom integrations. With MCP you write 20 servers and 5 clients.

### MCP roles: host, client, server

![MCP architecture: a host runs one client per server and the model never talks to a server directly](/ai/img/mcp-host-clients-servers.svg)MCP architecture: a host runs one client per server and the model never talks to a server directly

* **Roles:** the host is the AI application. It runs one client per server. The server exposes capabilities. The model never talks to the server directly.

The last sentence is the one to remember. The model writes a tool call. The host validates it, asks the user to approve if needed, and passes it to the client for that server. The host stays in control of what is called. A server also cannot read the whole conversation or see other servers; it receives only what the host sends.

### Three primitives, and who controls each

| Primitive | What it is | Who controls it | Example |
| --- | --- | --- | --- |
| Tools | Functions with a schema | The model decides when to call | `create_return`, `search_docs` |
| Resources | Read-only context, addressed by URI | The application loads them | A file, a database schema, a policy page |
| Prompts | Reusable templates | The user picks one | A "summarise this ticket" command |

Control matters for safety. A resource cannot act. A prompt runs only when a person chooses it. Tools are the risky primitive, because the model chooses them.

### Messages, transports and the rest of the protocol

* **Messages:** JSON-RPC 2.0, with methods such as `tools/list` and `tools/call`.
* **Transports:** stdio for local servers started as a subprocess; Streamable HTTP for remote servers. The older HTTP plus SSE transport is deprecated.
* **Authorization:** an OAuth-based framework for remote servers; local stdio servers read credentials from the environment.
* **Latest revision (2026-07-28):** the protocol became stateless. The initialize handshake and sessions were removed, each request carries its version, and state is passed through explicit handles. Tutorials written before this may be out of date.
* **Governance:** maintained under the Linux Foundation's Agentic AI Foundation, not by one vendor.
* **Practical limit:** every tool definition costs context tokens on every request, so a small set of well-described tools beats one tool per API endpoint.

A JSON-RPC request is a JSON object with a method name, parameters and an id. The reply carries the same id and either a result or an error. A tool call looks like this (the `_meta` field that carries the protocol version is left out):

```
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_order", "arguments": {"order_id": "A1042"}}}
```

Choosing a transport is simple. With stdio the host starts the server as a child process on the same machine and they exchange messages over standard input and output. Nothing listens on a network port. Use it for local files and developer tools. With Streamable HTTP the server is a service at a URL and each client message is an HTTP POST. Use it for shared company tools with many users.

"Explicit handles" means that a server needing state between calls, such as a shopping basket, returns an id from one tool and takes that id as an argument in the next. With no handshake, a client that wants to know a server's supported versions and capabilities up front calls `server/discover`. A failed tool run comes back as a normal result marked as an error, with readable text, so the model can fix the call.

These protocol details follow the MCP guide listed in the resources, checked against the 2026-07-28 specification.

One safety rule: a tool description is text that goes into your model's context. If the server is not yours, treat its descriptions and its results as untrusted input, not as instructions.

### MCP and A2A

A2A (Agent2Agent) is a protocol for agents to discover and talk to other agents. MCP connects an agent to tools; A2A connects agents to each other. A tool is a function with a schema: you call it and get a result. An agent is a peer that takes a goal, may work for minutes, and may ask questions back. A travel agent that calls `search_flights` uses MCP. A travel agent that hands "book a hotel near the venue" to a separate hotel agent built by another team uses A2A.

### Short-term and long-term memory

A model keeps nothing between calls. Whatever it "remembers" is text your application put into the prompt again.

* **Short-term memory** is the context window and run state. It lasts one conversation or one run. Keep the working state in the context, and summarise or drop old turns as it fills.
* **Long-term memory** is an external store (vector database, files, a key-value store) that the agent reads and writes. It survives across sessions. Write durable facts to it and retrieve them when relevant.

Decide what is worth remembering, because storing everything pollutes later retrieval.

There are two ways to run the reads and writes. In the first, the application does it: after each conversation a background step extracts facts and saves them, and before each model call the application searches the store and adds the hits to the prompt. This is predictable and easy to test. In the second, memory is a pair of tools (`save_memory`, `search_memory`) and the model decides when to use them. This is more flexible, but the model sometimes forgets to save or to search. Many systems mix them: an always-loaded profile from the application, plus a search tool for the model.

### Four types of memory

| Type | Holds | Example |
| --- | --- | --- |
| Working | The current task state, inside the context | The plan and recent tool results |
| Episodic | Past interactions and runs | The user rejected option B last week |
| Semantic | Facts about the user or domain | The user's team; the product catalogue |
| Procedural | How to do a task | Saved instructions, skills and playbooks |

The design questions are the same for each: what to write, when to retrieve, how to resolve conflicting facts, and how to delete on request.

### The four memory design questions

1. **What to write.** Only durable, useful facts: preferences, decisions, stable profile data. Not small talk, not guesses, not secrets such as card numbers. Run an explicit write step that extracts candidate facts and stores each with a user id, a timestamp and its source.
2. **When to retrieve.** Load a small profile (a few hundred tokens) at the start of every session. Search the rest only when the request needs it, and return the top 3 to 5 items, not everything.
3. **How to resolve conflicts.** "I live in Pune" in January and "I moved to Bengaluru" in March cannot both be current. Prefer the newest and keep its source. Mark the old fact as superseded; never blend the two. A fact the user stated beats one the system inferred.
4. **How to delete.** The user must be able to see, correct and delete what is stored. A delete must reach every copy: the record, its embedding in the vector index, and any summary built from it.

## Diagram

Rendering diagram…

## Worked example

**What 200 tools cost.** A company wraps every internal API endpoint as a tool and ends up with 200. Assume each definition is 150 tokens, an average task takes 12 model calls, and the agent runs 10,000 tasks a day.

* Definitions per model call: 200 x 150 = 30,000 tokens.
* Definitions per task: 30,000 x 12 = 360,000 tokens.
* Per day: 360,000 x 10,000 = 3.6 billion input tokens. At an assumed 1 USD per million input tokens that is 3,600 USD a day spent only on describing tools.

Now load tools on demand. Keep 5 core tools plus one `search_tools` tool always loaded: 6 x 150 = 900 tokens. Each step also carries the 5 definitions that the search returned: 5 x 150 = 750 tokens.

* Definitions per model call: 900 + 750 = 1,650 tokens.
* Definitions per task: 1,650 x 12 = 19,800 tokens.
* Per day: 19,800 x 10,000 = 198 million tokens, or 198 USD at the same assumed price.

That is 94.5% less. If the search costs one extra model call, a task takes 13 calls: 13 x 1,650 = 21,450 tokens, still 94% less. Prompt caching can make a stable block of definitions cheaper, but it does not give the context space back, and the model still has to choose among 200 similar names. Fewer visible tools fixes cost and tool choice together.

**One memory conflict.** The store holds `city = Pune` (written 5 January, source: user message). On 20 March the user says "I moved to Bengaluru". The write step stores `city = Bengaluru` with the new timestamp and marks the old record superseded. A later request, "find a dentist near me", retrieves only the newest `city`. If a batch job later replays the January message, its older timestamp loses, so the stale value cannot come back.

## Runnable code

Python · standard library and NumPy only · prints its own checks

```
"""A tool registry that validates arguments, and a small long-term memory store.

Standard library only. The registry sits between the model's tool call and your
real function: it rejects bad calls with errors the model can act on. The memory
store shows the four decisions: what to write, when to retrieve, how to resolve
conflicts (newest wins) and how to delete.
"""
import re

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, description, schema, fn):
        self.tools[name] = {"description": description, "schema": schema, "fn": fn}

    def definitions(self):
        """What is sent to the model on every request."""
        return [{"name": n, "description": t["description"], "arguments": t["schema"]}
                for n, t in self.tools.items()]

    def validate(self, name, args):
        if name not in self.tools:
            return [f"Unknown tool '{name}'. Available tools: {', '.join(sorted(self.tools))}."]
        schema, errors = self.tools[name]["schema"], []
        for key in args:
            if key not in schema:
                errors.append(f"Unknown argument '{key}'. Allowed arguments: {', '.join(schema)}.")
        for key, rule in schema.items():
            if key not in args:
                if rule.get("required"):
                    errors.append(f"Missing required argument '{key}' ({rule['hint']}).")
                continue
            value = args[key]
            types = {"string": str, "number": (int, float)}[rule["type"]]
            if isinstance(value, bool) or not isinstance(value, types):
                errors.append(f"'{key}' must be a {rule['type']}. You sent {value!r}.")
            elif "pattern" in rule and not re.fullmatch(rule["pattern"], value):
                errors.append(f"'{key}' must be {rule['hint']}. You sent {value!r}.")
            elif "enum" in rule and value not in rule["enum"]:
                errors.append(f"'{key}' must be one of {rule['enum']}. You sent {value!r}.")
            elif "max" in rule and not (rule.get("min", 0) <= value <= rule["max"]):
                errors.append(f"'{key}' must be between {rule.get('min', 0)} and {rule['max']}. You sent {value}.")
        return errors

    def call(self, name, args):
        """Always returns text for the model. Never raises into the agent loop."""
        errors = self.validate(name, args)
        if errors:
            return {"is_error": True, "content": " ".join(errors) + " Fix the call and try again."}
        return {"is_error": False, "content": self.tools[name]["fn"](**args)}

class MemoryStore:
    def __init__(self):
        self.records = {}   # (user, key) -> list of versions, newest first

    def write(self, user, key, value, timestamp, source):
        versions = self.records.setdefault((user, key), [])
        versions.append({"value": value, "timestamp": timestamp, "source": source})
        versions.sort(key=lambda v: v["timestamp"], reverse=True)   # ISO dates sort as text
        return versions[0]

    def retrieve(self, user, query, k=2):
        words = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored = []
        for (owner, key), versions in self.records.items():
            if owner != user:
                continue                       # never mix users
            newest = versions[0]               # conflict rule: the newest fact wins
            text = set(re.findall(r"[a-z0-9]+", f"{key} {newest['value']}".lower()))
            overlap = len(words & text)
            if overlap:
                scored.append((overlap, key, newest))
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [(key, rec["value"], rec["timestamp"], rec["source"]) for _, key, rec in scored[:k]]

    def delete(self, user, key):
        return self.records.pop((user, key), None) is not None

def get_order(order_id):
    return f"Order {order_id}: shipped, arrives Friday, total 1200 INR."

def issue_refund(order_id, amount, reason):
    return f"Refund of {amount} INR queued for {order_id} ({reason})."

if __name__ == "__main__":
    reg = ToolRegistry()
    order_rule = {"type": "string", "required": True, "pattern": r"A\d{4}", "hint": "the letter A then 4 digits, like A1042"}
    reg.register("get_order", "Look up one order by id. Use for status or delivery questions.",
                 {"order_id": order_rule}, get_order)
    reg.register("issue_refund", "Refund an order. Use only after the policy check passed.",
                 {"order_id": order_rule,
                  "amount": {"type": "number", "required": True, "min": 1, "max": 5000, "hint": "INR, 1 to 5000"},
                  "reason": {"type": "string", "required": True, "enum": ["damaged", "wrong_item", "late"], "hint": "why"}},
                 issue_refund)
    print("tools sent to the model:", [d["name"] for d in reg.definitions()])

    calls = [
        ("get_ordr", {"order_id": "A1042"}),
        ("get_order", {"id": "A1042"}),
        ("get_order", {"order_id": "1042"}),
        ("issue_refund", {"order_id": "A1042", "amount": 9000, "reason": "angry"}),
        ("issue_refund", {"order_id": "A1042", "amount": 1200, "reason": "damaged"}),
        ("get_order", {"order_id": "A1042"}),
    ]
    for name, args in calls:
        result = reg.call(name, args)
        print(f"\ncall  : {name}({args})")
        print("error :" if result["is_error"] else "result:", result["content"])
    assert reg.call("get_order", {"order_id": "1042"})["is_error"]
    assert not reg.call("get_order", {"order_id": "A1042"})["is_error"]

    print("\n--- memory ---")
    mem = MemoryStore()
    mem.write("u1", "city", "Pune", "2026-01-05", "user message")
    mem.write("u1", "diet", "vegetarian food only", "2026-01-09", "user message")
    mem.write("u2", "city", "Chennai", "2026-02-01", "user message")
    print("retrieve 1:", mem.retrieve("u1", "which city should the dentist be in"))
    current = mem.write("u1", "city", "Bengaluru", "2026-03-20", "user message")
    print("after the move, current city:", current["value"])
    stale = mem.write("u1", "city", "Pune", "2026-01-05", "replayed import")
    print("after replaying the old fact, current city:", stale["value"])
    print("retrieve 2:", mem.retrieve("u1", "which city should the dentist be in"))
    print("retrieve 3:", mem.retrieve("u1", "book a table, vegetarian food, in my city"))
    assert mem.retrieve("u1", "city")[0][1] == "Bengaluru"
    print("delete city:", mem.delete("u1", "city"))
    print("retrieve 4:", mem.retrieve("u1", "which city should the dentist be in"))
    assert mem.retrieve("u1", "city") == []
    assert mem.retrieve("u2", "city")[0][1] == "Chennai"
    print("other users untouched:", mem.retrieve("u2", "city"))
```

## Key takeaways

* The model never runs a tool. It writes a name and JSON arguments; your code validates, executes and sends the result back.
* A tool definition is a prompt: a clear name, a description that says when to use it, typed arguments, short results, and errors that say how to fix the call.
* Every tool definition costs context tokens on every request. With many tools, load definitions on demand through a tool search step.
* MCP: a host runs one client per server; servers expose tools (the model calls), resources (the application loads) and prompts (the user picks). The model never talks to a server directly.
* MCP uses JSON-RPC 2.0 over stdio for local servers or Streamable HTTP for remote ones. Since the 2026-07-28 revision it is stateless.
* MCP connects an agent to tools; A2A connects agents to each other.
* Short-term memory is the context window and run state. Long-term memory is an external store the agent reads and writes.
* For any memory, answer four questions: what to write, when to retrieve, how to resolve conflicts, how to delete.

## Common mistakes

* Wrapping every API endpoint as its own tool. The context fills with definitions and the model confuses similar tools.
* Writing a description that says what the tool is but not when to use it or when not to.
* Returning raw API responses. A 4,000-token JSON row stays in the context for every later step.
* Raising an exception or returning a bare status code on bad arguments, so the model cannot tell what to change.
* Saying "MCP replaces function calling". MCP packages and exposes tools; the model still asks for them through function calling.
* Storing every message as memory, with no timestamp, no source and no way to delete.

## Practice

* Write definitions for 5 tools of a food-delivery support agent. For each, list one request that should trigger it and one that should not. Target: a classmate picks the right tool for 10 out of 10 test requests using only your descriptions.
* Run the code example, then add a `limit` argument (number, 1 to 20) to a new `search_orders` tool. Send 5 invalid calls and confirm that every error names the argument and says how to fix it.
* Count the tokens in your tool definitions with a tokenizer, or estimate them as characters divided by 4. Report tokens per model call with all tools loaded and with only the top 5 loaded.
* Extend the memory store with a `superseded` list per key and a `forget_user` method. Test: after `forget_user("u1")`, every retrieve for u1 returns an empty list and u2 is unchanged.

## Interview questions (11)

1.MCP vs plain function calling?Easy

Function calling is how one model asks for one tool inside one app. I send tool definitions with the prompt, the model returns a name and JSON arguments, and my code runs it. MCP is a standard way to package and expose tools so any client can discover and use them. MCP sits on top of function calling; it does not replace it. The host fetches tool definitions from MCP servers, hands them to the model as ordinary function definitions, and when the model emits a call the host forwards it to the right server. The gain is reuse: I build a tool once and it works across models and frameworks.

2.How do you give an agent memory?Medium

Keep the working state in the context. Summarise or drop old turns as it fills. Write durable facts to an external store and retrieve them when relevant. Decide what is worth remembering, because storing everything pollutes later retrieval. In practice that means an explicit write step that extracts facts with a user id, timestamp and source, a small profile that is always loaded, and a search over the rest that returns only the top few items for the current request.

3.Explain MCP's architecture.Medium

A host application runs one client per server. Servers expose tools the model can call, resources the application loads, and prompts the user picks. Messages are JSON-RPC, over stdio for local servers or Streamable HTTP for remote ones. The host stays in control of what is called and what the user approves. The model never talks to a server directly: it writes a tool call, and the host decides whether to send it. In the 2026-07-28 revision the protocol became stateless, so there is no initialize handshake or session; each request carries its version, and state is passed through explicit handles.

4.An agent has 200 tools. What breaks, and what do you do?Hard

Tool definitions eat the context, and the model picks wrong tools when many look alike. At an assumed 150 tokens per definition that is 30,000 tokens on every model call. I would group and namespace tools, retrieve only the relevant ones per step, merge overlapping tools, and move specialised sets into sub-agents. The retrieval step is a tool search: a small core set stays loaded, and a search tool returns the few definitions that match the task. Then I check tool-selection accuracy on a fixed set of tasks before and after.

5.How would you design memory for a personal assistant agent?Hard

Store stable facts and preferences as structured records, and past conversations as searchable summaries. Retrieve only what is relevant to the current request. When facts conflict, prefer the newest and keep its source. Let the user see, correct and delete what is stored. I would key every record by user id so users never mix, load a short profile at the start of each session, and search the rest on demand. Deletion has to reach the record, its embedding and any summary built from it. I would keep secrets such as card numbers out of memory completely.

6.What does a good tool definition look like?Easy

One clear job per tool. A name that says the action, like create\_return. A description that says when to use it and when not to, because the model reads only the definition, never the code. Typed arguments with patterns, enums and ranges, so my code can reject a bad call before it runs. Short results with only the fields the model needs. And errors written as instructions: "order\_id must look like A1042, you sent 1042" lets the model fix the call in one step, where a bare 500 makes it guess.

7.In MCP, who controls tools, resources and prompts?Medium

Tools are controlled by the model: it decides when to call one, based on the description and the conversation. Resources are controlled by the application: the host chooses which read-only context to load, addressed by URI. Prompts are controlled by the user: they are templates a person picks, for example from a menu. This split matters for safety. Resources cannot act and prompts need a human choice, so tools are the primitive that needs validation, permissions and approval for risky actions.

8.stdio or Streamable HTTP: how do you choose a transport?Medium

Stdio is for local servers. The host starts the server as a subprocess and they talk over standard input and output, with no network port open. It suits developer tools and local files, and the server reads credentials from the environment. Streamable HTTP is for remote servers: one service at a URL, shared by many users, with OAuth-based authorization. I pick stdio when the tool needs the user's own machine and HTTP when a team wants one deployed, monitored server. The older HTTP plus SSE transport is deprecated, so I would not start new work on it.

9.What is the difference between MCP and A2A?Easy

MCP connects an agent to tools; A2A connects agents to each other. With MCP the other side is a function with a schema: I call it and get a result back. With A2A the other side is another agent that takes a goal, may work for a long time and may ask questions back. A2A covers how agents discover each other and exchange tasks. They are used together: an agent uses MCP for its own tools and A2A to hand part of the job to an agent owned by another team or vendor.

10.A tool returns 40,000 tokens of JSON. What do you change?Medium

I fix the tool, not the prompt. The result stays in the context for every later step, so it costs tokens again on each call and pushes useful content out. I would return only the fields the model needs, add filters and a limit argument, paginate, and return a reference such as an id or file path for the bulky part so the agent can fetch details only when needed. In the agent runtime I would also cap tool-result size and clear old results once they have been used.

11.What goes wrong with long-term memory in production?Hard

Four things. Stale facts: an old address is retrieved after the user moved, so every record needs a timestamp and newest-wins. Pollution: storing everything means retrieval returns noise, so I filter at write time. Leaks: a memory from one user appears for another, so every read is filtered by user id in code. And poisoned memory: text from a web page or email gets saved as a "fact" and steers later sessions, so I store the source and only trust facts the user stated. I would also test deletion end to end.

## Quiz

1.The model returns a tool call. What happens next?

2.In MCP, which primitive does the model decide to use?

3.A team runs an MCP server on a shared host for 300 employees. Which transport fits?

4.An agent has 200 tools at an assumed 150 tokens per definition. How many tokens of definitions go with each model call if all are loaded?

5.Memory holds "city: Pune" from January and "city: Bengaluru" from March. What should retrieval return?

## Practice these problems

* [GENAIChatbot with long-term memoryMedium](/ai/problems/chatbot-with-memory)
* [GENAICustomer support agent with tools and approvalsHard](/ai/problems/customer-support-agent)
* [GENAIAgent runtime: loop, tools, checkpoints and budgetsHard](/ai/problems/agent-runtime-harness)
* [GENAIMCP tool platform for internal APIsMedium](/ai/problems/mcp-tool-platform)

## Further reading

* [Model Context Protocol documentationGuidemodelcontextprotocol.io](https://modelcontextprotocol.io/)
* [Model Context Protocol specificationGuidemodelcontextprotocol.io](https://modelcontextprotocol.io/specification/latest)
* [What is MCP (Model Context Protocol)?Articlescalar.com](https://scalar.com/learn/mcp/what-is-mcp)
* [MemGPT: Towards LLMs as Operating SystemsPaperarxiv.org](https://arxiv.org/abs/2310.08560)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousAgent frameworks - LangChain, LangGraph](/ai/learn/agent-frameworks-langchain-langgraph)[NextAgents in depth - patterns, reliability, security](/ai/learn/agents-in-depth)

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

1. [What a tool is, and the flow of one call](#what-a-tool-is-and-the-flow-of-one-call)
2. [What a good tool definition looks like](#what-a-good-tool-definition-looks-like)
3. [Every tool definition costs context tokens](#every-tool-definition-costs-context-tokens)
4. [MCP: build a tool once, use it everywhere](#mcp-build-a-tool-once-use-it-everywhere)
5. [MCP roles: host, client, server](#mcp-roles-host-client-server)
6. [Three primitives, and who controls each](#three-primitives-and-who-controls-each)
7. [Messages, transports and the rest of the protocol](#messages-transports-and-the-rest-of-the-protocol)
8. [MCP and A2A](#mcp-and-a2a)
9. [Short-term and long-term memory](#short-term-and-long-term-memory)
10. [Four types of memory](#four-types-of-memory)
11. [The four memory design questions](#the-four-memory-design-questions)
