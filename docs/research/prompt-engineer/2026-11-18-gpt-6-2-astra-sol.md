# GPT-6.2 Astra and Sol (2026-11-18)

Record for the update of the `prompt-engineer` skill after OpenAI released GPT-6.2 Astra and GPT-6.2 Sol on 2026-11-17. It covers `references/gpt.md` (and its split into `gpt.md`, `gpt-6.md` and `gpt-hosts.md`), `references/model-selection.md`, twelve in-place edits to `SKILL.md`, and small dependent edits in `gemini.md`, `grok.md`, `kimi.md`, `langgraph.md`, `agent-harness-patterns.md` and the skill's `README.md`.

## Why

Both models were released the day before. The skill listed GPT-6 Astra and GPT-6.1 Sol as OpenAI's current models, and OpenAI's docs changed two parts of the request contract with the release.

## Sources

All fetched on 2026-11-18 between 11:00 and 12:00 Israel time unless noted. OpenAI's developer pages return markdown when `.md` is appended to the URL.

| Id | Source |
|---|---|
| O1 | OpenAI, *Using GPT-6.2*: https://developers.openai.com/api/docs/guides/latest-model (the GPT-6 version is still at `.../latest-model/gpt-6-astra`) |
| O2 | OpenAI, *Keep the prefix unchanged*: https://developers.openai.com/api/docs/guides/keep-prefix-unchanged (also served at `.../guides/preserved-reasoning`) |
| O3 | OpenAI, *Reasoning models*: https://developers.openai.com/api/docs/guides/reasoning (sections *Reasoning effort*, *Change reasoning mid-conversation*, *Reasoning item removal across requests*) |
| O4 | OpenAI, *Prompt caching*: https://developers.openai.com/api/docs/guides/prompt-caching, and *Prompt cache diagnostics*: `.../prompt-caching/diagnostics` |
| O5 | OpenAI model pages: https://developers.openai.com/api/docs/models/gpt-6.2-astra and `.../gpt-6.2-sol`; the models index `.../models` |
| O6 | OpenAI changelog, entries of Nov 17: https://developers.openai.com/api/docs/changelog |
| O7 | OpenAI pricing: https://developers.openai.com/api/docs/pricing; *Background mode*: `.../guides/background`; *Ultrafast mode*: `.../guides/ultrafast-mode`; data residency: `.../guides/data-residency`; priority processing: `.../guides/priority-processing` |
| O8 | OpenAI, *Model selection*: https://developers.openai.com/api/docs/guides/model-selection |
| O9 | OpenAI, *Compaction*, *Structured outputs* (changing the format mid-conversation), *Tool search* (`additional_tools`), *Responses multi-agent*: under https://developers.openai.com/api/docs/guides/ |
| O10 | OpenAI, *Introducing GPT-6.2 Astra and Sol*: https://openai.com/index/introducing-gpt-6-2-astra-sol/ (HTML fetch) |
| O11 | OpenAI, GPT-6.2 system card: https://deploymentsafety.openai.com/gpt-6-2-astra-sol |
| O12 | OpenAI, *GPT-6.2* (what's new) and *Prompting GPT-6.2 in Codex*: https://learn.chatgpt.com/docs/whats-new/gpt-62-astra-sol and https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra |
| O13 | OpenAI's open-source Codex CLI, https://github.com/openai/codex at `ca21fe65d1` (2026-11-18): `codex-rs/models-manager/models.json`, entries `gpt-6.2-astra`, `gpt-6.2-sol` and `gpt-6-astra` (`model_messages.instructions_template` and the model settings) |
| H1 | Microsoft, *GPT-6.2 Astra and GPT-6.2 Sol now generally available in Microsoft Foundry* (Nov 17): https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/gpt-6-2-astra-and-gpt-6-2-sol-now-generally-available-in-microsoft-foundry/4574122 |
| H2 | AWS, what's-new post (Nov 17): https://aws.amazon.com/about-aws/whats-new/2026/11/openai-gpt-6-2-astra-sol-amazon-bedrock/ and the Bedrock model cards `model-card-openai-gpt-6-2-astra` and `-sol` under https://docs.aws.amazon.com/bedrock/latest/userguide/ |
| F1 | OpenCode 2.3.2 release notes (Nov 18): https://github.com/anomalyco/opencode/releases/tag/v2.3.2 |
| A1 | Artificial Analysis API, `GET https://artificialanalysis.ai/api/v2/language/models/free`, pulled 11:09 and again 11:14 (4 pages, 758 rows, `intelligence_index_version` 5) |
| A2 | 71 Artificial Analysis model pages, `https://artificialanalysis.ai/models/<slug>`, fetched 11:10-11:13 |
| B1 | BullshitBench, https://github.com/petergpt/bullshit-benchmark at `c9d1b94` (2026-11-18, "Publish seven models across fourteen BullshitBench v2 variants"), `data/v2/latest/leaderboard.csv` |
| B2 | SemiAnalysis GDPx, https://gdpx.semianalysis.com/ (overall board, the board that excludes safety-classifier domains, and the software-engineering domain) |
| B3 | Arena Agent leaderboard, https://arena.ai/leaderboard/agent (dated Nov 13) |
| G1 | Google pricing, https://aistudio.google.com/docs/pricing.md (Carbon and Argon rows) |

## What OpenAI changed

**The models (O5, O6, O10).** `gpt-6.2-astra`: $8 / $40 per 1M tokens, cached input $0.40, cache writes $10 (30 minutes) or $20 (12 hours), knowledge cutoff May 18 2026. `gpt-6.2-sol`: $2 / $10, cached input $0.10, cache writes $2.50 or $5, cutoff Jun 1 2026. Both: 1,050,000-token context, 922,000 maximum input, 128,000 maximum output, text and image in, `none` effort rejected, tool calling on the Responses API only, Ultrafast at 3 times Standard through Feb 28 2027 and 6 times from Mar 1 2027.

**Reasoning is dropped after a prefix edit (O1, O2, O3).** O1: "Starting with GPT-6.2, the Responses API drops reasoning items after mid-conversation edits to the conversation history (prefix edits), certain model changes (including downgrades), or changes to the end user or organization." O3 lists the removal reasons reported in `input_transformations`: `prefix_mismatch` and `end_user_mismatch` are new with 6.2; `model_mismatch`, `organization_mismatch` and `turn_boundary` are described without that qualifier. O3 on `prefix_mismatch`: "Deleting whole items without editing the remaining items, or appending new items after the reasoning item, does not by itself trigger this reason." O2 has the table of append-only replacements that the skill's bullet list follows.

**Top-level `instructions` is appended after `input` (O1, O4).** O4: "OpenAI bills those instruction tokens at the uncached input-token rate on every request, even if you repeat identical instructions." F1 is one harness's measurement of the effect: "On GitHub Copilot `gpt-6.2-sol`, uncached input per step dropped from about 14,000 tokens to 3."

**Other API facts used:** background completion windows, 30% and 40% below Standard (O6, O7); `configuration_update` now also changes `text.format` (O3, O9); multi-agent beta model list and header (O9); cache reads at 0.05 times input on both 6.2 models (O4).

## What OpenAI says about behavior

O1 lists four behaviors for GPT-6.2 Astra (writing style, task completion, coding style, frontend design) with a prompt for each; the skill quotes them. O12 adds effort guidance, "use subagents as needed", and reviewing visual work at display size.

O11 is the source for the numbers in the skill's *Prompting GPT-6.2* section:

- Blocker Deception: "GPT-6.2 Astra omitted a known obstacle to completing its work in 22.28 percent of trials, compared with 11.09 percent for GPT-6 Astra." Broken Search Tool: 23.00% against 7.58% (and 1.00% for GPT-6.1 Terra). "The Codex developer prompt used in these evaluations is not applied to direct API requests." O11 gives Sol's figures only in charts; the text says both models regressed.
- Respecting Warnings (completed circumventions): 17.41% for 6.2 Astra, 19.37% for GPT-6 Astra, 29.63% for GPT-6.1 Terra. O11 notes that this metric replaced the earlier count of attempts.
- Prompt injection in model-generated environments: resisted 84.67% (6.2 Astra), 91.65% (6.2 Sol), 44.98% (GPT-6 Astra).
- Replayed internal Codex traffic: instruction-following failures in 2.87% of turns (6.2 Astra) against 1.96% (GPT-6 Astra), and 4.66% (6.2 Sol) against 3.21% (GPT-6.1 Sol).
- Evaluation awareness, the tighter cyber refusal boundary, misalignment monitoring for both models, and the distillation figures (54.0% to 0.2%).

O13 is OpenAI's own prompt for these models in Codex. Its `gpt-6.2-astra` and `gpt-6.2-sol` templates are identical and contain the lines the skill quotes ("If you are blocked and unable to make useful progress…", "In your final answer back to the user, mention any relevant flaws…", "Do not invent requirements, rules or policies…"); a search of the `gpt-6-astra` template for "blocked and unable", "relevant flaws", "Disclosure in commentary", "Do not invent requirements" and "earlier refusal or blocker" finds none of them. O11 credits "the Codex developer prompt" as a whole and does not say which lines reduce the omissions, and the skill says so. The reading that the "Do not invent requirements" line points at a model habit is ours and is marked as such in the skill.

## Benchmarks read

**Artificial Analysis (A1, A2).** All 60 table rows were re-pulled in one pass, with GPT-6.2 Astra and Sol replacing GPT-6 Astra and GPT-6.1 Sol. For the 50 retained rows, intelligence, cost per task and hallucination rate were unchanged from Nov 17 (scripted assertions), with one exception: A1 now prices Gemini 4 Carbon at $4 / $20 and reports $6.59 (`medium`), $7.76 (`high`) and $7.19 (`low`) per task, while A2's Carbon pages still use $2 / $10 and the Nov 17 costs. G1 confirms Google still charges $2 / $10 through Nov 30, so the table keeps the page figures and the text gives both. The earlier text projected Carbon's Dec 1 cost by doubling ($9.36-10.97); A1's own list-price figures are lower, and A1's `pricing` fields show the same $4 cache-write price under both, so that projection was removed. Time per task moved by -5.8% to +5.8% on retained rows, tok/s by -5.3% to +6.4%.

Output tokens divided by time per task equalled A1's `performance_v3` mean within 0.1% on 53 of the 59 rows that have a time; five rows differed by 0.2-0.6% and GPT-6.2 Astra `medium` by 8.1% (page: 13,165 tokens and 231 s, which implies 57.0 tok/s; API: 52.7). A second API pull five minutes later returned the same speeds for all 61 variants, and re-fetching the six pages returned the same times, so the difference is not a stale page. The table uses the API speed and the page time, as before, and the column note states the mismatch.

**BullshitBench (B1).** New runs published the same morning. Clear-pushback rate (`green_rate`, all attempts) at the lowest and highest effort run: Gemini 4 Hydrogen 62% / 90%, Grok 4.7 75% / 72%, Gemini 4 Carbon 61% / 72%, Claude Fable 5.2 62% / 66%, Kimi K3.1 Pro 50% / 60%, GPT-6.2 Astra 49% / 55%, GPT-6.1 Terra 54% / 53%, GPT-6.2 Sol 46% / 42%. Higher effort scored higher for five of the eight, which the skill now says next to its older "effort often hurts" finding.

**GDPx (B2).** Claude Fable 5.2 was added since the Nov 7 read: 16.4% overall ($88.15 per task), 16.8% on the board that excludes safety-classifier domains, 24.4% on the software-engineering domain. The other rows are unchanged. GPT-6.2 is not listed.

**Arena (B3).** The Nov 13 board has the same top 11 as the Nov 11 board in the skill. GPT-6.2 is not listed.

## What changed in the skill

| File | Change |
|---|---|
| `references/gpt.md` | Model list led by the 6.2 models; new sections *GPT-6.2: what changed in the API* and *Prompting GPT-6.2 (Astra and Sol)*; a *To GPT-6.2* migration list; updates to effort, sampling, verbosity, tools, caching, the model ladder, safeguards and frontend |
| `references/gpt-6.md` (new) | The three sections on the GPT-6 models before 6.2, moved out of `gpt.md` with one added sentence from O12 |
| `references/gpt-hosts.md` (new) | The Azure Foundry and AWS Bedrock section, moved out of `gpt.md`, with the 6.2 facts from H1 and H2 |
| `references/model-selection.md` | Table rebuilt from one pull; cost frontier, time frontier, value leader, effort, Fable 5.2, hallucination, per-model entries, Arena, GDPx, BullshitBench, decision rules and the refresh notes rewritten for the new data |
| `SKILL.md` | Twelve in-place edits (routing to the new files, the 6.2 knobs, the false-premise bullet, tables); still 495 lines |
| `gemini.md`, `grok.md`, `kimi.md` | Figures that quote Artificial Analysis refreshed to the Nov 18 pull; the Nov 18 BullshitBench results added next to their statements about effort |
| `langgraph.md` | One bullet: on GPT-6.2 a history edit drops reasoning (derived from O2; not measured in LangChain, and the bullet says so) |
| `agent-harness-patterns.md`, `README.md` | Pointers to the new files |

**Why `gpt.md` was split.** With the 6.2 material the file was 76.8 KB. A single call of the reading tool this skill is used with returned lines 1-241 of 325 and reported 28,621 tokens against a cap of 25,000. The skill tells the reader to read each reference file in full, and on Nov 13 `claude.md` was split for the same reason. `gpt.md` is now 60.4 KB; the two new files are read when their models or hosts are in scope (Step 0b).

## Data

Artificial Analysis, pulled 2026-11-18 11:09 Israel time (API) and 11:10-11:13 (pages). Cost per task is the API figure; for the three Carbon rows the table in the skill shows the page figures instead ($5.48, $4.68, $5.22).

| Model | Effort | AA slug | Intel | Cost / task (API) | Time s (page) | v3 tok/s (API) | Output tokens / task | Halluc. | First answer token s |
|---|---|---|---|---|---|---|---|---|---|
| Claude Fable 5.2 | max | `claude-fable-5-2` | 64.6 | $26.539 | 2467 | 110.96 | 273776 | 59% | 215.3 |
| Claude Fable 5.2 | xhigh | `claude-fable-5-2-xhigh` | 62.2 | $14.829 | 1443 | 112.24 | 161944 | 60% | 56.9 |
| Claude Fable 5.2 | high (default) | `claude-fable-5-2-high` | 61.8 | $9.078 | 892 | 109.71 | 97841 | 58% | 24.5 |
| Claude Fable 5.2 | medium | `claude-fable-5-2-medium` | 56.4 | $3.803 | 382 | 112.81 | 43131 | 58% | 10.0 |
| Claude Fable 5.2 | low | `claude-fable-5-2-low` | 53.9 | $3.097 | 321 | 111.74 | 35860 | 56% | 7.3 |
| Gemini 4 Carbon | high | `gemini-4-carbon` | 60.0 | $7.755 | 2051 | 59.87 | 122768 | 11% | 74.4 |
| Gemini 4 Carbon | medium (default) | `gemini-4-carbon-medium` | 58.3 | $6.586 | 1731 | 59.50 | 103012 | 4% | 28.0 |
| Gemini 4 Carbon | low | `gemini-4-carbon-low` | 54.2 | $7.187 | 1778 | 48.47 | 86165 | 20% | 8.7 |
| Claude Opus 5.5 | max | `claude-opus-5-5` | 59.1 | $10.036 | 1472 | 117.73 | 173313 | 50% | 358.0 |
| Claude Opus 5.5 | xhigh | `claude-opus-5-5-xhigh` | 57.4 | $6.047 | 937 | 110.33 | 103395 | 65% | 65.4 |
| Claude Opus 5.5 | high | `claude-opus-5-5-high` | 51.8 | $3.465 | 556 | 108.00 | 60071 | 64% | 21.0 |
| Claude Opus 5.5 | medium (default) | `claude-opus-5-5-medium` | 48.2 | $2.451 | 411 | 106.68 | 43817 | 67% | 11.9 |
| Claude Opus 5.5 | low | `claude-opus-5-5-low` | 34.8 | $0.976 | 181 | 105.28 | 19060 | 66% | 5.0 |
| GPT-6.2 Astra | max | `gpt-6-2-astra` | 62.1 | $3.998 | 689 | 59.55 | 41029 | 59% | 178.5 |
| GPT-6.2 Astra | xhigh | `gpt-6-2-astra-xhigh` | 61.6 | $2.521 | 391 | 56.84 | 22238 | 58% | 53.9 |
| GPT-6.2 Astra | high | `gpt-6-2-astra-high` | 60.1 | $2.074 | 305 | 58.41 | 17828 | 58% | 23.1 |
| GPT-6.2 Astra | medium | `gpt-6-2-astra-medium` | 57.0 | $1.618 | 231 | 52.73 | 13165 | 54% | 3.2 |
| GPT-6.2 Astra | low | `gpt-6-2-astra-low` | 45.7 | $0.662 | 93 | 56.30 | 5216 | 56% | 2.8 |
| GPT-6.2 Sol | max | `gpt-6-2-sol` | 57.3 | $1.014 | 474 | 85.06 | 40360 | 55% | 68.2 |
| GPT-6.2 Sol | xhigh | `gpt-6-2-sol-xhigh` | 55.7 | $0.648 | 297 | 81.96 | 24323 | 56% | 27.4 |
| GPT-6.2 Sol | high | `gpt-6-2-sol-high` | 54.9 | $0.564 | 254 | 79.49 | 20160 | 60% | 10.0 |
| GPT-6.2 Sol | medium | `gpt-6-2-sol-medium` | 52.7 | $0.406 | 184 | 74.38 | 13651 | 61% | 3.1 |
| GPT-6.2 Sol | low | `gpt-6-2-sol-low` | 40.6 | $0.184 | 85 | 70.40 | 5980 | 66% | 2.0 |
| Claude Sonnet 5.5 | max | `claude-sonnet-5-5` | 54.5 | $10.021 | 1935 | 147.48 | 285387 | 43% | 295.8 |
| Claude Sonnet 5.5 | xhigh | `claude-sonnet-5-5-xhigh` | 49.9 | $4.092 | 851 | 143.64 | 122205 | 62% | 29.4 |
| Claude Sonnet 5.5 | high (default) | `claude-sonnet-5-5-high` | 41.5 | $1.636 | 421 | 138.88 | 58421 | 64% | 9.6 |
| Claude Sonnet 5.5 | medium | `claude-sonnet-5-5-medium` | 30.8 | $0.781 | 225 | 136.73 | 30746 | 50% | 5.3 |
| Claude Sonnet 5.5 | low | `claude-sonnet-5-5-low` | 25.6 | $0.511 | 154 | 134.70 | 20856 | 48% | 2.5 |
| Gemini 4 Hydrogen | xhigh | `gemini-4-hydrogen` | 53.9 | $3.160 | 896 | 172.39 | 154406 | 8% | 42.9 |
| Gemini 4 Hydrogen | high (default) | `gemini-4-hydrogen-high` | 50.8 | $1.873 | 501 | 169.47 | 84978 | 9% | 17.4 |
| Gemini 4 Hydrogen | medium | `gemini-4-hydrogen-medium` | 41.2 | $0.798 | 241 | 162.15 | 39353 | 12% | 12.6 |
| Gemini 4 Hydrogen | low | `gemini-4-hydrogen-low` | 26.9 | $0.292 | 89 | 157.82 | 14074 | 19% | 6.2 |
| GPT-6.1 Terra | max | `gpt-6-1-terra` | 51.3 | $0.961 | 860 | 69.64 | 59883 | 35% | 148.1 |
| GPT-6.1 Terra | xhigh | `gpt-6-1-terra-xhigh` | 45.3 | $0.401 | 394 | 66.50 | 26200 | 37% | 29.7 |
| GPT-6.1 Terra | high | `gpt-6-1-terra-high` | 42.4 | $0.259 | 253 | 66.08 | 16746 | 37% | 10.7 |
| GPT-6.1 Terra | medium (default) | `gpt-6-1-terra-medium` | 38.2 | $0.169 | 169 | 64.24 | 10875 | 40% | 4.7 |
| GPT-6.1 Terra | low | `gpt-6-1-terra-low` | 29.4 | $0.071 | 72 | 61.25 | 4422 | 42% | 3.0 |
| GPT-6.1 Terra | none | `gpt-6-1-terra-non-reasoning` | 30.5 | $0.226 | 150 | 63.44 | 9488 | 77% | 2.7 |
| Gemini 4 Argon | high | `gemini-4-argon` | 50.4 | $4.973 | 1753 | 66.37 | 116368 | 4% | 47.2 |
| Gemini 4 Argon | medium (default) | `gemini-4-argon-medium` | 47.6 | $4.315 | 1684 | 59.62 | 100407 | 15% | 14.9 |
| Kimi K3.1 Pro | max (default) | `kimi-k3-1-pro` | 46.5 | $3.681 | 2305 | 31.34 | 72239 | 37% | 157.8 |
| Claude Haiku 5.5 | max | `claude-haiku-5-5` | 36.5 | $0.411 | 884 | 255.48 | 225966 | 34% | 192.0 |
| Claude Haiku 5.5 | xhigh | `claude-haiku-5-5-xhigh` | 34.6 | $0.248 | 577 | 235.99 | 136177 | 39% | 44.2 |
| Claude Haiku 5.5 | high | `claude-haiku-5-5-high` | 29.9 | $0.159 | 387 | 227.17 | 88064 | 39% | 20.2 |
| Claude Haiku 5.5 | medium (default) | `claude-haiku-5-5-medium` | 24.6 | $0.092 | 237 | 225.23 | 53335 | 40% | 10.3 |
| Claude Haiku 5.5 | low | `claude-haiku-5-5-low` | 18.6 | $0.044 | 131 | 214.78 | 28161 | 40% | 5.8 |
| Grok 4.7 | xhigh | `grok-4-7` | 35.5 | $7.771 | 1459 | 71.62 | 104531 | 20% | 49.5 |
| Grok 4.7 | high (default) | `grok-4-7-high` | 35.2 | $6.184 | 1275 | 69.91 | 89127 | 20% | 37.5 |
| Grok 4.7 | low | `grok-4-7-low` | 31.1 | $2.922 | 601 | 71.08 | 42670 | 34% | 13.4 |
| Gemini 3.8 Flash | high | `gemini-3-8-flash` | 30.8 | $7.766 | 852 | 116.23 | 98940 | 55% | 22.4 |
| Gemini 3.8 Flash | medium (default) | `gemini-3-8-flash-medium` | 30.1 | $6.259 | 682 | 120.27 | 82068 | 51% | 15.4 |
| Gemini 3.8 Flash | low | `gemini-3-8-flash-low` | 22.5 | - | - | 107.56 | - | 68% | 4.2 |
| GPT-6 Luna | max | `gpt-6-luna` | 27.9 | $0.152 | 730 | 103.19 | 75296 | 79% | 67.7 |
| GPT-6 Luna | xhigh | `gpt-6-luna-xhigh` | 23.5 | $0.104 | 439 | 99.88 | 43893 | 84% | 15.8 |
| GPT-6 Luna | high | `gpt-6-luna-high` | 21.4 | $0.073 | 350 | 93.79 | 32839 | 85% | 10.4 |
| GPT-6 Luna | medium (default) | `gpt-6-luna-medium` | 18.5 | $0.042 | 207 | 95.73 | 19823 | 85% | 5.3 |
| GPT-6 Luna | low | `gpt-6-luna-low` | 9.7 | $0.005 | 37 | 88.37 | 3296 | 85% | 2.5 |
| GPT-6 Luna | none | `gpt-6-luna-non-reasoning` | 9.4 | $0.071 | 110 | 91.17 | 10059 | 80% | 1.5 |
| Gemini 3.5 Flash-Lite | high | `gemini-3-5-flash-lite` | 11.7 | $0.693 | 92 | 326.85 | 30301 | 27% | 4.8 |
| Claude Haiku 4.5 | - | `claude-4-5-haiku-reasoning` | 7.4 | $0.532 | 226 | 111.88 | 25258 | 23% | 19.6 |

Superseded rows from the same pull (no longer in the table):

| Model | Effort | AA slug | Intel | Cost / task (API) | Time s (page) | v3 tok/s (API) | Output tokens / task | Halluc. | First answer token s |
|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Astra | max | `gpt-6-astra` | 56.9 | $6.245 | 1195 | 43.50 | 51973 | 50% | 189.1 |
| GPT-6 Astra | xhigh | `gpt-6-astra-xhigh` | 55.3 | $3.659 | 610 | 43.71 | 26724 | 45% | 83.0 |
| GPT-6 Astra | high | `gpt-6-astra-high` | 54.8 | $3.239 | 526 | 43.74 | 23133 | 43% | 40.2 |
| GPT-6 Astra | medium | `gpt-6-astra-medium` | 51.6 | $2.732 | 388 | 46.48 | 18052 | 45% | 6.0 |
| GPT-6 Astra | low | `gpt-6-astra-low` | 43.3 | $1.424 | 199 | 45.95 | 9126 | 44% | 3.4 |
| GPT-6.1 Sol | max | `gpt-6-1-sol` | 54.6 | $1.272 | 1398 | 48.52 | 67824 | 52% | 145.2 |
| GPT-6.1 Sol | xhigh | `gpt-6-1-sol-xhigh` | 52.5 | $0.764 | 561 | 53.86 | 30241 | 48% | 59.7 |
| GPT-6.1 Sol | high | `gpt-6-1-sol-high` | 50.3 | $0.591 | 445 | 50.81 | 22606 | 49% | 26.3 |
| GPT-6.1 Sol | medium (default) | `gpt-6-1-sol-medium` | 46.3 | $0.359 | 257 | 52.57 | 13518 | 48% | 4.8 |
| GPT-6.1 Sol | low | `gpt-6-1-sol-low` | 34.8 | $0.162 | 113 | 51.77 | 5838 | 50% | 3.0 |

## Review

Two engines read the change against the sources with the same prompt (the `pair-intelligence` skill; Codex with live web search, Gemini without). Every finding was checked against the source before it was fixed.

- **Codex** (gpt-6.1-sol, high effort, 328 s): 9 findings, 3 high and 6 medium, all confirmed and fixed. (1) Opus 5.5 was still called the strongest model with standard ZDR eligibility, though GPT-6.2 Astra is ZDR-eligible and scores higher. (2) `SKILL.md` said a top-level effort change only restarts the cache; on GPT-6.2 it is a prefix change. (3) The compaction recipe left out declaring again the tools added with `additional_tools`. (4) The cost-frontier text excluded Claude Haiku 5.5 `high`, which is on the frontier. (5) "Under 3% of turns" was attached to test suspicion; O11 attaches it to apparent changes in behavior. (6) `grok.md` still said Grok 4.7 was not scored on BullshitBench. (7) A decision rule still said Sonnet 5.5 matched the top of GDPx's software-engineering domain. (8) Grok 4.7's GDPx rank was 12, now 13. (9) Flex pricing was claimed for the 6.2 models, and O7 has no Flex row for them. Codex also checked all 60 table cells and both frontiers by script.
- **Gemini** (gemini-4-argon, 1,774 s; its tool-time limit ended the run before it finished a cell-by-cell pass): 8 findings. Four repeated Codex's (5, 6, 8, 9). Four were new, confirmed and fixed: the multi-agent sentence implied GPT-6 Astra runs the beta, which O9 lists only for the 6.2 models, GPT-6.1 Sol and GPT-5.6; the caching section named the Chat Completions usage field for the Responses API (an older error, also in `SKILL.md`); the time-frontier list left out GPT-6 Luna `low`; and this record's data table printed speeds with one decimal.
- After finding 6 the other provider files were checked for the same kind of stale claim: `gemini.md` and `kimi.md` now give the Nov 18 BullshitBench figures next to their older statements about effort.
- **Fix check.** A second Codex pass over the fixes only (medium effort, 118 s) confirmed them and found one more defect of the same kind as finding 4: the Claude Haiku 5.5 entry still said GPT-6 Luna and Terra match it for the same or less per task, which is not true of its `low` and `high` rows. Reworded. A third pass over that sentence (51 s) found nothing.

## Test

Two questions, each answered by a subagent (Claude Sonnet 5.5, high effort) once with the revised skill and once with the skill as committed before this change, then graded against written checks.

| Question | Checks | Revised skill | Previous skill |
|---|---|---|---|
| Move a coding-agent harness from GPT-6.1 Sol to GPT-6.2 Sol: request code, prompt and evals | 9 | 9 | 3 |
| Shortlist models for a report-and-deck agent under cost, time and retention limits | 7 | 6 | 3 |

With the previous skill the first answer said it had no facts about GPT-6.2 and advised keeping the system prompt in `instructions`; the second shortlisted GPT-6 Astra and GPT-6.1 Sol. The revised skill's one miss: its second answer did not state the retention status of each shortlisted model. Mean tokens per run were 199,827 (revised) and 181,831 (previous); mean time 144 s and 128 s. The runs used the text after the Codex fixes and before the Gemini fixes and the fix check.

The runs also recorded how files were read. A single read returned the whole of the revised `gpt.md`. `SKILL.md` (about 36,000 tokens by the tool's count) and `claude.md` (26,363 tokens) needed more than one read with both versions of the skill; this round did not change the size of either.

## Not re-read in this round

- Artificial Analysis sub-benchmark scores (the paragraph in `model-selection.md` is still the Nov 7 pull and says so).
- GDPx per-domain winners other than software engineering (the sentence is now marked as predating Fable 5.2).
- Whether Foundry and Bedrock apply the prefix check and the `instructions` change (H1 and H2 are silent; the skill says to test).
- OpenAI's general guides beyond the sections listed under O3, O4 and O9, and the other vendors' pages.
- The `writing-project-instructions` skill in the same repository, which cites GPT-6 Astra's guidance on `AGENTS.md`.
- The size of `claude.md`, which the test runs showed is slightly over the single-read limit.
