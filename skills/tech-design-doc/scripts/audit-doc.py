#!/usr/bin/env python3
"""audit-doc.py — static audit of a technical design doc against the skill's house rules.

Usage:
    audit-doc.py <path-to-doc.md>

Checks (errors fail the audit; warnings don't):
    [error]   Status header present with required fields
    [error]   Summary section present and not empty
    [error]   Goals section present
    [error]   Non-goals section present (warns for mini-adr)
    [error]   Alternatives section present with ≥3 alternatives
    [error]   Decision log row drafted
    [warn]    Buzzword goals (scalable, modern, fast, etc. without numbers nearby)
    [warn]    No diagrams (mermaid block) in standard+ docs
    [warn]    Partner-mode: glossary present
    [warn]    Partner-mode: decision-ownership table present
    [warn]    Cross-cutting checklist filled (no silent omissions)
    [warn]    Implementation manual smell (lots of code blocks with schemas)

Exit codes:
    0 — all checks pass
    1 — one or more errors
    2 — usage error
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

# ANSI colors for terminal output
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Buzzword adjectives that need a quantified neighbor
BUZZWORDS = [
    "scalable", "flexible", "reliable", "modern", "fast", "low-cost",
    "secure", "robust", "simple", "elegant", "lightweight", "performant",
    "maintainable", "best-in-class", "cutting-edge",
]

# Sections that count as "Summary" — accept "Context, Goals, Non-Goals" composite too
SUMMARY_HEADERS = re.compile(r"^#+\s*(\d+\.\s+)?(summary|tl;?dr|overview|executive summary|context\b)", re.I | re.M)
# Goals can be a heading OR a bold inline label "**Goals:**"
GOALS_HEADERS = re.compile(r"^#+\s*(\d+\.\s+)?(goals?\b)", re.I | re.M)
GOALS_INLINE = re.compile(r"\*\*goals?:\*\*", re.I)
NONGOALS_HEADERS = re.compile(r"^#+\s*(non[\s-]?goals?)\b", re.I | re.M)
NONGOALS_INLINE = re.compile(r"\*\*non[\s-]?goals?:\*\*", re.I)
ALTERNATIVES_HEADERS = re.compile(r"^#+\s*(\d+\.\s+)?alternatives?\s+considered\b", re.I | re.M)
GLOSSARY_HEADERS = re.compile(r"^#+\s*(\d+\.\s+)?glossary\b", re.I | re.M)
DECISION_OWNERSHIP_HEADERS = re.compile(r"^#+\s*(\d+\.\s+)?decision[\s-]?ownership\b", re.I | re.M)
CROSS_CUTTING_HEADERS = re.compile(r"^#+\s*(\d+\.\s+)?cross[\s-]?cutting", re.I | re.M)
# A doc that has explicit Security / Privacy / Observability sections is doing cross-cutting,
# even if it's not labeled "cross-cutting concerns"
SECURITY_SECTION = re.compile(r"^#+\s*(\d+\.\s+)?(security(\s*&\s*compliance)?|privacy|observability)\b", re.I | re.M)
DECISION_LOG_HEADERS = re.compile(r"^#+\s*decision[\s-]?log[\s-]?row\b", re.I | re.M)

# Markdown heading regex (any level)
HEADING_RE = re.compile(r"^(#+)\s+(.+?)\s*$", re.M)

# Status header field regex (markdown table or list) — accept hyphens and (s) suffixes
STATUS_FIELD_RE = re.compile(r"^\s*\|\s*([A-Za-z][\w\s/\-()]+?)\s*\|", re.M)


class AuditResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passes: list[str] = []

    def err(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def ok(self, msg: str):
        self.passes.append(msg)

    @property
    def exit_code(self) -> int:
        return 1 if self.errors else 0


def detect_template_kind(content: str) -> str:
    """Return one of: 'mini-adr', 'standard', 'heavyweight', 'partner', 'unknown'."""
    if re.search(r"^#\s*ADR-\d", content, re.M):
        return "mini-adr"
    if "## 8. Decision ownership" in content or DECISION_OWNERSHIP_HEADERS.search(content):
        return "partner"
    if "Production Readiness Review" in content or re.search(r"^### [A-G]\.\s+", content, re.M):
        return "heavyweight"
    if re.search(r"^##\s*\d+\.\s+", content, re.M):
        return "standard"
    return "unknown"


def extract_section(content: str, header_re: re.Pattern) -> str | None:
    """Extract the body of a section starting at a header matched by header_re,
    up to the next heading at the same or higher level."""
    m = header_re.search(content)
    if not m:
        return None
    start_idx = m.start()
    # Find heading level
    line_start = content.rfind("\n", 0, m.start()) + 1
    line = content[line_start:m.end()]
    level_match = re.match(r"^(#+)", line)
    if not level_match:
        return None
    level = len(level_match.group(1))
    # Find next heading at same or higher level
    after = m.end()
    pat = re.compile(r"^#{1," + str(level) + r"}\s+", re.M)
    nxt = pat.search(content, after)
    end_idx = nxt.start() if nxt else len(content)
    return content[start_idx:end_idx]


def _matches_field(target: str, fields: set[str]) -> bool:
    """Match a required field name flexibly: 'Author' matches 'Author', 'Authors', 'Author(s)'."""
    t = target.lower().rstrip("s").rstrip("(").rstrip(")")
    for f in fields:
        f_norm = f.lower().rstrip("s").rstrip(")").rstrip("(").rstrip()
        if f_norm == t or f_norm.startswith(t):
            return True
    return False


def check_status_header(content: str, result: AuditResult, kind: str):
    required = {"Status", "Author"}
    if kind != "mini-adr":
        required |= {"Version"}
    # First ~60 lines should contain a status table OR a bold-key list
    head = "\n".join(content.splitlines()[:60])
    fields = set()
    # Pattern 1: markdown table rows
    for m in STATUS_FIELD_RE.finditer(head):
        f = m.group(1).strip()
        if f.lower() not in {"field", "value", "---"}:
            fields.add(f)
    # Pattern 2: bold-key inline list, "**Version:** v0.1"
    for m in re.finditer(r"\*\*([A-Za-z][\w\s/\-()]+?):\*\*", head):
        fields.add(m.group(1).strip())
    # Pattern 3: bold-key with em-dash, "**Version** — v0.1"
    for m in re.finditer(r"\*\*([A-Za-z][\w\s/\-()]+?)\*\*\s*[—\-:]\s+\S", head):
        fields.add(m.group(1).strip())
    # "Last updated" counts as Last edited; accept either
    if any(f.lower() in {"last updated", "last-updated"} for f in fields):
        fields.add("Last edited")
    # Version: accept "Draft v0.1 — date" patterns where Version isn't a field
    if "Version" not in {f for f in fields if f.lower() == "version"}:
        if re.search(r"^\*\*Version[:\s]", head, re.M | re.I) or re.search(r"v\d+\.\d+", head):
            fields.add("Version")
    missing = [f for f in required if not _matches_field(f, fields)]
    if missing:
        result.err(f"Status header missing required field(s): {', '.join(missing)}")
    else:
        result.ok("Status header present with required fields")
    # Check status value isn't blank (table form)
    status_match = re.search(r"\|\s*Status\s*\|\s*([^\|]+?)\s*\|", head, re.I)
    if status_match:
        val = status_match.group(1).strip()
        if val in {"", "_(filled when accepted)_", "TBD", "(TBD)"}:
            result.warn(f"Status value looks empty/placeholder: '{val}'")


def check_summary(content: str, result: AuditResult):
    sec = extract_section(content, SUMMARY_HEADERS)
    if not sec:
        result.err("Summary / TL;DR / Overview section not found")
        return
    # Body must have at least 30 chars after the heading
    body = re.sub(r"^#+.+?\n", "", sec, count=1, flags=re.M).strip()
    if len(body) < 30:
        result.err("Summary section is empty or near-empty")
    elif "BLUF" in body and "{{" not in body:
        result.ok("Summary section present and non-empty")
    else:
        result.ok("Summary section present and non-empty")


def check_goals(content: str, result: AuditResult, kind: str):
    sec = extract_section(content, GOALS_HEADERS)
    if not sec and GOALS_INLINE.search(content):
        # Goals as bold inline label "**Goals:**" — accept and audit the surrounding paragraph
        m = GOALS_INLINE.search(content)
        # Take the next ~800 chars as the goals body
        body = content[m.end(): m.end() + 800]
        sec = "## Goals\n" + body
    if not sec:
        if kind == "mini-adr":
            return  # ADRs don't always have explicit goals
        result.err("Goals section not found")
        return
    body = re.sub(r"^#+.+?\n", "", sec, count=1, flags=re.M)
    # Buzzword check: each buzzword on a line should have a number nearby (±60 chars)
    for line in body.split("\n"):
        if not line.strip() or line.strip().startswith("_"):
            continue
        for bw in BUZZWORDS:
            if re.search(rf"\b{bw}\b", line, re.I):
                # Look for a number within the line
                if not re.search(r"\d", line):
                    result.warn(
                        f"Buzzword goal without quantification: '{bw}' in line:\n    {line.strip()[:120]}"
                    )
                    break
    result.ok("Goals section present")


def check_nongoals(content: str, result: AuditResult, kind: str):
    sec = extract_section(content, NONGOALS_HEADERS)
    if not sec and NONGOALS_INLINE.search(content):
        result.ok("Non-Goals section present (inline)")
        return
    if not sec:
        if kind == "mini-adr":
            return
        result.err("Non-Goals section not found (load-bearing for scope clarity)")
        return
    result.ok("Non-Goals section present")


def check_alternatives(content: str, result: AuditResult, kind: str):
    if kind == "mini-adr":
        # Mini-ADRs can have inline alternatives
        if re.search(r"^#+\s*alternatives?\s+considered", content, re.I | re.M):
            result.ok("Alternatives section present (mini-adr inline)")
            return
        if re.search(r"^-\s*\*\*Alternative", content, re.I | re.M):
            result.ok("Alternatives present (inline)")
            return
        result.warn("Mini-ADR has no Alternatives section — even ADRs benefit from naming alternatives")
        return

    sec = extract_section(content, ALTERNATIVES_HEADERS)
    if not sec:
        result.err("Alternatives Considered section not found")
        return
    body = re.sub(r"^#+.+?\n", "", sec, count=1, flags=re.M)
    # Count alternatives — looking for headers like "### A1." or "### A2." or "### Status quo"
    alts = re.findall(r"^###\s+(?:A\d+\.|Status quo|Alt|Alternative\b|Proposal\b)", body, re.M | re.I)
    if len(alts) < 3:
        result.err(f"Alternatives Considered has {len(alts)} alternative sub-sections; need ≥3 (status quo + incremental + proposal at minimum)")
    else:
        result.ok(f"Alternatives Considered has {len(alts)} sub-sections")
    # Check for "Why appealing" pattern
    why_appealing = len(re.findall(r"why\s+appealing", body, re.I))
    if len(alts) >= 3 and why_appealing < len(alts) - 1:
        result.warn(f"Only {why_appealing} 'Why appealing' lines for {len(alts)} alternatives — every alt should have one (even rejected ones)")


def check_decision_log(content: str, result: AuditResult):
    if not DECISION_LOG_HEADERS.search(content):
        result.err("No Decision log row section found — required for institutional memory")
        return
    # Check for a markdown table row drafted
    sec = extract_section(content, DECISION_LOG_HEADERS)
    if sec and re.search(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|", sec):
        result.ok("Decision log row drafted")
    else:
        result.warn("Decision log row section present but template row not filled in")


def check_glossary_partner(content: str, result: AuditResult):
    if not GLOSSARY_HEADERS.search(content):
        result.warn("Partner-mode: Glossary section missing (mandatory in partner-mode)")
    else:
        result.ok("Partner-mode: Glossary section present")


def check_decision_ownership_partner(content: str, result: AuditResult):
    if not DECISION_OWNERSHIP_HEADERS.search(content):
        result.warn("Partner-mode: Decision ownership table missing")
    else:
        result.ok("Partner-mode: Decision ownership table present")


def check_diagrams(content: str, result: AuditResult, kind: str):
    if kind == "mini-adr":
        return
    has_mermaid = "```mermaid" in content
    if not has_mermaid:
        result.warn("No mermaid diagrams found — required minimum is 1 C4 context + 1 sequence diagram for standard+ docs")
    else:
        # Count blocks
        n = content.count("```mermaid")
        result.ok(f"Diagrams present ({n} mermaid block(s))")
        # Check for sequence with retry/timeout/fail keyword
        if "sequenceDiagram" in content:
            if not re.search(r"retry|timeout|fail|error|alt|opt|503", content, re.I):
                result.warn("Sequence diagram present but no retry/timeout/failure keywords found — happy-path-only diagrams imply false completeness")


def check_cross_cutting(content: str, result: AuditResult, kind: str):
    if kind == "mini-adr":
        return
    sec = extract_section(content, CROSS_CUTTING_HEADERS)
    if not sec:
        # Fallback: doc may have separate Security / Privacy / Observability sections
        # rather than a single "Cross-cutting concerns" block.
        sec_count = len(SECURITY_SECTION.findall(content))
        if sec_count >= 1:
            result.warn(f"No 'Cross-cutting concerns' section, but {sec_count} related section(s) found (Security/Privacy/Observability). Consider consolidating into a single checklist.")
            return
        result.err("Cross-cutting concerns section not found")
        return
    # Count items two ways:
    #  1) Standard checklist rows: | Concern | ✅/⚠️/N/A | notes |
    rows = re.findall(r"\|\s*[A-Z][\w/\s\-]+\|\s*(✅|⚠️|N/A)", sec)
    #  2) Heavyweight PRR sub-sections: "### A. Feature enablement", "### B. Rollout..."
    prr_subs = re.findall(r"^###\s+[A-G]\.\s+\w+", sec, re.M)
    if rows >= [] and len(rows) >= 4:
        result.ok(f"Cross-cutting checklist filled ({len(rows)} rows)")
    elif len(prr_subs) >= 5:
        # Heavyweight PRR format — check that questions are answered (not just listed)
        # A filled PRR sub-section has prose after each question. Naive check: ratio of bullet lines to "?" lines.
        question_lines = len(re.findall(r"^- _", sec, re.M))
        answered_hints = len(re.findall(r"^[A-Za-z]", sec, re.M))
        if question_lines > 0 and answered_hints < question_lines:
            result.warn(f"PRR has {len(prr_subs)} sub-sections with {question_lines} question stubs but no answers — fill in each question or mark N/A with reason")
        else:
            result.ok(f"PRR present ({len(prr_subs)} sub-sections)")
    else:
        result.warn(f"Cross-cutting checklist looks sparse ({len(rows)} filled rows, {len(prr_subs)} PRR sub-sections); expected 8 standard rows or 5+ PRR sub-sections")
    # Find rows with empty notes
    empty_notes = re.findall(r"\|\s*[A-Z][\w/\s\-]+\|\s*(✅|⚠️|N/A)\s*\|\s*\.\.\.\s*\|", sec)
    if empty_notes:
        result.warn(f"{len(empty_notes)} cross-cutting rows have placeholder '...' instead of real notes")


def check_placeholder_content(content: str, result: AuditResult, kind: str):
    """Warn if key sections look like unfilled scaffold (mostly italic placeholder text or '...' stubs)."""
    # Italic-only line: `_..._` or `_...._` filling a whole non-empty line (allow leading bullet)
    italic_only_re = re.compile(r"^[\s\-\*]*_[^_\n]{20,}_\s*$", re.M)
    placeholder_phrases = [
        "your proposal", "your reasoning", "fill me in", "TBD", "(TBD)", "_e.g._",
        "[date]", "[reasons]", "[link]", "_link to_", "_what +", "_what,", "Quantified",
        "Replace with actual", "_3-7 quantified", "_5-10 quantified",
        "_Lead with_", "_Numbered list_", "_Mark explicit",
    ]
    # Detect main sections by their headings
    sections_to_check = {
        "Summary": SUMMARY_HEADERS,
        "Goals": GOALS_HEADERS,
        "Alternatives Considered": ALTERNATIVES_HEADERS,
    }
    flagged = []
    for label, pat in sections_to_check.items():
        sec = extract_section(content, pat)
        if not sec:
            continue
        body = re.sub(r"^#+.+?\n", "", sec, count=1, flags=re.M).strip()
        if not body:
            continue
        nonblank_lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith("|")]
        if not nonblank_lines:
            continue
        italic_lines = sum(1 for l in nonblank_lines if italic_only_re.match(l))
        phrase_hits = sum(1 for p in placeholder_phrases if p.lower() in body.lower())
        # >40% italic-only OR ≥3 placeholder phrases → flag
        if (italic_lines / max(len(nonblank_lines), 1)) > 0.4 or phrase_hits >= 3:
            flagged.append(f"{label} ({italic_lines}/{len(nonblank_lines)} italic-only lines, {phrase_hits} placeholder phrases)")
    if flagged:
        result.warn("Placeholder content detected — fresh scaffold not yet filled in: " + "; ".join(flagged))


def check_implementation_manual_smell(content: str, result: AuditResult):
    code_blocks = re.findall(r"```(\w+)?\n.*?```", content, re.S)
    schema_blocks = sum(1 for b in code_blocks if re.search(r"\b(string|number|integer|UUID|VARCHAR|CREATE TABLE|interface\s+\w+\s*\{)", b))
    if schema_blocks >= 4:
        result.warn(f"{schema_blocks} schema-like code blocks — design doc may be turning into an implementation manual; link to API spec instead")


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(2)

    content = path.read_text(encoding="utf-8")
    kind = detect_template_kind(content)
    result = AuditResult()

    print(f"{BOLD}Auditing:{RESET} {path}")
    print(f"{BOLD}Detected template kind:{RESET} {kind}")
    print()

    check_status_header(content, result, kind)
    check_summary(content, result)
    check_goals(content, result, kind)
    check_nongoals(content, result, kind)
    check_alternatives(content, result, kind)
    check_decision_log(content, result)
    check_diagrams(content, result, kind)
    check_cross_cutting(content, result, kind)
    check_placeholder_content(content, result, kind)
    check_implementation_manual_smell(content, result)
    if kind == "partner":
        check_glossary_partner(content, result)
        check_decision_ownership_partner(content, result)

    # Print results grouped
    if result.passes:
        print(f"{GREEN}{BOLD}PASS{RESET} ({len(result.passes)})")
        for p in result.passes:
            print(f"  {GREEN}✓{RESET} {p}")
        print()
    if result.warnings:
        print(f"{YELLOW}{BOLD}WARNINGS{RESET} ({len(result.warnings)})")
        for w in result.warnings:
            print(f"  {YELLOW}⚠{RESET}  {w}")
        print()
    if result.errors:
        print(f"{RED}{BOLD}ERRORS{RESET} ({len(result.errors)})")
        for e in result.errors:
            print(f"  {RED}✗{RESET} {e}")
        print()

    if result.errors:
        print(f"{RED}{BOLD}Audit FAILED{RESET} — {len(result.errors)} error(s), {len(result.warnings)} warning(s)")
    elif result.warnings:
        print(f"{YELLOW}{BOLD}Audit PASSED with {len(result.warnings)} warning(s){RESET}")
    else:
        print(f"{GREEN}{BOLD}Audit CLEAN{RESET} ✨")

    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
