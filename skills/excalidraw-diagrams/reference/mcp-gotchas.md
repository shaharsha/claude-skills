# Excalidraw MCP gotchas

Behaviours of the Excalidraw+ MCP that will burn you if you don't know them. Each
was hit for real. The MCP's own `read_excalidraw_format` guide does **not** cover
these — they're about the *tool*, not the element format.

## Contents
- Screenshots don't render text
- Z-order: new elements land in index gaps, not on top
- `textAlign:"center"` makes x the CENTER anchor
- Bound labels are always vertically centered
- Bound arrow labels: created only at `add` time, and invisible to text search
- Can't delete a shape and its bound arrow in one call
- Verify with `search_scene_content`, not just the screenshot
- Verify element IDs before binding or updating (don't trust transcribed IDs)
- Add-payload hygiene (no id, tempId only within one call)
- Deleting temp scenes

## Screenshots don't render text

`take_screenshot` renders shapes, fills, arrows, and icons faithfully — but **not
text**: standalone text and shape labels come back blank or as faint boxes. A
screenshot that "looks empty" often has all its labels present and correct.

**Never conclude text is missing/wrong from a screenshot.** Verify text with
`search_scene_content` (returns each text element's `text`, `x`, `y`, `fontSize`,
and each shape's `labelText`). Use the screenshot for layout, spacing, overlap,
arrow routing, colour, and icon shape — the things it *does* show.

**Thin line-icons also vanish at low render width.** A full-scene screenshot
downscaled to `maxWidth` ~800–1000 can drop small thin-stroke icons entirely — you'll
swear an icon is missing when it renders fine. Before concluding an icon is absent,
re-shoot at higher `maxWidth` (up to 1920) or crop to the region: wrap it in a
temporary `frame`, `take_screenshot` with that `frameId`, then delete the frame.

## Z-order: new elements land in index gaps, not on top

Excalidraw orders elements by a fractional `index` string (`"a0" < "a1" < …`). When
you `add` elements, the server assigns indices **non-monotonically** — not strictly
append-order. It does **not** guarantee new elements go on top. A standalone label or
icon added *after* a solid-filled rectangle can be slotted *below* it and render
invisibly (and the screenshot won't reveal it, because screenshots don't render
text — double whammy).

**This bites on a FRESH, delete-free build, not just after edits.** Across a
multi-call build the server distributes indices such that a later `add` (e.g. the
icons you place on top of cards, or the cards you place inside an account box) can
land *under* an earlier-added container/card **fill**. Symptom seen in practice:
build all the container boxes, then the cards, then the icons — and half the icons
and some cards are invisible, inconsistently (some show, some don't), because their
index fell below the opaque fill that overlaps them.

**Fix (preferred) — transparent fills on every grouping container AND card.** A
`backgroundColor:"transparent"` shape draws only its border, so it can **never**
occlude anything beneath it, and z-order stops mattering for "content inside a box."
Give account/VPC/subnet frames *and* the individual cards transparent fills (keep the
colored border + a bound/standalone label); icons and captions then always render.
On a white canvas a white card fill was doing nothing visually anyway, so you lose
nothing. This is far more robust than fighting indices element-by-element — reach for
explicit indices only when you genuinely need an *opaque* element to sit on top of
another opaque element.

**Fix (when you truly need an opaque element on top):** pass an explicit `index`
that is **strictly greater than the current maximum index in the scene** — don't use
a fixed literal. As a scene grows the
server's own default indices advance well into `"b0*"`, `"b1*"`, `"c*"`, … so a
hard-coded `"b01"` can still land *below* later elements (this bites in practice: by
~20 elements the default indices already reach `b14`, so `"b01"` renders
underneath). Instead:
1. `search_scene_content` to read back the elements and their `index` values;
2. find the current max index string (plain string comparison — `"b14" > "b0w"`);
3. give your on-top element an index strictly greater. The simplest robust choice is
   a leading char beyond everything present — e.g. `"z00"`, `"z01"`, … when the scene
   only holds `a*`/`b*` indices — otherwise increment past the observed max.

When a label "isn't showing," this is the first suspect — confirm via
`search_scene_content` that the element exists, then `update` (or re-add) it with an
index above the current max.

## `textAlign:"center"` makes x the CENTER anchor

For a standalone `text` element with `"textAlign":"center"`, the server rewrites
`x` to `x − width/2` on insert — i.e. **the x you pass is treated as the horizontal
center**, not the left edge. So to center a label under a box whose center is at
`X`, pass `x: X` (not `X − width/2`).

`update` patches, by contrast, take the raw left-edge x. So the same label needs
`x = center` on add but `x = center − width/2` on a later update. Easy to get
backwards.

## Bound labels are always vertically centered

A `label` on a shape (`{"label":{"text":"…"}}`) is a *bound* text element, and
Excalidraw pins it to the shape's vertical middle. You **cannot** make an
"icon on top, label below, both centered as a unit" layout with a bound label —
the label will sit dead-center and the icon will overlap or float.

**Fix:** for icon-over-label blocks, don't use a bound label. Add the icon and a
**standalone** text element and position both yourself (the `place` subcommand of
`scripts/excalidraw_tools.py` computes the two y-values so the pair is centered as
one block). Use bound labels only when the text alone is centered in the shape.

## Bound arrow labels: created only at `add` time, and invisible to text search

A label on an arrow (`{"label":{"text":"…"}}`) is the clean way to put text *on* a
line — Excalidraw draws it in a **gap** in the line, so it never strikes through. But
two non-obvious rules bite:

- **The label is created only when the arrow is `add`ed — never on `update`.** Passing
  `label` in an `update` to an existing arrow returns `added:0` and silently no-ops;
  the label never appears. To (re)label an existing arrow, **delete it and re-`add` it**
  with the `label` field. (The arrow should also be **bound** to shapes for the label
  to attach cleanly.) Symptom seen in practice: a label kept "vanishing" on every
  update attempt until the arrow was deleted and re-added with the label inline.
- **Bound-label texts do NOT appear in `search_scene_content(types:["text"])`** — they
  carry a `containerId` and come back as the owning arrow's `labelText` instead. A text
  search for the label string returns 0 matches even though the label exists. To
  confirm/read an arrow's label, search `types:["arrow"]` and read `labelText` /
  `boundElements`.

Corollary — labelling a line: a **standalone** text on a line can't reproduce the gap,
so it renders struck-through, and a masking rectangle behind it won't reliably win
z-order (see z-order above). For a label *on* a line, use a bound label; for a label
*near* a busy/overlapping line, place a standalone text in a pocket no line crosses.
When two arrows overlap the same segment, a bound label on one is still struck by the
other's line — draw it as one trunk + a branch (second arrow starts mid-trunk) so only
one line runs under the label.

## Can't delete a shape and its bound arrow in one call

If an arrow is bound to a shape, deleting both in a single `edit_scene_content`
call fails validation: `Bound arrow element … must reference element …`. The delete
pass runs before the bookkeeping settles.

**Fix:** delete the arrow in its own `edit_scene_content` call first, then delete
the shape (or re-parent the arrow) in a second call.

## Verify with `search_scene_content`, not just the screenshot

`search_scene_content` is the source of truth for anything text- or geometry-
related. Use it to:
- confirm a label exists and read its real `text` (screenshots can't).
- read back a shape's `labelText`, `x`, `y`, `width`, `height`, `index`, and
  `boundElements` (arrows/labels attached to it).
- get **real persisted IDs** for `update`/`delete` without dumping the whole scene
  (`get_scene_content` returns everything and is large — prefer search).

Pattern: `edit_scene_content` → `take_screenshot` (layout/shape check) →
`search_scene_content` (text/geometry check) → fix → repeat.

## Verify element IDs before binding or updating (don't trust transcribed IDs)

Across-call `update`/`delete` and arrow `startBinding`/`endBinding` need **real
persisted IDs**. The IDs echoed in an `edit_scene_content` result are easy to
mis-transcribe, and IDs from a scene you **deleted and recreated** are dead. Two
silent-ish failure modes to recognise:

- **`update` returns `updated:0`.** The patch referenced an ID that isn't in the
  scene (stale/typo'd), so nothing changed — no error. If a change "didn't take,"
  check the return count, don't just re-screenshot.
- **Arrow add errors `Unknown tempId reference '<id>'`.** A binding `elementId` that
  the server can't find is treated as an undefined same-call `tempId`. The message
  says "tempId" even when you meant a *persisted* ID — it just means that ID doesn't
  exist. One bad binding aborts the whole `add` (nothing is added).

**Fix:** before a batch of bindings/updates, `search_scene_content` (e.g.
`types:["rectangle"]`, or query a unique label) to read back the **current** IDs +
their `x/y`, and bind/patch against those. Cheaper than a failed multi-element call.

## Add-payload hygiene

- **Never** include `id` in an `add` payload — the server generates it. Sending one
  errors.
- Reference elements you're adding **in the same call** via `tempId` (for
  `frameId`, `containerId`, `startBinding.elementId`, `endBinding.elementId`). A
  `tempId` is single-call scope only; use real IDs across calls.
- Don't reuse a `tempId` twice in one payload.
- Strip server-managed fields when copying elements (from a library, another scene,
  etc.): drop `id`, `seed`, `version`, `versionNonce`, `updated`, `boundElements`,
  `frameId` (unless intentionally set), `index` (unless intentionally set). Keep the
  visual fields. `scripts/excalidraw_tools.py` does this whitelist for library icons.
- Legacy elements use `type:"draw"` (→ use `"freedraw"`) and `fontFamily` `1/2/3`
  (→ use `5` Excalifont / `7` Lilita One / `8` Comic Shanns).

## Deleting temp scenes

When you create a throwaway scene (e.g. to identify unnamed library icons), delete
it with `delete_scene` when done so the user's workspace stays clean. Name it
obviously (`TEMP — … (safe to delete)`) in case cleanup is interrupted.
