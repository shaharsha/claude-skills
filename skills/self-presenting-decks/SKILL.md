---
name: self-presenting-decks
description: Use when a presentation needs to explain itself — the user wants a deck with voiceover/narration, a self-playing or self-presenting deck, "add audio to my slides and also make a video", a narrated deck to share async (WhatsApp/Slack/Drive/email), or asks how to produce/update the whole deck → narration → video chain, including a narrated Google Slides deck. Use for orchestration even when only one artifact is mentioned, if others exist for the same deck.
---

# Self-Presenting Decks (orchestration)

## Overview

Producing a deck that presents itself is a three-skill pipeline with a fixed order. This skill is the map — each stage's depth lives in its own skill.

```
deck (pptx) ──▶ narration (audio + autoplay pptx) ──▶ video (mp4)
   content            depends on final slides          depends on final slides + final audio
```

**Order is the whole game: content → narration → video.** Narration is written against the finished slides, so slides must be final first. The video embeds both the rendered slides and the audio, so it's always last. Editing upstream invalidates downstream — see the update matrix.

## The stages

| Stage | Skill to use | Output |
|---|---|---|
| 0. Intake | — | **Where it will be watched** (PowerPoint file, Google Slides, a video, or all three; it decides which artifacts to build); voice and language/register (these live in narrating-pptx; the voice, model, key and tags in elevenlabs-tts) |
| 1. Build/edit the deck | **document-skills:pptx** (pptxgenjs or template editing); **presentation-generator** for AI-image decks | `deck.pptx` (the clean copy — keep it) |
| 2. Validate rendering | **office-render** — real PowerPoint → PDF → images | layout proof + **the PDF the video will reuse — always from the CLEAN pptx** (the narrated copy renders speaker icons onto slides) |
| 3. Narrate | **narrating-pptx** — scripts → **human approves scripts BEFORE TTS** (it's real credit spend, often in a cloned voice) → TTS via **elevenlabs-tts** (Eleven v4, sample one slide first) → for a pptx: embed → PowerPoint-authored autoplay → its own validation pass; for Google Slides: one autoplaying Drive video per slide on the deck synced from the **clean** pptx | `narration/scripts.json`, `narration/slideNN.mp3`, then `deck-narrated.pptx` and/or the narrated Google Slides deck |
| 4. Video | **deck-to-video** — the stage-2 clean-deck PDF + the same `narration/` mp3s → mp4 (progress bar + slide counter are defaults; flags turn them off) | `deck.mp4` |

Keep `narration/` and all artifacts as siblings next to the deck.

## Narrate like a presenter, not a screen reader

**Describe position only when the viewer could not otherwise find it.** That is the test, and it is observable before you write the line.

- **A diagram passes it.** "The dashed box inside", "the red box at the bottom", "look at the right-hand column, because that is the real argument" — the viewer cannot orient without you, and directing attention is what a presenter does.
- **Three cards of text fail it.** The viewer can already see three cards. "On the left… in the middle… on the right" over them is an audio-description track, and it makes the voice sound like it is reading the slide aloud. Say the content; the order carries the mapping.

**If you strip the verbal pointer, add a visual one.** Removing "on the left" leaves nothing telling the viewer which card is being discussed. In the video that gap is closable — highlight the active element in time with the voice (see deck-to-video). In the pptx it is not, so accept that the narrated deck is slightly less guided and let the card headings carry it.

## The artifacts, and who each is for

Build what the destination needs, not every artifact by default. A team that reviews in Google Slides wants the narrated Slides deck; an mp4 nobody asked for is wasted work and one more thing to keep in sync.

- **Clean pptx** — live presenting; humans talk over it. Also the source for the PDF and for any Google Slides copy.
- **Narrated pptx** — guided self-review at the viewer's own pace (they can linger, skip, re-listen per slide).
- **Narrated Google Slides** — the same, in the browser, for people who review in Drive. Viewers need access to the Drive folder holding the narration videos, and Slides won't advance on its own when a clip ends.
- **mp4** — zero-friction async sharing; plays anywhere, but forces the narration's pace. Never ship *only* the mp4 to someone who needs to study the content. Where it will be *played* decides how subtitles ship: a sidecar or soft track is reversible and free, but an inline Slack/Teams player exposes no subtitle control, so reaching those viewers means burning them in (deck-to-video).

Keep the files named as siblings (`Deck.pptx`, `Deck_Narrated.pptx`, `Deck.mp4`) so nobody presents the narrated copy live by accident, and hand each over as an absolute path or the file itself (a Slides deck as its link).

## The update matrix — what to rebuild when something changes

| What changed | Rebuild |
|---|---|
| Slide content/visuals | deck → re-render the **whole** PDF (PDFs aren't patchable per page) → **re-check affected narration scripts** (they reference what's visible) → regenerate only the changed clips → re-embed + autoplay → video |
| Narration text only | the changed clips → re-embed + autoplay pptx → video → **re-align those clips** if the video highlights elements in time with the voice |
| Narration voice settings (stability, model, voice) | **all** clips, not just the changed ones — mixed settings are audible → re-embed → re-align → video |
| TTS model upgrade (e.g. Eleven v3 → v4) | v3 scripts and tags run unchanged on v4, but re-sample one slide first (a voice can sound different) → **all** clips → re-embed → re-align → video. Partial upgrades are audible |
| Narration pace ("too slow") | `ffmpeg -filter:a atempo=1.1` on the mp3s (pitch-preserving, no TTS cost) → re-embed → **re-align if anything is synced to the voice** (atempo shifts every timestamp) → video |
| A slide inserted or deleted mid-deck | `renumber_slides.py` (narrating-pptx) shifts every later clip, script and manifest entry → write and generate only the new slide's clip (`generate_tts.py --only NN`) → re-embed / re-insert → video |
| The deck re-synced to Google Slides (gslides-sync) | the sync wipes the narration videos: re-run `gslides_narration.py insert`, then `check` |
| Voice switched to the user's own clone | **rewrite the scripts in first person as the user** (written as an assistant explaining to them, they sound wrong in their voice) → approval → **all** clips → re-embed / re-insert → re-align → video |
| Video overlay only (bar, counter) | video only — pptx artifacts untouched |
| Subtitle form (sidecar ⇄ soft track ⇄ burned in) | video only — re-mux, or re-encode **from the pre-burn master**; pptx artifacts untouched. Keep that master, or a restyle stacks a second generation |

Regenerating *only changed* narration clips saves TTS cost (`generate_tts.py --only`, with the voice and settings from `_manifest.json`) — but always rebuild the narrated pptx, Slides narration and video from the full final audio set, and keep the previous narrated file until the user has the new one.

## Hard-won rules that hold across the whole pipeline

- **Never hand-write PowerPoint `<p:timing>` autoplay XML** — corrupts the file. PowerPoint authors it via the narrating-pptx script. A video-only request is the escape hatch when PowerPoint isn't available.
- **All slide rasterization comes from real PowerPoint** (office-render), never LibreOffice — fonts and layout re-flow otherwise, and the video won't match the deck. office-render quits PowerPoint for a clean state, so it now stops when the user has presentations open; have them save and close, rather than forcing it.
- **A pptx's audio never survives a push to Google Slides.** Sync the clean pptx, then add narration with narrating-pptx's Google Slides section.
- **One narration source of truth**: the pptx and the video must embed the *same* mp3s, same pace — otherwise reviewers hear two different presentations.
- **Ear-testing is human work**: autoplay start and audio levels can't be verified headlessly — say so explicitly when handing off.
- **Timings are read from the audio, never estimated**: anything synced to the voice (highlights, subtitles) comes from forced alignment of the finished clips, so a re-record self-corrects on the next align.

## Choosing the entry point

- "Add narration/voiceover to my deck" → stages 2–3 for the destination the user names (+ offer 4; the mp3s make the video nearly free, but don't build it unasked).
- "The narration doesn't play in Google Slides" → the import dropped it: narrating-pptx, Google Slides section.
- "Make a video of my deck" with no narration yet → the full chain; the narration is where the work is.
- "Make a video" and narration already exists → stage 4 only, reusing `narration/`.
- Deck doesn't exist yet → stage 1 first; don't write narration for unbuilt slides.
