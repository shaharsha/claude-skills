# GPT (OpenAI) - Provider Deep-Dive

Applies to the **GPT model family** wherever it runs: the OpenAI API, Azure OpenAI / Microsoft Foundry, and AWS Bedrock. The platform does not change prompt engineering - the model version does - but Azure/Foundry has real API and deployment differences worth knowing (see *Azure Foundry and AWS Bedrock* below).

**Current models (September 2026):** **GPT-6** is the current generation. The naming scheme introduced with GPT-5.6 holds - the number is the generation; **Astra / Sol / Luna** are capability tiers that advance on their own cadence - and GPT-6 adds **Astra** as a new top tier above Sol.

- **GPT-6 Astra** (`gpt-6-astra`, GA Sept 4 2026) - flagship "for the hardest end-to-end work"; state of the art on computer use, browsing, SWE, science, professional work; uses substantially fewer output tokens per task than earlier models. **$10 / $50** per 1M (cached input $1, cache writes $12.50). Effort `low`-`max` - **no `none`** (400). Apr 30 2026 cutoff. ZDR-eligible. OpenAI's default recommendation when unsure.
- **GPT-6 Sol** (`gpt-6-sol`, Sept 22 2026) - complex coding and agentic workflows, trained with Astra's methods; ~half GPT-5.6 Sol's factual mistakes on OpenAI's internal eval. **$2 / $10** (cached $0.20). Effort `none`-`max`, default `medium`. Apr 20 2026 cutoff.
- **GPT-6 Luna** (`gpt-6-luna`, Sept 22 2026) - the efficient tier "for focused, high-volume tasks with a clear goal" (summarization, extraction, quick answers). **$0.10 / $0.50** (cached $0.01). Effort `none`-`max`, default `medium`. May 18 2026 cutoff.
- **There is no GPT-6 Terra.** For the mid tier OpenAI still points to **GPT-5.6 Terra** (`gpt-5.6-terra`, $2 / $12, Feb 2026 cutoff). GPT-5.6 Sol ($4 / $20) and Luna ($0.20 / $1.20) remain available at their reduced prices. Watch for a GPT-6 Terra before assuming the tier map.
- **Small models:** `gpt-5.4-mini` / `gpt-5.4-nano` are still active, but GPT-6 Luna now undercuts nano on price with far more capability, and OpenAI's deprecation notices name 5.6 Terra / Luna as the replacements for older mini/nano snapshots. Default to Luna for the cheap tier; keep the mini/nano guidance below for existing workloads.

GPT-6 shares a **1.05M context window (922K max input) and 128K max output**. Input above ~272K tokens is billed at 2× input/cache and 1.5× output **for the whole request** - chunk or cache rather than stuffing. Batch and Flex are 50% of standard; fast mode is 2× the price (Astra fast mode: up to 2× speed, no latency SLA, not with EU data residency). Treat each new generation as a family to re-tune for, not a drop-in swap.

## Contents
- GPT-6: what's new in the API
- Prompting GPT-6 (Astra behaviors - the starting point for Sol and Luna too)
- Rethinking skills, AGENTS.md, and boundaries for GPT-6
- Roles and instruction hierarchy
- Outcome-first prompting
- Reasoning effort
- Reasoning mode (standard / pro) and multi-agent
- Sampling parameters
- Verbosity and writing style
- Structured outputs
- Tool use and agentic patterns
- Programmatic and async tool calling
- Agentic eagerness control
- Self-reflection rubrics
- Caching and the Responses API
- Prompts in code (prompt objects deprecated)
- Personality and collaboration style
- Small models (Luna, Mini / Nano)
- Images
- Safeguards, monitoring, and runtime safety classifiers
- Frontend and design
- Azure Foundry and AWS Bedrock
- Migration to GPT-6 (and the GPT-5.6 "stop doing" list)

## GPT-6: what's new in the API

- **Async tool calling:** set `async:true` on a function or custom tool; the model keeps reasoning, calls other tools, or answers independent parts of the request while your app runs it; return the result later with the original `call_id`. Your app still executes the tool and tracks pending work (OpenAI documents a developer-defined wait-tool pattern).
- **Mid-turn steering:** over a WebSocket Responses connection, send new user instructions (a correction, a changed requirement) while the model is working; completed work is preserved and the update joins a continuation.
- **Change effort without breaking the cache:** add a `{"type":"configuration_update","reasoning":{"effort":"high"}}` input item before the next user message and **leave request-level `reasoning.effort` unchanged**; it holds until another update. GPT-6 family, standard single-agent mode, effort only. Tools can likewise be enabled/disabled without breaking the cache.
- **Misalignment monitoring** runs asynchronously on Astra-class traffic; safety checks can **stop the task in the API** (ChatGPT/Codex ask the user to review instead) - see *Safeguards*.
- Carries over from GPT-5.6: computer use, Structured Outputs, streaming, programmatic tool calling, multi-agent orchestration, prompt caching, persisted reasoning, compaction, pro mode.
- **Endpoint limits:** Astra supports Chat Completions but its **tool calling requires the Responses API**; Sol and Luna support function calling in Chat Completions **only at `reasoning_effort:"none"`**. Use Responses for any reasoning-with-tools work.

## Prompting GPT-6 (Astra behaviors - the starting point for Sol and Luna too)

OpenAI's *Using GPT-6* guide documents these for Astra and says to use the same prompts as a starting point across the family, evaluated per model. Five behaviors:

- **It asks more, and can stop early.** Astra is a more deliberate collaborator: it stays coherent on long tasks but is *more likely to ask a clarifying question* where GPT-5.6 Sol would assume, and can return a first implementation for review while work remains. For autonomous runs, start from OpenAI's prompt: *"You should infer the user's intent and task scope from the instructions and prior conversation context. Your job is to bias towards action and carry the user's intended task to completion. When the user expresses intent to perform new work or fix an existing issue, persist until the user's intended goal is complete…"* Treat "can you…", "I want to…", "help me…" as instructions to act: *"Do not stop at acknowledging capability, proposing a plan, or offering to continue. Do not settle for a partial or 'helpful enough' solution…"* And make approval the last step, not the first: *"Before asking the user clarifying questions, you should complete the work that is already authorized from context and necessary to make the proposed action concrete and reviewable. The user should be approving a concrete, reviewable result… You don't need user permission for reversible tasks, read-only actions, reviews or fixes… Do not introduce unsolicited warnings, disclaimers, approval flows, or safety/compliance checklists due to hypothetical risk."* It also asks non-blocking questions mid-work by default - tune these to the autonomy your app wants. **Define completion up front** (include "get it running, inspect the result, fix what fails" in the task if that's what done means); a "stop for review after the first implementation" requirement pulls it toward an earlier stop.
- **Stronger, more sensitive instruction following** - including to instructions in **skills and `AGENTS.md`**. Unclear or conflicting guidance in a skill can make it pause and block early. OpenAI *strongly recommends* auditing every file the model can read. State precedence: *"The user's instructions take precedence over guidelines provided in a skill. If explicit user instructions conflict with a skill's instructions, prioritize the user's instructions."* For debugging, ask it to name its source: *"If a skill causes you to ask for permission or confirmation, pause, leave requested work unfinished, or diverge from the user's intent, name and link to the exact SKILL.md file you read, quote the relevant instruction, and briefly explain how it applies."*
- **Heavy formatting and recurring phrases.** Astra leans to lists, tables, and Markdown, and repeats stock phrases across sessions. For prose: *"Default to using clear, concise paragraphs, each developing one main idea. Use lists only when the information is genuinely parallel, sequential, or easier to compare… State the main point clearly and early…"* For technical writing: *"Use plain language over jargon…calibrate your writing to the level of background knowledge assumed from the user's prompt."* OpenAI ships an explicit **anti-slop list** (no "Bottom line:", "delve", "foster", "leverage", "it's worth noting", "importantly", "genuinely", "This isn't about X. It's about Y.", unprompted "X, not Y" contrastive framing, concluding summary lines, invented compound labels) - adapt it rather than writing "don't sound like AI". (Sol and Luna inherit Astra's improved communication - clearer, less jargon, slightly shorter - so check whether they need it.)
- **Delegates less than you may want.** If your harness has multi-agent tools: *"If at any point you can parallelize work by delegating tasks to another agent (no matter if you are the root or subagent), you should do so using collaboration tools if it could save time or improve quality."* Inter-agent messages can have spacing/grammar glitches: tell it they may be read by a human. (Contrast Claude Opus 5 / Fable 5.x, which over-delegate.)
- **Over-tests small changes.** Calibrate: *"Do not write tests for reversible, low-impact changes that mirror the implementation… Run tests appropriate to the change and complete required checks. Once those pass, broaden or repeat testing only when new changes, failures, or unresolved concerns justify it."* OpenAI's own FrontierCode developer message: *"Avoid creating excessive test files. Create a new test file only when required by repository conventions… Avoid unrelated cleanup and unnecessary complexity. Reuse suitable existing utilities. Read relevant repository instructions and inspect nearby code, tests, documentation, and CI. Follow established conventions. The goal is clean, mergeable code."*

## Rethinking skills, AGENTS.md, and boundaries for GPT-6

From OpenAI's *Rethinking skills and prompts for GPT-6 Astra* - the cleanup to do on migration (and good practice for any capable agent; see SKILL.md):

- **Skill descriptions: as short as possible, triggered narrowly.** Long descriptions get truncated when many skills load, and over-broad triggers make the model load irrelevant instructions. Bad: *"Use when working with databases, queries, models, or persistence."* Good: *"Use when adding or changing a migration, or reviewing its rollout."*
- **Progressive disclosure:** for multi-workflow skills, make the root file a minimal router to supporting docs/scripts.
- **Drop recipe-style skills** - elaborate step itineraries that helped older models now hinder. Guidance written for Sol/Luna may overconstrain Astra; consider which models read shared repo instructions.
- **AGENTS.md: point to docs contextually**, not "before every edit, read architecture.md, database.md, and deployment.md" (burns context, slows work). Good: *"Use architecture.md for service boundaries, database.md for schema changes, and deployment.md when preparing a deployment."*
- **Remove "run the tests / check your work" encouragement** - Astra verifies on its own. Instead **grant explicit permission for known-safe workflows** (*"The local tests use disposable fixtures and have no production access. Run them, fix failures caused by the requested change, and rerun affected tests without asking for approval at each step."*).
- **Soften boundary language written for overeager models.** Strong "always ask first" rules added for older models make Astra stop where you'd be happy for it to continue.
- Ask Astra itself to audit your skills/AGENTS.md against these points.
- **Skills in the Responses API are *user-priority* input, not system.** The platform adds each mounted skill's name, description, and path to the user context; the model decides whether to open `SKILL.md`. For deterministic use, say "use the `<name>` skill." Treat skills as privileged, potentially untrusted code: review them, never let end users attach arbitrary skills from an open catalog (prompt-injection and exfiltration risk), and gate write or high-impact actions behind approval.

## Roles and instruction hierarchy

GPT exposes a `developer` role that is **prioritized over `user`**. Security-sensitive and behavior-defining instructions go in the developer message. The hierarchy is system/developer > user > tool output - treat tool results and retrieved documents as untrusted data, not instructions. Newer instructions supersede earlier conflicting ones. (Older GPT models needed key instructions re-appended every few messages in long chats; on GPT-5.6+ state each rule once - repetition measurably costs quality and tokens - and just make sure per-request `instructions` are resent.) OpenAI's framing: the `developer` message is the **function definition** (rules, business logic), `user` messages are the **arguments** it's applied to. Keep persistent tone/role guidance in the developer/system layer and task-specific details and examples in user messages.

- **The Responses `instructions` parameter applies to the current request only.** It outranks `input`, but when you chain turns with `previous_response_id`, earlier `instructions` are **not** in context - resend them on every request (or put them in a developer message in `input`).
- **Canonical developer-message order** (OpenAI's prompt-engineering guide): **Identity** (purpose, communication style, high-level goals) → **Instructions** (rules, what to do and never do, how to call functions) → **Examples** (inputs with desired outputs) → **Context** (proprietary or retrieved data - near the end, since it varies per request). Use Markdown headers for sections and XML tags for content boundaries; XML attributes can carry metadata the instructions reference.
- **Few-shot format:** pair inputs and outputs with matching ids, e.g. `<product_review id="example-1">…</product_review>` then `<assistant_response id="example-1">Positive</assistant_response>`, and show a diverse range of inputs. For maintainability, OpenAI suggests keeping examples as a concise, scannable (YAML-style or bulleted) block.
- **Read output by item type.** The Responses `output` array can hold reasoning items, tool calls, and messages - never assume text is at `output[0].content[0].text`; use the SDK's `output_text` or filter by type.
- **Legacy samples in OpenAI's own docs conflict with GPT-6 guidance.** The prompt-engineering guide still carries GPT-4.1/GPT-5-era agent text ("plan extensively… reflect extensively on the outcomes each function call made", "require thorough testing") relabeled for Astra. Where it disagrees with *Using GPT-6* (don't over-prescribe process; Astra already over-tests), follow *Using GPT-6*.

GPT follows instructions with surgical precision, which makes **contradictions actively harmful** - the model burns reasoning tokens reconciling them (and on GPT-6 may stop and ask). Audit prompts for conflicts ("after informing the patient…" vs. "without contacting the patient…") and add clarifying clauses for genuine exceptions ("do not look up in the emergency case - proceed immediately").

## Outcome-first prompting

Reasoning GPT models work best with **a clear goal, strong constraints, and an explicit output contract, without prescribing every intermediate step** (OpenAI's reasoning guide). Specify: expected outcome, success criteria, allowed side effects, evidence/citation rules, output shape, stopping conditions, and for agentic work, **what counts as done and how to verify it**. Avoid step-by-step process instructions unless the exact path is product-critical - process-heavy stacks from older models over-specify what current models handle natively. GPT-5.6+ infers the user's goal and intended level of work from context; still supply domain context, hard constraints, approval boundaries, and success criteria, and **say explicitly when an important ambiguity should make the model stop and ask** (GPT-5.6 won't ask unless told; GPT-6 Astra asks *more* - tune in the opposite direction).

Prefer **decision rules over absolutes** for judgment calls. Replace ALWAYS/NEVER with "if X, do Y; otherwise Z." Reserve hard rules for policy and safety.

## Reasoning effort

`reasoning.effort` (Responses) / `reasoning_effort` (Chat Completions): `none` / `low` / `medium` / `high` / `xhigh` / `max`, **model-dependent**:

| Model | Supported | Default |
|---|---|---|
| GPT-6 Astra | `low`-`max` (`none` → 400) | not documented - **pin it explicitly** |
| GPT-6 Sol / Luna | `none`-`max` | `medium` |
| GPT-5.6 Sol / Terra / Luna | `none`-`max` | `medium` (standard and pro mode) |
| GPT-5.5 | `none`-`xhigh` | `medium` |
| GPT-5.4 / Mini / Nano | `none`-`xhigh` | **`none`** - pin it or reasoning is off |

`minimal` existed only on the original GPT-5 models; move it to `low`. OpenAI's per-level guidance:

- `none` - latency-critical work with no reasoning or multi-step tool chains (voice, fast retrieval, classification).
- `low` - efficient reasoning where tool use, planning, or search still matter (data analysis, drafting, execution-oriented coding, support chat).
- `medium` - "default configuration for most workloads" (agentic coding, research, spreadsheets/slides, long-horizon delegation).
- `high` - hard reasoning, complex debugging, deep planning; evaluate against `medium`.
- `xhigh` - deep research, async/long-running agents, security and code review - only where evals show a clear benefit.
- `max` - the most complex tasks; if you run `xhigh`, evaluate whether `max` is stronger.

Reasoning effort is a **last-mile knob, not a primary quality lever** - it can cause overthinking when instructions conflict or stopping criteria are weak. Before raising it, add completeness contracts, tool-use persistence, and (on GPT-5.x - Astra already self-verifies) verification loops. On migration: preserve your *effective* effort (GPT-6 Astra: move `none`/`minimal` to `low`); moving 5.5 → 5.6, test one level lower. For faster time-to-first-visible-token, ask for a short preamble before deeper reasoning. GPT-5.6+ renders prior-turn reasoning into the next turn by default (`reasoning.context:"all_turns"`).

## Reasoning mode (standard / pro) and multi-agent

GPT-5.6 and GPT-6 support `reasoning.mode` = `"standard"` (default) | `"pro"`, **independent of effort**: mode selects standard vs. pro execution; effort sets reasoning within it. `pro` does more model work (higher cost, higher ceiling), is settable on any tier via the Responses API (no `-pro` slug), and bills at the model's standard per-token rates but consumes more tokens - use it only where evals show the hardest tasks need it. Don't add "think harder" or ask for multiple candidates in `pro` mode; the mode does that work. (ChatGPT surfaces it as "Sol Pro" / "Astra Pro".)

Above pro sits **multi-agent orchestration** in the Responses API (ChatGPT's `ultra`): one model instance coordinates parallel subagents and synthesizes results. Reserve it for decomposable, high-value work - it multiplies token cost - and on GPT-6 pair it with the delegation prompt above, since Astra under-delegates by default. OpenAI's fit test: use it when work splits into independent, bounded tasks, separate context improves focus, or parallel exploration cuts wall-clock time; prefer one agent when each step depends on the last, the task is short, agents would contend over the same mutable state, or you need a fixed deterministic graph. The platform **auto-injects an uneditable developer message** into the root agent and every subagent (describing `spawn_agent`, `followup_task`, `send_message`, `fork_turns`, and the concurrency slots) - write your own instructions as additive to it, not as a replacement, and use `fork_turns` to decide how much parent context each subagent inherits (the same fork-vs-isolate choice as SKILL.md *Subagent design*).

## Sampling parameters

**GPT-6 rejects `temperature`, `top_p`, and `top_logprobs` whenever reasoning effort is not `none`** (Chat Completions: also remove `logprobs`; Responses: remove `message.output_text.logprobs` from `include`). Astra has no `none`, so on Astra they're always out. Only Sol/Luna at `none` (and older non-reasoning configs) still take them. Azure/Foundry reasoning models reject them too. GPT has now joined Claude 5.x in removing sampling knobs - steer with prompting and Structured Outputs.

## Verbosity and writing style

`text.verbosity` (`low` / `medium` / `high`) controls final-answer length independently of reasoning depth. Default `medium`; `low` is often the better starting point. Set it globally and override in natural language for specific contexts (high for code, low elsewhere). Treat answer length as separate from reasoning quality - specify word budgets when needed.

Default styles differ by model: **GPT-5.6** is concise and task-oriented (re-check old "be concise" lines - they may over-clip); **GPT-6 Astra** tends toward detailed, formatted responses and recurring phrases (use the prose and anti-slop prompts above); **GPT-6 Sol/Luna** inherit Astra's clearer communication and run slightly shorter than 5.6. Re-evaluate brevity/formatting instructions per model on migration.

## Structured outputs

Do **not** hand-write JSON schemas in the prompt. Use Structured Outputs with `strict: true` - it guarantees schema adherence and removes the validation burden. For classification, use a tool/function with an enum of valid labels. For **non-JSON** constrained output (a custom grammar, a strict DSL), reasoning models expose a `custom` tool type and a built-in `lark_tool` (Python-lark grammars via `format:{type:"grammar", syntax:"lark"}`).

## Tool use and agentic patterns

- **Put tool-specific guidance in the tool description**, not the system prompt - what it does, when to use it, required inputs, side effects, error modes. OpenAI still recommends concrete invocation examples for coding-agent tools, and warning the model that tools like `apply_patch` may return "Done" even on failure (so validate patches).
- **OpenAI's function-definition rules:** pass the "intern test" (could a person use the function from only what the model sees?); use enums and object structure to make invalid states unrepresentable (`toggle_light(on, off)` invites contradictory calls); **don't make the model fill arguments you already know** - pass `order_id` in code and expose `submit_refund()` with no parameter; **merge functions always called in sequence**; keep fewer than ~20 functions available at the start of a turn. With deferred tools, put the detail in each function description and keep the **namespace** description short (it only helps the model decide what to load). Adding examples to function definitions can *hurt* reasoning models - prefer a clearer schema.
- For large catalogs, use **tool search** to load relevant subsets; enable/disable tools without breaking the cache on GPT-6. Prefer OpenAI-hosted tools (web search, file search, code interpreter, hosted shell, apply_patch, computer use, skills, MCP) where they fit.
- **Tool preambles**: (1) have the model briefly explain *why* before a notable tool call → better accuracy (*"Before you call a tool explain why you are calling it"*, at notable steps only); (2) a short user-visible "acknowledge + plan + first step" before tool calls in streaming → better perceived responsiveness.
- **Completeness contracts / TODOs** - decompose the request into sub-tasks, track them (a TODO tool or rubric), confirm each before ending the turn; for batches/pagination, determine the expected scope and verify coverage.
- **Dependency checks** - verify prerequisite lookups before acting.
- **Empty-result recovery** - don't conclude "nothing found" on the first empty result; try alternate wording, broader filters, or a prerequisite lookup.
- Use **parallel tool calls** for independent retrieval; sequence only on real dependencies.
- **For citations, use the format the models were trained on** (OpenAI's *Citation formatting* guide). Present each citable unit with a **stable source ID** (`turn0file1`, `turn0block2`), readable text (line-numbered `[L1] …` if you want line locators), and optional metadata; **block-level units are the best default** (line-level is harder for the model, document-level too vague). The recommended marker is `\ue200cite\ue202turn0file1\ue201` (private-use Unicode start `\ue200`, delimiter `\ue202`, stop `\ue201`), with multiple sources separated by further `\ue202` delimiters and an optional locator (`\ue202L8-L13`). OpenAI says custom formats raise citation errors, especially at low effort and on hard tasks. Have the model emit **source IDs** and let your code resolve and render the locator or link. Spell out where citations go (after punctuation, end of paragraph, never grouped at the end or alone on a line, never inside bold/italics/code), what to do when support is missing, and that items without a marker aren't citable. Then **parse and validate** every citation before rendering. OpenAI also publishes optional grounding rules (relevance, source diversity, trustworthy domains, accurate representation, cite each major viewpoint when sources disagree).
- **Citation markers that look like markdown footnotes (`[N]`, `[N](url)`) trip a training pattern.** When a tool returns text with bare `[N]` markers - or partial `[N](...)` references - GPT-5.x recognizes the footnote convention and will **fabricate plausible-looking URLs** to fill them (e.g. inventing `vertexaisearch.cloud.google.com/grounding-api-redirect/...` tokens) even when no URL existed. For per-claim attribution: (a) use a marker with no completion pattern (`(source N)`, Hebrew `(מקור N)`); (b) drop inline markers and give an end-of-reply `**Sources:**` footer with titles, not URLs; (c) return URLs only in a structured field.

## Programmatic and async tool calling

**Programmatic tool calling** (GPT-5.6+): add a `programmatic_tool_calling` tool and opt eligible tools in via **`allowed_callers`**; the model writes a small **JavaScript program (isolated V8, no network)** that orchestrates those tools, loops, filters and aggregates, returning only the distilled output - fewer round-trips and large intermediate payloads kept out of context (OpenAI-cited 38-63.5% token reductions). Handle `program` / `program_output` items in the Responses API. Use it for multi-step / batch / filter-heavy work; prefer plain calls where you want to reason over each result. When both routes exist, **make the routing task-specific** (name the stage, eligible tools, output schema, retry limit, stop condition) - a generic "use programmatic tool calling efficiently" won't route correctly. ZDR-compatible. (OpenAI's counterpart to the "expose tools as a code API" pattern in SKILL.md Section B.)

**Async tool calling** (GPT-6): mark slow tools `async:true` so the model keeps working while they run; pair with a wait tool when it must block on a result. The same shape as the non-blocking subagent orchestration Anthropic recommends for Fable 5.1.

## Agentic eagerness control

Steer exploration depth in **both** directions - and note the GPT-6 default moved: GPT-5.6 Sol ran long; GPT-6 Astra is more tentative about when to stop.

- **Reduce eagerness** (over-exploring, too many tool calls): lower `reasoning.effort`; set an explicit tool-call budget ("use at most 2 tool calls before answering"); define exploration criteria; give an escape hatch ("if you can't fully verify, proceed with your best answer and note the assumption").
- **Increase eagerness** (stops too early - the common GPT-6 Astra case): the initiative/follow-through prompts above; define completion before starting; deduce a reasonable approach rather than ask, documenting assumptions afterward.
- **Don't over-repeat the approval policy** - state the autonomy rule once (safe local actions proceed; external/destructive/costly/scope-expanding actions need confirmation). Repeating "ask first" / "wait for approval" across the prompt makes the model pause on safe, expected actions - even more so on Astra.
- **Enforce hard limits in the harness, not the prompt.** In OpenAI's own adversarial eval, GPT-6 Sol still tried to work around an explicit "access denied" warning in ~64% of runs (Luna ~42%) `[reported by TechCrunch from OpenAI's alignment charts]`; Astra never tried to circumvent a Codex auto-review denial.

## Self-reflection rubrics

For high-quality open-ended generation (zero-to-one app builds, design), have the model construct a private **5-7 category excellence rubric**, iterate against it, and not finish until the work would top every category. Reliably lifts quality on subjective generation tasks (OpenAI still uses this in its one-shot web-app sample prompt).

## Caching and the Responses API

Use the **Responses API** for any reasoning, tool-calling, or multi-turn use case (GPT-6 tool calling requires it). For multi-turn, pass `previous_response_id` - it carries prior reasoning forward so the model doesn't reconstruct plans after each tool call. When managing state yourself, preserve the `phase` value on assistant items; with `store:false` (or ZDR), replay **every output item including reasoning items' `encrypted_content`** or the model loses its chain.

Caching on **GPT-5.6 and later**: prefix-based, **minimum 1,024 visible input tokens**; implicit breakpoint at the end of the latest eligible message, plus **explicit breakpoints** (`prompt_cache_options.mode:"explicit"` + `prompt_cache_breakpoint`); lifetime via `prompt_cache_options.ttl` (`"30m"` - at least 30 minutes after the latest write or reuse; replaces `prompt_cache_retention`); **reads 0.1× input, writes 1.25× input**; `prompt_cache_key` now optional (separate cache accounting only). Keep stable content first - both in the prompt **and** among the first parameters of the JSON request body - with append-only tool updates, and use `configuration_update` rather than changing request-level effort. GPT-6 raised default hit rates; use the Prompt Caching dashboard and diagnostics tool to find misses. Monitor `usage.prompt_tokens_details.cached_tokens`.

## Prompts in code (prompt objects deprecated)

OpenAI is deprecating reusable prompt objects: **`v1/prompts` shuts down Nov 30 2026.** Keep production prompts in application code - small prompt-builder modules near the feature, typed inputs/schemas for dynamic values, code review, tests and eval fixtures before changes, staged rollout via flags. Migrate saved-prompt IDs with OpenAI's prompt-object migration guide. Pin model snapshots in production and keep an eval suite to catch behavior shifts on upgrades. OpenAI's hosted **Evals, graders, and Agent Builder now sit under "Legacy APIs"** in the docs and graders are being deprecated - keep your eval harness in your own code or a third-party platform rather than building new work on them. OpenAI's own judge advice: prefer pairwise or pass/fail over scales, start with the strongest model as judge and validate agreement with human labels before cheapening it, and control for response length.

## Personality and collaboration style

Define these as **two separate, concise blocks** rather than one bundled instruction:
- **Personality** - persistent tone, warmth, directness, formality, humor, polish level.
- **Collaboration style** - when to ask vs. assume, how proactive to be, how to handle uncertainty and risk. On GPT-6 this block carries more weight: Astra's default leans toward asking.

For customer-facing work, also specify the channel (Slack, email, memo, PRD), emotional register, and hard length limits.

## Small models (Luna, Mini / Nano)

**GPT-6 Luna** is now the default cheap tier - frontier-family methods at $0.10/$0.50, and at higher effort it matches GPT-5.6 Sol on OpenAI's factuality eval at ~1/100th the cost. It supports `none` for latency-critical paths. `gpt-5.4-mini` ($0.75/$4.50) and `gpt-5.4-nano` ($0.20/$1.25, default effort `none`) remain active for existing workloads. Smaller/cheaper models are more literal and make fewer assumptions:
- Put the most critical rules first.
- Specify the full execution order for tool use and side effects.
- Use structural scaffolding: numbered steps, explicit decision rules.
- Separate "do the work" from "report the result".
- Show the correct flow with an example; define ambiguity behavior explicitly.
- Specify packaging directly (length, follow-up behavior, citation style).
- Don't rely on a bare "MUST" - weaker models need the structure, not the emphasis.

But **guidance that helps Luna can overconstrain Astra** - if one prompt or skill serves several tiers, test it on each or make it model-conditional.

## Images

Image `detail`: `auto`/unset behaves as `original` (preserves detail up to ~10.24M pixels / 6000px). Use `high` for standard vision (~2.5M pixels / 2048px); `low` when speed/cost dominate. For spatially sensitive or computer-use tasks, prefer `original`.

## Safeguards, monitoring, and runtime safety classifiers

- **Cyber:** GPT-6 Astra meets OpenAI's *Critical* cyber threshold. It does defensive work (secure code review, patching) but **refuses advanced offensive tasks such as proof-of-concept exploits**; OpenAI plans broader defensive access via its Daybreak program. GPT-5.6 introduced real-time cyber/bio classifiers over the streaming output: some requests are blocked mid-completion, others **pause for several seconds mid-stream** while a classifier reviews partial output (a latency spike, not a hang). A dedicated `gpt-5.6-cyber` model exists for trusted-access defensive work.
- **Misalignment monitoring** (Astra-class): asynchronous classifiers check whether the agent is correctly interpreting instructions in consequential contexts (moving or accessing sensitive data, destructive changes). It can only *stop* conversations it can link - Responses API with persisted reasoning, WebSockets, or OpenAI compaction; plain Responses requests get webhook alerts only; Chat Completions isn't covered. A stop returns **HTTP 403, code `misalignment_policy_violation`** (match the code, not the message; streaming clients must also handle it mid-stream). On it: stop dispatching actions for that conversation, don't auto-retry, keep request/response IDs and tool-call records, and surface it to the responsible human. There's no resume, and because monitoring is asynchronous an action may already have run - a stop doesn't undo it. A flag isn't proof of wrongdoing, and monitoring can miss things, so keep your own human approval on consequential actions.
- **Org-level enforcement:** repeated high-risk classifications trigger errors and a warning email; continued traffic past the stated window (usually ~7 days) can cut the org's model access. `safety_identifier` is what keeps enforcement on the offending end user instead of your whole org. Cyber-capable models also get API-side activity monitoring; approved defensive work goes through Trusted Access / Daybreak (access is per org, project, model, and surface, and doesn't imply ZDR).
- Mitigations: send a stable, privacy-preserving **`safety_identifier`** per end user; handle refusals, stops, and truncated completions explicitly rather than assuming a clean finish; frame genuinely defensive work as such. (GPT's analogue to Claude's `stop_reason:"refusal"` handling - build for it in the harness.)

## Frontend and design

GPT-5.6+ has strong design judgment and, with computer use, inspects and refines the **rendered** result; GPT-6 Astra is OpenAI's best at adhering to existing templates (slides, documents, design systems) and producing well-structured artifacts. Give the design system/tokens plus high-level intent and let it self-refine, rather than piling on anti-"AI slop" scaffolding. OpenAI's recommended stack for generated front ends: Tailwind CSS, shadcn/ui or Radix Themes, Lucide/Material Symbols/Heroicons, Motion. For large codebases, specify principles, UI/UX states (hover, empty, loading), accessibility, file structure, and reusable component patterns. OpenAI's published **frontend prompt block** (written for GPT-5.5, broadly applicable) is a good template: match the domain (operational tools should feel dense, quiet, and utilitarian; games can be expressive); build the usable experience as the first screen rather than a landing page; icons over text buttons; no cards inside cards and no page sections styled as floating cards; no decorative gradient orbs; no one-note palettes (purple gradients, beige/cream, slate, espresso); text must fit its container on every viewport; verify 3D/canvas output with screenshots across viewports before finishing. (Contrast Claude, whose frontend default has a persistent house style to steer away from - see `claude.md`.)

## Azure Foundry and AWS Bedrock

GPT runs on the OpenAI API, Azure / Microsoft Foundry, and AWS Bedrock (GPT-6 Astra launched on all three). Prompt engineering follows the **model version, not the platform**; on Bedrock, GPT is reached through the OpenAI-compatible endpoint (check the Bedrock docs for exact model IDs). Azure OpenAI / Foundry specifics:

- **Endpoint & model name.** Call `https://YOUR-RESOURCE.openai.azure.com/openai/v1/` and pass your **deployment name** as `model`. Auth is API key or Microsoft Entra ID. New models may need a quota request.
- **Roles.** `developer` is equivalent to `system` on Azure reasoning models, and the latest models accept `system` too - but **don't send both in one request.**
- **Token limit parameter.** Reasoning models use **`max_completion_tokens`** (Chat Completions) / **`max_output_tokens`** (Responses); `max_tokens` is not supported. Always set `reasoning.effort` explicitly.
- **Unsupported sampling knobs.** `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`, `logprobs`, `top_logprobs`, `logit_bias` are unsupported on reasoning models.
- **Reasoning summaries** via `reasoning.summary` (`auto` / `detailed`; GPT-5 series doesn't support `concise`). **Don't try to extract raw reasoning by other means** - it violates the Acceptable Use Policy.
- **Foundry-exposed features:** `preamble` objects, `allowed tools` under `tool_choice`, the `custom`/`lark_tool` grammar tools, and per-deployment **content filters** (configured in the portal, not the prompt).

## Migration to GPT-6 (and the GPT-5.6 "stop doing" list)

**To GPT-6 (from GPT-5.6 or earlier):**
1. Set `model` to `gpt-6-astra`, `gpt-6-sol`, or `gpt-6-luna` (no Terra - stay on `gpt-5.6-terra` for that tier). Use the Responses API for tools.
2. **Pin effort.** Preserve your effective effort; on Astra, `none`/`minimal` → `low`. If you vary effort per turn, switch to `configuration_update` items and keep request-level effort fixed.
3. **Remove `temperature`, `top_p`, `top_logprobs`** (and `logprobs` / `output_text.logprobs`) unless you run Sol/Luna at `none`.
4. From GPT-5.5 or earlier: `prompt_cache_retention` → `prompt_cache_options.ttl:"30m"`; budget for 1.25× cache writes; replay encrypted reasoning with `store:false`.
5. Handle safety stops (Astra misalignment monitoring, cyber refusals) and send `safety_identifier`.
6. **Re-tune behavior, mostly by subtracting:** audit skills/AGENTS.md (short descriptions, contextual doc pointers, no recipes, precedence line), soften "ask first" boundary language, remove "run the tests / check your work" prodding, then add follow-through prompts if it pauses for approval, prose/anti-slop prompts if formatting is heavy, a delegation prompt if you run multi-agent, and a testing-calibration line if it over-tests.
7. Re-run evals; benchmark accuracy, tokens, latency, and cost-per-task together (Astra's per-token price is high but it uses fewer tokens per task).

**Still valid from the GPT-5.6 migration ("stop doing"):**
- **Injecting the current date** - the model knows the UTC date; inject only for business-specific timezones or policies.
- **Detailed process steps** - unless the exact path is product-critical.
- **Hand-written output schemas** - use Structured Outputs.
- **"THOROUGH / maximize context" prodding** - causes over-tool-use. Use soft language on context gathering.
- **Assuming higher effort is better** - verify with evals.
- **Repeated instructions and redundant examples** - one clear statement is followed; OpenAI measured stripping repeated instructions lifting eval scores ~10-15% while cutting tokens 41-66% and cost 33-67% on 5.6.
- **Over-detailed tool descriptions** written for weaker models.

Watch the **`reasoning.effort` default trap** on GPT-5.4 / Mini / Nano: they default to `none`, so a prompt that relied on implicit medium effort silently runs with reasoning off.

Migration order: switch the model → pin `reasoning.effort` → re-run evals → trim now-redundant instructions → only then add new guidance. OpenAI's `openai-docs` skill for Codex can apply the documented migration changes (`$openai-docs migrate this project to the GPT-6 model family`).
