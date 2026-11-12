# Batch Speech to Text API reference

`POST https://api.elevenlabs.io/v1/speech-to-text`, multipart/form-data, header `xi-api-key`. From the official API reference and models page, read on 2026-11-13. Items marked *measured* were checked against the live API that day.

## Contents
1. Request parameters
2. Additional formats (SRT and others)
3. Response
4. Limits, concurrency, regions
5. Errors seen

## 1. Request parameters

**Input:** exactly one of these.

| Field | Notes |
|---|---|
| `file` | audio or video file, ≥100 ms, <5 GB. Audio formats: AAC, AIFF, OGG, MP3, OPUS, WAV, FLAC, M4A, WebM. Video formats: MP4, AVI, MKV, MOV, WMV, FLV, WebM, MPEG, 3GPP |
| `source_url` | hosted file (S3, GCS, R2, CDN, pre-signed URLs) or a YouTube or TikTok link. *Measured:* a 21.5-min YouTube talk took 120 s |
| `cloud_storage_url` | deprecated alias of `source_url`, HTTPS, <2 GB |
| `file_format` | `pcm_s16le_16` for raw 16 kHz mono 16-bit little-endian PCM (lower latency), otherwise `other` |

**Model and language**

| Field | Notes |
|---|---|
| `model_id` | required: `scribe_v3`, `scribe_v2`, `scribe_v2_medical` (`scribe_v1` is deprecated) |
| `language_code` | ISO 639-1 or 639-3; auto-detected when omitted (the response reports `language_code` and `language_probability`) |
| `secondary_language_codes` | list, **scribe_v3 only**. *Measured:* HTTP 500 twice when sent without `language_code`, OK with it |
| `numbers_format` | `digits` or `words`, **scribe_v3 only**. *Measured:* v2 returns 400 "not supported with model 'scribe_v2'" |
| `no_verbatim` | removes fillers, false starts and non-speech sounds (v2, v2 medical, v3) |
| `tag_audio_events` | non-speech sounds as `audio_event` words, e.g. "(laughter)" |
| `timestamps_granularity` | `word` (default), `character`, or `none` |
| `temperature` | 0.0-2.0, usually 0 |
| `seed` | 0-2147483647; determinism is best-effort |

**Vocabulary and rewriting**

| Field | Notes |
|---|---|
| `keyterms` | list, ≤1,000 terms, each ≤50 chars and ≤5 words, none of `< > { } [ ] \`. 20% surcharge (list: +$0.05/h); over 100 terms sets a 20 s minimum billable duration. Send as repeated form fields |
| `transcript_edit` | instruction of ≤2,000 chars. The result is in `edited_transcript`. 30% surcharge (+$0.07/h), at least 10 s billed. Not with `entity_detection`, `entity_redaction` or `use_multi_channel`; not offered in data-residency environments. Experimental |

**Speakers and channels**

| Field | Notes |
|---|---|
| `diarize` | adds `speaker_id` to each word; up to 32 speakers on v3 |
| `num_speakers` | upper bound, max 32; when null the model's maximum is used |
| `diarization_threshold` | default ~0.22; only with `diarize=true` and no `num_speakers`; higher means fewer speakers |
| `use_speaker_library` | match speakers against the workspace speaker library (needs `diarize`) |
| `detect_speaker_roles` | `speaker_id` becomes `agent` or `customer`; needs `diarize`; not with multichannel; +10% |
| `use_multi_channel` | ≤5 channels, one speaker each; words carry `channel_index`; every channel billed at full length |
| `multichannel_output_style` | `separate` (default: `transcripts[]`, one per channel) or `combined` (one transcript sorted by time) |

**Entities**

| Field | Notes |
|---|---|
| `entity_detection` | `all`, a category (`pii`, `phi`, `pci`, `other`, `offensive_language`), a type, or a list; JSON string. Returned as `entities[]` with `text`, `entity_type`, `start_char`, `end_char` |
| `entity_redaction` | a subset of the detected entities; when set, `entities` is not returned |
| `entity_redaction_mode` | `redacted` → `{REDACTED}`, `entity_type` → `{CREDIT_CARD}`, `enumerated_entity_type` → `{CREDIT_CARD_1}` |

**Async and auth**

| Field | Notes |
|---|---|
| `webhook` | `true` returns early; the result goes to the STT webhooks configured in workspace settings |
| `webhook_id` | send to one configured webhook only |
| `webhook_metadata` | JSON object, ≤2 levels deep, ≤16 KB, echoed back |
| `token` (query) | single-use token from `POST /v1/single-use-token/batch_scribe`, for browsers; expires in 15 min |
| `enable_logging` (query) | `false` = zero retention, Enterprise only |

## 2. Additional formats

`additional_formats` is a JSON list of `{"format": ..., options}`. The response puts each in `additional_formats[]` with `requested_format`, `file_extension`, `content_type`, `is_base64_encoded` and `content`. PDF and DOCX content comes back base64-encoded.

- Formats: `srt`, `txt`, `segmented_json`, `docx`, `pdf`, `html`.
- Options seen in use: `max_characters_per_line` (srt, txt), `max_segment_duration_s`, `max_segment_chars`, `segment_on_silence_longer_than_s`, `include_speakers`, `include_timestamps`.
- *Measured:* `{"format":"srt","max_characters_per_line":42,"max_segment_duration_s":6,"include_speakers":false}` gave cues of at most 2 lines, 42 characters per line and 5.94 s.
- *Measured:* without `diarize=true` the request fails with 400 "Requesting additional formats must have diarization and timestamps enabled."

## 3. Response

```json
{"language_code": "heb", "language_probability": 0.9997, "text": "…", "transcription_id": "…",
 "audio_duration_secs": 180.0,
 "words": [{"text": "ומה", "start": 0.44, "end": 0.62, "type": "word", "speaker_id": "speaker_0", "logprob": -0.01},
           {"text": " ", "start": 0.62, "end": 0.64, "type": "spacing", "speaker_id": "speaker_0"}],
 "additional_formats": [ … ], "entities": [ … ],
 "edited_transcript": {"kind": "transcript", "text": "…", "edited_text": "…"}}
```

- `type` is one of `word`, `spacing` or `audio_event`.
- `edited_transcript` has `kind: "error"` with `error_type: "edit_failed"` when the edit fails, and is absent when no edit was asked for.
- Multichannel responses wrap chunks in `transcripts[]`.
- Webhook-mode responses carry `message`, `request_id` and `transcription_id`.
- The response headers include `x-trace-id` and `character-cost`.

## 4. Limits, concurrency, regions

- **Limits:** 5 GB per upload and 15 hours of audio (in multichannel, all channels together).
- **Concurrency** per plan, batch / realtime: Free 8/6, Starter 12/9, Creator 20/15, Pro 40/30, Scale and Business 60/45.
- **Files over 8 minutes** are split and use `min(4, ceil(duration_s / 480))` concurrency slots. *Measured:* 21 parallel 42-minute files got 15 HTTP 429s; 4 at a time worked, and each took about 27 s.
- **Regions:** US by default (*measured:* `x-region: us-central1`). Enterprise-only isolated environments in the EU, India and Singapore have separate accounts, keys and endpoints. Support and moderation processing may still happen outside the region.

## 5. Errors seen

| Response | Meaning | Fix |
|---|---|---|
| 400 `invalid_parameters` "numbers_format … not supported with model 'scribe_v2'" | v3-only parameter on v2 | use `scribe_v3` or drop it |
| 400 "Requesting additional formats must have diarization and timestamps enabled." | SRT/TXT/etc. without diarization | `diarize=true`, `timestamps_granularity=word` |
| 500 `service_unavailable` "You have not been charged" | server-side; seen with `secondary_language_codes` and no `language_code` | retry with backoff; add `language_code` |
| 401 `missing_permissions` | the key lacks Speech to Text | enable it on the key |
| 422 | validation error, with `detail[].loc` naming the field | fix the field |
| 429 | concurrency limit | back off; lower parallelism |
