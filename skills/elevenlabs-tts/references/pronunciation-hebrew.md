# Pronunciation in Hebrew (and other non-English) TTS on eleven_v4

Verified on `eleven_v4` in 2026-10 with a large cloned-voice cast. Everything here was decided by a human listening, never by reading a transcript: Scribe "hears" the word you intended even when the voice said something else.

## The ladder: try in this order

Each rung fixes something the one before can't, and each has its own failure. **Loanwords, brands and names:** rungs 1, 2, then 4 and 5. **A Hebrew word read wrong:** rung 3. **Acronyms:** rung 6.

1. **Latin script inside the Hebrew.** Write loanwords, brands and names in Latin letters, and keep the Hebrew prefix, hyphenated:
   `הבאתי ה-Absolut ל-Shiran` instead of `הבאתי האבסולוט לשירן`.
   This fixed every brand and name in the cast. Fails when the English spelling itself is ambiguous: move to rung 2.
2. **Respell the name the way it sounds.** A name's usual English spelling can be read with the wrong vowels. Spell out the vowel you hear (an extra `e` or `a`), then A/B it. Fails for non-English foreign words: move to rung 4.
3. **Niqqud.** It fixes vowels in Hebrew words. On loanwords it backfired: a three-syllable loanword came out as three separate syllables, and much worse under a "slowly" tag. Never combine niqqud with `[slowly]`.
4. **Full niqqud on a foreign word written in Hebrew letters.** For a non-English foreign word (a Japanese martial-arts term, say), Hebrew letters with full niqqud beat both Latin script and IPA.
5. **IPA in quotes, as the last resort:** `"/ˈkaɾate/"`.
6. **Acronyms: write what should be heard.** Latin capitals (`TV`, `NASA`) rather than the Hebrew letter names spelled out. Check by ear: some acronyms come out as a word.

## Homographs from prefixes

Hebrew glues `ה ו מ ל ב ש` to the next word. Glued to a name, a prefix can produce an ordinary word that v4 reads instead (seen: מ + a two-syllable name was read as a verb). The fix is the same as rung 1: keep the prefix in Hebrew, hyphenated, and the name in Latin: `מ-Dani`, `ל-Shiran`.

## The A/B procedure

1. Generate each variant as its own clip, same voice and settings.
2. Join them, a second apart, and print where each starts:
   ```bash
   python3 <this-skill-dir>/scripts/ab_concat.py ab.mp3 v1.mp3 v2.mp3 v3.mp3
   #   A  0:00.00  v1.mp3
   #   B  0:02.87  v2.mp3
   #   C  0:05.92  v3.mp3
   ```
3. Send `ab.mp3` with the table, and ask one question: "which one sounds like Shiran?"
4. The human answers by timestamp ("the one at 0:05"). Keep the losing variants until the project ships; the human sometimes changes their mind once the line sits in context.

## What not to trust

- **Scribe transcripts.** The transcript of a mispronounced name usually shows the right name.
- **Your own reading of the text.** You cannot hear the audio. Say so.
- **v3-era advice.** It may still hold, but re-verify on v4: v4 is updated continuously.

## Subtitles keep the real spelling

Keep a `pronounce` table of `[from, to]` pairs, applied in order with the prefixed forms first (`["האבסולוט", "ה-Absolut"]` before `["אבסולוט", "Absolut"]`), and apply it **only to the TTS input**. Subtitles and on-screen text come from the original script. A viewer of a Hebrew video must never see `Absolut` inside a Hebrew subtitle line.
