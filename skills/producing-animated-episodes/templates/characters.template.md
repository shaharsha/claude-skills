# Characters

| Key | Display name | Photo refs | Face (what must not change) | Build (and what it is not) | Outfit and prop | Backdrop color | Voice id | Sample line |
|---|---|---|---|---|---|---|---|---|
| <id> | <name on screen> | <faces/id-1.png, faces/id-2.png or "none"> | <face shape, hair, facial hair, eyes, usual expression> | <e.g. tall and thin, not muscular> | <clothes, plus one prop that identifies them> | <color name #RRGGBB, unique per character> | <voice id> | <one line in their register> |

Copy each row into `episode.json` `characters` (`display`, `refs`, `likeness`, `body`, `outfit`, `pose`, `background`, `voice`).

## Likeness feedback log

Record every correction the human asks for, so a retake keeps it.

| Date | Key | Feedback | Change made |
|---|---|---|---|
| <yyyy-mm-dd> | <id> | <"the face should be a bit fuller"> | <face_adjust: "with a slightly fuller face"> |
