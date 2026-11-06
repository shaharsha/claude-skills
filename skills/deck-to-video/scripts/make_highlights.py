#!/usr/bin/env python3
"""Build build_video.py's --highlights JSON from markers, boxes and forced alignment.

  python3 make_highlights.py markers.json boxes.json alignment/ highlights.json
      [--size 1920x1080] [--inches SLIDE_WIDTH_IN] [--colour "#B45309"] [--dim white]
      [--min-window 1.4] [--lead 0.12] [--tail 0.25]

markers.json - per slide, the regions in the order the narration reaches them, each
with the phrase where the narration turns to it (copied from the slide's script):
  {"03": [["chart", "Last year"], ["callout", "The real problem"], ["_end", "Now, to the plan"]],
   "07": {"marks": [["a", "First"], ["b", "Second"]], "dim": "black", "colour": "#E07A5F",
          "colours": {"b": "#F2CC8F"}}}
  A region's window runs from its phrase to the next marker's phrase. "_end" closes the
  previous window without opening one (otherwise the last window runs to the end of the
  speech). The dict form sets the slide's dim ("white" on light slides, "black" on dark
  ones), its colour, and per-region colours.

boxes.json - per slide, region -> [x, y, w, h], in output pixels, or in slide inches
with --inches SLIDE_WIDTH_IN (the deck's page width; scaled to --size). Take them from
the deck builder's own layout constants, never by measuring a rendered image.

alignment/ - slideNN.json from elevenlabs-tts align_narration.py ({stripped, characters}).

Each phrase is searched for after the previous one's match, so a word the script says
twice can't pull a window back. Exits non-zero when a phrase isn't in the script, a
region has no box, a box (with the glow drawn around it) leaves the frame, or an
alignment file doesn't match its script. Windows too short to read once the glow has
faded in and out are skipped with a warning.
"""
import argparse, json, os, re, sys

GLOW = 19         # px build_video.py draws outside a box: an 11 px outline plus an 8 px blur
FADE = 0.5        # s build_video.py takes to fade a glow in, and again to fade it out


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def find_phrase(text, phrase, start):
    """(start, end) of phrase in text at or after `start`, or None. Exact first; then any
    run of whitespace in the script may stand for a space in the marker, ignoring case."""
    i = text.find(phrase, start)
    if i >= 0:
        return i, i + len(phrase)
    pat = r"\s+".join(re.escape(w) for w in phrase.split())
    m = re.compile(pat, re.IGNORECASE).search(text, start)
    return (m.start(), m.end()) if m else None


def slide_spec(value, default_colour, default_dim):
    if isinstance(value, dict):
        return (value["marks"], value.get("colour", default_colour), value.get("dim", default_dim),
                value.get("colours", {}))
    return value, default_colour, default_dim, {}


def windows(marks, alignment, lead=0.12, tail=0.25):
    """[(region, start, end)] for one slide, or raises ValueError naming the phrase that wasn't found."""
    text, chars = alignment["stripped"], alignment["characters"]
    if len(chars) != len(text):
        raise ValueError(f"alignment has {len(chars)} characters for a {len(text)}-character script")
    points, pos = [], 0
    for region, phrase in marks:
        hit = find_phrase(text, norm(phrase), pos)
        if hit is None:
            raise ValueError(f"phrase not found after character {pos}: {phrase!r}")
        points.append((region, chars[hit[0]]["start"]))
        pos = hit[1]
    speech_end = max(c["end"] for c in chars) + tail
    out = []
    for k, (region, t0) in enumerate(points):
        if region == "_end":
            continue
        t1 = points[k + 1][1] - lead if k + 1 < len(points) else speech_end
        out.append((region, round(max(0.0, t0 - lead), 2), round(t1, 2)))
    return out


def check_box(box, size):
    """'' if the box and its glow fit the frame; an error for a box off the frame; a warning if only the glow is clipped."""
    W, H = size
    x, y, w, h = box
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > W or y + h > H:
        return f"error: box {box} is outside the {W}x{H} frame"
    if x < GLOW or y < GLOW or x + w > W - GLOW or y + h > H - GLOW:
        return f"warning: box {box} is within {GLOW} px of the edge; its glow will be clipped"
    return ""


def build(markers, boxes, alignment_dir, size, scale=1.0, colour="#B45309", dim="white",
          min_window=1.4, lead=0.12, tail=0.25, prefix="slide"):
    """(highlights, report_lines, errors)."""
    out, report, errors = {}, [], []
    for slide in sorted(markers, key=lambda k: int(k)):
        marks, s_colour, s_dim, colours = slide_spec(markers[slide], colour, dim)
        path = os.path.join(alignment_dir, f"{prefix}{slide}.json")
        if not os.path.exists(path):
            errors.append(f"{slide}: no alignment file {path}"); continue
        try:
            wins = windows(marks, json.load(open(path, encoding="utf-8")), lead, tail)
        except ValueError as e:
            errors.append(f"{slide}: {e}"); continue
        slide_boxes = boxes.get(slide, {})
        kept = []
        for region, t0, t1 in wins:
            if region not in slide_boxes:
                errors.append(f"{slide}: no box for region {region!r}"); continue
            box = [round(v * scale) for v in slide_boxes[region]]
            msg = check_box(box, size)
            if msg.startswith("error"):
                errors.append(f"{slide} {region}: {msg}"); continue
            if msg:
                report.append(f"{slide} {region}: {msg}")
            if t1 - t0 < min_window:
                report.append(f"{slide} {region}: skipped, {t1 - t0:.1f}s is too short to read after "
                              f"{FADE}s fades in and out - give it its own beat in the narration")
                continue
            kept.append({"card": region, "box": box, "colour": colours.get(region, s_colour),
                         "dim": s_dim, "start": t0, "end": t1})
        out[slide] = kept
        report.append(f"{slide}: " + ("  ".join(f"{w['card']} {w['start']:.1f}-{w['end']:.1f}" for w in kept)
                                      or "no windows"))
    return out, report, errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markers"); ap.add_argument("boxes"); ap.add_argument("alignment_dir"); ap.add_argument("out")
    ap.add_argument("--size", default="1920x1080", help="the video's size, as given to build_video.py")
    ap.add_argument("--inches", type=float, metavar="SLIDE_WIDTH_IN",
                    help="boxes are in slide inches; this is the deck's page width (e.g. 13.333)")
    ap.add_argument("--colour", default="#B45309", help="glow colour unless a slide or region sets one")
    ap.add_argument("--dim", default="white", choices=["white", "black"],
                    help="wash for inactive regions unless a slide sets one: white on light slides, black on dark")
    ap.add_argument("--min-window", type=float, default=1.4, help="skip windows shorter than this (s)")
    ap.add_argument("--lead", type=float, default=0.12, help="start the glow this early (s)")
    ap.add_argument("--tail", type=float, default=0.25, help="hold the last window past the speech (s)")
    ap.add_argument("--prefix", default="slide", help="alignment file prefix (default: slide)")
    a = ap.parse_args(argv)
    W, H = (int(v) for v in a.size.lower().split("x"))
    scale = W / a.inches if a.inches else 1.0
    markers = json.load(open(a.markers, encoding="utf-8"))
    boxes = json.load(open(a.boxes, encoding="utf-8"))
    out, report, errors = build(markers, boxes, a.alignment_dir, (W, H), scale, a.colour, a.dim,
                                a.min_window, a.lead, a.tail, a.prefix)
    print("\n".join(report))
    if errors:
        sys.exit("\n" + "\n".join(errors) + f"\n{len(errors)} problem(s); {a.out} not written")
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\n{sum(len(v) for v in out.values())} windows on {len(out)} slides -> {a.out}")


if __name__ == "__main__":
    main()
