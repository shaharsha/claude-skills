---
name: deck-to-video
description: Use when turning a slide deck plus per-slide narration audio into an mp4 video — a self-playing/self-presenting deck video, "slides to video", "presentation to mp4", a shareable WhatsApp/Slack/Drive video of a narrated deck, or when a slide video needs a per-slide progress bar / countdown / slide counter. Also use when a slide video should highlight, glow or spotlight the element being talked about in time with the voice, or when narration and on-screen animation need syncing. Also use when an ffmpeg-drawn progress bar renders full/static from the first frame, or ffmpeg errors "No such filter: 'drawtext'".
---

# Deck to Video (slides + narration → self-playing mp4)

## Overview

Turn N slide images (or a PDF) + N per-slide audio clips into one mp4: each slide holds for exactly its narration's length plus a short pause, then hard-cuts to the next. Overlays: a filling progress bar + seconds-remaining countdown (bottom-right) and an "N / M" slide counter (top-right).

**The one command** (the script ships in this skill's own `scripts/` directory — call it by its full path there):
```bash
python3 <this-skill-dir>/scripts/build_video.py SLIDES AUDIO_DIR out.mp4
# SLIDES = slides.pdf (rasterized at 200dpi) OR a directory of per-slide images
#          (numeric-aware ordering: s2 before s10; zero-padded names still recommended)
# AUDIO_DIR = slide01.mp3, slide02.mp3, … — count MUST equal slide count
# options: --size 1920x1080 · --pad 0.7 · --no-bar · --no-counter · --bar-color HEX · --crf 20
#          --highlights hl.json · --anim-fps 30   (see "Highlighting elements" below)
```
On success it prints one line per slide — that per-slide length **already includes the pad** — and ends with `duration matches segment sum` (it exits non-zero otherwise).

## Getting the inputs right

1. **Slides: if starting from a pptx, rasterize from real PowerPoint, not LibreOffice.** Export the pptx to PDF via actual PowerPoint (the **office-render** skill does this on macOS), then hand the PDF to the script — LibreOffice substitutes fonts and re-flows layouts, so the video would not match what the deck's author sees. 200 dpi keeps dense slide text crisp at 1080p. (Already have per-slide images? Use them directly — skip this step.)
2. **Audio: one clip per slide, named `slideNN.mp3`.** If the deck was narrated with the **narrating-pptx** skill, its `narration/` directory is already in this exact shape — reuse it so the pptx and the video sound identical.
3. If narration pace was adjusted (e.g. `ffmpeg -filter:a atempo=1.1`), build the video from the *adjusted* files.

## Why the overlays are baked with PIL, not drawn by ffmpeg (paid for in blood)

- **`drawbox` with a `t`-based width expression renders a FULL bar from frame 0** in several ffmpeg builds — the expression is evaluated once at init, not per frame. The failure is silent: the video encodes fine and the bar simply never moves. `drawtext` expressions *do* update per frame in the same builds, which makes the broken bar easy to miss next to a working countdown.
- **Homebrew's ffmpeg bottles (2026+) are built without libfreetype** — `No such filter: 'drawtext'` — and the keg versions (`ffmpeg@7`, `ffmpeg@8`) are the same. Don't spend an install cycle discovering this; if a full build is needed for anything else, `uv tool install static-ffmpeg` ships one (the script auto-falls-back to it).

So the script bakes frames with PIL (bar fill, countdown, counter) and feeds ffmpeg an image sequence encoded at `-r 30`. Deterministic, font-controlled, and *cheaper* to encode than filtering a 30 fps stream. **One frame per second is the default and is right while nothing on the slide moves** — second-granularity updates read naturally for a countdown. Slides carrying `--highlights` bake at 30 fps instead, for the reason in the next section.

## Encoding choices the script already makes (don't undo them)

| Choice | Why |
|---|---|
| `apad=pad_dur=PAD` + `-t seg_dur` | exact tail padding; naive `-shortest` cuts the pause after speech |
| `yuv420p` + even dimensions | anything else fails to play in QuickTime/WhatsApp/browsers |
| `-tune stillimage`, CRF 20 | static slides compress well without text shimmer |
| concat demuxer + `-c copy` | lossless join of identically-encoded segments |
| `-movflags +faststart` | video streams before it finishes downloading |

## Validate — assume the overlay is broken until frames prove otherwise

The script asserts final duration ≈ sum of segments. The overlay needs *eyes*:

```bash
ffmpeg -y -ss T1 -i out.mp4 -frames:v 1 a.jpg   # early in some slide
ffmpeg -y -ss T2 -i out.mp4 -frames:v 1 b.jpg   # late in the same slide
```
Pick T1/T2 from the script's printed per-slide lengths (cumulative-sum them for slide boundaries; remember they include the pad). Read both images. The bar must be visibly fuller in `b.jpg` and the countdown lower — and it should reset at each new slide. **A full-looking bar at an early timestamp = the static-bar bug** — this exact check is what caught it originally. You cannot verify audio headlessly — say so; never claim you heard it.

## Highlighting elements in time with the narration

Narration that says "on the left… in the middle… on the right" reads like an audio-description track (see self-presenting-decks). The fix is to strip the verbal pointer and glow the element instead — but only if the timing comes from the audio.

**The audio is the master; the animation follows it.** Never write narration to hit a mark, and never estimate when a phrase lands. Generate the clip normally, then use ElevenLabs **forced alignment** (`POST /v1/forced-alignment`, audio + transcript → per-character `start`/`end`) to read back when each thing was *actually* said, and derive the windows from that. Re-record a clip later and re-aligning self-corrects.

- **Anchor on character offsets, not keywords.** Author the script as per-element segments, join them for TTS, and keep each segment's offset into the joined string. Searching for a distinctive word breaks the moment it appears twice — "tags" appears four times on one slide.
- **Strip audio tags before aligning.** `[confident]` is performed, not spoken. Send it to the aligner and it hunts for the word in the audio and drags every later offset with it. Compute offsets against the same stripped string.
- Check the returned character count equals the text length, and watch `loss` (0.04-0.10 across a healthy 17-clip deck; a clear outlier is the signal, not an absolute threshold). A mismatch means every window on that slide is wrong.

**The `--highlights` JSON**, keyed by zero-padded slide number, boxes in output pixels:

```json
{"09": [{"card": 0, "box": [87, 468, 549, 374], "colour": "#B45309",
         "dim": "white", "start": 13.6, "end": 22.9}]}
```
Derive `box` from the deck's own layout code (inches → pixels), never by eyeballing the render — a card's geometry is already exact in the builder that drew it. `dim` is `white` on light slides, `black` on dark ones. Slides absent from the file bake at 1 fps as usual.

**Subtitles come free once aligned.** The same word timings make an `.srt` with no second transcription pass:

```bash
python3 <this-skill-dir>/scripts/make_srt.py narration/alignment/ narration/audio/ out.srt --pad 0.7
```
`--pad` must match the pad the video was built with, or cues drift further out with every slide. Ship it as a sidecar rather than burning it in — burned-in subtitles can't be turned off and fight the slide's own text.

**1 fps is a sync limit, not just a smoothness one.** The default bake is one frame per second, so a highlight can only change on an integer second — up to a full second off the word it points at, which reads as broken. Animated slides need ~30 fps.

**30 fps is cheap if you cache frames.** A 60 s slide is 1,800 frames, but nearly all are pixel-identical — the glow only moves during the fades. Key each frame on its visual state and hardlink the duplicates:

```python
key = (active_element, round(fade_alpha, 2), int(t))   # int(t) = the bar's step
if key in cache: os.link(cache[key], path); continue
```

120-200 real composites per slide instead of ~1,800, and no extra disk. **But quantise the progress bar to whole seconds first** — a continuously sliding bar makes every frame unique and defeats the cache entirely. (At 1 fps it already behaved that way, so nothing is lost.)

**Invert the dim on dark slides.** Washing inactive elements with translucent white pushes them back on a light slide and *brightens* them on a dark one. Carry the dim colour per slide, not per deck.

**Don't animate what is said too fast.** Measure the spoken span before committing: four list items rattled off in ~1.2 s each leave ~0.2 s of glow after a 0.5 s fade in and out, and strobe. Either give each item its own beat in the narration — usually an improvement, since one-breath lists are the densest thing in any deck — or leave the slide static.

## Common mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| ffmpeg `drawbox` animated by `t` | bar full from frame 0, silently | PIL-baked frames (the script) |
| Assuming `drawtext` exists | `No such filter` on Homebrew builds | script falls back to static-ffmpeg / PIL text |
| LibreOffice rasterization | fonts/layout differ from the real deck | real PowerPoint PDF via office-render |
| `-shortest` for segment length | eats the pause after narration | `apad` + explicit `-t` |
| Audio count ≠ slide count | desynced or missing slides | script hard-fails; fix inputs, don't skip slides |
| Judging output by "it encoded fine" | static bar / wrong slide slips through | extract early/late frames and look |
| Deck prints its own slide numbers | number appears twice (deck footer + counter) | render the video from a numberless deck variant, or pass `--no-counter` |
| ffmpeg hangs at 0% CPU after writing a segment | build stalls forever; a killed attempt leaves an INVALID partial file | the script now times out each segment (300s) and retries once, deleting the partial first |
| Estimating when a phrase lands instead of aligning | highlights drift off the words, worst on the longest slides | forced alignment on the finished clip |
| Reading card geometry off a rendered image | boxes are a few px out and the glow sits crooked | compute from the deck's own layout constants |
| Piping the build through `\| tail` inside an `&&` chain | pipeline exit = tail's 0 — a failed build "succeeds" and stale artifacts get delivered | run the script unpiped (or `set -o pipefail`); keep delivery/sync in a separate step gated on verified output |

## Caveats

- Hard cuts between slides by design — crossfades break the lossless `-c copy` concat and add little.
- ~13–17 min of 1080p mostly-static slides ≈ 40–50 MB.
- The video is a *third* artifact beside the clean pptx and the narrated pptx — it forces the narration's pace on the viewer, so keep the pptx variants for people who prefer reading.
