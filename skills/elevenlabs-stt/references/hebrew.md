# Hebrew and mixed Hebrew/English: what was measured

Two clips, both measured on 2026-11-13:
- **Talk:** 3 minutes of a public Hebrew tech talk, one speaker, with dense English jargon (agent, harness, sandbox, evals, benchmark).
- **Meeting:** 5 minutes of a Hebrew engineering meeting with 7 participants and frequent English terms.

Counts are words containing Latin letters in the `words[]` array, which measures how many English terms stayed in English script. They are not error rates: there is no hand-checked reference for these clips.

## English terms: Latin vs Hebrew script

| Variant | Talk: Latin words (of ~456) | Meeting: Latin words (of ~565) |
|---|---|---|
| v2, diarize | 37 | 74 |
| v2 + 8 keyterms | 38 | - |
| v2 + no_verbatim | - | 57 (of 501, fillers removed) |
| v3, diarize | 6 (repeat run: 5) | 57 |
| v3, no diarize | 2 | - |
| v3 + `language_code=he` | 2 | - |
| v3 + `language_code=he` + `secondary_language_codes=en` | 2 | 62 |
| v3 + 1 unrelated keyterm ("Kubernetes") | 6 | - |
| v3 + 10 generic tech keyterms | - | 57 |
| v3 + 75 glossary names/tools + 20 English terms incl. Python, proxy | - | 56 (`Python`/`proxy` still 0 of 12 in Latin; `SSM` now right) |
| v3 + 8 keyterms said in the talk | 26 | - |
| v3 + 12 keyterms said in the talk (via `transcribe.py`) | 33 | - |
| v3 + no_verbatim | 34 | 66 |
| v3 + `transcript_edit` "write English terms in Latin script" | 6 (and the edit romanized the Hebrew) | - |

What this shows:
- **Plain v3 transliterates English loanwords**, strongly in fluent monologue (`האייג'נט`, `סטייט מאשין`, `רביט הול`, `סנדבוקס`, `הבנצ'מארק`) and less in a meeting (`פרוקסי`, `פייתון`).
- **Keyterms that are actually said** pulled the talk back to Latin script, and the effect spread beyond the listed words: 8 terms brought 26 words back. An unrelated term did nothing. On the meeting, even listed common words (`Python`, `proxy`) stayed in Hebrew letters (12 of 12), although keyterms still fixed recognition (`SSM` instead of `Excel`).
- **`no_verbatim` flipped the style back on both clips**: 34 Latin words on the talk, and on the meeting `Python`/`proxy` came out Latin 8 times (v2: 7). It drops fillers (`אה`, `אמ`, repeated words), so it suits subtitles, summaries and searchable archives, not a verbatim record.
- **v3 Title-Cases English terms in meetings** (`ה-Agent`, `Web Search`, `Daily`) where v2 wrote lower case. Normalize in post-processing if it matters.

## Word differences, v2 vs v3 (talk, same audio)

About 95% of words were identical (difflib ratio 0.944-0.945). The differences, with the likely-correct reading judged from context:

| v2 | v3 | Likely right |
|---|---|---|
| merge queue | merge | v2 (v3 + "merge queue" keyterm gets it) |
| חמשתאלף | חמשת אלפים | v3 |
| ה-eval | האיוולים / ה-evils (no_verbatim) | v2 |
| Judge | Jaja | v2 |
| ברג | ברק | unclear |
| Flexorace | Flexorase | both wrong ("Flexor" keyterm did not fix it) |

On the meeting, v3 got some words v2 missed (`Tenant` for v2's `טנר`) and missed some v2 got (`Excel` for `SSM`, `Corpus Master` for `Open Source`). Neither model is clearly better on Hebrew tech speech. ElevenLabs publishes no Hebrew-specific v3 figure (its language table still rates Hebrew "Good", 10-20% WER, based on v2).

## Diarization (meeting, 7 people, about 4 speaking in the clip)

| Variant | Speakers found | Speaker turns |
|---|---|---|
| v2 | 4 | 22 |
| v3 | 4 | 20 |
| v3 + `num_speakers=7` | 4 | 22 |

Same clusters on this clip. ElevenLabs reports 12% fewer diarization errors overall and 17% fewer with 3+ speakers.

## Speed

| Clip | v2 | v3 |
|---|---|---|
| 3 min | 46-48 s | 26-34 s |
| 5 min | 53-60 s | 35-41 s |

## Earlier v2 results worth knowing

From a Hebrew ASR benchmark run in 2026 on WhatsApp voice notes, podcasts, read speech and a code-switching set:
- Scribe v2 scored WER 11.2% (WhatsApp), 6.6% (podcast), 16.7% (formal/read, FLEURS-He), 2.4% (mixed Hebrew/English) and 5.1% (English).
- It was the only model tested that transcribed a real mixed-language Zoom call correctly.
- v3 has not been run on that benchmark.

## Recipe for Hebrew/English tech audio

1. Build a keyterm list from what will be said: product, tool and company names, people's names in Latin script, and the English jargon of the field. Short and relevant beats long and generic.
2. `transcribe.py FILE --out DIR --language he --keyterms-file terms.txt`. Add `--clean` when English terms must stay in Latin script and fillers don't matter (subtitles, searchable archives).
3. Read the `Latin-script words` line. If it is near zero while English terms were spoken, add the terms you see transliterated and re-run; if common words such as `Python` stay in Hebrew letters, `--clean` is the lever that worked.
4. Normalize casing and known mishearings in post-processing, and keep the raw JSON.
