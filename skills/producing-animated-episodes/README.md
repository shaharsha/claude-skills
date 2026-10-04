# producing-animated-episodes

A voiced, subtitled, animated, lip-synced vertical episode, made from photos or character descriptions and a script, in any style and in Hebrew (right-to-left) or English. One `episode.json` holds the project, and one engine runs every phase from it.

## Why this exists

An episode like this breaks in the same places every time:
- cards too fast to read
- music that stops a second early
- an ending that gets cut off
- a line buried under the music
- a character pointing before their line
- the wrong mouth moving
- Hebrew text that comes out reversed

One-off scripts rediscover each of these. This skill holds the workflow, the approval points and an engine where those are already handled. The engine was proven by rebuilding a real 3.5-minute episode from its config: identical frames, identical audio, and the exact length the original had missed.

## What it does

- **Workflow** (`SKILL.md`, `references/pipeline.md`): 11 phases from script to delivery, each with the human approval it needs, its commands, and measured costs and times.
- **Engine** (`engine/episode.py`), driven by `episode.json`:
  - generation: character faces and cards, panels, dialogue (crowd lines, tempo, trimming, leveling), music and sound effects, image-to-video clips, lip-sync
  - the edit, with every shot timed from the real dialogue audio, frame-exact
  - camera moves, effects, overlay styles and speaker subtitles (with right-to-left shaping)
  - device-screen composites, and a group shot with equal face sizes
  - a ducked, compressed mix that is exactly as long as the video
  - a review sheet per shot, and a chat-app delivery encode
- **References**: script writing, the config schema, a QA checklist, troubleshooting.
- **Templates**: a script, a character bible, and a complete small example episode.

## Install

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install video-production@shaharsha-skills
```
Or link it: `ln -s "$PWD/claude-skills/skills/producing-animated-episodes" ~/.claude/skills/producing-animated-episodes`.

It drives three sibling skills, which must sit next to it: [image-generation](../image-generation), [elevenlabs-tts](../elevenlabs-tts) and [generating-video-clips](../generating-video-clips).

## Requirements

- Python 3 with `pip install -r requirements.txt`: Pillow built with RAQM (for Hebrew and Arabic) and numpy. OpenCV is optional, for equal face sizes in the group shot.
- ffmpeg 7 or newer.
- Keys in env vars: `OPENAI_IMAGE_API_KEY`, `ELEVENLABS_API_KEY`, `GEMINI_API_KEY`, `FAL_KEY`.

## Quick start

```bash
python3 engine/episode.py /tmp demo                  # a fictional 11-second episode with stand-in art, no API calls
python3 engine/episode.py /tmp/demo-episode check
python3 engine/episode.py /tmp/demo-episode build
python3 engine/episode.py /tmp/demo-episode sheet    # build/review/shots_0.jpg
```
For a real episode, copy `templates/episode.example.json` into a new folder as `episode.json`, then follow `references/pipeline.md`.

## Gotchas

- **The dialogue is the clock.** Shots last as long as their lines plus pads, so a one-word card needs a `mindur` to stay readable.
- **A music cue must be longer than its window.** The build warns when it isn't.
- **Pronunciation fixes go in `pronounce`, never in the line,** or the respelling shows up in the subtitles.
- **Batch your fixes.** A full build takes minutes; collect a review round's notes and rebuild once.
- **You can't hear or watch the result.** The human judges voices, timing and likeness; the skill makes you ask, with timestamps.

## Related skills

- [image-generation](../image-generation), [elevenlabs-tts](../elevenlabs-tts), [generating-video-clips](../generating-video-clips): the providers the engine drives.
- [deck-to-video](../deck-to-video): the same ffmpeg lessons, for narrated slide decks.

## License

MIT
