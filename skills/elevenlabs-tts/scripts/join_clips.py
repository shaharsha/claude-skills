#!/usr/bin/env python3
"""Join clips into one mp3 with a pause between them, and print where each one starts.

  python3 join_clips.py out.mp3 audio/part01.mp3 audio/part02.mp3 ... [--gap 0.8] [--chapters out.txt]

For a spoken briefing made of several clips: the listener gets one file, and the
printed start times ("0:00 part01 / 1:28 part02 ...") go into the written list or
email sent beside it. Every input is resampled to 44.1 kHz mono and re-encoded at
128 kbit/s, so clips with different rates or layouts can't break the join the way
a stream-copy concat does. The pause is padding on each clip, not a separate
silence input.

ffmpeg runs with -nostdin and stdin closed: inside an agent's shell, ffmpeg left
reading stdin can wait forever. Exits non-zero if the result's length is off.
"""
import argparse, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el_common import duration, mmss


def build_cmd(clips, out, gap):
    """ffmpeg argv: resample every clip, pad all but the last with `gap` seconds, concat."""
    args = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    for c in clips:
        args += ["-i", c]
    parts = []
    for i in range(len(clips)):
        chain = f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono"
        if gap > 0 and i < len(clips) - 1:
            chain += f",apad=pad_dur={gap}"
        parts.append(f"{chain}[a{i}]")
    graph = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(clips)))
    graph += f"concat=n={len(clips)}:v=0:a=1[out]"
    return args + ["-filter_complex", graph, "-map", "[out]",
                   "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "1", out]


def chapters(names, lengths, gap):
    """[(start_seconds, name)] for clips joined in order with `gap` after all but the last."""
    t, rows = 0.0, []
    for name, length in zip(names, lengths):
        rows.append((t, name))
        t += length + gap
    return rows


def main():
    ap = argparse.ArgumentParser(description="Join clips into one mp3 with pauses; print chapter starts.")
    ap.add_argument("out"); ap.add_argument("clips", nargs="+")
    ap.add_argument("--gap", type=float, default=0.8, help="seconds of silence between clips (default 0.8)")
    ap.add_argument("--chapters", help="also write the start times to this text file")
    ap.add_argument("--timeout", type=int, default=900, help="seconds before ffmpeg is killed")
    a = ap.parse_args()
    if os.path.abspath(a.out) in {os.path.abspath(c) for c in a.clips}:
        ap.error("the output would overwrite one of the inputs")
    missing = [c for c in a.clips if not os.path.exists(c)]
    if missing:
        sys.exit(f"missing clips: {missing}")

    lengths = [duration(c) for c in a.clips]
    tmp = a.out + ".part.mp3"
    try:
        subprocess.run(build_cmd(a.clips, tmp, a.gap), check=True, stdin=subprocess.DEVNULL,
                       timeout=a.timeout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        sys.exit(f"ffmpeg failed: {e}")
    os.replace(tmp, a.out)

    rows = chapters([os.path.splitext(os.path.basename(c))[0] for c in a.clips], lengths, a.gap)
    expected = sum(lengths) + a.gap * (len(a.clips) - 1)
    got = duration(a.out)
    lines = [f"{mmss(t)}  {name}" for t, name in rows]
    print("\n".join(lines))
    print(f"total {mmss(got)} ({got:.1f}s) -> {a.out}")
    if a.chapters:
        open(a.chapters, "w").write("\n".join(lines) + f"\ntotal {mmss(got)}\n")
    if abs(got - expected) > 0.5 + 0.05 * len(a.clips):  # mp3 frame padding adds a little per clip
        sys.exit(f"length {got:.1f}s differs from the expected {expected:.1f}s - check the inputs")


if __name__ == "__main__":
    main()
