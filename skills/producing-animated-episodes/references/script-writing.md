# Writing the episode

## Skeletons

**Under 30 seconds** (3-4 shots): a cold open with the title as an overlay, one dialogue shot, one payoff shot with the end caption as an overlay. No intro montage. Keep each dialogue shot under about 8-9 s (the clip length an image-to-video model holds well); split longer exchanges into two shots.

**Narrated** (one storyteller voice, e.g. for a class): the narrator is a `speakers` entry with a voice, so it is never drawn; each shot holds about one narration line, and nobody needs lip-sync unless a character also speaks on screen.

**About 1 minute** (8-10 shots):
1. Cold open, 0-4 s: the problem in one image and one line.
2. Title card.
3. Who's who: one fast card per character (optional for 2-3 characters).
4. The situation escalates: 2-3 shots.
5. The turn: a clue, a twist or a confession.
6. The button: a last joke or callback.
7. End card.

**About 3-4 minutes** (25-35 shots):
1. Cold open, 0-4 s.
2. Title and opening music.
3. An intro montage: every character says one word that defines them, about 1.2-1.5 s per card.
4. Setup: where and when, an on-screen caption.
5. The inciting event.
6. Investigation: everyone gets a turn, accusations, red herrings.
7. A low point or a quiet moment, so the comedy can breathe.
8. The reveal, fairly clued earlier.
9. Celebration or consequence.
10. A button, then an end card with a "next episode?" hook.

## Pacing numbers that held up

- About 8-10 shots a minute. Shots with dialogue take as long as their lines plus small pads; the engine measures them.
- Lines of 12 words or fewer. Long lines read badly as subtitles and give lip-sync less to work with.
- One-word lines for an intro montage: generate, trim and level them (`trim`, `level` in `lines`).
- On-screen text needs reading time: about 0.8 s plus 0.06 s per character. A short card needs 1.2-1.5 s, and a final caption 4-6 s. The first cut of a montage at 0.6 s per card was unreadable.
- Give the ending room: keep 4-6 s after the last caption appears, and let the fade-out finish.

## Mining a chat export (for a group of friends or a team)

What makes it theirs is what the group already says: running jokes, catchphrases, nicknames, who always does what, who argues with whom. Read the whole export before writing, and keep a short list of the five or six recurring bits, with one real example each.

**Sensitive topics are the user's call, not yours.** A chat holds things people would not want in a video shared with the group: health, money, relationships, family trouble, fights. Make a list of every such topic you'd like to use, ask the user about each, and use only what they confirm. When in doubt, leave it out; an inside joke works as well when it's affectionate.

## Writing for text-to-speech

- Audio tags in English inside the line: `[shocked, loud]`, `[whispering]`, `[proud, energetic]`. One per line is usually enough.
- Numbers, dates and times written as words.
- Names and loanwords that the voice may mispronounce go in `pronounce`, not in the line. The line keeps normal spelling, because subtitles are made from it.
- Every character speaks at least once. A character with no line needs a reason (asleep, absent, on a video call) that is itself a joke.

## A worked example (fictional)

"The Last Slice", about one minute:

| # | Shot | Line | On screen |
|---|---|---|---|
| 1 | S01 kitchen at night, empty pizza box | Maya: "[shocked, loud] Who ate the last slice?!" | title pops: "The Last Slice" |
| 2 | C01 Maya's card | Maya: "[proud] Justice!" | band: Maya, pizza judge |
| 3 | C02 Ido's card | Ido: "[innocent, slow] Pizza?" | band: Ido, suspect no. 1 |
| 4 | S02 video call on a tablet | Ido: "[nervous, fast] I wasn't even here. I was on my phone." | |
| 5 | S03 close-up: tomato sauce on Ido's sleeve | (no line) | caption: "Exhibit A." |
| 6 | S04 Maya slowly turns to the camera | Maya: "[deadpan] On your phone." | |
| 7 | S05 group shot | (no line) | end card: "The Last Slice - the end" |

The clue (the sauce on the sleeve) is planted in the first frame and paid off in shot 5.
