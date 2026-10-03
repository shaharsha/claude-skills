# Gemini Omni Flash 1.1: image to clip

`gemini-omni-1.1-flash` through Google's **Interactions API**, with a Google AI Studio key. Verified in 2026-10 across a full animated episode. Inside ElevenLabs Flows the same model is app-only; through Google it is a plain synchronous HTTP call.

## Request

```
POST https://generativelanguage.googleapis.com/v1beta/interactions
x-goog-api-key: $GEMINI_API_KEY
Content-Type: application/json
```
```json
{"model": "gemini-omni-1.1-flash",
 "input": [{"type": "image", "data": "<base64 JPEG, fitted inside 1080x1920>", "mime_type": "image/jpeg"},
           {"type": "text", "text": "<base prompt> + <timeline>"}],
 "response_format": {"type": "video", "aspect_ratio": "9:16", "resolution": "720p"},
 "store": false, "background": false, "stream": false}
```
- The call is synchronous: about 25-35 s, so allow a long timeout (the script uses 900 s).
- The video is at `steps[]` with `type == "model_output"`, then `content[].data`, as a base64 mp4.
- The output is 720x1280 (9:16) at 24 fps, **with an audio track the model invented**. Mute it: your dialogue comes from TTS.
- Retry 429, 500 and 503 with a pause. Never retry a 400 (bad key or bad body) or a 403.

`scripts/omni_generate.py` does all of this, with takes and skip-existing.

## Prompt anatomy

**Base**, prefixed to every shot:
```text
Bring this still to life as it is: same art style, palette, light and layout, and every character keeps the face, hair, build and clothes they have in it. Natural, fluid movement. Nothing written on screen, no speech bubbles, nobody new, one continuous shot.
```
**Timeline**, one bracket per beat. The clip runs about as long as the timeline, 4-9 s.

Example 1: a two-person dialogue panel (both will be lip-synced):
```text
[0-3s] The woman in the red jacket on the left leans forward and talks, excited, gesturing with one hand. The friend in the green hoodie on the right listens and nods. [3-6s] The friend in the green hoodie talks back, shrugging; the woman in the red jacket crosses her arms. Subtle camera push-in.
```
- Characters are named by **what they wear and where they are**. The model doesn't know who "Maya" is.
- Each speaker **"talks"** in their own bracket, so their mouth is already moving where the lip-sync will go.
- The listener gets a small reaction, not stillness.

Example 2: a stormy-night scene with every pin it needed (a fictional version of a real shot):
```text
Static camera; the set never changes and has a single window, in the left wall, and no other window or door. Only ONE hooded figure exists, always outside that window: an unlit dark form with no visible face or eyes and no light on it, carrying one lantern. [0-4s] A lighthouse keeper in a yellow raincoat dozes at the desk, takes a sip from a mug and peers at the window. [4-6s] The hooded figure stops and glances at her. [6-9s] The hooded figure backs away into the rain and is gone; the keeper looks straight at the camera, defeated. Nobody else appears, no extra window, no glowing eyes.
```
Each sentence before the timeline answers a failure of an earlier take (see `failure-modes.md`). Pins go **before** the timeline, so they frame everything after them.

## Takes

- One take is fine for simple motion.
- After any failure, use `--takes 3`: same prompt, three clips, `S09_t1.mp4` to `S09_t3.mp4`.
- Compare them on one sheet (`take_sheet.py sheet`), pick, copy the winner to `S09.mp4`, and keep the rest in `_old/`.
- The script never overwrites, so a rerun after a partial failure only pays for what is missing.

## Limits seen

- Faces and outfits hold well up to about 8 s. Past that, drift starts.
- **Drift also starts with framing.** When a clip ends on a closer view of a face than the still had, the model invents detail at the larger size and the face turns rounder and more generic (seen at ~5 s on a photoreal still). Pin the distance: "the camera keeps the same distance; the face never gets larger than in the first frame", or end at the source scale.
- **Small facial actions can be skipped**, especially in the last beat: "[4-6s] ... a quick wink" never appeared (one test). Give a small action its own beat, not the final one, and look for it on the sheet.
- **Input aspect doesn't have to match.** A 2:3 still sent with `--aspect 9:16` came back as a clean 720x1280 clip, and it looked better than a version pre-outpainted to 9:16 (one test each).
- **Moderation differs by provider.** A costume still that OpenAI's output filter refused to produce as a variant was accepted by Google for animation (one case). If GPT Image refuses a variant, the GPT still you already have can still be animated.
- Wide shots with many people get more hand and body errors than two-shots. Keep crowd motion small ("the people around them nod").
- Text inside the still (signs, phone screens) gets garbled when it moves. Keep text out of the panel and overlay it in the edit.
- Gestures at the start of a clip often happen once, stop, and happen again. Plan to start the clip after the first one (see `failure-modes.md`).

## Cost

Budget roughly $0.40 a call (an estimate from one episode's billing total); check Google's current pricing page before a large batch.
