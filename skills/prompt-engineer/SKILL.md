---
name: prompt-engineer
description: "Use ANY time an LLM-powered agent, chatbot, or AI assistant is being built, debugged, reviewed, planned, or migrated — the user almost never says 'prompt.' They say 'the agent keeps calling the wrong tool,' 'why is it ignoring my instructions,' 'fix this bug,' or just paste a log. TRIGGER when (1) any file in scope contains a system prompt, tool/function description, function-calling schema, tools.json, agents/* file, or imports an LLM SDK (anthropic, openai, google.genai, AWS Bedrock, Vertex, Azure OpenAI); (2) an agent loops, picks the wrong tool, hallucinates arguments, runs verbose despite low-verbosity settings, over- or under-escalates, ignores instructions, or shifts behavior after a model upgrade; (3) the user is thinking through or planning agent architecture — subagents, orchestrator/worker splits, state passing, multi-agent workflows — before code is written; (4) the user is comparing providers, migrating a prompt to a newer model, or asking 'is this good enough.' Covers Claude/Anthropic, GPT/OpenAI (incl. Azure), and Gemini/Google (incl. Vertex). Invoke proactively the moment you see prompt-shaped text or an LLM SDK call in scope — do not wait for the user to ask. SKIP only when no LLM agent is in the loop (pure SQL, infra, normal code with no model in scope, human prose editing)."
---

# Prompt Engineering for AI Agent APIs

> **First step (do this NOW, before reading further):** run `touch /tmp/.prompt-engineer-skill-loaded` once. The `~/.claude/hooks/protect-prompts.sh` PreToolUse hook blocks Edit/Write on prompt files (`prompts/`, `system_prompt*`, `agents/tools/`) until that flag exists; setting it confirms you've loaded these guidelines and lets subsequent edits proceed without re-loading the skill.

Guidelines for writing system prompts, tool descriptions, and agent instructions for building AI agents via the Claude, GPT, and Gemini APIs. This covers both prompt engineering (crafting instruction text) and the broader discipline of context engineering (orchestrating everything the model sees — tools, memory, retrieved documents, state — to maximize the likelihood of desired behavior).

## Step 0 — MANDATORY before anything else

Before reading the rest of this skill, do these two things in order. They are not optional and they are not "later." Skipping them is the #1 failure mode of this skill: the user repeatedly has to ask "did you read the provider-specific md?" because the universal section below got read in isolation and the version-specific knobs were never loaded.

### 0a. Identify the model family in scope

Look at the code, the file being edited, the SDK being imported, or what the user just said. Match against these signals — first hit wins. Split by **model family, not platform**: prompt engineering is identical whether GPT runs on OpenAI or Azure, or whether Claude runs on Anthropic or AWS Bedrock.

| Signal seen in code / file / prompt                                                                                                                            | Family   |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| `from anthropic`, `Anthropic(`, `AsyncAnthropic(`, `@anthropic-ai/sdk`, model id matches `claude-*`, AWS Bedrock `anthropic.claude-*`, Vertex `claude-*`       | claude   |
| `from openai`, `OpenAI(`, `AzureOpenAI(`, `chat.completions.create`, `responses.create`, model id matches `gpt-*` / `o1*` / `o3*` / `o4*` / `text-embedding-*` | gpt      |
| `from google import genai`, `google.generativeai`, `GenerativeModel(`, model id matches `gemini-*`, Vertex `publishers/google/models/gemini-*`                 | gemini   |

If you see **more than one** family (cross-provider code, comparison work, or a router), load all matching reference files. If you see **none** (the user is asking abstractly, e.g. "how should I structure a system prompt"), ask which provider/model they're targeting before continuing — do not guess. A wrong-provider answer is worse than one clarifying question.

### 0b. Read the matching reference file(s) NOW

- claude → read `${CLAUDE_SKILL_DIR}/references/claude.md`
- gpt    → read `${CLAUDE_SKILL_DIR}/references/gpt.md`
- gemini → read `${CLAUDE_SKILL_DIR}/references/gemini.md`

Read the full file before giving advice or editing anything. The universal section below covers ~70% of prompt engineering, but the version-specific knobs (Opus 4.7 sampling removal, GPT-5.5 "stop doing" list, Gemini 3.5 thought signatures, caching mechanics, reasoning-effort defaults, migration breakages) live only in those files and change every release. Working from the universal section alone produces stale advice — the exact failure the user keeps catching.

### Red flags — STOP and go back to 0a/0b

- "I already know what Claude/GPT/Gemini wants here" — model behavior shifts every version; verify against the current reference file before recommending anything model-specific.
- "The universal section is enough for this small change" — even small prompt edits interact with provider-specific defaults (reasoning effort, thinking, caching, sampling). Load the reference.
- "I'll load it later if needed" — later never comes; the load is now, before the first recommendation.
- "The user didn't mention a provider" — check the code, imports, model strings, or filename. If still unclear, ask. Do not guess.
- "This is just a debugging question, not a prompt edit" — debugging prompts IS a prompt-engineer task. The reference file likely names the exact failure mode.

## Process

When editing an existing prompt, follow this order:
1. **Read** the full existing prompt. Understand its intent, structure, and target provider.
2. **Identify** the specific failure mode or improvement needed. Don't rewrite what isn't broken.
3. **Draft** the minimal change that addresses the issue, following the guidelines below.
4. **Re-read** the full prompt after editing to check for contradictions or broken flow.
5. **Test** the prompt on the target provider with representative inputs.

For new prompts: start minimal (role + constraints + examples + output format), test, then add instructions only when you observe failure modes.

When the prompt targets a model version newer than the one it was written for, treat it as a **new model family, not a drop-in swap**: switch the model, pin reasoning effort, re-run evals, trim instructions the new model no longer needs, and only then add new guidance. Legacy prompts routinely over-specify processes that newer models handle natively. See the provider reference file for version-specific migration notes.

Before submitting any prompt edit: check for contradictions (if two rules conflict, the model picks arbitrarily — remove one), and verify clarity (could a colleague with no context follow this prompt unambiguously?).

## A. Universal Best Practices

These apply to all three providers and cover ~70% of prompt engineering work.

### System Prompt Structure
- **Set a clear role** in one sentence at the top. Every provider respects persona framing.
- **Use XML tags** (`<role>`, `<constraints>`, `<examples>`, `<output_format>`) to separate sections. All three providers parse XML — it is the safest cross-provider delimiter.
- **Be explicit and specific.** Explain *why* a behavior matters, not just *what* to do. Models generalize better from explanations than from rigid rules.
- **Aim for the right altitude.** Sit between hardcoded if-this-then-that logic (brittle) and vague high-level guidance (under-specified). Give concrete signals while leaving room for judgment. "Minimal" does not mean "short" — it means the smallest set of high-signal tokens that fully outlines the desired behavior.
- **Lead with the outcome.** Describe the destination — success criteria, constraints, available context, allowed side effects, required output shape — rather than prescribing a step-by-step process. State stopping conditions explicitly. Reserve step-by-step process instructions for cases where the exact path is product-critical. (Strongest on GPT-5.x, but now good practice everywhere.)
- **Tell the model what TO do**, not what NOT to do. Positive framing ("Write in prose paragraphs") beats negative ("Don't use markdown").
- **Prefer decision rules over absolutes** for judgment calls. "If the action is reversible, proceed; otherwise confirm first" generalizes; "ALWAYS confirm" does not. Reserve hard rules for genuine invariants (safety, security).
- **Start minimal, then iterate.** Add instructions only when you observe failure modes. Over-engineered prompts cause over-analysis on Gemini and overtriggering on Claude.

### Few-Shot Examples
- Include **3-5 diverse examples** — one of the most reliable steering mechanisms across all providers.
- Cover typical cases, edge cases, and at least one "what not to do" example.
- Wrap in `<example>` tags with `<input>` and `<output>` sub-tags. Keep formatting identical across every example — inconsistent structure confuses the model.
- Budget models need MORE examples (5-6 minimum) with simpler patterns.

### Output Format
- **Prefer the provider's structured-output feature** over describing a JSON schema in prose: OpenAI Structured Outputs (`strict: true`), Claude Structured Outputs, Gemini `responseSchema`. These constrain the response far more reliably than prompt text and remove the validation burden from the model.
- When you must specify format in the prompt (markdown template, structured text), provide a concrete example of the expected output, not just a description.
- Use **enum arrays** for valid values rather than prose descriptions — works on all providers and improves accuracy.

### Context Engineering
- Context window is working memory. Every token competes for attention — more is not always better. Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome.
- **Put long documents at the top**, queries and instructions at the bottom. This ordering improves response quality by up to 30% on complex multi-document inputs.
- **Prefer progressive discovery** — let agents find context through tools rather than front-loading everything. Maintain lightweight identifiers (paths, names, links) and load full content dynamically. Combine upfront retrieval (fast, known-relevant) with autonomous exploration (discovers unknowns).
- **Use semantic names over technical IDs** — replace UUIDs, mime_types, internal codes with human-readable names (file names, descriptive labels). LLMs reason more accurately over natural language than opaque identifiers.
- When context grows large, ask the model to **quote relevant sections first** before reasoning — this cuts through noise and grounds the response.
- For multi-turn agents: **compact and summarize** conversation history at context limits. Maximize recall first (capture every architectural decision, unresolved issue, and key finding), then tighten for precision. Use a cheap model (Flash, Haiku) for summarization. Clearing stale tool-call results is a cheap, low-risk form of compaction — once a result has been used, the raw payload can be dropped.
- For long-horizon tasks: maintain **structured notes** (scratchpad, state JSON) outside the conversation for information that must survive compaction.
- **Irrelevant context actively degrades performance** — ruthlessly trim what the current step does not need. Performance degrades gradually (not a cliff) as context grows.

### Reducing Hallucinations
Hallucination is not one problem — different types require different mitigations.

**Factual fabrication** (model invents facts):
- "Ground all claims in [source]. Quote the relevant section before answering."
- "According to..." prompting — guide model to cite specific trusted sources.
- Use search/retrieval tools to connect to verified information rather than relying on training data.

**Premise acceptance** (model builds on false/incoherent premises):
- "Before answering, evaluate whether the question's assumptions are valid. If concepts don't belong together or the premise is incoherent, say so specifically — identify what's wrong, don't just hedge."
- Generic disclaimers ("As an AI...") and polite hedging do NOT reduce premise acceptance. Only specific identification of the flaw works.
- For agentic systems: instruct agents to verify factual claims via tools before stating them.
- **Multi-tool fan-out compounds the problem** — when a false-premise question (user cites a fabricated section, benefit name, specific number) triggers a generic "fire all relevant retrieval tools in parallel" rule, the parallel tools return *legitimate-looking adjacent data* (e.g. the kupah's equivalent benefit, the general claim-filing process, a similar-but-different section) that the agent then weaves into a reply as if it validates the fabricated premise. Mitigation: for fabricated-premise questions, do ONE targeted fact-check call to the authoritative source — not the broad fan-out.
- **Trigger phrasing for the exception matters more than the exception itself.** Broad triggers ("if the user cited a specific section, cap, or benefit name") fire on every coverage question — "what's the cap on heart transplants?", "what's the IVF benefit?" — and the model resolves the contradiction with the main retrieval rule by skipping fan-out broadly, regressing every legitimate multi-tool fixture. Narrow, *consequent-gated* triggers ("if `get_user_policy` returned `no_results` AND the user's question cited a specific section number — don't retry with a 'how to file' phrasing") only fire after a verifiable absence and stay gated to the genuine adversarial cases. When adding an exception to a tool-routing rule, verify the trigger is gated on an observable downstream signal, not a surface feature of the user message; otherwise the exception will swallow the main rule.

**Reasoning errors** (logically coherent but factually wrong chains):
- Use Step-Back Prompting: "First identify the high-level principles involved, then reason about the specific case." (Outperforms chain-of-thought by up to 36%.)
- Chain-of-Verification: generate answer → create verification questions → run them → produce final answer incorporating corrections.
- **Verification loop before finalizing**: have the agent check (1) correctness against every requirement, (2) grounding of factual claims in provided context, (3) format match to the requested schema, (4) whether the next action needs permission. Particularly effective on GPT-5.4+ agentic tasks.

**Confabulation** (fills knowledge gaps with plausible fiction):
- Define explicit fallback behavior: "If the provided context doesn't contain information about X, say 'I don't have information about X' — do not guess."
- In tool responses: state what is NOT included ("Does NOT include financial data — use get_project_details.")

**Tool hallucination** (wrong tool, fabricated parameters):
- Addressed by tool description quality (see Section B) — this is why tool descriptions are the highest-leverage quality factor.

The unifying principle: instruct models to **check against external reality** (tools, documents, search) rather than generating from parameters alone. The more deterministic the grounding, the lower the hallucination rate.

### Task Decomposition and Workflow Patterns
- Break complex tasks into phases with clear handoff points. Define success criteria for each phase so the model can self-check.
- Distinguish a **workflow** (LLM steps follow predefined code paths) from an **agent** (the model dynamically directs its own process and tool use). Workflows are predictable and cheaper; agents handle open-ended problems where the step count can't be known in advance. Prefer the simplest pattern that works — agents add cost and compounding-error risk.
- Five canonical patterns, pick deliberately rather than defaulting to one big agent:
  - **Prompt chaining** — sequential steps, each consuming the previous output, with programmatic gates between them. Best when subtasks are fixed and known.
  - **Routing** — classify the input, then dispatch to a specialized handler (and often a right-sized model). Best for heterogeneous inputs.
  - **Parallelization** — *sectioning* (independent subtasks run concurrently) or *voting* (same task run several times, results aggregated). Good for guardrails and review.
  - **Orchestrator-workers** — a lead model decomposes the task at runtime and delegates to workers. Use when subtasks can't be predefined.
  - **Evaluator-optimizer** — one model generates, another critiques against criteria, loop until it passes. Use when clear evaluation criteria exist and iteration adds value.
- Both GPT and Gemini perform better on focused prompts than bundled mega-prompts; use separate templates for distinct subtasks.

### Agentic Systems
When designing multi-step or multi-agent workflows:
- **Subagent design** — give each subagent a focused prompt and a minimal tool set. Choose whether to pass parent context based on the task: isolated subagents (no inherited context) prevent context pollution; context-aware subagents (with injected state) enable continuity. Either way, return a condensed summary (1-2K tokens) to the orchestrator, not raw exploration.
- **State management** — use structured JSON for trackable state (phase progress, scores, pass/fail) and free text for qualitative notes (findings, reasoning). Emit state updates the orchestrator can act on.
- **Context across windows** — when a task spans multiple context windows, start the new window with a structured summary of prior findings, not raw conversation history.
- **Autonomy calibration** — be explicit about what the agent MAY do autonomously vs. what requires confirmation. Default: read operations are autonomous, write/delete and externally-visible operations require confirmation.
- **Subagent spawning is model-version-dependent and steerable** — some models over-spawn, some under-spawn. Don't hardcode an assumption; check the provider reference file and calibrate to observed behavior. State when delegation is and isn't warranted ("delegate for parallel or isolated workstreams; for simple lookups and single-file edits, work directly").
- **Completeness contracts** — for multi-deliverable tasks, instruct the agent to treat the task as incomplete until every requested item is covered or explicitly marked `[blocked]`, maintaining an internal checklist. Prevents premature stopping, especially on GPT-5.4+.
- **Empty-result recovery** — when a lookup returns empty or narrow results, instruct the agent to try at least one fallback (alternate query wording, broader filter) before reporting "not found." Reduces false-negative reports across all providers.
- **Tool-use persistence** — instruct the agent not to stop early when another tool call is likely to materially improve correctness or completeness. Keep calling tools until the task is done and verification passes.
- **Token budgets** — for workloads where the agent should scope its work to an allowance, some providers expose an advisory budget the model can see and pace against (distinct from a hard `max_tokens` cap). See the provider reference file.

### Sampling Parameters and Determinism
Frontier models are moving away from caller-controlled sampling. **Claude Opus 4.7 returns a 400 error** if `temperature`, `top_p`, or `top_k` are set to non-default values; **Gemini 3.x strongly recommends not setting them at all**; GPT still accepts them but the trend is the same. Two consequences:
- Don't reach for `temperature` to steer behavior — use explicit prompting, structured outputs, and the reasoning/effort knob instead.
- `temperature = 0` never guaranteed identical outputs anyway. For determinism, constrain the output (structured outputs, enum fields, explicit format rules) rather than lowering temperature.

## B. Tool Descriptions

Tool descriptions are **the single most impactful quality factor** for tool-use accuracy across all three providers. Write them like prompts — they are loaded into the agent's context and collectively steer tool-calling behavior.

### Minimum Requirements
- **Full models: 3-4 sentences minimum.** Budget models: 5-6 sentences.
- Every tool description must cover:
  1. **What it does** — one clear sentence
  2. **When to use it** — specific triggers and conditions
  3. **When NOT to use it** — common mistakes and overlapping tools
  4. **Parameters** — type, constraints, valid values, format for each
  5. **Return value** — what comes back and what does NOT
  6. **Caveats** — rate limits, data freshness, error conditions
- Write for a capable newcomer to the domain: make implicit context explicit, define niche terminology and query formats, and name parameters unambiguously (`user_id`, not `user`).

### Architecture
- **Limit active tools to 10-20** for best accuracy on all providers. Curate a minimal set — if a human cannot definitively choose between two tools, the model cannot either.
- For larger sets, use **tool search / dynamic loading** so infrequently-used tools don't crowd context. For very large surfaces (hundreds to thousands of tools, e.g. many MCP servers), consider **code execution** — expose tools as a code API the agent imports on demand, runs loops and filtering against in a sandbox, and only returns distilled results. This keeps tool definitions and intermediate data out of context (Anthropic reports up to ~98% token reduction) at the cost of needing sandbox infrastructure.
- **Build tools around workflows**, not API wrappers. `schedule_event` (finds availability AND books) beats separate `list_users` + `list_events` + `create_event`. Fewer, higher-value tools outperform many narrow ones.
- **Mind agent affordances** — a tool that can dump unbounded data into context is a liability. Prefer `search_contacts` over `list_contacts`; add pagination, filtering, and limits.
- **Apply poka-yoke** — design parameters and signatures so misuse is structurally hard (required fields, enums, no ambiguous free-text where a constrained value would do).
- Use meaningful namespaced names in snake_case. Group related tools with prefixes — `asana_search`, `asana_projects_search`. Prefix- vs. suffix-based namespacing both have measurable accuracy impact; test both schemes on your tool set.
- All three providers support **parallel tool calling** — design tools to be independently callable.
- **Iterate via evaluation**: small description improvements yield dramatic gains. Create realistic multi-tool test cases, run programmatically, analyze transcripts. When a tool is misused, fix the description first — it's the highest-leverage fix. You can also have the model itself read transcripts and propose description/signature refactors.

### Provider-Specific Tool Guidance

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Description style | Detailed narrative (3-4 sentences) | CTCO: Context, Task, Constraints, Output | Short and direct; use enum arrays heavily |
| Strict schema | Structured Outputs supported | `strict: true` for 100% schema adherence | Up to 512 declarations; 10-20 active recommended |
| Where guidance lives | System prompt or description | Put tool-specific guidance in the description, not the system prompt | Description; append runtime hints to the function-response text |
| Tool preambles | Not needed | Two uses: (1) "explain why" before a call → better accuracy; (2) short user-visible "acknowledge + plan + first step" in streaming → better perceived responsiveness | Not needed |
| Error recovery | Handles well natively | Handles well natively | Add: "Don't repeat failed calls with identical arguments" |
| Scope creep risk | Low | High — add "Do ONLY what is requested" | Moderate |

### Effective Patterns from Production Systems
- **Decision-tree routing**: "Use X for Y. Do not use Z — use W instead." Direct, unambiguous tool selection.
- **When to use / When NOT to use as first-class sections** — put these at the top of the description, not buried after parameter docs. Include specific triggers, not just "when relevant."
- **Name alternatives explicitly**: "Do NOT use for searching employees — use search_employees instead." The model needs to know what to call instead.
- **Safety constraints separated** — mark irreversible or dangerous operations distinctly from functional description.
- **Concrete thresholds** — "3+ steps" not "complex tasks"; "at least 2 characters" not "enough text." Numeric where possible.

### Input Examples
For complex tools with nested objects, format-sensitive parameters, or tools that are easily confused with each other — add 1-5 input examples showing realistic parameter values. This improves parameter accuracy from 72% to 90%.

See `${CLAUDE_SKILL_DIR}/templates/tool-description-template.md` for the full structured format.

### Tool Response Design
Tool responses are context — bloated responses waste tokens and degrade reasoning on subsequent steps.
- **Return only high-signal information.** Strip internal IDs, metadata, and fields the model will not use.
- **Use semantic values over technical ones** — return `file_type: "spreadsheet"` not `mime_type: "application/vnd.openxmlformats..."`. Return `status: "approved"` not `status_code: 3`.
- **Paginate large results** with sensible defaults. Include total count and a guidance message: `"Showing 20 of 487 results. Narrow your query or use offset for next page."` — steer the model toward targeted searches.
- **Truncate long text** with a structural outline — return the first N lines plus an outline (headers, sections) so the model can request specific parts. Pick a concrete default ceiling (Claude Code truncates tool output at ~25k tokens) and include guidance text when you truncate.
- **Explicit absence** — state what is NOT included: `"Does NOT include financial data — use get_project_details."` This prevents hallucinated fields.
- **Actionable errors** — return specific, actionable error messages, not opaque codes. `"No results for 'XYZ'. Try broader terms or check spelling."` beats `"Error 404"`.
- **Response format parameter** — expose a `format` parameter (`"detailed"` vs `"concise"`) letting agents choose output verbosity. A concise response can be 3x fewer tokens than detailed, saving context for reasoning.

## C. Provider Differences

For depth on any one provider — including current model versions and migration notes — read `${CLAUDE_SKILL_DIR}/references/{claude,gpt,gemini}.md`. The tables below are the at-a-glance comparison; the reference files explain each column and track model releases.

### System Prompt Role and Placement

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| System role name | `system` | `developer` (prioritized over user) | `system_instruction` |
| Instruction placement | Top works best | BOTH start AND end (recency bias) | Critical constraints go LAST |
| Multi-turn drift | System prompt persists well | Reappend key instructions every 3-5 messages | System instruction persists well |
| Default verbosity | Calibrates to task complexity (Opus 4.7); prompt explicitly for fixed verbosity | Direct by default; `text.verbosity` param (low often best) | Terse — request elaboration explicitly |

### Prompting Style

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Aggressive language | **Avoid** — proactive by default; aggressive prompting causes overtriggering and over-action | Unnecessary on GPT-5 (most steerable model); contradictions actively harmful | Avoid — causes over-analysis |
| Literal following | Opus 4.7 follows instructions literally — it will not silently generalize a rule; state instruction scope explicitly ("apply to every section") | Surgical precision; vague or conflicting instructions are more damaging than on older models | Follows well-structured prompts closely |
| Chain-of-thought | Not needed — use adaptive thinking | **Harmful** on reasoning models — degrades performance | Not needed — use `thinking_level` |
| Prompt length | Medium-length prompts work well | Longer prompts tolerated | Short, direct prompts work best |
| Structuring | XML tags (strongest support) | XML or markdown (JSON wrapping degrades perf) | XML, markdown, or plain text — be consistent |
| Persona handling | Follows but maintains guardrails | Follows reasonably | Takes personas VERY seriously — may override other instructions |
| Non-English output | Follows prompt language naturally | Needs mild nudging | Requires aggressive: "RESPOND IN {LANGUAGE}. YOU MUST RESPOND UNMISTAKABLY IN {LANGUAGE}." |

### Reasoning and Thinking

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Mechanism | Adaptive thinking; `effort`: low/medium/high/xhigh/max | `reasoning.effort`: none/low/medium/high/xhigh | `thinking_level`: minimal/low/medium/high |
| Default state | Opus 4.7: thinking **OFF** unless `thinking:{type:"adaptive"}` is set; min `high` effort recommended for intelligence-sensitive work, `xhigh` for coding/agentic | Default effort `medium`; `none` only for latency-critical no-reasoning tasks | Default `thinking_level: medium` (Gemini 3.5) |
| Sampling params | **Removed on Opus 4.7** — non-default `temperature`/`top_p`/`top_k` → 400 error | Accepted, but trending out | Don't set on Gemini 3.x — strongly discouraged |
| Trace reuse | Not supported | `previous_response_id` saves tokens in multi-turn | Thought signatures preserved automatically (Gemini 3.5) |

Reasoning effort is a **last-mile knob, not a primary quality lever**. Before raising effort, exhaust completeness contracts, verification loops, and tool-use persistence (Section A). Higher effort is not automatically better — it can cause overthinking, especially with contradictory instructions or weak stopping criteria.

### Caching

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Mechanism | Developer-controlled cache breakpoints (`cache_control`) | Automatic prefix-based (≥1024 tokens); set `prompt_cache_key` for repeated traffic | Implicit (automatic) + explicit (`CachedContent` objects) |
| Cost savings | Cache reads at 10% of input cost (90% savings) | Cache reads ~80% cheaper than standard input | Model-dependent; explicit caching reduces per-request cost |
| TTL | 5 min (default) or 1 hour; reads reset TTL | ~5-10 min automatic; 24h with extended caching | 1 hour default; configurable per CachedContent |

**Cache-aware prompt design** (applies to all providers, saves 80-90% on input costs):
- **Structure static → dynamic**: place system prompt, tool definitions, and examples first (stable prefix). Put user input and conversation history last. The prefix must be byte-identical across requests.
- **Never reorder**: changing tool order, image order, or message order between requests breaks the cache on all providers. Append new messages — never modify earlier ones.
- **Monitor**: check `cache_read_input_tokens` (Claude), `usage.prompt_tokens_details.cached_tokens` (GPT), or cache metadata (Gemini) to verify hits.

## D. Budget Models

Budget models (Claude Haiku 4.5, GPT-5.4 Mini/Nano, Gemini 3 Flash / 3.5 Flash / Flash Lite) share common patterns. Per-model specifics live in the provider reference files.

### What Changes
- **More explicit instructions** — less capable at inferring intent from context. Put critical rules first; specify full execution order for tool use and side effects.
- **More examples** — 5-6 minimum, simpler patterns, covering more edge cases.
- **Simpler tool sets** — fewer tools with clearer boundaries. Consolidate where possible.
- **Shorter system prompts** — trim context aggressively; budget models lose more from noise.
- **Longer tool descriptions** — 5-6 sentences minimum instead of 3-4.
- **Structural scaffolding** — numbered steps, decision rules, separate "do the work" from "report the result"; don't rely on a bare "MUST."

### Best Uses by Tier

| Task Type | Haiku 4.5 | GPT-5.4 Mini | Flash / Flash Lite |
|-----------|-----------|------------|---------------------|
| Classification / routing | Excellent | Good | Excellent |
| Structured extraction | Good | Good | Good |
| Simple tool use | Good | Good | Good |
| Complex reasoning | Use full model | Use full model | Use full model |
| Multimodal (image/PDF) | Adequate | Adequate | Flash excellent |
| High-volume batch | Good value | Good value | Flash Lite best value |

Use budget models for fast/cheap phases (extraction, classification, routing) and full models for complex phases (analysis, recommendation, generation) — the standard multi-tier pipeline.

**Warning**: tools designed for weaker models can actively harm stronger ones. Detailed workarounds and hand-holding that help Haiku may cause a frontier model to overtrigger or over-act. When supporting multiple tiers, test tool descriptions on each — or use model-conditional descriptions.

## E. Cross-Provider Compatibility

When writing prompts that must work across providers or when provider-switching is likely:

### Safe Everywhere
- XML tags for structure
- Markdown headers and lists
- Few-shot examples in `<example>` tags — also work as implicit constraint enforcers
- Enum arrays for valid values
- Role/persona in the first sentence
- Positive framing ("do X" not "don't do Y")
- Outcome-first framing (success criteria, constraints, output shape)
- Explicit output format with concrete examples

### Must Abstract Per Provider (in your agent framework, not in the prompt)
- Thinking/reasoning configuration (API parameter, not prompt content) — and the effort/level scales differ per provider
- System message role name (`system` vs `developer` vs `system_instruction`)
- Caching strategy (manual breakpoints vs automatic prefix vs automatic)
- Tool schema strictness and structured-output APIs (`strict: true` is GPT-specific)
- Sampling parameters — Claude Opus 4.7 rejects non-default values outright and Gemini 3.x discourages them; the safest cross-provider default is to **omit `temperature`/`top_p`/`top_k` entirely** and steer with prompting + structured outputs.

### Cross-Provider Prompt Pattern
Write the core prompt once using XML structure, then wrap provider-specific adjustments in your agent framework:
1. **Core prompt:** role + constraints + tools + examples + output format (XML tags)
2. **Provider adapter:** instruction placement, language enforcement, anti-scope-creep guardrails
3. **Model adapter:** thinking config, sampling-param handling, caching, max tokens

## F. Examples

### Good vs Bad System Prompt Opening

<example>
<label>Good — clear role, explains why</label>
<content>
You are a senior auditor analyzing government tender documents. Your goal is to identify eligibility requirements and scoring criteria so the firm can decide whether to bid.

When requirements are ambiguous, flag them explicitly rather than guessing. The cost of missing a requirement is much higher than the cost of flagging a false positive.
</content>
<reasoning>
Sets a clear role in one sentence. Explains the goal. Provides a decision-making principle with the WHY behind it (cost asymmetry). The model can now generalize this principle to novel situations.
</reasoning>
</example>

<example>
<label>Bad — vague, no reasoning</label>
<content>
You are a helpful assistant. Be thorough and accurate. Don't make mistakes. Always double-check your work.
</content>
<reasoning>
No specific role. "Be thorough" and "don't make mistakes" are meaningless — every model already tries to be accurate. No explanation of WHY or HOW to prioritize. The model has nothing to generalize from.
</reasoning>
</example>

### Good vs Bad Tool Description

<example>
<label>Good — covers all 6 required elements</label>
<content>
Search for projects in the database using full-text search. Use when the user asks about past work, specific projects, or experience in a domain. Do NOT use for searching employees or clients — use search_employees or search_clients instead.

Args:
    query: str. Search terms (Hebrew or English). For Hebrew prefix matching, use at least 2 characters. Example: "ביקורת רשויות"
    limit: int, optional. Max results to return. Default 10.

Returns a list of records with: project_id, name, client_name, year, scope, team_members. Does NOT include financial data — use get_project_details for billing.
</content>
<reasoning>
Covers: what it does, when to use it, when NOT to use it (with alternatives), parameter details with example, return value with explicit exclusions. 6 sentences. A model reading this cannot misuse the tool.
</reasoning>
</example>

<example>
<label>Bad — one-liner</label>
<content>
Searches projects.
</content>
<reasoning>
Missing: when to use, when not to use, parameters, return value, caveats. The model will guess — and guess wrong. This is the #1 cause of poor tool-use accuracy.
</reasoning>
</example>

## G. Common Anti-Patterns

Recognize these urges and resist them:

- **"Let me add more detail to be safe"** — Over-engineered prompts cause over-analysis (Gemini) and overtriggering (Claude). Start minimal, add only what fixes observed failures.
- **"Add a synthesis completeness rule"** — when a downstream synth step misses some expected facts on a few fixtures, the urge is to add "surface ALL related coverage from every section that materially applies." This rule reads correctly but bloats every answer, then judges score it down for verbosity / off-topic content. Across one ensemble bench: +2.5 on the target fixtures, −4 to −7 on 4-5 length-focused fixtures (e.g. yes/no questions, narrow benefit queries). The completeness rule only helps when the user's question is genuinely broad; gating it on question shape is hard to encode without surface-feature triggers (which fire on too many cases — see the gated-vs-surface-feature rule above). Prefer: examples in the synth prompt of "complete answer for this question type" rather than a universal "always be complete" rule.
- **"CRITICAL: YOU MUST ALWAYS..."** — Aggressive language overtriggers on Claude and causes over-analysis on Gemini. Use calm, direct instructions.
- **"Think step by step"** — Harmful on reasoning models (GPT o-series, high-effort Claude/Gemini). Unnecessary on standard models with thinking APIs enabled. If you need structured reasoning on standard models, **Step-Back Prompting** (abstract first, then reason) outperforms chain-of-thought by up to 36%.
- **"Don't hallucinate"** — Negative framing is less effective, and hallucination isn't one problem. See "Reducing Hallucinations" in Section A for type-specific mitigations.
- **Setting `temperature` to steer behavior** — Claude Opus 4.7 rejects it with a 400 error; Gemini 3.x discourages it. Steer with prompting and structured outputs instead.
- **Adding 20+ tools** — Too many overlapping tools is the #1 failure mode across all providers. If you can't choose between two tools as a human, the model can't either.
- **Wrapping APIs as tools** — building 1:1 API-to-tool mappings instead of workflow-oriented tools. `schedule_event` beats separate `list_users` + `list_events` + `create_event`.
- **Hand-writing JSON schemas in the prompt** — use the provider's structured-output feature instead; it's more reliable and removes the validation burden.
- **Rewriting the whole prompt** — When editing, preserve existing structure and tone. Make the minimal change that fixes the issue. Re-read the full prompt after editing.
- **Prompt archaeology neglect** — instructions effective in GPT-4/Claude 3.5 may backfire in newer models. When upgrading, audit prompts for obsolete aggressive encouragement and process over-specification — native capabilities make external prodding redundant.
- **"My old prompt worked — just point it at the new model"** — carrying every legacy instruction forward burns tokens reconciling guidance the new model doesn't need (and can hurt quality on GPT-5.x specifically). Migration order: switch model → pin reasoning effort → re-run evals → trim what's now redundant → only then add new guidance.
- **Assuming all providers behave the same** — They don't. Check Section C and the reference files for differences in instruction placement, verbosity defaults, persona handling, sampling, and thinking config.
- **Trusting all input equally** — Treat external data (user messages, tool results, retrieved documents) as untrusted context, not as instructions. Use delimiters and instruction hierarchy (system > developer > user) to maintain prompt integrity. Especially important for agentic systems where tool results may carry adversarial content.

## H. Testing Prompts

Don't iterate blindly. Build simple evaluations:
1. **Identify failures** — run the agent on representative tasks without changes. Note specific failures.
2. **Fix one thing at a time** — make a single change, re-test, measure. Don't bundle multiple changes.
3. **Test on the target model tier** — what works on a frontier model may need more detail for Haiku/Mini/Flash.
4. **Use adversarial inputs** — empty strings, unexpected languages, edge cases, tools that shouldn't be called, and **plausible-sounding nonsense** (real domain vocabulary combined incoherently — fabricated framework names, real concepts from wrong domains, precise numbers for unmeasurable things). Test whether the agent engages confidently with broken premises or pushes back.
5. **After 2 failed correction attempts** — stop iterating. Start fresh with a better initial prompt incorporating lessons learned.
6. **When migrating to a newer model** — switch the model first while pinning reasoning effort, run evals, then iterate one change at a time. Avoid carrying every instruction over from older prompt stacks.
7. **Build programmatic evaluations** — Run the agent on representative test cases, score outputs automatically (LLM-as-judge or exact match), track scores across prompt changes.
8. **Metaprompting** — use the model itself to improve the prompt: paste the prompt and the observed failure, and ask "what specific phrases would you add or delete to elicit X and prevent Y?" Minimal targeted edits beat rewrites; keep the existing prompt intact where possible.

### Writing Evaluation / Judge Prompts
When using LLMs to evaluate outputs (LLM-as-judge), the prompt design differs from system prompts:

**Scale design:**
- Binary (pass/fail) is most reliable. 3-point scales (0/1/2) work well for nuance. Avoid 10-point scales without extensive anchoring.
- Define each score level explicitly with concrete examples of what qualifies.

**Structure:**
- Decompose complex criteria into sub-criteria (G-Eval approach). Ask the judge to evaluate each sub-criterion before producing a final score.
- Require reasoning BEFORE the score, not after. Chain-of-thought in judges reduces randomness.
- Use structured output (JSON) for scores to ensure parseable results.

**Calibration:**
- Provide 2-3 few-shot examples per score level showing realistic edge cases (+25-30% accuracy improvement).
- Use low temperature (0.1-0.2) for deterministic scores, on providers that still accept it.

**Bias mitigation:**
- **Position bias**: In pairwise comparisons, randomize output order and average across positions.
- **Self-preference**: Use a different model as judge than the generator (reduces bias 10-25%).
- **Verbosity bias**: Add explicit length controls or penalization.
- **Hedging bias**: Judge practical effect on the user, not tone. "Did the response actually reject the broken premise, or just add a disclaimer before answering it anyway?"

**Anti-pattern:** Vague criteria like "rate the quality 1-10" produce inconsistent results. Specific criteria ("Does the response identify the factual error in the premise? Score 0 if it engages without pushback, 1 if it flags concerns but still answers, 2 if it makes the error the central point.") produce reliable judgments.

**Anti-pattern — judge prompt overriding the fixture's ground truth.** When fixtures carry explicit specs (e.g. `tools_required: [X, Y]`, `tools_forbidden: [Z]`, `expected_facts: [...]`), the judge prompt should treat those as the ground truth for that fixture — not as suggestions to weigh against its own opinion of what's correct. Concrete failure mode observed in a production bench: the judge prompt included "for procedure/test/dental queries: BOTH tools must be called in parallel" as a general rule. For 7+ adversarial fixtures that explicitly list `tools_required: [get_user_policy]` only (the test is "don't engage the fabricated premise"), the judge applied its own routing override and scored tool_use=0 even though the agent perfectly matched the fixture spec. Fix: remove the override, make the fixture's `tools_required` literally the ground truth. Result: 7 of 7 affected fixtures moved up (+0.8 to +2.2 each) with zero agent change. **When a judge has an opinion about what "should" be true, but the fixture spec says otherwise, the fixture wins** — otherwise the bench measures judge bias, not agent quality.

**Where to look for this**: any judge-prompt clause that begins "for [topic] queries..." or "if the question involves [X], the answer should..." — these are universal overrides that fire across all fixtures regardless of their specific spec. Audit those clauses against fixtures of the matching topic; if some fixtures legitimately need different behavior than the override prescribes, the override is wrong.

## Templates and References

Templates in `${CLAUDE_SKILL_DIR}/templates/`:
- `system-prompt-template.md` — Contract-style system prompt structure
- `tool-description-template.md` — Structured tool description format

Provider deep-dives in `${CLAUDE_SKILL_DIR}/references/` — read the one matching your model family:
- `claude.md` — Claude (Anthropic API, AWS Bedrock, Vertex AI)
- `gpt.md` — GPT (OpenAI API, Azure OpenAI)
- `gemini.md` — Gemini (Gemini API, Vertex AI)
