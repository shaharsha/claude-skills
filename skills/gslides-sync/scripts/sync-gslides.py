#!/usr/bin/env python3
"""
Sync a .pptx file to an existing Google Slides presentation.

Pipeline:
  1. PATCH the pptx via Drive resumable upload (Google converts natively)
  2. Rewrite broken in-deck slide refs (slide-N.xml, #slideN, etc.) to
     native pageObjectId links
  3. Rewrite cross-presentation links (other.pptx#anchor) to deep-links
     into the sibling Slides URL, when --cross-pres-map is provided
  4. Resize oversized images that exceed the page bounds
  5. Optionally apply RIGHT_TO_LEFT direction to every text shape

Usage:
    ./sync-gslides.py <pptx-file> --pres-id <FILE_ID> [--sa-key <path>] [--rtl]
        [--no-links] [--max-image-width <pt>]
        [--cross-pres-map "name.pptx=PRES_ID" ...]

Auth (two supported paths):
    1. Service account (recommended): pass --sa-key path/to/sa.json. The SA
       email must have Editor access to the Slides file, and the SA's GCP
       project must have Drive + Slides APIs enabled. Requires `pip install
       google-auth`.
    2. gcloud ADC (fallback): run `gcloud auth application-default login` first.
       Strips GOOGLE_APPLICATION_CREDENTIALS if set. May be blocked by
       Google's "this app is blocked" policy for sensitive scopes.

Backup:
    The pptx import is destructive — Drive replaces the presentation body,
    which wipes pending suggested edits and orphans comments whose anchored
    text no longer matches. Make a copy via the Drive API `copy` endpoint or
    "File → Make a copy" before first use on a deck you care about.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BASE_DELAY = 1.5

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

SA_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/presentations",
]

LINK_TEXT_NUM_RE = re.compile(r"(\d+)")
# Patterns for broken slide refs that pptx → Slides conversion sometimes leaves behind
BROKEN_SLIDE_URL_RES = [
    re.compile(r"(?:^|/)slide[-_]?(\d+)(?:\.xml)?$", re.IGNORECASE),
    re.compile(r"^#slide[-_]?(\d+)$", re.IGNORECASE),
    re.compile(r"\.xml$", re.IGNORECASE),
]


def google_slugify(text: str) -> str:
    """Slug normalizer matching Google's markdown-import slugger.

    Lowercase, drop non-word chars, collapse whitespace to dashes, strip edges.
    Hebrew/Arabic/CJK preserved via re.UNICODE.
    """
    s = text.lower()
    s = s.replace("/", " ")
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    return s.strip("-")


def get_token(sa_key=None) -> str:
    """OAuth access token via SA key (preferred) or gcloud ADC fallback."""
    if sa_key:
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests as gar
        except ImportError:
            print(
                "error: --sa-key requires `pip install google-auth`.\n"
                "Install it and retry, or omit --sa-key to use gcloud ADC.",
                file=sys.stderr,
            )
            sys.exit(1)
        creds = service_account.Credentials.from_service_account_file(sa_key, scopes=SA_SCOPES)
        creds.refresh(gar.Request())
        return creds.token
    env = os.environ.copy()
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    try:
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            env=env, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        print(
            "error: `gcloud` not found on PATH.\n"
            "Install the Google Cloud CLI or pass --sa-key to use a service account instead.",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(
            "error: gcloud ADC auth failed. Run:\n"
            "  gcloud auth application-default login\n"
            f"\ngcloud stderr:\n{e.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    return result.stdout.strip()


def api(token: str, method: str, url: str, body=None, content_type="application/json", extra_headers=None, return_response=False):
    """Call a Google API with automatic retry on 429/5xx."""
    headers = {"Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    data = None
    if body is not None:
        if content_type == "application/json":
            data = json.dumps(body).encode()
        else:
            data = body
        headers["Content-Type"] = content_type

    last_err = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                if return_response:
                    return {"headers": dict(resp.headers), "body": resp.read(), "status": resp.status}
                raw = resp.read()
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            if e.code in RETRYABLE_STATUS and attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"  ! HTTP {e.code} on {method} {url.split('?')[0]} — retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})",
                      file=sys.stderr)
                time.sleep(delay)
                last_err = e
                continue
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            if err_body:
                print(f"HTTP {e.code} on {method} {url.split('?')[0]}:\n{err_body}", file=sys.stderr)
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"  ! {type(e).__name__} on {method} — retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})",
                      file=sys.stderr)
                time.sleep(delay)
                last_err = e
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("unreachable: retry loop exited without success or error")


def push_pptx(token: str, pres_id: str, pptx_path: str) -> None:
    """Step 1: PATCH the pptx via Drive resumable upload. Drive converts natively.

    Resumable is used (not simple media upload) because pptx files routinely
    exceed Google's 5 MB simple-upload guideline. Two HTTP calls:
      a) PATCH with uploadType=resumable to initiate; receive Location header.
      b) PUT the bytes to that Location URL.
    """
    with open(pptx_path, "rb") as f:
        content = f.read()
    size = len(content)

    init_url = f"https://www.googleapis.com/upload/drive/v3/files/{pres_id}?uploadType=resumable&supportsAllDrives=true"
    init = api(
        token, "PATCH", init_url,
        body=b"{}",
        content_type="application/json; charset=UTF-8",
        extra_headers={
            "X-Upload-Content-Type": PPTX_MIME,
            "X-Upload-Content-Length": str(size),
        },
        return_response=True,
    )
    upload_url = init["headers"].get("Location") or init["headers"].get("location")
    if not upload_url:
        raise RuntimeError(f"resumable init returned no Location header: {init['headers']}")

    # PUT the bytes. Note: upload_url is fully-qualified and pre-authenticated;
    # we don't reuse the bearer token here.
    req = urllib.request.Request(upload_url, data=content, method="PUT", headers={
        "Content-Type": PPTX_MIME,
        "Content-Length": str(size),
    })
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req) as resp:
                resp.read()
                break
        except urllib.error.HTTPError as e:
            if e.code in RETRYABLE_STATUS and attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"  ! HTTP {e.code} on resumable PUT — retrying in {delay:.1f}s", file=sys.stderr)
                time.sleep(delay)
                last_err = e
                continue
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            if err_body:
                print(f"HTTP {e.code} on resumable PUT:\n{err_body}", file=sys.stderr)
            raise
    print(f"[1/5] Pushed pptx: {pptx_path} ({size:,} bytes)")


def extract_text(text_obj) -> str:
    """Concatenate textRun content from a Slides text object."""
    if not text_obj:
        return ""
    out = []
    for el in text_obj.get("textElements", []):
        tr = el.get("textRun")
        if tr:
            out.append(tr.get("content", ""))
    return "".join(out).strip()


def slide_title(slide) -> str:
    """Find the title text of a slide.

    Prefers a shape with placeholder.type == TITLE or CENTERED_TITLE; falls
    back to the first non-empty text shape on the slide.
    """
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
    """Invoke fn(shape_object_id, text_obj, cell_location_or_None) for every
    text-bearing shape and table cell across all slides."""
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


def fix_slide_anchor_links(token: str, pres_id: str) -> int:
    """Step 2: rewrite broken in-deck slide refs to native pageObjectId links."""
    pres = api(token, "GET", f"https://slides.googleapis.com/v1/presentations/{pres_id}")

    slides = pres.get("slides", [])
    index_to_oid = {i + 1: s["objectId"] for i, s in enumerate(slides)}  # 1-indexed
    slug_to_oid = {}
    for s in slides:
        title = slide_title(s)
        if title:
            slug_to_oid[google_slugify(title)] = s["objectId"]

    requests = []

    def visit(shape_oid, text_obj, cell_location):
        for el in text_obj.get("textElements", []):
            tr = el.get("textRun")
            if not tr:
                continue
            link = tr.get("style", {}).get("link")
            if not link:
                continue
            url = link.get("url", "")
            if not url:
                continue  # already a pageObjectId/slideIndex link, leave alone
            decoded = urllib.parse.unquote(url)
            target_oid = None
            # Try numeric slide index from URL patterns
            for pat in BROKEN_SLIDE_URL_RES:
                m = pat.search(decoded)
                if m and m.groups():
                    try:
                        n = int(m.group(1))
                    except ValueError:
                        continue
                    target_oid = index_to_oid.get(n)
                    if target_oid:
                        break
            # Try slug match against the URL fragment
            if not target_oid and "#" in decoded:
                anchor = decoded.rsplit("#", 1)[1]
                target_oid = slug_to_oid.get(anchor) or slug_to_oid.get(google_slugify(anchor))
            # Try numeric from visible link text
            if not target_oid:
                m = LINK_TEXT_NUM_RE.search(tr.get("content", ""))
                if m:
                    target_oid = index_to_oid.get(int(m.group(1)))
            if not target_oid:
                continue
            req = {
                "updateTextStyle": {
                    "objectId": shape_oid,
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": el["startIndex"],
                        "endIndex": el["endIndex"],
                    },
                    "style": {"link": {"pageObjectId": target_oid}},
                    "fields": "link",
                }
            }
            if cell_location is not None:
                req["updateTextStyle"]["cellLocation"] = cell_location
            requests.append(req)

    walk_text_shapes(pres, visit)

    if requests:
        api(token, "POST", f"https://slides.googleapis.com/v1/presentations/{pres_id}:batchUpdate",
            body={"requests": requests})
    print(f"[2/5] Fixed {len(requests)} in-deck slide-anchor links")
    return len(requests)


def fetch_target_pres_slugs(token: str, target_pres_id: str):
    """Get a target Slides' (slug → pageObjectId, index → pageObjectId) maps."""
    pres = api(token, "GET", f"https://slides.googleapis.com/v1/presentations/{target_pres_id}")
    slug_map = {}
    index_map = {}
    for i, s in enumerate(pres.get("slides", [])):
        index_map[i + 1] = s["objectId"]
        title = slide_title(s)
        if title:
            slug_map[google_slugify(title)] = s["objectId"]
    return slug_map, index_map


def fix_cross_pres_links(token: str, pres_id: str, cross_pres_map: dict) -> int:
    """Step 3: rewrite [text](other.pptx#anchor) cross-deck refs into
    deep-links pointing at the sibling Slides + slide objectId."""
    if not cross_pres_map:
        print("[3/5] Skipped cross-pres link rewriting (no --cross-pres-map)")
        return 0

    target_caches = {}
    for path, target_id in cross_pres_map.items():
        slug_map, index_map = fetch_target_pres_slugs(token, target_id)
        target_caches[path] = (target_id, slug_map, index_map)

    pres = api(token, "GET", f"https://slides.googleapis.com/v1/presentations/{pres_id}")

    requests = []

    def visit(shape_oid, text_obj, cell_location):
        for el in text_obj.get("textElements", []):
            tr = el.get("textRun")
            if not tr:
                continue
            link = tr.get("style", {}).get("link")
            if not link:
                continue
            url = link.get("url", "")
            if not url:
                continue
            decoded = urllib.parse.unquote(url)
            for path, (target_id, slug_map, index_map) in target_caches.items():
                if path not in decoded:
                    continue
                anchor = ""
                if "#" in decoded:
                    anchor = decoded.rsplit("#", 1)[1]
                target_oid = None
                if anchor:
                    target_oid = slug_map.get(anchor) or slug_map.get(google_slugify(anchor))
                    if not target_oid:
                        m = re.match(r"slide[-_]?(\d+)$", anchor, re.IGNORECASE)
                        if m:
                            target_oid = index_map.get(int(m.group(1)))
                if not target_oid:
                    m = LINK_TEXT_NUM_RE.search(tr.get("content", ""))
                    if m:
                        target_oid = index_map.get(int(m.group(1)))
                if target_oid:
                    new_url = f"https://docs.google.com/presentation/d/{target_id}/edit#slide=id.{target_oid}"
                else:
                    new_url = f"https://docs.google.com/presentation/d/{target_id}/edit"
                req = {
                    "updateTextStyle": {
                        "objectId": shape_oid,
                        "textRange": {
                            "type": "FIXED_RANGE",
                            "startIndex": el["startIndex"],
                            "endIndex": el["endIndex"],
                        },
                        "style": {"link": {"url": new_url}},
                        "fields": "link",
                    }
                }
                if cell_location is not None:
                    req["updateTextStyle"]["cellLocation"] = cell_location
                requests.append(req)
                return

    walk_text_shapes(pres, visit)

    if requests:
        api(token, "POST", f"https://slides.googleapis.com/v1/presentations/{pres_id}:batchUpdate",
            body={"requests": requests})
    print(f"[3/5] Fixed {len(requests)} cross-pres links")
    return len(requests)


def _emu_to_pt(emu: float) -> float:
    """914400 EMU = 1 inch = 72 pt."""
    return emu * 72 / 914400.0


def _unit_to_pt(magnitude: float, unit: str) -> float:
    if unit == "PT":
        return magnitude
    if unit == "EMU":
        return _emu_to_pt(magnitude)
    return magnitude  # unknown unit; treat as pt


def resize_oversized_images(token: str, pres_id: str, max_width_pt) -> int:
    """Step 4: shrink images whose effective width exceeds max_width_pt.

    Effective width = size.width * transform.scaleX. Rescale uniformly to
    preserve aspect; recompute translate so the image's center stays fixed.

    If max_width_pt is None (default), use the presentation's actual page
    width — so an image sized exactly to fill the slide is not shrunk.
    """
    pres = api(token, "GET", f"https://slides.googleapis.com/v1/presentations/{pres_id}")

    if max_width_pt is None:
        page_size = pres.get("pageSize", {})
        pw = page_size.get("width", {})
        max_width_pt = _unit_to_pt(pw.get("magnitude", 720), pw.get("unit", "EMU"))
        print(f"   ↳ using page width {max_width_pt:.1f}pt as max-image-width default")

    requests = []
    resized = 0
    for slide in pres.get("slides", []):
        for el in slide.get("pageElements", []):
            if "image" not in el:
                continue
            size = el.get("size", {})
            w = size.get("width", {})
            h = size.get("height", {})
            base_w = _unit_to_pt(w.get("magnitude", 0), w.get("unit", "EMU"))
            base_h = _unit_to_pt(h.get("magnitude", 0), h.get("unit", "EMU"))
            if base_w <= 0 or base_h <= 0:
                continue
            tr = el.get("transform", {}) or {}
            scale_x = tr.get("scaleX", 1) or 1
            scale_y = tr.get("scaleY", 1) or 1
            eff_w = base_w * scale_x
            eff_h = base_h * scale_y
            if eff_w <= max_width_pt + 0.5:  # tolerate sub-pt rounding
                continue
            shrink = max_width_pt / eff_w
            new_scale_x = scale_x * shrink
            new_scale_y = scale_y * shrink
            # Translate is in EMU (or whatever transform.unit is). base_w/base_h
            # are already in pt above; convert center delta back to the
            # transform's native unit so we shift correctly.
            tr_unit = tr.get("unit", "EMU")
            cur_tx = tr.get("translateX", 0) or 0
            cur_ty = tr.get("translateY", 0) or 0
            # Width/height delta in pt, then back to tr_unit for translate
            dw_pt = eff_w * (1 - shrink)
            dh_pt = eff_h * (1 - shrink)
            if tr_unit == "EMU":
                dw_native = dw_pt * 914400 / 72
                dh_native = dh_pt * 914400 / 72
            else:
                dw_native = dw_pt
                dh_native = dh_pt
            # Keep image centered: shift translate by half the width/height delta
            new_tx = cur_tx + dw_native / 2
            new_ty = cur_ty + dh_native / 2
            requests.append({
                "updatePageElementTransform": {
                    "objectId": el["objectId"],
                    "transform": {
                        "scaleX": new_scale_x,
                        "scaleY": new_scale_y,
                        "shearX": tr.get("shearX", 0),
                        "shearY": tr.get("shearY", 0),
                        "translateX": new_tx,
                        "translateY": new_ty,
                        "unit": tr_unit,
                    },
                    "applyMode": "ABSOLUTE",
                },
            })
            resized += 1

    if requests:
        api(token, "POST", f"https://slides.googleapis.com/v1/presentations/{pres_id}:batchUpdate",
            body={"requests": requests})
    print(f"[4/5] Resized {resized} oversized images (max width {max_width_pt}pt)")
    return resized


def apply_rtl(token: str, pres_id: str) -> int:
    """Step 5 (optional): set RIGHT_TO_LEFT direction on every text shape."""
    pres = api(token, "GET", f"https://slides.googleapis.com/v1/presentations/{pres_id}")

    requests = []

    def visit(shape_oid, text_obj, cell_location):
        if not extract_text(text_obj):
            return
        req = {
            "updateParagraphStyle": {
                "objectId": shape_oid,
                "textRange": {"type": "ALL"},
                "style": {"direction": "RIGHT_TO_LEFT"},
                "fields": "direction",
            }
        }
        if cell_location is not None:
            req["updateParagraphStyle"]["cellLocation"] = cell_location
        requests.append(req)

    walk_text_shapes(pres, visit)

    if requests:
        # Slides batchUpdate accepts up to 500 requests per call; chunk defensively.
        for i in range(0, len(requests), 400):
            chunk = requests[i:i + 400]
            api(token, "POST", f"https://slides.googleapis.com/v1/presentations/{pres_id}:batchUpdate",
                body={"requests": chunk})
    print(f"[5/5] Applied RTL to {len(requests)} text shapes")
    return len(requests)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync a .pptx to an existing Google Slides: push, fix slide refs, resize images, optional RTL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pptx", help="Path to the .pptx file to push")
    parser.add_argument("--pres-id", required=True, help="Google Slides file ID (the long string in the URL)")
    parser.add_argument("--sa-key", default=None,
                        help="Path to a service-account JSON key. Recommended. The SA email must have Editor access to the Slides. If omitted, falls back to gcloud ADC.")
    parser.add_argument("--rtl", action="store_true",
                        help="Apply RIGHT_TO_LEFT direction to every text shape (for Hebrew/Arabic decks)")
    parser.add_argument("--no-links", action="store_true",
                        help="Skip slide-anchor + cross-pres rewriting (steps 2 and 3)")
    parser.add_argument("--max-image-width", type=float, default=None,
                        help="Max image width in points; larger images are scaled down preserving aspect ratio (image stays centered). Default: the presentation's actual page width (e.g. 960pt for default 16:9), so full-bleed images are not touched. Set 0 to skip.")
    parser.add_argument("--cross-pres-map", action="append", default=[], metavar="NAME=PRES_ID",
                        help="Map a pptx filename (or path fragment that appears in cross-deck link URLs) to a sibling Google Slides ID. Repeatable. Cross-pres links get rewritten to deep-link into the target Slides at the matching slide. Example: --cross-pres-map 'spec.pptx=1AbC...'")
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

    push_pptx(token, args.pres_id, args.pptx)

    if not args.no_links:
        fix_slide_anchor_links(token, args.pres_id)
        fix_cross_pres_links(token, args.pres_id, cross_pres_map)
    else:
        print("[2/5] Skipped slide-anchor rewriting (--no-links)")
        print("[3/5] Skipped cross-pres rewriting (--no-links)")

    if args.max_image_width is None or args.max_image_width > 0:
        resize_oversized_images(token, args.pres_id, args.max_image_width)
    else:
        print("[4/5] Skipped image resize (--max-image-width 0)")

    if args.rtl:
        apply_rtl(token, args.pres_id)
    else:
        print("[5/5] Skipped RTL (use --rtl to enable)")

    print(f"Done. https://docs.google.com/presentation/d/{args.pres_id}/edit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
