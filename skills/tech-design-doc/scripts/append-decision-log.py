#!/usr/bin/env python3
"""append-decision-log.py — append a one-row decision log entry to DECISIONS.md.

Pulls Title / Status / Author / Date from the doc's frontmatter status table.
Creates DECISIONS.md with a header if it doesn't exist.

Usage:
    append-decision-log.py <path-to-doc.md> [--log DECISIONS.md] [--decision-date YYYY-MM-DD]

If the doc's status is not Accepted/Rejected/Superseded, prompts before logging.
"""
from __future__ import annotations
import argparse
import re
import sys
from datetime import date
from pathlib import Path

DEFAULT_LOG_HEADER = """# Decision log

One row per accepted/rejected technical design decision. Auto-appended by
`~/.claude/skills/tech-design-doc/scripts/append-decision-log.py`.

| Date | Title | Status | Author | Doc |
|------|-------|--------|--------|-----|
"""


def parse_status_table(content: str) -> dict[str, str]:
    """Return dict of field→value from the status header table."""
    fields = {}
    head = "\n".join(content.splitlines()[:60])
    for m in re.finditer(r"^\|\s*([A-Za-z][\w\s/\-()]+?)\s*\|\s*([^\|\n]+?)\s*\|\s*$", head, re.M):
        key, val = m.group(1).strip(), m.group(2).strip()
        if key.lower() in {"field", "---", "value"}:
            continue
        fields[key.lower()] = val
    return fields


def extract_title(content: str) -> str:
    m = re.search(r"^#\s+(.+?)\s*$", content, re.M)
    return m.group(1).strip() if m else "(untitled)"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("doc", type=Path, help="Path to the design doc markdown file")
    ap.add_argument("--log", type=Path, default=None,
                    help="Path to DECISIONS.md (default: <doc-parent>/DECISIONS.md)")
    ap.add_argument("--decision-date", default=None,
                    help="Decision date YYYY-MM-DD (default: today)")
    ap.add_argument("--force", action="store_true", help="Append even if status is not Accepted")
    args = ap.parse_args()

    if not args.doc.exists():
        print(f"error: doc not found: {args.doc}", file=sys.stderr)
        sys.exit(2)

    content = args.doc.read_text(encoding="utf-8")
    fields = parse_status_table(content)
    title = extract_title(content).lstrip("# ").strip()
    status = fields.get("status", "(unknown)")
    author = fields.get("author", fields.get("author(s)", fields.get("authors", "(unknown)")))
    decision_date = args.decision_date or fields.get("decision date") or date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", decision_date):
        decision_date = date.today().isoformat()

    if status not in {"Accepted", "Rejected", "Superseded"} and not args.force:
        print(f"warning: doc status is '{status}' (not Accepted/Rejected/Superseded).", file=sys.stderr)
        print("        Use --force to append anyway, or update the doc's status first.", file=sys.stderr)
        sys.exit(1)

    log_path = args.log or (args.doc.parent / "DECISIONS.md")
    if not log_path.exists():
        log_path.write_text(DEFAULT_LOG_HEADER, encoding="utf-8")
        print(f"created new log: {log_path}")

    rel_doc = args.doc.relative_to(log_path.parent) if log_path.parent in args.doc.parents else args.doc

    # Escape | in title
    safe_title = title.replace("|", "\\|")
    row = f"| {decision_date} | {safe_title} | {status} | {author} | [{rel_doc}]({rel_doc}) |\n"

    with log_path.open("a", encoding="utf-8") as f:
        f.write(row)

    print(f"✓ Appended to {log_path}:")
    print(f"  {row.strip()}")


if __name__ == "__main__":
    main()
