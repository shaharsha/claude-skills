# generating-video-clips

Turn a finished still (a character card, a comic panel, an illustration) into a short animated clip, review every take without watching it, fit clips to their shots frame-exactly, and lip-sync characters to your own dialogue.

## Why this exists

Image-to-video models are good enough for stylized art now, but the hard parts sit around the call:
- reaching the model at all (plan gates, app-only models)
- writing a motion prompt it follows
- catching the artifacts it invents (a second door, a doubled prop, a hand through a body)
- making a clip exactly as long as its shot
- getting the right character's mouth to move with your audio

This skill is what a full animated episode taught about each of those.

## What it does

| Script | What it does |
|---|---|
| `scripts/omni_generate.py` | Still to 4-9 s clip with Gemini Omni Flash 1.1 through Google's Interactions API; multiple takes; never overwrites; retries 429/5xx; no partial files |
| `scripts/take_sheet.py` | `sheet`: one image with rows = takes and columns = times, for comparing takes. `point`: a frame with a box at a pixel, to confirm a lip-sync speaker point |
| `scripts/lipsync_parts.py` | `normalize`: clip to exactly N frames (offset, slow-down, fps, scale, last-frame hold). `split`: shot into one-speaker parts with padded audio. `join`: synced parts back together, frame-exact |
| `scripts/lipsync_fal.py` | Sync 3 lip-sync on fal (`fal-ai/sync-lipsync/v3`) with a speaker point; upload, queue, poll, download; batch with `--jobs` |

All four are Python standard library plus ffmpeg. No SDKs.

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install video-production@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/generating-video-clips" ~/.claude/skills/generating-video-clips
```

## Requirements

- Python 3 and ffmpeg/ffprobe (7 or newer).
- `GEMINI_API_KEY`: a Google AI Studio key, for Omni.
- `FAL_KEY`: the full fal key, exactly as fal shows it, for lip-sync.
- Keys come from the environment only and are never printed.

## Quick start

```bash
# 1. animate (jobs.json: {"base": "...", "jobs": {"S05": {"image": "panels/p05.png", "prompt": "[0-3s] ..."}}})
python3 scripts/omni_generate.py jobs.json clips/ --takes 2

# 2. look at the takes, pick one
python3 scripts/take_sheet.py sheet review/S05.jpg clips/S05_t1.mp4 clips/S05_t2.mp4

# 3. fit the chosen take to the shot, then split it into one-speaker parts
python3 scripts/lipsync_parts.py normalize clips/S05_t2.mp4 parts/S05_full.mp4 --frames 132 --off 0.5
python3 scripts/lipsync_parts.py split S05.json parts/

# 4. split wrote parts/S05_lipsync_jobs.json (non-skip parts only): set each "face" to "x,y@<mid>", sync, then join
python3 scripts/lipsync_fal.py --jobs parts/S05_lipsync_jobs.json
python3 scripts/lipsync_parts.py join parts/S05_plan.json synced/ final/S05.mp4
```

## Gotchas

- **Name people by clothes in the motion prompt**, not by name: the model doesn't know your characters.
- **Mute the clip.** Omni invents its own audio track.
- **Sheet every take.** Doubled props, new doors and second figures are common, and they are easy to see on a sheet and easy to miss otherwise.
- **A bad first second is an offset, not a re-roll.**
- **Lip-sync one speaker per part, with a point on their face.** A two-person shot synced whole animates one mouth for both lines.
- **fal's older upload path started failing in 2026-10** (`storage_type=gcs` returns 400). The script uses the CDN-token flow the official client uses today.

## Related skills

- [image-generation](../image-generation): the stills.
- [elevenlabs-tts](../elevenlabs-tts): the dialogue.
- [viewing-videos](../viewing-videos): seeing a video through frames.

## License

MIT
