# Video providers: access paths and gates

What it took to reach each model in 2026-10. "Verified" means a real clip came back through that path.

| Model | ID / endpoint | Access path | Auth | Gate encountered | Verified | Notes |
|---|---|---|---|---|---|---|
| Gemini Omni Flash 1.1 | `gemini-omni-1.1-flash`, `POST /v1beta/interactions` | Google AI Studio | `x-goog-api-key` (an image-scoped key works) | none | **yes, 2026-10** (anime and photoreal stills) | 720p 9:16 or 16:9, any input aspect, ~25-35 s, synchronous; invents an audio track; accepted a still OpenAI's filter refused to vary |
| Gemini Omni (inside Flows) | - | ElevenLabs Flows | - | app-only, no API | no | use Google directly |
| Veo 3.1 / Veo 3.1 Fast | Gemini API, image as start frame | Google AI Studio | `x-goog-api-key` | - | no | photoreal stills; check current docs before use |
| Seedance 2.5 | via ElevenLabs Flows, or ByteDance | ElevenLabs API | `xi-api-key` | Flows gates (below), account approval | no | |
| Any video model in ElevenLabs Flows | Flows API | ElevenLabs API | `xi-api-key` with the `image_video_generation` permission | 401 `missing_permissions` without the permission; 402 `paid_plan_required` below Pro | no | one key for everything, if the plan allows |
| Sync 3 lip-sync | `fal-ai/sync-lipsync/v3` | fal queue API | `Authorization: Key <full key>` | none | **yes, 2026-10** | ~$0.133/s, 70-150 s per part |
| Kling lip-sync | `fal-ai/kling-video/lipsync/audio-to-video` | fal | same | - | no | alternative, not compared |
| PixVerse lip-sync | `fal-ai/pixverse/lipsync` | fal | same | - | no | alternative, not compared |

## fal REST, without the SDK

`scripts/lipsync_fal.py` uses these (current as of 2026-10):
1. **Upload token:** `POST https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3` (`Authorization: Key <key>`, body `{}`), which returns `{token, token_type, base_url}`.
2. **Upload:** `POST https://v3.fal.media/files/upload` with the raw bytes and `Authorization: <token_type> <token>`, which returns `{access_url}`.
3. **Submit:** `POST https://queue.fal.run/fal-ai/sync-lipsync/v3`, which returns `{request_id, status_url, response_url}`.
4. **Poll** `status_url` until `COMPLETED`. A failed job is also `COMPLETED`, with an `error` field.
5. **Fetch** `response_url`, which returns `{video: {url}}`. Download it promptly: media URLs expire.

The older `storage/upload/initiate?storage_type=gcs` path now answers `400 Invalid storage type`.

## Check access before a batch

Make one cheap call per provider and read the error body:
- **401 / 403:** the key, or its permissions. Fix it in the dashboard.
- **402:** the plan.
- **429:** rate limit. Lower the concurrency.

Never retry a 401 or 402 in a loop: it will not start working, and some providers count failed calls.
