#!/usr/bin/env python3
"""gsheets — Google Sheets API v4 CLI.

A comprehensive single-file wrapper over the Sheets API covering:

  Data         read, write, append, clear
  Tabs         list-tabs, add-tab, delete-tab, rename-tab, duplicate-tab
  Structure    resize-cols, resize-rows, freeze, merge, unmerge,
               insert-rows, insert-cols, delete-rows, delete-cols
  Styling      format, format-header, borders, banding, conditional-format
  Filter/sort  add-filter, clear-filter, sort
  Escape       batch-update (raw Sheets batchUpdate requests[])
  Meta         info

Auth: --sa-key path/to/sa.json  (recommended)
      OR gcloud ADC (`gcloud auth application-default login` with explicit
      --scopes for spreadsheets + drive).

Most commands take SPREADSHEET_ID as the first positional. Get it from the
URL: https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import random
import re
import subprocess
import sys
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

_MAX_RETRIES = 5
_BASE_DELAY = 1.5
_MAX_BACKOFF = 32.0
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


# ─── Auth ─────────────────────────────────────────────────────────────────

def get_token(sa_key: Path | None) -> str:
    """Return an OAuth bearer token for the Sheets + Drive scopes.

    Two paths, in order of preference:

    1. **Service account** (--sa-key). Uses `google.oauth2.service_account`
       if available, falls back to a self-signed JWT we mint by hand so this
       script stays usable without google-auth installed.

    2. **gcloud ADC**. We always pass --scopes explicitly to
       `print-access-token` because the default cloud-platform scope does
       NOT include spreadsheets/drive — the printed token would 403 even if
       ADC was configured with the right scopes. We also strip
       GOOGLE_APPLICATION_CREDENTIALS first because a stale env var pointing
       at a missing key file is a common footgun.
    """
    if sa_key is not None:
        return _token_from_service_account(sa_key)

    env = os.environ.copy()
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    try:
        result = subprocess.run(
            [
                "gcloud", "auth", "application-default", "print-access-token",
                "--scopes=" + ",".join(SCOPES),
            ],
            env=env, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        sys.exit("error: gcloud not on PATH and no --sa-key provided")
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"error: gcloud ADC auth failed:\n{e.stderr}\n")
        sys.stderr.write(
            "\nfix one of:\n"
            "  (1) gcloud auth application-default login --scopes="
            + ",".join(SCOPES) + "\n"
            "  (2) pass --sa-key /path/to/service-account.json\n"
        )
        sys.exit(1)
    return result.stdout.strip()


def _token_from_service_account(sa_key: Path) -> str:
    """Exchange a service-account JSON for an access token.

    Prefer `google-auth` (pip install google-auth) — it handles refresh,
    clock-skew, etc. If unavailable, mint a JWT manually using only stdlib.
    """
    try:
        from google.oauth2 import service_account  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
        creds = service_account.Credentials.from_service_account_file(
            str(sa_key), scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds.token
    except ImportError:
        pass

    # Fallback: hand-rolled JWT (RS256). Requires `cryptography`.
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        sys.exit(
            "error: --sa-key needs `google-auth` (preferred) or `cryptography`.\n"
            "       pip install google-auth"
        )

    import base64
    sa = json.loads(sa_key.read_text())
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT", "kid": sa.get("private_key_id")}
    claim = {
        "iss": sa["client_email"],
        "scope": " ".join(SCOPES),
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    }
    def b64(d: dict) -> bytes:
        return base64.urlsafe_b64encode(
            json.dumps(d, separators=(",", ":")).encode()
        ).rstrip(b"=")
    signing_input = b64(header) + b"." + b64(claim)
    key = serialization.load_pem_private_key(
        sa["private_key"].encode(), password=None,
    )
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion.decode(),
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


# ─── HTTP ─────────────────────────────────────────────────────────────────

def api(
    token: str,
    method: str,
    url: str,
    body: Any = None,
    content_type: str = "application/json",
) -> Any:
    """HTTP call with truncated-exponential-backoff retry on 429 / 5xx.

    `body` is JSON-encoded when it's a dict/list; bytes pass through (for
    text/csv uploads). Returns the parsed JSON response, or {} on 204/empty.
    """
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

    for attempt in range(_MAX_RETRIES):
        req = urllib.request.Request(url, data=payload, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                ctype = resp.headers.get("Content-Type", "")
                if "application/json" in ctype:
                    return json.loads(raw)
                return raw
        except urllib.error.HTTPError as e:
            if e.code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES - 1:
                delay = min(_BASE_DELAY * (2 ** attempt), _MAX_BACKOFF)
                delay += random.uniform(0, 1.0)  # jitter
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
            sys.stderr.write(f"\nHTTP {e.code} on {method} {url}:\n{err_body[:800]}\n")
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < _MAX_RETRIES - 1:
                delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.0)
                sys.stderr.write(
                    f"  ! {type(e).__name__} on {method} — retrying in {delay:.1f}s\n"
                )
                time.sleep(delay)
                continue
            raise
    raise RuntimeError("retry loop exhausted")


# ─── Utilities ────────────────────────────────────────────────────────────

_COL_RX = re.compile(r"^([A-Z]+)([0-9]*)$")


def col_letter_to_index(letter: str) -> int:
    """'A' → 0, 'B' → 1, 'Z' → 25, 'AA' → 26, etc."""
    letter = letter.upper()
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


def parse_color(hex_str: str) -> dict:
    """'#1a73e8' or '1a73e8' → {red, green, blue} in 0-1 floats.

    Sheets API uses normalized RGB. Alpha not supported here (rarely needed).
    """
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


def parse_a1(a1: str) -> tuple[str | None, str]:
    """Split 'Tab Name!A1:C10' → ('Tab Name', 'A1:C10').

    Returns (None, range_part) if there's no sheet prefix. Handles
    single-quoted tab names: "'Sheet 1'!A1".
    """
    if "!" not in a1:
        return None, a1
    tab, _, rng = a1.partition("!")
    tab = tab.strip()
    if tab.startswith("'") and tab.endswith("'"):
        tab = tab[1:-1].replace("''", "'")
    return tab, rng


def a1_to_grid_range(a1: str, sheet_id: int) -> dict:
    """'A1:C10' or 'A:C' or '1:3' → GridRange dict (no sheet prefix).

    GridRange uses half-open intervals: startRowIndex/endRowIndex are
    0-indexed, end is exclusive. Omitting an index means "open".
    """
    _, rng = parse_a1(a1)  # drop any 'Tab!' prefix
    if ":" in rng:
        start, end = rng.split(":", 1)
    else:
        start = end = rng
    sm = _COL_RX.match(start)
    em = _COL_RX.match(end)
    if not sm or not em:
        raise ValueError(f"invalid range: {a1!r}")
    gr: dict = {"sheetId": sheet_id}
    s_col, s_row = sm.groups()
    e_col, e_row = em.groups()
    if s_col:
        gr["startColumnIndex"] = col_letter_to_index(s_col)
    if s_row:
        gr["startRowIndex"] = int(s_row) - 1
    if e_col:
        gr["endColumnIndex"] = col_letter_to_index(e_col) + 1
    if e_row:
        gr["endRowIndex"] = int(e_row)
    return gr


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


def load_values(args) -> list[list]:
    """Resolve --values-json / --csv / --values-stdin into a 2D array."""
    if args.values_json is not None:
        raw = args.values_json
        if raw.startswith("@"):
            raw = Path(raw[1:]).read_text()
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("--values-json must be a JSON 2D array")
        return [list(row) if isinstance(row, list) else [row] for row in data]
    if args.csv is not None:
        text = Path(args.csv).read_text()
        reader = csv.reader(io.StringIO(text))
        return [row for row in reader]
    if args.values_stdin:
        reader = csv.reader(sys.stdin)
        return [row for row in reader]
    raise ValueError("provide one of --values-json, --csv, --values-stdin")


# ─── Sheet metadata ───────────────────────────────────────────────────────

_meta_cache: dict[str, dict] = {}


def get_spreadsheet(token: str, spreadsheet_id: str, force: bool = False) -> dict:
    """GET the spreadsheet metadata (cached per process).

    The response includes sheets[].properties (sheetId, title, gridProperties).
    We need this for any operation that takes --tab "Title" since the API
    actually requires the numeric sheetId.
    """
    if not force and spreadsheet_id in _meta_cache:
        return _meta_cache[spreadsheet_id]
    fields = "spreadsheetId,properties.title,sheets.properties"
    url = f"{SHEETS_BASE}/{spreadsheet_id}?fields={urllib.parse.quote(fields)}"
    meta = api(token, "GET", url)
    _meta_cache[spreadsheet_id] = meta
    return meta


def resolve_tab(token: str, spreadsheet_id: str, title: str) -> dict:
    """Resolve a tab title → its full properties dict (incl. sheetId).

    Raises SystemExit with a helpful message listing available titles.
    """
    meta = get_spreadsheet(token, spreadsheet_id)
    for sh in meta.get("sheets", []):
        p = sh.get("properties", {})
        if p.get("title") == title:
            return p
    titles = [s.get("properties", {}).get("title") for s in meta.get("sheets", [])]
    sys.exit(f"error: tab {title!r} not found. available: {titles}")


def resolve_tab_id(token: str, spreadsheet_id: str, title: str) -> int:
    return resolve_tab(token, spreadsheet_id, title)["sheetId"]


def batch_update(token: str, spreadsheet_id: str, requests: list[dict]) -> dict:
    """POST {spreadsheet}:batchUpdate. All requests run atomically — if any
    fails, none commit. This is also the most quota-efficient way to apply
    many changes: the whole batch counts as 1 API call against the per-minute
    quota."""
    url = f"{SHEETS_BASE}/{spreadsheet_id}:batchUpdate"
    return api(token, "POST", url, {"requests": requests})


# ─── Subcommand: meta / info ──────────────────────────────────────────────

def cmd_info(args, token: str) -> int:
    """Print spreadsheet name + tabs summary — a safe dry-run probe."""
    fields = (
        "spreadsheetId,properties(title,locale,timeZone),"
        "sheets.properties(sheetId,title,index,gridProperties)"
    )
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}?fields={urllib.parse.quote(fields)}"
    meta = api(token, "GET", url)

    # Also hit Drive for canEdit / owner
    drive_fields = "id,name,owners(emailAddress),capabilities(canEdit),modifiedTime"
    drive_url = (
        f"{DRIVE_BASE}/files/{args.spreadsheet_id}"
        f"?fields={urllib.parse.quote(drive_fields)}&supportsAllDrives=true"
    )
    dmeta = api(token, "GET", drive_url)

    out = {
        "spreadsheetId": meta["spreadsheetId"],
        "title": meta["properties"]["title"],
        "locale": meta["properties"].get("locale"),
        "timeZone": meta["properties"].get("timeZone"),
        "modifiedTime": dmeta.get("modifiedTime"),
        "owners": [o.get("emailAddress") for o in (dmeta.get("owners") or [])],
        "canEdit": (dmeta.get("capabilities") or {}).get("canEdit"),
        "tabs": [
            {
                "sheetId": s["properties"]["sheetId"],
                "title": s["properties"]["title"],
                "index": s["properties"].get("index"),
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


# ─── Subcommand: data (values.*) ──────────────────────────────────────────

def cmd_read(args, token: str) -> int:
    rng = urllib.parse.quote(args.range, safe="")
    qs = f"valueRenderOption={args.value_render}"
    if args.major_dimension:
        qs += f"&majorDimension={args.major_dimension}"
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{rng}?{qs}"
    resp = api(token, "GET", url)
    print(json.dumps(resp.get("values", []), indent=2, ensure_ascii=False))
    return 0


def cmd_write(args, token: str) -> int:
    values = load_values(args)
    rng = urllib.parse.quote(args.range, safe="")
    url = (
        f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{rng}"
        f"?valueInputOption={args.value_input_option}"
    )
    body = {"range": args.range, "majorDimension": "ROWS", "values": values}
    resp = api(token, "PUT", url, body)
    rows = resp.get("updatedRows", 0)
    cols = resp.get("updatedColumns", 0)
    cells = resp.get("updatedCells", 0)
    print(f"✓ wrote {cells} cells ({rows}r × {cols}c) to {args.range}")
    return 0


def cmd_append(args, token: str) -> int:
    values = load_values(args)
    rng = urllib.parse.quote(args.range, safe="")
    qs = (
        f"valueInputOption={args.value_input_option}"
        f"&insertDataOption={args.insert_data_option}"
    )
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{rng}:append?{qs}"
    body = {"range": args.range, "majorDimension": "ROWS", "values": values}
    resp = api(token, "POST", url, body)
    updates = resp.get("updates", {})
    print(
        f"✓ appended {updates.get('updatedRows', 0)} rows, "
        f"{updates.get('updatedCells', 0)} cells → {updates.get('updatedRange')}"
    )
    return 0


def cmd_clear(args, token: str) -> int:
    rng = urllib.parse.quote(args.range, safe="")
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{rng}:clear"
    resp = api(token, "POST", url, {})
    print(f"✓ cleared {resp.get('clearedRange', args.range)}")
    return 0


# ─── Subcommand: tabs ─────────────────────────────────────────────────────

def cmd_list_tabs(args, token: str) -> int:
    meta = get_spreadsheet(token, args.spreadsheet_id, force=True)
    rows = []
    for s in meta.get("sheets", []):
        p = s["properties"]
        g = p.get("gridProperties", {})
        rows.append((
            p["sheetId"], p.get("index"), p["title"],
            g.get("rowCount"), g.get("columnCount"),
            g.get("frozenRowCount", 0), g.get("frozenColumnCount", 0),
        ))
    print(f"{'sheetId':>10}  {'idx':>3}  {'title':<30}  {'rows':>6}  {'cols':>5}  {'frR':>3}  {'frC':>3}")
    for r in rows:
        print(f"{r[0]:>10}  {r[1]:>3}  {str(r[2])[:30]:<30}  {str(r[3]):>6}  {str(r[4]):>5}  {r[5]:>3}  {r[6]:>3}")
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
    if args.color:
        props["tabColorStyle"] = {"rgbColor": parse_color(args.color)}
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
    sid = resolve_tab_id(token, args.spreadsheet_id, getattr(args, "from"))
    batch_update(token, args.spreadsheet_id, [{
        "updateSheetProperties": {
            "properties": {"sheetId": sid, "title": args.to},
            "fields": "title",
        }
    }])
    print(f"✓ renamed tab {getattr(args, 'from')!r} → {args.to!r}")
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

def cmd_resize_cols(args, token: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.tab)
    start, end = col_range_to_indices(args.cols)
    dim_range = {
        "sheetId": sid, "dimension": "COLUMNS",
        "startIndex": start, "endIndex": end,
    }
    if args.auto:
        req = {"autoResizeDimensions": {"dimensions": dim_range}}
    else:
        if args.width is None:
            sys.exit("error: provide --width N or --auto")
        req = {
            "updateDimensionProperties": {
                "range": dim_range,
                "properties": {"pixelSize": args.width},
                "fields": "pixelSize",
            }
        }
    batch_update(token, args.spreadsheet_id, [req])
    mode = "auto" if args.auto else f"{args.width}px"
    print(f"✓ resized cols {args.cols} of {args.tab!r} → {mode}")
    return 0


def cmd_resize_rows(args, token: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.tab)
    start, end = row_range_to_indices(args.rows)
    dim_range = {
        "sheetId": sid, "dimension": "ROWS",
        "startIndex": start, "endIndex": end,
    }
    if args.auto:
        req = {"autoResizeDimensions": {"dimensions": dim_range}}
    else:
        if args.height is None:
            sys.exit("error: provide --height N or --auto")
        req = {
            "updateDimensionProperties": {
                "range": dim_range,
                "properties": {"pixelSize": args.height},
                "fields": "pixelSize",
            }
        }
    batch_update(token, args.spreadsheet_id, [req])
    mode = "auto" if args.auto else f"{args.height}px"
    print(f"✓ resized rows {args.rows} of {args.tab!r} → {mode}")
    return 0


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
    batch_update(token, args.spreadsheet_id, [{
        "updateSheetProperties": {
            "properties": {"sheetId": sid, "gridProperties": grid},
            "fields": ",".join(fields),
        }
    }])
    print(f"✓ froze {args.rows or 0} rows × {args.cols or 0} cols on {args.tab!r}")
    return 0


def cmd_merge(args, token: str) -> int:
    tab, _ = parse_a1(args.range)
    if not tab:
        sys.exit("error: --range must include a tab prefix, e.g. 'Sheet1!A1:C1'")
    sid = resolve_tab_id(token, args.spreadsheet_id, tab)
    gr = a1_to_grid_range(args.range, sid)
    batch_update(token, args.spreadsheet_id, [{
        "mergeCells": {"range": gr, "mergeType": args.merge_type},
    }])
    print(f"✓ merged {args.range} ({args.merge_type})")
    return 0


def cmd_unmerge(args, token: str) -> int:
    tab, _ = parse_a1(args.range)
    if not tab:
        sys.exit("error: --range must include a tab prefix")
    sid = resolve_tab_id(token, args.spreadsheet_id, tab)
    gr = a1_to_grid_range(args.range, sid)
    batch_update(token, args.spreadsheet_id, [{"unmergeCells": {"range": gr}}])
    print(f"✓ unmerged {args.range}")
    return 0


def _dim_op(args, token: str, op: str, dimension: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.tab)
    if dimension == "ROWS":
        start, end = row_range_to_indices(args.rows)
    else:
        start, end = col_range_to_indices(args.cols)
    dim_range = {
        "sheetId": sid, "dimension": dimension,
        "startIndex": start, "endIndex": end,
    }
    if op == "insertDimension":
        req = {"insertDimension": {"range": dim_range, "inheritFromBefore": False}}
    else:
        req = {"deleteDimension": {"range": dim_range}}
    batch_update(token, args.spreadsheet_id, [req])
    verb = "inserted" if op == "insertDimension" else "deleted"
    print(f"✓ {verb} {dimension.lower()} [{start},{end}) on {args.tab!r}")
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
    """Build (userEnteredFormat dict, fields list) from --bg/--fg/--bold/etc."""
    cell_fmt: dict = {}
    text_fmt: dict = {}
    fields: list[str] = []

    if args.bg:
        cell_fmt["backgroundColor"] = parse_color(args.bg)
        fields.append("userEnteredFormat.backgroundColor")
    if args.fg:
        text_fmt["foregroundColor"] = parse_color(args.fg)
    if args.bold is not None:
        text_fmt["bold"] = args.bold
    if args.italic is not None:
        text_fmt["italic"] = args.italic
    if args.font_size:
        text_fmt["fontSize"] = args.font_size
    if args.font:
        text_fmt["fontFamily"] = args.font
    if text_fmt:
        cell_fmt["textFormat"] = text_fmt
        fields.append("userEnteredFormat.textFormat")
    if args.align:
        cell_fmt["horizontalAlignment"] = _H_ALIGN[args.align]
        fields.append("userEnteredFormat.horizontalAlignment")
    if args.valign:
        cell_fmt["verticalAlignment"] = _V_ALIGN[args.valign]
        fields.append("userEnteredFormat.verticalAlignment")
    if args.wrap:
        cell_fmt["wrapStrategy"] = "WRAP"
        fields.append("userEnteredFormat.wrapStrategy")
    if args.number_format:
        cell_fmt["numberFormat"] = {"type": "NUMBER", "pattern": args.number_format}
        fields.append("userEnteredFormat.numberFormat")
    return cell_fmt, fields


def cmd_format(args, token: str) -> int:
    tab, _ = parse_a1(args.range)
    if not tab:
        sys.exit("error: --range must include a tab prefix, e.g. 'Sheet1!A1:Z1'")
    sid = resolve_tab_id(token, args.spreadsheet_id, tab)
    gr = a1_to_grid_range(args.range, sid)
    cell_fmt, fields = _build_format(args)
    if not fields:
        sys.exit("error: nothing to format — pass at least one of --bg/--fg/--bold/...")
    batch_update(token, args.spreadsheet_id, [{
        "repeatCell": {
            "range": gr,
            "cell": {"userEnteredFormat": cell_fmt},
            "fields": ",".join(fields),
        }
    }])
    print(f"✓ formatted {args.range}")
    return 0


def cmd_format_header(args, token: str) -> int:
    """One-shot: bold + bg/fg color on row 1, freeze row 1, optional filter.

    Bundled into a single batchUpdate (atomic + cheap on quota).
    """
    tab_props = resolve_tab(token, args.spreadsheet_id, args.tab)
    sid = tab_props["sheetId"]
    col_count = tab_props.get("gridProperties", {}).get("columnCount", 26)

    bg = parse_color(args.bg) if args.bg else parse_color("#1a73e8")
    fg = parse_color(args.fg) if args.fg else parse_color("#ffffff")

    requests: list[dict] = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 0, "endRowIndex": 1,
                    "startColumnIndex": 0, "endColumnIndex": col_count,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": bg,
                        "textFormat": {
                            "foregroundColor": fg,
                            "bold": True,
                        },
                        "horizontalAlignment": "LEFT",
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": (
                    "userEnteredFormat("
                    "backgroundColor,textFormat,horizontalAlignment,verticalAlignment"
                    ")"
                ),
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sid,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
    ]
    if args.filter:
        requests.append({
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": sid,
                        "startRowIndex": 0,
                        "startColumnIndex": 0,
                        "endColumnIndex": col_count,
                    }
                }
            }
        })
    batch_update(token, args.spreadsheet_id, requests)
    extra = " + filter" if args.filter else ""
    print(f"✓ styled header of {args.tab!r}: bg + bold + frozen row 1{extra}")
    return 0


def cmd_borders(args, token: str) -> int:
    tab, _ = parse_a1(args.range)
    if not tab:
        sys.exit("error: --range must include a tab prefix")
    sid = resolve_tab_id(token, args.spreadsheet_id, tab)
    gr = a1_to_grid_range(args.range, sid)
    border = {
        "style": args.style,
        "colorStyle": {"rgbColor": parse_color(args.color)},
    }
    req: dict = {"updateBorders": {"range": gr}}
    if args.all:
        for side in ("top", "bottom", "left", "right", "innerHorizontal", "innerVertical"):
            req["updateBorders"][side] = border
    else:
        if args.top: req["updateBorders"]["top"] = border
        if args.bottom: req["updateBorders"]["bottom"] = border
        if args.left: req["updateBorders"]["left"] = border
        if args.right: req["updateBorders"]["right"] = border
        if args.inner:
            req["updateBorders"]["innerHorizontal"] = border
            req["updateBorders"]["innerVertical"] = border
    if len(req["updateBorders"]) == 1:  # only "range" set
        sys.exit("error: specify --all or at least one side (--top --bottom --left --right --inner)")
    batch_update(token, args.spreadsheet_id, [req])
    print(f"✓ borders applied to {args.range}")
    return 0


def cmd_banding(args, token: str) -> int:
    tab, _ = parse_a1(args.range)
    if not tab:
        sys.exit("error: --range must include a tab prefix")
    sid = resolve_tab_id(token, args.spreadsheet_id, tab)
    gr = a1_to_grid_range(args.range, sid)

    # Material-ish defaults that read well on white: blue header, white + pale-blue alt
    row_props = {
        "headerColorStyle": {"rgbColor": parse_color(args.header_bg or "#1a73e8")},
        "firstBandColorStyle": {"rgbColor": parse_color(args.first_bg or "#ffffff")},
        "secondBandColorStyle": {"rgbColor": parse_color(args.second_bg or "#f1f3f4")},
    }
    if args.footer_bg:
        row_props["footerColorStyle"] = {"rgbColor": parse_color(args.footer_bg)}

    batch_update(token, args.spreadsheet_id, [{
        "addBanding": {
            "bandedRange": {
                "range": gr,
                "rowProperties": row_props,
            }
        }
    }])
    print(f"✓ banding applied to {args.range}")
    return 0


def cmd_conditional_format(args, token: str) -> int:
    tab, _ = parse_a1(args.range)
    if not tab:
        sys.exit("error: --range must include a tab prefix")
    sid = resolve_tab_id(token, args.spreadsheet_id, tab)
    gr = a1_to_grid_range(args.range, sid)

    if args.rule:
        rule_body = args.rule
        if rule_body.startswith("@"):
            rule_body = Path(rule_body[1:]).read_text()
        rule = json.loads(rule_body)
        if "ranges" not in rule:
            rule["ranges"] = [gr]
    else:
        # Convenience: --condition NUMBER_GREATER --value 100 --bg #...
        if not (args.condition and (args.value is not None or args.condition in (
            "BLANK", "NOT_BLANK", "TEXT_IS_EMAIL", "TEXT_IS_URL",
        ))):
            sys.exit(
                "error: provide either --rule '@rule.json' OR "
                "--condition <TYPE> [--value V] with at least one of --bg/--fg/--bold"
            )
        condition: dict = {"type": args.condition}
        if args.value is not None:
            condition["values"] = [{"userEnteredValue": args.value}]
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
        rule = {
            "ranges": [gr],
            "booleanRule": {"condition": condition, "format": fmt},
        }

    batch_update(token, args.spreadsheet_id, [{
        "addConditionalFormatRule": {"rule": rule, "index": args.index},
    }])
    print(f"✓ conditional format added to {args.range}")
    return 0


# ─── Subcommand: filter / sort ────────────────────────────────────────────

def cmd_add_filter(args, token: str) -> int:
    tab, _ = parse_a1(args.range)
    if not tab:
        sys.exit("error: --range must include a tab prefix")
    sid = resolve_tab_id(token, args.spreadsheet_id, tab)
    gr = a1_to_grid_range(args.range, sid)
    batch_update(token, args.spreadsheet_id, [{
        "setBasicFilter": {"filter": {"range": gr}},
    }])
    print(f"✓ basic filter set on {args.range}")
    return 0


def cmd_clear_filter(args, token: str) -> int:
    sid = resolve_tab_id(token, args.spreadsheet_id, args.tab)
    batch_update(token, args.spreadsheet_id, [{"clearBasicFilter": {"sheetId": sid}}])
    print(f"✓ filter cleared on {args.tab!r}")
    return 0


def cmd_sort(args, token: str) -> int:
    tab, _ = parse_a1(args.range)
    if not tab:
        sys.exit("error: --range must include a tab prefix")
    sid = resolve_tab_id(token, args.spreadsheet_id, tab)
    gr = a1_to_grid_range(args.range, sid)
    specs = []
    # --by accepts a comma-separated list like "B:asc,C:desc"
    for spec in args.by.split(","):
        col, _, order = spec.strip().partition(":")
        order = (order or "asc").lower()
        if order not in ("asc", "desc"):
            sys.exit(f"error: invalid sort order {order!r} (use asc or desc)")
        specs.append({
            "dimensionIndex": col_letter_to_index(col),
            "sortOrder": "ASCENDING" if order == "asc" else "DESCENDING",
        })
    batch_update(token, args.spreadsheet_id, [{
        "sortRange": {"range": gr, "sortSpecs": specs},
    }])
    print(f"✓ sorted {args.range} by {args.by}")
    return 0


# ─── Subcommand: batch-update (escape hatch) ──────────────────────────────

def cmd_batch_update(args, token: str) -> int:
    raw = args.requests
    if raw.startswith("@"):
        raw = Path(raw[1:]).read_text()
    payload = json.loads(raw)
    if isinstance(payload, dict) and "requests" in payload:
        requests = payload["requests"]
    elif isinstance(payload, list):
        requests = payload
    else:
        sys.exit("error: --requests must be a JSON array OR an object with 'requests' key")
    resp = batch_update(token, args.spreadsheet_id, requests)
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    return 0


# ─── argparse wiring ──────────────────────────────────────────────────────

def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("spreadsheet_id", help="Spreadsheet file ID (from the URL)")
    p.add_argument(
        "--sa-key", type=Path, default=None,
        help="Path to service-account JSON key (recommended)",
    )


def _add_values_input(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--values-json", help="JSON 2D array (inline or @file.json)")
    g.add_argument("--csv", help="CSV file path")
    g.add_argument("--values-stdin", action="store_true", help="Read CSV from stdin")


def _add_format_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--bg", help="Background color, hex (#RRGGBB)")
    p.add_argument("--fg", help="Foreground/text color, hex")
    p.add_argument("--bold", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--italic", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--font-size", type=int)
    p.add_argument("--font", help="Font family, e.g. 'Roboto', 'Arial'")
    p.add_argument("--align", choices=["left", "center", "right"])
    p.add_argument("--valign", choices=["top", "middle", "bottom"])
    p.add_argument("--wrap", action="store_true", help="Set wrapStrategy=WRAP")
    p.add_argument("--number-format", help="Pattern like '0.00%%' or '#,##0.00'")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gsheets",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<command>")

    # ── meta ──
    s = sub.add_parser("info", help="Print spreadsheet metadata + tabs (safe dry-run probe)")
    _add_common(s)
    s.set_defaults(func=cmd_info)

    # ── data ──
    s = sub.add_parser("read", help="Read a range and emit as JSON")
    _add_common(s)
    s.add_argument("--range", required=True, help="A1 like 'Tab!A1:C10'")
    s.add_argument("--value-render", default="FORMATTED_VALUE",
                   choices=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"])
    s.add_argument("--major-dimension", choices=["ROWS", "COLUMNS"])
    s.set_defaults(func=cmd_read)

    s = sub.add_parser("write", help="Overwrite a range with values")
    _add_common(s)
    s.add_argument("--range", required=True)
    s.add_argument("--value-input-option", default="USER_ENTERED",
                   choices=["RAW", "USER_ENTERED"])
    _add_values_input(s)
    s.set_defaults(func=cmd_write)

    s = sub.add_parser("append", help="Append rows after the last data row")
    _add_common(s)
    s.add_argument("--range", required=True, help="A range covering the table, e.g. 'Tab!A:Z'")
    s.add_argument("--value-input-option", default="USER_ENTERED",
                   choices=["RAW", "USER_ENTERED"])
    s.add_argument("--insert-data-option", default="INSERT_ROWS",
                   choices=["OVERWRITE", "INSERT_ROWS"])
    _add_values_input(s)
    s.set_defaults(func=cmd_append)

    s = sub.add_parser("clear", help="Clear cell values in a range (preserves formatting)")
    _add_common(s)
    s.add_argument("--range", required=True)
    s.set_defaults(func=cmd_clear)

    # ── tabs ──
    s = sub.add_parser("list-tabs", help="List worksheets with their sheetId / dimensions")
    _add_common(s)
    s.set_defaults(func=cmd_list_tabs)

    s = sub.add_parser("add-tab", help="Add a new worksheet (tab)")
    _add_common(s)
    s.add_argument("--title", required=True)
    s.add_argument("--rows", type=int, help="Initial row count (default 1000)")
    s.add_argument("--cols", type=int, help="Initial column count (default 26)")
    s.add_argument("--index", type=int, help="Tab position (0 = first)")
    s.add_argument("--color", help="Tab color, hex")
    s.set_defaults(func=cmd_add_tab)

    s = sub.add_parser("delete-tab", help="Delete a worksheet by title")
    _add_common(s)
    s.add_argument("--title", required=True)
    s.set_defaults(func=cmd_delete_tab)

    s = sub.add_parser("rename-tab", help="Rename a worksheet")
    _add_common(s)
    s.add_argument("--from", required=True, dest="from")
    s.add_argument("--to", required=True)
    s.set_defaults(func=cmd_rename_tab)

    s = sub.add_parser("duplicate-tab", help="Duplicate a worksheet")
    _add_common(s)
    s.add_argument("--from", required=True, dest="from")
    s.add_argument("--to", required=True, help="Name for the copy")
    s.add_argument("--index", type=int)
    s.set_defaults(func=cmd_duplicate_tab)

    # ── structure ──
    s = sub.add_parser("resize-cols", help="Set column width(s) or autoresize")
    _add_common(s)
    s.add_argument("--tab", required=True)
    s.add_argument("--cols", required=True, help="Column range like 'A:C' or 'B'")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--width", type=int, help="Width in pixels")
    g.add_argument("--auto", action="store_true", help="Autoresize to content")
    s.set_defaults(func=cmd_resize_cols)

    s = sub.add_parser("resize-rows", help="Set row height(s) or autoresize")
    _add_common(s)
    s.add_argument("--tab", required=True)
    s.add_argument("--rows", required=True, help="Row range like '1:3' or '5'")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--height", type=int)
    g.add_argument("--auto", action="store_true")
    s.set_defaults(func=cmd_resize_rows)

    s = sub.add_parser("freeze", help="Freeze the first N rows and/or M columns")
    _add_common(s)
    s.add_argument("--tab", required=True)
    s.add_argument("--rows", type=int, help="Number of rows to freeze (0 to unfreeze)")
    s.add_argument("--cols", type=int, help="Number of columns to freeze")
    s.set_defaults(func=cmd_freeze)

    s = sub.add_parser("merge", help="Merge cells in a range")
    _add_common(s)
    s.add_argument("--range", required=True)
    s.add_argument("--merge-type", default="MERGE_ALL",
                   choices=["MERGE_ALL", "MERGE_COLUMNS", "MERGE_ROWS"])
    s.set_defaults(func=cmd_merge)

    s = sub.add_parser("unmerge", help="Unmerge cells in a range")
    _add_common(s)
    s.add_argument("--range", required=True)
    s.set_defaults(func=cmd_unmerge)

    for op_name, fn, dim_help in (
        ("insert-rows", cmd_insert_rows, "Rows like '5:7' (1-indexed, inclusive)"),
        ("delete-rows", cmd_delete_rows, "Rows like '5:7'"),
    ):
        s = sub.add_parser(op_name, help=op_name.replace("-", " ").capitalize())
        _add_common(s)
        s.add_argument("--tab", required=True)
        s.add_argument("--rows", required=True, help=dim_help)
        s.set_defaults(func=fn)

    for op_name, fn, dim_help in (
        ("insert-cols", cmd_insert_cols, "Cols like 'B:D'"),
        ("delete-cols", cmd_delete_cols, "Cols like 'B:D'"),
    ):
        s = sub.add_parser(op_name, help=op_name.replace("-", " ").capitalize())
        _add_common(s)
        s.add_argument("--tab", required=True)
        s.add_argument("--cols", required=True, help=dim_help)
        s.set_defaults(func=fn)

    # ── styling ──
    s = sub.add_parser("format", help="Apply formatting to a range (bg/fg/bold/etc.)")
    _add_common(s)
    s.add_argument("--range", required=True)
    _add_format_flags(s)
    s.set_defaults(func=cmd_format)

    s = sub.add_parser(
        "format-header",
        help="Style row 1 as a header (bold, bg, frozen) — optional filter",
    )
    _add_common(s)
    s.add_argument("--tab", required=True)
    s.add_argument("--bg", help="Header background (default #1a73e8)")
    s.add_argument("--fg", help="Header text color (default #ffffff)")
    s.add_argument("--filter", action="store_true",
                   help="Also add a basic filter on row 1")
    s.set_defaults(func=cmd_format_header)

    s = sub.add_parser("borders", help="Set borders on a range")
    _add_common(s)
    s.add_argument("--range", required=True)
    s.add_argument("--style", default="SOLID",
                   choices=["SOLID", "SOLID_MEDIUM", "SOLID_THICK",
                            "DOTTED", "DASHED", "DOUBLE", "NONE"])
    s.add_argument("--color", default="#000000")
    s.add_argument("--all", action="store_true", help="All sides + inner")
    s.add_argument("--top", action="store_true")
    s.add_argument("--bottom", action="store_true")
    s.add_argument("--left", action="store_true")
    s.add_argument("--right", action="store_true")
    s.add_argument("--inner", action="store_true",
                   help="Inner horizontal + vertical")
    s.set_defaults(func=cmd_borders)

    s = sub.add_parser("banding", help="Alternating-row banding (zebra stripes)")
    _add_common(s)
    s.add_argument("--range", required=True)
    s.add_argument("--header-bg", help="Header band color (default #1a73e8)")
    s.add_argument("--first-bg", help="First band color (default #ffffff)")
    s.add_argument("--second-bg", help="Second band color (default #f1f3f4)")
    s.add_argument("--footer-bg")
    s.set_defaults(func=cmd_banding)

    s = sub.add_parser(
        "conditional-format",
        help="Add a conditional-format rule (boolean condition with format)",
    )
    _add_common(s)
    s.add_argument("--range", required=True)
    s.add_argument(
        "--condition",
        help=(
            "Condition type, e.g. NUMBER_GREATER, NUMBER_LESS, NUMBER_EQ, "
            "TEXT_CONTAINS, TEXT_EQ, TEXT_STARTS_WITH, BLANK, NOT_BLANK, "
            "CUSTOM_FORMULA, DATE_BEFORE, DATE_AFTER. See the Sheets API "
            "ConditionType enum for the full list."
        ),
    )
    s.add_argument("--value", help="Value for the condition (or formula for CUSTOM_FORMULA)")
    s.add_argument("--bg", help="Fill color when condition matches")
    s.add_argument("--fg", help="Text color when condition matches")
    s.add_argument("--bold", action="store_true")
    s.add_argument("--rule", help="Raw rule JSON (inline or @rule.json) — overrides --condition")
    s.add_argument("--index", type=int, default=0, help="Rule priority index")
    s.set_defaults(func=cmd_conditional_format)

    # ── filter / sort ──
    s = sub.add_parser("add-filter", help="Add a basic filter (dropdown arrows) to a range")
    _add_common(s)
    s.add_argument("--range", required=True)
    s.set_defaults(func=cmd_add_filter)

    s = sub.add_parser("clear-filter", help="Clear the basic filter on a tab")
    _add_common(s)
    s.add_argument("--tab", required=True)
    s.set_defaults(func=cmd_clear_filter)

    s = sub.add_parser("sort", help="Sort a range by one or more columns")
    _add_common(s)
    s.add_argument("--range", required=True)
    s.add_argument(
        "--by", required=True,
        help="Comma-separated list like 'B:asc,C:desc'. Bare 'B' = ascending.",
    )
    s.set_defaults(func=cmd_sort)

    # ── escape hatch ──
    s = sub.add_parser(
        "batch-update",
        help="Send a raw Sheets batchUpdate requests[] array (escape hatch)",
    )
    _add_common(s)
    s.add_argument(
        "--requests", required=True,
        help="JSON array of request objects (inline or @file.json), or "
             "a full {requests:[...]} object",
    )
    s.set_defaults(func=cmd_batch_update)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    token = get_token(args.sa_key)
    try:
        return args.func(args, token)
    except urllib.error.HTTPError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
