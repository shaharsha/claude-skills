---
name: elevenlabs-tts
description: Use when generating speech, voiceover, narration or any spoken audio with ElevenLabs in any language (Hebrew, English, mixed), including the everyday ask "make me an MP3 explaining X" - an audio briefing of a plan, thread, meeting or open decisions for someone to listen to. Also for audio-tag scripts, eleven_v4 settings, batches of clips, cloned or library voices, one file joined from several clips, or word timings for subtitles and synced animation. Use when output reads tags aloud, sounds monotone or over-acted, drifts between clips, mispronounces a term or Hebrew name, returns 429s, when ffmpeg hangs joining clips, or subtitles drift after tagged narration. Use whenever the user mentions ElevenLabs, 11labs, eleven_v4/v3, audio tags or TTS, even without naming ElevenLabs. Also for ElevenLabs music or sound effects (music_v2_5, SFX), a cast of voices with one-word lines that repeat or sigh, or a key failing with missing_permissions or paid_plan_required.
---

# ElevenLabs TTS (Eleven v4)

## Overview

Script → speech with ElevenLabs, done so the delivery is directed, the batch is consistent, and the timings are trustworthy. **Eleven v4** (`eleven_v4`, released 2026-09-28) is the default for anything pre-rendered. It directs delivery entirely through **audio tags written into the text** — there is no speed, style, or SSML control — so writing the script *is* directing the performance.

You cannot hear the audio. Everything here is built so that the parts a machine *can* check get checked (tags spoken vs performed, durations, alignment), and the parts it can't (is this the right emotion?) are handed to a human explicitly.

**Requirements:** an API key, a voice ID (default Josh, see Voices), Python 3 (scripts are stdlib-only), ffmpeg and ffprobe (the join, trim, level, A/B and music scripts use them).

**The key.** The bundled scripts read `ELEVENLABS_API_KEY`, else the first line of `~/.config/elevenlabs/api_key` (chmod 600). If neither exists but the user keeps keys in a notes file, load it inside the command substitution, matched by the line's label (`export ELEVENLABS_API_KEY="$(grep -m1 '<label of that line>' FILE | grep -oE 'sk_[A-Za-z0-9_-]+')"`), never by line number - the file changes and a line number silently picks the wrong key. Never print it; check its length if you must.

**"Explain X to me as an MP3"** is the most common job: go straight to *Spoken briefings* below. Narration for slides is the second; deck-specific steps live in narrating-pptx.

## Choose the model

| Model | Use for |
|---|---|
| `eleven_v4` | **Default.** Voiceover, narration, audiobooks, decks — anything pre-rendered. 10,000 chars/request, 90+ languages incl. Hebrew |
| `eleven_v4_turbo` | Real-time only: agents, Realtime Translation, the Text to Dialogue WebSocket (see `references/api.md`) — not for narration |
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
- Write numbers, dates, units and acronyms out in words — "11" is "eleven" or "אחת-עשרה" depending on the reader's guess — with the number agreeing in gender with its noun (שתי משימות, שני באגים). `language_code: "he"` helps short or ambiguous text.
- Keep the terms the audience says in English in English, joined the Hebrew way (`ה-pipeline`, `ה-agent`).
- Loanwords, brands and names: write them in Latin script inside the Hebrew, prefixes hyphenated (`ה-Absolut`, `מ-Dani`). Verified on v4 in 2026-10, with the full fix ladder in `references/pronunciation-hebrew.md`.
- A voice speaking a language other than its reference language now gets a *native* accent in that language — deliberate on v4.

**Pronunciation of one stubborn term:** inline IPA in slashes inside quotes — `"/ˈtɔːrk/"` — with stress marks; or a pronunciation dictionary (`references/api.md` §7). SSML `<phoneme>` does not work on v4.

**Limit:** 10,000 chars per request on v4 (5,000 on v3); tags count. Longer → split at paragraph boundaries.

## Spoken briefings: "make me an MP3 explaining X"

The most common request: one listener, one file, explaining a plan, a thread, a meeting or the decisions waiting on them, often in the middle of other work. It is not a deck, so skip the sample round: the one clip is the product. What makes it land:

1. **Short by default.** One to two minutes unless asked otherwise; up to ~5 minutes for a plan with decisions to make. "Concise" means about one minute. Josh reads Hebrew on v4 at about 14 spoken characters a second, roughly 850 a minute, so two minutes is ~1,700 characters of script. For long material, make the short briefing and offer the long version as a second file rather than one long one.
2. **Built for listening.** Open with what it covers and how many items ("three decisions, then one question"). Number the items; give your recommendation with each decision; close with what you need from the listener. Send the same numbered list in writing beside the audio: the listener maps "item two" to its link, PR or exact figure there.
3. **Self-contained.** Each file stands alone. If an earlier briefing may not have been heard, fold its content in instead of sending only what changed.
4. **Written for the ear.** No paths, code identifiers, URLs or ticket numbers read aloud: say "the import PR" and let the written list carry the number. Numbers in words, money rounded ("about one point two million shekels") with the exact figure in the list. The Hebrew rules above apply.
5. **One request if it fits.** Up to 10,000 characters is one v4 clip. Make the key the final file name, so nothing needs renaming:
   ```bash
   # brief.json: {"rollout-plan-2026-11-05-he": "[Warm, conversational tone] ..."}
   python3 <this-skill-dir>/scripts/generate_tts.py brief.json VOICE_ID audio/ --prefix "" --language-code he
   python3 <this-skill-dir>/scripts/check_tags_spoken.py brief.json audio/ --language-code he
   ```
   The generator prints the clip's length. If it overshoots the target, cut the script, don't speed the audio. Longer than one request, or several sections: generate one clip per section, then join them, which prints each section's start time for the written list:
   ```bash
   python3 <this-skill-dir>/scripts/join_clips.py plan-2026-11-05-he.mp3 audio/part*.mp3 --gap 0.8
   ```
6. **Saved beside the work.** Next to the plan or in the project's deliverables folder, not `/tmp`, named `<topic>-<YYYY-MM-DD>-<lang>.mp3`, with the script JSON and `_manifest.json` (voice and settings, for a later redo) next to it.
7. **Delivered so it plays.** If the host has a send-file tool, use it with inline rendering: in the Claude desktop app that is `SendUserFile` with `display: "render"`, which shows a player, while without it the user gets a download card and has to ask again. Give the length and the numbered list, and say you have not heard it. Email it only when asked, with the list in the body.

## Generate — sample first, then batch

**1. Sample before spending the batch.** You can't hear it; the user can. Generate one representative, tag-rich clip and run the leak check on it. If the brief has any expressive ambition, A/B stability on that clip (e.g. 0.35 vs 0.5) and let the human pick. Since v4 is updated continuously, re-sample before a big batch even with a voice that worked last month.

**2. Batch** with the bundled script (parallel, 429-safe, validates that responses are real mp3, refuses over-limit scripts):

```bash
python3 <this-skill-dir>/scripts/generate_tts.py scripts.json VOICE_ID audio/ \
  --model eleven_v4 --stability 0.5 [--similarity 0.75] [--seed 42] [--language-code he] [--stitch]
# scripts.json: {"01": "text…", "02": "text…"}  →  audio/slide01.mp3 … (--prefix to rename)
```

- **One stability, one model, one voice for the whole set** — a mix is audible. The script records every clip's file name and settings in `audio/_manifest.json` and warns when a directory mixes them, so a later partial regeneration can't silently drift. Read the voice and settings back from the manifest before regenerating a clip.
- It prints each clip's length and pace (spoken characters per second). A clip far off the batch's median is marked `PACE?`: listen to it for a dropped or repeated sentence. Tag-heavy clips with long performed pauses run slower, so it is a prompt, not a failure.
- `--concurrency 4` by default (Creator plan allows 5). A 429 is concurrency, not quota; the script backs off.
- `--stitch` generates sequentially, passing earlier clips' request IDs (`previous_request_ids`) for smoother prosody across boundaries — worth it when clips play back-to-back with no gap (audiobook chapters, one continuous voiceover split for length). Separate slides with a pause between them don't need it.
- Regenerating one clip later: same settings, and `--seed` if you used one, so it sits closer to its neighbours.

**3. Check what a machine can check:**
```bash
python3 <this-skill-dir>/scripts/check_tags_spoken.py scripts.json audio/ [--only 03 07] [--language-code he]
```
`check_tags_spoken.py` flags a clip when a tag word was spoken (`LEAK`), the transcript runs longer than the tag-free script (`EXTRA` — catches a tag spoken in another script's letters), or it runs much shorter even allowing for numbers written as digits (`SHORT` — a dropped sentence). It finds the clips through the manifest, so a `--prefix` given to the generator need not be repeated. It transcribes with Scribe v3 (`scribe_v3`); on 10 Hebrew v4 clips it gave the same ratios as v2 (0.97-1.05, checked 2026-11-13), and `--model scribe_v2` stays available to compare. It costs speech-to-text credits ($0.20 per audio hour); run it on the sample and on a few batch clips, not on every draft. For transcription itself (meetings, talks, subtitles), use elevenlabs-stt.

Reading its numbers: "words said/scripted" sits around 0.92-1.01 on a clean clip. A number-heavy script reads lower (0.75-0.87 on Hebrew decks) because Scribe writes spoken numbers as digits; the script allows for that before calling a clip `SHORT`, and prints a note instead. To confirm nothing was dropped, compare the clip's pace with its neighbours (the generator prints it).

False alarms to expect: Scribe writes non-speech as a bracketed annotation in the clip's own language (a Hebrew word for "sighs" in brackets is an annotation, not a leaked tag); a one-word clip can be transcribed in the wrong language (pass `--language-code`); and a tag word that also appears in the line itself (a `[whispering]` tag on a line that says "stop whispering") trips `LEAK`. Read the transcript before regenerating.

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

`loss` is relative: compare clips within a batch and investigate a clear outlier; short clips with long tag-driven pauses score higher. Hebrew aligns fine despite the docs' language list (verified 2026-10-02), at a much higher loss than English: 0.59-0.77 across a healthy 26-clip Hebrew deck, against 0.04-0.10 on an English one.

## Voices

Pass any voice ID. **A voice the user names always wins; otherwise use Josh** for everything, briefings and decks alike. If a request returns `HTTP 404 voice_not_found` (the generator fails on it immediately, nothing billed), that voice is not on this key's account: pick a Voice Library voice and say so. All four generated cleanly on `eleven_v4` on 2026-10-02 (tags performed, not spoken), and the owner ear-checked Josh, Jarnathan and Shahar on v4.

| Name | Voice ID | Notes |
|---|---|---|
| **Josh** ⭐ | `ZoiZ8fuDWInAcwPXaVeq` | **default** — warm, slightly faster; good for Hebrew narration and briefings |
| Shahar | `p9D03Ni3gGv3AsJpmpBV` | the owner's own instant voice clone, only when asked for; **works only with the owner's ElevenLabs account/key** |
| Kevin | `1fz2mW1imKTf5Ryjk5su` | alternative, a little more measured |
| Jarnathan | `c6SfcYrb2t09NHXiT80T` | Voice Library, "Confident and Versatile" — middle-aged American English, conversational. On Hebrew text v4 gives it a native Hebrew accent rather than an American one |

**Write as the person whose voice it is.** A script in the user's own cloned voice is the user speaking, in first person; one written as an assistant explaining things *to* the user sounds wrong in their voice. If the user switches to their own voice after hearing a draft, rewrite the script before regenerating.

Library voices and instant clones work on v4 as-is. A **professional** voice clone (PVC) needs fine-tuning on v4 in the web app (My Voices → hover → "+" next to Eleven v4), and the result can sound different from its v3 self, so re-sample before regenerating anything that must match old audio.

## A cast of voices and very short lines

Character work (one voice per character, many short lines) breaks things narration never hits. Full recipe: `references/short-lines-and-casts.md`.

- **One model and one stability for the whole cast** (0.4 suited a large comedic cast), with `language_code` set.
- **Then stop for the ear check.** Generate one sample line per voice, send the files to the human, and wait for their verdict on every voice *before* generating the real lines. A voice that is wrong for its character found after the batch costs the whole batch again.
- **One-word lines come back dirty**: the word said twice, a sigh or laugh from the tag, a long lead-in. Trim each clip to its spoken words with forced alignment, then level the set:
  ```bash
  python3 <this-skill-dir>/scripts/trim_to_words.py lines.json raw/ trimmed/ --prefix ""
  python3 <this-skill-dir>/scripts/level_clips.py trimmed/ leveled/ --target -18
  ```
- **A swallowed word mid-sentence** shows up as a weak window in `level_clips.py raw/ --report`. Regenerate that line with a firmer tag (`[clear, confident]`), compare the takes by the report, then let the human pick.
- **Pace**: `atempo=1.1` on the whole set (pitch kept) tightened comedy timing. Force-align after the tempo change, never before it.
- **Crowd shouts**: record the line in 6-10 voices and mix them 0-160 ms apart (recipe in the reference).

## Pronunciation, names and A/B tests

Read `references/pronunciation-hebrew.md` before fixing a mispronounced word. Verified on v4 (2026-10):
- **Latin script inside the Hebrew** fixed every loanword and name.
- **Niqqud on a loanword** produced a syllable-by-syllable read.
- **A prefix letter glued to a name** can turn it into another Hebrew word.

Never decide by reading a transcript. Put the variants in one file and let the human answer by timestamp:
```bash
python3 <this-skill-dir>/scripts/ab_concat.py ab.mp3 v1.mp3 v2.mp3 v3.mp3   # prints A 0:00.00 / B 0:03.41 / ...
```
On-screen text keeps normal Hebrew spelling: the Latin respelling is TTS input only.

## Music and sound effects

```bash
python3 <this-skill-dir>/scripts/generate_music_and_sfx.py sounds.json audio/
# sounds.json: {"op": {"type": "music", "prompt": "...", "seconds": 52}, "whoosh": {"type": "sfx", "prompt": "...", "seconds": 1}}
```
`/v1/music` still defaults to `music_v1`, which ElevenLabs removes on 2027-01-31. The script sends `model_id: music_v2_5` and `force_instrumental: true` by default (an entry's `model` or `"vocals": true` overrides them). A cue shorter than the stretch it scores simply stops, so ask for the window plus 2-4 s and check the real length with `ffprobe`: the length you get is not exactly the length you asked for (a 6 s request came back 7.5 s). Prompts, cue planning and SFX: `references/music-and-sfx.md`.

## When the key or the plan says no

| Response | Meaning | Fix |
|---|---|---|
| 401 `missing_permissions` | the key lacks that feature's permission (music, sound effects, image/video generation) | enable it on the key in the ElevenLabs dashboard, or use a key with all permissions |
| 402 `paid_plan_required` | the feature needs a higher plan (Flows image/video needs Pro) | upgrade, or call the provider directly (see [generating-video-clips](../generating-video-clips)) |
| 401 `quota_exceeded` | the month's credits are used up | wait for the reset or buy credits; the scripts wrote nothing partial |
| 404 `voice_not_found` | the voice isn't on this key's account | use a voice that account owns |

## Cost

Characters (tags included) are billed: `eleven_v4` is $0.08 per 1K at API list price (the launch discount ended 2026-10-12), the same as v3, so there's no cost reason to stay on v3. A request under one credit is billed as one. Rough sizes: a two-minute briefing ≈ 1,700 chars, a 15-slide deck at ~800 chars/slide ≈ 12K, a 90-minute read-through ≈ 75K — the last is worth confirming before you generate it. Real cost is regenerations: get scripts approved by the human *before* generating, sample before batching.

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
| Professional clone used without v4 fine-tuning | Lower fidelity | Fine-tune it on v4, re-sample (instant clones need nothing) |
| Picking the key out of a notes file by line number | The file changes; the wrong key or none, silently | `ELEVENLABS_API_KEY` or `~/.config/elevenlabs/api_key`; else match the line's label |
| ffmpeg run from an agent's shell without `-nostdin` | It waits on stdin and the command never returns | `-nostdin` (or `< /dev/null`); the bundled scripts do it |
| Joining clips with `-f concat -c copy` | Fails or glitches when clips differ in rate or layout | `join_clips.py` re-encodes to one format |
| A briefing left in `/tmp` and reported as a path | The user can't play it and asks again | Save beside the work; send it with the host's file tool, rendered as a player |
| A five-minute briefing for "explain this to me" | "Real concise" — made again | One to two minutes by default; offer the long version |
| A briefing that only covers what changed since the last one | The listener never heard the last one | Each file self-contained |
| Paths, ticket numbers and exact figures read aloud | Noise the listener can't use | Spoken names and rounded numbers; the exact ones in the written list |
| `/v1/music` without `model_id` | the old music_v1 model | `model_id: music_v2_5` (the bundled script) |
| A music cue exactly as long as its scene | it stops before the scene ends | ask for 2-4 s more; check the real length |
| One-word clips used raw | repeated word, stray sighs, uneven gaps | `trim_to_words.py`, then `level_clips.py` |
| `loudnorm` on one-word clips | the silence sets the level; loud and quiet clips stay uneven | level the voiced part (`level_clips.py`) |
| Latin respelling copied into subtitles | viewers see "Absolut" inside a Hebrew subtitle | respell only the TTS input |
| Judging pronunciation from a transcript | Scribe "hears" the intended word | A/B by ear: `ab_concat.py`, the human picks by timestamp |

## Related skills

- **narrating-pptx** — puts these clips one-per-slide on a deck: a pptx with PowerPoint-authored autoplay, or a Google Slides deck.
- **deck-to-video** — builds the mp4 from the same clips; consumes `alignment/` for subtitles and highlights.
- **elevenlabs-stt** — the other direction: Scribe v3 transcripts, SRT subtitles and live transcription.
- **self-presenting-decks** — the deck → narration → video map and its update matrix.
