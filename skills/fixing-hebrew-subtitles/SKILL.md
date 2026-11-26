---
name: fixing-hebrew-subtitles
description: Use when a Hebrew subtitle (.srt) shows punctuation or dashes on the wrong side of the line, shows as gibberish (×ª×•... or ????) in Kodi, VLC, Plex or a TV, is early or late against the video, drifts over the film, or needs to be "ready for Kodi". Also use to check which of several subtitle files fits a video best, to shift a subtitle by a fixed offset, or to convert a cp1255 / windows-1255 subtitle to UTF-8 with RTL marks, whatever site it came from.
---

# Fixing Hebrew subtitles

Most Hebrew subtitles on the web (ktuvit, Wizdom, OpenSubtitles, old fan sites) are written for players
without right-to-left support: cp1255, with punctuation typed at the wrong end of each line (".טקסט").
On a modern player that shows reversed, or as gibberish. They are also synced to whatever release the
uploader had. This skill measures the fit, shifts it, and rewrites it so it displays right. It never
changes the words.

## Tools (in `scripts/`, run with `python3 -I`)

| Script | Does |
|---|---|
| `sync_check.py <video-or-wav> a.srt [b.srt ...]` | Offset, frame-rate scale and drift per quarter against the video's audio, with a verdict. |
| `sync_check.py <reference.srt> a.srt [b.srt ...]` | The same against another subtitle's timing, when there is no video. |
| `fix_hebrew_srt.py in.srt out.heb.srt [--shift S] [--drop-cue N]` | Fix punctuation order, shift, drop cues, write UTF-8 with BOM and RTL marks, verify. |

Python 3.10+ standard library. Checking against a video needs `ffmpeg` and `ffsubsync`
(`pip install ffsubsync`); the audio is extracted once and cached.

## Steps

1. **Check the fit, if there is a video.** `sync_check.py <video> <subtitle(s)>`. Verdicts:
   - "fits as-is": no shift.
   - "fits with shift": one constant offset fixes it; it prints the `--shift` value. A large offset
     alone (+27 s) is fine: releases differ in studio logos before the film.
   - "drifts / cut differs" or "frame-rate mismatch": a shift is not enough. Pick another file if you
     have one, and say so if you don't.
   No video? Measure against a subtitle synced to the user's exact release (same group):
   `sync_check.py <that.srt> <this.srt>`. A subtitle for any other release, even the same source, only
   shows that those two agree, not that either fits the user's copy; without an exact-release reference,
   say the timing is unverified. A reference from the same family (a twin, or another file from the same
   zip) proves nothing either. Trust the per-quarter numbers, not the last cue: files often differ only
   in a credits cue at the end.
   With several candidates, measure them all in one run and prefer the better translation that fits.
2. **Fix it.** `fix_hebrew_srt.py in.srt out.heb.srt --shift <value from step 1>`. It must print
   `verify: OK`; if not, it names the line: fix that line by hand in the output, keeping the RLE/PDF marks
   around the text.
3. **Read what it lists.**
   - "check by eye" cues: unbalanced brackets, lines starting with a digit or Latin letter, and
     multi-part numbers. The visual format scrambles those; fix any that read wrong, keeping the RLE/PDF
     marks around the text.
   - Multi-part numbers in a visual-order file (a score "1-2", a date range "30-29 במאי", a phone number
     in dash-separated groups) often have their parts in reverse order. Read each against the scene: May
     29-30 should read "29-30 במאי", and the score of the race just shown decides "1-2" vs "2-1". A file
     can reverse some and not others. With no frame to look at, use what you know (real dates) and say so.
     Reverse the groups by hand; leave single numbers alone.
   - Lines that already ended with punctuation in a visual-order file were probably typed in normal order.
     If the sentence runs into the next cue, its `...` belongs at the end.
   - A cue it says looks like release info ("BluRay / BRRip ... FPS"): run again with `--drop-cue N` added;
     it overwrites the output. Keep real credits (translator, syncer, "צפייה נעימה").
   - Order: settle `--shift` and `--drop-cue` first, because each run overwrites the output; make hand
     edits last, in the final file. `--drop-cue` takes source cue numbers; the check-by-eye list uses the
     output's numbers, which are the ones you edit.
4. **Name and place it.** `<video file name without extension>.heb.srt` next to the video (or
   `Title (Year).heb.srt` in a Kodi movie folder). `.heb`, not `.he`.
5. **Report:** the shift, the sync verdict (or that it is unverified), and anything fixed by hand.

## Mistakes that happened without this skill

| Mistake | Instead |
|---|---|
| Only converted cp1255 to UTF-8 | Also flip the punctuation and add the BOM and RTL marks; `fix_hebrew_srt.py` does all three |
| Stripped the RLM marks before flipping punctuation, garbling lines like `."‏-כן` | Keep them; in visual files they mark where the wrong-end punctuation stops |
| Checked drift by matching part of a subtitle against the whole audio; it locked onto end-credits music (+57 s) | `sync_check.py` matches each quarter against that quarter's own audio |
| Rewrote the timing with ffsubsync's output file | Measure with ffsubsync, then apply one `--shift`; the text and cue layout stay exactly as written |
| Named it `.he.srt` | `.heb.srt` |
