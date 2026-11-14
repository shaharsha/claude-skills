# elevenlabs-tts

Script → speech with ElevenLabs **Eleven v4**, in any language (Hebrew, English, mixed): short spoken briefings ("make me an MP3 explaining this"), directing the performance with v4 audio tags, generating a consistent batch of clips, checking that no tag was read aloud — without ears — and getting trustworthy word timings for subtitles and synced animation.

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

Most real use turned out not to be decks at all but **spoken briefings**: one listener, one file, a plan or a set of decisions explained in a minute or two. Every session that made one rebuilt the same pieces by hand: loading the key, joining sections into one file (an ffmpeg call that hung in an agent shell), and getting the file to the listener as something that plays. The skill now has a recipe for that, and `join_clips.py`.

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
/plugin install elevenlabs-tts@shaharsha-skills
```

That installs only this skill. For the whole `documents-and-decks` bundle, run `/plugin install documents-and-decks@shaharsha-skills` instead.

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/elevenlabs-tts" ~/.claude/skills/elevenlabs-tts
```

## Requirements

- An API key in `ELEVENLABS_API_KEY` or in `~/.config/elevenlabs/api_key` (chmod 600), never pasted into output. The key needs Text to Speech; the leak check and alignment also use Speech to Text; music and sound effects need their own permissions on the key.
- A voice ID
- Python 3. The scripts use only the standard library.
- ffmpeg and ffprobe (the trim, level, A/B and music scripts need them; `afinfo` on macOS also gives durations)

## Quick start

```bash
# a spoken briefing: one clip named after its topic, checked, ready to send
#   brief.json: {"rollout-plan-2026-11-06-en": "[Warm, conversational tone] Three decisions today…"}
python3 scripts/generate_tts.py brief.json VOICE_ID audio/ --prefix ""
python3 scripts/check_tags_spoken.py brief.json audio/

# several sections joined into one file, with each section's start time printed
python3 scripts/join_clips.py plan.mp3 audio/part*.mp3 --gap 0.8

# scripts.json: {"01": "[Warm, conversational tone] Text…", "02": "…"}

# 1. sample one representative clip, check it, let a human listen / pick stability
python3 scripts/generate_tts.py sample.json VOICE_ID sample/ --stability 0.5
python3 scripts/check_tags_spoken.py sample.json sample/

# 2. the batch, one setting for every clip (recorded in audio/_manifest.json)
python3 scripts/generate_tts.py scripts.json VOICE_ID audio/ --stability 0.5 [--seed 42] [--stitch]

# 3. timings for subtitles / synced visuals
python3 scripts/align_narration.py scripts.json audio/ alignment/

# a cast of voices with one-word lines: trim to the spoken word, then level the set
python3 scripts/trim_to_words.py lines.json raw/ trimmed/ --prefix ""
python3 scripts/level_clips.py trimmed/ leveled/ --target -18     # or: level_clips.py raw/ --report (swallowed words)

# pronunciation A/B by ear: one file, a timestamp per variant
python3 scripts/ab_concat.py ab.mp3 v1.mp3 v2.mp3 v3.mp3

# music cues and sound effects (music_v2_5, instrumental)
python3 scripts/generate_music_and_sfx.py sounds.json audio/
```

## The scripts

| Script | What it does |
|---|---|
| `generate_tts.py` | One clip per `scripts.json` entry; parallel with 429 backoff; validates responses are real mp3 (not error JSON); refuses over-limit scripts per model; `--seed`, `--language-code`, `--stitch` (request stitching); prints each clip's length and pace and flags an outlier; writes `_manifest.json` (file names and settings) and warns when a directory mixes settings |
| `join_clips.py` | Joins clips into one mp3 with a pause between them, resampling everything to one format; prints each clip's start time; `-nostdin` and a timeout so it can't hang |
| `check_tags_spoken.py` | Transcribes clips with Scribe and flags `LEAK` (a tag word was spoken), `EXTRA` (transcript longer than the tag-free script — catches a tag spoken in another alphabet) or `SHORT` (much shorter, even allowing for numbers written as digits); finds clips through the manifest |
| `align_narration.py` | Forced alignment against the tag-stripped script; verifies `len(characters) == len(text)` so character offsets map to timestamps |
| `trim_to_words.py` | Cuts short clips to the first-to-last aligned word (lead 0.04 s, tail 0.14 s, short fades); drops a repeated word or a stray sigh; never touches the originals |
| `level_clips.py` | Levels clips to one **voiced** loudness (silence excluded) with a limiter; `--report` lists 150 ms windows where a word sagged |
| `ab_concat.py` | Joins pronunciation variants a second apart and prints each start time, so the human picks by timestamp |
| `generate_music_and_sfx.py` | Music cues (`/v1/music`, `music_v2_5`, instrumental) and SFX (`/v1/sound-generation`) from one spec; skips existing files, never leaves a partial one |

## References

- [`references/audio-tags.md`](references/audio-tags.md) — the v4 tag vocabulary by family, narration directions, writing your own, troubleshooting.
- [`references/api.md`](references/api.md) — full request schema, request stitching, timestamps vs forced alignment, Text to Dialogue, real-time Turbo, Studio, pronunciation, output formats, concurrency, pricing, clones.
- [`references/short-lines-and-casts.md`](references/short-lines-and-casts.md) - a cast of voices, one-word lines, pace, crowd shouts, swallowed words, leak-check false alarms.
- [`references/pronunciation-hebrew.md`](references/pronunciation-hebrew.md) - the fix ladder for names and loanwords (Latin script, respelling, niqqud, IPA) and the A/B procedure.
- [`references/music-and-sfx.md`](references/music-and-sfx.md) - music and SFX requests, prompt recipe, planning cues against the edit, plan gating.

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
| ffmpeg from an agent shell without `-nostdin` | Hangs on stdin | `-nostdin`; the bundled scripts set it |
| A briefing left in `/tmp` as a path | The listener can't play it | Save beside the work; send it as a playable file |

## Related skills

- [narrating-pptx](../narrating-pptx) — puts these clips one per slide on a deck: a pptx with PowerPoint-authored autoplay, or Google Slides.
- [deck-to-video](../deck-to-video) — builds an mp4 from the same clips and uses `alignment/` for subtitles and highlights.
- [self-presenting-decks](../self-presenting-decks) — the deck → narration → video map.

## License

MIT — see [LICENSE](../../LICENSE).
