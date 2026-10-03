# A cast of voices and very short lines

Character work (one cloned or library voice per character, many short lines, crowd shouts) breaks things that narration never hits. Everything here comes from a large cast on `eleven_v4` in 2026-10.

## 1. Casting

- Keep a voice table per project: character, voice ID, one sample file. Voice IDs of private clones belong in the project, never in a public repo.
- Generate **one sample line per voice**, in the register that character will use (an angry line for the angry one), and play the whole set to the human before any batch.
- **One model and one stability for the whole cast** (0.4 suited comedy), and `language_code` set. A different setting on one character is audible next to the others.
- Clones made before v4 should be retrained on v4 first (see SKILL.md, Voices).

## 2. One-word and very short lines

What goes wrong, in the order it happened:
- **The word said twice** ("yes, yes"): the model fills the time.
- **A sigh, laugh or breath before the word**, from a tag like `[sighs]` or `[laughing]`.
- **A long lead-in** of near-silence.

The fix is to trim to the aligned words, then level:
```bash
python3 <this-skill-dir>/scripts/trim_to_words.py lines.json raw/ trimmed/ --prefix ""
python3 <this-skill-dir>/scripts/level_clips.py trimmed/ leveled/ --target -18
```
- `trim_to_words.py` force-aligns each clip against its tag-stripped text and keeps the first to the last word, with a 0.04 s lead, a 0.14 s tail and 20/60 ms fades. It never touches `raw/`.
- When a clip's audio no longer matches its script (you cut one word out of another take), pass the words actually in it: `--text 04-07="the word"`.
- When the word was repeated, the window usually covers one occurrence, but listen.
- `level_clips.py` brings every clip's **voiced** mean to the target. Plain `loudnorm` on a one-word clip measures mostly silence, so loud and quiet clips stay uneven.
- Expect to regenerate a few words in every batch for a repeat or a wrong reading.

## 3. Pace

`atempo=1.1` on every line (pitch is kept) tightened comedic timing noticeably:
```bash
mkdir -p fast && for f in raw/*.mp3; do ffmpeg -y -i "$f" -af atempo=1.1 -ar 44100 -b:a 160k "fast/$(basename "$f")"; done
```
Apply it to the whole set, and force-align **after** it, never before.

## 4. Crowd shouts

"Everyone shouts the toast": generate the same line in 6-10 voices, then mix them a few tens of milliseconds apart so it sounds like a crowd, not a choir:
```bash
ffmpeg -y -i a.mp3 -i b.mp3 -i c.mp3 -i d.mp3 -i e.mp3 -i f.mp3 -filter_complex \
 "[0]adelay=0|0,volume=0.9[a0];[1]adelay=37|37,volume=0.9[a1];[2]adelay=74|74,volume=0.9[a2];[3]adelay=111|111,volume=0.9[a3];[4]adelay=148|148,volume=0.9[a4];[5]adelay=25|25,volume=0.9[a5];[a0][a1][a2][a3][a4][a5]amix=inputs=6:normalize=0,loudnorm=I=-16:TP=-1.5[o]" \
 -map "[o]" -ar 44100 -ac 1 -b:a 128k crowd.mp3
```
(Offsets are `i*37 % 160` ms.) Crowd lines get no lip-sync; nobody's mouth matches a crowd.

## 5. Swallowed words

A take can drop one word to a mumble in the middle of a good line. Find it before the music goes under it:
```bash
python3 <this-skill-dir>/scripts/level_clips.py raw/ --report
#   02-1   voiced mean  -19.4 dB  peak  -2.1 dB  weak at [1.35]
```
A weak window is a 150 ms stretch 12 dB or more under the clip's voiced median, but louder than a pause.
- Regenerate that line 2-3 times with a firmer tag (`[clear, confident]`, `[loud and clear]`), keep the take with the fewest weak windows, and let the human confirm.
- In the final mix, two filters keep dialogue on top:
  - a dialogue-bus compressor: `acompressor=threshold=0.06:ratio=3.5:attack=5:release=150:makeup=2.2`
  - music ducked under dialogue: `sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350`, with the music as input and the dialogue as the key
  - pad the dialogue before it becomes the key (`[dlg]apad,asplit=2[dlg1][key]`): `sidechaincompress` ends when its key ends, so without the pad the music goes silent after the last line

## 6. Leak-check false alarms

`check_tags_spoken.py` flags three things that are not leaks:

| Flag | What it really is | What to do |
|---|---|---|
| A bracketed word in the transcript | Scribe annotating non-speech, in the clip's own language (a Hebrew word for "sighs" in brackets) | ignore it |
| `EXTRA` on a one-word clip | Scribe guessed the wrong language for one word | rerun with `--language-code he` |
| `LEAK` on a word that is also in the line (a `[whispering]` tag on a line that says "stop whispering") | the tag word appears in the content | read the transcript; no regeneration needed |

## 7. What only the human can judge

Pronunciation, emotion, a repeated word, a word cut mid-syllable, and whether a voice fits a character. Send the file, give timestamps ("02-1 at 0:01.3: is 'Dani' clear?"), and ask one question per issue. Never say you heard it.
