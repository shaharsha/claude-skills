# elevenlabs-stt

Speech → text with ElevenLabs **Scribe v3**, in any language (Hebrew, English, mixed). It covers transcripts of meetings, talks, calls and videos (or a YouTube link) with timestamps and speaker labels, SRT subtitles, keyterms for names and jargon, and live transcription over the Scribe v3 Live WebSocket. It also covers what changed from v2, measured rather than taken from the launch post.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Scribe v3 and v3 Live shipped on 2026-11-10. ElevenLabs reports 27% fewer word errors than v2, diarization up to 32 speakers, and the same price. Upgrading is a `model_id` change. An agent left to itself still reaches for `scribe_v2`, because that is what its training data and most docs and SDK examples show. A few things are worth knowing before you switch:

- **On Hebrew speech, v3 can write English terms in Hebrew letters.** On a Hebrew tech talk, v2 kept 37 terms in Latin script (`ה-agent`, `state machine`) and plain v3 kept 2-6 (`האייג'נט`, `סטייט מאשין`). Keyterms for the terms actually said brought most of them back there, but not on a meeting, where `Python` and `proxy` stayed in Hebrew letters even as keyterms. `no_verbatim` restored them on both. A language hint changes nothing. `transcript_edit` makes it worse: asked to fix the script, it romanized the Hebrew.
- **Some new parameters are v3-only and fail loudly on v2** (`numbers_format`, `secondary_language_codes`). `secondary_language_codes` without `language_code` returned HTTP 500.
- **The API can produce SRT itself**, but only with diarization on, and its cues include sub-second fragments that an agent then writes a script to merge. The bundled script merges them.
- **`source_url` takes a YouTube link**, so there's nothing to download. A 21.5-minute talk came back in two minutes.
- **The realtime WebSocket defaults to `scribe_v2_realtime`**, and the official SDKs can't yet use v3 Live's turn prediction, multilingual mode or keyterm library.

Everything marked *measured* was checked against the live API on 2026-11-13: two Hebrew clips (a public tech talk and a 7-person meeting), a YouTube source, SRT options, and a WebSocket session.

## What it does

```
file / YouTube link ──▶ transcribe.py (scribe_v3, keyterms, diarization) ──▶ <name>.scribe.json  (raw, re-render for free)
                                                                        ├──▶ <name>.transcript.md  [mm:ss] speaker_N: text
                                                                        └──▶ <name>.srt  (API SRT, fragments merged)
                         checks printed: language, speakers, Latin-script words, gaps with no words, cost

audio file ──▶ stream_live.py ──▶ wss://…/speech-to-text/realtime (scribe_v3_live) ──▶ committed / diarized events
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install elevenlabs-stt@shaharsha-skills
```

That installs only this skill. For the whole `documents-and-decks` bundle, run `/plugin install documents-and-decks@shaharsha-skills` instead.

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/elevenlabs-stt" ~/.claude/skills/elevenlabs-stt
```

## Requirements

- An API key with Speech to Text permission, in `ELEVENLABS_API_KEY` or `~/.config/elevenlabs/api_key` (chmod 600), never pasted into output
- Python 3; `transcribe.py` uses only the standard library
- ffmpeg, for video input and `--start/--end` ranges
- [uv](https://docs.astral.sh/uv/) for `stream_live.py` (it pulls in `websockets` itself)

## Quick start

```bash
# a Hebrew talk with English jargon: keyterms for the names and terms said (add --clean if terms still come out in Hebrew letters)
python3 scripts/transcribe.py talk.mp4 --out t/ --language he --keyterms "Claude Code,sandbox,agent,pass@k"

# a YouTube link, nothing downloaded
python3 scripts/transcribe.py --url https://youtu.be/VIDEO_ID --out t/ --name talk

# subtitles: at most 2 lines of 42 characters and 6 s per cue, fillers dropped
python3 scripts/transcribe.py talk.mp4 --out subs/ --srt --clean --keyterms "..."

# a meeting with a known headcount, then one garbled passage again
python3 scripts/transcribe.py meeting.m4a --out t/ --speakers 7
python3 scripts/transcribe.py meeting.m4a --out t/ --start 41:10 --end 43:00

# try live settings on a file before writing an integration
uv run scripts/stream_live.py call.wav --secs 60 --param language_code=he --param commit_strategy=turn_prediction
```

## The scripts

| Script | What it does |
|---|---|
| `transcribe.py` | One batch request to `POST /v1/speech-to-text`. It cuts video or a range to a small mp3 first, or sends `--url` as `source_url`. It writes the raw JSON, a paragraph-per-turn `transcript.md`, and an `.srt` with fragment cues merged or re-split at word boundaries, plus the API's original. It prints the language, speakers, Latin-script word count, stretches with no words and the list-price cost, and retries 429/5xx. `--from-json` re-renders without paying again |
| `stream_live.py` | Streams a file at real-time pace to Scribe v3 Live and prints the session config the server applied, plus every committed, diarized, entity and error message with its arrival time. A test bench for commit strategy, diarization, language and keyterm settings |

## References

- [`references/api.md`](references/api.md) - every batch parameter, additional formats, the response shape, limits, concurrency, regions and the errors seen.
- [`references/hebrew.md`](references/hebrew.md) - the Hebrew/English measurements: Latin vs Hebrew script by variant, word differences between v2 and v3, diarization, speed, and a recipe.
- [`references/realtime.md`](references/realtime.md) - the v3 Live WebSocket: query parameters, message types, errors, SDK gaps, telephony notes, and what the smoke test showed.

## Gotchas

| Mistake | Consequence | Fix |
|---|---|---|
| Keeping v2 habits for Hebrew tech talk | English terms in Hebrew letters | keyterms for the terms said, `--clean` when fillers don't matter; read the Latin-script count |
| `numbers_format` / `secondary_language_codes` on v2 | HTTP 400 | v3 only |
| `secondary_language_codes` without `language_code` | HTTP 500 | send both |
| SRT without diarization | HTTP 400 | `diarize=true` (the script forces it) |
| No `model_id` on the WebSocket | runs `scribe_v2_realtime` | `scribe_v3_live` |
| `transcript_edit` to fix the script or spelling | romanized or rewritten text | keyterms; post-process names |
| Throwing away the raw JSON | paying again to re-render | keep `.scribe.json`, use `--from-json` |
| "The transcript is right" | you can't hear | report gaps, speakers and Latin-script count; name passages for a human to check |

## Related skills

- [elevenlabs-tts](../elevenlabs-tts) - the speech side; its tag-leak check transcribes with Scribe v3.
- [deck-to-video](../deck-to-video) - burns an `.srt` into an mp4.
- [viewing-videos](../viewing-videos) - reads what is on screen when a transcript isn't enough.

## License

MIT - see [LICENSE](../../LICENSE).
