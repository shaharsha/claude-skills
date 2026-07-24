# Model Selection & Cost (cross-provider)

> **Scope — read this when *choosing* a model, not when *prompting* one.** Which tier for a task, at what budget, good at what. For *how to write the prompt* once you've picked, use `claude.md` / `gpt.md` / `gemini.md`. Keep this file **out of the prompt-authoring context** — benchmark tables are low-signal noise while writing a prompt (the "context rot" caution in SKILL.md Section A applies to the skill itself).
>
> **Staleness — the numbers are a dated snapshot, the *relationships* are the durable part.** Source: Artificial Analysis **Intelligence Index v4.1** + LMArena, captured **2026-07-24**. Frontier rankings churn every few weeks (Kimi K3, Grok 4.5, and others sit in the same band). Trust the **bands, gaps, and "good at what" shape**; re-pull exact figures before you rely on one. AA has an API: `GET https://artificialanalysis.ai/api/v2/data/llms/models` with header `x-api-key` (fields: `evaluations.*`, `pricing.*`, `median_output_tokens_per_second`). LMArena leaderboard: lmarena.ai/leaderboard.

## Snapshot — AA Intelligence Index v4.1 (2026-07-24)

Sorted by aggregate intelligence. Coding = AA Coding Index; Agentic = TerminalBench 2.1 (%); `$/1M` = AA blended price (3:1 in:out); tok/s = median output speed. Effort matters — AA tests a fixed setting per model; raising/lowering `effort`/`thinking_level` moves intelligence *and* cost.

| Model | Intel | Coding | Agentic | $/1M blended | tok/s |
|-------|:-----:|:------:|:-------:|:------------:|:-----:|
| **Claude Fable 5** | 59.9 | 77 | 85% | $20.00 | 59 |
| **GPT-5.6 Sol** | 58.9 | 77 | 88% | $11.25 | 62 |
| **Claude Opus 4.8** | 55.7 | 74 | 85% | $10.00 | 61 |
| **GPT-5.6 Terra** | 55.0 | 77 | 88% | $5.63 | 122 |
| **Claude Sonnet 5** | 53.4 | 72 | 81% | $4.00 | 81 |
| **GPT-5.6 Luna** | 51.2 | 71 | 81% | $2.25 | 170 |
| **Gemini 3.6 Flash** | 50.1 | 69 | 78% | $3.00 | 255 |
| **Gemini 3.1 Pro** | 46.5 | 69 | 74% | $4.50 | 128 |
| **Gemini 3.5 Flash-Lite** | 36.5 | 49 | 54% | $0.85 | 357 |
| **Claude Haiku 4.5** | 29.6 | 44 | 44% | $2.00 | 135 |

For context, non-provider frontier models cluster in the same top band (Kimi K3 ≈ 57, Grok 4.5 ≈ 53) — six labs now field a model above 50. This file covers the three families the skill supports.

## What each is good at

- **GPT-5.6 Sol** — the objective **coding/agentic champion**: top Coding Index (77), TerminalBench (88%), tool-use (τ-banking), and science (GPQA 94%), at **~half Fable's blended cost**. Default pick when benchmark capability-per-dollar on hard coding/agents is the goal.
- **GPT-5.6 Terra** — the **value standout**: coding (77) ties Fable/Sol and agentic (88%) ties Sol, at **$5.63** (½ Sol, ¼ Fable). The strongest price/coding point in the frontier band.
- **GPT-5.6 Luna** — cheap *frontier-family* coding (71) at $2.25 / 170 tok/s. A budget frontier tier, not a nano.
- **Claude Fable 5** — **#1 aggregate intelligence (59.9)** and **#1 on human preference (LMArena)**; its edge compounds on the longest, most ambiguous, multi-hour work. But Sol nearly ties it on benchmarks at half the price, and Fable is the **slowest (59 tok/s) and priciest ($20)** — reserve for genuinely hard long-horizon work.
- **Claude Opus 4.8** — strong all-rounder (55.7 / coding 74), the **recommended default flagship**; cheaper than Sol and ranks far higher on human preference (LMArena top ~5).
- **Claude Sonnet 5** — best **balance** (53.4 / coding 72) at $4 — near-Opus coding for a third of Sol's cost.
- **Claude Haiku 4.5** — cheapest Claude; high-volume, latency-critical, bounded tasks (classification, routing, extraction).
- **Gemini 3.6 Flash** — the **fast multimodal/knowledge workhorse**: 255 tok/s, GPQA 93%, $3 blended, ~17% more token-efficient than 3.5 Flash. Best per-dollar for high-throughput agentic + multimodal.
- **Gemini 3.5 Flash-Lite** — **cheapest ($0.85) and fastest (357 tok/s)**; classification/routing/extraction at volume. Low intelligence (36.5) — don't reach for it on hard reasoning; raise its `thinking_level` for a cheap boost on ambiguous inputs.
- **Gemini 3.1 Pro** — best **instruction-following** (IFBench, tops this set) and tied-top **science** (GPQA 94%); the Gemini reasoning tier when you need adherence over raw agentic coding.

## LMArena — pick the arena that matches your task (it has ~13)

LMArena runs a **separate human-vote leaderboard per task**: Agent, Text (chat), WebDev/Code, Vision, Search, Document, and image/video arenas. Citing the wrong one misleads — the general **Text (chat)** arena scatters these agentic models (Fable 5 #1, but Sol #11, Opus 4.8-Thinking #13, Sonnet 5 #38) because open-chat preference ≠ agentic capability. Once you use the *task-matched* arena, **LMArena agrees with AA** (the "AA vs arena" gap in older notes was an artifact of reading the chat arena). Snapshot Jul 21 2026:

- **Agent Arena** (real-world tool orchestration — the right lens for agent/coding products; ~1.2M sessions): **#1 Fable 5, #2 GPT-5.6 Sol, #3 Opus 4.8 (Thinking), #4 Kimi K3, #5 Sonnet 5, #6 GPT-5.5.** Per-signal leaders — steerability & user-praise → **Fable 5**; bash-recovery → **GPT-5.5**; task-confirmation → **Kimi K3**.
- **⚠️ On Opus 4.8, thinking is load-bearing for tool use.** With adaptive thinking ON it ranks **#3 at 0.22% tool-hallucination**; the *same model with thinking OFF (the API default)* falls to **#15 at ~19% tool-hallucination**. For any tool-using agent on Opus 4.8, set `thinking:{type:"adaptive"}` — don't rely on the default. Fable 5 (always-on) and Sonnet 5 (on by default) don't have this trap.
- **WebDev / Code Arena** (front-end + agentic coding, Elo): **#1 Kimi K3, #2 Fable 5, #3 GPT-5.6 Sol, #5 Opus 4.8 (Thinking), #9 Sonnet 5, #12 Gemini 3.6 Flash, #36 Gemini 3.1 Pro.** Consistent with AA/Agent.
- **Text Arena** (general chat — a *different* question): Fable 5 #1 across nearly every category; **Gemini 3.6 Flash is a standout #2 on Math**; Sonnet 5 is #15 Coding / #11 Expert despite #38 overall. Use for user-facing prose/chat, not agent capability.
- **Vision Arena** (multimodal chat): Fable 5 #1; Gemini Pro/Flash cluster in the top ~8.

**Bottom line:** AA (objective evals) and the *task-matched* LMArena arena mostly agree — where they diverge, weight **AA for test-graded capability/cost**, **LMArena for which output humans prefer**. All of this churns; re-pull from lmarena.ai/leaderboard (per-arena) and the AA API.

## Picking a model — decision rules

- **Hardest long-horizon / highest ceiling** → **Fable 5** (its lead widens with task length; note ZDR-ineligible, always-on thinking). If objective coding-per-dollar matters more than its human-preference edge, **GPT-5.6 Sol** is ~equal on benchmarks at half the cost.
- **Default agentic coding** → **Sol** (benchmarks) or **Opus 4.8** (human preference + ecosystem). If cost matters, **Terra** nearly matches on coding at ½ Sol's price.
- **Everyday business / support / internal tools** → **Terra** or **Sonnet 5**.
- **Fast multimodal / knowledge work at scale** → **Gemini 3.6 Flash**.
- **High-volume classification / routing / extraction** → **Gemini 3.5 Flash-Lite** (cheapest + fastest) or **Luna**; **Haiku 4.5** for the cheapest Claude.
- **Strict instruction-following / adherence** → **Gemini 3.1 Pro**.
- **Multi-tier pipeline** (the usual pattern): cheap/fast tier for extract-classify-route (Flash-Lite / Haiku / Luna) → frontier tier for analysis/generation (Sol / Opus 4.8 / Fable 5). See SKILL.md Section D.

## Cost-per-task ≠ per-token price

AA also publishes **cost-per-Intelligence-Index-task** (blended price × tokens *actually used*). Because **GPT-5.6 is markedly token-efficient** (reaches frontier scores with fewer output tokens), its cost-per-task advantage over Claude/Fable is *larger* than the per-token gap suggests — and Fable's high price is compounded by longer, deeper reasoning. Flash-Lite and Luna win raw volume economics. When you compare real cost, compare cost-per-*task* at your effort setting, not headline $/1M.

## Methodology notes

AA **Intelligence Index v4.1** aggregates 9 evals: GDPval-AA v2, τ³-Banking, Terminal-Bench v2.1, SciCode, Humanity's Last Exam, GPQA Diamond, CritPt, AA-Omniscience, AA-LCR. Sub-indices used above: Coding Index, TerminalBench 2.1 (agentic), τ-banking (tool-use), GPQA (science), IFBench (instruction-following). One evaluator's methodology; treat as directional and cross-check against your own evals — a model's rank on a public benchmark rarely predicts its rank on *your* task (see SKILL.md Section H on building your own evals).
