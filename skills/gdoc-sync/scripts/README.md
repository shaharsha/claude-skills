# scripts/

## `sync-gdoc.py`

Single-file Python script. Python 3.9+. Optional dep: `google-auth` (only for `--sa-key` path).

### Usage

```bash
./sync-gdoc.py <markdown-file> --doc-id <ID> [flags]
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--doc-id <id>` | *required* | Google Doc file ID |
| `--sa-key <path>` | *none* | Service-account JSON. Recommended over gcloud ADC. |
| `--rtl` | off | Apply RIGHT_TO_LEFT direction to every body paragraph |
| `--no-links` | off | Skip anchor-link rewriting (step 2) |
| `--max-image-width <pt>` | `300` | Resize inline images wider than this. `0` to skip. |

### What runs, in order

1. **Push markdown** → `PATCH /upload/drive/v3/files/{id}` with `Content-Type: text/markdown`. Google converts natively.
2. **Fix anchor links** → `GET /v1/documents/{id}` to walk the structure, build a `section-number → headingId` map, then `POST /v1/documents/{id}:batchUpdate` with `updateTextStyle` requests rewriting `link.url` → `link.headingId`. Skipped with `--no-links`.
3. **Resize images** → Find inline images wider than `--max-image-width`, `deleteContentRange` + `insertInlineImage` with explicit `objectSize`. Uses image URLs from the original markdown. Skipped with `--max-image-width 0`.
4. **Apply RTL** → `updateParagraphStyle` with `direction: RIGHT_TO_LEFT` across the full body range (`startIndex=1` to `endIndex-1`). Skipped by default; enable with `--rtl`.

### Error handling

- **429/500/502/503/504** — retries with exponential backoff (`1.5s`, `3s`, `6s`, `12s`), up to 4 attempts.
- **403 Forbidden** — usually means (a) the SA/user doesn't have Editor access to the Doc, or (b) Drive/Docs APIs aren't enabled in the SA's project. See [`../reference/auth-setup.md`](../reference/auth-setup.md).
- **Other HTTP errors** — the server's error body is printed to stderr before the exception re-raises.

### Exit codes

- `0` — success
- `1` — markdown file not found, auth failure, or unrecoverable HTTP error

### Dependencies

- **Python 3.9+** (uses `|` type syntax sparingly; mostly stdlib).
- **`google-auth`** — only if you use `--sa-key`. Install: `pip install google-auth`.
- **`gcloud` CLI** — only if you use the fallback ADC path. Ensure `gcloud auth application-default login` has been run.

### Quick test

Against a new empty Google Doc you own, shared with your SA as Editor:

```bash
cat > /tmp/test.md <<'EOF'
# Test Doc

## 1. Section one
See [section 2](#2-section-two) for more.

## 2. Section two
Hello, world.
EOF

./sync-gdoc.py /tmp/test.md --doc-id YOUR_DOC_ID --sa-key ~/sa.json
```

Expected output:
```
[1/4] Pushed markdown: /tmp/test.md (N bytes)
[2/4] Fixed 1 anchor links
[3/4] Skipped image resize (no images)
[4/4] Skipped RTL (use --rtl to enable)
Done. https://docs.google.com/document/d/YOUR_DOC_ID/edit
```

Open the Doc and verify: the `[section 2]` link is clickable and scrolls to the correct heading (not broken `#2-section-two`).
