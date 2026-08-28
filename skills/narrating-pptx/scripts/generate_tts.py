#!/usr/bin/env python3
"""Generate per-slide TTS narration via ElevenLabs (eleven_v3), in parallel with 429-safe batching.

Usage:
  ELEVENLABS_API_KEY=... python3 generate_tts.py scripts.json VOICE_ID outdir/ [--concurrency 4] [--stability 0.5]

  --stability: eleven_v3 has three modes - 0.0 Creative (most expressive, strongest
  response to audio tags, least predictable), 0.5 Natural (default), 1.0 Robust.
  A/B one slide before generating a whole deck, and keep one value across all clips.

scripts.json: {"01": "text...", "02": "text...", ...}  (keys become outdir/slideKEY.mp3)
Texts may include ElevenLabs v3 audio tags like [warm], [pause], [confident].
Max 5,000 chars per text (eleven_v3 limit). Never print the API key.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

def tts(key, voice, slide_id, text, outdir):
    body = json.dumps({
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {"stability": STABILITY, "similarity_boost": 0.75, "use_speaker_boost": True},
    }).encode("utf-8")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json"})
    path = os.path.join(outdir, f"slide{slide_id}.mp3")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            if len(data) < 100_000 and len(text) > 120:  # suspiciously small = error body
                raise RuntimeError(f"slide{slide_id}: tiny response ({len(data)}B)")
            open(path, "wb").write(data)
            return f"slide{slide_id}: OK {len(data)}B"
        except urllib.error.HTTPError as e:
            if e.code == 429:  # concurrency limit — back off and retry
                time.sleep(4 * (attempt + 1)); continue
            return f"slide{slide_id}: HTTP {e.code} {e.read()[:200]!r}"
        except Exception as e:
            if attempt < 3: time.sleep(3); continue
            return f"slide{slide_id}: FAILED {e}"
    return f"slide{slide_id}: FAILED after retries (429s)"

STABILITY = 0.5   # overridden by --stability


def main():
    global STABILITY
    ap = argparse.ArgumentParser(
        description="Generate one ElevenLabs clip per slide from scripts.json.",
        epilog="stability: 0.0 Creative (most expressive, strongest response to audio "
               "tags, least predictable) / 0.5 Natural / 1.0 Robust. A/B one slide "
               "before generating a deck, and keep one value across all clips.")
    ap.add_argument("scripts", help="scripts.json: {\"01\": \"text\", ...}")
    ap.add_argument("voice", help="ElevenLabs VOICE_ID")
    ap.add_argument("outdir", help="directory to write slideNN.mp3 into")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--stability", type=float, default=STABILITY)
    args = ap.parse_args()
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        ap.error("set ELEVENLABS_API_KEY env var (never paste the key into commands/output)")
    scripts_path, voice, outdir = args.scripts, args.voice, args.outdir
    conc, STABILITY = args.concurrency, args.stability
    print(f"stability={STABILITY}", flush=True)
    os.makedirs(outdir, exist_ok=True)
    scripts = json.load(open(scripts_path))
    for k, v in scripts.items():
        assert len(v) <= 5000, f"script {k} exceeds eleven_v3 5,000-char limit ({len(v)})"
    failures = []
    with ThreadPoolExecutor(max_workers=conc) as ex:
        futs = [ex.submit(tts, key, voice, k, v, outdir) for k, v in scripts.items()]
        for f in as_completed(futs):
            msg = f.result(); print(msg, flush=True)
            if "OK" not in msg: failures.append(msg)
    if failures:
        print(f"\n{len(failures)} FAILURES — regenerate those before embedding", file=sys.stderr); sys.exit(1)
    print("\nall clips OK")

if __name__ == "__main__":
    main()
