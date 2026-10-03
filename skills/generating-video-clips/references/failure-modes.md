# Clip failure modes and their fixes

Every row below happened in a real animated episode (Gemini Omni Flash 1.1, 2026-10); the examples here are rewritten as fictional scenes. Find the problem on a take sheet first (`take_sheet.py sheet`), name the exact second, then pick the fix. Where the problem sits decides the fix.

| Symptom | How it shows on a sheet | Fix |
|---|---|---|
| A prop doubles at the start (a figure holds two lanterns) | first 1-2 columns only | start later (`--off 1.5`), then slow the rest if it no longer fills the shot (`--speed` up to ~1.25) |
| A door, wall or window appears | from some column on, the room changes | pin the room: "one single window on the left wall, no other windows or doors appear"; 2-3 takes |
| A second figure appears | an extra person in later columns | "There is exactly ONE ...", "No second figure"; 2-3 takes |
| A hand passes through a body | a hand overlaps another character mid-clip | pin the hands: "her hands stay flat on the table the whole time; no hand crosses in front of anyone's body"; retake |
| Glowing eyes on a hooded or shadowed figure | bright dots on a dark shape | "a solid dark shape with no visible face, eyes or glow" |
| A gesture before its line, then again (points, lowers, points) | the pose repeats | start the clip after the first gesture (`--off`), or split the shot: play the earlier line on a crop that keeps the hand out of frame, then cut into the clip after the gesture |
| A scene cut mid-clip | one column looks like a different shot; confirm with `ffmpeg -i clip.mp4 -vf "select='gt(scene,0.3)',showinfo" -an -f null - 2>&1 \| grep pts_time` | "no scene cuts" in the base prompt; trim before the cut |
| Faces drift from the character art | later columns look less like the cards, often as the camera moves closer | keep clips ≤ 8 s; describe people by clothes, not names; pin the framing: "the camera keeps the same distance; the face never gets larger than in the first frame" |
| Text appears or the still's text garbles | letters in frames | "No text, no subtitles" in the base; keep text out of the still and overlay it in the edit |

## Worked example: a stormy lighthouse shot

The shot in the edit is 7.5 s; the clip is 8 s. The sheet shows two problems:
- **0.0-1.0 s:** the hooded figure at the window holds two lanterns.
- **From 4.0 s:** a second window appears in the back wall.

Steps:
1. **First, can trimming alone save it?** Skipping 1.0 s leaves 7 s, but the new window appears at 4.0 s, which is 3 s into the shot. Trimming alone fails.
2. **Regenerate with pins,** 3 takes. Move the old takes to `_old/` first: the script skips any take file that already exists, so a rerun with a new prompt would otherwise silently produce nothing.
   ```text
   Static camera; the set never changes and has a single window, in the left wall, and no other window or door. Only ONE hooded figure exists, always outside that window: an unlit dark form with no visible face or eyes and no light on it, carrying one lantern ... Nobody else appears, no extra window, no glowing eyes.
   ```
3. **Sheet the three takes** (`take_sheet.py sheet review/S04.jpg S04_t1.mp4 S04_t2.mp4 S04_t3.mp4 --times 0.3,1,2,3,4,5,6,7`). Take 1 is clean except a doubled lantern in its first 1.5 s.
4. **Fit it.** Starting at 1.5 s leaves 6.5 s for a 7.5 s shot, so also slow it by 7.5 / 6.5 ≈ 1.16 (180 frames at 24 fps):
   ```bash
   python3 <this-skill-dir>/scripts/lipsync_parts.py normalize S04_t1.mp4 S04_shot.mp4 --frames 180 --off 1.5 --speed 1.16
   ```
5. **Check the result** on one more sheet before it goes into the edit.
