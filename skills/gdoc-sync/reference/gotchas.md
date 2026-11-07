# Gotchas

Things that will bite you if you don't know them. Read this before the first sync of a Doc you care about.

## The push is destructive

Step 1, the `PATCH` with `Content-Type: text/markdown`, **replaces the whole Doc body**. Google re-parses the markdown from scratch:

- **Pending suggested edits are wiped.**
- **Comments anchored to changed text are orphaned.** They stay in the sidebar without a highlighted span.
- **Formatting done in the UI or through the API is lost.** That includes bold added by a person, and the styling pass from the previous sync (which is why step 6 exists and runs on every sync).
- **Elements added later through the API are gone.** Page breaks, borders and inserted images all go.

### The guard (step 0)

Right after each push, the script records the Doc's Drive `modifiedTime` in `~/.cache/gdoc-sync/state.json`. It writes atomically, under a lock, so parallel syncs of sibling Docs are safe. Before the next push it lists the Doc's Drive **revisions** since that time:

| Revisions since the last push | Result |
|---|---|
| None, or only ones made by this run's identity (the service account, or your own account under gcloud ADC) | Push |
| Any by someone else, including an edit made *while* the previous sync was still styling the Doc | **Refuse** (exit 3). It prints who edited and when |
| No record yet (first sync on this machine) | Push, with a note |

If you're refused, open File → Version history, fold the person's edit into the markdown, and sync again. Pass `--force` only when you mean to discard the edit.

Limits:
- The state is per machine. The first sync on a new machine has no baseline, so it pushes.
- Drive merges rapid edits into one revision. A person's edit made within moments of the script's own edits can be credited to the service account and missed.

### Getting back

Every push creates an entry in **File → Version history**, so any earlier state can be restored from the UI. A copy through the Drive API (`files/{id}/copy`) is not a reliable backup when run as the service account: the copy would be owned by the service account, which has no Drive storage, so it fails with `storageQuotaExceeded`. Make copies as a person (**File → Make a copy**).

## Multi-tab Docs

Docs can have tabs. The Docs API without `includeTabsContent` returns only the first tab, and a markdown push writes **one** tab of content: the other tabs are lost. The script refuses a Doc with more than one tab unless you pass `--force`. Keep each synced document in its own single-tab Doc and link between them with `--cross-doc-map`.

## What the markdown import does

| Markdown | In the Doc |
|---|---|
| `#`…`######` | Heading 1-6, each with a `headingId` |
| Lists, bold, italic, `~strike~`, inline code | Converted |
| Tables | Converted. A table that splits across pages **repeats its header row** on each page |
| Fenced code | A code block |
| `[text](https://…)` | A link |
| `[text](#slug)` | A URL link to the literal `#slug`, which step 2 fixes |
| `[text](other.md#slug)` | A URL link to the literal filename, which step 3 fixes |
| `![](https://public/url.png)` | An inline image at its native size, which step 4 shrinks |
| `![](relative/path.png)` or `data:` URIs | **Dropped**: Google can't fetch them |
| Blank lines between blocks | Often an extra **empty paragraph** between blocks. Remove them with `--drop-empty-paragraphs` |
| Raw HTML, footnotes, front matter | Unreliable. Don't depend on them |

The import's default paragraph style uses line spacing 115 plus the empty paragraphs above, which reads loose next to a hand-tightened Doc. Step 6's flags restore a tighter style on every sync.

Limits: Docs hold about 1.02 million characters, and Drive converts text files up to 50 MB.

## Anchor-link rewriting (step 2)

Each `#slug` link is matched in this order:

1. **The heading's slug.** It is computed from the heading text the same way a markdown renderer does: lowercase, punctuation dropped, spaces to `-`, Hebrew and Arabic kept. `[see onboarding](#onboarding-flow)` finds `## Onboarding flow`.
2. **The section number in the link text,** falling back through shorter prefixes: `5.3.1`, then `5.3`, then `5`. `[§5.3.1](#531-x)` finds `## 5.3 …` when 5.3.1 doesn't exist.

Links that resolve neither way are left alone. The step-2 line lists the first few unresolved anchors. Common causes are a typo in the anchor, or a heading whose text changed after the link was written. When two headings share a slug, the first one wins.

## Cross-doc links (step 3)

`--cross-doc-map "spec.md=DOC_ID"` is opt-in per sibling. A link matches when its URL-decoded URL *contains* the key, so `../specs/spec.md#x` matches `spec.md`. The anchor resolves by slug, then by a section number taken from the anchor (the slug drops dots, so `162` may mean `16.2` or `1.6.2`), then by a number in the link text. If none of those works, the link points at the top of the target Doc.

## RTL (step 5)

`--rtl` sets `RIGHT_TO_LEFT` across the whole body in one request, table cells included. Mixed docs, for example Hebrew with one English chapter, usually look fine, because Docs' bidi handling copes with LTR runs. There is no per-paragraph control. On an empty Doc (body `endIndex` 2) the range is empty, so the call succeeds and does nothing.

## Styling (step 6)

- The flags are applied paragraph by paragraph, table cells included. Headings (`HEADING_*`, `TITLE`, `SUBTITLE`) take `--heading-space-*`; everything else takes the body values. `--line-spacing` applies to both. `--font-size` applies to body text only.
- `--drop-empty-paragraphs` keeps three kinds of empty paragraph: the last one in the body, the one right before a table (the API refuses to delete it), and those inside table cells. A paragraph holding only a horizontal rule, an image, a page break or a chip counts as content and stays.
- For anything the flags don't cover, such as table borders, cell padding or page breaks before headings, write a small Docs `batchUpdate` script and run it after every sync. Note that the paragraph indexes change on each push, so find elements by text, not by index.

## Images (step 4)

Step 4 pairs the Doc's inline images with the markdown's image URLs **by position**. If the counts differ (an image failed to import, or the Doc has an image that isn't in the markdown), it prints the counts and skips. The resize deletes each oversized image and re-inserts it from the **markdown's URL**, so the URL must still be reachable.

## Auth and 403s

1. **Doc not shared with the service account.** Share it with the `client_email` from the key, as Editor.
2. **APIs not enabled.** Enable the [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) and the [Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com) in the service account's project, then wait 1-3 minutes.
3. **Wrong key.** Check it with `jq -r .client_email sa-key.json`.
4. **gcloud ADC without Drive scopes.** `print-access-token --scopes` only works for scopes granted at login. See [auth-setup.md](auth-setup.md#path-b-gcloud-adc-fallback).
5. **Workspace policy blocking external sharing.** Ask your Workspace admin.

The script prints a `hint:` line under the API's error for the common cases.

## Rate limits and retries

A sync makes roughly 6-10 API calls, plus one per batch of 400 style updates. The script retries 429 and 5xx responses up to 4 times with exponential backoff. If you sync dozens of Docs in a loop, add a short sleep between them.

## Shared drives

Uploads and metadata calls pass `supportsAllDrives=true`. On a shared drive, add the service account as a **Content Manager** of the drive. Org policies can still block service-account access, so check with your Workspace admin if you get 403s.
