# Excalidraw element reference

The vocabulary for `edit_scene_content` add-payloads. This is the fast, practical
subset — the MCP's `read_excalidraw_format` returns the full normative guide, and
you should still call it once per session before your first write (it's the source
of truth and occasionally updated). Use this file to move quickly and to remember
the values that matter.

## Contents
- Common fields (every element)
- Rectangles, ellipses, diamonds
- Text (standalone vs bound label)
- Lines and freedraw
- Arrows and bindings
- Frames (slides / grouping regions)
- Fonts
- Color palette (semantic)
- Charts (built from primitives)

## Common fields

Required on every new element: `type`, `x`, `y`, `width`, `height`. Useful optional
fields (sensible defaults shown):

```json
{
  "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "roundness": {"type": 3}
}
```

- `roughness`: `1` = hand-drawn (default Excalidraw character); `0` = clean/technical.
- `roundness`: `{"type":3}` = rounded corners; omit/`null` for sharp. Don't round charts.
- `strokeStyle`: `"solid" | "dashed" | "dotted"`. Dashed reads as "boundary/logical".
- Coordinates are absolute canvas px. There's no z field you set directly — see the
  index/z-order note in mcp-gotchas.md.

## Rectangles, ellipses, diamonds

Text-bearing content blocks. Use a **`label`** for text that belongs to the shape —
the server creates the bound text and keeps it centered:

```json
{"type":"rectangle","x":100,"y":100,"width":200,"height":90,
 "backgroundColor":"#e7f5ff","strokeColor":"#1971c2","fillStyle":"solid",
 "roundness":{"type":3},"label":{"text":"Client","fontSize":18,"fontFamily":5}}
```

- Rectangles → actions, objects, systems, containers, cards. Prefer rounded.
- Diamonds → **true decisions only**, short text (one question). A bound label
  longer than the diamond is wide is **silently hard-wrapped** by the server (e.g.
  `tests pass?` → two lines) — keep it to a couple of short words, or widen the
  diamond, so the wrap is intentional rather than a surprise.
- Ellipses → start/end states, events, or (with fills) logo blobs. No multiline text.
- Minimum labeled size ≈ 160×85 so text fits with padding.

## Text (standalone vs bound label)

Use a **bound `label`** (above) when text sits inside and centered in a shape.

Use a **standalone `text` element** for titles, subtitles, annotations, captions,
timeline/tree labels, and — importantly — any "icon-above, label-below" block
(bound labels can't do that; see mcp-gotchas.md). Give generous `width`/`height`;
never force wrapping with a narrow box. Use `\n` for intentional breaks.

```json
{"type":"text","x":100,"y":70,"width":480,"height":40,
 "text":"Architecture overview","fontSize":32,"fontFamily":7,"strokeColor":"#1e1e1e"}
```

Two anchor traps (details in mcp-gotchas.md): with `"textAlign":"center"` the `x`
you pass is the **center**; and standalone text can be slotted **under** a filled
shape by z-order unless you pass a high `index`.

## Lines and freedraw

- `line` → timelines, dividers, tree connectors, boundaries, and custom icon
  geometry. `points` are relative to the element's `x,y`: `[[0,0],[16,0]]`.
  A closed `points` ring with a `backgroundColor` renders as a filled polygon.
- `freedraw` → hand-sketched strokes (the legacy `draw` type maps to this).

## Arrows and bindings

An arrow that points at a shape **must** declare bindings, or it detaches on the
next edit (geometry alone is decorative):

```json
{"type":"arrow","x":300,"y":140,"width":90,"height":0,
 "points":[[0,0],[90,0]],"endArrowhead":"arrow",
 "startBinding":{"elementId":"boxA","fixedPoint":[1,0.5],"mode":"inside"},
 "endBinding":{"elementId":"boxB","fixedPoint":[0,0.5],"mode":"inside"}}
```

- `elementId` = a real persisted ID, or a `tempId` of a shape added in the **same**
  call. For shape→shape arrows include **both** bindings.
- `mode`: `"inside"` (default — attach to edge/interior), `"orbit"` (route around),
  `"skip"`. Use `"inside"` unless you specifically want orbit.
- `fixedPoint`: `[0.5,0]` top · `[1,0.5]` right · `[0.5,1]` bottom · `[0,0.5]` left.
- For workflows/swimlanes use **elbow** routing: `points` with horizontal+vertical
  segments only (e.g. `[[0,0],[40,0],[40,120],[80,120]]`), no long diagonals.

## Frames (slides / grouping regions)

A `frame` is a named region; children reference it via `frameId`. **Child
coordinates are absolute canvas coordinates**, not relative to the frame origin.
For a presentation, one frame = one slide (16:9, min 854×480, ~450px apart,
laid left-to-right). Add the frame + its children in one call, giving the frame a
`tempId` and every child `frameId: <tempId>`. Put presenter notes in
`customData.presenterNotes` (bulleted). Build slide content first, wrap in the
frame last.

## Fonts

- `fontFamily: 5` — Excalifont (hand-drawn) — most labels, body, annotations.
- `fontFamily: 7` — Lilita One — titles, section/lane headers, strong hierarchy.
- `fontFamily: 8` — Comic Shanns (mono) — code, API paths, event names, JSON keys,
  identifiers, commands.
- For **professional/technical** diagrams, avoid the hand-drawn look: use
  `fontFamily: 8` (or 7 for titles), `roughness: 0`, and cleaner colors.
- Sizes: body ≥16, headings ≥24, slide titles 36–48, subtitles 22–30, captions 14–16.

## Color palette (semantic)

Darker stroke + lighter pastel fill. Never use the lightest tint for text. Keep to
≤5 semantic colors unless building a taxonomy. `[fill, stroke]` pairs:

| meaning | fill | stroke |
|---|---|---|
| neutral / info | `#f8f9fa` | `#868e96` |
| blue | `#e7f5ff` | `#1971c2` |
| green (success) | `#ebfbee` / `#d3f9d8` | `#2f9e44` |
| yellow | `#fff9db` | `#f08c00` |
| orange (pending) | `#fff4e6` | `#e8590c` |
| red (failure) | `#fff5f5` / `#ffe3e3` | `#e03131` |
| violet | `#f3f0ff` | `#7048e8` |
| teal | `#e6fcf5` | `#0ca678` |
| pink | `#fff0f6` | `#e64980` |

Semantics: green = success/done, amber/orange = pending/processing/retry, red =
failure/blocked, gray or blue-gray = informational. Base technical diagrams in
gray/blue with one accent for the critical path.

## Charts (built from primitives)

No chart element exists — compose from primitives: `rectangle` bars, `line` axes and
grid, connected `line` for line charts, `ellipse` dots, standalone `text` for
labels/legend/title. Rules: always a title (`fontFamily:7`); dark axis labels;
`roughness:0`; **no** `roundness` on bars; light fills + darker strokes; colors map
to categories/series, not decoration; show values when known; label "approx." when
illustrative. Bars from a shared baseline, sorted descending for rankings.
