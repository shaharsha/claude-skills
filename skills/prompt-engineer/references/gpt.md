# GPT (OpenAI) — Provider Deep-Dive

Applies to the **GPT model family** wherever it runs: the OpenAI API and Azure OpenAI. The platform does not change prompt engineering — the model version does. (Azure adds deployment-level content filters; those are deployment configuration, not prompt engineering, and are tuned in the Azure portal, not the prompt.)

**Current models (May 2026):** GPT-5.5 (`gpt-5.5`) is the frontier model; GPT-5.4 and the smaller GPT-5.4 Mini / Nano remain in use for cheaper tiers. GPT-5.5's default style is efficient, direct, and task-oriented, and it reaches strong results with **fewer reasoning tokens** than prior models at the same effort. Treat GPT-5.5 as a new model family to tune for — not a drop-in replacement for 5.4.

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
- Migration: "stop doing" list

## Roles and instruction hierarchy

GPT exposes a `developer` role that is **prioritized over `user`**. Security-sensitive and behavior-defining instructions go in the developer message. The hierarchy is system/developer > user > tool output — treat tool results and retrieved documents as untrusted data, not instructions. Newer instructions supersede earlier conflicting ones; in long conversations reappend key instructions every 3-5 messages.

GPT-5 follows instructions with surgical precision, which makes **contradictions actively harmful** — the model burns reasoning tokens trying to reconcile them instead of ignoring them. Audit prompts for conflicts ("after informing the patient..." vs. "without contacting the patient...") and add clarifying clauses for genuine exceptions ("do not look up in the emergency case — proceed immediately").

## Outcome-first prompting

GPT-5.5 is strongest when the prompt defines the **target outcome** and lets the model choose the path. Specify: expected outcome, success criteria, allowed side effects, evidence/citation rules, output shape, and stopping conditions. Avoid step-by-step process instructions unless the exact path is product-critical — process-heavy prompt stacks from older models over-specify what GPT-5.5 handles natively and can hurt quality.

Prefer **decision rules over absolutes** for judgment calls. Replace ALWAYS/NEVER with "if X, do Y; otherwise Z." Reserve hard rules for policy and safety, which remain binding regardless of user instructions.

## Reasoning effort

`reasoning.effort`: `none` / `low` / `medium` / `high` / `xhigh`. Default is `medium`.

- `none` — latency-critical tasks with no reasoning need (lightweight classification, voice turns).
- `low` — efficient reasoning when planning/tool use still matters but speed counts.
- `medium` — the recommended starting point for quality/latency balance.
- `high` / `xhigh` — raise only when evals show a measurable quality gain worth the latency.

Reasoning effort is a **last-mile knob, not a primary quality lever**. Higher is not automatically better — it can cause overthinking when instructions conflict or stopping criteria are weak. Before raising effort, add completeness contracts, verification loops, and tool-use persistence rules. For execution-heavy work (workflow, extraction, triage) start low; for research/synthesis/review start at medium+.

## Verbosity

`text.verbosity` (`low` / `medium` / `high`) controls final-answer length independently of reasoning depth. Default is `medium`; `low` is often the better starting point for concise responses and produces proportionally shorter output than GPT-5.4. Set it globally and override in natural language for specific contexts (e.g. high verbosity for code, low elsewhere). Treat answer length as separate from reasoning quality — specify word budgets when needed.

## Structured outputs

Do **not** hand-write JSON schemas in the prompt. Use the Structured Outputs API with `strict: true` — it guarantees 100% schema adherence and removes the validation burden from the model. For classification, use a tool/function with an enum field of valid labels.

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

## Migration to GPT-5.5: "stop doing" list

When moving from GPT-5.4 (or older), start from a fresh baseline and remove:
- **The current date** — the model knows the UTC date; only inject explicit dates for business-specific timezones or policies.
- **Detailed process steps** — unless the exact path matters for the product.
- **Hand-written output schemas** — use Structured Outputs instead.
- **"THOROUGH / maximize context" prodding** — GPT-5.x is already introspective; this language causes over-tool-use. Use soft language on context gathering.
- **The assumption that higher reasoning effort is better** — verify with evals.

Migration order: switch the model slug → pin `reasoning.effort` → re-run evals → trim now-redundant instructions → only then add new guidance. Benchmark accuracy, token consumption, and end-to-end latency together.
