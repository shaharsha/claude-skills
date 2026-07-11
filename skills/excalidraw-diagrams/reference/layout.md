# Layout, alignment & design patterns

How to make a scene read as a deliberate visual argument rather than "boxes with
text." Covers spacing defaults, centering/alignment (the fiddly part), and which
structure to choose for a given idea.

## Contents
- The one test that matters
- Plan before you place
- Spacing defaults
- Centering & alignment (icons, labels, blocks)
- Choosing a structure
- Swimlanes
- Common failure modes

## The one test that matters

**If you deleted every label, would the structure still communicate the idea?**
Fan-outs should visibly fan out; convergence should visibly merge; a hierarchy
should look like a tree; a cycle should loop; sequence should read in order;
ownership should be separated by lanes/boundaries. Layout carries meaning first;
text confirms it. If the answer is no, the diagram is "card soup" — restructure
before polishing.

## Plan before you place

Decide, in order, before emitting any element:
1. **Family** — workflow, architecture, timeline, hierarchy, comparison, cycle,
   concept map, or slides.
2. **Reading direction** — top-to-bottom, left-to-right, radial, or loop.
3. **Regions** — sketch the canvas bounds, margins, rows/columns/lanes, and which
   group goes where. Assign groups to regions *before* placing individual nodes.
4. **Placement order** — frames/regions → lane/group containers → primary nodes →
   secondary nodes → annotations → arrows (only once nodes are stable) → accents.

Placing arrows before their nodes are stable, or reaching for a uniform grid of
equal cards when relationships exist, are the two most common ways a diagram goes
wrong at the planning stage.

## Spacing defaults

- Outer canvas margin: ~80px.
- Gap between major groups: 64–120px.
- Gap between sibling nodes: 32–56px.
- Internal group/container padding: 40–64px.
- Text-to-container edge: ≥16px.
- Align siblings on a shared axis; keep sibling widths equal where possible.
- ≤6–8 primary nodes per row. Prefer generous spacing over cramming.

## Centering & alignment (icons, labels, blocks)

**Horizontal centering of a standalone label** under a node whose center is `X`:
set the label's `x = X` with `"textAlign":"center"` (the server treats x as the
center anchor — see mcp-gotchas.md). Don't subtract half the width on `add`.

**Icon + label as one vertically-centered block** (the common card layout):
a bound `label` can't do this — it's always pinned to the shape's middle. Instead
add the icon and a **standalone** label and position both so the *combined* block is
centered. The math (given a box and the icon height + font size):

```
label_h  = fontSize * 1.25
block_h  = icon_h + gap + label_h
top      = box_y + (box_h - block_h) / 2
icon:  center_x = box_x + box_w/2,  top_y = top
label: center_x = box_x + box_w/2,  y     = top + icon_h + gap
```

Let the script do it: `python scripts/excalidraw_tools.py place --box X Y W H
--icon-h H --font F [--gap G]` prints the icon and label positions. Verify the
result with `search_scene_content` (screenshots won't show the text) — the top and
bottom margins inside the box should match.

**Aligning a row of nodes**: share one `y` and one `height`; step `x` by a constant
`cell_w`. **A column**: share `x`/`width`, step `y`. Keeping these exact is what
makes a diagram look intentional rather than hand-nudged.

## Choosing a structure

| The idea is… | Use | Not |
|---|---|---|
| a set of truly equal peers | a uniform card grid | (only case a grid is right) |
| a process across actors/systems | vertical swimlanes | a flat row of cards |
| steps with a decision | boxes + one diamond, elbow arrows | dense text in a diamond |
| one source → many outputs | fan-out (visible spread) | a stack |
| many inputs → one result | convergence (visible merge) | scattered boxes |
| ranked/compared quantities | bar chart or comparison columns | prose |
| iteration / feedback | a visible loop with a return arrow | a straight line |
| hierarchy / ownership | a tree (lines + labels, few boxes) | boxed grid |
| chronological events | one timeline axis + dots + labels | big cards |
| related ideas around a core | concept map (central + grouped) | flat grid |

Only default to a grid of equal cards when the items are genuinely peers with no
sequence, hierarchy, ownership, or dependency. If a relationship exists, show it
with arrows, lanes, grouping, boundaries, or spatial structure.

## Swimlanes

For a workflow with ≥2 actors/systems/teams: vertical lanes, each a lightly tinted
rectangle with a header (`fontFamily:7`), consistent widths. Main narrative flows
top-to-bottom within a lane; left-to-right motion means a cross-lane handoff.
Related steps share a horizontal row. Elbow arrows only, minimal crossings, route
along clean channels. Group outcome states near the decision that produced them
(green success / amber pending / red failure).

## Common failure modes

- **Card soup** — equal boxes, no relationships shown. Restructure to the table above.
- **Diagonal arrow spaghetti** — use elbow routing and align nodes to channels.
- **Unbound arrows** — they detach on the next edit; always bind arrows to shapes.
- **Overlap / clipping** — labels longer than their box, icons over text. Re-measure
  via `search_scene_content`; widen boxes or shorten text.
- **Color as decoration** — every color should carry meaning; cap at ~5.
- **Text-invisible-under-fill** — z-order gap; pass a high `index` (mcp-gotchas.md).
