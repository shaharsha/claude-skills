# Gemini (Google) - Provider Deep-Dive

Applies to the **Gemini model family** wherever it runs: the Gemini API (Google AI Studio) and Vertex AI / Gemini Enterprise Agent Platform. The platform does not change prompt engineering - the model version does.

**Current models (September 2026):** Gemini ships a new **Flash every ~3 weeks** (3.6 in late July, 3.7 Aug 13, 3.8 Sept 2) - re-check this list before trusting it. There is **no Gemini 4**, and **Gemini 3.5 Pro still has not shipped** (announced at I/O in May; rumored specs stay `[unverified]` until a model card exists). Gemini 3.1 Pro is still the only Pro model, and still *preview*.

- **Gemini 3.8 Flash** (`gemini-3.8-flash`, GA Sept 2 2026) - "our most intelligent Flash model", built on 3.7 Flash for long-horizon software engineering, autonomous agents, and complex enterprise workflows; default model for Google's managed **Antigravity** agent and SDK. **`thinking_level` `low`/`medium`/`high` only - `minimal` returns an error**; default `medium`. **Uses more tokens by design** (smaller reasoning steps, iterative tool calls, self-verification) - lower the level for everyday work, or stay on 3.7 Flash. Knowledge cutoff **March 2026** (some domains still Jan 2025).
- **Gemini 3.7 Flash** (`gemini-3.7-flash`, GA Aug 13 2026) - algorithmic improvements on 3.6 Flash (not a new pretrain); same thinking rules as 3.8 (no `minimal`, default `medium`); March 2026 cutoff. Google recommends it where **compute efficiency** matters most.
- **Gemini 3.6 Flash** (`gemini-3.6-flash`, July 2026) - previous-gen Flash; keeps the full `minimal`-`high` range, default `medium`; March 2026 cutoff.
- **Gemini 3.5 Flash** (`gemini-3.5-flash`) - legacy Flash (full range, default `medium`, Jan 2025 cutoff).
- **Gemini 3.5 Flash-Lite** (`gemini-3.5-flash-lite`) - still the newest, cheapest / fastest tier ($0.30 / $2.50); default `minimal`, full range. **Gemini 3.1 Flash-Lite** is the prior Lite.
- **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`, preview) - the Pro-tier reasoning model; `low`/`medium`/`high`, default `high`; $2 / $12 (≤200k input), $4 / $18 above; Jan 2025 cutoff.
- **Gemini 3.8 Flash Cyber** - security-tuned sibling for finding and fixing vulnerabilities, restricted to governments and trusted partners through **Google Fairwind** (succeeds 3.5 Flash Cyber). Prompt it like 3.8 Flash.
- Also current: Gemini 3.8 Live / Live Extended Thinking (voice agents), 3.8 Flash TTS / Flash-Lite TTS, Nano Banana 2 / Pro (images). `gemini-3-flash-preview` and Gemini 2.5 remain; Gemini 2.0 shut down June 1 2026.

**Pricing:** 3.8, 3.7, and 3.6 Flash share an **introductory $0.75 / $3.75 per 1M** (output includes thinking tokens; context cache $0.075) **through Dec 31 2026**, rising to **$1.50 / $7.50 on Jan 1 2027** - budget for the step-up. Batch and Flex are 50%.

Current Gemini 3 models share a **~1M-token input window (1,048,576) and 64K output (65,536)**. **Cutoffs differ by model**: March 2026 for 3.6-3.8 Flash (uneven - some domains still end at Jan 2025), Jan 2025 for 3.5 Flash, 3.5 Flash-Lite, and 3.1 Pro.

## Contents
- The Interactions API (now the default surface)
- System instructions and placement
- Sampling parameters (don't set them)
- Thinking level
- Thought preservation and signatures
- Prompt design fundamentals (few-shot, completion priming, decomposition, iteration)
- Gemini 3 prompting principles and Flash clauses
- Agentic workflows: steering dimensions and system-instruction template
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
- Migration to Gemini 3.8 / 3.7 Flash

## The Interactions API (now the default surface)

Google's **Interactions API** (GA June 2026) is "the best way to build with Gemini models and agents" and where every new model, tool, and agent feature launches; the original `generateContent` API is now **legacy** but fully supported. One endpoint covers models and agents (`client.interactions.create(model=… | agent=…, input=…)`), including managed agents such as Deep Research and Antigravity (`antigravity-preview-09-2026`).

- **Stateful by default.** Pass `previous_interaction_id` to continue a conversation; the server keeps history, thoughts, and signatures, and implicit caching hits more often. **But `previous_interaction_id` preserves only history - `system_instruction`, `tools`, and `generation_config` (incl. `thinking_level`) are interaction-scoped and must be re-sent on every call.** A system instruction sent only on turn 1 is silently gone on turn 2.
- **It stores interactions by default** - 55 days on the paid tier, 1 day on free (configurable to 7/14/28/55 days in AI Studio). For sensitive data set `store=false`, which also disables `background=true` execution and `previous_interaction_id` (you then resend history yourself).
- Background execution (`background=true`) for long-running tasks (Deep Think, Deep Research); observable typed execution **steps** for debugging and UI. The SDK's `.output_text` joins only the *final* run of text blocks - text interleaved with thoughts, tool calls, or images is dropped, so iterate over `steps` for anything non-trivial. In stateless mode (`store=false`) resend the full history including every model-generated step (`thought`, `function_call`) exactly as received.
- **Limitations:** remote MCP is not yet supported on Gemini 3; when mixing models in one conversation, each later model must accept the earlier models' output modalities as input.
- The OpenAI-compatibility layer maps `reasoning_effort` to `thinking_level` automatically.

## System instructions and placement

Use `system_instruction` for role, behavioral rules, and format requirements. Google's current guidance: put essential behavioral constraints, persona, and output-format requirements **in the system instruction or at the very beginning of the user prompt**; for large inputs put **all the context first and the specific question/instruction at the very end**, bridged with a phrase like *"Based on the information above…"*. Gemini also shows a **recency bias** - critical constraints restated last are followed more reliably. Use one structural convention consistently (XML tags *or* Markdown headings - don't mix within a prompt). XML tags also mark data as data: content inside `<context>` is read as input, not instructions.

## Sampling parameters (don't set them)

For Gemini 3.x, **do not set `temperature`, `top_p`, or `top_k`** - leave `temperature` at the default 1.0. Setting it below 1.0 risks **looping or degraded performance**, especially on math and complex reasoning; the 3.8 migration checklist says to strip all three, plus `candidate_count` (unsupported on Gemini 3). For determinism, use explicit rules and structured output. (Google's general prompt-design page still carries older advice such as "increase the temperature" to escape fallback responses - that predates 3.x; ignore it.)

## Thinking level

Gemini 3.x uses `thinking_level`, replacing the numeric `thinking_budget` (still accepted for back-compat - **never send both; that's a 400**). Levels and defaults are **per model**:

| Model | Default | Supported |
|---|---|---|
| 3.8 Flash, 3.7 Flash | `medium` | `low`, `medium`, `high` (**`minimal` → error**) |
| 3.6 Flash, 3.5 Flash | `medium` | `minimal`-`high` |
| 3.5 Flash-Lite | `minimal` | `minimal`-`high` |
| 3.1 Pro (preview) | `high` | `low`, `medium`, `high` |
| 3 Flash (preview) | `high` | `minimal`-`high` |

- `minimal` - speed; chat, quick facts, simple tool calls (*does not guarantee thinking is off*).
- `low` - latency-critical work: real-time chat, drafts, fast data analysis, incident pipelines, high-throughput.
- `medium` - "best quality for most tasks"; complex code and agentic use cases.
- `high` - deep reasoning, math, the hardest multi-step tasks and tool orchestration.

Start at the model's default; drop a level for faster/cheaper; escalate only for genuinely hard work. On 3.8 Flash the default already self-verifies heavily - `low` is the lever when token use outruns the task. If an older prompt used chain-of-thought text to force reasoning, delete it and raise `thinking_level` instead (in-response plans are unnecessary - the model thinks internally; for the hardest problems Google notes a simple *"Think very hard before answering"* can help, at a thinking-token cost). For long outputs, prompting the model to think less saves tokens.

**`max_output_tokens` is a hard cutoff that includes thinking.** If the model hits it while reasoning, the interaction ends `incomplete` with truncated or empty output - and you're still billed for the thinking. To cut cost or latency, lower `thinking_level`; don't shrink `max_output_tokens`.

**Cost:** thinking tokens bill **at the output rate**, so the level moves the bill more than the model choice often does. Fine for low-volume calls; on a high-throughput path keep it low (on 3.8/3.7 Flash `low` is the floor - route truly no-reasoning traffic to Flash-Lite at `minimal`) and recover accuracy with the prompt and examples first. The knob is per-request. Thought summaries are opt-in (`thinking_summaries:"auto"`) - read them to debug failures.

## Thought preservation and signatures

Thought preservation is on by default on Gemini 3.x - the model carries intermediate reasoning across turns (better iterative work, more tokens). In **stateful** Interactions mode (`store` on + `previous_interaction_id`) the server manages thoughts and signatures entirely. In **stateless** mode (or legacy `generateContent` over REST) you must round-trip them:

- **Single function call** → return the `thoughtSignature` inside its original `Part`.
- **Parallel calls** → only the **first** `functionCall` carries a signature; return the response parts in the **exact order received**.
- **Sequential / compositional calls** → return **all** accumulated signatures.
- **Image generation/editing** → signatures strictly validated (first part and every subsequent `inlineData` part).
- **Injected or synthesized calls** → pass a **dummy signature string** so validation passes.

Always pass the matching call `id` back in each function response (see *Function calling*).

## Prompt design fundamentals (few-shot, completion priming, decomposition, iteration)

From Google's *Prompt design strategies* guide:

- **Always include few-shot examples** - "prompts without few-shot examples are likely to be less effective," and clear examples can **replace instructions** entirely. Use specific, varied examples; too many and the model overfits to them. Keep formatting identical across examples - XML tags, whitespace, newlines, and splitters.
- **Completion priming:** start the output (an outline's first line, the opening of a JSON object, an `Output:` line after examples) and let the model continue the pattern - more reliable than describing the shape. For complex JSON, use structured output instead.
- **Add context rather than assuming knowledge:** paste the relevant reference text and say "Answer the question using the text below."
- **Break complex prompts down:** one prompt per instruction (route by input), **chain** sequential steps, or **aggregate** parallel operations over parts of the data.
- **Iteration tactics when a prompt won't behave:** rephrase; switch to an **analogous task** (e.g. recast an open classification as a multiple-choice question to keep answers inside the option set); **reorder** examples / context / input and compare.
- Enable Search grounding for obscure or recent facts, and code execution for any arithmetic, counting, or calculation.

## Gemini 3 prompting principles and Flash clauses

- **Be precise and direct**; avoid persuasive or over-engineered prompting - Gemini 3 over-analyzes verbose prompt techniques written for older models.
- **Define ambiguous terms and parameters** explicitly.
- **Treat multimodal inputs as equal-class** and reference each one clearly.
- Google's evaluated **system-instruction clauses for Flash**:
  - *Current date:* *"For time-sensitive user queries that require up-to-date information, you MUST follow the provided current time (date and year) when formulating search queries in tool calls. Remember it is 2026 this year."*
  - *Knowledge cutoff:* *"Your knowledge cutoff date is [cutoff]."* - Google's page still says "January 2025"; use the actual model's cutoff (March 2026 for 3.6-3.8 Flash).
  - *Strict grounding* (for document-grounded answers): *"You are a strictly grounded assistant limited to the information provided in the User Context… If the exact answer is not explicitly written in the context, you must state that the information is not available."*
- Google's reference template pairs a `<role>`, `<instructions>` (plan → execute → validate → format), `<constraints>` (verbosity, tone), and `<output_format>` in the system instruction with `<context>` + `<task>` in the user turn. (Its closing "Remember to think step-by-step" line is optional on thinking models - `thinking_level` does that work.)

## Agentic workflows: steering dimensions and system-instruction template

Google frames agent prompting as choosing a setting on each of nine dimensions - name the ones that matter for your agent explicitly:
- **Reasoning and strategy:** logical decomposition (how thoroughly to analyze constraints and order of operations), problem diagnosis (accept the obvious cause or explore less-probable ones), information exhaustiveness (read every policy vs. move fast).
- **Execution and reliability:** adaptability (stick to the plan vs. pivot on new evidence), persistence and recovery (how hard to self-correct - more persistence, more tokens and loop risk), risk assessment (reads vs. state-changing writes).
- **Interaction and output:** ambiguity and permission handling (when to assume vs. ask), verbosity alongside tool calls, precision and completeness (every edge case vs. ballpark).

Google also publishes a **researcher-evaluated agentic system instruction** (improves results on rulebook-heavy, user-interactive agent benchmarks) - adapt rather than copy. Its core: before *any* action, plan through (1) logical dependencies and constraints, resolved in priority order (policy rules → order of operations → other prerequisites → user preferences); (2) risk assessment - for exploratory calls, missing *optional* parameters is low risk, so **prefer calling the tool over asking the user**; (3) abductive hypothesis exploration - look past the obvious cause, don't discard low-probability ones early; (4) re-plan when an observation disproves a hypothesis; (5) use every information source (tools, policies, history, the user); (6) precision - quote the exact applicable policy; (7) completeness - avoid premature conclusions; (8) intelligent persistence - retry *transient* errors up to an explicit limit, change strategy on other errors, never repeat the same failed call; (9) act only after the reasoning is complete.

## Verbosity

Gemini 3.x defaults to **terse, direct answers**. If you want detail or a conversational persona, request it explicitly ("Explain this as a friendly, talkative assistant" / "answer comprehensively unless the user asks for brevity") - the model will not elaborate on its own.

## Grounding and built-in tools

Native **Google Search grounding** connects the model to real-time information (5,000 free grounded requests/month shared across Gemini 3.x, then $14 / 1,000). Built-in tools: **Google Search, Maps grounding, File Search, Code Execution, URL Context**, and **Computer Use** (preview, built in - no separate model). Gemini 3 combines any of them with custom function calling **and with structured output** in a single request. Enable Search for current or obscure facts and Code Execution for calculations.

## Function calling

- Each function call carries a unique call id - every response must include the matching id (`call_id` in Interactions; `id` + `name` on every `FunctionResponse` in `generateContent`) and exactly one response per call.
- **Function responses can carry multimodal content** - place images/audio **inside** the function-response payload, not alongside it.
- Append extra runtime guidance to the function-response text, separated by `\n\n`, not as a separate part.
- **Calling modes** (`function_calling_config.mode`): `AUTO` (default with declarations only), `VALIDATED` (default when built-in tools are combined with custom functions; constrains output to the schema), `ANY` (force a call every turn), `NONE`.
- Keep the active tool set to **10-20** declarations; only a **subset of OpenAPI schema** is supported, and very large or deeply nested schemas may be rejected (especially under `ANY`/`VALIDATED`). Validate calls before executing.
- **Don't require structured text right before a tool call.** If the prompt demands an `<UPDATE>…</UPDATE>` block (or JSON/YAML) immediately before calling a tool, the call can fail with **`Malformed_Function_Call`**. Google's fixes, preferred first: (1) move those notes into a dedicated **`update()` function** (params like `previous_step`, `plan`, `next_step`) that the model calls before other tools; (2) have it write notes as Markdown headers (`# UPDATE`, `## PLAN`); (3) drop the pre-tool text requirement.
- Check `finishReason` / interaction status to catch turns where no valid call was produced.

## Tool-use control and error recovery

If the model overuses tools - more likely on 3.8 Flash, which calls tools iteratively by design - first lower `thinking_level`, then constrain the budget in the system instruction (*"You have a limited action budget of N tool calls."*). Gemini benefits from an explicit recovery rule: **"Don't repeat a failed call with identical arguments"** - change the query, parameters, or approach; retry transient errors only up to a stated limit.

## Structured output

Prefer the structured-output feature over describing a JSON schema in prose (JSON Schema via the response-format config - field names differ between the Interactions API and legacy `responseSchema` / `responseMimeType`, so confirm for your SDK version). Structured output now combines with built-in tools and function calling. Guidance:

- Use specific types and put fixed value sets in an `enum` - ideal for classification/routing.
- Put per-field instructions in schema `description` fields, and still state the task plainly in the prompt.
- `propertyOrdering` is a Gemini-2.0-only requirement.
- Very large or deeply nested schemas may be rejected; unsupported keywords are ignored. **Always validate the output in your own code.**

## Caching

**Implicit caching is automatic** (stateful and stateless) - no setup; cached tokens appear in `usage.total_cached_tokens`. To raise the hit rate, put large, common content (system instruction, tool defs, shared context) at the **start** and send same-prefix requests close together; continuing conversations with `previous_interaction_id` also improves implicit hits. **The minimum cacheable input is 4,096 tokens on all current 3.x models** (3.5-3.8 Flash, 3.1 Pro; 2,048 on 2.5). **Explicit caching** (cache once, reference by handle) gives guaranteed savings at scale; TTL defaults to 1 hour, with a per-hour storage charge. Cache when a large fixed context is reused by shorter requests.

## Long context

The 1M window makes "put everything in context" viable, but mind recall: single-needle retrieval is ~99%, **multi-needle recall degrades** - when you need several distinct facts pulled reliably, prefer separate targeted requests. Put the query **last**, after the context, with an anchoring phrase. Longer inputs raise time-to-first-token; pair reused large contexts with caching.

## Non-English output

Gemini needs **aggressive** language enforcement to hold a non-English output language: *"RESPOND IN {LANGUAGE}. YOU MUST RESPOND UNMISTAKABLY IN {LANGUAGE}."* Also note 3.8 Flash's model card reports a slight **regression in non-English safety** vs 3.7 Flash - test safety behavior in each target language if it matters.

## Temporal grounding

Cutoffs differ by model - **March 2026 for 3.6-3.8 Flash** (with some domains still at Jan 2025), **January 2025** for 3.5 Flash, 3.5 Flash-Lite, and 3.1 Pro. For anything past the cutoff, enable Search grounding. For time-sensitive tasks, anchor the date explicitly (Google's clause above: *"Remember it is 2026 this year"*) and tell the model its cutoff - Gemini benefits from being told both even though it can search.

## Multimodal

Treat text, images, audio, video, and PDFs as equal-class inputs and reference each clearly with explicit labels.

**File / instruction ordering.** For a single image or video, **place the file before the text prompt**. For interleaved multi-file prompts, use the most natural ordering. With a large file + a question, put the question last.

**`media_resolution`** trades fidelity against token cost:

| Input | Recommended | Tokens |
|-------|-------------|--------|
| Images | `media_resolution_high` (default) | 1120 |
| PDFs / documents | `media_resolution_medium` - quality saturates at medium | 560 |
| Video (general) | `media_resolution_low`/`medium` | 70 / frame |
| Video with dense text (OCR, small details) | `media_resolution_high` | 280 / frame |

Gemini 3 defaults can raise token use for PDFs and lower it for video; reduce resolution explicitly if requests overflow.

**Troubleshooting.** If the model misses details, hint *which* aspects to draw from; if output is generic, ask it to **describe the image first**, then answer; to curb fabrication, ask for shorter descriptions (keep temperature at the default). Image segmentation is unsupported on Gemini 3 (use Gemini 2.5 Flash with thinking off). **Computer Use** is a built-in client-side tool (preview) on current Flash models - intent-based actions across browser / mobile / desktop, no separate model. Its safety layer is configured, not prompted: built-in policy categories (`FINANCIAL_TRANSACTIONS`, `SENSITIVE_DATA_MODIFICATION`, `COMMUNICATION_TOOL`, `ACCOUNT_CREATION`, `DATA_MODIFICATION`, `USER_CONSENT_MANAGEMENT`, `LEGAL_TERMS_AND_AGREEMENTS`) block or require confirmation; function calls can carry a `safety_decision` of `require_confirmation` - prompt the user and return `safety_acknowledgement` in the result. **Always handle that decision even if you set overrides** (overrides are preferences, not guarantees). From 3.5 Flash on, opt-in **prompt-injection detection** scans screenshots for hidden instructions and blocks execution (off by default - turn it on). Pair with a custom safety system instruction, a sandboxed VM/container/browser profile, and human-in-the-loop for consequential actions.

## Flash tier and inference tiers (Flex / Priority)

The Flash line is now Google's workhorse, including for agents and coding - 3.8 Flash competes with larger frontier models on long-horizon SWE. Pick by workload: **3.8 Flash** for hard agentic/coding work (accept the token appetite or lower the level); **3.7 Flash** when compute efficiency matters more; **3.5 Flash-Lite** for high-volume classification, routing, and extraction (raise its `thinking_level` for a cheap accuracy boost on ambiguous inputs). Give Flash-Lite more explicit instructions and more (simpler) examples, and keep its tool set small.

Separately, **Flex** (batch-tolerant, ~50% cost) and **Priority** (faster, steadier latency at a premium) inference tiers apply per request, independent of the model.

## Migration to Gemini 3.8 / 3.7 Flash

Google's `gemini-api-dev` skill can automate this for coding agents.
- Update the model ID (`gemini-3.8-flash` or `gemini-3.7-flash`); pin explicit IDs, not `-latest` aliases (alias targets shift; `gemini-3-pro-preview` was already retired → `gemini-3.1-pro-preview`).
- **Replace `thinking_level:"minimal"` with `low`** (or route that traffic to Flash-Lite) - `minimal` errors on 3.7/3.8. Replace numeric `thinking_budget` with `thinking_level`; never send both.
- Remove `temperature`, `top_p`, `top_k`, and `candidate_count`.
- **Move to the Interactions API** for new work: standardize multi-turn on `previous_interaction_id`, **re-send `system_instruction` / `tools` / `generation_config` every call**, and decide on `store` (default retention 55 days).
- **Drop assistant prefill** - a history ending on a non-empty `model` turn returns 400. Force shape with structured output.
- Audit function calling: multimodal assets inside the response payload; inline guidance separated by `\n\n`; ids/`call_id` on every response; remove structured pre-tool text (see *Function calling*) if you hit `Malformed_Function_Call`.
- Keep thought signatures round-tripping in stateless mode (or go stateful).
- **Expect higher token use on 3.8 Flash** and budget for the Jan 1 2027 price doubling; compare cost-per-task against 3.7 Flash.
- The knowledge cutoff advanced to **March 2026** from 3.6 Flash on - you can drop date-anchoring workarounds for facts it now knows, but keep telling it the current date.
- Re-test: Gemini 3.x is terser and more direct - prompts written for a chattier older model may need an explicit elaboration request.
