#!/usr/bin/env python3
"""audit-contrast.py — WCAG 2.2 AA/AAA contrast matrix for a brand palette.

Runs the full sRGB-relative-luminance contrast math (WCAG 2.1 formula,
which is what 2.2 still uses). Emits a markdown table showing every
foreground/background pair's ratio and its pass/fail status at AA and
AAA.

Exits non-zero only if a *body-text* pair (fg on bg / fg on bg-elevated)
fails AA (< 4.5:1). Accent-on-bg and similar are expected to fail body
AA — that's why the accent is used for CTA *fills* (text on accent),
not prose. The script warns without failing in those cases.

Usage:
  audit-contrast.py --bg '#F3EAD3' --fg '#0E1320' --accent '#B85A3A'
  audit-contrast.py --bg '#F3EAD3' --fg '#0E1320' --accent '#B85A3A' \\
    --theme dark  # also check dark-mode swap (bg↔fg)

Exit codes:
  0   All body-text pairs pass AA
  1   One or more body-text pairs fail AA
  2   Invalid arguments
"""
from __future__ import annotations

import argparse
import sys
from typing import NamedTuple


class Color(NamedTuple):
    hex: str
    name: str


def srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_str: str) -> float:
    """WCAG 2.1/2.2 relative luminance of an sRGB hex colour."""
    s = hex_str.lstrip("#")
    if len(s) != 6:
        raise ValueError(f"Invalid hex: {hex_str}")
    r, g, b = (int(s[i : i + 2], 16) for i in (0, 2, 4))
    return (
        0.2126 * srgb_to_linear(r)
        + 0.7152 * srgb_to_linear(g)
        + 0.0722 * srgb_to_linear(b)
    )


def contrast_ratio(fg: str, bg: str) -> float:
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def grade(ratio: float, large: bool = False) -> str:
    """Return 'AAA', 'AA', or 'fail' for a given ratio."""
    if large:
        if ratio >= 4.5:
            return "AAA"
        if ratio >= 3.0:
            return "AA"
        return "fail"
    else:
        if ratio >= 7.0:
            return "AAA"
        if ratio >= 4.5:
            return "AA"
        return "fail"


def emoji_for(grade_str: str) -> str:
    return {"AAA": "✅", "AA": "✓", "fail": "❌"}.get(grade_str, "?")


def run_audit(
    bg: str,
    fg: str,
    accent: str,
    bg_elevated: str | None = None,
    fg_muted: str | None = None,
) -> tuple[list[dict], bool]:
    """Return (rows, body_text_fails)."""
    colors = [
        Color(bg, "bg"),
        Color(fg, "fg"),
        Color(accent, "accent"),
    ]
    if bg_elevated:
        colors.append(Color(bg_elevated, "bg-elevated"))
    if fg_muted:
        colors.append(Color(fg_muted, "fg-muted"))

    rows = []
    body_text_fails = False

    # Body-text pairs we care about most
    required_pairs = [(fg, bg), (fg, accent), (bg, accent)]
    if bg_elevated:
        required_pairs.insert(1, (fg, bg_elevated))

    for fg_c in colors:
        for bg_c in colors:
            if fg_c.hex.lower() == bg_c.hex.lower():
                continue
            ratio = contrast_ratio(fg_c.hex, bg_c.hex)
            body_grade = grade(ratio, large=False)
            large_grade = grade(ratio, large=True)

            # Flag body-text requirement pairs
            is_body_required = (fg_c.hex, bg_c.hex) in [
                (fg, bg),
                (fg, bg_elevated) if bg_elevated else None,
            ]
            if is_body_required and body_grade == "fail":
                body_text_fails = True

            rows.append(
                {
                    "fg": fg_c.hex,
                    "fg_name": fg_c.name,
                    "bg": bg_c.hex,
                    "bg_name": bg_c.name,
                    "ratio": ratio,
                    "body_grade": body_grade,
                    "large_grade": large_grade,
                    "required": is_body_required,
                }
            )
    return rows, body_text_fails


def print_matrix(rows: list[dict], title: str) -> None:
    print(f"\n## {title}\n")
    print("| Foreground | Background | Ratio | Body (≥4.5) | Large/UI (≥3) | Notes |")
    print("|---|---|---:|:---:|:---:|---|")
    for r in rows:
        notes = []
        if r["required"]:
            notes.append("**body-text required**")
        if r["body_grade"] == "fail" and r["large_grade"] != "fail":
            notes.append("use for large/UI only")
        if r["body_grade"] == "fail" and r["large_grade"] == "fail":
            notes.append("⚠️ do not pair")
        notes_str = "; ".join(notes) or "—"
        print(
            f"| `{r['fg']}` ({r['fg_name']}) | `{r['bg']}` ({r['bg_name']}) | "
            f"{r['ratio']:.2f}:1 | "
            f"{emoji_for(r['body_grade'])} {r['body_grade']} | "
            f"{emoji_for(r['large_grade'])} {r['large_grade']} | "
            f"{notes_str} |"
        )


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--bg", required=True, help="Primary light surface hex (e.g. '#F3EAD3')")
    p.add_argument("--fg", required=True, help="Primary text / dark surface hex")
    p.add_argument("--accent", required=True, help="Accent hex")
    p.add_argument("--bg-elevated", help="Optional elevated surface (e.g. card bg)")
    p.add_argument("--fg-muted", help="Optional muted text")
    p.add_argument(
        "--theme",
        choices=["light", "dark", "both"],
        default="light",
        help="Which theme to audit (default: light). 'dark' swaps bg↔fg. 'both' prints both.",
    )
    args = p.parse_args()

    print("# WCAG 2.2 contrast audit")
    print(f"\nPalette: bg `{args.bg}` · fg `{args.fg}` · accent `{args.accent}`")

    body_fails = False

    if args.theme in ("light", "both"):
        rows, fails = run_audit(
            args.bg, args.fg, args.accent, args.bg_elevated, args.fg_muted
        )
        print_matrix(rows, "Light theme")
        body_fails = body_fails or fails

    if args.theme in ("dark", "both"):
        # In dark mode, bg and fg swap (Agentleh parity rule)
        rows, fails = run_audit(
            args.fg, args.bg, args.accent, args.fg_muted, args.bg_elevated
        )
        print_matrix(rows, "Dark theme (bg↔fg swapped; accent constant)")
        body_fails = body_fails or fails

    print(
        "\n_Legend: **Body** ≥ 4.5:1 required for paragraph text. "
        "**Large/UI** ≥ 3:1 required for ≥24px text, icons, focus rings, "
        "non-text UI elements. AAA is ≥ 7:1 body / ≥ 4.5:1 large._"
    )

    if body_fails:
        print(
            "\n❌ **FAIL** — at least one body-text pair is below WCAG 2.2 AA (4.5:1). "
            "Adjust the palette before shipping."
        )
        return 1
    else:
        print("\n✓ All required body-text pairs pass WCAG 2.2 AA.")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
