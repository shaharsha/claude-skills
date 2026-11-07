# scripts/

## `sync-gslides.py`

One Python file (3.9+), stdlib only. It uses `google-auth` when importable and otherwise signs the service-account token with `cryptography` or the `openssl` CLI, so a bare `python3` works from any directory. `uv run sync-gslides.py …` works too.

```bash
python3 sync-gslides.py <pptx-file> --pres-id <ID> [flags]
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--pres-id <id>` | *required* | Google Slides file ID |
| `--sa-key <path>` | `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC | Service-account JSON key |
| `--title <name>` | — | Also rename the deck in Drive |
| `--rtl` | off | RIGHT_TO_LEFT on every text shape and table cell |
| `--no-links` | off | Skip steps 2 and 3 |
| `--max-image-width <pt>` | page width | Shrink wider images; `0` skips |
| `--cross-pres-map NAME=PRES_ID` | — | Repeatable |
| `--thumbnails <dir>` | — | Save `slide-NN.png` per slide after syncing |
| `--export-pdf <path>` | — | Save a PDF render |
| `--force` | off | Push even if a person edited the deck since the last sync |

### What runs, in order

0. **Guard + audit.** Lists the deck's Drive revisions since the time recorded at the last push (`~/.cache/gdoc-sync/state.json`), and refuses if any are by someone other than this run's identity. Scans the pptx zip for audio parts and native charts and warns about them.
1. **Push.** Resumable upload: `PATCH /upload/drive/v3/files/{id}?uploadType=resumable` (metadata carries `name` when `--title` is set), then `PUT` the bytes to the returned `Location`. It reads `pageSize` before and after. It also counts `narr_*` narration videos beforehand, and prints the `gslides_narration.py insert`/`check` commands that put them back.
2. **Slide links.** `updateTextStyle` sets `link.pageObjectId`.
3. **Cross-deck links.** Sets `link.url` to `…/presentation/d/ID/edit#slide=id.X`.
4. **Images.** `updatePageElementTransform` with a uniform shrink, keeping the center.
5. **RTL.** `updateParagraphStyle` with `textRange: ALL` per shape or cell.
6. **QA.** `pages/{id}/thumbnail?thumbnailSize=LARGE`, then a download of `contentUrl`; `files/{id}/export?mimeType=application/pdf`.


### Exit codes

| Code | Meaning |
|---|---|
| 0 | Synced |
| 1 | File not found, auth failure, or an API error (body and `hint:` on stderr) |
| 2 | Usage error |
| 3 | Refused by the guard: a person edited the deck since the last sync (`--force` overrides) |

### Quick test

Against an empty deck you own, shared with the service account as Editor:

```bash
python3 sync-gslides.py /path/to/deck.pptx --pres-id YOUR_PRES_ID --thumbnails /tmp/thumbs
```

Expected: `[1/6] Pushed pptx: … page 960x540pt`, then `[6/6] Saved N slide thumbnails`. Open `/tmp/thumbs/slide-01.png`.
