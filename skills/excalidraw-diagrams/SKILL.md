---
name: excalidraw-diagrams
description: Use when creating, editing, or updating any Excalidraw scene, diagram, flowchart, architecture/system diagram, mind map, wireframe, timeline, or slide deck through the Excalidraw+ MCP — whenever the user says "excalidraw", "draw a diagram", "make a flowchart/architecture diagram", "put this on a canvas", or wants recognizable tech/logo icons (Postgres, React, Docker, AWS…) in a diagram. Covers the MCP workflow, element format, layout/centering/alignment, real library icons, and the MCP quirks that silently break diagrams (invisible text, z-order, bindings). Use even for a "simple" diagram — the gotchas bite there too.
---

# Excalidraw diagrams (via the Excalidraw+ MCP)

Build scenes that read as a deliberate **visual argument**, not "boxes with text,"
and get them right the first time by knowing the MCP's non-obvious behaviours up
front. The element JSON here is standard Excalidraw, so it also applies if you ever
generate `.excalidraw` files directly — but this skill targets the hosted
**Excalidraw+ MCP** (shareable scenes, collections), which is the usual case.

## The workflow

1. **Plan the structure first** (see `reference/layout.md`). Pick the family
   (workflow / architecture / timeline / hierarchy / comparison / cycle / slides),
   the reading direction, and the regions — *before* placing anything. The test:
   if you deleted every label, would the layout alone still convey the idea?
2. **Call `read_excalidraw_format` once** before your first write this session. It's
   the MCP's own normative element guide (occasionally updated) and the server
   expects it. `reference/elements.md` is your fast working subset.
3. **Create or target a scene.** New: `create_scene` (needs a `collectionId` — get
   it from `list_collections`). Existing: find it via `list_scenes` /
   `get_workspace`; to edit an earlier one, get real element IDs with
   `search_scene_content`. The shareable link is
   `https://app.excalidraw.com/s/<workspace_id>/<scene_id>` — both IDs come back in
   the `create_scene` metadata (`workspace` and `id`); give this link to the user.
4. **Add content** with `edit_scene_content` — one coherent diagram per call.
   Build in placement order: regions/frames → containers → primary nodes →
   secondary nodes → labels → arrows (bound, once nodes are stable) → accents.
5. **Add icons** where they help (`reference/library-icons.md` + the bundled
   script) — real Postgres/React/Docker/AWS icons, inserted via the MCP.
6. **Verify — this is mandatory, not optional (see "Verifying" below).** Screenshot
   for layout, `search_scene_content` for text/geometry, fix, repeat.

## Non-negotiables (each one silently ruins a diagram)

These are the traps that make a diagram look broken or fall apart on the next edit.
Full explanations in `reference/mcp-gotchas.md` — internalize these five:

- **Screenshots don't render text.** A screenshot that looks "empty" usually has all
  its labels. Never judge text presence/content from a screenshot — use
  `search_scene_content`.
- **New elements can land *under* existing fills** (the server assigns indices
  non-monotonically, even on a fresh delete-free build). Icons placed on cards, or
  cards placed in a box, can render invisibly under the opaque fill — often
  *inconsistently* (some show, some don't). **Simplest robust fix: give grouping
  containers AND cards `backgroundColor:"transparent"`** (keep the coloured border) —
  a transparent fill can never occlude, so z-order stops mattering for content inside
  a box, and a white card on a white canvas looked identical anyway. Only fall back to
  an explicit high `index` (read the current max via `search_scene_content`, don't
  trust a literal like `"b01"`) when you need one *opaque* element atop another. See
  `reference/mcp-gotchas.md`.
- **`textAlign:"center"` makes the `x` you pass the CENTER** of a standalone label
  (not the left edge). To center under a node at center X, pass `x: X`.
- **Bound labels are always vertically centered** in their shape. For an
  icon-above-label block, use a *standalone* label positioned yourself, not a bound
  `label`.
- **Arrows pointing at shapes must be bound** (`startBinding`/`endBinding`, mode
  `"inside"`), or they detach on the next edit. A **bound arrow label** (`label:{}`) is
  created only at `add` time — adding one via `update` silently no-ops (`added:0`), so
  re-add an arrow to (re)label it, and read the label as the arrow's `labelText` (it's
  invisible to a `types:["text"]` search). You can't delete a shape and its bound arrow
  in the same call — delete the arrow first.

## Verifying (do not claim done without this)

A green `edit_scene_content` result is not verification. After building:
1. `take_screenshot` → check layout, spacing, overlap, arrow routing, colour, icon
   shapes. (Not text — it won't render.)
2. `search_scene_content` → confirm every label exists with the right `text`, and
   that positions/alignment are what you intended (e.g. equal top/bottom margins for
   a centered block; shared `y` across a row).
3. Fix and re-verify until both pass. Typical: 2–4 iterations.

## Centering, alignment & icons — the fiddly parts

The bundled script does the error-prone math and the icon extraction. Run it from
the skill directory:

```bash
# centering: where to put an icon + standalone label as one centered block in a box
python scripts/excalidraw_tools.py place --box X Y W H --icon-h H --font F

# find an icon pack, list its items, extract one positioned icon as add-JSON
python scripts/excalidraw_tools.py catalog <keyword>
python scripts/excalidraw_tools.py list <author/name.excalidrawlib>
python scripts/excalidraw_tools.py icon <lib> --item <idx|name> --at <cx> <top_y> --height <h> [--swap OLD=NEW]
```

`place` and `icon` both take `--at` as **center-x, top-y** (not the box's top-left
`x,y`) — feed `icon --at` the exact `center_x`/`top_y` that `place` printed.

Row/column alignment is just shared `y`+`height` (row) or `x`+`width` (column) with
a constant step — keeping those exact is what separates intentional from
hand-nudged. Details and the reasoning in `reference/layout.md`.

## Reference map

Read the file that matches the task; don't load them all up front.

- `reference/mcp-gotchas.md` — the MCP quirks above, in full. **Read before any real
  scene work** — these cause the most wasted time.
- `reference/elements.md` — element fields, fonts, semantic color palette, arrow
  bindings, frames/slides, charts. Your working reference while building.
- `reference/layout.md` — planning, spacing, centering/alignment math, and which
  structure to choose for a given idea (with a decision table).
- `reference/library-icons.md` — finding and inserting real community icons via the
  MCP; identifying unnamed icons; recommended packs.
- `scripts/excalidraw_tools.py` — `catalog` / `list` / `icon` / `place`. Run
  `--help` for any subcommand.

## Professional vs hand-drawn

Excalidraw defaults to a hand-drawn look (`roughness:1`, Excalifont). For clean,
technical diagrams set `roughness:0`, use `fontFamily:8` (mono) or `7` (titles),
and lean on gray/blue with one accent. For approachable/whiteboard diagrams, keep
the defaults. Match the register to the audience.
