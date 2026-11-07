# gdoc-sync

Sync a local Markdown file to an existing Google Doc. Internal anchor links work, cross-doc links work, images are sized to the page, and the tight paragraph styling survives every re-sync. Optional RTL for Hebrew and Arabic. A guard stops it from overwriting edits someone made in the Doc in the meantime. Works as a standalone CLI and as an agent skill.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why

Google Docs imports markdown natively, which handles most of the conversion. It falls over on these:

1. **`[see §5](#section-5)`** imports as a URL link to the literal string `#section-5`, which goes nowhere. It should be a native heading link.
2. **`[see the plan](other.md#anchor)`** links to a local filename. It should deep-link into the sibling Doc.
3. **Inline images** arrive at their source resolution, often 1500+ pt wide, which breaks the layout.
4. **Styling resets on every push.** Line spacing returns to 115, empty paragraphs appear between blocks, and any tightening you did by hand is gone.
5. **Paragraph direction** is never set, so Hebrew and Arabic render LTR.
6. **The push replaces the whole body.** A colleague's edit made in the Doc since your last push is silently lost.

`gdoc-sync` is one Python script that pushes the markdown and fixes all six.

## What it does

```
 guard ──▶ push .md (+ rename) ──▶ fix #anchors ──▶ fix cross-doc links ──▶ resize images
                                                                             │
                     export PDF (opt) ◀── restyle (opt) ◀── RTL (opt) ◀───────┘
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install documents-and-decks@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/gdoc-sync" ~/.claude/skills/gdoc-sync
```

No Python packages needed: the script uses `google-auth` if it is installed, and otherwise signs the service-account token with `cryptography` or the `openssl` CLI.

## Quick start

```bash
python3 scripts/sync-gdoc.py path/to/your.md --doc-id <GOOGLE_DOC_ID> \
  [--title "Name in Drive"] [--rtl] [--cross-doc-map "other.md=OTHER_DOC_ID"] \
  [--line-spacing 100 --space-below 3 --heading-space-above 8 --drop-empty-paragraphs] \
  [--export-pdf out.pdf]
```

The Doc ID is the long string in `https://docs.google.com/document/d/` **`1lSsp...FDU-BEE`** `/edit`.

## Setup (one-time)

Use a service account. It is stable, it works headless, and it never hits the "This app is blocked" consent screen. Step by step: [`reference/auth-setup.md`](reference/auth-setup.md). In short:

1. In a Google Cloud project, enable the **Google Drive API** and the **Google Docs API**.
2. Create a service account, download its JSON key, and save it as `~/.config/gdoc-sync/sa-key.json`. Alternatively, set `$GOOGLE_SA_KEY`, or pass `--sa-key`.
3. **Share each target Doc with the service account's email as Editor.** A service account can't create files, so create the Doc in the UI first.

The same key and setup serve the sister skills [gsheets](../gsheets) and [gslides-sync](../gslides-sync).

## Flags

| Flag | Default | Description |
|---|---|---|
| `--doc-id <id>` | *required* | Google Doc file ID |
| `--sa-key <path>` | `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC | Service-account JSON key |
| `--title <name>` | — | Also rename the file in Drive |
| `--rtl` | off | `direction: RIGHT_TO_LEFT` on every paragraph |
| `--no-links` | off | Skip anchor and cross-doc rewriting |
| `--max-image-width <pt>` | `300` | Shrink wider images; `0` skips |
| `--cross-doc-map NAME=DOC_ID` | — | Repeatable; deep-links `NAME#anchor` into the sibling Doc |
| `--line-spacing`, `--space-above`, `--space-below`, `--heading-space-above`, `--heading-space-below`, `--font-size` | — | Styling re-applied after every push |
| `--drop-empty-paragraphs` | off | Remove the empty paragraphs the import inserts |
| `--export-pdf <path>` | — | Google's render, for a visual check |
| `--force` | off | Push even if a person edited the Doc since the last sync, or it has several tabs |

## Gotchas

- **The push replaces the body.** Pending suggestions are wiped and comments on changed text are orphaned. The guard refuses when someone edited the Doc since the last sync. Every push is in File → Version history.
- **One tab only.** A markdown push writes a single tab, so the script refuses a Doc that has several.
- **Images need public URLs.** Relative paths and `data:` URIs are dropped by the import.
- **Keep the sync command in a script** next to the markdown. The styling flags must run on every sync, because the push resets them.

Full list: [`reference/gotchas.md`](reference/gotchas.md).

## Non-goals

- Creating Docs (it operates on an existing Doc ID).
- Reading back from the Doc (it is one-way, `md → Doc`). For the reverse, use Drive's `text/markdown` export.
- Preserving comments or suggestions across syncs.
- Managing sharing.

## Dependencies

- Python 3.9+, stdlib only.
- For signing, whichever is present: `google-auth` (+ `requests`), `cryptography`, or the `openssl` CLI.
- The `gcloud` CLI, only for the ADC fallback.
