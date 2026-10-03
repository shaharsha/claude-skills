# Scenes with several recurring characters

Story panels (comic frames, storyboard shots, frames to animate) where two or more characters from approved character cards appear together. Measured on GPT Image 2.5 in 2026-10 over a full episode of panels, some with many named characters.

## Model choice

| References in the panel | Draft with | Why |
|---|---|---|
| 0-1 character cards | Flare `medium` (`--draft`) | cheap and fine |
| 2 or more cards | **Sunburst `high`** (`--quality high`) | Flare drew only Image 1, put the scene outdoors, and added subtitles |

Promote approved drafts with a Sunburst `max` edit (`--ref <draft>`), as for any asset. A fresh generation at `max` composes a different picture.

## Prompt skeleton

```text
Image 1: Dana's character card (use it for her identity only).
Image 2: Omer's character card (use it for his identity only).
Image 3: Lior's character card (use it for their identity only).
Image 4: Noa's character card (use it for her identity only).
GOAL: a new anime illustration of these 4 named people, each recognizable from their card (face, hair, build and clothes), placed in the scene below. Leave the cards' flat backdrops, framing and poses behind. Only the props the scene mentions.
SCENE: THE LIVING ROOM: <the room's location block, pasted verbatim>. ACTION: Dana (the person from Image 1) hands Omer (the person from Image 2) a phone, while Lior (the person from Image 3) and Noa (the person from Image 4) watch from the green sofa.
STYLE: <the cast's panel style paragraph>
NO TEXT: no letters or numbers anywhere[ except <the quoted text, once>]; no subtitles or captions in any language (English and Japanese included), no titles, speech bubbles, logos or watermark. Each named person matches their card, appears once, and no one else is in the frame unless the scene says so.
A vertical 9:16 frame. If the scene is inside, keep it inside.
```
Pass the cards as `--ref` in the same order as the `Image k` lines.

**Bind every name to its card on first mention.** "Dana" means nothing to the model. "Dana (the person from Image 1)" ties the name to a face. Do it in code so you never miss one:
```python
import re
for k, name in enumerate(names, 1):
    scene = re.sub(rf"\b{re.escape(name)}\b", f"{name} (the person from Image {k})", scene, count=1)
```

## Consistency between panels

- **A location bible.** Write each recurring room once (walls, floor, windows, the key furniture, the light) and copy it word for word into each panel set there.
- **Props, the same way.** Define each recurring prop once ("a red steel thermos with one white star on the side and no readable text") and reuse that exact sentence.
- **Allowed text, quoted once.** When a panel needs a word in it (a sign, a label), put it in the constraints as `except the word "SALE" printed once`. Repeat it in the promote prompt ("leave the word "SALE" untouched and add no other text"), or the promote erases it.

## Wording that invites trouble

| Wording | What it brought | Instead |
|---|---|---|
| "a frame from a TV anime episode" | subtitles and title cards | "an anime illustration" |
| "set in <city>" | outdoor streets in an indoor scene | describe the room; add "If the scene is inside, keep it inside" |
| a semicolon inside a hand-rolled `curl -F prompt=...` | everything after the `;` silently dropped | `openai-image.sh` (it uses `--form-string`) |

## Screens: phones, tablets, laptops

Devices come out seen from behind, or with an unreadable screen, and chroma-green screen prompts fail. Make the screen content a full-frame image of its own (the video-call face, the chat, the avatar), then composite it into a device frame in the edit. An animated-episode engine can draw the device frame around it.

## Inserts beat fights

When a reaction shot keeps losing a prop (the empty box, the umbrella), stop re-rolling. Draw the reaction without it, plus a separate close-up insert of the prop, and cut between them.

## Many characters in one panel

The edits endpoint accepts up to 16 references, but every extra named character weakens each likeness. Keep the people the shot is about large and in front. Check each face on the draft before promoting, and re-draft a crowded panel rather than accepting one wrong face.

## Review loop

1. Draft every panel.
2. Send one contact sheet:
   ```bash
   ffmpeg -pattern_type glob -i 'panels/draft/*.png' -vf scale=270:-2,tile=6x4 panels_sheet.jpg
   ```
3. The human approves, or asks for changes per panel.
4. Promote only the approved panels.

## Cost

A Sunburst `high` draft at 1152x2048 is about $0.04-0.06, and the `max` promote about $0.18. With retakes, budget about $0.30 per panel.
