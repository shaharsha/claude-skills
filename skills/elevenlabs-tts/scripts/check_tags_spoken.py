#!/usr/bin/env python3
"""Catch audio tags that were read aloud instead of performed - without ears.

  ELEVENLABS_API_KEY=... python3 check_tags_spoken.py scripts.json audio/ [--prefix slide]

Transcribes each clip with ElevenLabs Scribe (scribe_v2) and flags a clip when
  LEAK   a word from its tags shows up in the transcript more often than the
         script itself says it (e.g. "conversational" spoken from
         "[Warm, conversational tone]"), or
  EXTRA  the transcript runs noticeably longer than the tag-stripped script -
         the tell when a tag was spoken but transcribed in another script
         (an English tag inside Hebrew speech can come back as Hebrew letters).
Exits non-zero if any clip is flagged. Costs speech-to-text credits per minute of
audio - small next to regenerating a deck, but run it on samples, not on every draft.

This checks *spoken vs performed* only. Whether the performance is the right one
(over-acted, wrong emotion) still needs a human ear.
"""
import argparse, json, os, re, sys, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

TAG = re.compile(r"\[[^\[\]\n]*\]")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
# Glue words that appear in tags *and* in ordinary speech - useless as evidence.
STOP = {"and", "the", "with", "then", "but", "for", "into", "like", "who", "has",
        "her", "his", "from", "that", "this", "very", "more", "less", "after", "before",
        "slightly", "voice", "tone"}


def words(s):
    return [w.lower() for w in WORD.findall(s)]


def transcribe(mp3, key, language_code=None, retries=3):
    b = "----scribe"
    fields = [("model_id", "scribe_v2")] + ([("language_code", language_code)] if language_code else [])
    body = b"".join(
        f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode() for n, v in fields
    ) + (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\n'
         f'Content-Type: audio/mpeg\r\n\r\n').encode() + open(mp3, "rb").read() + f"\r\n--{b}--\r\n".encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body,
                                         headers={"xi-api-key": key,
                                                  "Content-Type": f"multipart/form-data; boundary={b}"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)["text"]
        except urllib.error.HTTPError as e:
            if (e.code == 429 or e.code >= 500) and attempt < retries:
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:200]!r}")
    raise RuntimeError("transcription failed")


def check(script, transcript, extra_ratio):
    spoken_script = TAG.sub(" ", script)
    tag_words = {w for t in TAG.findall(script) for w in words(t) if len(w) >= 3 and w not in STOP}
    said, meant = words(transcript), words(spoken_script)
    leaks = sorted(w for w in tag_words if said.count(w) > meant.count(w))
    ratio = len(said) / max(1, len(meant))
    return leaks, ratio, ratio > extra_ratio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts"); ap.add_argument("audio_dir")
    ap.add_argument("--prefix", default="slide")
    ap.add_argument("--language-code", default=None, help="ISO code hint for Scribe, e.g. he")
    ap.add_argument("--extra-ratio", type=float, default=1.15,
                    help="flag when transcript words / script words exceeds this")
    ap.add_argument("--only", nargs="*", help="check just these keys (e.g. a one-slide sample)")
    ap.add_argument("--concurrency", type=int, default=3)
    a = ap.parse_args()
    key = os.environ.get("ELEVENLABS_API_KEY") or sys.exit("ELEVENLABS_API_KEY not set")
    scripts = json.load(open(a.scripts))
    keys = sorted(a.only or scripts)

    def one(k):
        mp3 = os.path.join(a.audio_dir, f"{a.prefix}{k}.mp3")
        if not os.path.exists(mp3):
            return k, None, f"MISSING {mp3}"
        text = transcribe(mp3, key, a.language_code)
        return k, check(scripts[k], text, a.extra_ratio), text

    flagged = []
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        for k, res, text in ex.map(one, keys):
            if res is None:
                flagged.append(k); print(f"  {a.prefix}{k}: {text}"); continue
            leaks, ratio, extra = res
            status = "LEAK" if leaks else "EXTRA" if extra else "ok"
            if status != "ok":
                flagged.append(k)
            detail = f" spoken tag words: {leaks}" if leaks else ""
            print(f"  {a.prefix}{k}: {status:5} words said/scripted={ratio:.2f}{detail}", flush=True)
            if status != "ok":
                print(f"      transcript: {text[:300]}")
    if flagged:
        sys.exit(f"\n{len(flagged)} clip(s) need an ear-check / regeneration: {flagged}")
    print("\nno tag was read aloud in any checked clip")


if __name__ == "__main__":
    main()
