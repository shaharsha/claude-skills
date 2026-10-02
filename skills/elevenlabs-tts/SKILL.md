---
name: elevenlabs-tts
description: Use when generating speech, voiceover, narration, or any spoken audio with ElevenLabs in any language (Hebrew, English, mixed) — writing scripts with audio tags, choosing eleven_v4 vs v3 settings, batching many clips, cloned or library voices, or getting word/character timings for subtitles and synced animation. Also use when ElevenLabs output reads tags aloud, sounds monotone or over-acted, drifts between clips, mispronounces a term, returns 429s, or when alignment/subtitles drift after tagged narration. Use whenever the user mentions ElevenLabs, eleven_v4/eleven_v3, Eleven v4, audio tags, or TTS voiceover — even if they don't say "ElevenLabs" but want a voice generated.
---

# ElevenLabs TTS (Eleven v4)

## Overview

Script → speech with ElevenLabs, done so the delivery is directed, the batch is consistent, and the timings are trustworthy. **Eleven v4** (`eleven_v4`, released 2026-09-28) is the default for anything pre-rendered. It directs delivery entirely through **audio tags written into the text** — there is no speed, style, or SSML control — so writing the script *is* directing the performance.

You cannot hear the audio. Everything here is built so that the parts a machine *can* check get checked (tags spoken vs performed, durations, alignment), and the parts it can't (is this the right emotion?) are handed to a human explicitly.

**Requirements:** `ELEVENLABS_API_KEY` env var (never echo it), a voice ID, Python 3 (scripts are stdlib-only), `afinfo`/`ffprobe` for durations.

## Choose the model

| Model | Use for |
|---|---|
| `eleven_v4` | **Default.** Voiceover, narration, audiobooks, decks — anything pre-rendered. 10,000 chars/request, 90+ languages incl. Hebrew |
| `eleven_v4_turbo` | Real-time agents only, via the Text to Dialogue WebSocket (see `references/api.md`) — not for narration |
| `eleven_v3` | Only to regenerate a clip inside a set already made on v3 — mixing models in one deck is audible. 5,000 chars/request |

**Always send `model_id`** — the endpoint's own default is still `eleven_multilingual_v2`, which ignores tags.

## The request

```
POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128
xi-api-key: $ELEVENLABS_API_KEY
{"text": "...", "model_id": "eleven_v4",
 "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
```

v4 has exactly two voice controls:

| Setting | Range | What it does on v4 |
|---|---|---|
| `stability` | 0–1, **continuous** (default 0.5) | lower = more expressive and varied take-to-take; higher = closer to a fixed baseline, less dramatic |
| `similarity_boost` | 0–1 (default 0.75) | adherence to the reference voice; higher can cost naturalness |

What changed from v3, because old scripts and habits will carry it in: v3's three stability presets (0.0 Creative / 0.5 Natural / 1.0 Robust) are gone — any value works (0.3 verified accepted). Similarity is now honoured (v3 ignored it, so old settings did nothing). `style`, `speed` and `use_speaker_boost` are still in the schema but are not v4 controls — setting them only *looks* like control. SSML `<break>` is disabled. Optional extras: `seed` (best-effort determinism), `language_code` (ISO 639-1), request stitching — see `references/api.md` §1–2.

## Write the script — you are the "Enhance" button

ElevenLabs' UI "Enhance" is an LLM inserting tags; there is no Enhance API. You do it, and on v4 it's the whole directing job.

**How v4 reads tags** (full catalog and troubleshooting: `references/audio-tags.md`):
- **Square brackets, English, placed right before the words they colour** (or right after, for a reaction: `…done. [sighs]`). English tags work *inside Hebrew and other languages*.
- **A tag holds until the next one.** Tag the *shifts* in the performance, not every sentence. One tag per clause; contradictory tags on the same words blur.
- **Descriptive, comma-combined directions are the v4 idiom**: `[Warm, conversational tone, faint amusement]`, `[Low, steady voice, restrained urgency]`, `[Gentle pause, then quiet realization]`. Single words (`[warm]`, `[curious]`) still work.
- **Say "voice" when you mean voice.** v4 also renders sound effects, so an ambiguous tag can come out as an SFX. `[low, gravelly voice]`, not `[gravel]`. Keep SFX tags (`[applause]`, `[door creaks]`) out of narration unless asked — they're baked into the speech track and shift every timing after them.
- **Pace and pauses live in the text:** `[pause]`, `[long pause]`, `[slowly]`, `[rushed]`, ellipsis `…`, line breaks. CAPS = emphasis. No speed setting exists.
- **Don't put stage directions in prose** ("she said warmly") — prose is spoken.

**Narration palette** (presenter / explainer register): `[Warm, conversational tone]` · `[Quiet, measured narration]` · `[thoughtful]` · `[curious]` · `[Gradually building energy]` · `[excited]` · `[Pause, dry amusement]` · `[soft chuckle]` · `[serious]` · `[sighs]` · `[Softening, reflective]` · `[Voice rising into firm resolve]` · `[Brief pause]`. Match the tag to the content's beat (reveal → `[excited]`; cost → `[serious]`; wry aside → `[Pause, dry amusement]`; "so what?" → `[curious]`).

**Density:** for a clean professional read, a baseline tag at the start plus a tag at each real shift — typically 2–5 per 600–900 chars. For an explicitly expressive performance, more shifts, varied — but each must mark a change. If every sentence has its own tag, they stop meaning anything and delivery gets jerky. `[excited]` plus `!` reads childish on many voices; prefer `[warm, calm]`-style baselines with one or two peaks.

**Hebrew and other non-English text:**
- English tags inside the Hebrew are performed, not read aloud (verified 2026-10-02 with Josh on v4: Scribe transcripts of tagged Hebrew clips contained no tag words, and `[Pause, dry amusement]` produced a real ~1.9 s pause). Still sample one clip per new voice/register — `scripts/check_tags_spoken.py`.
- Write numbers, dates, units and acronyms out in words — "11" is "eleven" or "אחת-עשרה" depending on the reader's guess. `language_code: "he"` helps short or ambiguous text.
- Keep the terms the audience says in English in English, joined the Hebrew way (`ה-pipeline`, `ה-agent`).
- If a loanword's stress lands wrong, write it in Latin script; if a name breaks, add niqqud or respell it phonetically. (Third-party v3-era findings — re-check on v4.)
- A voice speaking a language other than its reference language now gets a *native* accent in that language — deliberate on v4.

**Pronunciation of one stubborn term:** inline IPA in slashes inside quotes — `"/ˈtɔːrk/"` — with stress marks; or a pronunciation dictionary (`references/api.md` §7). SSML `<phoneme>` does not work on v4.

**Limit:** 10,000 chars per request on v4 (5,000 on v3); tags count. Longer → split at paragraph boundaries.

## Generate — sample first, then batch

**1. Sample before spending the batch.** You can't hear it; the user can. Generate one representative, tag-rich clip and run the leak check on it. If the brief has any expressive ambition, A/B stability on that clip (e.g. 0.35 vs 0.5) and let the human pick. Since v4 is updated continuously, re-sample before a big batch even with a voice that worked last month.

**2. Batch** with the bundled script (parallel, 429-safe, validates that responses are real mp3, refuses over-limit scripts):

```bash
export ELEVENLABS_API_KEY=...   # env var only — never paste the key into output
python3 <this-skill-dir>/scripts/generate_tts.py scripts.json VOICE_ID audio/ \
  --model eleven_v4 --stability 0.5 [--similarity 0.75] [--seed 42] [--language-code he] [--stitch]
# scripts.json: {"01": "text…", "02": "text…"}  →  audio/slide01.mp3 … (--prefix to rename)
```

- **One stability, one model, one voice for the whole set** — a mix is audible. The script records every clip's settings in `audio/_manifest.json` and warns when a directory mixes them, so a later partial regeneration can't silently drift.
- `--concurrency 4` by default (Creator plan allows 5). A 429 is concurrency, not quota; the script backs off.
- `--stitch` generates sequentially, passing earlier clips' request IDs (`previous_request_ids`) for smoother prosody across boundaries — worth it when clips play back-to-back with no gap (audiobook chapters, one continuous voiceover split for length). Separate slides with a pause between them don't need it.
- Regenerating one clip later: same settings, and `--seed` if you used one, so it sits closer to its neighbours.

**3. Check what a machine can check:**
```bash
python3 <this-skill-dir>/scripts/check_tags_spoken.py scripts.json audio/ [--only 03 07]   # Scribe transcript vs script
afinfo audio/slide01.mp3 | grep duration      # or ffprobe
```
`check_tags_spoken.py` flags a clip when a tag word was spoken (`LEAK`) or the transcript runs longer than the tag-free script (`EXTRA` — catches a tag spoken in another script's letters). It costs speech-to-text credits; run it on the sample and on a few batch clips, not on every draft.

**4. Hand the ear-check to the human, explicitly.** Emotion, over-acting, pace and pronunciation need ears. Say that you have not heard the audio; never claim you did.

## Timings for subtitles and synced visuals

When anything must follow the voice, read the timings out of the finished audio — never estimate them, and never build them from text length.

```bash
python3 <this-skill-dir>/scripts/align_narration.py scripts.json audio/ alignment/
```

This calls `POST /v1/forced-alignment` (audio + transcript → per-character and per-word `start`/`end`, plus `loss`) and writes `alignment/slideNN.json`. Two rules it enforces, spelled out because hand-rolled versions break on them:
- **Strip the tags first.** Tags are performed, not spoken; leave `[Warm, conversational tone]` in and the aligner hunts for those words in the audio and drags every later offset. v4 tags contain commas, hyphens and whole sentences — strip *anything in brackets*, not `[a-zA-Z ]+` (that pattern silently misses v4 tags).
- **Check `len(characters) == len(stripped text)`.** Then a character offset in the stripped script converts straight to a timestamp. A mismatch means every offset on that clip is wrong; the script exits non-zero.

**`/with-timestamps` vs forced alignment.** `/with-timestamps` returns timing in the same request as the audio, so it's free if you're generating anyway — but on v4 its `characters` are the input *including tags*, and each tag's characters carry the time of its performance (a `[Pause, dry amusement]` span covered the actual 0.6 s pause). Drop the tag spans and the remaining word starts matched forced alignment within ~0.05 s, with one word 0.26 s off (measured 2026-10-02 on one v4 take). So it's usable as a first pass. Forced alignment stays the master because it works on audio that **already exists**: after an `atempo` pace change, a single-clip regeneration, or for clips that were generated without timestamps, it re-reads the real audio for speech-to-text cents, and it returns `words[]` and `loss` for sanity checks. If you take timing from `/with-timestamps`, save the response JSON beside the mp3 — it can't be fetched again later.

`loss` is relative: compare clips within a batch and investigate a clear outlier; short clips with long tag-driven pauses score higher. Hebrew aligns fine despite the docs' language list (verified 2026-10-02).

## Voices

Pass any voice ID. **Default to Shahar** unless the user names another. Shahar is the owner's own clone, so it exists only on the owner's ElevenLabs account: if the first request returns `HTTP 404 voice_not_found` (the generator fails on it immediately, nothing billed), fall back to **Josh** and say so. All four generated cleanly on `eleven_v4` on 2026-10-02 (tags performed, not spoken), and the owner ear-checked Josh, Jarnathan and Shahar on v4.

| Name | Voice ID | Notes |
|---|---|---|
| **Shahar** ⭐ | `p9D03Ni3gGv3AsJpmpBV` | **default** — the owner's own instant voice clone; **works only with the owner's ElevenLabs account/key** (anyone else: `voice_not_found` → use Josh). Created after v4 launched, so no v4 retraining needed |
| **Josh** | `ZoiZ8fuDWInAcwPXaVeq` | fallback default — warm, slightly faster; good for Hebrew narration |
| Kevin | `1fz2mW1imKTf5Ryjk5su` | alternative, a little more measured |
| Jarnathan | `c6SfcYrb2t09NHXiT80T` | Voice Library, "Confident and Versatile" — middle-aged American English, conversational. On Hebrew text v4 gives it a native Hebrew accent rather than an American one |

Library voices work on v4 as-is. A user's **own** clones made before v4 should be retrained on v4 in the web app (My Voices → "+" next to Eleven v4) — and a retrained clone can sound different from its v3 self, so re-sample before regenerating anything that must match old audio.

## Cost

Characters (tags included) are billed. `eleven_v4` is $0.022/1K chars **until 2026-10-12**, list $0.08 — same as v3, so there's no cost reason to stay on v3. A 15-slide deck at ~800 chars/slide ≈ 12K chars. Real cost is regenerations: get scripts approved by the human *before* generating, sample before batching.

## Common mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Omitting `model_id` | Endpoint defaults to Multilingual v2 — tags ignored or spoken | Always send `eleven_v4` |
| v3 habits: stability only 0/0.5/1, `speed`/`style` to set pace | Pace unchanged; v4 control misunderstood | Continuous stability; pace via tags and punctuation |
| SSML `<break time="1s"/>` | Dropped on v4 | `[pause]`, `[long pause]`, `…` |
| Tagging every sentence | Jerky, over-acted | Tag the shifts; tags carry forward |
| Ambiguous tag (`[storm]`, `[gravel]`) | Rendered as a sound effect | Describe the voice: `[low, gravelly voice]` |
| Tag stripper `\[[a-zA-Z ]+\]` | Misses `[Pause, dry amusement]` → alignment drift, length mismatch | Strip `\[[^\[\]\n]*\]` (the bundled scripts) |
| Subtitles straight from `/with-timestamps` | Tag text appears in captions; tag spans hold real pause time | Drop the tag spans, or force-align the stripped script |
| Regenerating a few clips at new settings | Audible seam between clips | Regenerate the whole set; the manifest warns |
| Size-based "error response" check | Short real clips rejected and paid for again | Check mp3 magic bytes (bundled script) |
| Firing all requests at once | 429s on most | `--concurrency 4` with backoff |
| "It sounds right" | You can't hear | Leak check + durations; ear-check by the human |
| Old clone used unretrained on v4 | Lower fidelity | Retrain on v4, re-sample |

## Related skills

- **narrating-pptx** — embeds these clips one-per-slide into a pptx with PowerPoint-authored autoplay.
- **deck-to-video** — builds the mp4 from the same clips; consumes `alignment/` for subtitles and highlights.
- **self-presenting-decks** — the deck → narration → video map and its update matrix.
