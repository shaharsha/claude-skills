# ElevenLabs API — the parts beyond one-clip TTS

Read this when the task needs multiple voices in one clip, real-time/streaming speech, Studio projects, pronunciation dictionaries, a non-mp3 output, or cost/concurrency planning. Facts as of 2026-10-02; v4 is "under active, continuous development" and ElevenLabs recommends periodic re-testing.

Sources: [models](https://elevenlabs.io/docs/overview/models) · [v4](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4) · [OpenAPI](https://api.elevenlabs.io/openapi.json) · [changelog 2026-09-28](https://elevenlabs.io/docs/changelog/2026/9/28) · [request stitching](https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/request-stitching) · [Text to Dialogue](https://elevenlabs.io/docs/overview/capabilities/text-to-dialogue) · [WebSockets](https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/tts-vs-ttd-websockets) · [forced alignment](https://elevenlabs.io/docs/overview/capabilities/forced-alignment) · [API pricing](https://elevenlabs.io/pricing/api)

## Contents
1. Full TTS request schema
2. Request stitching
3. Timestamps endpoints (and why they're not the subtitle source)
4. Text to Dialogue (multi-voice)
5. Real-time: eleven_v4_turbo
6. Studio projects
7. Pronunciation
8. Output formats
9. Concurrency and 429s
10. Pricing
11. Voices: clones, library, design
12. SDK

## 1. Full TTS request schema

`POST /v1/text-to-speech/{voice_id}` (also `/stream`, `/with-timestamps`, `/stream/with-timestamps`). Query: `output_format` (default `mp3_44100_128`), `enable_logging`.

| Field | Notes |
|---|---|
| `text` | required. ≤10,000 chars on `eleven_v4`, ≤5,000 on `eleven_v3` |
| `model_id` | **the endpoint default is still `eleven_multilingual_v2`** — always send it |
| `voice_settings.stability` | 0–1, default 0.5. Continuous on v4 (0.3 verified accepted) |
| `voice_settings.similarity_boost` | 0–1, default 0.75. Honoured on v4 (v3 ignored it) |
| `voice_settings.style`, `.speed`, `.use_speaker_boost` | accepted by the schema, **not part of v4's controls** ("Style and Speed sliders are not available") — third-party tests with a fixed seed found speed/style ignored. Don't rely on them |
| `seed` | 0–4294967295, best-effort determinism |
| `language_code` | ISO 639-1; enforces language + normalization. Unsupported codes are ignored, not rejected |
| `apply_text_normalization` | `auto` (default) / `on` / `off` |
| `previous_text`, `next_text` | continuity hints (text form) |
| `previous_request_ids`, `next_request_ids` | ≤3 each; win over the `_text` forms |
| `pronunciation_dictionary_locators` | ≤3 |
| `use_pvc_as_ivc` | un-deprecated 2026-09-28 |

No SSML on v4 — `<break>`, `<phoneme>`, `<emphasis>` are dropped or disabled.

## 2. Request stitching

Not available on v3; back on v4 and "significantly more reliable". Pass the `request-id` response header of earlier clips as `previous_request_ids` (max 3, each **≤2 hours old**; for streamed requests the audio must be fully read first). It smooths prosody at clip boundaries — most valuable when clips are concatenated back-to-back with no gap. Cost: generation becomes sequential. `generate_tts.py --stitch` does this.

## 3. Timestamps endpoints

`/with-timestamps` returns `audio_base64` + `alignment` / `normalized_alignment` with `characters`, `character_start_times_seconds`, `character_end_times_seconds`. **Verified 2026-10-02 on `eleven_v4`:** the returned `characters` are the input text *including the tag characters*, and a tag's characters carry the time of its performance (in one take, `[Pause, dry amusement]` spanned 1.60–2.22 s — the actual pause; a leading `[Warm…]` took 0.07 s). After dropping tag spans, word starts matched forced alignment on the same take within ~0.05 s, one word 0.26 s off. Usable when you're generating anyway — save the JSON, it can't be fetched later.

**Forced alignment is the master** because it works on audio that already exists (after `atempo`, regenerations, clips made without timestamps): (`POST /v1/forced-alignment`, multipart `file` + `text` → `characters[]{text,start,end}`, `words[]{text,start,end,loss}`, top-level `loss`). Feed it the tag-stripped script. Limits: 10 h audio, 675,000 chars, file size 1 GB (API ref) / 3 GB (capability page — conflicting docs). Priced as speech-to-text. The docs' language list omits Hebrew, but **Hebrew works** (verified 2026-10-02: 49/49 characters aligned on a v4 clip). `loss` is relative — compare clips within a batch; short clips with long tag-driven pauses score higher.

## 4. Text to Dialogue (multi-voice)

`POST /v1/text-to-dialogue` (+ `/stream`, `/with-timestamps`). Body: `inputs: [{text, voice_id}, …]`, `model_id` (**default `eleven_v3` — send `eleven_v4`**), `settings.stability`, `settings.similarity`, `seed`, `language_code`, `previous_text`/`future_text` (≤100 chars each — note *future*, not *next*), `previous_request_ids`/`next_request_ids`.
- ≤10 unique voices; keep total `inputs[].text` ≤ **2,000 chars per request** for reliable output (far below TTS's 10,000).
- Tags go inside the turn they affect. Dashes = interruptions, ellipses = trailing off.
- `/with-timestamps` adds `voice_segments[]` (`voice_id`, start/end seconds, character indices, `dialogue_input_index`). A third-party report found v3 dialogue timing broken and rescued it with forced alignment — verify before trusting.

## 5. Real-time: `eleven_v4_turbo`

Median ~100 ms inference, ~150 ms to first speech over WebSocket. **The TTS WebSocket (`/v1/text-to-speech/{voice_id}/stream-input`) does not accept v3 or v4.** Real-time v4 runs on the Text to Dialogue WebSocket `wss://api.elevenlabs.io/v1/text-to-dialogue/stream-input` — `eleven_v4` up to 10 voices, `eleven_v4_turbo` exactly 1; it closes after 20 s idle unless you send `keep_alive`. Turbo sounds slightly lower quality and its char limit is undocumented — use full `eleven_v4` for anything pre-rendered.

## 6. Studio projects

Studio supports v4, but **its default model is still Multilingual v2** — set `default_model_id`. Limits: 500 chapters/project, 400 paragraphs/chapter, 5,000 chars/paragraph. Changing a project's model does not regenerate existing audio. `project_voice_ref_id` replaced `voice_id` (2026-06-15); `quality_preset` may be `null` (= best for the tier).

## 7. Pronunciation

- **IPA inline (v4):** wrap the transcription in slashes inside double quotes: `The term "/ˌbaɪoʊˈkemɪstri/" refers to…`. Include stress marks, use selectively, regenerate a few times — results vary by voice.
- **Dictionaries:** PLS or TXT, alias or phoneme rules, case-sensitive, first match wins; ≤3 per request.
- `<phoneme>` SSML works only on `eleven_flash_v2` — not v4.

## 8. Output formats

28 values, e.g. `mp3_44100_128` (default), `mp3_44100_192` (Creator+), `opus_48000_*`, `pcm_*`, `pcm_44100` / `wav_44100` (Pro+), `ulaw_8000`, `alaw_8000`. Decks and video: keep `mp3_44100_128` so the pptx and the mp4 embed identical files.

## 9. Concurrency and 429s

HTTP concurrency (models page, no separate v4 column): Free 2 · Starter 3 · Creator 5 · Pro 10 · Scale 15 · Business 15 (pricing page says 25). Response headers `current-concurrent-requests` / `maximum-concurrent-requests` tell you where you are. A 429 is concurrency, not quota — back off and retry; `--concurrency 4` suits Creator.

## 10. Pricing (per 1,000 chars, API)

| Model | Price |
|---|---|
| `eleven_v4` | $0.022 **until 2026-10-12** (72% launch discount), list $0.08 |
| `eleven_v4_turbo` | $0.011 until 2026-10-12, list $0.04 |
| `eleven_v3`, Multilingual v2 | $0.08 |

Tags count as characters. At list price v4 = v3, so there is no cost reason to stay on v3.

## 11. Voices: clones, library, design

- Every Voice Library voice works on v4 (17,500+).
- **Your own** IVCs/PVCs made before 2026-09-28 should be retrained on v4 (My Voices → hover → "+" next to Eleven v4). A retrained clone "may sound quite different from its v3 version", and v4 reproduces recording flaws more faithfully.
- Voice Design has no v4 model (`eleven_multilingual_ttv_v2`, `eleven_ttv_v3`); designed voices work on v4 but "may be less performative".

## 12. SDK

Python `elevenlabs` 2.70.0 / JS `@elevenlabs/elevenlabs-js` 2.70.0: `client.text_to_speech.convert(voice_id, text=…, model_id="eleven_v4")`, `convert_with_timestamps`, `stream`, `client.text_to_dialogue.convert(...)`. The SDK's model enums don't list v4 yet — irrelevant, `model_id` is a plain string. The bundled scripts use only the standard library, so no install is needed.
