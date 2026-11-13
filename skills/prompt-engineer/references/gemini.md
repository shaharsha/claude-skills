# Gemini (Google) - Provider Deep-Dive

Applies to the **Gemini model family** wherever it runs: the Gemini API (Google AI Studio) and Vertex AI / Gemini Enterprise Agent Platform. The platform does not change prompt engineering - the model version does.

**Current models (November 13 2026):** **Gemini 4 has three generally available models.** **Carbon** (GA Nov 10) is the strongest and spends the most thinking per turn; **Argon** (GA Oct 13) is the efficient frontier model "for the majority of software engineering and knowledge work"; **Hydrogen** (GA Nov 12) is the fast, cheap one and Google's new default ("Start with `gemini-4-hydrogen`"), the recommended upgrade from 3.8 Flash. All three share one API contract (unified 1M window, long decode, implicit caching only, no sampling params; thought-signature rules below). **Gemini 3.5 Pro is cancelled** ("Google no longer plans to release Gemini 3.5 Pro" - Google spokesperson to Reuters, Sept 30 2026), and Google Cloud says to migrate from 3.1 Pro Preview to Carbon or Argon. New, and not a chat model: **Gemini Decision 1** (Nov 11), a calibrated classifier behind the new Decisions API. Re-check this list before trusting it.

- **Gemini 4 Carbon** (`gemini-4-carbon`, announced Oct 28 for cyber defenders via the Fairwind Program, **GA Nov 10 2026** on the paid tier; stable ID; not on the free tier) - "our strongest reasoning model", built on Argon for "sustained agentic workflows". The difference from Argon is depth: "Carbon spends more thinking tokens per turn to explore thoroughly and verify its work, which increases per-turn token use and latency compared to Argon." Text / image / video / audio / PDF in, text out. Same contract as Argon: **`thinking_level` `low`/`medium`/`high`, default `medium`**; unified 1,048,576-token window; 65,536 output tokens per streaming response but **32,768 per non-streaming one** (on both the Gemini API and Vertex), up to ~1M with long decode; **implicit caching only**. **$2 / $10 through Nov 30 2026, then $4 / $20 from Dec 1** (cached input $0.10 → $0.20). Cutoff not published. Google's claims at the Oct 28 announcement: #1 on AA's Intelligence Index v5 at launch (Claude Fable 5.2 has led it since Nov 9), about 2× fewer unsupported claims than Argon, 0.0% attack success on Gray Swan's indirect-prompt-injection benchmark (Argon 0.7%), 26% less overreach and 29% less under-service on multi-step plans. An allowlisted variant, Gemini 4 Carbon for cyber (`gemini-4-carbon-cyber-permissive`, default thinking `high`), is on Vertex. See *Prompting Gemini 4 Carbon*.
- **Gemini 4 Argon** (`gemini-4-argon`, announced Sept 30 for cyber defenders via the Fairwind Program, **GA Oct 13 2026** on the paid tier; stable ID, no `-preview`) - Google's generally available flagship, "larger in size than Google's previous line of advanced 'Pro' models", a new sparse MoE pretrain (not a fine-tune), "trained to **work longer** and **retain context better** than any previous Gemini model." Text / image / video / audio / PDF in, text out. **`thinking_level` `low`/`medium`/`high`, default `medium`** (`minimal` and `thinking_budget` → 400 on Vertex; the AI Studio guide says `thinking_budget` only warns - don't send either). **Unified 1,048,576-token window shared by input, thinking, and output**; 64K output per synchronous response, **up to ~1M with long decode** (below). **Implicit caching only** (no explicit caches), sampling params ignored, **no prefilled model turns**. **$2 / $10 introductory through Nov 30 2026, then $4 / $20 from Dec 1** (cached input $0.10 → $0.20, 0.05×; Batch/Flex half; not on the free tier). On Vertex the intro price is the $4 / $20 list price with **50% credited back** on net spend, so usage is costed at list and the promo arrives as a billing credit (in the BigQuery billing export, `credits.amount` on the usage rows; net cost is `cost` plus the credits); the Cyber Permissive variant gets no promo, and non-global endpoints cost 10% more. March 2026 cutoff. Interactions API is Preview on Vertex. Allowlisted variant **`gemini-4-argon-cyber-permissive`** (Vertex) for defensive security work - default thinking `high`.
- **Gemini 4 Hydrogen** (`gemini-4-hydrogen`, **GA Nov 12 2026** on the free and paid tiers, Gemini API and Vertex; stable ID) - "speed and efficiency for everyday coding and agentic workflows", standalone or as the execution model under Carbon or Argon; Google's "recommended upgrade from Gemini 3.8 Flash and earlier Gemini 3 and 2.5 models", and since Nov 12 the default model of the managed Antigravity agent. **`thinking_level` `low`/`medium`/`high`/`xhigh`, default `high`** (`xhigh` is new; `minimal` is rejected, and `thinking_budget` returns 400 on Vertex). Same unified 1M window and long decode as Carbon and Argon, with 65,536-token non-streaming hops. **$1.50 / $7.50 flat** across the window (cached $0.075); free tier rate-limited. Google's claims against 3.8 Flash: 2.5× faster at `high`, Terminal-Bench 4.1 57% vs 18.2%, and "cuts fabricated claims by more than 5x ... by flagging missing context instead of guessing"; it batches read and search calls in parallel. Cutoff not published. See *Prompting Gemini 4 Hydrogen*.
- **Gemini Decision 1** (`gemini-decision-1`, Nov 11 2026, Gemini Developer API only) - not a chat model: it answers typed yes/no, choice and rubric-score questions with calibrated probabilities and **zero output tokens**, through the new Decisions API. $0.10 per 1M input tokens. See *Decisions API (Gemini Decision 1)*.
- **Gemini 3.8 Flash** (`gemini-3.8-flash`, GA Sept 2 2026) - the last Gemini 3 Flash, for long-horizon software engineering, autonomous agents, and complex enterprise workflows; **superseded for new work by Hydrogen** (Antigravity's default moved to Hydrogen on Nov 12; still served, no shutdown date). **`thinking_level` `low`/`medium`/`high` only - `minimal` returns an error**; default `medium`. **Uses more tokens by design** (smaller reasoning steps, iterative tool calls, self-verification) - lower the level for everyday work. Knowledge cutoff **March 2026** (some domains still Jan 2025).
- **Gemini 3.6 Flash** (`gemini-3.6-flash`, July 2026) - "our previous generation Flash model"; keeps the full `minimal`-`high` range, default `medium`; March 2026 cutoff.
- **Deprecated and silently re-routed (Oct 8 2026):** `gemini-3.7-flash` now serves **`gemini-3.8-flash`** and `gemini-3.5-flash` now serves **`gemini-3.6-flash`** - the endpoints still answer, but a prompt tuned on those IDs is running on a different model (3.8 is the token-hungrier one). Re-run evals and switch the ID explicitly.
- **Gemini 3.5 Flash-Lite** (`gemini-3.5-flash-lite`) - still the newest, cheapest / fastest tier ($0.30 / $2.50); default `minimal`, full range. **Gemini 3.1 Flash-Lite** is the prior Lite (shutdown May 7 2027).
- **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`, preview, no shutdown date) - the last Pro model; `low`/`medium`/`high`, default `high`; $2 / $12 (≤200k input), $4 / $18 above; Jan 2025 cutoff. New Pro-tier work goes to Argon. In the Gemini app, Deep Think (a 3.1 Pro mode) "is being replaced by Gemini 4 Argon".
- **Gemini 3.8 Flash Cyber** (`gemini-3.8-flash-cyber`) - security-tuned sibling, GA behind an allowlist (Google Fairwind). **No grounding, code execution, function calling, or URL context, and no Interactions API** - a bare-generation model; prompt it like 3.8 Flash.
- Also current: Gemini 3.8 Live / Live Extended Thinking (voice agents; default asynchronous function calling), 3.8 Flash TTS / Flash-Lite TTS, Nano Banana 2.1 (`gemini-nano-banana-2.1`, images; succeeds `gemini-3.1-flash-image`). `gemini-3-flash-preview` remains; **Gemini 2.5 is going away, differently per platform** (Google's Nov 2 note): on **Vertex AI / Agent Platform**, `gemini-2.5-pro`, `gemini-2.5-flash` and `gemini-2.5-flash-lite` were already **retired on Oct 20 2026**; on the **Gemini Developer API**, from **Dec 1 2026** `gemini-2.5-pro` silently routes to `gemini-3.8-flash` and `gemini-2.5-flash` to `gemini-3.5-flash-lite` (2.5 Flash-Lite unchanged for now), billed at the new model's rates, with the 3.x breaking changes (thought-signature validation, `thinking_level`, no sampling params, no prefill); switch IDs and re-run evals before then. Gemini 2.0 shut down June 1 2026.

**Pricing (per 1M tokens; output includes thinking):** **Carbon and Argon $2 / $10 through Nov 30 2026, then $4 / $20 from Dec 1**; **Hydrogen $1.50 / $7.50** flat; 3.8 and 3.6 Flash an introductory **$0.75 / $3.75 through Dec 31 2026**, rising on Jan 1 2027 to $1.50 / $7.50 - Hydrogen's price - so plan the move to Hydrogen before then. Decision 1: $0.10 input, no output tokens. Budget for every step-up. Batch and Flex are 50%.

Gemini 3 models have a **~1M-token input window (1,048,576) and 64K output (65,536)**; all three Gemini 4 models put input, thinking and output in **one** 1,048,576-token window. **Cutoffs differ by model**: March 2026 for Argon and 3.6-3.8 Flash (uneven - some domains still end at Jan 2025), Jan 2025 for 3.5 Flash-Lite and 3.1 Pro, not published for Carbon or Hydrogen.

## Contents
- The Interactions API (now the default surface)
- System instructions and placement
- Sampling parameters (don't set them)
- Thinking level
- Thought preservation and signatures
- Prompting Gemini 4 Argon
- Prompting Gemini 4 Carbon
- Prompting Gemini 4 Hydrogen
- Output budget and long decode (Gemini 4)
- Prompt design fundamentals (few-shot, completion priming, decomposition, iteration)
- Gemini 3 prompting principles and Flash clauses
- Agentic workflows: steering dimensions and system-instruction template
- Verbosity
- Grounding and built-in tools
- Function calling
- Tool-use control and error recovery
- Structured output
- Decisions API (Gemini Decision 1)
- Caching
- Long context
- Non-English output
- Temporal grounding
- Multimodal
- Flash tier and inference tiers (Flex / Priority)
- Migration to Gemini 4 Argon or Carbon
- Migration to Gemini 4 Hydrogen (from 3.8 Flash)
- Migration to Gemini 3.8 Flash

## The Interactions API (now the default surface)

Google's **Interactions API** (GA June 2026) is "the best way to build with Gemini models and agents" and where every new model, tool, and agent feature launches; the original `generateContent` API is now **legacy** but fully supported. One endpoint covers models and agents (`client.interactions.create(model=… | agent=…, input=…)`), including managed agents such as Deep Research and Antigravity (`antigravity-preview-09-2026`).

- **Stateful by default.** Pass `previous_interaction_id` to continue a conversation; the server keeps history, thoughts, and signatures, and implicit caching hits more often. **But `previous_interaction_id` preserves only history - `system_instruction`, `tools`, and `generation_config` (incl. `thinking_level`) are interaction-scoped and must be re-sent on every call.** A system instruction sent only on turn 1 is silently gone on turn 2.
- **It stores interactions by default** - on the Gemini API 55 days on the paid tier, 1 day on free (configurable to 7/14/28/55 days in AI Studio); on Vertex 7 days. For sensitive data set `store=false`, which also disables `background=true` execution and `previous_interaction_id` (you then resend history yourself). **Since Oct 26 2026, new paid-tier projects on `generateContent` also store requests by default** (existing projects keep their setting) - check `store` on both surfaces.
- Background execution (`background=true`) for long-running tasks (Gemini 4 long decode, Deep Research); observable typed execution **steps** for debugging and UI. Terminal statuses: `completed`, `requires_action`, `incomplete` (text can be empty if the model was still thinking), `failed`, `cancelled`. The SDK's `.output_text` joins only the *final* run of text blocks - text interleaved with thoughts, tool calls, or images is dropped, so iterate over `steps` for anything non-trivial. In stateless mode (`store=false`) resend the full history including every model-generated step (`thought`, `function_call`) exactly as received.
- **Limitations:** remote MCP works only inside **managed agents** (Antigravity, Deep Research) as an `mcp_server` tool - Streamable HTTP only (no SSE), and the server name must be lowercase alphanumeric (uppercase → a generic 400); for raw model calls, bridge MCP tools yourself as function declarations. When mixing models in one conversation, each later model must accept the earlier models' output modalities as input.
- The OpenAI-compatibility layer maps `reasoning_effort` to `thinking_level` automatically (on Argon `minimal` and `low` both map to `low`).
- **Managed agents:** Antigravity `antigravity-preview-09-2026` defaults to Hydrogen (since Nov 12; 3.8 Flash before) and accepts Carbon or Argon via `agent_config: {"type": "antigravity", "model": "gemini-4-carbon"}` (`antigravity-preview-05-2026` shut down Oct 5). Deep Research is now `deep-research-preview-04-2026` (fast, streams well) or `deep-research-max-preview-04-2026` (most comprehensive); `deep-research-pro-preview-12-2025` shut down Oct 23.

## System instructions and placement

Use `system_instruction` for role, behavioral rules, and format requirements. Google's current guidance: put essential behavioral constraints, persona, and output-format requirements **in the system instruction or at the very beginning of the user prompt**; for large inputs put **all the context first and the specific question/instruction at the very end**, bridged with a phrase like *"Based on the information above…"*. Gemini also shows a **recency bias** - critical constraints restated last are followed more reliably. Use one structural convention consistently (XML tags *or* Markdown headings - don't mix within a prompt). XML tags also mark data as data: content inside `<context>` is read as input, not instructions.

## Sampling parameters (don't set them)

**Strip `temperature`, `top_p`, and `top_k` from every request.** Google's prompt-design page (Oct 13 2026): "Gemini 4 and Gemini 3.6+ models ignore custom values for `temperature`, `top_p`, and `top_k` and return deprecation warning headers (**and will return `400` errors in a future release**)." On earlier Gemini 3 models keep them at the defaults (`temperature` 1.0) - below 1.0 risks **looping or degraded performance**, especially on math and complex reasoning. Also drop `candidate_count` (values above 1), and on Gemini 4 models `frequency_penalty` / `presence_penalty` (Vertex's Argon and Hydrogen guides; a 400 on Vertex for Argon). For determinism, use explicit rules and structured output. (Google's general prompt-design page still carries older advice such as "increase the temperature" to escape fallback responses - that predates 3.x; ignore it.)

## Thinking level

Gemini 3.x and 4 use `thinking_level`, replacing the numeric `thinking_budget` (still accepted on 3.x for back-compat - **never send both; that's a 400**; on Gemini 4 models `thinking_budget` alone is a 400 on Vertex). Levels and defaults are **per model**:

| Model | Default | Supported |
|---|---|---|
| **4 Carbon** | `medium` | `low`, `medium`, `high` (**`minimal` → 400**); cyber-permissive variant defaults to `high` |
| **4 Argon** | `medium` | `low`, `medium`, `high` (**`minimal` → 400**); cyber-permissive variant defaults to `high` |
| **4 Hydrogen** | **`high`** | `low`, `medium`, `high`, **`xhigh`** (**`minimal` → 400**) |
| 3.8 Flash (and `gemini-3.7-flash`, which now routes to it) | `medium` | `low`, `medium`, `high` (**`minimal` → error**) |
| 3.6 Flash (and `gemini-3.5-flash`, which now routes to it) | `medium` | `minimal`-`high` |
| 3.5 Flash-Lite | `minimal` | `minimal`-`high` |
| 3.1 Pro (preview) | `high` | `low`, `medium`, `high` |
| 3 Flash (preview) | `high` | `minimal`-`high` |

- `minimal` - speed; chat, quick facts, simple tool calls (*does not guarantee thinking is off*).
- `low` - latency-critical work: real-time chat, drafts, fast data analysis, incident pipelines, high-throughput.
- `medium` - "best quality for most tasks"; complex code and agentic use cases.
- `high` - deep reasoning, math, the hardest multi-step tasks and tool orchestration.
- `xhigh` (Hydrogen only) - "hard, multi-step coding and agentic problems where `high` falls short"; Google warns it "can cause overthinking on simpler prompts".

Start at the model's default; drop a level for faster/cheaper; escalate only for genuinely hard work. On 3.8 Flash the default already self-verifies heavily - `low` is the lever when token use outruns the task. If an older prompt used chain-of-thought text to force reasoning, delete it and raise `thinking_level` instead (in-response plans are unnecessary - the model thinks internally; for the hardest problems Google notes a simple *"Think very hard before answering"* can help, at a thinking-token cost). For long outputs, prompting the model to think less saves tokens.

**`max_output_tokens` is a hard cutoff that includes thinking.** If the model hits it while reasoning, the interaction ends `incomplete` with truncated or empty output - and you're still billed for the thinking. To cut cost or latency, lower `thinking_level`; don't shrink `max_output_tokens`.

**Cost:** thinking tokens bill **at the output rate**, so the level moves the bill more than the model choice often does. Fine for low-volume calls; on a high-throughput path keep it low (on Gemini 4 and 3.8 Flash `low` is the floor - route truly no-reasoning traffic to Flash-Lite at `minimal`, and closed yes/no or choice decisions to Decision 1) and recover accuracy with the prompt and examples first. The knob is per-request. Thought summaries are opt-in (`thinking_summaries:"auto"`) - read them to debug failures.

## Thought preservation and signatures

Thought preservation is on by default on Gemini 3.x and 4 - the model carries intermediate reasoning across turns (better iterative work, more tokens). In **stateful** Interactions mode (`store` on + `previous_interaction_id`) the server manages thoughts and signatures entirely. In **stateless** mode (or legacy `generateContent` over REST) you must round-trip them:

- **Single function call** → return the `thoughtSignature` inside its original `Part`.
- **Parallel calls** → only the **first** `functionCall` carries a signature; return the response parts in the **exact order received**.
- **Sequential / compositional calls** → return **all** accumulated signatures.
- **Image generation/editing** → signatures strictly validated (first part and every subsequent `inlineData` part).
- **Injected or synthesized calls** → pass a **dummy signature string** so validation passes. Use this only for calls the model never made: Google's Gemini 4 guide (Vertex) warns that stripping real signatures from earlier turns or substituting bypass values such as `skip_thought_signature_validator` "removes reasoning context, degrades output quality, and can cause `MALFORMED_FUNCTION_CALL` finish reasons".

Always pass the matching call `id` back in each function response (see *Function calling*).

**Gemini 4 tightens the rules** (Vertex's Gemini 4 migration table and Hydrogen guide; the Gemini API pages don't describe these, checked Nov 13):
- **Return every signature from every earlier turn**, on `functionCall` parts and final text parts alike, not only within the active turn. Validation (a 400) applies to the active turn's calls; dropping older ones costs quality.
- **Parallel calls:** only the first `functionCall` carries the signature; omitting it there or copying it onto sibling calls is a 400, and so is interleaving calls and responses - keep all parallel calls in one model turn followed by all their responses in one user turn.
- **Signatures are bound to the conversation prefix** (system instruction, tools, and earlier turns). By default (`prefix_mismatch_behavior="ERROR"`), replaying a conversation to the same model with an edited earlier turn or system instruction returns **400 `INVALID_ARGUMENT`**. If your harness compacts, prunes, or edits history, set `prefix_mismatch_behavior="DROP"` in `ThinkingConfig` (`generation_config.prefix_mismatch_behavior="drop"` on the Interactions API): the server drops the mismatched signatures and keeps the visible text, calls and media. Signatures from a different model (Carbon or Argon history sent to Hydrogen) are dropped automatically. This is the same design as Claude's preserved-thinking check (`claude.md`): treat history as append-only, or opt into dropping.

## Prompting Gemini 4 Argon

Argon is built to run long and unattended, so Google's guidance shifts the work to **before** the run (agree on the goal) and **into** the run (give it something to check against). From Google's *5 practical tips for building with Gemini 4 Argon* (AI Studio developer guide, Oct 13 2026) and the Vertex developer's guide:

- **Agree on intent up front.** "Clear alignment upfront on measurable goals and key milestones helps you get to your result most effectively." State the goal and success criteria, then ask Argon to **surface clarifying questions** about edge cases first, and run a **pre-flight check** - have it confirm it has the tools and docs it needs and restate the intent. Then "step back and let Argon run to completion" rather than steering turn by turn; it is trained to pause for confirmation before irreversible steps, so you don't need to prompt that in.
- **Give it a verification loop.** "Argon does its best long-horizon work when it can test its own changes against a real feedback loop." Have it write a reproducible verification script, record a baseline, and test every change against it until the target is met; if there's nothing to measure, ask it to build a baseline benchmark first. This is the external signal Section A says a critic step needs.
- **Prompt with the goal, put conventions in files.** Google's worked example (an 11-hour unattended performance run on the ADK codebase) started from a single goal paragraph ("…back each change with a test that would catch a regression") - Argon spent 70 minutes measuring before editing, and its first-round failures were all **missing maintainer conventions** (it changed a public JSON schema, ran only nearby tests). Round two put those conventions in `.agents/skills` (a short `SKILL.md` index pointing to `references/` files) and stated the deliverable ("Open one pull request … with before and after numbers in its description. Don't merge it.") - the run then used the full test suite. Lesson: the prompt carries the goal and the deliverable; durable rules live in skills/`AGENTS.md`.
- **Orchestrate with a faster model.** Google's recommended topology: **Argon (`medium` or `high`) as lead orchestrator** for architecture, planning, and review; **parallel, well-scoped work to cheaper subagents** - the Argon guide (Oct) names 3.8 Flash; since Nov 12 Google's recommended execution model is Hydrogen (*Prompting Gemini 4 Hydrogen*). An **adversarial critic subagent** run at the end of each round ("list at least 3 specific flaws to fix … keep iterating until the critic rates it 9/10") is Google's pattern for open-ended quality.
- **Ask it to reflect into instructions.** "Having Argon write those lessons into `AGENTS.md` or a reusable skill means future sessions take the direct path on the first try" - e.g. *"Investigate our current session to see where things stalled or required extra steps, and analyze why. Propose updates to our AGENTS.md or custom skills."*
- **Point at a reference instead of describing a look.** For visual work give 1-2 concrete references, or have Argon distill typography, palette, and layout rules into a short `DESIGN.md` first.
- **Style.** Argon "answers questions more directly with less hedging, doesn't repeat itself more than necessary, and skips clichés"; on long tasks it reports progress more often. Prompts that pushed earlier Gemini models to elaborate may now over-correct - test before carrying them over.
- **Request shape (Vertex guide):** no assistant prefill (a history can't end on a `model` turn); **no unstructured text before a tool call** - log intermediate state through a dedicated `update(previous_step, plan, next_step)` function, and separate inline instructions with `\n\n`; **"each FunctionResponse must match the id, name, and order of the preceding FunctionCall"**; and **"prefer sequential tool execution turns in multi-step tool loops."**
- **Thinking level:** `low` for classification, summarization, extraction, and light analysis/writing; **`medium` (default) for most work, including complex code, tool use, and document Q&A**; `high` for multi-file engineering, proofs, architecture, hard math/science, and vulnerability discovery. Google: "Run your evaluations at all three levels, then pick the lowest level that meets your quality bar." On BullshitBench `low` slightly *outscored* `high` - the Section A finding that effort doesn't fix false-premise acceptance holds here too.

## Prompting Gemini 4 Carbon

Google's *Gemini 4 Carbon: Developer Guide* (AI Studio, Nov 10 2026) repeats Argon's five tips almost word for word - agree on intent and run a pre-flight check, give it a verification loop (have it build a baseline benchmark if you have none), point at concrete references or a `DESIGN.md` (new with Carbon: Google's `gemini-frontend-design` skill, `npx skills add google-gemini/demolab --skill gemini-frontend-design`, which Google says beats no skill and popular third-party design skills, and the `gemini-api-cli` skill for generating images, video, speech or music from the terminal), run it as the orchestrator, and have it reflect lessons into `AGENTS.md` or a skill - so everything in *Prompting Gemini 4 Argon* above applies. What changes:

- **Pick Carbon for depth, Argon for throughput.** Same API, price and window; switching is a model-string change. Google: Carbon for "complex root-cause debugging, architectural design, dense multimodal synthesis, scientific proofs, and security auditing"; Argon for "interactive coding, day-to-day feature work, and fast production loops."
- **Give it the lead and verifier roles in a multi-agent setup.** Google pins Carbon (`medium` or `high`) "as the lead orchestrator and verifier to break down the architecture, define interfaces, and audit completed changes", with parallel implementation on cheaper models (its guide names 3.8 Flash or Argon; Google's Hydrogen launch pairs Carbon with Hydrogen workers and verifiers - see *Prompting Gemini 4 Hydrogen*).
- **Budget for longer turns.** Keep `thinking_level` at `medium` unless a workload needs `high`, raise `max_output_tokens` to at least 32,768, and allow HTTP timeouts of 15-20 minutes or use background execution.

The Oct 28 launch post's behavior claims that change how you prompt:

- **It surfaces discrepancies before acting.** "Rather than guessing or forcing a path forward, Carbon retrieves the relevant sources and surfaces discrepancies to the user before acting." On ambiguous tasks expect more check-ins than Argon; Argon's up-front alignment (clarifying questions plus a pre-flight check before an unattended run) is how you keep a long run from stopping on them.
- **It reports what it couldn't do.** It "puts methodological caveats directly into the deliverable or withholds blocked actions with a clear list of what remains required, rather than fabricating or hedging around missing evidence." Give it somewhere to put that list (a section of the report, a `blocked` field) and treat an open item as unfinished work, not a failure.
- **It stays inside the scope.** Google reports 26% less overreach and 29% less under-service than Argon, "staying strictly within scope" - so state the scope you want rather than adding anti-scope-creep guardrails, and say so explicitly when you *do* want adjacent fixes.
- **Effort:** `medium` is the default. Google: `low` for "high-speed classification, routing, and targeted extraction", `high` for "multi-file root-cause debugging, security vulnerability patching, formal math, and upfront architecture design". On AA's v5 index `low` was not cheaper per task than `medium` (54.2 at $5.22 vs 58.3 at $4.68, at the intro price; Nov 13) and scored lower [one evaluator], so sweep all three on your own tasks before assuming `low` saves money.

## Prompting Gemini 4 Hydrogen

From Google's Hydrogen pages (the Gemini API what's-new page, the Nov 12 launch post, and the Vertex developer's guide):

- **Default `high` is the recommended setting** "for most tasks, including complex coding, agentic execution, tool calling, and multimodal knowledge work"; `medium` for interactive coding and latency-sensitive tool turns; `low` for high-throughput work; `xhigh` only where `high` falls short. Google: "Run your evaluations at all four levels with a high `max_output_tokens` so the limit doesn't cut answers short. Then pick the lowest `thinking_level` that meets your quality bar." Coming from 3.8 Flash, note the default moved from `medium` to `high` - set it explicitly if you want 3.8 Flash's cost profile.
- **Declare tools natively.** "Do not prompt the model via system instructions to emit custom raw-text JSON tool calls with zero declared tools, which can return `MALFORMED_FUNCTION_CALL`" - use function calling or structured output.
- **It flags missing context instead of guessing** (Google's explanation of the 5× drop in fabricated claims). Give it a place to report what it couldn't find, and don't add "always produce an answer" pressure that works against this.
- **Use it as the execution model under Carbon or Argon.** Google: "Have Carbon plan system interfaces or resolve hard roadblocks, then delegate code edits, parallel subagent tasks, and test runs to Hydrogen." You can switch models across turns of one session with `previous_interaction_id`; Google's Antigravity Orchestrator does this automatically and reached "near-Carbon task success rates" on Terminal-Bench 4.0 with 24% less quota and 19% faster. Mind the cache and signature effects of switching (thought signatures from another model are dropped).
- **Parallel reads come naturally.** Hydrogen "batches read and search tool calls in parallel"; keep parallel calls in one turn and their responses in the next (*Thought preservation and signatures*).
- **Reasoning tokens pile up across turns** at `high` and `xhigh` when you preserve signatures: set `max_output_tokens` high enough for thinking plus answer, and avoid very low compaction thresholds in multi-turn coding harnesses (Vertex guide).

## Output budget and long decode (Gemini 4)

The rules below were written for Argon and Google repeats them for Carbon and Hydrogen; the differences are noted.

- **Thinking counts against `max_output_tokens`, and Gemini 4 models think more than earlier models** (Carbon most of all). Google's migration note: apps with a limit under 32K should "raise max_output_tokens to at least 32,768 … To use fewer tokens, lower the thinking level instead." For Hydrogen: "Remove hardcoded low caps (such as 8,192) or raise `max_output_tokens` to 65,536." Check the value your agent framework or eval tool sets - "a low value, such as 8,192, stops the model before it finishes thinking", and the turn ends `incomplete` with truncated or empty text while still billing the thinking.
- **Gemini 4 models don't follow length targets** (the long-decode guide covers Carbon, Argon and Hydrogen). Asked whether it can write to a fixed length, Google's long-decode guide answers: "No. The model doesn't follow length targets." `max_output_tokens` is room, not a target - "the model still decides how much to write." Control depth with `thinking_level` and shape with the prompt and `response_schema`, not with word counts.
- **Long decode** lets one response run past 64K tokens, up to 1,048,576 minus input, in one of two ways on the **Interactions API** (Google's long-decode guide, Nov 2026):
  - **Background execution** (`background: true`, which requires `store: true`, plus `max_output_tokens` > 65,536; without a limit it stops at 64K): the server runs every hop, for up to 24 h. Output arrives as several `model_output` steps - **join the text across all of them**; streaming sends ~5K-token chunks, reconnect with `last_event_id`.
  - **Client-side continuation** (foreground, `background: false`): the Gen AI SDK runs the hops for you when `max_output_tokens` exceeds the per-hop cap below (`automatic_continuation`, on by default; Python ≥ 2.34.0, JS ≥ 2.32.0) and returns one interaction; older SDKs and direct HTTP stop at one hop unless you loop; with REST or your own loop, each hop ends with status `requires_continuation` and an encrypted `continuation_token` to send back. It works stored or stateless (`store: false`). **Per-hop caps:** 65,536 tokens per streaming hop and per non-streaming hop on Hydrogen, but **32,768 per non-streaming hop on Carbon and Argon**; a hop runs at most 20 min streaming, 10 min non-streaming. A failed hop after progress raises `ContinuationInterruptedError` with the partial output.
  On **`generateContent`** the SDK follows `finish_reason=CONTINUATION` + `continuation_token` the same way (v1beta1). (Google's Carbon developer guide, also Nov 10, still calls client-side continuation GenerateContent-only and "coming soon" to Interactions; the long-decode guide and the Carbon and Hydrogen what's-new pages document it on Interactions - check your SDK version.) **Don't append partial output and ask the model to "continue"**, and don't decide when to compact from the cumulative input count: on the Interactions API `usage.total_input_tokens` re-counts every hop's input, so estimate context as your prompt size (or `usage.initial_input_tokens` on non-streaming SDK responses) plus `total_output_tokens` and `total_thought_tokens`; on `generateContent` read `initial_prompt_token_count`, not the cumulative `prompt_token_count`. For complex reasoning and coding Google suggests `max_output_tokens` of 131,072 or 262,144.
- **Don't use long decode for tool-heavy agents** - many short turns with large outputs fill the shared window fast.
- **Timeouts:** hard prompts can take several minutes (AA measured ~51 s to the first answer token); use background execution or HTTP timeouts of at least 15 minutes. **On Vertex, from Nov 13 2026, a completion past 32K tokens is billed for its "retrievable token usage" even when the request then fails on a client or server timeout** (Vertex pricing page; the Gemini API page doesn't say), so a client timeout shorter than the run pays for output you never receive.

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

Native **Google Search grounding** connects the model to real-time information (5,000 free grounded requests/month shared across Gemini 3.x, then $14 / 1,000, capped at 1,500 requests a day on the Gemini API; on Gemini 4 models the grounding tool's own system instructions and declarations bill as input tokens). Built-in tools: **Google Search, Maps grounding, File Search, Code Execution, URL Context**, and **Computer Use** (built in - no separate model; all three Gemini 4 models; **GA since Oct 30 2026** on both the Interactions and `generateContent` APIs). Gemini 3 and 4 combine any of them with custom function calling (still Preview) **and with structured output** in a single request. On Vertex, Argon also grounds through Agent Search, Parallel Web Search, Exa Web Search, and Web Grounding for Enterprise. Enable Search for current or obscure facts and Code Execution for calculations.

**Grounded source links are usually redirects, not the source URL - on both APIs.** On `generateContent`, `groundingChunks[].web.uri` is typically a `https://vertexaisearch.cloud.google.com/grounding-api-redirect/...` link whose `title` is just the domain (Google's own Gemini API grounding example; Firebase AI Logic's grounding docs; python-genai issues #1512 and #1322; a Google AI forum request for a real-URL field), but some chunks carry a direct URL with a descriptive title (Vertex's own example has a google.com search link). **The Interactions API's `url_citation` annotations are redirects too in practice**: Google's Interactions example shows plain URLs, but a live Gemini API call on Nov 7 2026 (`gemini-3.8-flash` with `google_search`) returned 8 of 8 `url_citation.url` values as `grounding-api-redirect` links, `title` again just the domain [unverified: one call]. To show, dedupe, or verify a source, resolve only the links with that redirect prefix: send one `HEAD` request without following redirects and read the `Location` header, keep the redirect link if there is none, and keep direct URLs as they are. Take the domain from the resolved URL, not from `title`. Measured: 51 of 51 redirect links resolved this way in about 3 s on Nov 5 2026 (through Vertex AI) and 10 of 10 in about 4 s on Nov 7 2026 (the Gemini API, `generateContent` and Interactions links) [unverified: one test each]. Resolve them before handing them to the URL Context tool, which failed on the redirect links in python-genai #1322 (Vertex, Gemini 2.5).

## Function calling

- Each function call carries a unique call id - every response must include the matching id (`call_id` in Interactions; `id` + `name` on every `FunctionResponse` in `generateContent`) and exactly one response per call.
- **Function responses can carry multimodal content** - place images/audio **inside** the function-response payload, not alongside it. Since Nov 5 2026 they also take video, audio, and Office / OpenDocument files, and a Files API URI (`fileData`) instead of inline bytes, with `displayName` on both and `mediaProcessing` (`STATIC` / `AGENTIC`) on video; on the Interactions API, `function_result` steps take `document`, `audio`, and `video` blocks (by `data` or `uri`; video in `v1beta` / `v1alpha`). So a tool can hand back the file itself instead of a text description of it.
- Append extra runtime guidance to the function-response text, separated by `\n\n`, not as a separate part.
- **Calling modes** (`function_calling_config.mode`): `AUTO` (default with declarations only), `VALIDATED` (default when built-in tools are combined with custom functions; constrains output to the schema), `ANY` (force a call every turn), `NONE`.
- Keep the active tool set to **10-20** declarations; only a **subset of OpenAPI schema** is supported, and very large or deeply nested schemas may be rejected (especially under `ANY`/`VALIDATED`). Validate calls before executing.
- **Don't require structured text right before a tool call.** If the prompt demands an `<UPDATE>…</UPDATE>` block (or JSON/YAML) immediately before calling a tool, the call can fail with **`Malformed_Function_Call`**. Google's fixes, preferred first: (1) move those notes into a dedicated **`update()` function** (params like `previous_step`, `plan`, `next_step`) that the model calls before other tools; (2) have it write notes as Markdown headers (`# UPDATE`, `## PLAN`); (3) drop the pre-tool text requirement.
- Check `finishReason` / interaction status to catch turns where no valid call was produced.

## Tool-use control and error recovery

If the model overuses tools - more likely on 3.8 Flash, which calls tools iteratively by design, and on Argon, which averaged ~116K output tokens per task on AA's v5 index (2.2× GPT-6 Astra at `max`) - first lower `thinking_level`, then constrain the budget in the system instruction (*"You have a limited action budget of N tool calls."*). **For research loops, also enforce the budget in your tool layer.** Given unlimited web search in an agent harness, Argon ran 159 searches in 30 minutes in one run, and 27 searches plus 86 page reads in 20 minutes in another, and neither run returned an answer. With a 20-call budget, where each call past the limit got a refusal saying to answer now from what it had, the same kind of consult answered in about 5 minutes [unverified: one harness, a handful of runs, Nov 2026]. Built-in Google Search runs server-side, so a hard per-call cap means exposing search as your own function. Gemini benefits from an explicit recovery rule: **"Don't repeat a failed call with identical arguments"** - change the query, parameters, or approach; retry transient errors only up to a stated limit.

## Structured output

Prefer the structured-output feature over describing a JSON schema in prose (JSON Schema via the response-format config - field names differ between the Interactions API and legacy `responseSchema` / `responseMimeType`, so confirm for your SDK version). Structured output now combines with built-in tools and function calling. Guidance:

- Use specific types and put fixed value sets in an `enum` - ideal for classification/routing.
- Put per-field instructions in schema `description` fields, and still state the task plainly in the prompt.
- `propertyOrdering` is a Gemini-2.0-only requirement.
- Very large or deeply nested schemas may be rejected; unsupported keywords are ignored. **Always validate the output in your own code.**

## Decisions API (Gemini Decision 1)

When code needs a judgment to branch on - route a request, check a policy, score against a rubric, pick the tools an agent needs, decide whether to compact, escalate or stop - Google's **Decisions API** (Nov 11 2026; `gemini-decision-1`, Gemini Developer API v1beta only) answers it without generating text. Free tier and paid; SDK 3.2+. One request sends shared input (text, JSON as a string, images, audio, video, PDF) and up to 1,000 **questions** (instructions are text only - media goes in the shared input); **the shared input and every question's instructions and criteria together must fit in 262,144 tokens**, each of type `noul` (yes/no: a calibrated probability from 0.01 to 0.99 - so a threshold above 0.99 never fires), `choice` (2-255 options, per-option probabilities) or `score` (2-255 ordered rubric levels; the score is the probability-weighted level index), plus a `confidence`. Output tokens are always 0; the shared input bills once per request at $0.10 per 1M, and each question adds its own instruction and criteria tokens. No batch, caching, or Flex/Priority; conversation history, thoughts and tool blocks can't be input (serialize them as text). Use generated text or structured output instead when you need explanations, extracted values, or tool calls with arguments.

Writing the questions is prompt engineering of its own (Google's best practices):
- **One decision per question**, combined in code with ordinary `if`s and weights. Questions run in isolation and can't see each other.
- **Write the full question in `instructions`** - "The model never sees question keys or your variable names."
- **Describe every option and level**, make adjacent score levels clearly distinct, and keep scales linear (2-10 levels for most rubrics): the score averages indices, so 1 / 10 / 100 / 1000 skews it.
- **Plan for inputs that fit no option:** threshold `confidence`, add a yes/no scope check ("Is this message about an order?"), or add a catch-all with a non-positional key such as `other` - option keys are sorted alphabetically, so `none_of_the_above` lands ahead of `shipping`.
- **Prefer positive phrasing** ("Is the tier Gold?", then 1 - p in code) over negated questions.
- **Send only the fields the questions need** ("Unrelated content lowers accuracy"), and compare numbers, dates and durations in code, passing the result or a named bucket.
- **Treat input as untrusted:** "User-supplied text can argue for its own classification." Write explicit criteria, test adversarial examples, and keep a second check on high-stakes actions.
- **Set thresholds from labeled examples of your own traffic**, weighing a false positive against a false negative (`evals.md`, judges).

## Caching

**Implicit caching is automatic** (stateful and stateless) - no setup; cached tokens appear in `usage.total_cached_tokens`. To raise the hit rate, put large, common content (system instruction, tool defs, shared context) at the **start** and send same-prefix requests close together; continuing conversations with `previous_interaction_id` also improves implicit hits. **The minimum cacheable input is 4,096 tokens on Gemini 4 and all current 3.x models** (2,048 on 2.5; some Vertex Argon pages say 6,144 - design for the larger number). **Argon's agent-loop rule** (documented for Argon; assume it for Carbon and Hydrogen until Google says otherwise): "Gemini caches the full previous request only if the new request adds at least 2,050 tokens" (model output, thoughts, and function results all count); smaller additions re-process the last 2,050 tokens at the full input rate - so tiny tool-loop turns cache worse than you'd expect. **Explicit caching** (cache once, reference by handle) gives guaranteed savings at scale, TTL 1 hour by default with a per-hour storage charge - but it is **not available on the Interactions API, or on any Gemini 4 model** (Argon, Carbon, Hydrogen) at all; use `generateContent` with a supported 3.x model if you need it. Gemini 4 cached input is 0.05× (95% off; vs ~0.1× on Flash).

## Long context

The 1M window makes "put everything in context" viable, but mind recall (and on Gemini 4 models the window is shared with thinking and output - a 900K-token prompt leaves little room to answer): single-needle retrieval is ~99%, **multi-needle recall degrades** - when you need several distinct facts pulled reliably, prefer separate targeted requests. Put the query **last**, after the context, with an anchoring phrase. Longer inputs raise time-to-first-token; pair reused large contexts with caching.

## Non-English output

Gemini needs **aggressive** language enforcement to hold a non-English output language: *"RESPOND IN {LANGUAGE}. YOU MUST RESPOND UNMISTAKABLY IN {LANGUAGE}."* Also note 3.8 Flash's model card reports a slight **regression in non-English safety** vs 3.7 Flash - test safety behavior in each target language if it matters. Google hasn't published Gemini 4 language guidance; keep the enforcement clause and test.

## Temporal grounding

Cutoffs differ by model - **March 2026 for Argon and 3.6-3.8 Flash** (with some domains still at Jan 2025), **January 2025** for 3.5 Flash-Lite and 3.1 Pro; Google hasn't published Carbon's or Hydrogen's. For anything past the cutoff, enable Search grounding. For time-sensitive tasks, anchor the date explicitly (Google's clause above: *"Remember it is 2026 this year"*) and tell the model its cutoff - Gemini benefits from being told both even though it can search.

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

Gemini 3 defaults can raise token use for PDFs and lower it for video; reduce resolution explicitly if requests overflow. **Agentic video understanding** (the model seeks through a video rather than reading fixed frames) is GA but **off by default on Gemini 4 models** - uploaded videos use `media_processing="static"`; set `"agentic"` to turn it on.

**Troubleshooting.** If the model misses details, hint *which* aspects to draw from; if output is generic, ask it to **describe the image first**, then answer; to curb fabrication, ask for shorter descriptions (keep temperature at the default). Image segmentation is unsupported on Gemini 3. Gemini 2.5 Flash (thinking off) did it, but it is retired on Vertex and reroutes to 3.5 Flash-Lite on the Gemini API from Dec 1 2026, so plan another route for segmentation. **Computer Use** is a built-in client-side tool (GA since Oct 30 2026) on current Flash models and all three Gemini 4 models - intent-based actions across browser / mobile / desktop, no separate model. Its safety layer is configured, not prompted: built-in policy categories (`FINANCIAL_TRANSACTIONS`, `SENSITIVE_DATA_MODIFICATION`, `COMMUNICATION_TOOL`, `ACCOUNT_CREATION`, `DATA_MODIFICATION`, `USER_CONSENT_MANAGEMENT`, `LEGAL_TERMS_AND_AGREEMENTS`) block or require confirmation; function calls can carry a `safety_decision` of `require_confirmation` - prompt the user and return `safety_acknowledgement` in the result. **Always handle that decision even if you set overrides** (overrides are preferences, not guarantees). From 3.5 Flash on, opt-in **prompt-injection detection** scans screenshots for hidden instructions and blocks execution (off by default - turn it on). Pair with a custom safety system instruction, a sandboxed VM/container/browser profile, and human-in-the-loop for consequential actions.

## Flash tier and inference tiers (Flex / Priority)

Pick by workload: **Carbon** for the hardest, deepest work and as orchestrator or verifier; **Argon** for most advanced work at lower token use; **Hydrogen** as the default for everyday coding, tool-using agents and parallel subagents (it replaces 3.8 Flash; same price as 3.8 Flash's list price from Jan 2027); **3.8 Flash** only for existing tuned prompts until you've re-run evals on Hydrogen; **3.6 Flash** when you need `minimal` thinking on a Flash-class model (3.7 Flash, the compute-efficient option, now routes to 3.8); **3.5 Flash-Lite** for high-volume classification, routing, and extraction (raise its `thinking_level` for a cheap accuracy boost on ambiguous inputs). Give Flash-Lite more explicit instructions and more (simpler) examples, and keep its tool set small.

Separately, **Flex** (batch-tolerant, ~50% cost) and **Priority** (faster, steadier latency at a premium) inference tiers apply per request, independent of the model.

## Migration to Gemini 4 Argon or Carbon

From 3.1 Pro Preview (Google Cloud's recommended path) or from a Flash model being promoted to the top tier. Google's `gemini-api-dev` skill offers `migrate my app to Gemini 4 Argon` (or Carbon).
- Model ID `gemini-4-argon` or `gemini-4-carbon` (both stable). Treat it as a new family, not a drop-in: re-run evals at `low`, `medium`, and `high` and keep the lowest level that passes.
- **Raise `max_output_tokens` to ≥ 32,768** (check framework and eval-tool defaults too); lower `thinking_level` to cut tokens instead of shrinking the cap. Raise client timeouts to ≥ 15 minutes or use background execution.
- Remove `temperature` / `top_p` / `top_k` (ignored, 400 later), `candidate_count`, `frequency_penalty`, `presence_penalty`, any `thinking_budget`, and `minimal`.
- **Drop assistant prefill** and histories ending on a `model` turn; force shape with `response_schema`.
- **Explicit caches don't carry over** - rely on implicit caching: static prefix first, ≥ 4,096 tokens, and expect weaker hits on small agent-loop turns (the 2,050-token rule).
- Function calling: exact id/name/order symmetry on responses; no free text before calls (use an `update()` function); prefer sequential tool turns.
- Remove word-count and length targets from prompts - Gemini 4 models ignore them; trim elaboration nudges written for terser 3.x models and re-check output length.
- Rewrite long agentic prompts around a **measurable goal + a verification script + a stated deliverable**, and move conventions into `AGENTS.md`/skills (see *Prompting Gemini 4 Argon*).
- Budget: $2 / $10 until Nov 30 2026, then **$4 / $20** - compare cost per task against GPT-6 Astra and Claude Opus 5.5 at the price you'll actually pay.
- **Argon → Carbon:** "no request schema changes" - change the model string, keep `thinking_level` at `medium` unless a workload needs `high`, and make room in `max_output_tokens` and HTTP timeouts for longer turns. Keep Argon where speed and token spend matter; re-run evals rather than assuming Carbon is better on your task. See *Prompting Gemini 4 Carbon*.
- **Thought signatures:** follow the Gemini 4 rules in *Thought preservation and signatures* (every earlier turn's signatures; first parallel call only; set `prefix_mismatch_behavior="DROP"` if your harness edits or compacts history).

## Migration to Gemini 4 Hydrogen (from 3.8 Flash)

Google's recommended path for 3.8 Flash and earlier Gemini 3 / 2.5 workloads; `gemini-api-dev` offers `migrate my app to Gemini 4 Hydrogen`.
- Model ID `gemini-4-hydrogen`; upgrade the Gen AI SDK (Vertex guide: Python `google-genai` ≥ 2.34.0, JS `@google/genai` ≥ 2.32.0).
- **Window:** 3.8 Flash had separate 1M input / 64K output budgets; Hydrogen shares one 1,048,576-token window across input, thinking and output, with a 65,536-token default and per-request cap. Remove low hardcoded `max_output_tokens` caps or raise them to 65,536; past 64K use background execution or client-side continuation (*Output budget and long decode*).
- **Thinking:** default moves from `medium` to **`high`**, `xhigh` is new, `minimal` is rejected (and `thinking_budget` is a 400 on Vertex - use `thinking_level` only). Test `medium` and `high` on your evals; set the level explicitly.
- **Caching:** no explicit caching - remove `cached_content`; implicit caching applies to prefixes of 4,096+ tokens at 95% off, so put static content first.
- Remove `temperature`, `top_p`, `top_k` (ignored), and per Vertex's guide `frequency_penalty`, `presence_penalty`, `candidate_count` above 1, and prefilled model turns.
- **Tools:** declare them natively (no prompted raw-JSON tool calls); keep thought signatures per the Gemini 4 rules (*Thought preservation and signatures*).
- **Billing:** every token is billed, including thinking and the grounding tool's internal instructions and declarations; Search grounding still bills per query.
- Re-run evals: Hydrogen is a different model, not a faster 3.8 Flash; Google reports far fewer fabricated claims and more flagged gaps, which can change pass rates on tasks that rewarded a confident answer.

## Migration to Gemini 3.8 Flash

Google's `gemini-api-dev` skill can automate this for coding agents.
- Update the model ID to `gemini-3.8-flash` (`gemini-3.7-flash` is deprecated and already routes there); pin explicit IDs, not `-latest` aliases (alias targets shift; `gemini-3-pro-preview` was already retired → `gemini-3.1-pro-preview`).
- **Replace `thinking_level:"minimal"` with `low`** (or route that traffic to Flash-Lite) - `minimal` errors on 3.8. Replace numeric `thinking_budget` with `thinking_level`; never send both.
- Remove `temperature`, `top_p`, `top_k`, and `candidate_count`.
- **Move to the Interactions API** for new work: standardize multi-turn on `previous_interaction_id`, **re-send `system_instruction` / `tools` / `generation_config` every call**, and decide on `store` (default retention 55 days).
- **Drop assistant prefill** - a history ending on a non-empty `model` turn returns 400. Force shape with structured output.
- Audit function calling: multimodal assets inside the response payload; inline guidance separated by `\n\n`; ids/`call_id` on every response; remove structured pre-tool text (see *Function calling*) if you hit `Malformed_Function_Call`.
- Keep thought signatures round-tripping in stateless mode (or go stateful).
- **Expect higher token use on 3.8 Flash** and budget for the Jan 1 2027 price doubling; compare cost-per-task against 3.6 Flash and Argon `low`.
- The knowledge cutoff advanced to **March 2026** from 3.6 Flash on - you can drop date-anchoring workarounds for facts it now knows, but keep telling it the current date.
- Re-test: Gemini 3.x is terser and more direct - prompts written for a chattier older model may need an explicit elaboration request.
