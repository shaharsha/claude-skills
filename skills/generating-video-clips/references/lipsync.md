# Lip-sync to your own dialogue

The clip moves, but the mouths don't match your TTS lines. Lip-sync fixes the mouth and nothing else. Verified in 2026-10 on the dialogue shots of a full drawn (anime) episode.

## Why video-to-video

Two kinds of model exist:
- **Avatar / talking-head models** (HeyGen Avatar 4, OmniHuman 1.5, Creatify Aurora) take a still and audio and generate a whole new video. That throws away the animation you paid for, and they are tuned for real faces.
- **Video-to-video lip-sync** (Sync 3, Sync Lipsync 2 Pro, Veed Lipsync) keeps the clip and re-times only the mouth region. This is the right kind for animated shots.

Lip-sync models offered in ElevenLabs Flows (credits per second of output, 2026-10):

| Model | Credits/s | Kind |
|---|---|---|
| Veed Lipsync 2.0 | 424 | video-to-video |
| Sync Lipsync 2 Pro | 661 | video-to-video |
| Creatify Aurora | 848 | avatar |
| Sync 3 | 1,053 | video-to-video |
| HeyGen Avatar 4 | 1,212 | avatar |
| Veed Fabric | 1,212 | avatar |
| OmniHuman 1.5 | 1,267 | avatar |

The default is **Sync 3 on fal directly** (`fal-ai/sync-lipsync/v3`, about $0.133 per output second): no Flows plan gate, and the human called its result on a drawn face "perfect".

## Speaker selection

In a shot with two or more faces, tell the model whose mouth to move:
```json
"options": {"active_speaker_detection": {"auto_detect": false, "frame_number": 30, "coordinates": [410, 560]}}
```
`coordinates` is a pixel on the speaker's face, in the part video's own resolution (720x1280 for Omni clips), on frame `frame_number` of that part. Without it, Sync guesses, and in a two-shot it often animates the listener.

**Pick the point by eye, not with a face detector.** Haar and similar detectors are unreliable on drawn faces (they miss them, or find faces in hair).
1. Read the part's middle frame (the `mid` in the plan) as an image.
2. Pick a pixel on the speaker's face.
3. Confirm it: `take_sheet.py point part.mp4 check.jpg --frame 30 --xy 410,560`, then read `check.jpg`. The red box must sit on the right face.

## Splitting rules (`lipsync_parts.py split`)

- **One speaker per part.** A shot with lines from two people becomes two parts.
- **The cut** is the middle of the gap between two lines, or the next line's start when the lines overlap. Every frame belongs to exactly one part.
- **Skip** (keep the original frames) when the speaker is seen from behind, off screen, faceless (a silhouette), or it's a crowd shouting together.
- Each part's audio is the line placed at its real offset inside the part and padded with silence to the part's length. `sync_mode: cut_off` stops the output at the video's end.

## Joining (`lipsync_parts.py join`)

Each part is forced to its exact frame count (`fps`, `scale`, `tpad` holding the last frame for as long as needed, then `-frames:v N`), then everything is concatenated and re-encoded once at CRF 15. A part that came back short holds its last frame, so the shot stays frame-exact against the edit; the joined file's frame count is checked against the plan.

join looks for `synced/<id>_<k>.mp4`. A non-skip part without that file keeps its unsynced frames and is reported as a WARNING. Use `--strict` to make that an error, so a failed or misnamed sync never ships silently. The jobs file `split` writes already uses those names.

## Failures

| Symptom | Fix |
|---|---|
| The wrong face talks | rerun that part alone with the corrected point and `--force`: `lipsync_fal.py parts/S05_1.mp4 parts/S05_1.wav synced/S05_1.mp4 --face X,Y@MID --force` (existing outputs are otherwise skipped; `--force` with `--jobs` redoes every part) |
| The mouth moves before the line | the part starts too early: check `f0` in the plan against the line's start |
| A part comes back shorter | nothing to do; join holds the last frame |
| HTTP 401 from fal | the key was shortened; pass it exactly as fal shows it |
| Upload fails with a 4xx | fal changed its upload path (the older one started failing in 2026-10); compare with `storage/auth/token` and `files/upload` in the current `fal_client` source |
| `failed: ... no face` | the point is off the face, or the face is too small: crop or zoom the shot first |

## Cost and time

Total part seconds x $0.133: a 4 s part costs about $0.55, and a few minutes of dialogue shots about $25. Each part takes 70-150 s; `lipsync_fal.py --jobs` runs 6 in parallel.
