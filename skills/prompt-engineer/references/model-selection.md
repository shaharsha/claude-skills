# Model Selection & Cost (cross-provider)

> **Scope - read this when *choosing* a model, not when *prompting* one.** Which tier for a task, at what budget, good at what. For *how to write the prompt* once you've picked, use `claude.md` / `gpt.md` / `gemini.md`. Keep this file **out of the prompt-authoring context** - benchmark tables are low-signal noise while writing a prompt (the "context rot" caution in SKILL.md Section A applies to the skill itself).
>
> **Staleness - the numbers are a dated snapshot, the *relationships* are the durable part.** Sources: Artificial Analysis (**2026-09-29**, every model × effort variant), Arena (formerly LMArena) Agent arena (**2026-09-15**), BullshitBench (repo pulled **2026-09-23**). **AA re-based its index between July and September** - scores dropped ~10 points across the board (Opus 5 at max: 60.7 in July, 50.8 now), so **never compare against the July numbers**. Releases land weekly; trust the **bands, gaps, and shape of the curves**, and re-pull before relying on a figure (see *Refreshing the AA data* at the end).

## Intelligence, cost, and speed - per model and effort (AA, 2026-09-29)

Every effort level AA tests for the current models. **Intel** = AA Intelligence Index. **Cost / task** = what AA actually paid per Intelligence Index task (list prices × tokens really used, incl. reasoning and cache reads/writes) - the number to compare, not $/1M. **Time / task** = wall-clock per task. **tok/s** = median output speed. **Halluc.** = AA-Omniscience hallucination rate (answers wrong instead of abstaining on knowledge it lacks; lower is better - Haiku and Flash-Lite score low by abstaining, not by knowing more). "-" = not published. Superseded models (GPT-6 Sol, Opus 5, Sonnet 5, GPT-5.6 Luna) are omitted; GPT-6.1 Sol beats GPT-6 Sol at every effort for similar cost.

| Model | Effort | Intel | Cost / task | Time / task | tok/s | Halluc. |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Claude Opus 5.5** | max | 57.6 | $5.98 | 807 s | 96 | 59% |
|  | xhigh | 56.0 | $3.46 | 503 s | 81 | 66% |
|  | high | 53.6 | $1.82 | 294 s | 74 | 68% |
|  | *medium (default)* | 51.2 | $1.34 | 216 s | 74 | 68% |
|  | low | 42.3 | $0.55 | 86 s | 75 | 68% |
| **Claude Sonnet 5.5** | max | 56.0 | $7.60 | 868 s | 145 | 47% |
|  | xhigh | 51.9 | $2.74 | 443 s | 110 | 63% |
|  | *high (default)* | 46.7 | $1.08 | 228 s | 106 | 65% |
|  | medium | 40.7 | $0.59 | 135 s | 88 | 51% |
|  | low | 35.8 | $0.41 | 99 s | 91 | 50% |
| **Claude Fable 5.1** | max | 53.4 | $7.63 | 723 s | 69 | 73% |
|  | xhigh | 53.2 | $5.98 | 662 s | 60 | 71% |
|  | *high (default)* | 51.2 | $3.91 | 442 s | 51 | 69% |
|  | medium | 48.9 | $2.98 | 332 s | 50 | 69% |
|  | low | 46.8 | $2.37 | 272 s | 51 | 66% |
| **GPT-6 Astra** | max | 52.7 | $3.26 | 472 s | 59 | 51% |
|  | xhigh | 52.4 | $2.31 | 340 s | 54 | 48% |
|  | high | 50.9 | $1.73 | 238 s | 52 | 45% |
|  | medium | 49.6 | $1.54 | 207 s | 52 | 47% |
|  | low | 45.8 | $0.82 | 92 s | 50 | 47% |
| **GPT-6.1 Sol** | max | 51.8 | $0.72 | 569 s | 87 | 54% |
|  | xhigh | 51.0 | $0.39 | 271 s | 89 | 51% |
|  | high | 50.2 | $0.32 | 203 s | 78 | 49% |
|  | *medium (default)* | 47.8 | $0.21 | 127 s | 74 | 52% |
|  | low | 42.1 | $0.13 | 54 s | 81 | 52% |
| **GPT-6 Luna** | max | 37.3 | $0.068 | 335 s | 138 | 77% |
|  | xhigh | 33.9 | $0.042 | 203 s | 137 | 82% |
|  | high | 32.1 | $0.029 | 150 s | 140 | 84% |
|  | *medium (default)* | 29.5 | $0.018 | - | - | 85% |
|  | low | 20.9 | $0.005 | 17 s | 137 | 84% |
|  | none | 18.3 | $0.011 | 27 s | 136 | 79% |
| **GPT-5.6 Terra** | max | 42.1 | $1.40 | 398 s | 106 | 88% |
|  | xhigh | 38.0 | $0.63 | 242 s | 88 | 89% |
|  | high | 34.2 | $0.34 | 131 s | 90 | 90% |
|  | *medium (default)* | 30.1 | $0.18 | 68 s | 95 | 90% |
|  | low | 27.5 | $0.14 | 49 s | 90 | 90% |
|  | none | 20.8 | $0.14 | 37 s | 87 | 95% |
| **Gemini 3.8 Flash** | high | 40.9 | $1.24 | 291 s | 230 | 55% |
|  | *medium (default)* | 39.8 | $0.93 | - | - | 52% |
| **Gemini 3.7 Flash** | high | 39.1 | $0.93 | 198 s | - | 65% |
| **Gemini 3.1 Pro (preview)** | - | 29.7 | $0.67 | 158 s | 131 | 51% |
| **Gemini 3.5 Flash-Lite** | high | 22.2 | $0.12 | 56 s | 329 | 34% |
| **Claude Haiku 4.5** | - | 16.9 | $0.28 | 176 s | 105 | 27% |

### What the curves say

- **Cost frontier (most intelligence per dollar): GPT-6 Luna → GPT-6.1 Sol → Claude Opus 5.5.** Nothing else is on it. Luna covers ~21-37 for under $0.07/task; **6.1 Sol covers 42-52 for $0.13-0.72**; above ~52 only Opus 5.5 (`high` 53.6 at $1.82, `xhigh` 56.0 at $3.46, `max` 57.6 at $5.98).
- **GPT-6.1 Sol is the value leader in the middle band by a wide margin:** at `xhigh` it matches Opus 5.5 `medium` / Astra `high` / Fable 5.1 `high` (~51) for **$0.39 vs $1.34 / $1.73 / $3.91**.
- **Claude Sonnet 5.5 is cheap per token, not per task, at high effort.** It gets fast and capable but token-hungry as effort rises: `max` reaches 56.0 but costs **$7.60** - more than Opus 5.5 `xhigh` for the same score ($3.46) - and `high` (46.7, $1.08) costs ~5× GPT-6.1 Sol `medium` (47.8, $0.21). Its case is speed (106-145 tok/s), Claude-specific behavior, and ZDR, at `low`/`medium`/`high`; if you need Sonnet 5.5 at `xhigh`+, price Opus 5.5 at `high`/`xhigh` first.
- **Effort curves flatten at the top, differently per model.** Fable 5.1 gains only 6.6 points from `low` to `max`, so its `low` (46.8, $2.37) is the value setting; Astra gains 2 points from `high` to `max` for nearly 2× the cost; Opus 5.5 keeps climbing to `max`.
- **Time frontier (fastest wall-clock per level):** 6.1 Sol `low`/`medium`/`high` (54-203 s) for ~42-50, then Opus 5.5 `medium`/`high` (216-294 s) for 51-54. Fable 5.1 and Sonnet 5.5 `max` are the slowest (720-870 s per task).
- **Gemini 3.8 Flash is fast but not cheap per task** (40.9 at $1.24 - GPT-6.1 Sol `low` scores 42.1 for $0.13), because it spends tokens on self-verification; its speed (230 tok/s) is its selling point.
- **Hallucination varies by effort and model, not just intelligence.** GPT-6 Astra (45-51%) and Sonnet 5.5 at `max` (47%) are the most calibrated frontier options; GPT-5.6 Terra (~90%) and Luna (77-85%) guess the most - pair them with retrieval and an explicit "say you don't know" instruction.

AA sub-benchmarks where published: Fable 5.1 max - coding index 81.6, Terminal-Bench 2.1 91%, GPQA 94%; GPT-6 Astra max - coding 76.9, TB 2.1 88%, GPQA 96%; Gemini 3.8 Flash high - coding 76.3, TB 2.1 88%, GPQA 95%; Gemini 3.1 Pro - IFBench 77% (highest published). Other labs' models sit in the same bands (Grok 4.7 ≈ 46, Kimi K3 ≈ 44).

## What each is good at

- **Claude Opus 5.5** - the **new default flagship and AA #1** (57.6 at max; 51.2 at its `medium` default, already ≈ Opus 5 at max). Anthropic reports Fable-5.1-level work at ~40% lower cost than Opus 5, stronger long-running coding, knowledge work with fewer invented figures, sharper chart/screenshot reading, and the lowest prompt-injection rate it has measured (tied with Fable 5.1). $4/$20, ZDR-eligible. Not yet rated on Arena or BullshitBench.
- **Claude Fable 5.1** - **#1 on Arena's Agent arena** and top AA coding/agentic sub-scores; still the pick for the longest, most ambiguous multi-hour work. $10/$50 (cache reads now 0.025×, which matters on long agent loops), **not ZDR-eligible**.
- **GPT-6 Astra** - OpenAI's flagship; **#2 on the Agent arena** and #1 on its "praise vs. complaint" signal; top GPQA (96%); best-in-class computer use and template adherence per OpenAI; fewer output tokens per task than prior GPTs. $10/$50.
- **Claude Sonnet 5.5** - the **fastest Claude** (106-145 tok/s) at $2/$10 per token, scoring 56.0 at `max` (tied with Opus 5.5 `xhigh`). But it's **token-hungry at high effort**, so per *task* it isn't cheap there: `max` costs more than Opus 5.5 `xhigh` for the same score, and at `high` it costs ~5× GPT-6.1 Sol `medium` for a similar score. Best at `low`-`high` for speed-sensitive Claude workloads; Anthropic reports it within 2 points of Opus 5.5 on GDPval-AA and above it on Terminal-Bench 4.0, while Opus 5.5 stays stronger on open-ended work needing sustained judgment. ZDR-eligible.
- **GPT-6.1 Sol** - OpenAI's new balanced default and **the value leader of the 42-52 band on AA** (on the cost frontier at every effort; `xhigh` ≈ Opus 5.5 `medium` for under a third of the cost per task). "Near-Astra" at $2/$10 (cached input $0.10); OpenAI reports Astra-level DeepSWE and near-Astra OSWorld at ~1/7 the cost per task. No `none` effort.
- **GPT-6 Sol** - the previous Sol, beaten by 6.1 Sol at every effort; keep it only if you need `none` effort.
- **GPT-6 Luna** - cheapest frontier-family model ($0.10/$0.50) scoring near Sonnet 5 at max. Default choice for cheap GPT volume work.
- **GPT-5.6 Terra** - OpenAI hasn't shipped a GPT-6 Terra, but GPT-6.1 Sol now beats Terra at every effort for similar or lower cost per task, with far lower hallucination - prefer 6.1 Sol.
- **Claude Opus 5** - previous flagship ($5/$25); still #3-4 on the Agent arena. Prefer Opus 5.5 (cheaper, stronger).
- **Claude Sonnet 5** - previous balanced Claude ($2/$10), superseded by Sonnet 5.5; strong false-premise pushback (see below) and still the cyber fallback for Sonnet 5.5.
- **Gemini 3.8 Flash** - the **fastest capable model** (highest tok/s in the 40+ band) with coding (76.3) and agentic (88%) near the frontier at $1.50 blended per token (intro; doubles Jan 1 2027) - but it uses more tokens by design, so per *task* it costs more than GPT-6.1 Sol `low` for a lower score. Pick it for speed and multimodality, not cost. #13 on the Agent arena.
- **Gemini 3.7 Flash** - same price, more compute-efficient than 3.8.
- **Gemini 3.5 Flash-Lite** - cheapest Gemini ($0.85) and fastest in the table for classification/routing/extraction; low intelligence.
- **Gemini 3.1 Pro** (preview) - still top **instruction-following** (IFBench 77%, highest among models with a published IFBench score - AA hasn't published it for most Sept releases) and science (GPQA 94%), but no longer competitive on general intelligence; Gemini 3.5 Pro still unreleased.
- **Claude Haiku 4.5** - cheapest Claude for bounded high-volume work; far below the new cheap frontier tiers (GPT-6 Luna, Gemini Flash) on AA. Haiku 5.5 is announced.

## Arena (formerly LMArena) - pick the arena that matches your task

Arena runs a **separate human-vote leaderboard per task** (Agent, Text/chat, WebDev/Code, Vision, Search, Document, image/video). Use the task-matched one - the general Text/chat arena scatters agentic models because chat preference ≠ agentic capability. **Agent arena, Sept 15 2026** (1.85M sessions; predates Opus 5.5 and GPT-6 Sol/Luna): **#1 Fable 5.1 (max), #2 GPT-6 Astra (max), #3-4 Opus 5 (high/max), #5 Fable 5, #6 Opus 4.8, #7 GPT-5.6 Sol, #8 Kimi K3, #9 Sonnet 5, #13 Gemini 3.8 Flash.** Per-signal leaders: confirmed success → Fable 5.1; praise vs. complaint → GPT-6 Astra; steerability → Opus 4.8; bash recovery → Opus 5.

**⚠️ On Opus 4.8, thinking is load-bearing for tool use** (July Agent-arena finding): with adaptive thinking ON it had ~0.2% tool hallucination, with thinking OFF (its API default) ~19%. Set `thinking:{type:"adaptive"}` for any tool-using agent on Opus 4.8. Every newer Claude model has thinking on by default or always on.

**Bottom line:** AA (objective evals) and the task-matched arena agree on the top band - Fable 5.1, GPT-6 Astra, Opus 5.x. Weight **AA for test-graded capability/cost**, **Arena for which output humans prefer**.

## Beyond intelligence - false-premise detection (BullshitBench)

A capability AA/Arena miss: **does the model call out a nonsensical or false premise instead of building on it?** On [BullshitBench](https://petergpt.github.io/bullshit-benchmark/) (v2: 100 nonsense prompts, 13 techniques, 5 domains, models run with no system prompt; clear-pushback rate over **all attempts** from `leaderboard.csv`, repo pulled 2026-09-23 - the dashboard's headline instead **excludes refusals** from the denominator, so heavy refusers such as Fable 5.x read ~10 points higher there): **Claude Opus 4.8 is still #1 at ~95%**; the Claude 5 generation is lower - **Sonnet 5 ~80%, Fable 5.1 64-77%, Opus 5 70-73%**; **GPT-6 Astra jumped to 64-69%** (GPT-5.6 Sol ~47%, Terra ~47-54%, Luna ~37-41%); **Gemini 3.7 Flash ~31-35%**. The durable lessons hold: **raising effort doesn't help and often hurts** (Fable 5.1: 77% at `low` vs 64% at `max`), and **refusal ≠ pushback** (Fable 5.x declines 11-36% of prompts instead of naming the flaw). Not yet benchmarked: Opus 5.5, Sonnet 5.5, GPT-6 / 6.1 Sol, GPT-6 Luna, Gemini 3.8 Flash. If your app must not act on broken user premises, weight this - and fix it with explicit prompting + model choice, not the effort knob.

## Picking a model - decision rules

- **Highest ceiling** → **Claude Opus 5.5** (AA #1, $4/$20, ZDR) as the default top pick; **Fable 5.1** for the longest, most ambiguous multi-hour work (Agent-arena #1, but 2.5× the price and no ZDR); **GPT-6 Astra** when you want OpenAI's stack, computer use, or template-faithful documents.
- **Default agentic coding** → **Opus 5.5** at `medium` (its default already matches Opus 5 at max); for the best capability-per-dollar, **GPT-6.1 Sol** (`high`/`xhigh`); on Claude, Sonnet 5.5 at `medium` for well-specified tasks (fast) - above that, Opus 5.5 is usually cheaper per task.
- **Everyday business / support / internal tools** → **GPT-6.1 Sol** (`low`/`medium`) or **Sonnet 5.5** (`low`/`medium`) - GPT-5.6 Terra is now dominated by 6.1 Sol on AA.
- **Fast multimodal / agentic work at scale** → **Gemini 3.8 Flash** (or 3.7 Flash when token efficiency matters) when throughput is the constraint; if cost per task is, GPT-6.1 Sol `low` beats both. Budget for the Jan 2027 price step-up.
- **High-volume classification / routing / extraction** → **GPT-6 Luna** or **Gemini 3.5 Flash-Lite**; **Haiku 4.5** only if you must stay on Claude.
- **Strict instruction-following / adherence** → Gemini 3.1 Pro still leads IFBench, but weigh its preview status and low general score; otherwise Claude 4.7+ (literal following) or GPT-6.
- **Must not build on false premises** → Anthropic models lead (Opus 4.8 > Sonnet 5 > Opus 5 / Fable 5.1); GPT-6 Astra is now competitive; Gemini Flash lags.
- **Data retention constraints** → Fable 5.x requires 30-day retention; Opus 5.5 and GPT-6 Astra are ZDR-eligible; Gemini's Interactions API stores 55 days by default (set `store=false`).
- **Before combining models, sweep effort on one.** Anthropic's measurements: a frontier model at *low* effort often beats a cheaper model at its default on cost per solved task, and in every measured case where the work fit one context window and had no cost tail, the lead model alone at lower effort was cheaper than an orchestrator. Two multi-model shapes earn their keep: an **advisor** (cheap executor consults a frontier model on hard decisions - only pays if the executor actually consults, which low effort can suppress) and an **orchestrator** (frontier lead, cheaper workers - pays as insurance against a routine-task cost tail, or when input exceeds one context window).
- **Routing inside an agent loop** → worth it only if the price gap pays for the router. LangChain + NVIDIA Switchyard (Aug 2026): on a 145-task agent suite, escalation routing between a 30B open model and Claude Opus 4.8 sent ~7% of calls to Opus (which still carried 68% of spend), cutting cost 74% for ~6 points of accuracy; the router's judge was 21% of routed spend because it gets no cache benefit. Break-even: **minimum offload share = judge cost ÷ (expensive-model cost − cheap-model cost)** per run - if your two models are close in price this exceeds 100% and routing can't pay (unless the cheap model is self-hosted). Budget for a range, since escalation rates vary run to run; skip routing on latency-critical or short single-turn workloads.
- **Multi-tier pipeline** (the usual pattern): cheap tier for extract-classify-route (Luna / Flash-Lite) → frontier tier for analysis and generation (Opus 5.5 / Sol / Astra / Fable 5.1). See SKILL.md Section D.

## Cost-per-task ≠ per-token price

Compare **cost per task at your effort setting**, not headline $/1M. Token efficiency now varies a lot: Opus 5.5 finishes tasks in fewer tokens than Opus 5, GPT-6 Astra uses substantially fewer output tokens than prior GPTs despite a higher per-token price, while Gemini 3.8 Flash deliberately spends *more* tokens (self-verification) - its low per-token price overstates its advantage on long agentic tasks. Cache-read pricing is now a first-order cost on agent loops: 0.025× input on Fable 5.1, 0.05× on Opus 5.5, 0.1× on GPT-6 and most others. And watch scheduled price changes (Gemini Flash doubles Jan 1 2027).

## Methodology notes

AA's Intelligence Index aggregates many evals (τ-Banking, Terminal-Bench, SciCode, HLE, GPQA, AA-LCR, and others); it was re-based between July and September 2026, and sub-benchmarks for the Sept 22 releases were still pending at capture. Arena's Agent arena scores "net improvement" from human votes on real agent sessions. BullshitBench uses a 0/1/2 rubric (accepted nonsense / buried challenge / clear pushback) from a 3-judge panel over 100 prompts × 5 domains. All three are one evaluator's methodology - directional. A model's rank on a public benchmark rarely predicts its rank on *your* task (SKILL.md Section H: build your own evals).

## Refreshing the AA data

- **Full per-effort data (cost per task, time per task, hallucination, intelligence):** embedded in every AA **model page** (e.g. `artificialanalysis.ai/models/claude-opus-5-5`) as Next.js flight data - decode the `self.__next_f.push([1,"…"])` strings and JSON-decode each `{"id":…,"slug":…}` object; fields `name`, `effort.label`, `intelligenceIndex`, `intelligenceIndexCostPerTask.cost.total`, `intelligenceIndexTimePerTask`, `omniscienceHallucinationRate`. One page carries all ~170 variants AA prices, not just that model's.
- **Speed and the complete variant list:** `GET https://artificialanalysis.ai/api/v2/data/llms/models` (header `x-api-key`) - intelligence, per-token prices, `median_output_tokens_per_second`, TTFT, for every model and effort, but **no cost per task**.
- **Cost per task via API:** `GET https://artificialanalysis.ai/api/v2/language/models/free` (same key) adds `artificial_analysis_intelligence_index_cost.cost_per_task.total_cost` and a `performance` block, but it's **capped at 200 variants** and omitted 21 of the 34 current effort variants on 2026-09-29 - use it to cross-check (its values matched the page data exactly), not as the source.

