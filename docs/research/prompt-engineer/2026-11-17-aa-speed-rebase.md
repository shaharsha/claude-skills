# Artificial Analysis speed re-base to Performance v3 (2026-11-17)

Record for the change to the Time / task and tok/s columns of `skills/prompt-engineer/references/model-selection.md`, and to one dependent sentence each in `gemini.md` and `kimi.md`, made on this date. It closes the open item left by the same day's Hydrogen re-check (`2026-11-17-gemini-4-hydrogen-recheck.md`).

## Why

Artificial Analysis (AA) says in its API notes that the `performance` block, which holds medians, returns null from 2026-12-10, and that `performance_v3` replaces it. The table's tok/s column used the median, and its rows came from three pull dates (Nov 7, Nov 10, Nov 17). So the column mixed dates and was about to lose its source.

## Sources (all fetched 2026-11-17 between 18:21 and 18:24 Israel time, except A3)

| Id | Source |
|---|---|
| A1 | `GET https://artificialanalysis.ai/api/v2/language/models/free`, 4 pages, 742 rows, `intelligence_index_version` 5 (needs an API key) |
| A2 | 60 model pages, `https://artificialanalysis.ai/models/<slug>`, one per table row, with the slug taken from A1's `slug` field. Each page embeds per-variant data: `intelligenceIndexTimePerTask`, `intelligenceIndexOutputTokensPerTask.output`, `omniscienceHallucinationRate`, `intelligenceIndexCostPerTask.cost.total` |
| A3 | API notes, https://artificialanalysis.ai/data-api/docs (read at 15:40 the same day) |
| A4 | Performance benchmarking methodology, https://artificialanalysis.ai/methodology/performance-benchmarking (version history entry 3.0.0, 3 November 2026) |

## What Performance v3 measures (A4)

`performance_v3.mean_output_tokens_per_second` is not the old median with a different average. A4's version history lists what changed in 3.0.0:

- **Workloads.** Single requests of about 1,000, 10,000 and 100,000 input tokens, plus multi-turn agentic tasks with tool calls "from our coding, knowledge work and automation evaluations", all measured under concurrent load.
- **Headline speed.** "An endpoint's value for a workload is the average of its run medians over the past 5 days", and the headline figure "now averages the workloads we measured over the past 5 days (previously the median of the 10k input token workload over the past 72 hours)". Each workload counts equally.
- **What counts as output time.** "Output speed now covers each request's full duration, including time to first token, and excludes the time tools take to run in multi-turn sessions." Reasoning tokens are counted as output.
- **Failures.** "Failures on the endpoint's side now count as an output speed of 0."
- **Token counting.** "We count output tokens as reported by each provider's API (previously tiktoken o200k_base)."
- **Frequency.** Every 6 hours (previously every 3).

The skill's column note states these points. Its advice to compare time per task across vendors and tok/s within one vendor is the author's inference from the token-counting change: a provider-reported token is not the same unit across vendors, while time per task divides provider tokens by a provider-token speed, so the unit cancels.

## Checks

- A1 and A2 join on the variant id for 60 of 60 rows.
- Intelligence (A1 and A2), cost per task (A1 and A2) and hallucination rate (A2) equal the table's existing cells on all 60 rows. The apply script asserts each one, so those cells were not edited.
- Output tokens per task divided by time per task (both A2) equals A1's `performance_v3` mean within 0.005 tok/s on all 59 rows that have a time (3.8 Flash `low` has no cost or time). So AA's time per task is computed from the v3 speed, and the two columns now agree with each other.
- Same-day drift, against the API pull made at 15:25: the v3 mean moved 4.5% on Carbon `high` and at most 2.1% on the other 59 rows. The median moved up to 5.5%.

## What changed in the skill

| Change | Source |
|---|---|
| Time / task refreshed on all 59 rows that have one. Against the table's earlier cells the change runs from -19% to +12%, and 17 rows moved more than 5% | A2 |
| tok/s changed from the `performance` median to the `performance_v3` mean on all 60 rows | A1 |
| Column note rewritten: what tok/s now measures, and the change of basis and its date. The time estimate is now said to leave out only tool execution, because the v3 speed covers each request's full duration under AA's test load (first-token wait and queueing included) | A4, A1 |
| Staleness header and table title: every row is now from one pull date | A1, A2 |
| Time frontier: Fable 5.2 holds it at every level from 53.9 points up. Opus 5.5 `xhigh` (945 s for 57.4) is no longer on it, because Fable 5.2 `high` now reads 878 s for 61.8 | A1, A2 |
| Speed ranges in prose: Sonnet 5.5 131-147, Fable 5.2 106-112, Hydrogen 162-179, Haiku 5.5 213-257, Flash-Lite 322, Kimi K3.1 Pro 31, Carbon 50-61 | A1 |
| GPT-6.1 Terra is no longer called fast per token (62-70 tok/s, below every current Claude model and Hydrogen). The entry now cites its short estimated generation times (71-252 s at `low` to `high`) | A1, A2 |
| Time ranges in prose: Fable 5.2 878-2,446 s, Carbon 1,734-2,004 s, Astra 538-649 s, Hydrogen `high` 474 s, Kimi K3.1 Pro 2,321 s | A2 |
| Time to first answer token, now the v3 mean: Kimi K3.1 Pro about 153 s (`model-selection.md`, `kimi.md`); Carbon `high` 73 s, Argon `high` 47 s, Hydrogen `xhigh` 44 s (`gemini.md`, replacing an undated "~51 s") | A1 |
| *Refreshing the AA data*: the v3 method and its URL, the instruction to refresh all rows from one pull, and that the API's `slug` is the page slug | A1, A3, A4 |

How the two measures compare on the same pull, by family (v3 mean against median): Claude models read 10% to 49% faster, Gemini 4 models 12% to 35% slower, GPT-6.1 Terra 9% to 21% slower, GPT-6 Luna 12% to 20% slower, GPT-6.1 Sol between 23% slower and 8% faster, GPT-6 Astra between 12% slower and 7% faster.

The Haiku 4.5 row's old tok/s (88) was close to the non-reasoning variant's median (87 on this pull), not the reasoning variant's (101). Every cell in that row now comes from the reasoning variant, the one that carries the 7.4 score.

## Data

Time in seconds. "Table before" is what the skill held (rows pulled Nov 7, Fable 5.2 rows Nov 10, Gemini 4 rows Nov 17 at 15:25). The tok/s before was the median. Output tokens are per Intelligence Index task. TTFAT is `mean_time_to_first_answer_token_seconds`.

| Model | Effort | AA slug | Time before | Time now | tok/s before | Median now | v3 mean now | Output tokens | TTFAT (s) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Fable 5.2 | max | `claude-fable-5-2` | 2784 | 2446 | 95 | 93 | 112 | 273,776 | 221 |
| Claude Fable 5.2 | xhigh | `claude-fable-5-2-xhigh` | 1582 | 1532 | 83 | 77 | 106 | 161,944 | 49 |
| Claude Fable 5.2 | high | `claude-fable-5-2-high` | 1059 | 878 | 76 | 75 | 111 | 97,841 | 24 |
| Claude Fable 5.2 | medium | `claude-fable-5-2-medium` | 501 | 406 | 75 | 73 | 106 | 43,131 | 10 |
| Claude Fable 5.2 | low | `claude-fable-5-2-low` | 388 | 324 | 75 | 74 | 111 | 35,860 | 7 |
| Gemini 4 Carbon | high | `gemini-4-carbon` | 1913 | 2004 | 85 | 83 | 61 | 122,768 | 73 |
| Gemini 4 Carbon | medium | `gemini-4-carbon-medium` | 1802 | 1777 | 78 | 77 | 58 | 103,012 | 25 |
| Gemini 4 Carbon | low | `gemini-4-carbon-low` | 1735 | 1734 | 76 | 76 | 50 | 86,165 | 10 |
| Claude Opus 5.5 | max | `claude-opus-5-5` | 1499 | 1475 | 95 | 94 | 117 | 173,313 | 353 |
| Claude Opus 5.5 | xhigh | `claude-opus-5-5-xhigh` | 953 | 945 | 81 | 78 | 109 | 103,395 | 66 |
| Claude Opus 5.5 | high | `claude-opus-5-5-high` | 553 | 556 | 76 | 74 | 108 | 60,071 | 21 |
| Claude Opus 5.5 | medium | `claude-opus-5-5-medium` | 407 | 407 | 74 | 72 | 108 | 43,817 | 12 |
| Claude Opus 5.5 | low | `claude-opus-5-5-low` | 181 | 182 | 76 | 74 | 105 | 19,060 | 5 |
| GPT-6 Astra | max | `gpt-6-astra` | 1261 | 1226 | 49 | 48 | 42 | 51,973 | 196 |
| GPT-6 Astra | xhigh | `gpt-6-astra-xhigh` | 630 | 649 | 47 | 47 | 41 | 26,724 | 87 |
| GPT-6 Astra | high | `gpt-6-astra-high` | 544 | 538 | 46 | 44 | 43 | 23,133 | 45 |
| GPT-6 Astra | medium | `gpt-6-astra-medium` | 391 | 395 | 42 | 45 | 46 | 18,052 | 6 |
| GPT-6 Astra | low | `gpt-6-astra-low` | 212 | 202 | 41 | 42 | 45 | 9,126 | 4 |
| GPT-6.1 Sol | max | `gpt-6-1-sol` | 1302 | 1387 | 62 | 63 | 49 | 67,824 | 156 |
| GPT-6.1 Sol | xhigh | `gpt-6-1-sol-xhigh` | 588 | 581 | 67 | 56 | 52 | 30,241 | 66 |
| GPT-6.1 Sol | high | `gpt-6-1-sol-high` | 417 | 445 | 59 | 52 | 51 | 22,606 | 30 |
| GPT-6.1 Sol | medium | `gpt-6-1-sol-medium` | 246 | 255 | 53 | 49 | 53 | 13,518 | 5 |
| GPT-6.1 Sol | low | `gpt-6-1-sol-low` | 109 | 112 | 52 | 52 | 52 | 5,838 | 3 |
| Claude Sonnet 5.5 | max | `claude-sonnet-5-5` | 1889 | 1938 | 135 | 131 | 147 | 285,387 | 287 |
| Claude Sonnet 5.5 | xhigh | `claude-sonnet-5-5-xhigh` | 907 | 854 | 106 | 100 | 143 | 122,205 | 27 |
| Claude Sonnet 5.5 | high | `claude-sonnet-5-5-high` | 414 | 406 | 104 | 99 | 144 | 58,421 | 9 |
| Claude Sonnet 5.5 | medium | `claude-sonnet-5-5-medium` | 215 | 236 | 97 | 99 | 131 | 30,746 | 5 |
| Claude Sonnet 5.5 | low | `claude-sonnet-5-5-low` | 157 | 155 | 100 | 99 | 135 | 20,856 | 2 |
| Gemini 4 Hydrogen | xhigh | `gemini-4-hydrogen` | 893 | 896 | 208 | 201 | 172 | 154,406 | 44 |
| Gemini 4 Hydrogen | high | `gemini-4-hydrogen-high` | 473 | 474 | 206 | 204 | 179 | 84,978 | 15 |
| Gemini 4 Hydrogen | medium | `gemini-4-hydrogen-medium` | 237 | 238 | 205 | 205 | 166 | 39,353 | 12 |
| Gemini 4 Hydrogen | low | `gemini-4-hydrogen-low` | 87 | 87 | 246 | 246 | 162 | 14,074 | 6 |
| GPT-6.1 Terra | max | `gpt-6-1-terra` | 825 | 856 | 112 | 89 | 70 | 59,883 | 150 |
| GPT-6.1 Terra | xhigh | `gpt-6-1-terra-xhigh` | 370 | 388 | 89 | 78 | 67 | 26,200 | 30 |
| GPT-6.1 Terra | high | `gpt-6-1-terra-high` | 241 | 252 | 87 | 74 | 66 | 16,746 | 10 |
| GPT-6.1 Terra | medium | `gpt-6-1-terra-medium` | 155 | 168 | 89 | 73 | 65 | 10,875 | 5 |
| GPT-6.1 Terra | low | `gpt-6-1-terra-low` | 64 | 71 | 84 | 74 | 62 | 4,422 | 3 |
| GPT-6.1 Terra | none | `gpt-6-1-terra-non-reasoning` | 133 | 148 | 78 | 71 | 64 | 9,488 | 2 |
| Gemini 4 Argon | high | `gemini-4-argon` | 1760 | 1755 | 89 | 90 | 66 | 116,368 | 47 |
| Gemini 4 Argon | medium | `gemini-4-argon-medium` | 1704 | 1680 | 83 | 83 | 60 | 100,407 | 13 |
| Kimi K3.1 Pro | max | `kimi-k3-1-pro` | 2169 | 2321 | 27 | 28 | 31 | 72,239 | 153 |
| Claude Haiku 5.5 | max | `claude-haiku-5-5` | 964 | 880 | 232 | 233 | 257 | 225,966 | 187 |
| Claude Haiku 5.5 | xhigh | `claude-haiku-5-5-xhigh` | 582 | 588 | 178 | 179 | 232 | 136,177 | 48 |
| Claude Haiku 5.5 | high | `claude-haiku-5-5-high` | 395 | 391 | 165 | 159 | 225 | 88,064 | 19 |
| Claude Haiku 5.5 | medium | `claude-haiku-5-5-medium` | 248 | 238 | 166 | 159 | 224 | 53,335 | 10 |
| Claude Haiku 5.5 | low | `claude-haiku-5-5-low` | 129 | 132 | 161 | 154 | 213 | 28,161 | 5 |
| Grok 4.7 | xhigh | `grok-4-7` | 1435 | 1470 | 75 | 70 | 71 | 104,531 | 51 |
| Grok 4.7 | high | `grok-4-7-high` | 1223 | 1267 | 65 | 65 | 70 | 89,127 | 35 |
| Grok 4.7 | low | `grok-4-7-low` | 597 | 595 | 55 | 63 | 72 | 42,670 | 13 |
| Gemini 3.8 Flash | high | `gemini-3-8-flash` | 872 | 847 | 121 | 123 | 117 | 98,940 | 21 |
| Gemini 3.8 Flash | medium | `gemini-3-8-flash-medium` | 759 | 680 | 130 | 119 | 121 | 82,068 | 15 |
| Gemini 3.8 Flash | low | `gemini-3-8-flash-low` | - | - | 126 | 121 | 106 | - | 4 |
| GPT-6 Luna | max | `gpt-6-luna` | 750 | 735 | 124 | 116 | 102 | 75,296 | 68 |
| GPT-6 Luna | xhigh | `gpt-6-luna-xhigh` | 446 | 441 | 118 | 114 | 100 | 43,893 | 16 |
| GPT-6 Luna | high | `gpt-6-luna-high` | 342 | 352 | 118 | 113 | 93 | 32,839 | 10 |
| GPT-6 Luna | medium | `gpt-6-luna-medium` | 214 | 208 | 115 | 116 | 95 | 19,823 | 5 |
| GPT-6 Luna | low | `gpt-6-luna-low` | 37 | 36 | 117 | 113 | 90 | 3,296 | 3 |
| GPT-6 Luna | none | `gpt-6-luna-non-reasoning` | 117 | 110 | 109 | 110 | 91 | 10,059 | 2 |
| Gemini 3.5 Flash-Lite | high | `gemini-3-5-flash-lite` | 103 | 94 | 392 | 411 | 322 | 30,301 | 5 |
| Claude Haiku 4.5 | - | `claude-4-5-haiku-reasoning` | 255 | 224 | 88 | 101 | 113 | 25,258 | 25 |

## Review

One round on the diff with the sources staged, same prompt to both reviewers (2026-11-17).

| Reviewer | Finding | Verdict | Fix |
|---|---|---|---|
| Codex | The column note and the time-frontier bullet still said the time estimate leaves out queueing. A4 measures output speed over "a request's full duration, from sending the request to receiving the final token", under concurrent load, so queueing on AA's requests is inside it | Confirmed | Both sentences now say the estimate leaves out tool execution and reflects AA's test load |
| Codex | `kimi.md` said K3.1 Pro "streams at ~31 tok/s". The v3 figure is an end-to-end rate that includes reasoning tokens and the first-token wait, not a decode rate | Confirmed | Reworded to "runs at ~31 output tok/s end to end (reasoning tokens and the first-token wait included)" |
| Gemini | No findings | | |

Both reviewers reported that all 60 rows, every range, rank and frontier statement, and every percentage in this record match the staged data. A second Codex round on the two fixes alone found nothing.

## Test

Two questions, each answered once with the revised skill and once with the skill as it stood before this change (Claude Sonnet 5.5, no web): picking the model with the shortest generation time at 54 or more index points, and refreshing a speed column from the AA API in December. Checks passed: 15 of 15 with the revised skill, 5 of 15 with the earlier one. The earlier skill's misses were the figures this change replaces (it gave Fable 5.2 `medium` as 501 s at 75 tok/s where AA now reads 406 s and 106) and the method difference between the two speed measures. Mean tokens per run: 96K for both. The test ran before the two review fixes.

One incident during the edit: the apply script opened `gemini.md` for writing before reading it and emptied the file. It was restored from the copy staged for that afternoon's review, which the session log shows was taken after the last edit to the file.

## Not re-read in this round

- The sub-benchmark paragraph, Arena, GDPx and BullshitBench.
- AA's wording of the time-per-task definition that the column note quotes. It is not on the model pages fetched here, so the quotation stays as it was.
- Time to first answer token for models other than the four named above.
