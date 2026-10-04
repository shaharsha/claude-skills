# The pipeline, phase by phase

Every command below is `python3 <this-skill-dir>/engine/episode.py PROJECT <command>`, written as `episode.py ...`. PROJECT is the folder holding `episode.json`. Costs and times were measured in 2026-10; a "gate" is a stop where you send something to the human and wait.

## 1. Story and script

- **In:** the request, plus any source material (a chat export, photos, notes).
- **Do:** draft `script.md` from `templates/script.template.md` (rules: `script-writing.md`).
- **Gate:** the human approves the script and answers the open questions. Every private or sensitive detail you found in the source is confirmed or dropped.
- **Out:** `script.md`, then the `lines` list and a first `shots` list in `episode.json`.

## 2. Character bible

- **Do:** fill `templates/characters.template.md`, and copy each character's prompt fields into `episode.json` `characters`.
- **For real people:** collect 1-3 photos each. Crop the faces with image-generation's `scripts/crop_faces.py photos/ faces/ --sheet faces/_sheet.jpg`, ask which crop is whom, rename the chosen ones `faces/<id>-1.png`, and list them in `refs`.
- **For invented characters:** leave `refs` empty; the face prompt then works from `likeness` alone.

## 3. Faces, cards, promote

```bash
episode.py PROJECT chars face            # 2 face options per character (Flare)
episode.py PROJECT chars card maya=maya-face-2.png ido=ido-face.png   # costume card from the chosen face
episode.py PROJECT chars final maya ido  # promote approved cards (Sunburst max) into characters/final/
```
- **Gate:** the likeness of every card, on one sheet (`ffmpeg -pattern_type glob -i 'characters/*-card.png' -vf scale=256:-2,tile=6x3 cards.jpg`). Judge faces on zoomed crops. Expect retakes on about one card in four. When the human asks for a change ("a bit fuller face"), put it in `face_adjust` and rerun only that card.
- **Cost:** about $0.30 per character with retakes; under a minute per batch of 5.

## 4. Panels

```bash
episode.py PROJECT panels draft          # 2+ characters: Sunburst high, otherwise Flare
episode.py PROJECT panels final p01 p02  # promote the approved ones
```
- **Gate:** every panel, on a sheet. A recurring room or prop is described once and pasted verbatim (see image-generation, multi-character scenes).
- **Cost:** about $0.25-0.30 per panel with retakes.

## 5. Voices

- One sample line per voice, in that character's register: add them to `lines` (ids like `00-maya`) and run `episode.py PROJECT lines 00-maya 00-ido`. Without ids, `lines` regenerates every line.
- **Gate:** the human hears every voice before any batch.
- Settle the shared `voice` settings (one model, one stability, `language_code`, `tempo`).

## 6. Lines

```bash
episode.py PROJECT lines                 # all lines; or: episode.py PROJECT lines 02-1 05-3
```
This generates every line in its speaker's voice, mixes crowd lines, applies the tempo, then trims and levels the lines marked `trim`/`level`. The originals stay in `paths.lines_raw`, with `_scripts.json` (the exact TTS text), so the leak check runs as is:
```bash
python3 <elevenlabs-tts>/scripts/check_tags_spoken.py audio/lines_raw/_scripts.json audio/lines_raw --prefix "" --language-code he
```
- **Gate:** the full set by ear, with timestamps. For names and loanwords, use A/B files (elevenlabs-tts `ab_concat.py`), and put the winning spelling in `pronounce`.
- **Cost:** ElevenLabs bills characters (tags included); `lines` prints the count.

## 7. Music and sound effects

```bash
episode.py PROJECT sound
```
Ask for each cue's window plus 2-4 s; the build warns when a cue is shorter than its window.
- **Gate:** the music choice.
- **Cost:** ElevenLabs credits per second of music and per effect; `sound` prints what it requests. Compare your ElevenLabs usage before and after if you need exact figures.

## 8. Animatic (free)

```bash
episode.py PROJECT build                 # before any clips exist: every shot is its still panel with a camera move
```
The animatic has the real voices, timing, subtitles, cards, music and effects, with stills instead of motion. It is the cheapest place to change pace, order and line choice: a changed line costs cents now, but after animation it also costs the clips for that shot.
- **Gate:** the human watches the animatic and approves the pace, plus the video budget for the next two phases.
- **Then write the motion prompts from the real timing.** `build/timeline.json` has each shot's length and each line's start and end within it; make each shot's `[0-3s]` beats match (a character "talks" during their line, reacts outside it), and keep dialogue shots under about 8-9 s, the clip length a model holds well.

## 9. Animation

```bash
episode.py PROJECT animate               # one take per shot, straight to video/omni/<shot>.mp4
episode.py PROJECT animate S05 --takes 2 # a shot that failed: 2 more takes, S05_t1.mp4 and S05_t2.mp4
episode.py PROJECT animate pick S05 2    # install take 2 as video/omni/S05.mp4 (the old one moves to _old/)
```
Sheet every take (generating-video-clips `take_sheet.py`). Fix bad starts with `clip_off`, short clips with `clip_speed`, and bad middles by splitting the shot. Regenerate only what can't be fitted.
- **Gate:** motion, from sheets.
- **Cost:** about $0.10 per second of clip, per take: a 6 s shot is about $0.60 per take, so `--takes 2` on every shot doubles the bill. Start with one take and retake only what fails; `animate` prints the cost of what it made.

## 10. Lip-sync

```bash
episode.py PROJECT lipsync plan          # the parts: one speaker each
episode.py PROJECT lipsync prep          # cut the parts, write each part's middle frame
# read video/lipsync/parts/<shot>_<k>_mid.png, pick a pixel on the speaker's face, confirm it with
#   python3 <generating-video-clips>/scripts/take_sheet.py point video/lipsync/parts/S05_0.mp4 check.jpg --frame <mid> --xy 410,560
# then list the shot and the point in episode.json: "lipsync": {"shots": ["S05"], "faces": {"S05|0": [410, 560]}}
episode.py PROJECT lipsync run           # prints the cost, runs Sync 3 on fal for every part with a point, joins
```
Mark a line `skip` when its speaker is seen from behind, off screen, faceless, or it's a crowd. The joined shots land in `video/lipsync/final/` and the build prefers them.
- **Gate:** spot-check frames of each synced shot.
- **Cost:** about $0.13 per second of dialogue shot; 70-150 s per part, 6 in parallel.

## 11. Edit and deliver

```bash
episode.py PROJECT check                 # assets, keys, sibling skills, overlay widths
episode.py PROJECT build                 # renders missing segments, mixes, muxes, checks durations
episode.py PROJECT build --only S05,S06  # re-render just these shots
episode.py PROJECT sheet                 # 3 frames per shot, for review
```
A full build of a 3-4 minute episode takes about 4 minutes on an M-series Mac; rebuilds re-render only the shots whose inputs changed (new clips after the animatic, a promoted panel, an edited line or shot).
- **Gate:** the human watches the mp4. Collect every note from one viewing, fix them all, and rebuild once.

Then deliver:

```bash
episode.py PROJECT deliver               # build/<output>_whatsapp.mp4, about 75 MB for 3.5 minutes
```
Send the file with your file-sending tool, and offer to reveal it in Finder.
