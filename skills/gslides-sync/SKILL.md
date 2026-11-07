---
name: gslides-sync
description: Sync a .pptx file to an existing Google Slides presentation — pushes the pptx via Drive resumable upload (Google auto-converts), rewrites broken in-deck slide references and cross-presentation links into native pageObjectId links, resizes images that overflow the page, warns when the pptx's audio or narration videos will be lost and prints how to restore them, saves slide thumbnails or a PDF for visual QA, refuses to overwrite edits someone made in the deck since the last sync, and optionally applies right-to-left paragraph direction for Hebrew/Arabic decks. Use when the user asks to sync/push/deploy a pptx to Google Slides, update an existing Google Slides from a local .pptx file, refresh a stakeholder deck whose source of truth is a locally-generated pptx, or maintain a Hebrew/Arabic deck whose text must render RTL.
---

# gslides-sync

`scripts/sync-gslides.py` replaces a Google Slides deck with a local `.pptx`; Drive converts it. It then fixes what the converter gets wrong. It runs on a bare `python3`, and it finds the service-account key on its own: `--sa-key`, then `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC.

## Quick start

```bash
python3 scripts/sync-gslides.py deck.pptx --pres-id 1ImErdoIfgdebBjHvZ7YBbkUaeVLiswlPiA87ae44taI \
  --title "DEV delivery - Nov 2026" --thumbnails /tmp/deck-thumbs
```

```
[0/6] Deck unchanged since the last sync
[1/6] Pushed pptx: deck.pptx (15,865,389 bytes); renamed to 'DEV delivery - Nov 2026'; page 960x540pt
[2/6] Fixed 0 in-deck slide-anchor links
[3/6] Skipped cross-pres link rewriting (no --cross-pres-map)
[4/6] Resized 0 oversized images (max width 960pt)
[5/6] Skipped RTL (use --rtl to enable)
[6/6] Saved 14 slide thumbnails → /tmp/deck-thumbs/slide-NN.png
Done. https://docs.google.com/presentation/d/1ImErdo.../edit
```

`--pres-id` is the token in `docs.google.com/presentation/d/<ID>/edit`. The deck must already exist and be shared with the service account's email as Editor. A service account can't create files, so create the empty deck in the UI first. **Look at the thumbnails after every push.**

## The pipeline

| Step | What | Why |
|---|---|---|
| **0. Guard + audit** | Refuses (exit 3) if a person edited the deck since this script last synced it; `--force` overrides. Warns when the pptx has embedded audio or native charts | The push replaces the whole deck. Audio and charts don't survive the converter |
| **1. Push** | Drive resumable upload onto the deck ID (`--title` renames it). Reports the page size, and flags it when the size changed. If the deck had narration videos, it prints the command that puts them back | The pptx sets the page size (for example 720x405 → 960x540), which moves anything positioned for the old size; the push deletes every element added after the last import |
| **2. Slide links** | Rewrites `slide-3.xml` / `#slide5` / `#title-slug` URL links into `pageObjectId` links | Some pptx slide links survive conversion as broken URLs |
| **3. Cross-deck links** | With `--cross-pres-map "b.pptx=PRES_ID"`, rewrites `b.pptx#…` into `…/presentation/d/PRES_ID/edit#slide=id.X` | The converter keeps the local filename as the URL |
| **4. Images** | Shrinks images wider than `--max-image-width` (default: the page width), keeping each centered | A defensive sweep; full-bleed images are left alone |
| **5. RTL** | With `--rtl`, sets `RIGHT_TO_LEFT` on every text shape and table cell | The converter doesn't carry Hebrew/Arabic paragraph direction reliably |
| **6. QA** | `--thumbnails DIR` saves `slide-NN.png` per slide; `--export-pdf PATH` saves a PDF | A share link needs a Google sign-in; these let you check the result directly |

## Narrated decks

Google Slides drops a pptx's embedded audio on every import, and the Slides API can't insert audio. The narration for a Google Slides deck is one small autoplaying Drive video per slide, handled by the **narrating-pptx** skill (its Google Slides section, `scripts/gslides_narration.py`). The two skills split the work:

1. Push the **clean, audio-free** pptx with this skill. If you push the narrated pptx instead, the audit warns and the slides keep silent speaker icons.
2. Attach the narration with `gslides_narration.py insert`, then confirm it with `gslides_narration.py check`.
3. **After every later push, run `insert` again.** The push deletes the videos. This skill counts them before pushing, and afterwards prints the exact `insert`/`check` commands, with the Drive folder already filled in.

## Gotchas

The full list is in [reference/gotchas.md](reference/gotchas.md). The ones that bite most:

- **Every push wipes the deck,** including pending suggestions, comments on changed shapes, hand edits, and every element added through the API, such as narration videos. Re-run `gslides_narration.py insert` after each push. Each push is an entry in File → Version history.
- **Charts and embedded video become static images,** and chart category labels can disappear. Render charts as pictures in the pptx you push to Google.
- **Fonts outside Google Fonts fall back to Arial,** which changes line breaks. Use Google Fonts in the source pptx.
- **Decks over 100 MB fail to convert.** Compress the images or split the deck.

## When to use / not

| Scenario | Use |
|---|---|
| A Slides deck whose source of truth is a local `.pptx` | This skill |
| Image-only decks (one full-bleed image per slide) | This skill; steps 2-5 do nothing |
| A narrated deck that must play in Google Slides | This skill for the push, then narrating-pptx's `gslides_narration.py` |
| Hebrew / Arabic decks with real text | This skill with `--rtl` |
| Editing in Slides and syncing back to pptx | Not this: it is one-way. Use Drive `files.export` |
| Keeping custom masters, animations or transitions exact | Not possible: the converter flattens them |

## Files

```
gslides-sync/
├── SKILL.md                    # this file
├── README.md                   # GitHub landing page
├── scripts/sync-gslides.py     # the script (stdlib only; google-auth used when present)
├── scripts/README.md           # flags and exit codes
└── reference/
    ├── auth-setup.md           # service account, API enablement, sharing, ADC fallback
    └── gotchas.md              # destructive behaviors, converter losses, limits
```

## Related skills

- [`gdoc-sync`](../gdoc-sync/SKILL.md): the same pattern for markdown → Google Docs, with the same key.
- [`presentation-generator`](../presentation-generator/SKILL.md) produces image-per-slide decks this skill consumes.
- [`narrating-pptx`](../narrating-pptx/SKILL.md) builds the narration, and its Google Slides section attaches it to the deck this skill pushed. [`self-presenting-decks`](../self-presenting-decks/SKILL.md) runs the whole deck → narration → video chain.
