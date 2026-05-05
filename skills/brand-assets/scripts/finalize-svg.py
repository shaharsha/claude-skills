#!/usr/bin/env python3
"""
finalize-svg.py — clean up an SVG.

Snaps fills to exact brand hexes, filters extraneous paths, normalizes viewBox.
See reference/finalize.md for the full option table.

Usage:
  finalize-svg.py --input raw.svg --output clean.svg \
    --brand '#0E1320' '#F3EAD3' '#B85A3A' \
    --require-contains '#F3EAD3:#B85A3A' \
    --min-area 50 --square --tolerance 15
"""

from __future__ import annotations
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def snap_fill(fill: str, brand: list[str], tolerance: int) -> str:
    if not fill or not fill.startswith("#"):
        return fill
    try:
        rgb = hex_to_rgb(fill)
    except ValueError:
        return fill
    best, best_dist = None, float("inf")
    for b in brand:
        d = rgb_dist(rgb, hex_to_rgb(b))
        if d < best_dist:
            best, best_dist = b, d
    if best_dist <= tolerance:
        return best
    raise SystemExit(
        f"ERROR: fill {fill} is {best_dist:.1f} RGB-units from closest brand color {best}. "
        f"Raise --tolerance above {int(best_dist) + 1} to accept, or clean the source SVG."
    )


# Simple bbox estimator from SVG path data.
# Handles the commands potrace/vtracer emit: M, L, H, V, C, S, Q, T, A, Z (absolute + relative).
PATH_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?[\d.]+(?:[eE][+-]?\d+)?")


def path_bbox(d: str) -> Optional[tuple[float, float, float, float]]:
    tokens = PATH_TOKEN.findall(d)
    if not tokens:
        return None
    x = y = 0.0
    start_x = start_y = 0.0
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    i = 0
    cmd = None
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                x, y = start_x, start_y
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
            continue
        # Consume coordinates per command
        rel = cmd.islower() if cmd else False
        def consume(n):
            nonlocal i
            vals = list(map(float, tokens[i:i + n]))
            i += n
            return vals
        if cmd in "Mm":
            nx, ny = consume(2)
            if rel: nx += x; ny += y
            x, y = nx, ny
            start_x, start_y = x, y
            # subsequent pairs are L (per SVG spec)
            cmd = "l" if rel else "L"
        elif cmd in "Ll":
            nx, ny = consume(2)
            if rel: nx += x; ny += y
            x, y = nx, ny
        elif cmd in "Hh":
            nx, = consume(1)
            if rel: nx += x
            x = nx
        elif cmd in "Vv":
            ny, = consume(1)
            if rel: ny += y
            y = ny
        elif cmd in "CcSs":
            # cubic Bezier; for bbox we approximate with endpoint (good enough for trace output)
            n = 6 if cmd in "Cc" else 4
            coords = consume(n)
            if rel:
                coords = [c + (x if idx % 2 == 0 else y) for idx, c in enumerate(coords)]
            # sample control points in addition to end point for tighter bbox
            pts = [(coords[k], coords[k + 1]) for k in range(0, len(coords), 2)]
            for px, py in pts:
                minx = min(minx, px); maxx = max(maxx, px)
                miny = min(miny, py); maxy = max(maxy, py)
            x, y = pts[-1]
        elif cmd in "QqTt":
            n = 4 if cmd in "Qq" else 2
            coords = consume(n)
            if rel:
                coords = [c + (x if idx % 2 == 0 else y) for idx, c in enumerate(coords)]
            pts = [(coords[k], coords[k + 1]) for k in range(0, len(coords), 2)]
            for px, py in pts:
                minx = min(minx, px); maxx = max(maxx, px)
                miny = min(miny, py); maxy = max(maxy, py)
            x, y = pts[-1]
        elif cmd in "Aa":
            # arc — skip to endpoint
            vals = consume(7)
            nx, ny = vals[5], vals[6]
            if rel: nx += x; ny += y
            x, y = nx, ny
        else:
            i += 1
        minx = min(minx, x); maxx = max(maxx, x)
        miny = min(miny, y); maxy = max(maxy, y)
    if minx == float("inf"):
        return None
    return (minx, miny, maxx, maxy)


def bbox_contains(outer: tuple[float, float, float, float],
                  inner: tuple[float, float, float, float],
                  slack: float = 0.0) -> bool:
    ox0, oy0, ox1, oy1 = outer
    ix0, iy0, ix1, iy1 = inner
    return (ox0 - slack <= ix0 and ix1 <= ox1 + slack and
            oy0 - slack <= iy0 and iy1 <= oy1 + slack)


def parse_transform(tr: str) -> tuple[float, float]:
    """Extract tx, ty from a translate(x,y) transform (other transforms ignored)."""
    m = re.match(r"translate\s*\(\s*([-\d.]+)\s*[, ]\s*([-\d.]+)\s*\)", tr or "")
    if m:
        return float(m.group(1)), float(m.group(2))
    return 0.0, 0.0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--brand", nargs="+", required=True, help="brand hex palette, e.g. #0E1320 #F3EAD3 #B85A3A")
    p.add_argument("--tolerance", type=int, default=15, help="max RGB-distance snap (default 15)")
    p.add_argument("--min-area", type=float, default=0, help="drop paths with bbox area below this")
    p.add_argument("--require-contains", action="append", default=[],
                   help="A:B — keep color-A paths whose bbox contains any color-B bbox (repeatable)")
    p.add_argument("--contains-slack", type=float, default=0,
                   help="px slack added to bbox containment check")
    p.add_argument("--drop-group", action="append", default=[], help="drop entire color group (repeatable)")
    p.add_argument("--square", action="store_true", help="pad viewBox to square (centered)")
    p.add_argument("--trim", action="store_true", help="tight-trim viewBox to content bbox")
    p.add_argument("--pad-percent", type=float, default=0, help="pad viewBox by N%% on all sides")
    p.add_argument("--default-fill", default=None, help="fill to assign to paths without a colored group")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    brand = [b.upper() for b in args.brand]
    drop_groups = {g.upper() for g in args.drop_group}
    contains_rules = [r.upper().split(":", 1) for r in args.require_contains]

    tree = ET.parse(args.input)
    root = tree.getroot()

    # Collect all colored paths. Each entry: (fill_hex, path_elem, group_elem, group_tx, group_ty, bbox_in_group_coords, bbox_in_svg_coords)
    entries = []
    for group in root.iter():
        tag = group.tag.split("}")[-1]
        if tag != "g":
            continue
        fill = group.attrib.get("fill", "")
        if not fill.startswith("#"):
            continue
        fill = snap_fill(fill.upper(), brand, args.tolerance).upper()
        group.set("fill", fill)
        tx, ty = parse_transform(group.attrib.get("transform", ""))
        for path in group.findall(f"{{{SVG_NS}}}path"):
            d = path.attrib.get("d", "")
            raw_bbox = path_bbox(d)
            if raw_bbox is None:
                continue
            gbbox = raw_bbox  # in group-local coords
            sbbox = (gbbox[0] + tx, gbbox[1] + ty, gbbox[2] + tx, gbbox[3] + ty)
            entries.append({"fill": fill, "path": path, "group": group, "gbbox": gbbox, "sbbox": sbbox})

    # Handle top-level paths (no colored group wrapper)
    for path in list(root.findall(f"{{{SVG_NS}}}path")):
        fill = args.default_fill or "#000000"
        fill = snap_fill(fill.upper(), brand, args.tolerance).upper()
        path.set("fill", fill)
        d = path.attrib.get("d", "")
        sbbox = path_bbox(d)
        if sbbox is None:
            continue
        # Wrap in a synthetic group tracked in entries
        entries.append({"fill": fill, "path": path, "group": None, "gbbox": sbbox, "sbbox": sbbox})

    # Filter: drop entire groups
    entries = [e for e in entries if e["fill"] not in drop_groups]

    # Filter: min-area
    if args.min_area > 0:
        def area(bb):
            return max(0.0, bb[2] - bb[0]) * max(0.0, bb[3] - bb[1])
        entries = [e for e in entries if area(e["sbbox"]) >= args.min_area]

    # Filter: require-contains
    for outer_hex, inner_hex in contains_rules:
        inner_bboxes = [e["sbbox"] for e in entries if e["fill"] == inner_hex]
        if not inner_bboxes:
            print(f"warning: --require-contains {outer_hex}:{inner_hex} — no {inner_hex} paths found; skipping filter", file=sys.stderr)
            continue
        kept = []
        for e in entries:
            if e["fill"] != outer_hex:
                kept.append(e)
                continue
            if any(bbox_contains(e["sbbox"], ib, slack=args.contains_slack) for ib in inner_bboxes):
                kept.append(e)
        entries = kept

    # Materialize: rebuild <g fill="HEX"> groups with kept paths, sorted bg → fg
    # Brand order implies stacking order: first in --brand = behind, last = on top.
    # Remove all existing <g> and top-level <path> elements from root.
    for child in list(root):
        tag = child.tag.split("}")[-1]
        if tag in ("g", "path"):
            root.remove(child)

    new_groups: dict[str, ET.Element] = {}
    for color in brand:
        new_groups[color] = ET.SubElement(root, f"{{{SVG_NS}}}g", {"fill": color})

    for e in entries:
        path = e["path"]
        # Strip the group-local transform from this path by rewriting d? We already have sbbox.
        # Simpler: preserve original transform via a wrapping group only when transform was non-zero.
        # For most trace output this is fine because group transforms are all translate(tx,ty).
        # We baked the translation into sbbox but not into d. So preserve the original group's transform
        # by wrapping this path in a per-path <g transform>.
        src_group = e["group"]
        if src_group is not None and src_group.attrib.get("transform"):
            wrapper = ET.SubElement(new_groups[e["fill"]], f"{{{SVG_NS}}}g",
                                    {"transform": src_group.attrib["transform"]})
            wrapper.append(path)
        else:
            new_groups[e["fill"]].append(path)

    # Drop empty groups
    for color, g in list(new_groups.items()):
        if len(g) == 0:
            root.remove(g)
            del new_groups[color]

    # Compute overall svg content bbox for viewBox operations
    if entries:
        minx = min(e["sbbox"][0] for e in entries)
        miny = min(e["sbbox"][1] for e in entries)
        maxx = max(e["sbbox"][2] for e in entries)
        maxy = max(e["sbbox"][3] for e in entries)
    else:
        print("warning: no paths remain after filtering; output will have empty viewBox", file=sys.stderr)
        minx = miny = 0
        maxx = maxy = 100

    # viewBox operations
    vb = None
    if args.trim:
        vb = (minx, miny, maxx - minx, maxy - miny)
    elif args.square:
        w = maxx - minx
        h = maxy - miny
        side = max(w, h)
        vb_x = minx - (side - w) / 2
        vb_y = miny - (side - h) / 2
        vb = (vb_x, vb_y, side, side)
    else:
        # keep existing viewBox if present
        vb_attr = root.attrib.get("viewBox")
        if vb_attr:
            parts = [float(x) for x in vb_attr.replace(",", " ").split()]
            if len(parts) == 4:
                vb = tuple(parts)
        if vb is None:
            vb = (minx, miny, maxx - minx, maxy - miny)

    # Optional extra padding
    if args.pad_percent > 0:
        pct = args.pad_percent / 100.0
        vx, vy, vw, vh = vb
        pad = max(vw, vh) * pct
        vb = (vx - pad, vy - pad, vw + 2 * pad, vh + 2 * pad)

    root.set("viewBox", " ".join(f"{v:g}" for v in vb))
    # Drop explicit width/height so the viewBox drives scaling
    for attr in ("width", "height"):
        if attr in root.attrib:
            del root.attrib[attr]

    Path(args.output).write_bytes(ET.tostring(root, encoding="utf-8"))

    if not args.quiet:
        by_color = {}
        for e in entries:
            by_color[e["fill"]] = by_color.get(e["fill"], 0) + 1
        counts = " ".join(f"{c}={n}" for c, n in by_color.items())
        size = Path(args.output).stat().st_size
        print(f"{Path(args.input).name} → {Path(args.output).name}: {counts} ({size}B)")


if __name__ == "__main__":
    main()
