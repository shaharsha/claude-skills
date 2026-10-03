#!/usr/bin/env python3
"""Join pronunciation variants into one file, a second of silence apart, and print where each starts.

  python3 ab_concat.py out.mp3 a.mp3 b.mp3 c.mp3 [--gap 1.0]

The human listens once and answers by timestamp ("the one at 0:07"), instead of opening four files.
"""
import argparse, subprocess


def starts(durations, gap=1.0):
    t, out = 0.0, []
    for d in durations:
        out.append(round(t, 2))
        t += d + gap
    return out


def mmss(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out"); ap.add_argument("clips", nargs="+")
    ap.add_argument("--gap", type=float, default=1.0)
    a = ap.parse_args()
    durs = [float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", c],
                                 capture_output=True, text=True, check=True).stdout) for c in a.clips]
    args, chains = [], []
    for i, c in enumerate(a.clips):
        args += ["-i", c]
        chains.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono,apad=pad_dur={a.gap}[a{i}]")
    fc = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(len(a.clips))) + \
        f"concat=n={len(a.clips)}:v=0:a=1[o]"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, "-filter_complex", fc,
                    "-map", "[o]", "-b:a", "160k", a.out], check=True)
    for label, t, c in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", starts(durs, a.gap), a.clips):
        print(f"  {label}  {mmss(t)}  {c}")


if __name__ == "__main__":
    main()
