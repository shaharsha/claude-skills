# gslides-sync

Sync a local `.pptx` file to an existing Google Slides presentation — with broken slide-anchor links rewritten, oversized images shrunk to fit the page, and optional RTL paragraph direction for Hebrew/Arabic decks. Works as a standalone CLI and as an agent skill.

Part of [shaharsha/claude-skills](../..). MIT.

Sister skill to [gdoc-sync](../gdoc-sync) — same pattern, swapped for Slides.

---

## Why

Google Slides has a native pptx converter — Drive will happily turn a pptx into a Google Slides file. But four things break:

1. **In-deck slide-to-slide links** sometimes survive conversion as URL strings pointing at the literal pptx XML part name (`slide-3.xml`), not as native `link.pageObjectId` references. They show as broken links in the Slides UI.
2. **Cross-presentation links like `[t](other.pptx#section-2)`** import as URL links pointing at a literal pptx filename (broken). They should deep-link into the sibling Slides at the matching slide.
3. **Images can overflow the page** if the pptx had off-spec sizes or the converter scaled up.
4. **Paragraph direction is not always preserved.** Hebrew / Arabic decks need `direction: RIGHT_TO_LEFT` applied per text shape after import.

`gslides-sync` is a single Python script that does the import **plus** all four post-processing passes, so the resulting Slides actually looks like your pptx intended.

## What it does

```
┌──────────────────────────────────────────────────────────────────────────┐
│  local .pptx ──push──▶ Google Slides ──fix slide refs──▶ resize images   │
│                                                              │            │
│                                                              ▼            │
│                                  apply RTL (opt) ◀──── fix cross-pres    │
└──────────────────────────────────────────────────────────────────────────┘
```

One command, three to four API calls, a deck that works.

## Quick start

```bash
# Install the one optional dependency (only needed for service-account auth)
pip install google-auth

# Clone this repo
cd skills/gslides-sync

# Run
scripts/sync-gslides.py path/to/your.pptx \
  --pres-id <GOOGLE_SLIDES_ID> \
  --sa-key path/to/service-account.json \
  [--rtl] [--no-links] [--max-image-width 720] \
  [--cross-pres-map "other.pptx=OTHER_PRES_ID" ...]
```

The presentation ID is the long string in the URL: `https://docs.google.com/presentation/d/` **`1ImErdo...4taI`** `/edit`.

## Setup (one-time)

You need a way to authenticate against Google's Drive + Slides APIs. The recommended path is a service account — it's stable, scriptable, and doesn't hit Google's OAuth "this app is blocked" friction.

See [`reference/auth-setup.md`](reference/auth-setup.md) for the step-by-step. Summary:

1. Create (or reuse) a Google Cloud project.
2. Enable **Google Drive API** and **Google Slides API** in that project.
3. Create a service account, download its JSON key.
4. **Share the target Google Slides with the service account's email as Editor.**
5. Pass `--sa-key path/to/key.json` when you run the script.

If you already use `gdoc-sync` with an SA, **the same SA works** — just enable the Slides API in its project and share the target Slides.

## Flags

| Flag | Default | Description |
|---|---|---|
| `--pres-id <id>` | *required* | Google Slides file ID |
| `--sa-key <path>` | *none* | Path to a service-account JSON. If omitted, falls back to gcloud ADC. |
| `--rtl` | off | Apply `direction: RIGHT_TO_LEFT` across every text shape (for Hebrew/Arabic) |
| `--no-links` | off | Skip slide-anchor + cross-pres rewriting (steps 2 and 3) |
| `--max-image-width <pt>` | *page width* | Max effective image width in points. Default is auto-detected from the presentation's `pageSize` (e.g. 960pt for the standard 16:9 widescreen) — full-bleed images are left alone. Larger images are scaled down preserving aspect ratio, with the center kept fixed. Set `0` to skip. |
| `--cross-pres-map "name=ID"` | repeatable | Map a pptx filename fragment to a sibling Slides ID; matching links get rewritten as deep-links. |

Typical invocations:

```bash
# Plain English deck
scripts/sync-gslides.py deck.pptx --pres-id $PRES --sa-key $SA

# Hebrew deck
scripts/sync-gslides.py deck.pptx --pres-id $PRES --sa-key $SA --rtl

# Image-only deck — skip the (no-op) link rewriting and don't fight on image sizes
scripts/sync-gslides.py deck.pptx --pres-id $PRES --sa-key $SA --no-links --max-image-width 0

# Two sibling decks
scripts/sync-gslides.py deck-a.pptx --pres-id $A --sa-key $SA \
  --cross-pres-map "deck-b.pptx=$B"
```

## How it works

1. **`PATCH /upload/drive/v3/files/{id}?uploadType=resumable`** to initiate, then **`PUT`** the bytes to the returned `Location`. `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation`. Drive converts natively.
2. **`GET /v1/presentations/{id}`** to walk the resulting Slides structure. Build `index → pageObjectId` and `slug → pageObjectId` maps; rewrite text-run links matching broken patterns to use `link.pageObjectId`.
3. **For each `--cross-pres-map`**, `GET` the target Slides, build its slug map, then rewrite text-run links containing the source pptx name to deep-link URLs into the sibling.
4. **Find image page-elements** whose effective width exceeds `--max-image-width`; `updatePageElementTransform` with a uniform shrink factor.
5. *(Optional)* **`batchUpdate` with `updateParagraphStyle`** setting `direction: RIGHT_TO_LEFT` across each text shape's full text range. Walks shapes and table cells.

Resumable upload (not simple media) is used because pptx files routinely exceed Google's 5 MB simple-upload guideline.

## Gotchas

- **The pptx import is destructive.** It wipes pending suggested edits and orphans comments whose anchored shape no longer matches. **Make a copy of your Slides before the first sync** — via Drive's "Make a copy" or `POST /drive/v3/files/{id}/copy`.
- **Fonts get substituted.** Non-Google fonts (Hebrew Noto Sans, custom corporate fonts) downgrade to Arial-equivalents. Use Google-hosted fonts in your pptx source if fidelity matters.
- **Custom slide masters / layouts may be stripped.** Drive's converter normalizes layouts. If you depend on a custom master, expect drift.
- **Animations and transitions** are converted with limited fidelity. Complex animation timelines and embedded media (video / OLE objects) are lost or simplified.
- **Slides has a 100 MB conversion ceiling.** Decks above this size will fail conversion silently. Compress images in the pptx before syncing.

Full list: [`reference/gotchas.md`](reference/gotchas.md).

## Non-goals

- Does not create new Google Slides (operate on existing ones by ID).
- Does not read back from the Slides — one-way only (`pptx → Slides`).
- Does not preserve comments or suggestions across syncs.
- Does not manage permissions or sharing.
- Does not guarantee fidelity of animations, transitions, or embedded media.

## Dependencies

- Python 3.9+
- **Service account path:** `google-auth` (install via `pip install google-auth`).
- **gcloud ADC path:** `gcloud` CLI on `$PATH`.

No other dependencies — uses Python's `urllib` stdlib for all HTTP.

## License

MIT — see [LICENSE](../../LICENSE).

## Contributing

Issues and PRs welcome. The script is intentionally single-file and stdlib-leaning — please keep it that way.

## Related skills

- [gdoc-sync](../gdoc-sync) — Markdown → Google Docs. Same auth model.
- [gsheets](../gsheets) — the Sheets-shaped sibling.
- [presentation-generator](../presentation-generator) — produces the `.pptx` files this consumes.
