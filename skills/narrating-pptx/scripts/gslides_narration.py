#!/usr/bin/env python3
"""Narration for a Google Slides deck: one autoplaying Drive video per slide.

Google's pptx import drops embedded audio every time (the speaker icon survives,
silent), and the Slides API cannot insert audio, only Drive or YouTube videos.
So each slide's mp3 becomes a small mp4 (a still badge plus the audio) that sits
in a corner of its slide and plays when the slide opens.

  # 1. one mp4 per clip, cut to the audio's exact length
  python3 gslides_narration.py videos audio/ videos/ [--still badge.png]
  # 2. put them in a Drive folder (updates in place when the files already exist)
  python3 gslides_narration.py upload videos/ --folder FOLDER_ID --sa-key sa.json
  # 3. wait until Drive has processed every file at its new length
  python3 gslides_narration.py wait videos/ --folder FOLDER_ID --sa-key sa.json
  # 4. place them on the slides, autoplaying (safe to re-run; run after every re-sync)
  python3 gslides_narration.py insert --pres PRES_ID --folder FOLDER_ID --sa-key sa.json [--skip 12 13] [--dry-run]
  # 5. read-only check: every narrated slide has its video, autoplaying, at the right length
  python3 gslides_narration.py check --pres PRES_ID --folder FOLDER_ID --sa-key sa.json [--videos videos/]

Videos are named narration-slideNN.mp4 and matched to slide NN by that number (older
names like "Narration - slide NN.mp4" or narration-slideNN-v3.mp4 match too; the
newest file for a slide wins).
Auth: --sa-key (a service account with Editor on the deck and the folder; needs
`pip install google-auth`), else gcloud application-default credentials.
A service account has no Drive storage of its own, so it cannot CREATE files in a
My Drive folder (403 "Service Accounts do not have storage quota"): `upload` then
lists the files for a person to drag into the folder once, and every later run
overwrites them in place, which works. A folder on a shared drive the account
belongs to avoids the manual step.
"""
import argparse, hashlib, json, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STILL = os.path.join(HERE, "..", "assets", "speaker-badge.png")
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/presentations"]
DRIVE = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
SLIDES = "https://slides.googleapis.com/v1/presentations"
# narration-slide05.mp4, and the hand-made names already in use: narration-slide05-v3.mp4, "Narration - slide 05.mp4"
NAME = re.compile(r"narration\W*slide\W*(\d+)(?:-v\d+)?\.mp4$", re.IGNORECASE)
PREFIX = "narr_"  # objectId prefix of the videos this script owns


# --- auth and HTTP -------------------------------------------------------------------------------

def get_token(sa_key=None):
    if sa_key:
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests as gar
        except ImportError:
            sys.exit("--sa-key needs `pip install google-auth` (or omit it to use gcloud ADC)")
        creds = service_account.Credentials.from_service_account_file(os.path.expanduser(sa_key), scopes=SCOPES)
        creds.refresh(gar.Request())
        return creds.token
    env = {k: v for k, v in os.environ.items() if k != "GOOGLE_APPLICATION_CREDENTIALS"}
    try:
        return subprocess.run(["gcloud", "auth", "application-default", "print-access-token"], env=env,
                              capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        sys.exit(f"no Google credentials: pass --sa-key, or run `gcloud auth application-default login` ({e})")


class Api:
    def __init__(self, token, opener=urllib.request.urlopen):
        self.token, self.opener = token, opener

    def call(self, method, url, body=None, raw=None, ctype="application/json"):
        """(status, parsed body). Retries 429/5xx; returns 4xx to the caller instead of raising."""
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        headers = {"Authorization": f"Bearer {self.token}"}
        if data is not None:
            headers["Content-Type"] = ctype
        for attempt in range(5):
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with self.opener(req, timeout=300) as r:
                    txt = r.read()
                    return r.status, (json.loads(txt) if txt else {})
            except urllib.error.HTTPError as e:
                if (e.code == 429 or e.code >= 500) and attempt < 4:
                    time.sleep(2 * (attempt + 1)); continue
                err = e.read().decode("utf-8", "replace")
                try:
                    return e.code, json.loads(err)
                except ValueError:
                    return e.code, {"error": {"message": err[:500]}}
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt < 4:
                    time.sleep(2 * (attempt + 1)); continue
                return 0, {"error": {"message": f"network error: {e}"}}
        return 0, {"error": {"message": "gave up after retries"}}

    def folder_videos(self, folder):
        """{slide_number: file} for narration-slideNN.mp4 in the folder; newest wins on duplicates."""
        # Drive's `name contains` matches word prefixes, so ask broadly and let NAME decide locally.
        q = urllib.parse.quote(f"'{folder}' in parents and trashed=false and name contains 'narration'")
        st, b = self.call("GET", f"{DRIVE}?q={q}&pageSize=200&supportsAllDrives=true&includeItemsFromAllDrives=true"
                                 "&fields=files(id,name,modifiedTime,md5Checksum,hasThumbnail,"
                                 "videoMediaMetadata(durationMillis))")
        if st != 200:
            sys.exit(f"listing folder {folder}: HTTP {st} {b.get('error', {}).get('message', b)}")
        out = {}
        for f in sorted(b.get("files", []), key=lambda f: f.get("modifiedTime", "")):
            m = NAME.search(f["name"])
            if m:
                out[int(m.group(1))] = f
        return out


# --- 1. videos -----------------------------------------------------------------------------------

def probe_seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60, check=True).stdout
    return float(out.strip())


def video_cmd(still, mp3, seconds, out):
    """Still image + audio -> mp4 of exactly `seconds`.

    -t, not -shortest: with a looped still, -shortest overshot by 30-50% in practice,
    which leaves the slide's video running on in silence.
    """
    return ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-framerate", "2", "-i", still, "-i", mp3, "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "2",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:a", "aac", "-b:a", "128k", "-t", f"{seconds:.3f}", "-movflags", "+faststart", out]


def slide_clips(audio_dir):
    """{slide_number: mp3 path} from audio/slideNN.mp3 (or the manifest's file names)."""
    clips = {}
    manifest = os.path.join(audio_dir, "_manifest.json")
    entries = json.load(open(manifest)) if os.path.exists(manifest) else {}
    for name in sorted(os.listdir(audio_dir)):
        m = re.match(r"slide(\d+)\.mp3$", name)
        if m:
            clips[int(m.group(1))] = os.path.join(audio_dir, name)
    for k, e in entries.items():
        if k.isdigit() and e.get("file") and int(k) not in clips:
            p = os.path.join(audio_dir, e["file"])
            if os.path.exists(p):
                clips[int(k)] = p
    return clips


def cmd_videos(a):
    still = a.still or DEFAULT_STILL
    clips = slide_clips(a.audio_dir)
    if not clips:
        sys.exit(f"no slideNN.mp3 in {a.audio_dir}")
    os.makedirs(a.out_dir, exist_ok=True)
    bad = []
    for n, mp3 in sorted(clips.items()):
        if a.only and n not in a.only:
            continue
        secs = probe_seconds(mp3)
        out = os.path.join(a.out_dir, f"narration-slide{n:02d}.mp4")
        subprocess.run(video_cmd(still, mp3, secs, out), check=True, stdin=subprocess.DEVNULL, timeout=600)
        got = probe_seconds(out)
        ok = abs(got - secs) <= 0.25
        bad += [] if ok else [n]
        print(f"slide {n:02d}: audio {secs:6.1f}s  video {got:6.1f}s  {'OK' if ok else 'LENGTH MISMATCH'}")
    if bad:
        sys.exit(f"video length differs from its audio on slides {bad}")


# --- 2. upload -----------------------------------------------------------------------------------

def multipart(meta, data, boundary="narration-boundary"):
    head = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
            f"--{boundary}\r\nContent-Type: video/mp4\r\n\r\n").encode()
    return head + data + f"\r\n--{boundary}--\r\n".encode(), f"multipart/related; boundary={boundary}"


def cmd_upload(a, api=None):
    api = api or Api(get_token(a.sa_key))
    existing = api.folder_videos(a.folder)
    local = sorted(f for f in os.listdir(a.videos_dir) if NAME.search(f))
    if not local:
        sys.exit(f"no narration-slideNN.mp4 in {a.videos_dir}")
    need_manual = []
    for name in local:
        n = int(NAME.search(name).group(1))
        data = open(os.path.join(a.videos_dir, name), "rb").read()
        if n in existing:
            st, b = api.call("PATCH", f"{UPLOAD}/{existing[n]['id']}?uploadType=media&supportsAllDrives=true",
                             raw=data, ctype="video/mp4")
            print(f"{name}: {'updated in place' if st == 200 else f'FAILED HTTP {st}'}")
            if st != 200:
                sys.exit(b.get("error", {}).get("message", b))
            continue
        body, ctype = multipart({"name": name, "parents": [a.folder], "mimeType": "video/mp4"}, data)
        st, b = api.call("POST", f"{UPLOAD}?uploadType=multipart&supportsAllDrives=true", raw=body, ctype=ctype)
        msg = json.dumps(b)
        if st == 200:
            print(f"{name}: created")
        elif st == 403 and ("storageQuotaExceeded" in msg or "storage quota" in msg):
            need_manual.append(name)
        else:
            sys.exit(f"{name}: HTTP {st} {b.get('error', {}).get('message', b)}")
    if need_manual:
        print(f"\nThe service account cannot create files in this folder (no Drive storage of its own).\n"
              f"Ask the user to drag these {len(need_manual)} file(s) from {os.path.abspath(a.videos_dir)} into the "
              f"folder once:\n  " + "\n  ".join(need_manual) +
              "\nEvery later run updates them in place. A shared-drive folder avoids this step.")
        sys.exit(2)


# --- 3. wait -------------------------------------------------------------------------------------

def drive_state(f, want_ms, want_md5, tol_ms=300):
    """'' when Drive's copy is this exact file, processed; otherwise what is still wrong.

    The checksum proves the content is the new upload (a one-word script fix changes
    the length by well under a second, so length alone can't); the duration and the
    thumbnail prove Drive has finished processing it.
    """
    if not f:
        return "no video file in the folder"
    if f.get("md5Checksum") and want_md5 and f["md5Checksum"] != want_md5:
        return "Drive holds a different file than the local one"
    got = int((f.get("videoMediaMetadata") or {}).get("durationMillis") or 0)
    if not got or not f.get("hasThumbnail"):
        return "Drive is still processing it"
    if abs(got - want_ms) > tol_ms:
        return f"Drive length {got / 1000:.1f}s vs local {want_ms / 1000:.1f}s"
    return ""


def processed(files, local):
    """Slide numbers whose Drive copy is the local file, fully processed. local: {n: (ms, md5)}."""
    return sorted(n for n, (ms, md5) in local.items() if not drive_state(files.get(n), ms, md5))


def local_lengths(videos_dir):
    """{slide_number: (length_ms, md5)} for the local narration videos."""
    out = {}
    for f in os.listdir(videos_dir):
        m = NAME.search(f)
        if m:
            p = os.path.join(videos_dir, f)
            out[int(m.group(1))] = (probe_seconds(p) * 1000, hashlib.md5(open(p, "rb").read()).hexdigest())
    return out


def cmd_wait(a, api=None, sleep=time.sleep, clock=time.time):
    api = api or Api(get_token(a.sa_key))
    want = local_lengths(a.videos_dir)
    t0 = clock()
    while True:
        done = processed(api.folder_videos(a.folder), want)
        print(f"{int(clock() - t0)}s: {len(done)}/{len(want)} processed at their new length", flush=True)
        if len(done) == len(want):
            return
        if clock() - t0 > a.timeout:
            sys.exit(f"still processing after {a.timeout}s: slides {sorted(set(want) - set(done))}")
        sleep(20)


# --- 4. insert -----------------------------------------------------------------------------------

def placement(page_w, page_h, corner, size_frac, margin_frac=0.012):
    """(size, x, y) in EMU for a square badge in a corner, scaled to the page (pages change size on re-sync)."""
    size = page_w * size_frac
    m = page_w * margin_frac
    x = page_w - size - m if "right" in corner else m
    y = page_h - size - m if "bottom" in corner else m
    return size, x, y


def insert_requests(pres, files, corner="bottom-right", size_frac=0.05, skip=()):
    """batchUpdate requests: remove this script's earlier videos, then one autoplaying video per narrated slide."""
    w, h = (pres["pageSize"][k]["magnitude"] for k in ("width", "height"))
    unit = pres["pageSize"]["width"].get("unit", "EMU")
    if unit != "EMU":  # Slides reports EMU; PT appears in some exports
        w, h = w * 12700, h * 12700
    size, x, y = placement(w, h, corner, size_frac)
    reqs, placed = [], []
    for e in (el for s in pres["slides"] for el in s.get("pageElements", [])):
        if e["objectId"].startswith(PREFIX):
            reqs.append({"deleteObject": {"objectId": e["objectId"]}})
    for i, s in enumerate(pres["slides"], 1):
        if i in skip or i not in files:
            continue
        oid = f"{PREFIX}{i:02d}"
        reqs.append({"createVideo": {"objectId": oid, "source": "DRIVE", "id": files[i]["id"], "elementProperties": {
            "pageObjectId": s["objectId"],
            "size": {"width": {"magnitude": size, "unit": "EMU"}, "height": {"magnitude": size, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}}}})
        reqs.append({"updateVideoProperties": {"objectId": oid, "fields": "autoPlay,mute",
                                               "videoProperties": {"autoPlay": True, "mute": False}}})
        placed.append(i)
    return reqs, placed


def narr_videos(pres):
    """{slide_number: (drive_file_id, autoplay)} for this script's videos on the deck."""
    out = {}
    for i, s in enumerate(pres["slides"], 1):
        for e in s.get("pageElements", []):
            if e["objectId"].startswith(PREFIX) and "video" in e:
                v = e["video"]
                out[i] = (v.get("id"), bool(v.get("videoProperties", {}).get("autoPlay")))
    return out


def cmd_insert(a, api=None):
    api = api or Api(get_token(a.sa_key))
    files = api.folder_videos(a.folder)
    st, pres = api.call("GET", f"{SLIDES}/{a.pres}")
    if st != 200:
        sys.exit(f"reading the deck: HTTP {st} {pres.get('error', {}).get('message', pres)}")
    reqs, placed = insert_requests(pres, files, a.corner, a.size, set(a.skip or ()))
    missing = [i for i in range(1, len(pres["slides"]) + 1) if i not in files and i not in set(a.skip or ())]
    print(f"deck has {len(pres['slides'])} slides; folder has videos for {sorted(files)}")
    if missing:
        print(f"no video for slides {missing} (left without narration)")
    if a.dry_run:
        print(f"dry run: would send {len(reqs)} requests, placing videos on slides {placed}")
        return
    if not reqs:
        sys.exit("nothing to do")
    st, b = api.call("POST", f"{SLIDES}/{a.pres}:batchUpdate", {"requests": reqs})
    if st != 200:
        sys.exit(f"batchUpdate: HTTP {st} {b.get('error', {}).get('message', b)}")
    st, pres = api.call("GET", f"{SLIDES}/{a.pres}")
    if st != 200:
        sys.exit(f"the videos were sent, but re-reading the deck failed: HTTP {st} - run `check`")
    on = narr_videos(pres)
    playing = sorted(i for i, (_, auto) in on.items() if auto)
    print(f"autoplaying narration on {len(playing)} of {len(placed)} intended slides")
    if playing != sorted(placed):
        sys.exit(f"expected {sorted(placed)}, found {playing}")


# --- 5. check ------------------------------------------------------------------------------------

def cmd_check(a, api=None):
    api = api or Api(get_token(a.sa_key))
    files = api.folder_videos(a.folder)
    st, pres = api.call("GET", f"{SLIDES}/{a.pres}")
    if st != 200:
        sys.exit(f"reading the deck: HTTP {st} {pres.get('error', {}).get('message', pres)}")
    on = narr_videos(pres)
    want = local_lengths(a.videos_dir) if a.videos_dir else {}
    problems = []
    for i in range(1, len(pres["slides"]) + 1):
        if i in set(a.skip or ()):
            continue
        f, v = files.get(i), on.get(i)
        notes = []
        if not f:
            notes.append("no video file in the folder")
        if not v:
            notes.append("no narration video on the slide")
        elif f and v[0] != f["id"]:
            notes.append("slide shows an older file than the folder's")
        elif not v[1]:
            notes.append("autoplay is off")
        if f and want.get(i):
            state = drive_state(f, *want[i])
            if state:
                notes.append(state)
        print(f"slide {i:02d}: {'OK' if not notes else '; '.join(notes)}")
        if notes:
            problems.append(i)
    if problems:
        sys.exit(f"{len(problems)} slide(s) need attention: {problems}")
    print("every narrated slide has its video, autoplaying")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("videos"); v.add_argument("audio_dir"); v.add_argument("out_dir")
    v.add_argument("--still", help="square image shown while the clip plays (default: a speaker badge)")
    v.add_argument("--only", nargs="*", type=int, help="just these slide numbers")
    for name in ("upload", "wait"):
        p = sub.add_parser(name); p.add_argument("videos_dir")
        p.add_argument("--folder", required=True); p.add_argument("--sa-key")
        if name == "wait":
            p.add_argument("--timeout", type=int, default=600)
    for name in ("insert", "check"):
        p = sub.add_parser(name)
        p.add_argument("--pres", required=True); p.add_argument("--folder", required=True)
        p.add_argument("--sa-key"); p.add_argument("--skip", nargs="*", type=int, help="slides left unnarrated")
        if name == "insert":
            p.add_argument("--corner", default="bottom-right",
                           choices=["bottom-right", "top-right", "bottom-left", "top-left"])
            p.add_argument("--size", type=float, default=0.05, help="badge width as a fraction of the page width")
            p.add_argument("--dry-run", action="store_true")
        else:
            p.add_argument("--videos", dest="videos_dir", help="local videos dir, to compare lengths with Drive's")
    a = ap.parse_args(argv)
    {"videos": cmd_videos, "upload": cmd_upload, "wait": cmd_wait, "insert": cmd_insert, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
