# Characters from photos of real people

For a comic, storyboard or animated episode where real people (friends, family, a team) become recurring cartoon or anime characters that they recognize instantly. Measured on GPT Image 2.5 in 2026-10 with a large cast.

**The one rule:** never pass whole photos as `--ref`. The edit endpoint treats a reference photo as the image to restyle, so you get the photo back in anime colors: the same pose, clothes and background, sometimes with invented caption text. Likeness comes from the **face only**; everything else comes from the prompt.

## The pipeline

| Step | Input | Model | Output | Human gate |
|---|---|---|---|---|
| 1. Crops | 1-3 photos per person | `scripts/crop_faces.py` (OpenCV) | `faces/<photo>-<n>.png` + numbered sheet | which crop is whom |
| 2. Face | 1-2 crops | Flare `--draft --n 2` | two anime faces | pick one, or ask for an adjustment |
| 3. Card | the chosen face | Flare `--draft` edit | half-body costume card on a flat color | - |
| 4. Likeness review | all cards on one sheet | - | retake list | yes: likeness, body, outfit |
| 5. Promote | approved card | Sunburst `max` edit | final card | - |

### 1. Crop the faces

```bash
pip install opencv-python-headless        # once
python3 <this-skill-dir>/scripts/crop_faces.py photos/ faces/ --sheet faces/_sheet.jpg
```
Each detected face becomes a square crop with 60% margin (forehead, hair and beard included), largest face first. Read the sheet, then ask the human which crop is which person. Keep 1-2 sharp, frontal crops per person: a typical expression beats a perfect photo. Group photos are fine as a source; the crop isolates the face.

### 2. Anime face (Flare draft, two options)

```bash
bash <this-skill-dir>/scripts/openai-image.sh --size 1024x1536 --n 2 --draft \
  --ref faces/dana-1.png --ref faces/dana-2.png --output characters/dana-face.png --prompt "$PROMPT"
```
```text
GOAL: a head-and-shoulders anime portrait of one specific real person, for an animated story.
REFERENCES: both images are close-ups of the same person's face. Draw that one person as an anime character whom people who know them would recognize at once.
FACE: round face, short black bob haircut, big dark eyes, small silver nose ring, wide easy smile. Keep their actual face shape, hairline, facial hair and weight; don't make them thinner, prettier or younger.
STYLE: <one style paragraph, identical for every character in the cast>
NO TEXT: no writing of any kind in any language (Japanese and English included): no captions, labels, name tags, banners, speech bubbles, logos or watermark. A single person, seen once.
```
With a single crop, write "the image is a close-up of the person's face." The FACE line is what the human would say about the person's face: shape, hairline, hair, facial hair, eyes, the expression they always have.

### 3. Pick, or adjust

Show both faces. If the human says "close, but the face should be a little fuller", carry it into the card step as an adjustment instead of re-rolling the face: "the same person as in Image 1, but with a slightly fuller face."

### 4. Costume card (Flare edit of the face)

```bash
bash <this-skill-dir>/scripts/openai-image.sh --size 1024x1536 --draft \
  --ref characters/dana-face.png --output characters/dana-card.png --prompt "$PROMPT"
```
```text
Image 1 is this character's approved face. Draw the same character again, now as a waist-up figure: BUILD: average height, a soft and slightly round build, not muscular. POSE: one hand on her hip, pointing with the other. CLOTHES: red bomber jacket over a striped shirt. BACKDROP COLOR: hot magenta #E0218A.
The face stays exactly as drawn in Image 1 (its shape, hairline, facial hair, eyes, nose, skin tone, line work and colors); only framing, pose, clothes and backdrop are new.
FRAMING: a waist-up view, the figure standing centered and facing the viewer, with some headroom.
BACKDROP: a single flat color edge to edge, with no gradient, sky, room or scenery.
NO TEXT: <the same no-text block>
```
- **State the build, with what it is not.** Left alone, the model makes everyone slim or muscular. Phrases in this shape worked: "sturdy, wide shoulders, but not heavy", "soft and a bit round in the middle, not athletic", "tall and thin".
- **One flat, unique background color per character.** It doubles as the character's subtitle color, and it lets a group collage cut the card out by flood fill.
- **A prop per character** (a guitar, a skateboard, a red cap) makes them readable in a crowd scene later.
- Flare follows this edit as well as Sunburst `high` does, at a fraction of the cost.

### 5. Likeness review

Put every card on one sheet and send it:
```bash
ffmpeg -pattern_type glob -i 'characters/*-card.png' -vf scale=256:-2,tile=6x3 cards_sheet.jpg
```
Expect retakes on roughly one card in four: a body type that drifted, an accessory nobody asked for (a hat), a face that drifted toward generic. Record each correction in the character bible so the next retake keeps it.

**Judge likeness on a zoomed face crop, side by side with the photo, not on the downscaled full frame.** Shrunk, a face can read older or rounder than it is; in one photoreal run a "change only the face" retake ($0.19) changed almost nothing, because the likeness had been fine all along. Crop the face region from both and put them next to each other, then read the result:
```bash
magick photo.jpg -crop 400x400+300+120 +repage a.png && magick output.png -crop 400x400+310+140 +repage b.png && magick a.png b.png +append face_check.png
```

### 6. Promote (Sunburst max edit)

```bash
bash <this-skill-dir>/scripts/openai-image.sh --size 1024x1536 \
  --ref characters/dana-card.png --output characters/final/dana.png --prompt "$PROMPT"
```
```text
Image 1 is the approved draft of this card. Redo it as the finished version: improve only the rendering (crisper line work, cleaner shading, richer color). Everything else stays as it is: framing, face and expression, hair, build, pose and hands, clothes, every prop and where it sits, and the flat hot magenta #E0218A backdrop. Add nothing new: no extra objects, no writing, no watermark.
```

## Photoreal versions of a real person

The same pipeline works for photoreal stills (a person as a superhero, say), with differences seen in one 2026-10 run. Only do this for people who agreed to it.
- **OpenAI's output moderation is stricter on photoreal edits of a real photo.** A Flare draft was blocked as "other", and a revealing costume as "sexual". What passed: a fuller costume (armor with shoulder pieces rather than a strapless top) and softer identity wording ("a reference for the person's face, hair and skin tone" instead of "preserve the face exactly, instantly recognizable"). The same strong wording passed for a comic-book style.
- **Costume archetypes override details.** A prompt that asked for leggings came back with bare legs, because the model followed the classic heroine look. Describe the whole costume concretely, garment by garment.
- **Two references for a likeness edit worked:** Image 1 = the approved design draft (costume, lighting, palette), Image 2 = the original photo, labeled as a face reference only.
- If OpenAI refuses a variant, the still you already have can still be animated (see generating-video-clips): Google's video model accepted it.

## Cost (measured 2026-10)

| Step | Model | Per character |
|---|---|---|
| Face, 2 options | Flare `medium` | ~$0.02-0.05 |
| Card | Flare `medium` | ~$0.02-0.05 |
| Promote | Sunburst `max` | ~$0.18 |

With retakes, budget about $0.30 per character.

## Failures and fixes

| Symptom | Cause | Fix |
|---|---|---|
| The output is the reference photo, restyled | whole photo passed as `--ref` | face crops only |
| Japanese or English captions on the card | no text ban that names the languages | the no-text block, naming Japanese |
| A character sheet: several views, labels | nothing limits the views | "A single person, seen once." |
| Everyone muscular, or everyone slim | build left to the model | a BUILD line that also says what they are not |
| A beautified, younger face | likeness not pinned | "don't make them thinner, prettier or younger" |
| An accessory nobody wanted | not ruled out | name it out: "plain grey sweater, no hat" |
| The prompt's constraints seem ignored in edits | prompt cut at a `;` by `curl -F` (fixed in `openai-image.sh` 2026-10, which now sends text fields with `--form-string`) | update the script; avoid hand-rolled `curl -F prompt=...` |
