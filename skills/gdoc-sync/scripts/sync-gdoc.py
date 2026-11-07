#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["google-auth", "requests"]
# ///
"""
Sync a markdown file to an existing Google Doc.

Pipeline:
  0. Guard: refuse if someone edited the Doc since this script last synced
     it (--force overrides), and refuse a Doc with several tabs (the push
     flattens them into one; --force overrides)
  1. Replace the Doc body with the markdown via the Drive upload API
     (Google converts it), and optionally rename the file (--title)
  2. Rewrite in-doc anchor links [text](#slug) -> native heading links
  3. Rewrite cross-doc links [text](other.md#anchor) -> deep-links into the
     sibling Doc, when --cross-doc-map is provided
  4. Resize oversized inline images (Google imports at source resolution)
  5. Optional RTL paragraph direction (Hebrew/Arabic)
  6. Optional styling that every push resets: line spacing, paragraph
     spacing, body font size, empty-paragraph removal
  7. Optional PDF export for visual QA (--export-pdf)

Usage:
    sync-gdoc.py <markdown-file> --doc-id <FILE_ID> [--sa-key <path>] [--rtl]
        [--title "Name in Drive"] [--no-links] [--max-image-width <pt>]
        [--cross-doc-map "name.md=DOC_ID" ...]
        [--line-spacing 100] [--space-below 3] [--heading-space-above 8]
        [--font-size 10] [--drop-empty-paragraphs] [--export-pdf out.pdf]
        [--force]

Auth (first match wins): --sa-key, $GOOGLE_SA_KEY,
~/.config/gdoc-sync/sa-key.json, then gcloud ADC. Runs on a bare python3:
without google-auth it signs the JWT with `cryptography` or the openssl CLI.
The service account needs Editor on the Doc, and its project needs the
Drive and Docs APIs enabled.

Backup: the push replaces the whole body. Every push is a new entry in the
Doc's File → Version history, which is the way back.
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
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BASE_DELAY = 1.5

SA_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]
DEFAULT_SA_KEY = Path.home() / ".config" / "gdoc-sync" / "sa-key.json"
SA_KEY_ENV = "GOOGLE_SA_KEY"
STATE_FILE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "gdoc-sync" / "state.json"
DOCS = "https://docs.googleapis.com/v1/documents"
DRIVE = "https://www.googleapis.com/drive/v3/files"

HEADING_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\b")
LINK_TEXT_NUM_RE = re.compile(r"(\d+(?:\.\d+)*)")
MARKDOWN_IMAGE_RE = re.compile(r"""!\[[^\]]*\]\(\s*(?:<([^>]+)>|([^)\s]+))(?:\s+["'][^)]*["'])?\s*\)""")

SA_EMAIL = None
SELF_EMAIL = None


def google_slugify(text: str) -> str:
    """Mimic the slug a markdown renderer generates for a heading.

    "5.1 עקרונות מנחים" -> "51-עקרונות-מנחים"
    "12.1 Milestone 1 - MVP" -> "121-milestone-1---mvp"

    Lowercase, drop punctuation that isn't word/space/dash, slashes become
    separators, whitespace runs become one dash. Hebrew/Arabic/CJK survive.
    """
    s = text.lower()
    s = s.replace("/", " ")
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    return s.strip("-")


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
    """OAuth token from a service account (preferred) or gcloud ADC."""
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
                 "  run with `uv run sync-gdoc.py ...` or `pip install google-auth requests`")
    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(pem)
        return subprocess.run([openssl, "dgst", "-sha256", "-sign", path],
                              input=data, capture_output=True, check=True).stdout
    finally:
        os.unlink(path)


# ─── HTTP ─────────────────────────────────────────────────────────────────

def api(token: str, method: str, url: str, body=None, content_type="application/json", raw=False):
    """Call a Google API, retrying transient failures (429/5xx)."""
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError("api(token, method, url, body): url must start with https://")
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode() if content_type == "application/json" else body
        headers["Content-Type"] = content_type

    last_err = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
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
            if e.code in (403, 404) and "has not been used" not in err_body:
                print(f"hint: share the Doc with {SA_EMAIL or 'the service account'} as Editor", file=sys.stderr)
            elif "has not been used" in err_body or "is disabled" in err_body:
                print("hint: enable the Drive API and the Docs API in the service account's project",
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


def batch(token: str, doc_id: str, requests: list, revision=None, chunk: int = 400) -> None:
    """Docs batchUpdate in chunks. `revision` is the revisionId the indexes
    were computed from: the server transforms them against anything written
    since (our earlier chunks, a retried request, a collaborator)."""
    for i in range(0, len(requests), chunk):
        body = {"requests": requests[i:i + chunk]}
        if revision:
            body["writeControl"] = {"targetRevisionId": revision}
        api(token, "POST", f"{DOCS}/{doc_id}:batchUpdate", body=body)


# ─── Step 0: guard ────────────────────────────────────────────────────────

def drive_meta(token: str, doc_id: str) -> dict:
    fields = "name,modifiedTime,lastModifyingUser(displayName,emailAddress)"
    return api(token, "GET", f"{DRIVE}/{doc_id}?fields={urllib.parse.quote(fields)}&supportsAllDrives=true")


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
        print(f"[0/7] No sync recorded for this {noun} yet; pushing (later runs refuse if a person "
              f"edited the {noun} in between)")
        return
    since = last.get("syncedAt") or last.get("modifiedTime") or ""
    edits = foreign_edits(token, file_id, since)
    if not edits:
        print(f"[0/7] {noun.capitalize()} unchanged by others since the last sync")
        return
    who = sorted({u for _, u in edits})
    msg = (f"the {noun} was edited by {', '.join(who)} (latest {max(t for t, _ in edits)}) after the last "
           f"sync ({since}); pushing would discard those edits")
    if not force:
        print(f"REFUSED: {msg}. {fix}, or pass --force.", file=sys.stderr)
        sys.exit(3)
    print(f"  ! {msg} (--force)", file=sys.stderr)


def guard(token: str, doc_id: str, force: bool) -> None:
    """Refuse a multi-tab Doc (the push flattens it), and refuse to overwrite
    edits a person made since the last push."""
    doc = api(token, "GET", f"{DOCS}/{doc_id}?includeTabsContent=true&fields="
              + urllib.parse.quote("tabs(tabProperties(title),childTabs(tabProperties(title)))"))
    tabs = doc.get("tabs", [])
    n_tabs = len(tabs) + sum(len(t.get("childTabs", [])) for t in tabs)
    if n_tabs > 1:
        names = [t["tabProperties"].get("title") for t in tabs]
        msg = (f"this Doc has {n_tabs} tabs {names}; a markdown push replaces the whole Doc "
               "with ONE tab of content and the other tabs are lost")
        if not force:
            print(f"REFUSED: {msg}. Sync into a single-tab Doc, or pass --force.", file=sys.stderr)
            sys.exit(3)
        print(f"  ! {msg} (--force)", file=sys.stderr)
    check_edits(token, doc_id, force, "Doc", "Fold them into the markdown first")


# ─── Step 1: push ─────────────────────────────────────────────────────────

def push_markdown(token: str, doc_id: str, md_path: str, title=None) -> None:
    """PATCH the markdown via the Drive upload API; Google converts it."""
    with open(md_path, "rb") as f:
        content = f.read()
    url = f"https://www.googleapis.com/upload/drive/v3/files/{doc_id}?uploadType=media&supportsAllDrives=true"
    api(token, "PATCH", url, body=content, content_type="text/markdown")
    msg = f"[1/7] Pushed markdown: {md_path} ({len(content):,} bytes)"
    if title:
        api(token, "PATCH", f"{DRIVE}/{doc_id}?supportsAllDrives=true", body={"name": title})
        msg += f"; renamed to {title!r}"
    print(msg)


# ─── Helpers over the document structure ──────────────────────────────────

def get_doc(token: str, doc_id: str) -> dict:
    return api(token, "GET", f"{DOCS}/{doc_id}")


def iter_paragraphs(content_list):
    """Yield every paragraph element, including those inside table cells."""
    for elem in content_list:
        if "paragraph" in elem:
            yield elem
        tbl = elem.get("table")
        if tbl:
            for row in tbl.get("tableRows", []):
                for cell in row.get("tableCells", []):
                    yield from iter_paragraphs(cell.get("content", []))


def paragraph_text(p) -> str:
    return "".join(e.get("textRun", {}).get("content", "") for e in p.get("elements", []))


def heading_maps(doc: dict):
    """(slug → headingId, section-number → headingId) from the Doc's headings."""
    slug_map, section_map = {}, {}
    for elem in doc["body"]["content"]:
        p = elem.get("paragraph")
        if not p:
            continue
        ps = p.get("paragraphStyle", {})
        if not ps.get("namedStyleType", "").startswith(("HEADING_", "TITLE")):
            continue
        hid = ps.get("headingId")
        if not hid:
            continue
        text = paragraph_text(p).strip()
        slug_map.setdefault(google_slugify(text), hid)
        m = HEADING_NUM_RE.match(text)
        if m:
            section_map.setdefault(m.group(1), hid)
    return slug_map, section_map


def _section_lookup(num: str, section_map: dict):
    """'5.3.1' → the deepest existing prefix: 5.3.1, then 5.3, then 5."""
    parts = num.split(".")
    for k in range(len(parts), 0, -1):
        cand = ".".join(parts[:k])
        if cand in section_map:
            return section_map[cand]
    return None


# ─── Step 2: in-doc anchors ───────────────────────────────────────────────

def fix_anchor_links(token: str, doc_id: str) -> int:
    """Rewrite URL links to a literal '#slug' into native heading links.

    Resolution: the slug itself (works for any heading text), then the
    section number in the slug's prefix, then a number in the link text.
    """
    doc = get_doc(token, doc_id)
    slug_map, section_map = heading_maps(doc)
    requests, unresolved = [], []
    for elem in iter_paragraphs(doc["body"]["content"]):
        for e in elem["paragraph"].get("elements", []):
            tr = e.get("textRun")
            if not tr:
                continue
            url = tr.get("textStyle", {}).get("link", {}).get("url", "")
            if not url.startswith("#"):
                continue
            anchor = urllib.parse.unquote(url[1:])
            hid = slug_map.get(anchor) or slug_map.get(google_slugify(anchor))
            if not hid:
                m = LINK_TEXT_NUM_RE.search(tr.get("content", ""))
                if m:
                    hid = _section_lookup(m.group(1), section_map)
            if not hid:
                unresolved.append(anchor)
                continue
            requests.append({"updateTextStyle": {
                "range": {"startIndex": e.get("startIndex", 0), "endIndex": e["endIndex"]},
                "textStyle": {"link": {"headingId": hid}},
                "fields": "link",
            }})
    if requests:
        batch(token, doc_id, requests, doc.get("revisionId"))
    extra = f"; {len(unresolved)} unresolved: {sorted(set(unresolved))[:5]}" if unresolved else ""
    print(f"[2/7] Fixed {len(requests)} in-doc anchor links{extra}")
    return len(requests)


# ─── Step 3: cross-doc links ──────────────────────────────────────────────

def fix_cross_doc_links(token: str, doc_id: str, cross_doc_map: dict) -> int:
    """Rewrite [text](other.md#anchor) into deep-links into the sibling Doc.

    cross_doc_map: {filename-or-path-fragment: target_doc_id}; a link matches
    when its URL-decoded URL contains the key. Anchor resolution: slug, then
    a section number from the anchor, then one from the link text, then the
    top of the target Doc.
    """
    if not cross_doc_map:
        print("[3/7] Skipped cross-doc link rewriting (no --cross-doc-map)")
        return 0
    targets = {}
    for path, target_id in cross_doc_map.items():
        slug_map, section_map = heading_maps(get_doc(token, target_id))
        targets[path] = (target_id, slug_map, section_map)

    doc = get_doc(token, doc_id)
    requests = []
    for elem in iter_paragraphs(doc["body"]["content"]):
        for e in elem["paragraph"].get("elements", []):
            tr = e.get("textRun")
            if not tr:
                continue
            url = tr.get("textStyle", {}).get("link", {}).get("url", "")
            if not url:
                continue
            decoded = urllib.parse.unquote(url)
            for path, (target_id, slug_map, section_map) in sorted(targets.items(), key=lambda kv: -len(kv[0])):
                if path not in decoded:
                    continue
                anchor = decoded.rsplit("#", 1)[1] if "#" in decoded else ""
                hid = (slug_map.get(anchor) or slug_map.get(google_slugify(anchor))) if anchor else None
                if not hid and anchor:
                    m = re.match(r"(\d+)(?:[-.]|$)", anchor)
                    if m:
                        raw = m.group(1)
                        # The slug drops dots: "162" may be "16.2" or "1.6.2".
                        for k in range(len(raw), 0, -1):
                            for split in range(1, k + 1):
                                cand = raw[:split] + "." + raw[split:k] if split < k else raw[:k]
                                if cand in section_map:
                                    hid = section_map[cand]
                                    break
                            if hid:
                                break
                if not hid:
                    m = LINK_TEXT_NUM_RE.search(tr.get("content", ""))
                    if m:
                        hid = section_map.get(m.group(1))
                new_url = f"https://docs.google.com/document/d/{target_id}/edit"
                if hid:
                    new_url += f"#heading={hid}"
                requests.append({"updateTextStyle": {
                    "range": {"startIndex": e.get("startIndex", 0), "endIndex": e["endIndex"]},
                    "textStyle": {"link": {"url": new_url}},
                    "fields": "link",
                }})
                break
    if requests:
        batch(token, doc_id, requests, doc.get("revisionId"))
    print(f"[3/7] Fixed {len(requests)} cross-doc links")
    return len(requests)


# ─── Step 4: images ───────────────────────────────────────────────────────

def resize_oversized_images(token: str, doc_id: str, md_path: str, max_width_pt: float) -> int:
    """Google imports inline images at source size. Re-insert the ones wider
    than max_width_pt with an explicit size, using the image URL from the
    markdown (so that URL must still be publicly reachable)."""
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_urls = [x or y for x, y in MARKDOWN_IMAGE_RE.findall(f.read())]
    if not markdown_urls:
        print("[4/7] Skipped image resize (no images in the markdown)")
        return 0
    doc = get_doc(token, doc_id)
    inline_images = []
    for elem in iter_paragraphs(doc["body"]["content"]):
        for e in elem["paragraph"].get("elements", []):
            iobj = e.get("inlineObjectElement")
            if iobj:
                inline_images.append((e.get("startIndex", 0), e["endIndex"], iobj["inlineObjectId"]))
    if len(inline_images) != len(markdown_urls):
        print(f"[4/7] Skipped image resize: the markdown has {len(markdown_urls)} images, the Doc "
              f"{len(inline_images)} (an unreachable or relative-path image is dropped by the import)",
              file=sys.stderr)
        return 0
    resized = 0
    for (start, end, oid), url in reversed(list(zip(inline_images, markdown_urls))):
        size = doc["inlineObjects"].get(oid, {}).get("inlineObjectProperties", {}) \
            .get("embeddedObject", {}).get("size", {})
        cur_w = size.get("width", {}).get("magnitude", 0)
        cur_h = size.get("height", {}).get("magnitude", 0)
        if cur_w <= max_width_pt or cur_w == 0 or cur_h == 0:
            continue
        new_h = max_width_pt * cur_h / cur_w
        batch(token, doc_id, [
            {"deleteContentRange": {"range": {"startIndex": start, "endIndex": end}}},
            {"insertInlineImage": {"location": {"index": start}, "uri": url, "objectSize": {
                "height": {"magnitude": new_h, "unit": "PT"},
                "width": {"magnitude": max_width_pt, "unit": "PT"}}}},
        ], doc.get("revisionId"))
        resized += 1
    print(f"[4/7] Resized {resized} oversized images (max width {max_width_pt}pt)")
    return resized


# ─── Step 5: RTL ──────────────────────────────────────────────────────────

def apply_rtl(token: str, doc_id: str) -> None:
    """RIGHT_TO_LEFT direction on every body paragraph (tables included)."""
    doc = get_doc(token, doc_id)
    end = doc["body"]["content"][-1]["endIndex"]
    batch(token, doc_id, [{"updateParagraphStyle": {
        "range": {"startIndex": 1, "endIndex": end - 1},
        "paragraphStyle": {"direction": "RIGHT_TO_LEFT"},
        "fields": "direction",
    }}])
    print(f"[5/7] Applied RTL across doc (1..{end - 1})")


# ─── Step 6: styling that each push resets ────────────────────────────────

def drop_empty_paragraphs(token: str, doc_id: str) -> int:
    """Delete empty body paragraphs the import leaves between blocks.

    Keeps the last paragraph of the body, the paragraph right before a table
    (the API can't delete it), and paragraphs inside table cells.
    """
    doc = get_doc(token, doc_id)
    content = doc["body"]["content"]
    ranges = []
    for i, elem in enumerate(content):
        p = elem.get("paragraph")
        if not p or i == len(content) - 1:
            continue
        if "table" in content[i + 1]:
            continue
        # Empty = only whitespace text runs; a rule, image, page break or chip counts as content.
        if any("textRun" not in e or e["textRun"].get("content", "").strip()
               for e in p.get("elements", [])):
            continue
        ranges.append((elem.get("startIndex", 0), elem["endIndex"]))
    requests = [{"deleteContentRange": {"range": {"startIndex": s, "endIndex": e}}}
                for s, e in sorted(ranges, reverse=True)]
    if requests:
        batch(token, doc_id, requests, doc.get("revisionId"))
    return len(requests)


def apply_styling(token: str, doc_id: str, args) -> None:
    """Paragraph spacing / line spacing / font size, per paragraph (table
    cells included), because a push resets them to the import defaults."""
    dropped = drop_empty_paragraphs(token, doc_id) if args.drop_empty_paragraphs else 0
    body_style, body_fields, head_style, head_fields = {}, [], {}, []
    if args.line_spacing is not None:
        body_style["lineSpacing"] = args.line_spacing
        body_fields.append("lineSpacing")
        head_style["lineSpacing"] = args.line_spacing
        head_fields.append("lineSpacing")
    for attr, key in (("space_above", "spaceAbove"), ("space_below", "spaceBelow")):
        v = getattr(args, attr)
        if v is not None:
            body_style[key] = {"magnitude": v, "unit": "PT"}
            body_fields.append(key)
    for attr, key in (("heading_space_above", "spaceAbove"), ("heading_space_below", "spaceBelow")):
        v = getattr(args, attr)
        if v is not None:
            head_style[key] = {"magnitude": v, "unit": "PT"}
            head_fields.append(key)
    requests, doc = [], {}
    if body_fields or head_fields or args.font_size:
        doc = get_doc(token, doc_id)
        for elem in iter_paragraphs(doc["body"]["content"]):
            p = elem["paragraph"]
            rng = {"startIndex": elem.get("startIndex", 0), "endIndex": elem["endIndex"]}
            named = p.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
            is_heading = named.startswith("HEADING_") or named in ("TITLE", "SUBTITLE")
            style, fields = (head_style, head_fields) if is_heading else (body_style, body_fields)
            if fields:
                requests.append({"updateParagraphStyle": {"range": rng, "paragraphStyle": style,
                                                          "fields": ",".join(fields)}})
            if args.font_size and not is_heading and elem["endIndex"] - elem.get("startIndex", 0) > 1:
                requests.append({"updateTextStyle": {
                    "range": {"startIndex": elem.get("startIndex", 0), "endIndex": elem["endIndex"] - 1},
                    "textStyle": {"fontSize": {"magnitude": args.font_size, "unit": "PT"}},
                    "fields": "fontSize"}})
    if requests:
        batch(token, doc_id, requests, doc.get("revisionId"))
    asked = args.drop_empty_paragraphs or body_fields or head_fields or args.font_size
    if asked:
        print(f"[6/7] Styling: removed {dropped} empty paragraphs, {len(requests)} style updates")
    else:
        print("[6/7] Skipped styling (no --line-spacing/--space-*/--font-size/--drop-empty-paragraphs)")


# ─── Step 7: export ───────────────────────────────────────────────────────

def export_pdf(token: str, doc_id: str, out: str) -> None:
    data = api(token, "GET", f"{DRIVE}/{doc_id}/export?mimeType=application/pdf", raw=True)
    Path(out).expanduser().write_bytes(data)
    print(f"[7/7] Exported PDF → {out} ({len(data):,} bytes)")


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)  # keep stdout and stderr lines in order when piped
    parser = argparse.ArgumentParser(
        description="Sync a markdown file to an existing Google Doc.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__,
    )
    parser.add_argument("markdown", help="Path to the markdown file to push")
    parser.add_argument("--doc-id", required=True, help="Google Doc file ID (the long string in the URL)")
    parser.add_argument("--sa-key", default=None,
                        help=f"Service-account JSON key (default: ${SA_KEY_ENV}, then "
                             "~/.config/gdoc-sync/sa-key.json, then gcloud ADC)")
    parser.add_argument("--title", help="Also rename the Doc in Drive (the file name, not the H1)")
    parser.add_argument("--rtl", action="store_true", help="Right-to-left paragraphs (Hebrew/Arabic)")
    parser.add_argument("--no-links", action="store_true", help="Skip anchor and cross-doc link rewriting")
    parser.add_argument("--max-image-width", type=float, default=300.0,
                        help="Max inline image width in points (default 300); 0 skips the resize step")
    parser.add_argument("--cross-doc-map", action="append", default=[], metavar="NAME=DOC_ID",
                        help="Map a markdown filename (or path fragment in link URLs) to a sibling Doc ID. "
                             "Repeatable. Example: --cross-doc-map 'product-plan.md=1lSsp...'")
    style = parser.add_argument_group("styling (re-applied after every push, which resets it)")
    style.add_argument("--line-spacing", type=float, help="Line spacing in percent, e.g. 100 (import default 115)")
    style.add_argument("--space-above", type=float, help="Points above body paragraphs")
    style.add_argument("--space-below", type=float, help="Points below body paragraphs")
    style.add_argument("--heading-space-above", type=float, help="Points above headings")
    style.add_argument("--heading-space-below", type=float, help="Points below headings")
    style.add_argument("--font-size", type=float, help="Body text size in points")
    style.add_argument("--drop-empty-paragraphs", action="store_true",
                       help="Delete the empty paragraphs the import leaves between blocks")
    parser.add_argument("--export-pdf", metavar="PATH", help="After syncing, save a PDF render for visual QA")
    parser.add_argument("--force", action="store_true",
                        help="Push even if someone edited the Doc since the last sync, or it has several tabs")
    args = parser.parse_args()

    cross_doc_map = {}
    for entry in args.cross_doc_map:
        if "=" not in entry:
            print(f"error: --cross-doc-map expects NAME=DOC_ID, got {entry!r}", file=sys.stderr)
            return 1
        name, did = entry.split("=", 1)
        cross_doc_map[name.strip()] = did.strip()
    if not os.path.isfile(args.markdown):
        print(f"error: markdown file not found: {args.markdown}", file=sys.stderr)
        return 1

    token = get_token(args.sa_key)
    try:
        guard(token, args.doc_id, args.force)
        push_markdown(token, args.doc_id, args.markdown, args.title)
        mark_synced(token, args.doc_id, os.path.abspath(args.markdown))
        if not args.no_links:
            fix_anchor_links(token, args.doc_id)
            fix_cross_doc_links(token, args.doc_id, cross_doc_map)
        else:
            print("[2/7] Skipped in-doc anchor rewriting (--no-links)")
            print("[3/7] Skipped cross-doc rewriting (--no-links)")
        if args.max_image_width > 0:
            resize_oversized_images(token, args.doc_id, args.markdown, args.max_image_width)
        else:
            print("[4/7] Skipped image resize (--max-image-width 0)")
        if args.rtl:
            apply_rtl(token, args.doc_id)
        else:
            print("[5/7] Skipped RTL (use --rtl to enable)")
        apply_styling(token, args.doc_id, args)
        if args.export_pdf:
            export_pdf(token, args.doc_id, args.export_pdf)
        else:
            print("[7/7] Skipped PDF export (use --export-pdf PATH)")
    except urllib.error.HTTPError:
        return 1
    print(f"Done. https://docs.google.com/document/d/{args.doc_id}/edit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
