# Gotchas

Things that will bite you if you don't know. Read before using on a deck you care about.

## The pptx import is destructive

Step 1 — resumable upload to Drive — **completely rewrites the Slides body**. Drive's converter reparses the pptx from scratch. Consequences:

- **Pending suggested edits are wiped.** If a reviewer had uncommitted suggestions, they're gone.
- **Comments anchored to changed shapes are orphaned.** They stay on the file but detached from any element. You'll see them pile up in the comments sidebar without a corresponding highlighted shape.
- **Manual formatting inside the Slides is lost.** If someone tweaked a slide in the Slides UI between your syncs, the next sync reverts it.

**Mitigation:** make a copy of the Slides before the first sync.

Via the Drive UI: **File → Make a copy**.

Via the API:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "https://www.googleapis.com/drive/v3/files/${PRES_ID}/copy" \
  -H "Content-Type: application/json" \
  -d '{"name": "Backup — '"$(date +%F)"'"}'
```

## Font substitution

Drive's converter substitutes any font not in Google's web-fonts catalog. Common casualties:

- **Custom corporate fonts** → fall back to a generic sans-serif
- **System fonts** (San Francisco, Segoe UI) → fall back to Arial-equivalents
- **Hebrew Noto Sans** → usually OK if the pptx specifies it explicitly; falls back to default Hebrew otherwise

This often shifts text metrics — a string that fit on one line in PowerPoint may wrap in Slides. **Use Google Fonts (`Roboto`, `Open Sans`, `Noto Sans`, `Noto Sans Hebrew`) in your pptx source if fidelity matters.**

## Custom slide masters and layouts

If your pptx has custom slide masters / layouts, Drive's converter typically **flattens them into per-slide formatting**. The visual result is usually fine, but:

- The "layouts" sidebar in Slides won't reflect your pptx's layout structure.
- Future template-driven editing in Slides loses the original abstraction.
- Master-level placeholders may render as floating shapes on each slide instead of inheriting from a master.

No fix in code. If you need the master structure preserved, author directly in Google Slides instead of pptx.

## Animations, transitions, embedded media

Drive's converter has limited animation/transition fidelity:
- Simple entrance/exit animations: usually preserved
- Complex animation timelines, motion paths, triggers: lost or simplified
- Slide transitions: most basic ones survive
- **Embedded video / OLE objects: lost.** Video shapes become static placeholders.
- **Embedded audio: lost.**

If your pptx uses these, expect drift. No fix in code.

## 100 MB conversion ceiling

Drive's pptx-to-Slides converter caps at ~100 MB input. Decks over this fail conversion **silently** — you may get a successful upload that produces an empty or partial Slides. Compress images in the pptx before syncing, or split into multiple decks.

## Slide-anchor link rewriting

Step 2 walks each text run, looks at its `link.url`, and tries to detect broken in-deck slide refs:

| Pattern | Action |
|---|---|
| URL matches `slide[-_]?N(\.xml)?$` | Rewrite to `link.pageObjectId` for the Nth slide |
| URL is `#slideN` or `#anchor-slug` | Rewrite by index or by slide-title slug match |
| URL ends in `.xml` | Try numeric extraction; rewrite to slide N if it matches |
| Already a `pageObjectId` / `slideIndex` / `relativeLink` link | **Left alone** — these survived conversion correctly |
| Working external URL (https://...) that doesn't match a sibling pres | **Left alone** |

If your pptx has slide-to-slide links that come through as plain `relativeLink: NEXT_SLIDE` etc., those work fine without rewriting. The rewriter only fires on broken URL-string patterns.

## Cross-pres links require explicit mapping

`--cross-pres-map "name.pptx=PRES_ID"` is **opt-in per sibling**. The script doesn't crawl your pptx to discover sibling references — you must declare each one. The match is by substring on the URL-decoded link URL, so any link whose `url` contains the `name` key matches.

If a cross-pres link points at an anchor that doesn't match the target's slide titles, it falls back to linking to the top of the target Slides (no slide deep-link).

## Image resize uses the converted dimensions

Step 4 reads each image page-element's `size.width × transform.scaleX` to compute its **effective** width on the slide. This is what's actually visible — the converted dimensions, not the source pixel size.

**Default `--max-image-width` is auto-detected from the presentation's `pageSize.width`** — the actual page width. For Slides' standard 16:9 widescreen, that's **960pt** (12191675 EMU); for the older 4:3, it's 720pt. Detecting at runtime means full-bleed images are not touched regardless of the page size you chose.

The resize preserves aspect ratio uniformly and **keeps the image's center fixed** — important for centered or full-bleed images, since pptx-converted images often have non-zero translate offsets baked in. (The first version of this script kept the original translate, which shifted resized images into the top-left quadrant of the slide. Fixed.)

For **image-only decks** (full-bleed slides, each one a single image), the per-slide image is exactly the page width — the resize step is a no-op.

## RTL applies per text shape

`--rtl` walks every shape and table cell with non-empty text and applies `direction: RIGHT_TO_LEFT` to its full text range. It does **not** touch:

- Empty shapes (no text → nothing to direct)
- Speaker notes (separate text element, not walked)
- Master / layout placeholders (not walked, since they appear on the actual slide as inherited content)

For mixed-direction decks (mostly Hebrew with one English chapter), this still usually works — Slides' bidi algorithm handles LTR runs inside RTL paragraphs reasonably.

## Cached tokens and 1-hour TTL

- **Service account tokens** last ~1 hour. `google-auth` refreshes them automatically on every `refresh()` call (script does this once per run).
- **gcloud ADC tokens** last ~1 hour but refresh automatically while the refresh token is valid. If you sleep your laptop for hours, the refresh may fail — re-run `gcloud auth application-default login`.

## 403 Forbidden — diagnostic checklist

In order of likelihood:

1. **Slides not shared with SA?** Open the Slides, Share, confirm the SA email has Editor access.
2. **APIs not enabled?** Visit [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) and [Slides API](https://console.cloud.google.com/apis/library/slides.googleapis.com) in the SA's project. If just enabled, wait 1-3 minutes for propagation.
3. **Wrong SA key?** The key's `client_email` must match the email shared on the Slides. `cat sa-key.json | jq -r .client_email` to check.
4. **Using gcloud ADC without Slides scope?** The default `cloud-platform` scope doesn't include Slides write. See [auth-setup.md Path B](auth-setup.md#path-b-gcloud-adc-fallback).
5. **Org policy blocking external sharing?** Some Google Workspace orgs disable external-user sharing. Check with your Workspace admin.

## Resumable upload Location header

The script uses the resumable upload protocol: `PATCH` to initiate, then `PUT` the bytes to the `Location` URL returned in the response headers. If the initiate response doesn't include a `Location` header (rare — usually means the request was malformed), the script raises with the full headers dict for debugging.

## Rate limits

Google Slides API has per-user and per-project quotas. For a single sync of a reasonably-sized deck, you'll use ~5-10 API calls — nowhere near any limit. If you're syncing dozens of decks in a loop, add `time.sleep(0.5)` between runs or you may hit 429s.

The script retries 429/5xx automatically up to 4 times with exponential backoff, so transient hits are absorbed.

## Shared drives

The script uses `supportsAllDrives=true` on the Drive upload, so Shared Drives should work. If you hit issues:
- Ensure the SA is added to the Shared Drive as **Content Manager** (not just shared on the file)
- Some org-level policies still block SA access to Shared Drives — check with your Workspace admin

File an issue if this fails for you.
