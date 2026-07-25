# self-presenting-decks

The orchestration map for making a presentation explain itself: **content → narration → video**, which skill owns each stage, the three-artifacts-three-audiences rule, and an update matrix for exactly what to rebuild when slides change vs narration text vs pace vs video overlays.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Each stage of a narrated deck already has a skill. What kept going wrong was the *seams* between them.

**Order is the whole game: content → narration → video.** Narration scripts describe what's on the slides ("look at the tree on the left"), so slides must be final before a word is written. The video embeds both the rendered slides and the audio, so it's always last. Edit anything upstream and everything downstream is invalidated — quietly, because a stale video still plays.

Three seam rules in particular are easy to get wrong and expensive to discover late:

- **The video renders from the *clean* deck's PDF, not the narrated one** — the narrated copy has speaker icons drawn onto every slide, which would be baked into the video forever.
- **Scripts get human approval *before* TTS.** That's real credit spend, often in a cloned voice. Approving after generation means paying twice.
- **Regenerate only the changed narration clips, but always rebuild the final artifacts from the full audio set.** Half-updated audio is the classic way to ship a deck where two slides sound like a different person.

## What it does

```
deck (pptx) ──▶ narration (audio + autoplay pptx) ──▶ video (mp4)
   content            depends on final slides          depends on final slides + final audio
```

| Stage | Skill | Output |
|---|---|---|
| 0. Intake | — | ElevenLabs voice ID + `ELEVENLABS_API_KEY` (env var, never echoed); language and register choices |
| 1. Build/edit the deck | Anthropic's `pptx` skill (pptxgenjs or template editing); [presentation-generator](../presentation-generator) for AI-image decks | `deck.pptx` — the clean copy, keep it |
| 2. Validate rendering | [office-render](../office-render) — real PowerPoint → PDF → images | Layout proof, **and the PDF the video will reuse** |
| 3. Narrate | [narrating-pptx](../narrating-pptx) — scripts → human approval → TTS → embed → PowerPoint-authored autoplay → validation | `narration/scripts.json`, `narration/slideNN.mp3`, `deck-narrated.pptx` |
| 4. Video | [deck-to-video](../deck-to-video) — the stage-2 clean PDF + the same mp3s | `deck.mp4` |

Keep `narration/` and every artifact as siblings next to the deck.

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install documents-and-decks@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/self-presenting-decks" ~/.claude/skills/self-presenting-decks
```

This is a guidance skill — no scripts of its own. The stages it points at have the dependencies (macOS + PowerPoint, ffmpeg, an ElevenLabs key).

## Quick start

Ask for the outcome, not the stage:

- "add narration to this deck and make a video I can send on WhatsApp"
- "make my deck self-presenting"
- "the pace is too slow — fix it and rebuild everything"

## Three artifacts, three audiences

| Artifact | For | Note |
|---|---|---|
| **Clean pptx** | Live presenting | A human talks over it |
| **Narrated pptx** | Guided self-review | Viewer can linger, skip, re-listen per slide |
| **mp4** | Zero-friction async sharing | Plays anywhere, but forces the narration's pace |

Never ship *only* the mp4 to someone who needs to study the content. Name all three as siblings (`Deck.pptx`, `Deck_Narrated.pptx`, `Deck.mp4`) so nobody presents the narrated copy live by accident.

## The update matrix

| What changed | Rebuild |
|---|---|
| Slide content / visuals | Deck → re-render the **whole** PDF (PDFs aren't patchable per page) → **re-check affected narration scripts** (they reference what's visible) → regenerate only changed clips → re-embed + autoplay → video |
| Narration text only | The changed clips → re-embed + autoplay pptx → video |
| Narration pace ("too slow") | `ffmpeg -filter:a atempo=1.1` on the mp3s (pitch-preserving, no TTS cost) → re-embed → video |
| Video overlay only (bar, counter) | Video only — pptx artifacts untouched |

## Choosing the entry point

- *"Add narration/voiceover to my deck"* → stages 2–3, and offer 4; the mp3s make the video nearly free.
- *"Make a video of my deck"*, no narration yet → the full chain. The narration is where the work is.
- *"Make a video"*, narration already exists → stage 4 only, reusing `narration/`.
- Deck doesn't exist yet → stage 1 first. Don't write narration for unbuilt slides.

## Gotchas

- **Never hand-write PowerPoint `<p:timing>` autoplay XML** — it corrupts the file. PowerPoint authors it, via narrating-pptx. A video-only request is the escape hatch when PowerPoint isn't available.
- **All slide rasterization comes from real PowerPoint**, never LibreOffice — fonts and layout re-flow otherwise, and the video stops matching the deck.
- **One narration source of truth.** The pptx and the video must embed the *same* mp3s at the same pace, or reviewers hear two different presentations.
- **Ear-testing is human work.** Autoplay start and audio levels can't be verified headlessly — say so explicitly when handing off, and never claim you heard it.

## Related skills

- [narrating-pptx](../narrating-pptx) · [deck-to-video](../deck-to-video) · [office-render](../office-render) · [presentation-generator](../presentation-generator)

## License

MIT — see [LICENSE](../../LICENSE).
