---
name: narrating-pptx
description: Use when adding voice narration, voiceover, or TTS audio to a PowerPoint/pptx or Google Slides deck in ANY language (Hebrew, English, mixed) — making a deck self-presenting, generating per-slide speech with ElevenLabs, re-narrating slides after edits, or when embedded pptx audio won't autoplay, triggers PowerPoint's "found a problem / Repair" dialog, or goes silent after the deck is pushed to Google Slides. Use whenever the user mentions narration, voiceover, audio in slides, TTS for a presentation, ElevenLabs + pptx or Google Slides, or a self-playing deck — even if they don't say "narration" explicitly.
---

# Narrating PPTX (ElevenLabs → per-slide autoplay)

## Overview

Turn any deck into a self-presenting one: write presenter-style narration scripts (any language), generate one clip per slide with ElevenLabs, and make each clip play on slide entry — in a **pptx** (steps 3-5) or in **Google Slides** (its own section below). Where the deck will be watched decides which; ask if it isn't clear. A Google Slides copy pushed from a pptx loses its audio every time, so narrating the pptx does not narrate the Slides copy.

**REQUIRED SUB-SKILL: elevenlabs-tts** — owns everything about the voice: model (`eleven_v4`), audio tags, stability, voices, the batch generator, leak checks, and timings. This skill owns what is specific to a deck: what the narration says, and getting the audio into PowerPoint without corrupting the file.

**The iron rule (paid for in blood): NEVER hand-write `<p:timing>` autoplay XML.** Hand-rolled timing XML corrupts the file — PowerPoint shows "found a problem… Repair". The only reliable method is letting **real PowerPoint author the XML itself** via AppleScript play-settings (`scripts/set_autoplay.sh`). If you're tempted to inject timing XML "just this once" — that's the exact failure this skill exists to prevent.

**Requirements:** an ElevenLabs key and a voice ID (elevenlabs-tts covers both). For a pptx: macOS + Microsoft PowerPoint (the autoplay step) and `python-pptx`. For Google Slides: ffmpeg and the service account the gslides-sync skill uses. Its key is found automatically (`$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`; or pass `--sa-key`), and no Python packages are needed.

## Pipeline (5 steps, in order)

### 1. Write the narration scripts → `scripts.json`

`{"01": "text…", "02": "text…", …}` — keys are 1-based slide positions, zero-padded.

**Language: exactly what the user asks for.** Hebrew, English, or mixed. For Hebrew (or any non-English), write like a native presenter in that language who naturally keeps technical terms in English (e.g., Israeli hi-tech register: "ה-agent מנתח את הדאטה וכותב manifest"). Don't translate terms the audience uses in English.

**Depth: the voice IS the presenter, not a caption reader.** Target ~600–900 chars per slide (≈45–75 s), **within a budget for the whole deck**: 26 slides at that depth is over 20 minutes. Agree a total with the user for long decks, and give near-identical slides less (360–740 chars worked across 22 similar slides). Each script: open with context → work through what the slide actually shows → explain the *why* → bridge to the next slide. **Describe position only when the viewer needs it to follow.** On a diagram, "the dashed box inside" is orientation they cannot get otherwise; over three cards of text, "on the left… in the middle… on the right" is audio-description rather than presenting (see **self-presenting-decks**). Short caption-style scripts (~200 chars) feel like labels, not a presentation — users reject them.

**Numbers on slides:** the slide shows "9 days → 4 hours"; the script says "nine days… to four hours". Write them as words (elevenlabs-tts explains why); subtitles generated from the alignment will then read as words too, which is fine. In Hebrew the number words agree in gender with their noun, and a relative date ("כשבדקנו", "when we checked") ages better than "two weeks ago".

**Who is speaking.** Write as the person whose voice it is. In the user's own cloned voice the script is the user presenting, in first person; a script written as an assistant explaining things *to* the user sounds wrong in their voice. Switching voices after approval means rewriting the script, not only regenerating it.

**Direct the delivery with audio tags** — follow elevenlabs-tts ("Write the script"): English bracket tags at the beat they modify, tagging the *shifts* in the performance, descriptive v4 directions (`[Warm, conversational tone]`, `[Pause, dry amusement]`). Default to a clean professional read; go denser only when the user wants an expressive performance.

**Get the scripts approved by the human before generating** — TTS is real credit spend, often in a cloned voice, and every later script change is a regeneration.

### 2. Generate the clips

Use elevenlabs-tts' generator — it writes exactly the `audio/slideNN.mp3` names the next steps expect:

```bash
python3 <elevenlabs-tts-dir>/scripts/generate_tts.py scripts.json VOICE_ID audio/ --model eleven_v4 --stability 0.5
```

Sample one tag-rich slide first (and A/B stability if the brief is expressive) — elevenlabs-tts "Generate — sample first". Generate the sample into the same `audio/` with the batch's settings, then batch the rest with `--only`, so the manifest records every slide. One model, one stability, one voice for every slide; mixing is audible across slide changes. The generator prints each clip's length.

### 3. Embed one clip per slide

**Existing pptx** (the common case):
```bash
python3 scripts/add_audio.py deck.pptx audio/ narrated.pptx
```
Adds a small speaker icon bottom-right of each slide (click-to-play at this point — that's expected). Look at the render: on a busy layout the icon can cover a content card. Move it with python-pptx (see *Progress bar*), not by shrinking it below 0.5 in.

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

## Google Slides

Google's pptx import **drops embedded audio every time**: each slide keeps the speaker icon as a silent picture. The Slides API cannot insert audio, only Drive or YouTube videos. So each slide gets a small Drive video (a still badge plus that slide's mp3) that autoplays in a corner. `scripts/gslides_narration.py` does each step:

```bash
S=<this-skill-dir>/scripts/gslides_narration.py
F=$(python3 $S folder --pres PRES_ID)        # 0. the deck's own folder on the shared drive
python3 $S videos audio/ videos/                                       # 1. one mp4 per clip, cut to the audio's exact length
python3 $S upload videos/ --folder $F          # 2. into a Drive folder
python3 $S wait   videos/ --folder $F          # 3. until Drive has processed them
python3 $S insert --pres PRES_ID --folder $F   # 4. on the slides, autoplaying [--skip 12 13]
python3 $S check  --pres PRES_ID --folder $F --videos videos/   # 5. read-only proof
```

- **Push the clean pptx to Slides, not the narrated one** (gslides-sync). The narrated one leaves a dead speaker icon on every slide.
- **Keep narration on a shared drive.** A service account has no Drive storage, so it cannot create files in a My Drive folder (403 "Service Accounts do not have storage quota"). On a shared drive where it is a **Manager**, it can. Name each shared drive for its organisation, e.g. "Deck narration (example.com)": `folder --pres PRES_ID` picks the drive named for the deck owner's domain (or pass `--drive NAME`) and keeps one folder per deck there: it creates the folder on first use, finds it again by the deck's id, and renames it when the deck is renamed. Without a shared drive, `upload` lists the files for a person to drag into the folder once, and every later run overwrites them in place.
- **Only the deck's audience can see its narration, if the drive itself stays narrow.** Shared-drive members see every file on the drive, and no per-folder grant can hide anything from them. So the drive's members are only the owner and the service account, and nobody else is ever added to the drive. `folder` and `insert` give each person, group, domain or anyone-with-the-link grant on the deck view-only access to that deck's folder, without notification emails, and nothing broader. They only ever add; `insert` grants access before it places the videos, and exits non-zero naming any grant that failed (for example, a drive that blocks sharing outside the org). `insert --dry-run` prints the grants without making them. Run `share --pres … --folder … --prune` to also remove people the deck no longer includes. For this to work, the drive's setting "Allow people who aren't shared drive members to access files" must be on, and for outside viewers, "Allow people outside <org> to access files" too.
- **Wait before inserting.** Until Drive has processed a file, the slide shows a broken or old-length video; `wait` polls for the thumbnail and the new length. Brand-new files can take several minutes (about 7 for three short clips on a shared drive), so leave the default 10-minute `--timeout` alone and run it in the background in an agent shell.
- **Re-run `insert` after every gslides-sync.** A re-push wipes the videos, and can change the page size (720×405 to 960×540 pt), so the badge is placed as a fraction of the page. `insert` replaces its own earlier videos (object IDs `narr_…`) and nothing else, so re-running is safe; `--dry-run` shows the plan first.
- **A viewer without access to the videos sees a deck that won't play.** `insert` re-grants access on every run. If the deck's sharing changes between syncs, run `share` again.
- **Slides cannot advance when a clip ends.** The viewer clicks to the next slide. For hands-free playback, ship the video too (deck-to-video).

## Updating a narrated deck

- **Changed slides only:** edit those scripts, get them approved, then `generate_tts.py … --only 04 07` with the voice and settings read from `audio/_manifest.json`. Rebuild the narrated pptx (or re-run `upload`, `wait`, `insert`) from the full audio set.
- **A slide inserted or deleted** in the middle: `python3 scripts/renumber_slides.py scripts.json audio/ --insert 5` for a new slide 5, i.e. one added after slide 4 (or `--delete 5` to drop slide 5, and `--alignment alignment/` if the video uses it) moves every later clip, script and manifest entry by one, so audio can't land on the wrong slide. Then write and generate only the new slide's clip. On Google Slides the Drive videos are matched by slide number, so rebuild and re-upload the videos for that slide and every later one (`videos`, `upload`, `wait`, `insert`).
- Keep the previous narrated file until the user has the new one.

## Handing it over

Give every deliverable as an absolute path, or send the file itself if the host can: never "it's in narration/". For a Google Slides deck, give its link.

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
| Pushing the narrated pptx to Google Slides | Silent speaker icons on every slide: "i dont hear the narration" | Push the clean pptx; add narration with `gslides_narration.py` |
| `ffmpeg -loop 1 … -shortest` for a still + audio video | The video runs 30–50% past its audio | `-t <audio seconds>` (the `videos` step) |
| Inserting videos before Drive has processed them | Broken or old-length video on the slide | `wait`, then `insert` |
| Not re-running `insert` after a gslides-sync | The re-push wiped every narration video | `insert` after every sync; `check` proves it |
| Videos in a My Drive folder | The service account can't create them, so someone drags files in by hand | A shared drive per org with the account as Manager; `folder --pres PRES_ID` |
| Viewers not given access to the narration folder | The deck plays for you, but viewers see a video they can't open | `insert` grants access before placing videos; re-run `share` when the deck's sharing changes |
| Adding people to the narration shared drive itself | They can see every deck's narration | Keep the drive's members to the owner and the service account; access is granted per deck folder |
| Copying an approved sample into the batch by hand | The manifest has no record of that slide | Generate the sample into `audio/`, batch the rest with `--only` |

## Caveats

- Autoplay survives PowerPoint (desktop/365). **Google Slides import drops embedded audio every time** (use the Google Slides section); LibreOffice is unreliable with it; PDF export drops audio entirely.
- File grows ~0.3–1.5 MB per narrated minute (mp3 128kbps).
- Keep a clean (non-narrated) copy — narration is a variant, not a replacement.
- Deck edits after narration are fine; re-run step 4 only if you re-add media. Inserted or deleted slides need `renumber_slides.py` first.
