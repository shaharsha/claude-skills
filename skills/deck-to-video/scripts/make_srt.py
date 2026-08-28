#!/usr/bin/env python3
"""Subtitles from forced-aligned narration - no second transcription pass.

  python3 make_srt.py alignment/ audio/ out.srt [--pad 0.7]

Consumes the alignment produced by narrating-pptx's align_narration.py. Cue
timings are absolute in the finished video, so --pad must match the pad the
video was built with or the subtitles drift further out with every slide.
"""
import argparse, json, os, subprocess, sys

def ts(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"

def cues(words, offset, max_chars=84, max_gap=0.8, max_dur=6.0,
         min_words=4, min_dur=1.0):
    """Group words into cues, breaking at sentence ends, then fold any runt back
    into its neighbour - a one-word subtitle flashing past reads as a glitch."""
    groups, cur = [], []
    for w in words:
        if not w["text"].strip():
            continue
        if cur:
            gap = w["start"] - cur[-1]["end"]
            length = sum(len(x["text"]) + 1 for x in cur) + len(w["text"])
            ends = cur[-1]["text"].rstrip().endswith((".", "?", "!", "…"))
            if gap > max_gap or length > max_chars or (w["end"] - cur[0]["start"]) > max_dur:
                groups.append(cur); cur = []
            elif ends and length > max_chars * 0.55:
                groups.append(cur); cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    merged = []
    for g in groups:
        runt = len(g) < min_words or (g[-1]["end"] - g[0]["start"]) < min_dur
        if runt and merged and (sum(len(x["text"]) + 1 for x in merged[-1])
                                + sum(len(x["text"]) + 1 for x in g)) <= max_chars * 1.35:
            merged[-1].extend(g)
        else:
            merged.append(g)
    return [(c[0]["start"] + offset, c[-1]["end"] + offset,
             " ".join(x["text"] for x in c).strip().replace("—", "-"))
            for c in merged]

def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("alignment_dir"); ap.add_argument("audio_dir"); ap.add_argument("out")
    ap.add_argument("--pad", type=float, default=0.7,
                    help="must match the pad the video was built with")
    a = ap.parse_args()
    keys = sorted(f[5:-5] for f in os.listdir(a.alignment_dir)
                  if f.startswith("slide") and f.endswith(".json"))
    if not keys:
        sys.exit(f"no slideNN.json in {a.alignment_dir} - run align_narration.py first")
    lines, n, offset = [], 1, 0.0
    for k in keys:
        al = json.load(open(os.path.join(a.alignment_dir, f"slide{k}.json")))
        for s, e, txt in cues(al["words"], offset):
            lines.append(f"{n}\n{ts(s)} --> {ts(e)}\n{txt}\n"); n += 1
        offset += round(dur(os.path.join(a.audio_dir, f"slide{k}.mp3")) + a.pad, 3)
    open(a.out, "w").write("\n".join(lines))
    print(f"  {a.out}: {n - 1} cues over {offset / 60:.1f} min (pad {a.pad}s)")

if __name__ == "__main__":
    main()
