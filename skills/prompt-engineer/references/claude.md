# Claude (Anthropic) — Provider Deep-Dive

Applies to the **Claude model family** wherever it runs: the Anthropic API, AWS Bedrock, and Google Vertex AI. The platform does not change prompt engineering — the model version does.

**Current models (May 2026):** Claude Opus 4.7 (`claude-opus-4-7`), Claude Sonnet 4.6, Claude Haiku 4.5. Opus 4.7 is the frontier model — strongest at long-horizon agentic work, coding, knowledge work, vision, and memory. It runs existing Opus 4.6 prompts well out of the box; the items below are what most often needs tuning.

## Contents
- Effort and thinking
- Sampling parameters (removed)
- Task budgets
- Tokenizer and token budgeting
- Literal instruction following
- Verbosity and tone
- Tool use and subagents
- Migrating away from prefill
- Caching
- Agentic and long-horizon work
- Overengineering
- Code review harnesses
- Frontend design
- Vision
- Opus 4.6 → 4.7 migration checklist

## Effort and thinking

Opus 4.7 uses **adaptive thinking** and the `effort` parameter (low/medium/high/xhigh/max). Two things changed in 4.7 and break old assumptions:

- **Adaptive thinking is OFF by default.** A request with no `thinking` field runs with no thinking. Set `thinking: {type: "adaptive"}` explicitly to enable it. (`budget_tokens` extended thinking is removed — `thinking: {type:"enabled", budget_tokens:N}` returns a 400 error. Adaptive is the only thinking-on mode and outperforms extended thinking in Anthropic's evals.)
- **Thinking content is omitted from responses by default.** Thinking blocks still stream but their `thinking` field is empty unless you opt in with `thinking: {type:"adaptive", display:"summarized"}`. If your product streams reasoning to users, the default looks like a long pause before output — set `display:"summarized"` to restore visible progress.

Effort guidance for Opus 4.7:
- `xhigh` (new, between high and max) — best for most coding and agentic use cases.
- `high` — minimum recommended for intelligence-sensitive use cases.
- `medium` — cost-sensitive work that can trade some intelligence.
- `low` — short, scoped, latency-sensitive tasks that are not intelligence-sensitive.
- `max` — intelligence-demanding tasks; can show diminishing returns and occasional overthinking.

Opus 4.7 respects effort **strictly**, especially at the low end — at `low`/`medium` it scopes work to exactly what was asked. If you see shallow reasoning on hard problems, raise effort rather than prompting around it. If you must stay at `low` for latency, add targeted guidance: *"This task involves multi-step reasoning. Think carefully through the problem before responding."*

Adaptive-thinking triggering is steerable. Large/complex system prompts can make the model think more often than you want; counter with: *"Thinking adds latency and should only be used when it will meaningfully improve answer quality — typically multi-step reasoning. When in doubt, respond directly."* When thinking is disabled, Claude is sensitive to the word "think" — prefer "consider," "evaluate," "reason through."

At `max`/`xhigh`, set a large `max_tokens` (start at 64k) so the model has room to think and act across tool calls.

## Sampling parameters (removed)

Setting `temperature`, `top_p`, or `top_k` to any non-default value on Opus 4.7 returns a **400 error**. Omit them entirely. `temperature = 0` never guaranteed identical outputs anyway — for determinism, constrain the output with Structured Outputs, enum fields, and explicit format rules, and use prompting to guide behavior.

## Task budgets (beta)

A `task_budget` gives Claude a rough token target for a full agentic loop (thinking + tool calls + results + output). The model sees a running countdown and paces itself to finish gracefully. Set the beta header `task-budgets-2026-03-13` and add `output_config: {effort:..., task_budget:{type:"tokens", total:N}}`. Minimum 20k tokens.

This is **advisory**, not a hard cap — distinct from `max_tokens` (a hard per-request ceiling the model never sees). Use `task_budget` when you want the model to self-moderate; use `max_tokens` as the hard ceiling. For open-ended work where quality matters more than speed, don't set a task budget — too tight a budget makes the model cut corners or refuse.

## Tokenizer and token budgeting

Opus 4.7 uses a new tokenizer that may consume **~1x to 1.35x as many tokens** as Opus 4.6 for the same text (varies by content). `count_tokens` returns different numbers than before. Give `max_tokens` and any compaction triggers extra headroom. Opus 4.7 provides a 1M-token context window at standard pricing (no long-context premium).

## Literal instruction following

Opus 4.7 interprets prompts more literally than 4.6, especially at lower effort. It will **not silently generalize** an instruction from one item to another, and will not infer requests you didn't make. This is good for structured extraction and predictable pipelines. If you need an instruction applied broadly, state the scope: *"Apply this formatting to every section, not just the first one."*

## Verbosity and tone

Opus 4.7 calibrates response length to perceived task complexity — short on simple lookups, long on open-ended analysis — rather than a fixed verbosity. If your product needs a fixed style, prompt for it explicitly; positive examples of the right concision beat "don't be verbose." Tone is more direct and opinionated than 4.6, with less validation-forward phrasing and fewer emoji. If you need a warmer voice: *"Use a warm, collaborative tone. Acknowledge the user's framing before answering."*

## Tool use and subagents

Opus 4.7 uses tools **less often** than 4.6 and reasons more — usually better results. Raising `effort` is the main lever to increase tool usage (`high`/`xhigh` show substantially more tool use in agentic search and coding). If a specific tool is under-used, describe explicitly when and why to use it.

Opus 4.7 also spawns **fewer subagents** by default. This is steerable — give explicit guidance when subagents are wanted:

```
Do not spawn a subagent for work you can complete directly in a single response.
Spawn multiple subagents in the same turn when fanning out across items or reading multiple files.
```

For maximum parallel tool calling (~100% reliability), instruct: *"If you intend to call multiple tools with no dependencies between them, make all the independent calls in parallel. Never use placeholders or guess missing parameters."*

## Migrating away from prefill

Prefilled responses on the last assistant turn are unsupported on Claude 4.6+ (400 error). Replace common uses: force output format → Structured Outputs; skip preamble → "Respond directly without preamble"; continue an interrupted response → move the partial text into the user turn and ask the model to continue.

## Caching

Claude uses developer-controlled `cache_control` breakpoints. Cache reads are 10% of input cost. Place the system prompt, tool definitions, and examples first as a byte-identical stable prefix; append new messages at the end; never reorder tools or messages. Check `cache_read_input_tokens` to confirm hits. The memory tool pairs naturally with multi-window workflows.

## Agentic and long-horizon work

- **Context awareness** — Claude 4.x tracks its remaining context window. If your harness compacts or saves state to files, tell the model so it doesn't wrap up early: *"Your context window will be compacted as it approaches its limit... do not stop tasks early due to token budget concerns. Save progress to memory before the window refreshes."*
- **Multi-window tasks** — use the first window to set up scaffolding (write tests, `init.sh`), later windows to iterate against a todo list and a structured `tests.json`. Starting a fresh window often beats compaction — Claude is strong at rediscovering state from the filesystem and git.
- **State** — structured JSON for trackable state, freeform notes for progress, git for checkpoints.
- **Balancing autonomy and safety** — Claude may take hard-to-reverse actions without guidance. For confirmation-gating: *"Take local, reversible actions (editing files, running tests) freely, but for destructive or externally-visible actions — deleting files/branches, force-push, posting to shared systems — ask first. Never use destructive shortcuts like `--no-verify`."*

## Overengineering

Claude can over-deliver — extra files, unnecessary abstractions, unrequested flexibility. Counter with a scoped guidance block: don't add features/refactors/"improvements" beyond what was asked; don't add docs or error handling for code you didn't change or for scenarios that can't happen; no abstractions for one-time operations. *"The right amount of complexity is the minimum needed for the current task."*

## Code review harnesses

Opus 4.7 is meaningfully better at finding bugs (higher recall and precision). But a harness tuned for an older model that says "only report high-severity issues" / "be conservative" / "don't nitpick" — Opus 4.7 follows that faithfully and may investigate just as deeply but report fewer findings, which looks like a recall drop. Fix: separate finding from filtering. *"Report every issue you find, including low-severity and uncertain ones — coverage is the goal here; a separate step will rank and filter. Include a confidence level and estimated severity for each finding."* If you must self-filter in one pass, set a concrete bar ("bugs that could cause incorrect behavior, a test failure, or a misleading result") rather than qualitative terms.

## Frontend design

Opus 4.7 has strong design instincts but a persistent default house style — warm cream/off-white backgrounds (~`#F4F1EA`), serif display type, italic accents, terracotta/amber. Great for editorial/hospitality/portfolio; wrong for dashboards, dev tools, fintech, healthcare, enterprise. Generic instructions ("make it clean," "no cream") just shift it to another fixed palette. Two reliable fixes: (1) specify a concrete alternative palette/typography precisely — the model follows explicit specs well; (2) ask the model to propose 3-4 distinct visual directions first and let the user pick. A short `<frontend_aesthetics>` block discouraging generic fonts (Inter, Roboto), cliché purple-on-white gradients, and cookie-cutter layouts works well combined with either.

## Vision

Opus 4.7 is the first Claude with high-resolution image support — up to 2576px / 3.75MP, with model coordinates 1:1 to actual pixels (no scale-factor math). Better at pointing, measuring, counting, and bounding-box localization. High-res images cost more tokens; downsample when the extra fidelity isn't needed. For computer use, 1080p is a good performance/cost balance.

## Opus 4.6 → 4.7 migration checklist

1. Switch the model ID to `claude-opus-4-7`.
2. Remove `temperature`/`top_p`/`top_k` — non-default values now 400.
3. Replace `thinking:{type:"enabled", budget_tokens:N}` with `thinking:{type:"adaptive"}` + `output_config:{effort:...}`. Add `display:"summarized"` if you stream reasoning.
4. Decide effort explicitly — `xhigh` for coding/agentic, `high` minimum for intelligence-sensitive.
5. Bump `max_tokens` and compaction triggers for the new tokenizer (~1–1.35x tokens).
6. Re-baseline: remove scaffolding the model no longer needs (forced status updates, "double-check the layout," anti-laziness prodding, forced subagent counts). Run evals before adding anything new.
7. State instruction scope explicitly where you previously relied on the model generalizing.
