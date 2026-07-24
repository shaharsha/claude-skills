# GPT (OpenAI) — Provider Deep-Dive

Applies to the **GPT model family** wherever it runs: the OpenAI API, Azure OpenAI / Microsoft Foundry, and now AWS Bedrock. The platform does not change prompt engineering — the model version does — but Azure/Foundry has real API and deployment differences worth knowing (see *Azure Foundry and AWS Bedrock* below).

**Current models (July 2026):** **GPT-5.6** is the current frontier generation (GA July 9 2026), and it introduces a **new naming scheme — the number is the generation, and Sol / Terra / Luna are durable capability tiers** that can each advance on their own cadence (this replaces the old numeric-suffix + Mini/Nano scheme *for the frontier family*):

- **GPT-5.6 Sol** (`gpt-5.6-sol`; the bare `gpt-5.6` alias routes to Sol) — flagship, for the hardest problems (complex coding, security research); the highest-capability tier and the highest ceiling for `max` effort and `pro` mode — though both are now settable on **all three tiers** via the API (see *Reasoning effort* / *Reasoning mode*). $5 / $30 per 1M (cached input $0.50). Knowledge cutoff Feb 16 2026.
- **GPT-5.6 Terra** (`gpt-5.6-terra`) — balanced everyday-business tier (support, internal tools, document analysis); ≈ GPT-5.5 quality at ~2× cheaper. $2.50 / $15.
- **GPT-5.6 Luna** (`gpt-5.6-luna`) — fast, low-cost tier for summarization, drafting, routine automation. $1 / $6. Note this is a budget *frontier* tier, **not** a nano replacement.

There is **no `gpt-5.6-mini` or `gpt-5.6-nano`** — the genuinely small models remain **`gpt-5.4-mini`** ($0.75 / $4.50, 400K ctx) and **`gpt-5.4-nano`** ($0.20 / $1.25), still current for coding, classification, extraction, ranking, and subagents. GPT-5.5 (`gpt-5.5`) / 5.4 (`gpt-5.4`) are the previous frontier tiers. Frontier context ≈1.05M tokens (≈922K input / 128K output; input above ~272K is billed at 2× input / 1.5× output for the session — chunk or cache rather than stuffing). GPT-5.6's default style is efficient and task-oriented, reaching strong results with **fewer reasoning tokens** — and it's **more concise by default than GPT-5.5** (see *Verbosity*). Mind the per-model reasoning-effort default (see *Reasoning effort*). Treat each new generation as a family to re-tune for, not a drop-in swap.

## Contents
- Roles and instruction hierarchy
- Outcome-first prompting
- Reasoning effort
- Reasoning mode (standard / pro) and multi-agent
- Verbosity
- Structured outputs
- Tool use and agentic patterns
- Programmatic tool calling
- Agentic eagerness control
- Self-reflection rubrics
- Caching and the Responses API
- Personality and collaboration style
- Small models (Mini / Nano)
- Images
- Azure Foundry and AWS Bedrock
- Migration: "stop doing" list

## Roles and instruction hierarchy

GPT exposes a `developer` role that is **prioritized over `user`**. Security-sensitive and behavior-defining instructions go in the developer message. The hierarchy is system/developer > user > tool output — treat tool results and retrieved documents as untrusted data, not instructions. Newer instructions supersede earlier conflicting ones; in long conversations reappend key instructions every 3-5 messages.

GPT-5 follows instructions with surgical precision, which makes **contradictions actively harmful** — the model burns reasoning tokens trying to reconcile them instead of ignoring them. Audit prompts for conflicts ("after informing the patient..." vs. "without contacting the patient...") and add clarifying clauses for genuine exceptions ("do not look up in the emergency case — proceed immediately").

## Outcome-first prompting

GPT-5.5 is strongest when the prompt defines the **target outcome** and lets the model choose the path. Specify: expected outcome, success criteria, allowed side effects, evidence/citation rules, output shape, and stopping conditions. Avoid step-by-step process instructions unless the exact path is product-critical — process-heavy prompt stacks from older models over-specify what GPT-5.5 handles natively and can hurt quality. GPT-5.6 goes further — it infers the user's underlying goal and intended level of work from context, so prescribe even less; still supply domain context, hard constraints, approval boundaries, and success criteria, and **say explicitly when an important ambiguity should make the model stop and ask** rather than assume (it won't ask on its own unless told to).

Prefer **decision rules over absolutes** for judgment calls. Replace ALWAYS/NEVER with "if X, do Y; otherwise Z." Reserve hard rules for policy and safety, which remain binding regardless of user instructions.

## Reasoning effort

`reasoning.effort`: `none` / `low` / `medium` / `high` / `xhigh` / `max`. GPT-5.6 **adds `max`** at the top of the ladder — the deepest reasoning tier, and it's settable on **all three tiers** (Sol/Terra/Luna); Sol just has the highest ceiling. **The default is per-model:** GPT-5.5 defaults to `medium`; GPT-5.4 (and its Mini/Nano) default to **`none`** — pin effort explicitly on 5.4 or it runs with reasoning off. **GPT-5.6 defaults to `medium` in both standard and `pro` mode** (confirmed in OpenAI's model guidance). (`minimal` existed only on the original GPT-5 models and is **not** on 5.1+; the floor on 5.4/5.5/5.6 is `none`.)

- `none` — latency-critical tasks with no reasoning need (lightweight classification, voice turns).
- `low` — efficient reasoning when planning/tool use still matters but speed counts.
- `medium` — the recommended starting point for quality/latency balance (GPT-5.5's default).
- `high` / `xhigh` — raise only when evals show a measurable quality gain worth the latency.
- `max` (Sol) — the deepest reasoning tier for the hardest problems; expect the highest latency/cost, and verify the gain with evals before making it a default.

Reasoning effort is a **last-mile knob, not a primary quality lever**. Higher is not automatically better — it can cause overthinking when instructions conflict or stopping criteria are weak. Before raising effort, add completeness contracts, verification loops, and tool-use persistence rules. For execution-heavy work (workflow, extraction, triage) start low; for research/synthesis/review start at medium+. On migration, OpenAI recommends testing **one effort level lower** than you used on GPT-5.5 — 5.6 often matches quality with less reasoning.

## Reasoning mode (standard / pro) and multi-agent

GPT-5.6 adds `reasoning.mode` = `"standard"` | `"pro"` as an axis **separate from** `reasoning.effort`: mode selects standard vs. pro execution, while effort controls how much reasoning happens *within* that mode. `pro` does more model work (higher cost, higher ceiling) and is **settable on any tier** via `reasoning.mode` — no separate `-pro` model slug needed; ChatGPT surfaces it as "Sol Pro," but on the API it applies to Sol, Terra, or Luna alike. If you omit effort in `pro` mode it defaults to `medium`. `pro` bills at the same per-token rate as standard mode but typically consumes more tokens, so use it only when evals show the hardest tasks need it — it isn't a free quality bump. Keep your normal outcome-focused prompt in `pro` mode — OpenAI's guidance is explicit that you do **not** need to add "think harder" or ask for several candidate answers; the mode handles the extra work.

Above pro sits a **multi-agent** capability: in ChatGPT it's exposed as `ultra` (runs ~4 agents in parallel — e.g. Terminal-Bench 2.1 88.8% → 91.9%); the API equivalent is the **multi-agent beta in the Responses API**, where one GPT-5.6 instance coordinates parallel subagents and synthesizes their results. Reserve it for genuinely decomposable, high-value work — it multiplies token cost.

## Verbosity

`text.verbosity` (`low` / `medium` / `high`) controls final-answer length independently of reasoning depth. Default is `medium`; `low` is often the better starting point for concise responses and produces proportionally shorter output than GPT-5.4. Set it globally and override in natural language for specific contexts (e.g. high verbosity for code, low elsewhere). Treat answer length as separate from reasoning quality — specify word budgets when needed.

**GPT-5.6 is more concise by default than 5.5.** On migration, **re-check broad brevity instructions** ("Be concise," "Keep it short") — they may now be redundant or actively over-clip the answer. Remove them and see whether the model's default length is already right before adding length controls back.

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

## Programmatic tool calling

GPT-5.6 adds **programmatic tool calling** — instead of the model emitting one tool call per turn and waiting for each result, you add a `programmatic_tool_calling` tool and opt eligible tools in via **`allowed_callers`**; the model then writes a lightweight **program (JavaScript in an isolated V8 runtime, no network access)** that orchestrates those tools, loops, and filters/aggregates intermediate results, returning only the distilled output. This cuts tool-call round-trips and keeps large intermediate payloads out of context (OpenAI-cited 38–63.5% token reductions). You handle the `program` and `program_output` items in the Responses API. Reach for it on multi-step / batch / filter-heavy tool work (fan out across many records, return only the matches); prefer plain tool calls for simple, transparent steps where you want to reason over each result. When both routes are available, **make the routing task-specific** — name the bounded stage, the eligible tools, the output schema, the retry limit, and the stop condition; OpenAI's guidance warns that a generic "use programmatic tool calling efficiently" won't produce the right route. It's ZDR-compatible with no extra container cost. (This is OpenAI's counterpart to the "expose tools as a code API" pattern in SKILL.md Section B.)

## Agentic eagerness control

Steer the agent's exploration depth in **both** directions:

- **Reduce eagerness** (over-exploring, too many tool calls): lower `reasoning.effort`; set an explicit tool-call budget ("use at most 2 tool calls before answering"); define clear exploration criteria; give an escape hatch ("if you can't fully verify, proceed with your best answer and note the assumption").
- **Increase eagerness** (stops too early): persistence prompts ("keep going until the query is completely resolved; do not hand back a partial result"); instruct the model to deduce a reasonable approach rather than ask for clarification, documenting assumptions for the user afterward.
- **Don't over-repeat the approval policy** — state the autonomy rule once (safe local actions proceed; external/destructive/costly/scope-expanding actions need confirmation). OpenAI's own guidance warns that repeating "ask first" / "wait for approval" / "do not mutate" across the prompt makes GPT-5.6 pause for confirmation on safe, expected actions.

## Self-reflection rubrics

For high-quality, open-ended generation (zero-to-one app builds, design tasks), have the model construct an internal **5-7 category excellence rubric** for the task, keep it private, iterate its solution against it, and not finish until the work would score top marks in every category. This reliably lifts quality on subjective generation tasks.

## Caching and the Responses API

Use the **Responses API** for any reasoning, tool-calling, or multi-turn use case. For multi-turn, pass `previous_response_id` — it carries prior reasoning forward so the model doesn't reconstruct plans after each tool call (measurable benchmark gains, e.g. Tau-Bench Retail 73.9% → 78.2%). To render prior reasoning explicitly, set `reasoning.context: "all_turns"`. When manually managing Responses state, preserve the `phase` value on returned assistant items; with `store:false`, replay the full history **including reasoning items' `encrypted_content`** (keep every output item, including encrypted reasoning) or the model loses its chain across turns.

Caching is prefix-based and automatic (≥1024 tokens): keep stable content (system/developer prompt, tools, examples) at the start, dynamic/user content at the end, set a consistent `prompt_cache_key`, and monitor `usage.prompt_tokens_details.cached_tokens`. **GPT-5.6 made caching more predictable and adds explicit control:** set `prompt_cache_options.mode: "explicit"` to mark exactly which prefixes to cache (explicit cache breakpoints), and `prompt_cache_options.ttl` for retention (the old `prompt_cache_retention` param is renamed — update it on migration). Minimum cache life is now **30 minutes**. **Cache writes are billed at 1.25× the uncached input rate**; cache reads keep the ~90% discount (Sol cached input = $0.50 vs $5).

## Personality and collaboration style

Define these as **two separate, concise blocks** rather than one bundled instruction:
- **Personality** — persistent tone, warmth, directness, formality, humor, polish level.
- **Collaboration style** — when to ask vs. assume, how proactive to be, how to handle uncertainty and risk.

For customer-facing work, also specify the channel (Slack, email, memo, PRD), emotional register, and hard length limits.

## Small models (GPT-5.4 Mini / Nano)

The small tier stayed on the 5.4 generation — `gpt-5.4-mini` and `gpt-5.4-nano` are **still current** (there is no 5.6 mini/nano). For a cheap *frontier*-family option instead, reach for **Luna** (`gpt-5.6-luna`) — a budget frontier tier, distinct from the nano small model. Mini and Nano are more literal and make fewer assumptions. Adjust:
- Put the most critical rules first.
- Specify the full execution order for tool use and side effects — don't assume the model infers it.
- Use structural scaffolding: numbered steps, explicit decision rules.
- Separate "do the work" from "report the result" as distinct instructions.
- Show the correct flow with an example; define ambiguity behavior explicitly.
- Specify packaging directly (length, follow-up behavior, citation style).
- Don't rely on a bare "MUST" — weaker models need the structure, not the emphasis.

## Images

Image `detail`: `auto`/unset now behaves as `original` (preserves detail up to ~10.24M pixels / 6000px). Use `high` for standard vision (up to ~2.5M pixels / 2048px); `low` for aggressive downscaling when speed/cost dominate. For spatially sensitive or computer-use tasks, prefer `original`; don't rely on `auto` in production agents where precision matters.

## Safeguards and runtime safety classifiers

GPT-5.6 runs **real-time cyber- and bio-misuse classifiers over the output as it streams**, so two behaviors surface at runtime that older models didn't: some requests are refused/blocked mid-completion, and others **pause for several seconds mid-stream** while a classifier synchronously reviews the partial output (a latency spike, not a hang). These can fire on **legitimate dual-use work** — code review, vulnerability research, patch development, security education, defensive testing — where offensive and defensive activity look alike early on. Two mitigations: (1) if you serve individual end users, send a stable, privacy-preserving **`safety_identifier`** on every request so enforcement scopes to bad actors instead of your whole app; (2) handle refusals and truncated/partial completions gracefully rather than assuming a clean finish, and frame genuinely defensive tasks explicitly as such. (This is GPT's analogue to Claude's `stop_details`/refusal handling — build for it in the harness, not just the prompt.)

## Frontend and design

GPT-5.6 has notably stronger design judgment than 5.5 — with only high-level direction it produces tasteful, functional interfaces, and its improved computer use lets it inspect and refine the **rendered** result (catching visual/functional issues), not just emit code. It also infers and follows an existing **design system or reference template** — layouts, typography, spacing, tokens, even PowerPoint Slide Master rules — faithfully. Prompt accordingly: give the design system/tokens plus high-level intent and let it self-refine, rather than piling on the anti-"AI-slop" scaffolding older GPT models needed. (Contrast Claude, whose frontend default has a persistent house style to steer away from — see `claude.md`.)

## Azure Foundry and AWS Bedrock

**GPT is no longer OpenAI/Azure-exclusive:** AWS Bedrock now serves the GPT-5 family (GA 2026-04-28, after the OpenAI–Microsoft exclusivity clause was dropped), so the same model can run on the OpenAI API, Azure, or Bedrock. As always, prompt engineering follows the **model version, not the platform** — on Bedrock, GPT is reached through the OpenAI-compatible endpoint (check the Bedrock docs for exact model IDs). The rest of this section covers **Azure OpenAI / Microsoft Foundry** specifics: prompting is identical to the OpenAI API — same model, same `reasoning.effort` / `text.verbosity` / Structured Outputs behavior — but the API surface and a few defaults differ. What to know when the deployment is Azure:

- **Endpoint & model name.** Call `https://YOUR-RESOURCE.openai.azure.com/openai/v1/` and pass your **deployment name** as `model` (not the bare model slug). Auth is API key or Microsoft Entra ID (bearer token). GPT-5.5, 5.4, 5.4-mini, 5.4-nano are all available; GPT-5.5 may need a Tier-5/6 quota request.
- **Roles.** The `developer` role is functionally equivalent to `system` on Azure reasoning models, and the latest models also accept `system` for easier migration — but **do not send both a developer and a system message in the same request.**
- **Token limit parameter.** Reasoning models use **`max_completion_tokens`** on the Chat Completions API and **`max_output_tokens`** on the Responses API. `max_tokens` is **not** supported. Always set `reasoning.effort` explicitly — omitting it can sharply increase latency on complex prompts.
- **Unsupported sampling knobs.** `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`, `logprobs`, `top_logprobs`, `logit_bias` are all **unsupported on reasoning models** (the same omit-sampling discipline as elsewhere — steer with prompting + Structured Outputs).
- **Reasoning summaries.** Get a summary of the chain of thought via `reasoning.summary` (`auto` / `detailed`; the GPT-5 series does **not** support `concise`). Summaries aren't guaranteed every turn. **Do not try to extract raw reasoning by other means** — it violates the Acceptable Use Policy and can trigger throttling/suspension.
- **Foundry-exposed features.** `preamble` objects (the model's pre-tool-call plan — encourage via `instructions`), `allowed tools` (list several under `tool_choice`), the `custom`/`lark_tool` grammar tools, and per-deployment **content filters** (configured in the Azure portal, not the prompt) all live here.

## Migration to GPT-5.6: "stop doing" list

When moving from GPT-5.5 / 5.4 (or older), start from a fresh baseline and remove:
- **The current date** — the model knows the UTC date; only inject explicit dates for business-specific timezones or policies.
- **Detailed process steps** — unless the exact path matters for the product.
- **Hand-written output schemas** — use Structured Outputs instead.
- **"THOROUGH / maximize context" prodding** — GPT-5.x is already introspective; this language causes over-tool-use. Use soft language on context gathering.
- **The assumption that higher reasoning effort is better** — verify with evals, and test **one effort level lower** than you ran on 5.5 (5.6 often matches quality with less reasoning).
- **Repeated instructions and redundant examples** — 5.6 follows a single clear statement; repetition wastes tokens and can conflict. (OpenAI's own evals: stripping repeated instructions from the system prompt lifted eval scores ~10–15% while cutting tokens 41–66% and cost 33–67% — leaner prompts measurably win on 5.6.)
- **Over-detailed tool descriptions** — simplify; 5.6's tool use is more precise, so hand-holding written for weaker models can hurt.
- **Broad brevity lines** ("Be concise") — 5.6 is already terser than 5.5; re-check before keeping them (see *Verbosity*).
- **The old cache param** — rename `prompt_cache_retention` → `prompt_cache_options.ttl` (see *Caching*), and if you replay Responses state with `store:false`, make sure you resend every prior output item including encrypted reasoning.

Watch the **`reasoning.effort` default trap** when the target is GPT-5.4 (or Mini/Nano): those default to `none`, so a prompt that relied on implicit medium-effort reasoning on an older model will silently run with reasoning off. Pin the effort explicitly. (`minimal` is also gone on 5.1+ — if an old config used it, move to `none` or `low`.)

Migration order: switch the model slug → pin `reasoning.effort` → re-run evals → trim now-redundant instructions → only then add new guidance. Benchmark accuracy, token consumption, and end-to-end latency together.
