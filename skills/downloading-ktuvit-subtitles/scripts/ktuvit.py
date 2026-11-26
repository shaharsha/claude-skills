#!/usr/bin/env python3
"""ktuvit.me client: search titles, list a movie's or an episode's Hebrew subtitles, download one.

  python3 ktuvit.py search "Prisoners" --year 2013
  python3 ktuvit.py search "Breaking Bad" --series
  python3 ktuvit.py list <film_id>                         # movie
  python3 ktuvit.py list <series_id> --season 2 --episode 3
  python3 ktuvit.py download <film_or_series_id> <subtitle_id> -o out.srt

Search needs no account. list and download log in. Credentials are never printed:
KTUVIT_EMAIL + KTUVIT_PASSWORD env vars if set, else the Proton Pass login item named by
--pass-item (default: $KTUVIT_PASS_ITEM or "ktuvit") in --vault (default "Personal").
Add --json to search/list for machine-readable output.

Python standard library only. The login hash needs AES: the `openssl` command (present on macOS and
Linux), or the `cryptography` package if it is installed.
"""
import argparse
import base64
import hashlib
import html
import http.cookiejar
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.request
from html.parser import HTMLParser

BASE = "https://www.ktuvit.me/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130 Safari/537.36")
# Sent with HTTP 200 instead of the file, now and then. Retrying with a new identifier fixes it.
NOT_FOUND = "הבקשה לא נמצאה"
NO_SUBS = "אין כתוביות"


# ---------- login password hash (port of the site's LoginHandler.js Encrypt) ----------
SALT = "C8928DC731EC4E30AE6C523A34BE353A"  # `encryptionSalt` in every ktuvit page


def _js_parseint_hex(s):
    n = None
    for ch in s:
        if ch not in "0123456789abcdefABCDEF":
            break
        n = (n or 0) * 16 + int(ch, 16)
    return n  # None plays the role of JS NaN


def _cryptojs_hex_parse_iv(s):
    # The site calls CryptoJS.enc.Hex.parse(email): garbage-in, but deterministic. AES uses 16 bytes.
    words = [0] * max(4, math.ceil(len(s) / 8))
    for i in range(0, len(s), 2):
        v = _js_parseint_hex(s[i:i + 2]) or 0
        words[i >> 3] |= (v << (24 - (i % 8) * 4)) & 0xFFFFFFFF
    return b"".join(w.to_bytes(4, "big") for w in words[:4])


def _aes128_cbc(key, iv, data):
    try:
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        padder = padding.PKCS7(128).padder()
        enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        return enc.update(padder.update(data) + padder.finalize()) + enc.finalize()
    except ImportError:
        r = subprocess.run(["openssl", "enc", "-aes-128-cbc", "-K", key.hex(), "-iv", iv.hex()],
                           input=data, capture_output=True)
        if r.returncode:
            sys.exit("the login hash needs `openssl` on PATH or `pip install cryptography`")
        return r.stdout  # openssl pads with PKCS7 by default


def password_hash(email, password):
    key = hashlib.pbkdf2_hmac("sha1", SALT.encode(), email.encode(), 3000, 16)
    ct = _aes128_cbc(key, _cryptojs_hex_parse_iv(email), password.encode())
    return base64.b64encode(hashlib.sha256(ct).digest()).decode()


# ---------- session ----------
class Session:
    """The few bits of requests.Session this needs: cookies, JSON POST, GET."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.headers = {"User-Agent": UA, "Accept-Language": "he,en;q=0.8"}

    def _open(self, url, data=None, extra=None, timeout=20):
        req = urllib.request.Request(url, data=data, headers={**self.headers, **(extra or {})})
        with self.opener.open(req, timeout=timeout) as r:
            return r.read(), r.headers

    def post_json(self, url, payload):
        body, _ = self._open(url, json.dumps(payload).encode(), {"Content-Type": "application/json; charset=utf-8"})
        return json.loads(json.loads(body)["d"])

    def get(self, url, timeout=20):
        return self._open(url, timeout=timeout)

    def has_cookie(self, name):
        return any(c.name == name for c in self.jar)


def credentials(pass_item, vault):
    if os.environ.get("KTUVIT_EMAIL") and os.environ.get("KTUVIT_PASSWORD"):
        return os.environ["KTUVIT_EMAIL"], os.environ["KTUVIT_PASSWORD"]

    def field(name):
        r = subprocess.run(["pass-cli", "item", "view", "--vault-name", vault, "--item-title", pass_item,
                            "--field", name], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""

    email = field("email") or field("username")
    password = field("password")
    if not (email and "@" in email and password):
        sys.exit(f"no ktuvit credentials: set KTUVIT_EMAIL/KTUVIT_PASSWORD or create Proton Pass login "
                 f"'{pass_item}' in vault '{vault}' with an email and password (the site logs in by email)")
    return email, password


def session(login=True, pass_item="ktuvit", vault="Personal"):
    s = Session()
    if login:
        email, pw = credentials(pass_item, vault)
        res = s.post_json(BASE + "Services/MembershipService.svc/Login",
                          {"request": {"Email": email, "Password": password_hash(email, pw)}})
        if not res.get("IsSuccess") or not s.has_cookie("Login"):
            sys.exit(f"login failed: {res.get('ErrorMessage') or 'no Login cookie'}")
    return s


# ---------- search ----------
def search(s, name, year="", series=False):
    def run(y):
        q = {"FilmName": name, "Actors": [], "Studios": None, "Directors": [], "Genres": [], "Countries": [],
             "Languages": [], "Year": str(y or ""), "Rating": [], "Page": 1,
             "SearchType": "1" if series else "0", "WithSubsOnly": False}
        return s.post_json(BASE + "Services/ContentProvider.svc/SearchPage_search", {"request": q})["Films"]
    films = run(year)
    if not films and year:  # some catalog entries have no year set
        films = run("")
    return films


# ---------- list ----------
class _Rows(HTMLParser):
    """Collects each <tr>: per-<td> text, the first-<td> <small> labels, and data-subtitle-id."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.td, self.small, self.depth_div = [], None, None, None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self.row = {"tds": [], "smalls": [], "release_parts": [], "sid": None}
        elif self.row is None:
            return
        elif tag == "td":
            self.td = []
            self.row["tds"].append(self.td)
        elif tag == "small":
            self.small = []
        elif tag == "br" and len(self.row["tds"]) == 1:
            self.row["release_done"] = True
        if self.row is not None and a.get("data-subtitle-id") and not self.row["sid"]:
            self.row["sid"] = a["data-subtitle-id"]

    def handle_endtag(self, tag):
        if tag == "small" and self.small is not None and self.row is not None:
            self.row["smalls"].append(" ".join("".join(self.small).split()))
            self.small = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.row is None or self.td is None:
            return
        self.td.append(data)
        if self.small is not None:
            self.small.append(data)
        elif len(self.row["tds"]) == 1 and not self.row.get("release_done"):
            self.row["release_parts"].append(data)


def _parse_rows(page):
    p = _Rows()
    p.feed(page)
    subs = []
    for row in p.rows:
        tds = [" ".join("".join(t).split()) for t in row["tds"]]
        if not row["sid"] or len(tds) < 5:
            continue
        meta = {}
        for t in row["smalls"]:
            for key, label in (("translator", "תרגום"), ("synced_by", "סנכרון"), ("uploader", 'הועלה ע"י')):
                if t.startswith(label):
                    meta[key] = t.split(":", 1)[1].strip()
        try:
            downloads = int(tds[4])
        except ValueError:
            downloads = 0
        release = " ".join("".join(row["release_parts"]).split())
        subs.append({"release": html.unescape(release).lstrip("_"), "format": tds[1], "size": tds[2],
                     "uploaded": tds[3], "downloads": downloads, "translator": meta.get("translator", ""),
                     "synced_by": meta.get("synced_by", ""), "uploader": meta.get("uploader", ""),
                     "subtitle_id": row["sid"]})
    subs.sort(key=lambda x: -x["downloads"])
    # Same size + same translator is almost always the same file uploaded under several release names.
    first = {}
    for i, x in enumerate(subs, 1):
        k = (x["size"], x["translator"])
        x["rank"] = i
        x["same_file_as"] = first.get(k)
        first.setdefault(k, i)
    return subs


def list_subs(s, film_id, season=None, episode=None):
    if season is not None and episode is not None:
        url = (f"{BASE}Services/GetModuleAjax.ashx?moduleName=SubtitlesList"
               f"&SeriesID={film_id}&Season={season}&Episode={episode}")
    else:
        url = BASE + "MovieInfo.aspx?ID=" + film_id
    page = s.get(url)[0].decode("utf-8", "replace")
    if "התחבר על מנת להציג את התוכן" in page:
        sys.exit("ktuvit hid the list: the session is not logged in")
    return _parse_rows(page)


# ---------- download ----------
def download(s, film_id, sub_id, out, attempts=10):
    req = {"FilmID": film_id, "SubtitleID": sub_id, "FontSize": 0, "FontColor": "", "PredefinedLayout": -1}
    for attempt in range(1, attempts + 1):
        res = s.post_json(BASE + "Services/ContentProvider.svc/RequestSubtitleDownload", {"request": req})
        if not res.get("IsSuccess"):
            sys.exit(f"download request refused: {res.get('ErrorMessage')} (not logged in, or wrong FilmID)")
        time.sleep(res.get("ValidIn", 0) + 0.5)
        content, headers = s.get(BASE + "Services/DownloadFile.ashx?DownloadIdentifier=" + res["DownloadIdentifier"],
                                 timeout=30)
        if len(content) > 500 and NOT_FOUND.encode() not in content[:300]:
            name = re.search(r'filename="?([^";]+)', headers.get("Content-Disposition", "") or "")
            name = name.group(1) if name else ""
            if content[:2] == b"PK":  # some uploads are zips holding several syncs
                return _unzip(content, out), name
            with open(out, "wb") as f:
                f.write(content)
            return [out], name
        time.sleep(min(2 + attempt, 5))  # measured: ~40% of single tries succeed, independent of client
    sys.exit(f"download failed after {attempts} tries: ktuvit kept answering '{NOT_FOUND}'. It is "
             f"intermittent: run the command again in a minute, or download an entry marked 'same file as' "
             f"this one.")


def _unzip(blob, out):
    import io
    import zipfile
    folder = os.path.splitext(out)[0] + "_zip"
    os.makedirs(folder, exist_ok=True)
    saved = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for m in z.infolist():
            base = os.path.basename(m.filename)
            if m.is_dir() or not base.lower().endswith((".srt", ".ass", ".ssa", ".sub", ".vtt")):
                continue
            path = os.path.join(folder, base)
            with open(path, "wb") as f:
                f.write(z.read(m))
            saved.append(path)
    return saved


# ---------- CLI ----------
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pass-item", default=os.environ.get("KTUVIT_PASS_ITEM", "ktuvit"))
    p.add_argument("--vault", default=os.environ.get("KTUVIT_PASS_VAULT", "Personal"))
    p.add_argument("--json", action="store_true")
    sp = p.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("search")
    a.add_argument("name")
    a.add_argument("--year", default="")
    a.add_argument("--series", action="store_true", help="search TV series instead of movies")
    a = sp.add_parser("list")
    a.add_argument("film_id")
    a.add_argument("--season", type=int)
    a.add_argument("--episode", type=int)
    a = sp.add_parser("download")
    a.add_argument("film_id", help="the movie ID, or the series ID for an episode")
    a.add_argument("subtitle_id")
    a.add_argument("-o", "--out", required=True)
    args = p.parse_args()

    if args.cmd == "search":
        films = search(session(login=False), args.name, args.year, args.series)
        if args.json:
            print(json.dumps([{k: f.get(k) for k in ("ID", "EngName", "HebName", "ReleaseDate", "IsSeries",
                                                      "NumOfSubs", "ImdbID")} for f in films], ensure_ascii=False))
        for f in [] if args.json else films:
            kind = "series" if f.get("IsSeries") else "movie"
            print(f'{f["ID"]}  {f["EngName"]} / {f["HebName"]} ({f["ReleaseDate"]}) {kind} '
                  f'subs={f["NumOfSubs"]} imdb={f.get("ImdbID")}')
        return

    s = session(pass_item=args.pass_item, vault=args.vault)
    if args.cmd == "list":
        if (args.season is None) != (args.episode is None):
            sys.exit("give both --season and --episode for an episode, or neither for a movie")
        subs = list_subs(s, args.film_id, args.season, args.episode)
        if args.json:
            print(json.dumps(subs, ensure_ascii=False, indent=1))
            return
        for x in subs:
            who = " | ".join(f"{lbl} {x[k]}" for lbl, k in (("tr:", "translator"), ("sync:", "synced_by"),
                                                             ("up:", "uploader")) if x[k])
            dup = f"  (same file as #{x['same_file_as']})" if x["same_file_as"] else ""
            print(f'#{x["rank"]:<3} {x["downloads"]:>5} dl  {x["size"]:>9}  {x["uploaded"]}  {x["release"]}\n'
                  f'      {who}  id={x["subtitle_id"]}{dup}')
        print(f"{len(subs)} subtitles")
    else:
        files, name = download(s, args.film_id, args.subtitle_id, args.out)
        if len(files) == 1 and files[0] == args.out:
            print(f"saved {args.out} ({os.path.getsize(args.out)} bytes; ktuvit's name: {name})")
        else:
            print(f"ktuvit sent a zip ({name}); extracted {len(files)} subtitle files, pick one:")
            for f in files:
                print(f"  {f}")


if __name__ == "__main__":
    main()
