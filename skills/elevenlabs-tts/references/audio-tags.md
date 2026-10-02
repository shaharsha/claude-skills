# Eleven v4 audio tags — the catalog

Read this when you are choosing tags for a script and want more than the narration palette in SKILL.md, or when a tag is misbehaving.

**There is no closed list.** ElevenLabs: "There is no definitive ElevenLabs Audio Tags list because you can create any combination you'd like by writing in natural language." What follows is the vocabulary ElevenLabs itself uses in its v4 docs and examples, grouped the way they group it. v3 tags all still work on v4 ("scripts you previously wrote for v3 will still work in v4"); no tag is deprecated.

Sources (fetched 2026-10-02): [tags list blog](https://elevenlabs.io/blog/elevenlabs-audio-tags-list) · [best practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices) · [v4 model page](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4) · [v4 landing](https://elevenlabs.io/v4) · [Text to Dialogue](https://elevenlabs.io/docs/overview/capabilities/text-to-dialogue)

## Contents
1. How v4 reads a tag (syntax, scope, stacking)
2. Narration directions (the long-form style)
3. Emotion, by family
4. Delivery and volume
5. Pacing and pauses
6. Human reactions (non-verbal)
7. Accent and character
8. Sound effects
9. Writing your own
10. Troubleshooting

## 1. How v4 reads a tag

- **Square brackets only.** Parentheses or braces get read aloud.
- **Placement:** immediately before the words it modifies (`[annoyed] This is hard.`), or immediately after for a reaction (`This is hard. [sighs]`).
- **Scope carries forward.** "Emotion carries forward across the line, meaning you only need to introduce another tag when you want the delivery to shift." Tag the *shifts*, not every sentence. (One agent-docs page written for the real-time conversational model says ~4–5 words; for pre-rendered v4 TTS, treat a tag as holding until the next one.)
- **Stacking:** comma-separate qualities inside one bracket — `[whispering, playful]`, `[low, steady voice, restrained urgency]`. Adjacent brackets also work (`[annoyed] [under his breath]`).
- **One tag per clause.** "Contrasting tags on the same words can blur the performance."
- **v4 renders sound effects too**, so a bare tag can be read as an SFX request. When you mean the *voice*, say voice: `[low, gravelly voice]` rather than `[gravel]`.
- **The voice no longer has to be cast for the tag.** "A voice that has never whispered should still be able to follow `[whispering]`" — but it may be less reliable, and a serious corporate voice still resists `[giggles]`.

## 2. Narration directions (the long-form style)

ElevenLabs' own v4 narration examples use descriptive, comma-separated directions rather than single words. This is the style to reach for in presenter narration:

`[Quiet, measured narration]` · `[Warm, conversational tone, faint amusement]` · `[Warm, intimate narration]` · `[Quiet, reflective narration]` · `[Gradually building energy]` · `[Building tension, measured pace]` · `[Quick, light, playful pace]` · `[Low, steady voice, restrained urgency]` · `[Voice rising into firm resolve]` · `[Softening, reflective]` · `[Softly, with wonder]` · `[Gentle laugh, then sincere]` · `[Pause, dry amusement]` · `[Brief pause]` · `[Gentle pause, then quiet realization]` · `[Quietly, with controlled fear]` · `[lower, thoughtful]` · `[measured]` · `[quietly curious]` · `[casual]`

## 3. Emotion, by family

| Family | Tags |
|---|---|
| High energy | `[excited]` `[playful]` `[amazed]` `[powerful]` `[proud]` `[optimistic]` `[startled]` `[ecstatic]` `[delighted]` `[elated]` `[triumphant]` |
| Heated | `[mad]` `[aggressive]` `[bitter]` `[critical]` `[repelled]` `[annoyed]` `[dismissive]` `[disgusted]` |
| Tense | `[anxious]` `[stressed]` `[scared]` `[threatened]` `[vulnerable]` `[confused]` `[busy]` `[nervous]` `[jittery]` `[frazzled]` `[uncertain]` |
| Low energy | `[tired]` `[bored]` `[distant]` `[despair]` `[let down]` `[sad]` |
| Calm / reflective | `[peaceful]` `[content]` `[curious]` `[thoughtful]` `[trusting]` `[hopeful]` `[intrigued]` `[warm]` |
| Wry | `[sarcastic]` `[smug]` `[mischievously]` `[amused]` `[puzzled]` `[quizzically]` |

If a delivery misses, swap to a neighbouring tag in the same family (`[let down]` instead of `[despair]`) before rewriting the line.

## 4. Delivery and volume

`[whispers]` `[whispering]` `[shouts]` `[softly]` `[quietly]` `[hushed]` `[barely audible]` `[booming]` `[low, threatening]` `[under his breath]` `[cheerfully]` `[cautiously]` `[stuttering]` `[disbelief]`

## 5. Pacing and pauses

`[slowly]` `[rushed]` `[drawn out]` `[snappy]` `[speedy]` `[pause]` `[short pause]` `[long pause]` `[slightly pause]`

There is **no speed setting on v4** and **SSML `<break>` is disabled** — pace lives here and in punctuation. A third-party Hebrew pipeline measured one sentence at `[speedy]` 5.1 s · `[snappy]` 5.5 s · `[calm]` 6.1 s · `[slowly]` 7.2 s, so pacing tags do move the clock. Verified 2026-10-02: `[Pause, dry amusement]` mid-script produced a real ~1.9 s pause.

Punctuation levers: ellipsis `…` = pause with weight · CAPS = emphasis · dash = interruption · line break = longer beat · real `?` and `,` set rhythm.

## 6. Human reactions (non-verbal)

`[laughs]` `[laughs harder]` `[starts laughing]` `[chuckles]` `[soft chuckle]` `[giggles]` `[nervous laugh]` `[wheezing]` `[sighs]` `[exhales]` `[exhales sharply]` `[inhales deeply]` `[gasps]` `[clears throat]` `[crying]` `[starts crying]` `[snorts]` `[gulps]` `[swallows]` `[yawning]` `[groaning]`

v4 also inserts small disfluencies on its own when the text invites them ("Y- you came back?").

## 7. Accent and character

`[British accent]` `[French accent]` `[Australian accent]` `[Irish accent]` `[strong X accent]` (experimental) `[pirate voice]` `[sleepy drowsy voice]` `[said angrily in French accent]` `[whispered in a British accent]` `[like a sports commentator, speeding up]` `[auctioneer]`

Note: when a voice speaks a language other than its reference language, v4 deliberately uses that language's **native** accent rather than carrying the voice's source accent over. An accent tag is the only lever ("results may vary").

## 8. Sound effects

`[applause]` `[crowd applause]` `[clapping]` `[thunder rumbling]` `[light rain]` `[footsteps]` `[gentle footsteps]` `[door creaking]` `[door slams]` `[phone buzzing]` `[dog barking]` `[leaves rustling]` `[Gong sounds]` `[gunshot]` `[explosion]` `[zipper opening]` — experimental: `[sings]` `[woo]`

**Keep these out of presentation narration** unless the user asked for them: they are rendered into the speech track, can't be mixed down afterwards, and they eat into the clip's timeline (shifting every forced-alignment offset after them).

## 9. Writing your own

Any of these shapes work — combine qualities, describe the manner, the situation, the character, or a shift:
`[tense, cautious]` · `[like a sports commentator, speeding up]` · `[out of breath after running up the stairs]` · `[a tired detective who has heard it all before]` · `[starting calm, then losing patience]` · `[nervous, trying to sound confident]` · `[hushed and reverent, like a nature documentary narrator]`

Don't write narrative cues in prose ("she said, trembling") — prose is spoken.

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Tag word spoken aloud | non-bracket delimiters; tag the model can't map; voice/tag mismatch | square brackets; rephrase as a description; `scripts/check_tags_spoken.py` to find which clips |
| A sound effect where you wanted a tone | tag read as SFX | name the voice quality: `[low, gravelly voice]` |
| Over-acted, cartoonish | `[excited]` + `!` stacked; too many shifts | one shift per beat; `[warm, calm]` baseline; raise stability |
| Flat despite tags | tags fighting a high stability, or every sentence re-tagged | lower stability (A/B), tag only shifts |
| Blurry delivery | contradictory tags on the same clause | one tag per clause |
| Behaviour changed week to week | v4 is updated continuously after launch | re-test a reference clip before a big batch |
