# viewing-videos

Claude can't watch video — this skill is how it sees one anyway: turn the file into the **fewest frames that answer the question** with ffmpeg, triage them on a contact sheet, then read only the interesting ones at full resolution.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Born from a real need: a 30-minute Zoom recording whose transcript captured every word and none of the numbers that were on screen.

The naive fix — sample a frame per second and read them — is why this needs a method. Thirty minutes becomes 1,800 near-identical images, and reading them one by one burns the entire context before reaching the part that matters. The useful move is almost always the opposite: extract *few* frames, chosen well, then look closely at a handful.

So the skill is a decision procedure, not a command:

- **Know the moment?** Targeted seek. One frame, done.
- **Screen shares, slides, UI demos?** Scene-change detection fires exactly on slide and page changes — webcam segments cluster harmlessly.
- **Continuous motion?** Scenes never "change"; derive an interval from the duration instead.

Then triage on a contact sheet with timestamps printed under each tile, and only read the frames that matter at full resolution.

## What it does

```
video.mp4 ──ffprobe──▶ duration + resolution ──▶ pick a strategy
                                                      │
      ┌───────────────────────────────┬───────────────┴────────────┐
targeted seek              scene-change sweep              interval sampling
      │                               │                            │
      └──────────────▶ frames renamed to tMMmSSs.png ◀─────────────┘
                                      │
                        montage contact sheet (triage)
                                      │
                    read the few that matter, full-res
                                      │
                       still unreadable? crop + 2× upscale
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install utilities@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/viewing-videos" ~/.claude/skills/viewing-videos
```

## Requirements

`ffmpeg` and ImageMagick's `montage` (both via Homebrew). No scripts to install — the skill is a set of recipes.

## Quick start

Ask naturally:

- "can you watch this video and tell me what numbers are on screen"
- "what slide was up when they said X"
- "check this screen recording for the error message"

### Probe first

```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height \
  -of default=noprint_wrappers=1 video.mp4
```

Duration picks the strategy; resolution sets expectations — 1080p+ screen content reads fine, and at 720p big KPI numbers are fine but dense tables need the crop+upscale step.

### Targeted frame

`-ss` before `-i` is a fast seek:

```bash
ffmpeg -ss 12:34 -i video.mp4 -frames:v 1 /tmp/frames/t12m34s.png
```

### Scene-change sweep → timestamp names → contact sheet

```bash
rm -rf /tmp/frames && mkdir -p /tmp/frames
ffmpeg -hide_banner -i video.mp4 -vf "select='gt(scene,0.2)',showinfo" \
  -fps_mode vfr /tmp/frames/frame_%03d.png 2> /tmp/frames/log.txt
cd /tmp/frames && grep -o 'pts_time:[0-9.]*' log.txt | cut -d: -f2 \
  | awk '{n++; t=int($1); printf "mv frame_%03d.png t%02dm%02ds.png\n", n, t/60, t%60}' | sh
montage -label '%t' -font /System/Library/Fonts/Helvetica.ttc t*.png \
  -tile 6x -geometry 320x180+4+4 -pointsize 18 contact_%d.png
```

Read `contact_0.png` to triage, then read only the frames that matter at full resolution. Threshold 0.2 works well for meetings.

### Small text unreadable? Crop + upscale

Re-extract just the region at 2× rather than squinting at the full frame:

```bash
ffmpeg -ss 17:40 -i video.mp4 -frames:v 1 \
  -vf "crop=900:500:80:120,scale=2*iw:-1" /tmp/frames/zoom_t17m40s.png
```

Get the crop coordinates by reading the full frame first.

## Frame budget

Aim for **≤ ~100 frames per sweep** — enough to cover a long video, few enough to triage on one or two contact sheets. Tune to hit it; don't accept whatever falls out.

- Scene detection over-firing? Raise the threshold to `gt(scene,0.3)`–`0.4`.
- Interval sampling: derive the interval from duration rather than fixing it — `interval = max(5, duration_seconds / 100)`, then `-vf fps=1/$INTERVAL`. A 10-minute clip samples every ~6 s; a 3-hour recording every ~108 s, instead of 1,080 frames at a blind 1/10 s.
- If the answer lives in one segment, sweep coarse first, then densify only that range: `ffmpeg -ss <start> -to <end> -i video.mp4 -vf fps=1/2 …`.

## With a transcript

A timestamped transcript (`.vtt`) means going targeted: find where figures or screens are discussed and seek those times. A plain-text transcript means sweeping, then correlating by content order. If the user has a choice, ask for the timestamped export.

## Gotchas

- **Globs in compound commands.** zsh aborts the whole `&&` chain on a no-match glob — `rm -f *.png` and ffmpeg never runs. Use `rm -rf dir && mkdir -p dir`.
- **`montage` without `-font`** fails with "unable to read font" on macOS. Always pass `-font /System/Library/Fonts/Helvetica.ttc`.
- **Blind 1-frame-per-second sampling.** 30 minutes → 1,800 redundant frames. Scene detection or interval sampling first; densify only where needed.
- **Skipping the contact sheet.** Reading 60+ full frames one at a time burns context. Triage on the sheet, read few.
- **Trusting frame numbers instead of timestamps.** Rename to `tMMmSSs.png` immediately, or you can't correlate with the transcript or seek back for a better frame.

## Caveats

- Frames only — this skill doesn't transcribe audio. Pair it with a transcript when the question spans both.
- Footage with constant motion will blow the frame budget under scene detection; switch to interval sampling.

## License

MIT — see [LICENSE](../../LICENSE).
