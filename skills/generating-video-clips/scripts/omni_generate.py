#!/usr/bin/env python3
"""Image -> short video clip with Gemini Omni Flash (gemini-omni-1.1-flash) through Google's Interactions API.

  GEMINI_API_KEY=... python3 omni_generate.py jobs.json out/ [--only S05 S09] [--takes 3] [--concurrency 4]
      [--aspect 9:16] [--resolution 720p]

jobs.json: {"base": "Bring this still to life as it is: same art style ... nobody new, one continuous shot. ",
            "jobs": {"S05": {"image": "panels/p05.png", "prompt": "[0-3s] ... [3-6s] ..."}}}
The base is prefixed to every job's prompt; image paths are relative to jobs.json. Writes out/<id>.mp4, or
out/<id>_t1.mp4 ... with --takes > 1, and never overwrites: an existing file is skipped, so a rerun after a
partial failure only pays for what is missing. Each call is synchronous (~25-35 s). The clip carries Omni's
own invented audio track: mute it downstream.
"""
import argparse, base64, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = "gemini-omni-1.1-flash"


def api_key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_IMAGE_API_KEY")
    if not k:
        sys.exit("set GEMINI_API_KEY (a Google AI Studio key)")
    return k


def to_jpeg(path):
    """The image as JPEG bytes, fitted inside 1080x1920 (bigger inputs only cost upload time)."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "in.jpg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", path, "-vf",
                        "scale=w='min(1080,iw)':h='min(1920,ih)':force_original_aspect_ratio=decrease",
                        "-q:v", "3", out], check=True)
        return open(out, "rb").read()


def build_body(jpeg, prompt, aspect="9:16", resolution="720p"):
    return {"model": MODEL,
            "input": [{"type": "image", "data": base64.b64encode(jpeg).decode(), "mime_type": "image/jpeg"},
                      {"type": "text", "text": prompt}],
            "response_format": {"type": "video", "aspect_ratio": aspect, "resolution": resolution},
            "store": False, "background": False, "stream": False}


def extract_video(js):
    for step in js.get("steps", []):
        if step.get("type") == "model_output":
            for c in step.get("content", []):
                if c.get("data") and "video" in c.get("mime_type", "video"):
                    return base64.b64decode(c["data"])
    return None


def generate(body, key, out, opener=urllib.request.urlopen, sleep=time.sleep):
    """One clip -> out. Returns a one-line status. Retries 429/500/503; never leaves a partial file."""
    data = json.dumps(body).encode()
    for attempt in range(3):
        req = urllib.request.Request(API, data=data, method="POST",
                                     headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        t0 = time.time()
        try:
            with opener(req, timeout=900) as r:
                js = json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode("utf-8", "replace")
            if e.code in (429, 500, 503) and attempt < 2:
                sleep(20 * (attempt + 1))
                continue
            return f"HTTP {e.code} {msg}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:  # synchronous call: nothing billed yet
            if attempt < 2:
                sleep(20 * (attempt + 1))
                continue
            return f"network error: {e}"
        video = extract_video(js)
        if not video:
            return f"no video in response (status {js.get('status')})"
        tmp = out + ".part"
        with open(tmp, "wb") as fh:
            fh.write(video)
        os.replace(tmp, out)
        return f"OK {time.time() - t0:.0f}s {len(video) // 1024} KB"
    return "gave up after 3 attempts"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jobs"); ap.add_argument("out_dir")
    ap.add_argument("--only", nargs="*"); ap.add_argument("--takes", type=int, default=1)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--aspect", default="9:16"); ap.add_argument("--resolution", default="720p")
    a = ap.parse_args()
    spec = json.load(open(a.jobs, encoding="utf-8"))
    root = os.path.dirname(os.path.abspath(a.jobs))
    key = api_key()
    os.makedirs(a.out_dir, exist_ok=True)
    work = []
    for jid, j in spec["jobs"].items():
        if a.only and jid not in a.only:
            continue
        for t in range(1, a.takes + 1):
            name = f"{jid}.mp4" if a.takes == 1 else f"{jid}_t{t}.mp4"
            out = os.path.join(a.out_dir, name)
            if os.path.exists(out):
                print(f"  {name}: exists, skipped")
                continue
            work.append((name, os.path.join(root, j["image"]), spec.get("base", "") + j["prompt"], out))

    def one(w):
        name, img, prompt, out = w
        try:
            return name, generate(build_body(to_jpeg(img), prompt, a.aspect, a.resolution), key, out)
        except Exception as e:  # a bad image or job must not hide the other jobs' results
            return name, f"failed: {e!r}"

    bad = []
    with ThreadPoolExecutor(a.concurrency) as ex:
        for name, msg in ex.map(one, work):
            print(f"  {name}: {msg}", flush=True)
            if not msg.startswith("OK"):
                bad.append(name)
    if bad:
        sys.exit(f"failed: {bad}")


if __name__ == "__main__":
    main()
