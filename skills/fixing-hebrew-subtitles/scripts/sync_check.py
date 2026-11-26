#!/usr/bin/env python3
"""Measure how well one or more subtitle files fit a video's audio: global offset, then drift per quarter.

  python3 -I sync_check.py <video-or-wav> a.srt [b.srt ...]
  python3 -I sync_check.py <reference.srt> a.srt [b.srt ...]     # no video: timing vs another subtitle

Reference-subtitle mode is for when there is no video: use a subtitle that matches the release exactly
(e.g. the SPARKS fan sub for a SPARKS file) as the timing reference and measure a better translation
(e.g. a studio one synced to RARBG) against it. Same verdicts; the offset is what to pass to --shift so
the candidate lands on the reference's timing. It compares "a subtitle is on screen" over time, so it
works across different translations of the same film.

For each subtitle:
  1. ffsubsync against the whole audio -> constant offset (seconds to ADD to the subtitle) and frame-rate
     scale. A scale other than 1.000 means a frame-rate mismatch (e.g. 25 vs 23.976 fps).
  2. Applies that offset, splits the cues into four time quarters, and runs ffsubsync again for each quarter
     against ONLY that quarter's stretch of audio. The residuals should all be ~0. Matching a partial
     subtitle against the full audio can lock onto the wrong place (end credits music is a classic), which
     is why each quarter gets its own audio.

Verdict per file:
  "fits as-is"            |offset| < 0.3 s and every quarter within 0.5 s
  "fits with shift"       one constant offset fixes it; pass it to fix_hebrew_srt.py --shift
  "drifts / cut differs"  quarters disagree: different cut or frame rate; a constant shift is not enough

The video's audio is extracted once to $HEBREW_SUBS_CACHE (default /tmp/hebrew-subs-sync)/<id>.wav (mono 16 kHz, first audio track), so
a second run is fast. Needs ffmpeg and ffsubsync (pip install ffsubsync).
"""
import atexit
import hashlib
import os
import shutil
import tempfile
import re
import subprocess
import sys

CACHE = os.environ.get("HEBREW_SUBS_CACHE", "/tmp/hebrew-subs-sync")  # audio mode only; reference mode writes nothing
TS = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(r.stdout.strip())


def _extract(cmd_in, out):
    """Run ffmpeg into a per-process temp name, then move it into place atomically. Two sessions can share
    the cache: each writes its own .part file, and whichever finishes last replaces an identical file."""
    part = f"{out}.{os.getpid()}.part.wav"
    r = run(["ffmpeg", "-nostdin", "-v", "error", "-y", *cmd_in, part])
    if r.returncode:
        sys.exit(f"ffmpeg failed: {r.stderr[-500:]}")
    os.makedirs(os.path.dirname(out), exist_ok=True)  # in case the cache was cleaned meanwhile
    os.replace(part, out)


def cache_dir_for(src):
    key = hashlib.md5(f"{os.path.abspath(src)}:{os.path.getsize(src)}".encode()).hexdigest()[:10]
    d = os.path.join(CACHE, key)
    os.makedirs(d, exist_ok=True)
    return d


def audio_for(src):
    if src.lower().endswith(".wav"):
        return src
    wav = os.path.join(cache_dir_for(src), "audio.wav")
    if not os.path.exists(wav):
        print(f"extracting audio once to {wav} (a few minutes for a big file)...", flush=True)
        _extract(["-i", src, "-map", "0:a:0", "-ac", "1", "-ar", "16000"], wav)
    return wav


def load(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1255", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    text = re.sub("[‎‏‪-‮⁦-⁩]", "", text.replace("\r", ""))
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        m = TS.search(block)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        body = block[m.end():].strip()
        cues.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                     body or "."))
    return cues


def ts(x):
    ms = int(round(max(0.0, x) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write(cues, path, shift=0.0):
    with open(path, "w", encoding="utf-8") as f:
        for i, (s, e, b) in enumerate(cues, 1):
            f.write(f"{i}\n{ts(s + shift)} --> {ts(e + shift)}\n{b}\n\n")


def ffsubsync(wav, srt, max_offset=None):
    cmd = ["ffsubsync", wav, "-i", srt, "-o", srt + ".out.srt", "--encoding", "utf-8"]
    if max_offset:
        cmd += ["--max-offset-seconds", str(max_offset)]
    r = run(cmd)
    log = r.stdout + r.stderr
    off = re.search(r"offset seconds: (-?[\d.]+)", log)
    scale = re.search(r"framerate scale factor: ([\d.]+)", log)
    if not off:
        return None, None
    return float(off.group(1)), float(scale.group(1)) if scale else 1.0


def _signal(cues, res=0.1):
    """'A subtitle is on screen' per 100 ms bin, as one big int (bit i = bin i). Stdlib, and fast."""
    x = 0
    for s, e, _ in cues:
        a, b = max(0, int(s / res)), max(0, int(e / res))
        if b > a:
            x |= ((1 << (b - a)) - 1) << a
    return x


def _overlap(ref, cand, lag):
    shifted = cand << lag if lag >= 0 else cand >> -lag
    return (ref & shifted).bit_count()


def _best_lag(ref, cand, lo, hi):
    best, best_v = 0, -1
    for lag in range(lo, hi + 1):  # shift cand later by `lag` bins
        v = _overlap(ref, cand, lag)
        if v > best_v:
            best, best_v = lag, v
    return best, best_v


def reference_mode(ref_path, cands):
    ref = load(ref_path)
    end = max(e for _, e, _ in ref)
    print(f"reference: {os.path.basename(ref_path)} ({len(ref)} cues, last ends {ts(end)})\n")
    for src in cands:
        cues = load(src)
        name = os.path.basename(src)
        if not cues:
            print(f"{name}: no cues\n")
            continue
        R, C = _signal(ref), _signal(cues)
        lag, v = _best_lag(R, C, -1200, 1200)
        off = lag / 10
        overlap = v / max(1, min(R.bit_count(), C.bit_count()))
        res = []
        for q in range(4):
            a, b = end * q / 4, end * (q + 1) / 4
            part = [(s + off, e + off, t) for s, e, t in cues if a <= s + off < b]
            if len(part) < 15:
                res.append(None)
                continue
            Rq = _signal([c for c in ref if a <= c[0] < b])
            l2, _ = _best_lag(Rq, _signal(part), -100, 100)
            res.append(l2 / 10)
        known = [r for r in res if r is not None]
        if overlap < 0.6:
            verdict = f"poor match (overlap {overlap:.0%}): different cut, or not the same film"
        elif not all(abs(r) < 0.5 for r in known):
            verdict = "drifts / cut differs from the reference: a constant shift is not enough"
        elif abs(off) < 0.3:
            verdict = "same timing as the reference"
        else:
            verdict = f"same timing after a shift: fix_hebrew_srt.py --shift {off:.1f}"
        qtxt = "  ".join(f"Q{i + 1} {'n/a' if r is None else f'{r:+.1f}'}" for i, r in enumerate(res))
        print(f"{name}\n  cues {len(cues)}, last ends {ts(cues[-1][1])}\n  offset {off:+.1f} s, overlap {overlap:.0%}"
              f"\n  residual per quarter after shift: {qtxt}\n  -> {verdict}\n")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1].lower().endswith((".srt", ".ass", ".ssa", ".vtt", ".sub")):
        return reference_mode(sys.argv[1], sys.argv[2:])
    wav = audio_for(sys.argv[1])
    total = duration(wav)
    work = tempfile.mkdtemp(prefix="sync_check-")  # per run: parallel sessions never share work files
    atexit.register(shutil.rmtree, work, True)
    quarters = [(total * q / 4, total * (q + 1) / 4) for q in range(4)]
    qdir = cache_dir_for(wav)  # quarter clips live in the cache, never next to the user's own files
    qwavs = []
    for q, (a, b) in enumerate(quarters):
        qw = os.path.join(qdir, f"q{q + 1}.wav")
        if not os.path.exists(qw):
            _extract(["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", wav], qw)
        qwavs.append(qw)

    print(f"audio: {total / 60:.1f} min\n")
    for src in sys.argv[2:]:
        cues = load(src)
        name = os.path.basename(src)
        if not cues:
            print(f"{name}: no cues (zip? extract it first)\n")
            continue
        tmp = os.path.join(work, "full.srt")
        write(cues, tmp)
        off, scale = ffsubsync(wav, tmp)
        if off is None:
            print(f"{name}: ffsubsync found no alignment\n")
            continue
        res = []
        for q, (a, b) in enumerate(quarters):
            part = [(s - a, e - a, t) for s, e, t in [(s + off, e + off, t) for s, e, t in cues] if a <= s < b]
            if len(part) < 15:
                res.append(None)
                continue
            qs = os.path.join(work, f"q{q + 1}.srt")
            write(part, qs)
            r, _ = ffsubsync(qwavs[q], qs, max_offset=20)
            res.append(r)
        known = [r for r in res if r is not None]
        spread_ok = all(abs(r) < 0.5 for r in known)  # fan subs jitter ~0.3 s; a cut moves seconds
        if abs(scale - 1.0) > 0.001:
            verdict = f"frame-rate mismatch (scale {scale:.4f}): a constant shift is not enough"
        elif not spread_ok:
            verdict = "drifts / cut differs: quarters disagree, a constant shift is not enough"
        elif abs(off) < 0.3:
            verdict = "fits as-is"
        else:
            verdict = f"fits with shift: fix_hebrew_srt.py --shift {off:.2f}"
        qtxt = "  ".join(f"Q{i + 1} {'n/a' if r is None else f'{r:+.2f}'}" for i, r in enumerate(res))
        print(f"{name}\n  cues {len(cues)}, last ends {ts(cues[-1][1])}\n  offset {off:+.2f} s, scale {scale:.3f}"
              f"\n  residual per quarter after shift: {qtxt}\n  -> {verdict}\n")


if __name__ == "__main__":
    main()
