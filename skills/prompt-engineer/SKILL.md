---
name: prompt-engineer
description: "Expert prompt engineering for building AI agents via Claude, GPT, and Gemini APIs. Triggers when: writing or editing system prompts, tool descriptions, agent instructions, function calling schemas, tool response design, context engineering, agentic system design, or discussing prompt quality for any LLM API. Also triggers on: prompt optimization, tool-use accuracy, cross-provider compatibility, or prompt review. Examples: 'improve the system prompt', 'write a tool description', 'the agent keeps calling the wrong tool', 'make this work on Gemini too', 'the tool returns too much data', 'design the agent context flow'."
---

# Prompt Engineering for AI Agent APIs

Guidelines for writing system prompts, tool descriptions, and agent instructions for building AI agents via the Claude, GPT, and Gemini APIs. This covers both prompt engineering (crafting instruction text) and the broader discipline of context engineering (orchestrating everything the model sees — tools, memory, retrieved documents, state — to maximize the likelihood of desired behavior).

## Process

When editing an existing prompt, follow this order:
1. **Read** the full existing prompt. Understand its intent, structure, and target provider.
2. **Identify** the specific failure mode or improvement needed. Don't rewrite what isn't broken.
3. **Draft** the minimal change that addresses the issue, following the guidelines below.
4. **Re-read** the full prompt after editing to check for contradictions or broken flow.
5. **Test** the prompt on the target provider with representative inputs.

For new prompts: start minimal (role + constraints + examples + output format), test, then add instructions only when you observe failure modes.

Before submitting any prompt edit: check for contradictions (if two rules conflict, the model picks arbitrarily — remove one), and verify clarity (could a colleague with no context follow this prompt unambiguously?).

## A. Universal Best Practices

These apply to all three providers and cover ~70% of prompt engineering work.

### System Prompt Structure
- **Set a clear role** in one sentence at the top. Every provider respects persona framing.
- **Use XML tags** (`<role>`, `<constraints>`, `<examples>`, `<output_format>`) to separate sections. All three providers parse XML — it is the safest cross-provider delimiter.
- **Be explicit and specific.** Explain *why* a behavior matters, not just *what* to do. Models generalize better from explanations than from rigid rules.
- **Tell the model what TO do**, not what NOT to do. Positive framing ("Write in prose paragraphs") beats negative ("Don't use markdown").
- **Start minimal, then iterate.** Add instructions only when you observe failure modes. Over-engineered prompts cause over-analysis on Gemini and overtriggering on Claude.
- **For GPT-5.x: prefer outcome-first prompts.** Describe the destination (success criteria, constraints, available context, required output fields) rather than prescribing step-by-step process. Older "do X then Y then Z" prompting over-specifies what newer models handle on their own.

### Few-Shot Examples
- Include **3-5 diverse examples** — one of the most reliable steering mechanisms across all providers.
- Cover typical cases, edge cases, and at least one "what not to do" example.
- Wrap in `<example>` tags with `<input>` and `<output>` sub-tags.
- Budget models need MORE examples (5-6 minimum) with simpler patterns.

### Output Format
- **Define output format explicitly** — JSON schema, markdown template, or structured text.
- Provide a concrete example of the expected output, not just a description.
- Use **enum arrays** for valid values rather than prose descriptions — works on all providers and improves accuracy.

### Context Engineering
- Context window is working memory. Every token competes for attention — more is not always better. Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome.
- **Put long documents at the top**, queries and instructions at the bottom. This ordering improves response quality by up to 30% on complex multi-document inputs.
- **Prefer progressive discovery** — let agents find context through tools rather than front-loading everything. Maintain lightweight identifiers (paths, names, links) and load full content dynamically. Combine upfront retrieval (fast, known-relevant) with autonomous exploration (discovers unknowns).
- **Use semantic names over technical IDs** — replace UUIDs, mime_types, internal codes with human-readable names (file names, descriptive labels). LLMs reason more accurately over natural language than opaque identifiers.
- When context grows large, ask the model to **quote relevant sections first** before reasoning — this cuts through noise and grounds the response.
- For multi-turn agents: **compact and summarize** conversation history at context limits, preserving key decisions and findings. Use a cheap model (Flash, Haiku) for summarization.
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

### Task Decomposition
- Break complex tasks into phases with clear handoff points.
- Define success criteria for each phase so the model can self-check.
- Use separate prompt templates for distinct subtasks (analysis, extraction, generation).
- For complex workflows, break into sequential chained prompts — output from one becomes input for the next. Both GPT and Gemini perform better on focused prompts than bundled mega-prompts.

### Agentic Systems
When designing multi-step or multi-agent workflows:
- **Subagent design** — give each subagent a focused prompt and a minimal tool set. Choose whether to pass parent context based on the task: isolated subagents (no inherited context) prevent context pollution; context-aware subagents (with injected state) enable continuity. Either way, return a condensed summary (1-2K tokens) to the orchestrator, not raw exploration.
- **State management** — use structured JSON for trackable state (phase progress, scores, pass/fail) and free text for qualitative notes (findings, reasoning). Emit state updates the orchestrator can act on.
- **Context across windows** — when a task spans multiple context windows, start the new window with a structured summary of prior findings, not raw conversation history.
- **Autonomy calibration** — be explicit about what the agent MAY do autonomously vs. what requires confirmation. Default: read operations are autonomous, write/delete operations require confirmation. Claude 4.6 is highly proactive — dial back aggressive prompting or it will over-act.
- **Delegation discipline** — Claude 4.6 over-spawns subagents for simple tasks. Add: "Only delegate when the task requires specialized tools or a clean context. For simple lookups, do it yourself."
- **Completeness contracts** — for multi-deliverable tasks, instruct the agent to treat the task as incomplete until every requested item is covered or explicitly marked `[blocked]`, maintaining an internal checklist. Prevents premature stopping, especially on GPT-5.4+.
- **Empty-result recovery** — when a lookup returns empty or narrow results, instruct the agent to try at least one fallback (alternate query wording, broader filter) before reporting "not found." Reduces false-negative reports across all providers.
- **Tool-use persistence** — instruct the agent not to stop early when another tool call is likely to materially improve correctness or completeness. Keep calling tools until the task is done and verification passes. Counteracts the tendency to summarize partial findings instead of finishing the work.

## B. Tool Descriptions

Tool descriptions are **the single most impactful quality factor** for tool-use accuracy across all three providers.

### Minimum Requirements
- **Full models: 3-4 sentences minimum.** Budget models: 5-6 sentences.
- Every tool description must cover:
  1. **What it does** — one clear sentence
  2. **When to use it** — specific triggers and conditions
  3. **When NOT to use it** — common mistakes and overlapping tools
  4. **Parameters** — type, constraints, valid values, format for each
  5. **Return value** — what comes back and what does NOT
  6. **Caveats** — rate limits, data freshness, error conditions

### Architecture
- **Limit active tools to 10-20** for best accuracy on all providers. Use tool search or dynamic loading for larger sets — both Anthropic and OpenAI recommend deferring infrequently-used tools.
- Curate a minimal set — if a human cannot definitively choose between two tools, the model cannot either.
- **Build tools around workflows**, not API wrappers. `schedule_event` (finds availability AND books) beats separate `list_users` + `list_events` + `create_event`. Fewer, higher-value tools outperform many narrow ones.
- Use meaningful namespaced names in snake_case (`github_list_prs`, not `list`). Group related tools with prefixes. Some providers reject names with spaces or special characters.
- Design tool responses carefully — see Tool Response Design below.
- All three providers support **parallel tool calling** — design tools to be independently callable.
- **Iterate via evaluation**: small description improvements yield dramatic gains. Create realistic multi-tool test cases, run programmatically, analyze transcripts. When a tool is misused, fix the description first — it's the highest-leverage fix.

### Provider-Specific Tool Guidance

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Description style | Detailed narrative (3-4 sentences) | CTCO: Context, Task, Constraints, Output | Short and direct; use enum arrays heavily |
| Strict schema | Supported | `strict: true` for 100% schema adherence | Up to 512 declarations; 10-20 active recommended |
| Tool preambles | Not needed | Two distinct uses: (1) "explain why" before a tool call → better tool-use accuracy; (2) short user-visible "acknowledge + first step" preamble before tool calls in streaming → better perceived responsiveness on GPT-5.5 | Not needed |
| Error recovery | Handles well natively | Handles well natively | Add: "Don't repeat failed calls with identical arguments" |
| Scope creep risk | Low | High — add "Do ONLY what is requested" | Moderate |

### Effective Patterns from Production Systems
Patterns from Claude Code's tool descriptions and other production agents:
- **Decision-tree routing**: "ALWAYS use X for Y. NEVER use Z — use W instead." Direct, unambiguous tool selection.
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
- **Truncate long text** with a structural outline — return the first N lines plus an outline (headers, sections) so the model can request specific parts.
- **Explicit absence** — state what is NOT included: `"Does NOT include financial data — use get_project_details."` This prevents hallucinated fields.
- **Actionable errors** — return specific, actionable error messages, not opaque codes. `"No results for 'XYZ'. Try broader terms or check spelling."` beats `"Error 404"`.
- **Response format parameter** — expose a `format` parameter (`"detailed"` vs `"concise"`) letting agents choose output verbosity. A concise response can be 3x fewer tokens than detailed, saving context for reasoning.

## C. Provider Differences

### System Prompt Role and Placement

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| System role name | `system` | `developer` (prioritized over user) | `system_instruction` |
| Instruction placement | Top works best | BOTH start AND end (recency bias) | Critical constraints go LAST |
| Multi-turn drift | System prompt persists well | Reappend key instructions every 3-5 messages | System instruction persists well |
| Default verbosity | Verbose — request conciseness if needed | Moderate — use `text.verbosity` param | Concise — request elaboration if needed |

### Prompting Style

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Aggressive language | **Avoid** — 4.6 is proactive by default; aggressive prompting causes overtriggering and over-action | Unnecessary on GPT-5 (most steerable model); contradictions actively harmful | Avoid — causes over-analysis |
| Chain-of-thought | Not needed — use adaptive thinking | **Harmful** on reasoning models — degrades performance | Not needed — use thinkingLevel |
| Prompt length | Medium-length prompts work well | Longer prompts tolerated | Short, direct prompts work best |
| Structuring | XML tags (strongest support) | XML or markdown (JSON wrapping degrades perf) | XML, markdown, or plain text — be consistent |
| Persona handling | Follows but maintains guardrails | Follows reasonably | Takes personas VERY seriously — may override other instructions |
| Non-English output | Follows prompt language naturally | Needs mild nudging | Requires aggressive: "RESPOND IN {LANGUAGE}. YOU MUST RESPOND UNMISTAKABLY IN {LANGUAGE}." |

### Reasoning and Thinking

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Mechanism | Adaptive by default; use `effort` param (low/medium/high/max) for control | `reasoning.effort`: none/low/medium/high/xhigh (GPT-5.4+); peaks across multiple agent turns. Default to `none`/`low` for latency-sensitive work; raise to `high`/`xhigh` only after exhausting completeness contracts, verification loops, and tool-use persistence (see Agentic Systems in Section A) — reasoning effort is a last-mile knob, not a primary quality lever | `thinkingLevel`: minimal/low/medium/high (Gemini 3); `thinkingBudget` token count (Gemini 2.5) |
| Default state | Adaptive (model decides) — no config needed | OFF — must enable explicitly | Cannot disable on latest Pro models |
| Temperature | 0.0-1.0 typical range | 0.0-1.0 typical range | **Keep at 1.0** — lowering causes looping/degradation |
| Trace reuse | Not supported | `previous_response_id` saves tokens in multi-turn | Not supported |

### Caching

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Mechanism | Developer-controlled cache breakpoints (`cache_control`) | Automatic prefix-based (≥1024 tokens, 128-token granularity) | Implicit (automatic) + explicit (`CachedContent` objects) |
| Cost savings | Cache reads at 10% of input cost (90% savings) | Cache reads ~80% cheaper than standard input | Model-dependent; explicit caching reduces per-request cost |
| Minimum tokens | 1,024-4,096 depending on model | 1,024 tokens | Varies by model |
| TTL | 5 min (default) or 1 hour; reads reset TTL | ~5-10 min automatic; 24h with extended caching | 1 hour default; configurable per CachedContent |

**Cache-aware prompt design** (applies to all providers, saves 80-90% on input costs):
- **Structure static → dynamic**: place system prompt, tool definitions, and examples first (stable prefix). Put user input and conversation history last. The prefix must be byte-identical across requests.
- **Never reorder**: changing tool order, image order, or message order between requests breaks the cache on all providers. Append new messages — never modify earlier ones.
- **Multi-turn**: append assistant response + new user message at the end. The stable prefix (system + tools + earlier messages) hits cache automatically.
- **Monitor**: check `cache_read_input_tokens` (Claude), `cached_tokens` (GPT), or cache metadata (Gemini) in responses to verify hits.

### Unique Features
- **Claude:** Prefill removed in 4.6. Adaptive thinking is default — no config needed. Context-aware (can track remaining context window). Parallel tool calling ~100% success with explicit instruction. Use `effort` param (not `budget_tokens`) for thinking control — `max` level available for quality-critical tasks. Tool search available for deferring large tool sets.
- **GPT — APIs and params:** `developer` role prioritized over `user` — security-sensitive instructions go in developer message. `strict: true` guarantees 100% JSON schema adherence. Independent `text.verbosity` param (low/medium/high) controls output length separately from reasoning depth. `previous_response_id` preserves reasoning across turns (73.9% → 78.2% on benchmarks). Fifth reasoning effort level `xhigh` available for quality-critical tasks. Image `detail` control: set `"high"` for standard vision, `"original"` for spatially sensitive or computer-use tasks, `"low"` only when speed dominates — don't rely on `auto` in production agents.
- **GPT — prompting style (5.4/5.5):** Contradictions are more damaging on GPT-5 than older models — it spends tokens reconciling conflicts instead of ignoring them. Prefer outcome-first contracts (describe destination, not steps). Define `Personality` (tone, warmth, directness, formality) and `Collaboration style` (when to ask vs. assume, how to handle uncertainty) as two separate concise blocks rather than one bundled instruction.
- **Gemini:** Native Google Search grounding (exclusive anti-hallucination tool — connects model to real-time verified information). Media resolution control for multimodal (image/video/PDF token budgets). Gemini 3 can combine built-in tools (Search, Code Execution) with custom function calling in a single call; function calls generate unique IDs that must be returned with results. `customtools` model variant optimized for agentic workflows prioritizing custom tools. Few-shot examples are critical — "prompts without few-shot examples are likely to be less effective." Default verbosity is terse — request elaboration explicitly. Add temporal grounding ("Remember it is {YEAR} this year") for time-sensitive tasks. Completion priming (start the response, let model continue) is more reliable than describing format preferences. Thought signatures (`thoughtSignatures`) preserve reasoning chains across multi-turn calls — capture and return them to maintain coherence.

## D. Budget Models

Budget models (Claude Haiku 4.5, GPT-5.4 Mini, Gemini 3 Flash / 3.1 Flash Lite) share common patterns:

### What Changes
- **More explicit instructions** — less capable at inferring intent from context.
- **More examples** — 5-6 minimum, simpler patterns, covering more edge cases.
- **Simpler tool sets** — fewer tools with clearer boundaries. Consolidate where possible.
- **Shorter system prompts** — trim context aggressively; budget models lose more from noise.
- **Longer tool descriptions** — 5-6 sentences minimum instead of 3-4.

### Best Uses by Tier

| Task Type | Haiku 4.5 | GPT-5.4 Mini | Flash / Flash Lite |
|-----------|-----------|------------|---------------------|
| Classification / routing | Excellent | Good | Excellent |
| Structured extraction | Good | Good | Good |
| Simple tool use | Good | Good | Good |
| Complex reasoning | Use full model | Use full model | Use full model |
| Multimodal (image/PDF) | Adequate | Adequate | Flash excellent |
| High-volume batch | Good value | Good value | Flash Lite best value |

### Practical Pattern
Use budget models for fast/cheap phases (extraction, classification, routing) and full models for complex phases (analysis, recommendation, generation). This is the standard multi-tier agent pipeline.

**Warning**: tools designed for weaker models can actively harm stronger ones. Detailed workarounds and hand-holding that help Haiku may cause Opus to overtrigger or over-act. When supporting multiple model tiers, test tool descriptions on each tier — or use model-conditional tool descriptions.

## E. Cross-Provider Compatibility

When writing prompts that must work across providers or when provider-switching is likely:

### Safe Everywhere
- XML tags for structure
- Markdown headers and lists
- Few-shot examples in `<example>` tags — also work as implicit constraint enforcers (can sometimes replace explicit instructions if examples are clear enough)
- Enum arrays for valid values
- Role/persona in the first sentence
- Positive framing ("do X" not "don't do Y")
- Explicit output format with concrete examples

### Must Abstract Per Provider (in your agent framework, not in the prompt)
- Thinking/reasoning configuration (API parameter, not prompt content)
- Temperature settings (especially Gemini's 1.0 requirement)
- System message role name (`system` vs `developer` vs `system_instruction`)
- Caching strategy (manual breakpoints vs automatic prefix vs automatic)
- Tool schema strictness (`strict: true` is GPT-specific)
- Reasoning effort levels (different scales per provider)

### Cross-Provider Prompt Pattern
Write the core prompt once using XML structure, then wrap provider-specific adjustments in your agent framework:
1. **Core prompt:** role + constraints + tools + examples + output format (XML tags)
2. **Provider adapter:** instruction placement, language enforcement, anti-scope-creep guardrails
3. **Model adapter:** thinking config, temperature, caching, max tokens

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
- **"CRITICAL: YOU MUST ALWAYS..."** — Aggressive language overtriggers on Claude 4.6 and causes over-analysis on Gemini. Use calm, direct instructions.
- **"Think step by step"** — Harmful on reasoning models (GPT o-series, high-effort Claude/Gemini). Unnecessary on standard models with thinking APIs enabled. If you need structured reasoning on standard models, **Step-Back Prompting** (abstract first, then reason) outperforms chain-of-thought by up to 36%. For reasoning models, simplicity wins — zero-shot first, add examples only if needed.
- **"Don't hallucinate"** — Negative framing is less effective, and hallucination isn't one problem. See "Reducing Hallucinations" in Section A for type-specific mitigations. The short version: instruct models to check against external reality (tools, documents, search) before claiming.
- **Adding 20+ tools** — Too many overlapping tools is the #1 failure mode across all providers. If you can't choose between two tools as a human, the model can't either.
- **Wrapping APIs as tools** — building 1:1 API-to-tool mappings instead of workflow-oriented tools. `schedule_event` (finds availability AND books) beats separate `list_users` + `list_events` + `create_event`.
- **Over-delegating to subagents** — Claude 4.6 spawns subagents for tasks it could handle directly. If the task needs no specialized tools or clean context, do it in-line.
- **Rewriting the whole prompt** — When editing, preserve existing structure and tone. Make the minimal change that fixes the issue. Re-read the full prompt after editing.
- **Prompt archaeology neglect** — instructions effective in GPT-4/Claude 3.5 may backfire in newer models. When upgrading models, audit prompts for obsolete aggressive encouragement — native capabilities make external prodding redundant.
- **"My old prompt worked — just point it at the new model"** — carrying every legacy instruction forward burns tokens reconciling guidance the new model doesn't need (and can hurt quality on GPT-5.x specifically). Migration order: switch model → pin reasoning effort → re-run evals → trim what's now redundant → only then add new guidance.
- **Assuming all providers behave the same** — They don't. Check Section C for differences in instruction placement, verbosity defaults, persona handling, and temperature.
- **Trusting all input equally** — Treat external data (user messages, tool results, retrieved documents) as untrusted context, not as instructions. Use delimiters and instruction hierarchy (system > developer > user) to maintain prompt integrity. This is especially important for agentic systems where tool results may contain adversarial content.

## H. Testing Prompts

Don't iterate blindly. Build simple evaluations:
1. **Identify failures** — run the agent on representative tasks without changes. Note specific failures.
2. **Fix one thing at a time** — make a single change, re-test, measure. Don't bundle multiple changes.
3. **Test on the target model tier** — what works on Opus/GPT-5.4/Gemini Pro may need more detail for Haiku/Mini/Flash.
4. **Use adversarial inputs** — empty strings, unexpected languages, edge cases, tools that shouldn't be called, and **plausible-sounding nonsense** (real domain vocabulary combined incoherently — fabricated framework names, real concepts from wrong domains, precise numbers for unmeasurable things). Test whether the agent engages confidently with broken premises or pushes back.
5. **After 2 failed correction attempts** — stop iterating. Start fresh with a better initial prompt incorporating lessons learned.
6. **When migrating to a newer model** — switch the model first while pinning reasoning effort, run evals, then iterate one change at a time. Avoid carrying every instruction over from older prompt stacks — legacy prompts often over-specify processes newer models handle natively.
7. **Build programmatic evaluations** — Run the agent on representative test cases, score outputs automatically (LLM-as-judge or exact match), track scores across prompt changes. Small description improvements in tools yield dramatic gains — but only if you measure.

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
- Use low temperature (0.1-0.2) for deterministic, reproducible scores.

**Bias mitigation:**
- **Position bias**: In pairwise comparisons, randomize output order and average across positions.
- **Self-preference**: Use a different model as judge than the generator (reduces bias 10-25%).
- **Verbosity bias**: Add explicit length controls or penalization.
- **Hedging bias**: Judge practical effect on the user, not tone. "Did the response actually reject the broken premise, or just add a disclaimer before answering it anyway?"

**Anti-pattern:** Vague criteria like "rate the quality of this response 1-10" produce inconsistent results. Specific criteria ("Does the response identify the factual error in the premise? Score 0 if it engages without pushback, 1 if it flags concerns but still answers, 2 if it makes the error the central point.") produce reliable judgments.

## Templates

Reference templates in `${CLAUDE_SKILL_DIR}/templates/`:
- `system-prompt-template.md` — Contract-style system prompt structure
- `tool-description-template.md` — Structured tool description format
