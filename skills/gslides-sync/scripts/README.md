# scripts/

## `sync-gslides.py`

Single-file Python script. Python 3.9+. Optional dep: `google-auth` (only for `--sa-key` path).

### Usage

```bash
./sync-gslides.py <pptx-file> --pres-id <ID> [flags]
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--pres-id <id>` | *required* | Google Slides file ID |
| `--sa-key <path>` | *none* | Service-account JSON. Recommended over gcloud ADC. |
| `--rtl` | off | Apply RIGHT_TO_LEFT direction to every text shape |
| `--no-links` | off | Skip slide-anchor + cross-pres rewriting (steps 2 and 3) |
| `--max-image-width <pt>` | *page width* | Max effective image width in points. Default is auto-detected from the presentation's `pageSize` (e.g. 960pt for 16:9 widescreen). Larger images are scaled down preserving aspect, with center kept fixed. `0` to skip. |
| `--cross-pres-map "name=ID"` | repeatable | Map a pptx filename fragment to a sibling Slides ID for cross-deck deep-linking. |

### What runs, in order

1. **Push pptx** → resumable upload: `PATCH /upload/drive/v3/files/{id}?uploadType=resumable` to initiate, then `PUT` the bytes to the returned `Location` URL. `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation`. Drive converts natively. Resumable (not simple media) is required because pptx routinely exceeds the 5 MB simple-upload guideline.
2. **Fix slide-anchor links** → `GET /v1/presentations/{id}` to walk the structure, build `index → pageObjectId` and `slug → pageObjectId` maps, then `POST /v1/presentations/{id}:batchUpdate` with `updateTextStyle` requests rewriting `link.url` (matching broken patterns like `slide-N.xml`, `#slideN`) to `link.pageObjectId`. Skipped with `--no-links`.
3. **Fix cross-pres links** → For each `--cross-pres-map`, `GET` the target Slides, build its slug + index maps, then rewrite source-deck text-runs whose link URL contains the source filename to a deep-link URL (`https://docs.google.com/presentation/d/{ID}/edit#slide=id.{OBJECT_ID}`). Skipped if no `--cross-pres-map`.
4. **Resize oversized images** → For each image page-element whose effective width (`size.width × transform.scaleX`) exceeds `--max-image-width`, `updatePageElementTransform` with a uniform shrink factor preserving aspect; translate is recomputed so the image's center stays in the same place. Default `--max-image-width` is auto-detected from `presentation.pageSize.width`, so full-bleed images are not touched. Skipped with `--max-image-width 0`.
5. **Apply RTL** → `updateParagraphStyle` with `direction: RIGHT_TO_LEFT` and `textRange.type: ALL` per text shape and table cell. Skipped by default; enable with `--rtl`.

### Error handling

- **429/500/502/503/504** — retries with exponential backoff (`1.5s`, `3s`, `6s`, `12s`), up to 4 attempts.
- **403 Forbidden** — usually means (a) the SA/user doesn't have Editor access to the Slides, or (b) Drive/Slides APIs aren't enabled in the SA's project. See [`../reference/auth-setup.md`](../reference/auth-setup.md).
- **Other HTTP errors** — the server's error body is printed to stderr before the exception re-raises.

### Exit codes

- `0` — success
- `1` — pptx file not found, auth failure, or unrecoverable HTTP error

### Dependencies

- **Python 3.9+** (mostly stdlib).
- **`google-auth`** — only if you use `--sa-key`. Install: `pip install google-auth`.
- **`gcloud` CLI** — only if you use the fallback ADC path. Ensure `gcloud auth application-default login` has been run.

### Quick test

Against a Google Slides you own, shared with your SA as Editor:

```bash
./sync-gslides.py /path/to/deck.pptx --pres-id YOUR_PRES_ID --sa-key ~/sa.json
```

Expected output:
```
[1/5] Pushed pptx: /path/to/deck.pptx (N bytes)
[2/5] Fixed 0 in-deck slide-anchor links
[3/5] Skipped cross-pres link rewriting (no --cross-pres-map)
[4/5] Resized 0 oversized images (max width 720.0pt)
[5/5] Skipped RTL (use --rtl to enable)
Done. https://docs.google.com/presentation/d/YOUR_PRES_ID/edit
```

Open the Slides URL and verify the deck content matches your pptx.
