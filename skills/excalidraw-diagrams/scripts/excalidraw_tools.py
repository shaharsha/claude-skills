#!/usr/bin/env python3
"""
excalidraw_tools.py — helpers for building Excalidraw scenes via the Excalidraw+ MCP.

The MCP's `edit_scene_content` add-payload is plain JSON of standard Excalidraw
elements, so these subcommands prepare that JSON for you:

  catalog  <keyword>                     search the community library catalog
  list     <lib>                         enumerate items in a .excalidrawlib
  icon     <lib> --item <idx|name> ...   emit an add-payload for ONE icon, scaled
                                         and positioned (rotation-aware), ready to
                                         paste into edit_scene_content `add`
  place    --box X Y W H ...             centering math: where to put an icon + a
                                         standalone label so they read as one
                                         vertically-centered block inside a box

`<lib>` is either `author/name.excalidrawlib` (fetched from the official catalog)
or a path to a local .excalidrawlib file. Downloads are cached under a temp dir.

Everything prints JSON or a small table to stdout — nothing touches the scene;
you copy the JSON into an `edit_scene_content` call yourself, then screenshot to
verify. See ../reference/library-icons.md for the full workflow.
"""
import argparse
import json
import math
import os
import sys
import tempfile
import urllib.request

CATALOG_URL = "https://raw.githubusercontent.com/excalidraw/excalidraw-libraries/main/libraries.json"
LIB_BASE = "https://raw.githubusercontent.com/excalidraw/excalidraw-libraries/main/libraries/"
CACHE = os.path.join(tempfile.gettempdir(), "excalidraw_libs_cache")

# Fields worth copying into a fresh add-payload. Everything else (id/seed/version/
# boundElements/updated…) is server-managed and must NOT be sent on `add`.
KEEP = [
    "type", "x", "y", "width", "height", "angle", "strokeColor", "backgroundColor",
    "fillStyle", "strokeWidth", "strokeStyle", "roughness", "opacity", "points",
    "text", "fontSize", "fontFamily", "textAlign", "roundness", "arrowhead",
    "startArrowhead", "endArrowhead",
]


def _fetch(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
    except Exception as e:
        sys.exit(f"error: could not fetch {url}\n  {e}")
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def _resolve_lib(lib):
    """Return a local path to the .excalidrawlib for `lib` (local path or author/name)."""
    if os.path.exists(lib):
        return lib
    if not lib.endswith(".excalidrawlib"):
        lib += ".excalidrawlib"
    dest = os.path.join(CACHE, lib.replace("/", "__"))
    if os.path.exists(dest):
        return dest
    return _fetch(LIB_BASE + lib, dest)


def _load_items(path):
    """Return a list of (name, elements) tuples. Handles v1 and v2 library shapes."""
    with open(path) as f:
        d = json.load(f)
    raw = d.get("libraryItems") or d.get("library") or []
    items = []
    for i, it in enumerate(raw):
        if isinstance(it, dict):  # v2: {name, elements}
            items.append((it.get("name") or f"#{i}", it.get("elements", [])))
        else:  # v1: bare list of elements, no name
            items.append((f"#{i}", it))
    return items


def _select(items, ref):
    """Pick an item by integer index or by (case-insensitive substring) name."""
    if ref.lstrip("-").isdigit():
        idx = int(ref)
        if not (0 <= idx < len(items)):
            sys.exit(f"error: index {idx} out of range (0..{len(items)-1})")
        return items[idx]
    matches = [it for it in items if ref.lower() in it[0].lower()]
    if not matches:
        sys.exit(f"error: no item name contains {ref!r}. Try `list` to see names.")
    if len(matches) > 1:
        names = ", ".join(m[0] for m in matches)
        sys.exit(f"error: {ref!r} is ambiguous: {names}")
    return matches[0]


def _corners(e):
    """Absolute corner points of one element, respecting rotation about its bbox centre.

    Rotation matters: a library icon like the React atom has orbit ellipses with an
    `angle` and negative `points`, so a naive x/y/width bbox is wildly wrong. We rotate
    the real corners so scale/centre are correct.
    """
    if e.get("points"):
        pts = [(e["x"] + p[0], e["y"] + p[1]) for p in e["points"]]
    else:
        x, y, w, h = e["x"], e["y"], e.get("width", 0), e.get("height", 0)
        pts = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    a = e.get("angle", 0) or 0
    if a:
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        ca, sa = math.cos(a), math.sin(a)
        pts = [(cx + (px - cx) * ca - (py - cy) * sa,
                cy + (px - cx) * sa + (py - cy) * ca) for px, py in pts]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _group_bbox(els):
    bs = [_corners(e) for e in els]
    return (min(b[0] for b in bs), min(b[1] for b in bs),
            max(b[2] for b in bs), max(b[3] for b in bs))


def _place(els, cx, top, target_h, swaps):
    x0, y0, x1, y1 = _group_bbox(els)
    w, h = x1 - x0, y1 - y0
    if h == 0:
        sys.exit("error: item has zero height; cannot scale")
    s = target_h / h
    out = []
    for e in els:
        ne = {k: e[k] for k in KEEP if k in e}
        if ne.get("type") == "draw":          # legacy element name
            ne["type"] = "freedraw"
        ne["x"] = round(cx - w * s / 2 + (e["x"] - x0) * s, 2)
        ne["y"] = round(top + (e["y"] - y0) * s, 2)
        if "width" in e:
            ne["width"] = round(e["width"] * s, 2)
        if "height" in e:
            ne["height"] = round(e["height"] * s, 2)
        if ne.get("points"):
            ne["points"] = [[round(p[0] * s, 2), round(p[1] * s, 2)] for p in ne["points"]]
        if ne.get("type") == "text":
            ne["fontSize"] = round(e.get("fontSize", 16) * s, 2)
            if ne.get("fontFamily") in (1, 2, 3):   # legacy font ids → modern
                ne["fontFamily"] = 8 if ne["fontFamily"] == 3 else 5
            if e.get("text") in swaps:
                ne["text"] = swaps[e["text"]]
    # emit width/height keys the server expects even when source omitted them
        out.append(ne)
    return out, (w * s, h * s)


def cmd_catalog(args):
    path = _fetch(CATALOG_URL, os.path.join(CACHE, "libraries.json")) \
        if not os.path.exists(os.path.join(CACHE, "libraries.json")) \
        else os.path.join(CACHE, "libraries.json")
    libs = json.load(open(path))
    kws = [k.lower() for k in args.keywords]
    hits = []
    for l in libs:
        text = (l.get("name", "") + " " + l.get("description", "")).lower()
        if all(k in text for k in kws):
            hits.append(l)
    if not hits:
        print(f"No libraries match {' '.join(args.keywords)!r}. (catalog has {len(libs)} libs)")
        return
    for l in hits:
        print(f"{l.get('source'):55} {l.get('name')}")
        print(f"{'':55} {l.get('description','')[:100]}")


def cmd_list(args):
    items = _load_items(_resolve_lib(args.lib))
    print(f"{len(items)} items in {args.lib}:")
    for i, (name, els) in enumerate(items):
        types = {}
        texts = []
        for e in els:
            types[e["type"]] = types.get(e["type"], 0) + 1
            if e["type"] == "text":
                texts.append(e.get("text", "")[:20])
        t = " ".join(f"{k}:{v}" for k, v in sorted(types.items()))
        extra = f"  text={texts}" if texts else ""
        print(f"  [{i:2}] {name:24} {len(els):3} els  {t}{extra}")
    print("\nUnnamed items (#N) come from a v1 library — identify them by inserting a few "
          "into a TEMP scene and screenshotting. Note: MCP screenshots do NOT render text.")


def cmd_icon(args):
    items = _load_items(_resolve_lib(args.lib))
    name, els = _select(items, args.item)
    swaps = {}
    for pair in (args.swap or []):
        if "=" not in pair:
            sys.exit(f"error: --swap expects OLD=NEW, got {pair!r}")
        k, v = pair.split("=", 1)
        swaps[k] = v
    out, (w, h) = _place(els, args.at[0], args.at[1], args.height, swaps)
    sys.stderr.write(
        f"# icon {name!r}: {len(out)} els, ~{w:.0f}x{h:.0f}px, "
        f"centred x={args.at[0]}, top y={args.at[1]}\n")
    print(json.dumps(out, separators=(",", ":")))


def cmd_place(args):
    x, y, w, h = args.box
    icon_h = args.icon_h
    font = args.font
    gap = args.gap
    label_h = font * 1.25                      # excalidraw line-height
    block_h = icon_h + gap + label_h
    top = y + (h - block_h) / 2                 # centre the whole block in the box
    icon_top = round(top, 2)
    icon_cx = round(x + w / 2, 2)
    label_y = round(top + icon_h + gap, 2)
    label_cx = icon_cx                          # with textAlign:center, x is the CENTRE
    print(json.dumps({
        "icon": {"center_x": icon_cx, "top_y": icon_top, "height": icon_h},
        "label": {"center_x": label_cx, "y": label_y, "fontSize": font,
                  "note": "standalone text with textAlign:'center' — x is the CENTER anchor"},
        "block": {"height": round(block_h, 2), "centered_in_box": True},
    }, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("catalog", help="search the community library catalog")
    c.add_argument("keywords", nargs="+")
    c.set_defaults(func=cmd_catalog)

    c = sub.add_parser("list", help="enumerate items in a .excalidrawlib")
    c.add_argument("lib")
    c.set_defaults(func=cmd_list)

    c = sub.add_parser("icon", help="emit an add-payload for one icon")
    c.add_argument("lib")
    c.add_argument("--item", required=True, help="item index (0-based) or name substring")
    c.add_argument("--at", nargs=2, type=float, required=True, metavar=("X", "Y"),
                   help="X = horizontal CENTRE, Y = top of the icon")
    c.add_argument("--height", type=float, required=True, help="target icon height in px")
    c.add_argument("--swap", action="append", metavar="OLD=NEW",
                   help="replace a text label inside the icon (repeatable)")
    c.set_defaults(func=cmd_icon)

    c = sub.add_parser("place", help="centering math for icon + standalone label in a box")
    c.add_argument("--box", nargs=4, type=float, required=True, metavar=("X", "Y", "W", "H"))
    c.add_argument("--icon-h", type=float, required=True)
    c.add_argument("--font", type=float, default=18)
    c.add_argument("--gap", type=float, default=8)
    c.set_defaults(func=cmd_place)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
