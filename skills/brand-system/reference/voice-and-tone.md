# Voice & tone

The two rules that separate a real voice chapter from a template:

1. Write the chapter *in* the brand's voice, not *about* it.
2. Tone varies by **reader emotional state**, not by channel.

Both come from [Mailchimp's Content Style Guide](https://styleguide.mailchimp.com/),
still the reference after 15+ years.

## Voice vs tone

- **Voice** = who the brand *is*. Constant. 3–5 attributes.
- **Tone** = how the voice adjusts to context. Variable. A matrix.

A brand has one voice and many tones. A confused reader in a homepage
hero gets the same tone-shift as a confused reader in an error
message — the reader's feeling determines the dial, not the surface.

## Voice: 3–5 attributes, each with a "but not"

```
We are plainspoken.  (but not dumbed-down)
We are direct.       (but not cold)
We are funny.        (but not jokey)
We are confident.    (but not arrogant)
```

The "but not" is the falsifiable bit. "Plainspoken" without "but not
dumbed-down" opens the door to patronising copy. The constraint is
where the voice lives.

## Tone matrix by reader emotional state

| Reader state | Formality | Warmth | Humour | Urgency | Example |
|---|---|---|---|---|---|
| Confused / lost | low | high | none | low | "No worries — let's retry that." |
| Frustrated / blocked | low | medium | none | medium | "Here's what broke. Here's the fix." |
| Relieved / fixed | low | high | light | low | "Back on track." |
| Celebrating | low | high | light | low | "You did the thing." |
| Learning (onboarding, docs) | medium | medium | none | low | "Quick context, then the how." |
| Error / hard-block | medium | low | none | high | "Can't continue until X. Contact: Y." |
| Legal / T&C | high | low | none | low | Formal, plain, neutral — no voice at all. |

The matrix lives in §13 of BRAND.md. Fill it with concrete examples per
row, not just the dials.

## The 150-word voice sample

Required. Pick a surface (welcome email, 404 page, cancellation, error
message) and write it in the brand's *actual* voice. Paste it
verbatim into §13. The sample must do two things:

1. Be good writing.
2. Be recognisably this brand and no other.

If you could swap in a competitor's name and the copy still worked,
it's not the brand's voice yet.

**Agentleh example** (welcome email after coupon redeem, abridged to ~100 words):

> Hi Yossi — your agent is ready. Text any WhatsApp message to +972-…
> and it'll reply as you would, in your voice.
>
> Three things to try first:
> - Forward an email from a customer. The agent drafts the reply.
> - Ask "what's on tomorrow?" — the agent reads your calendar.
> - Say "book Mai for a cut at 4" — the agent writes the invite.
>
> Give me an agent. Talk to us whenever.

Short. Direct. Numbers where adjectives would go. Present tense.
Second-person direct (`give me an agent`). Unmistakably Agentleh.

## Three levels of the same thought

When the team debates copy, use the three-levels exercise. Write the
same idea three times:

**Bad (corporate)**:
> "Agentiko leverages advanced AI to streamline your daily business
> communications and optimize workflow efficiency."

**Okay (direct but flat)**:
> "Agentiko is an AI assistant that handles your emails and schedules
> meetings in WhatsApp."

**On-brand**:
> "Your inbox answers itself. Your calendar fills itself. You do the
> actual job."

The third is harder to write and easier to recognise. The exercise is
quick and forces intentionality.

## Say this, not that — concrete pairs

Table of 5–10 rows. Each row is a real swap the team has made. Not
theoretical. Generic versions of this table are worthless; specific ones
are load-bearing.

```
| Instead of                      | Say                          |
| "Revolutionize your workflow"   | "Give your inbox back."       |
| "AI-powered assistant"          | "An agent that works for you."|
| "Seamlessly integrated"         | "Lives where you already are."|
| "Learn more"                    | "See how it works."           |
| "Get started today"             | "Give me an agent."           |
| "We'd love to hear from you"    | "Talk to us."                 |
| "Thank you for your interest"   | (cut entirely)                |
```

## Microcopy rules

- **CTAs**: verb-first. `Send`, `Start`, `Show me how`, `Give me one`.
- **Empty states**: explain what will appear; don't apologise for
  nothing being there.
- **Errors**: what happened → what to do. Never blame the user. Never
  show a stack trace.
- **Loading**: only show a loader if the wait exceeds 400ms — below that
  it flashes and looks broken.
- **Confirmations**: past tense, not future. "Sent." not "Sending…"
- **Destructive actions**: state what will happen *and* what won't.
  "This deletes the draft. Published posts stay up."

## RTL/i18n voice

Voice doesn't translate; it re-authors. Hebrew "we" is gendered; Arabic
has four+ politeness registers; Japanese has polite/plain/casual
forms. A Hebrew sentence written from an English source reads translated.
A Hebrew sentence written from the brand's voice, in Hebrew, reads
*right*.

Commission a native-speaker editor per language. Record the specific
language moves in §13: "we use second-person direct (`את`), not formal
third-person"; "numerals always as digits"; "avoid English loan words
where a native word exists (`תהליך`, not `וורקפלאו`)."

## Anti-patterns

- Adjective-only voice sections ("friendly, professional, approachable"
  with no examples).
- Voice described in corporate prose. Write *as* the brand.
- No tone matrix — single tone across all contexts.
- Theoretical say/not-say pairs instead of real ones.
- Translating instead of re-authoring for other languages.
- Using emoji for tone. 🎉 is not a tone dial.
