---
name: gdoc-sync
description: Sync a Markdown file to an existing Google Doc — pushes the markdown via Drive upload, rewrites Google's broken `[text](#slug)` in-doc anchors AND `[text](other.md#slug)` cross-doc references into working heading links, resizes oversized inline images, re-applies paragraph styling (line spacing, spacing, font size, empty-paragraph cleanup) that every push resets, renames the Doc, exports a PDF for visual QA, refuses to overwrite edits someone made in the Doc since the last sync, and optionally applies right-to-left paragraph direction for Hebrew/Arabic. Use when the user asks to sync/push/deploy markdown to a Google Doc, update an existing Google Doc from a local .md file, keep a Doc's styling tight across re-syncs, link from one synced Doc into a sibling synced Doc, or maintain a Hebrew/Arabic Doc whose body must render RTL.
allowed-tools: Read, Write, Bash, Edit, Glob, Grep
---

# gdoc-sync

`scripts/sync-gdoc.py` replaces a Google Doc's body with a local Markdown file through the Drive API, which converts the markdown. It then fixes what that conversion gets wrong, and re-applies the styling that every push resets. It runs on a bare `python3`, and it finds the service-account key on its own: `--sa-key`, then `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC.

## Quick start

```bash
python3 scripts/sync-gdoc.py plan.md --doc-id 1lSspmI7TXXxVPjX8mLRa8LZEPkhE2rNDYJ_fFDU-BEE \
  --title "Product Plan" \
  --line-spacing 100 --space-below 3 --heading-space-above 8 --drop-empty-paragraphs \
  --export-pdf /tmp/plan.pdf
```

```
[0/7] Doc unchanged since the last sync
[1/7] Pushed markdown: plan.md (84,468 bytes); renamed to 'Product Plan'
[2/7] Fixed 35 in-doc anchor links
[3/7] Skipped cross-doc link rewriting (no --cross-doc-map)
[4/7] Resized 2 oversized images (max width 300.0pt)
[5/7] Skipped RTL (use --rtl to enable)
[6/7] Styling: removed 41 empty paragraphs, 212 style updates
[7/7] Exported PDF → /tmp/plan.pdf (182,311 bytes)
Done. https://docs.google.com/document/d/1lSspmI7.../edit
```

`--doc-id` is the token in `docs.google.com/document/d/<ID>/edit`. The Doc must already exist and be shared with the service account's email as Editor. A service account can't create files, so create the empty Doc in the UI first.

**Keep the full command next to the markdown,** in a `sync.sh` or a Makefile target. The styling flags are part of every sync, not a one-off: a push resets them. If the command lives only in a session transcript, the next person has to reverse-engineer it.

## The pipeline

| Step | What | Why |
|---|---|---|
| **0. Guard** | Refuses (exit 3, "REFUSED: …") if a person edited the Doc after this script last synced it. Also refuses a Doc with several tabs. `--force` overrides both | The push replaces the whole body. Without the guard, a hand edit made between syncs is silently lost, and a multi-tab Doc is flattened into one tab |
| **1. Push** | `PATCH /upload/drive/v3/files/{id}` with `Content-Type: text/markdown`; `--title` also renames the file in Drive | Google converts headings, lists, tables, code blocks and public-URL images |
| **2. In-doc anchors** | Rewrites `[text](#slug)` links into native heading links. It matches the heading's slug first (any heading text), then a section number (`5.3.1` → `5.3` → `5`) | The import leaves these as URL links to a literal `#slug`, which go nowhere |
| **3. Cross-doc links** | With `--cross-doc-map "spec.md=DOC_ID"`, rewrites `[text](spec.md#slug)` into `https://docs.google.com/document/d/DOC_ID/edit#heading=h.xxx` | The import keeps the local filename as the URL |
| **4. Images** | Re-inserts inline images wider than `--max-image-width` (default 300pt) at that width | The import uses each image's native size, often past the margins |
| **5. RTL** | With `--rtl`, sets `direction: RIGHT_TO_LEFT` on every paragraph | Neither the import nor the UI sets direction for Hebrew/Arabic |
| **6. Styling** | `--line-spacing`, `--space-above/--space-below` (body), `--heading-space-above/-below`, `--font-size` (body), `--drop-empty-paragraphs`. Applied per paragraph, table cells included | The import's defaults are loose: line spacing 115 and an empty paragraph between blocks. A push wipes any styling you applied earlier |
| **7. Export** | `--export-pdf PATH` saves Google's own render | So you can look at the result. Convert a page with `pdftoppm -png -r 110 -f 1 -l 1 out.pdf page` |

A "compact business document" preset that worked well: `--line-spacing 100 --space-below 3 --heading-space-above 8 --font-size 10 --drop-empty-paragraphs`.

## Gotchas

**The push is destructive.** It replaces the body: pending suggestions are wiped, comments on changed text are orphaned, and formatting made in the UI is lost. The guard catches edits since the last sync. Version history (File → Version history) keeps every push, so that is the way back. Read [reference/gotchas.md](reference/gotchas.md) before the first sync of a Doc you care about.

**The Doc's title is not the H1.** What Drive and the browser tab show is the file name. Use `--title` to set it. A Doc can show one name in Drive and a different heading on page one, so check both when documents should look like a matched set.

**Only public image URLs survive.** A relative path (`![](img/a.png)`) or a `data:` URI is dropped by the import, and the image-count mismatch then skips step 4. Host images at a stable https URL.

**One tab only.** Without `--force`, the script refuses to push into a Doc that has several tabs. A markdown push writes one tab of content, and the other tabs are lost.

## When to use / not

| Scenario | Use |
|---|---|
| A Doc whose source of truth is a local `.md` | This skill |
| Hebrew / Arabic Doc | This skill with `--rtl` |
| Two Docs that link into each other | This skill with `--cross-doc-map` on each |
| Edit in the Doc, then pull back to markdown | Not this: it is one-way. Drive can export `text/markdown` (`files/{id}/export?mimeType=text/markdown`) |
| Preserve comments or suggestions across syncs | Not possible with a full-body push |
| Sharing or permissions | Drive UI or the Drive permissions API |

## Files

```
gdoc-sync/
├── SKILL.md                 # this file
├── README.md                # GitHub landing page
├── scripts/sync-gdoc.py     # the script (stdlib only; google-auth used when present)
├── scripts/README.md        # flags and exit codes
└── reference/
    ├── auth-setup.md        # service account, API enablement, Doc sharing, ADC fallback
    └── gotchas.md           # destructive behaviors, conversion quirks, limits
```

## Related skills

- [`gslides-sync`](../gslides-sync/SKILL.md): the same pattern for `.pptx` → Google Slides.
- [`gsheets`](../gsheets/SKILL.md): the Sheets sibling. One service account and one key path cover all three; enable each API in its project.
- [`tech-design-doc`](../tech-design-doc/SKILL.md) calls this skill to push a finished design doc to a live Doc.
- [`brand-system`](../brand-system/SKILL.md) scaffolds long-form BRAND.md documents worth rendering to a Doc.
