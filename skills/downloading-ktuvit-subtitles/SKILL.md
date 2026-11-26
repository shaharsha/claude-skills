---
name: downloading-ktuvit-subtitles
description: Use when the user wants Hebrew subtitles (כתוביות בעברית) for a movie or TV episode, mentions ktuvit.me, ktuvit or screwzira, names a video file or release (e.g. Movie.2013.1080p.BluRay.x264-GROUP) that needs a Hebrew .srt, or asks which Hebrew subtitle fits a release or a Kodi library file. Also use when a Hebrew .srt is out of sync with a video, shows punctuation on the wrong side, or reads as gibberish in Kodi, or when a ktuvit download returns "הבקשה לא נמצאה" instead of a file.
---

# Downloading ktuvit subtitles

ktuvit.me is the main Hebrew subtitle site. Searching is public; listing and downloading need a login.
A ktuvit file is almost never ready for Kodi as downloaded: it is usually cp1255 with punctuation
typed at the wrong end of each line, and it is synced to whatever release the uploader had.
The job is to pick the right file, check it fits the video, and make it Kodi-ready.

## Tools (in `scripts/`, run with `python3 -I`)

| Script | Does |
|---|---|
| `ktuvit.py search "Title" [--year Y] [--series]` | Find the film or series ID. No login. |
| `ktuvit.py list <id> [--season S --episode E]` | Every subtitle, sorted by downloads, with translator, syncer, uploader, size, and "same file as #n". |
| `ktuvit.py download <id> <subtitle_id> -o file.srt` | Download one. Retries the "request not found" reply; unpacks zips. For an episode, `<id>` is the series ID. |
| `sync_check.py <video-or-wav> a.srt [b.srt ...]` | Offset, frame-rate scale and per-quarter drift against the real audio, with a verdict. |
| `sync_check.py <reference.srt> a.srt [b.srt ...]` | No video: the same check against another subtitle's timing. |
| `prepare_for_kodi.py in.srt out.heb.srt [--shift S] [--drop-cue N]` | Fix punctuation order, shift, write UTF-8 BOM with RTL marks, verify. |

Login: the scripts read `KTUVIT_EMAIL` and `KTUVIT_PASSWORD`, or else a Proton Pass login item (default
`ktuvit` in vault `Personal`; `--pass-item`/`--vault` or `KTUVIT_PASS_ITEM`/`KTUVIT_PASS_VAULT` change it).
The site logs in by email. They never print the password. Never ask the user to paste a password into the
chat; if no login is set up, ask them to set one up. Python 3.10+ standard library, plus the `openssl`
command for the login hash; checking against a video also needs `ffmpeg` and `ffsubsync`.

## Steps

1. **Check for a finished subtitle first.** If a `.heb.srt` already sits next to the video or in its
   Kodi folder, check it with `sync_check.py` and ask before replacing it.
2. **Pin down the release.** Read title, year, season/episode, source (BluRay, WEB-DL, HDTV), resolution
   and group from the file name. If you have the video file, note its path; you will measure against it.
3. **Search and confirm the title.** Search can return near-misses ("Rushlights" for "Rush"). Match the
   year and IMDb ID. A series needs `--series`; its `subs=0` in search is normal, the episodes have them.
4. **Read the list before downloading anything.** Judge each row on:
   - **Translator** (`tr:`). `אולפנים` or a named studio is an official, professional translation,
     usually the best text. A named fan translator (e.g. `ZIPC (Qsubs)`, `פיפו`) can be good.
     `אלמוני` means unknown.
   - **Release.** Same source and group as the video first, then same source (BluRay vs WEB vs HDTV).
     Resolution rarely matters: 720p and 1080p of one group share timing.
   - **Downloads.** The list is already sorted; a high count means people found it good.
   - **"same file as #n"** marks one file uploaded under several release names. Download only one of
     each group.
   - **Size.** An entry several times bigger than the rest is usually a zip of several syncs.
   Shortlist 1-3 files: the best studio translation, if any, plus the best release match. Do not
   download the whole list. With no studio translation, go by release match, then downloads. If no row
   has the video's group, the closest is the same source (BluRay for a BluRay rip), and that beats a
   more-downloaded WEB or HDTV sync. A re-encode whose group no one syncs to (e.g. BHDStudio) has no
   exact match; measure instead. Open a big zip only when no row matches the release; it may hold one.
5. **Download the shortlist.** If a download keeps failing, wait a minute and rerun it, or take its
   "same file as" twin.
   A zip gets unpacked into a folder; pick the file for your release from it.
6. **Measure.** With the video, run `sync_check.py <video> <every candidate>`. Without it, use the
   exact-release candidate as the reference: `sync_check.py <exact-release.srt> <studio.srt>`. Prefer, in
   order: a studio translation that fits as-is; a studio translation that fits with one shift; any file
   that fits as-is; any file that fits with one shift. Reject "drifts / cut differs" unless nothing else
   exists, and then say so. A reference from the same release family (its twin, or another file from
   the same zip) proves nothing; say the sync is unverified. Between equally good files, take the
   smaller shift. A large offset alone
   (+27 s) is fine: releases differ in studio logos before the film. With neither a video nor an
   exact-release sub, take the best release match and say the sync is unverified.
7. **Make it Kodi-ready.** Run `prepare_for_kodi.py` with the `--shift` from step 6. Then:
   - It must print `verify: OK`. If not, it names the line; fix that line by hand in the output, keeping
     the RLE/PDF marks around the text, and check that no Hebrew line starts with `.`, `,`, `?` or `!`.
   - Read every cue it lists under "check by eye" and fix any that read wrong. A visual-order file
     sometimes has a line typed in normal order; if its sentence runs into the next cue, its `...`
     belongs at the end.
   - If it says a cue looks like release info (e.g. "BluRay / BRRip ... FPS"), run it again with
     `--drop-cue N` added; it overwrites the output. Keep real credits (translator, syncer, "צפייה נעימה").
8. **Name and place it.** Name it `<video file name without extension>.heb.srt` (or `Title (Year).heb.srt`
   for a Kodi movie folder), next to the video. `.heb`, not `.he`. For the Kodi drive, use the
   kodi-nas-media skill if you have it. If the video isn't on this machine, still name it after the video
   file the user named. If you don't know where the video is and the user named no place, save to
   `~/Downloads` and say so.
9. **Report:** the release it was synced to, the translator, the shift applied, sync verdict, and how many
   files you downloaded.

## Mistakes that happened without this skill

| Mistake | Instead |
|---|---|
| Downloaded all 44 entries to compare them | Shortlist from the list; "same file as" groups mean 44 entries were 7 files |
| Called the exact-release fan sub "the most downloaded" and ignored the studio translation with almost twice the downloads | Read the translator column; the list is sorted by downloads |
| Without the video, took the exact-release fan sub over the studio translation because the studio one "might not fit" | Measure the studio one against the exact-release sub with `sync_check.py`; for Prisoners it had identical timing |
| Saved the raw cp1255 file, or only re-encoded it | Run `prepare_for_kodi.py`; it also flips the punctuation and adds the BOM and RTL marks |
| Saved an 83-byte "הבקשה לא נמצאה" reply as the subtitle | `ktuvit.py download` checks this and retries |
| Checked drift by matching part of a subtitle against the whole audio, and it locked onto end-credits music (+57 s) | `sync_check.py` matches each quarter against that quarter's audio |
| Named it `.he.srt` | `.heb.srt` |
| Stripped the RLM marks before flipping punctuation, which garbled lines like `."‏-כן` | `prepare_for_kodi.py` keeps them; they mark where the wrong-end punctuation stops |
