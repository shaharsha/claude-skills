#!/usr/bin/env python3
"""Force-align finished narration clips against their scripts.

Turns clips you already generated into per-character timings, so anything that
must follow the voice (subtitles, on-screen highlights) is derived from what was
actually said rather than estimated. The audio stays the master.

  ELEVENLABS_API_KEY=... python3 align_narration.py scripts.json audio/ alignment/ [--prefix slide]

Reads audio/<prefix>NN.mp3 (the names generate_tts.py writes) and writes
alignment/<prefix>NN.json: {stripped, characters[], words[], loss}.
`characters` maps 1:1 onto the tag-stripped script, so a character offset in the
script converts straight to a timestamp.
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

# Anything in square brackets is a tag. v4 tags are free-form directions -
# "[Pause, dry amusement]", "[a tired detective who has heard it all before]" -
# so a letters-and-spaces pattern silently misses them and they reach the aligner.
TAG = re.compile(r"\[[^\[\]\n]*\]")

def strip_tags(s):
    """Audio tags are performed, not spoken. Leave them in and the aligner hunts
    for 'confident' in the audio, dragging every later offset with it."""
    # A tag becomes a space, not nothing: "agent.[Brief pause]Then" must not glue
    # into "agent.Then"; then drop the space a removed tag leaves before punctuation.
    s = re.sub(r"\s+", " ", TAG.sub(" ", s))
    return re.sub(r" ([,.;:!?…])", r"\1", s).strip()

def align(mp3, text, key, retries=3):
    b = "----align"
    body = b"".join([
        f'--{b}\r\nContent-Disposition: form-data; name="text"\r\n\r\n{text}\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\n'
        f'Content-Type: audio/mpeg\r\n\r\n'.encode(),
        open(mp3, "rb").read(),
        f"\r\n--{b}--\r\n".encode()])
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                "https://api.elevenlabs.io/v1/forced-alignment", data=body,
                headers={"xi-api-key": key,
                         "Content-Type": f"multipart/form-data; boundary={b}"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:200]!r}")
    raise RuntimeError("alignment failed")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts"); ap.add_argument("audio_dir"); ap.add_argument("out_dir")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--prefix", default="slide", help="clip filename prefix (default: slide)")
    a = ap.parse_args()
    key = os.environ.get("ELEVENLABS_API_KEY") or sys.exit("ELEVENLABS_API_KEY not set")
    scripts = json.load(open(a.scripts))
    os.makedirs(a.out_dir, exist_ok=True)

    def one(k):
        mp3 = os.path.join(a.audio_dir, f"{a.prefix}{k}.mp3")
        if not os.path.exists(mp3):
            return k, f"MISSING {mp3}", False
        stripped = strip_tags(scripts[k])
        if "[" in stripped or "]" in stripped:  # unclosed tag: would be "spoken" to the aligner
            return k, f"UNBALANCED BRACKET left after stripping: {stripped[:80]!r}", False
        res = align(mp3, stripped, key)
        chars = res.get("characters", [])
        json.dump({"stripped": stripped, "characters": chars,
                   "words": res.get("words", []), "loss": res.get("loss")},
                  open(os.path.join(a.out_dir, f"{a.prefix}{k}.json"), "w"))
        ok = len(chars) == len(stripped)
        return k, f"chars={len(chars)} text={len(stripped)} loss={res.get('loss'):.3f}", ok

    bad = []
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        for k, msg, ok in sorted(ex.map(one, sorted(scripts))):
            if not ok: bad.append(k)
            print(f"  {a.prefix}{k}: {'OK ' if ok else 'LENGTH MISMATCH'} {msg}", flush=True)
    if bad:
        sys.exit(f"\nlength mismatch on {bad} - offsets on those slides would be wrong")
    print("\nall clips aligned; character counts match their scripts")

if __name__ == "__main__":
    main()
