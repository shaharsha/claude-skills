---
name: deck-to-video
description: Use when turning a slide deck plus per-slide narration audio into an mp4 video — a self-playing/self-presenting deck video, "slides to video", "presentation to mp4", a shareable WhatsApp/Slack/Drive video of a narrated deck, or when a slide video needs a per-slide progress bar / countdown / slide counter. Also use when an ffmpeg-drawn progress bar renders full/static from the first frame, or ffmpeg errors "No such filter: 'drawtext'".
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
```
On success it prints one line per slide — that per-slide length **already includes the pad** — and ends with `duration matches segment sum` (it exits non-zero otherwise).

## Getting the inputs right

1. **Slides: if starting from a pptx, rasterize from real PowerPoint, not LibreOffice.** Export the pptx to PDF via actual PowerPoint (the **office-render** skill does this on macOS), then hand the PDF to the script — LibreOffice substitutes fonts and re-flows layouts, so the video would not match what the deck's author sees. 200 dpi keeps dense slide text crisp at 1080p. (Already have per-slide images? Use them directly — skip this step.)
2. **Audio: one clip per slide, named `slideNN.mp3`.** If the deck was narrated with the **narrating-pptx** skill, its `narration/` directory is already in this exact shape — reuse it so the pptx and the video sound identical.
3. If narration pace was adjusted (e.g. `ffmpeg -filter:a atempo=1.1`), build the video from the *adjusted* files.

## Why the overlays are baked with PIL, not drawn by ffmpeg (paid for in blood)

- **`drawbox` with a `t`-based width expression renders a FULL bar from frame 0** in several ffmpeg builds — the expression is evaluated once at init, not per frame. The failure is silent: the video encodes fine and the bar simply never moves. `drawtext` expressions *do* update per frame in the same builds, which makes the broken bar easy to miss next to a working countdown.
- **Homebrew's ffmpeg bottles (2026+) are built without libfreetype** — `No such filter: 'drawtext'` — and the keg versions (`ffmpeg@7`, `ffmpeg@8`) are the same. Don't spend an install cycle discovering this; if a full build is needed for anything else, `uv tool install static-ffmpeg` ships one (the script auto-falls-back to it).

So the script bakes one frame per second with PIL (bar fill, countdown, counter) and feeds ffmpeg a 1 fps image sequence encoded at `-r 30`. Deterministic, font-controlled, and *cheaper* to encode than filtering a 30 fps stream — the slide is static anyway. Second-granularity updates read naturally for a countdown.

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

## Caveats

- Hard cuts between slides by design — crossfades break the lossless `-c copy` concat and add little.
- ~13–17 min of 1080p mostly-static slides ≈ 40–50 MB.
- The video is a *third* artifact beside the clean pptx and the narrated pptx — it forces the narration's pace on the viewer, so keep the pptx variants for people who prefer reading.
