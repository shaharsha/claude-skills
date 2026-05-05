# Exemplar brand books + design systems

Ten references for §15 "Reference set" of a new BRAND.md. Each entry:
URL, one-line value, what to steal, what to *not* copy.

## 1. IBM Carbon — [carbondesignsystem.com](https://carbondesignsystem.com/)

**One-line**: The most complete enterprise design system — tokens,
components, icons, accessibility, content, governance, all in one place.

**Steal**: Per-component pages with purpose / anatomy / content /
accessibility / code, all first-class peers. The contribution model.
The token tiering pedagogy.

**Don't**: Enterprise maximalism — most products don't need 80 components
in v1.

## 2. Shopify Polaris — [polaris.shopify.com](https://polaris.shopify.com/)

**One-line**: Best per-component usage guidance; every component has
purpose + anatomy + content + a11y + code.

**Steal**: The "content guidelines" section on every component. The
four-states documentation (default/loading/empty/error) on surfaces.

**Don't**: Shopify's commerce-specific primitives (Checkout, Cart).
They're the product, not the system.

## 3. Atlassian Design System — [atlassian.design](https://atlassian.design/)

**One-line**: Tokens and accessibility lead; everything else is bodywork.

**Steal**: The chapter order (Tokens first, then Accessibility, then
Content, then Foundations). First-class content-design as a peer to
tokens. "Reject infinite flexibility" as an explicit anti-principle.

**Don't**: The enterprise bias. Atlassian ships a system; brand-first
products have a brand *with* a system.

## 4. Material 3 — [m3.material.io](https://m3.material.io/)

**One-line**: Dynamic Color and motion physics; reference for colour
sophistication.

**Steal**: The Material Theme Builder pedagogy — how a palette is
derived from a source. The motion-physics thinking. Dynamic Color's
extraction from imagery.

**Don't**: The "floating action button" and Material-specific component
language. It's iconic but reads as Google.

## 5. GOV.UK Design System — [design-system.service.gov.uk](https://design-system.service.gov.uk/)

Plus [10 principles](https://www.gov.uk/guidance/government-design-principles).

**One-line**: Best principles document in tech; every principle is a
refusal, not a slogan.

**Steal**: "Do less." "Make things open, it makes things better." Short,
falsifiable, load-bearing. The separation of Components (primitives)
and Patterns (task flows).

**Don't**: The aesthetic — deliberately neutral and accessibility-first.
A brand-product needs presence.

## 6. Mailchimp Content Style Guide — [styleguide.mailchimp.com](https://styleguide.mailchimp.com/)

**One-line**: The reference for voice-vs-tone, written *in* the brand's
voice.

**Steal**: The reader-emotional-state tone matrix. "Writing About People"
as a dedicated chapter. The chapter's own prose written AS the brand —
the book is an instance of the brand it documents.

**Don't**: The Freddie mascot. You can't have Freddie. That's Mailchimp's.

## 7. Vercel Geist — [vercel.com/geist](https://vercel.com/geist)

**One-line**: Minimalism with a point of view; proves "fewer decisions,
more absolute" scales.

**Steal**: Typography-first restraint. Black-on-white with almost no
accent colour — the brand lives in the spacing, not the palette.
Component alphabetical ordering.

**Don't**: Copying Geist's aesthetic makes you look like a Vercel
user, not your own brand. The restraint is the lesson; the specifics
are Vercel's.

## 8. Linear Method — [linear.app/method](https://linear.app/method)

**One-line**: Not a brand book — a *product philosophy*. Shows how
brand emerges from opinionated product decisions.

**Steal**: "Linear" as a proper noun always capitalised (the kind of
tiny naming rule that telegraphs the whole brand). "Quality over
quantity" as a falsifiable product principle. Two-colour palette
(violates the "document ≥5 neutral steps" template).

**Don't**: Linear's specific product shape. The Method works *because*
Linear is Linear.

## 9. Stripe Brand — [brand.stripe.com](https://brand.stripe.com/) + [legal/marks](https://stripe.com/legal/marks)

**One-line**: Trademark rigor + "mark as sentence" voice; brand-as-
product-discipline.

**Steal**: Gradients labelled by emotion ("optimistic", "technical",
"human") instead of by hex. The `/legal/marks` page as an example of
trademark clarity. Product-as-marketing — the brand is shown, not told.

**Don't**: Stripe's restraint demands budget; a small team can't
maintain this level of polish.

## 10. Uber Base — [base.uber.com](https://base.uber.com/)

**One-line**: Typography principles and one of the deepest public a11y
sections.

**Steal**: "Go Big / Less is More / Simple Semantics" — the clearest
published typography principles. The [accessibility section](https://base.uber.com/6d2425e9f/p/876899-accessib).
Composition as a first-class primitive (most systems bury it in
"spacing").

**Don't**: Uber's globality — you don't need 100 languages supported on
day one.

## Bonus references

- **Alla Kholmatova — *Design Systems***: [designsystemsbook.com](https://designsystemsbook.com/) — the functional vs perceptual patterns split is still the best mental model after a decade.
- **Brad Frost — *Atomic Design***: [atomicdesign.bradfrost.com](https://atomicdesign.bradfrost.com/) — the "living system, not static artifact" frame.
- **Nathan Curtis / EightShapes**: [eightshapes.com](https://eightshapes.com/) — canonical token-naming taxonomy.
- **Workday Canvas — RTL and Bidi**: [canvas.workday.com](https://canvas.workday.com/globalization/rtl-and-bidi/) — best public RTL design-system documentation.
- **Spotify Encore**: [spotify.design](https://spotify.design/article/can-i-get-an-encore-spotifys-design-system-three-years-on) — ships an MCP server for AI agents (2026) so the system is queryable directly.
- **Anthropic brand-guidelines skill**: [github.com/anthropics/skills/tree/main/skills/brand-guidelines](https://github.com/anthropics/skills/tree/main/skills/brand-guidelines) — brand guidelines as an executable Claude skill.

## Anti-references (the shelf you're NOT on)

List 3–5 of these in §15 of BRAND.md. One-line reason each.

- **Linear's neon gradients** — energetic, but doesn't match a
  craft-forward brand.
- **"Dashboard marketing page" SaaS templates** — generic B2B-ish
  startup sites with hero-features-pricing-testimonials. Ubiquitous.
- **Framer-template sites** — beautiful, but signal "I shipped fast" not
  "we considered this."
- **Lottie-heavy Webflow showcases** — animated everywhere; signals
  "modern" but reads as noise.
- **Any AI product branding with robots or circuits** — "powered by AI"
  visual language. Tells people the thing is a machine; great brands
  make the machine fade and the value lead.

## Using this file in §15

Copy 5–8 exemplars and 3–5 anti-references into BRAND.md §15 with
one-line reasons each. Don't list all 10 here — pick the ones that
actually relate to your brand's positioning. For a marketing-first
product, Mailchimp + Stripe + Vercel may belong; for a dev tool,
Linear + Geist + GOV.UK may make more sense.

The exemplar list should feel *curated*, not comprehensive.
