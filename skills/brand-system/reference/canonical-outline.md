# Canonical 20-section outline

Per-chapter must-haves for `BRAND.md`. Use this as a checklist when
drafting each section. `scripts/audit-outline.py` validates presence
of sections 0–20; content quality is a judgment call that this doc
guides.

## §0. The idea

One sentence. The brand's single load-bearing decision. Must pass the
"strip everything else" test — if you removed the mark and all chrome,
would something still say *this is us*?

**Bad**: "{{PRODUCT}} delivers innovative AI solutions."
**Good**: "A real worker who lives inside WhatsApp."

## §1. Reading the mark

3–5 simultaneous readings the mark supports. The Pentagram/FedEx-arrow
move: one restrained design doing multiple jobs.

Plus **construction notes** — stroke weight, asymmetry, counter
geometry — that explain *why the mark looks the way it does* so it
survives future redraws.

## §2. Signature primitive

The one semantic token that appears across every surface. Not
decoration — a *primitive*. Must list ≥8 use-sites (auditor enforces).
See [signature-moves.md](signature-moves.md).

Also list ≥3 places it **never appears** — constraints create meaning.

## §3. Signature moves

5–7 things that identify the brand without the logo. Committed, not
aspirational. Final bullet: the one best-practice the brand deliberately
breaks.

## §4. Brand essence

Under 8 bullet-equivalents. "What we are / are not / tone / positioning
sentence." Short. If this section is more than ~8 pages of prose, it's
marketing fluff.

## §5. Logo system

Variants table (icon/wordmark × light/dark), clear space, min size,
don'ts. **Include the full favicon + PWA pack spec** per
[favicon-pack.md](favicon-pack.md) — this is a load-bearing section
most brand books skip. Also include theme-color meta tags and the
system-aware SVG favicon pattern.

## §6. Colour system

See [color.md](color.md). Three tiers (primitive / semantic / component)
per [tokens.md](tokens.md). The 62/30/8 rule. The accent-is-constant-across-themes
rule. The colour story (where the palette comes from; *not* a vibe).

## §7. Typography

See [typography.md](typography.md). Face + rationale, type scale with
semantic roles (mega / display / h1–h3 / lead / body / ui / micro),
measure (45–75ch), tabular nums, RTL moves per [rtl.md](rtl.md).

## §8. Iconography

Style, colour rules (the accent is never used on icons — it's reserved
for the signature primitive), size tokens, RTL flipping policy.

## §9. Spacing & layout

8-point grid, container widths (narrow / default / wide), radii ladder
with concentric-radii rule. Density note: marketing pages and dashboards
use different scales; call out which.

## §10. Surfaces & materials

See [surfaces.md](surfaces.md). Default material + floating material.
Grain overlay if any. Hero backgrounds.

## §11. Motion

See [motion.md](motion.md). Principle (static by default), ease /
duration tokens, the one signature animation, reduced-motion policy.

## §12. Imagery & illustration

Photography rules (natural vs studio, subject, cultural context, never
AI humans in production). Illustration style. Anti-patterns.

## §13. Voice & tone

See [voice-and-tone.md](voice-and-tone.md). Must start with the 150-word
voice sample written AS the brand, not about it. Include the tone matrix
by reader emotional state (Mailchimp's move).

## §14. Accessibility

See [accessibility.md](accessibility.md). WCAG 2.2 AA contrast matrix
(from `scripts/audit-contrast.py`), focus rings, reduced motion, forced
colors, RTL equivalence, target size 24×24.

## §15. Reference set

5–8 brands you admire with one-line reasons; 3–5 anti-references with
one-line reasons. "What shelf the brand sits on." See
[exemplars.md](exemplars.md) for the shelves we've already catalogued.

## §16. Anti-patterns

Specific don'ts — concrete visual bad habits banned. Include the three
real don'ts from the signature interview (§16 is the home for them).

## §17. Implementation — Tailwind v4 `@theme`

See [tailwind-v4.md](tailwind-v4.md). Full `@theme` block, `:root`
light-mode semantics, `[data-theme="dark"]` overrides. The accent is
constant; only surface/text tokens swap.

## §18. Components

Opinionated copy-paste primitives. Per component: document all four
states (default, loading, empty, error). Kholmatova's functional-patterns
move. Covers buttons, links, inputs, cards, badges, nav, alerts,
dialogs, menus, prose, landing primitives.

## §19. Migration plan

What's being retired. ✅/⚠️/❌ status per token/pattern. Dates. Ships
incrementally, not as a big bang.

## §20. What this document is not + Decision log

Explicit non-goals — and the dated table of decisions with one-line
rationale each. The decision log is what makes this document *durable*;
without it, future-you can't tell which rules are load-bearing.

## The optional Governance section (§19.5)

For teams/projects with multiple contributors:

- **Ownership**: who maintains the book
- **Contribution model**: request → review → design → build → document → release
- **Release cadence**: monthly minor, quarterly major
- **Adoption metrics**: component coverage %, exception log, time-to-component

Skip for solo projects. Add if the design system crosses team boundaries.
