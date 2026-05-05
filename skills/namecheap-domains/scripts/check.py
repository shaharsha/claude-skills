#!/usr/bin/env python3
"""Check domain availability via the Namecheap API.

Usage:
    check.py domain1.com domain2.ai ...
    check.py --file domains.txt
    check.py --base myname --tlds com,io,ai,dev,co
    check.py foo.com bar.io --available-only
    check.py foo.com bar.io --json

Credentials: env vars NAMECHEAP_API_USER / NAMECHEAP_API_KEY /
NAMECHEAP_CLIENT_IP, or a `## Namecheap` section in
~/.claude/projects/-Users-shaharshavit/memory/api-keys.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

API_URL = "https://api.namecheap.com/xml.response"
NS = {"nc": "http://api.namecheap.com/xml.response"}
BATCH_MAX = 50  # Namecheap hard cap — verified 2026-04-24
CREDS_FILE = Path.home() / ".claude/projects/-Users-shaharshavit/memory/api-keys.md"


def load_creds() -> tuple[str, str, str]:
    user = os.environ.get("NAMECHEAP_API_USER")
    key = os.environ.get("NAMECHEAP_API_KEY")
    ip = os.environ.get("NAMECHEAP_CLIENT_IP")
    if user and key and ip:
        return user, key, ip

    if CREDS_FILE.exists():
        text = CREDS_FILE.read_text()
        m = re.search(r"##\s*Namecheap\b(.*?)(?=^##\s|\Z)", text, re.S | re.M)
        if m:
            block = m.group(1)

            def grab(label: str) -> str | None:
                mm = re.search(rf"\*\*{label}\*\*:\s*`([^`]+)`", block)
                return mm.group(1) if mm else None

            user = user or grab("API User")
            key = key or grab("API Key")
            ip = ip or grab("Whitelisted IP")

    if not (user and key and ip):
        sys.exit(
            "error: missing Namecheap credentials. Set NAMECHEAP_API_USER / "
            "NAMECHEAP_API_KEY / NAMECHEAP_CLIENT_IP, or add a `## Namecheap` "
            f"section to {CREDS_FILE}."
        )
    return user, key, ip


def check(domains: list[str], creds: tuple[str, str, str]) -> list[dict]:
    user, key, ip = creds
    params = {
        "ApiUser": user,
        "ApiKey": key,
        "UserName": user,
        "ClientIp": ip,
        "Command": "namecheap.domains.check",
        "DomainList": ",".join(domains),
    }
    with urlopen(f"{API_URL}?{urlencode(params)}", timeout=30) as resp:
        body = resp.read().decode()

    root = ET.fromstring(body)
    if root.attrib.get("Status") != "OK":
        errs = [e.text for e in root.findall("nc:Errors/nc:Error", NS)]
        raise RuntimeError(f"Namecheap API error: {errs or body}")

    out = []
    for r in root.findall("nc:CommandResponse/nc:DomainCheckResult", NS):
        a = r.attrib
        out.append({
            "domain": a["Domain"],
            "available": a["Available"] == "true",
            "premium": a.get("IsPremiumName") == "true",
            "premium_price": float(a.get("PremiumRegistrationPrice", 0) or 0),
            "icann_fee": float(a.get("IcannFee", 0) or 0),
            "eap_fee": float(a.get("EapFee", 0) or 0),
        })
    return out


def check_bulk(domains: list[str], creds: tuple[str, str, str]) -> list[dict]:
    seen: set[str] = set()
    unique: list[str] = []
    for d in domains:
        d = d.strip().lower()
        if d and d not in seen:
            seen.add(d)
            unique.append(d)
    results: list[dict] = []
    for i in range(0, len(unique), BATCH_MAX):
        results.extend(check(unique[i : i + BATCH_MAX], creds))
    return results


def expand_tlds(bases: list[str], tlds: list[str]) -> list[str]:
    return [f"{b}.{t.lstrip('.')}" for b in bases for t in tlds]


def main() -> int:
    ap = argparse.ArgumentParser(description="Namecheap domain availability checker")
    ap.add_argument("domains", nargs="*", help="explicit domains to check")
    ap.add_argument("--file", help="read one domain per line")
    ap.add_argument("--base", action="append", default=[],
                    help="base name (repeatable) to combine with --tlds")
    ap.add_argument("--tlds", help="comma-separated TLDs for --base, e.g. com,io,ai")
    ap.add_argument("--available-only", action="store_true",
                    help="print only available domains")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()

    domains = list(args.domains)
    if args.file:
        domains += [ln.strip() for ln in Path(args.file).read_text().splitlines() if ln.strip()]
    if args.base:
        if not args.tlds:
            ap.error("--base requires --tlds")
        domains += expand_tlds(args.base, [t.strip() for t in args.tlds.split(",") if t.strip()])
    if not domains:
        ap.error("no domains given (pass positional args, --file, or --base/--tlds)")

    results = check_bulk(domains, load_creds())
    if args.available_only:
        results = [r for r in results if r["available"]]

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for r in results:
        mark = "AVAILABLE" if r["available"] else "taken    "
        tag = ""
        if r["premium"]:
            tag = f" [premium ${r['premium_price']:.2f}]"
        if r["eap_fee"] > 0:
            tag += f" [EAP +${r['eap_fee']:.2f}]"
        print(f"{mark}  {r['domain']}{tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
