#!/usr/bin/env python3
"""Make a Hebrew .srt display correctly in Kodi, VLC, Plex and TV players, without touching its words or
(unless asked) its timing. Works on a subtitle from any source.

  python3 -I fix_hebrew_srt.py in.srt "Movie (2013).heb.srt" [--shift 5.04] [--order auto|visual|logical]
                                 [--drop-cue N ...]

What it does, in order:
  1. Decodes cp1255 / UTF-8 (with or without BOM) and drops any old RTL control marks.
  2. Fixes punctuation order. Most ktuvit files are "visual": punctuation was typed at the wrong end so
     it looked right on players without RTL support (".טקסט", "...הפכפכים", "טקסט-"). A player with
     proper RTL support (Kodi, VLC, Plex) shows that reversed. --order auto (default) detects it; the fix swaps each line's leading and trailing
     punctuation runs. A file that is already logical is left alone.
  3. Shifts every cue by --shift seconds (positive = later), if given. Get the number from sync_check.py.
  4. Drops cues by number (--drop-cue), e.g. a release-info header cue ("BluRay ... FPS ... אורך").
  5. Writes UTF-8 with BOM, each Hebrew line wrapped in RLE (U+202B) ... PDF (U+202C), after leading tags.
     Players can misdetect Hebrew without the BOM (cp1255 shows as gibberish); without the marks, lines ending in numbers, English or
     punctuation render in the wrong order.
  6. Verifies: same cue count (minus drops), text with marks stripped equals the fixed text, no Hebrew
     line starts with sentence punctuation. Then prints cues a person should read: unbalanced brackets or
     a Hebrew line starting with a digit or Latin letter (the visual format scrambles those), and likely
     release-info cues near the start or end.
"""
import argparse
import re
import sys

TS = re.compile(r"^\s*(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")
HEB = re.compile("[א-ת]")
# Embedding/isolate controls from earlier tools are dropped; LRM/RLM (U+200E/F) are kept, because in visual
# files the uploader's RLM marks where the wrong-end punctuation stops ('."\u200f-כן' = '-כן ... ."').
MARKS = re.compile("[‪-‮⁦-⁩]")
PUN = ".,?!:;-…\"'()[]"
MIRROR = str.maketrans("()[]", ")(][")
LEAD_TAGS = re.compile(r"^((?:<[^>]+>|\{\\an\d\})*)(.*?)((?:<[^>]+>)*)$")
RELEASE_HINT = re.compile(r"(?i)\b(fps|bluray|blu-ray|brrip|bdrip|web-?dl|webrip|hdtv|dvdrip|x26[45]|1080p|720p|2160p)\b|אורך:|גרסה")


def decode(raw):
    for enc in ("utf-8-sig", "cp1255"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1"), "latin-1"


def parse(text):
    text = MARKS.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.split("\n")
        k = next((i for i, l in enumerate(lines) if TS.match(l)), None)
        if k is None:
            continue
        g = [int(x) for x in TS.match(lines[k]).groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        body = [l.strip() for l in lines[k + 1:] if l.strip()]
        if body:
            cues.append([start, end, body])
    return cues


def split_line(l):
    return LEAD_TAGS.match(l).groups()


def leading_pun(core):
    return re.match("^[" + re.escape(PUN) + r"\s]*", core).group()


def detect_order(cues):
    starts = ends = 0
    for _, _, body in cues:
        for l in body:
            core = split_line(l)[1]
            if not HEB.search(core):
                continue
            # "..." and "-" can legitimately start a logical line, so count only . , ? ! here
            if re.match(r"^[.,?!]", core) and not core.startswith("..."):
                starts += 1
            if re.search(r"[.,?!]$", core):
                ends += 1
    return ("visual" if starts > ends else "logical"), starts, ends


def flip(l):
    pre, core, post = split_line(l)
    if not HEB.search(core):
        return l
    lead = leading_pun(core)
    rest = core[len(lead):]
    trail = re.search("[" + re.escape(PUN) + r"\s]*$", rest).group()
    mid = rest[:len(rest) - len(trail)] if trail else rest
    # the edge runs trade places; brackets mirror because they were typed for left-to-right display
    return (pre + trail.replace(" ", "")[::-1].translate(MIRROR) + mid
            + lead.replace(" ", "")[::-1].translate(MIRROR) + post)


def wrap(l):
    pre, core, post = split_line(l)
    return pre + "‫" + core + "‬" + post if core else l


def ts(x):
    ms = int(round(max(0.0, x) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--shift", type=float, default=0.0, help="seconds to add to every cue (negative = earlier)")
    ap.add_argument("--order", choices=("auto", "visual", "logical"), default="auto")
    ap.add_argument("--drop-cue", type=int, action="append", default=[], help="1-based cue number in the source")
    a = ap.parse_args()

    text, enc = decode(open(a.src, "rb").read())
    cues = parse(text)
    if not cues:
        sys.exit("no subtitle cues found (is this a .srt? zips must be extracted first)")
    detected, starts, ends = detect_order(cues)
    order = detected if a.order == "auto" else a.order
    print(f"source: {len(cues)} cues, {enc}; punctuation order: {order}"
          f"{' (detected: ' + str(starts) + ' lines start with . , ? !  vs ' + str(ends) + ' end with them)' if a.order == 'auto' else ''}")

    # In a visual file, a line that already ENDS with punctuation was probably typed in logical order by
    # mistake ("השמיים ברובם מעוננים..." continuing into the next cue). The flip moves its punctuation to
    # the front. When such lines are rare, list them so a person can decide.
    odd = []
    if order == "visual":
        odd = [(i, l) for i, (_, _, body) in enumerate(cues, 1) for l in body
               if HEB.search(l) and re.search(r"[.,?!…]$", split_line(l)[1]) and not leading_pun(split_line(l)[1])]
    kept = [c for i, c in enumerate(cues, 1) if i not in set(a.drop_cue)]
    fixed = [[s + a.shift, e + a.shift, [flip(l) if order == "visual" else l for l in body]] for s, e, body in kept]
    if fixed and fixed[0][0] < 0:
        print(f"warning: the shift pushes {sum(1 for c in fixed if c[0] < 0)} cue(s) before 0:00; they are clamped")

    with open(a.out, "w", encoding="utf-8-sig", newline="\r\n") as f:
        for i, (s, e, body) in enumerate(fixed, 1):
            f.write(f"{i}\n{ts(s)} --> {ts(e)}\n" + "\n".join(wrap(l) for l in body) + "\n\n")

    # ---- verify ----
    raw = open(a.out, "rb").read()
    problems = []
    if not raw.startswith(b"\xef\xbb\xbf"):
        problems.append("no BOM")
    back = parse(raw.decode("utf-8-sig"))
    if len(back) != len(fixed):
        problems.append(f"cue count {len(back)} != {len(fixed)}")
    elif any(b[2] != f_[2] for b, f_ in zip(back, fixed)):
        problems.append("text changed while writing")
    # A logical line may open with "..." (a sentence continuing from the last cue); a lone . , ? ! may not.
    bad_start = [(i, l) for i, (_, _, body) in enumerate(fixed, 1) for l in body
                 if HEB.search(l) and re.match(r"^[.,?!:;]", split_line(l)[1].lstrip("‎‏"))
                 and not re.match(r"^(\.\.\.|…)", split_line(l)[1].lstrip("‎‏"))]
    if bad_start:
        problems.append(f"{len(bad_start)} Hebrew line(s) still start with punctuation, e.g. cue {bad_start[0][0]}: "
                        f"{bad_start[0][1]}  (wrong --order?)")
    print(f"wrote {a.out}: {len(fixed)} cues, UTF-8 BOM, RLE/PDF marks"
          f"{', shifted %+.3f s' % a.shift if a.shift else ''}"
          f"{', dropped cue(s) ' + ','.join(map(str, a.drop_cue)) if a.drop_cue else ''}")
    print("verify: " + ("OK" if not problems else "PROBLEMS: " + "; ".join(problems)))

    # ---- what a person should look at ----
    def plain(l):
        return re.sub(r"<[^>]+>|\{\\an\d\}", "", l)
    suspects = []
    for i, (_, _, body) in enumerate(fixed, 1):
        txt = "\n".join(plain(l) for l in body)
        if not HEB.search(txt):
            continue
        why = []
        if txt.count("(") != txt.count(")") or txt.count("[") != txt.count("]"):
            why.append("unbalanced brackets")
        if any(re.match(r"^[0-9A-Za-z]", plain(l)) and HEB.search(l) for l in body):
            why.append("line starts with a digit or Latin letter")
        if why:
            suspects.append((i, ", ".join(why), " / ".join(body)))
    if suspects:
        print(f"\ncheck by eye ({len(suspects)} cues; visual-order files can scramble brackets and numbers "
              f"at a line's edge. Read each; fix wrong ones by hand in {a.out}):")
        for i, why, t in suspects[:40]:
            print(f"  cue {i} [{why}]: {t}")
        if len(suspects) > 40:
            print(f"  ... {len(suspects) - 40} more")
    if 0 < len(odd) <= 20:
        print(f"\ncheck by eye ({len(odd)} source line(s) already END with punctuation, unusual in a visual file; "
              f"the flip moved it to the front. If the sentence continues into the next cue, the punctuation "
              f"belongs at the end: fix it by hand in {a.out}):")
        for i, l in odd:
            print(f"  source cue {i}: {l}")
    elif len(odd) > 20:
        print(f"\nnote: {len(odd)} source lines end with punctuation; that is this file's own convention, flipped.")
    edge = [i for i in list(range(1, min(4, len(cues)) + 1)) + list(range(max(1, len(cues) - 2), len(cues) + 1))
            if RELEASE_HINT.search(" ".join(cues[i - 1][2])) and i not in a.drop_cue]
    for i in sorted(set(edge)):
        print(f"\nsource cue {i} looks like release info, not dialogue or a credit; drop it with --drop-cue {i}?\n"
              f"  {' / '.join(cues[i - 1][2])}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
