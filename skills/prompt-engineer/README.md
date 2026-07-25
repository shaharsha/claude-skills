# prompt-engineer

Expert prompt-engineering reference for AI agents on the **Claude, GPT, and Gemini** APIs. Covers system-prompt structure, tool descriptions (the single highest-leverage quality factor), context engineering, provider differences, budget-model patterns, cross-provider compatibility, anti-patterns, and evaluation / judge-prompt design.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Two problems, and the second is the reason this is a skill rather than a document.

**Prompt engineering is provider-specific in ways that don't generalize.** Roughly 70% of the discipline is universal — role framing, XML delimiters, positive instruction, decision rules over absolutes. The other 30% is version-specific knobs that change every release: reasoning-effort defaults, sampling-parameter removals, thought signatures, caching mechanics, "stop doing" lists, migration breakages. Advice written from the universal layer alone is confidently stale, and stale prompt advice looks exactly like good prompt advice.

**So the skill enforces a load order.** Step 0 identifies the model family from the code in scope — not the platform, because AWS Bedrock serves GPT *and* Claude, Vertex serves Gemini *and* Claude, and Microsoft Foundry serves GPT *and* Claude — then reads the matching `references/<family>.md` **before** giving any advice. That discipline is the skill's actual product. Skipping it is the #1 failure mode, and the symptom is a user repeatedly asking "did you read the provider-specific file?"

It also triggers on the right things. Nobody says "I have a prompt problem." They say *"the agent keeps calling the wrong tool,"* *"why is it ignoring my instructions,"* *"it got worse after the model upgrade,"* or they paste a log.

## What it does

```
LLM code / prompt / failure report in scope
        │
        ▼
Step 0a: identify model family from imports, model IDs, SDK calls
        │  claude · gpt · gemini  (load all that match; ask if none)
        ▼
Step 0b: read references/<family>.md IN FULL — the version-specific knobs
        │
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
/plugin install building-agents@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/prompt-engineer" ~/.claude/skills/prompt-engineer
```

## Quick start

There's nothing to run — this is a reference library the agent loads. It fires on its own when prompt-shaped work is in scope. To invoke it deliberately:

- "review this system prompt for our Claude agent"
- "the agent keeps picking the wrong tool — look at the tool descriptions"
- "we're migrating this prompt from GPT-5.5 to 5.6, what changes"
- "write a judge prompt to evaluate these outputs"

## What's in the box

| Path | What |
|---|---|
| `SKILL.md` | The universal layer: system-prompt structure, altitude, tool descriptions, context engineering, anti-patterns, eval design |
| `references/claude.md` | Claude / Anthropic — effort defaults, sampling, thinking, caching, migration notes |
| `references/gpt.md` | GPT / OpenAI incl. Azure — verbosity, reasoning effort, the "stop doing" list |
| `references/gemini.md` | Gemini / Google incl. Vertex — thought signatures, caching, thinking cost |
| `references/model-selection.md` | Benchmarks and cost across providers |
| `templates/` | Reusable prompt scaffolds |

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
- **The platform never tells you the model family.** Bedrock, Vertex, and Foundry each host multiple families. Identify the family from imports and model IDs, then load *that* file.
- **If no provider is identifiable, ask.** A wrong-provider answer is worse than one clarifying question.
- **This skill's reference files go stale by design.** They track a fast-moving model roster; when a new flagship ships, the provider files need refreshing — and a refreshed model list sitting above an unrefreshed body section is the failure mode to watch for.
- **Local-only hook interaction:** if you use a `PreToolUse` hook that gates edits to prompt files, this skill's Step 0 touches the flag file that unblocks it. That's a personal-setup detail, not part of the skill's contract.

## Related skills

- [writing-project-instructions](../writing-project-instructions) — the sibling for CLAUDE.md / AGENTS.md, which is instruction-writing for a *coding agent* rather than for an API prompt.

## License

MIT — see [LICENSE](../../LICENSE).
