# gdoc-sync — a Claude Code skill

Sync a local Markdown file to an existing Google Doc — with working internal anchor links, auto-resized images, and optional RTL paragraph direction for Hebrew/Arabic docs. Packaged as both a standalone CLI and a [Claude Code](https://claude.com/claude-code) skill.

---

## Why

Google Docs has a native "import from markdown" endpoint — great for the first 80% of the conversion — but it falls over on four things:

1. **Internal anchor links like `[see §5](#section-5)`** get imported as *URL links* pointing at the literal string `#section-5` (broken). They should be native heading links.
2. **Cross-doc links like `[see §5 in plan](other.md#anchor)`** import as URL links pointing at a literal markdown filename (broken). They should deep-link into the sibling Doc.
3. **Inline images** get imported at their source resolution (often 1500+ pt wide), which destroys page layout.
4. **Paragraph direction** is never set. Hebrew / Arabic markdown content renders LTR — every paragraph needs `direction: RIGHT_TO_LEFT` applied after import.

`gdoc-sync` is a single Python script that does the import **plus** all three post-processing passes, so the resulting Doc actually looks like your markdown intended.

## What it does

```
┌─────────────────────────────────────────────────────────────────┐
│  local .md  ──push──▶  Google Doc  ──fix anchors──▶  resize imgs│
│                                                         │        │
│                                                         ▼        │
│                                                  apply RTL (opt) │
└─────────────────────────────────────────────────────────────────┘
```

One command, three API calls, a doc that works.

## Quick start

```bash
# Install the one optional dependency (only needed for service-account auth)
pip install google-auth

# Clone this repo
git clone https://github.com/shaharsha/claude-skill-gdoc-sync.git
cd claude-skill-gdoc-sync

# Run
scripts/sync-gdoc.py path/to/your.md \
  --doc-id <GOOGLE_DOC_ID> \
  --sa-key path/to/service-account.json \
  [--rtl] [--no-links] [--max-image-width 300] \
  [--cross-doc-map "other.md=OTHER_DOC_ID" ...]
```

The doc ID is the long string in the URL: `https://docs.google.com/document/d/` **`1lSsp...FDU-BEE`** `/edit`.

## Setup (one-time)

You need a way to authenticate against Google's Drive + Docs APIs. The recommended path is a service account — it's stable, scriptable, and doesn't hit Google's OAuth "this app is blocked" friction.

See [`reference/auth-setup.md`](reference/auth-setup.md) for the step-by-step. Summary:

1. Create (or reuse) a Google Cloud project.
2. Enable **Google Drive API** and **Google Docs API** in that project.
3. Create a service account, download its JSON key.
4. **Share the target Google Doc with the service account's email as Editor.**
5. Pass `--sa-key path/to/key.json` when you run the script.

Alternative: gcloud user ADC via `gcloud auth application-default login`. Works sometimes, gets blocked by Google for sensitive scopes on the default gcloud client. See [auth-setup.md](reference/auth-setup.md) for the workaround.

## Flags

| Flag | Default | Description |
|---|---|---|
| `--doc-id <id>` | *required* | Google Doc file ID (the long string in the URL) |
| `--sa-key <path>` | *none* | Path to a service-account JSON. If omitted, falls back to gcloud ADC. |
| `--rtl` | off | Apply `direction: RIGHT_TO_LEFT` across every body paragraph (for Hebrew/Arabic) |
| `--no-links` | off | Skip the anchor-link rewrite pass (step 2) |
| `--max-image-width <pt>` | `300` | Max inline image width in points; images wider than this are resized preserving aspect ratio. Set `0` to skip image resizing. |

Typical invocations:

```bash
# English doc with cross-references
scripts/sync-gdoc.py plan.md --doc-id $DOC --sa-key $SA

# Hebrew doc
scripts/sync-gdoc.py plan.md --doc-id $DOC --sa-key $SA --rtl

# No internal cross-references, just a one-shot push
scripts/sync-gdoc.py plan.md --doc-id $DOC --sa-key $SA --no-links

# Let images stay at their natural size
scripts/sync-gdoc.py plan.md --doc-id $DOC --sa-key $SA --max-image-width 0
```

## How it works

Four HTTP operations against `docs.googleapis.com` and `www.googleapis.com`:

1. **`PATCH /upload/drive/v3/files/{id}?uploadType=media`** with `Content-Type: text/markdown`. Google converts the markdown natively — headings, tables, inline images, code blocks all land.
2. **`GET /v1/documents/{id}`** to walk the resulting Doc structure. The script builds a `section-number → headingId` map from heading paragraphs, then rewrites every text run whose `link.url` starts with `#` to use `link.headingId` instead.
3. **Find oversized inline images** (width > `--max-image-width`), `deleteContentRange` + `insertInlineImage` with explicit `objectSize` — preserves aspect ratio.
4. *(Optional)* **`batchUpdate` with `updateParagraphStyle`** setting `direction: RIGHT_TO_LEFT` across the whole body range.

Table cells get walked recursively — `body.content` doesn't descend into `table.tableRows[].tableCells[].content` automatically.

## Gotchas

- **The markdown import is destructive.** It wipes pending suggested edits and orphans comments whose anchored text no longer matches. **Make a copy of your Doc before the first sync on a doc you care about** — via Drive's "Make a copy" or `POST /drive/v3/files/{id}/copy`.
- **Anchor resolution is regex-based on leading section numbers** (e.g. `5.3.1`, `11.4`). If the matching heading number isn't present, the rewrite falls back to progressively shorter prefixes (`5.3.1` → `5.3` → `5`). If you have heading styles without numeric prefixes, add `--no-links` or adjust the regex in the script.
- **RTL applies to every body paragraph.** If you need mixed direction, apply RTL on the whole doc and let Google's bidi algorithm handle individual LTR runs inside paragraphs — it usually does the right thing.
- **Cached tokens for gcloud ADC expire.** If you see `403: Forbidden` unexpectedly after switching machines or waking from sleep, re-run `gcloud auth application-default login`.

Full list: [`reference/gotchas.md`](reference/gotchas.md).

## Non-goals

- Does not create new Google Docs (operate on existing ones by ID).
- Does not read back from the Doc — one-way only (`md → Doc`).
- Does not preserve comments or suggestions across syncs.
- Does not manage permissions or sharing.

## Dependencies

- Python 3.9+
- **Service account path:** `google-auth` (install via `pip install google-auth`).
- **gcloud ADC path:** `gcloud` CLI on `$PATH`.

No other dependencies — uses Python's `urllib` stdlib for all HTTP.

## License

MIT. See [`LICENSE`](LICENSE).

## Contributing

Issues and PRs welcome. The script is intentionally single-file and stdlib-leaning — please keep it that way.

## Use with Claude Code

This repo is also a [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills). Clone it to `~/.claude/skills/gdoc-sync/` and Claude Code will auto-discover it when the user asks to sync markdown to a Google Doc.
