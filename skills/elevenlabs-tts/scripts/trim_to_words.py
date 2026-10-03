#!/usr/bin/env python3
"""Trim short clips to the words actually spoken, using ElevenLabs forced alignment.

One-word and very short lines on eleven_v4 often carry extra audio: the word said twice, a sigh or a laugh
from a tag, or a long lead-in. This keeps the span from the first aligned word to the last, plus a small lead
and tail, with short fades so the cut never clicks. Originals are never modified.

  ELEVENLABS_API_KEY=... python3 trim_to_words.py scripts.json audio/ trimmed/ [--prefix ""] [--only a b]
      [--text ID="the words actually kept"] [--lead 0.04] [--tail 0.14]

scripts.json is the {"id": "text with [tags]"} file generate_tts.py read. Use --text when a clip's audio no
longer matches its script (a take cut from another take). When the model repeated the word, the transcript
holds it once, so the window usually covers one occurrence; listen to the result anyway.
"""
import argparse, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align_narration import align, strip_tags  # noqa: E402


def word_window(words, duration, lead=0.04, tail=0.14):
    """(start, end) seconds from the first to the last spoken word, padded and clamped to the clip."""
    spoken = [w for w in words if w.get("text", "").strip()]
    if not spoken:
        raise ValueError("alignment returned no words")
    start = max(0.0, spoken[0]["start"] - lead)
    end = min(duration, spoken[-1]["end"] + tail)
    if end <= start:
        raise ValueError(f"empty window {start:.3f}-{end:.3f}")
    return start, end


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    if not out:
        raise FileNotFoundError(f"cannot read duration of {path}")
    return float(out)


def cut(src, dst, start, end):
    """Write src[start:end] to dst with 20 ms / 60 ms fades; dst appears only when ffmpeg succeeded."""
    n = end - start
    af = (f"atrim={start:.3f}:{end:.3f},asetpts=PTS-STARTPTS,"
          f"afade=t=in:d=0.02,afade=t=out:st={max(0.0, n - 0.06):.3f}:d=0.06")
    tmp = dst + ".part.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-af", af,
                    "-ar", "44100", "-b:a", "160k", tmp], check=True)
    os.replace(tmp, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scripts"); ap.add_argument("audio_dir"); ap.add_argument("out_dir")
    ap.add_argument("--prefix", default="", help="clip filename prefix (generate_tts.py's default is 'slide')")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--text", nargs="*", default=[], metavar="ID=TEXT", help="transcript override per clip")
    ap.add_argument("--lead", type=float, default=0.04)
    ap.add_argument("--tail", type=float, default=0.14)
    ap.add_argument("--concurrency", type=int, default=3)
    a = ap.parse_args()
    if os.path.abspath(a.audio_dir) == os.path.abspath(a.out_dir):
        sys.exit("out_dir must differ from audio_dir: originals are kept")
    key = os.environ.get("ELEVENLABS_API_KEY") or sys.exit("ELEVENLABS_API_KEY not set")
    scripts = json.load(open(a.scripts, encoding="utf-8"))
    override = dict(t.split("=", 1) for t in a.text)
    ids = [k for k in sorted(scripts) if not a.only or k in a.only]
    os.makedirs(a.out_dir, exist_ok=True)

    def one(k):
        src = os.path.join(a.audio_dir, f"{a.prefix}{k}.mp3")
        dst = os.path.join(a.out_dir, f"{a.prefix}{k}.mp3")
        try:
            text = override.get(k) or strip_tags(scripts[k])
            d = duration(src)
            s, e = word_window(align(src, text, key).get("words", []), d, a.lead, a.tail)
            cut(src, dst, s, e)
            return k, True, f"{d:.2f}s -> {e - s:.2f}s (kept {s:.2f}-{e:.2f})"
        except Exception as ex:  # one bad clip must not stop the batch
            return k, False, str(ex)[:200]

    bad = []
    with ThreadPoolExecutor(a.concurrency) as ex:
        for k, ok, msg in ex.map(one, ids):
            print(f"  {k}: {'OK  ' if ok else 'FAIL'} {msg}", flush=True)
            if not ok:
                bad.append(k)
    if bad:
        sys.exit(f"failed: {bad}")


if __name__ == "__main__":
    main()
