# Music cues and sound effects with ElevenLabs

Same key and the same credit pool as TTS. Verified in 2026-10 on a full episode's music cues and sound effects.

## Requests

**Music:** `POST https://api.elevenlabs.io/v1/music`
```json
{"prompt": "Upbeat cartoon title theme, instrumental: big band horns, snappy snare, walking bass, playful and bold, quick tempo, rises into a final hit. No vocals.",
 "music_length_ms": 52000,
 "model_id": "music_v2_5",
 "force_instrumental": true}
```
- **Always send `model_id: music_v2_5`.** The endpoint still defaults to `music_v1`, which sounds clearly older. v2.5 is the latest as of 2026-10.
- `force_instrumental: true` for anything under dialogue. "No vocals." in the prompt alone is not enough.
- The response body is the mp3.

**Sound effects:** `POST https://api.elevenlabs.io/v1/sound-generation`
```json
{"text": "quick swish for a scene transition", "duration_seconds": 1.0, "prompt_influence": 0.5}
```

Both go through one script, which skips files that already exist and never leaves a partial file:
```bash
python3 <this-skill-dir>/scripts/generate_music_and_sfx.py sounds.json audio/
```

## Writing a music prompt

Say, in this order: genre and use, instruments, mood, tempo, **shape**, and "No vocals.".

The shape matters most for editing:
- "rises into a final hit" (a title)
- "steady and loopable" (an underscore)
- "resolves on one long chord" (a sting)
- "stops on an open question" (before a reveal)

Examples (each ends "No vocals."):

| Cue | Prompt (abridged) | Length |
|---|---|---|
| Title theme | upbeat cartoon title theme, big band horns, snappy snare, walking bass, playful and bold, quick tempo, rises into a final hit | window + 3 s |
| Mystery underscore | light comic mystery bed, plucked cello, tiptoeing clarinet, soft shaker, curious, even medium tempo, loopable | 60 s, reused |
| Closing sting | short closing flourish, trumpets and timpani, lands on a bright final chord | 6 s |

## Planning cues against the edit

- **One cue per scene block** (title, investigation, flashback, party, ending), not one long track.
- **Request the window plus 2-4 s.** A cue shorter than its window just stops, and the silence lands on the worst moment: in one real edit, the title cue ran out one second before its last card. The length you get is not exactly the length you asked for (a 6 s request came back 7.5 s), so check every cue with `ffprobe` against its window before mixing.
- **Reuse a long underscore later** by starting it at an offset into the cue.
- **Fades:** 0.25 s in, 0.9 s out.
- **Volume:** 0.3-0.6 under dialogue, with the music ducked under the voices (see `short-lines-and-casts.md` section 5).

## Sound effect catalog

| Name | Prompt | Seconds |
|---|---|---|
| whoosh | quick swish for a scene transition | 0.6-1.0 |
| impact | heavy cinematic impact hit with a short boom | 1.0 |
| ding | bright single notification ding | 0.5 |
| shimmer | magical sparkle shimmer | 1.5 |
| choir | short heavenly choir "aah" sting | 2.0 |
| scribble | a pencil writing fast on a notepad | 1.5 |
| door | old wooden door creaking open | 1.5 |
| tick | clock ticking, a few seconds | 3.0 |
| snore | a loud cartoon snore | 2.0 |
| gasp | a small crowd gasping in surprise | 1.0 |
| cheer | a small group cheering | 2.0 |
| clink | glasses clinking in a toast | 1.0 |

`duration_seconds` accepts 0.5-30.

## When the key or the plan says no

| Response | Meaning | Fix |
|---|---|---|
| 401 `missing_permissions` | the key lacks the music or sound-effects permission | enable it on the key, or use a key with all permissions |
| 402 `paid_plan_required` | the feature needs a higher plan | upgrade |
| 401 `quota_exceeded` | the month's credits are used up | wait for the reset or buy credits |

Read the error body: it names the missing permission. Never retry a 401 or 402 in a loop.
