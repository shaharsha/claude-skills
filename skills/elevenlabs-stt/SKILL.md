---
name: elevenlabs-stt
description: Use when transcribing speech with ElevenLabs Scribe in any language (Hebrew, English, mixed) - a meeting, talk, call, podcast, voice note or video, a YouTube link, a transcript.md with timestamps and speakers, or SRT subtitles from audio. Also for speaker labels (diarization), word timestamps, keyterms for names and jargon, numbers as digits or words, filler removal, PII redaction, async webhooks for long files, and live or streaming transcription (scribe_v3_live, the realtime WebSocket, turn detection, voice agents). Use when moving from scribe_v2 or scribe_v2_realtime to Scribe v3, when English terms come out in Hebrew letters, when a request fails with "numbers_format is not supported with scribe_v2", "Requesting additional formats must have diarization", or a 500 service_unavailable, or whenever the user says Scribe, 11labs or ElevenLabs speech-to-text, STT or transcription, even without naming ElevenLabs.
---

# ElevenLabs STT (Scribe v3)

## Overview

Audio → text with ElevenLabs Scribe. **Scribe v3** (`scribe_v3`, released 2026-11-10) is the default for recorded audio and **Scribe v3 Live** (`scribe_v3_live`) for streams. ElevenLabs reports 27% fewer word errors than v2 across 102 languages, diarization up to 32 speakers, and the same price as v2. Upgrading is a `model_id` change; every v2 parameter still works.

You cannot hear the audio. So check what a machine can check: the language detected, the speaker count, stretches with no words (dropped speech), and, for Hebrew or Arabic speech, how many English terms came back in Latin script. Then tell the human what to spot-check by ear, and never say a transcript is correct because it reads well.

**Requirements:** an API key with Speech to Text permission, Python 3 (`transcribe.py` is stdlib-only), ffmpeg for video input or cut ranges, and `uv` for the live test bench.

**The key.** The scripts read `ELEVENLABS_API_KEY`, else the first line of `~/.config/elevenlabs/api_key` (chmod 600). If the user keeps keys in a notes file, load it inside the command substitution, matched by the line's label, never by line number. Never print the key.

## Choose the model

| Model | Use for |
|---|---|
| `scribe_v3` | **Default** for any recorded audio or video: `POST /v1/speech-to-text` |
| `scribe_v3_live` | Live audio (voice agents, captions, dictation): the realtime WebSocket, see *Live transcription* |
| `scribe_v2` | A/B against v3 on your own audio before moving a pipeline that depends on how its output looks, or to keep one consistent mid-project. Still available |
| `scribe_v2_medical` | Clinical audio, batch only |
| `scribe_v2_realtime` | Old realtime model; the WebSocket's default if you omit `model_id` |
| `scribe_v1` | Deprecated |

`model_id` is required on the batch endpoint. On the WebSocket it defaults to `scribe_v2_realtime`, so always send it.

## Transcribe a file or a link

```bash
python3 <this-skill-dir>/scripts/transcribe.py talk.mp4 --out transcripts/ --language he \
  --keyterms "Claude Code,EnterpriseRAG-Bench,pass@k,sandbox,agent" --title "Talk title"
python3 <this-skill-dir>/scripts/transcribe.py --url https://youtu.be/VIDEO_ID --out transcripts/ --name talk
python3 <this-skill-dir>/scripts/transcribe.py meeting.m4a --out t/ --speakers 7          # bound the speaker count
python3 <this-skill-dir>/scripts/transcribe.py meeting.m4a --out t/ --start 41:10 --end 43:00   # re-check one passage
python3 <this-skill-dir>/scripts/transcribe.py --from-json t/meeting.scribe.json --out t/       # re-render, no API call
```

It writes `<name>.scribe.json` (the raw response: keep it, because re-rendering is free and re-transcribing is not) and `<name>.transcript.md`, one `[mm:ss] speaker_N: text` paragraph per speaker turn or pause. Then it prints the length, the language, the speaker count, the Latin-script word count, any 45 s or longer stretch with no words, and the cost at list price. `--help` lists every option. Video is cut to a mono 16 kHz mp3 first, so a 1 GB mp4 uploads as a few MB.

- **`--url` takes hosted media and YouTube or TikTok links** (`source_url`), so nothing is downloaded. A 21.5-minute YouTube talk came back in 120 s (2026-11-13).
- **Speed:** v3 returned 3 minutes of audio in 26-34 s and 5 minutes in 36 s, about 40% faster than v2 on the same clips.
- **Speaker labels are voice clusters, not names.** Map `speaker_0` to a person from context or a participant list, and say which mappings are guesses. Similar voices merge: `--speakers N` sets an upper bound when you know the headcount.
- **Gap warnings** mean either silence or speech the model dropped. If people talk there, transcribe that range with `--start/--end` and splice it in, noting that in the transcript's header.

To call the API directly: it is multipart form data. A list parameter (`keyterms`, `secondary_language_codes`) is sent as the same field repeated, once per value. `additional_formats` and `entity_detection` take a JSON string.

## Parameters that change the result

| Parameter | What it does | Notes |
|---|---|---|
| `diarize`, `num_speakers` | speaker labels, up to 32 | `num_speakers` is an upper bound; `diarization_threshold` tunes it when no count is given |
| `keyterms` | bias toward names, products, jargon | up to 1,000 terms, ≤50 chars and ≤5 words each; +$0.05/h; over 100 terms bills at least 20 s |
| `language_code` | main language (ISO 639-1/3) | auto-detected when omitted; set it for short or one-language clips |
| `secondary_language_codes` | other languages in the audio | **v3 only, and send `language_code` with it**: alone it returned HTTP 500 twice |
| `numbers_format` | `digits` (42) or `words` (forty-two) | **v3 only** (v2 returns 400); unset = the model chooses |
| `no_verbatim` | drops fillers, false starts, sounds | good for subtitles and summaries; it also changes how Hebrew transcripts write English terms (below) |
| `tag_audio_events` | `(laughter)`, `(applause)` in the text | the script sends `false` unless `--events` |
| `transcript_edit` | a plain-English rewrite rule, result in `edited_transcript` | +$0.07/h, experimental; not with entity detection or multichannel. Unreliable for changing scripts or spellings (below) |
| `entity_detection`, `entity_redaction` | find or mask PII, PHI or PCI (65 entity types) | `entity_redaction_mode` sets the placeholder |
| `detect_speaker_roles` | labels speakers `agent` / `customer` | needs `diarize`; +10% |
| `use_multi_channel` | one speaker per channel, up to 5 channels | each channel is billed at the full length |
| `webhook` | returns at once; the result goes to the workspace's STT webhook | for long files and pipelines; `webhook_metadata` echoes your job id |

Full parameter list, response shape, limits and errors: `references/api.md`.

## Hebrew and other mixed-language speech

Measured on 2026-11-13 on a 3-minute public Hebrew tech talk and a 5-minute, 7-person Hebrew engineering meeting. Full numbers are in `references/hebrew.md`.

- **v3 can write English terms in Hebrew letters.** On the talk, v2 kept 37 English terms in Latin script (`ה-agent`, `state machine`) and plain v3 kept 2-6: it wrote `האייג'נט`, `סטייט מאשין`, `סנדבוקס`. On the meeting, v3 kept most terms in Latin but still wrote `פרוקסי`, `פייתון`, and Title-Cased the rest (`ה-Agent`, `Web Search`). `language_code=he` with `secondary_language_codes=en` did not change it.
- **Keyterms fix recognition, and sometimes the script too.** Keyterms for the terms actually said fixed misheard names and jargon (`merge queue`, `SSM`). On the talk they also brought Latin script back for 26-33 words. On the meeting they didn't: `Python` and `proxy`, even when listed, stayed `פייתון` and `פרוקסי`. Terms that aren't said do nothing, so build the list from the agenda, slides, participants and tool names.
- **`no_verbatim` restored Latin script on both clips**: 34 words on the talk, and on the meeting `Python`/`proxy` matched v2. It also drops fillers and false starts, so use it (`--clean`) when a clean, searchable transcript matters more than a verbatim record. For a verbatim record, use keyterms and accept some Hebrew-script loanwords, or keep v2.
- **Don't use `transcript_edit` to change the script.** "Write English terms in Latin script" romanized the Hebrew itself (`O-ma kora merge-shel`).
- **Read the `Latin-script words` line** the script prints. If English terms are expected but the count is near zero, re-run with keyterms, then with `--clean`.
- **The word errors that remain are names and jargon in both versions** (v3 wrote "evils" for evals, and v2 "Judge" where v3 heard "Jaja"). Keyterms fix those too. Before switching a pipeline whose readers search transcripts for English terms, A/B v2 and v3 on one real recording.
- Scribe does not translate: speech comes back in the language it was spoken in.

## Subtitles (SRT)

```bash
python3 <this-skill-dir>/scripts/transcribe.py talk.mp4 --out subs/ --srt --keyterms "..." [--srt-chars 42 --srt-secs 6] [--clean]
```

This asks the API for SRT through `additional_formats` with `max_characters_per_line` and `max_segment_duration_s`. Measured result: at most 2 lines, 42 characters per line and 5.94 s per cue. The API refuses additional formats unless diarization and word timestamps are on; the script sends both. The API's SRT also contains sub-second fragment cues, such as a lone word for 0.18 s. The script merges each one into a neighbour when the result still fits the limits. A fragment that can't merge whole is re-split with its neighbour at a word boundary (a sentence end when possible), using the response's word timestamps. The API's original is kept as `<name>.api.srt`. On the test talk this did 4 merges and 2 re-splits, leaving no lone-word cue. Don't write your own cue splitter. `--clean` (no_verbatim) reads better on screen, at the cost of a verbatim record. Check reading speed: fast speakers can push a cue past 17-20 characters a second, and the fix is shorter wording by hand, not longer cues. To burn the subtitles into a video, see deck-to-video. Other formats: `txt`, `docx`, `pdf`, `html`, `segmented_json` (see `references/api.md`).

## Long files and pipelines

- **Limits:** 5 GB per upload (`source_url` up to 2 GB), 15 hours of audio, at least 100 ms.
- **Synchronous** requests hold the connection until done: give them a long timeout (the script uses an hour).
- **`webhook=true`** returns at once with a `request_id`, and the result is POSTed to the STT webhook set in the workspace settings, not in the request. Use it when a job queue or a serverless function must not wait.
- **Speed:** a file longer than 8 minutes is split and transcribed in parallel, so long files come back fast. A 42-minute TV episode took about 27 s (22 episodes, v2 and v3 alike).
- **Concurrency** per plan: Creator 20, Pro 40, Scale and Business 60. A long file uses `min(4, ceil(seconds / 480))` of those slots, so on Creator only about 5 long files run at once. Firing 21 episodes at once got 15 HTTP 429s; 4 at a time (`xargs -P 4`) worked. A 500 `service_unavailable` said "You have not been charged" when seen, and the script retries both with backoff.
- **Word timestamps** matched a local Whisper check to within 0.2-0.5 s in normal dialogue. Three cases break them:
  - **Music:** songs and music under dialogue bunch the timestamps, with many words sharing one start and end, and lyrics come back as speech. Guard any sync or alignment logic against runs of identical times.
  - **Short lines:** shouts, crowd noise and mumbled one-word lines ("Okay", "Hey") can be missing.
  - **Names** come back as spoken ("Zoey heart" for Zoe Hart). Pass the cast list as keyterms, or match against subtitles fuzzily.
- **Data residency:** US by default. EU, India and Singapore environments are Enterprise-only, use separate accounts and keys, and lack `transcript_edit`. `enable_logging=false` (zero retention) is Enterprise-only.

## Live transcription (Scribe v3 Live)

```
wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v3_live&audio_format=pcm_16000
    &commit_strategy=turn_prediction&diarize=true&include_timestamps=true[&language_code=he][&multilang_mode=true]
```

- **Auth:** an `xi-api-key` header from a server, or a 15-minute single-use `token` for a browser (minted server-side; never ship the key to a client).
- **Send** `{"message_type":"input_audio_chunk","audio_base_64":…,"commit":false,"sample_rate":16000}` chunks. `previous_text` is allowed only on the first chunk.
- **Commit strategies:** `manual` (the default: nothing is committed until you send `commit: true`), `vad` (commits after silence; 1.5 s by default), and `turn_prediction` (v3 Live only: also commits when the model predicts the speaker has finished, so a caller pausing mid phone number is not cut off).
- **Receive** `partial_transcript` for display, then `committed_transcript`, `committed_transcript_with_timestamps` and `diarized_transcript`. The diarized message arrives after its committed text. Apply each `speakers_merged` message, in order, to labels you have already shown.
- **Keyterms** live: up to 50 terms of 20 characters each, plus a keyterm library of up to 10,000 (+$0.08/h).
- **The official SDKs don't yet support turn prediction, multilingual mode or the keyterm library.** Use the raw WebSocket for those.
- **Test settings before building:** `uv run <this-skill-dir>/scripts/stream_live.py FILE --secs 60 --param language_code=he`. It streams a file in real time and prints what the server accepted and returned. Smoke-tested on 2026-11-13 with Hebrew audio: commits, diarization and timestamps all arrived.

Message types, errors and what was measured: `references/realtime.md`.

## Cost (list price, per audio hour)

| | Batch (v3, v2, v2 medical) | Live (v3 Live, v2 Realtime) |
|---|---|---|
| Base | $0.20 | $0.22 |
| Keyterms | +$0.05 | +$0.08 (and the keyterm library) |
| Transcript edit | +$0.07 | +$0.12 |

Plans include hours (Creator: 110 batch hours a month). Silence is billed. A 1-hour meeting with keyterms costs about $0.25.

## Moving a pipeline from v2 to v3

1. Change `model_id` (`scribe_v2` → `scribe_v3`, `scribe_v2_realtime` → `scribe_v3_live`). The request parameters carry over.
2. A/B one representative real recording on both models, comparing names, jargon, and (for mixed-language audio) the script English terms come out in. Add keyterms if v3 transliterates them.
3. Update anything keyed by model id: billing or metering price tables (a missing row can bill the new model at zero), dashboards, tests, and the "made with Scribe v2" line in transcript headers.
4. Through a third party (Recall.ai's `elevenlabs_async`, gateways), check that it passes `scribe_v3` through before switching. Their docs still showed only v2 on 2026-11-13.

## Common mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Omitting `model_id` on the WebSocket | silently runs `scribe_v2_realtime` | send `scribe_v3_live` |
| Habits carried over from v2 for Hebrew tech talk | English terms come back in Hebrew letters | keyterms, then `--clean`; check the Latin-script count |
| `numbers_format` or `secondary_language_codes` on v2 | HTTP 400 | v3 only |
| `secondary_language_codes` without `language_code` | HTTP 500 | send both |
| `additional_formats` without diarization | HTTP 400 "must have diarization and timestamps enabled" | `diarize=true`, `timestamps_granularity=word` (the script forces them) |
| Building SRT cues by hand from word timestamps | cues too long or split mid-word | `additional_formats` srt with `max_characters_per_line` and `max_segment_duration_s` |
| `transcript_edit` used to fix spelling or script | romanized or rewritten text | keyterms; fix names in post-processing |
| Treating `speaker_0` as a person | wrong attribution | map clusters to names from evidence; say which mappings are guesses |
| Throwing away the raw JSON | paying again to re-render | keep `<name>.scribe.json`; use `--from-json` |
| "The transcript is right" | you can't hear it | report gaps, speaker count and Latin-script count; name passages for a human to spot-check |
| Downloading a YouTube video to transcribe it | wasted time and disk | `--url` (source_url) |
| `manual` commit strategy on a live mic | nothing is committed until you commit | `vad` or `turn_prediction` |

## Related skills

- **elevenlabs-tts**: the speech side; its `check_tags_spoken.py` uses Scribe to catch audio tags that were read aloud.
- **deck-to-video**: burns an `.srt` into an mp4.
- **viewing-videos**: what is on screen when the transcript isn't enough (slides, demos, names on badges).
