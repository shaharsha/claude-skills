# Claude (Anthropic) — Provider Deep-Dive

Applies to the **Claude model family** wherever it runs: the Anthropic API, AWS Bedrock, Google Vertex AI, and Microsoft Foundry. The platform does not change prompt engineering — the model version does.

**Current models (July 2026):** the **Claude 5 family** now tops the lineup, above the 4.x Opus tier:

- **Claude Fable 5** (`claude-fable-5`) — Anthropic's **most capable widely-released model** ("Mythos-class"); reach for it on the most demanding reasoning and long-horizon agentic work. GA June 9 2026. $10 / $50 per MTok.
- **Claude Mythos 5** (`claude-mythos-5`) — Fable 5's twin **without safety classifiers**, invitation-only via Project Glasswing (defensive-cyber); same specs/pricing/API as Fable 5. Use `claude-fable-5` unless the org is in Glasswing.
- **Claude Opus 5** (`claude-opus-5`, GA July 24 2026) — the **recommended default flagship** and current **#1 on the AA Intelligence & Coding indices** (~60.7 / 78, above Fable 5), at **$5 / $25** (same as Opus 4.8, ~½ of Fable 5) with a **May 2026 knowledge cutoff**. Replaces Opus 4.8 as the default — see the *Opus 5* section for its behavioral deltas.
- **Claude Opus 4.8** (`claude-opus-4-8`) — the previous flagship, still available at the same $5 / $25; prefer Opus 5 unless you specifically want 4.8's thinking-off-by-default behavior.
- **Claude Sonnet 5** (`claude-sonnet-5`, supersedes Sonnet 4.6) — best speed/intelligence balance, near-Opus on coding/agentic. $3 / $15 (intro $2 / $10 through Aug 31 2026).
- **Claude Haiku 4.5** (`claude-haiku-4-5`) — fastest / budget tier. $1 / $5.

Opus 5, the Claude 5 models, and Opus 4.8 share a **1M context window and 128K max output**; **Opus 5's reliable knowledge cutoff is May 2026 — 4 months newer than the rest of the family's Jan 2026** (Haiku 4.5 = 200K context, 64K output, Feb 2025 cutoff). **Opus 5 is now the practical default**, but this file's body is still written around **Opus 4.8** — Opus 5 runs existing 4.8 prompts well, so most guidance below carries; the **Opus 5 section covers the deltas that change or reverse it** (thinking on by default, higher verbosity, more subagents, self-verification), and the Fable 5 / Sonnet 5 sections cover those models. Opus 4.8 **builds on Opus 4.7 and runs existing 4.7 prompts unchanged — no breaking API changes from 4.7** (if your code is on Opus 4.6 or earlier, also apply the 4.7 migration steps — those *did* break: sampling params rejected, extended-thinking budgets removed, new tokenizer).

## Contents
- **Opus 5 — current default (deltas from Opus 4.8)**
- Effort and thinking
- Sampling parameters (removed)
- Task budgets
- Tokenizer and token budgeting
- Literal instruction following
- Verbosity and tone
- Tool use and subagents
- Migrating away from prefill
- Caching
- Mid-conversation system messages
- Fast mode
- Refusal stop details
- Agentic and long-horizon work
- Overengineering
- Code review harnesses
- Frontend design
- Vision
- Fable 5 and Mythos 5
- Sonnet 5 and Haiku 4.5
- Opus 4.7 → 4.8 migration checklist (and moving to Sonnet 5 / Fable 5)

## Opus 5 — current default (deltas from Opus 4.8)

**Claude Opus 5** (`claude-opus-5`, GA July 24 2026) is the new recommended default: **#1 on the AA Intelligence Index (~60.7) and AA Coding Index (78)**, at Opus 4.8's price ($5/$25) with a **May 2026 knowledge cutoff**. It runs existing Opus 4.8 prompts well, so migration is a model-ID swap plus these behavior changes — most of which mean *removing* legacy scaffolding, because Opus 5 leans more autonomous:

- **Thinking is ON by default** (the reverse of Opus 4.8's off-by-default). The model self-decides depth; `effort` is the control; `thinking:{type:"adaptive"}` still equals the default. **Breaking rule:** `thinking:{type:"disabled"}` is accepted only at effort ≤`high` — pairing it with `xhigh`/`max` returns a 400.
- **More verbose across the board** — conversational replies, agentic narration, *and* files it writes to disk all run longer than 4.8, and **`effort` controls thinking, not output length** (lowering it won't shorten the visible answer). Prompt for concision explicitly (*"keep responses focused and brief; spend most of the response on the main answer"*) and add length calibration for Claude-authored documents.
- **Remove verification / self-check scaffolding** — Opus 5 verifies and self-corrects unprompted. "Include a final verification step," "use a subagent to verify," and "double-check your answer" now cause *over*-verification (wasted tokens, no quality gain) — delete them. It also narrates corrections more; scope that down if it's user-facing.
- **Spawns subagents MORE readily** (the reverse of Opus 4.8's fewer) — cap it: delegate only for large, genuinely independent tracks; never to verify its own work; keep spawn counts low.
- **Scope creep** — it can widen a task or add unrequested steps; for narrow work, constrain scope (*"deliver what was asked, at the scope intended; check in only when different readings would lead to materially different work"*).
- **If you disable thinking** (only possible at ≤`high`), two artifacts appear, worst on tool-heavy/search work: **tool calls can leak into visible text** (never execute, pollute history) — allow a one-sentence pre-tool preamble; and **internal `<thinking>`/XML tags can leak** — *remove* any "don't think/don't reason" rule (it *increases* leakage) and use a general *"don't include internal or system XML tags."* Better: keep thinking on and lower `effort` instead of disabling.
- **Safety & retention:** ZDR-eligible (no data-retention floor, unlike Fable 5). Has cyber classifiers but **~85% less restrictive than Fable 5's** — allows source-code vuln finding; blocks binary scanning / pentest / exploit-gen; flagged requests **fall back to Opus 4.8** (default in the apps, opt-in on the API), returning `stop_reason:"refusal"` as with Fable 5.

Everything below (the effort ladder, caching, mid-conversation system messages, fast mode, vision, etc.) still applies to Opus 5 — just tune by *subtracting* prod-and-verify scaffolding and *adding* concision. See Anthropic's *Prompting Claude Opus 5* guide for the full set.

## Effort and thinking

Opus 4.8 uses **adaptive thinking** and the `effort` parameter (low/medium/high/xhigh/max). Things that break old assumptions:

- **`effort` now defaults to `high`** on all surfaces (Claude API and Claude Code). If you set it explicitly, your value is unchanged. Effort is more consequential on 4.8 than on any prior Opus — experiment with it actively when you upgrade.
- **Effort levels are recalibrated vs 4.7:** `medium` now allows somewhat *more* thinking, `high` somewhat *less*, and `xhigh` *substantially more*. If you tuned a level against 4.7 cost/latency, **re-baseline at the same level before adjusting**.
- **Adaptive thinking is OFF by default *on Opus 4.8/4.7*.** A request with no `thinking` field runs with no thinking. Set `thinking: {type: "adaptive"}` explicitly to enable it. (`budget_tokens` extended thinking is removed — `thinking: {type:"enabled", budget_tokens:N}` returns a 400 error. Adaptive is the only thinking-on mode and outperforms extended thinking in Anthropic's evals.) On 4.8, adaptive thinking decides **per turn** whether to reason — responding directly on simple lookups, reasoning on hard multi-step problems — which cuts wasted thinking tokens on bimodal workloads vs 4.7 at the same effort.
- **This default is model-specific across the family** — don't assume it: **Opus 5** runs adaptive **on by default** (the reverse of 4.8) and only lets you disable thinking at effort ≤`high` (`xhigh`/`max` + `disabled` → 400); **Sonnet 5** runs adaptive when you *omit* `thinking` (on by default); **Fable 5 / Mythos 5** have thinking **always on** (you cannot disable it — `thinking:{type:"disabled"}` returns 400); **Haiku 4.5** has no adaptive thinking at all (use extended thinking with `budget_tokens`). See the family sections below.
- **Thinking content is omitted from responses by default.** Thinking blocks still stream but their `thinking` field is empty unless you opt in with `thinking: {type:"adaptive", display:"summarized"}`. If your product streams reasoning to users, the default looks like a long pause before output — set `display:"summarized"` to restore visible progress.

Effort guidance (Opus 4.8 and Opus 5 share the ladder and the `high` default):
- `xhigh` — best for most coding and agentic use cases.
- `high` — the default; minimum recommended for intelligence-sensitive use cases.
- `medium` — cost-sensitive work that can trade some intelligence.
- `low` — short, scoped, latency-sensitive tasks that are not intelligence-sensitive.
- `max` — intelligence-demanding tasks; can show diminishing returns and occasional overthinking.

Opus 4.8 respects effort **strictly**, especially at the low end — at `low`/`medium` it scopes work to exactly what was asked (so on moderately complex tasks at `low` there's some under-thinking risk). If you see shallow reasoning on hard problems, raise effort rather than prompting around it. If you must stay at `low` for latency, add targeted guidance: *"This task involves multi-step reasoning. Think carefully through the problem before responding."*

Adaptive-thinking triggering is steerable. Large/complex system prompts can make the model think more often than you want; counter with: *"Thinking adds latency and should only be used when it will meaningfully improve answer quality — typically multi-step reasoning. When in doubt, respond directly."* When thinking is disabled, Claude is sensitive to the word "think" — prefer "consider," "evaluate," "reason through."

At `max`/`xhigh`, set a large `max_tokens` (start at 64k) so the model has room to think and act across tool calls.

## Sampling parameters (removed)

Setting `temperature`, `top_p`, or `top_k` to any non-default value on Opus 4.8 (same as 4.7) returns a **400 error**. Omit them entirely. `temperature = 0` never guaranteed identical outputs anyway — for determinism, constrain the output with Structured Outputs, enum fields, and explicit format rules, and use prompting to guide behavior.

## Task budgets (beta)

A `task_budget` gives Claude a rough token target for a full agentic loop (thinking + tool calls + results + output). The model sees a running countdown and paces itself to finish gracefully. Set the beta header `task-budgets-2026-03-13` and add `output_config: {effort:..., task_budget:{type:"tokens", total:N}}`. Minimum 20k tokens.

This is **advisory**, not a hard cap — distinct from `max_tokens` (a hard per-request ceiling the model never sees). Use `task_budget` when you want the model to self-moderate; use `max_tokens` as the hard ceiling. For open-ended work where quality matters more than speed, don't set a task budget — too tight a budget makes the model cut corners or refuse.

## Tokenizer and token budgeting

Opus 4.7+ (including 4.8) use a tokenizer that may consume **~1x to 1.35x as many tokens** as Opus 4.6 for the same text (varies by content) — a one-time change at the 4.6→4.7 jump, unchanged in 4.8. `count_tokens` returns different numbers than pre-4.7. Give `max_tokens` and any compaction triggers extra headroom. Opus 4.8 serves the **full 1M-token context window by default** at standard pricing (no long-context premium, no beta header) on the Claude API, Amazon Bedrock, and Vertex AI; **Microsoft Foundry caps it at 200k**. Max output is 128k tokens.

## Literal instruction following

Opus 4.8 interprets prompts literally and explicitly (as 4.7 did), especially at lower effort. It will **not silently generalize** an instruction from one item to another, and will not infer requests you didn't make. This is good for structured extraction and predictable pipelines. If you need an instruction applied broadly, state the scope: *"Apply this formatting to every section, not just the first one."*

## Verbosity and tone

Opus 4.8 calibrates response length to perceived task complexity — short on simple lookups, long on open-ended analysis — rather than a fixed verbosity. **(Opus 5 breaks this: it runs longer than 4.8 across replies, agentic narration, and written files, and `effort` won't shorten output — prompt for concision explicitly; see the Opus 5 section.)** If your product needs a fixed style, prompt for it explicitly; positive examples of the right concision beat "don't be verbose." Tone is direct and opinionated, with little validation-forward phrasing and sparing emoji. If you need a warmer voice: *"Use a warm, collaborative tone. Acknowledge the user's framing before answering."*

Two formatting defaults worth knowing: the latest models **default to LaTeX** for math/equations (add a plain-text instruction if you don't render LaTeX — *"Write all math in plain text: `/` for division, `*` for multiply, `^` for exponents; no `\( \)`, `$`, or `\frac{}{}`"*), and they lean toward markdown lists/bold; for flowing prose, instruct positively (*"write in flowing prose paragraphs; reserve markdown for code and headings"*) rather than "don't use markdown."

## Tool use and subagents

Opus 4.8 favors **reasoning over tool calls** — usually better results — but **triggers required tools more reliably than 4.7** (the 4.7 issue of skipping a tool call the task needed is largely fixed). Raising `effort` is still the main lever to increase tool usage (`high`/`xhigh` show substantially more tool use in agentic search and coding). If a specific tool is under-used, describe explicitly when and why to use it. **For any tool-using agent, turn adaptive thinking ON (`thinking:{type:"adaptive"}`) — it's OFF by default on Opus 4.8, and external agent evals (LMArena Agent Arena) show tool-hallucination jumping to ~19% with thinking off vs ~0.2% with it on. Don't run agentic tool loops on the thinking-off default.**

Opus 4.8 also gives **more regular, higher-quality user-facing progress updates** across long agentic traces. If you added scaffolding to force interim status messages ("after every 3 tool calls, summarize progress"), remove it; if the updates aren't calibrated to your product, describe what they should look like and give an example.

Opus 4.8 spawns **fewer subagents** by default (**Opus 5 inverts this — it over-delegates; cap it, per the Opus 5 section**). This is steerable — give explicit guidance when subagents are wanted:

```
Do not spawn a subagent for work you can complete directly in a single response.
Spawn multiple subagents in the same turn when fanning out across items or reading multiple files.
```

For maximum parallel tool calling (~100% reliability), instruct: *"If you intend to call multiple tools with no dependencies between them, make all the independent calls in parallel. Never use placeholders or guess missing parameters."*

## Migrating away from prefill

Prefilled responses on the last assistant turn are unsupported on Claude 4.6+ (400 error). Replace common uses: force output format → Structured Outputs; skip preamble → "Respond directly without preamble"; continue an interrupted response → move the partial text into the user turn and ask the model to continue.

## Caching

Claude uses developer-controlled `cache_control` breakpoints. Cache reads are 10% of input cost. Place the system prompt, tool definitions, and examples first as a byte-identical stable prefix; append new messages at the end; never reorder tools or messages. Check `cache_read_input_tokens` to confirm hits. The memory tool pairs naturally with multi-window workflows. On Opus 4.8 the **minimum cacheable prompt is 1,024 tokens** (lower than 4.7), so short prompts that couldn't cache before now can with no code change. To update instructions mid-conversation **without** breaking the cached prefix, use a mid-conversation system message (below) instead of rebuilding the message history.

## Mid-conversation system messages

New in Opus 4.8: you can place a `role: "system"` message in the `messages` array immediately after a user turn (subject to placement rules) to append updated instructions partway through a long conversation — **without restating the full system prompt**. This is the cache-friendly way to inject new guidance: earlier turns stay byte-identical so their prompt-cache hits survive, cutting input cost on agentic loops. No beta header. Use the top-level `system` field for instructions that apply from the start; use a mid-conversation system message for mid-run updates. (Earlier models, including 4.7, reject `role: "system"` in `messages` with a 400 error — so this also lets you delete any code that rebuilds the whole history just to update instructions.)

## Fast mode

Opus 4.8 offers **fast mode** (research preview on the Claude API): set `speed: "fast"` (beta header `fast-mode-2026-02-01`) for up to ~2.5× higher output tokens/sec from the *same model* at premium pricing. It changes throughput, not the model or its quality — reach for it on latency-sensitive interactive surfaces, not to save cost.

## Refusal stop details

When Claude declines a request, the response carries a `stop_details` object (alongside the existing `refusal` stop reason) describing the **category** of refusal — now publicly documented (available since 4.7). Read it to tell apart classes of declined request and route the user to the right next step instead of treating every refusal identically. No beta header, no opt-out.

**Fable 5 / Mythos 5 refusals go further:** their safety classifiers can return `stop_reason: "refusal"` (at HTTP 200, even mid-completion). Handle this stop reason explicitly and opt into a graceful `fallbacks` behavior rather than surfacing a raw truncated response — see the Fable 5 section for details. **Opus 5** carries the same mechanism but far milder — cyber classifiers ~85% less likely to fire than Fable 5's, falling back to Opus 4.8; handle its `stop_reason:"refusal"` the same way.

## Agentic and long-horizon work

- **Context awareness** — Claude 4.x tracks its remaining context window. If your harness compacts or saves state to files, tell the model so it doesn't wrap up early: *"Your context window will be compacted as it approaches its limit... do not stop tasks early due to token budget concerns. Save progress to memory before the window refreshes."*
- **Multi-window tasks** — use the first window to set up scaffolding (write tests, `init.sh`), later windows to iterate against a todo list and a structured `tests.json`. Starting a fresh window often beats compaction — Claude is strong at rediscovering state from the filesystem and git.
- **State** — structured JSON for trackable state, freeform notes for progress, git for checkpoints.
- **Balancing autonomy and safety** — Claude may take hard-to-reverse actions without guidance. For confirmation-gating: *"Take local, reversible actions (editing files, running tests) freely, but for destructive or externally-visible actions — deleting files/branches, force-push, posting to shared systems — ask first. Never use destructive shortcuts like `--no-verify`."*
- **Interactive vs. autonomous coding** — Opus 4.8 uses *more* tokens in interactive, multi-turn coding sessions (it reasons more after each user turn), which helps long-horizon coherence but costs more. To get both performance and efficiency, specify the task, intent, and constraints **fully in the first turn**, run at `xhigh`/`high`, and add an auto mode that reduces the number of human turns — an underspecified prompt dribbled across turns is the inefficient path (and matches the "one well-specified turn" finding in SKILL.md).

## Overengineering

Claude can over-deliver — extra files, unnecessary abstractions, unrequested flexibility. Counter with a scoped guidance block: don't add features/refactors/"improvements" beyond what was asked; don't add docs or error handling for code you didn't change or for scenarios that can't happen; no abstractions for one-time operations. *"The right amount of complexity is the minimum needed for the current task."*

## Code review harnesses

Opus 4.8 is meaningfully better at finding bugs (higher recall and precision). But a harness tuned for an older model that says "only report high-severity issues" / "be conservative" / "don't nitpick" — Opus 4.8 follows that faithfully and may investigate just as deeply but report fewer findings, which looks like a recall drop. Fix: separate finding from filtering. *"Report every issue you find, including low-severity and uncertain ones — coverage is the goal here; a separate step will rank and filter. Include a confidence level and estimated severity for each finding."* If you must self-filter in one pass, set a concrete bar ("bugs that could cause incorrect behavior, a test failure, or a misleading result") rather than qualitative terms.

## Frontend design

Opus 4.8 has strong design instincts but a persistent default house style — warm cream/off-white backgrounds (~`#F4F1EA`), serif display type (Georgia, Fraunces, Playfair), italic accents, terracotta/amber (it shows up in slide decks as well as web UIs). Great for editorial/hospitality/portfolio; wrong for dashboards, dev tools, fintech, healthcare, enterprise. Generic instructions ("make it clean," "no cream") just shift it to another fixed palette. Two reliable fixes: (1) specify a concrete alternative palette/typography precisely — the model follows explicit specs well; (2) ask the model to propose 3-4 distinct visual directions first and let the user pick (this also replaces using `temperature` for design variety, which is unavailable). Opus 4.8 needs *less* frontend prompting than prior models to avoid "AI slop"; a short `<frontend_aesthetics>` block discouraging generic fonts (Inter, Roboto), cliché purple-on-white gradients, and cookie-cutter layouts works well combined with either fix.

## Vision

High-resolution image support (introduced in Opus 4.7, retained in 4.8) — up to 2576px / 3.75MP, with model coordinates 1:1 to actual pixels (no scale-factor math). Strong at pointing, measuring, counting, and bounding-box localization. High-res images cost more tokens; downsample when the extra fidelity isn't needed. For computer use, 1080p is a good performance/cost balance (720p or 1366×768 for cost-sensitive workloads). A crop/"zoom" tool gives a consistent uplift on image tasks.

## Fable 5 and Mythos 5

**Claude Fable 5** (`claude-fable-5`) is Anthropic's most capable widely-released model — the top of the "Mythos-class" tier — and it widens its lead over Opus 4.8 the longer and more complex the task. Same API surface as Opus 4.7/4.8, with a few Fable-specific points:

- **Thinking is always on and cannot be disabled** — omit the `thinking` parameter; an explicit `thinking:{type:"disabled"}` returns a 400. The raw chain of thought is never returned; get summaries with `display:"summarized"`. `effort` still applies (low/medium/high/xhigh/max).
- **Safety-classifier refusals:** Fable 5's classifiers target **offensive cybersecurity** (exploits, malware, attack tooling), **biology/life-sciences**, and **extraction of its summarized thinking** — benign security/bio work can trip them too (Mythos 5 has *no* classifiers). A declined request returns `stop_reason:"refusal"` at HTTP 200 (not an error) and **names which classifier fired**. You aren't billed for a refusal that produces no output, and on retry `fallbacks` earns a **fallback credit** refunding the prompt-cache switch cost — so configure server- or client-side fallback to **Opus 4.8** rather than shipping a truncated response.
- **No assistant prefill** (as with the whole 4.6+/5 family); non-default sampling params rejected; same tokenizer as Opus 4.8 (token counts roughly unchanged vs 4.7/4.8).
- **Data-retention floor:** requires 30-day data retention — **not available under Zero Data Retention (ZDR)**. Factor this into any ZDR-bound deployment.
- Pricing $10/$50 per MTok; 1M context, 128K max output. It's ~2× the price of Opus 4.8 — reserve it for genuinely hard, long-horizon work, not routine calls.

**Claude Mythos 5** (`claude-mythos-5`) — identical capabilities, pricing, limits, and API behavior to Fable 5; only the model ID differs, and it's **invitation-only through Project Glasswing** (defensive cybersecurity), where it succeeds the earlier `claude-mythos-preview`. Prompt it exactly like Fable 5; use `claude-fable-5` unless the org participates in Glasswing.

**Prompting Fable 5** — the API surface matches Opus 4.8, but Fable behaves differently enough to re-tune for. These are the highest-leverage deltas (full set in Anthropic's *Prompting Claude Fable 5* guide):

- **Effort: default `high`, reserve `xhigh`** for the most capability-sensitive work; `medium`/`low` for routine. This inverts the Opus 4.8 advice (where `xhigh` is the coding default) — Fable's *lower* effort levels already often beat prior models at `xhigh`, so drop effort if a task finishes correctly but slower than needed.
- **Turns run much longer by default** — minutes at high effort, hours autonomously. Raise client timeouts, stream, and structure harnesses to check runs *asynchronously* rather than blocking. Curb over-planning on ambiguous tasks: *"When you have enough information to act, act. If you're weighing a choice, give a recommendation, not an exhaustive survey."*
- **Dispatches parallel subagents *more* readily than Opus 4.8** (which spawns fewer) — use them freely, prefer async orchestrator↔subagent messaging over blocking on each return, and keep long-lived subagents that carry context (cache-read savings). Don't carry over any "spawn fewer subagents" scaffolding written for Opus 4.8.
- **Steer with one brief instruction, not an enumeration** — instruction-following is strong enough that a single *"lead with the outcome; be selective about what you include rather than compressing into fragments"* line replaces listing every verbosity pattern. The overengineering-guard block still earns its place at high effort.
- **Ground progress claims against tool results** — *"Before reporting progress, audit each claim against a tool result from this session; if something isn't verified, say so."* In Anthropic's testing this nearly eliminated fabricated status reports on long runs.
- **Harness patterns**: state boundaries explicitly (Fable can take unrequested actions — drafting an email, defensive git-branch backups); give it a **memory place** (a Markdown notes file to read/write lessons); for long async agents add a **`send_to_user` tool** (tool inputs are never summarized, so verbatim deliverables survive intact) and, if your harness shows a context-budget countdown, reassure it not to hand off or summarize early.

## Sonnet 5 and Haiku 4.5

Most of this file is written for Opus 4.8, but the two lighter current models share the same foundations with a few important differences. Use Fable 5 / Opus 4.8 for the hardest, longest-horizon work; drop to Sonnet 5 when turnaround and cost matter more; use Haiku 4.5 for high-volume, latency-critical, bounded tasks.

**Claude Sonnet 5** (`claude-sonnet-5`, supersedes Sonnet 4.6) — the best speed/intelligence balance, near-Opus on coding and agentic work; 1M-token context, 128k output, $3/$15 per MTok ($2/$10 intro through Aug 31 2026), Jan 2026 knowledge cutoff. **Adaptive thinking is ON by default** (omitting `thinking` runs adaptive — the *opposite* of Opus 4.8), and `budget_tokens` extended thinking is removed. Like Opus 4.8 it **defaults to `effort: high`** on the Claude API and Claude Code — set it explicitly (`effort` supports low/medium/high/xhigh/max) or expect higher latency than you intend; `medium` suits most apps, `low` for high-volume/latency-sensitive. As a migration rule of thumb, Sonnet 5 at `medium` ≈ Sonnet 4.6 at `high`, and Sonnet 5 at `high` ≈ 4.6 at `max` — benchmark by observed thinking length, not effort name. Unlike Fable 5, Sonnet 5 *can* turn thinking off (`thinking:{type:"disabled"}`). Set a large `max_tokens` (64k) at medium/high so it has room to think and act. Uses the new tokenizer (~30% more tokens for the same text vs Sonnet 4.6) and high-resolution vision (2576px). (**Sonnet 4.6**, `claude-sonnet-4-6`, remains active as the previous-generation Sonnet — adaptive thinking, 1M context — but prefer Sonnet 5.)

**Claude Haiku 4.5** (`claude-haiku-4-5`, dated `…-20251001`) — the fastest model, with near-frontier intelligence; 200k-token context, 64k output, $1/$5 per MTok, reliable knowledge cutoff Feb 2025. **It does not support adaptive thinking or the `effort` parameter** — use **extended thinking with `budget_tokens`** (`thinking: {type:"enabled", budget_tokens:N}`; ~16k is a sane starting budget). Excellent for classification, routing, extraction, and high-volume batch work. Apply the universal budget-model patterns: more explicit instructions, more (simpler) few-shot examples, a small clearly-bounded tool set, and "do the work" separated from "report it." It has context awareness (tracks its remaining window) like the other 4.x models.

Two cross-cutting notes: prefill on the last assistant turn is **unsupported on all 4.6+ and 5 models** (400), so the prefill-migration guidance above applies to Sonnet 5, Fable 5, and Haiku 4.5 too. The hard 400 on non-default `temperature`/`top_p`/`top_k` is documented for Opus 4.7/4.8, Sonnet 5, and Fable 5 — for Haiku 4.5 it isn't explicitly stated, but omit sampling params anyway and steer with prompting + structured outputs (the determinism argument holds across the family). Model ID formats differ per platform (Bedrock `anthropic.claude-…`, Vertex `claude-…@date`).

## Opus 4.7 → 4.8 migration checklist (and moving to Sonnet 5 / Fable 5 / Opus 5)

No breaking API changes — code on 4.7 runs unchanged. These are behavior/knob checks after swapping the model ID:

1. Switch the model ID to `claude-opus-4-8` (or update aliases).
2. **Re-evaluate `effort`.** Default is now `high` on all surfaces; set `xhigh` explicitly for coding/high-autonomy. Levels are recalibrated (`medium` more thinking, `high` less, `xhigh` substantially more) — **re-baseline cost/latency at your chosen level before adjusting.**
3. If you rebuild conversation history to update instructions, switch to a **mid-conversation system message** to preserve prompt-cache hits.
4. Verify stop-reason handling reads `stop_details` on refusals.
5. Remove scaffolding 4.8 no longer needs: forced interim status updates (its progress reporting is better), anti-laziness/tool-prodding, forced subagent counts. Run evals before adding anything new.
6. Sampling params stay rejected (400 on non-default) and adaptive is still the only thinking-on mode — both unchanged from 4.7, so no action if you already migrated off them.

**Coming from Opus 4.6 or earlier?** First apply the 4.7 migration, which *does* have breaking changes: remove `temperature`/`top_p`/`top_k` (non-default → 400); replace `thinking:{type:"enabled", budget_tokens:N}` with `thinking:{type:"adaptive"}` + `output_config:{effort:...}` (add `display:"summarized"` if you stream reasoning); bump `max_tokens`/compaction triggers for the ~1–1.35× tokenizer; replace prefill (see *Migrating away from prefill*); state instruction scope explicitly where you relied on generalization. Then apply the 4.7→4.8 steps above.

**Moving to Sonnet 5?** From Sonnet 4.6 it's mostly a model-ID swap: `budget_tokens` extended thinking is gone (adaptive is on by default when you omit `thinking`), `effort` now defaults to `high` (set it explicitly), and the new tokenizer means ~30% more tokens — bump `max_tokens`. Non-default sampling params and last-turn prefill both 400. **Moving to Fable 5?** Same 4.7/4.8 baseline, plus: you cannot disable thinking (`thinking:{type:"disabled"}` → 400 — omit it), handle `stop_reason:"refusal"` with a `fallbacks` policy, and confirm your deployment allows 30-day retention (Fable 5 is **not** ZDR-eligible).

**Moving from Opus 4.8 to Opus 5?** Swap the model ID to `claude-opus-5`. Thinking is now **on by default** (omitting `thinking` reasons; `disabled` is valid only at effort ≤`high`, else 400). Then *remove*, don't add: verification/double-check instructions, forced subagent counts, and any "don't think/don't reason" rules — Opus 5 over-verifies, over-delegates, and leaks internal tags under those. *Add* explicit concision + document-length calibration (it's more verbose than 4.8). ZDR-eligible; carries milder cyber classifiers that fall back to Opus 4.8. Full deltas in the *Opus 5* section above.
