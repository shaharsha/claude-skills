# Gotchas

Things that will bite you if you don't know them. Read this before the first sync of a deck you care about.

## The push is destructive

Step 1, the resumable upload onto the deck ID, **replaces the whole presentation**. Drive's converter re-parses the pptx from scratch:

- **Pending suggestions are wiped**, and comments anchored to changed shapes are orphaned.
- **Edits made in the Slides UI are lost.**
- **Every element added through the API after the last import is deleted,** including narration videos, inserted images and shapes. Anything you attach after a push must be attached again after the next one. When the deck had narration videos (`narr_*`), the push prints the `gslides_narration.py insert` command that restores them.
- **The page size comes from the pptx.** A deck that was 720x405pt becomes 960x540pt if the pptx says so, and positions computed for the old size end up in the wrong place. The step-1 line prints the size, and says so when it changed.

### The guard (step 0)

Right after each push, the script records the deck's Drive `modifiedTime` in `~/.cache/gdoc-sync/state.json` (written atomically, under a lock). Before the next push it lists the deck's Drive **revisions** since then. If any were made by someone other than this run's identity (the service account, or your own account under gcloud ADC), it refuses with exit 3 and prints who edited and when. That includes edits made while the previous sync was still running. Fold the person's change into the pptx, or pass `--force` to discard it.

The state is per machine, and Drive can merge an edit made within moments of the script's own into one revision.

### Getting back

Every push is a new entry in **File → Version history**. A copy through the Drive API made as the service account fails, because a service account has no Drive storage (`storageQuotaExceeded`). Make backup copies as a person.

## What the converter drops or changes

| pptx content | In Google Slides |
|---|---|
| Embedded audio (narration) | **Dropped, every time.** The audio icon stays as a silent ~27pt picture. The script warns when the pptx has audio. Narrate with the narrating-pptx skill's Google Slides section instead |
| Embedded video | Converted to a static image |
| Native charts | Converted to images. Category or axis labels can disappear, so render charts as pictures in the pptx you push to Google |
| Fonts outside Google Fonts | Fall back to Arial-like fonts, even when embedded, so lines wrap differently. Use Google Fonts (Roboto, Open Sans, Noto Sans, Noto Sans Hebrew) |
| Custom masters and layouts | Flattened into per-slide formatting. The layout sidebar doesn't reflect the pptx's structure |
| Animations and transitions | Simple ones usually survive; motion paths, triggers and timelines are lost or simplified |
| Speaker notes | Usually kept |
| Decks over 100 MB | Conversion fails |

## Slide-link rewriting (step 2)

| Link URL | Action |
|---|---|
| Matches `slide[-_]?N(\.xml)?$` or `#slideN` | Rewritten to `pageObjectId` of slide N |
| `#anchor` matching a slide title's slug | Rewritten to that slide |
| Ends in `.xml` with a number in the link text | Rewritten to that slide number |
| Already a `pageObjectId`, `slideIndex` or `relativeLink` link | Left alone |
| A working external `https://` URL | Left alone |

## Cross-deck links (step 3)

`--cross-pres-map "name.pptx=PRES_ID"` is opt-in per sibling, and a link matches when its URL contains `name`. The anchor resolves by slide-title slug, then `slideN`, then a number in the link text. Otherwise the link points at the top of the target deck.

## Image resize (step 4)

The step uses each image's effective width (`size.width × transform.scaleX`), with a default maximum of the deck's page width, so full-bleed images aren't touched. Resized images keep their center. On image-only decks this step does nothing.

## RTL (step 5)

`--rtl` walks every shape and table cell with text and sets `RIGHT_TO_LEFT` on all of it. It skips empty shapes, speaker notes and master/layout placeholders.

## Auth and 403s

1. **Deck not shared with the service account.** Share with the key's `client_email`, as Editor.
2. **APIs not enabled.** Enable the [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) and the [Slides API](https://console.cloud.google.com/apis/library/slides.googleapis.com) in the service account's project, then wait 1-3 minutes.
3. **`storageQuotaExceeded`.** The service account tried to create a file; it has no Drive storage. See [auth-setup.md](auth-setup.md#what-a-service-account-cant-do).
4. **gcloud ADC without the scopes.** `print-access-token --scopes` only works for scopes granted at login. See [auth-setup.md](auth-setup.md#path-b-gcloud-adc-fallback).

The script prints a `hint:` line under the API's error for the common cases.

## Rate limits and retries

A sync makes about 8-12 calls, plus one per slide for `--thumbnails` (thumbnail requests are expensive against the Slides quota). 429 and 5xx responses are retried up to 4 times with backoff.

## Shared drives

Uploads pass `supportsAllDrives=true`. On a shared drive, add the service account as a **Content Manager**.
