# Troubleshooting

| Symptom | Cause | Fix | Confirm |
|---|---|---|---|
| Cards or captions too fast to read | shot length follows the audio, and a one-word line is short | raise the shot's `mindur` or `post` (~1.2-1.5 s per card, 4-6 s for a final caption) | watch it at speed, or read the timeline |
| A title or caption clipped at both edges | text wider than the 1080 px frame | lower the style's `size`, or add `wrap` | `check` warns "wider than the frame" |
| Music stops before the section ends | the cue is shorter than its window | regenerate the cue longer (window + 2-4 s), or split the section into two cues | the build prints "music cue ... will stop early" |
| Music cuts out after the last line | (fixed in the engine) the ducking key ended with the dialogue | update the engine; hand-built mixes must pad the key: `[dlg]asplit=2[dlg1][k0];[k0]apad[key]` | listen to the last seconds |
| The ending is cut off | a `-shortest` mux, or a mix trimmed short | the engine pads the mix to the exact timeline and checks both streams | the build's last line shows equal durations |
| A line is buried under music | a word sagged in the take, or the cue is loud | `level_clips.py raw/ --report`, then a firmer take; lower that cue's volume | listen at the timestamp |
| A one-word line has a repeat or a sigh | the model fills short lines | `trim: true` and `level: true` on the line, then `lines <id>` | listen |
| A name or loanword is mispronounced | the voice reads the spelling | a `pronounce` entry (Latin script works for most), A/B by ear | the human picks by timestamp |
| English letters inside a Hebrew subtitle | a respelling was put in `lines.text` | move it to `pronounce` | read a sheet |
| A character points or acts before their line | the clip starts mid-gesture | `clip_off` past it, or split the shot and crop the first part with `clip_cam` | sheet the first second |
| A door, prop or person appears mid-clip | image-to-video invention | regenerate with pinned prompts, 2-3 takes (generating-video-clips, failure modes) | sheet |
| Mouths don't move with the words | no lip-sync for that shot, or a part was skipped | add the shot to `lipsync.shots`, a face point, `lipsync run` | 3 frames per shot |
| A visible face talks, but the shot is not lip-synced | its mouth moves out of time with the line | hide the mouth in the panel (turned away, behind an object, a close-up elsewhere), or move the line to the clip's mouth movement with the shot's `pre` or a line `@` offset; `clip_off` moves the clip instead | 3 frames around the line |
| The wrong mouth moves | the face point is on the listener | correct `lipsync.faces`, delete that part's synced file, `lipsync run` | `take_sheet.py point` |
| One face much bigger in the group shot | face sizes not equalized | install `opencv-python-headless`; `mirror` a card whose prop covers a neighbor | read the collage frame |
| Only one character appears in a multi-character panel | drafted with Flare | the engine drafts 2+ characters with Sunburst high; force with `panels draft --hq` | read the draft |
| Captions appear inside panels | no language-named text ban | keep the default `panel_no_text` (it names English and Japanese) | read the draft |
| Everyone is muscular, or slim | build left to the model | a `body` that also says what they are not | read the cards |
| Hebrew renders reversed or unjoined | Pillow without RAQM | `check` explains; `brew install libraqm` and reinstall Pillow | `check` passes |
| `Unrecognized option 'filter_complex_script'` | an old script on ffmpeg 9 | the engine uses `-/filter_complex`; update hand-written commands | - |
| `credit_balance_exhausted` while generating panels | the OpenAI account is out of credit | top up, then rerun only the missing panels | - |
| `missing_permissions` / `paid_plan_required` from ElevenLabs | the key or the plan | see elevenlabs-tts, "When the key or the plan says no" | - |
| fal 401 | the key was shortened | pass the full key exactly as fal shows it | - |
| A segment is broken after a crash | an interrupted render | segments are written to `.part.mp4` first; delete the bad segment and rebuild | `build --only <shot>` |
| Rebuilds are slow | many shots changed | rebuild once per batch of fixes; the build re-renders only shots whose inputs changed (a style or font change touches every shot) | the build log lists the rendered shots |
