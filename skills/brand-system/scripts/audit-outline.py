#!/usr/bin/env python3
"""audit-outline.py — validate a BRAND.md against the canonical 20-section outline.

Checks:
- All 20 sections (§0–§20) are present as `## N. …` headings.
- §2 signature primitive lists ≥8 use-sites.
- §3 signature moves lists ≥3 items.
- §14 accessibility includes a contrast matrix.
- §20 decision log has at least one dated entry.
- No unresolved `{{TODO}}` / `{{PLACEHOLDER}}` markers in finalized sections.

Exits 0 on pass, 1 on structural failure, 2 on invalid input.

Usage:
  audit-outline.py BRAND.md
  audit-outline.py --input BRAND.md --strict  (fail on {{TODO}})
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CANONICAL_SECTIONS = [
    (0, "The idea"),
    (1, "Reading the mark"),
    (2, "signature|primitive|voice dot|accent"),
    (3, "Signature moves"),
    (4, "Brand essence"),
    (5, "Logo system"),
    (6, "Colou?r"),
    (7, "Typography"),
    (8, "Iconography"),
    (9, "Spacing|layout"),
    (10, "Surfaces|Materials"),
    (11, "Motion"),
    (12, "Imagery|illustration"),
    (13, "Voice|tone"),
    (14, "Accessibility"),
    (15, "Reference set"),
    (16, "Anti-patterns"),
    (17, "Implementation|Tailwind|@theme"),
    (18, "Components"),
    (19, "Migration"),
    (20, "What this.*not|Decision log"),
]


def check_sections(md: str) -> list[tuple[int, bool, str]]:
    """For each canonical section, return (number, present, keyword matched)."""
    results = []
    for num, pattern in CANONICAL_SECTIONS:
        # Match `## N. ...` or `## N ...` with the keyword anywhere in the heading line
        rx = re.compile(
            rf"^##\s+{num}\.?\s+.*(?:{pattern}).*$",
            re.IGNORECASE | re.MULTILINE,
        )
        m = rx.search(md)
        results.append((num, bool(m), pattern))
    return results


def check_primitive_use_sites(md: str) -> tuple[int, int]:
    """Count table rows in §2 that describe a use-site of the signature primitive."""
    m = re.search(
        r"(?ms)^##\s+2\.?\s.*?(?=^##\s|\Z)",
        md,
    )
    if not m:
        return 0, 8
    section = m.group(0)
    # Count markdown table rows that aren't the header or divider
    rows = [
        line
        for line in section.splitlines()
        if line.strip().startswith("|") and not re.match(r"^\|\s*-+\s*\|", line.strip())
    ]
    # Subtract 1 for the header row
    use_sites = max(0, len(rows) - 1)
    return use_sites, 8


def check_signature_moves(md: str) -> tuple[int, int]:
    """Count numbered moves in §3."""
    m = re.search(r"(?ms)^##\s+3\.?\s.*?(?=^##\s|\Z)", md)
    if not m:
        return 0, 3
    section = m.group(0)
    # Match lines like "1. **something**"
    moves = re.findall(r"^\d+\.\s+\*\*", section, re.MULTILINE)
    return len(moves), 3


def check_contrast_matrix(md: str) -> bool:
    """§14 must contain a contrast ratio table or explicit ratio numbers."""
    m = re.search(r"(?ms)^##\s+14\.?\s.*?(?=^##\s|\Z)", md)
    if not m:
        return False
    section = m.group(0)
    # Heuristic: look for "X.X:1" ratios or "WCAG" + "4.5"
    has_ratios = bool(re.search(r"\b\d+(?:\.\d+)?:1\b", section))
    mentions_wcag = bool(re.search(r"WCAG\s*2\.[12]", section, re.IGNORECASE))
    return has_ratios or mentions_wcag


def check_decision_log(md: str) -> int:
    """Count dated entries in the Decision log (§20 or appended)."""
    m = re.search(r"(?mi)^(?:##\s+)?Decision log.*", md)
    if not m:
        return 0
    tail = md[m.end() :]
    # Match lines starting with a YYYY-MM-DD pipe
    dates = re.findall(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", tail, re.MULTILINE)
    return len(dates)


def check_todos(md: str) -> int:
    return len(re.findall(r"\{\{TODO[^}]*\}\}", md))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip())
    p.add_argument("input", nargs="?", help="Path to BRAND.md")
    p.add_argument("--input", dest="input_flag", help="Alternative: --input BRAND.md")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any {{TODO}} placeholders remain",
    )
    args = p.parse_args()

    path = args.input or args.input_flag
    if not path:
        print("ERROR: provide BRAND.md path as positional arg or --input", file=sys.stderr)
        return 2

    md_path = Path(path)
    if not md_path.exists():
        print(f"ERROR: {md_path} not found", file=sys.stderr)
        return 2

    md = md_path.read_text(encoding="utf-8")

    print(f"# Auditing {md_path}\n")

    # ── Section presence ─────────────────────────────────
    print("## Canonical 20-section outline\n")
    print("| § | Section | Status |")
    print("|:-:|---|:-:|")
    missing = []
    for num, present, pattern in check_sections(md):
        pretty = pattern.replace("|", " / ").replace(r"\?", "")
        mark = "✓" if present else "❌"
        if not present:
            missing.append(num)
        print(f"| {num} | {pretty} | {mark} |")

    # ── Required content checks ──────────────────────────
    print("\n## Content checks\n")

    failures: list[str] = []
    if missing:
        failures.append(f"Missing sections: §{', §'.join(str(n) for n in missing)}")

    primitive_count, primitive_required = check_primitive_use_sites(md)
    status = "✓" if primitive_count >= primitive_required else "❌"
    print(f"- §2 signature primitive use-sites: {primitive_count} (need ≥{primitive_required}) {status}")
    if primitive_count < primitive_required:
        failures.append(f"§2 has only {primitive_count} use-sites (need ≥{primitive_required})")

    moves_count, moves_required = check_signature_moves(md)
    status = "✓" if moves_count >= moves_required else "❌"
    print(f"- §3 signature moves: {moves_count} (need ≥{moves_required}) {status}")
    if moves_count < moves_required:
        failures.append(f"§3 has only {moves_count} moves (need ≥{moves_required})")

    has_contrast = check_contrast_matrix(md)
    status = "✓" if has_contrast else "❌"
    print(f"- §14 contrast matrix present: {status}")
    if not has_contrast:
        failures.append("§14 missing contrast ratios — run audit-contrast.py and paste output")

    log_entries = check_decision_log(md)
    status = "✓" if log_entries >= 1 else "❌"
    print(f"- Decision log dated entries: {log_entries} (need ≥1) {status}")
    if log_entries < 1:
        failures.append("Decision log has no dated entries")

    todo_count = check_todos(md)
    if args.strict:
        status = "✓" if todo_count == 0 else "❌"
        print(f"- Unresolved {{{{TODO}}}} placeholders: {todo_count} (strict: must be 0) {status}")
        if todo_count > 0:
            failures.append(f"{todo_count} {{{{TODO}}}} placeholders remain (strict mode)")
    else:
        print(f"- Unresolved {{{{TODO}}}} placeholders: {todo_count} (informational — rerun with --strict to fail)")

    print()

    if failures:
        print("❌ **FAIL** — the brand book is incomplete:")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("✓ All canonical checks pass.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
