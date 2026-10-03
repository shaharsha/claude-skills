#!/usr/bin/env python3
"""Lip-sync a video to an audio track with Sync 3 on fal.ai (fal-ai/sync-lipsync/v3), stdlib only.

  FAL_KEY=... python3 lipsync_fal.py video.mp4 audio.wav out.mp4 [--face X,Y@FRAME] [--sync-mode cut_off]
  FAL_KEY=... python3 lipsync_fal.py --jobs jobs.json [--concurrency 6]
      jobs.json: [{"video": "...", "audio": "...", "out": "...", "face": "400,520@36"}, ...]  (paths relative to it)

--face picks the speaker when more than one face is visible: a pixel on the speaker's face, in the video's own
resolution, on frame FRAME of the clip. Without it the model guesses, and in a two-shot it often animates the
wrong mouth. Video-to-video: the clip's motion is kept and only the mouth is re-timed. ~$0.13 per second of
output; a 3-5 s part takes ~70-150 s. FAL_KEY is the full key exactly as fal shows it (prefix included).
Existing outputs are skipped; a failure leaves no file.
"""
import argparse, json, mimetypes, os, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

MODEL = "fal-ai/sync-lipsync/v3"
REST = "https://rest.fal.ai"
CDN = "https://v3.fal.media"
QUEUE = "https://queue.fal.run"


def parse_face(spec):
    xy, frame = spec.split("@")
    x, y = (int(v) for v in xy.split(","))
    return [x, y], int(frame)


def build_args(video_url, audio_url, face=None, sync_mode="cut_off"):
    args = {"video_url": video_url, "audio_url": audio_url, "sync_mode": sync_mode}
    if face:
        xy, frame = face
        args["options"] = {"active_speaker_detection": {"auto_detect": False, "frame_number": frame, "coordinates": xy}}
    return args


def _json(url, key, body=None, opener=urllib.request.urlopen, timeout=120):
    headers = {"Authorization": f"Key {key}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET", headers=headers)
    with opener(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def upload(path, key, opener=urllib.request.urlopen):
    """fal's CDN: a short-lived upload token from the REST API, then one POST of the raw bytes (files < 100 MB)."""
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    tok = _json(f"{REST}/storage/auth/token?storage_type=fal-cdn-v3", key, {}, opener)
    req = urllib.request.Request(f"{CDN}/files/upload", data=open(path, "rb").read(), method="POST",
                                 headers={"Authorization": f"{tok['token_type']} {tok['token']}", "Content-Type": ctype,
                                          "X-Fal-File-Name": os.path.basename(path)})
    with opener(req, timeout=300) as r:
        return json.loads(r.read())["access_url"]


RETRY_CODES = (429, 500, 502, 503, 504)


def _retrying(fn, sleep, tries=4):
    """Call fn(); retry transient failures (429/5xx, connection errors) with a growing pause."""
    for attempt in range(tries):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_CODES or attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == tries - 1:
                raise
        sleep(5 * (attempt + 1))


def _download(url, opener):
    with opener(urllib.request.Request(url), timeout=300) as r:
        return r.read()


def _why(e):
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code} {e.read()[:300].decode('utf-8', 'replace')}"
    return f"{type(e).__name__}: {e}"


def run(video, audio, out, key, face=None, sync_mode="cut_off", opener=urllib.request.urlopen, sleep=time.sleep,
        poll=5, max_wait=1800):
    try:
        args = build_args(upload(video, key, opener), upload(audio, key, opener), face, sync_mode)
        sub = _json(f"{QUEUE}/{MODEL}", key, args, opener)
    except Exception as e:  # nothing was submitted, nothing billed: a plain rerun is safe
        return _why(e)
    # from here on the job runs (and bills) at fal: every failure names it so the result can be fetched later
    where = f"(request {sub.get('request_id')}, result at {sub.get('response_url')})"
    try:
        waited = 0
        while True:
            st = _retrying(lambda: _json(sub["status_url"], key, opener=opener), sleep)
            if st.get("status") == "COMPLETED":
                if st.get("error"):
                    return f"failed: {st['error']} ({st.get('error_type', '')}) {where}"
                break
            if waited >= max_wait:
                return f"timed out after {max_wait}s {where}"
            sleep(poll)
            waited += poll
        res = _retrying(lambda: _json(sub["response_url"], key, opener=opener), sleep)
        url = (res.get("video") or {}).get("url")
        if not url:
            return f"no video in result: {json.dumps(res)[:300]} {where}"
        data = _retrying(lambda: _download(url, opener), sleep)
    except Exception as e:
        return f"{_why(e)} {where}"
    tmp = out + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, out)
    return "OK"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?"); ap.add_argument("audio", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--face"); ap.add_argument("--sync-mode", default="cut_off")
    ap.add_argument("--jobs"); ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--force", action="store_true", help="sync again even when the output exists (a corrected --face)")
    a = ap.parse_args()
    key = os.environ.get("FAL_KEY") or sys.exit("set FAL_KEY (the full key exactly as fal shows it)")
    if a.jobs:
        root = os.path.dirname(os.path.abspath(a.jobs))
        jobs = [{k: (os.path.join(root, v) if k in ("video", "audio", "out") else v) for k, v in j.items()}
                for j in json.load(open(a.jobs))]
    elif a.video and a.audio and a.out:
        jobs = [{"video": a.video, "audio": a.audio, "out": a.out, "face": a.face}]
    else:
        ap.error("give video audio out, or --jobs jobs.json")
    todo = []
    for j in jobs:
        if os.path.exists(j["out"]) and not a.force:
            print(f"  {os.path.basename(j['out'])}: exists, skipped (--force to sync again)")
        else:
            todo.append(j)

    def one(j):
        t0 = time.time()
        try:
            os.makedirs(os.path.dirname(os.path.abspath(j["out"])), exist_ok=True)
            face = parse_face(j["face"]) if j.get("face") else None
            msg = run(j["video"], j["audio"], j["out"], key, face, a.sync_mode)
        except Exception as e:  # a bad job entry must not hide the other jobs' results
            msg = f"failed: {e!r}"
        return j, f"{msg} {time.time() - t0:.0f}s"

    bad = []
    with ThreadPoolExecutor(a.concurrency) as ex:
        for j, msg in ex.map(one, todo):
            print(f"  {os.path.basename(j['out'])}: {msg}", flush=True)
            if not msg.startswith("OK"):
                bad.append(j["out"])
    if bad:
        sys.exit(f"failed: {bad}")


if __name__ == "__main__":
    main()
