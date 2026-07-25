---
name: gslides-sync
description: Sync a .pptx file to an existing Google Slides presentation — pushes the pptx via Drive resumable upload (Google auto-converts), rewrites broken in-deck slide references and cross-presentation links into native pageObjectId links, resizes images that overflow the page, and optionally applies right-to-left paragraph direction for Hebrew/Arabic decks. Use when the user asks to sync/push/deploy a pptx to a Google Slides, update an existing Google Slides from a local .pptx file, refresh a stakeholder-facing slide deck whose source of truth is a locally-generated pptx, or maintain a Hebrew/Arabic deck whose text must render RTL.
allowed-tools: Read, Write, Bash, Edit, Glob, Grep
---

# gslides-sync

Pushes a local `.pptx` into an existing Google Slides via the Drive + Slides APIs, then patches things Google's converter gets wrong: broken in-deck slide links, cross-presentation references to sibling Slides files, and oversized images. Optional final pass applies RTL to every text shape for Hebrew/Arabic decks.

The script is a single Python file (`scripts/sync-gslides.py`) with no install step beyond the Google auth library. It authenticates via a service-account JSON (recommended) or gcloud ADC (fallback). Sister skill to [`gdoc-sync`](../gdoc-sync/SKILL.md) — same auth model, same five-step pipeline shape, swapped out for Slides.

## Quick start

```bash
scripts/sync-gslides.py <pptx-file> --pres-id <FILE_ID> --sa-key <service-account.json> \
  [--rtl] [--no-links] [--max-image-width 720] \
  [--cross-pres-map "other.pptx=OTHER_PRES_ID" ...]
```

**End-to-end example** (Hebrew deck, service account auth):

```bash
scripts/sync-gslides.py deck.pptx \
  --pres-id 1ImErdoIfgdebBjHvZ7YBbkUaeVLiswlPiA87ae44taI \
  --sa-key ~/.config/gdoc-sync/sa-key.json \
  --rtl
```

Output:

```
[1/5] Pushed pptx: deck.pptx (15,865,389 bytes)
[2/5] Fixed 0 in-deck slide-anchor links
[3/5] Skipped cross-pres link rewriting (no --cross-pres-map)
[4/5] Resized 0 oversized images (max width 720.0pt)
[5/5] Applied RTL to 14 text shapes
Done. https://docs.google.com/presentation/d/1ImErdo.../edit
```

## What it does (five-step pipeline)

| Step | What | Why |
|---|---|---|
| **1. Push** | Drive resumable upload: initiate with `PATCH /upload/drive/v3/files/{id}?uploadType=resumable`, then `PUT` the bytes to the returned Location. `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation`. | Drive's converter natively turns pptx into Slides format. Resumable (not simple media) because pptx files routinely exceed Google's 5 MB simple-upload guideline. |
| **2. Fix slide-anchor links** | Walks `presentations.get`, builds an `index → pageObjectId` map and a `slide-title-slug → pageObjectId` map, then rewrites text-run links whose URL matches broken patterns (`slide-3.xml`, `#slide5`) to use `link.pageObjectId`. | pptx slide-to-slide links sometimes survive conversion as `relativeLink` (fine, left alone) but sometimes come through as URL strings pointing at the literal pptx XML part name (broken). |
| **3. Fix cross-pres links** | For each `--cross-pres-map "name=PRES_ID"`, fetches the target's slide map, then rewrites text-run links containing `name` into a deep-link URL `https://docs.google.com/presentation/d/PRES_ID/edit#slide=id.{OBJECT_ID}`. Resolution: anchor-slug match → numeric slide index in anchor → numeric in link text → top of presentation. | Decks that reference a sibling pptx file (`see deck-b.pptx#section-2`) import as URL links pointing at the literal filename — broken. This rewrites them to deep-links into the synced sibling Slides. |
| **4. Resize images** | Finds image page-elements whose effective width (`size.width × transform.scaleX`) exceeds `--max-image-width`, then `updatePageElementTransform` with a uniform shrink factor; recomputes translate so the image's center stays fixed. | Defensive sweep — pptx normally sizes images correctly, but some converters scale up beyond the page bounds. Default is the presentation's actual page width (auto-detected from `pageSize`, e.g. 960pt for 16:9 widescreen) — full-bleed images are not touched. |
| **5. RTL (optional)** | `batchUpdate` with `updateParagraphStyle` setting `direction: RIGHT_TO_LEFT` across each text shape's full text range (`textRange.type: ALL`). Walks every shape and table cell with non-empty text. | Slides supports `paragraphStyle.direction`, but pptx → Slides conversion doesn't reliably translate RTL paragraph markers. Without this, Hebrew/Arabic shapes render LTR by default. |

## When to use this skill

| Scenario | Use this | Why |
|---|---|---|
| Existing Google Slides, updated by editing a local `.pptx` | Yes | That's the whole purpose |
| Hebrew / Arabic / RTL deck with real text shapes (not just images) | Yes, with `--rtl` | No other tool sets paragraph direction across a Slides deck |
| Image-only decks (each slide is a full-bleed AI-generated image) | Yes — but most steps will be 0/no-ops | Step 1 is the only one that matters; the rest are defensive sweeps |
| Two sibling Slides decks linking into each other | Yes, with `--cross-pres-map` | Provide `name=PRES_ID` for each sibling; cross-deck anchors get rewritten to deep-links |
| One-shot export of a pptx to a brand-new Slides | Yes, but create the empty Slides first and pass its ID | Script operates on `--pres-id`; doesn't create files |

## When NOT to use

| Scenario | Use instead |
|---|---|
| You want a local-only pptx render | Open in PowerPoint / Keynote / LibreOffice |
| Round-trip editing (edit in Slides, sync back to pptx) | This skill is one-way (pptx → Slides). Use Drive's `files.export` for the reverse direction. |
| Preserving comments/suggestions across syncs | You can't — the import is destructive to pending suggestions and orphans comments whose anchored shape changed. See [reference/gotchas.md](reference/gotchas.md). |
| Managing Slides permissions / sharing | Out of scope — use the Drive UI or `drive/v3/files/.../permissions`. |
| Decks with custom slide masters / animations / transitions you need preserved exactly | Drive's converter strips or downgrades these. No fix in code. |

## Auth

Two supported paths, identical to [gdoc-sync](../gdoc-sync/reference/auth-setup.md). Service account is strongly recommended.

| Path | Flag | Setup | When |
|---|---|---|---|
| **Service account (recommended)** | `--sa-key path/to/sa.json` | One-time: create SA in GCP, enable **Drive + Slides APIs** in that SA's project, share the target Slides with the SA's email as Editor | Default — most reliable |
| **gcloud ADC (fallback)** | *(no flag, uses gcloud)* | `gcloud auth application-default login` with Drive + Slides scopes — may be blocked by Google for sensitive scopes | Only if SA setup is unavailable; expect friction |

If you already use `gdoc-sync` with an SA, **the same SA works** — just enable the Slides API in its project and share the target Slides with the SA email. Full instructions: [reference/auth-setup.md](reference/auth-setup.md).

## Gotchas

The import is destructive, fonts get substituted, and custom layouts can be stripped. Read [reference/gotchas.md](reference/gotchas.md) **before** running against a deck you care about — especially the first time.

## Non-goals

- **One-way only by design.** Does not read back from the Slides. For two-way sync, use a different tool.
- **Does not create new Slides.** Takes `--pres-id` of an existing presentation.
- **Does not manage sharing/permissions.**
- **Does not preserve animations, transitions, embedded media fidelity beyond Drive's converter.**
- **Does not preserve comments or suggested edits** — the import overwrites the body, which wipes pending suggestions and orphans comments whose anchored shape changed.

## Script layout

```
gslides-sync/
├── SKILL.md                   # this file
├── README.md                  # human-facing overview (GitHub landing page)
├── scripts/
│   ├── sync-gslides.py        # the main script (Python, stdlib + google-auth optional)
│   └── README.md              # per-script invocation + flags
└── reference/
    ├── auth-setup.md          # service account setup, API enablement, Slides sharing
    └── gotchas.md             # known quirks, destructive behaviors, edge cases
```

## Dependencies

- **Python 3.9+**
- **Service account path:** `pip install google-auth` (for the `google.oauth2.service_account` module)
- **gcloud ADC path:** `gcloud` CLI available on `$PATH`
- No other deps — uses Python's `urllib` stdlib for HTTP.

## Related skills

- [`gdoc-sync`](../gdoc-sync/SKILL.md) — same pattern for markdown → Google Docs.
- [`presentation-generator`](../presentation-generator/SKILL.md) — produces the .pptx files this skill consumes (image-per-slide decks).
