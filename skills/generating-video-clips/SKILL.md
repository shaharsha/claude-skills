---
name: generating-video-clips
description: Use when turning a still image, illustration, comic panel or character art into a short animated clip (image-to-video), choosing a video model or provider (Gemini Omni, Veo, Seedance, Kling, ElevenLabs Flows) or hitting their API gates, lip-syncing a character's mouth to existing dialogue audio (Sync, fal.ai, active speaker), or fixing a generated clip with artifacts - duplicated props, a door or a second figure appearing, hands through bodies, glowing eyes, a gesture repeated at the start, a sudden scene cut.
---

# Generating video clips (still to clip, then lip-sync)

## Overview

A finished still becomes a 4-9 s clip with an image-to-video model. Then, if a character talks on screen, a lip-sync model re-times their mouth to your own dialogue. You cannot watch the result: judge every clip from extracted frames (`scripts/take_sheet.py`, and the viewing-videos skill), and let the human have the final say on motion.

**Requirements:** Python 3 (stdlib only) and ffmpeg/ffprobe. Keys go in env vars: `GEMINI_API_KEY` (a Google AI Studio key; an image-scoped one works, and `GEMINI_IMAGE_API_KEY` is read as a fallback) for Omni, and `FAL_KEY` (the full key exactly as fal shows it) for lip-sync. Never print them.

## Choose the model

| Model | Reached through | Use for | Notes |
|---|---|---|---|
| **Gemini Omni Flash 1.1** (`gemini-omni-1.1-flash`) | Google Interactions API, AI Studio key | **Default** for illustrated, anime and cartoon stills; also worked on a photoreal still (one test) | keeps art style and faces; any input aspect (a 2:3 still came back as clean 9:16, so no need to outpaint or crop first); 720p 9:16 or 16:9; synchronous, ~25-35 s per clip; adds its own audio (mute it) |
| Veo 3.1 / Veo 3.1 Fast | Gemini API, image as the start frame | photoreal stills | not used in our runs; check current docs first |
| Seedance 2.5 | ElevenLabs Flows, or ByteDance directly | alternative look | needed account approval when tried |
| Any model inside ElevenLabs Flows | ElevenLabs API | one key for everything | API access needs the Pro plan (402 `paid_plan_required`) and the key's `image_video_generation` permission (401 without it); Omni there is app-only |

For lip-sync, **Sync 3 on fal** (`fal-ai/sync-lipsync/v3`) is the default. It works video-to-video, so it keeps the clip's motion and re-times only the mouth. Comparison and prices: `references/providers.md`.

## Animate a still

```bash
python3 <this-skill-dir>/scripts/omni_generate.py jobs.json clips/ [--takes 3] [--only S05]
```
```json
{"base": "Bring this still to life as it is: same art style, palette, light and layout, and every character keeps the face, hair, build and clothes they have in it. Natural, fluid movement. Nothing written on screen, no speech bubbles, nobody new, one continuous shot. ",
 "jobs": {"S05": {"image": "panels/p05.png",
                  "prompt": "[0-3s] The woman in the red jacket lifts the phone and talks, excited. [3-6s] The friend in the green hoodie leans back on the sofa and laughs. Slow camera push-in."}}}
```
How to write the prompt (full guide with examples in `references/gemini-omni.md`):
- **A per-second timeline**, one beat per bracket. The clip runs about as long as the timeline.
- **Name people by what they wear**, never by name: the model doesn't know who "Dana" is.
- **Say "talks"** for anyone who will be lip-synced, so the mouth already moves.
- **Pin what must not change**: "the camera stays still", "one single window on the left wall", "exactly ONE hooded figure", "her hands stay flat on the table". Each pin in `references/failure-modes.md` came from a real failure.

## Review every take before using it

```bash
python3 <this-skill-dir>/scripts/take_sheet.py sheet review/S09.jpg clips/S09_t1.mp4 clips/S09_t2.mp4 clips/S09_t3.mp4 --times 0.3,1,2,3,4,5,6
```
Read the sheet: rows are takes, columns are times. Look for props that double, doors or people that appear, hands crossing bodies, faces that drift, and a gesture done twice. Name the exact second of each problem, because the fix depends on where it is.

A hard cut is easy to miss between sampled frames. List them directly; no output means one continuous shot:
```bash
ffmpeg -i clips/S09_t1.mp4 -vf "select='gt(scene,0.3)',showinfo" -an -f null - 2>&1 | grep pts_time
```

## Fit a clip to its shot

An edit needs a clip that fills its shot exactly, at the edit's frame rate:

| Problem | Fix |
|---|---|
| Bad start (a gesture done before its line, a doubled prop in the first second) | Start later: `--off 1.5`. |
| Too short after trimming | Slow it with `--speed 1.22` (up to ~1.25 reads fine); the last frame is held. |
| Bad middle | Split the shot: play the first line on a crop that keeps the problem out of frame, then cut back after it. |
| Unfixable (a door appears, a second person walks in) | Regenerate with a pinned prompt, 2-3 takes, and pick on a sheet. |

`lipsync_parts.py normalize clip.mp4 shot.mp4 --frames N --off S --speed K` does the offset, speed, fps, scale (cover and center-crop, never stretch) and last-frame hold in one step, and always returns exactly N frames.

## Lip-sync dialogue

1. **Normalize** the clip to the shot: `python3 <this-skill-dir>/scripts/lipsync_parts.py normalize clip.mp4 shot.mp4 --frames 132 --off 1.5 --speed 1.22`.
2. **Split** at line boundaries so each part has one speaker.
   - Write `shot.json`: each line with its start/end in the shot (seconds) and its speaker; `frames` equals the `--frames` you normalized to. Add `"skip": true` for a speaker seen from behind, off screen, or a crowd shout:
     ```json
     {"id": "S05", "video": "shot.mp4", "fps": 24, "frames": 132,
      "lines": [{"id": "05-1", "audio": "lines/05-1.mp3", "start": 0.72, "end": 2.31, "speaker": "maya"},
                {"id": "05-2", "audio": "lines/05-2.mp3", "start": 2.43, "end": 4.10, "speaker": "ido"}]}
     ```
   - Run `lipsync_parts.py split shot.json parts/`. Besides the parts it writes `parts/S05_lipsync_jobs.json`: one entry per **non-skip** part, with absolute paths, `out` already named the way join expects (`synced/S05_<k>.mp4`), and `face: null`.
3. **Point at the speaker** in each part, and write it into that jobs file as `"face": "x,y@<mid>"` (`mid` is in each entry).
   - Pick a pixel on their face on the part's middle frame.
   - Confirm it: `take_sheet.py point parts/S05_1.mp4 check.jpg --frame 30 --xy 410,560`, then read the image.
   - Face detectors are unreliable on drawn faces, so pick and confirm by eye. Leave `null` only when one face is visible.
4. **Sync**: `lipsync_fal.py --jobs parts/S05_lipsync_jobs.json`. Expect ~$0.13 per second and ~70-150 s per part; 6 run in parallel. Existing outputs are skipped. To redo one part after correcting its face, run that part alone: `lipsync_fal.py parts/S05_1.mp4 parts/S05_1.wav synced/S05_1.mp4 --face 410,560@30 --force` (`--force` with `--jobs` would redo every part).
5. **Join**: `lipsync_parts.py join parts/S05_plan.json synced/ final/S05.mp4`. Each part is forced to its exact frame count, skipped parts keep their original frames, a part with no synced file is reported (`--strict` makes that an error), and the total frame count is checked.

Details, model choice and failure cases: `references/lipsync.md`.

## Costs and times (measured 2026-10)

| Step | Count | Cost | Time |
|---|---|---|---|
| Omni clip | per second of output video (a 6 s clip is ~$0.60; plan ~1.5 calls per shot for retakes) | ~$0.10 | ~30 s per call, 4 in parallel |
| Sync 3 lip-sync | per second of output (a part is typically 3-6 s) | ~$0.13 | ~70-150 s per part, 6 in parallel |

## Common mistakes

| Mistake | Result | Fix |
|---|---|---|
| Naming characters in the video prompt | the wrong person moves | describe them by clothes |
| Keeping Omni's audio | invented voices and music under your dialogue | mute it (`-an`) |
| Using a take without a sheet | doubled props and new doors ship | sheet every take |
| Re-rolling the whole clip for a bad first second | new problems elsewhere | offset plus slow-down |
| Lip-syncing a whole two-speaker shot | one mouth moves for both lines | split at line boundaries, one speaker per part |
| Letting the model pick the speaker | the wrong face talks | `--face X,Y@FRAME` |
| Shortening the fal key | 401 | pass the key exactly as fal shows it |
| Joining parts without fixing frame counts | the shot drifts out of sync with the edit | `lipsync_parts.py join` |

## Related skills

- [image-generation](../image-generation): the stills (character cards, panels).
- [elevenlabs-tts](../elevenlabs-tts): the dialogue the mouths sync to.
- [viewing-videos](../viewing-videos): frame extraction for reviewing clips.
- [producing-animated-episodes](../producing-animated-episodes): the whole episode workflow that uses these clips.
