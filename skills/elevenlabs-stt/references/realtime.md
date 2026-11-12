# Realtime (Scribe v3 Live) WebSocket reference

From the official API reference, read on 2026-11-13, plus a smoke test that day on Hebrew audio using `scripts/stream_live.py`.

## Endpoint and auth

`wss://api.elevenlabs.io/v1/speech-to-text/realtime`. Regional hosts:
- `wss://api.us.elevenlabs.io`
- `wss://api.eu.residency.elevenlabs.io`
- `wss://api.in.residency.elevenlabs.io`
- `wss://api.sg.residency.elevenlabs.io`

To authenticate, a server sends the `xi-api-key` header. A browser instead passes a single-use `token` query parameter, minted server-side (`realtime_scribe` token type), which expires after 15 minutes.

## Query parameters

| Parameter | Default | Values / notes |
|---|---|---|
| `model_id` | `scribe_v2_realtime` | `scribe_v3_live`. **Always send it** |
| `audio_format` | `pcm_16000` | `pcm_8000`, `pcm_16000`, `pcm_22050`, `pcm_24000`, `pcm_44100`, `pcm_48000`, `ulaw_8000` (telephony) |
| `language_code` | auto | ISO 639-1/3 |
| `secondary_languages` | - | list (the batch name is `secondary_language_codes`) |
| `multilang_mode` | false | code-switching mid-sentence (v3 Live) |
| `commit_strategy` | `manual` | `manual`, `vad`, `turn_prediction` (v3 Live) |
| `vad_silence_threshold_secs` | 1.5 (server config) | silence before a VAD commit; raise it so pauses mid phone number don't commit |
| `vad_threshold`, `min_speech_duration_ms`, `min_silence_duration_ms` | 0.4, 100, 100 (server config) | VAD tuning |
| `include_timestamps` | false | adds `committed_transcript_with_timestamps` |
| `include_language_detection` | false | language on committed messages |
| `diarize` | false | first realtime diarization (v3 Live); sends `diarized_transcript` and `speakers_merged` |
| `keyterms` | - | up to 50 terms, 20 chars each; repeat the parameter per term |
| `no_verbatim` | false | drops fillers |
| `entity_detection`, `entity_redaction`, `entity_redaction_mode` | - | as in batch; default mode `enumerated_entity_type` |
| `transcript_edit` | - | live edits, returned as `edited_transcript` |
| `filter_background_audio` | false | |
| `keepalive_interval_ms` | - | 500-10000 |
| `enable_logging` | true | `false` = zero retention (Enterprise) |

The keyterm library (up to 10,000 terms, consulted only when a likely match is heard, +$0.08/h) is v3 Live only. It is created in the ElevenLabs workspace; check the current docs for how a session references it.

## Messages

**Client → server:** `{"message_type": "input_audio_chunk", "audio_base_64": "<pcm>", "commit": false, "sample_rate": 16000}`
- `previous_text` (context) is allowed on the first chunk only; sending it later is an error.
- Send `commit: true` to force a commit, and always send one at the end of the audio.

**Server → client**

| Message | Fields / meaning |
|---|---|
| `session_started` | `session_id`, `config`: the settings the server actually applied. Log it |
| `partial_transcript` | `text`: interim, replace on each update |
| `committed_transcript` | `text`: final for that segment |
| `committed_transcript_with_timestamps` | `text`, `language_code`, `words[]` (`text`, `start`, `end`, `type`, `speaker_id`, `logprob`, `characters`) |
| `diarized_transcript` | `segment_index`, `text`, `words[]` with `speaker_id`. Arrives after its committed transcript |
| `speakers_merged` | `from_speaker_id`, `to_speaker_id`. IDs are never reused; apply merges in the order received |
| `committed_transcript_entities` | `entities[]` |
| `redacted_transcript`, `edited_transcript` | `redacted_text` / `edited_text` |
| `warning` | `warning` |

**Error types:** `error`, `auth_error`, `quota_exceeded`, `commit_throttled`, `unaccepted_terms`, `rate_limited`, `queue_overflow`, `resource_exhausted`, `session_time_limit_exceeded`, `input_error`, `invalid_request`, `chunk_size_exceeded`, `insufficient_audio_activity`, `transcriber_error`.

## SDK gaps (2026-11-13)

The official SDKs (`@elevenlabs/elevenlabs-js`, `@elevenlabs/react`, `elevenlabs` Python) connect with `modelId: "scribe_v3_live"` but don't yet support turn prediction, multilingual mode or the keyterm library. Use a raw WebSocket client for those.

## What the smoke test showed

40 s of a Hebrew meeting and 25 s of a Hebrew talk, streamed at real-time pace from `stream_live.py`:
- `turn_prediction` and `vad` both worked with `diarize=true` and `include_timestamps=true`. Each commit was followed by a `diarized_transcript` with speaker IDs.
- In continuous speech with no pause of 1.5 s or more, the first commit came only after about 36 s, and both strategies behaved the same. For captions, display the partials; don't wait for commits.
- No speech was lost: the final partial before each commit matched the committed text.
- Live, like batch v3, wrote some English terms in Hebrew letters (`סאב אייג'נט`) and wrote numbers as digits (`5,000`). It misheard "merge queue" as "Merc Q", with no keyterm for it.
- Billing is per second of audio streamed: $0.22/h list.

## Telephony notes

- Use `audio_format=ulaw_8000` for Twilio-style 8 kHz μ-law audio, rather than resampling it yourself.
- For callers who pause mid number, use `commit_strategy=turn_prediction` and raise `vad_silence_threshold_secs`.
- Diarization quality on 8 kHz audio is not documented: test with your own call recordings.
