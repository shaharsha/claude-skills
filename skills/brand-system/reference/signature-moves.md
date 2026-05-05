# The signature-moves interview

The most important thing this skill does. Every brand book that feels
AI-generated fails in the same five ways. The interview in
[templates/signature-interview.md.tmpl](../templates/signature-interview.md.tmpl)
refuses to let the author skip them.

This doc explains *why* each question is load-bearing so you can push back
productively when an author resists.

## Why this matters

The difference between Linear's brand book and a generic SaaS style guide
isn't budget, it's commitment to five specific moves. Without them, you
get a template. With them, you get a brand. Anyone can copy a palette
and a type scale. Nobody can copy a brand's *one invented proper noun*
or *one best-practice it deliberately breaks* — those identify the brand
the way a fingerprint does.

## The five required moves

### 1. One invented proper noun

**Prompt**: *"What is one visual or verbal element your brand calls by
a name no one else uses?"*

**Examples**:
- Agentleh: "voice dot"
- Mailchimp: "Freddie" (the monkey mascot)
- Discord: "Wumpus", "Nitro", "Boost", "Blurple"
- Linear: capitalising "Linear" as a proper noun (that itself is the move)
- Stripe: "ingredients" (their design-token tier)

A brand with no invented proper noun has no landmarks — everything is a
generic nav/button/card/footer. Proper nouns create *place* in a brand
universe. They're also what teams use in Slack ("wrap it in a voice
dot") — vocabulary is infrastructure.

**Anti-pattern**: describing the accent with generic terms ("call-to-action
orange"). That's a property, not a name.

**Where it lives**: §2 of BRAND.md. If §2 can't list 8 use-sites for the
primitive, the primitive isn't load-bearing enough. Go back.

### 2. Three falsifiable principles

**Prompt**: *"Name three rules a PR could fail a review against."*

A principle is falsifiable if you can point at a committed feature and
say "this violates the principle." Values are aspirational and can't be
failed.

**Falsifiable**:
- "Hebrew is the default; English is opt-in. A feature QA'd only in
  English is wrong." (Agentleh)
- "Every CTA has exactly one verb." (some teams)
- "No gradient on a button." (a real team's real rule)

**Not falsifiable**:
- "We are human." — what's not human?
- "We value simplicity." — simpler than what?
- "We are customer-obsessed." — a mood

**Where it lives**: §3 of BRAND.md.

### 3. Three don'ts from real past mistakes

**Prompt**: *"What are three design decisions your team has shipped and
now regrets?"*

Hypothetical don'ts ("don't stretch the logo") are table stakes —
template-generators can produce them. Real don'ts come from receipts.

**Real**:
- "Don't tint icons terracotta — terracotta is reserved for the voice-dot
  system. We shipped a month of accidental-terracotta icons and people
  stopped noticing the accent." (Agentleh)
- "Don't use the rainbow avatars on a customer-facing surface — they
  survived from an internal admin panel and shipped once; it looked like
  a different product." (a real team)

**Not real**:
- "Don't stretch the logo." — everyone says this; no one ships it.
- "Don't use Comic Sans." — not a real risk.

**Where it lives**: §16 of BRAND.md.

### 4. A 150-word voice sample written AS the brand

**Prompt**: *"Pick one concrete surface — a welcome email, a 404 page,
a cancellation confirmation — and write it in the brand's actual voice.
No descriptions of the voice; the text itself is the voice."*

Mailchimp's insight: write the brand book *in* the brand's voice, not
*about* it. If the voice chapter describes warmth in professional
corporate prose, the brand has no voice yet.

**Where it lives**: §13 of BRAND.md, as the lead paragraph. No
adjectives-only voice descriptions.

### 5. One best-practice you deliberately break

**Prompt**: *"What brand-book rule does your brand deliberately break,
and why?"*

Every real brand book has one thing a template-generator would never
recommend. It's what separates intentionality from convention.

**Examples**:
- Linear: two-colour palette only (breaks "document ≥5 neutral steps")
- Stripe: gradients labelled by emotion, not by brand name (breaks "keep
  brand language literal")
- Agentleh: paper grain at 2% everywhere (breaks "flat design ships
  faster")
- Vercel Geist: black-on-white with almost no accent colour (breaks
  "commit to a palette")

A brand-book with zero broken rules is probably a template.

**Where it lives**: §3 of BRAND.md, final bullet.

## How to use this reference

When a user says "let's write a brand book," don't rush them into
colour picking. First:

1. Open [templates/signature-interview.md.tmpl](../templates/signature-interview.md.tmpl).
2. Fill in every question. Pause on the 150-word voice passage; that's
   the slowest one and the one most likely to be skipped.
3. Only *then* run `scripts/new-brand-book.sh` with the interview answers
   as flags.
4. After scaffolding, `scripts/audit-outline.py` will warn if §2 has <8
   use-sites, §3 has <3 moves, or §14 lacks a contrast matrix.

If the user resists the interview ("can we just start with a palette?"),
gently surface the EasyPlant vs Linear comparison: EasyPlant has a
beautiful Figma file and no brand; Linear has a two-line rule and a
whole identity. The difference is this interview.
