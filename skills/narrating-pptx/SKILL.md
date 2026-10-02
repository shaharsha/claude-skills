---
name: narrating-pptx
description: Use when adding voice narration, voiceover, or TTS audio to a PowerPoint/pptx deck in ANY language (Hebrew, English, mixed) — making a deck self-presenting, generating per-slide speech with ElevenLabs, or when embedded pptx audio won't autoplay or triggers PowerPoint's "found a problem / Repair" dialog. Use whenever the user mentions narration, voiceover, audio in slides, TTS for a presentation, ElevenLabs + pptx, or a self-playing deck — even if they don't say "narration" explicitly.
---

# Narrating PPTX (ElevenLabs → per-slide autoplay)

## Overview

Turn any pptx into a self-presenting deck: write presenter-style narration scripts (any language), generate one clip per slide with ElevenLabs, embed the clips, and make each autoplay on slide entry.

**REQUIRED SUB-SKILL: elevenlabs-tts** — owns everything about the voice: model (`eleven_v4`), audio tags, stability, voices, the batch generator, leak checks, and timings. This skill owns what is specific to a deck: what the narration says, and getting the audio into PowerPoint without corrupting the file.

**The iron rule (paid for in blood): NEVER hand-write `<p:timing>` autoplay XML.** Hand-rolled timing XML corrupts the file — PowerPoint shows "found a problem… Repair". The only reliable method is letting **real PowerPoint author the XML itself** via AppleScript play-settings (`scripts/set_autoplay.sh`). If you're tempted to inject timing XML "just this once" — that's the exact failure this skill exists to prevent.

**Requirements:** macOS + Microsoft PowerPoint installed (for the autoplay step), `python-pptx`, `ELEVENLABS_API_KEY` env var, a voice ID (elevenlabs-tts lists the defaults).

## Pipeline (5 steps, in order)

### 1. Write the narration scripts → `scripts.json`

`{"01": "text…", "02": "text…", …}` — keys are 1-based slide positions, zero-padded.

**Language: exactly what the user asks for.** Hebrew, English, or mixed. For Hebrew (or any non-English), write like a native presenter in that language who naturally keeps technical terms in English (e.g., Israeli hi-tech register: "ה-agent מנתח את הדאטה וכותב manifest"). Don't translate terms the audience uses in English.

**Depth: the voice IS the presenter, not a caption reader.** Target ~600–900 chars per slide (≈45–75 s). Each script: open with context → work through what the slide actually shows → explain the *why* → bridge to the next slide. **Describe position only when the viewer needs it to follow.** On a diagram, "the dashed box inside" is orientation they cannot get otherwise; over three cards of text, "on the left… in the middle… on the right" is audio-description rather than presenting (see **self-presenting-decks**). Short caption-style scripts (~200 chars) feel like labels, not a presentation — users reject them.

**Numbers on slides:** the slide shows "9 days → 4 hours"; the script says "nine days… to four hours". Write them as words (elevenlabs-tts explains why); subtitles generated from the alignment will then read as words too, which is fine.

**Direct the delivery with audio tags** — follow elevenlabs-tts ("Write the script"): English bracket tags at the beat they modify, tagging the *shifts* in the performance, descriptive v4 directions (`[Warm, conversational tone]`, `[Pause, dry amusement]`). Default to a clean professional read; go denser only when the user wants an expressive performance.

**Get the scripts approved by the human before generating** — TTS is real credit spend, often in a cloned voice, and every later script change is a regeneration.

### 2. Generate the clips

Use elevenlabs-tts' generator — it writes exactly the `audio/slideNN.mp3` names the next steps expect:

```bash
export ELEVENLABS_API_KEY=...   # env var only — NEVER paste the key into output
python3 <elevenlabs-tts-dir>/scripts/generate_tts.py scripts.json VOICE_ID audio/ --model eleven_v4 --stability 0.5
```

Sample one tag-rich slide first (and A/B stability if the brief is expressive) — elevenlabs-tts "Generate — sample first". One model, one stability, one voice for every slide; mixing is audible across slide changes. Verify durations before embedding: `afinfo audio/slide01.mp3 | grep duration`.

### 3. Embed one clip per slide

**Existing pptx** (the common case):
```bash
python3 scripts/add_audio.py deck.pptx audio/ narrated.pptx
```
Adds a small speaker icon bottom-right of each slide (click-to-play at this point — that's expected).

**Deck you're building with pptxgenjs:** add per slide instead:
```js
slide.addMedia({ type: "audio", path: "audio/slide01.mp3", x: 9.38, y: 5.0, w: 0.5, h: 0.5 });  // >=0.5in: hoverable seek-bar target
```
(pptxgenjs emits `<a:videoFile>` for audio — a known quirk; harmless, PowerPoint normalizes it during step 4.)

### 4. Autoplay — via real PowerPoint (the only safe way)

```bash
cp narrated.pptx ~/Downloads/    # PowerPoint sandbox: Downloads/Documents/Desktop only
scripts/set_autoplay.sh "$HOME/Downloads/narrated.pptx" SLIDE_COUNT
```

Expect output `autoplay set on N media shapes` where **N == number of narrated slides**. The script targets the presentation **by filename** (never `presentation 1` — PowerPoint's "reopen windows" resurrects stale decks that steal that index), waits for large files to open, errors on slide-count mismatch, and fails on N=0.

### 5. Validate — assume it's broken until proven

- Export through real PowerPoint (use the **office-render** skill if available): a successful PDF export of all slides == no repair dialog. LibreOffice validation is NOT sufficient — it tolerates XML that PowerPoint rejects.
- Re-check N from step 4 equals expected.
- The human must ear-test autoplay once: slideshow mode (⌘⇧↩), audio should start on slide entry. You cannot verify sound headlessly — say so; never claim you heard it.

## Timings, subtitles, highlights

Anything that must follow the voice (subtitles, element highlights in the video) comes from forced alignment of the finished clips — elevenlabs-tts' `scripts/align_narration.py`, consumed by **deck-to-video**. Nothing in the pptx needs it.

## Progress bar during playback

Elapsed/remaining time is **hover-only** — there is no persistent countdown for embedded audio (confirmed: standard Insert Audio cannot show controls without hovering). For the hover bar to work, THREE things must hold:
1. **Slide Show ribbon → "Show Media Controls" is checked** (if unchecked, nothing appears on hover).
2. The icon is **big enough to hover** — ≥0.5 in. A 0.28 in icon (~27 px) is an unusable hover target; users report "no progress bar" when the real issue is they can't hit the icon.
3. `set_autoplay.sh` sets *hide while NOT playing*, never *hide during show* (which removes the hover target entirely).

To resize icons on an already-narrated deck, use python-pptx geometry (safe — round-trips preserve the timing XML). **Match media shapes by element XML, not `shape_type == MEDIA`** (audio pics report as PICTURE):
```python
for sh in slide.shapes:
    if 'audioFile' in sh._element.xml or 'videoFile' in sh._element.xml:
        sh.width = sh.height = Inches(0.5)
        sh.left = prs.slide_width - Inches(0.62); sh.top = prs.slide_height - Inches(0.62)
```
Avoid AppleScript for geometry (its `top`/`left position` properties fight the compiler); AppleScript is only for play settings.

## Common mistakes (each one happened in the baseline session)

| Mistake | Consequence | Fix |
|---|---|---|
| Hand-writing `<p:timing>` autoplay XML | PowerPoint Repair dialog — corrupt deliverable | `set_autoplay.sh` (PowerPoint authors it) |
| AppleScript `presentation 1` | Edits a stale reopened deck; wrong file saved | Target `presentation "name.pptx"`; verify slide count |
| Hand-rolling the TTS calls | v3-era settings, 429s, error bodies saved as `.mp3` | elevenlabs-tts' `generate_tts.py` |
| Caption-length scripts (~200 chars) | "It should explain more — it's the presenter" | 600–900 chars, presenter structure (step 1) |
| Numbers as digits in the script | "11" read in the wrong language/form | Write numbers as words |
| `for i in $var` in zsh | No word splitting — loop gets one token | `${=var}` in zsh, or use Python |
| Fixed `delay 2` after opening big pptx | "object does not exist" AppleScript error | Wait-loop until slide count matches (in script) |
| Validating with LibreOffice only | Misses PowerPoint-strict corruption | Export via real PowerPoint |
| Icon ≤0.3 in | User can't hover → "no progress bar" complaints | 0.5 in icon, bottom-right (default in add_audio.py) |
| `shape_type == MEDIA` in python-pptx | Finds 0 audio shapes (they report as PICTURE) | Match `'audioFile' in sh._element.xml` |
| AppleScript for shape geometry | `top`/`left position` compile errors | python-pptx for geometry; AppleScript only for play settings |

## Caveats

- Autoplay survives PowerPoint (desktop/365). **Google Slides import and LibreOffice are unreliable** with embedded audio autoplay; PDF export drops audio entirely.
- File grows ~0.3–1.5 MB per narrated minute (mp3 128kbps).
- Keep a clean (non-narrated) copy — narration is a variant, not a replacement.
- Deck edits after narration are fine; re-run step 4 only if you re-add media.
