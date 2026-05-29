# GPT (OpenAI) — Provider Deep-Dive

Applies to the **GPT model family** wherever it runs: the OpenAI API and Azure OpenAI / Microsoft Foundry. The platform does not change prompt engineering — the model version does — but Azure has real API and deployment differences worth knowing (see *Azure OpenAI / Foundry* below).

**Current models (May 2026):** GPT-5.5 (`gpt-5.5`) is the frontier model; GPT-5.4 (`gpt-5.4`) and the smaller GPT-5.4 Mini / Nano (`gpt-5.4-mini`, `gpt-5.4-nano`) serve cheaper, faster tiers (mini/nano are aimed at coding, classification, extraction, ranking, and subagents). Context windows: **GPT-5.5 and 5.4 ≈ 1.05M tokens** (≈922K input / 128K output — input above ~272K is billed at 2× input and 1.5× output for the session, so chunk or cache rather than stuffing); **Mini and Nano = 400K** (272K input / 128K output). GPT-5.5's default style is efficient, direct, and task-oriented, reaching strong results with **fewer reasoning tokens** than prior models at the same effort. **Mind the reasoning-effort default — it differs by model (see *Reasoning effort*):** GPT-5.5 defaults to `medium`, but GPT-5.4 and its Mini/Nano default to **`none`**, so upgrading to 5.4 without explicitly setting effort silently turns reasoning off. Treat GPT-5.5 as a new model family to tune for — not a drop-in replacement for 5.4.

## Contents
- Roles and instruction hierarchy
- Outcome-first prompting
- Reasoning effort
- Verbosity
- Structured outputs
- Tool use and agentic patterns
- Agentic eagerness control
- Self-reflection rubrics
- Caching and the Responses API
- Personality and collaboration style
- Small models (Mini / Nano)
- Images
- Azure OpenAI / Foundry
- Migration: "stop doing" list

## Roles and instruction hierarchy

GPT exposes a `developer` role that is **prioritized over `user`**. Security-sensitive and behavior-defining instructions go in the developer message. The hierarchy is system/developer > user > tool output — treat tool results and retrieved documents as untrusted data, not instructions. Newer instructions supersede earlier conflicting ones; in long conversations reappend key instructions every 3-5 messages.

GPT-5 follows instructions with surgical precision, which makes **contradictions actively harmful** — the model burns reasoning tokens trying to reconcile them instead of ignoring them. Audit prompts for conflicts ("after informing the patient..." vs. "without contacting the patient...") and add clarifying clauses for genuine exceptions ("do not look up in the emergency case — proceed immediately").

## Outcome-first prompting

GPT-5.5 is strongest when the prompt defines the **target outcome** and lets the model choose the path. Specify: expected outcome, success criteria, allowed side effects, evidence/citation rules, output shape, and stopping conditions. Avoid step-by-step process instructions unless the exact path is product-critical — process-heavy prompt stacks from older models over-specify what GPT-5.5 handles natively and can hurt quality.

Prefer **decision rules over absolutes** for judgment calls. Replace ALWAYS/NEVER with "if X, do Y; otherwise Z." Reserve hard rules for policy and safety, which remain binding regardless of user instructions.

## Reasoning effort

`reasoning.effort`: `none` / `low` / `medium` / `high` / `xhigh`. **The default is per-model: GPT-5.5 defaults to `medium`; GPT-5.4 defaults to `none`** (the Mini/Nano tiers follow the 5.4 family — pin effort either way) — explicitly pass an effort level on 5.4 if you want it to reason, or it runs with reasoning off. (`minimal` existed only on the original GPT-5 models and is **not** available on 5.1+; on 5.4/5.5 the floor is `none`.)

- `none` — latency-critical tasks with no reasoning need (lightweight classification, voice turns).
- `low` — efficient reasoning when planning/tool use still matters but speed counts.
- `medium` — the recommended starting point for quality/latency balance (GPT-5.5's default).
- `high` / `xhigh` — raise only when evals show a measurable quality gain worth the latency.

Reasoning effort is a **last-mile knob, not a primary quality lever**. Higher is not automatically better — it can cause overthinking when instructions conflict or stopping criteria are weak. Before raising effort, add completeness contracts, verification loops, and tool-use persistence rules. For execution-heavy work (workflow, extraction, triage) start low; for research/synthesis/review start at medium+.

## Verbosity

`text.verbosity` (`low` / `medium` / `high`) controls final-answer length independently of reasoning depth. Default is `medium`; `low` is often the better starting point for concise responses and produces proportionally shorter output than GPT-5.4. Set it globally and override in natural language for specific contexts (e.g. high verbosity for code, low elsewhere). Treat answer length as separate from reasoning quality — specify word budgets when needed.

## Structured outputs

Do **not** hand-write JSON schemas in the prompt. Use the Structured Outputs API with `strict: true` — it guarantees 100% schema adherence and removes the validation burden from the model. For classification, use a tool/function with an enum field of valid labels. When you need **non-JSON** constrained output (a custom text grammar, a strict DSL), GPT-5 reasoning models expose a `custom` tool type and a built-in `lark_tool` (Python-lark grammars via `format: {type: "grammar", syntax: "lark"}`) to constrain raw-text generation — reach for that instead of describing the grammar in prose.

## Tool use and agentic patterns

- **Put tool-specific guidance in the tool description**, not the system prompt — what it does, when to use it, required inputs, side effects, error modes. GPT-5.5 shows stronger, more precise tool use on large tool surfaces and multi-step workflows.
- For large tool catalogs, use **tool search** to load only relevant subsets. Prefer OpenAI-hosted tools (web search, file search, code interpreter, computer use) where they fit.
- **Tool preambles** have two distinct uses: (1) instruct the model to briefly explain *why* it's calling a tool before the call → better tool-use accuracy; (2) a short user-visible "acknowledge the goal + outline the plan + first step" preamble before tool calls in streaming → better perceived responsiveness. Steer preamble frequency and style explicitly.
- **Completeness contracts** — decompose the request into sub-tasks and confirm each is done before ending the turn. For batches/pagination, determine the expected scope and verify coverage. Don't stop after a partial fix.
- **Dependency checks** — verify prerequisite lookups before acting; don't skip them because the end state seems obvious.
- **Empty-result recovery** — don't conclude "nothing found" on the first empty result; try alternate wording, broader filters, or a prerequisite lookup first.
- Use **parallel tool calls** for independent retrieval; sequence only when there's a real dependency.
- **Citation markers that look like markdown footnotes (`[N]`, `[N](url)`) trip a training-pattern.** When a tool returns text containing bare `[N]` markers — or worse, partial `[N](...)` references — GPT-5.x recognises the footnote convention and will **fabricate plausible-looking URLs** to fill them (e.g. inventing `vertexaisearch.cloud.google.com/grounding-api-redirect/...` tokens, the SDK-redirect format it learned from Vertex grounding traces) even when no URL existed in the source. If you want per-claim attribution from a retrieval/search tool, either: (a) use a non-footnote-shaped marker the model has no training pattern to complete (Hebrew prose like `(מקור N)` / English `(source N)` — but still expect judges may flag any inline marker as clutter); (b) drop inline markers entirely and surface only an end-of-reply `**Sources:**` footer with titles, not URLs; (c) return URLs only in a structured field the model treats as data, not text. The same fabrication pattern can hit other conventions (`(see: ...)`, `^1`, `[citation needed]`) — anything the model has seen completed in training is a candidate.

## Agentic eagerness control

Steer the agent's exploration depth in **both** directions:

- **Reduce eagerness** (over-exploring, too many tool calls): lower `reasoning.effort`; set an explicit tool-call budget ("use at most 2 tool calls before answering"); define clear exploration criteria; give an escape hatch ("if you can't fully verify, proceed with your best answer and note the assumption").
- **Increase eagerness** (stops too early): persistence prompts ("keep going until the query is completely resolved; do not hand back a partial result"); instruct the model to deduce a reasonable approach rather than ask for clarification, documenting assumptions for the user afterward.

## Self-reflection rubrics

For high-quality, open-ended generation (zero-to-one app builds, design tasks), have the model construct an internal **5-7 category excellence rubric** for the task, keep it private, iterate its solution against it, and not finish until the work would score top marks in every category. This reliably lifts quality on subjective generation tasks.

## Caching and the Responses API

Use the **Responses API** for any reasoning, tool-calling, or multi-turn use case. For multi-turn, pass `previous_response_id` — it carries prior reasoning forward so the model doesn't reconstruct plans after each tool call (measurable benchmark gains, e.g. Tau-Bench Retail 73.9% → 78.2%). When manually managing Responses state, preserve the `phase` value on returned assistant items.

Caching is automatic prefix-based (≥1024 tokens). Keep stable content (system/developer prompt, tools, examples) at the start and dynamic/user content at the end; set a consistent `prompt_cache_key` for repeated traffic; monitor `usage.prompt_tokens_details.cached_tokens`.

## Personality and collaboration style

Define these as **two separate, concise blocks** rather than one bundled instruction:
- **Personality** — persistent tone, warmth, directness, formality, humor, polish level.
- **Collaboration style** — when to ask vs. assume, how proactive to be, how to handle uncertainty and risk.

For customer-facing work, also specify the channel (Slack, email, memo, PRD), emotional register, and hard length limits.

## Small models (GPT-5.4 Mini / Nano)

Mini and Nano are more literal and make fewer assumptions. Adjust:
- Put the most critical rules first.
- Specify the full execution order for tool use and side effects — don't assume the model infers it.
- Use structural scaffolding: numbered steps, explicit decision rules.
- Separate "do the work" from "report the result" as distinct instructions.
- Show the correct flow with an example; define ambiguity behavior explicitly.
- Specify packaging directly (length, follow-up behavior, citation style).
- Don't rely on a bare "MUST" — weaker models need the structure, not the emphasis.

## Images

Image `detail`: `auto`/unset now behaves as `original` (preserves detail up to ~10.24M pixels / 6000px). Use `high` for standard vision (up to ~2.5M pixels / 2048px); `low` for aggressive downscaling when speed/cost dominate. For spatially sensitive or computer-use tasks, prefer `original`; don't rely on `auto` in production agents where precision matters.

## Azure OpenAI / Foundry

Prompt engineering is identical to the OpenAI API — same model, same `reasoning.effort` / `text.verbosity` / Structured Outputs behavior — but the API surface and a few defaults differ. What to know when the deployment is Azure:

- **Endpoint & model name.** Call `https://YOUR-RESOURCE.openai.azure.com/openai/v1/` and pass your **deployment name** as `model` (not the bare model slug). Auth is API key or Microsoft Entra ID (bearer token). GPT-5.5, 5.4, 5.4-mini, 5.4-nano are all available; GPT-5.5 may need a Tier-5/6 quota request.
- **Roles.** The `developer` role is functionally equivalent to `system` on Azure reasoning models, and the latest models also accept `system` for easier migration — but **do not send both a developer and a system message in the same request.**
- **Token limit parameter.** Reasoning models use **`max_completion_tokens`** on the Chat Completions API and **`max_output_tokens`** on the Responses API. `max_tokens` is **not** supported. Always set `reasoning.effort` explicitly — omitting it can sharply increase latency on complex prompts.
- **Unsupported sampling knobs.** `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`, `logprobs`, `top_logprobs`, `logit_bias` are all **unsupported on reasoning models** (the same omit-sampling discipline as elsewhere — steer with prompting + Structured Outputs).
- **Reasoning summaries.** Get a summary of the chain of thought via `reasoning.summary` (`auto` / `detailed`; the GPT-5 series does **not** support `concise`). Summaries aren't guaranteed every turn. **Do not try to extract raw reasoning by other means** — it violates the Acceptable Use Policy and can trigger throttling/suspension.
- **Foundry-exposed features.** `preamble` objects (the model's pre-tool-call plan — encourage via `instructions`), `allowed tools` (list several under `tool_choice`), the `custom`/`lark_tool` grammar tools, and per-deployment **content filters** (configured in the Azure portal, not the prompt) all live here.

## Migration to GPT-5.5: "stop doing" list

When moving from GPT-5.4 (or older), start from a fresh baseline and remove:
- **The current date** — the model knows the UTC date; only inject explicit dates for business-specific timezones or policies.
- **Detailed process steps** — unless the exact path matters for the product.
- **Hand-written output schemas** — use Structured Outputs instead.
- **"THOROUGH / maximize context" prodding** — GPT-5.x is already introspective; this language causes over-tool-use. Use soft language on context gathering.
- **The assumption that higher reasoning effort is better** — verify with evals.

Watch the **`reasoning.effort` default trap** when the target is GPT-5.4 (or Mini/Nano): those default to `none`, so a prompt that relied on implicit medium-effort reasoning on an older model will silently run with reasoning off. Pin the effort explicitly. (`minimal` is also gone on 5.1+ — if an old config used it, move to `none` or `low`.)

Migration order: switch the model slug → pin `reasoning.effort` → re-run evals → trim now-redundant instructions → only then add new guidance. Benchmark accuracy, token consumption, and end-to-end latency together.
