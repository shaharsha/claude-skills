#!/usr/bin/env python3
"""Level dialogue clips to one voiced loudness, and report words a take let sag.

Cloned voices come out at different levels, and plain loudnorm on a one-word clip is dominated by its
silence. This measures the voiced part only (silence removed), then applies one gain per clip so every
clip's voiced mean lands on --target dB, with a limiter as a guard. Originals are never modified.

  python3 level_clips.py in_dir/ out_dir/ [--target -18] [--only a b]
  python3 level_clips.py in_dir/ --report      voiced mean/peak and weak 150 ms windows per clip; writes nothing

A weak window (12 dB or more under the clip's voiced median, but louder than a pause) is usually a
swallowed word: regenerate that line with a firmer tag, or let the mix's dialogue compressor lift it,
and ask a human to listen.
"""
import argparse, os, re, statistics, subprocess, sys

VOICED = ("silenceremove=start_periods=1:start_threshold=-45dB:"
          "stop_periods=-1:stop_threshold=-45dB:stop_duration=0.15")
PAUSE_DB = -45.0


def parse_volumedetect(stderr):
    mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", stderr)
    peak = re.search(r"max_volume:\s*(-?[\d.]+) dB", stderr)
    if not (mean and peak):
        raise ValueError("no volumedetect output (silent or unreadable clip?)")
    return float(mean.group(1)), float(peak.group(1))


def gain_for(mean_db, max_db, target_db=-18.0, ceiling_db=-1.0):
    """dB that puts the voiced mean on target, but never lifts the peak more than 6 dB past the ceiling."""
    return min(target_db - mean_db, ceiling_db + 6.0 - max_db)


def weak_spots(rms_db, win=0.15, rel_db=-12.0):
    """Start times of windows at least |rel_db| under the voiced median that are still louder than a pause."""
    voiced = [r for r in rms_db if r > -60]
    if not voiced:
        return []
    floor = statistics.median(voiced) + rel_db
    return [round(i * win, 2) for i, r in enumerate(rms_db) if PAUSE_DB < r < floor]


def voiced_levels(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", f"{VOICED},volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    return parse_volumedetect(r.stderr)


def rms_windows(path, win=0.15):
    n = int(44100 * win)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        f"aresample=44100,asetnsamples=n={n}:p=0,astats=metadata=1:reset=1,"
                        "ametadata=print:key=lavfi.astats.Overall.RMS_level",
                        "-f", "null", "-"], capture_output=True, text=True)
    vals = re.findall(r"lavfi\.astats\.Overall\.RMS_level=(\S+)", r.stdout + r.stderr)
    return [float(v) if v not in ("-inf", "inf", "nan") else -120.0 for v in vals]


def apply_gain(src, dst, gain_db):
    tmp = dst + ".part.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-af",
                    f"volume={gain_db:.2f}dB,alimiter=limit=0.891:level=false", "-ar", "44100", "-b:a", "160k", tmp],
                   check=True)
    os.replace(tmp, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_dir"); ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--target", type=float, default=-18.0)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if not a.report:
        if not a.out_dir or os.path.abspath(a.out_dir) == os.path.abspath(a.in_dir):
            sys.exit("give an out_dir different from in_dir (originals are kept), or use --report")
        os.makedirs(a.out_dir, exist_ok=True)
    names = sorted(f for f in os.listdir(a.in_dir) if f.endswith(".mp3") and (not a.only or f[:-4] in a.only))
    bad = []
    for f in names:
        src = os.path.join(a.in_dir, f)
        try:
            mean, peak = voiced_levels(src)
            if a.report:
                weak = weak_spots(rms_windows(src))
                print(f"  {f[:-4]:12} voiced mean {mean:6.1f} dB  peak {peak:5.1f} dB  weak at {weak or '-'}")
                continue
            g = gain_for(mean, peak, a.target)
            apply_gain(src, os.path.join(a.out_dir, f), g)
            capped = "  (peak-limited: stays under target)" if g < a.target - mean - 0.05 else ""
            print(f"  {f[:-4]:12} {mean:6.1f} dB -> gain {g:+.1f} dB{capped}")
        except Exception as e:  # one silent or broken clip must not stop the batch
            print(f"  {f[:-4]:12} FAIL {e}", file=sys.stderr)
            bad.append(f[:-4])
    if bad:
        sys.exit(f"failed: {bad} (nothing above -45 dB is treated as silence: check these clips by ear)")

if __name__ == "__main__":
    main()
