# scripts/

## `sync-gdoc.py`

One Python file (3.9+), stdlib only. It uses `google-auth` when importable and otherwise signs the service-account token with `cryptography` or the `openssl` CLI, so it runs on a bare `python3`. `uv run sync-gdoc.py …` works too.

```bash
python3 sync-gdoc.py <markdown-file> --doc-id <ID> [flags]
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--doc-id <id>` | *required* | Google Doc file ID |
| `--sa-key <path>` | `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC | Service-account JSON key |
| `--title <name>` | — | Also rename the Doc in Drive (the file name, not the H1) |
| `--rtl` | off | RIGHT_TO_LEFT on every paragraph |
| `--no-links` | off | Skip steps 2 and 3 |
| `--max-image-width <pt>` | `300` | Shrink wider inline images; `0` skips |
| `--cross-doc-map NAME=DOC_ID` | — | Repeatable. Rewrites links to `NAME…#anchor` into deep links |
| `--line-spacing <pct>` | — | e.g. `100` (the import uses 115) |
| `--space-above` / `--space-below <pt>` | — | Body paragraphs |
| `--heading-space-above` / `--heading-space-below <pt>` | — | Headings |
| `--font-size <pt>` | — | Body text |
| `--drop-empty-paragraphs` | off | Delete the empty paragraphs the import leaves between blocks |
| `--export-pdf <path>` | — | Save Google's PDF render after syncing |
| `--force` | off | Push despite a hand edit since the last sync, or a multi-tab Doc |

### What runs, in order

0. **Guard.** Refuses with exit 3 if the Doc has several tabs. It also lists the Doc's Drive revisions since the time recorded at the last push (`~/.cache/gdoc-sync/state.json`), and refuses if any are by someone other than this run's identity.
1. **Push.** `PATCH /upload/drive/v3/files/{id}?uploadType=media` with `Content-Type: text/markdown`, plus a Drive `PATCH {name}` when `--title` is given. The state is recorded right after this step.
2. **In-doc anchors.** `updateTextStyle` rewrites `link.url = "#slug"` to `link.headingId`, matched by slug and then by section number.
3. **Cross-doc links.** Rewrites them to `https://docs.google.com/document/d/ID/edit#heading=h.xxx`.
4. **Images.** `deleteContentRange` + `insertInlineImage` with an explicit `objectSize`, re-fetching each image from its markdown URL.
5. **RTL.** One `updateParagraphStyle` across the body.
6. **Styling.** Empty-paragraph deletion, then per-paragraph `updateParagraphStyle` and `updateTextStyle`, in batches of 400.
7. **Export.** `GET /drive/v3/files/{id}/export?mimeType=application/pdf`.

Every index-based Docs `batchUpdate` carries `writeControl.targetRevisionId`: the revision its indexes were read from. A retried or concurrent write is transformed instead of hitting stale indexes.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Synced |
| 1 | File not found, auth failure, or an API error (body and `hint:` on stderr) |
| 2 | Usage error |
| 3 | Refused by the guard: a hand edit since the last sync, or a multi-tab Doc. Re-run with `--force` to override |

### Errors and retries

- 429/500/502/503/504 are retried with backoff (1.5 s, 3 s, 6 s), up to 4 attempts.
- 403/404 usually mean the Doc isn't shared with the service account, or the Drive/Docs API isn't enabled in its project. See [`../reference/auth-setup.md`](../reference/auth-setup.md).

### Quick test

Against an empty Google Doc you own, shared with the service account as Editor:

```bash
cat > /tmp/test.md <<'EOF'
# Test Doc

## Overview
See [the details](#details) and [section 2](#2-section-two).

## Details
Hello.

## 2. Section two
World.
EOF

python3 sync-gdoc.py /tmp/test.md --doc-id YOUR_DOC_ID --drop-empty-paragraphs --export-pdf /tmp/test.pdf
```

Expected: `[2/7] Fixed 2 in-doc anchor links`. In the Doc, both links scroll to their headings.
