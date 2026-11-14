# prompt-engineer

Expert prompt-engineering reference for AI agents on the **Claude, GPT, Gemini, Kimi, and Grok** APIs. Covers system-prompt structure, tool descriptions (the single highest-leverage quality factor), context engineering, provider differences, budget-model patterns, cross-provider compatibility, anti-patterns, and evaluation / judge-prompt design.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Two problems, and the second is the reason this is a skill rather than a document.

**Prompt engineering is provider-specific in ways that don't generalize.** Roughly 70% of the discipline is universal — role framing, XML delimiters, positive instruction, decision rules over absolutes. The other 30% is version-specific knobs that change every release: reasoning-effort defaults, sampling-parameter removals, thought signatures, caching mechanics, "stop doing" lists, migration breakages. Advice written from the universal layer alone is confidently stale, and stale prompt advice looks exactly like good prompt advice.

**So the skill enforces a load order.** Step 0 identifies the model family from the code in scope — not the platform, because AWS Bedrock serves GPT, Claude, Kimi, *and* Grok, Vertex serves Gemini, Claude, *and* Grok, and Microsoft Foundry serves GPT, Claude, Grok, *and* Kimi — then reads the matching `references/<family>.md` **before** giving any advice. Not the SDK import either: Kimi and Grok are usually called through the OpenAI SDK with a different `base_url`. That discipline is the skill's actual product. Skipping it is the #1 failure mode, and the symptom is a user repeatedly asking "did you read the provider-specific file?"

It also triggers on the right things. Nobody says "I have a prompt problem." They say *"the agent keeps calling the wrong tool,"* *"why is it ignoring my instructions,"* *"it got worse after the model upgrade,"* or they paste a log.

## What it does

```
LLM code / prompt / failure report in scope
        │
        ▼
Step 0a: identify model family from imports, model IDs, SDK calls
        │  claude · gpt · gemini · kimi · grok  (load all that match; if none, check 0d, then ask)
        ▼
Step 0b: read references/<family>.md IN FULL — the version-specific knobs
        │  (Claude: claude.md + the per-model file: opus / fable / sonnet-haiku)
        ▼
Step 0c (evals, judges, failed runs): also read references/evals.md
        │
        ▼
Step 0d (framework code → langgraph.md; a coding agent's CLAUDE.md /
        │  AGENTS.md → the writing-project-instructions skill;
        │  an agent harness → agent-harness-patterns.md + a use-cases playbook)
        ▼
universal layer (≈70%) + provider layer (≈30%)
        │
        ▼
minimal targeted edit ──▶ re-read whole prompt for contradictions ──▶ test
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install prompt-engineer@shaharsha-skills
```

That installs only this skill. For the whole `building-agents` bundle, run `/plugin install building-agents@shaharsha-skills` instead.

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/prompt-engineer" ~/.claude/skills/prompt-engineer
```

## Quick start

There's nothing to run — this is a reference library the agent loads. It fires on its own when prompt-shaped work is in scope. To invoke it deliberately:

- "review this system prompt for our Claude agent"
- "the agent keeps picking the wrong tool — look at the tool descriptions"
- "we're migrating this prompt from GPT-5.6 to GPT-6, what changes"
- "write a judge prompt to evaluate these outputs"

## What's in the box

| Path | What |
|---|---|
| `SKILL.md` | The universal layer: system-prompt structure, altitude, tool descriptions, context engineering, anti-patterns, eval design |
| `references/claude.md` | Claude / Anthropic — current models, the 5.5-generation API contract (incl. Fable 5.2's breaking changes), effort defaults, sampling, thinking, caching, migration checklists |
| `references/claude-opus.md`, `claude-fable.md`, `claude-sonnet-haiku.md` | Per-model Claude prompting: Opus 5.5 / 5 / 4.8; Fable 5.2 / 5.1 and Mythos; Sonnet 5.5, Haiku 5.5, Sonnet 5, Haiku 4.5 (read with `claude.md`) |
| `references/gpt.md` | GPT / OpenAI incl. Azure and AWS Bedrock — verbosity, reasoning effort, host contracts, the "stop doing" list |
| `references/gemini.md` | Gemini / Google incl. Vertex — Gemini 4 Carbon, Argon and Hydrogen, the Decisions API, long decode, thought signatures (incl. Gemini 4 prefix binding), caching, thinking cost |
| `references/kimi.md` | Kimi / Moonshot — K3.1 Pro's always-on thinking, fixed sampling, `reasoning_content` replay, MFJS tool schemas, host differences |
| `references/grok.md` | Grok / xAI — Grok 4.7's encrypted reasoning, sampling values (required on xAI's API, rejected by Bedrock Converse), server-side tools (web/X search), caching keys, compaction |
| `references/langgraph.md` | LangGraph / LangChain / Deep Agents: layers, context primitives, typed HITL, skill-bound tools, harness profiles, MCP, subagent context modes, eval practice |
| `references/evals.md` | Evaluating and debugging agents: eval design, eval integrity (answer leakage, visible tests, side effects, milestones), diagnosing a run from its traces, judge prompts and calibration, gate classifiers for agent actions, reporting a judged pass rate |
| `references/agent-harness-patterns.md` | The harness around an agent: act or ask, approvals and who can give them, async work, mid-task steering, compaction prompts, modes, delegation, goal loops, one prompt for several models, helper prompts |
| `references/use-cases.md` | Task playbooks: coding and code review, app builders, research/RAG, data/SQL, extraction, multimodal, chat assistants, document agents, voice agents, browser agents |
| `references/model-selection.md` | Intelligence, cost per task, agent rankings, false-premise detection, routing math |
| `templates/` | Reusable prompt scaffolds |
| `SOURCES.md` | For maintainers: where each rule in the agent-harness guidance came from (official docs, vendors' open-source prompts, and public collections of extracted prompts), with commits and line references. The research record behind it is in [`docs/research/prompt-engineer/`](../../docs/research/prompt-engineer/) |

## The rules that carry the most weight

- **Tool descriptions are the highest-leverage surface in an agent.** More output quality moves through them than through the system prompt.
- **Aim for the right altitude** — between brittle if-this-then-that logic and vague high-level guidance. "Minimal" doesn't mean short; it means the smallest set of high-signal tokens that fully outlines the desired behaviour.
- **Lead with the outcome, not the procedure.** Describe the destination — success criteria, constraints, allowed side effects, output shape, stopping conditions — rather than prescribing steps. Reserve step-by-step for cases where the exact path is product-critical.
- **Prefer decision rules over absolutes.** "If the action is reversible, proceed; otherwise confirm" generalizes. "ALWAYS confirm" does not. Save hard rules for genuine invariants.
- **Tell the model what TO do.** Positive framing beats negative — and on Gemini, negative phrasing actively backfires.
- **Check for contradictions before shipping an edit.** If two rules conflict the model picks arbitrarily; remove one.
- **A model upgrade is a new model family, not a drop-in swap.** Switch the model, pin reasoning effort, re-run evals, *trim* instructions the new model no longer needs, and only then add new guidance. Legacy prompts routinely over-specify processes newer models handle natively.

## Gotchas

- **The universal section is not enough for "small" changes.** Even a one-line prompt edit interacts with provider defaults — reasoning effort, thinking, caching, sampling. Load the reference file first, every time.
- **The platform never tells you the model family.** Bedrock, Vertex, and Foundry each host multiple families. Identify the family from model IDs and `base_url` (then imports), then load *that* file.
- **Kimi and Grok break two cross-provider defaults.** Kimi fixes its sampling values and degrades silently if you don't replay the full assistant message; Grok on xAI's API asks you to *set* `temperature` 0.7 / `top_p` 0.95 instead of omitting them (Bedrock's Converse API rejects them). Both are in their reference files.
- **If no provider is identifiable, ask.** A wrong-provider answer is worse than one clarifying question.
- **Provider-doc claims need a second reader.** When refreshing a reference file, have another model with live web check the new claims before they land (pair-intelligence does this); in one refresh it caught two overstatements the author had missed.
- **This skill's reference files go stale by design.** They track a fast-moving model roster; when a new flagship ships, the provider files need refreshing — and a refreshed model list sitting above an unrefreshed body section is the failure mode to watch for.
- **Local-only hook interaction:** if you use a `PreToolUse` hook that gates edits to prompt files, this skill's Step 0 touches the flag file that unblocks it. That's a personal-setup detail, not part of the skill's contract.

## Related skills

- [pair-intelligence](../pair-intelligence) - cross-model review: have Codex or Gemini check a prompt, a plan, or a provider-doc claim in a fresh context.
- [writing-project-instructions](../writing-project-instructions) — the sibling for CLAUDE.md / AGENTS.md, which is instruction-writing for a *coding agent* rather than for an API prompt.

## License

MIT — see [LICENSE](../../LICENSE).
