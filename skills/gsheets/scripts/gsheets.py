#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["google-auth", "requests"]
# ///
"""gsheets — Google Sheets API v4 CLI.

  Data         read, find, write, batch-write, append, clear
  Tabs         list-tabs, add-tab, delete-tab, rename-tab, duplicate-tab,
               move-tab, set-title
  Structure    resize-cols, resize-rows, freeze, merge, unmerge,
               insert-rows, insert-cols, delete-rows, delete-cols
  Styling      format, format-header, borders, banding, conditional-format,
               validation, note, copy-format, table
  Filter/sort  add-filter, clear-filter, sort
  Inspect      info, inspect, revisions, export
  Escape       batch-update (raw Sheets batchUpdate requests[])

Usage: gsheets.py <command> <SPREADSHEET_ID> [RANGE] [flags]
  SPREADSHEET_ID is the token in .../spreadsheets/d/<ID>/edit.
  RANGE is A1 notation, positional or --range: "Tab!A1:C10", "'My Tab'!A:C".

Auth (first match wins):
  --sa-key PATH, then $GOOGLE_SA_KEY, then ~/.config/gdoc-sync/sa-key.json,
  then gcloud ADC. Runs on a bare python3: if google-auth is missing it
  signs the service-account JWT with `cryptography` or the openssl CLI.

Output: data commands print JSON on stdout; status lines start with "✓".
On any error stdout is empty and the exit code is non-zero (2 = usage,
3 = --expect refused the write, 4 = --verify found a mismatch), so check
the exit code before parsing.
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import random
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
from typing import Any

# ─── Constants ────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"

DEFAULT_SA_KEY = Path.home() / ".config" / "gdoc-sync" / "sa-key.json"
SA_KEY_ENV = "GOOGLE_SA_KEY"

_MAX_RETRIES = 5
_BASE_DELAY = 1.5
_MAX_BACKOFF = 32.0
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

DRY_RUN = False
_SA_EMAIL: str | None = None


class DryRun(Exception):
    """Raised after a --dry-run printed the request it would have sent."""


class Refused(Exception):
    """--expect found cells that differ from what the caller expected."""


# ─── Auth ─────────────────────────────────────────────────────────────────

def resolve_sa_key(sa_key: str | Path | None) -> Path | None:
    """--sa-key, then $GOOGLE_SA_KEY, then the default path if it exists."""
    if sa_key:
        p = Path(sa_key).expanduser()
        if not p.is_file():
            sys.exit(f"error: service-account key not found: {p}")
        return p
    env = os.environ.get(SA_KEY_ENV)
    if env:
        p = Path(env).expanduser()
        if not p.is_file():
            sys.exit(f"error: ${SA_KEY_ENV} points at a missing file: {p}")
        return p
    if DEFAULT_SA_KEY.is_file():
        return DEFAULT_SA_KEY
    return None


def get_token(sa_key: str | Path | None = None, scopes: list[str] | None = None) -> str:
    """Return an OAuth bearer token for the Sheets + Drive scopes.

    Service account (see resolve_sa_key) when one is found, else gcloud ADC.
    For ADC we pass --scopes explicitly, because the default cloud-platform
    scope does not cover Sheets/Drive, and we drop a stale
    GOOGLE_APPLICATION_CREDENTIALS, a common footgun.
    """
    scopes = scopes or SCOPES
    key = resolve_sa_key(sa_key)
    if key is not None:
        return _token_from_service_account(key, scopes)

    env = os.environ.copy()
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    try:
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token",
             "--scopes=" + ",".join(scopes)],
            env=env, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        sys.exit(
            "error: no service-account key found and gcloud is not on PATH.\n"
            f"  pass --sa-key PATH, set ${SA_KEY_ENV}, or put the key at {DEFAULT_SA_KEY}"
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"error: gcloud ADC auth failed:\n{e.stderr}\n")
        sys.stderr.write(
            "\nfix one of:\n"
            f"  (1) pass --sa-key PATH (or set ${SA_KEY_ENV})\n"
            "  (2) gcloud auth application-default login --scopes="
            + ",".join(scopes) + ",https://www.googleapis.com/auth/cloud-platform\n"
        )
        sys.exit(1)
    return result.stdout.strip()


def _token_from_service_account(sa_key: Path, scopes: list[str]) -> str:
    """Exchange a service-account JSON for an access token.

    google-auth when it is importable (it also needs `requests`); otherwise
    mint the RS256 JWT ourselves, signing with `cryptography` or, failing
    that, the openssl CLI, so a bare python3 works.
    """
    global _SA_EMAIL
    sa = json.loads(sa_key.read_text())
    _SA_EMAIL = sa.get("client_email")
    try:
        from google.oauth2 import service_account  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
    except ImportError:
        pass
    else:
        creds = service_account.Credentials.from_service_account_info(sa, scopes=scopes)
        creds.refresh(Request())
        return creds.token

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT", "kid": sa.get("private_key_id")}
    claim = {
        "iss": sa["client_email"],
        "scope": " ".join(scopes),
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    }

    def b64(d: dict) -> bytes:
        return base64.urlsafe_b64encode(
            json.dumps(d, separators=(",", ":")).encode()
        ).rstrip(b"=")

    signing_input = b64(header) + b"." + b64(claim)
    sig = _rs256_sign(sa["private_key"], signing_input)
    assertion = signing_input + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion.decode(),
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        sys.exit(f"error: token exchange failed (HTTP {e.code}): {detail}")


def _rs256_sign(private_key_pem: str, data: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives import hashes, serialization  # type: ignore
        from cryptography.hazmat.primitives.asymmetric import padding  # type: ignore
    except ImportError:
        pass
    else:
        key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
        return key.sign(data, padding.PKCS1v15(), hashes.SHA256())

    openssl = shutil.which("openssl")
    if not openssl:
        sys.exit(
            "error: service-account auth needs google-auth, cryptography or the openssl CLI.\n"
            "  run with `uv run gsheets.py ...` or `pip install google-auth requests`"
        )
    fd, path = tempfile.mkstemp(suffix=".pem")  # created 0600
    try:
        with os.fdopen(fd, "w") as f:
            f.write(private_key_pem)
        out = subprocess.run(
            [openssl, "dgst", "-sha256", "-sign", path],
            input=data, capture_output=True, check=True,
        )
        return out.stdout
    finally:
        os.unlink(path)


# ─── HTTP ─────────────────────────────────────────────────────────────────

def _hint(code: int, body: str) -> str | None:
    if code == 403 and ("has not been used" in body or "is disabled" in body):
        return "enable the Sheets API and the Drive API in the service account's GCP project"
    if code == 403:
        who = _SA_EMAIL or "the service account"
        return f"share the file with {who} as Editor (Viewer is enough for reads)"
    if code == 404:
        return "check the spreadsheet ID; a file that is not shared with you also returns 404"
    if code == 400 and "Unable to parse range" in body:
        return "check the tab name; quote names with spaces or symbols: \"'My Tab'!A1:C10\""
    return None


def api(
    token: str,
    method: str,
    url: str,
    body: Any = None,
    content_type: str = "application/json",
    raw: bool = False,
    idempotent: bool | None = None,
) -> Any:
    """HTTP call with truncated-exponential-backoff retry on 429 / 5xx.

    429 means nothing was applied, so it is always retried. A 5xx or a
    timeout may come after the server committed the write, so those are
    retried only for idempotent calls (GET/PUT by default; pass
    idempotent=True for POSTs that are safe to repeat).

    `body` is JSON-encoded when it's a dict/list; bytes pass through.
    Returns parsed JSON ({} for an empty reply), or bytes when the reply is
    not JSON or raw=True. Raises urllib.error.HTTPError after printing the
    API's error body (and a hint) to stderr.
    """
    if not isinstance(url, str) or not url.startswith("https://"):
        # Never echo the value: with swapped arguments it is the token.
        raise ValueError("api(token, method, url, body): url must start with https://")
    headers = {"Authorization": f"Bearer {token}"}
    payload: bytes | None = None
    if body is not None:
        if isinstance(body, (dict, list)):
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        elif isinstance(body, bytes):
            payload = body
            headers["Content-Type"] = content_type
        else:
            raise TypeError(f"unsupported body type: {type(body)}")

    if idempotent is None:
        idempotent = method in ("GET", "PUT", "DELETE")
    for attempt in range(_MAX_RETRIES):
        req = urllib.request.Request(url, data=payload, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                if raw:
                    return data
                if not data:
                    return {}
                if "application/json" in resp.headers.get("Content-Type", ""):
                    return json.loads(data)
                return data
        except urllib.error.HTTPError as e:
            if (e.code == 429 or (idempotent and e.code in _RETRYABLE_STATUS)) and attempt < _MAX_RETRIES - 1:
                delay = min(_BASE_DELAY * (2 ** attempt), _MAX_BACKOFF) + random.uniform(0, 1.0)
                sys.stderr.write(
                    f"  ! HTTP {e.code} on {method} {url.split('?')[0]} — "
                    f"retrying in {delay:.1f}s (attempt {attempt + 1}/{_MAX_RETRIES})\n"
                )
                time.sleep(delay)
                continue
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            sys.stderr.write(f"\nHTTP {e.code} on {method} {url.split('?')[0]}:\n{err_body[:1200]}\n")
            hint = _hint(e.code, err_body)
            if hint:
                sys.stderr.write(f"hint: {hint}\n")
            raise
        except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
            if idempotent and attempt < _MAX_RETRIES - 1:
                delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.0)
                sys.stderr.write(f"  ! {type(e).__name__} on {method} — retrying in {delay:.1f}s\n")
                time.sleep(delay)
                continue
            raise
    raise RuntimeError("retry loop exhausted")


# ─── A1 / GridRange utilities ─────────────────────────────────────────────

_CELL_RX = re.compile(r"^\$?([A-Za-z]*)\$?([0-9]*)$")


def col_letter_to_index(letter: str) -> int:
    """'A' → 0, 'Z' → 25, 'AA' → 26."""
    letter = letter.upper().lstrip("$")
    if not letter:
        raise ValueError("empty column letter")
    n = 0
    for ch in letter:
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"invalid column letter: {letter!r}")
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def col_index_to_letter(idx: int) -> str:
    """0 → 'A', 25 → 'Z', 26 → 'AA'."""
    if idx < 0:
        raise ValueError(f"negative col index: {idx}")
    out = ""
    n = idx + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(ord("A") + rem) + out
    return out


def quote_tab(title: str) -> str:
    """Always-safe A1 sheet prefix: 'My Tab' → "'My Tab'"."""
    return "'" + title.replace("'", "''") + "'"


def parse_a1(a1: str) -> tuple[str | None, str]:
    """'Tab Name!A1:C10' → ('Tab Name', 'A1:C10'); "'It''s'!A1" → ("It's", 'A1')."""
    a1 = a1.strip()
    if a1.startswith("'"):
        i = 1
        while i < len(a1):
            if a1[i] == "'":
                if i + 1 < len(a1) and a1[i + 1] == "'":
                    i += 2
                    continue
                break
            i += 1
        tab = a1[1:i].replace("''", "'")
        rest = a1[i + 1:]
        return tab, rest[1:] if rest.startswith("!") else rest
    if "!" not in a1:
        return None, a1
    tab, _, rng = a1.partition("!")
    return tab.strip(), rng


def range_bounds(rng: str) -> tuple[int | None, int | None, int | None, int | None]:
    """'B2:D10' → (sr=1, er=10, sc=1, ec=4), half-open, None = open.

    Accepts 'A1', 'A:C', '2:5', 'B2:B' (open end row), '' (whole sheet).
    """
    rng = rng.strip()
    if not rng:
        return None, None, None, None
    start, _, end = rng.partition(":")
    if not end:
        end = start
    sm, em = _CELL_RX.match(start), _CELL_RX.match(end)
    if not sm or not em:
        raise ValueError(f"invalid range: {rng!r}")
    s_col, s_row = sm.groups()
    e_col, e_row = em.groups()
    sr = int(s_row) - 1 if s_row else None
    er = int(e_row) if e_row else None
    sc = col_letter_to_index(s_col) if s_col else None
    ec = col_letter_to_index(e_col) + 1 if e_col else None
    if sr is None and er is not None:
        sr = 0
    if sc is None and ec is not None:
        sc = 0
    return sr, er, sc, ec


def a1_to_grid_range(a1: str, sheet_id: int) -> dict:
    """'A1:C10' / 'A:C' / '1:3' / 'B2:B' (with or without 'Tab!') → GridRange."""
    _, rng = parse_a1(a1)
    sr, er, sc, ec = range_bounds(rng)
    gr: dict = {"sheetId": sheet_id}
    if sr is not None:
        gr["startRowIndex"] = sr
    if er is not None:
        gr["endRowIndex"] = er
    if sc is not None:
        gr["startColumnIndex"] = sc
    if ec is not None:
        gr["endColumnIndex"] = ec
    return gr


def a1_to_dimension_range(a1: str, sheet_id: int) -> dict:
    """'A:C' → COLUMNS [0,3); '3:5' → ROWS [2,5)."""
    _, rng = parse_a1(a1)
    start, _, end = rng.partition(":")
    end = end or start
    if start.isdigit() and end.isdigit():
        return {"sheetId": sheet_id, "dimension": "ROWS",
                "startIndex": int(start) - 1, "endIndex": int(end)}
    if start.isalpha() and end.isalpha():
        return {"sheetId": sheet_id, "dimension": "COLUMNS",
                "startIndex": col_letter_to_index(start), "endIndex": col_letter_to_index(end) + 1}
    raise ValueError(f"dimension range must be rows ('3:5') or columns ('A:C'): {a1!r}")


def grid_to_a1(gr: dict, col_count: int | None = None) -> str:
    """GridRange → 'B2:D10' (no tab prefix). Open ends render as 'B2:B' / 'A:C' / '2:5'."""
    sr, er = gr.get("startRowIndex"), gr.get("endRowIndex")
    sc, ec = gr.get("startColumnIndex"), gr.get("endColumnIndex")
    if sc is None and ec is None:
        if sr is None and er is None:
            return ""
        return f"{(sr or 0) + 1}:{er if er is not None else ''}".rstrip(":")
    c1 = col_index_to_letter(sc or 0)
    if ec is not None:
        c2 = col_index_to_letter(ec - 1)
    elif col_count:
        c2 = col_index_to_letter(col_count - 1)
    else:
        c2 = c1
    left = c1 + (str(sr + 1) if sr is not None else "")
    right = c2 + (str(er) if er is not None else "")
    return left if left == right else f"{left}:{right}"


def col_range_to_indices(spec: str) -> tuple[int, int]:
    """'A:C' → (0, 3) half-open. Single 'A' → (0, 1)."""
    parts = spec.upper().split(":")
    if len(parts) == 1:
        i = col_letter_to_index(parts[0])
        return i, i + 1
    a, b = parts
    return col_letter_to_index(a), col_letter_to_index(b) + 1


def row_range_to_indices(spec: str) -> tuple[int, int]:
    """'1:3' → (0, 3) half-open. Single '5' → (4, 5)."""
    parts = spec.split(":")
    if len(parts) == 1:
        i = int(parts[0]) - 1
        return i, i + 1
    a, b = parts
    return int(a) - 1, int(b)


def parse_color(hex_str: str) -> dict:
    """'#1a73e8' / '1a73e8' / '#fff' → {red, green, blue} as 0-1 floats."""
    s = hex_str.lstrip("#").strip()
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"invalid hex color: {hex_str!r}")
    try:
        r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    except ValueError as e:
        raise ValueError(f"invalid hex color: {hex_str!r}") from e
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


def number_format(pattern: str) -> dict:
    """Pattern → NumberFormat, inferring the type the pattern needs.

    'TEXT' → plain text (keeps leading zeros typed later in the UI).
    """
    if pattern.upper() == "TEXT":
        return {"type": "TEXT"}
    p = re.sub(r'"[^"]*"|\[[^\]]*\]', "", pattern)  # ignore "$" literals and [Red] / [$₪-40D] tags
    if "%" in p:
        kind = "PERCENT"
    elif re.search(r"[yd]|mmm|m/|/m|h:|:m|:s", p, re.IGNORECASE):
        kind = "DATE_TIME" if re.search(r"h|:s", p, re.IGNORECASE) and re.search(r"[yd]", p, re.IGNORECASE) else (
            "TIME" if re.search(r"h|:s", p, re.IGNORECASE) else "DATE")
    elif re.search(r"[$€£₪¥]|\[\$", pattern) or re.search(r'"[$€£₪¥]', pattern):
        kind = "CURRENCY"
    elif re.search(r"[eE][+-]", p):
        kind = "SCIENTIFIC"
    else:
        kind = "NUMBER"
    return {"type": kind, "pattern": pattern}


def load_json_arg(raw: str) -> Any:
    """Inline JSON or @file.json."""
    if raw.startswith("@"):
        raw = Path(raw[1:]).expanduser().read_text()
    return json.loads(raw)


def load_values(args) -> list[list]:
    """Resolve --values-json / --csv / --values-stdin into a 2D array."""
    if getattr(args, "values_json", None) is not None:
        data = load_json_arg(args.values_json)
        if not isinstance(data, list):
            raise ValueError("--values-json must be a JSON 2D array")
        return [list(row) if isinstance(row, list) else [row] for row in data]
    if getattr(args, "csv", None) is not None:
        text = Path(args.csv).expanduser().read_text()
        return [row for row in csv.reader(io.StringIO(text))]
    if getattr(args, "values_stdin", False):
        return [row for row in csv.reader(sys.stdin)]
    raise ValueError("provide one of --values-json, --csv, --values-stdin")


# ─── Spreadsheet metadata ─────────────────────────────────────────────────

_meta_cache: dict[str, dict] = {}


def get_spreadsheet(token: str, spreadsheet_id: str, force: bool = False) -> dict:
    """GET spreadsheet + sheets[].properties (cached per process)."""
    if not force and spreadsheet_id in _meta_cache:
        return _meta_cache[spreadsheet_id]
    fields = "spreadsheetId,properties.title,sheets.properties"
    url = f"{SHEETS_BASE}/{spreadsheet_id}?fields={urllib.parse.quote(fields)}"
    meta = api(token, "GET", url)
    _meta_cache[spreadsheet_id] = meta
    return meta


def resolve_tab(token: str, spreadsheet_id: str, title: str) -> dict:
    """Tab title → its properties dict (incl. sheetId). Exits listing titles."""
    meta = get_spreadsheet(token, spreadsheet_id)
    for sh in meta.get("sheets", []):
        p = sh.get("properties", {})
        if p.get("title") == title:
            return p
    titles = [s.get("properties", {}).get("title") for s in meta.get("sheets", [])]
    sys.exit(f"error: tab {title!r} not found. available: {titles}")


def resolve_tab_id(token: str, spreadsheet_id: str, title: str) -> int:
    return resolve_tab(token, spreadsheet_id, title)["sheetId"]


def tab_and_grid(token: str, spreadsheet_id: str, a1: str) -> tuple[dict, dict]:
    """'Tab!A1:C3' → (tab properties, GridRange). The tab prefix is required."""
    tab, _ = parse_a1(a1)
    if not tab:
        sys.exit(f"error: range needs a tab prefix, e.g. 'Sheet1!A1:C1' (got {a1!r})")
    props = resolve_tab(token, spreadsheet_id, tab)
    return props, a1_to_grid_range(a1, props["sheetId"])


def batch_update(token: str, spreadsheet_id: str, requests: list[dict]) -> dict:
    """POST {spreadsheet}:batchUpdate. All requests commit together or none
    do, and the whole batch counts as one call against the write quota."""
    if not requests:
        return {"replies": []}
    if DRY_RUN:
        print(json.dumps({"requests": requests}, indent=2, ensure_ascii=False))
        raise DryRun()
    url = f"{SHEETS_BASE}/{spreadsheet_id}:batchUpdate"
    safe = not any(k in _UNSAFE_TO_REPEAT for r in requests for k in r)
    return api(token, "POST", url, {"requests": requests}, idempotent=safe)


# Requests that do something different when applied twice (a retry after a
# timeout would insert/delete again); batches containing them aren't retried.
_UNSAFE_TO_REPEAT = {
    "insertDimension", "deleteDimension", "appendDimension", "appendCells", "insertRange",
    "deleteRange", "moveDimension", "cutPaste", "duplicateSheet", "addConditionalFormatRule",
    "deleteConditionalFormatRule", "addChart", "addFilterView", "addProtectedRange",
    "addNamedRange", "addDimensionGroup", "deleteDimensionGroup", "addSlicer", "addTable",
}


def extent_range(rng: str, height: int, width: int) -> str:
    """The range a write of height×width values starting at rng's top-left
    actually covers (at least rng itself when rng is bounded)."""
    tab, a1 = parse_a1(rng)
    if tab is None:
        return rng  # bare "Sheet1" is ambiguous (tab name vs A1); leave it
    sr, er, sc, ec = range_bounds(a1) if a1 else (None, None, None, None)
    sr, sc = sr or 0, sc or 0
    h = max(height, (er - sr) if er is not None else 0)
    w = max(width, (ec - sc) if ec is not None else 0)
    if h <= 0 or w <= 0:
        return rng
    return f"{quote_tab(tab)}!{col_index_to_letter(sc)}{sr + 1}:{col_index_to_letter(sc + w - 1)}{sr + h}"


def _size(grid: list | None) -> tuple[int, int]:
    grid = grid or []
    return len(grid), max((len(r) for r in grid if isinstance(r, list)), default=0)


def fetch_values(
    token: str, spreadsheet_id: str, ranges: list[str],
    render: str = "FORMATTED_VALUE", major: str | None = None,
) -> list[tuple[str, list]]:
    """[(api_range, values)] for each requested range, in order.

    Uses values.get for one range and values:batchGet for several (one call).
    The API trims trailing empty cells and rows; values is [] when empty.
    """
    qs = [("valueRenderOption", render)]
    if major:
        qs.append(("majorDimension", major))
    if len(ranges) == 1:
        rng = urllib.parse.quote(ranges[0], safe="")
        url = f"{SHEETS_BASE}/{spreadsheet_id}/values/{rng}?{urllib.parse.urlencode(qs)}"
        resp = api(token, "GET", url)
        return [(resp.get("range", ranges[0]), resp.get("values", []))]
    qs += [("ranges", r) for r in ranges]
    url = f"{SHEETS_BASE}/{spreadsheet_id}/values:batchGet?{urllib.parse.urlencode(qs)}"
    resp = api(token, "GET", url)
    return [(vr.get("range", r), vr.get("values", []))
            for r, vr in zip(ranges, resp.get("valueRanges", []))]


def fetch_merges(token: str, spreadsheet_id: str, tab: str) -> list[dict]:
    fields = "sheets(properties(title),merges)"
    qs = urllib.parse.urlencode({"ranges": quote_tab(tab), "fields": fields})
    meta = api(token, "GET", f"{SHEETS_BASE}/{spreadsheet_id}?{qs}")
    for sh in meta.get("sheets", []):
        return sh.get("merges", []) or []
    return []


def range_start(api_range: str) -> tuple[int, int]:
    """0-based (row, col) of a values response's top-left cell."""
    _, rng = parse_a1(api_range)
    sr, _, sc, _ = range_bounds(rng)
    return sr or 0, sc or 0


# ─── Grid shaping (pad / merged cells / records) ──────────────────────────

def pad_grid(values: list[list], requested: str) -> list[list]:
    """Rectangularise: width = the requested range's column count when it is
    bounded, else the longest row; height = its row count when bounded."""
    tab, rng = parse_a1(requested)
    if tab is None and ":" not in rng:
        rng = ""  # a bare "Sheet1" is a tab name, not column-range "Sheet1"
    sr, er, sc, ec = range_bounds(rng) if rng else (None, None, None, None)
    width = (ec - (sc or 0)) if ec is not None else max((len(r) for r in values), default=0)
    rows = [list(r) + [""] * (width - len(r)) for r in values]
    if er is not None:
        height = er - (sr or 0)
        rows += [[""] * width for _ in range(height - len(rows))]
    return rows


def fill_merged(values: list[list], merges: list[dict], origin: tuple[int, int],
                only_rows: int | None = None) -> list[list]:
    """Copy each merge's top-left value into every cell it covers.

    The API returns a merged value only in its first cell. origin is the
    (row, col) of values[0][0]; only_rows limits filling to the first N rows.
    """
    r0, c0 = origin
    out = [list(r) for r in values]
    width = max((len(r) for r in out), default=0)  # merges past the data are irrelevant
    for m in merges:
        sr, er = m.get("startRowIndex", 0) - r0, m.get("endRowIndex", 0) - r0
        sc, ec = m.get("startColumnIndex", 0) - c0, m.get("endColumnIndex", 0) - c0
        ec = min(ec, width)
        if sr < 0 or sc < 0 or sr >= len(out) or sc >= ec:
            continue
        row = out[sr]
        top_left = row[sc] if sc < len(row) else ""
        for r in range(sr, min(er, len(out))):
            if only_rows is not None and r >= only_rows:
                break
            while len(out[r]) < ec:
                out[r].append("")
            for c in range(sc, ec):
                out[r][c] = top_left
    return out


def header_keys(header: list[list], c0: int, width: int | None = None) -> list[str]:
    width = max(max((len(r) for r in header), default=0), width or 0)
    keys: list[str] = []
    for j in range(width):
        parts: list[str] = []
        for row in header:
            v = str(row[j]).replace("\n", " ").strip() if j < len(row) else ""
            if v and (not parts or parts[-1] != v):
                parts.append(v)
        keys.append(" / ".join(parts) or col_index_to_letter(c0 + j))
    seen: dict[str, int] = {}
    for j, k in enumerate(keys):
        seen[k] = seen.get(k, 0) + 1
    for j, k in enumerate(keys):
        if seen[k] > 1:
            keys[j] = f"{k} ({col_index_to_letter(c0 + j)})"
    return keys


def to_records(values: list[list], header_rows: int, origin: tuple[int, int],
               merges: list[dict]) -> tuple[list[str], list[dict]]:
    """Rows below the header as dicts keyed by the (merge-filled) header path,
    plus "_row", the row's 1-based sheet row number. Empty rows are skipped."""
    filled = fill_merged(values, merges, origin, only_rows=header_rows)
    header = filled[:header_rows]
    keys = header_keys(header, origin[1], max((len(r) for r in filled), default=0))
    records = []
    for i, row in enumerate(filled[header_rows:]):
        if not any(str(v).strip() for v in row):
            continue
        rec: dict = {"_row": origin[0] + header_rows + i + 1}
        for j, k in enumerate(keys):
            rec[k] = row[j] if j < len(row) else ""
        records.append(rec)
    return keys, records


# ─── Compare-and-set (--expect) and read-back (--verify) ──────────────────

def _norm(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def check_expect(token: str, spreadsheet_id: str, expected: dict[str, list], render: str) -> None:
    """Raise Refused unless every range's live values equal `expected`.

    expected maps A1 range → 2D values in the same shape `read` prints, so a
    `read` saved earlier is a valid snapshot. Trailing blanks don't matter.
    """
    ranges = list(expected)
    live = fetch_values(token, spreadsheet_id, ranges, render=render)
    diffs = []
    for rng, (api_range, cur) in zip(ranges, live):
        exp = expected[rng] or []
        r0, c0 = range_start(api_range)
        tab, _ = parse_a1(api_range)
        height = max(len(exp), len(cur))
        for i in range(height):
            er = exp[i] if i < len(exp) else []
            cr = cur[i] if i < len(cur) else []
            for j in range(max(len(er), len(cr))):
                ev = _norm(er[j]) if j < len(er) else ""
                cv = _norm(cr[j]) if j < len(cr) else ""
                if ev != cv:
                    diffs.append({
                        "cell": f"{quote_tab(tab)}!{col_index_to_letter(c0 + j)}{r0 + i + 1}" if tab
                        else f"{col_index_to_letter(c0 + j)}{r0 + i + 1}",
                        "expected": ev, "actual": cv,
                    })
    if diffs:
        sys.stderr.write(json.dumps({"refused": True, "differences": diffs}, indent=2, ensure_ascii=False) + "\n")
        raise Refused(f"REFUSED: {len(diffs)} cell(s) differ from --expect; the sheet changed since you read it")


_ERROR_VALUES = ("#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A", "#ERROR!", "#NUM!", "#NULL!")


def verify_written(token: str, spreadsheet_id: str, written: dict[str, list], input_option: str) -> int:
    """Read back what was written; print suspicious conversions. Returns count."""
    ranges = list(written)
    stored = fetch_values(token, spreadsheet_id, ranges, render="FORMULA")
    shown = fetch_values(token, spreadsheet_id, ranges, render="FORMATTED_VALUE")
    problems, notes = [], 0
    for rng, (api_range, st), (_, sh) in zip(ranges, stored, shown):
        r0, c0 = range_start(api_range)
        for i, row in enumerate(written[rng]):
            for j, w in enumerate(row):
                if w is None:
                    continue
                s = st[i][j] if i < len(st) and j < len(st[i]) else ""
                f = sh[i][j] if i < len(sh) and j < len(sh[i]) else ""
                cell = f"{col_index_to_letter(c0 + j)}{r0 + i + 1}"
                if isinstance(f, str) and f in _ERROR_VALUES:
                    problems.append({"cell": cell, "sent": w, "shows": f, "why": "formula error"})
                    continue
                if isinstance(w, str) and isinstance(s, (int, float)) and not isinstance(s, bool):
                    digits = w.strip().replace(",", "")
                    if re.fullmatch(r"0\d+", digits):
                        problems.append({"cell": cell, "sent": w, "stored": s,
                                         "why": "leading zeros dropped (use RAW, or prefix the value with ')"})
                    elif re.fullmatch(r"\d{12,15}", digits):
                        problems.append({"cell": cell, "sent": w, "stored": s,
                                         "why": "long ID stored as a number (can show as 4.7E+11; use RAW to keep text)"})
                    else:
                        notes += 1
                elif _norm(w) != _norm(s) and not (isinstance(w, str) and w.startswith("=")):
                    notes += 1
    if problems:
        sys.stderr.write(json.dumps({"verify": "mismatch", "problems": problems}, indent=2, ensure_ascii=False) + "\n")
    total = sum(1 for r in written.values() for row in r for v in row if v is not None)
    extra = f"; {notes} were parsed into numbers/dates as {input_option} does" if notes else ""
    print(f"{'✗' if problems else '✓'} verify: {total - len(problems)}/{total} cells as intended{extra}")
    return len(problems)


# ─── Subcommand: meta ─────────────────────────────────────────────────────

def cmd_info(args, token: str) -> int:
    """Spreadsheet name, owner, last editor and tabs — a safe probe."""
    fields = (
        "spreadsheetId,properties(title,locale,timeZone),"
        "sheets.properties(sheetId,title,index,hidden,rightToLeft,gridProperties)"
    )
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}?fields={urllib.parse.quote(fields)}"
    meta = api(token, "GET", url)
    drive_fields = ("id,name,owners(emailAddress),capabilities(canEdit),modifiedTime,"
                    "lastModifyingUser(displayName,emailAddress)")
    drive_url = (f"{DRIVE_BASE}/files/{args.spreadsheet_id}"
                 f"?fields={urllib.parse.quote(drive_fields)}&supportsAllDrives=true")
    dmeta = api(token, "GET", drive_url)
    lmu = dmeta.get("lastModifyingUser") or {}
    out = {
        "spreadsheetId": meta["spreadsheetId"],
        "title": meta["properties"]["title"],
        "locale": meta["properties"].get("locale"),
        "timeZone": meta["properties"].get("timeZone"),
        "modifiedTime": dmeta.get("modifiedTime"),
        "lastModifyingUser": lmu.get("emailAddress") or lmu.get("displayName"),
        "owners": [o.get("emailAddress") for o in (dmeta.get("owners") or [])],
        "canEdit": (dmeta.get("capabilities") or {}).get("canEdit"),
        "tabs": [
            {
                "sheetId": s["properties"]["sheetId"],
                "title": s["properties"]["title"],
                "index": s["properties"].get("index"),
                "hidden": s["properties"].get("hidden", False),
                "rightToLeft": s["properties"].get("rightToLeft", False),
                "rowCount": s["properties"].get("gridProperties", {}).get("rowCount"),
                "columnCount": s["properties"].get("gridProperties", {}).get("columnCount"),
                "frozenRowCount": s["properties"].get("gridProperties", {}).get("frozenRowCount", 0),
                "frozenColumnCount": s["properties"].get("gridProperties", {}).get("frozenColumnCount", 0),
            }
            for s in meta.get("sheets", [])
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_revisions(args, token: str) -> int:
    """Recent Drive revisions: who edited and when (not what changed)."""
    fields = "nextPageToken,revisions(id,modifiedTime,lastModifyingUser(displayName,emailAddress))"
    revs, page = [], None
    while True:
        url = (f"{DRIVE_BASE}/files/{args.spreadsheet_id}/revisions?fields={urllib.parse.quote(fields)}"
               f"&pageSize=1000" + (f"&pageToken={page}" if page else ""))
        resp = api(token, "GET", url)
        revs += resp.get("revisions", [])
        page = resp.get("nextPageToken")
        if not page:
            break
    out = [{
        "id": r.get("id"),
        "modifiedTime": r.get("modifiedTime"),
        "user": (r.get("lastModifyingUser") or {}).get("emailAddress")
        or (r.get("lastModifyingUser") or {}).get("displayName"),
    } for r in revs[-args.limit:]]
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


# ─── Subcommand: data (values.*) ──────────────────────────────────────────

_RENDER_ALIASES = {
    "formatted": "FORMATTED_VALUE", "unformatted": "UNFORMATTED_VALUE",
    "formula": "FORMULA", "formulas": "FORMULA",
}


def _render(v: str) -> str:
    return _RENDER_ALIASES.get(v.lower(), v.upper())


def _ranges(args, required: bool = True) -> list[str]:
    pos = getattr(args, "range_pos", None)
    out = [pos] if isinstance(pos, str) else list(pos or [])
    flag = getattr(args, "range", None)
    if isinstance(flag, list):
        out += flag
    elif flag:
        out.append(flag)
    if required and not out:
        sys.exit("error: give a range, e.g. \"Sheet1!A1:C10\" (positional or --range)")
    return out


def _one_range(args) -> str:
    rs = _ranges(args)
    if len(rs) != 1:
        sys.exit("error: this command takes exactly one range")
    return rs[0]


def cmd_read(args, token: str) -> int:
    ranges = _ranges(args, required=not args.all_tabs)
    if args.all_tabs:
        titles = [s["properties"]["title"] for s in get_spreadsheet(token, args.spreadsheet_id)["sheets"]]
        ranges = [quote_tab(t) for t in titles]
        keys = titles
    else:
        keys = ranges
    render = _render(args.value_render)
    results = fetch_values(token, args.spreadsheet_id, ranges, render, args.major_dimension)
    shaped = []
    for req, (api_range, values) in zip(ranges, results):
        tab, _ = parse_a1(api_range)
        if args.header_rows or args.fill_merged:
            merges = fetch_merges(token, args.spreadsheet_id, tab) if tab else []
            origin = range_start(api_range)
            if args.header_rows:
                _, values = to_records(values, args.header_rows, origin, merges)
            else:
                values = fill_merged(values, merges, origin)
        if args.pad and not args.header_rows:
            values = pad_grid(values, req)
        if args.numbered and not args.header_rows:
            r0, _ = range_start(api_range)
            values = [{"_row": r0 + i + 1, "values": row} for i, row in enumerate(values)]
        shaped.append(values)
    out: Any = shaped[0] if len(shaped) == 1 and not args.all_tabs else dict(zip(keys, shaped))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def _tab_grid(token: str, args, header_rows: int):
    """(values, r0, c0, header keys) for a tab, merged header cells filled."""
    tab = args.tab
    rng = f"{quote_tab(tab)}!{args.within}" if getattr(args, "within", None) else quote_tab(tab)
    (api_range, values), = fetch_values(token, args.spreadsheet_id, [rng], _render(args.value_render))
    r0, c0 = range_start(api_range)
    keys: list[str] = []
    if header_rows:
        merges = fetch_merges(token, args.spreadsheet_id, tab)
        values = fill_merged(values, merges, (r0, c0), only_rows=header_rows)
        keys = header_keys(values[:header_rows], c0, max((len(r) for r in values), default=0))
    return values, r0, c0, keys


def cmd_headers(args, token: str) -> int:
    """Column letter ↔ header path, merged header cells filled."""
    _, _, c0, keys = _tab_grid(token, args, args.header_rows)
    print(json.dumps([{"col": col_index_to_letter(c0 + n), "header": k} for n, k in enumerate(keys)],
                     indent=2, ensure_ascii=False))
    return 0


def cmd_find(args, token: str) -> int:
    """Find rows by a cell's content; print their row numbers and A1 cells."""
    tab = args.tab
    header_rows = args.header_rows or 0
    if (args.col_header or args.show) and not header_rows:
        sys.exit("error: --col-header and --show need --header-rows N")
    values, r0, c0, keys = _tab_grid(token, args, header_rows)

    if args.value is not None:
        needle = args.value.strip()
        match = lambda v: str(v).strip() == needle  # noqa: E731
    elif args.contains is not None:
        needle = args.contains.lower()
        match = lambda v: needle in str(v).lower()  # noqa: E731
    else:
        rx = re.compile(args.regex)
        match = lambda v: bool(rx.search(str(v)))  # noqa: E731

    cols: list[int] | None = None
    if args.col:
        cols = [col_letter_to_index(c.strip()) - c0 for c in args.col.split(",")]
    if args.col_header:
        want = args.col_header.lower()
        by_header = [n for n, k in enumerate(keys) if want in k.lower()]
        if not by_header:
            sys.exit(f"error: no header contains {args.col_header!r}; run `headers` to list them")
        cols = sorted(set(cols or []) | set(by_header))
    show = [n for n, k in enumerate(keys) if args.show.lower() in k.lower()] if args.show else []
    with_record = args.record if args.record is not None else not args.show

    hits = []
    for i, row in enumerate(values[header_rows:], start=header_rows):
        rown = r0 + i + 1
        idx = cols if cols is not None else range(len(row))
        matched = [j for j in idx if 0 <= j < len(row) and match(row[j])]
        if not matched:
            continue
        j = matched[0]
        hit: dict = {"row": rown, "a1": f"{quote_tab(tab)}!{col_index_to_letter(c0 + j)}{rown}", "value": row[j]}
        if keys:
            hit["header"] = keys[j] if j < len(keys) else col_index_to_letter(c0 + j)
        if len(matched) > 1:
            hit["also"] = [f"{col_index_to_letter(c0 + m)}{rown}" for m in matched[1:]]
        if show:
            hit["cells"] = [{"header": keys[n], "a1": f"{quote_tab(tab)}!{col_index_to_letter(c0 + n)}{rown}",
                             "value": row[n] if n < len(row) else ""} for n in show]
        if with_record:
            if keys:
                hit["record"] = {k: (row[n] if n < len(row) else "") for n, k in enumerate(keys)}
            else:
                hit["values"] = row
        hits.append(hit)
    if not hits:
        sys.stderr.write("no matching rows\n")
    elif len(hits) > 1 and args.value is not None:
        sys.stderr.write(f"note: {len(hits)} rows match; tell them apart by another column before writing\n")
    print(json.dumps(hits, indent=2, ensure_ascii=False))
    return 0


def _prep_values(values: list[list], skip_empty: bool) -> list[list]:
    if skip_empty:
        return [[None if c == "" else c for c in row] for row in values]
    return values


def cmd_write(args, token: str) -> int:
    rng = _one_range(args)
    values = _prep_values(load_values(args), args.skip_empty)
    covered = extent_range(rng, *_size(values))
    if args.expect is not None:
        expected = load_json_arg(args.expect)
        h, w = _size(values)
        eh, ew = _size(expected)
        # Check every cell the write touches; cells past the snapshot must be empty now.
        check_expect(token, args.spreadsheet_id, {extent_range(rng, max(h, eh), max(w, ew)): expected},
                     _render(args.expect_render))
    q = urllib.parse.quote(rng, safe="")
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{q}?valueInputOption={args.value_input_option}"
    body = {"range": rng, "majorDimension": "ROWS", "values": values}
    if DRY_RUN:
        print(json.dumps({"method": "PUT", "valueInputOption": args.value_input_option, **body},
                         indent=2, ensure_ascii=False))
        raise DryRun()
    resp = api(token, "PUT", url, body)
    width = max((len(r) for r in values), default=0)
    print(f"✓ wrote {len(values)} rows × {width} cols to {resp.get('updatedRange', rng)} "
          f"(API counted {resp.get('updatedCells', 0)} cells in {resp.get('updatedRows', 0)} rows; "
          f"empty cells and skipped nulls don't count)")
    if args.verify:
        return 4 if verify_written(token, args.spreadsheet_id, {covered: values}, args.value_input_option) else 0
    return 0


def _load_data_map(raw: str) -> dict[str, list]:
    data = load_json_arg(raw)
    if isinstance(data, dict):
        return {k: v for k, v in data.items()}
    if isinstance(data, list):
        return {d["range"]: d["values"] for d in data}
    sys.exit("error: --data must be {\"Tab!A1\": [[...]], ...} or [{\"range\": ..., \"values\": [[...]]}]")


def cmd_batch_write(args, token: str) -> int:
    """Write many ranges in one values:batchUpdate call."""
    data = {k: _prep_values(v, args.skip_empty) for k, v in _load_data_map(args.data).items()}
    if args.expect is not None:
        snaps = _load_data_map(args.expect)
        missing = [k for k in data if k not in snaps]
        if missing:
            sys.exit(f"error: --expect has no snapshot for {missing}; give one for every range you write "
                     "(the keys must match --data)")
        check = {}
        for k, exp in snaps.items():
            (h, w), (eh, ew) = _size(data.get(k)), _size(exp)
            check[extent_range(k, max(h, eh), max(w, ew))] = exp
        check_expect(token, args.spreadsheet_id, check, _render(args.expect_render))
    body = {
        "valueInputOption": args.value_input_option,
        "data": [{"range": r, "majorDimension": "ROWS", "values": v} for r, v in data.items()],
    }
    if DRY_RUN:
        print(json.dumps(body, indent=2, ensure_ascii=False))
        raise DryRun()
    resp = api(token, "POST", f"{SHEETS_BASE}/{args.spreadsheet_id}/values:batchUpdate", body, idempotent=True)
    for r in resp.get("responses", []):
        print(f"✓ {r.get('updatedRange')}: {r.get('updatedCells', 0)} cells")
    print(f"✓ batch-write: {len(data)} ranges, {resp.get('totalUpdatedCells', 0)} cells in one call")
    if args.verify:
        covered = {extent_range(k, *_size(v)): v for k, v in data.items()}
        return 4 if verify_written(token, args.spreadsheet_id, covered, args.value_input_option) else 0
    return 0


def cmd_append(args, token: str) -> int:
    rng = _one_range(args)
    values = _prep_values(load_values(args), args.skip_empty)
    q = urllib.parse.quote(rng, safe="")
    qs = f"valueInputOption={args.value_input_option}&insertDataOption={args.insert_data_option}"
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{q}:append?{qs}"
    body = {"range": rng, "majorDimension": "ROWS", "values": values}
    if DRY_RUN:
        print(json.dumps({"method": "POST :append", "insertDataOption": args.insert_data_option, **body},
                         indent=2, ensure_ascii=False))
        raise DryRun()
    resp = api(token, "POST", url, body)
    updates = resp.get("updates", {})
    _, want = parse_a1(rng)
    _, got = parse_a1(updates.get("updatedRange", ""))
    want_col, got_col = range_bounds(want)[2], range_bounds(got)[2] if got else None
    if want_col is not None and got_col is not None and got_col != want_col:
        sys.stderr.write(
            f"  ! the rows landed at {updates.get('updatedRange')}, not from column "
            f"{col_index_to_letter(want_col)}: Sheets matched the table at {resp.get('tableRange')}. "
            "Check the sheet; for an exact position, write to an explicit range instead.\n")
    print(f"✓ appended {updates.get('updatedRows', 0)} rows, {updates.get('updatedCells', 0)} cells "
          f"→ {updates.get('updatedRange')} (table detected at {resp.get('tableRange', 'none')})")
    return 0


def cmd_clear(args, token: str) -> int:
    rng = _one_range(args)
    if args.formats or args.all:
        props, gr = tab_and_grid(token, args.spreadsheet_id, rng)
        fields = "userEnteredValue,userEnteredFormat"
        if args.all:
            fields += ",note,dataValidation"
        batch_update(token, args.spreadsheet_id, [{"updateCells": {"range": gr, "fields": fields}}])
        print(f"✓ cleared {rng} ({fields.replace(',', ', ')})")
        return 0
    if DRY_RUN:
        print(json.dumps({"method": "POST :clear", "range": rng}, indent=2))
        raise DryRun()
    q = urllib.parse.quote(rng, safe="")
    resp = api(token, "POST", f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{q}:clear", {}, idempotent=True)
    print(f"✓ cleared values in {resp.get('clearedRange', rng)} (formatting kept; --formats clears it too)")
    return 0


# ─── Subcommand: tabs ─────────────────────────────────────────────────────

def cmd_list_tabs(args, token: str) -> int:
    meta = get_spreadsheet(token, args.spreadsheet_id, force=True)
    print(f"{'sheetId':>10}  {'idx':>3}  {'title':<30}  {'rows':>6}  {'cols':>5}  {'frR':>3}  {'frC':>3}")
    for s in meta.get("sheets", []):
        p = s["properties"]
        g = p.get("gridProperties", {})
        print(f"{p['sheetId']:>10}  {p.get('index', 0):>3}  {str(p['title'])[:30]:<30}  "
              f"{str(g.get('rowCount')):>6}  {str(g.get('columnCount')):>5}  "
              f"{g.get('frozenRowCount', 0):>3}  {g.get('frozenColumnCount', 0):>3}")
    return 0


def cmd_add_tab(args, token: str) -> int:
    props: dict = {"title": args.title}
    grid: dict = {}
    if args.rows:
        grid["rowCount"] = args.rows
    if args.cols:
        grid["columnCount"] = args.cols
    if grid:
        props["gridProperties"] = grid
    if args.index is not None:
        props["index"] = args.index
    if args.sheet_id is not None:
        props["sheetId"] = args.sheet_id
    if args.color:
        props["tabColorStyle"] = {"rgbColor": parse_color(args.color)}
    if args.rtl:
        props["rightToLeft"] = True
    resp = batch_update(token, args.spreadsheet_id, [{"addSheet": {"properties": props}}])
    new_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
    print(f"✓ added tab {args.title!r} (sheetId={new_id})")
    return 0


def cmd_delete_tab(args, token: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.title)
    batch_update(token, args.spreadsheet_id, [{"deleteSheet": {"sheetId": sid}}])
    print(f"✓ deleted tab {args.title!r} (sheetId={sid})")
    return 0


def cmd_rename_tab(args, token: str) -> int:
    old = getattr(args, "from")
    sid = resolve_tab_id(token, args.spreadsheet_id, old)
    batch_update(token, args.spreadsheet_id, [{"updateSheetProperties": {
        "properties": {"sheetId": sid, "title": args.to}, "fields": "title"}}])
    print(f"✓ renamed tab {old!r} → {args.to!r}")
    return 0


def cmd_move_tab(args, token: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.title)
    batch_update(token, args.spreadsheet_id, [{"updateSheetProperties": {
        "properties": {"sheetId": sid, "index": args.index}, "fields": "index"}}])
    print(f"✓ moved tab {args.title!r} to index {args.index}")
    return 0


def cmd_set_title(args, token: str) -> int:
    """Rename the spreadsheet file itself (what Drive and the browser tab show)."""
    batch_update(token, args.spreadsheet_id, [{"updateSpreadsheetProperties": {
        "properties": {"title": args.title}, "fields": "title"}}])
    print(f"✓ spreadsheet title → {args.title!r}")
    return 0


def cmd_duplicate_tab(args, token: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, getattr(args, "from"))
    req: dict = {"duplicateSheet": {"sourceSheetId": sid, "newSheetName": args.to}}
    if args.index is not None:
        req["duplicateSheet"]["insertSheetIndex"] = args.index
    resp = batch_update(token, args.spreadsheet_id, [req])
    new_id = resp["replies"][0]["duplicateSheet"]["properties"]["sheetId"]
    print(f"✓ duplicated → {args.to!r} (sheetId={new_id})")
    return 0


# ─── Subcommand: structure ────────────────────────────────────────────────

def _resize(args, token: str, dimension: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.tab)
    spec = args.cols if dimension == "COLUMNS" else args.rows
    start, end = col_range_to_indices(spec) if dimension == "COLUMNS" else row_range_to_indices(spec)
    size = args.width if dimension == "COLUMNS" else args.height
    sizes = [int(x) for x in args.widths.split(",")] if getattr(args, "widths", None) else None
    reqs: list[dict] = []
    if args.auto:
        reqs.append({"autoResizeDimensions": {"dimensions": {
            "sheetId": sid, "dimension": dimension, "startIndex": start, "endIndex": end}}})
    elif sizes:
        for k, px in enumerate(sizes):
            if start + k >= end:
                break
            reqs.append({"updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": dimension, "startIndex": start + k, "endIndex": start + k + 1},
                "properties": {"pixelSize": px}, "fields": "pixelSize"}})
    else:
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": dimension, "startIndex": start, "endIndex": end},
            "properties": {"pixelSize": size}, "fields": "pixelSize"}})
    batch_update(token, args.spreadsheet_id, reqs)
    mode = "auto" if args.auto else (f"widths {sizes}" if sizes else f"{size}px")
    print(f"✓ resized {dimension.lower()} {spec} of {args.tab!r} → {mode}")
    return 0


def cmd_resize_cols(args, token: str) -> int:
    return _resize(args, token, "COLUMNS")


def cmd_resize_rows(args, token: str) -> int:
    return _resize(args, token, "ROWS")


def cmd_freeze(args, token: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.tab)
    grid: dict = {}
    fields = []
    if args.rows is not None:
        grid["frozenRowCount"] = args.rows
        fields.append("gridProperties.frozenRowCount")
    if args.cols is not None:
        grid["frozenColumnCount"] = args.cols
        fields.append("gridProperties.frozenColumnCount")
    if not fields:
        sys.exit("error: provide --rows N and/or --cols N")
    batch_update(token, args.spreadsheet_id, [{"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": grid}, "fields": ",".join(fields)}}])
    print(f"✓ froze {args.rows or 0} rows × {args.cols or 0} cols on {args.tab!r}")
    return 0


def cmd_merge(args, token: str) -> int:
    _, gr = tab_and_grid(token, args.spreadsheet_id, _one_range(args))
    batch_update(token, args.spreadsheet_id, [{"mergeCells": {"range": gr, "mergeType": args.merge_type}}])
    print(f"✓ merged {_one_range(args)} ({args.merge_type})")
    return 0


def cmd_unmerge(args, token: str) -> int:
    _, gr = tab_and_grid(token, args.spreadsheet_id, _one_range(args))
    batch_update(token, args.spreadsheet_id, [{"unmergeCells": {"range": gr}}])
    print(f"✓ unmerged {_one_range(args)}")
    return 0


def _dim_op(args, token: str, op: str, dimension: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.tab)
    if dimension == "ROWS":
        start, end = row_range_to_indices(args.rows)
    else:
        start, end = col_range_to_indices(args.cols)
    dim_range = {"sheetId": sid, "dimension": dimension, "startIndex": start, "endIndex": end}
    if op == "insertDimension":
        inherit = args.inherit or ("before" if start > 0 else "after")
        req = {"insertDimension": {"range": dim_range, "inheritFromBefore": inherit == "before"}}
    else:
        req = {"deleteDimension": {"range": dim_range}}
    batch_update(token, args.spreadsheet_id, [req])
    verb = "inserted" if op == "insertDimension" else "deleted"
    unit = "rows" if dimension == "ROWS" else "cols"
    spec = args.rows if dimension == "ROWS" else args.cols
    print(f"✓ {verb} {unit} {spec} ({end - start}) on {args.tab!r}")
    return 0


def cmd_insert_rows(args, token: str) -> int:
    return _dim_op(args, token, "insertDimension", "ROWS")


def cmd_insert_cols(args, token: str) -> int:
    return _dim_op(args, token, "insertDimension", "COLUMNS")


def cmd_delete_rows(args, token: str) -> int:
    return _dim_op(args, token, "deleteDimension", "ROWS")


def cmd_delete_cols(args, token: str) -> int:
    return _dim_op(args, token, "deleteDimension", "COLUMNS")


# ─── Subcommand: styling ──────────────────────────────────────────────────

_H_ALIGN = {"left": "LEFT", "center": "CENTER", "right": "RIGHT"}
_V_ALIGN = {"top": "TOP", "middle": "MIDDLE", "bottom": "BOTTOM"}


def _build_format(args) -> tuple[dict, list[str]]:
    """(userEnteredFormat, field paths) from --bg/--fg/--bold/... flags.

    Only the properties passed are in the field mask, so `format --bg` keeps
    the cell's existing bold, font, number format and so on.
    """
    cell_fmt: dict = {}
    text_fmt: dict = {}
    fields: list[str] = []
    if args.bg:
        cell_fmt["backgroundColor"] = parse_color(args.bg)
        fields.append("userEnteredFormat.backgroundColor")
    if args.fg:
        text_fmt["foregroundColor"] = parse_color(args.fg)
        fields.append("userEnteredFormat.textFormat.foregroundColor")
    if args.bold is not None:
        text_fmt["bold"] = args.bold
        fields.append("userEnteredFormat.textFormat.bold")
    if args.italic is not None:
        text_fmt["italic"] = args.italic
        fields.append("userEnteredFormat.textFormat.italic")
    if args.font_size:
        text_fmt["fontSize"] = args.font_size
        fields.append("userEnteredFormat.textFormat.fontSize")
    if args.font:
        text_fmt["fontFamily"] = args.font
        fields.append("userEnteredFormat.textFormat.fontFamily")
    if text_fmt:
        cell_fmt["textFormat"] = text_fmt
    if args.align:
        cell_fmt["horizontalAlignment"] = _H_ALIGN[args.align]
        fields.append("userEnteredFormat.horizontalAlignment")
    if args.valign:
        cell_fmt["verticalAlignment"] = _V_ALIGN[args.valign]
        fields.append("userEnteredFormat.verticalAlignment")
    if args.wrap is not None:
        cell_fmt["wrapStrategy"] = "WRAP" if args.wrap else "OVERFLOW_CELL"
        fields.append("userEnteredFormat.wrapStrategy")
    if args.number_format:
        cell_fmt["numberFormat"] = number_format(args.number_format)
        fields.append("userEnteredFormat.numberFormat")
    return cell_fmt, fields


def cmd_format(args, token: str) -> int:
    cell_fmt, fields = _build_format(args)
    if not fields:
        sys.exit("error: nothing to format — pass at least one of --bg/--fg/--bold/...")
    ranges = _ranges(args)
    reqs = []
    for rng in ranges:
        _, gr = tab_and_grid(token, args.spreadsheet_id, rng)
        reqs.append({"repeatCell": {"range": gr, "cell": {"userEnteredFormat": cell_fmt},
                                    "fields": ",".join(fields)}})
    batch_update(token, args.spreadsheet_id, reqs)
    print(f"✓ formatted {', '.join(ranges)}")
    return 0


def cmd_format_header(args, token: str) -> int:
    """Bold + bg/fg on header row N, freeze through it, optional filter — one batch."""
    tab_props = resolve_tab(token, args.spreadsheet_id, args.tab)
    sid = tab_props["sheetId"]
    col_count = tab_props.get("gridProperties", {}).get("columnCount", 26)
    row = args.row - 1
    bg = parse_color(args.bg or "#1a73e8")
    fg = parse_color(args.fg or "#ffffff")
    requests: list[dict] = [{"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": row, "endRowIndex": row + 1,
                  "startColumnIndex": 0, "endColumnIndex": col_count},
        "cell": {"userEnteredFormat": {
            "backgroundColor": bg,
            "textFormat": {"foregroundColor": fg, "bold": True},
            "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE",
        }},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
    }}]
    if args.freeze:
        requests.append({"updateSheetProperties": {
            "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": row + 1}},
            "fields": "gridProperties.frozenRowCount"}})
    if args.filter:
        requests.append({"setBasicFilter": {"filter": {"range": {
            "sheetId": sid, "startRowIndex": row, "startColumnIndex": 0, "endColumnIndex": col_count}}}})
    batch_update(token, args.spreadsheet_id, requests)
    extra = (f" + frozen rows 1-{row + 1}" if args.freeze else "") + (" + filter" if args.filter else "")
    print(f"✓ styled header row {row + 1} of {args.tab!r}{extra}")
    return 0


def cmd_borders(args, token: str) -> int:
    rng = _one_range(args)
    _, gr = tab_and_grid(token, args.spreadsheet_id, rng)
    border = {"style": args.style, "colorStyle": {"rgbColor": parse_color(args.color)}}
    req: dict = {"updateBorders": {"range": gr}}
    sides = ("top", "bottom", "left", "right", "innerHorizontal", "innerVertical")
    if args.all:
        for side in sides:
            req["updateBorders"][side] = border
    else:
        for side, on in (("top", args.top), ("bottom", args.bottom), ("left", args.left), ("right", args.right)):
            if on:
                req["updateBorders"][side] = border
        if args.inner:
            req["updateBorders"]["innerHorizontal"] = border
            req["updateBorders"]["innerVertical"] = border
    if len(req["updateBorders"]) == 1:
        sys.exit("error: specify --all or at least one side (--top --bottom --left --right --inner)")
    batch_update(token, args.spreadsheet_id, [req])
    print(f"✓ borders applied to {rng}")
    return 0


def _banding_request(gr: dict, header_bg: str | None, first_bg: str | None,
                     second_bg: str | None, footer_bg: str | None = None) -> dict:
    row_props = {
        "headerColorStyle": {"rgbColor": parse_color(header_bg or "#1a73e8")},
        "firstBandColorStyle": {"rgbColor": parse_color(first_bg or "#ffffff")},
        "secondBandColorStyle": {"rgbColor": parse_color(second_bg or "#f1f3f4")},
    }
    if footer_bg:
        row_props["footerColorStyle"] = {"rgbColor": parse_color(footer_bg)}
    return {"addBanding": {"bandedRange": {"range": gr, "rowProperties": row_props}}}


def cmd_banding(args, token: str) -> int:
    rng = _one_range(args)
    _, gr = tab_and_grid(token, args.spreadsheet_id, rng)
    batch_update(token, args.spreadsheet_id,
                 [_banding_request(gr, args.header_bg, args.first_bg, args.second_bg, args.footer_bg)])
    print(f"✓ banding applied to {rng}")
    return 0


def cmd_conditional_format(args, token: str) -> int:
    rng = _one_range(args)
    _, gr = tab_and_grid(token, args.spreadsheet_id, rng)
    if args.rule:
        rule = load_json_arg(args.rule)
        rule.setdefault("ranges", [gr])
    else:
        no_value = ("BLANK", "NOT_BLANK", "TEXT_IS_EMAIL", "TEXT_IS_URL")
        if not (args.condition and (args.value is not None or args.condition in no_value)):
            sys.exit("error: provide either --rule '@rule.json' OR "
                     "--condition <TYPE> [--value V] with at least one of --bg/--fg/--bold")
        condition: dict = {"type": args.condition}
        if args.value is not None:
            condition["values"] = [{"userEnteredValue": v} for v in args.value]
        fmt: dict = {}
        if args.bg:
            fmt["backgroundColor"] = parse_color(args.bg)
        text_fmt: dict = {}
        if args.fg:
            text_fmt["foregroundColor"] = parse_color(args.fg)
        if args.bold:
            text_fmt["bold"] = True
        if text_fmt:
            fmt["textFormat"] = text_fmt
        if not fmt:
            sys.exit("error: provide at least one of --bg/--fg/--bold for the format")
        rule = {"ranges": [gr], "booleanRule": {"condition": condition, "format": fmt}}
    batch_update(token, args.spreadsheet_id, [{"addConditionalFormatRule": {"rule": rule, "index": args.index}}])
    print(f"✓ conditional format added to {rng} (each call adds a rule; see inspect to list them)")
    return 0


def cmd_validation(args, token: str) -> int:
    """Dropdowns, checkboxes and list-from-range validation (setDataValidation)."""
    rng = _one_range(args)
    _, gr = tab_and_grid(token, args.spreadsheet_id, rng)
    req: dict = {"setDataValidation": {"range": gr}}
    if not args.clear:
        if args.one_of:
            items = next(csv.reader([args.one_of]))
            cond = {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v.strip()} for v in items]}
        elif args.one_of_range:
            ref = args.one_of_range if args.one_of_range.startswith("=") else "=" + args.one_of_range
            cond = {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": ref}]}
        elif args.checkbox:
            cond = {"type": "BOOLEAN"}
        elif args.formula:
            cond = {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": args.formula}]}
        else:
            sys.exit("error: pass --one-of, --one-of-range, --checkbox, --formula or --clear")
        rule: dict = {"condition": cond, "strict": args.strict, "showCustomUi": not args.no_dropdown}
        if args.help_text:
            rule["inputMessage"] = args.help_text
        req["setDataValidation"]["rule"] = rule
    batch_update(token, args.spreadsheet_id, [req])
    print(f"✓ {'cleared validation on' if args.clear else 'validation set on'} {rng}")
    return 0


def cmd_note(args, token: str) -> int:
    rng = _one_range(args)
    _, gr = tab_and_grid(token, args.spreadsheet_id, rng)
    note = "" if args.clear else args.text
    if note is None:
        sys.exit("error: pass --text TEXT or --clear")
    batch_update(token, args.spreadsheet_id, [{"repeatCell": {
        "range": gr, "cell": {"note": note}, "fields": "note"}}])
    print(f"✓ {'cleared note on' if args.clear else 'note set on'} {rng}")
    return 0


_PASTE_TYPES = {
    "format": "PASTE_FORMAT", "validation": "PASTE_DATA_VALIDATION",
    "conditional": "PASTE_CONDITIONAL_FORMATTING", "values": "PASTE_VALUES",
    "formulas": "PASTE_FORMULA", "all": "PASTE_NORMAL", "no-borders": "PASTE_NO_BORDERS",
}


def cmd_copy_format(args, token: str) -> int:
    """copyPaste from one range to another (format by default); the source
    repeats to fill a larger destination."""
    _, src = tab_and_grid(token, args.spreadsheet_id, getattr(args, "from"))
    _, dst = tab_and_grid(token, args.spreadsheet_id, args.to)
    batch_update(token, args.spreadsheet_id, [{"copyPaste": {
        "source": src, "destination": dst,
        "pasteType": _PASTE_TYPES[args.what], "pasteOrientation": "NORMAL"}}])
    print(f"✓ copied {args.what} {getattr(args, 'from')} → {args.to}")
    return 0


def _cell_value(v: Any) -> dict:
    """Typed CellData.userEnteredValue for updateCells (no parsing by Sheets)."""
    if v is None:
        return {}
    if isinstance(v, bool):
        return {"userEnteredValue": {"boolValue": v}}
    if isinstance(v, (int, float)):
        return {"userEnteredValue": {"numberValue": v}}
    s = str(v)
    if s.startswith("="):
        return {"userEnteredValue": {"formulaValue": s}}
    return {"userEnteredValue": {"stringValue": s}}


def cmd_table(args, token: str) -> int:
    """Write a header + rows and lay out the table: header style, freeze,
    filter, per-column number formats, widths, wrap, banding. --replace
    resets the tab first; --create adds it if missing; the grid grows to fit.

    Typed input (default for JSON) is ONE atomic batchUpdate. User-entered
    input (default for CSV) needs a values write in between, so it runs as:
    grow the grid + reset formatting → write values (parsed against clean
    formats) → lay out → clear the old values outside the new table. No old
    value is cleared before the new values are in, so a failure part-way
    never leaves the tab empty.
    """
    values = load_values(args)
    if not values:
        sys.exit("error: no rows to write")
    meta = get_spreadsheet(token, args.spreadsheet_id)
    tabs = {s["properties"]["title"]: s["properties"] for s in meta.get("sheets", [])}
    exists = args.tab in tabs
    if not exists and not args.create:
        sys.exit(f"error: tab {args.tab!r} not found (pass --create to add it). available: {list(tabs)}")

    sr, _, sc, _ = range_bounds(args.at)
    r0, c0 = sr or 0, sc or 0
    height = len(values)
    width = max(len(r) for r in values)
    need_rows, need_cols = r0 + height, c0 + width
    hdr = args.header_rows
    mode = args.input or ("user-entered" if args.csv or args.values_stdin else "typed")

    # 1. Grid: add the tab, or grow it, so every write below fits.
    grow: list[dict] = []
    if exists:
        sid = tabs[args.tab]["sheetId"]
        grid = tabs[args.tab].get("gridProperties", {})
        rows, cols = grid.get("rowCount", 1000), grid.get("columnCount", 26)
        if rows < need_rows:
            grow.append({"appendDimension": {"sheetId": sid, "dimension": "ROWS", "length": need_rows - rows}})
        if cols < need_cols:
            grow.append({"appendDimension": {"sheetId": sid, "dimension": "COLUMNS", "length": need_cols - cols}})
        rows, cols = max(rows, need_rows), max(cols, need_cols)
    else:
        sid = max({p["sheetId"] for p in tabs.values()} | {0}) + 1
        rows, cols = max(1000, need_rows), max(26, need_cols)
        grow.append({"addSheet": {"properties": {"sheetId": sid, "title": args.tab,
                                                 "gridProperties": {"rowCount": rows, "columnCount": cols}}}})

    table = {"sheetId": sid, "startRowIndex": r0, "endRowIndex": need_rows,
             "startColumnIndex": c0, "endColumnIndex": need_cols}

    # 2. Reset (--replace): formatting, merges, notes, validation, banding, rules, filter.
    reset: list[dict] = []
    if args.replace and exists:
        fields = "sheets(properties(sheetId,title),bandedRanges(bandedRangeId),conditionalFormats,basicFilter)"
        qs = urllib.parse.urlencode({"ranges": quote_tab(args.tab), "fields": fields})
        full = api(token, "GET", f"{SHEETS_BASE}/{args.spreadsheet_id}?{qs}")["sheets"][0]
        reset.append({"unmergeCells": {"range": {"sheetId": sid}}})
        cleared = "userEnteredFormat,note,dataValidation"
        if mode == "typed":
            cleared = "userEnteredValue," + cleared  # the typed write below lands in the same batch
        reset.append({"updateCells": {"range": {"sheetId": sid}, "fields": cleared}})
        if full.get("basicFilter"):
            reset.append({"clearBasicFilter": {"sheetId": sid}})
        for b in full.get("bandedRanges", []) or []:
            reset.append({"deleteBanding": {"bandedRangeId": b["bandedRangeId"]}})
        for i in reversed(range(len(full.get("conditionalFormats", []) or []))):
            reset.append({"deleteConditionalFormatRule": {"sheetId": sid, "index": i}})

    # 3. Layout.
    layout: list[dict] = []
    if hdr:
        layout.append({"repeatCell": {
            "range": {**table, "endRowIndex": r0 + hdr},
            "cell": {"userEnteredFormat": {
                "backgroundColor": parse_color(args.header_bg),
                "textFormat": {"foregroundColor": parse_color(args.header_fg), "bold": True},
                "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP",
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,wrapStrategy)",
        }})
    data_rows = {**table, "startRowIndex": r0 + hdr}
    if args.wrap:
        layout.append({"repeatCell": {
            "range": data_rows,
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}})
    for spec in args.col_format or []:
        col_spec, _, pattern = spec.partition("=")
        if not pattern:
            sys.exit(f"error: --col-format wants COLS=PATTERN, e.g. 'D:F=#,##0.00' (got {spec!r})")
        a, b = col_range_to_indices(col_spec)
        layout.append({"repeatCell": {
            "range": {**data_rows, "startColumnIndex": a, "endColumnIndex": b},
            "cell": {"userEnteredFormat": {"numberFormat": number_format(pattern)}},
            "fields": "userEnteredFormat.numberFormat"}})
    freeze = args.freeze if args.freeze is not None else (r0 == 0 and hdr > 0)
    if freeze or args.freeze_cols:
        gp, gf = {}, []
        if freeze:
            gp["frozenRowCount"] = r0 + hdr
            gf.append("gridProperties.frozenRowCount")
        if args.freeze_cols:
            gp["frozenColumnCount"] = args.freeze_cols
            gf.append("gridProperties.frozenColumnCount")
        layout.append({"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": gp},
                                                 "fields": ",".join(gf)}})
    filt_start = r0 + max(hdr - 1, 0)
    if args.filter:
        layout.append({"setBasicFilter": {"filter": {"range": {**table, "startRowIndex": filt_start}}}})
    if args.banding:
        layout.append(_banding_request({**table, "startRowIndex": filt_start}, args.header_bg, None, args.band_bg))
    if args.widths:
        for k, px in enumerate(int(x) for x in args.widths.split(",")):
            layout.append({"updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": c0 + k, "endIndex": c0 + k + 1},
                "properties": {"pixelSize": px}, "fields": "pixelSize"}})
    elif args.auto_width:
        layout.append({"autoResizeDimensions": {"dimensions": {
            "sheetId": sid, "dimension": "COLUMNS", "startIndex": c0, "endIndex": need_cols}}})

    q = quote_tab(args.tab)
    a1 = f"{q}!{grid_to_a1(table)}"
    if mode == "typed":
        write = {"updateCells": {
            "start": {"sheetId": sid, "rowIndex": r0, "columnIndex": c0},
            "rows": [{"values": [_cell_value(v) for v in row]} for row in values],
            "fields": "userEnteredValue",
        }}
        reqs = grow + reset + [write] + layout
        batch_update(token, args.spreadsheet_id, reqs)
        print(f"✓ table {a1}: {height - hdr} rows + {hdr} header row(s), typed values and layout in one "
              f"atomic batch ({len(reqs)} requests)")
        return 0

    # User-entered: values have to go through values.update.
    outside: list[str] = []
    if args.replace and exists:
        L = col_index_to_letter
        if rows > need_rows:
            outside.append(f"{q}!A{need_rows + 1}:{L(cols - 1)}{rows}")
        if cols > need_cols:
            outside.append(f"{q}!{L(need_cols)}1:{L(cols - 1)}{need_rows}")
        if r0 > 0:
            outside.append(f"{q}!{L(c0)}1:{L(need_cols - 1)}{r0}")
        if c0 > 0:
            outside.append(f"{q}!A1:{L(c0 - 1)}{need_rows}")
    start = f"{q}!{col_index_to_letter(c0)}{r0 + 1}"
    if DRY_RUN:
        print(json.dumps({"steps": [
            {"batchUpdate": {"requests": grow + reset}},
            {"PUT values": {"range": start, "valueInputOption": "USER_ENTERED", "values": values}},
            {"batchUpdate": {"requests": layout}},
            {"values:batchClear": {"ranges": outside}},
        ]}, indent=2, ensure_ascii=False))
        raise DryRun()
    batch_update(token, args.spreadsheet_id, grow + reset)
    api(token, "PUT", f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{urllib.parse.quote(start, safe='')}"
                      f"?valueInputOption=USER_ENTERED",
        {"range": start, "majorDimension": "ROWS", "values": values})
    batch_update(token, args.spreadsheet_id, layout)
    if outside:
        api(token, "POST", f"{SHEETS_BASE}/{args.spreadsheet_id}/values:batchClear", {"ranges": outside},
            idempotent=True)
    print(f"✓ table {a1}: {height - hdr} rows + {hdr} header row(s), user-entered values, then "
          f"{len(reset) + len(layout)} layout requests" + (", old values outside cleared" if outside else ""))
    return 0


# ─── Subcommand: inspect / export ─────────────────────────────────────────

def _runs(cells: dict[tuple[int, int], Any], col_count: int) -> list[dict]:
    """Group equal per-cell values into vertical runs: [{"range": "C2:C40", "value": v}]."""
    by_col: dict[int, list[tuple[int, Any]]] = {}
    for (r, c), v in cells.items():
        by_col.setdefault(c, []).append((r, v))
    out = []
    for c in sorted(by_col):
        items = sorted(by_col[c], key=lambda x: x[0])
        start, prev_r, prev_v = items[0][0], items[0][0], items[0][1]
        for r, v in items[1:] + [(None, None)]:
            if r is not None and r == prev_r + 1 and v == prev_v:
                prev_r = r
                continue
            L = col_index_to_letter(c)
            out.append({"range": f"{L}{start + 1}" if start == prev_r else f"{L}{start + 1}:{L}{prev_r + 1}",
                        "value": prev_v})
            if r is not None:
                start, prev_r, prev_v = r, r, v
    return out


def _hexify(obj: Any) -> Any:
    """Readable colors: {red, green, blue} → '#rrggbb'; drop the *Style twins."""
    if isinstance(obj, dict):
        if set(obj) <= {"red", "green", "blue", "alpha"} and obj:
            return "#" + "".join(f"{round(obj.get(c, 0) * 255):02x}" for c in ("red", "green", "blue"))
        return {k: _hexify(v) for k, v in obj.items()
                if not (k.endswith("ColorStyle") and k[:-5] in obj)}
    if isinstance(obj, list):
        return [_hexify(v) for v in obj]
    return obj


def cmd_inspect(args, token: str) -> int:
    """Everything about a tab that `read` can't show: widths, merges,
    conditional formats, validation, banding, filters, groups, charts,
    protected ranges; with --cells, per-cell number formats, notes and
    validation rules for a range."""
    tab = args.tab
    fields = ("sheets(properties,merges,conditionalFormats,bandedRanges,basicFilter,filterViews,"
              "protectedRanges,rowGroups,columnGroups,charts(chartId,spec(title,basicChart(domains,series),"
              "pieChart(domain,series))),data(columnMetadata(pixelSize,hiddenByUser,hiddenByFilter)))")
    qs = urllib.parse.urlencode({"ranges": quote_tab(tab), "fields": fields})
    sh = api(token, "GET", f"{SHEETS_BASE}/{args.spreadsheet_id}?{qs}")["sheets"][0]
    p = sh["properties"]
    g = p.get("gridProperties", {})
    ncols = g.get("columnCount", 26)
    a1 = lambda gr: grid_to_a1(gr, ncols)  # noqa: E731

    cols_meta = []
    data = sh.get("data") or [{}]
    for i, cm in enumerate(data[0].get("columnMetadata", []) or []):
        cols_meta.append({"col": col_index_to_letter(i), "width": cm.get("pixelSize"),
                          **({"hidden": True} if cm.get("hiddenByUser") else {})})

    def sources(obj: Any) -> list[str]:
        found = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "sources" and isinstance(v, list):
                    found += [a1(s) for s in v]
                else:
                    found += sources(v)
        elif isinstance(obj, list):
            for v in obj:
                found += sources(v)
        return found

    out: dict = {
        "tab": p.get("title"), "sheetId": p.get("sheetId"), "index": p.get("index"),
        "hidden": p.get("hidden", False), "rightToLeft": p.get("rightToLeft", False),
        "rowCount": g.get("rowCount"), "columnCount": ncols,
        "frozenRows": g.get("frozenRowCount", 0), "frozenCols": g.get("frozenColumnCount", 0),
        "columns": cols_meta,
        "merges": [a1(m) for m in sorted(sh.get("merges", []) or [],
                                         key=lambda m: (m.get("startRowIndex", 0), m.get("startColumnIndex", 0)))],
        "conditionalFormats": [
            {"index": i, "ranges": [a1(r) for r in cf.get("ranges", [])],
             **({"booleanRule": cf["booleanRule"]} if "booleanRule" in cf else {}),
             **({"gradientRule": cf["gradientRule"]} if "gradientRule" in cf else {})}
            for i, cf in enumerate(sh.get("conditionalFormats", []) or [])
        ],
        "bandedRanges": [{"id": b.get("bandedRangeId"), "range": a1(b.get("range", {}))}
                         for b in sh.get("bandedRanges", []) or []],
        "basicFilter": a1(sh["basicFilter"]["range"]) if sh.get("basicFilter") else None,
        "filterViews": [{"id": f.get("filterViewId"), "title": f.get("title"), "range": a1(f.get("range", {}))}
                        for f in sh.get("filterViews", []) or []],
        "protectedRanges": [{"id": pr.get("protectedRangeId"), "range": a1(pr.get("range", {})),
                             "description": pr.get("description"), "warningOnly": pr.get("warningOnly", False)}
                            for pr in sh.get("protectedRanges", []) or []],
        "rowGroups": [{"rows": f"{d['range'].get('startIndex', 0) + 1}:{d['range'].get('endIndex')}",
                       "depth": d.get("depth"), "collapsed": d.get("collapsed", False)}
                      for d in sh.get("rowGroups", []) or []],
        "columnGroups": [{"cols": f"{col_index_to_letter(d['range'].get('startIndex', 0))}:"
                                  f"{col_index_to_letter(d['range'].get('endIndex', 1) - 1)}",
                          "depth": d.get("depth"), "collapsed": d.get("collapsed", False)}
                         for d in sh.get("columnGroups", []) or []],
        "charts": [{"chartId": c.get("chartId"), "title": (c.get("spec") or {}).get("title"),
                    "sources": sources(c.get("spec"))} for c in sh.get("charts", []) or []],
    }

    if args.cells:
        rng = f"{quote_tab(tab)}!{args.cells}"
        cfields = ("sheets(data(startRow,startColumn,rowData(values(note,dataValidation,"
                   "userEnteredFormat(numberFormat,backgroundColor,textFormat(bold),horizontalAlignment,wrapStrategy)))))")
        qs = urllib.parse.urlencode({"ranges": rng, "includeGridData": "true", "fields": cfields})
        grid = api(token, "GET", f"{SHEETS_BASE}/{args.spreadsheet_id}?{qs}")["sheets"][0]["data"][0]
        r0, c0 = grid.get("startRow", 0), grid.get("startColumn", 0)
        notes, validation, formats = [], {}, {}
        for i, row in enumerate(grid.get("rowData", []) or []):  # rowData is absent on empty, unformatted ranges
            for j, cell in enumerate(row.get("values", []) or []):
                pos = (r0 + i, c0 + j)
                if cell.get("note"):
                    notes.append({"cell": f"{col_index_to_letter(pos[1])}{pos[0] + 1}", "note": cell["note"]})
                if cell.get("dataValidation"):
                    validation[pos] = cell["dataValidation"]
                if cell.get("userEnteredFormat"):
                    formats[pos] = cell["userEnteredFormat"]
        out["cells"] = {
            "range": args.cells,
            "notes": notes,
            "dataValidation": _runs(validation, ncols),
            "formats": _runs(formats, ncols),
        }
    print(json.dumps(out if args.raw else _hexify(out), indent=2, ensure_ascii=False))
    return 0


def cmd_export(args, token: str) -> int:
    """Download a tab (or range) as pdf / xlsx / csv / png for visual QA."""
    fmt = args.format
    params: list[tuple[str, str]] = [("format", "pdf" if fmt == "png" else fmt)]
    if args.tab:
        params.append(("gid", str(resolve_tab_id(token, args.spreadsheet_id, args.tab))))
    if args.cells:
        if not args.tab:
            sys.exit("error: --cells needs --tab")
        params.append(("range", args.cells))
    if fmt in ("pdf", "png"):
        params += [("portrait", "false" if args.landscape else "true"), ("fitw", "true"),
                   ("gridlines", "true" if args.gridlines else "false"),
                   ("sheetnames", "false"), ("printtitle", "false"), ("pagenumbers", "false")]
    url = f"https://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/export?{urllib.parse.urlencode(params)}"
    data = api(token, "GET", url, raw=True)
    out = Path(args.out).expanduser()
    if fmt != "png":
        out.write_bytes(data)
        print(f"✓ exported {fmt} → {out} ({len(data):,} bytes)")
        return 0
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "export.pdf"
        pdf.write_bytes(data)
        if shutil.which("pdftoppm"):
            subprocess.run(["pdftoppm", "-png", "-r", "110", "-singlefile", str(pdf), str(out.with_suffix(""))],
                           check=True)
        elif shutil.which("sips"):
            subprocess.run(["sips", "-s", "format", "png", str(pdf), "--out", str(out)],
                           check=True, capture_output=True)
        else:
            sys.exit("error: png needs pdftoppm (poppler) or macOS sips; use --format pdf instead")
    print(f"✓ exported page 1 as png → {out}")
    return 0


# ─── Subcommand: filter / sort ────────────────────────────────────────────

def cmd_add_filter(args, token: str) -> int:
    rng = _one_range(args)
    _, gr = tab_and_grid(token, args.spreadsheet_id, rng)
    batch_update(token, args.spreadsheet_id, [{"setBasicFilter": {"filter": {"range": gr}}}])
    print(f"✓ basic filter set on {rng}")
    return 0


def cmd_clear_filter(args, token: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.tab)
    batch_update(token, args.spreadsheet_id, [{"clearBasicFilter": {"sheetId": sid}}])
    print(f"✓ filter cleared on {args.tab!r}")
    return 0


def cmd_sort(args, token: str) -> int:
    rng = _one_range(args)
    _, gr = tab_and_grid(token, args.spreadsheet_id, rng)
    specs = []
    for spec in args.by.split(","):
        col, _, order = spec.strip().partition(":")
        order = (order or "asc").lower()
        if order not in ("asc", "desc"):
            sys.exit(f"error: invalid sort order {order!r} (use asc or desc)")
        specs.append({"dimensionIndex": col_letter_to_index(col),
                      "sortOrder": "ASCENDING" if order == "asc" else "DESCENDING"})
    batch_update(token, args.spreadsheet_id, [{"sortRange": {"range": gr, "sortSpecs": specs}}])
    print(f"✓ sorted {rng} by {args.by}")
    return 0


# ─── Subcommand: batch-update (escape hatch) ──────────────────────────────

# Requests whose "range"/"source"/"dimensions" fields are DimensionRanges.
_DIMENSION_REQUESTS = {
    "insertDimension", "deleteDimension", "updateDimensionProperties", "addDimensionGroup",
    "deleteDimensionGroup", "updateDimensionGroup", "moveDimension", "autoResizeDimensions",
    "appendDimension",
}
_RANGE_KEYS = {"range", "source", "destination", "dimensions"}


def translate_a1(token: str, spreadsheet_id: str, requests: list[dict]) -> list[dict]:
    """Let raw requests use A1 strings: "range": "Tab!A1:C3" becomes a
    GridRange (a DimensionRange inside dimension requests), "ranges": [..]
    becomes GridRanges, "sheetId": "Tab" becomes the numeric id, and
    "backgroundColor": "#1a73e8" (any *Color / *ColorStyle) becomes RGB."""
    def sid_of(title: str) -> int:
        return resolve_tab_id(token, spreadsheet_id, title)

    def conv(a1: str, dim: bool) -> dict:
        tab, rng = parse_a1(a1)
        if not tab:
            sys.exit(f"error: A1 range in --requests needs a tab prefix: {a1!r}")
        sid = sid_of(tab)
        if not rng:
            return {"sheetId": sid}
        return a1_to_dimension_range(a1, sid) if dim else a1_to_grid_range(a1, sid)

    def coord(a1: str) -> dict:
        gr = conv(a1, False)
        return {"sheetId": gr["sheetId"], "rowIndex": gr.get("startRowIndex", 0),
                "columnIndex": gr.get("startColumnIndex", 0)}

    def walk(obj: Any, dim: bool, kind: str = "") -> Any:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if kind == "cutPaste" and k == "destination" and isinstance(v, str):
                    out[k] = coord(v)  # cutPaste pastes at a GridCoordinate, not a GridRange
                elif k in _RANGE_KEYS and isinstance(v, str):
                    out[k] = conv(v, dim)
                elif k == "ranges" and isinstance(v, list) and all(isinstance(x, str) for x in v):
                    out[k] = [conv(x, False) for x in v]
                elif k == "sheetId" and isinstance(v, str) and not v.lstrip("-").isdigit():
                    out[k] = sid_of(v)
                elif k.lower().endswith("color") and isinstance(v, str) and v.startswith("#"):
                    out[k] = parse_color(v)
                elif k.lower().endswith("colorstyle") and isinstance(v, str) and v.startswith("#"):
                    out[k] = {"rgbColor": parse_color(v)}
                else:
                    out[k] = walk(v, dim, kind)
            return out
        if isinstance(obj, list):
            return [walk(v, dim, kind) for v in obj]
        return obj

    return [{k: walk(v, k in _DIMENSION_REQUESTS, k) for k, v in req.items()} for req in requests]


def cmd_batch_update(args, token: str) -> int:
    payload = load_json_arg(args.requests)
    if isinstance(payload, dict) and "requests" in payload:
        requests = payload["requests"]
    elif isinstance(payload, list):
        requests = payload
    else:
        sys.exit("error: --requests must be a JSON array OR an object with a 'requests' key")
    requests = translate_a1(token, args.spreadsheet_id, requests)
    resp = batch_update(token, args.spreadsheet_id, requests)
    if args.full:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return 0
    replies = resp.get("replies", [])
    for i, (req, rep) in enumerate(zip(requests, replies)):
        if rep:
            print(f"  [{i}] {next(iter(req))}: {json.dumps(rep, ensure_ascii=False)[:400]}")
    print(f"✓ batch-update: {len(requests)} requests applied atomically "
          f"({sum(1 for r in replies if r)} returned data; --full prints the raw reply)")
    return 0


# ─── argparse wiring ──────────────────────────────────────────────────────

def _common_parent() -> argparse.ArgumentParser:
    """Flags accepted both before and after the subcommand."""
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--sa-key", default=argparse.SUPPRESS,
                   help=f"Service-account JSON key (default: ${SA_KEY_ENV}, then ~/.config/gdoc-sync/sa-key.json)")
    p.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS,
                   help="Print the request(s) a write would send, then stop")
    return p


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("spreadsheet_id", help="Spreadsheet ID (from the URL)")


def _add_range(p: argparse.ArgumentParser, many: bool = False) -> None:
    p.add_argument("range_pos", nargs="*" if many else "?", metavar="RANGE",
                   help="A1 range like 'Tab!A1:C10' (or use --range)")
    if many:
        p.add_argument("--range", action="append", help="A1 range; repeat for several")
    else:
        p.add_argument("--range", help="A1 range like 'Tab!A1:C10'")


def _add_values_input(p: argparse.ArgumentParser, required: bool = True) -> None:
    g = p.add_mutually_exclusive_group(required=required)
    g.add_argument("--values-json", help="JSON 2D array (inline or @file.json); null leaves a cell untouched")
    g.add_argument("--csv", help="CSV file path")
    g.add_argument("--values-stdin", action="store_true", help="Read CSV from stdin")


def _add_value_input_option(p: argparse.ArgumentParser) -> None:
    p.add_argument("--value-input-option", dest="value_input_option", default="USER_ENTERED",
                   type=str.upper, choices=["RAW", "USER_ENTERED"],
                   help="USER_ENTERED (default) parses numbers, dates and formulas like typing; "
                        "RAW stores strings as-is (keeps leading zeros and long IDs)")


def _add_guard_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--expect", help="Compare-and-set: JSON (inline or @file) of the values you expect there "
                                    "now, e.g. a saved `read`; the write is refused (exit 3) if any differ")
    p.add_argument("--expect-render", default="FORMATTED_VALUE",
                   help="How --expect values are compared: formatted (default), unformatted or formula")
    p.add_argument("--skip-empty", action="store_true",
                   help="Treat \"\" as null: leave those cells untouched (protects formula columns)")
    p.add_argument("--verify", action="store_true",
                   help="Read back after writing; exit 4 on dropped leading zeros, IDs turned into numbers, or formula errors")


def _add_format_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--bg", help="Background color, hex (#RRGGBB)")
    p.add_argument("--fg", help="Text color, hex")
    p.add_argument("--bold", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--italic", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--font-size", type=int)
    p.add_argument("--font", help="Font family, e.g. 'Roboto', 'Arial'")
    p.add_argument("--align", choices=["left", "center", "right"])
    p.add_argument("--valign", choices=["top", "middle", "bottom"])
    p.add_argument("--wrap", action=argparse.BooleanOptionalAction, default=None,
                   help="--wrap sets WRAP; --no-wrap sets OVERFLOW_CELL")
    p.add_argument("--number-format",
                   help="Pattern like '#,##0.00', '0.0%%', '\"$\"#,##0', 'yyyy-mm-dd' or TEXT; type is inferred")


def build_parser() -> argparse.ArgumentParser:
    parent = _common_parent()
    p = argparse.ArgumentParser(prog="gsheets", description=__doc__, parents=[parent],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<command>")

    def add(name: str, help_: str, func) -> argparse.ArgumentParser:
        s = sub.add_parser(name, help=help_, parents=[parent])
        _add_common(s)
        s.set_defaults(func=func)
        return s

    # ── meta ──
    add("info", "Spreadsheet title, owner, last editor, tabs (safe probe)", cmd_info)
    s = add("revisions", "Recent Drive revisions: who edited and when", cmd_revisions)
    s.add_argument("--limit", type=int, default=20)

    # ── data ──
    s = add("read", "Read range(s) as JSON (bare 2D array for one range)", cmd_read)
    _add_range(s, many=True)
    s.add_argument("--all-tabs", action="store_true", help="Read every tab; JSON object keyed by tab title")
    s.add_argument("--value-render", "--render", dest="value_render", default="FORMATTED_VALUE",
                   help="formatted (default, what the UI shows), unformatted (raw numbers) or formula")
    s.add_argument("--major-dimension", choices=["ROWS", "COLUMNS"])
    s.add_argument("--pad", action="store_true",
                   help="Rectangular rows: pad trailing blanks (and rows, if the range is bounded)")
    s.add_argument("--fill-merged", action="store_true", help="Copy merged cells' value into every covered cell")
    s.add_argument("--header-rows", type=int, default=0,
                   help="Emit rows as records keyed by these header rows (merged headers filled), with _row")
    s.add_argument("--numbered", action="store_true", help="Emit [{\"_row\": N, \"values\": [...]}]")

    s = add("headers", "List column letters with their (merge-filled) header text", cmd_headers)
    s.add_argument("--tab", required=True)
    s.add_argument("--header-rows", type=int, default=1)
    s.add_argument("--within", help="Limit to a range of the tab, e.g. A1:BZ2")
    s.add_argument("--value-render", "--render", dest="value_render", default="FORMATTED_VALUE")

    s = add("find", "Find rows by a cell's content; prints row numbers and A1 cells", cmd_find)
    s.add_argument("--tab", required=True)
    s.add_argument("--col", help="Column(s) to search, e.g. A or A,C (default: all)")
    s.add_argument("--col-header", help="Search only columns whose header contains this, e.g. 'AWS / prod'")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--value", help="Exact match (trimmed)")
    g.add_argument("--contains", help="Case-insensitive substring")
    g.add_argument("--regex", help="Python regex")
    s.add_argument("--within", help="Limit to a range of the tab, e.g. A1:BZ500")
    s.add_argument("--header-rows", type=int, default=0, help="Skip and use these rows as the header")
    s.add_argument("--show", help="With --header-rows: list each hit's cells whose header contains this "
                                  "(their A1 addresses and values)")
    s.add_argument("--record", action=argparse.BooleanOptionalAction, default=None,
                   help="Include the whole row (default: on, off when --show is given)")
    s.add_argument("--value-render", "--render", dest="value_render", default="FORMATTED_VALUE")

    s = add("write", "Overwrite a range with values", cmd_write)
    _add_range(s)
    _add_value_input_option(s)
    _add_values_input(s)
    _add_guard_flags(s)

    s = add("batch-write", "Write many ranges in one call (values:batchUpdate)", cmd_batch_write)
    s.add_argument("--data", required=True,
                   help='{"Tab!A1": [[...]], "Other!C3": [["x"]]} inline or @file.json')
    _add_value_input_option(s)
    _add_guard_flags(s)

    s = add("append", "Append rows after the table the range points at", cmd_append)
    _add_range(s)
    _add_value_input_option(s)
    s.add_argument("--insert-data-option", default="INSERT_ROWS", choices=["OVERWRITE", "INSERT_ROWS"])
    s.add_argument("--skip-empty", action="store_true", help="Treat \"\" as null")
    _add_values_input(s)

    s = add("clear", "Clear values (keeps formatting unless --formats/--all)", cmd_clear)
    _add_range(s)
    s.add_argument("--formats", action="store_true", help="Also clear formatting")
    s.add_argument("--all", action="store_true", help="Clear values, formatting, notes and validation")

    # ── tabs ──
    add("list-tabs", "List tabs with sheetId and dimensions", cmd_list_tabs)
    s = add("add-tab", "Add a tab", cmd_add_tab)
    s.add_argument("--title", required=True)
    s.add_argument("--rows", type=int, help="Initial row count (default 1000)")
    s.add_argument("--cols", type=int, help="Initial column count (default 26)")
    s.add_argument("--index", type=int, help="Tab position (0 = first)")
    s.add_argument("--sheet-id", type=int, help="Fixed numeric sheetId (handy for later GridRanges)")
    s.add_argument("--color", help="Tab color, hex")
    s.add_argument("--rtl", action="store_true", help="Right-to-left tab (Hebrew/Arabic)")
    s = add("delete-tab", "Delete a tab by title", cmd_delete_tab)
    s.add_argument("--title", required=True)
    s = add("rename-tab", "Rename a tab", cmd_rename_tab)
    s.add_argument("--from", required=True, dest="from")
    s.add_argument("--to", required=True)
    s = add("duplicate-tab", "Duplicate a tab", cmd_duplicate_tab)
    s.add_argument("--from", required=True, dest="from")
    s.add_argument("--to", required=True, help="Name for the copy")
    s.add_argument("--index", type=int)
    s = add("move-tab", "Move a tab to a position", cmd_move_tab)
    s.add_argument("--title", required=True)
    s.add_argument("--index", type=int, required=True, help="0 = first")
    s = add("set-title", "Rename the spreadsheet file", cmd_set_title)
    s.add_argument("--title", required=True)

    # ── structure ──
    s = add("resize-cols", "Set column widths or autoresize", cmd_resize_cols)
    s.add_argument("--tab", required=True)
    s.add_argument("--cols", required=True, help="Column range like 'A:C' or 'B'")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--width", type=int, help="One width in pixels for every column")
    g.add_argument("--widths", help="Comma list, one per column from the first: '40,180,90'")
    g.add_argument("--auto", action="store_true", help="Fit to the widest cell, including long note rows")
    s = add("resize-rows", "Set row heights or autoresize", cmd_resize_rows)
    s.add_argument("--tab", required=True)
    s.add_argument("--rows", required=True, help="Row range like '1:3' or '5'")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--height", type=int)
    g.add_argument("--auto", action="store_true")
    s = add("freeze", "Freeze the first N rows and/or M columns", cmd_freeze)
    s.add_argument("--tab", required=True)
    s.add_argument("--rows", type=int, help="Rows to freeze (0 unfreezes)")
    s.add_argument("--cols", type=int, help="Columns to freeze")
    s = add("merge", "Merge cells in a range", cmd_merge)
    _add_range(s)
    s.add_argument("--merge-type", default="MERGE_ALL", choices=["MERGE_ALL", "MERGE_COLUMNS", "MERGE_ROWS"])
    s = add("unmerge", "Unmerge cells in a range", cmd_unmerge)
    _add_range(s)
    for name, fn, unit in (("insert-rows", cmd_insert_rows, "rows"), ("delete-rows", cmd_delete_rows, "rows"),
                           ("insert-cols", cmd_insert_cols, "cols"), ("delete-cols", cmd_delete_cols, "cols")):
        s = add(name, name.replace("-", " ").capitalize(), fn)
        s.add_argument("--tab", required=True)
        s.add_argument(f"--{unit}", required=True,
                       help="Rows like '5:7' (1-based, inclusive)" if unit == "rows" else "Cols like 'B:D'")
        if name.startswith("insert"):
            s.add_argument("--inherit", choices=["before", "after"],
                           help="Copy formatting from the row/col before (default when not first) or after")

    # ── styling ──
    s = add("format", "Format range(s): colors, bold, font, align, wrap, number format", cmd_format)
    _add_range(s, many=True)
    _add_format_flags(s)
    s = add("format-header", "Style a header row (bold, colors), freeze through it, optional filter",
            cmd_format_header)
    s.add_argument("--tab", required=True)
    s.add_argument("--row", type=int, default=1, help="Header row number (default 1)")
    s.add_argument("--bg", help="Header background (default #1a73e8)")
    s.add_argument("--fg", help="Header text color (default #ffffff)")
    s.add_argument("--freeze", action=argparse.BooleanOptionalAction, default=True,
                   help="Freeze rows 1..ROW (default on)")
    s.add_argument("--filter", action="store_true", help="Also add a basic filter from the header row")
    s = add("borders", "Set borders on a range", cmd_borders)
    _add_range(s)
    s.add_argument("--style", default="SOLID",
                   choices=["SOLID", "SOLID_MEDIUM", "SOLID_THICK", "DOTTED", "DASHED", "DOUBLE", "NONE"])
    s.add_argument("--color", default="#000000")
    s.add_argument("--all", action="store_true", help="All sides + inner")
    for side in ("top", "bottom", "left", "right"):
        s.add_argument(f"--{side}", action="store_true")
    s.add_argument("--inner", action="store_true", help="Inner horizontal + vertical")
    s = add("banding", "Alternating row colors (zebra stripes)", cmd_banding)
    _add_range(s)
    s.add_argument("--header-bg", help="Header band (default #1a73e8)")
    s.add_argument("--first-bg", help="First band (default #ffffff)")
    s.add_argument("--second-bg", help="Second band (default #f1f3f4)")
    s.add_argument("--footer-bg")
    s = add("conditional-format", "Add a conditional-format rule", cmd_conditional_format)
    _add_range(s)
    s.add_argument("--condition", help="NUMBER_GREATER, TEXT_EQ, TEXT_STARTS_WITH, BLANK, CUSTOM_FORMULA, "
                                       "NUMBER_BETWEEN, DATE_BEFORE, ... (Sheets ConditionType)")
    s.add_argument("--value", action="append",
                   help="Condition value; repeat for two-value conditions such as NUMBER_BETWEEN")
    s.add_argument("--bg")
    s.add_argument("--fg")
    s.add_argument("--bold", action="store_true")
    s.add_argument("--rule", help="Raw ConditionalFormatRule JSON (inline or @file); overrides --condition")
    s.add_argument("--index", type=int, default=0, help="Rule priority (0 = first)")
    s = add("validation", "Dropdowns, checkboxes and other data validation", cmd_validation)
    _add_range(s)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--one-of", help="Dropdown items, comma-separated: 'Open,Done,Blocked'")
    g.add_argument("--one-of-range", help="Dropdown from a range: \"=Roles!$S$2:$S$30\"")
    g.add_argument("--checkbox", action="store_true")
    g.add_argument("--formula", help="CUSTOM_FORMULA rule, e.g. '=LEN(A2)<=40'")
    g.add_argument("--clear", action="store_true", help="Remove validation from the range")
    s.add_argument("--strict", action=argparse.BooleanOptionalAction, default=True,
                   help="Reject invalid input (default) or only warn (--no-strict)")
    s.add_argument("--no-dropdown", action="store_true", help="Hide the dropdown arrow")
    s.add_argument("--help-text", help="Message shown when the cell is selected")
    s = add("note", "Set or clear a cell note", cmd_note)
    _add_range(s)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--clear", action="store_true")
    s = add("copy-format", "Copy formatting (or validation, ...) from one range to another", cmd_copy_format)
    s.add_argument("--from", required=True, dest="from", help="Source range, 'Tab!A2:H2'")
    s.add_argument("--to", required=True, help="Destination range; the source repeats to fill it")
    s.add_argument("--what", default="format", choices=list(_PASTE_TYPES))

    s = add("table", "Write a table and lay it out in one atomic batch", cmd_table)
    s.add_argument("--tab", required=True)
    s.add_argument("--at", default="A1", help="Top-left cell (default A1)")
    _add_values_input(s)
    s.add_argument("--input", choices=["typed", "user-entered"],
                   help="typed (default for JSON): numbers stay numbers, '=...' are formulas, other strings "
                        "are literal; user-entered (default for CSV): parsed like typing")
    s.add_argument("--header-rows", type=int, default=1, help="Header rows at the top (0 for none)")
    s.add_argument("--header-bg", default="#1a73e8")
    s.add_argument("--header-fg", default="#ffffff")
    s.add_argument("--col-format", action="append",
                   help="COLS=PATTERN for data rows, repeatable: 'D:F=#,##0.00', 'G=0.0%%', 'A=TEXT'")
    s.add_argument("--widths", help="Pixel widths from the first table column: '40,180,90'")
    s.add_argument("--auto-width", action="store_true")
    s.add_argument("--wrap", action="store_true", help="Wrap + top-align data cells")
    s.add_argument("--freeze", action=argparse.BooleanOptionalAction, default=None,
                   help="Freeze through the header (default on when the table starts at row 1)")
    s.add_argument("--freeze-cols", type=int)
    s.add_argument("--filter", action="store_true", help="Basic filter over the table")
    s.add_argument("--banding", action="store_true", help="Zebra stripes")
    s.add_argument("--band-bg", default="#f1f3f4", help="Second band color")
    s.add_argument("--replace", action="store_true",
                   help="Reset the tab first: values, formats, notes, validation, merges, banding, "
                        "conditional formats and the filter")
    s.add_argument("--create", action="store_true", help="Add the tab if it doesn't exist")

    # ── filter / sort ──
    s = add("add-filter", "Add a basic filter to a range", cmd_add_filter)
    _add_range(s)
    s = add("clear-filter", "Clear the basic filter on a tab", cmd_clear_filter)
    s.add_argument("--tab", required=True)
    s = add("sort", "Sort a range by one or more columns", cmd_sort)
    _add_range(s)
    s.add_argument("--by", required=True, help="'B:desc,C:asc'; bare 'B' = ascending")

    # ── inspect / export ──
    s = add("inspect", "Widths, merges, conditional formats, validation, groups, charts of a tab", cmd_inspect)
    s.add_argument("--tab", required=True)
    s.add_argument("--cells", help="Also per-cell number formats, notes, validation for this range, e.g. A1:H40")
    s.add_argument("--raw", action="store_true", help="Keep API color objects (to paste into batch-update)")
    s = add("export", "Download as pdf/xlsx/csv/png (visual QA)", cmd_export)
    s.add_argument("--tab", help="Only this tab (default: whole spreadsheet; csv needs a tab)")
    s.add_argument("--cells", help="Only this range of the tab, e.g. A1:H40")
    s.add_argument("--format", default="pdf", choices=["pdf", "xlsx", "csv", "png"])
    s.add_argument("--out", required=True)
    s.add_argument("--landscape", action="store_true")
    s.add_argument("--gridlines", action="store_true")

    # ── escape hatch ──
    s = add("batch-update", "Send raw batchUpdate requests (A1 strings allowed for ranges)", cmd_batch_update)
    s.add_argument("--requests", required=True,
                   help="JSON array of Request objects (inline or @file.json), or {\"requests\": [...]}")
    s.add_argument("--full", action="store_true", help="Print the full reply JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(line_buffering=True)  # keep stdout and stderr lines in order when piped
    global DRY_RUN
    args = build_parser().parse_args(argv)
    DRY_RUN = bool(getattr(args, "dry_run", False))
    token = get_token(getattr(args, "sa_key", None))
    try:
        return args.func(args, token)
    except DryRun:
        return 0
    except Refused as e:
        sys.stderr.write(f"{e}\n")
        return 3
    except urllib.error.HTTPError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
