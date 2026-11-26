---
name: downloading-ktuvit-subtitles
description: Use when the user wants to find or download Hebrew subtitles (כתוביות בעברית) for a movie or TV episode, mentions ktuvit.me, ktuvit or screwzira, names a video file or release (e.g. Movie.2013.1080p.BluRay.x264-GROUP) that needs a Hebrew .srt, or asks which Hebrew subtitle on ktuvit fits a release. Also use when a ktuvit download returns "הבקשה לא נמצאה" instead of a file, or when ktuvit's list hides behind a login.
---

# Downloading ktuvit subtitles

ktuvit.me is the main Hebrew subtitle site. Searching is public; listing and downloading need a login.
This skill finds the right file and downloads it as ktuvit serves it. It does not change the file.

## Tool: `scripts/ktuvit.py` (run with `python3 -I`)

| Command | Does |
|---|---|
| `search "Title" [--year Y] [--series]` | Find the film or series ID. No login. |
| `list <id> [--season S --episode E]` | Every subtitle, sorted by downloads, with translator, syncer, uploader, size, and "same file as #n". |
| `download <id> <subtitle_id> -o file.srt` | Download one. Retries ktuvit's intermittent "request not found" reply; unpacks zips. For an episode, `<id>` is the series ID. |

Add `--json` to `search`/`list` for machine-readable output.

Login: the script reads `KTUVIT_EMAIL` and `KTUVIT_PASSWORD`, or else a Proton Pass login item (default
`ktuvit` in vault `Personal`; `--pass-item`/`--vault` or `KTUVIT_PASS_ITEM`/`KTUVIT_PASS_VAULT` change it).
The site logs in by email. The script never prints the password. Never ask the user to paste a password
into the chat; if no login is set up, ask them to set one up. Python 3.10+ standard library, plus the
`openssl` command for the login hash.

## Steps

1. **Pin down the release.** Read title, year, season/episode, source (BluRay, WEB-DL, HDTV), resolution
   and group from the file name.
2. **Search and confirm the title.** Search can return near-misses ("Rushlights" for "Rush"). Match the
   year and IMDb ID. A series needs `--series`; its `subs=0` in search is normal, the episodes have them.
3. **Read the list before downloading anything.** Judge each row on:
   - **Translator** (`tr:`). `אולפנים` or a named studio is an official, professional translation,
     usually the best text. A named fan translator (e.g. `ZIPC (Qsubs)`) can be good. `אלמוני` means unknown.
   - **Release.** Same source and group as the video first, then same source (BluRay vs WEB vs HDTV).
     Resolution rarely matters: 720p and 1080p of one group share timing.
   - **Downloads.** The list is already sorted; a high count means people found it good.
   - **"same file as #n"** marks one file uploaded under several release names. Download one per group.
   - **Size.** An entry several times bigger than the rest is usually a zip of several syncs.
4. **Shortlist 1-3 files and download only those**: the best studio translation, if any, plus the best
   release match. With no studio translation, go by release match, then downloads; if no row has the
   video's group, the same source beats a more-downloaded WEB or HDTV sync. Open a big zip only when no
   row matches the release. If a download keeps failing, wait a minute and rerun it, or take its
   "same file as" twin. Do not download the whole list.
5. **Choose.** If the studio translation and the exact-release file differ, the right pick depends on
   timing: compare them with the fixing-hebrew-subtitles skill's `sync_check.py` (against the video, or,
   with no video, against the exact-release file, which then counts as one of your 1-3 downloads).
   Comparing doesn't change either file. A studio translation that fits beats a fan one. Without any way to
   measure, take the best release match and say the timing is unverified.
6. **Deliver the file as downloaded.** Name it after the video (`<video name>.heb.srt`; `.heb`, not
   `.he`) where the user wants it, or in `~/Downloads` if they named no place. Report the release it was
   synced to, the translator, and how many files you downloaded.

**Stop there unless the user asked for more.** Most ktuvit files are cp1255 with punctuation typed at
the wrong end of each line, and synced to the uploader's release. If the user wants it to play correctly,
be synced to their video, or be "ready for Kodi", use the fixing-hebrew-subtitles skill on it.

## Mistakes that happened without this skill

| Mistake | Instead |
|---|---|
| Downloaded all 44 entries to compare them | Shortlist from the list; "same file as" groups meant 44 entries were 7 files |
| Called the exact-release fan sub "the most downloaded" and ignored a studio translation with almost twice the downloads | Read the translator column; the list is sorted by downloads |
| Took the exact-release fan sub over the studio translation because the studio one "might not fit" | Measure it; for Prisoners (2013) the studio file had identical timing to the SPARKS sub |
| Saved an 83-byte "הבקשה לא נמצאה" reply as the subtitle | `ktuvit.py download` checks for it and retries; about 60% of single tries get it |
| Named it `.he.srt` | `.heb.srt` |
