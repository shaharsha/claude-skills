#!/usr/bin/env python3
"""Generate one ElevenLabs clip per script entry, in parallel and 429-safe.

Usage:
  ELEVENLABS_API_KEY=... python3 generate_tts.py scripts.json VOICE_ID outdir/
      [--model eleven_v4] [--stability 0.5] [--similarity 0.75] [--seed N]
      [--language-code he] [--concurrency 4] [--stitch] [--prefix slide]

scripts.json: {"01": "text...", "02": "text...", ...}  ->  outdir/<prefix><KEY>.mp3
Texts may contain audio tags: [warm], [pause], [Warm, conversational tone].

Writes outdir/_manifest.json recording the model and settings of every clip, so a
batch that mixes stabilities (audible) or models can be spotted after the fact.
Never prints the API key.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

# Per-request character caps. Unknown models fall back to the conservative 5,000.
CHAR_LIMITS = {"eleven_v4": 10_000, "eleven_v3": 5_000}
API = "https://api.elevenlabs.io/v1/text-to-speech"


def is_mp3(data):
    """ID3 tag or a raw MPEG frame sync, and more than an error body's worth of bytes."""
    return len(data) > 2_000 and (data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0))


def build_body(text, a, previous_ids=None):
    body = {"text": text, "model_id": a.model,
            "voice_settings": {"stability": a.stability, "similarity_boost": a.similarity}}
    if a.seed is not None:
        body["seed"] = a.seed
    if a.language_code:
        body["language_code"] = a.language_code
    if previous_ids:
        body["previous_request_ids"] = previous_ids[-3:]  # API maximum is 3
    return body


def tts(key, voice, clip_id, text, a, previous_ids=None):
    """Returns (clip_id, ok, message, request_id)."""
    data_out = json.dumps(build_body(text, a, previous_ids)).encode("utf-8")
    url = f"{API}/{voice}?output_format=mp3_44100_128"
    path = os.path.join(a.outdir, f"{a.prefix}{clip_id}.mp3")
    for attempt in range(5):
        req = urllib.request.Request(url, data=data_out, method="POST",
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data, rid = r.read(), r.headers.get("request-id")
            # Check the bytes are audio, not an error body that would be saved as .mp3.
            # A size threshold misfires: a short Hebrew line is legitimately < 100 KB.
            if not is_mp3(data):
                raise RuntimeError(f"response is not mp3 ({len(data)}B): {data[:120]!r}")
            open(path, "wb").write(data)
            return clip_id, True, f"OK {len(data)}B", rid
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:  # concurrency limit / transient
                time.sleep(4 * (attempt + 1)); continue
            return clip_id, False, f"HTTP {e.code} {e.read()[:300]!r}", None
        except Exception as e:
            if attempt < 4:
                time.sleep(3); continue
            return clip_id, False, f"FAILED {e}", None
    return clip_id, False, "FAILED after retries (429/5xx)", None


def main():
    ap = argparse.ArgumentParser(description="One ElevenLabs clip per scripts.json entry.")
    ap.add_argument("scripts"); ap.add_argument("voice"); ap.add_argument("outdir")
    ap.add_argument("--model", default="eleven_v4",
                    help="eleven_v4 (default) | eleven_v3 (only to match audio already made on v3)")
    ap.add_argument("--stability", type=float, default=0.5,
                    help="0-1, continuous on v4: lower = more expressive and varied, "
                         "higher = closer to a fixed baseline. Keep ONE value per batch.")
    ap.add_argument("--similarity", type=float, default=0.75,
                    help="0-1, adherence to the reference voice (honoured on v4)")
    ap.add_argument("--seed", type=int, default=None,
                    help="best-effort determinism; fix it to make a single-clip redo sound closer")
    ap.add_argument("--language-code", default=None,
                    help="ISO 639-1 (e.g. he). Helps short/ambiguous text; unsupported codes are ignored")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--stitch", action="store_true",
                    help="generate sequentially, passing the previous clips' request ids "
                         "(previous_request_ids) for smoother prosody across clips. Slower; "
                         "ids expire after 2 hours")
    ap.add_argument("--prefix", default="slide", help="output filename prefix (default: slide)")
    a = ap.parse_args()

    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        ap.error("set ELEVENLABS_API_KEY env var (never paste the key into commands/output)")
    if not 0 <= a.stability <= 1 or not 0 <= a.similarity <= 1:
        ap.error("--stability and --similarity must be between 0 and 1")

    scripts = json.load(open(a.scripts))
    limit = CHAR_LIMITS.get(a.model, 5_000)
    too_long = {k: len(v) for k, v in scripts.items() if len(v) > limit}
    if too_long:
        sys.exit(f"over the {limit:,}-char {a.model} request limit: {too_long} - split those entries")
    os.makedirs(a.outdir, exist_ok=True)
    print(f"model={a.model} stability={a.stability} similarity={a.similarity} "
          f"seed={a.seed} stitch={a.stitch}", flush=True)

    results = {}
    if a.stitch:
        prev = []
        for k in sorted(scripts):
            results[k] = tts(key, a.voice, k, scripts[k], a, prev)
            print(f"{a.prefix}{k}: {results[k][2]}", flush=True)
            if results[k][3]:
                prev.append(results[k][3])
    else:
        with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
            futs = [ex.submit(tts, key, a.voice, k, v, a) for k, v in scripts.items()]
            for f in as_completed(futs):
                r = f.result(); results[r[0]] = r
                print(f"{a.prefix}{r[0]}: {r[2]}", flush=True)

    manifest_path = os.path.join(a.outdir, "_manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    for k, (_, ok, _, rid) in results.items():
        if ok:
            manifest[k] = {"model": a.model, "stability": a.stability, "similarity": a.similarity,
                           "seed": a.seed, "voice": a.voice, "request_id": rid,
                           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    json.dump(manifest, open(manifest_path, "w"), indent=1, sort_keys=True)
    mixed = {(m["model"], m["stability"], m["voice"]) for m in manifest.values()}
    if len(mixed) > 1:
        print(f"\nWARNING: outdir now mixes settings {sorted(mixed)} - audible across clips; "
              "regenerate all clips at one setting", file=sys.stderr)

    failures = [k for k, r in results.items() if not r[1]]
    if failures:
        print(f"\n{len(failures)} FAILURES {sorted(failures)} - regenerate those before using the set",
              file=sys.stderr)
        sys.exit(1)
    print("\nall clips OK")


if __name__ == "__main__":
    main()
