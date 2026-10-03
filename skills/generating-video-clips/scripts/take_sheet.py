#!/usr/bin/env python3
"""See video takes without watching them: frame sheets for comparing takes, and a speaker-point check.

  python3 take_sheet.py sheet out.jpg take1.mp4 take2.mp4 ... [--times 0.5,2,4,6] [--width 240]
      rows = takes, columns = times in seconds (default: 6 evenly spaced over the shortest take)
  python3 take_sheet.py point clip.mp4 out.jpg --frame 36 --xy 400,520 [--box 140]
      that frame with a red box around the point, to confirm a lip-sync speaker point is on the right face

Read the output image; never judge a take you have not looked at frame by frame.
"""
import argparse, os, subprocess, tempfile


def ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


def probe(path, entries):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries,
                           "-of", "csv=p=0:s=x", path], capture_output=True, text=True, check=True).stdout.strip()


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True, check=True).stdout)


def grid_times(dur, n=6):
    return [round(dur * (i + 0.5) / n, 2) for i in range(n)]


def box_for(x, y, box, w, h):
    """Top-left of a box x box square centered on (x, y), kept inside a w x h frame."""
    return min(max(x - box // 2, 0), w - box), min(max(y - box // 2, 0), h - box)


def sheet(out, clips, times=None, width=240, pad=4):
    if times is None:
        times = grid_times(min(duration(c) for c in clips))
    with tempfile.TemporaryDirectory() as d:
        tiles, size = [], None
        for c in clips:
            for t in times:
                f = os.path.join(d, f"f{len(tiles):04d}.png")
                ff("-ss", f"{t:.3f}", "-i", c, "-frames:v", "1", "-vf", f"scale={width}:-2", f)
                if os.path.exists(f) and size is None:
                    size = probe(f, "stream=width,height")
                tiles.append(f)
        size = size or f"{width}x{width * 16 // 9 // 2 * 2}"
        for f in tiles:
            if not os.path.exists(f):  # t past this clip's end: a black tile keeps the grid aligned
                ff("-f", "lavfi", "-i", f"color=black:s={size}", "-frames:v", "1", f)
        ff("-i", os.path.join(d, "f%04d.png"), "-vf", f"tile={len(times)}x{len(clips)}:padding={pad}:color=white",
           "-frames:v", "1", "-q:v", "3", out)
    return times


def point(clip, out, frame, x, y, box=140):
    w, h = (int(v) for v in probe(clip, "stream=width,height").split("x"))
    bx, by = box_for(x, y, box, w, h)
    ff("-i", clip, "-vf", f"select=eq(n\\,{frame}),drawbox=x={bx}:y={by}:w={box}:h={box}:color=red@0.9:t=6",
       "-frames:v", "1", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet"); s.add_argument("out"); s.add_argument("clips", nargs="+")
    s.add_argument("--times"); s.add_argument("--width", type=int, default=240)
    p = sub.add_parser("point"); p.add_argument("clip"); p.add_argument("out")
    p.add_argument("--frame", type=int, required=True); p.add_argument("--xy", required=True)
    p.add_argument("--box", type=int, default=140)
    a = ap.parse_args()
    if a.cmd == "sheet":
        times = [float(t) for t in a.times.split(",")] if a.times else None
        print("times:", sheet(a.out, a.clips, times, a.width), "->", a.out)
    else:
        x, y = (int(v) for v in a.xy.split(","))
        point(a.clip, a.out, a.frame, x, y, a.box)
        print(a.out)


if __name__ == "__main__":
    main()
