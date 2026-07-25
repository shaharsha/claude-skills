# excalidraw-diagrams

Build architecture, flow, and system diagrams on an Excalidraw+ canvas through its MCP — with real, recognizable tech and logo icons (Postgres, React, Docker, AWS services…) extracted live from the ~230-pack community catalog, no bundled asset data. Encodes the whole workflow, the element format, the layout and alignment math, and the MCP quirks that silently break a diagram.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Diagram-building through an MCP looks trivial until you hit the failure modes, and every one of them is *silent* — the API returns green and the diagram is wrong.

- **Screenshots don't render text.** A screenshot that looks empty usually has all its labels. Judge text with `search_scene_content`, never with your eyes on a PNG.
- **New elements can land *under* existing fills.** The server assigns fractional z-indices non-monotonically, even on a delete-free fresh build. Icons placed on cards, or cards placed in a box, render invisibly beneath an opaque fill — often *inconsistently*, some showing and some not, which reads as a rendering bug rather than a z-order one.
- **Arrows silently detach.** An arrow that merely points at a shape looks bound and isn't; it comes loose on the next edit.
- **Bound arrow labels can only be set at `add` time.** Adding one via `update` returns `added:0` and no error.

None of that is discoverable from the MCP's own docs. The skill front-loads it so the first diagram is right instead of the fourth.

## What it does

```
plan the visual argument ──▶ read_excalidraw_format ──▶ create/target scene
        │
        ▼
regions/frames → containers → primary nodes → secondary nodes → labels
        → bound arrows → accents → real library icons
        │
        ▼
   VERIFY: take_screenshot (layout) + search_scene_content (text/geometry)
        │
    2–4 iterations ──▶ shareable app.excalidraw.com/s/<ws>/<scene> link
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install brand-and-visuals@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/excalidraw-diagrams" ~/.claude/skills/excalidraw-diagrams
```

## Requirements

- An **Excalidraw+ MCP server** connected to your harness (hosted scenes, collections, shareable links).
- Python 3 for the bundled `scripts/excalidraw_tools.py`.

The element JSON is standard Excalidraw, so the format guidance applies if you generate `.excalidraw` files directly — but the workflow targets the hosted MCP, which is the usual case.

## Quick start

Ask naturally — the skill fires on any of these:

- "draw me an architecture diagram of this service"
- "put this flow on an Excalidraw canvas"
- "make a flowchart with real Postgres and Docker icons"

The bundled script does the error-prone math and the icon extraction:

```bash
# Where to put an icon + standalone label as one centered block in a box
python scripts/excalidraw_tools.py place --box X Y W H --icon-h H --font F

# Find an icon pack, list its items, extract one positioned icon as add-JSON
python scripts/excalidraw_tools.py catalog <keyword>
python scripts/excalidraw_tools.py list <author/name.excalidrawlib>
python scripts/excalidraw_tools.py icon <lib> --item <idx|name> \
  --at <cx> <top_y> --height <h> [--swap OLD=NEW]
```

`place` and `icon` both take `--at` as **center-x, top-y** — not the box's top-left `x,y`. Feed `icon --at` the exact `center_x`/`top_y` that `place` printed.

## Gotchas

- **Screenshots don't render text.** Never judge label presence or content from a screenshot. Use `search_scene_content`.
- **Z-order is not insertion order.** Simplest robust fix: give grouping containers *and* cards `backgroundColor:"transparent"` and keep the coloured border. A transparent fill can never occlude, so z-order stops mattering for content inside a box — and a white card on a white canvas looked identical anyway. Only fall back to an explicit high `index` when you genuinely need one *opaque* element atop another, and read the current max via `search_scene_content` rather than trusting a literal like `"b01"`.
- **`textAlign:"center"` makes the `x` you pass the CENTER** of a standalone label, not its left edge. To center under a node at center X, pass `x: X`.
- **Bound labels are always vertically centered** in their shape. For an icon-above-label block, position a *standalone* label yourself instead of using a bound `label`.
- **Arrows pointing at shapes must be bound** (`startBinding`/`endBinding`, mode `"inside"`) or they detach on the next edit. A bound arrow label (`label:{}`) is created only at `add` time — adding one via `update` silently no-ops, so re-add the arrow to relabel it. Read it back as the arrow's `labelText`; it's invisible to a `types:["text"]` search. And you can't delete a shape and its bound arrow in the same call — delete the arrow first.
- **A green `edit_scene_content` result is not verification.** Screenshot for layout, `search_scene_content` for text and geometry, then fix and re-verify. Typical: 2–4 iterations.

## Professional vs hand-drawn

Excalidraw defaults to a hand-drawn look (`roughness:1`, Excalifont). For clean technical diagrams set `roughness:0`, use `fontFamily:8` (mono) or `7` (titles), and lean on gray/blue with a single accent. For approachable whiteboard diagrams, keep the defaults. Match the register to the audience.

## What's in the box

| Path | What |
|---|---|
| `reference/mcp-gotchas.md` | The quirks above, in full. Read before any real scene work. |
| `reference/elements.md` | Element fields, fonts, semantic colour palette, arrow bindings, frames/slides, charts |
| `reference/layout.md` | Planning, spacing, centering/alignment math, structure-choice decision table |
| `reference/library-icons.md` | Finding and inserting real community icons; identifying unnamed ones; recommended packs |
| `scripts/excalidraw_tools.py` | `catalog` / `list` / `icon` / `place` — `--help` on any subcommand |

## License

MIT — see [LICENSE](../../LICENSE).
