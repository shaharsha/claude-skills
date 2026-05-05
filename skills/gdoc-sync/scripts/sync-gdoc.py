#!/usr/bin/env python3
"""
Sync a markdown file to an existing Google Doc.

Pipeline:
  1. PATCH the markdown via Drive upload API (Google converts natively)
  2. Rewrite broken in-doc anchor links [text](#slug) -> native headingId links
  3. Rewrite cross-doc links [text](other.md#anchor) -> deep-links into the
     sibling Doc, when --cross-doc-map is provided
  4. Resize oversized inline images (Google imports at source resolution)
  5. Optionally apply RTL paragraph direction (for Hebrew/Arabic docs)

Usage:
    ./sync-gdoc.py <markdown-file> --doc-id <FILE_ID> [--sa-key <path>] [--rtl]
        [--no-links] [--max-image-width <pt>]
        [--cross-doc-map "name.md=DOC_ID" ...]

Auth (two supported paths):
    1. Service account (recommended): pass --sa-key path/to/sa.json. The SA
       email must have Editor access to the Doc, and the SA's GCP project
       must have Drive + Docs APIs enabled. Requires `pip install google-auth`.
    2. gcloud ADC (fallback): run `gcloud auth application-default login` first.
       Strips GOOGLE_APPLICATION_CREDENTIALS if set (common misconfig). May be
       blocked by Google's "this app is blocked" policy for sensitive scopes.

Backup:
    This script does NOT make a backup. The markdown import is destructive:
    it wipes pending suggested edits and orphans comments whose anchored text
    no longer matches. Make a copy via the Drive API `copy` endpoint or the
    "Make a copy" menu before first use on a doc you care about.
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


# Google's Drive/Docs APIs occasionally return transient 500/503/429. Retry a few times.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BASE_DELAY = 1.5  # seconds; exponential backoff


HEADING_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\b")
LINK_TEXT_NUM_RE = re.compile(r"(\d+(?:\.\d+)*)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def google_slugify(text: str) -> str:
    """Mimic the slug Google's markdown import generates for a heading.

    "5.1 עקרונות מנחים" -> "51-עקרונות-מנחים"
    "12.1 Milestone 1 - MVP" -> "121-milestone-1---mvp"
    "16.2 Technical (חוסם Technical Design)" -> "162-technical-חוסם-technical-design"

    Rules: lowercase, drop punctuation that isn't `\\w`/space/dash/slash, slashes
    become dashes (treated like word separators), runs of whitespace collapse
    into a single dash, leading/trailing dashes trimmed. Hebrew/Arabic/CJK are
    preserved via re.UNICODE.
    """
    s = text.lower()
    s = s.replace("/", " ")
    # Drop everything that isn't a word char, whitespace, or dash
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    return s.strip("-")


def fetch_target_doc_headings(token: str, target_doc_id: str):
    """Get a target Doc's headings as (slug_map, section_map). Cached per call site."""
    doc = api(token, "GET", f"https://docs.googleapis.com/v1/documents/{target_doc_id}")
    slug_map = {}
    section_map = {}
    for elem in doc["body"]["content"]:
        p = elem.get("paragraph")
        if not p:
            continue
        ps = p.get("paragraphStyle", {})
        if not ps.get("namedStyleType", "").startswith("HEADING_"):
            continue
        hid = ps.get("headingId")
        if not hid:
            continue
        text = "".join(
            e.get("textRun", {}).get("content", "")
            for e in p.get("elements", [])
        ).strip()
        slug_map[google_slugify(text)] = hid
        m = HEADING_NUM_RE.match(text)
        if m:
            # Don't overwrite if multiple headings start with the same number
            section_map.setdefault(m.group(1), hid)
    return slug_map, section_map


SA_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def get_token(sa_key=None) -> str:
    """Get an OAuth access token.

    If sa_key is given (path to a service-account JSON), use that. Otherwise
    fall back to gcloud ADC, stripping GOOGLE_APPLICATION_CREDENTIALS first
    (common misconfig pointing at a missing service-account file).
    """
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


def api(token: str, method: str, url: str, body=None, content_type="application/json"):
    """Call a Google API with automatic retry on transient failures (429/5xx)."""
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        if content_type == "application/json":
            data = json.dumps(body).encode()
        else:
            data = body  # raw bytes
        headers["Content-Type"] = content_type

    last_err = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
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
            # Non-retryable HTTP error: surface the server's error body to help debug.
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


def push_markdown(token: str, doc_id: str, md_path: str) -> None:
    """Step 1: PATCH the markdown via Drive upload API. Google converts natively."""
    with open(md_path, "rb") as f:
        content = f.read()
    url = f"https://www.googleapis.com/upload/drive/v3/files/{doc_id}?uploadType=media&supportsAllDrives=true"
    api(token, "PATCH", url, body=content, content_type="text/markdown")
    print(f"[1/5] Pushed markdown: {md_path} ({len(content):,} bytes)")


def fix_anchor_links(token: str, doc_id: str) -> int:
    """Step 2: rewrite broken URL anchors to native headingId links. Returns count."""
    doc = api(token, "GET", f"https://docs.googleapis.com/v1/documents/{doc_id}")

    # Build section-number -> headingId map from headings
    section_to_hid = {}
    for elem in doc["body"]["content"]:
        p = elem.get("paragraph")
        if not p:
            continue
        ps = p.get("paragraphStyle", {})
        if not ps.get("namedStyleType", "").startswith("HEADING_"):
            continue
        hid = ps.get("headingId")
        if not hid:
            continue
        text = "".join(e.get("textRun", {}).get("content", "") for e in p.get("elements", [])).strip()
        m = HEADING_NUM_RE.match(text)
        if m:
            section_to_hid[m.group(1)] = hid

    # Walk text runs (body + table cells), rewrite broken URL anchors
    requests = []

    def process_element(e):
        tr = e.get("textRun")
        if not tr:
            return
        link = tr.get("textStyle", {}).get("link")
        if not link or not link.get("url", "").startswith("#"):
            return
        m = LINK_TEXT_NUM_RE.search(tr.get("content", ""))
        if not m:
            return
        num = m.group(1)
        hid = section_to_hid.get(num)
        if not hid:
            # Progressively shorter prefix (5.3.1 -> 5.3 -> 5)
            parts = num.split(".")
            for k in range(len(parts) - 1, 0, -1):
                cand = ".".join(parts[:k])
                if cand in section_to_hid:
                    hid = section_to_hid[cand]
                    break
        if not hid:
            return
        requests.append({"updateTextStyle": {
            "range": {"startIndex": e["startIndex"], "endIndex": e["endIndex"]},
            "textStyle": {"link": {"headingId": hid}},
            "fields": "link",
        }})

    def walk(content_list):
        for elem in content_list:
            p = elem.get("paragraph")
            if p:
                for e in p.get("elements", []):
                    process_element(e)
            tbl = elem.get("table")
            if tbl:
                for row in tbl.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk(cell.get("content", []))

    walk(doc["body"]["content"])

    if requests:
        api(token, "POST", f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
            body={"requests": requests})
    print(f"[2/5] Fixed {len(requests)} in-doc anchor links")
    return len(requests)


def fix_cross_doc_links(token: str, doc_id: str, cross_doc_map: dict) -> int:
    """Step 3: rewrite [text](other.md#anchor) cross-doc references into proper
    deep-links pointing at the corresponding sibling Google Doc + heading ID.

    cross_doc_map: {markdown_filename_or_path_fragment: target_doc_id}.
    Match is by substring on the URL-decoded link URL — so any path that
    contains the key matches. Anchor resolution tries (in order):
      1. Slug match — google_slugify(target_heading_text) == anchor
      2. Section number match — extract leading number from anchor or link text
      3. Fallback — link to the target Doc's top with no anchor

    Returns count of links rewritten.
    """
    if not cross_doc_map:
        print("[3/5] Skipped cross-doc link rewriting (no --cross-doc-map)")
        return 0

    # Fetch heading maps for each target Doc once
    target_caches = {}
    for path, target_id in cross_doc_map.items():
        slug_map, section_map = fetch_target_doc_headings(token, target_id)
        target_caches[path] = (target_id, slug_map, section_map)

    doc = api(token, "GET", f"https://docs.googleapis.com/v1/documents/{doc_id}")

    requests = []

    def process_element(e):
        tr = e.get("textRun")
        if not tr:
            return
        link = tr.get("textStyle", {}).get("link")
        if not link:
            return
        url = link.get("url", "")
        if not url:
            return
        decoded_url = urllib.parse.unquote(url)
        # Find a matching cross-doc path
        for path, (target_id, slug_map, section_map) in target_caches.items():
            if path not in decoded_url:
                continue
            # Extract anchor portion (after #), if any
            anchor = ""
            if "#" in decoded_url:
                anchor = decoded_url.rsplit("#", 1)[1]
            # 1. Try slug match
            hid = slug_map.get(anchor) if anchor else None
            # 2. Try section number from anchor leading digits
            if not hid and anchor:
                m = re.match(r"(\d+)(?:[-.]|$)", anchor)
                if m:
                    raw = m.group(1)
                    # The slug strips dots: "162" could be "16.2" or "1.6.2".
                    # Try the longest matching prefix that exists in section_map.
                    for k in range(len(raw), 0, -1):
                        for split in range(1, k + 1):
                            cand = raw[:split] + "." + raw[split:k] if split < k else raw[:k]
                            if cand in section_map:
                                hid = section_map[cand]
                                break
                        if hid:
                            break
            # 3. Try section number from link text
            if not hid:
                text = tr.get("content", "")
                m = LINK_TEXT_NUM_RE.search(text)
                if m:
                    hid = section_map.get(m.group(1))
            # Build new URL
            if hid:
                new_url = f"https://docs.google.com/document/d/{target_id}/edit#heading={hid}"
            else:
                new_url = f"https://docs.google.com/document/d/{target_id}/edit"
            requests.append({"updateTextStyle": {
                "range": {"startIndex": e["startIndex"], "endIndex": e["endIndex"]},
                "textStyle": {"link": {"url": new_url}},
                "fields": "link",
            }})
            return  # only one match per link

    def walk(content_list):
        for elem in content_list:
            p = elem.get("paragraph")
            if p:
                for e in p.get("elements", []):
                    process_element(e)
            tbl = elem.get("table")
            if tbl:
                for row in tbl.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk(cell.get("content", []))

    walk(doc["body"]["content"])

    if requests:
        api(token, "POST", f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
            body={"requests": requests})
    print(f"[3/5] Fixed {len(requests)} cross-doc links")
    return len(requests)


def resize_oversized_images(token: str, doc_id: str, md_path: str, max_width_pt: float) -> int:
    """Step 3: Google's markdown import sets inline images to their source
    resolution. Find any image wider than max_width_pt, delete it, and
    re-insert with explicit objectSize preserving aspect ratio. Uses the image
    URL from the original markdown (so the image source must still be
    reachable — the doc doesn't re-host the bytes locally).

    Returns count of images resized.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_urls = MARKDOWN_IMAGE_RE.findall(f.read())
    if not markdown_urls:
        return 0

    doc = api(token, "GET", f"https://docs.googleapis.com/v1/documents/{doc_id}")

    # Walk the doc to find inline image elements in text order
    def walk(content_list, out):
        for elem in content_list:
            p = elem.get("paragraph")
            if p:
                for e in p.get("elements", []):
                    iobj = e.get("inlineObjectElement")
                    if iobj:
                        out.append({
                            "start_index": e["startIndex"],
                            "end_index": e["endIndex"],
                            "inline_object_id": iobj["inlineObjectId"],
                        })
            tbl = elem.get("table")
            if tbl:
                for row in tbl.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk(cell.get("content", []), out)

    inline_images = []
    walk(doc["body"]["content"], inline_images)

    if len(inline_images) != len(markdown_urls):
        print(f"  ! image count mismatch: markdown has {len(markdown_urls)}, doc has {len(inline_images)} — skipping resize",
              file=sys.stderr)
        return 0

    resized = 0
    # Process in reverse order so earlier indices remain stable as we modify later ones
    # (each delete+insert is net zero length, but belt-and-suspenders)
    for img, url in reversed(list(zip(inline_images, markdown_urls))):
        obj = doc["inlineObjects"].get(img["inline_object_id"], {})
        size = obj.get("inlineObjectProperties", {}).get("embeddedObject", {}).get("size", {})
        cur_w = size.get("width", {}).get("magnitude", 0)
        cur_h = size.get("height", {}).get("magnitude", 0)

        if cur_w <= max_width_pt or cur_w == 0 or cur_h == 0:
            continue  # already reasonable size, or couldn't read dimensions

        aspect = cur_h / cur_w
        new_w = max_width_pt
        new_h = max_width_pt * aspect

        api(token, "POST", f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
            body={"requests": [
                {"deleteContentRange": {"range": {
                    "startIndex": img["start_index"],
                    "endIndex": img["end_index"],
                }}},
                {"insertInlineImage": {
                    "location": {"index": img["start_index"]},
                    "uri": url,
                    "objectSize": {
                        "height": {"magnitude": new_h, "unit": "PT"},
                        "width": {"magnitude": new_w, "unit": "PT"},
                    },
                }},
            ]})
        resized += 1

    print(f"[4/5] Resized {resized} oversized images (max width {max_width_pt}pt)")
    return resized


def apply_rtl(token: str, doc_id: str) -> None:
    """Step 5 (optional): set RIGHT_TO_LEFT direction on all body paragraphs."""
    doc = api(token, "GET", f"https://docs.googleapis.com/v1/documents/{doc_id}")
    end = doc["body"]["content"][-1]["endIndex"]
    api(token, "POST", f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
        body={"requests": [{
            "updateParagraphStyle": {
                "range": {"startIndex": 1, "endIndex": end - 1},
                "paragraphStyle": {"direction": "RIGHT_TO_LEFT"},
                "fields": "direction",
            }
        }]})
    print(f"[5/5] Applied RTL across doc (1..{end - 1})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync a markdown file to an existing Google Doc: push markdown, fix anchor links, resize images, optional RTL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("markdown", help="Path to the markdown file to push")
    parser.add_argument("--doc-id", required=True, help="Google Doc file ID (the long string in the URL)")
    parser.add_argument("--sa-key", default=None,
                        help="Path to a service-account JSON key. Recommended. The SA email must have Editor access to the Doc. If omitted, falls back to gcloud ADC.")
    parser.add_argument("--rtl", action="store_true",
                        help="Apply RTL paragraph direction (for Hebrew/Arabic docs)")
    parser.add_argument("--no-links", action="store_true",
                        help="Skip anchor-link rewriting (step 2)")
    parser.add_argument("--max-image-width", type=float, default=300.0,
                        help="Max inline image width in points (default 300pt); wider images are resized preserving aspect ratio. Set 0 to skip.")
    parser.add_argument("--cross-doc-map", action="append", default=[], metavar="NAME=DOC_ID",
                        help="Map a markdown filename (or path fragment that appears in cross-doc link URLs) to a sibling Google Doc ID. Repeatable. Cross-doc links are rewritten to deep-link into the target Doc's heading. Example: --cross-doc-map 'product-plan.md=1lSsp...'")
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

    push_markdown(token, args.doc_id, args.markdown)

    if not args.no_links:
        fix_anchor_links(token, args.doc_id)
        fix_cross_doc_links(token, args.doc_id, cross_doc_map)
    else:
        print("[2/5] Skipped in-doc anchor rewriting (--no-links)")
        print("[3/5] Skipped cross-doc rewriting (--no-links)")

    if args.max_image_width > 0:
        resize_oversized_images(token, args.doc_id, args.markdown, args.max_image_width)
    else:
        print("[4/5] Skipped image resize (--max-image-width 0)")

    if args.rtl:
        apply_rtl(token, args.doc_id)
    else:
        print("[5/5] Skipped RTL (use --rtl to enable)")

    print(f"Done. https://docs.google.com/document/d/{args.doc_id}/edit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
