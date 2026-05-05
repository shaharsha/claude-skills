# Consistency tactics — making 8-12 independent generations look like one deck

The hardest problem in image-as-slide deck generation is **drift**: each slide is a separate API call, and small differences accumulate (palette shifts a hue, motif weight changes, typography looks slightly different). After 10 slides the deck feels patchwork.

Here are the levers that prevent drift, in priority order.

## 1. Style reference image (the strongest lever)

Generate 1-2 abstract reference frames from the deck's `style_brief` alone, before any content slides. Pass the chosen reference as `--ref` to *every* slide generation. gpt-image-2 uses references at high fidelity through the `/v1/images/edits` endpoint.

This is what `lock-style.py` does. The reference encodes:

- The exact palette (hex values get baked into pixel colors the model can sample)
- The decorative motif (whatever shape, weight, color, and placement the ref has, subsequent slides will echo)
- The general aesthetic register (dark UI infographic vs editorial photo vs hand-drawn)
- Typography vibe (the model picks similar letterforms across slides)

Without a style reference, the deck will drift even with a great `style_brief`. *With* one, every slide passes through the same visual filter.

**Tactic**: when picking which of the two refs to lock as `style_ref`, pick the one whose palette and motif are most *unambiguous*. A subtler reference gives the model more latitude to drift; a bolder one constrains it harder.

## 2. The `style_brief` is appended to every prompt

`generate-deck.py` automatically appends the deck plan's `style_brief` to every per-slide `image_prompt`. So you write the brief once and it's there for all 10 calls.

This combined with the style reference is the consistency floor. See [visual-style-brief.md](visual-style-brief.md) for how to write one that does work.

## 3. Color names by role, not hex per slide

In per-slide prompts, refer to colors by *role* ("headline in [accent], body in white") not by hex code. The hex codes live in `style_brief` and propagate. This prevents per-slide drift if you accidentally specify a slightly different shade in slide 7's prompt.

## 4. Repeat the motif language across slides

Every per-slide `image_prompt` should end with a one-line callback to the motif. The example deck does this with "Faint dotted background lines" or "Faint background dots and curves" at the end of most slides. The repetition reminds the model to render the motif on each frame.

## 5. Explicitly include in `style_brief` what NEVER changes

The strongest constraints are exclusions:

- "Never use white or light backgrounds." → forces dark mode across all slides.
- "Never use serif typography." → forces sans-serif across all slides.
- "Never include 3D shading or gradients." → forces flat aesthetic.

A well-placed exclusion does more than three positive constraints.

## 6. Composition variety actually helps consistency feel intentional

Counterintuitively: if every slide uses a *different* composition (split, cards, flowchart, big-number, photo) but they all share palette + motif + typography, the deck feels *more* unified than if every slide is the same composition with slight palette drift. The audience reads "this is one deck because the palette is everywhere" — not "this is one deck because every slide is the same template."

This is why NotebookLM Cinematic Video Overviews feel cohesive despite varying frame compositions: the style locks, the composition varies, and the eye accepts that as intentional.

## 7. Sequence-aware prompt nudges

For decks where flow matters (e.g., a step-by-step explainer where slides 4-7 are all process diagrams):

- Add a line in those slides' prompts like "consistent with the previous slide's diagram style — same connector weight, same node treatment, same arrow style".
- gpt-image-2 doesn't actually see the previous slide unless you pass it as `--ref`, but the language constrains the model's choices toward what would naturally match.

For maximum consistency in a process-diagram sequence, regenerate the whole sequence with a prior slide's PNG as `--ref` for the next:

```bash
# Hand-roll for a tightly-coupled sequence
~/.claude/skills/image-generation/scripts/openai-image.sh \
  --prompt "..." --output slides/slide-04.png \
  --ref refs/style-ref-1.png --ref slides/slide-03.png
```

But for normal use, `style_ref` alone is sufficient.

## 8. When drift is unavoidable: regenerate the worst-fitting slide

After Phase 5 visual QA, if 1-2 slides drift, regenerate just those — same `style_ref`, refined prompt. The other slides stay locked. You don't have to redo the whole deck.

## 9. Hand-tuning the brief based on first generation

Sometimes you only learn the brief is loose by seeing the first deck. If three slides all have slightly different shades of "dark blue" instead of the locked navy:

- Tighten the brief: add "Use exactly hex #1A1F2E for the dark background — no other dark blues."
- Regenerate all slides. Faster than touching them up individually.

## 10. Reference-image consistency for portraits / specific people

If a deck includes the same person across multiple slides (e.g., a founder's headshot appearing on intro and closing), pass the headshot PNG as `--ref` to both slides. gpt-image-2's `/edits` endpoint preserves face identity across calls.

For decks with multiple recurring characters, switch those slides to `model: gemini` — Gemini Pro accepts up to 14 reference images and is purpose-built for character lock.

---

## The hierarchy in one paragraph

The `style_ref` image is the strongest lever — pixels constrain pixels. The `style_brief` paragraph is the second strongest — it's appended to every prompt and tells the model what role each color plays. Per-slide prompts should refer to colors by role, repeat the motif language, and never re-specify what's already in the brief. After 8-10 slides, this combination produces deck cohesion that reads as intentional design rather than AI patchwork.
