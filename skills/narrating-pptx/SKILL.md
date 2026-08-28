---
name: narrating-pptx
description: Use when adding voice narration, voiceover, or TTS audio to a PowerPoint/pptx deck in ANY language (Hebrew, English, mixed) — making a deck self-presenting, generating per-slide speech with ElevenLabs, or when embedded pptx audio won't autoplay or triggers PowerPoint's "found a problem / Repair" dialog. Use whenever the user mentions narration, voiceover, audio in slides, TTS for a presentation, ElevenLabs + pptx, or a self-playing deck — even if they don't say "narration" explicitly.
---

# Narrating PPTX (ElevenLabs → per-slide autoplay)

## Overview

Turn any pptx into a self-presenting deck: write presenter-style narration scripts (any language), generate speech via ElevenLabs `eleven_v3`, embed one clip per slide, and make each clip autoplay on slide entry.

**The iron rule (paid for in blood): NEVER hand-write `<p:timing>` autoplay XML.** Hand-rolled timing XML corrupts the file — PowerPoint shows "found a problem… Repair". The only reliable method is letting **real PowerPoint author the XML itself** via AppleScript play-settings (`scripts/set_autoplay.sh`). If you're tempted to inject timing XML "just this once" — that's the exact failure this skill exists to prevent.

**Requirements:** macOS + Microsoft PowerPoint installed (for the autoplay step), `python-pptx`, `ELEVENLABS_API_KEY` env var, an ElevenLabs voice ID from the user.

## Pipeline (5 steps, in order)

### 1. Write the narration scripts → `scripts.json`

`{"01": "text…", "02": "text…", …}` — keys are 1-based slide positions, zero-padded.

**Language: exactly what the user asks for.** Hebrew, English, or mixed. For Hebrew (or any non-English), write like a native presenter in that language who naturally keeps technical terms in English (e.g., Israeli hi-tech register: "ה-agent מנתח את הדאטה וכותב manifest"). Don't translate terms the audience uses in English.

**Depth: the voice IS the presenter, not a caption reader.** Target ~600–900 chars per slide (≈45–75 s). Each script: open with context → work through what the slide actually shows → explain the *why* → bridge to the next slide. **Describe position only when the viewer needs it to follow.** On a diagram, "the dashed box inside" is orientation they cannot get otherwise; over three cards of text, "on the left… in the middle… on the right" is audio-description rather than presenting (see **self-presenting-decks**). Short caption-style scripts (~200 chars) feel like labels, not a presentation — users reject them.

**Audio tags = the "Enhance" feature.** ElevenLabs' UI "Enhance" button just uses an LLM to add tags — there is no Enhance API. You are that LLM: weave tags into the script. Tags stay in **English brackets even inside Hebrew/other-language text**, placed at the emotional beat they modify.

**Tag catalog (Eleven v3)** — pick to match the moment, don't just repeat `[warm]`/`[confident]`:
- **Tone / emotion:** `[warm]` `[excited]` `[confident]` `[curious]` `[surprised]` `[impressed]` `[amused]` `[thoughtful]` `[serious]` `[reassuring]` `[professional]` `[sympathetic]` `[questioning]` `[sarcastic]` `[mischievously]` `[nervous]` `[frustrated]` `[calm]`
- **Non-verbal reactions:** `[chuckles]` `[laughs]` `[giggles]` `[sighs]` `[exhales]` `[gasps]` `[whispers]` `[clears throat]`
- **Punctuation levers (combine with tags):** ellipsis `…` = natural pause (more reliable than `[pause]`); CAPS = emphasis; real question marks / commas set rhythm. Structure matters more than tag count.

**Density:** default 2–4 per script for a clean corporate read. Some users explicitly want a *dense, expressive* performance — then go heavier (5–8, varied), matching tag to content (`[excited]`/`[surprised]` on a reveal, `[amused]`/`[chuckles]` on a wry aside, `[serious]`/`[sighs]` on a cost, `[curious]` on a "so what?" pivot). Cap around one tag per sentence — past that, delivery gets jerky and tags start leaking into the audio.

**⚠️ Non-English caveat (Hebrew, etc.):** ElevenLabs has **no documented tag support for non-English**. Heavy tagging on Hebrew can (a) make v3 *speak the tag word aloud*, (b) over-act, or (c) insert odd pauses. So when tagging densely or in a non-English language, **generate ONE slide first and ear-check that tags are performed, not spoken**, before spending credits on the whole deck. Sources: [v3 audio tags](https://elevenlabs.io/blog/v3-audiotags), [best practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices).

**Hard limit:** 5,000 chars per script (`eleven_v3` request cap).

### 2. Choose stability, then generate speech (parallel, 429-safe)

**Eleven v3 has three stability modes, and the default is the middle one.** This matters because step 1 tells you to write dense audio tags, and Natural is the conservative reading of them:

| stability | mode | behaviour |
|---|---|---|
| `0.0` | **Creative** | most expressive, **responds most strongly to audio tags** — and least predictable |
| `0.5` | Natural | the script default. Safe, but can under-perform the tags you wrote |
| `1.0` | Robust | very stable, largely ignores directional prompts |

If a deck sounds monotone despite heavy tagging, the tags are probably fine and the stability is wrong. **A/B one tag-rich slide at 0.0 and 0.5 and let the human pick before spending the batch** — you cannot ear-check this yourself. Then regenerate **all** clips at the chosen value: mixing stabilities across slides is audible.

Creative also runs slightly *shorter* (more dynamic delivery moves faster through flat passages), so expect durations to shift and the video to need a re-render.

**v3 has no `speed` parameter.** Pace is controlled by sentence structure and `…` pauses at write time, or `ffmpeg -filter:a atempo=` afterwards — never by a generation setting.

```bash
export ELEVENLABS_API_KEY=...   # env var only — NEVER paste the key into output
python3 scripts/generate_tts.py scripts.json VOICE_ID audio/ --concurrency 4 --stability 0.5
```

The script parallelizes (default 4 — typical plan concurrency is ~5; 16-at-once returns 429 on most), retries 429s with backoff, rejects suspiciously-small responses (a 429/error body saved as `.mp3` is ~600 bytes), and exits non-zero on any failure. Verify durations before embedding: `afinfo audio/slide01.mp3 | grep duration`.

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

## ElevenLabs quick reference

| Item | Value |
|---|---|
| Endpoint | `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128` |
| Auth | header `xi-api-key` (from env var; never echo) |
| Body | `{"text", "model_id": "eleven_v3", "voice_settings": {"stability": STABILITY, "similarity_boost": 0.75, "use_speaker_boost": true}}` |
| Languages | 70+ incl. Hebrew; tags like `[pause]` inline |
| Limits | 5,000 chars/request · ~5 concurrent requests (429 = concurrency, not quota) |
| Stability | 0.0 Creative / 0.5 Natural / 1.0 Robust — pick per deck, see step 2. No `speed` param on v3 |

## Voices on hand

The skill is voice-agnostic — pass any ElevenLabs `VOICE_ID` to `generate_tts.py`. **Default to Josh** unless the user asks for another voice. Both are Hebrew-capable and tested on `eleven_v3`:

| Name | Voice ID | Notes |
|---|---|---|
| **Josh** ⭐ | `ZoiZ8fuDWInAcwPXaVeq` | **default** — warm, slightly faster; good for Hebrew narration |
| Kevin | `1fz2mW1imKTf5Ryjk5su` | alternative, a little more measured |

## Getting timings back out of finished audio

`POST https://api.elevenlabs.io/v1/forced-alignment` — multipart `file` (audio) + `text` (transcript) → `characters[]` and `words[]` with `start`/`end`, plus a `loss` confidence. Priced at speech-to-text rates.

```bash
python3 scripts/align_narration.py narration/scripts.json narration/audio/ narration/alignment/
```

This turns finished clips into timed data **without regenerating anything**, which is what makes subtitles and narration-synced animation cheap (see deck-to-video). The script handles both traps below and exits non-zero on a length mismatch; the traps are spelled out because anything hand-rolling this will hit them:

- **Strip audio tags from the transcript first.** `[confident]` is performed, not spoken; leave it in and the aligner searches for the word, drifting everything after it.
- **Verify `len(characters) == len(text)`.** They map 1:1 when it works, which is what lets you go from a character offset in the script to a timestamp. A mismatch means the mapping is silently wrong.

`/v1/text-to-speech/{voice}/with-timestamps` returns the same timing at generation time — use it only when you are generating anyway, since it costs a re-record.

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
| Firing all TTS requests at once | HTTP 429 on most; error JSON saved as `.mp3` | `--concurrency 4` + size-integrity check |
| Caption-length scripts (~200 chars) | "It should explain more — it's the presenter" | 600–900 chars, presenter structure (step 1) |
| Looking for an "Enhance" API | Doesn't exist (UI-only LLM feature) | Author the audio tags yourself |
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
