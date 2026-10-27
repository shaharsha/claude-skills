# Grok (xAI) - Provider Deep-Dive

Applies to the **Grok model family** wherever it runs: the xAI API (`api.x.ai`; the company now also brands itself "SpaceXAI" / "SpaceXSI" in docs - same API, same `grok-*` IDs), AWS Bedrock, Microsoft Foundry, Oracle OCI, Google Vertex / Gemini Enterprise Agent Platform, OpenRouter, and Vercel AI Gateway. Prompting is the same everywhere, but **a few API behaviors differ by host** (server-side tools, whether `max_output_tokens` counts reasoning) - see *Third-party hosts*.

**Current models (late October 2026):** xAI doc pages are undated - re-check before trusting this list. **No Grok 5** has been announced.

- **Grok 4.7** (`grok-4.7`, Sept 21 2026) - the flagship: "For everything else, including code, use Grok 4.7. It is the most capable model we've built." **500K context** (down from 1M on 4.3 / 4.20). **Reasoning is always on** ("Reasoning cannot be disabled"); effort `low` / `medium` / **`high` (default)** / `xhigh`. Text + image in, text out. **$2 / $6 per 1M, cached input $0.50 (0.25×)** below 200K prompt tokens; **at ≥200K prompt tokens every token in the request bills at double** (cached tokens count toward the threshold). Batch 20% off, Priority 2×, US-only endpoint (`us.api.x.ai`) 1.1×. Knowledge cutoff May 2026 per the docs (the model card says June 2026 pretraining plus data to August in supplemental training). `max_output_tokens` defaults to 128,000. Co-developed with Cursor (supplemental training on Cursor workflow data).
- **Grok 4.6** (`grok-4.6`, Aug 12 2026) - same price, context, and effort range; superseded by 4.7.
- **Grok 4.5** (`grok-4.5`, July 2026; alias `grok-build-latest`) - same price, cached input $0.30; `xhigh` "treated as `high`" per the reasoning page (the model page disagrees).
- **Grok 4.3** (`grok-4.3`, Apr 30 2026) - cheaper ($1.25 / $2.50, cached $0.20), 1M context, effort includes **`none`**, **default `low`**. The redirect target for retired models.
- **Grok 4.20** (`grok-4.20-0309-reasoning`, `grok-4.20-0309-non-reasoning`, March 2026) - 1M context, $1.25 / $2.50. **`grok-4.20-0309-non-reasoning` is the only current non-reasoning Grok ID.** xAI markets 4.20 reasoning as "the lowest hallucination rate on the market with strict prompt adherence."
- **Grok 4.20 Multi-Agent** (`grok-4.20-multi-agent-0309`, beta) - effort sets the **number of agents**, not depth (`low`/`medium` = 4, `high`/`xhigh` = 16); only the leader's output returns; **no client-side tools, no Chat Completions, no `max_tokens`**.
- **Grok Build 0.1** (`grok-build-0.1`, early access; aliases include `grok-code-fast-1`) - coding model, 256K, $1 / $2; no Batch.
- **Grok 4.7 Fast** is *not* an API model - "the same model served on faster infrastructure", only in Cursor and Grok Build.
- **Retired May 15 2026 and silently redirected:** `grok-4-0709`, `grok-4-fast-*`, `grok-4-1-fast-*`, `grok-3`, `grok-code-fast-1`. Reasoning slugs now serve `grok-4.3` at `low`, non-reasoning slugs `grok-4.3` at `none`, `grok-code-fast-1` → `grok-build-0.1` - **billed at the new model's price**. Old IDs in code still "work" but run a different model; switch explicitly and re-run evals.
- Non-text: `grok-imagine-image-2.0` (recommended; `-quality` retires Nov 2), `grok-imagine-video-1.5`, `grok-voice-3.0`.

## Contents
- API surface and recognising Grok in code
- Reasoning and the encrypted-reasoning contract
- Sampling and rejected parameters
- Effort and cost
- Prompting Grok 4.7
- Content controls, persona, and safety
- Function calling
- Server-side tools (Agent Tools)
- Structured outputs
- Caching
- Long context and compaction
- Multimodal
- Third-party hosts
- Migration

## API surface and recognising Grok in code

- **Use the Responses API.** "Use the Responses API. Chat Completions is deprecated." - and "Results from it understate what Grok reasoning models can do, especially across multiple turns and tool calls." (No sunset date yet; Chat Completions has no field for encrypted reasoning.) The **Anthropic-compatible `/v1/messages` is "fully deprecated"**, and legacy `/v1/completions` doesn't support reasoning models.
- **Responses state:** `store` defaults to **true** and responses are kept **30 days**; chain turns with `previous_response_id`. `instructions` (the system prompt) **cannot be combined with `previous_response_id`** - the chained response's original system prompt is used, so change instructions by appending a message instead. Team-wide ZDR disables the stateful Responses API, Files, Collections, Batch, and deferred completions.
- **Live Search is gone:** `search_parameters` returns **410** ("Live search is deprecated. Please switch to the Agent Tools API"). Use server-side `web_search` / `x_search` tools.
- **SDKs:** the official Python gRPC SDK `xai_sdk` (`Client().chat.create(model="grok-4.7")`, `chat.append(user(...))`, `chat.sample()`), the official TypeScript SDK `@xai-official/sdk`, the OpenAI SDK with `base_url="https://api.x.ai/v1"`, or Vercel's `@ai-sdk/xai`.
- **Recognition signals:** `api.x.ai` / `us.api.x.ai`; `XAI_API_KEY`; imports `xai_sdk`, `@xai-official/sdk`, `@ai-sdk/xai`; model strings `grok-*`, `x-ai/grok-*` (OpenRouter), `xai/grok-*` (LiteLLM, Vertex), `xai.grok-*` / `global.xai.grok-*` (Bedrock, OCI), `spacexai/grok-*` (Vercel); the `x-grok-conv-id` header; fields `use_encrypted_content`, `store_messages`, `max_turns`, `server_side_tool_usage`, `cost_in_usd_ticks`, `guidelines`, `safety_identifier`; tool types `x_search`, `code_execution`, `collections_search`.

## Reasoning and the encrypted-reasoning contract

- **Always on** for 4.5 / 4.6 / 4.7; set the depth with `reasoning={"effort": …}` on Responses (or flat `reasoning_effort` on Chat Completions / `xai_sdk`). xAI: set effort "explicitly on every request so a default never decides your result."
- **Pass the reasoning back.** "On the Responses API, `grok-4.7` returns `reasoning.encrypted_content` on every response … pass them back unchanged in the next request's `input` so the model keeps its reasoning across turns." Two supported patterns: chain with `previous_response_id` (with `store` on), or `store: false` + `include: ["reasoning.encrypted_content"]` and append **every output item** yourself. xAI's list of mistakes, worth checking any harness against: a loop that "extracts `output_text` and appends it as a plain assistant message"; one that "edits, reorders, or filters output items before sending them back. Pass them back exactly as received"; and one that "rebuilds the conversation from a transcript in a different format, such as a Chat Completions `messages` array." Getting this right "drastically improves performance on multi-turn conversations and agent loops" and is also the top cause of cache misses (below).
- **Readable reasoning** is a summary (`response.reasoning_summary_text.delta` / `reasoning_text.delta`); `reasoning.summary` is ignored ("always return `detailed`").
- **Budget and timeouts:** on the xAI API "`max_output_tokens` caps only the visible answer; reasoning and function call tokens do not count toward it" (128,000 default) - treat `status: "incomplete"` as truncated. **On Azure Foundry the cap includes reasoning.** Reasoning tokens bill at the output rate (`usage.output_tokens_details.reasoning_tokens`; `usage.cost_in_usd_ticks` gives the cost). "Set the client timeout to at least 900 seconds"; hard evals can exceed 1,800 s per request.

## Sampling and rejected parameters

Grok is the exception to SKILL.md's "omit sampling parameters" default - xAI asks you to **set** them:

- "Set `temperature` to 0.7 and `top_p` to 0.95, and don't deviate far from these values. Grok models don't respond well to other sampling settings, and quality usually drops when you change them." The server also caps them (temperature ≤ 1, top_p ≤ 0.95; higher values are sampled at the cap but echoed back unchanged).
- **Errors on reasoning models:** `stop`, `presence_penalty`, `frequency_penalty`. Also 400: a `guidelines` field combined with `stop` or on the multi-agent model.
- **Silently ignored:** `logprobs` / `top_logprobs` (Grok 4.20 and newer), `logit_bias`, `truncation`, `metadata`, `background`, `context_management` ("parsed but not yet executed"), and `strict` inside a JSON schema (strictness is always on).
- Reasoning models aren't deterministic; `seed` is best effort. xAI's eval advice: "Run each item several times, report the mean and spread."

## Effort and cost

Grok 4.7's main cost is its token appetite: Artificial Analysis measured **~81K output tokens per Intelligence Index task at `xhigh`** - 2.25× Grok 4.6 and ~3× GPT-6 Astra - for +2 index points, "very verbose" (240M tokens vs an 87M median), $3.74 per task. Community reports (Cursor forum) consistently mention verbosity, long "exploring" phases, and overthinking at `high`.

- **Start at `low` or `medium`, not the `high` default.** xAI's own effort cookbook on short support tickets: `medium`, `high`, and `xhigh` used about the same ~600 reasoning tokens; **`low` used ~140 and cost half as much, and every effort scored 87-93%.** Per xAI's table: `low` for latency-sensitive agentic use and simple tool calling; `medium` for complex data analysis and long-context reasoning; `high` for very challenging problems; `xhigh` for the hardest work where quality outweighs latency.
- **Effort doesn't buy premise-checking:** on BullshitBench, Grok 4.3 and 4.6 pushed back on nonsense *less* at higher effort (4.6: 66% clear pushback at minimal vs 56% at max). Grok 4.7 isn't scored yet.
- Moving from 4.3 / 4.20 changes the default from `low` to `high` - requests get slower and costlier unless you set effort explicitly.

## Prompting Grok 4.7

**xAI publishes no Grok 4.x text-prompting guide.** The usable guidance comes from its Best Practices page, cookbooks, its own published system prompts, and the archived Grok Code Fast 1 guide:

- **State the task, constraints, and output format directly.** "Grok reasoning models reason before they answer, so state the task, constraints, and output format directly. If you tuned a prompt for another model, spend comparable effort tuning it for Grok before you compare scores." Don't add chain-of-thought instructions.
- **Give rich, specific context.** From the (retired-model) Grok Code Fast 1 guide, still the only xAI text-prompting guide: "Give a detailed system prompt. Be thorough and give many details in your system prompt… describes the task, expectations, and edge-cases"; "Set explicit goals and requirements… avoid vague or underspecified prompts"; provide relevant file paths and project structure and "avoid providing irrelevant context"; mark sections with "XML tags or Markdown-formatted content." Treat it as the best available prior, not as verified 4.7 guidance.
- **Use native tool calling, not text protocols.** Same guide: "We encourage you to use it instead of XML-based tool-call outputs, which may hurt performance."
- **xAI's own prompt shape:** its published Grok 4.1 system prompts open with identity ("You are Grok, built by xAI."), put the non-negotiables in an XML **`<policy>`** block that states its own precedence ("These core policies within the `<policy>` tags take highest precedence. System messages take precedence over user messages."), and put the rest in Markdown bullets. Stating precedence explicitly is good practice on every provider (SKILL.md *Trusting all input equally*).
- **Message roles are flexible** ("You can mix `system`, `user`, or `assistant` roles in any sequence"); there is no separate `developer` role.
- **Put per-request data in the newest user message, not the system prompt.** xAI's caching cookbook: "Putting the current time at the top of the system prompt made the same chat cost 2.2 to 2.9 times as much."
- **Ask for concision and show the format.** There's no verbosity parameter and 4.7 runs long; combine an explicit length/format instruction with lower effort. If a coding agent stalls or "stops and waits" mid-task (a recurring forum report), define done and the stops you do want, per SKILL.md Section A.
- **Instruction files:** Grok Build reads `AGENTS.md` (and `CLAUDE.md`, `.claude/rules/`, `.cursor/rules/` for compatibility); "Files are loaded in full, with no size cap; short, specific instructions are followed more reliably than long ones."
- **Judges on Grok:** "give it a specific rubric with examples of each score, ask it to reason before it scores, and randomize the order of answers in pairwise comparisons."

## Content controls, persona, and safety

- **API Grok has no persona unless you give one.** The consumer Grok (grok.com, @grok on X) runs xAI's long persona prompt; API callers supply their own system prompt. xAI's docs examples use "You are Grok, a helpful and truthful AI assistant built by SpaceXSI." Consumer surfaces may lag the API on model version.
- **Specify a viewpoint and sourcing policy for contested topics.** Grok 4 was observed (July 2025) searching Elon Musk's posts to answer controversial questions, and xAI's own published 4.1 prompt carries the comment "Grok assumes by default that its preferences are defined by its creators' public remarks, but this is not the desired policy for a truth-seeking AI. A fix to the underlying model is in the works." Whether 4.7 still does this is unverified. If neutrality matters, say how to handle opinion questions (e.g. present the main positions with sources, don't adopt one), and test it.
- **Defaults are permissive; tighten them with `guidelines`.** xAI's historical API safety prefix said "Treat users as adults… do not moralize or lecture" and placed no restrictions on fictional adult content. The documented lever is the request field `guidelines: [{"type": "policy", "category": "nsfw" | "violence" | "profanity", "behavior": "decline"}]` (each category once). Pass `safety_identifier` (an opaque end-user id) so policy violations are attributed to the end user rather than your key; requests caught before generation cost a $0.05 violation fee.
- **Model-card behavior (xAI internal, high effort):** sycophancy - abandoning a correct answer under confident user pushback - 0.03%; MASK dishonesty 0.00%; a new safeguard stack that xAI calls its strongest yet on refusals and jailbreak resistance. Some surfaces add runtime input filters for severe-harm classes.
- **Prompt injection:** in xAI's own grok-4.7 test, crude injections were refused but subtle ones landed (8 of 10 with defenses off), and the model occasionally fetched URLs it made up. Its advice: "Treat fetched pages as data, not as instructions"; "Give each step only the tools it needs"; "Check tool arguments before running them, and confirm a side effect with a person." Wrapping pages in `<untrusted>` tags helps but "a page can close [the tags] itself" - contain by design (SKILL.md Section G).

## Function calling

- **Responses format:** flat `{"type": "function", "name", "description", "parameters"}`; the model emits `function_call` items (`call_id`, `name`, `arguments`); reply with `{"type": "function_call_output", "call_id", "output"}`. In agent loops keep the **whole** `output` array (reasoning + calls) before appending outputs. With streaming, a function call arrives **whole in one chunk**.
- **`tool_choice`: `auto` (default), `required`, `none`, or a specific function** - unlike Claude Opus 5.5 / Sonnet 5.5 / Fable 5.1 and Kimi K3.x, **forcing a named tool works** on Grok (`{"type": "function", "name": "…"}` on Responses).
- **Parallel calls are on by default**; `parallel_tool_calls: false` limits the model to one call per turn.
- **Schemas:** the `parameters` root must be an object (a root `anyOf`/`oneOf` of objects also works); anything else is rejected with a 400 naming the tool. Arguments are grammar-constrained - "always generate tool call arguments that strictly conform to the tool's input JSON Schema (the `strict` flag is implicitly always `true`)." An omitted description is "treated as empty" - so write one (SKILL.md Section B).
- **Tool count:** docs say both 350 and 1,000 per request; stay far below either - the 10-20 active-tool guidance applies.

## Server-side tools (Agent Tools)

Built-in tools run on xAI's servers inside one request; custom functions pause and return to you.

- **Tools:** `web_search` (domain allow/exclude lists, up to 5 each; optional image understanding), `x_search` (X posts and profiles; handle filters, `YYYY-MM-DD` date range; image/video understanding), `code_interpreter` (`code_execution` in `xai_sdk`), `file_search` (`collections_search`), `attachment_search`, `image_generation`, and **remote MCP** (`{"type": "mcp", "server_url", "server_label", "allowed_tools", …}`; Streamable HTTP or SSE). Priced per 1K successful calls ($5 web search; X search $5 / 1K posts, $10 / 1K profiles; $2.50 file search); remote MCP is token-billed.
- **You don't see server-side tool outputs** - "Only the tool call invocations are shown." Ask the model to cite what it relied on.
- **Inline citations are on by default** in the Responses API, as `[[N]](url)` markers in the text; disable them with `include: ["no_inline_citations"]` if your UI renders sources separately (and see `gpt.md` on how footnote-style markers can confuse other models in a mixed pipeline).
- **`max_turns`** limits server-side tool turns within one request (client-side calls reset it); it doesn't cap the number of individual calls.
- **Remote MCP:** without `allowed_tools`, "all tool definitions exposed by the MCP server are automatically injected into the model's context" - always set it. `require_approval` is **not supported**, so approval gates for MCP actions must live in your harness or on the MCP server.
- **Not on Bedrock** (no server-side tools there) and not with the multi-agent model's client tools.

## Structured outputs

`text.format` (Responses) or `response_format` `json_schema` (Chat Completions); "When using supported schema features, the response is guaranteed to match your schema." Supported: string/number/integer/boolean/null, `enum`, `const`, arrays, objects, `anyOf`/`oneOf`, single-subschema `allOf`, non-circular `$ref`/`$defs`; enforced formats `date`, `time`, `date-time`, `email`, `uuid`, `ipv4`, `ipv6`, `uri`. Guaranteed limits: string length ≤ 2,048, items ≤ 256, properties ≤ 64. **`additionalProperties` defaults to `false`.** `pattern` is an ECMA-262 subset - no backreferences, lookaround, `\b`, or `\p{}`, and **`^`/`$` are implicit** (the pattern matches the whole string). Best-effort only: `not`, `if/then/else`, multi-schema `allOf`. Structured outputs combine with tools on supported Grok 4 models.

## Caching

- **Automatic prefix caching** on all Grok language models; cached input bills at 0.25× ($0.50 vs $2 on 4.7). Read hits in `usage.input_tokens_details.cached_tokens` (Responses), `usage.prompt_tokens_details.cached_tokens` (Chat Completions), `usage.cached_prompt_text_tokens` (`xai_sdk`). Cached tokens still count toward TPM.
- **Set a routing key - xAI calls this essential:** "We highly recommend setting a `prompt_cache_key` (Responses API; `x-grok-conv-id` header on Chat Completions). It routes a conversation's requests to the same server, making cache hits reliable; without it you often pay full input price on a cache-cold server." Use the conversation id; on gRPC pass `x-grok-conv-id` as metadata.
- **128-token blocks** (measured by xAI's cookbook; no documented minimum) - the last partial block is always uncached.
- **What breaks it:** editing, removing, or reordering earlier items ("only append new ones"); **dropping the reasoning** ("omitting it is the top cause of cache misses"); per-request data in the system prompt; and compaction (the turn after a compaction re-caches from scratch).

## Long context and compaction

- **500K tokens on 4.7** (1M only on 4.3 / 4.20). Past **200K prompt tokens the whole request bills at 2×** - compact or retrieve rather than stuffing. Artificial Analysis measured a **long-context regression** on 4.7 (AA-LCR −3.7 points vs 4.6), so don't assume a longer window means better recall.
- **Compaction API** (`POST /v1/responses/compact`) returns one opaque `compaction` item (encrypted; don't parse or edit it). **Ordering matters:** "A compaction item has to come first, because the API drops anything before it, `instructions` included" - put the system prompt as a message **right after** the compaction item. In xAI's test, putting it before the item or in `instructions` dropped a reference handbook "entirely, and Grok made up menu details." Summary length varied from 15 to 2,350 tokens (the 15-token one forgot a key fact), and for short chats compaction "cost more than it saved" - compact only long sessions, and verify critical facts survive.

## Multimodal

Grok 4.7 takes images (jpg/png, ≤ 20 MiB, any number, any order with text; `detail` `auto`/`low`/`high`). "When sending images, it is advised to not store request/response history on the server. Otherwise the request may fail" - use `store: false` with encrypted reasoning for image conversations. Search tools can view images (and X videos) they find. Image and video generation are separate `grok-imagine-*` models or the `image_generation` tool.

## Third-party hosts

| Host | Model ID | Differences |
|---|---|---|
| AWS Bedrock | `xai.grok-4.7` via `global.xai.grok-4.7` / `us.xai.grok-4.7` (no in-Region) | OpenAI-compatible base `bedrock-runtime.{region}.amazonaws.com/openai/v1` plus Converse/Invoke; **no server-side tools**; implicit caching only; 524,288-token shared window. In Converse, effort goes in `additionalModelRequestFields` and **reasoning arrives in the first content block** - search blocks by type, don't read `content[0]`. EOL no sooner than Sept 28 2027. |
| Microsoft Foundry | your deployment of `grok-4.7` | **`max_output_tokens` includes reasoning** (unlike xAI); the Responses table lists only `low`/`medium`/`high` (Chat Completions accepts `xhigh`); Live Search options don't apply. GA Grok models stay at least six months. |
| Oracle OCI | `xai.grok-4.7` | On-demand only; hosted by xAI. |
| Vertex AI / Gemini Enterprise Agent Platform | `xai/grok-4.7` | OpenAI-compatible Responses and Chat Completions. |
| OpenRouter | `x-ai/grok-4.7` | 450K max output; no `stop`. |
| Vercel AI Gateway | `spacexai/grok-4.7` | `reasoning: 'xhigh'` in the AI SDK. |

## Migration

- **4.6 → 4.7:** same price, context, and effort levels. Responses now **always** returns encrypted reasoning - make sure your loop sends output items back unchanged. Expect about 2× output tokens per task: raise timeouts and budgets, and try `low`/`medium`.
- **4.3 / 4.20 → 4.7:** context drops from 1M to 500K; price rises to $2 / $6; no `none` effort and no non-reasoning sibling; default effort rises from `low` to `high` - set it explicitly. Keep `grok-4.20-0309-non-reasoning` for traffic that must not reason.
- **Retired IDs** (Grok 4, 4 Fast, 4.1 Fast, Grok 3, `grok-code-fast-1`) silently redirect - replace them and re-run evals.
- **API:** Chat Completions → Responses (`messages` → `input`, `max_tokens` → `max_output_tokens`, keep full output items); `search_parameters` → `web_search` / `x_search` tools; Anthropic `/v1/messages` → Responses or gRPC; remove `stop` and the penalties; pin `temperature` 0.7 / `top_p` 0.95; add `prompt_cache_key`.
- **Prompts:** prompts tuned for another provider need their own tuning pass on Grok (xAI's own advice); remove CoT scaffolding; move timestamps out of the system prompt; add a `guidelines` policy if your app needs stricter content limits than Grok's defaults.
