---
name: producing-animated-episodes
description: Use when making a narrated or voiced animated video with recurring characters - an anime, cartoon or comic episode, a short for a group chat, a story video about friends, family, a class or a team - from photos, a chat export, a story idea or a script, in any visual style, Hebrew/RTL or English. Also use when such a video has subtitles or cards too fast to read, music stopping early, the ending cut off, lines buried under music, mouths out of sync, a gesture before its line, or one face bigger than the others in a group shot.
---

# Producing animated episodes

## Overview

A vertical, voiced, subtitled, animated episode: character art, panels, cloned or library voices, music, image-to-video clips and lip-sync, cut by an engine that times every shot from the real dialogue audio. One `episode.json` holds the whole project, and `engine/episode.py` runs every phase from it. The sibling skills do the provider work.

**Use the engine; don't write your own edit scripts.** Timeline, overlays, subtitles, right-to-left text, the mix, durations and lip-sync joins are already in `engine/`. It was proven by rebuilding a real 3.5-minute episode: identical frames, identical audio, and the exact length the original had missed. A hand-written edit rediscovers every bug in `references/troubleshooting.md`.

**The audio is the master.** Shot lengths, subtitle times and lip-sync parts come from the finished dialogue files. Never estimate a timing from text.

**You can't watch or hear.** You check frames, durations and numbers. The human judges likeness, voices, pronunciation, timing and jokes. Plan their gates and keep them.

**Requires:**
- These skills next to this one: image-generation, elevenlabs-tts, generating-video-clips.
- Python 3 with `pip install -r <this-skill-dir>/requirements.txt` (Pillow built with RAQM, numpy; OpenCV optional).
- ffmpeg 7 or newer.
- Fonts: styles and subtitles name font keys (`bold`, `hblack`, `black` in the example) that `fonts` maps to installed `.ttf` files. For Hebrew and Latin, Rubik and Heebo (free, Google Fonts) work well; `check` blocks on a missing one.
- Keys in env vars, set in every shell that runs the engine: `OPENAI_IMAGE_API_KEY`, `ELEVENLABS_API_KEY`, `GEMINI_API_KEY`, `FAL_KEY`.

To see the whole pipeline work with no API calls, run `python3 <this-skill-dir>/engine/episode.py /tmp demo`, then `check` and `build` the demo project it creates.

## The pipeline and its gates

Every gate is a stop: send the artifact, ask, wait. Commands are `python3 <this-skill-dir>/engine/episode.py PROJECT <command>`. Costs measured 2026-10.

| # | Phase | Command | Gate (the human) | Cost |
|---|---|---|---|---|
| 1 | Story and script | `script.md` from `templates/script.template.md` | the script, and every sensitive topic | - |
| 2 | Character bible | `templates/characters.template.md`, then `characters` in episode.json | - | - |
| 3 | Faces, cards, promote | `chars face`, `chars card key=face.png`, `chars final keys` | likeness, on one sheet of all cards | ~$0.30 per character |
| 4 | Panels | `panels draft`, then `panels final ids` | every panel, on a sheet | ~$0.30 per panel |
| 5 | Voices | one sample per voice (elevenlabs-tts) | every voice, by ear, before the batch | cents |
| 6 | Lines | `lines` | the set by ear, with timestamps; names A/B | cents to a few $ |
| 7 | Music and SFX | `sound` | the music | cents |
| 8 | **Animatic** | `build` (no clips yet: stills with camera moves) | **pace and order, before any video spend** | free |
| 9 | Animation | `animate`, sheets, retakes with `animate S --takes 2` + `animate pick S K` | motion, from sheets | ~$0.10 per second of clip, per take |
| 10 | Lip-sync | `lipsync prep`, face points in config, `lipsync run` | spot-check frames | ~$0.13 per second |
| 11 | Edit and deliver | `build`, `sheet`, `deliver` | the human watches the mp4 | free |

Commands, inputs, outputs and failure handling for each phase: `references/pipeline.md`.

## Writing the script

Rules that held up (details and a worked example: `references/script-writing.md`):
- **A hook in the first 3-4 seconds** (a cold open on the problem), then the title. Under 30 seconds, put the title and end card as overlays on story shots and skip the montage.
- **Every recurring character speaks at least once.** An intro montage, one word each in their own voice at about 1.2-1.5 s per card, is cheap and loved.
- **On-screen text must be readable:** about 0.8 s plus 0.06 s per character; 1.2-1.5 s for a short card; 4-6 s for a final caption. Give cards a `mindur`.
- **Plant clues early and pay them off.** Callbacks to a group's real running jokes land hardest.
- **Sensitive topics are the user's call.** List every private detail you'd like to use (health, money, relationships, family, fights), ask about each, and use only what they confirm.
- **Lines of 12 words or fewer, numbers in words.** On-screen text stays in normal spelling; pronunciation fixes go in `pronounce`.
- **Music and sound effects, even for narration.** At least one music bed and a few effects (whooshes on cuts, a hit on the reveal); a silent bed sounds unfinished.

## episode.json in one screen

`templates/episode.example.json` is a complete small episode; every key is in `references/config-schema.md`. The parts you edit most:
- `characters`: display name, color, voice, and the prompt fields from the character bible.
- `speakers`: voices that are never drawn, such as a narrator (`{"display": null, "voice": "<id>"}` gives subtitles without a name).
- `lines`: id, speaker, text with audio tags; `trim` and `level` on one-word lines.
- `shots`: image, lines (`"02-3@-0.4"` overlaps the previous line), pads, `mindur`, camera, fx, sfx, overlays, clip offset and speed.
- `music_cues`: `[cue, from shot, to shot, volume, offset]`. The build warns when a cue is shorter than its window.
- `lipsync`: which shots, which lines to skip, one face point per part.
- `prompts`: override `char_style` and `panel_style` for a different look (3D cartoon, watercolor, photoreal).

## Building and reviewing

- **Batch the fixes.** A full build takes minutes. Collect every note from a review round (a line take, a pad, a clip offset), apply them all, then rebuild once.
- **Segments are cached and tracked.** `build` re-renders exactly the shots whose inputs changed: a new clip or lip-synced version, a promoted panel, an edited line, shot or style. `build --only S05,S06` forces those shots; `--force` re-renders everything.
- **A lip-synced shot is redone after any change to its clip, offset, speed or lines:** `lipsync prep S05 && lipsync run S05`. Until then the build warns it is stale and uses the raw clip.
- **Regenerating an existing asset needs `--force`** (`sound theme --force`, `animate S05 --force`); without it, existing files are kept and only gaps are filled.
- **Review with sheets.** `sheet` puts 3 frames per shot on a page. When the human names a moment by time, extract and read those frames before answering (`ffmpeg -ss T -i build/<output>.mp4 -frames:v 1 f.jpg`).
- **`check` before every build:** missing assets, keys, sibling skills, and overlay text wider than the frame.
- **Durations are verified at the end of every build.** Audio shorter than video fails the build instead of cutting the ending.
- **Before sending:** `references/qa-checklist.md`.

## Working with the human

- Send every artifact with your file-sending tool and offer to reveal it in Finder; don't just print a path. The final step is `deliver` and sending that file.
- For audio, say what to listen for and where ("at 0:41, does Dani's name sound right?"). Never claim you heard it.
- Pronunciation and voice choices are theirs: A/B files with timestamps (elevenlabs-tts).
- Before each paid phase, give the cost estimate; after it, the running total.

## When something looks wrong

| Symptom | Fix |
|---|---|
| Cards or captions too fast to read | raise `mindur` / `post`: ~1.2-1.5 s per short card, 4-6 s for the final caption |
| A title clipped at both edges | `check` warns; lower the style's `size` or add `wrap` |
| Music stops before the section ends | the build warned: raise the cue's `seconds`, `sound <cue> --force`; or split the section into two cues |
| The ending is cut off | can't happen with the engine (exact-length mix, duration check); in hand-made muxes, see deck-to-video |
| A line is buried under music | `level_clips.py --report` on that line, then a firmer take; lower that cue's volume |
| A character points or acts before their line | `clip_off` past it, or split the shot and crop the first part with `clip_cam` |
| Mouths don't move with the words | lip-sync phase; if the wrong mouth moves, fix its face point |
| One face bigger in the group shot | install OpenCV (faces are equalized), or `mirror` a card whose prop covers a neighbor |
| Hebrew renders reversed or unjoined | Pillow without RAQM: `check` says how to fix it |
| A name or loanword mispronounced | a `pronounce` entry, A/B by ear |

More, with causes: `references/troubleshooting.md`.

## Related skills

- [image-generation](../image-generation): character cards and panels ("Recurring characters and story panels").
- [elevenlabs-tts](../elevenlabs-tts): voices, one-word lines, pronunciation, music and SFX.
- [generating-video-clips](../generating-video-clips): clips, take sheets, lip-sync.
- [deck-to-video](../deck-to-video): the same ffmpeg lessons for slide videos.
