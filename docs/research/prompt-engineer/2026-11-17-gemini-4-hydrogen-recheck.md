# Gemini 4 Hydrogen re-check and Artificial Analysis pull (2026-11-17)

Record for the change to `skills/prompt-engineer/references/gemini.md` and `model-selection.md` made on this date. Hydrogen itself entered the skill on 2026-11-13 (commit `7e5c861`); this round re-read Google's pages five days after launch and re-pulled Artificial Analysis (AA).

## Sources read (all fetched 2026-11-17)

Google, Gemini API (AI Studio docs; `aistudio.google.com/docs/<page>.md` returns markdown):

| Id | Page |
|---|---|
| G1 | Release notes, https://ai.google.dev/gemini-api/docs/changelog (newest entry: Nov 12, Hydrogen GA) |
| G2 | What's new in Gemini 4 Hydrogen, https://ai.google.dev/gemini-api/docs/whats-new-gemini-4-hydrogen |
| G3 | Hydrogen model page, https://ai.google.dev/gemini-api/docs/models/gemini-4-hydrogen |
| G4 | Context caching, https://ai.google.dev/gemini-api/docs/caching |
| G5 | Thinking guide (stateless mode), https://ai.google.dev/gemini-api/docs/thinking |
| G6 | Pricing, https://ai.google.dev/gemini-api/docs/pricing |
| G7 | Deprecations, https://ai.google.dev/gemini-api/docs/deprecations |
| G8 | Thought signatures, https://ai.google.dev/gemini-api/docs/thought-signatures |

Google DeepMind model cards:

| Id | Page |
|---|---|
| D1 | Hydrogen, https://deepmind.google/models/model-cards/gemini-4-hydrogen/ |
| D2 | Carbon, https://deepmind.google/models/model-cards/gemini-4-carbon/ |
| D3 | Argon, https://deepmind.google/models/model-cards/gemini-4-argon/ |

Google Cloud (Vertex AI, now Gemini Enterprise Agent Platform):

| Id | Page |
|---|---|
| V1 | Developer's guide to Gemini 4 Hydrogen, https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-hydrogen |
| V2 | Hydrogen model page, https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-hydrogen |
| V3 | Context caching overview, https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/context-cache/context-cache-overview |
| V4 | Developer's guide to Gemini 4 Argon, https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-argon |
| V5 | Carbon and Argon model pages, `.../models/gemini/4-carbon`, `.../models/gemini/4-argon` |

Artificial Analysis:

| Id | Source |
|---|---|
| A1 | `GET https://artificialanalysis.ai/api/v2/language/models/free` (needs an API key; 742 rows, `intelligence_index_version` 5) |
| A2 | Model pages `artificialanalysis.ai/models/gemini-4-argon`, `-argon-medium`, `-hydrogen-high`, `-carbon` (embedded per-effort data) |
| A3 | API notes, https://artificialanalysis.ai/data-api/docs |

Other vendors, checked for releases since 2026-11-14: OpenAI API changelog (newest: Nov 16, a moderation classifier) and Anthropic release notes (newest: Nov 16, text watermark on older models). Nothing that changes the skill.

## What changed in the skill, and why

| Change | Source |
|---|---|
| Knowledge cutoff is March 2026 for Hydrogen and Carbon (the skill said "not published") | D1, D2 ("The knowledge cutoff for Gemini 4 Hydrogen is March 2026, though in some domains the model's knowledge may be less up to date"); V2 and the Carbon page in V5 list March 2026 |
| Hydrogen is "adapted from Gemini 4 Carbon" | D1 |
| Hydrogen refuses benign requests more often than 3.8 Flash (+5.57 points, "particularly for multimodal prompts") | D1, safety evaluation table |
| "may use more tokens ... at higher thinking levels"; "occasional slowness or timeout issues" | D1, known limitations |
| Out-of-range sampling values return 400 on Hydrogen; in-range values are ignored | G2, migration checklist |
| "better adapts when tool calls fail" | G2 |
| Stateless model switching: resend the earlier model's thought blocks; "The backend manages compatibility" | G5 |
| Long decode on Vertex needs `v1beta1`; changing model, system instruction or function declarations between continuation segments returns 400 | V1 and V4, known issues |
| The 2,050-token agent-loop caching rule is stated for Gemini 4 as a whole (the skill had it as Argon-only) | G4 |
| On Vertex, implicit caching needs 6,144 tokens on 3.8 Flash, 3.7 Flash, 3.1 Pro Preview and 3 Flash Preview, and 4,096 on Gemini 4; the Gemini API lists 4,096 for 3.8 Flash, 3.6 Flash and 3.1 Pro | V3 limits table; V1 (migration section); G4 |
| Durable caching: second implicit tier on Vertex, on by default for Gemini 4 and 3.8 Flash, 24-hour ceiling, can be disabled | V3 |
| From 2027-01-12, "Gemini 4 Hydrogen and later models" get cache control with TTL on Vertex; cache writes at 1.25x input | V2, V3. Not on V5 or any Gemini API page |
| SDK minimums for Go (1.77.0) and Java (1.80.0) | V1 |
| AA: Argon `medium` row (47.6, $4.31, 1,704 s, 83 tok/s, 15% hallucination) | A1, A2 |
| AA: Gemini 4 speed and time-per-task refreshed | A1 (`performance.median_output_tokens_per_second`), A2 (`intelligenceIndexTimePerTask`) |
| AA: `performance` returns null from 2026-12-10, replaced by `performance_v3` (means); v5.0.1; capability indexes; v1 API 410 from 2026-12-16 | A3 |
| Google's benchmark table against Claude Sonnet 5.5 and GPT-6.1 Terra | D1, evaluation results |

## AA numbers, Nov 13 against Nov 17

Scores, cost per task and hallucination rates did not move for any row in the skill's table. Speed did:

| Model, effort | tok/s Nov 13 | tok/s Nov 17 | Time / task Nov 13 | Time / task Nov 17 |
|---|---|---|---|---|
| Carbon high | 101 | 85 | 1,702 s | 1,913 s |
| Carbon medium | 94 | 78 | 1,451 s | 1,802 s |
| Carbon low | 93 | 76 | 1,484 s | 1,735 s |
| Hydrogen xhigh | 256 | 208 | 819 s | 893 s |
| Hydrogen high | 237 | 206 | 474 s | 473 s |
| Hydrogen medium | 249 | 205 | 223 s | 237 s |
| Hydrogen low | 255 | 246 | 79 s | 87 s |
| Argon high | 89 | 89 | 1,665 s | 1,760 s |

AA's time per task equals output tokens per task divided by the `performance_v3` mean speed (Hydrogen `high`: 84,978 / 473 s = 179.7 tok/s; v3 mean 179.65). At the time of this pull the table's tok/s column still used the `performance` median. It moved to the `performance_v3` mean three hours later (`2026-11-17-aa-speed-rebase.md`), which also replaced the speeds and times in the table above.

Other vendors' medians also moved since their pull dates (GPT-6.1 Terra `max` 112 to 90, GPT-6.1 Sol `xhigh` 67 to 58), but their rows were not re-pulled in this round.

## Review

One round on the diff with the saved sources staged, same prompt to both reviewers (2026-11-17).

| Reviewer | Finding | Verdict | Fix |
|---|---|---|---|
| Codex, Gemini | Carbon's prose kept the Nov 13 time range (1,451-1,702 s) | Confirmed | 1,735-1,913 s |
| Codex, Gemini | The first draft called Vertex's 6,144-token minimum for 3.8 Flash historical; V3's limits table still lists it for four Gemini 3 models (implicit caching only) | Confirmed | `gemini.md` states the minimum per platform; the `SKILL.md` caching cell is corrected |
| Codex | List-price projections doubled rounded costs ($10.96, $9.94) | Confirmed | Doubled from the unrounded costs: $10.97, $9.95 |

A second Codex round on the fixes alone found nothing. Both reviewers reported that every added quotation and every refreshed AA cell matched the saved sources. One error found on the author's own read before the round: "better adapts when tool calls fail" had been written as a comparison with 3.8 Flash, which G2 does not say.

## Test

Three tasks, each answered once with the revised skill and once with the skill at `origin/main` (Claude Sonnet 5.5, no web): a 3.8 Flash to Hydrogen migration of a document-intake agent, a caching plan for Hydrogen on Vertex, and a check of an Argon-at-defaults choice. Checks passed: 11 of 11 with the revised skill, 5 of 11 with the old one. The old skill's misses were the facts this change adds (cutoff, refusals, durable caching, the January 2027 cache control, Argon's `medium` hallucination rate). Mean tokens per run: 123K revised, 132K old.

## Checked and unchanged

- Hydrogen's price ($1.50 / $7.50, cached $0.075), thinking levels and default, limits, capabilities, and migration checklist (G2, G3, G6) match the Nov 13 text.
- No shutdown date for 3.8 Flash (G7).
- `prefix_mismatch_behavior` is still documented only on Vertex (G8 has no mention).
- AA intelligence, cost and hallucination for every row in the table.

## Left for later

- Done the same day, see `2026-11-17-aa-speed-rebase.md`: re-base the whole tok/s column to `performance_v3` in one pull, and re-pull time per task for the non-Gemini rows.
- Arena and GDPx positions were not re-read in this round.
- Hydrogen's Safety and Security Report is listed as "coming soon" on the model card.
