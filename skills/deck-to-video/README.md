# deck-to-video

Turn slides (a PDF or per-slide images) plus per-slide narration audio into a **self-playing mp4**: each slide holds for exactly its narration's length plus a breath, then hard-cuts to the next — with a filling progress bar and seconds-remaining countdown (bottom-right) and an "N / M" slide counter (top-right). One bundled script does the whole build.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

The naive version of this is a one-liner: loop slides, set each one's duration from its mp3, concat. It produces a video that looks fine and is quietly wrong, in two ways that cost a full afternoon each to find.

**1. ffmpeg's `drawbox` renders a full progress bar from frame 0.** Animate a bar by giving `drawbox` a width expression in `t` and, in several ffmpeg builds, the expression is evaluated *once at init* rather than per frame. The failure is silent — the video encodes cleanly, the bar simply never moves. It's especially easy to miss because `drawtext` expressions *do* update per frame in those same builds, so the countdown beside the frozen bar animates correctly and everything looks alive.

**2. Homebrew's ffmpeg bottles (2026+) ship without libfreetype** — `No such filter: 'drawtext'` — and the keg-only versions (`ffmpeg@7`, `ffmpeg@8`) are built the same way. You can burn an entire install cycle discovering this.

So this script bakes every overlay frame with PIL and hands ffmpeg a 1 fps image sequence encoded at `-r 30`. Deterministic, font-controlled, and *cheaper* to encode than filtering a 30 fps stream — the slide is static anyway, and second-granularity updates read naturally for a countdown.

## What it does

```
slides.pdf ──rasterize 200dpi──┐
                               ├──▶ per-second PIL frames (bar · countdown · N/M)
narration/slideNN.mp3 ─────────┘                │
                                                ▼
                              per-slide segment (apad + explicit -t)
                                                │
                                    concat -c copy ──▶ out.mp4
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install documents-and-decks@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/deck-to-video" ~/.claude/skills/deck-to-video
```

## Requirements

- `ffmpeg` (any build — the script falls back to `static-ffmpeg` if a full one is needed)
- Python 3 with **Pillow**
- `pdftoppm` (poppler) when the input is a PDF

## Quick start

```bash
python3 scripts/build_video.py SLIDES AUDIO_DIR out.mp4
```

- `SLIDES` — `slides.pdf` (rasterized at 200 dpi) **or** a directory of per-slide images. Ordering is numeric-aware (`s2` before `s10`), but zero-padded names are still recommended.
- `AUDIO_DIR` — `slide01.mp3`, `slide02.mp3`, … The count **must** equal the slide count; the script hard-fails otherwise.

On success it prints one line per slide — each length **already includes the pad** — and ends with `duration matches segment sum`, exiting non-zero if it doesn't.

## Flags

| Flag | Default | Description |
|---|---|---|
| `--size WxH` | `1920x1080` | Output resolution |
| `--pad SECONDS` | `0.7` | Silence appended after each slide's narration |
| `--no-bar` | off | Drop the progress bar + countdown |
| `--no-counter` | off | Drop the "N / M" slide counter |
| `--bar-color HEX` | — | Progress-bar fill colour |
| `--crf N` | `20` | x264 quality |

## Getting the inputs right

1. **From a pptx? Rasterize with real PowerPoint, not LibreOffice.** Export to PDF via actual PowerPoint (the [office-render](../office-render) skill does this on macOS), then hand the PDF over. LibreOffice substitutes fonts and re-flows layouts, so the video wouldn't match what the deck's author sees. 200 dpi keeps dense slide text crisp at 1080p.
2. **One audio clip per slide, named `slideNN.mp3`.** If the deck was narrated with [narrating-pptx](../narrating-pptx), its `narration/` directory is already in exactly this shape — reuse it so the pptx and the video sound identical.
3. If narration pace was adjusted (`ffmpeg -filter:a atempo=1.1`), build from the *adjusted* files.

## Encoding choices the script already makes

Don't undo these:

| Choice | Why |
|---|---|
| `apad=pad_dur=PAD` + `-t seg_dur` | Exact tail padding; naive `-shortest` cuts the pause after speech |
| `yuv420p` + even dimensions | Anything else fails to play in QuickTime / WhatsApp / browsers |
| `-tune stillimage`, CRF 20 | Static slides compress well without text shimmer |
| concat demuxer + `-c copy` | Lossless join of identically-encoded segments |
| `-movflags +faststart` | Streams before it finishes downloading |

## Validate — assume the overlay is broken until frames prove otherwise

The script asserts final duration ≈ sum of segments. The overlay needs *eyes*:

```bash
ffmpeg -y -ss T1 -i out.mp4 -frames:v 1 a.jpg   # early in some slide
ffmpeg -y -ss T2 -i out.mp4 -frames:v 1 b.jpg   # late in the same slide
```

Pick T1/T2 by cumulative-summing the script's printed per-slide lengths (they include the pad). The bar must be visibly fuller in `b.jpg`, the countdown lower, and both must reset at each new slide. **A full-looking bar at an early timestamp is the static-bar bug** — this exact check is what caught it originally.

You cannot verify audio headlessly. Say so; never claim you heard it.

## Gotchas

| Mistake | Consequence | Fix |
|---|---|---|
| ffmpeg `drawbox` animated by `t` | Bar full from frame 0, silently | PIL-baked frames (what the script does) |
| Assuming `drawtext` exists | `No such filter` on Homebrew builds | Script falls back to static-ffmpeg / PIL text |
| LibreOffice rasterization | Fonts and layout differ from the real deck | Real PowerPoint PDF via [office-render](../office-render) |
| `-shortest` for segment length | Eats the pause after narration | `apad` + explicit `-t` |
| Audio count ≠ slide count | Desynced or missing slides | Script hard-fails; fix the inputs, don't skip slides |
| Judging output by "it encoded fine" | Static bar / wrong slide slips through | Extract early/late frames and look |
| Deck prints its own slide numbers | Number appears twice | Render from a numberless variant, or `--no-counter` |
| ffmpeg hangs at 0% CPU mid-segment | Build stalls forever; a killed attempt leaves an INVALID partial file | Script times out each segment (300s) and retries once, deleting the partial first |
| Piping the build through `\| tail` in an `&&` chain | Pipeline exit becomes tail's 0 — a failed build "succeeds" and stale artifacts ship | Run unpiped, or `set -o pipefail`; gate delivery on verified output |

## Caveats

- Hard cuts between slides by design — crossfades break the lossless `-c copy` concat and add little.
- ~13–17 min of 1080p mostly-static slides ≈ 40–50 MB.
- The video is a *third* artifact beside the clean pptx and the narrated pptx. It forces the narration's pace on the viewer, so keep the pptx variants for people who'd rather read.

## Related skills

- [self-presenting-decks](../self-presenting-decks) — the orchestration map this is the last stage of.
- [narrating-pptx](../narrating-pptx) — produces the `narration/` mp3s this consumes.
- [office-render](../office-render) — produces the real-PowerPoint PDF this rasterizes.

## License

MIT — see [LICENSE](../../LICENSE).
