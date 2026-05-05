# Narrative frameworks — operationalized for image-as-slide decks

The single biggest determinant of whether a deck lands is whether it has a narrative arc. AI deck generators that skip this step produce flat "title + 5 bullets × 8 slides" output that audiences forget within minutes. Use this doc when writing `deck-plan.json` in Phase 2.

You will not use all of these on every deck. Pick the spine that best matches the deck type and run it through.

---

## SCQA — McKinsey's narrative spine

Best for: business cases, briefings, decision decks, anything where the audience needs to be moved from current understanding to a recommendation.

```
Situation → Complication → Question → Answer
```

- **Situation**: state of the world the audience already accepts. Don't argue it. Establish baseline.
- **Complication**: the trigger or new fact that breaks the baseline. This is where tension begins.
- **Question**: the natural question the audience now asks. Often unsaid, but everyone is thinking it.
- **Answer**: your main idea, the recommendation, the resolution.

Map to slides: 1 slide for Situation, 1-2 for Complication, the Question is implicit (usually no slide of its own — the slide *after* the complication is where the audience is asking it), then 4-7 for Answer (your evidence + recommendation), and a closing/CTA.

**Why it works for AI**: SCQA is sequential and formulaic. Each step has a single purpose. Easy to map to slide roles: Situation → `problem` slides describing baseline, Complication → `data` or `story` showing the rupture, Answer → `takeaway` and `data` slides.

---

## The Pyramid Principle (Minto)

Best for: any deck where the audience is time-poor and could leave at any moment. C-suite, investor, board.

```
                   [main idea]
                        |
        +---------------+---------------+
        |               |               |
   [supporting]    [supporting]    [supporting]
        |               |               |
   [evidence]      [evidence]      [evidence]
```

Lead with the conclusion. Stack supporting points. Each supporting point has its own evidence underneath. The audience can leave after any layer and still have the most important version.

Map to slides: Slide 1 (after title) is the takeaway. Slides 2-4 are the three supporting points. Slides 5-9 are evidence for each. Slide 10 is the call to action.

**When to choose Pyramid over SCQA**: when you suspect the audience won't sit through a 30-minute build. Pyramid front-loads.

---

## Duarte's "What is / what could be" oscillation

Best for: vision decks, product pitches, anything where you need the audience to *feel* the gap between today and the future you're proposing.

```
What is  →  What could be  →  What is  →  What could be  →  What is  →  What could be  →  New normal
```

Each oscillation is 1-2 slides. The contrast itself creates emotional tension. End on "new normal" — the world after your idea is realized.

Map to slides: even-numbered slides are "what is" (current pain, baseline, status quo). Odd-numbered slides are "what could be" (vision, alternative, your proposal). End with one or two "new normal" slides showing the resolved future.

**S.T.A.R. moment** ("Something They'll Always Remember"): once per deck, plant a single image, statistic, or comparison so striking the audience will repeat it after they leave. Identify it in your deck plan. Don't bury it in slide 4 — put it where it has the most weight, usually the takeaway slide or its prelude.

---

## Kawasaki's 10/20/30 — operational constraint

```
10 slides max
20 minutes total
30pt font minimum
```

Use this as a sanity check, not as a literal rule. Adjust:

- **5-7 slides** for a tight 10-minute brief
- **8-10 slides** for a normal 20-30 minute meeting
- **11-15 slides** for an extended 45-minute session
- **>15 slides** only if the user explicitly asks for it

For image-only decks, the 30pt rule translates to: any text overlay must read at audience distance. We accomplish this by limiting overlays to 6-8 words and by rendering them at high resolution within the image.

---

## Choosing your spine — quick decision tree

```
Is this a recommendation or decision deck?
  YES → SCQA
  NO  ↓

Is the audience C-suite or investor (impatient)?
  YES → Pyramid Principle
  NO  ↓

Is this a vision / pitch / change-management deck?
  YES → Duarte oscillation
  NO  ↓

Default: SCQA, with one Duarte-style "what could be" moment as the takeaway slide.
```

---

## NotebookLM-derived rules (apply on top of the spine)

Distilled from observing how Google's NotebookLM Video Overviews handle storytelling. These transfer directly to static decks:

1. **One idea per slide.** If you can't state the slide's single takeaway in a sentence, the slide is doing too much. Split or cut.
2. **Sequence as Setup → Tension → Resolution → Takeaway** within each section. Don't lay out facts side-by-side; let each fact create the question that the next slide answers.
3. **Open with a question, not a topic.** "What if onboarding is the product?" lands harder than "Onboarding considerations."
4. **Pull one quote, number, or artifact from your sources per slide and let it breathe.** Don't crowd. Big single thing > small many things.
5. **Speaker notes carry the verbal weight.** 40-60 words of narration per slide. The image carries the visual; the speaker carries the argument. Together they are denser than bullets, never redundant.
6. **Visual style locks from frame one.** Never switch aesthetics mid-deck. The deck is one artifact, not a stitched-together compilation.

---

## How this plays out in `deck-plan.json`

Pick a spine. Fill in `narrative_arc` (SCQA fields are optional but help you stay honest). Then design the slide sequence so each `role` advances the spine:

- SCQA pitch deck (10 slides): `title, problem (situation), problem (complication), data (rupture moment), takeaway (your answer), story (proof point), data (evidence), comparison (old vs new), takeaway (synthesis), cta`
- Pyramid investor brief (8 slides): `title, takeaway (lead with the conclusion), data (supporting 1), data (supporting 2), data (supporting 3), story (vivid example), takeaway (synthesis), cta`
- Duarte vision deck (10 slides): `title, problem (what is), takeaway (what could be), data (what is), story (what could be), comparison (what is vs what could be), data (what is — the cost of inaction), takeaway (new normal), cta, closing`

Mix and match. The roles in the schema (`title | agenda | section | problem | data | story | comparison | quote | takeaway | cta | closing`) are descriptive, not prescriptive.
