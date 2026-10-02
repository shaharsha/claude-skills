# Pricing reference (October 2026)

Per-image cost matters because iteration discipline depends on it. List prices; date-sensitive items are marked.

## OpenAI: tokens, not a price list

GPT Image 2, 2.5 Flare and 2.5 Sunburst share the same token rates:

| Token type | Standard | Batch API |
|---|---|---|
| Image output | $30 / 1M | $15 / 1M |
| Image input (references) | $8 / 1M | $4 / 1M |
| Text input | $5 / 1M | $2.50 / 1M |

Cached input ($2/1M image, $1.25/1M text) applies only through the Responses API image tool. **Per-image cost = output tokens × rate, and output tokens depend on model, quality and size** — OpenAI publishes no per-image table for 2.5 and its calculator doesn't cover 2.5. `scripts/openai-image.sh` prints the real cost of every call from the response's `usage`; sum those lines.

Measured 2026-10-02 (1024×1536 unless noted):

| Model + quality | Output tokens | Cost | Latency |
|---|---|---|---|
| Flare `medium` (`--draft`) | 343 | ≈ $0.010 | ~15 s |
| Flare `medium` 1024×1024 | 439 | ≈ $0.013 | ~10 s |
| Sunburst `high` | 1,372 | ≈ $0.041 | ~35 s |
| Sunburst `max` | 5,488 | ≈ $0.165 | ~87 s |
| Sunburst `max` edit with 1 reference (draft promotion) | 5,488 | ≈ $0.178 | ~85 s |
| Sunburst `high`, transparent, 1024×1024 | 1,756 | ≈ $0.053 | ~35 s |

Third-party reference points: Artificial Analysis lists Sunburst/Flare at `max` at ~$0.21 per 1024×1024 (the same as gpt-image-2 `high`). The token ladder at 2048×1152 is low 157 · medium 367 · high 1,413 · xhigh 2,511 · max 5,650 — larger sizes scale up roughly with pixel count.

## Gemini: per image

| Model | 512 | 1K | 2K | 4K |
|---|---|---|---|---|
| `gemini-3.1-flash-lite-image` | — | $0.034 | — | — |
| `gemini-3.1-flash-image` | $0.045 | $0.067 | $0.101 | $0.151 |
| `gemini-3-pro-image` | — | $0.134 | $0.134 | $0.24 |

Batch halves these. `gemini-2.5-flash-image` reached its shutdown date 2026-10-02; Imagen models shut down 2026-08-17.

## Common scenarios — total cost calculator

### Logo project (explore → promote)

| Step | Calls | Model | Cost each | Subtotal |
|---|---|---|---|---|
| Explore directions | 6 | Flare `--draft` 1024² | $0.013 | $0.08 |
| Second round on the favourite | 3 | Flare `--draft` | $0.013 | $0.04 |
| Promote the pick | 1-2 | Sunburst `max` edit | ~$0.20 | $0.20-0.40 |
| Transparent version | 1 | Sunburst `max` edit, `--background transparent` | ~$0.20 | $0.20 |
| **Total** | | | | **≈ $0.50-0.75** |

### UI mockup (5 mobile screens)

| Step | Calls | Model | Subtotal |
|---|---|---|---|
| Layout drafts | 5-10 | Flare `--draft` 1024×1536 | $0.05-0.10 |
| Finals | 5 | Sunburst `max` 1024×1536 | ~$0.85 |
| Fix-up edits | 2-3 | Sunburst `max` edit | ~$0.55 |
| **Total** | | | **≈ $1.50** |

### Marketing hero set (3 images, 2048×1152)

| Step | Calls | Model | Subtotal |
|---|---|---|---|
| Drafts | 6 | Flare `--draft` | ~$0.10 |
| Finals | 3 | Sunburst `max` (~5,650 tokens each) | ~$0.51 |
| **Total** | | | **≈ $0.60** |

### Product catalog cutouts (10 products, transparent)

10 × Sunburst `max` 1024² with `--background transparent` ≈ $2.10, plus a few re-dos. No rembg step.

### Portrait / founder headshot (photoreal)

2 × Sunburst `max` + 2 × Gemini Pro 4K for a side-by-side ≈ $0.90.

## Batch API discounts

- **Gemini Batch API:** ≈ 50% off, 24-hour turnaround. Use for non-interactive bulk generation.
- **OpenAI Batch API:** 50% off, 24-hour turnaround.

For interactive design work (the main use of this skill), batch APIs are useless because you need to see results to iterate. They matter for one-shot bulk jobs.

## Cost discipline rules

1. **Explore on Flare `--draft`.** ~1¢ a call: 30 explorations cost ~$0.40, against ~$6 at Sunburst `max`.
2. **Promote, don't re-roll.** One Sunburst `max` edit of the chosen draft (~$0.18) keeps the look the user picked; re-running the prompt at `max` buys a different image.
3. **Don't go above 2560×1440 until the final.** Output tokens scale with pixels, and above 2560×1440 is "experimental".
4. **Don't iterate >3 times on the same image.** Drift compounds, cost compounds. Rewrite the prompt from scratch.
5. **Transparent PNGs are native on 2.5** — no extra step or cost. rembg stays the free option for Gemini outputs or existing images.
6. **For 24+ assets in the same style, prefer grid-based generation** on Sunburst `max` (6-8 per grid) — one call locks the style across cells better than independent calls.
7. **Never `quality=auto`** — identical calls land on different token budgets, so cost becomes unpredictable.

## Sanity-check budgets per asset type

| Asset | Reasonable budget | Red flag if you exceed |
|---|---|---|
| Single logo, exploration to final | $1-3 | $5 |
| Icon set of 12-24 | $1-3 | $5 |
| 5-screen UI mockup (mobile) | $1-2 | $4 |
| 1-screen hi-fi dashboard | $0.50-1 | $2 |
| 3-image hero set for landing | $1-2 | $3 |
| 10-image product catalog (objects) | $2-4 | $6 |
| 10-image product catalog (people) | $3-5 | $8 |
| Portrait / founder headshot | $0.50-1 | $2 |

If you're approaching the red flag, pause and ask the user whether to keep going or pivot strategy.
