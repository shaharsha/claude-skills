# Gemini (Google) — Provider Deep-Dive

Applies to the **Gemini model family** wherever it runs: the Gemini API (Google AI Studio) and Vertex AI. The platform does not change prompt engineering — the model version does.

**Current models (July 2026):** the Gemini 3.x line leads — there is **no Gemini 4** (the I/O 2026 flagship was Gemini 3.5; "Gemma 4" is the separate open-weights model, not Gemini).

- **Gemini 3.6 Flash** (`gemini-3.6-flash`, ~July 21 2026) — the current stable Flash flagship: "balances speed with intelligence" for agentic/multimodal work. Supersedes 3.5 Flash as the go-to Flash. Pricing (ai.google.dev/gemini-api/docs/pricing): **$1.50 / 1M input, $7.50 / 1M output (thinking tokens billed at the output rate)**.
- **Gemini 3.5 Flash-Lite** (`gemini-3.5-flash-lite`, ~July 21 2026) — the current stable cheapest / fastest tier for high-throughput classification, routing, extraction. Supersedes 3.1 Flash-Lite. Default `thinking_level` `minimal` (supports the full `minimal`/`low`/`medium`/`high` knob — raise it for a cheap accuracy boost when a terse/ambiguous input needs domain reasoning; it stays cheap because the classifier is usually low-volume). Pricing: **$0.30 / 1M input, $2.50 / 1M output (incl. thinking)**.
- **Gemini 3.5 Flash** (`gemini-3.5-flash`, GA May 19 2026) — prior-gen Flash, still in the API. Default `thinking_level` `medium`.
- **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`, Feb 19 2026) — the current GA Pro-tier reasoning model (default `thinking_level` `high`; a `gemini-3.1-pro-preview-customtools` variant prioritizes custom tools).
- **Gemini 3.1 Deep Think** — a max-reasoning tier aimed at the hardest science / research / engineering problems.
- **Gemini 3.1 Flash-Lite** (`gemini-3.1-flash-lite`) — prior-gen cheapest tier (superseded by 3.5 Flash-Lite), still in the API; **supports `thinking_level`** (default `minimal`).

Current models share a **~1M-token input window, ~64–65k max output, and a January 2025 knowledge cutoff** (verify the exact cutoff per model — official docs list Jan 2025 for the 3.x line). Gemini 3 Flash (`gemini-3-flash-preview`) and Gemini 2.5 remain in the API; **Gemini 2.0 shut down June 1 2026** and `gemini-3-pro-preview` was retired March 9 2026 (redirects to `gemini-3.1-pro-preview`). **Gemini 3.5 Pro is NOT yet available** — as of mid-July 2026 it has missed multiple launch targets, and rumored specs (e.g. a 2M context, a "Deep Think Reasoning Layer") are `[unverified]`; treat it as *coming*, not shippable, and don't build against it until Google publishes a model card. Gemini 3.x models respond best to prompts that are direct, well-structured, and explicit about the task and constraints.

## Contents
- System instructions and placement
- Sampling parameters (don't set them)
- Thinking level
- Thought preservation and signatures
- Stateful mode (Interactions API)
- Few-shot examples
- Completion priming
- Verbosity
- Grounding and built-in tools
- Function calling
- Tool-use control and error recovery
- Structured output
- Caching
- Long context
- Non-English output
- Temporal grounding
- Multimodal
- Flash tier and inference tiers (Flex / Priority)
- Migration to Gemini 3.5

## System instructions and placement

Use `system_instruction` for role, behavioral rules, and format requirements. Gemini has a **recency bias** — put the most critical constraints **last**, and for large inputs put long context first and the actual query at the end, bridged with a phrase like "Based on the above...". Use one structural convention consistently (XML tags or markdown headings — don't mix).

## Sampling parameters (don't set them)

For Gemini 3.x, **do not set `temperature`, `top_p`, or `top_k`** — Google strongly recommends leaving them at the default (`temperature` = 1.0). The models are optimized for default sampling; specifically, **setting `temperature` below 1.0 risks looping or degraded performance**, especially on math and complex reasoning. For determinism, use explicit rules in the system instruction and structured outputs (see *Structured output* below), not sampling tweaks. (On older Gemini 2.5 a default of 1.0 was the guidance; on 3.x, omit the parameters entirely.)

## Thinking level

Gemini 3.x uses `thinking_level` (`minimal` / `low` / `medium` / `high`), replacing the older numeric `thinking_budget`. **The default differs by model: Gemini 3.1 Pro defaults to `high`; Gemini 3.5 Flash defaults to `medium`** (lowered from `high` in the 3 Flash preview for cost/latency); Gemini 3.1 Flash-Lite supports the same enum. Per-level intent:

- `minimal` — response speed; chat, quick factual answers, simple tool calls. (Note: `minimal` *does not guarantee thinking is off*.)
- `low` — low-latency agentic tasks with fewer steps; high-throughput.
- `medium` — best quality for most code and agentic use cases.
- `high` — hard reasoning, math, and the most difficult code or agent tasks.

Start at the model's default; drop a level for faster/cheaper responses; escalate only for genuinely hard work. If an older prompt used chain-of-thought text to force reasoning, delete that scaffolding and raise `thinking_level` with a simpler prompt instead. **Do not send both `thinking_level` and the legacy `thinking_budget` in one request — it returns a 400 error.**

**Cost:** thinking tokens are billed **at the output-token rate** (Google's pricing table lists a single "output price including thinking tokens"), so raising the level raises the bill — often more than switching model does. That's fine for **low-volume** calls (a twice-weekly discovery classifier over a few dozen candidates: MEDIUM vs LOW is a fraction of a cent), but on a **high-throughput** path (per-request classification at scale) keep it `minimal`/`low` and recover accuracy via the prompt/examples first. The knob is per-request, so run the same model `minimal` for the hot path and `medium`/`high` for the occasional hard call.

## Thought preservation and signatures

On Gemini 3.5, **thought preservation is on by default** — the model carries intermediate reasoning across multi-turn conversations automatically, which improves iterative tasks (debugging, refactoring) but can increase token usage. The official SDKs handle this for you; **manual REST users must round-trip thought signatures**, or the reasoning chain breaks. The rules:

- **Single function call** → return the `thoughtSignature` inside its original `Part`.
- **Parallel calls** → only the **first** `functionCall` carries a signature; return the response parts in the **exact order received**.
- **Sequential / compositional calls** → return **all** accumulated signatures from the history.
- **Image generation/editing** → signatures are strictly validated (guaranteed on the first part and every subsequent `inlineData` part).
- **Injected or non-Gemini-generated calls** (e.g. you synthesize a tool call) → pass a **dummy signature string** so validation passes.

Also pass the matching per-call `id` back in each `functionResponse` (see *Function calling*).

## Stateful mode (Interactions API)

The signature round-tripping above is the **stateless** path (you resend the `thought` blocks yourself). Gemini now offers a **stateful** alternative — the **Interactions API** with `store: true` + `previous_interaction_id`: the server manages thoughts and signatures across turns, so you don't resend them. The official SDKs also auto-handle signatures for ordinary function calling. Use stateful mode to avoid manual signature bookkeeping; keep to the stateless round-trip rules when you manage history yourself or work over raw REST.

## Few-shot examples

Few-shot examples are **critical** on Gemini — "prompts without few-shot examples are likely to be less effective." Include several diverse input/output examples with clear `INPUT:` / `OUTPUT:` labels. Keep formatting, spacing, tags, and delimiters identical across every example — inconsistency confuses the model. Use enough examples to establish the pattern but not so many that responses overfit to the samples.

## Completion priming

Gemini responds more reliably to **completion priming** than to described format preferences — start the response (an outline's first line, the opening of a JSON structure) and let the model continue the pattern, rather than only describing the desired shape.

## Verbosity

Gemini 3.x defaults to **terse, efficient answers**. If you want a detailed or conversational response, request it explicitly in the instructions — the model will not elaborate on its own.

## Grounding and built-in tools

Gemini has native **Google Search grounding** — the exclusive anti-hallucination tool, connecting the model to real-time verified information. The built-in tool set has grown to **Google Search, Maps grounding, File Search, Code Execution, and URL Context**, and Gemini 3 can combine any of them with custom function calling **in a single request** (shipped March 2026). Enable Search for current or obscure facts and Code Execution for calculations.

## Function calling

- Gemini 3 generates a **unique `id` per function call** — each function response must include that matching `id`, a matching `name`, and exactly one response per call.
- **Function responses can carry multimodal content** (images, audio) — place it **inside** the function-response parts, not alongside them.
- Append extra runtime guidance to the function-response text (separated by two newlines), not as a separate part.
- **Calling modes** (`function_calling_config.mode`): `AUTO` (default when only declarations are set — model chooses text or a call), `VALIDATED` (default when built-in tools are combined with custom functions; constrains output to the schema), `ANY` (force a function call every turn), `NONE` (disable calls). Use `ANY` when a call is mandatory, `NONE` to suppress.
- Keep the active tool set to **10-20** declarations; beyond that, selection accuracy drops (curate or load dynamically). Only a **subset of OpenAPI schema** is supported, and very large or deeply nested schemas may be rejected (especially under `ANY`/`VALIDATED`).
- Check `finishReason` to catch turns where the model failed to produce a valid call, and don't repeat a failed call with identical arguments (see below).

## Tool-use control and error recovery

If the model overuses tools, first lower `thinking_level`, then add a system instruction constraining the usage budget — concretely, something like **"You have a limited action budget of N tool calls."** Gemini benefits from an explicit error-recovery rule: **"Don't repeat a failed call with identical arguments"** — change the query, parameters, or approach on retry.

## Structured output

Prefer the structured-output feature over describing a JSON schema in prose. On current models, set `response_format` with `text.mimeType: "application/json"` and `text.schema` holding a JSON Schema (the older `responseSchema` / `responseMimeType` fields are being superseded — confirm the exact field names for your SDK version). Guidance:

- Use specific types (`integer`, `string`, `boolean`) and put fixed value sets in an `enum` — ideal for classification/routing.
- Put per-field instructions in the schema's `description` fields, and still state the task plainly in the prompt.
- `propertyOrdering` is a **Gemini-2.0-only** requirement; 2.5/3.x don't need it.
- The API may reject very large or deeply nested schemas; unsupported JSON-Schema keywords are ignored. **Always validate the output in your own code** before using it.

## Caching

**Implicit caching is on by default for Gemini 2.5 and newer** — no setup needed; check `usage_metadata` for cached-token counts. To raise the implicit hit rate, put large, common content (system instruction, tool defs, shared context) at the **start** of the prompt and send same-prefix requests close together in time. **Explicit caching** (cache once, reference by handle) gives guaranteed savings at scale; minimum cacheable input differs by model — **Gemini 3.5 Flash: 1,024 tokens; Gemini 3 Pro: 4,096 tokens** — and the cache **TTL defaults to 1 hour** (configurable). Cache when a substantial fixed context is referenced repeatedly by shorter requests (system-heavy chatbots, repeated document/video queries).

## Long context

The 1M-token window makes "put everything in context" viable, but mind recall: single-needle retrieval is ~**99%** accurate, while **multi-needle recall degrades** — when you need several distinct facts pulled reliably, prefer **separate, targeted requests** over one mega-prompt. Put the query **last**, after the context. Longer inputs raise time-to-first-token, so when the same large context is reused, pair long context with caching rather than resending it.

## Non-English output

Gemini needs **aggressive** language enforcement to hold a non-English output language — a mild instruction drifts. Use emphatic, explicit wording: "RESPOND IN {LANGUAGE}. YOU MUST RESPOND UNMISTAKABLY IN {LANGUAGE}."

## Temporal grounding

Gemini 3.x models have a **knowledge cutoff of January 2025** — for anything more recent, enable Search grounding. For time-sensitive tasks, also anchor the date explicitly: "Remember it is {YEAR} this year." Gemini benefits from being told the current date even though it can ground via Search.

## Multimodal

Treat text, images, audio, and video as equal-class inputs and reference each clearly in the instruction with explicit labels.

**File / instruction ordering.** For a prompt with a **single image or video, place the file before the text prompt** — it tends to perform better. For multi-file prompts that interleave images and text, use the most natural ordering. (As elsewhere, with a large file + a question, put the question last.)

**`media_resolution`** trades fidelity against token cost; defaults are per-type:

| Input | Recommended | Tokens |
|-------|-------------|--------|
| Images | `media_resolution_high` (default) | 1120 |
| PDFs / documents | `media_resolution_medium` — quality saturates at medium | 560 |
| Video (general: action/description) | `media_resolution_low`/`medium` | 70 / frame |
| Video with dense text (OCR, small details) | `media_resolution_high` | 280 / frame |

**Multimodal troubleshooting.** If the model misses relevant details, hint *which* aspects of the image to draw from. If output is too generic or you can't tell comprehension from reasoning failure, ask it to **describe the image first**, then answer. To curb fabrication, ask for **shorter descriptions** — *the legacy "lower the temperature" tip is superseded on 3.x; keep temperature at the default 1.0.*

Image segmentation is unsupported on Gemini 3.x (use Gemini 2.5 Flash or Robotics-ER). **Computer Use now runs on Gemini 3.5 Flash** (public preview, June 24 2026) with simplified intent-based actions across browser / mobile / desktop, and it's integrated — no separate model needed.

## Flash tier and inference tiers (Flex / Priority)

Gemini 3.5 Flash / 3 Flash / 3.1 Flash-Lite are the budget tier — excellent for classification, routing, translation, and high-volume multimodal batch work; Flash-Lite is the best value for high-volume bounded tasks. Note that **Gemini 3.1 Flash-Lite now supports `thinking_level`**, so it's no longer a strictly no-thinking model — raise its level for a cheap accuracy boost on tasks that benefit from a little reasoning, keep it low/minimal for raw throughput. Give Flash-tier models more explicit instructions and more (simpler) few-shot examples than you would a Pro model, and keep the tool set small and clearly bounded.

Beyond model choice, Gemini exposes **Flex and Priority inference tiers** (added April 1 2026) as a separate cost/latency lever: **Flex** trades latency for lower cost on batch-tolerant work; **Priority** buys faster, steadier latency at a premium. Pick the tier to match the workload's latency sensitivity, independent of which model you run.

## Migration to Gemini 3.5

- Update the model ID to `gemini-3.5-flash` (or the relevant 3.x model).
- Remove `temperature`, `top_p`, `top_k` from the request config.
- Replace `thinking_budget` (numeric) with `thinking_level` (`minimal`/`low`/`medium`/`high`). `thinking_budget` is kept only for backward compat — and **don't send both in one request (400)**.
- Delete chain-of-thought scaffolding that forced reasoning — use `thinking_level` instead.
- Expect thought preservation on by default; ensure thought signatures round-trip with function results (or use the stateful **Interactions API** to have the server manage them).
- If moving a no-thinking Flash-Lite workload up to `gemini-3.1-flash-lite`, you can now set `thinking_level` on it — start `minimal`/`low` and raise only where accuracy needs it.
- **Pin explicit model IDs, not `-latest` aliases** — alias targets shift and `gemini-3-pro-preview` was already retired (→ `gemini-3.1-pro-preview`).
- Re-test: Gemini 3.x is terser and more direct — prompts written for a chattier older model may need an explicit elaboration request.
