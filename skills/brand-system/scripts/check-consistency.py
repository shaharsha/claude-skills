#!/usr/bin/env python3
"""check-consistency.py — validate BRAND.md tokens match one or more target CSS files.

Brand books don't fail at v1; they fail when the code silently drifts.
This script parses colour tokens from BRAND.md (§6 / §17) and from each
target CSS file, then reports matches, drifts (different hex), and
missing / extra tokens per file.

Usage:
  check-consistency.py BRAND.md landing/src/index.css
  check-consistency.py BRAND.md landing/src/index.css app/frontend/src/index.css tokens.css
  check-consistency.py BRAND.md --target landing/src/index.css --target app/frontend/src/index.css

Exit codes:
  0   No drift across any target file
  1   Drift detected (at least one token mismatch)
  2   Invalid input (file not found, etc.)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEX_RE = re.compile(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})")
# Match `--name`, `--name-50`, `--color-name`, etc. followed by ": #hex"
# in CSS, or in markdown table rows `| \`--name\` | \`#hex\` |`
TOKEN_DECL_RE = re.compile(
    r"(?P<name>--[a-z][a-z0-9-]*)\s*:\s*#(?P<hex>[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})"
)
MARKDOWN_TOKEN_RE = re.compile(
    r"`(?P<name>--[a-z][a-z0-9-]*)`\s*\|\s*`?#(?P<hex>[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})"
)


def norm_hex(h: str) -> str:
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"#{h.upper()}"


def parse_css_tokens(path: Path) -> dict[str, str]:
    """Extract `--name: #hex` declarations from a CSS file.

    When the same name is declared multiple times (e.g. once in @theme
    for light mode, again in [data-theme="dark"] for dark mode), we keep
    the *first* occurrence — which is almost always the light/default
    value, matching how BRAND.md's primitives are written.
    """
    text = path.read_text(encoding="utf-8")
    tokens: dict[str, str] = {}
    for m in TOKEN_DECL_RE.finditer(text):
        name = m.group("name")
        if name in tokens:
            continue  # first-wins so dark-mode overrides don't mask light values
        tokens[name] = norm_hex(m.group("hex"))
    return tokens


def parse_all_css_hexes(path: Path) -> set[str]:
    """Return the full set of hex values that appear anywhere in the CSS,
    regardless of name — includes dark-mode overrides, section stops, glass
    gradients, etc. Used for 'is this brand hex present anywhere?' coverage.
    """
    text = path.read_text(encoding="utf-8")
    hexes: set[str] = set()
    for m in HEX_RE.finditer(text):
        hexes.add(norm_hex(m.group(1)))
    return hexes


def parse_markdown_tokens(path: Path) -> dict[str, str]:
    """Extract `--name` / `#hex` pairs from BRAND.md colour tables + @theme blocks."""
    text = path.read_text(encoding="utf-8")
    tokens: dict[str, str] = {}
    # Markdown table rows: | `--name` | `#hex` | ...
    for m in MARKDOWN_TOKEN_RE.finditer(text):
        tokens[m.group("name")] = norm_hex(m.group("hex"))
    # CSS-style declarations inside fenced code blocks
    for m in TOKEN_DECL_RE.finditer(text):
        tokens.setdefault(m.group("name"), norm_hex(m.group("hex")))
    return tokens


def compare(source: dict[str, str], target: dict[str, str]) -> tuple[list, list, list, list]:
    """Return (matches, drifts, missing_in_target, extra_in_target).

    - matches: tokens present in both with same hex (by name)
    - drifts: tokens present in both but with different hex (by name)
    - missing_in_target: tokens in source but not in target (by name)
    - extra_in_target: tokens in target but not in source (by name)
    """
    matches, drifts, missing, extra = [], [], [], []
    for name, hex_src in source.items():
        if name not in target:
            missing.append((name, hex_src))
        elif target[name] != hex_src:
            drifts.append((name, hex_src, target[name]))
        else:
            matches.append((name, hex_src))
    for name in target:
        if name not in source:
            extra.append((name, target[name]))
    return matches, drifts, missing, extra


def hex_coverage(
    source: dict[str, str],
    target: dict[str, str],
    all_target_hexes: set[str],
) -> tuple[list, list]:
    """Compute palette coverage by hex value (ignoring token names).

    A BRAND.md hex is "covered" if it appears anywhere in the target CSS
    — including in rgba() calls, section gradient stops, dark-mode
    overrides, etc. — even under a different name.

    `target`: dict[name -> first-seen hex] (for alias reporting)
    `all_target_hexes`: all hexes anywhere in the CSS (including duplicates
    across light/dark) — for true "is this hex present?" coverage.

    Returns (covered_hexes, orphan_hexes):
    - covered_hexes: [(source_name, hex, list_of_target_names_using_that_hex)]
    - orphan_hexes:  [(source_name, hex)] — absent from target entirely
    """
    target_by_hex: dict[str, list[str]] = {}
    for name, hex_val in target.items():
        target_by_hex.setdefault(hex_val, []).append(name)

    covered, orphans = [], []
    seen_hexes: set[str] = set()
    for src_name, hex_src in source.items():
        if hex_src in seen_hexes:
            continue
        seen_hexes.add(hex_src)
        if hex_src in all_target_hexes:
            # We have coverage. If we know a name for it, report those names;
            # otherwise it lives in an rgba() or similar.
            names = target_by_hex.get(hex_src, [])
            covered.append((src_name, hex_src, names))
        else:
            orphans.append((src_name, hex_src))
    return covered, orphans


def check_file(source_tokens: dict[str, str], target_path: Path) -> bool:
    """Report consistency of one target file vs the source. Return True if clean."""
    target_tokens = parse_css_tokens(target_path)
    all_target_hexes = parse_all_css_hexes(target_path)

    print(f"\n## {target_path}\n")

    if not target_tokens:
        print(f"⚠️  No `--name: #hex` declarations found. Skipping.")
        return True

    matches, drifts, missing, extra = compare(source_tokens, target_tokens)
    covered, orphans = hex_coverage(source_tokens, target_tokens, all_target_hexes)

    total_unique_hexes = len(covered) + len(orphans)
    print(f"### By hex (palette coverage — the one that actually matters)\n")
    print(f"- **Brand hexes present in this file**: {len(covered)} / {total_unique_hexes}")
    print(f"- **Brand hexes absent**: {len(orphans)}")
    print()
    print(f"### By name (naming-layer alignment)\n")
    print(f"- **Matches** (same name + same hex): {len(matches)}")
    print(f"- **Drifts** (same name, different hex): {len(drifts)}")
    print(f"- **Missing by name** (in BRAND.md under this name, not in this file): {len(missing)}")
    print(f"- **Extra by name** (in this file, not in BRAND.md under this name): {len(extra)}")

    if drifts:
        print("\n### ❌ Drifts — BRAND.md and this file disagree on the hex for a given name")
        print("| Token | BRAND.md | This file |")
        print("|---|---|---|")
        for name, src, tgt in drifts:
            print(f"| `{name}` | `{src}` | `{tgt}` |")

    if orphans:
        print("\n### ❌ Brand hexes absent from this file (not present under ANY name)")
        print("These colours are defined in BRAND.md but nowhere in this CSS.")
        print("Either add them or retire them from BRAND.md.")
        for name, hex_src in orphans:
            print(f"- `{hex_src}` — BRAND.md calls this `{name}`")

    if covered:
        # Show only interesting cases: where the name doesn't match (alias used)
        aliased = [(s, h, tgts) for s, h, tgts in covered if s not in tgts]
        if aliased:
            print("\n### ℹ️  Aliased — same hex, different name in this file")
            for src_name, hex_val, tgt_names in aliased[:10]:
                tgts_str = ", ".join(f"`{t}`" for t in tgt_names)
                print(f"- `{hex_val}` — BRAND.md: `{src_name}` · this file: {tgts_str}")
            if len(aliased) > 10:
                print(f"- _(and {len(aliased) - 10} more)_")

    if extra:
        print("\n### ℹ️  Extra hexes in this file (not tracked in BRAND.md)")
        # Dedup extras by hex
        seen_hexes = set()
        for name, hex_tgt in extra:
            if hex_tgt in seen_hexes:
                continue
            seen_hexes.add(hex_tgt)
            print(f"- `{hex_tgt}` (e.g. `{name}`) — in CSS; add to BRAND.md or retire from CSS")

    # Drifts are failures. Orphans are failures (real brand hexes missing).
    # Aliased / name-mismatches / extras are informational.
    return not drifts and not orphans


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip())
    p.add_argument("brand_md", help="Path to BRAND.md (the source of truth)")
    p.add_argument(
        "targets",
        nargs="*",
        help="Target CSS files to check against BRAND.md (positional)",
    )
    p.add_argument(
        "--target",
        action="append",
        default=[],
        help="Target CSS file (can be passed multiple times)",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Also fail on missing or extra tokens (default: only fail on drifts)",
    )
    args = p.parse_args()

    brand_md_path = Path(args.brand_md)
    if not brand_md_path.exists():
        print(f"ERROR: {brand_md_path} not found", file=sys.stderr)
        return 2

    targets = [Path(t) for t in args.targets + args.target]
    if not targets:
        print("ERROR: provide at least one target CSS file", file=sys.stderr)
        return 2

    missing_files = [t for t in targets if not t.exists()]
    if missing_files:
        for m in missing_files:
            print(f"ERROR: {m} not found", file=sys.stderr)
        return 2

    print(f"# Token consistency check\n\nSource: `{brand_md_path}`")
    source = parse_markdown_tokens(brand_md_path)
    print(f"\nFound {len(source)} colour tokens in BRAND.md.")

    all_clean = True
    strict_fail = False

    for target in targets:
        clean = check_file(source, target)
        if not clean:
            all_clean = False
        if args.strict:
            target_tokens = parse_css_tokens(target)
            _, _, missing, extra = compare(source, target_tokens)
            if missing or extra:
                strict_fail = True

    print()
    if not all_clean:
        print("❌ **FAIL** — one or more tokens drifted between BRAND.md and target CSS.")
        print("Fix the discrepancies, then re-run.")
        return 1
    if strict_fail:
        print("❌ **FAIL (strict)** — missing or extra tokens detected.")
        print("Either add to BRAND.md or remove from CSS, then re-run.")
        return 1
    print("✓ All tracked tokens are consistent between BRAND.md and target CSS files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
