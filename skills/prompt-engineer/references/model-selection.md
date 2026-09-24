# Model Selection & Cost (cross-provider)

> **Scope - read this when *choosing* a model, not when *prompting* one.** Which tier for a task, at what budget, good at what. For *how to write the prompt* once you've picked, use `claude.md` / `gpt.md` / `gemini.md`. Keep this file **out of the prompt-authoring context** - benchmark tables are low-signal noise while writing a prompt (the "context rot" caution in SKILL.md Section A applies to the skill itself).
>
> **Staleness - the numbers are a dated snapshot, the *relationships* are the durable part.** Sources: Artificial Analysis Intelligence Index (API pull **2026-09-23**), Arena (formerly LMArena) Agent arena (**2026-09-15**), BullshitBench (repo pulled **2026-09-23**). **AA re-based its index between July and September** - scores dropped ~10 points across the board (Opus 5 at max: 60.7 in July, 50.8 now), so **never compare against the July numbers**. Releases now land weekly (Opus 5.5 and GPT-6 Sol/Luna shipped Sept 22 and have only a headline AA score so far). Trust the **bands, gaps, and "good at what" shape**; re-pull before relying on a figure. AA API: `GET https://artificialanalysis.ai/api/v2/data/llms/models` with header `x-api-key` (fields: `evaluations.*`, `pricing.*`, `median_output_tokens_per_second`). Arena: arena.ai/leaderboard/<arena>.

## Snapshot - AA Intelligence Index (2026-09-23)

Best available effort per model unless noted. Coding = AA Coding Index; Agentic = TerminalBench 2.1 (%); `$/1M` = AA blended price (3:1 in:out, **intro prices where they apply**); tok/s = median output speed (blank = not yet measured). "-" = sub-benchmarks not yet published.

| Model | Intel | Coding | Agentic | $/1M blended | tok/s |
|-------|:-----:|:------:|:-------:|:------------:|:-----:|
| **Claude Opus 5.5** (max) - new Sept 22 | 57.6 | - | - | $8.00 | - |
| **Claude Opus 5.5** (xhigh / *medium, default*) | 56.0 / *51.2* | - | - | $8.00 | 84 / 75 |
| **Claude Fable 5.1** (max) | 53.4 | 81.6 | 91% | $20.00 | 63 |
| **GPT-6 Astra** (max) | 52.7 | 76.9 | 88% | $20.00 | 55 |
| **Claude Opus 5** (max) | 50.8 | 78.0 | 89% | $10.00 | 53 |
| **GPT-6 Sol** (max) - new Sept 22 | 47.5 | - | - | $4.00 | 107 |
| **GPT-5.6 Sol** (max) | 47.0 | 77.4 | 88% | $8.00 | 58 |
| **GPT-5.6 Terra** (max) | 42.1 | 76.7 | 88% | $4.50 | 84 |
| **Claude Opus 4.8** (max) | 41.8 | 74.3 | 85% | $10.00 | - |
| **Gemini 3.8 Flash** (high) | 40.9 | 76.3 | 88% | $1.50 (intro) | 315 |
| **Gemini 3.7 Flash** (medium) | 39.6 | 71.5 | 78% | $1.50 (intro) | - |
| **Claude Sonnet 5** (max) | 38.2 | 71.5 | 81% | $4.00 | 83 |
| **GPT-6 Luna** (max) - new Sept 22 | 37.3 | - | - | $0.20 | 136 |
| **Gemini 3.1 Pro** (preview) | 29.7 | 68.8 | 74% | $4.50 | 140 |
| **Gemini 3.5 Flash-Lite** | 22.2 | 49.3 | 54% | $0.85 | 350 |
| **Claude Haiku 4.5** (reasoning) | 16.9 | 43.9 | 44% | $2.00 | 159 |

**Effort moves both axes.** Opus 5.5 spans 42.3 (low) → 51.2 (medium, its default) → 57.6 (max); GPT-6 Sol spans 33.9 (low) → 47.5 (max). Compare models *at the effort you'll actually run*, not at their max. Non-covered labs sit in the same bands (Grok 4.7 ≈ 46, Kimi K3 ≈ 44).

## What each is good at

- **Claude Opus 5.5** - the **new default flagship and AA #1** (57.6 at max; 51.2 at its `medium` default, already ≈ Opus 5 at max). Anthropic reports Fable-5.1-level work at ~40% lower cost than Opus 5, stronger long-running coding, knowledge work with fewer invented figures, sharper chart/screenshot reading, and the lowest prompt-injection rate it has measured (tied with Fable 5.1). $4/$20, ZDR-eligible. Not yet rated on Arena or BullshitBench.
- **Claude Fable 5.1** - **#1 on Arena's Agent arena** and top AA coding/agentic sub-scores; still the pick for the longest, most ambiguous multi-hour work. $10/$50 (cache reads now 0.025×, which matters on long agent loops), **not ZDR-eligible**.
- **GPT-6 Astra** - OpenAI's flagship; **#2 on the Agent arena** and #1 on its "praise vs. complaint" signal; top GPQA (96%); best-in-class computer use and template adherence per OpenAI; fewer output tokens per task than prior GPTs. $10/$50.
- **GPT-6 Sol** - the **value pick in the frontier band**: 47.5 at $2/$10 (half GPT-5.6 Sol's price, ~same score) and ~107 tok/s. OpenAI claims it beats Claude Opus 5 at max on AutomationBench at 9% of the cost per task `[vendor claim]`.
- **GPT-6 Luna** - cheapest frontier-family model ($0.10/$0.50) scoring near Sonnet 5 at max. Default choice for cheap GPT volume work.
- **GPT-5.6 Terra** - still OpenAI's mid tier (no GPT-6 Terra); strong coding (76.7) at $2/$12.
- **Claude Opus 5** - previous flagship ($5/$25); still #3-4 on the Agent arena. Prefer Opus 5.5 (cheaper, stronger).
- **Claude Sonnet 5** - balanced Claude at **$2/$10 (made permanent Aug 10)**; strong false-premise pushback (see below).
- **Gemini 3.8 Flash** - the **fastest capable model** (315 tok/s) with coding (76.3) and agentic (88%) near the frontier at $1.50 blended (intro; doubles Jan 1 2027); uses more tokens by design. #13 on the Agent arena.
- **Gemini 3.7 Flash** - same price, more compute-efficient than 3.8.
- **Gemini 3.5 Flash-Lite** - cheapest Gemini ($0.85) and fastest (350 tok/s) for classification/routing/extraction; low intelligence.
- **Gemini 3.1 Pro** (preview) - still top **instruction-following** (IFBench 77%, highest among models with a published IFBench score - AA hasn't published it for most Sept releases) and science (GPQA 94%), but no longer competitive on general intelligence; Gemini 3.5 Pro still unreleased.
- **Claude Haiku 4.5** - cheapest Claude for bounded high-volume work; far below the new cheap frontier tiers (GPT-6 Luna, Gemini Flash) on AA. Haiku 5.5 is announced.

## Arena (formerly LMArena) - pick the arena that matches your task

Arena runs a **separate human-vote leaderboard per task** (Agent, Text/chat, WebDev/Code, Vision, Search, Document, image/video). Use the task-matched one - the general Text/chat arena scatters agentic models because chat preference ≠ agentic capability. **Agent arena, Sept 15 2026** (1.85M sessions; predates Opus 5.5 and GPT-6 Sol/Luna): **#1 Fable 5.1 (max), #2 GPT-6 Astra (max), #3-4 Opus 5 (high/max), #5 Fable 5, #6 Opus 4.8, #7 GPT-5.6 Sol, #8 Kimi K3, #9 Sonnet 5, #13 Gemini 3.8 Flash.** Per-signal leaders: confirmed success → Fable 5.1; praise vs. complaint → GPT-6 Astra; steerability → Opus 4.8; bash recovery → Opus 5.

**⚠️ On Opus 4.8, thinking is load-bearing for tool use** (July Agent-arena finding): with adaptive thinking ON it had ~0.2% tool hallucination, with thinking OFF (its API default) ~19%. Set `thinking:{type:"adaptive"}` for any tool-using agent on Opus 4.8. Every newer Claude model has thinking on by default or always on.

**Bottom line:** AA (objective evals) and the task-matched arena agree on the top band - Fable 5.1, GPT-6 Astra, Opus 5.x. Weight **AA for test-graded capability/cost**, **Arena for which output humans prefer**.

## Beyond intelligence - false-premise detection (BullshitBench)

A capability AA/Arena miss: **does the model call out a nonsensical or false premise instead of building on it?** On [BullshitBench](https://petergpt.github.io/bullshit-benchmark/) (v2: 100 nonsense prompts, 13 techniques, 5 domains, models run with no system prompt; clear-pushback rate over **all attempts** from `leaderboard.csv`, repo pulled 2026-09-23 - the dashboard's headline instead **excludes refusals** from the denominator, so heavy refusers such as Fable 5.x read ~10 points higher there): **Claude Opus 4.8 is still #1 at ~95%**; the Claude 5 generation is lower - **Sonnet 5 ~80%, Fable 5.1 64-77%, Opus 5 70-73%**; **GPT-6 Astra jumped to 64-69%** (GPT-5.6 Sol ~47%, Terra ~47-54%, Luna ~37-41%); **Gemini 3.7 Flash ~31-35%**. The durable lessons hold: **raising effort doesn't help and often hurts** (Fable 5.1: 77% at `low` vs 64% at `max`), and **refusal ≠ pushback** (Fable 5.x declines 11-36% of prompts instead of naming the flaw). Not yet benchmarked: Opus 5.5, GPT-6 Sol/Luna, Gemini 3.8 Flash. If your app must not act on broken user premises, weight this - and fix it with explicit prompting + model choice, not the effort knob.

## Picking a model - decision rules

- **Highest ceiling** → **Claude Opus 5.5** (AA #1, $4/$20, ZDR) as the default top pick; **Fable 5.1** for the longest, most ambiguous multi-hour work (Agent-arena #1, but 2.5× the price and no ZDR); **GPT-6 Astra** when you want OpenAI's stack, computer use, or template-faithful documents.
- **Default agentic coding** → **Opus 5.5** at `medium` (its default already matches Opus 5 at max), or **GPT-6 Sol** at high/max for the best capability-per-dollar.
- **Everyday business / support / internal tools** → **GPT-6 Sol**, **Sonnet 5**, or **GPT-5.6 Terra**.
- **Fast multimodal / agentic work at scale** → **Gemini 3.8 Flash** (or 3.7 Flash when token efficiency matters); budget for the Jan 2027 price step-up.
- **High-volume classification / routing / extraction** → **GPT-6 Luna** or **Gemini 3.5 Flash-Lite**; **Haiku 4.5** only if you must stay on Claude.
- **Strict instruction-following / adherence** → Gemini 3.1 Pro still leads IFBench, but weigh its preview status and low general score; otherwise Claude 4.7+ (literal following) or GPT-6.
- **Must not build on false premises** → Anthropic models lead (Opus 4.8 > Sonnet 5 > Opus 5 / Fable 5.1); GPT-6 Astra is now competitive; Gemini Flash lags.
- **Data retention constraints** → Fable 5.x requires 30-day retention; Opus 5.5 and GPT-6 Astra are ZDR-eligible; Gemini's Interactions API stores 55 days by default (set `store=false`).
- **Before combining models, sweep effort on one.** Anthropic's measurements: a frontier model at *low* effort often beats a cheaper model at its default on cost per solved task, and in every measured case where the work fit one context window and had no cost tail, the lead model alone at lower effort was cheaper than an orchestrator. Two multi-model shapes earn their keep: an **advisor** (cheap executor consults a frontier model on hard decisions - only pays if the executor actually consults, which low effort can suppress) and an **orchestrator** (frontier lead, cheaper workers - pays as insurance against a routine-task cost tail, or when input exceeds one context window).
- **Routing inside an agent loop** → worth it only if the price gap pays for the router. LangChain + NVIDIA Switchyard (Aug 2026): on a 145-task agent suite, escalation routing between a 30B open model and Claude Opus 4.8 sent ~7% of calls to Opus (which still carried 68% of spend), cutting cost 74% for ~6 points of accuracy; the router's judge was 21% of routed spend because it gets no cache benefit. Break-even: **minimum offload share = judge cost ÷ (expensive-model cost − cheap-model cost)** per run - if your two models are close in price this exceeds 100% and routing can't pay (unless the cheap model is self-hosted). Budget for a range, since escalation rates vary run to run; skip routing on latency-critical or short single-turn workloads.
- **Multi-tier pipeline** (the usual pattern): cheap tier for extract-classify-route (Luna / Flash-Lite) → frontier tier for analysis and generation (Opus 5.5 / Sol / Astra / Fable 5.1). See SKILL.md Section D.

## Cost-per-task ≠ per-token price

AA also measures what it actually costs to run its Intelligence Index - blended price × tokens *really used*, including cache reads/writes and reasoning. Snapshot 2026-09-23, **at each model's headline (max) effort** (not published per effort level on the page); "time/task" is wall-clock per eval task; "halluc." is AA-Omniscience's hallucination rate (how often the model answers wrong instead of abstaining on knowledge questions it doesn't know - lower is better):

| Model | Intel | Cost per task | Time/task | Halluc. |
|---|:---:|:---:|:---:|:---:|
| Claude Opus 5.5 | 57.6 | $5.98 | 525 s | 59% |
| Claude Fable 5.1 | 53.4 | $7.63 | 724 s | 73% |
| GPT-6 Astra | 52.7 | $3.26 | 525 s | 51% |
| GPT-6 Sol | 47.5 | **$1.06** | 269 s | 60% |
| Gemini 3.8 Flash | 40.9 | $1.24 | 240 s | 55% |
| GPT-6 Luna | 37.3 | **$0.07** | 353 s | 77% |
| Gemini 3.5 Flash-Lite | 22.2 | $0.12 | 48 s | 34% |

What it shows: **GPT-6 Astra costs less than half of Fable 5.1 per task at the same per-token price** (token efficiency), **Gemini 3.8 Flash costs *more* per task than GPT-6 Sol despite a per-token price ~8× lower** (its deliberate token appetite), and GPT-6 Luna is in a class of its own for cheap volume. Max-effort cost overstates what you'll pay at defaults (e.g. Opus 5.5 at `medium` already scores 51.2). Hallucination rate is a separate axis from intelligence - Flash-Lite's low rate comes from abstaining more, not knowing more. Source: the per-model records embedded in artificialanalysis.ai/models (`intelligenceIndexCostPerTask`, `intelligenceIndexTimePerTask`, `omniscienceHallucinationRate`); the v2 API returns intelligence and per-token prices but not cost per task.

Compare **cost per task at your effort setting**, not headline $/1M. Token efficiency now varies a lot: Opus 5.5 finishes tasks in fewer tokens than Opus 5, GPT-6 Astra uses substantially fewer output tokens than prior GPTs despite a higher per-token price, while Gemini 3.8 Flash deliberately spends *more* tokens (self-verification) - its low per-token price overstates its advantage on long agentic tasks. Cache-read pricing is now a first-order cost on agent loops: 0.025× input on Fable 5.1, 0.05× on Opus 5.5, 0.1× on GPT-6 and most others. And watch scheduled price changes (Gemini Flash doubles Jan 1 2027).

## Methodology notes

AA's Intelligence Index aggregates many evals (τ-Banking, Terminal-Bench, SciCode, HLE, GPQA, AA-LCR, and others); it was re-based between July and September 2026, and sub-benchmarks for the Sept 22 releases were still pending at capture. Arena's Agent arena scores "net improvement" from human votes on real agent sessions. BullshitBench uses a 0/1/2 rubric (accepted nonsense / buried challenge / clear pushback) from a 3-judge panel over 100 prompts × 5 domains. All three are one evaluator's methodology - directional. A model's rank on a public benchmark rarely predicts its rank on *your* task (SKILL.md Section H: build your own evals).
