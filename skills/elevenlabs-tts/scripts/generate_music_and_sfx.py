#!/usr/bin/env python3
"""Music cues and sound effects from ElevenLabs, from one spec file.

  ELEVENLABS_API_KEY=... python3 generate_music_and_sfx.py sounds.json out/ [--only op whoosh] [--force]

sounds.json:
  {"op":     {"type": "music", "prompt": "Upbeat cartoon title theme ... No vocals.", "seconds": 52},
   "whoosh": {"type": "sfx",   "prompt": "quick swish for a scene transition", "seconds": 1.0}}

Music: POST /v1/music with model_id music_v2_5 (the endpoint still defaults to music_v1) and
force_instrumental true unless the entry says "vocals": true. Ask for more seconds than the cue must cover:
a cue that ends inside its window just stops. SFX: POST /v1/sound-generation (duration_seconds,
prompt_influence 0.5). Writes out/<name>.mp3 only for a real mp3; an error prints the API's own message
(missing_permissions, paid_plan_required, quota_exceeded) and leaves no file. Existing files are skipped.
"""
import argparse, json, os, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_tts import is_mp3  # noqa: E402

API = "https://api.elevenlabs.io/v1"


def request_for(name, spec):
    kind = spec.get("type")
    if kind == "music":
        return f"{API}/music", {"prompt": spec["prompt"], "music_length_ms": int(round(spec["seconds"] * 1000)),
                                "model_id": spec.get("model", "music_v2_5"),
                                "force_instrumental": not spec.get("vocals", False)}
    if kind == "sfx":
        return f"{API}/sound-generation", {"text": spec["prompt"], "duration_seconds": spec["seconds"],
                                           "prompt_influence": spec.get("influence", 0.5)}
    raise ValueError(f"{name}: type must be 'music' or 'sfx', got {kind!r}")


def post(url, body, out, key, opener=urllib.request.urlopen, sleep=time.sleep):
    data = json.dumps(body).encode()
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
        try:
            with opener(req, timeout=600) as r:
                audio = r.read()
        except urllib.error.HTTPError as e:
            if (e.code == 429 or e.code >= 500) and attempt < 4:
                sleep(5 * (attempt + 1))
                continue
            return f"HTTP {e.code} {e.read()[:300].decode('utf-8', 'replace')}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < 4:
                sleep(5 * (attempt + 1))
                continue
            return f"network error: {e}"
        if not is_mp3(audio):
            return f"not an mp3 ({len(audio)} bytes): {audio[:200]!r}"
        tmp = out + ".part"
        with open(tmp, "wb") as fh:
            fh.write(audio)
        os.replace(tmp, out)
        return f"OK {len(audio) // 1024} KB"
    return "gave up after 5 attempts"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec"); ap.add_argument("out_dir")
    ap.add_argument("--only", nargs="*"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--concurrency", type=int, default=3)
    a = ap.parse_args()
    key = os.environ.get("ELEVENLABS_API_KEY") or sys.exit("ELEVENLABS_API_KEY not set")
    spec = json.load(open(a.spec, encoding="utf-8"))
    os.makedirs(a.out_dir, exist_ok=True)
    todo = []
    for name, s in spec.items():
        if a.only and name not in a.only:
            continue
        out = os.path.join(a.out_dir, f"{name}.mp3")
        if os.path.exists(out) and not a.force:
            print(f"  {name}: exists, skipped (--force to regenerate)")
            continue
        todo.append((name, *request_for(name, s), out))

    bad = []
    with ThreadPoolExecutor(a.concurrency) as ex:
        for name, msg in ex.map(lambda t: (t[0], post(t[1], t[2], t[3], key)), todo):
            print(f"  {name}: {msg}", flush=True)
            if not msg.startswith("OK"):
                bad.append(name)
    if bad:
        sys.exit(f"failed: {bad}")


if __name__ == "__main__":
    main()
