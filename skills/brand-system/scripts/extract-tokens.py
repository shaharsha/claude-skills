#!/usr/bin/env python3
"""extract-tokens.py — parse BRAND.md token tables and emit tokens.css or tokens.json.

Scans a BRAND.md file for the §6 Colour / §7 Typography / §9 Spacing /
§9 Radii / §11 Motion tables and re-emits the values as:

- `tailwind-v4` (default): a `@theme { ... }` block + `:root` semantics + `[data-theme="dark"]`
- `dtcg`: W3C Design Tokens Community Group JSON (for Style Dictionary / Tokens Studio)
- `css-vars`: a bare `:root { ... }` block, no Tailwind namespacing

Usage:
  extract-tokens.py --input BRAND.md --format tailwind-v4 > tokens.css
  extract-tokens.py --input BRAND.md --format dtcg       > tokens.json
  extract-tokens.py --input BRAND.md --format css-vars   > vars.css
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


HEX_RE = re.compile(r"`?#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})`?")
TOKEN_RE = re.compile(r"`(--[a-z0-9-]+)`")


def find_section(md: str, heading_pattern: str) -> str:
    """Extract the markdown body under a section heading until the next `## ` or `---`."""
    m = re.search(
        rf"(?ms)^#+\s+\d*\.?\s*{heading_pattern}\b.*?(?=^\#\#\s|\Z|^---)",
        md,
        re.IGNORECASE | re.MULTILINE,
    )
    return m.group(0) if m else ""


def extract_color_tokens(md: str) -> dict[str, str]:
    """Pull color tokens from §6 Colour system tables.

    Looks for table rows shaped like:
      | `--color-name` | `#HEX`   | Description |
    """
    section = find_section(md, r"Colou?r(\s+system)?")
    if not section:
        section = md  # fallback: scan the whole doc

    tokens: dict[str, str] = {}
    for line in section.splitlines():
        token_match = TOKEN_RE.search(line)
        hex_match = HEX_RE.search(line)
        if token_match and hex_match:
            name = token_match.group(1)
            hex_val = hex_match.group(1)
            if len(hex_val) == 3:
                hex_val = "".join(c * 2 for c in hex_val)
            tokens[name] = f"#{hex_val.upper()}"
    return tokens


def extract_numeric_tokens(md: str, section_pattern: str, prefix: str) -> dict[str, str]:
    """Extract numeric tokens (spacing, radii) from a section's table.

    Looks for:
      | `--space-4` | 16px | Default gap |
      | `--radius-sm` | 6px | Inputs |
    """
    section = find_section(md, section_pattern)
    if not section:
        return {}

    tokens: dict[str, str] = {}
    # Match `--name` followed by `| VALUE` within the same row
    for row in section.splitlines():
        token_match = re.search(rf"`({prefix}[a-z0-9-]*)`", row)
        if not token_match:
            continue
        # Value cell — find first plain number or number + unit after the token
        value_match = re.search(
            r"\|\s*(?:`)?([0-9]+(?:\.[0-9]+)?(?:px|rem|em|%|s|ms)?)\s*(?:`)?\s*\|",
            row,
        )
        if value_match:
            tokens[token_match.group(1)] = value_match.group(1)
    return tokens


def tier_colors(colors: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Split color tokens into primitives vs semantics.

    Every extracted token carries a concrete hex value, so they are all
    primitives in the DTCG sense — semantic aliases (e.g. `--bg: var(--cream)`)
    don't carry hexes and never appear in `colors`. We keep the function
    because the downstream Tailwind emitter calls it, but return everything
    as a primitive and an empty semantic dict.
    """
    primitives = dict(colors)
    semantics: dict[str, str] = {}
    return primitives, semantics


def emit_tailwind_v4(md: str) -> str:
    colors = extract_color_tokens(md)
    primitives, _ = tier_colors(colors)
    spacing = extract_numeric_tokens(md, r"Spacing", "--space")
    # Some books use `--spacing-` in @theme; support both
    spacing_themed = {k.replace("--space-", "--spacing-"): v for k, v in spacing.items()}
    radii = extract_numeric_tokens(md, r"Radii|Spacing\s*&\s*layout|Radius", "--radius")

    lines: list[str] = ["/* Extracted from BRAND.md via extract-tokens.py */", "", "@theme {"]
    if primitives:
        lines.append("  /* ── Core palette ─────────────────── */")
        for k, v in primitives.items():
            lines.append(f"  {k}: {v};")
        lines.append("")
    if spacing_themed:
        lines.append("  /* ── Spacing ──────────────────────── */")
        for k, v in spacing_themed.items():
            lines.append(f"  {k}: {v};")
        lines.append("")
    if radii:
        lines.append("  /* ── Radii ────────────────────────── */")
        for k, v in radii.items():
            lines.append(f"  {k}: {v};")
        lines.append("")
    lines.append("}")
    lines.append("")

    # Heuristic semantics — map by convention
    if primitives:
        # Guess a bg and fg primitive
        bg_primitive = next(
            (k for k in primitives if k in ("--color-bg", "--color-cream", "--color-bg-100")),
            next(iter(primitives)),
        )
        fg_primitive = next(
            (k for k in primitives if k in ("--color-fg", "--color-navy", "--color-fg-900")),
            None,
        )
        accent = next(
            (k for k in primitives if "accent" in k or "terracotta" in k),
            None,
        )
        lines.append(":root {")
        lines.append(f"  --bg:     var({bg_primitive});")
        if fg_primitive:
            lines.append(f"  --text:   var({fg_primitive});")
        if accent:
            lines.append(f"  --accent: var({accent});")
        lines.append("}")

    return "\n".join(lines) + "\n"


def emit_dtcg(md: str) -> str:
    """Emit W3C DTCG JSON (https://tr.designtokens.org/format/)."""
    colors = extract_color_tokens(md)
    spacing = extract_numeric_tokens(md, r"Spacing", "--space")
    radii = extract_numeric_tokens(md, r"Radii|Spacing\s*&\s*layout", "--radius")

    data: dict = {"color": {}, "spacing": {}, "radius": {}}

    for k, v in colors.items():
        # --color-cream -> cream; --bg -> bg
        name = k.lstrip("-").removeprefix("color-")
        data["color"][name] = {"$value": v, "$type": "color"}

    for k, v in spacing.items():
        name = k.lstrip("-").removeprefix("space-").removeprefix("spacing-")
        data["spacing"][name] = {"$value": v, "$type": "dimension"}

    for k, v in radii.items():
        name = k.lstrip("-").removeprefix("radius-")
        data["radius"][name] = {"$value": v, "$type": "dimension"}

    # Drop empty categories
    data = {k: v for k, v in data.items() if v}

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def emit_css_vars(md: str) -> str:
    colors = extract_color_tokens(md)
    spacing = extract_numeric_tokens(md, r"Spacing", "--space")
    radii = extract_numeric_tokens(md, r"Radii|Spacing\s*&\s*layout", "--radius")

    lines = ["/* Extracted from BRAND.md via extract-tokens.py */", "", ":root {"]
    for group, tokens in (("Colors", colors), ("Spacing", spacing), ("Radii", radii)):
        if not tokens:
            continue
        lines.append(f"  /* ── {group} ── */")
        for k, v in tokens.items():
            lines.append(f"  {k}: {v};")
        lines.append("")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip())
    p.add_argument("--input", required=True, help="Path to BRAND.md")
    p.add_argument(
        "--format",
        choices=["tailwind-v4", "dtcg", "css-vars"],
        default="tailwind-v4",
    )
    args = p.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"ERROR: {src} not found", file=sys.stderr)
        return 2

    md = src.read_text(encoding="utf-8")

    if args.format == "tailwind-v4":
        print(emit_tailwind_v4(md), end="")
    elif args.format == "dtcg":
        print(emit_dtcg(md), end="")
    else:
        print(emit_css_vars(md), end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
