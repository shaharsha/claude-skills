# fixing-hebrew-subtitles

Make a Hebrew subtitle file display correctly in Kodi, VLC, Plex or a TV, and match your video: check the timing against the audio, shift it, and fix the punctuation, encoding and right-to-left marks without touching a word.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Most Hebrew subtitles on the web were written for players without right-to-left support:

- **Visual order.** Punctuation is typed at the wrong end of each line (`.טקסט`, `...הפכפכים`, `טקסט-`) so it looked right on an old left-to-right player. A modern player shows it reversed.
- **cp1255 encoding.** Without a BOM, players often read it as Latin and show gibberish.
- **Someone else's release.** The file is synced to the uploader's copy. On yours it can be 5 or 27 seconds off, or drift when the cut differs.

Re-encoding to UTF-8 fixes only the second problem. Flipping punctuation naively garbles lines that use RLM marks, brackets or numbers. And checking sync by matching part of a subtitle against a whole film can lock onto end-credits music and report a drift that isn't there.

## What it does

```
subtitle(s) + video (or a reference subtitle)
        │
   sync_check ── ffsubsync on the whole audio ──▶ offset + frame-rate scale
        │       then each quarter against that quarter's own audio ──▶ drift
        │       verdict: fits as-is · fits with shift · drifts / cut differs
        ▼
   fix_hebrew_srt ── decode cp1255/UTF-8 · detect visual order · flip edge punctuation (keeping RLM, mirroring brackets)
        │            shift · drop a release-info cue · UTF-8 BOM + RLE/PDF marks
        ▼
   verify (same cues, same text, no line starts with punctuation) + a short list to check by eye
        ▼
   <video name>.heb.srt next to the video
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install fixing-hebrew-subtitles@shaharsha-skills
```

That installs only this skill. For the whole `utilities` bundle, which includes downloading-ktuvit-subtitles, run `/plugin install utilities@shaharsha-skills` instead.

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/fixing-hebrew-subtitles" ~/.claude/skills/fixing-hebrew-subtitles
```

## Requirements

- Python 3.10+, standard library only.
- To check against a video: `ffmpeg` and `ffsubsync` (`pip install ffsubsync`). The audio is extracted once to `/tmp/hebrew-subs-sync/` (or `$HEBREW_SUBS_CACHE`) and reused; subtitle-only checks write nothing.

## Quick start

Ask naturally:

- "the Hebrew subtitle shows periods on the wrong side in Kodi"
- "this srt is a few seconds late, fix it: ~/Movies/Rush (2013)/Rush.mkv"
- "which of these three subtitles fits my file best?"

Or run the scripts yourself:

```bash
F=skills/fixing-hebrew-subtitles/scripts
python3 $F/sync_check.py movie.mkv a.srt b.srt           # or, with no video: sync_check.py exact-release.srt a.srt
python3 $F/fix_hebrew_srt.py a.srt "movie.heb.srt" --shift 5.04 --drop-cue 1
```

## Gotchas

- **Keep the RLM marks.** In visual files the uploader's RLM (U+200F) marks where the wrong-end punctuation stops (`."‏-כן` is `-כן ... ."`). Stripping it first garbles the line.
- **An odd line typed in normal order** inside a visual file (`...` that continues into the next cue) gets flipped like the rest. The script lists those so you can fix them by hand.
- **A big offset is normal.** Releases differ in studio logos before the film; +27 s with no drift is a clean fit.
- **A reference from the same release family proves nothing.** Two syncs from one zip agree with each other by construction.
- **Name it `.heb.srt`**, not `.he.srt`.

## What's in the box

| File | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | The procedure the agent follows: measure, fix, read the flags, name. |
| [scripts/sync_check.py](scripts/sync_check.py) | Offset, frame-rate scale and per-quarter drift, against audio or a reference subtitle. |
| [scripts/fix_hebrew_srt.py](scripts/fix_hebrew_srt.py) | Punctuation flip, shift, cue drop, UTF-8 BOM + RTL marks, verification. |

## Related skills

- [downloading-ktuvit-subtitles](../downloading-ktuvit-subtitles): getting the subtitle in the first place.
- [elevenlabs-stt](../elevenlabs-stt): making a Hebrew subtitle from the audio when no file fits.

## License

MIT — see [LICENSE](../../LICENSE).
