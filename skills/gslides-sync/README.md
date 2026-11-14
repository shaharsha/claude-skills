# gslides-sync

Sync a local `.pptx` to an existing Google Slides presentation. Broken slide links are rewritten, and oversized images are shrunk to the page. It warns when narration will be lost, and prints how to restore it. Optional RTL for Hebrew and Arabic decks. A guard stops it from overwriting edits someone made in the deck in the meantime. Works as a standalone CLI and as an agent skill.

Part of [shaharsha/claude-skills](../..). MIT.

Sister skill to [gdoc-sync](../gdoc-sync): the same pattern, for Slides.

---

## Why

Drive will convert a pptx into Google Slides, but these break:

1. **In-deck slide links** sometimes arrive as URLs to the literal pptx part name (`slide-3.xml`), not as native slide links.
2. **Cross-deck links like `other.pptx#section-2`** point at a local filename.
3. **Images can overflow the page.**
4. **Hebrew and Arabic** need `RIGHT_TO_LEFT` applied per text shape.
5. **Narration is gone.** Embedded pptx audio is dropped on import, and every push deletes narration videos attached since the last one. This skill warns, and prints the command that restores them with [narrating-pptx](../narrating-pptx).
6. **The push replaces the whole deck.** A colleague's edit made in Slides since your last push is silently lost.

`gslides-sync` is one Python script that pushes the pptx and fixes all six.

## What it does

```
 guard + audit ──▶ push .pptx (+ rename) ──▶ fix slide links ──▶ fix cross-deck links ──▶ resize images
                                                                                          │
                              thumbnails / PDF (opt) ◀── RTL (opt) ◀─────────────────────┘
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install gslides-sync@shaharsha-skills
```

That installs only this skill. For the whole `documents-and-decks` bundle, run `/plugin install documents-and-decks@shaharsha-skills` instead.

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/gslides-sync" ~/.claude/skills/gslides-sync
```

No Python packages needed: the script uses `google-auth` if it is installed, and otherwise signs the service-account token with `cryptography` or the `openssl` CLI.

## Quick start

```bash
python3 scripts/sync-gslides.py path/to/your.pptx --pres-id <GOOGLE_SLIDES_ID> \
  [--title "Name in Drive"] [--rtl] [--cross-pres-map "other.pptx=OTHER_PRES_ID"] \
  [--thumbnails /tmp/thumbs]
```

The presentation ID is the long string in `https://docs.google.com/presentation/d/` **`1ImErdo...4taI`** `/edit`.

## Setup (one-time)

Step by step: [`reference/auth-setup.md`](reference/auth-setup.md). In short:

1. In a Google Cloud project, enable the **Google Drive API** and the **Google Slides API**.
2. Create a service account, download its JSON key, and save it as `~/.config/gdoc-sync/sa-key.json`. Alternatively, set `$GOOGLE_SA_KEY`, or pass `--sa-key`.
3. **Share the target deck with the service account's email as Editor.** A service account can't create files, so create the deck in the UI first.

The same key serves [gdoc-sync](../gdoc-sync) and [gsheets](../gsheets).

## Narrated decks

Push the audio-free pptx with this skill, then attach one autoplaying Drive video per slide with [narrating-pptx](../narrating-pptx)'s `scripts/gslides_narration.py` (`insert`, then `check`). Run `insert` again after every push: when the deck had narration videos, this skill prints the exact command.

## Flags

| Flag | Default | Description |
|---|---|---|
| `--pres-id <id>` | *required* | Google Slides file ID |
| `--sa-key <path>` | `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC | Service-account JSON key |
| `--title <name>` | — | Also rename the deck in Drive |
| `--rtl` | off | `RIGHT_TO_LEFT` on every text shape |
| `--no-links` | off | Skip slide-link and cross-deck rewriting |
| `--max-image-width <pt>` | page width | Shrink wider images, keeping the center; `0` skips |
| `--cross-pres-map NAME=ID` | — | Repeatable |
| `--thumbnails <dir>` / `--export-pdf <path>` | — | QA renders after the sync |
| `--force` | off | Push even if a person edited the deck since the last sync |

Full reference: [`scripts/README.md`](scripts/README.md).

## Gotchas

- **The push replaces the deck,** including pending suggestions, hand edits, and every element added through the API. The guard refuses when someone edited the deck since the last sync. Every push is in File → Version history.
- **Audio is dropped, and charts and video become images.** Chart labels can vanish, so render charts as pictures.
- **The pptx sets the page size,** which can change the deck from 720x405 to 960x540; the push reports it.
- **Fonts outside Google Fonts fall back to Arial.**
- **Decks over 100 MB fail to convert.**

Full list: [`reference/gotchas.md`](reference/gotchas.md).

## Non-goals

- Creating decks (it operates on an existing deck ID).
- Reading back from Slides (it is one-way, `pptx → Slides`).
- Preserving comments, suggestions, animations or custom masters across syncs.
- Managing sharing.

## Dependencies

- Python 3.9+, stdlib only.
- For signing, whichever is present: `google-auth` (+ `requests`), `cryptography`, or the `openssl` CLI.
- The `gcloud` CLI, only for the ADC fallback.

## License

MIT — see [LICENSE](../../LICENSE).

## Related skills

- [gdoc-sync](../gdoc-sync): Markdown → Google Docs, with the same auth model.
- [gsheets](../gsheets): the Sheets sibling.
- [presentation-generator](../presentation-generator) produces the `.pptx` files this skill consumes.
- [narrating-pptx](../narrating-pptx): narration, including the Google Slides videos. [self-presenting-decks](../self-presenting-decks): the whole deck → narration → video chain.
