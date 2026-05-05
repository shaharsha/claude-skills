# Gotchas

Things that will bite you if you don't know. Read before using on a doc you care about.

## The markdown import is destructive

Step 1 — `PATCH` with `Content-Type: text/markdown` — **completely rewrites the Doc body**. Google's server reparses the markdown from scratch. Consequences:

- **Pending suggested edits are wiped.** If a reviewer had uncommitted suggestions, they're gone.
- **Comments anchored to changed text are orphaned.** They stay on the Doc but detached from any paragraph. You'll see them pile up in the comments sidebar without a corresponding highlighted span.
- **Manual formatting inside the Doc is lost.** If someone bolded a word in the Doc UI between your syncs, the next sync reverts it.

**Mitigation:** make a copy of the Doc before the first sync.

Via the Drive UI: **File → Make a copy**.

Via the API:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "https://www.googleapis.com/drive/v3/files/${DOC_ID}/copy" \
  -H "Content-Type: application/json" \
  -d '{"name": "Backup — $(date +%F)"}'
```

## Anchor-link rewriting is regex-based on leading section numbers

Step 2 builds its `heading → headingId` map by extracting the leading numeric prefix from each heading (e.g., `5.3.1` from `## 5.3.1 Onboarding flow`). It then rewrites `[text](#anchor)` links whose visible text contains a matching number.

This works well for numbered docs (product specs, legal, technical RFCs) but fails in specific cases:

| Case | Behavior |
|---|---|
| Heading has no number prefix | Not included in the map; anchor links to it can't be rewired |
| Link text doesn't contain the section number | Not rewritten (e.g., `[see the onboarding section](#onboarding)` when heading is `## 3. Onboarding`) |
| Section number exists but link points to a nested depth that doesn't | Falls back to progressively shorter prefixes (`5.3.1` → `5.3` → `5`) |
| Heading has duplicate numbers (e.g., two `## 5. Foo` headings) | Later overrides earlier — last-writer-wins |

If your doc has non-numeric headings, either:
- Add numeric prefixes to your markdown headings, OR
- Use `--no-links` to skip the rewrite pass entirely.

## RTL applies to every body paragraph

`--rtl` runs one `updateParagraphStyle` across `[startIndex=1, endIndex=lastIndex-1]` — the entire body. Every paragraph becomes `direction: RIGHT_TO_LEFT`.

This is correct for Hebrew / Arabic docs. For **mixed** docs (e.g., a primarily Hebrew doc with one chapter in English), it's still usually fine — Google's bidi algorithm handles LTR runs inside RTL paragraphs reasonably well. But expect slight layout differences from what you'd get with paragraph-by-paragraph direction assignments.

There's no per-paragraph direction control in this script. If you need it, sync with `--no-links` (or equivalent) and set direction manually in the Doc UI after.

## Image resize uses the markdown source URL

Step 3 (image resize) finds oversized inline images in the Doc, then deletes and re-inserts them. The re-insert uses the image URL **from the original markdown** — not a Google-hosted copy of the pixels.

Implication: **the image source must still be reachable** for the resize step to succeed. If your markdown points at a transient URL (e.g., a local dev server, an expired CDN link), the resize will fail.

**Best practice:** host images on stable public URLs — R2, Cloudflare Images, S3, GitHub raw, etc. Not `localhost:3000/img.png`.

## Image count must match

Step 3 pairs each inline image in the Doc with its URL in the markdown **by position** (first image in markdown → first image in Doc, etc.). If the counts don't match — because the markdown has an image reference that failed to embed, or the Doc has an image that wasn't sourced from the markdown — the resize step prints a warning and skips.

Common cause: mid-sync, the image URL was temporarily unreachable and Google's import silently omitted that image. Re-run the sync when the URL is reachable again.

## Cached tokens and 5-min TTL

Anthropic prompt caching is unrelated to this script. **Google's own token caching**:

- **Service account tokens** last ~1 hour. `google-auth` refreshes them automatically on every `refresh()` call (script does this once per run).
- **gcloud ADC tokens** last ~1 hour but refresh automatically while the refresh token is valid. If you sleep your laptop for hours, the refresh may fail — re-run `gcloud auth application-default login`.

## 403 Forbidden — diagnostic checklist

In order of likelihood:

1. **Doc not shared with SA?** Open the Doc, Share, confirm the SA email has Editor access.
2. **APIs not enabled?** Visit [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) and [Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com) in the SA's project. If just enabled, wait 1-3 minutes for propagation.
3. **Wrong SA key?** The key's `client_email` must match the email shared on the Doc. `cat sa-key.json | jq -r .client_email` to check.
4. **Using gcloud ADC without Drive scope?** The default `cloud-platform` scope doesn't include Drive write. See [auth-setup.md Path B](auth-setup.md#path-b-gcloud-adc-fallback).
5. **Org policy blocking external Docs?** Some Google Workspace orgs disable external-user sharing. Check with your Workspace admin.

## "This app is blocked" on gcloud login

Google's sensitive-scopes policy blocks Drive/Docs scopes on the default gcloud OAuth client. Workaround: use your own OAuth client via `--client-id-file` — see [auth-setup.md](auth-setup.md#attempt-3--your-own-oauth-client).

## Empty body edge case

If the Doc is completely empty (just `endIndex: 2`), the RTL step's range `[1, endIndex-1=1]` is empty — the API returns success with no changes. Not an error, just a no-op. Put a single character in the Doc first if you need RTL applied before content exists.

## Rate limits

Google Drive API has per-user and per-project quotas (default ~10K queries/100s). For a single sync of a reasonably-sized Doc (~80KB markdown), you'll use ~5-10 API calls — nowhere near the limit. If you're syncing dozens of Docs in a loop, add a `time.sleep(0.5)` between runs or you may hit 429s.

The script retries 429/5xx automatically up to 4 times with exponential backoff, so transient rate-limit hits are absorbed.

## Large image dimensions break Docs

If your markdown has an image referencing a huge source image (say 4000×3000 pixels), Google's import sets the inline image at that native size. Step 3 resizes to `--max-image-width` (default 300pt — roughly a 4" column width).

If step 3 fails (e.g., image URL unreachable), the Doc ends up with an oversized image blowing past the margins. Either re-run the sync after fixing the image URL, or manually resize in the Doc UI.

## Shared drives

The script has been tested on personal-drive-owned Docs and domain-owned Docs in Google Workspace. It *should* work on Shared Drives but isn't specifically tested. If you hit issues, try:
- Ensuring the SA is explicitly added to the Shared Drive as Content Manager (not just granted access to a specific file)
- Using `supportsAllDrives=true` query param on the Drive upload URL (would require a script edit)

File an issue if this fails for you.
