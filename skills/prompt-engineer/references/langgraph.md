# LangGraph / LangChain — Framework Deep-Dive

A **framework** reference, not a provider one. LangGraph (the graph/state/durable-execution runtime) and LangChain (the agent + middleware layer on top of it) are **provider-agnostic plumbing** — model choice, thinking/effort config, sampling rules, and caching mechanics still come from the `claude.md` / `gpt.md` / `gemini.md` files. This file is about how the universal Section A patterns — context engineering and agentic systems — map onto concrete LangGraph/LangChain primitives. Read it when the code imports `langgraph` / `langchain` or the user is building a stateful, multi-step, or multi-agent system and asking how to structure context, memory, or coordination.

As of 2026 this is the agent runtime most production teams have standardized on, precisely because it owns the unglamorous parts — durability, replay, checkpointing, human approvals, fan-out — that ad-hoc agent loops eventually need.

## Three layers - pick the right one

LangChain's open-source stack is three composable layers at different points on the determinism ↔ agency spectrum (LangChain, *Deep Agents vs LangChain vs LangGraph*, Aug 2026):

- **Deep Agents** (`create_deep_agent`) - the **agent harness**: the core loop plus opinionated context-engineering middleware (filesystem, subagents, skills, memory, summarization). Most agency. LangChain's rule of thumb: **start here** for a capable general agent (it's what they run internally for GTM, coding, and docs agents).
- **LangChain** (`create_agent`) - the **agent framework**: a minimal, un-opinionated loop (model + tools) plus middleware hooks for the deterministic steps you add (summarize near the limit, run a verifier at the end, require approval). Pick it for less built-in context management and finer control over what reaches the model each step - e.g. a RAG Q&A bot, or latency-critical apps. Deep Agents is literally `create_agent` + middleware.
- **LangGraph** - the **agent runtime**: durable, graph-shaped workflows where you encode domain logic in the topology. Pick it when the task doesn't fit a single loop or mixes deterministic and agentic steps (e.g. an application-processing pipeline where only extraction touches an LLM and scoring/approval is code).

They compose: a `create_deep_agent` can be a node in a LangGraph workflow, and a custom graph can be a subagent. Middleware is the first tool for adding determinism (approvals, compliance checks, business rules) around an agentic loop; drop to a custom graph only when middleware hooks aren't enough.

## Contents
- Three layers - pick the right one
- The mental model: State, checkpointer, Store
- Durable execution and human-in-the-loop
- Context types and data sources
- Context engineering: write / select / compress / isolate → primitives
- Agents and middleware (the main steering surface)
- Multi-agent: supervisor vs swarm
- Deep Agents (the four levers, prebuilt)
- Prompt-engineering implications
- Observability and the eval loop

## The mental model: State, checkpointer, Store

- **State** — the shared, typed object that flows through the graph; every node receives it and returns updates (merged via reducers). It *is* the agent's accumulated context: messages, tool outputs, intermediate results, flags. This is your **short-term / thread-scoped memory** and your scratchpad.
- **Checkpointer** — persists State across every step of a thread (e.g. `MemorySaver` in dev, a DB-backed saver in prod). Enables durability, replay, time-travel, and human-in-the-loop pauses. Short-term memory = State + checkpointer.
- **Store** — **long-term, cross-conversation memory** (e.g. `InMemoryStore` in dev, a vector/DB store in prod): user preferences, extracted insights, profiles, episodic/semantic/procedural memories that must outlive a single thread.

Keep nodes **small and single-purpose** — one node, one job. Small nodes are testable, debuggable, and recomposable as the agent evolves; god-nodes that read everything and decide everything are where context bloat and untraceable behavior creep in.

## Durable execution and human-in-the-loop

The checkpointer is what makes the graph **durable**: a checkpoint is a `StateSnapshot` saved at each super-step, so a run interrupted by a crash or a deliberate pause resumes from its last recorded state instead of restarting. Three capabilities fall out of this, and two of them change how you prompt:

- **Human-in-the-loop.** `interrupt(...)` (or `interrupt_before` on a node) pauses the graph, surfaces state for a human to approve/edit, and resumes via a `Command`. **This is the structural way to do the autonomy-calibration from Section A** — instead of *prompting* "ask before destructive/externally-visible actions," you put an `interrupt` before the tool node so the gate can't be rationalized away by the model. Use prompting for judgment ("is this risky?") and an interrupt for the hard stop.
- **Time-travel / replay.** `get_state_history` lists past checkpoints, `get_state` fetches one, `update_state` mutates it before resuming — giving undo and "what-if" branching. Useful for debugging an agent trajectory and for eval harnesses that replay from a fixed state.
- **Fault tolerance.** Long autonomous runs survive process restarts; pair this with the Section A "don't stop early" context-window prompting so the model keeps going after a resume.

## Context types and data sources

LangChain frames what an agent controls as three **context types**: **model context** (what goes into the model call — instructions, message history, tools, response format; changes are *transient*, per-call), **tool context** (what tools can read/produce via State / Store / runtime; changes *persist*), and **life-cycle context** (what happens *between* model and tool calls — summarization, guardrails, logging; persists to State). And three **data sources**: **runtime context** (static per-conversation config — user id, permissions, API keys), **State** (short-term), and **Store** (long-term). Knowing which bucket a piece of context lives in tells you where to put it and how long it survives.

## Context engineering: write / select / compress / isolate → primitives

The universal taxonomy (see SKILL.md *Context Engineering*) maps cleanly onto LangGraph:

| Lever | What it means | LangGraph/LangChain primitive |
|-------|---------------|-------------------------------|
| **Write** | persist context outside the window so it survives truncation | write to a State field (scratchpad) via a tool; write durable facts to the **Store**; check-pointed State survives across steps |
| **Select** | pull only the relevant subset back in | expose specific State fields to the model; retrieve from Store by key/semantic search; **RAG** over documents; **semantic tool selection** (e.g. `langgraph-bigtool`) when the tool catalog is large |
| **Compress** | keep only the tokens the next step needs | **`SummarizationMiddleware`** (summarizes older messages with a cheap model when a token threshold trips, replacing them in State); message **trimming**; post-process token-heavy tool outputs before they re-enter context |
| **Isolate** | split context across separate spaces | **subagents** with their own windows/tools (supervisor/swarm); **state-schema isolation** — keep heavy tool outputs in State fields the model doesn't see until needed; **sandbox** execution (E2B/Pyodide) holding large objects as environment variables, not context |

The single highest-leverage LangGraph habit: **the State schema is your context budget.** Store everything you need for durability, but expose to the model only the fields the current step needs. Heavy tool results can live in State (for later selection) while staying out of the prompt.

## Agents and middleware (the main steering surface)

The standard entry point in current LangChain (v1) is **`create_agent`** — a production-ready ReAct loop on LangGraph's durable runtime (the successor to `langgraph.prebuilt`'s `create_react_agent`). You rarely hand-build the graph; you configure the agent and attach **middleware**, which is the primitive for customization — each piece handles one concern, hooks the agent loop at the right moment, and composes with the others.

Middleware hooks into any step of the lifecycle to **update context** (modify State/Store, edit message history) or **jump** to a different step:

- **`@dynamic_prompt`** — rewrite the system instructions per call based on State (message count), Store (user prefs), or runtime context (compliance/role). Dynamic system-prompt selection in code rather than one bloated static prompt.
- **`@wrap_model_call`** — intercept the model call to adjust messages, tools, model choice, or response format (e.g. swap to a cheaper model on long threads, or narrow the tool set by auth state).
- **Prebuilt middleware** to reach for before writing your own: **`SummarizationMiddleware`** (the compress lever - condenses history near the context limit; the trigger and summary prompt are configurable, e.g. `trigger=("fraction", 0.5)` to summarize at 50% and stay out of the long-context "dumb zone", with a prompt that keeps file paths and decisions verbatim), **human-in-the-loop** (pause for approval; see above), **PII redaction**, and **`ModelRetryMiddleware`** / **`ToolRetryMiddleware`**. In Deep Agents v0.7+, passing a middleware whose `.name` matches a default **replaces** that default in place.
- **Routing and guard middleware (experimental, 2026):** model-routing middleware that picks a cheap vs. capable model per request or escalates a session after repeated bad turns (`ModelRouterMiddleware` from `langchain-typesafe`, NVIDIA's Switchyard middleware), and **`AutoModeMiddleware`**, which classifies each tool call (e.g. `bash`) as risky before it executes and blocks it - the "auto mode" action classifier that coding harnesses ship, made available to any agent. Both use small, fast decision models rather than a chat LLM per check. Treat as experimental; measure routing with the break-even math in `model-selection.md`.
- **`ToolRuntime`** — how a tool reads/writes State and Store; type it (`ToolRuntime[Context]`) so each tool sees only what it needs (isolation by construction).

Streaming has distinct `stream_mode`s / typed event channels — `values` (full state per step), `updates` (just the delta), `messages` (token-by-token model output), plus `tools` and lifecycle/`custom` channels. Pick `messages` for user-facing token streaming and `updates`/`values` for orchestration and debugging. For multi-agent UX, stream **subagent status and key messages, not every token from every worker** (a research view shouldn't pay the wire cost of every worker's output), and support **reconnect-and-replay from the last checkpoint** so a browser refresh doesn't restart a long run.

Guiding rule from the docs: **start static, add dynamics only when needed.** Begin with a fixed prompt and fixed tools; introduce `@dynamic_prompt` / `@wrap_model_call` / summarization only when an observed failure mode calls for it — the same "start minimal, iterate on failures" discipline as prompt writing.

## Multi-agent: supervisor vs swarm

- **Supervisor** (`langgraph-supervisor`) — a central agent analyzes the request, routes to specialized workers, and aggregates results. Predictable routing, clear traces, single decision point. This is the **orchestrator-workers** pattern from Section A and the **safe default**.
- **Swarm** (`langgraph-swarm`) — peers hand off control directly via `create_handoff_tool`; the system records the `active_agent` so the conversation resumes with whoever's in control. No bottleneck and naturally distributed, but traces are harder to follow. Use it only when peer-to-peer handoff genuinely fits the problem.
- Both share one **State** schema for continuity and take a **checkpointer** (short-term) and/or **Store** (long-term) at compile time. Isolation note: subagents buy parallel, independent context windows but can cost **multiples more tokens** than a single agent (Anthropic has reported ~15×) — isolate when the parallelism or context-pollution win is real, not by default.
- **Subagent context modes (Deep Agents): `isolated` vs `fork`.** `isolated` (default) starts the subagent with only the task description; `fork` hands it the supervisor's full conversation (the trailing tool call is excised and the task becomes a user message), and prompt caching still applies. LangChain's rule: **fork workers** that continue work the supervisor already diagnosed (no re-reading files or rediscovering evidence) and **memory extractors** (the conversation *is* their input); **isolate verifiers/reviewers** (inheriting the supervisor's reasoning anchors their judgment) and **parallel researchers** (forking each duplicates history they don't need). Specialize subagents further with their own tools and filesystem permissions (e.g. a memorizer that may read `AGENTS.md` and docs but write nothing else).
- **Tools vs. subagents vs. sandboxes** (monday.com's production lesson after a one-agent/many-tools V1 got *worse* as tools grew): a **tool** for bounded, auditable operations (read a board, update an item, send an approved message); a **subagent** for a narrower kind of reasoning that benefits from focused instructions and a small toolset (research, risk analysis, writing); a **sandbox** for work with intermediate state that would muddy the main context (files, scripts, iterative transforms, charts) - the main agent gets only the result and a summary. One request often uses all three. They also tier tool discovery: the agent sees a menu and must activate a tool to unlock its full schema.

## Deep Agents (the four levers, prebuilt)

**Deep Agents** ([`langchain-ai/deepagents`](https://github.com/langchain-ai/deepagents); JS port `deepagentsjs`; [docs](https://docs.langchain.com/oss/python/deepagents/overview)) is LangChain's batteries-included agent harness for long-running, autonomous tasks — built via `create_deep_agent` on the LangGraph runtime — and it's the clearest worked example of write/select/compress/isolate assembled into one place. Worth reading as a reference design even if you don't adopt it:

- **v0.7 (July 2026) got leaner - a data point for "trim before you add."** It removed the hidden base system prompt, cut built-in tool descriptions 43%, and made the todo list opt-in: **65% fewer base input tokens (~6k → ~2k) at comparable reward** across autonomous, conversational, and long-context evals on four models (GPT-5.6 Luna saw −34% tokens, −15% cost, +4% reward). LangChain explicitly cites the provider guides' findings: interfaces beat examples, and repeating an instruction in both the system prompt and a tool description adds nothing. A side effect: your own prompt gets more effective with no hidden prompt competing with it.
- **Plan (write) - now opt-in:** `TodoListMiddleware` / the `write_todos` tool maintains a structured task list in state. In v0.7 evals the planning prompt + todo tool **did not improve reward and cost more**, so it's off by default. Turn it on for **long multi-step tasks**, **less capable models** that drop steps, and **UI-facing agents** where a visible plan matters.
- **Subagents (isolate or fork):** the main agent delegates via a `task` tool; subagents run in an `isolated` fresh context by default or `fork` the supervisor's conversation (see *Multi-agent* above). Instruct subagents to return summaries, not raw data.
- **Virtual filesystem (write + select):** `ls` / `read_file` / `write_file` / `edit_file` / `glob` / `grep`, with **automatic offloading** — tool inputs/results over ~20k tokens are replaced in-context by a file-path pointer + preview, so heavy content lives on disk and is pulled back only on demand.
- **Summarization (compress):** by default near ~85% of the window, an LLM writes a structured summary (intent, artifacts, next steps) while the originals persist to the filesystem as the canonical record. The threshold and prompt are overridable - summarizing earlier (e.g. 50%) keeps the model out of degraded long-context territory.
- **Programmatic tool calling (compress):** a code-interpreter runtime lets the agent write code that composes tools and *keeps intermediate outputs in the runtime, returning only the final result or selected evidence to context* — the same token-saving move as the code-execution tool surface in Section B (LangChain reports up to ~35% fewer tokens on some tasks). Use it for multi-step/batch/filter-heavy work (e.g. classify or extract across 10k documents); prefer direct tool calls for simple, transparent steps where you want to reason over each result. (At scale, delta-channel checkpointing — storing diffs, not full snapshots — keeps long runs cheap to persist.)
- **Layered system prompt:** the assembled system message stacks your custom prompt + memory (`AGENTS.md`, always loaded) + skills (progressive disclosure) + filesystem + subagent + middleware + HITL layers (no hidden base prompt since v0.7). Keep memory minimal (conventions only); push task-specific capability into focused skills loaded on demand.
- **The system prompt as a map** (LangChain's Paid Media Agent): one sentence of role, then three short sections - *how to operate*, *where numbers come from*, *how to present results* - and everything else a pointer ("the playbook lives here, the wiki there, read the index first"). Separate layers by rate of change: **skills** say *how* to do the work, a **wiki/knowledge files** describe the business, **live tools** give current data. Let **code** do deterministic work (fetch, align date windows, compute totals, apply fixed rules) and write compact results for the model, which does the judgment (connect evidence, explain causes, recommend). When sources can't be joined reliably, have the agent state the limitation (source, date window, attribution model) rather than fill the gap.
- **Memory has to forget.** Long-term memory degrades through drift and poisoning as the source of truth changes. OpenWiki's pattern: record each material claim with the version of the evidence that supports it, deterministically flag claims stale when that evidence changes, and keep them flagged until the agent re-verifies or corrects them - update cost then scales with what changed, not with memory size.

The lesson for any agent, framework or not: planning, subagent isolation, filesystem offloading, and threshold summarization are the load-bearing context-engineering moves for long-horizon work — Deep Agents just packages them.

## Prompt-engineering implications

- **Per-agent prompts, not one mega-prompt.** Each node/subagent gets a focused role + minimal tools; this is the same anti-bloat principle as the universal section, enforced by graph structure.
- **The provider rules still apply inside every node.** Thinking/effort, sampling-param restrictions, caching breakpoints, structured outputs — set them per the provider reference for whatever model that node calls. LangGraph doesn't change them.
- **Handoffs are context decisions.** Whatever crosses a handoff or returns to a supervisor should be a condensed summary (1–2K tokens), not raw exploration — decide the shape explicitly.
- **Cache-aware ordering still matters.** Keep the stable prefix (system prompt, tools) byte-identical across steps so provider prompt-caching keeps hitting; append, don't reorder.

## Observability and the eval loop

Context engineering is empirical: instrument with **LangSmith** tracing to see *where tokens accumulate* and which step degrades, then **evaluate** whether a change (a summarization node, a tool-selection retriever, a prompt tweak) actually helps before shipping. Observe → engineer → test → repeat - the same eval discipline as Section H, applied to the whole context pipeline rather than a single prompt. LangChain's 2026 practice, in brief:

- **Offline + online evals.** Offline = curated datasets, the ground truth for "did this change help?"; online = judges over a sample (or all) of production traces, a benchmark for "did quality dip overnight?" You need both, and production failures, negative feedback, and reviewer edits should flow back into the offline set - evals built only from synthetic data make agents good at imagined problems.
- **Trajectory evals** for multi-agent systems - grade which subagent was chosen, tool use, step order, and unnecessary calls, not just the final answer, which can hide routing mistakes.
- **Two eval layers:** a fast deterministic **capability suite** (unit tests for specific harness behaviors: tool selection, memory, file operations) plus end-to-end **benchmarks** by kind of work (autonomous, conversational, long-context). Harbor-format tasks (instruction + environment + verifier) let the same task run against different models, prompts, and harness versions.
- **Verifiers get reward-hacked** - agents over-cite irrelevant sources, claim actions they never took, read exposed answer material, or satisfy a proxy. The first verifier is rarely the last: inspect the verifier's own trajectory and evidence, not just its score. Interviewing the user about which capabilities matter produced better-accepted evals than one-shot generation.
- **Evaluate cost and capability together** - token, cost, and latency cuts only count if completion rate and answer quality hold.
- See SKILL.md Section H for judge calibration, repeatability, and rubric design.
