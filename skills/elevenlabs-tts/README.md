# elevenlabs-tts

Script → speech with ElevenLabs **Eleven v4**, in any language (Hebrew, English, mixed): directing the performance with v4 audio tags, generating a consistent batch of clips, checking that no tag was read aloud — without ears — and getting trustworthy word timings for subtitles and synced animation.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Eleven v4 (released 2026-09-28) moves all delivery control into the text. There is no speed slider, no style slider, no SSML — only two voice settings and whatever you write in square brackets. So the script *is* the direction, and an agent writing it needs to know how v4 actually reads a tag. Most of what it would carry over from v3 is now wrong or misleading:

- **Stability is a continuous dial now.** v3 had three presets (Creative / Natural / Robust); v4 takes any 0–1 value. Similarity, which v3 ignored, now matters.
- **Tags carry forward until the next one** and take free-form, comma-combined directions — `[Warm, conversational tone, faint amusement]`. Re-tagging every sentence makes delivery jerky.
- **A tag can turn into a sound effect**, because v4 renders SFX too. Say "voice" when you mean voice.
- **The endpoint's default model is still Multilingual v2.** Forget `model_id` and your tags are ignored.
- **A tag stripper written for v3 silently breaks on v4.** `\[[a-zA-Z ]+\]` doesn't match `[Pause, dry amusement]`, so the tag reaches the forced aligner and every subtitle after it drifts.
- **`/with-timestamps` returns the tags too**, and each tag's characters hold the time of the pause or reaction it caused.

And one thing that hasn't changed: the agent can't hear the result. The skill splits verification into what a machine can check (a speech-to-text pass that catches tags spoken aloud, durations, alignment length) and what it hands to a human with an explicit "I have not listened to this".

Facts that the docs leave open were measured against the live API on 2026-10-02 rather than guessed. The checks covered continuous stability, tags in `/with-timestamps`, Hebrew forced alignment, request stitching, and tags performed rather than spoken in Hebrew text.

## What it does

```
script + tags ──▶ sample one clip ──▶ check_tags_spoken.py (Scribe) ──▶ human ear-check / stability A/B
                                                                                   │
scripts.json ──▶ generate_tts.py (eleven_v4, one setting, 429-safe, manifest) ──▶ audio/*.mp3
                                                                                   │
                                     align_narration.py (forced alignment, tags stripped) ──▶ alignment/*.json
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
ln -s "$PWD/claude-skills/skills/elevenlabs-tts" ~/.claude/skills/elevenlabs-tts
```

## Requirements

- `ELEVENLABS_API_KEY` as an env var, never pasted into output. The key needs Text to Speech; the leak check and alignment also use Speech to Text.
- A voice ID
- Python 3. The scripts use only the standard library.
- `afinfo` (macOS) or `ffprobe` for durations

## Quick start

```bash
export ELEVENLABS_API_KEY=...
# scripts.json: {"01": "[Warm, conversational tone] Text…", "02": "…"}

# 1. sample one representative clip, check it, let a human listen / pick stability
python3 scripts/generate_tts.py sample.json VOICE_ID sample/ --stability 0.5
python3 scripts/check_tags_spoken.py sample.json sample/

# 2. the batch, one setting for every clip (recorded in audio/_manifest.json)
python3 scripts/generate_tts.py scripts.json VOICE_ID audio/ --stability 0.5 [--seed 42] [--stitch]

# 3. timings for subtitles / synced visuals
python3 scripts/align_narration.py scripts.json audio/ alignment/
```

## The scripts

| Script | What it does |
|---|---|
| `generate_tts.py` | One clip per `scripts.json` entry; parallel with 429 backoff; validates responses are real mp3 (not error JSON); refuses over-limit scripts per model; `--seed`, `--language-code`, `--stitch` (request stitching); writes `_manifest.json` and warns when a directory mixes settings |
| `check_tags_spoken.py` | Transcribes clips with Scribe and flags `LEAK` (a tag word was spoken) or `EXTRA` (transcript longer than the tag-free script — catches a tag spoken in another alphabet) |
| `align_narration.py` | Forced alignment against the tag-stripped script; verifies `len(characters) == len(text)` so character offsets map to timestamps |

## References

- [`references/audio-tags.md`](references/audio-tags.md) — the v4 tag vocabulary by family, narration directions, writing your own, troubleshooting.
- [`references/api.md`](references/api.md) — full request schema, request stitching, timestamps vs forced alignment, Text to Dialogue, real-time Turbo, Studio, pronunciation, output formats, concurrency, pricing, clones.

## Gotchas

| Mistake | Consequence | Fix |
|---|---|---|
| Omitting `model_id` | Multilingual v2 — tags ignored or spoken | Always send `eleven_v4` |
| `speed` / `style` / `<break>` for pacing | Silently ignored on v4 | `[pause]`, `[slowly]`, `…`, line breaks |
| Tagging every sentence | Jerky, over-acted | Tag the shifts — tags carry forward |
| `[gravel]`, `[storm]` | Rendered as a sound effect | Describe the voice: `[low, gravelly voice]` |
| `\[[a-zA-Z ]+\]` tag stripper | Alignment drift after the first v4 tag | Strip anything in brackets |
| Regenerating a few clips at new settings | Audible seam | Regenerate the set; the manifest warns |
| Size-based error check | Short real clips rejected and re-billed | Check mp3 magic bytes |
| "It sounds right" | You can't hear | Leak check + durations + a human ear-check |

## Related skills

- [narrating-pptx](../narrating-pptx) — embeds these clips one per slide into a pptx with PowerPoint-authored autoplay.
- [deck-to-video](../deck-to-video) — builds an mp4 from the same clips and uses `alignment/` for subtitles and highlights.
- [self-presenting-decks](../self-presenting-decks) — the deck → narration → video map.

## License

MIT — see [LICENSE](../../LICENSE).
