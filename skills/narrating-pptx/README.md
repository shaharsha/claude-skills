# narrating-pptx

Turn any `.pptx` into a self-presenting deck: write presenter-style narration scripts in any language (Hebrew, English, mixed), generate one clip per slide with ElevenLabs (via [elevenlabs-tts](../elevenlabs-tts), on **Eleven v4**), embed the clips, and set autoplay-on-slide-entry through **real PowerPoint** — the one method that doesn't trigger the "found a problem / Repair" dialog.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

**The iron rule, paid for in blood: never hand-write PowerPoint's `<p:timing>` autoplay XML.**

It is the obvious approach. There's a documented schema, the file is a zip of XML, and injecting a `<p:timing>` block to make audio autoplay on slide entry looks like a twenty-line patch. It corrupts the file. PowerPoint opens it and offers to Repair — which is a *deliverable* failing in front of whoever you sent it to.

The only reliable method is letting real PowerPoint author that XML itself, via AppleScript play-settings. This skill exists so nobody re-derives that the expensive way.

Everything else here is the same shape — mistakes that each happened once and are now impossible:

- **AppleScript `presentation 1` edits the wrong deck.** PowerPoint's "reopen windows" resurrects stale decks that steal index 1. You save changes into a file you weren't looking at.
- **Caption-length scripts get rejected by users.** ~200 chars per slide reads as a label, not a presentation. The voice *is* the presenter.
- **Validating with LibreOffice proves nothing** — it tolerates XML that PowerPoint rejects.

## What it does

```
scripts.json ──elevenlabs-tts generate_tts.py (eleven_v4)──────────────▶ audio/slideNN.mp3
                                                                        │
deck.pptx ──────────────────────────────────────────────────────────────┤
                                                                        ▼
                                        add_audio.py (speaker icon per slide)
                                                        │
                                    set_autoplay.sh (real PowerPoint authors <p:timing>)
                                                        │
                                        validate: PowerPoint PDF export ──▶ narrated.pptx
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
ln -s "$PWD/claude-skills/skills/narrating-pptx" ~/.claude/skills/narrating-pptx
```

## Requirements

- **macOS + Microsoft PowerPoint** installed — required for the autoplay step, which has no substitute.
- `python-pptx`
- [elevenlabs-tts](../elevenlabs-tts) installed beside it — it generates the audio
- `ELEVENLABS_API_KEY` as an env var (never pasted into output)
- An ElevenLabs voice ID (elevenlabs-tts lists the defaults)

## Quick start

```bash
# 1. Write narration scripts → scripts.json
#    {"01": "text…", "02": "text…"} — 1-based, zero-padded slide positions

# 2. Generate speech with the elevenlabs-tts skill (parallel, 429-safe)
export ELEVENLABS_API_KEY=...
python3 ../elevenlabs-tts/scripts/generate_tts.py scripts.json VOICE_ID audio/ --model eleven_v4

# 3. Embed one clip per slide
python3 scripts/add_audio.py deck.pptx audio/ narrated.pptx

# 4. Autoplay — via real PowerPoint (the only safe way)
cp narrated.pptx ~/Downloads/          # PowerPoint sandbox: Downloads/Documents/Desktop
scripts/set_autoplay.sh "$HOME/Downloads/narrated.pptx" SLIDE_COUNT
# expect: "autoplay set on N media shapes", N == number of narrated slides

# 5. Validate — export through real PowerPoint; a clean PDF of all slides
#    means no repair dialog. Then a human ear-tests slideshow mode once.
```

## Writing the scripts

This is where a narrated deck is won or lost.

- **Language: exactly what the user asks for.** Hebrew, English, or mixed. For Hebrew, write like a native presenter who naturally keeps technical terms in English (Israeli hi-tech register: "ה-agent מנתח את הדאטה וכותב manifest"). Don't translate terms the audience uses in English.
- **Depth: ~600–900 chars per slide (≈45–75 s).** Open with context → work through what the slide actually shows → explain the *why* → bridge to the next slide. Point at positions only where the viewer couldn't otherwise find the thing (a box inside a diagram), not over three cards they can already see.
- **Numbers as words** — the slide says "9 days", the script says "nine days".
- **Direct the delivery with audio tags** — English bracket tags at the beat they modify, tagging the shifts. How v4 reads them, the full catalog, Hebrew behaviour, stability and the 10,000-char limit all live in [elevenlabs-tts](../elevenlabs-tts).
- **The human approves the scripts before any audio is generated** — every later script change is a regeneration.

## The progress bar during playback

Elapsed/remaining time is **hover-only** — there is no persistent countdown for embedded audio. For the hover bar to appear at all, three things must hold:

1. Slide Show ribbon → **"Show Media Controls" is checked**.
2. The icon is **≥ 0.5 in** — big enough to hover. A 0.28 in icon (~27 px) is an unusable target, and users report "no progress bar" when the real problem is they can't hit the icon.
3. `set_autoplay.sh` sets *hide while NOT playing*, never *hide during show* (which removes the hover target entirely).

To resize icons on an already-narrated deck, use python-pptx geometry — round-trips preserve the timing XML. **Match media shapes by element XML, not `shape_type == MEDIA`** (audio pics report as `PICTURE`):

```python
for sh in slide.shapes:
    if 'audioFile' in sh._element.xml or 'videoFile' in sh._element.xml:
        sh.width = sh.height = Inches(0.5)
        sh.left = prs.slide_width - Inches(0.62); sh.top = prs.slide_height - Inches(0.62)
```

Avoid AppleScript for geometry — its `top`/`left position` properties fight the compiler. AppleScript is only for play settings.

## Gotchas

| Mistake | Consequence | Fix |
|---|---|---|
| Hand-writing `<p:timing>` autoplay XML | PowerPoint Repair dialog — corrupt deliverable | `set_autoplay.sh` lets PowerPoint author it |
| AppleScript `presentation 1` | Edits a stale reopened deck; wrong file saved | Target `presentation "name.pptx"`; verify slide count |
| Hand-rolling the TTS calls | v3-era settings, 429s, error bodies saved as `.mp3` | elevenlabs-tts' `generate_tts.py` |
| Caption-length scripts (~200 chars) | "It should explain more — it's the presenter" | 600–900 chars, presenter structure |
| `for i in $var` in zsh | No word splitting — loop gets one token | `${=var}` in zsh, or use Python |
| Fixed `delay 2` after opening a big pptx | "object does not exist" AppleScript error | Wait-loop until slide count matches (in the script) |
| Validating with LibreOffice only | Misses PowerPoint-strict corruption | Export via real PowerPoint |
| Icon ≤ 0.3 in | User can't hover → "no progress bar" | 0.5 in, bottom-right (the default) |
| `shape_type == MEDIA` in python-pptx | Finds 0 audio shapes | Match `'audioFile' in sh._element.xml` |

## Caveats

- Autoplay survives PowerPoint desktop/365. **Google Slides import and LibreOffice are unreliable** with embedded-audio autoplay; PDF export drops audio entirely.
- File grows ~0.3–1.5 MB per narrated minute (mp3 128 kbps).
- Keep a clean, non-narrated copy — narration is a variant, not a replacement.
- Deck edits after narration are fine; re-run the autoplay step only if you re-add media.
- **You cannot verify sound headlessly.** Say so; never claim you heard it.

## Related skills

- [elevenlabs-tts](../elevenlabs-tts) — the voice: model, tags, settings, generation, leak checks, timings.
- [self-presenting-decks](../self-presenting-decks) — the orchestration map this is stage 3 of.
- [deck-to-video](../deck-to-video) — reuses the same per-slide mp3s to build the mp4.
- [office-render](../office-render) — the real-PowerPoint export used for validation.
- [presentation-generator](../presentation-generator) — produces decks worth narrating.

## License

MIT — see [LICENSE](../../LICENSE).
