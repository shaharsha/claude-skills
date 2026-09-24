---
name: prompt-engineer
description: "Use ANY time an LLM-powered agent, chatbot, or AI assistant is being built, debugged, reviewed, planned, or migrated — the user almost never says 'prompt.' They say 'the agent keeps calling the wrong tool,' 'why is it ignoring my instructions,' 'fix this bug,' or just paste a log. TRIGGER when (1) any file in scope contains a system prompt, tool/function description, function-calling schema, tools.json, agents/* file, or imports an LLM SDK or agent framework (anthropic, openai, google.genai, AWS Bedrock, Vertex, Azure OpenAI, LangGraph/LangChain); (2) an agent loops, picks the wrong tool, hallucinates arguments, runs verbose despite low-verbosity settings, over- or under-escalates, ignores instructions, or shifts behavior after a model upgrade; (3) the user is thinking through or planning agent architecture — subagents, orchestrator/worker splits, state passing, multi-agent workflows — before code is written; (4) the user is comparing providers, migrating a prompt to a newer model, or asking 'is this good enough.' Covers Claude/Anthropic, GPT/OpenAI (incl. Azure), and Gemini/Google (incl. Vertex). Invoke proactively the moment you see prompt-shaped text or an LLM SDK call in scope — do not wait for the user to ask. SKIP only when no LLM agent is in the loop (pure SQL, infra, normal code with no model in scope, human prose editing)."
---

# Prompt Engineering for AI Agent APIs

> **First step (do this NOW, before reading further):** run `touch /tmp/.prompt-engineer-skill-loaded` once. The `~/.claude/hooks/protect-prompts.sh` PreToolUse hook blocks Edit/Write on prompt files (`prompts/`, `system_prompt*`, `agents/tools/`) until that flag exists; setting it confirms you've loaded these guidelines and lets subsequent edits proceed without re-loading the skill.

Guidelines for writing system prompts, tool descriptions, and agent instructions for building AI agents via the Claude, GPT, and Gemini APIs. This covers both prompt engineering (crafting instruction text) and the broader discipline of context engineering (orchestrating everything the model sees — tools, memory, retrieved documents, state — to maximize the likelihood of desired behavior).

## Step 0 — MANDATORY before anything else

Before reading the rest of this skill, do these two things in order. They are not optional and they are not "later." Skipping them is the #1 failure mode of this skill: the user repeatedly has to ask "did you read the provider-specific md?" because the universal section below got read in isolation and the version-specific knobs were never loaded.

### 0a. Identify the model family in scope

Look at the code, the file being edited, the SDK being imported, or what the user just said. Match against these signals — first hit wins. Split by **model family, not platform**: prompt engineering is identical whether GPT runs on OpenAI or Azure, or whether Claude runs on Anthropic or AWS Bedrock. This matters more now that **each major platform hosts several families** — AWS Bedrock serves **GPT and Claude**, Vertex AI serves **Gemini and Claude**, and Microsoft Foundry serves **GPT and Claude** — so the platform alone never tells you which reference file to load; identify the model family and load *that* file.

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

Read the full file before giving advice or editing anything. The universal section below covers ~70% of prompt engineering, but the version-specific knobs (Opus 5.5's always-on thinking + `medium` default + no forced `tool_choice`, GPT-6 Astra's follow-through and skill-sensitivity prompts, Gemini 3.8 Flash's missing `minimal` level and Interactions-API scoping, caching mechanics, reasoning-effort defaults, migration breakages) live only in those files and change every release. Working from the universal section alone produces stale advice - the exact failure the user keeps catching.

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
- **Lead with the outcome.** Describe the destination - success criteria, constraints, available context, allowed side effects, required output shape - rather than prescribing a step-by-step process. State stopping conditions explicitly. Reserve step-by-step process instructions for cases where the exact path is product-critical. (Strongest on GPT-5.x/6, but now good practice everywhere.)
- **Tell the model what TO do**, not what NOT to do. Positive framing ("Write in prose paragraphs") beats negative ("Don't use markdown").
- **Prefer decision rules over absolutes** for judgment calls. "If the action is reversible, proceed; otherwise confirm first" generalizes; "ALWAYS confirm" does not. Reserve hard rules for genuine invariants (safety, security).
- **Start minimal, then iterate.** Add instructions only when you observe failure modes. Over-engineered prompts cause over-analysis on Gemini and overtriggering on Claude.
- **Don't lead the witness.** Stating the answer you expect — or your own opinion, or "are you sure?" pressure — biases the model toward agreeing (sycophancy is trained in by RLHF; when a prompt hints an answer, models reason *backward* to justify it — arXiv:2310.13548). For judgments, extraction, and LLM-as-judge, withhold your expected answer and ask for reasoning before a verdict; to stress-test a claim, ask for the counter-case, not "do you agree?"

### Few-Shot Examples
- Include **3-5 diverse examples** — one of the most reliable steering mechanisms across all providers.
- Cover typical cases and edge cases. Models copy details of examples closely (Anthropic: Claude "pays very close attention to details in examples"), so examples should model **only behavior you want** - if you include a "what not to do" case, label it unmistakably as a counter-example and pair it with the correct version, or state the anti-pattern in prose instead.
- Choosing examples dynamically (nearest-neighbor retrieval) is not reliably better than a fixed or random diverse set in every domain (arXiv:2512.22966, clinical tasks) - measure before building the retrieval machinery.
- Wrap in `<example>` tags with `<input>` and `<output>` sub-tags. Keep formatting identical across every example — inconsistent structure confuses the model.
- Budget models need MORE examples (5-6 minimum) with simpler patterns.
- **On reasoning/thinking models, few-shot CoT is model-family-specific - check the matching reference file before adding it.** The cross-model default is to skip it: stacked exemplars and hand-written step-by-step demos run neutral-to-*harmful*, and the model tends to ignore the exemplars and follow the instructions instead. Describe the task + output format zero-shot and reach for examples to pin **output format/schema**. (DeepSeek-R1's own guidance: few-shot "consistently degrades its performance… use a zero-shot setting" - arXiv:2501.12948; corroborated by arXiv:2506.14641.) **Claude is the documented exception** - Anthropic recommends examples even with thinking on, including `<thinking>`-tagged ones; see `references/claude.md`. Gemini's guide likewise says to always include few-shot examples (for format and pattern, not hand-written reasoning chains); OpenAI says try zero-shot first on reasoning models.

### Output Format
- **Prefer the provider's structured-output feature** over describing a JSON schema in prose: OpenAI Structured Outputs (`strict: true`), Claude Structured Outputs / strict tool use, Gemini structured output (a JSON Schema response format). These constrain the response far more reliably than prompt text and remove the validation burden from the model.
- When you must specify format in the prompt (markdown template, structured text), provide a concrete example of the expected output, not just a description.
- Use **enum arrays** for valid values rather than prose descriptions — works on all providers and improves accuracy.
- **When a task needs reasoning AND structured output, order the schema so a reasoning/scratchpad field comes *before* the answer field.** Forcing the answer token first makes the model commit before it thinks and can sharply cut accuracy; the loss is largest on small/local models, and well-ordered constrained decoding is otherwise neutral-to-positive (arXiv:2408.02442; JSONSchemaBench, arXiv:2501.10868).

### Context Engineering
- Context window is working memory. Every token competes for attention — more is not always better. Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome.
- **Four levers (the industry-standard taxonomy, from [LangChain](https://www.langchain.com/blog/context-engineering-for-agents) building on Anthropic's context-engineering work).** Most of the techniques below are instances of one of these — name the lever you're pulling: **Write** (persist context *outside* the window — scratchpads, state, long-term memory — so it survives truncation), **Select** (pull only the relevant subset back in — RAG, semantic tool selection, exposing specific state fields), **Compress** (keep only the tokens the next step needs — summarization, trimming, dropping used tool payloads), **Isolate** (split context across separate spaces — subagents with their own windows, sandboxed state, schema fields hidden from the model until needed). For how these map to concrete primitives in a framework, see the LangGraph reference.
- **Put long documents at the top**, queries and instructions at the bottom. This ordering improves response quality by up to 30% on complex multi-document inputs.
- **Prefer progressive discovery** — let agents find context through tools rather than front-loading everything. Maintain lightweight identifiers (paths, names, links) and load full content dynamically. Combine upfront retrieval (fast, known-relevant) with autonomous exploration (discovers unknowns).
- **Use semantic names over technical IDs** — replace UUIDs, mime_types, internal codes with human-readable names (file names, descriptive labels). LLMs reason more accurately over natural language than opaque identifiers.
- When context grows large, ask the model to **quote relevant sections first** before reasoning — this cuts through noise and grounds the response.
- For multi-turn agents: **compact and summarize** conversation history at context limits. Maximize recall first (capture every architectural decision, unresolved issue, and key finding), then tighten for precision. Use a cheap model (Flash, Haiku) for summarization. Clearing stale tool-call results is a cheap, low-risk form of compaction — once a result has been used, the raw payload can be dropped.
- For long-horizon tasks: maintain **structured notes** (scratchpad, state JSON) outside the conversation for information that must survive compaction.
- **Don't paste data the model has to compute over - give it the file and code execution.** Anthropic's measurement: a ~91K-token CSV pasted into the prompt got 6 of 25 aggregate questions right on Sonnet 5; the same file uploaded and queried with code execution got 25 of 25 at about a twelfth of the cost. Tables in context are for reading, not arithmetic.
- **Point at an artifact instead of describing one.** When a spec is hard to write out — a visual design, a behavior with a lot of edge cases, a convention you'd recognize but can't articulate — hand over the thing itself. Anthropic reports source code is the highest-fidelity reference (it carries structure, naming, and idiom a paraphrase loses) and that an HTML mockup of a design outperforms a prose description *or a screenshot* of it. Other forms that work as specs: a test suite, a function in another codebase to port (language doesn't have to match), and a rubric a verifier agent scores against. Beyond "code beats prose beats screenshot," these are alternatives rather than a ranked ladder — pick by which one you can actually produce.
- **Irrelevant context actively degrades performance, and length itself is a cost — "context rot."** Every added token lowers reliability, even far below the window limit and even on trivial retrieval; a single distractor measurably hurts, and models can do *worse* on a coherent long context than a shuffled one (Chroma "Context Rot," 18-model study, 2025). Treat a 200K/1M window as reliable to *tens of thousands* of tokens, not its max: retrieve the few highest-relevance chunks, prune near-duplicate distractors, and don't pad. Degradation is gradual, not a cliff.
- **Know what your conversation state actually carries - and keep history append-only.** All three providers now push server-side or bound state, and each has a silent failure mode: OpenAI's Responses `instructions` parameter is **not** carried by `previous_response_id`; Gemini's Interactions API carries history via `previous_interaction_id` but **`system_instruction`, `tools`, and `generation_config` must be re-sent every call**; Claude Opus 5.5 / Fable 5.1 bind thinking blocks to the exact prior conversation, so **editing** the system prompt, tools, or an earlier turn mid-session 400s (or drops reasoning). The portable discipline: treat history as append-only, deliver instruction and tool changes as new messages (mid-conversation system messages, turn-scoped reminders, `configuration_update` items) rather than edits, and resend request-scoped settings explicitly. The same discipline keeps prompt caches warm.
- **Instruction files are context too - skills, `AGENTS.md`, `CLAUDE.md`.** Capable models follow them *more* literally, so stale or conflicting guidance there now blocks work (OpenAI reports GPT-6 Astra pausing on unclear skill instructions). Keep skill descriptions as short as possible with **narrow triggers** ("use when adding or changing a migration", not "use when working with databases"); make multi-workflow skills a minimal router with progressive disclosure; replace "before every edit, read X, Y, Z" with contextual pointers ("use X for service boundaries, Y for schema changes"); delete step-by-step recipes and "check your work" prodding that frontier models no longer need; and state precedence ("the user's explicit instructions override a skill's"). Guidance written for a small model can overconstrain a large one reading the same file.

### Reducing Hallucinations
Hallucination is not one problem — different types require different mitigations.

**Factual fabrication** (model invents facts):
- "Ground all claims in [source]. Quote the relevant section before answering."
- "According to..." prompting — guide model to cite specific trusted sources.
- Use search/retrieval tools to connect to verified information rather than relying on training data.
- **Force citations on every material fact (not necessarily shown to user).** Research-validated lever for production document-grounded agents. Authoritative head-to-head ([Princeton ALCE, EMNLP 2023](https://arxiv.org/abs/2305.14627)): on ASQA dataset, "Vanilla" (passages in context + cite instruction) achieves 73.6 citation recall + 72.5 precision; "Vanilla + Rerank" (sample 4 responses, pick best) reaches 84.8 + 81.6 — the highest measured. **"InlineSearch" (search-during-generation) underperforms** (58.3 recall) — *"retrieving text on the fly does not improve performance."* Provider-level: [Anthropic Citations API](https://platform.claude.com/docs/en/build-with-claude/citations) (Jan 2025 GA) auto-chunks documents and returns interleaved citation blocks with `cited_text`; cited_text doesn't count toward output tokens. Anthropic claims significantly better citation quality than prompt-based approaches. Google's [NotebookLM](https://arxiv.org/abs/2509.25498) reports **13% hallucination vs 40% for ungrounded LLMs** (3× reduction) via RAG + inline citations. [DeepMind GopherCite](https://deepmind.google/blog/gophercite-teaching-language-models-to-support-answers-with-verified-quotes/) added a critical pattern: the model can **abstain ("I don't know")** when no good evidence exists — accuracy improved dramatically when allowed to refuse. Implementation patterns ranked by ROI: (1) verifier pass with bounded retry (Chain-of-Verification, +3-5s latency), (2) ALCE-style sample-then-rerank (2-3× cost), (3) full citation-token system with deterministic grounding guard (regex + SQL + set-membership; survives prompt injection because no LLM step is in the verification loop).

**Premise acceptance** (model builds on false/incoherent premises):
- "Before answering, evaluate whether the question's assumptions are valid. If concepts don't belong together or the premise is incoherent, say so specifically — identify what's wrong, don't just hedge."
- Generic disclaimers ("As an AI...") and polite hedging do NOT reduce premise acceptance. Only specific identification of the flaw works.
- **It's heavily model-dependent, and effort doesn't fix it.** On [BullshitBench](https://petergpt.github.io/bullshit-benchmark/) (a nonsense-detection benchmark: 100 false-premise prompts across 5 domains, 3-judge panel), clear-pushback rates span **2%–95%** across models, and *raising* reasoning/effort does **not** help - it often *lowers* detection (GPT-5.2 `none` 38% > `high` 28%; Gemini 3.6 Flash `minimal` 39% > `xhigh` 28%), because more reasoning lets the model rationalize a way to engage the premise. Its judge rubric corroborates the point above - hedging, disclaimers, and compliments score as *failure*; only making the incoherence the central point counts. Those rates are *un-prompted* defaults (models are run with **no system prompt at all**), so an explicit "first, check whether the premise holds" instruction is exactly the lever the benchmark leaves untested. Fix premise-acceptance with explicit prompting + model choice, not the effort/`thinking_level` knob.
- For agentic systems: instruct agents to verify factual claims via tools before stating them.
- **Multi-tool fan-out compounds the problem** — when a false-premise question (user cites a fabricated section, benefit name, specific number) triggers a generic "fire all relevant retrieval tools in parallel" rule, the parallel tools return *legitimate-looking adjacent data* (e.g. the kupah's equivalent benefit, the general claim-filing process, a similar-but-different section) that the agent then weaves into a reply as if it validates the fabricated premise. Mitigation: for fabricated-premise questions, do ONE targeted fact-check call to the authoritative source — not the broad fan-out.
- **Trigger phrasing for the exception matters more than the exception itself.** Broad triggers ("if the user cited a specific section, cap, or benefit name") fire on every coverage question — "what's the cap on heart transplants?", "what's the IVF benefit?" — and the model resolves the contradiction with the main retrieval rule by skipping fan-out broadly, regressing every legitimate multi-tool fixture. Narrow, *consequent-gated* triggers ("if `get_user_policy` returned `no_results` AND the user's question cited a specific section number — don't retry with a 'how to file' phrasing") only fire after a verifiable absence and stay gated to the genuine adversarial cases. When adding an exception to a tool-routing rule, verify the trigger is gated on an observable downstream signal, not a surface feature of the user message; otherwise the exception will swallow the main rule.

**Reasoning errors** (logically coherent but factually wrong chains):
- Use Step-Back Prompting: "First identify the high-level principles involved, then reason about the specific case." (Outperforms chain-of-thought by up to 36%.)
- Chain-of-Verification: generate answer → create verification questions → run them → produce final answer incorporating corrections.
- **Verification loop before finalizing**: have the agent check (1) correctness against every requirement, (2) grounding of factual claims in provided context, (3) format match to the requested schema, (4) whether the next action needs permission. Effective on GPT-5.4/5.6-era agentic tasks - but **skip it on models that already self-verify** (Claude Opus 5.x, GPT-6 Astra, Gemini 3.8 Flash): there a verify instruction causes over-verification and over-testing at extra cost with no quality gain (see the provider files).
- **A verification/critic step needs an EXTERNAL signal to help.** Intrinsic self-correction — re-checking with no new information — is flat-to-negative and can flip correct answers to wrong (Huang et al., ICLR 2024, arXiv:2310.01798). Give the check something the generator lacks: a tool/test result, retrieval, a schema/validator, or a separate-context (different-lineage) judge. Cap reflection at 2–3 iterations — unbounded self-critique loops degenerate.

**Confabulation** (fills knowledge gaps with plausible fiction):
- Define explicit fallback behavior: "If the provided context doesn't contain information about X, say 'I don't have information about X' — do not guess."
- In tool responses: state what is NOT included ("Does NOT include financial data — use get_project_details.")
- **Eliciting usable confidence:** models are reasonably calibrated on multiple-choice and on "propose an answer, then rate P(it is correct)" (P(True)), but *overconfident* in free-form "how sure are you, 0–100%?". Prefer MC framing or a few-shot P(True) self-check, and route low confidence to a tool or human — don't trust a free-form percentage (arXiv:2207.05221).

**Tool hallucination** (wrong tool, fabricated parameters):
- Addressed by tool description quality (see Section B) — this is why tool descriptions are the highest-leverage quality factor.

The unifying principle: instruct models to **check against external reality** (tools, documents, search) rather than generating from parameters alone. The more deterministic the grounding, the lower the hallucination rate.

### Task Decomposition and Workflow Patterns
- Break complex tasks into phases with clear handoff points. Define success criteria for each phase so the model can self-check.
- Distinguish a **workflow** (LLM steps follow predefined code paths) from an **agent** (the model dynamically directs its own process and tool use). Workflows are predictable and cheaper; agents handle open-ended problems where the step count can't be known in advance. Prefer the simplest pattern that works — agents add cost and compounding-error risk.
- Five canonical patterns, pick deliberately rather than defaulting to one big agent:
  - **Prompt chaining** — sequential steps, each consuming the previous output, with programmatic gates between them. Best when subtasks are fixed and known.
  - **Routing** - classify the input, then dispatch to a specialized handler (and often a right-sized model). Best for heterogeneous inputs. Model routing inside an agent loop is a real cost lever - in one 145-task agent suite only ~7% of calls needed the frontier model yet carried ~68% of the bill; escalation routing (start cheap, promote the session after repeated bad turns) cut cost 74% for ~6 points of accuracy. It only pays when the price gap between the two models covers the router/judge overhead (break-even math in `model-selection.md`). Small typed "decision" classifiers (returning a choice or calibrated probability rather than text) now make routing and per-call guard checks cheap enough to run on every turn.
  - **Parallelization** — *sectioning* (independent subtasks run concurrently) or *voting* (same task run several times, results aggregated). Good for guardrails and review.
  - **Orchestrator-workers** — a lead model decomposes the task at runtime and delegates to workers. Use when subtasks can't be predefined.
  - **Evaluator-optimizer** — one model generates, another critiques against criteria, loop until it passes. Use when clear evaluation criteria exist and iteration adds value.
- Both GPT and Gemini perform better on focused prompts than bundled mega-prompts; use separate templates for distinct subtasks.

### Agentic Systems
When designing multi-step or multi-agent workflows:
- **The agent loop is `gather context → act → verify → repeat`.** The verify step is load-bearing — pick the *cheapest verifier that fits the output*: rules/code first (linters, type-checks, validators, unit tests — the most reliable signal), a visual check second (screenshot-diff against a target), an LLM-as-judge last (least robust, highest latency — use only when the boost is worth it). This is the external signal the critic step needs (see *Reducing Hallucinations*).
- **Subagent design** - give each subagent a focused prompt and a minimal tool set. Choose whether to pass parent context based on the subagent's *relationship to the work*: **fork** (inherit the parent's conversation) for **workers** continuing something the parent already diagnosed - no re-reading files or rediscovering evidence, and prompt caching makes it cheap - and for memory extraction; **isolate** (task description only) for **verifiers/reviewers**, whom inherited reasoning would anchor, and for **parallel researchers**, where forking just duplicates history. Split work by kind: tools for bounded auditable actions, subagents for narrower reasoning with a small toolset, a sandbox for work with intermediate state (files, scripts, iterative transforms) that shouldn't pass through the main context. Either way, return a condensed summary (1-2K tokens) to the orchestrator, not raw exploration. **Spell out four things in every delegation - objective, output format, tool/source guidance, and task boundaries;** vague delegation ("research X") makes subagents duplicate work and leave gaps.
- **State management** — use structured JSON for trackable state (phase progress, scores, pass/fail) and free text for qualitative notes (findings, reasoning). Emit state updates the orchestrator can act on.
- **Context across windows** — when a task spans multiple context windows, start the new window with a structured summary of prior findings, not raw conversation history.
- **Autonomy calibration — prompt says, harness enforces.** Be explicit about what the agent MAY do autonomously vs. what requires confirmation (default: reads autonomous; write/delete and externally-visible operations require confirmation). But a system-prompt prohibition ("never do X") *reduces, not eliminates* the behavior, and a one-time assertion (identity, a pricing rule, a safety limit) decays over long context — so enforce load-bearing guardrails in the harness (least-privilege tools, human approval on irreversible actions, external memory/verification tools over recall), not in prose alone. (Models also misbehave somewhat more when they believe the situation is real rather than an eval.)
- **Subagent spawning is model-version-dependent and steerable** — some models over-spawn, some under-spawn. Don't hardcode an assumption; check the provider reference file and calibrate to observed behavior. State when delegation is and isn't warranted ("delegate for parallel or isolated workstreams; for simple lookups and single-file edits, work directly").
- **Completeness contracts** — for multi-deliverable tasks, instruct the agent to treat the task as incomplete until every requested item is covered or explicitly marked `[blocked]`, maintaining an internal checklist. Prevents premature stopping, especially on GPT-5.4+.
- **Stopping is a harness concern, not just a prompt one ("write loops that prompt the model").** The 2026 frontier models each stop early in their own way: Claude Opus 5.5 ends turns with a progress report, GPT-6 Astra stops to ask a clarifying question or for review of a first implementation, Fable 5.1 describes its next step instead of taking it. All three vendors converge on the same fix: **define "done" up front** (including "get it running, inspect the result, fix what fails" if that's part of done); keep the task's parts in a checklist or TODO tool the model updates (for long, multi-part tasks - on short tasks LangChain found a default planning/todo tool added cost without improving results, so don't bolt it onto everything); treat a text-only end-of-turn as a *report*, not completion; if items remain open with no stated blocker, send a short continuation message naming them (or have a small model check the completion condition); **cap automatic continuations at 2-3** so a genuinely stuck run ends for review. In the prompt, **name the specific early stops you don't want and the stops you do want** (nothing can proceed without the user; a protected blocker) - models respond to that far better than to a generic "be autonomous." Calibrate the opposite way too: approval requests should come after the work that's already authorized, so the user approves a concrete, reviewable result. And don't over-repeat "ask first" - repeated approval language makes current models pause on safe, expected actions.
- **Time is a steering signal for multi-agent runs.** Some current models pace themselves to visible time: appending `elapsed 340s / 1200s` to each harness message made Claude Opus 5.5 lead agents parallelize more and finish sooner at similar quality. A time budget buys parallelism; lower effort cuts work - they're different levers. Keep a hard timeout either way.
- **Reliability ≠ capability — design for consistency, not just a good single run.** A tool-agent that passes ~half of tasks once passes *all* of k repeated trials far less often (τ-bench pass^8 <25%, arXiv:2406.12045), and models "get lost" in multi-turn — dribbling a task out across turns costs ~39% vs. one well-specified turn, because they commit to early assumptions and don't recover (arXiv:2505.06120). So: give a fully-specifiable task in ONE well-formed turn (or periodically re-state a consolidated spec on long runs); tell the agent to hold early assumptions as revisable and not finalize prematurely; move rule-checkable steps (eligibility, limits) into deterministic checks rather than free-form reasoning; and evaluate with repeated-trial consistency (pass^k), not a single pass.
- **Empty-result recovery** — when a lookup returns empty or narrow results, instruct the agent to try at least one fallback (alternate query wording, broader filter) before reporting "not found." Reduces false-negative reports across all providers.
- **Search wide, then narrow** — tell research/tool-using agents to start with short, broad queries to survey the space before drilling into specifics; they default to over-long, over-specific queries that return too little.
- **Tool-use persistence** — instruct the agent not to stop early when another tool call is likely to materially improve correctness or completeness. Keep calling tools until the task is done and verification passes.
- **Token budgets** — for workloads where the agent should scope its work to an allowance, some providers expose an advisory budget the model can see and pace against (distinct from a hard `max_tokens` cap). See the provider reference file.
- **Multi-agent topology** — when you do split into multiple agents, pick the coordination shape deliberately: **supervisor** (a central agent routes to and aggregates specialized workers — predictable, debuggable, the orchestrator-workers pattern) vs **swarm** (peers hand off control directly to one another — flexible, no bottleneck, harder to trace). Supervisor is the safe default; reach for swarm only when peer-to-peer handoff genuinely fits. Either way, give each agent a focused prompt + minimal tools, and decide explicitly what shared state crosses the handoff. The framework reference (`${CLAUDE_SKILL_DIR}/references/langgraph.md`) shows how these map to concrete primitives.
- **Scale effort to the task, and budget the cost.** Rough depth heuristics: a simple fact-find ≈ 1 agent / 3–10 tool calls; a comparison ≈ 2–4 subagents / 10–15 calls each; a complex task ≈ 10+ subagents with divided roles. Fan-out is expensive — an agent spends ~4× the tokens of a chat turn and a multi-agent system ~15× (token usage alone explained ~80% of performance variance in Anthropic's research), so reach for subagents only when the task's value justifies the spend.

### Sampling Parameters and Determinism
Caller-controlled sampling is effectively gone on frontier reasoning models. **Claude (Opus 4.7+, Sonnet 5, all Claude 5.x) returns a 400** on non-default `temperature`/`top_p`/`top_k`; **GPT-6 rejects `temperature`/`top_p`/`top_logprobs` whenever reasoning effort isn't `none`** (Astra has no `none`, so always; Azure/Foundry reasoning models likewise); **Gemini 3.x says to leave them at default** (below-1.0 temperature risks looping) and its migration checklists strip them. Two consequences:
- Don't reach for `temperature` to steer behavior — use explicit prompting, structured outputs, and the reasoning/effort knob instead.
- `temperature = 0` never guaranteed identical outputs anyway. For determinism, constrain the output (structured outputs, enum fields, explicit format rules) rather than lowering temperature.

## B. Tool Descriptions

Tool descriptions are **the single most impactful quality factor** for tool-use accuracy across all three providers. Write them like prompts — they are loaded into the agent's context and collectively steer tool-calling behavior.

### Minimum Requirements
- **Full models: 3-4 sentences minimum.** Budget models: 5-6 sentences. The minimum is about *coverage* of the six elements below, not length - on frontier models, trim hand-holding written for weaker ones (OpenAI's GPT-6 migration and LangChain's Deep Agents v0.7, which cut built-in tool descriptions 43% at equal reward, both found leaner descriptions win), and never repeat a tool's guidance in the system prompt.
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
| Strict schema | Structured Outputs + strict tool use (`strict: true`) | `strict: true` for 100% schema adherence | Up to 512 declarations; 10-20 active recommended; structured output combines with tools |
| Forcing a call | **Opus 5.5 / Fable 5.1 reject `tool_choice` `any`/`tool` (400)** - say in the prompt when the tool applies; older models still accept it | `tool_choice` supported | `function_calling_config.mode: ANY` |
| Where guidance lives | Claude 5: the tool description — delete the system-prompt duplicate; earlier models sometimes needed the reinforcement | Put tool-specific guidance in the description, not the system prompt | Description; append runtime hints to the function-response text |
| Tool preambles | Not needed; on Opus 5.5 / Fable 5.1 the between-call narration arrives in thinking blocks (`display:"updates"`) | Two uses: (1) "explain why" before a call → better accuracy; (2) short user-visible "acknowledge + plan + first step" in streaming → better perceived responsiveness | **Don't require structured text (XML/JSON) right before a call** - it can fail with `Malformed_Function_Call`; put notes in an `update()` tool instead |
| Error recovery | Handles well natively | Handles well natively | Add: "Don't repeat failed calls with identical arguments" |
| Scope creep risk | Moderate on 5.x - Opus 5 widens tasks, Fable 5.1 adds unrequested fixes and tests; constrain scope explicitly | Lower on GPT-6 (Astra respects task boundaries and may *under*-reach); keep "Do ONLY what is requested" for GPT-5.x | Moderate |

### Effective Patterns from Production Systems
- **Decision-tree routing**: "Use X for Y. Do not use Z — use W instead." Direct, unambiguous tool selection.
- **When to use / When NOT to use as first-class sections** — put these at the top of the description, not buried after parameter docs. Include specific triggers, not just "when relevant."
- **Name alternatives explicitly**: "Do NOT use for searching employees — use search_employees instead." The model needs to know what to call instead.
- **Safety constraints separated** — mark irreversible or dangerous operations distinctly from functional description.
- **Concrete thresholds** — "3+ steps" not "complex tasks"; "at least 2 characters" not "enough text." Numeric where possible.

### Input Examples
For complex tools with nested objects, optional parameters, format-sensitive inputs, or tools easily confused with each other — supply 1-5 valid example inputs. On Claude this is a first-class field on the tool definition, `input_examples`, not prose buried in the description; Anthropic's internal testing puts it at **72% → 90% on complex parameter handling** ([advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use)). They add tokens to every request, so they earn their place where the schema is genuinely hard to guess and not where it's self-evident.

Keep this distinct from examples that teach a model **how or when to call** a tool. For the Claude 5 generation Anthropic reports those constrain the model to the exploration space the examples imply — design an expressive interface instead. A `status` enum of `pending`/`in_progress`/`completed` conveys the state machine, and one line ("keep exactly one item `in_progress`") conveys the rule, with no example needed. `input_examples` answers *"what does a valid input look like"*; interface design answers *"when do I reach for this."*

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
| Instruction placement | Top works best; a short tail reminder helps length control on Opus 5 | Developer message: identity → instructions → examples → context; state each rule once (GPT-5.6+ loses quality on repeated instructions) | Critical constraints in the system instruction or at the start of the prompt; query after long context |
| Multi-turn drift | System prompt persists well | Older GPT models needed key instructions re-appended in long chats; on current models, resend per-request `instructions` rather than repeating rules | System instruction persists - but must be re-sent on every Interactions call |
| Default verbosity | Model-specific: Opus 5.5 clearer and less wordy than Opus 5 (which ran long); Fable 5.1 dense prose and *less* formatting; prompt explicitly for a fixed style | `text.verbosity` param (low often best); GPT-6 Astra leans to lists/tables/Markdown and stock phrases, Sol/Luna slightly shorter | Terse - request elaboration explicitly |
| State scoping | Append-only history required on Opus 5.5 / Fable 5.1 (edits invalidate thinking); change instructions via mid-conversation system messages | Responses `instructions` is per-request - not carried by `previous_response_id` | Interactions API: `system_instruction` / `tools` / `generation_config` per-call - resend each turn |

### Prompting Style

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Aggressive language | **Avoid** - proactive by default; aggressive prompting causes overtriggering and over-action | Unnecessary (highly steerable); on GPT-6 strong "ask first" boundary language makes Astra stop too early | Avoid - causes over-analysis |
| Literal following | Claude 4.7+ follows instructions literally - it will not silently generalize a rule; state instruction scope explicitly ("apply to every section") | Surgical precision; conflicting instructions are damaging, and GPT-6 Astra also obeys skills/`AGENTS.md` more literally | Follows well-structured prompts closely |
| Initiative default | Leans autonomous (Opus 5.x / Fable over-delegate and can widen scope); unattended runs may stop to report | GPT-6 Astra leans to asking and early review stops - prompt for follow-through; GPT-5.6 Sol ran long | 3.8 Flash self-verifies and calls tools iteratively (token-hungry) |
| Chain-of-thought | Not needed — use adaptive thinking | **Harmful** on reasoning models — degrades performance | Not needed — use `thinking_level` |
| Prompt length | Medium-length prompts work well | Longer prompts tolerated | Short, direct prompts work best |
| Structuring | XML tags (strongest support) | XML or markdown (JSON wrapping degrades perf) | XML, markdown, or plain text — be consistent |
| Persona handling | Follows but maintains guardrails | Follows reasonably | Takes personas VERY seriously — may override other instructions |
| Non-English output | Follows prompt language naturally | Needs mild nudging | Requires aggressive: "RESPOND IN {LANGUAGE}. YOU MUST RESPOND UNMISTAKABLY IN {LANGUAGE}." |

### Reasoning and Thinking

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Mechanism | Adaptive thinking; `effort`: low/medium/high/xhigh/max | `reasoning.effort`: none/low/medium/high/xhigh/max (+ `reasoning.mode` standard/pro) | `thinking_level`: minimal/low/medium/high (3.7/3.8 Flash: no `minimal`) |
| Default state | **Opus 5.5 and Fable 5.x: thinking always on** (`disabled` → 400); Opus 5 / Sonnet 5 on by default; Opus 4.8 **off** unless `thinking:{type:"adaptive"}`. Default `effort`: **Opus 5.5 `medium`**, all others `high` | GPT-6 Astra: `low`-`max` (no `none`), default undocumented - pin it; GPT-6 Sol/Luna and GPT-5.6: `medium`; GPT-5.4/Mini/Nano: `none` | 3.8/3.7/3.6/3.5 Flash `medium`; 3.1 Pro `high`; 3.5 Flash-Lite `minimal` |
| Change effort mid-session | Per-message effort (system message with `output_config.effort`, beta) keeps the cache on Opus 5.x / Fable 5.1 | `configuration_update` input item keeps the cache on GPT-6 | Per-call `generation_config` (Interactions API re-sends it anyway) |
| Sampling params | **Removed on Claude 4.7+ and all 5.x** - non-default `temperature`/`top_p`/`top_k` → 400 | **Rejected on GPT-6 unless effort is `none`**; unsupported on Azure/Foundry reasoning models | Leave at default on 3.x - below-1.0 temperature risks looping |
| Trace reuse | Thinking blocks passed back unmodified; bound to the conversation on Opus 5.5 / Fable 5.1 | `previous_response_id` (or replay `encrypted_content`); 5.6+ renders prior reasoning by default | Stateful Interactions (`previous_interaction_id`) manages thought signatures; stateless must round-trip them |

Reasoning effort is a **last-mile knob, not a primary quality lever**. Before raising effort, exhaust completeness contracts, verification loops, and tool-use persistence (Section A). Higher effort is not automatically better — it can cause overthinking, especially with contradictory instructions or weak stopping criteria.

As a **cost** knob it's the first one to turn, and the cheapest experiment there is (Anthropic's measured playbook, detailed in `claude.md`; the pattern generalizes): **sweep two or three effort levels on a sample of your own traffic before adding models or architecture** - on research and knowledge work the accuracy-vs-cost curve was nearly flat (low effort gave up 1-3 points for a third to half the cost), while long-horizon coding genuinely bought accuracy with effort. When outcomes are checkable (tests, a verifier), **run everything at low effort and re-run only the failures higher** - same pass rate at about half the cost. Compare models by **cost per solved task on your hardest ~10% of traffic**, not per-token price: a more capable model at low effort often beats a cheaper model at its default. And ask for the answer you'll actually read - a one-line decision format matched a five-section memo's accuracy at a sixth of the output tokens, and in agent loops every output token is re-read as input on each later turn.

### Caching

| Aspect | Claude | GPT | Gemini |
|--------|--------|-----|--------|
| Mechanism | Opt-in: automatic top-level `cache_control` or explicit breakpoints; min 512 tokens on Opus 5.5 / Fable 5.x | Automatic prefix-based (≥1,024 tokens) + **explicit breakpoints on GPT-5.6+** (`prompt_cache_options.mode:"explicit"`); `prompt_cache_key` optional | Implicit (automatic) + explicit (cached content); **min 4,096 tokens** on current 3.x |
| Cost | Reads 0.1× input (**0.05× on Opus 5.5, 0.025× on Fable 5.1**); writes 1.25× (5-min) / 2× (1-hour) | Reads 0.1× input; **writes 1.25×** on GPT-5.6+ | Reads ~0.1× input plus a per-hour storage fee for explicit caches |
| TTL | 5 min (default) or 1 hour; reads reset TTL | `prompt_cache_options.ttl:"30m"` - at least 30 min after last use (GPT-5.6+) | 1 hour default for explicit caches; configurable |

**Cache-aware prompt design** (applies to all providers, saves 80-90% on input costs):
- **Structure static → dynamic**: place system prompt, tool definitions, and examples first (stable prefix). Put user input and conversation history last. The prefix must be byte-identical across requests.
- **Never reorder**: changing tool order, image order, or message order between requests breaks the cache on all providers. Append new messages — never modify earlier ones.
- **Per-request text goes last**: a timestamp, queue position, or status line placed *ahead of* the stable prefix turns every request into a full cache write - Anthropic measured a 25-token status line at the top of a system prompt taking a run from $0.59 to $4.24, worse than no caching. Put anything that changes per request in the newest user turn. In agent loops, cache hit rate is the number to watch (Anthropic sees a median ~84% of input read from cache; below ~80% something is breaking it) - task cost grows roughly with the square of turn count, so caching usually matters more than model choice.
- **Monitor**: check `cache_read_input_tokens` (Claude), `usage.prompt_tokens_details.cached_tokens` (GPT), or `usage.total_cached_tokens` (Gemini) to verify hits.
- **Change settings without breaking the prefix**: per-turn effort and instruction changes go in as appended items (Claude mid-conversation / turn-scoped system messages and per-message effort; GPT-6 `configuration_update`), not as edits to the top-level request - editing the system prompt, tools, or top-level effort restarts the cache (and on Claude 5.5-generation models, invalidates thinking).

## D. Budget Models

Budget models (Claude Haiku 4.5, GPT-6 Luna and GPT-5.4 Mini/Nano, Gemini 3.5 Flash-Lite) share common patterns. Per-model specifics live in the provider reference files. (The budget line is blurring: GPT-6 Luna and the Gemini 3.7/3.8 Flash models are frontier-family models at budget prices - they need less hand-holding than the list below implies, and 3.7/3.8 Flash can't run at `minimal` thinking; route true no-reasoning volume to Flash-Lite. Haiku 5.5 is announced but not yet shipped.)

### What Changes
- **More explicit instructions** — less capable at inferring intent from context. Put critical rules first; specify full execution order for tool use and side effects.
- **More examples** — 5-6 minimum, simpler patterns, covering more edge cases.
- **Simpler tool sets** — fewer tools with clearer boundaries. Consolidate where possible.
- **Shorter system prompts** — trim context aggressively; budget models lose more from noise.
- **Longer tool descriptions** — 5-6 sentences minimum instead of 3-4.
- **Structural scaffolding** — numbered steps, decision rules, separate "do the work" from "report the result"; don't rely on a bare "MUST."

### Best Uses by Tier

| Task Type | Haiku 4.5 | GPT-6 Luna / 5.4 Mini | Flash / Flash Lite |
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
- Tool schema strictness and structured-output APIs (OpenAI and Claude both offer `strict: true` tools but with different schema subsets; Gemini uses calling modes and a JSON Schema response format) and how to force a tool call (Claude Opus 5.5 / Fable 5.1 no longer allow it)
- Sampling parameters - Claude 4.7+/5.x and GPT-6 (at any effort above `none`) reject them outright and Gemini 3.x discourages them; the safest cross-provider default is to **omit `temperature`/`top_p`/`top_k` entirely** and steer with prompting + structured outputs.

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
- **"Think step by step"** - Harmful on reasoning models (GPT-5.x/6 at non-`none` effort, Claude with thinking on, Gemini 3.x), and on Claude Opus 5.5 / Fable 5.x a request to *write out* reasoning in the reply can be refused outright (`reasoning_extraction`). Unnecessary on standard models with thinking APIs enabled. Explicit CoT earns its cost mainly on **math/logic/symbolic** tasks - a meta-analysis of 100+ papers found ~95% of its MMLU benefit comes from questions containing "=" (Sprague et al., ICLR 2025, arXiv:2409.12183); on knowledge/reading tasks it mostly adds latency, and where the work is symbolic a tool/executor beats more prose reasoning. If you need structured reasoning on standard models, **Step-Back Prompting** (abstract first, then reason) outperforms chain-of-thought by up to 36%.
- **"Don't hallucinate"** — Negative framing is less effective, and hallucination isn't one problem. See "Reducing Hallucinations" in Section A for type-specific mitigations.
- **Setting `temperature` to steer behavior** - Claude 4.7+/5.x and GPT-6 reject it with a 400 error; Gemini 3.x discourages it. Steer with prompting and structured outputs instead.
- **"Don't sound like AI" / "avoid slop"** - vague style bans just swap one default for another. **Define the anti-pattern concretely**: list the stock phrases and constructions to drop (OpenAI's GPT-6 list: "delve", "leverage", "it's worth noting", "Bottom line:", "This isn't about X. It's about Y.", unprompted "X, not Y" contrasts, concluding summary lines), or define the failure and why it fails (Anthropic's "mannered prose": metaphor and flourish substituting for direct statement). Same for design: name the specific default styles to avoid (cream backgrounds, italic accent words, numbered section labels), then iterate on what the model falls back to next.
- **Adding 20+ tools** — Too many overlapping tools is the #1 failure mode across all providers. If you can't choose between two tools as a human, the model can't either.
- **Wrapping APIs as tools** — building 1:1 API-to-tool mappings instead of workflow-oriented tools. `schedule_event` beats separate `list_users` + `list_events` + `create_event`.
- **Hand-writing JSON schemas in the prompt** — use the provider's structured-output feature instead; it's more reliable and removes the validation burden.
- **Rewriting the whole prompt** — When editing, preserve existing structure and tone. Make the minimal change that fixes the issue. Re-read the full prompt after editing.
- **Prompt archaeology neglect** — instructions effective in GPT-4/Claude 3.5 may backfire in newer models. When upgrading, audit prompts for obsolete aggressive encouragement and process over-specification — native capabilities make external prodding redundant.
- **"My old prompt worked - just point it at the new model"** - carrying every legacy instruction forward burns tokens reconciling guidance the new model doesn't need (and can hurt quality on GPT-5.x specifically). Anthropic measured it: prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no accuracy gain, and an audit that removed the stale text made the new model 14% cheaper *and* more accurate (92% → 97%). Instructions the new model follows too literally ("verify twice", "be maximally thorough", mandatory step scripts) cost money; text that no longer fits (retired thinking settings, contradictory rules, a hand-rolled scratchpad fighting native reasoning) cost 7-11 accuracy points each. Audit tool descriptions and skills the same way. Migration order: switch model → pin reasoning effort → re-run evals → trim what's now redundant → only then add new guidance.
- **Assuming all providers behave the same** — They don't. Check Section C and the reference files for differences in instruction placement, verbosity defaults, persona handling, sampling, and thinking config.
- **Trusting all input equally** - Treat external data (user messages, tool results, retrieved documents) as untrusted context, not as instructions. Use delimiters and instruction hierarchy (system > developer > user) to maintain prompt integrity. Especially important for agentic systems where tool results may carry adversarial content. Two hard caveats: (1) the instruction hierarchy is **not reliably enforced** - models don't consistently prioritize system over user on conflicts (arXiv:2502.15851) - so state precedence explicitly ("if X and Y conflict, X wins") and repeat load-bearing constraints near the point of use; (2) **prompt-level injection defenses don't hold** - adaptive attacks broke all 8 tested defenses (arXiv:2503.00061). Spotlighting/datamarking (marking untrusted spans and telling the model to distrust them) reduces naive injection but is a mitigation, not a guarantee. This now extends to **content the user pastes**: wrap each pasted block in tags carrying an app-generated random id (Anthropic's Opus 5.5 pattern: `<pasted_content id="ab12">…</pasted_content id="ab12">`) and tell the model to follow instructions inside only where the user's own message asks it to. For consequential tool-using agents, **contain by design**: least-privilege tools, capability/policy gating, human-confirm on irreversible actions, and separating control-flow (from the trusted instruction) from untrusted data (CaMeL, arXiv:2503.18813). Don't let one agent hold private-data access + untrusted content + external comms at once (the "lethal trifecta"). And beware **many-shot conformity** - enough faux in-context examples of the assistant misbehaving can override safety training (scales with the number of shots; distinct from injection), so screen/classify untrusted *long* inputs upstream before they reach the model.

## H. Testing Prompts

Don't iterate blindly. Before tuning anything, have two things: **success criteria** and **a way to test against them** (Anthropic's [success-criteria and evals guide](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)).

- **Success criteria are specific, measurable, achievable, relevant - and usually multidimensional.** "Classifies sentiment well" is not a criterion; "F1 ≥ 0.85 on a held-out set of 10,000 diverse posts, 99.5% non-toxic, p95 latency < 200 ms" is. Pick the dimensions that matter for the use case - task fidelity (incl. edge cases), consistency across similar inputs, relevance/coherence, tone/style, privacy preservation, context utilization, latency, price - and give each a threshold. Even "hazy" goals quantify ("< 0.1% of 10,000 outputs flagged by the content filter").
- **Not every failing criterion is a prompt problem.** Latency and cost are often fixed faster by a different model or tier (see `model-selection.md`), and a capability gap by a stronger model - check before spending prompt iterations on it.
- **Eval set design:** mirror the real task distribution, including edge cases (irrelevant or missing input, overly long input, poor or harmful user input, cases where even humans would disagree); structure items so grading can be automated; and prefer **more items with slightly noisier automated grading over fewer hand-graded ones**.
- **Grader choice - fastest reliable method wins:** code-based (exact/string match, validators, tests) first; LLM-as-judge for nuanced judgments, validated against a sample of human labels before you scale it; human grading only where unavoidable.

Then iterate:
1. **Identify failures** — run the agent on representative tasks without changes. Note specific failures.
2. **Fix one thing at a time** — make a single change, re-test, measure. Don't bundle multiple changes.
3. **Test on the target model tier** — what works on a frontier model may need more detail for Haiku/Mini/Flash.
4. **Use adversarial inputs** - empty strings, unexpected languages, edge cases, tools that shouldn't be called, and **plausible-sounding nonsense** (real domain vocabulary combined incoherently - fabricated framework names, real concepts from wrong domains, precise numbers for unmeasurable things). Test whether the agent engages confidently with broken premises or pushes back. For a ready-made design, [BullshitBench](https://github.com/petergpt/bullshit-benchmark) enumerates **13 nonsense techniques** (`plausible_nonexistent_framework`, `misapplied_mechanism`, `cross_domain_stitching`, `specificity_trap`, `nested_nonsense`, …) - reuse them to build false-premise fixtures. Weight the hardest ones: across all models the false-precision **`specificity_trap` is caught only ~10% of the time** (precise-sounding detail disarms skepticism; next hardest: cross-domain stitching ~24%, plausible nonexistent frameworks ~27%), and software premises fool models far more than physics (~29% vs ~52% clear pushback across all models, Sept 2026 data). Pair each nonsense fixture with a legitimate *near-miss control* so you score specific-flaw identification, not blanket skepticism: a model that cries "nonsense" at everything aces an all-nonsense set but over-refuses real questions in production. BullshitBench itself has **no legitimate control questions**, so it can't measure over-rejection - your fixture set must.
5. **After 2 failed correction attempts** — stop iterating. Start fresh with a better initial prompt incorporating lessons learned.
6. **When migrating to a newer model** — switch the model first while pinning reasoning effort, run evals, then iterate one change at a time. Avoid carrying every instruction over from older prompt stacks.
7. **Build programmatic evaluations** - Run the agent on representative test cases, score outputs automatically (LLM-as-judge or exact match), track scores across prompt changes. Start small - ~20 representative tasks is enough to begin; early prompt tweaks routinely move success 30%→80%, so don't wait for a big set. For **stateful** agents, grade the *final state*, not the turn-by-turn path - agents reach the same goal by different routes. Keep production prompts **versioned in code** (typed prompt-builder modules, reviewed in PRs, rolled out behind flags) so every change runs through the eval suite - OpenAI is shutting down hosted reusable prompt objects (`v1/prompts`, Nov 30 2026) for exactly this reason. Pin model snapshots in production and re-run the suite on every model upgrade.
8. **Metaprompting** — use the model itself to improve the prompt: paste the prompt and the observed failure, and ask "what specific phrases would you add or delete to elicit X and prevent Y?" Minimal targeted edits beat rewrites; keep the existing prompt intact where possible.
9. **Control the environment, or small deltas are noise.** For agentic evals the sandbox is part of the experiment: Anthropic moved Terminal-Bench scores ~6 points by changing only container resource limits (tight limits OOM-kill runs and reward lean strategies; generous ones let agents pull heavy dependencies). Hold hardware, time limits, and concurrency constant across the arms you compare, report them, repeat runs at different times, and treat differences under ~3 points with suspicion until the setups match.
10. **Keep eval scenarios realistic.** Newer models can detect they're being tested and behave better than in production - so a passing *artificial* guardrail/safety eval can overstate real behavior. Avoid cartoonish or obviously-synthetic setups; make the scenario look like real traffic.

### Writing Evaluation / Judge Prompts
When using LLMs to evaluate outputs (LLM-as-judge), the prompt design differs from system prompts:

**Scale design:**
- Binary (pass/fail) is most reliable. 3-point scales (0/1/2) work well for nuance. Avoid 10-point scales without extensive anchoring.
- Define each score level explicitly with concrete examples of what qualifies.

**Structure:**
- Decompose complex criteria into sub-criteria (G-Eval approach). Ask the judge to evaluate each sub-criterion before producing a final score - and **keep per-criterion scores and comments visible instead of trusting one aggregate.** Similarweb lost a week reverting a good prompt change because two criteria (source breadth vs. attribution) moved in opposite directions inside the average; the per-criterion comments showed it immediately. Give every criterion explicit score anchors (what 0.0 / 0.3 / 0.8 / 1.0 look like), return a short gap + one-sentence reason per criterion, and check criteria for conflicting incentives (e.g. conciseness rewarded more clearly than completeness shortens reports that needed depth).
- Match the method to the output: golden answers work for focused questions; long-form outputs need anchored rubrics, **faithfulness checks** (does each claim follow from the retrieved data?), and **A/B judgment against an accepted baseline** rather than isolated absolute scores.
- Require reasoning BEFORE the score, not after, and **discard the reasoning** - parse only the verdict. Chain-of-thought in judges reduces randomness. On judge models with always-on thinking (Claude Opus 5.5 / Fable 5.x, GPT/Gemini at non-minimal effort) native thinking already gives you reasoning-before-verdict; ask for the verdict (plus at most a short rationale field) rather than "write out your reasoning in `<thinking>` tags", which Opus 5.5 can decline as `reasoning_extraction`.
- Give the judge a concrete, checkable rubric ("The answer must mention 'Acme Inc.' in the first sentence; if it does not, grade 'incorrect'"). One criterion may need several rubrics for a holistic grade.
- Use structured output (JSON) for scores to ensure parseable results.

**Calibration:**
- Provide 2-3 few-shot examples per score level showing realistic edge cases (+25-30% accuracy improvement).
- Don't count on low temperature for consistency - current frontier models reject it or discourage it. Get stable scores from a tight rubric, binary or 3-point scales, structured output, and repeated runs (majority vote or mean).

**Bias mitigation:**
- **Position bias**: In pairwise comparisons, randomize output order and average across positions.
- **Self-preference**: Use a different model as judge than the generator (reduces bias 10-25%).
- **Judge repeatability**: a judge can be accurate on average and still flip on identical input. Score the same traces several times and measure variance as well as agreement with human labels (LangChain's "signal value" = accuracy × repeatability). In one study, repeated LLM judges agreed with the human label 80-99.8% of the time depending on the model, while a small typed decision model (returning a choice or probability, not text) matched 100% at ~1/80th the cost - cheap enough to score every production trace. Calibrate any judge by hand-labeling real traces, running the judge, and iterating on its prompt where it disagrees; a miscalibrated judge is worse than none because it gives false confidence.
- **Verbosity bias**: Add explicit length controls or penalization.
- **Hedging bias**: Judge practical effect on the user, not tone. "Did the response actually reject the broken premise, or just add a disclaimer before answering it anyway?"
- **Don't grade by the chain-of-thought**: a model's stated reasoning is a scratchpad that *influences* the answer, not a faithful audit of it — models verbalize an outcome-changing hint only ~25–39% of the time (Anthropic, arXiv:2505.05410). Judge the *output* against the requirement; don't score correctness by how plausible the reasoning looks, and don't rely on visible CoT as a safety monitor.

**Anti-pattern:** Vague criteria like "rate the quality 1-10" produce inconsistent results. Specific criteria ("Does the response identify the factual error in the premise? Score 0 if it engages without pushback, 1 if it flags concerns but still answers, 2 if it makes the error the central point.") produce reliable judgments.

**Anti-pattern — judge prompt overriding the fixture's ground truth.** When fixtures carry explicit specs (e.g. `tools_required: [X, Y]`, `tools_forbidden: [Z]`, `expected_facts: [...]`), the judge prompt should treat those as the ground truth for that fixture — not as suggestions to weigh against its own opinion of what's correct. Concrete failure mode observed in a production bench: the judge prompt included "for procedure/test/dental queries: BOTH tools must be called in parallel" as a general rule. For 7+ adversarial fixtures that explicitly list `tools_required: [get_user_policy]` only (the test is "don't engage the fabricated premise"), the judge applied its own routing override and scored tool_use=0 even though the agent perfectly matched the fixture spec. Fix: remove the override, make the fixture's `tools_required` literally the ground truth. Result: 7 of 7 affected fixtures moved up (+0.8 to +2.2 each) with zero agent change. **When a judge has an opinion about what "should" be true, but the fixture spec says otherwise, the fixture wins** — otherwise the bench measures judge bias, not agent quality.

**Where to look for this**: any judge-prompt clause that begins "for [topic] queries..." or "if the question involves [X], the answer should..." — these are universal overrides that fire across all fixtures regardless of their specific spec. Audit those clauses against fixtures of the matching topic; if some fixtures legitimately need different behavior than the override prescribes, the override is wrong.

## Templates and References

Templates in `${CLAUDE_SKILL_DIR}/templates/`:
- `system-prompt-template.md` — Contract-style system prompt structure
- `tool-description-template.md` — Structured tool description format

Provider deep-dives in `${CLAUDE_SKILL_DIR}/references/` — read the one matching your model family:
- `claude.md` — Claude (Anthropic API, AWS Bedrock, Vertex AI, Microsoft Foundry)
- `gpt.md` — GPT (OpenAI API, Azure / Microsoft Foundry, AWS Bedrock)
- `gemini.md` — Gemini (Gemini API, Vertex AI)

Framework deep-dive (provider-agnostic; read in addition to a provider file when the agent is built on it):
- `langgraph.md` - LangGraph / LangChain / Deep Agents: choosing among the three layers, how context engineering (write/select/compress/isolate), memory (State/checkpointer/Store), middleware (incl. routing and action guards), and multi-agent (supervisor/swarm, fork vs isolated subagents) map to concrete primitives, plus LangChain's 2026 eval practice

Task playbooks (provider-agnostic; read when the agent's job is clearly one of these):
- `use-cases.md` - task-specific levers for coding agents / SWE (incl. code review), deep research / RAG, data analysis / SQL, extraction / classification, and multimodal / document AI

Model selection (read when *choosing* a model, not when prompting one — keep it out of the prompt-authoring context):
- `model-selection.md` - cross-provider intelligence/coding/agentic snapshot, cost per task, Arena agent rankings, false-premise detection (BullshitBench), "good at what," and model-choice and routing decision rules. Dated and directional; re-pull live numbers before relying on a figure.
