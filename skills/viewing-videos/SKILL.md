---
name: viewing-videos
description: Use when the user wants Claude to view, watch, inspect, or extract information from a video file (mp4, mov, webm, mkv, screen recording, Zoom/Meet/Teams meeting recording, demo, screencast, phone clip) — e.g. "can you see this video", "what numbers are shown on screen", "what slide was up when X was said", "check the recording", or when a transcript exists but on-screen content (figures, slides, UIs, dashboards) must be read visually. Claude cannot ingest video natively; this skill is how Claude sees one.
---

# Viewing Videos

## Overview

Claude can't watch video, but it reads images well. Turn the video into the *fewest frames that answer the question* with ffmpeg, triage them on a contact sheet, then Read the interesting ones at full resolution. Requires `ffmpeg` + ImageMagick `montage` (both via Homebrew).

## Step 0: Probe first

```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of default=noprint_wrappers=1 video.mp4
```

Duration picks the strategy; resolution sets expectations — 1080p+ screen content reads fine, at 720p big KPI numbers are fine but dense tables/spreadsheets need the crop+upscale step below.

## Pick a strategy

| Situation | Strategy |
|---|---|
| You know the moment (timestamped transcript, user says "at 12:34") | Targeted single frames |
| Screen shares / slides / UI demos, unknown moments | Scene-change sweep (default) |
| Continuous motion (camera footage, gameplay) — scenes never "change" | Interval sampling (see frame budget below) |

## Targeted frame

`-ss` before `-i` = fast seek:

```bash
ffmpeg -ss 12:34 -i video.mp4 -frames:v 1 /tmp/frames/t12m34s.png
```

## Scene-change sweep → timestamp names → contact sheet

```bash
rm -rf /tmp/frames && mkdir -p /tmp/frames
ffmpeg -hide_banner -i video.mp4 -vf "select='gt(scene,0.2)',showinfo" -fps_mode vfr /tmp/frames/frame_%03d.png 2> /tmp/frames/log.txt
cd /tmp/frames && grep -o 'pts_time:[0-9.]*' log.txt | cut -d: -f2 | awk '{n++; t=int($1); printf "mv frame_%03d.png t%02dm%02ds.png\n", n, t/60, t%60}' | sh
montage -label '%t' -font /System/Library/Fonts/Helvetica.ttc t*.png -tile 6x -geometry 320x180+4+4 -pointsize 18 contact_%d.png
```

Read `contact_0.png` to triage (timestamps are printed under each tile), then Read only the frames that matter at full resolution. Threshold 0.2 works for meetings: webcam segments cluster harmlessly, screen shares fire exactly on slide/page changes. Footage with constant motion → hundreds of frames; switch to interval sampling.

## Frame budget

Aim for ≤ ~100 frames per sweep — enough to cover a long video, few enough to triage on 1–2 contact sheets. Tune to hit it, don't accept whatever falls out:

- Scene detection over-firing? Raise the threshold (`gt(scene,0.3)`–`0.4`).
- Interval sampling: derive the interval from duration instead of fixing it — `interval = max(5, duration_seconds / 100)`, i.e. `-vf fps=1/$INTERVAL`. A 10-min clip samples every ~6s; a 3-hour recording every ~108s (not 1080 frames at a blind 1/10s).
- If the question lives in one segment, sweep coarse first, then densify only that range: `ffmpeg -ss <start> -to <end> -i video.mp4 -vf fps=1/2 ...`.

## Small text unreadable? Crop + upscale

Re-extract just the region at 2× rather than squinting at the full frame:

```bash
ffmpeg -ss 17:40 -i video.mp4 -frames:v 1 -vf "crop=900:500:80:120,scale=2*iw:-1" /tmp/frames/zoom_t17m40s.png
```

Get crop coords by reading the full frame first.

## With a transcript

Timestamped transcript (`.vtt`) → go targeted: find where figures/screens are discussed, seek those times. Plain text transcript (no timestamps) → sweep, then correlate by content order. If the user has a choice, ask for the timestamped export.

## Common mistakes

- **Globs in compound commands**: zsh aborts the whole `&&` chain on a no-match glob (`rm -f *.png` → ffmpeg never runs). Use `rm -rf dir && mkdir -p dir`.
- **`montage` without `-font`**: fails with "unable to read font" on macOS. Always pass `-font /System/Library/Fonts/Helvetica.ttc`.
- **Blind 1-frame-per-second sampling**: 30 min → 1800 redundant frames. Scene detection or 1/10s intervals first; densify only where needed.
- **Skipping the contact sheet**: reading 60+ full frames one by one burns context. Triage on the sheet, read few.
- **Trusting frame numbers instead of timestamps**: rename to `tMMmSSs.png` immediately, or you can't correlate with the transcript or seek back for a better frame.
