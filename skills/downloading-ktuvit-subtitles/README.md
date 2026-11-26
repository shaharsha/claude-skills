# downloading-ktuvit-subtitles

Get the right Hebrew subtitle from [ktuvit.me](https://www.ktuvit.me) for a movie or TV episode, check that it fits your video, and make it play correctly in Kodi.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

ktuvit is the main Hebrew subtitle site, and a popular title can have 40+ entries. Three things go wrong when an agent handles it without help:

- **It picks badly.** The list mixes professional studio translations (`תרגום: אולפנים`) with fan translations, many synced to different releases. Entries that look different are often one file under several release names: for Rush (2013), 44 entries were 7 files. An agent without guidance downloaded all 44, or called a fan sub "the most downloaded" when a studio translation had almost twice the downloads.
- **The file isn't ready for Kodi.** Most ktuvit subtitles are cp1255 in "visual" order, with punctuation typed at the wrong end of each line (`.טקסט`). Kodi shows that reversed, and without a BOM it can misread the Hebrew.
- **Sync checks fool you.** A subtitle synced to another release can be off by 5 or 27 seconds. Matching part of a subtitle against the full audio can lock onto end-credits music and report a +57 s "drift" that isn't there.

## What it does

```
title / video file ──search──▶ ktuvit ID ──list──▶ rows sorted by downloads
                                                    translator · syncer · release · "same file as #n"
                                                              │
                                              shortlist 1-3 (studio + best release match)
                                                              │
                                                          download (retries ktuvit's "request not found")
                                                              │
                 sync_check: against the video's audio, or against the exact-release subtitle
                       offset · frame-rate scale · drift per quarter · verdict
                                                              │
         prepare_for_kodi: flip punctuation · shift · drop release-info cue · UTF-8 BOM + RTL marks · verify
                                                              │
                                                   <video name>.heb.srt next to the video
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install downloading-ktuvit-subtitles@shaharsha-skills
```

That installs only this skill. For the whole `utilities` bundle, run `/plugin install utilities@shaharsha-skills` instead.

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/downloading-ktuvit-subtitles" ~/.claude/skills/downloading-ktuvit-subtitles
```

## Requirements

- Python 3.10+, standard library only. The login hash uses the `openssl` command (on macOS and Linux by default), or the `cryptography` package if installed.
- A ktuvit.me account. Searching works without one; listing and downloading don't.
- For checking sync against a video: `ffmpeg` and `ffsubsync` (`pip install ffsubsync`).

**Login.** The scripts read `KTUVIT_EMAIL` and `KTUVIT_PASSWORD`, or a [Proton Pass](../proton-pass) login item (default title `ktuvit` in vault `Personal`; change with `--pass-item` / `--vault` or `KTUVIT_PASS_ITEM` / `KTUVIT_PASS_VAULT`). The site logs in by email. The password is never printed.

## Quick start

Ask naturally:

- "get me Hebrew subs for Prisoners.2013.1080p.BluRay.x264-SPARKS.mkv"
- "find the ktuvit subtitle that best fits this file and make it ready for Kodi: ~/Movies/Rush (2013)/Rush.mkv"
- "the Hebrew subtitle shows periods on the wrong side in Kodi"

Or run the scripts yourself:

```bash
S=skills/downloading-ktuvit-subtitles/scripts
python3 $S/ktuvit.py search "Prisoners" --year 2013
python3 $S/ktuvit.py list AB164A8239ABDA7F8854339FEC9231B1
python3 $S/ktuvit.py download AB164A8239ABDA7F8854339FEC9231B1 <subtitle_id> -o studio.srt
python3 $S/sync_check.py movie.mkv studio.srt                 # or: sync_check.py exact-release.srt studio.srt
python3 $S/prepare_for_kodi.py studio.srt "movie.heb.srt" --shift 5.04 --drop-cue 1
```

For an episode: `search "Breaking Bad" --series`, then `list <series_id> --season 2 --episode 3`, and download with the series ID.

## Gotchas

- **"הבקשה לא נמצאה"** (request not found) comes back with HTTP 200 instead of the file, now and then. `download` retries; if it keeps failing, run it again later or take the entry's "same file as" twin.
- **Some entries are zips** holding several syncs, usually the ones several times bigger than the rest. `download` unpacks them into a folder.
- **A series shows `subs=0` in search.** Normal; the episodes have the subtitles.
- **Keep the RLM marks.** In visual files the uploader's RLM (U+200F) marks where the wrong-end punctuation stops (`."‏-כן` is `-כן ... ."`). Stripping it first garbles the line.
- **An odd line typed in normal order** inside a visual file (`...` that continues into the next cue) gets flipped like the rest. `prepare_for_kodi.py` lists those lines so you can fix them by hand.
- **Name it `.heb.srt`**, not `.he.srt`.

## What's in the box

| File | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | The procedure the agent follows: how to read the list, pick, measure, prepare and name. |
| [scripts/ktuvit.py](scripts/ktuvit.py) | Search, list (movies and episodes), download. |
| [scripts/sync_check.py](scripts/sync_check.py) | Offset, frame-rate scale and per-quarter drift, against audio or a reference subtitle. |
| [scripts/prepare_for_kodi.py](scripts/prepare_for_kodi.py) | Punctuation flip, shift, cue drop, UTF-8 BOM + RTL marks, verification. |

## Related skills

- [proton-pass](../proton-pass): storing the ktuvit login.
- [elevenlabs-stt](../elevenlabs-stt): making a Hebrew subtitle from the audio when ktuvit has nothing usable.

## License

MIT — see [LICENSE](../../LICENSE).
