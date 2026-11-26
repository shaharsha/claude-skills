# downloading-ktuvit-subtitles

Find and download the right Hebrew subtitle from [ktuvit.me](https://www.ktuvit.me) for a movie or TV episode, without downloading the whole list.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

ktuvit is the main Hebrew subtitle site, and a popular title can have 40+ entries. Picking well is the hard part:

- The list mixes professional studio translations (`תרגום: אולפנים`) with fan translations, each synced to some release.
- Entries that look different are often one file under several release names. For Rush (2013), 44 entries were 7 files.
- Without guidance, an agent downloaded all 44, or called a fan sub "the most downloaded" when a studio translation had almost twice the downloads.
- About 60% of single download requests come back as an 83-byte "הבקשה לא נמצאה" (request not found) page with HTTP 200, which is easy to save as if it were the subtitle.

This skill reads the list the way an experienced viewer does (translator, release, downloads, duplicates), downloads 1-3 files, and hands back the file as ktuvit serves it.

It does not change the file. To make it display right or match your video, use [fixing-hebrew-subtitles](../fixing-hebrew-subtitles).

## What it does

```
title / video file ──search──▶ ktuvit ID ──list──▶ rows sorted by downloads
                                                    translator · syncer · release · "same file as #n"
                                                              │
                                              shortlist 1-3 (studio + best release match)
                                                              │
                                     download (retries "request not found", unpacks zips)
                                                              │
                                              <video name>.heb.srt, as downloaded
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install downloading-ktuvit-subtitles@shaharsha-skills
```

That installs only this skill. For the whole `utilities` bundle, which includes fixing-hebrew-subtitles, run `/plugin install utilities@shaharsha-skills` instead.

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/downloading-ktuvit-subtitles" ~/.claude/skills/downloading-ktuvit-subtitles
```

## Requirements

- Python 3.10+, standard library only. The login hash uses the `openssl` command (on macOS and Linux by default), or the `cryptography` package if installed.
- A ktuvit.me account. Searching works without one; listing and downloading don't.

**Login.** The script reads `KTUVIT_EMAIL` and `KTUVIT_PASSWORD`, or a [Proton Pass](../proton-pass) login item (default title `ktuvit` in vault `Personal`; change with `--pass-item` / `--vault` or `KTUVIT_PASS_ITEM` / `KTUVIT_PASS_VAULT`). The site logs in by email. The password is never printed.

## Quick start

Ask naturally:

- "download the Hebrew sub from ktuvit for Prisoners.2013.1080p.BluRay.x264-SPARKS"
- "which Hebrew subtitle on ktuvit fits Breaking.Bad.S02E03.720p.BluRay.x264-DEMAND?"

Or run the script yourself:

```bash
K=skills/downloading-ktuvit-subtitles/scripts/ktuvit.py
python3 $K search "Prisoners" --year 2013
python3 $K list AB164A8239ABDA7F8854339FEC9231B1
python3 $K download AB164A8239ABDA7F8854339FEC9231B1 <subtitle_id> -o Prisoners.heb.srt
```

For an episode: `search "Breaking Bad" --series`, then `list <series_id> --season 2 --episode 3`, and download with the series ID.

## Gotchas

- **"הבקשה לא נמצאה"** comes back instead of the file on most single tries, from any client. `download` retries up to 10 times with a fresh request each time; if it still fails, wait a minute or take the entry's "same file as" twin.
- **Some entries are zips** holding several syncs, usually the ones several times bigger than the rest. `download` unpacks them into a folder.
- **A series shows `subs=0` in search.** Normal; the episodes have the subtitles.
- **Search returns near-misses** ("Rushlights" for "Rush"). Match year and IMDb ID.
- **Name it `.heb.srt`**, not `.he.srt`.

## What's in the box

| File | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | The procedure the agent follows: how to read the list, shortlist, download and name. |
| [scripts/ktuvit.py](scripts/ktuvit.py) | Search, list (movies and episodes), download. |

## Related skills

- [fixing-hebrew-subtitles](../fixing-hebrew-subtitles): sync check, shift, punctuation and encoding fixes for players.
- [proton-pass](../proton-pass): storing the ktuvit login.
- [elevenlabs-stt](../elevenlabs-stt): making a Hebrew subtitle from the audio when ktuvit has nothing usable.

## License

MIT — see [LICENSE](../../LICENSE).
