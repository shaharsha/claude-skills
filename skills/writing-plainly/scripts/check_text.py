#!/usr/bin/env python3
"""Flag the mechanical signs of hard-to-read or AI-sounding text in a draft.

Usage:
    python3 check_text.py draft.md [--genre chat|email|pr|ticket|doc] [--max-words N]
    python3 check_text.py - --genre chat < draft.md

Every finding is a prompt to look again, not a verdict: a human can use
"crucial" once. What reads as machine-made is a cluster. Code blocks and
`inline code` are skipped. Exit code is 0 unless --strict is given and
something was flagged.
"""
import argparse
import re
import sys

# Words whose frequency jumped after ChatGPT (Kobak et al. 2025, Wikipedia
# "Signs of AI writing", Russell et al. 2025). One is fine; several is a tell.
STRONG_WORDS = [
    "delve", "delves", "delved", "delving", "tapestry", "testament", "underscore",
    "underscores", "underscored", "underscoring", "pivotal", "showcase",
    "showcases", "showcasing", "vibrant", "intricate", "intricacies",
    "meticulous", "meticulously", "garner", "garnered", "bolstered", "boasts",
    "interplay", "realm", "multifaceted", "seamless", "seamlessly", "embark",
]
WEAK_WORDS = [
    "crucial", "foster", "fostering", "enhance", "enhances", "enhancing",
    "robust", "leverage", "leveraging", "landscape", "enduring", "valuable",
    "comprehensive", "streamline", "holistic", "paradigm", "synergy", "notably",
    "moreover", "furthermore", "additionally", "navigate", "navigating",
    "quietly", "dependable", "nuanced", "insightful", "elevate", "unlock",
]

PATTERNS = [
    # (label, regex, genres it applies to, or None for all)
    ("stock contrast 'not just X, but Y'",
     r"\bnot (?:just|only|merely|simply)\b[^.!?\n]{0,80}\bbut\b", None),
    ("stock contrast 'it's not X, it's Y'",
     r"\b(?:it|this|that)(?:'s| is) not\b[^.!?\n]{0,60}[,;:]\s*(?:it|this|that)(?:'s| is)\b", None),
    ("inflated significance (check the plain verb or the fact reads better)",
     r"\b(?:stands as|serves as|is a testament|a testament to|plays? an? (?:crucial|pivotal|key|vital|significant) role|marks? a (?:shift|turning point|milestone)|underscor\w* the importance|in today's (?:fast|rapidly|ever)|ever-evolving|evolving landscape)\b", None),
    ("trailing '-ing' significance clause",
     r",\s(?:highlighting|underscoring|emphasizing|showcasing|reflecting|symbolizing|fostering|paving the way)\b", None),
    ("chatbot opener/closer",
     r"(?:\bI hope (?:this|my) (?:email|message|note) finds you\b|\bI hope you(?:'re| are) (?:doing )?well\b|\bhope (?:this|that) helps\b|\bgreat question\b|^\s*(?:certainly|absolutely|of course)[!,.]|^\s*here(?:'s| is) a (?:quick|short|brief)\b|\blet me know if you have any\b|\bfeel free to\b|\bdon'?t hesitate to\b|\bhappy to help\b)", None),
    ("hedge / filler",
     r"\b(?:it(?:'s| is) (?:important|worth) (?:to note|noting)|it should be noted|due to the fact that|at the end of the day|needless to say)\b", None),
    ("vague attribution",
     r"\b(?:experts (?:say|agree|argue)|studies show|research shows|observers (?:note|have)|industry reports)\b", None),
    ("summary opener (in a short message, just stop)",
     r"^\s*(?:in summary|in conclusion|to sum up|to summarize|overall|tl;dr)(?=[\s,:])", ("chat", "email")),
]

HEBREW = re.compile(r"[֐-׿]")
HEBREW_AI = ["בנוסף", "יתרה מכך", "יתרה מזאת", "חשוב לציין", "ראוי לציין", "באופן משמעותי", "לסיכום", "מעבר לכך"]
# Bullet or number marker, then any markdown emphasis, quote marks or emoji before the first word.
LEAD = re.compile(r"^\s*(?:(?:[-*•>]|\d+[.)])\s+)?[\s*_~\"'(“”‘’☀-➿\U0001F300-\U0001FAFF️]*")


def strip_code(text):
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else re.sub(r"`[^`\n]*`", "code", line))
    return out


def sentences(lines):
    """Split per line first: a bullet, heading or line break ends a sentence."""
    out = []
    for line in lines:
        line = re.sub(r"^\s*(?:#{1,6}\s+|[-*•>]\s+|\d+[.)]\s+)", "", line).strip()
        if line:
            out += [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[\"'(\[A-Za-z֐-׿0-9])", line) if s.strip()]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="file to check, or - for stdin")
    ap.add_argument("--genre", choices=["chat", "email", "pr", "ticket", "doc"], default="chat")
    ap.add_argument("--max-words", type=int, default=None, help="flag drafts longer than this")
    ap.add_argument("--strict", action="store_true", help="exit 1 when anything is flagged")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.path == "-" else open(a.path, encoding="utf-8").read()
    lines = strip_code(raw)
    raw_lines = raw.splitlines()
    text = "\n".join(lines)
    words = re.findall(r"\S+", raw)
    findings = []

    def flag(lineno, label, snippet):
        if lineno and snippet.strip() == lines[lineno - 1].strip():
            snippet = raw_lines[lineno - 1]  # show the line as written, not with code masked
        findings.append((lineno, label, snippet.strip()[:90]))

    for i, line in enumerate(lines, 1):
        if "—" in line:
            flag(i, "em dash (restructure: period, comma, colon or parentheses)", line)
        if "–" in line:
            flag(i, "en dash (a plain hyphen reads more naturally)", line)
        for label, rx, genres in PATTERNS:
            if genres and a.genre not in genres:
                continue
            for m in re.finditer(rx, line, re.I):
                flag(i, label, m.group(0))
        if re.match(r"^\s*(?:(?:[-*•]|\d+[.)])\s*)?\*{1,2}[^*\n]{1,40}?[:.]?\*{1,2}\s*[:.]", line) or \
           re.match(r"^\s*(?:(?:[-*•]|\d+[.)])\s*)?\*{1,2}[^*\n]{1,40}?[:.]\*{1,2}", line):
            flag(i, "bold lead-in label", line)
        if a.genre in ("chat", "email"):
            if re.match(r"^\s*#{1,6}\s", line):
                flag(i, "heading in a message (write plain sentences)", line)
            if re.match(r"^\s*[A-Z][\w']*(?:\s+[\w']+){0,3}:(?:\s|$)", line) and \
               not re.match(r"^\s*(?:Re|Fwd|Subject|To|Cc|Hi|Hey|Dear|P\.?S|Note|Update|FYI)\b", line):
                flag(i, "label opener (a 'Label:' line reads like a report; check it reads as a sentence)", line)
        h = re.match(r"^\s*#{1,6}\s+(.+)", line)
        if h:
            ws = [w for w in re.findall(r"[A-Za-z]+", h.group(1)) if len(w) > 3]
            if len(ws) >= 2 and all(w[0].isupper() for w in ws):
                flag(i, "Title Case heading (use sentence case unless these are names)", line)
        if HEBREW.search(line):
            if "→" in line:
                flag(i, "right arrow in Hebrew text (use ← for 'leads to')", line)
            for s in re.split(r"(?<=[.!?])\s+", line.strip()):
                first = LEAD.sub("", s)[:1]
                if first and not HEBREW.match(first):
                    flag(i, "Hebrew sentence starts with a non-Hebrew character (renders left-to-right)", s)
            for w in HEBREW_AI:
                if re.search(rf"(?<![֐-׿]){w}(?![֐-׿])", line):
                    flag(i, "formal Hebrew connector", w)

    lower = re.findall(r"[a-z']+", text.lower())
    strong = sorted({w for w in lower if w in STRONG_WORDS})
    weak = [w for w in lower if w in WEAK_WORDS]
    if strong:
        flag(0, "AI-associated words (fine alone, a tell in clusters; check each)", ", ".join(strong))
    if len(weak) >= 3:
        flag(0, "cluster of overused words", ", ".join(sorted(set(weak))))

    sents = [s for s in sentences(lines) if len(s.split()) > 2]
    for s in sents:
        if len(s.split()) > 25:
            flag(0, f"long sentence ({len(s.split())} words)", s)
    if a.max_words and len(words) > a.max_words:
        flag(0, f"over budget: {len(words)} words > {a.max_words}", "")

    avg = sum(len(s.split()) for s in sents) / len(sents) if sents else 0
    print(f"{len(words)} words, {len(sents)} sentences, average {avg:.1f} words per sentence")
    if not findings:
        print("No mechanical flags. Still read it aloud and ask what the reader can cut.")
    for lineno, label, snip in findings:
        where = f"line {lineno}" if lineno else "text"
        print(f"- {where}: {label}" + (f": {snip}" if snip else ""))
    sys.exit(1 if (a.strict and findings) else 0)


if __name__ == "__main__":
    main()
