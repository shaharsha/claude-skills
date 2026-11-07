#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["google-auth", "requests"]
# ///
"""
Sync a .pptx file to an existing Google Slides presentation.

Pipeline:
  0. Guard: refuse if a person edited the deck since this script last pushed
     it (--force overrides); warn about pptx audio and charts, which the
     import drops or flattens
  1. Replace the deck with the pptx (Drive resumable upload; Google
     converts it), optionally rename the file (--title), report page size,
     and say how to restore narration videos the push deleted
  2. Rewrite broken in-deck slide refs (slide-N.xml, #slideN) to native links
  3. Rewrite cross-deck links (other.pptx#anchor) to deep-links into the
     sibling Slides, when --cross-pres-map is provided
  4. Shrink images wider than the page, keeping them on the page
  5. Optional RIGHT_TO_LEFT direction on every text shape (--rtl)
  6. Optional QA output: per-slide thumbnails (--thumbnails DIR), a PDF
     (--export-pdf PATH)

Narration: Google drops pptx audio on import. Push the audio-free pptx,
then attach per-slide Drive videos with the narrating-pptx skill's
scripts/gslides_narration.py (insert, then check), after every push.

Usage:
    sync-gslides.py deck.pptx --pres-id <FILE_ID> [--sa-key <path>] [--rtl]
        [--title "Name in Drive"] [--no-links] [--max-image-width <pt>]
        [--cross-pres-map "name.pptx=PRES_ID" ...]
        [--thumbnails DIR] [--export-pdf PATH] [--force]

Auth (first match wins): --sa-key, $GOOGLE_SA_KEY,
~/.config/gdoc-sync/sa-key.json, then gcloud ADC. Runs on a bare python3:
without google-auth it signs the JWT with `cryptography` or the openssl CLI.
The service account needs Editor on the deck; its project needs the Drive
and Slides APIs enabled.

Backup: the push replaces the whole deck. Every push is a new entry in
File → Version history, which is the way back.
"""
import argparse
import base64
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BASE_DELAY = 1.5

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
SA_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/presentations",
]
DEFAULT_SA_KEY = Path.home() / ".config" / "gdoc-sync" / "sa-key.json"
SA_KEY_ENV = "GOOGLE_SA_KEY"
STATE_FILE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "gdoc-sync" / "state.json"
SLIDES = "https://slides.googleapis.com/v1/presentations"
DRIVE = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
EMU_PER_PT = 12700

LINK_TEXT_NUM_RE = re.compile(r"(\d+)")
BROKEN_SLIDE_URL_RES = [
    re.compile(r"(?:^|/)slide[-_]?(\d+)(?:\.xml)?$", re.IGNORECASE),
    re.compile(r"^#slide[-_]?(\d+)$", re.IGNORECASE),
]
AUDIO_EXT = (".mp3", ".m4a", ".wav", ".wma", ".aac", ".ogg")

SA_EMAIL = None
SELF_EMAIL = None


def google_slugify(text: str) -> str:
    s = text.lower().replace("/", " ")
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", "-", s).strip("-")


# ─── Auth ─────────────────────────────────────────────────────────────────

def resolve_sa_key(sa_key):
    """--sa-key, then $GOOGLE_SA_KEY, then the default path if it exists."""
    for cand, label in ((sa_key, "--sa-key"), (os.environ.get(SA_KEY_ENV), f"${SA_KEY_ENV}")):
        if cand:
            p = Path(cand).expanduser()
            if not p.is_file():
                sys.exit(f"error: {label} points at a missing file: {p}")
            return p
    return DEFAULT_SA_KEY if DEFAULT_SA_KEY.is_file() else None


def get_token(sa_key=None) -> str:
    key = resolve_sa_key(sa_key)
    if key:
        return _token_from_service_account(key)
    env = os.environ.copy()
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    try:
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token",
             "--scopes=" + ",".join(SA_SCOPES)],
            env=env, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        sys.exit("error: no service-account key found and gcloud is not on PATH.\n"
                 f"  pass --sa-key PATH, set ${SA_KEY_ENV}, or put the key at {DEFAULT_SA_KEY}")
    except subprocess.CalledProcessError as e:
        sys.exit("error: gcloud ADC auth failed. Pass --sa-key, or log in with the scopes:\n"
                 "  gcloud auth application-default login --scopes="
                 + ",".join(SA_SCOPES) + ",https://www.googleapis.com/auth/cloud-platform\n"
                 f"\ngcloud stderr:\n{e.stderr}")
    return result.stdout.strip()


def _token_from_service_account(sa_key: Path) -> str:
    global SA_EMAIL
    sa = json.loads(sa_key.read_text())
    SA_EMAIL = sa.get("client_email")
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except ImportError:
        pass
    else:
        creds = service_account.Credentials.from_service_account_info(sa, scopes=SA_SCOPES)
        creds.refresh(Request())
        return creds.token

    def b64(d) -> bytes:
        return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=")

    now = int(time.time())
    signing_input = b64({"alg": "RS256", "typ": "JWT", "kid": sa.get("private_key_id")}) + b"." + b64({
        "iss": sa["client_email"], "scope": " ".join(SA_SCOPES),
        "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600,
    })
    sig = _rs256_sign(sa["private_key"], signing_input)
    assertion = signing_input + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": assertion.decode()}).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"error: token exchange failed (HTTP {e.code}): {e.read().decode('utf-8', 'replace')[:400]}")


def _rs256_sign(pem: str, data: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        pass
    else:
        key = serialization.load_pem_private_key(pem.encode(), password=None)
        return key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    openssl = shutil.which("openssl")
    if not openssl:
        sys.exit("error: service-account auth needs google-auth, cryptography or the openssl CLI.\n"
                 "  run with `uv run sync-gslides.py ...` or `pip install google-auth requests`")
    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(pem)
        return subprocess.run([openssl, "dgst", "-sha256", "-sign", path],
                              input=data, capture_output=True, check=True).stdout
    finally:
        os.unlink(path)


# ─── HTTP ─────────────────────────────────────────────────────────────────

def api(token, method, url, body=None, content_type="application/json", extra_headers=None,
        return_response=False, raw=False):
    """Call a Google API, retrying transient failures (429/5xx)."""
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError("api(token, method, url, body): url must start with https://")
    headers = {"Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode() if content_type == "application/json" else body
        headers["Content-Type"] = content_type

    last_err = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                if return_response:
                    return {"headers": dict(resp.headers), "body": resp.read(), "status": resp.status}
                payload = resp.read()
                if raw:
                    return payload
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            if e.code in RETRYABLE_STATUS and attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"  ! HTTP {e.code} on {method} {url.split('?')[0]} — retrying in {delay:.1f}s "
                      f"(attempt {attempt + 1}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(delay)
                last_err = e
                continue
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            print(f"HTTP {e.code} on {method} {url.split('?')[0]}:\n{err_body[:1200]}", file=sys.stderr)
            if "has not been used" in err_body or "is disabled" in err_body:
                print("hint: enable the Drive API and the Slides API in the service account's project",
                      file=sys.stderr)
            elif e.code in (403, 404):
                print(f"hint: share the file with {SA_EMAIL or 'the service account'} as Editor",
                      file=sys.stderr)
            raise
        except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"  ! {type(e).__name__} on {method} — retrying in {delay:.1f}s", file=sys.stderr)
                time.sleep(delay)
                last_err = e
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("unreachable: retry loop exited without success or error")


def get_pres(token, pres_id, fields=None):
    url = f"{SLIDES}/{pres_id}"
    if fields:
        url += "?fields=" + urllib.parse.quote(fields)
    return api(token, "GET", url)


def batch(token, pres_id, requests, chunk=400):
    """Slides batchUpdate takes up to 500 requests per call; chunk below that."""
    for i in range(0, len(requests), chunk):
        api(token, "POST", f"{SLIDES}/{pres_id}:batchUpdate", body={"requests": requests[i:i + chunk]})


def _unit_to_pt(magnitude, unit):
    return magnitude / EMU_PER_PT if unit == "EMU" else magnitude


def page_size_pt(pres):
    ps = pres.get("pageSize", {})
    w, h = ps.get("width", {}), ps.get("height", {})
    return (_unit_to_pt(w.get("magnitude", 0), w.get("unit", "EMU")),
            _unit_to_pt(h.get("magnitude", 0), h.get("unit", "EMU")))


# ─── Step 0: guard + pptx audit ───────────────────────────────────────────

def drive_meta(token, file_id):
    fields = "name,modifiedTime,lastModifyingUser(displayName,emailAddress)"
    return api(token, "GET", f"{DRIVE}/{file_id}?fields={urllib.parse.quote(fields)}&supportsAllDrives=true")


def whoami(token: str) -> str:
    """The identity this run writes as: the service account, or the ADC user."""
    global SELF_EMAIL
    if SELF_EMAIL is None:
        SELF_EMAIL = SA_EMAIL or (api(token, "GET", "https://www.googleapis.com/drive/v3/about?fields="
                                      + urllib.parse.quote("user(emailAddress)")).get("user") or {}).get("emailAddress", "")
    return SELF_EMAIL


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except FileNotFoundError:
        return {}
    except ValueError:
        print(f"  ! {STATE_FILE} is unreadable; treating every file as never synced", file=sys.stderr)
        return {}


def mark_synced(token: str, file_id: str, source: str) -> None:
    """Record the file's modifiedTime right after the push. Revisions after
    it by anyone but us are a person's edits that the next push would lose."""
    meta = drive_meta(token, file_id)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_path = STATE_FILE.with_suffix(".lock")
    with open(lock_path, "w") as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)  # sibling syncs may run in parallel
        state = _load_state()
        state[file_id] = {"syncedAt": meta.get("modifiedTime"), "source": source}
        tmp = STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
        tmp.write_text(json.dumps(state, indent=2))
        os.replace(tmp, STATE_FILE)


def foreign_edits(token: str, file_id: str, since: str) -> list:
    """Revisions after `since` whose author isn't this run's identity."""
    me = whoami(token)
    fields = "nextPageToken,revisions(modifiedTime,lastModifyingUser(displayName,emailAddress))"
    out, page = [], None
    while True:
        url = (f"https://www.googleapis.com/drive/v3/files/{file_id}/revisions?pageSize=1000&fields="
               + urllib.parse.quote(fields) + (f"&pageToken={page}" if page else ""))
        resp = api(token, "GET", url)
        for r in resp.get("revisions", []):
            user = r.get("lastModifyingUser") or {}
            if r.get("modifiedTime", "") > since and user.get("emailAddress") != me:
                out.append((r["modifiedTime"], user.get("emailAddress") or user.get("displayName") or "someone"))
        page = resp.get("nextPageToken")
        if not page:
            return out


def check_edits(token: str, file_id: str, force: bool, noun: str, fix: str) -> None:
    last = _load_state().get(file_id)
    if not last:
        print(f"[0/6] No sync recorded for this {noun} yet; pushing (later runs refuse if a person "
              f"edited the {noun} in between)")
        return
    since = last.get("syncedAt") or last.get("modifiedTime") or ""
    edits = foreign_edits(token, file_id, since)
    if not edits:
        print(f"[0/6] {noun.capitalize()} unchanged by others since the last sync")
        return
    who = sorted({u for _, u in edits})
    msg = (f"the {noun} was edited by {', '.join(who)} (latest {max(t for t, _ in edits)}) after the last "
           f"sync ({since}); pushing would discard those edits")
    if not force:
        print(f"REFUSED: {msg}. {fix}, or pass --force.", file=sys.stderr)
        sys.exit(3)
    print(f"  ! {msg} (--force)", file=sys.stderr)


def guard(token, pres_id, force):
    """Refuse to overwrite edits a person made in the deck since the last push."""
    check_edits(token, pres_id, force, "deck", "Fold them into the pptx first")


def audit_pptx(pptx_path):
    """Warn about pptx content the Slides import drops."""
    try:
        with zipfile.ZipFile(pptx_path) as z:
            names = z.namelist()
            audio = [n for n in names if n.startswith("ppt/media/") and n.lower().endswith(AUDIO_EXT)]
            slides_with_audio = 0
            for n in names:
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", n):
                    xml = z.read(n)
                    if b"<p:audio" in xml or b"audioFile" in xml:
                        slides_with_audio += 1
            charts = [n for n in names if n.startswith("ppt/charts/chart") and n.endswith(".xml")]
    except zipfile.BadZipFile:
        sys.exit(f"error: {pptx_path} is not a valid pptx (zip) file")
    if audio or slides_with_audio:
        print(f"  ! the pptx has embedded audio ({len(audio)} files, {slides_with_audio} slides). Google "
              "Slides drops it on import and leaves each audio icon as a silent picture. Push an audio-free "
              "pptx and add narration with the narrating-pptx skill (scripts/gslides_narration.py).",
              file=sys.stderr)
    if charts:
        print(f"  ! the pptx has {len(charts)} native charts; the import turns charts into static images "
              "and can lose category labels. Render charts as images in the pptx if they matter.",
              file=sys.stderr)


# ─── Step 1: push ─────────────────────────────────────────────────────────

def narration_videos(token, pres_id):
    """(count, Drive folder) of the narr_* videos gslides_narration.py placed."""
    pres = get_pres(token, pres_id, "slides(pageElements(objectId,video(id)))")
    ids = [el["video"]["id"] for s in pres.get("slides", []) for el in s.get("pageElements", [])
           if el.get("objectId", "").startswith("narr_") and el.get("video", {}).get("id")]
    folder = None
    if ids:
        try:
            parents = api(token, "GET", f"{DRIVE}/{ids[0]}?fields=parents&supportsAllDrives=true").get("parents")
            folder = (parents or [None])[0]
        except urllib.error.HTTPError:
            pass
    return len(ids), folder


def push_pptx(token, pres_id, pptx_path, title=None, sa_key=None):
    """PATCH the pptx via Drive resumable upload (initiate, then PUT bytes)."""
    before = page_size_pt(get_pres(token, pres_id, "pageSize"))
    n_videos, folder = narration_videos(token, pres_id)
    with open(pptx_path, "rb") as f:
        content = f.read()
    size = len(content)
    init = api(
        token, "PATCH", f"{UPLOAD}/{pres_id}?uploadType=resumable&supportsAllDrives=true",
        body=json.dumps({"name": title}).encode() if title else b"{}",
        content_type="application/json; charset=UTF-8",
        extra_headers={"X-Upload-Content-Type": PPTX_MIME, "X-Upload-Content-Length": str(size)},
        return_response=True,
    )
    _put_resumable(init, content, PPTX_MIME)
    after = page_size_pt(get_pres(token, pres_id, "pageSize"))
    msg = f"[1/6] Pushed pptx: {pptx_path} ({size:,} bytes)"
    if title:
        msg += f"; renamed to {title!r}"
    if abs(before[0] - after[0]) > 0.5 or abs(before[1] - after[1]) > 0.5:
        msg += (f"; page size changed {before[0]:.0f}x{before[1]:.0f}pt → {after[0]:.0f}x{after[1]:.0f}pt "
                "(the pptx sets it; positions computed for the old size are now off)")
    else:
        msg += f"; page {after[0]:.0f}x{after[1]:.0f}pt"
    print(msg)
    if n_videos:
        key = f" --sa-key {sa_key}" if sa_key else ""
        print(f"  ! the push deleted {n_videos} narration videos. Put them back (narrating-pptx skill):\n"
              f"      python3 <narrating-pptx>/scripts/gslides_narration.py insert --pres {pres_id} "
              f"--folder {folder or 'FOLDER_ID'}{key}\n"
              f"      python3 <narrating-pptx>/scripts/gslides_narration.py check  --pres {pres_id} "
              f"--folder {folder or 'FOLDER_ID'}{key}", file=sys.stderr)


def _put_resumable(init, content, mime):
    upload_url = init["headers"].get("Location") or init["headers"].get("location")
    if not upload_url:
        raise RuntimeError(f"resumable init returned no Location header: {init['headers']}")
    last_err = None
    for attempt in range(MAX_RETRIES):
        # The Location URL is pre-authorised; no bearer token needed.
        req = urllib.request.Request(upload_url, data=content, method="PUT",
                                     headers={"Content-Type": mime, "Content-Length": str(len(content))})
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code in RETRYABLE_STATUS and attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"  ! HTTP {e.code} on resumable PUT — retrying in {delay:.1f}s", file=sys.stderr)
                time.sleep(delay)
                last_err = e
                continue
            err = e.read().decode("utf-8", errors="replace")
            print(f"HTTP {e.code} on resumable PUT:\n{err[:1200]}", file=sys.stderr)
            raise
    if last_err:
        raise last_err


# ─── Shared walkers ───────────────────────────────────────────────────────

def extract_text(text_obj):
    if not text_obj:
        return ""
    return "".join(el.get("textRun", {}).get("content", "") for el in text_obj.get("textElements", [])).strip()


def slide_title(slide):
    """TITLE/CENTERED_TITLE placeholder text, else the first non-empty text."""
    fallback = ""
    for el in slide.get("pageElements", []):
        shape = el.get("shape")
        if not shape:
            continue
        ptype = shape.get("placeholder", {}).get("type", "")
        text = extract_text(shape.get("text"))
        if ptype in ("TITLE", "CENTERED_TITLE") and text:
            return text
        if not fallback and text:
            fallback = text
    return fallback


def walk_text_shapes(presentation, fn):
    """fn(shape_object_id, text_obj, cell_location_or_None) for every text shape and table cell."""
    for slide in presentation.get("slides", []):
        for el in slide.get("pageElements", []):
            shape = el.get("shape")
            if shape and shape.get("text"):
                fn(el["objectId"], shape["text"], None)
            tbl = el.get("table")
            if tbl:
                for r_idx, row in enumerate(tbl.get("tableRows", [])):
                    for c_idx, cell in enumerate(row.get("tableCells", [])):
                        if cell.get("text"):
                            fn(el["objectId"], cell["text"], {"rowIndex": r_idx, "columnIndex": c_idx})


def _link_request(shape_oid, el, cell_location, link):
    req = {"updateTextStyle": {
        "objectId": shape_oid,
        "textRange": {"type": "FIXED_RANGE", "startIndex": el.get("startIndex", 0), "endIndex": el["endIndex"]},
        "style": {"link": link}, "fields": "link"}}
    if cell_location is not None:
        req["updateTextStyle"]["cellLocation"] = cell_location
    return req


# ─── Step 2: in-deck links ────────────────────────────────────────────────

def fix_slide_anchor_links(token, pres_id):
    pres = get_pres(token, pres_id)
    slides = pres.get("slides", [])
    index_to_oid = {i + 1: s["objectId"] for i, s in enumerate(slides)}
    slug_to_oid = {google_slugify(slide_title(s)): s["objectId"] for s in slides if slide_title(s)}
    requests = []

    def visit(shape_oid, text_obj, cell_location):
        for el in text_obj.get("textElements", []):
            tr = el.get("textRun")
            url = (tr or {}).get("style", {}).get("link", {}).get("url", "")
            if not url:
                continue  # no link, or already a pageObjectId/slideIndex/relativeLink link
            decoded = urllib.parse.unquote(url)
            target = None
            for pat in BROKEN_SLIDE_URL_RES:
                m = pat.search(decoded)
                if m:
                    target = index_to_oid.get(int(m.group(1)))
                    if target:
                        break
            if not target and decoded.startswith("#"):  # bare in-deck anchor only, never https://x#y
                anchor = decoded[1:]
                target = slug_to_oid.get(anchor) or slug_to_oid.get(google_slugify(anchor))
            if not target and decoded.lower().endswith(".xml"):
                m = LINK_TEXT_NUM_RE.search(tr.get("content", ""))
                if m:
                    target = index_to_oid.get(int(m.group(1)))
            if target:
                requests.append(_link_request(shape_oid, el, cell_location, {"pageObjectId": target}))

    walk_text_shapes(pres, visit)
    if requests:
        batch(token, pres_id, requests)
    print(f"[2/6] Fixed {len(requests)} in-deck slide-anchor links")
    return len(requests)


# ─── Step 3: cross-deck links ─────────────────────────────────────────────

def fix_cross_pres_links(token, pres_id, cross_pres_map):
    if not cross_pres_map:
        print("[3/6] Skipped cross-pres link rewriting (no --cross-pres-map)")
        return 0
    targets = {}
    for path, target_id in cross_pres_map.items():
        tp = get_pres(token, target_id)
        slug_map, index_map = {}, {}
        for i, s in enumerate(tp.get("slides", [])):
            index_map[i + 1] = s["objectId"]
            if slide_title(s):
                slug_map[google_slugify(slide_title(s))] = s["objectId"]
        targets[path] = (target_id, slug_map, index_map)

    pres = get_pres(token, pres_id)
    requests = []

    def visit(shape_oid, text_obj, cell_location):
        for el in text_obj.get("textElements", []):
            tr = el.get("textRun")
            url = (tr or {}).get("style", {}).get("link", {}).get("url", "")
            if not url:
                continue
            decoded = urllib.parse.unquote(url)
            for path, (target_id, slug_map, index_map) in sorted(targets.items(), key=lambda kv: -len(kv[0])):
                if path not in decoded:
                    continue
                anchor = decoded.rsplit("#", 1)[1] if "#" in decoded else ""
                oid = None
                if anchor:
                    oid = slug_map.get(anchor) or slug_map.get(google_slugify(anchor))
                    m = re.match(r"slide[-_]?(\d+)$", anchor, re.IGNORECASE)
                    if not oid and m:
                        oid = index_map.get(int(m.group(1)))
                if not oid:
                    m = LINK_TEXT_NUM_RE.search(tr.get("content", ""))
                    if m:
                        oid = index_map.get(int(m.group(1)))
                new_url = f"https://docs.google.com/presentation/d/{target_id}/edit"
                if oid:
                    new_url += f"#slide=id.{oid}"
                requests.append(_link_request(shape_oid, el, cell_location, {"url": new_url}))
                break  # next text run; other links in this shape still get rewritten

    walk_text_shapes(pres, visit)
    if requests:
        batch(token, pres_id, requests)
    print(f"[3/6] Fixed {len(requests)} cross-pres links")
    return len(requests)


# ─── Step 4: images ───────────────────────────────────────────────────────

def resize_oversized_images(token, pres_id, max_width_pt):
    """Shrink images whose effective width (size × scaleX) exceeds the max,
    keeping each image's center fixed. Default max = the page width."""
    pres = get_pres(token, pres_id)
    page_w, page_h = page_size_pt(pres)
    if max_width_pt is None:
        max_width_pt = page_w or 720
    requests = []
    for slide in pres.get("slides", []):
        for el in slide.get("pageElements", []):
            if "image" not in el:
                continue
            w, h = el.get("size", {}).get("width", {}), el.get("size", {}).get("height", {})
            base_w = _unit_to_pt(w.get("magnitude", 0), w.get("unit", "EMU"))
            base_h = _unit_to_pt(h.get("magnitude", 0), h.get("unit", "EMU"))
            if base_w <= 0 or base_h <= 0:
                continue
            tr = el.get("transform", {}) or {}
            sx, sy = tr.get("scaleX", 1) or 1, tr.get("scaleY", 1) or 1
            eff_w, eff_h = base_w * sx, base_h * sy
            if eff_w <= max_width_pt + 0.5:
                continue
            shrink = max_width_pt / eff_w
            unit = tr.get("unit", "EMU")
            to_native = EMU_PER_PT if unit == "EMU" else 1
            # Keep the center, then pull the image back inside the page if it still hangs off an edge.
            new_x = (tr.get("translateX", 0) or 0) / to_native + eff_w * (1 - shrink) / 2
            new_y = (tr.get("translateY", 0) or 0) / to_native + eff_h * (1 - shrink) / 2
            if page_w:
                new_x = min(max(new_x, 0), max(page_w - eff_w * shrink, 0))
            if page_h:
                new_y = min(max(new_y, 0), max(page_h - eff_h * shrink, 0))
            requests.append({"updatePageElementTransform": {
                "objectId": el["objectId"],
                "transform": {
                    "scaleX": sx * shrink, "scaleY": sy * shrink,
                    "shearX": tr.get("shearX", 0), "shearY": tr.get("shearY", 0),
                    "translateX": new_x * to_native,
                    "translateY": new_y * to_native,
                    "unit": unit,
                },
                "applyMode": "ABSOLUTE",
            }})
    if requests:
        batch(token, pres_id, requests)
    print(f"[4/6] Resized {len(requests)} oversized images (max width {max_width_pt:.0f}pt)")
    return len(requests)


# ─── Step 5: RTL ──────────────────────────────────────────────────────────

def apply_rtl(token, pres_id):
    pres = get_pres(token, pres_id)
    requests = []

    def visit(shape_oid, text_obj, cell_location):
        if not extract_text(text_obj):
            return
        req = {"updateParagraphStyle": {"objectId": shape_oid, "textRange": {"type": "ALL"},
                                        "style": {"direction": "RIGHT_TO_LEFT"}, "fields": "direction"}}
        if cell_location is not None:
            req["updateParagraphStyle"]["cellLocation"] = cell_location
        requests.append(req)

    walk_text_shapes(pres, visit)
    if requests:
        batch(token, pres_id, requests)
    print(f"[5/6] Applied RTL to {len(requests)} text shapes")
    return len(requests)


# ─── Step 6: QA output ────────────────────────────────────────────────────

def save_thumbnails(token, pres_id, out_dir):
    out = Path(out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    slides = get_pres(token, pres_id, "slides(objectId)").get("slides", [])
    for i, s in enumerate(slides, start=1):
        meta = api(token, "GET", f"{SLIDES}/{pres_id}/pages/{s['objectId']}/thumbnail"
                                 "?thumbnailProperties.thumbnailSize=LARGE&thumbnailProperties.mimeType=PNG")
        with urllib.request.urlopen(meta["contentUrl"], timeout=120) as resp:
            (out / f"slide-{i:02d}.png").write_bytes(resp.read())
    print(f"[6/6] Saved {len(slides)} slide thumbnails → {out}/slide-NN.png")


def export_pdf(token, pres_id, out):
    data = api(token, "GET", f"{DRIVE}/{pres_id}/export?mimeType=application/pdf", raw=True)
    Path(out).expanduser().write_bytes(data)
    print(f"[6/6] Exported PDF → {out} ({len(data):,} bytes)")


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)  # keep stdout and stderr lines in order when piped
    parser = argparse.ArgumentParser(
        description="Sync a .pptx to an existing Google Slides deck.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__,
    )
    parser.add_argument("pptx", help="Path to the .pptx file to push")
    parser.add_argument("--pres-id", required=True, help="Google Slides file ID (the long string in the URL)")
    parser.add_argument("--sa-key", default=None,
                        help=f"Service-account JSON key (default: ${SA_KEY_ENV}, then "
                             "~/.config/gdoc-sync/sa-key.json, then gcloud ADC)")
    parser.add_argument("--title", help="Also rename the deck in Drive")
    parser.add_argument("--rtl", action="store_true", help="RIGHT_TO_LEFT on every text shape (Hebrew/Arabic)")
    parser.add_argument("--no-links", action="store_true", help="Skip slide-anchor + cross-pres rewriting")
    parser.add_argument("--max-image-width", type=float, default=None,
                        help="Max image width in points (default: the page width); 0 skips")
    parser.add_argument("--cross-pres-map", action="append", default=[], metavar="NAME=PRES_ID",
                        help="Map a pptx filename (or path fragment in link URLs) to a sibling Slides ID. Repeatable.")
    parser.add_argument("--thumbnails", metavar="DIR", help="After syncing, save slide-NN.png renders")
    parser.add_argument("--export-pdf", metavar="PATH", help="After syncing, save a PDF render")
    parser.add_argument("--force", action="store_true",
                        help="Push even if someone edited the deck since the last sync")
    args = parser.parse_args()

    cross_pres_map = {}
    for entry in args.cross_pres_map:
        if "=" not in entry:
            print(f"error: --cross-pres-map expects NAME=PRES_ID, got {entry!r}", file=sys.stderr)
            return 1
        name, pid = entry.split("=", 1)
        cross_pres_map[name.strip()] = pid.strip()
    if not os.path.isfile(args.pptx):
        print(f"error: pptx file not found: {args.pptx}", file=sys.stderr)
        return 1

    token = get_token(args.sa_key)
    try:
        guard(token, args.pres_id, args.force)
        audit_pptx(args.pptx)
        push_pptx(token, args.pres_id, args.pptx, args.title, args.sa_key)  # gslides_narration finds the same default key
        mark_synced(token, args.pres_id, os.path.abspath(args.pptx))
        if not args.no_links:
            fix_slide_anchor_links(token, args.pres_id)
            fix_cross_pres_links(token, args.pres_id, cross_pres_map)
        else:
            print("[2/6] Skipped slide-anchor rewriting (--no-links)")
            print("[3/6] Skipped cross-pres rewriting (--no-links)")
        if args.max_image_width is None or args.max_image_width > 0:
            resize_oversized_images(token, args.pres_id, args.max_image_width)
        else:
            print("[4/6] Skipped image resize (--max-image-width 0)")
        if args.rtl:
            apply_rtl(token, args.pres_id)
        else:
            print("[5/6] Skipped RTL (use --rtl to enable)")
        if args.thumbnails:
            save_thumbnails(token, args.pres_id, args.thumbnails)
        if args.export_pdf:
            export_pdf(token, args.pres_id, args.export_pdf)
        if not (args.thumbnails or args.export_pdf):
            print("[6/6] Skipped QA output (use --thumbnails DIR or --export-pdf PATH)")
    except urllib.error.HTTPError:
        return 1
    print(f"Done. https://docs.google.com/presentation/d/{args.pres_id}/edit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
