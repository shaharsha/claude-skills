# Gemini 4 Neon, and a full benchmark refresh (2026-11-26)

Record for the update of the `prompt-engineer` skill after a check of Anthropic's, OpenAI's and Google's model lists on 2026-11-26. One chat model was missing from the skill: Google's Gemini 4 Neon (`gemini-4-neon`, generally available since 2026-11-18). Adding it meant re-pulling every benchmark the skill quotes, and three of them had changed in ways that go beyond Neon.

## What was checked

| Vendor | Pages read | Result |
|---|---|---|
| Anthropic | Models overview, API release notes (Nov 10 to Nov 23), model deprecations | No new model. Lineup: Fable 5.2, Opus 5.5, Sonnet 5.5, Haiku 5.5 |
| OpenAI | Models index, API changelog (Nov 17 to Nov 24), pricing | No new text model. New since Nov 18: healthcare configurations of existing models (Nov 24), GPT-Live-1.1 (voice, Nov 19) |
| Google | Models index, API changelog (Nov 17 to Nov 19) | **Gemini 4 Neon (Nov 18)**. Also Genie 4 (interactive world generation, Nov 19), tool retrieval (preview, Nov 19), slicing of Office, video and audio inputs (Nov 18) |
| Web search | Six queries for unreleased or unlisted models | Nothing released beyond the above. "Claude Opus 5.6" appears only as unconfirmed rumor; no GPT-6.2 Terra, GPT-6.2 Luna or GPT-6.3 exists |

Found and **not** added in this round (they are not new models, or belong to another vendor's file): Anthropic's Enterprise Frontier Safeguards beta (Nov 23; zero data retention for eligible organizations on its most capable models, which `claude.md` still describes as not yet available), the Claude Opus 4.5 deprecation (retires Jan 22 2027), OpenAI's healthcare configurations and GPT-Live-1.1, and Genie 4.

## Sources

Fetched on 2026-11-26 between 21:00 and 22:30 Israel time. Google's Gemini API pages return markdown when `.md` is appended to the URL.

| Id | Source |
|---|---|
| G1 | Gemini API changelog: https://aistudio.google.com/docs/changelog (entries of Nov 17, 18 and 19) |
| G2 | *What's new in Gemini 4 Neon*: https://aistudio.google.com/docs/whats-new-gemini-4-neon |
| G3 | Model page: https://aistudio.google.com/docs/models/gemini-4-neon, and the models index `.../docs/models` |
| G4 | *Choosing a model*: https://aistudio.google.com/docs/choosing-a-model; *Latest Gemini models*: `.../docs/latest-model` |
| G5 | *Thinking*, *Long decode*, *Caching*, *Deprecations*: `.../docs/thinking`, `/long-decode`, `/caching`, `/deprecations` |
| G6 | *Tool retrieval*: https://aistudio.google.com/docs/tool-retrieval |
| G7 | Google, *Introducing Gemini 4 Neon* (Nov 18, updated Nov 23): https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-neon/ |
| G8 | Google DeepMind model card: https://deepmind.google/models/model-cards/gemini-4-neon/ |
| V1 | Google Cloud, *Developer's guide to Gemini 4 Neon*: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-neon |
| V2 | Google Cloud model page: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-neon |
| A1 | Artificial Analysis API, `GET https://artificialanalysis.ai/api/v2/language/models/free`, pulled 21:28 (4 pages, 766 rows, `intelligence_index_version` 5) |
| A2 | 65 Artificial Analysis model pages, `https://artificialanalysis.ai/models/<slug>`, fetched 21:28-21:30 |
| A3 | Artificial Analysis, *Intelligence Benchmarking Methodology* (version history; cost reporting): https://artificialanalysis.ai/methodology/intelligence-benchmarking |
| B1 | BullshitBench, https://github.com/petergpt/bullshit-benchmark at `2b8bef8` (2026-11-26), `data/v2/latest/leaderboard.csv` |
| B2 | SemiAnalysis GDPx, https://gdpx.semianalysis.com/ (all 26 models selected; the overall board, the board that excludes safety-classifier domains, and the software-engineering domain) |
| B3 | Arena Agent leaderboard, https://arena.ai/leaderboard/agent (board dated Nov 22; read twice through a fetch tool, the two reads agree on all 15 rows shown) |

## Gemini 4 Neon: the facts used

- **Identity and limits (G1, G2, G3, G8).** `gemini-4-neon`, generally available Nov 18 2026 on the paid tier; "adapted from Gemini 4 Carbon" (G8); text, image, video, audio and PDF in, text out; one 1,048,576-token window for input, thinking and output; 65,536 output tokens per response, up to 1,048,576 with long decode; implicit caching only (4,096-token minimum); knowledge cutoff March 2026 (G8).
- **Thinking (G2, G5).** `low`, `medium`, `high` (default) and `xhigh`. G2: "Neon defaults to `high` and supports `xhigh`, like Hydrogen. Carbon and Argon default to `medium` and cap at `high`."
- **Price (G2).** $3.00 input, $15.00 output, $0.15 cached input per 1M tokens; no free tier; G4: "Neon has no promotional price."
- **Position (G2, G4).** G2: "It sits between Gemini 4 Hydrogen and Gemini 4 Carbon for high-frequency complex tasks." G4's comparison table lists Carbon, Neon, Hydrogen and 3.5 Flash-Lite and no longer lists Argon; its upgrade table sends `gemini-3.1-pro-preview` to "`gemini-4-neon` (or `gemini-4-carbon` for your hardest problems)". V1: "Gemini 4 Neon (gemini-4-neon) is the target upgrade for Gemini 3.1 Pro (gemini-3.1-pro-preview) and for general coding and enterprise reasoning workloads on Gemini 4 Argon (gemini-4-argon)." Argon has no shutdown date (G5, deprecations).
- **Long decode (G5).** Per-hop caps: 64K on streaming and non-streaming calls for `gemini-4-neon` and `gemini-4-hydrogen`, 32K per non-streaming hop for `gemini-4-carbon` and `gemini-4-argon`.
- **Google Cloud (V1, V2).** Global endpoint and the `us` and `eu` multi-regions; "available to verified enterprise customers in select regions"; `thinking_budget` and `MINIMAL` return HTTP 400; the same request rules as the other Gemini 4 guides (no prefilled model turns, thought-signature placement, an `update` function for pre-tool notes); V2 repeats that cache control with TTL arrives on Jan 12 2027 for "Gemini 4 Hydrogen and later models".
- **Behavior claims (G7).** Under-service down 43%-56% and overreach down 13%-35% against Carbon; shortcuts on 2.45% of tasks in Google's coding cheating evaluation; 0.0% attack success on Gray Swan's indirect-prompt-injection benchmark "with real-time safeguards at its highest thinking level"; SWE-sweep 12.8% in the mini-SWE harness and 39.0% in Antigravity.
- **Model card table (G8).** 19 rows against Claude Opus 5.5 and GPT-6.2 Sol. Neon is first on 16; Opus 5.5 leads Terminal-bench 4.1 (65.8% vs 65.2%) and FrontierCode 2.0 (47.3% vs 46.2%); GPT-6.2 Sol leads Chartography (75.1% vs 73.5%). The card compares Neon with neither Fable 5.2, GPT-6.2 Astra nor Carbon. Safety deltas are against Hydrogen (unjustified refusals -3.00 points).
- **No prompting guide.** Google published five-tip developer guides for Argon and Carbon. None was found for Neon on Nov 26, and the skill says so; its Neon section is built from G2, G4, G7, G8 and V1.

Also taken from G1 and G6 for the shared Gemini file: tool retrieval (preview since Nov 19; Interactions API `v1beta`; `{"type": "tool_search"}` plus `defer_loading: true`; the best-practice list), and slicing of documents, spreadsheets, video and audio (Nov 18; direct Office and OpenDocument inputs are older - the Nov 5 changelog entry already extends them).

## Benchmarks: what changed since Nov 18

**Artificial Analysis (A1, A2, A3).** All 60 existing rows were re-pulled and four Neon rows added (64 rows). Output tokens divided by time per task equalled the API speed on all 63 rows that have a time.

- **The index is now v5.0.2.** A3: "Replaced Terminal-Bench 4.0 with Terminal-Bench 4.1: the same 66 tasks, scored with updated verifiers", and FrontierCode was regraded. 28 of the 60 existing rows changed by 0.1 to 0.3 points.
- **Costs moved without price changes.** A3: "When reporting cache hit rates and cost, we combine these token counts with live measurements of the model's typical cache hit rate". Gemini 3.8 Flash fell 58-61% ($7.77 to $3.02 at `high`), Hydrogen `low` rose 26% ($0.29 to $0.37), and Argon is now costed at its $4 / $20 list price ($4.97 to $7.06 at `high`, $4.31 to $8.63 at `medium`). Carbon's API cost is unchanged; its model pages now show the list-price cost too, so the table switched from the intro-price figures it carried on Nov 18.
- **Speeds moved.** The GPT-6.2 rows read 15-28% slower per token than on Nov 18, the day after their launch, so their time per task rose 22-39%. Across all rows, speed moved between -28% and +27%, and 28 rows moved by more than 5%.
- **Neon's rows.** `xhigh` 61.5, $6.44, 1,637 s, 87 tok/s, 14% hallucination; `high` 59.8, $3.74, 884 s, 102 tok/s, 14%; `medium` 54.9, $1.90, 525 s, 95 tok/s, 16%; `low` 44.1, $0.88, 229 s, 95 tok/s, 19%. Third by best score, behind Fable 5.2 (64.8) and GPT-6.2 Astra (62.2). It is on neither the cost nor the time frontier, Neon `xhigh` beats Carbon `high` and Neon `high` beats Carbon `medium` on score, cost and time; Neon `high` is 0.3 points under Carbon `high`.
- **Frontier changes.** Fable 5.2 `xhigh` (62.2, $14.83) left the cost frontier because GPT-6.2 Astra `max` now scores 62.2 for $4.00. Fable 5.2 `high` (61.9, 881 s) joined the time frontier between GPT-6.2 Astra `xhigh` and `max`.

**Arena Agent leaderboard (B3).** The page now publishes an "Agent Arena Index" with a median cost and time per task; the "net improvement" percentage the skill quoted is gone, and so are the rank ranges. Board dated Nov 22: 3,175,883 sessions, 69 models. Neon (xHigh, preliminary) is third at 1,331; GPT-6.2 Astra (Max) is eighth at 1,275, two places below GPT-6 Astra (sixth, 1,284).

**GDPx (B2).** 26 models, up from 21. New: GPT-6.2 Astra (first, 19.3%), GPT-6.2 Sol (fourth, 11.5%), Neon (sixth, 10.1%), Qwen 4 Max and Kimi K3.1 Pro. Opus 5.5 reads 11.9% (12.0% on Nov 18). The page shows 11 models by default; the full list needs the model picker. On the software-engineering domain Neon scores 4.4% (rank 13).

**BullshitBench (B1).** Two Neon rows were added: 67% clear pushback at `low` and 84% at `xhigh`.

## What changed in the skill

| File | Change |
|---|---|
| `references/gemini.md` | Model list for four Gemini 4 models; Neon bullet; thinking table; per-hop caps; caching; pricing; a tool-retrieval bullet; Office inputs; the per-model sections moved out |
| `references/gemini-4.md` (new) | *Prompting Gemini 4 Argon*, *Carbon*, *Hydrogen* and the two Gemini 4 migration sections, moved from `gemini.md`; new *Prompting Gemini 4 Neon* and *Migration to Gemini 4 Neon* |
| `references/model-selection.md` | Table rebuilt (64 rows); frontiers, per-model entries, Arena, GDPx, BullshitBench, decision rules and methodology rewritten for the new data; the refresh recipe moved out |
| `references/model-selection-refresh.md` (new) | *Refreshing the AA data*, moved from `model-selection.md` and updated for this pull |
| `SKILL.md` | Eight in-place edits (routing to `gemini-4.md`, thinking and caching table cells); still 495 lines |
| `README.md`, `gpt.md`, `gpt-6.md`, `kimi.md`, `grok.md` | The file table, and figures quoted from Artificial Analysis; `kimi.md` also gets Kimi K3's BullshitBench figures as the CSV reads now (72% and 74%; the file said 58% and 44%) |

**Why `gemini.md` was split.** It was 64.8 KB, and the reading tool returns at most about 62 KB of these files per call. With Neon it would not have fit one read. The split follows the Claude files: the shared contract stays in `gemini.md`, per-model prompting and migration go to `gemini-4.md`, and Step 0b routes to it. `gemini.md` is now 53.1 KB and `gemini-4.md` 23.1 KB.

**Why the refresh recipe left `model-selection.md`.** The test runs below showed the revised file (53.6 KB) coming back partial: the reading tool counted 25,282 tokens against its cap of 25,000. This file is dense with numbers, about 2.1 characters per token where the prose files run about 2.6, so its limit is near 53 KB, not 62. *Refreshing the AA data* is a recipe for whoever updates the table, not for choosing a model, so it moved to `model-selection-refresh.md` with a pointer from `model-selection.md`, `SKILL.md` and the README. `model-selection.md` is now 50.4 KB, and a single read returned all four files whole (`model-selection.md`, `model-selection-refresh.md`, `gemini.md`, `gemini-4.md`).

## Data

Artificial Analysis, API pulled 2026-11-26 21:28 Israel time, pages 21:28-21:30.

| Model | Effort | AA slug | Intel | Cost / task | Time s (page) | v3 tok/s (API) | Output tokens / task | Halluc. | First answer token s |
|---|---|---|---|---|---|---|---|---|---|
| Claude Fable 5.2 | max | `claude-fable-5-2` | 64.8 | $26.539 | 2422 | 113.03 | 273776 | 59% | 232.7 |
| Claude Fable 5.2 | xhigh | `claude-fable-5-2-xhigh` | 62.2 | $14.829 | 1448 | 111.82 | 161944 | 60% | 70.7 |
| Claude Fable 5.2 | high (default) | `claude-fable-5-2-high` | 61.9 | $9.078 | 881 | 111.09 | 97841 | 58% | 26.8 |
| Claude Fable 5.2 | medium | `claude-fable-5-2-medium` | 56.3 | $3.803 | 393 | 109.83 | 43131 | 58% | 11.4 |
| Claude Fable 5.2 | low | `claude-fable-5-2-low` | 53.9 | $3.097 | 323 | 111.00 | 35860 | 56% | 8.5 |
| GPT-6.2 Astra | max | `gpt-6-2-astra` | 62.2 | $3.998 | 924 | 44.43 | 41029 | 59% | 165.7 |
| GPT-6.2 Astra | xhigh | `gpt-6-2-astra-xhigh` | 61.8 | $2.521 | 510 | 43.59 | 22238 | 58% | 53.1 |
| GPT-6.2 Astra | high | `gpt-6-2-astra-high` | 60.3 | $2.074 | 404 | 44.13 | 17828 | 58% | 25.2 |
| GPT-6.2 Astra | medium | `gpt-6-2-astra-medium` | 57.0 | $1.618 | 295 | 44.64 | 13165 | 54% | 3.4 |
| GPT-6.2 Astra | low | `gpt-6-2-astra-low` | 45.7 | $0.662 | 129 | 40.46 | 5216 | 56% | 2.9 |
| Gemini 4 Neon | xhigh | `gemini-4-neon` | 61.5 | $6.445 | 1637 | 86.52 | 141631 | 14% | 60.9 |
| Gemini 4 Neon | high (default) | `gemini-4-neon-high` | 59.8 | $3.743 | 884 | 102.02 | 90188 | 14% | 35.2 |
| Gemini 4 Neon | medium | `gemini-4-neon-medium` | 54.9 | $1.905 | 525 | 95.19 | 50000 | 16% | 26.3 |
| Gemini 4 Neon | low | `gemini-4-neon-low` | 44.1 | $0.882 | 229 | 94.84 | 21726 | 19% | 19.3 |
| Gemini 4 Carbon | high | `gemini-4-carbon` | 60.1 | $7.755 | 2374 | 51.72 | 122768 | 11% | 80.7 |
| Gemini 4 Carbon | medium (default) | `gemini-4-carbon-medium` | 58.4 | $6.586 | 1700 | 60.59 | 103012 | 4% | 38.1 |
| Gemini 4 Carbon | low | `gemini-4-carbon-low` | 54.2 | $7.187 | 1758 | 49.02 | 86165 | 20% | 11.7 |
| Claude Opus 5.5 | max | `claude-opus-5-5` | 59.1 | $10.036 | 1481 | 117.06 | 173313 | 50% | 330.4 |
| Claude Opus 5.5 | xhigh | `claude-opus-5-5-xhigh` | 57.5 | $6.047 | 933 | 110.82 | 103395 | 65% | 79.3 |
| Claude Opus 5.5 | high | `claude-opus-5-5-high` | 51.8 | $3.465 | 548 | 109.64 | 60071 | 64% | 21.8 |
| Claude Opus 5.5 | medium (default) | `claude-opus-5-5-medium` | 48.3 | $2.451 | 413 | 106.04 | 43817 | 67% | 13.6 |
| Claude Opus 5.5 | low | `claude-opus-5-5-low` | 34.8 | $0.976 | 177 | 107.40 | 19060 | 66% | 5.5 |
| GPT-6.2 Sol | max | `gpt-6-2-sol` | 57.3 | $1.014 | 638 | 63.22 | 40360 | 55% | 113.5 |
| GPT-6.2 Sol | xhigh | `gpt-6-2-sol-xhigh` | 55.6 | $0.648 | 397 | 61.19 | 24323 | 56% | 49.1 |
| GPT-6.2 Sol | high | `gpt-6-2-sol-high` | 54.8 | $0.564 | 334 | 60.36 | 20160 | 60% | 17.9 |
| GPT-6.2 Sol | medium | `gpt-6-2-sol-medium` | 52.4 | $0.406 | 223 | 61.10 | 13651 | 61% | 4.1 |
| GPT-6.2 Sol | low | `gpt-6-2-sol-low` | 40.6 | $0.184 | 103 | 57.84 | 5980 | 66% | 1.9 |
| Claude Sonnet 5.5 | max | `claude-sonnet-5-5` | 54.7 | $10.021 | 1861 | 153.34 | 285387 | 43% | 249.9 |
| Claude Sonnet 5.5 | xhigh | `claude-sonnet-5-5-xhigh` | 49.9 | $4.092 | 824 | 148.25 | 122205 | 62% | 36.5 |
| Claude Sonnet 5.5 | high (default) | `claude-sonnet-5-5-high` | 41.5 | $1.636 | 414 | 141.26 | 58421 | 64% | 12.5 |
| Claude Sonnet 5.5 | medium | `claude-sonnet-5-5-medium` | 30.9 | $0.781 | 216 | 142.43 | 30746 | 50% | 5.1 |
| Claude Sonnet 5.5 | low | `claude-sonnet-5-5-low` | 25.6 | $0.511 | 156 | 134.12 | 20856 | 48% | 3.8 |
| Gemini 4 Hydrogen | xhigh | `gemini-4-hydrogen` | 54.1 | $3.160 | 885 | 174.48 | 154406 | 8% | 50.0 |
| Gemini 4 Hydrogen | high (default) | `gemini-4-hydrogen-high` | 51.0 | $1.873 | 480 | 176.99 | 84978 | 9% | 17.4 |
| Gemini 4 Hydrogen | medium | `gemini-4-hydrogen-medium` | 41.1 | $0.798 | 234 | 168.29 | 39353 | 12% | 12.6 |
| Gemini 4 Hydrogen | low | `gemini-4-hydrogen-low` | 26.9 | $0.367 | 93 | 150.68 | 14074 | 19% | 6.0 |
| GPT-6.1 Terra | max | `gpt-6-1-terra` | 51.4 | $0.961 | 906 | 66.13 | 59883 | 35% | 186.7 |
| GPT-6.1 Terra | xhigh | `gpt-6-1-terra-xhigh` | 45.3 | $0.401 | 410 | 63.85 | 26200 | 37% | 35.3 |
| GPT-6.1 Terra | high | `gpt-6-1-terra-high` | 42.5 | $0.259 | 266 | 62.92 | 16746 | 37% | 13.1 |
| GPT-6.1 Terra | medium (default) | `gpt-6-1-terra-medium` | 38.1 | $0.169 | 176 | 61.66 | 10875 | 40% | 5.5 |
| GPT-6.1 Terra | low | `gpt-6-1-terra-low` | 29.4 | $0.071 | 73 | 60.92 | 4422 | 42% | 2.8 |
| GPT-6.1 Terra | none | `gpt-6-1-terra-non-reasoning` | 30.5 | $0.226 | 155 | 61.17 | 9488 | 77% | 2.3 |
| Gemini 4 Argon | high | `gemini-4-argon` | 50.5 | $7.062 | 1458 | 79.80 | 116368 | 4% | 37.8 |
| Gemini 4 Argon | medium (default) | `gemini-4-argon-medium` | 47.7 | $8.629 | 1449 | 69.31 | 100407 | 15% | 10.1 |
| Kimi K3.1 Pro | max (default) | `kimi-k3-1-pro` | 46.6 | $3.681 | 2001 | 36.11 | 72239 | 37% | 158.6 |
| Claude Haiku 5.5 | max | `claude-haiku-5-5` | 36.5 | $0.411 | 879 | 256.95 | 225966 | 34% | 168.2 |
| Claude Haiku 5.5 | xhigh | `claude-haiku-5-5-xhigh` | 34.6 | $0.248 | 573 | 237.73 | 136177 | 39% | 47.5 |
| Claude Haiku 5.5 | high | `claude-haiku-5-5-high` | 30.0 | $0.159 | 384 | 229.56 | 88064 | 39% | 19.9 |
| Claude Haiku 5.5 | medium (default) | `claude-haiku-5-5-medium` | 24.6 | $0.092 | 241 | 221.17 | 53335 | 40% | 10.0 |
| Claude Haiku 5.5 | low | `claude-haiku-5-5-low` | 18.6 | $0.044 | 128 | 220.48 | 28161 | 40% | 7.1 |
| Grok 4.7 | xhigh | `grok-4-7` | 35.4 | $7.771 | 1333 | 78.45 | 104531 | 20% | 48.3 |
| Grok 4.7 | high (default) | `grok-4-7-high` | 35.2 | $6.184 | 1116 | 79.85 | 89127 | 20% | 34.6 |
| Grok 4.7 | low | `grok-4-7-low` | 31.1 | $2.922 | 568 | 75.18 | 42670 | 34% | 9.4 |
| Gemini 3.8 Flash | high | `gemini-3-8-flash` | 30.7 | $3.022 | 959 | 103.18 | 98940 | 55% | 20.6 |
| Gemini 3.8 Flash | medium (default) | `gemini-3-8-flash-medium` | 30.1 | $2.606 | 782 | 105.00 | 82068 | 51% | 12.8 |
| Gemini 3.8 Flash | low | `gemini-3-8-flash-low` | 22.5 | - | - | 84.05 | - | 68% | 2.3 |
| GPT-6 Luna | max | `gpt-6-luna` | 27.9 | $0.152 | 606 | 124.31 | 75296 | 79% | 64.2 |
| GPT-6 Luna | xhigh | `gpt-6-luna-xhigh` | 23.5 | $0.104 | 371 | 118.17 | 43893 | 84% | 15.9 |
| GPT-6 Luna | high | `gpt-6-luna-high` | 21.5 | $0.073 | 275 | 119.49 | 32839 | 85% | 9.8 |
| GPT-6 Luna | medium (default) | `gpt-6-luna-medium` | 18.5 | $0.042 | 180 | 110.36 | 19823 | 85% | 5.5 |
| GPT-6 Luna | low | `gpt-6-luna-low` | 9.7 | $0.005 | 33 | 101.07 | 3296 | 85% | 2.2 |
| GPT-6 Luna | none | `gpt-6-luna-non-reasoning` | 9.4 | $0.071 | 101 | 99.83 | 10059 | 80% | 1.3 |
| Gemini 3.5 Flash-Lite | high | `gemini-3-5-flash-lite` | 11.7 | $0.693 | 101 | 300.84 | 30301 | 27% | 4.7 |
| Claude Haiku 4.5 | - | `claude-4-5-haiku-reasoning` | 7.4 | $0.532 | 237 | 106.46 | 25258 | 23% | 20.2 |

## Review

**Round 1 (Nov 26).** Two reviewers read a staged copy of the change with the sources above; neither saw the other's answer.

- **Gemini** (`gemini-4-hydrogen` at `high`, 37 reads, 5 minutes), scoped to `gemini.md`, `gemini-4.md`, the `SKILL.md` routing and the split: no defects.
- **Codex** (`gpt-6.2-sol` at `high`, live web, 39 reads, 7 minutes), on the whole change: 17 findings, 4 high and 13 medium. It confirmed that the split loses nothing and that all 64 table rows and their order match the data. Every finding was checked against the source and held:

| # | Finding | Fix |
|---|---|---|
| 1 | `gemini.md` gave Argon "64K output per synchronous response"; the long-decode guide gives 32,768 for a non-streaming response on Argon and Carbon (text older than this round) | Both caps stated |
| 2 | "Neon beats Carbon at every comparable point ... about half the cost" joined two comparisons: Neon `high` is 0.3 points under Carbon `high` | The comparisons are corrected in five sentences of `model-selection.md`; the curve notes and this record list all three pairs together |
| 3 | The cost column was defined as "what AA actually paid"; AA's methodology uses a measured typical cache hit rate, and the Carbon and Argon rows use a price not yet charged | Defined as AA's estimate |
| 4 | The Neon heading "set it explicitly when you come from Carbon or Argon" could be read as "pin `high`"; Google says to pin `medium` to keep the old behavior | Heading and migration bullet reworded |
| 5 | "Ahead of both ... on 16 of 19 rows": three of the 16 rows show only one competitor | Reworded |
| 6 | Kimi K3's BullshitBench figures (58% minimal, 44% xhigh) do not match the CSV (72%, 74%); the CSV did not change between Nov 18 and Nov 26, so the error is older than this round | `kimi.md` and `model-selection.md` corrected; K3 removed from the "higher effort scored lower" list |
| 7 | "Fable 5.x declines 11-36%" left out Fable 5.2 (2%) | Scoped to Fable 5 and 5.1 |
| 8 | "The harness changes the result more than the prompt": the two SWE-sweep figures compare harnesses only | Heading now says the harness moves the score a lot |
| 9 | The `xhigh` warning was quoted without "or exhaust `max_output_tokens`" | Full quotation |
| 10 | This record put GPT-6.2 Astra one place below GPT-6 Astra on the Arena board; it is two | Corrected |
| 11 | "Google's model chooser gives that second role to Neon": the chooser gives routine edits to Hydrogen and complex interactive work to Neon | Reworded |
| 12 | The Neon migration sweep started at `medium`; Google says to evaluate all four levels | `low` added, with Google's sentence |
| 13 | Direct Office inputs were dated Nov 18; the Nov 5 changelog entry already extends them. Nov 18 added slicing | Date attached to slicing only |
| 14 | A decision rule said finance and legal "are unsolved by every model"; the dated paragraph gives Carbon 2.8% on finance and neither was re-read | Rule now cites the Nov 7 read |
| 15 | "Hydrogen ... the best current model" on BullshitBench: Qwen 4 Max also scores 90% | Scoped to the vendors the skill covers, Qwen named |
| 16 | `model-selection.md` sent a reader to `gemini.md` only | Now names the per-model files |
| 17 | "One or two solved attempts apart" on GDPx's software-engineering domain did not hold for Fable 5.2 (six ahead) | Stated separately |

**Fix round.** Codex (`gpt-6.2-sol` at `medium`) read the fixes as diffs against the round 1 text, twice. The first pass (24 reads, 3 minutes) recomputed the new ratios, confirmed the moved refresh recipe matches the removed text, and found four medium defects, all confirmed and fixed: the Hydrogen entry still called it the best current model on BullshitBench (Qwen 4 Max ties it); the migration bullet told a Carbon user to send `medium` "to keep its old behavior" (Google's advice is for Argon's latency, and Neon `medium` scores 54.9 against Carbon `medium`'s 58.4); the GDPx attempt gaps were not anchored to Sonnet 5.5; and a line in this record overstated where the three Neon-Carbon pairs appear. The second pass on those four fixes (12 reads, 1 minute): sound, no findings.

Not reviewed by a second model: the wording of this Review section's fix-round paragraph, written after the last pass.

## Test

Two tasks, each answered twice by a fresh agent (Claude Sonnet 5.5, high effort) that could use only the skill's files: once with the revised skill, once with the committed one (`git archive` of the branch point). The checks were written before the answers came back and are facts a correct answer has to contain.

| Task | Revised skill | Committed skill |
|---|---|---|
| Move a code-review agent off `gemini-3.1-pro-preview` on Vertex (`europe-west2`, `thinking_budget`, an explicit cache, a prefilled model turn, an absolute scope rule) | 10 of 10 | 6 of 10 |
| Pick Gemini models and thinking levels for an orchestrator and eight workers, with scores, cost per task, prices and dates | 8 of 8 | 2 of 8 |
| Total | 18 of 18 | 8 of 18 |

With the committed skill the migration answer chose Argon at `medium` and could not say where the model is served; the pipeline answer chose Carbon at `medium` for the orchestrator (58.3 on AA, $6.59 per task at list price, 1,731 s) from the Nov 18 figures. With the revised skill both answers chose Neon (`high` for the orchestrator: 59.8, $3.74, 884 s), named its levels, price and Vertex locations, and said Argon is superseded. Mean tokens per run: 174.6K revised against 168.6K committed (3.5% more); mean time 92 s against 99 s.

The runs also logged every read: `gemini.md` and `gemini-4.md` came back whole in one call, and `model-selection.md` did not (25,282 tokens), which led to the move described above.

Limits: one run per task and version; the checks are the author's and lean on facts only the new text holds, so the gap measures whether the new content reaches an answer, not general quality; the runs used the text as it stood before the review fixes and the `model-selection.md` move, and were not repeated.

## Not re-read in this round

- Artificial Analysis sub-benchmark scores (the paragraph in `model-selection.md` is still the Nov 7 pull and says so).
- GDPx finance and legal results and per-domain winners other than software engineering (marked as earlier reads).
- Arena rows below rank 15, which the page hides, and its per-signal rankings.
- Whether remote MCP servers now work with raw model calls on the Interactions API (the tool-retrieval guide describes deferring them; the Interactions page still says remote MCP for Gemini 3 is "coming soon").
- Google's Safety and Security Report for Neon, and the Vertex pricing page.
- The Claude and GPT files, apart from figures quoted from Artificial Analysis.
