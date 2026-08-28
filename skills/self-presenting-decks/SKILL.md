---
name: self-presenting-decks
description: Use when a presentation needs to explain itself — the user wants a deck with voiceover/narration, a self-playing or self-presenting deck, "add audio to my slides and also make a video", a narrated deck to share async (WhatsApp/Slack/Drive/email), or asks how to produce/update the whole deck → narration → video chain. Use for orchestration even when only one artifact is mentioned, if others exist for the same deck.
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
| 0. Intake | — | ElevenLabs voice ID + `ELEVENLABS_API_KEY` (env var, never echoed); language/register choices (these live in narrating-pptx, not here) |
| 1. Build/edit the deck | **document-skills:pptx** (pptxgenjs or template editing); **presentation-generator** for AI-image decks | `deck.pptx` (the clean copy — keep it) |
| 2. Validate rendering | **office-render** — real PowerPoint → PDF → images | layout proof + **the PDF the video will reuse — always from the CLEAN pptx** (the narrated copy renders speaker icons onto slides) |
| 3. Narrate | **narrating-pptx** — scripts → **human approves scripts BEFORE TTS** (it's real credit spend, often in a cloned voice) → TTS → embed → PowerPoint-authored autoplay → its own validation pass proves the narrated file clean | `narration/scripts.json`, `narration/slideNN.mp3`, `deck-narrated.pptx` |
| 4. Video | **deck-to-video** — the stage-2 clean-deck PDF + the same `narration/` mp3s → mp4 (progress bar + slide counter are defaults; flags turn them off) | `deck.mp4` |

Keep `narration/` and all artifacts as siblings next to the deck.

## Narrate like a presenter, not a screen reader

**Describe position only when the viewer could not otherwise find it.** That is the test, and it is observable before you write the line.

- **A diagram passes it.** "The dashed box inside", "the red box at the bottom", "look at the right-hand column, because that is the real argument" — the viewer cannot orient without you, and directing attention is what a presenter does.
- **Three cards of text fail it.** The viewer can already see three cards. "On the left… in the middle… on the right" over them is an audio-description track, and it makes the voice sound like it is reading the slide aloud. Say the content; the order carries the mapping.

**If you strip the verbal pointer, add a visual one.** Removing "on the left" leaves nothing telling the viewer which card is being discussed. In the video that gap is closable — highlight the active element in time with the voice (see deck-to-video). In the pptx it is not, so accept that the narrated deck is slightly less guided and let the card headings carry it.

## Three artifacts, three audiences

- **Clean pptx** — live presenting; humans talk over it.
- **Narrated pptx** — guided self-review at the viewer's own pace (they can linger, skip, re-listen per slide).
- **mp4** — zero-friction async sharing; plays anywhere, but forces the narration's pace. Never ship *only* the mp4 to someone who needs to study the content.

Keep all three named as siblings (`Deck.pptx`, `Deck_Narrated.pptx`, `Deck.mp4`) so nobody presents the narrated copy live by accident.

## The update matrix — what to rebuild when something changes

| What changed | Rebuild |
|---|---|
| Slide content/visuals | deck → re-render the **whole** PDF (PDFs aren't patchable per page) → **re-check affected narration scripts** (they reference what's visible) → regenerate only the changed clips → re-embed + autoplay → video |
| Narration text only | the changed clips → re-embed + autoplay pptx → video → **re-align those clips** if the video highlights elements in time with the voice |
| Narration voice settings (e.g. stability) | **all** clips, not just the changed ones — mixed settings are audible → re-embed → re-align → video |
| Narration pace ("too slow") | `ffmpeg -filter:a atempo=1.1` on the mp3s (pitch-preserving, no TTS cost) → re-embed → **re-align if anything is synced to the voice** (atempo shifts every timestamp) → video |
| Video overlay only (bar, counter) | video only — pptx artifacts untouched |

Regenerating *only changed* narration clips saves TTS cost — but always rebuild the narrated pptx and video from the full final audio set.

## Hard-won rules that hold across the whole pipeline

- **Never hand-write PowerPoint `<p:timing>` autoplay XML** — corrupts the file. PowerPoint authors it via the narrating-pptx script. A video-only request is the escape hatch when PowerPoint isn't available.
- **All slide rasterization comes from real PowerPoint** (office-render), never LibreOffice — fonts and layout re-flow otherwise, and the video won't match the deck.
- **One narration source of truth**: the pptx and the video must embed the *same* mp3s, same pace — otherwise reviewers hear two different presentations.
- **Ear-testing is human work**: autoplay start and audio levels can't be verified headlessly — say so explicitly when handing off.
- **Timings are read from the audio, never estimated**: anything synced to the voice (highlights, subtitles) comes from forced alignment of the finished clips, so a re-record self-corrects on the next align.

## Choosing the entry point

- "Add narration/voiceover to my deck" → stages 2–3 (+ offer 4; the mp3s make the video nearly free).
- "Make a video of my deck" with no narration yet → the full chain; the narration is where the work is.
- "Make a video" and narration already exists → stage 4 only, reusing `narration/`.
- Deck doesn't exist yet → stage 1 first; don't write narration for unbuilt slides.
