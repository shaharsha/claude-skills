# Motion

## Principle: static by default

Motion serves exactly two jobs: **confirming a user action** (150–250ms)
or **embodying the signature primitive** (the one signature animation).
Everything else is off.

Specifically banned:

- Parallax (any kind)
- Scroll-jacked reveals
- `whileInView` fade-ups on every section
- Framer-Motion card staggers
- 3D hover-tilts
- Lottie everywhere
- Animated icons in UI chrome
- Loading spinners where a signature-primitive pulse works

If motion exists to "look modern," it's wrong.

## Tokens

```css
--ease-out:      cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out:   cubic-bezier(0.65, 0, 0.35, 1);
--duration-fast: 150ms;   /* hover, focus, small state changes */
--duration-base: 200ms;   /* dropdowns, tooltips */
--duration-slow: 320ms;   /* modals, sheets */
```

Use sparingly. A well-tuned `--ease-out` at 150ms on hover is the
default; scripted motion is the exception.

## The signature animation

Every brand should have exactly one animation that carries the
primitive. Not three. One.

```css
@keyframes signature-pulse {
  0%, 100% { transform: scale(1);    opacity: 1; }
  50%      { transform: scale(0.92); opacity: 0.85; }
}
.{signature-primitive-class} {
  animation: signature-pulse 1.8s var(--ease-in-out) infinite;
}
```

**Where it fires** (examples from Agentleh's voice-dot):

- Inside the mark on landing-hero first paint
- "Agent typing" indicator in the app
- Loading state on any agent-action button
- The cursor dot on hover (desktop, optional)
- The period in standalone prices (`₪249/month.`)

**Where it never fires**:

- Nav, footer, legal chrome
- Decorative marks
- More than once per screen-fold

## Page-load reveal

Allowed once, at first paint. Background fades from `--void` (or the
darker surface) to `--bg` over 600ms `--ease-out`. Type and signature
primitive arrive at 300ms in. One moment where the palette tells its
story.

```css
.page-reveal {
  animation: reveal 600ms var(--ease-out);
}
@keyframes reveal {
  from { background: var(--void); opacity: 0.85; }
  to   { background: var(--bg);  opacity: 1; }
}
```

Never on subsequent navigation within a session.

## Optional: Liquid Glass specular shift

On `.glass` surfaces (§10), the inner specular highlight can shift in
response to cursor proximity — up to 4° of shift, 300ms damped, desktop
only (`@media (pointer: fine)`). This is Apple's published Liquid Glass
behaviour. Gated on `prefers-reduced-motion`.

## Reduced motion

Non-optional. Every animation and transition is gated:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Signature pulse**: stops entirely.
**Hero wash**: stays (it's static when not animating anyway).
**Page-load reveal**: disappears.
**Cursor dot**: still follows the cursor but stops pulsing. Don't ever
disable the cursor — leaving a user cursorless is an accessibility
regression.

## Motion and the brand's dark-mode narrative

If dark mode has a narrative (Agentleh's "the agent works overnight"),
motion can support it. The signature pulse might be 10% dimmer in dark
mode, for example. Subtle, not showy.

## Anti-patterns

- Framer-Motion card-staggered fade-ups on every landing section.
- Scroll-triggered "reveal" animations.
- Multiple distinct animations (three spinners, four loaders, two
  transitions — pick one signature animation).
- Forgetting `prefers-reduced-motion`.
- Animating the mark in nav/footer chrome.
- Motion as decoration rather than feedback.
- Parallax of any kind.
- Hover-tilt 3D cards.
- Loading spinners where a signature-primitive pulse would work
  (spinners look like every other product).
