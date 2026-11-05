#!/usr/bin/env python3
"""Replace Gemini's grounding redirect links in an answer with the pages they point to.

agy's web search cites sources as vertexaisearch.cloud.google.com/grounding-api-redirect/...
links, which a reader cannot check as given (measured 2026-11-05: 40 in one research
answer). Each answers a plain request with a redirect to the source, so the source is
read from that one response's Location header; the page itself is never fetched.
Requests go only to that Google host: the links come from model output.

    pair_links.py <answer.md> <map.json>

Rewrites the answer in place, writes {redirect: source} to map.json, and prints how many
were resolved. A link that does not resolve stays as it was.
"""
import concurrent.futures
import http.client
import json
import os
import re
import sys
import urllib.parse

HOST = "vertexaisearch.cloud.google.com"
LINK = re.compile(r"https://vertexaisearch\.cloud\.google\.com/grounding-api-redirect/[A-Za-z0-9_\-=]+")
# Offline tests point the requests at a local server; the links matched stay the same.
ORIGIN = os.environ.get("PAIR_LINKS_ORIGIN", "https://" + HOST)


def resolve(link):
    path = urllib.parse.urlsplit(link).path
    origin = urllib.parse.urlsplit(ORIGIN)
    conn_cls = http.client.HTTPSConnection if origin.scheme == "https" else http.client.HTTPConnection
    try:
        conn = conn_cls(origin.hostname, origin.port, timeout=8)
        conn.request("HEAD", path)
        r = conn.getresponse()
        where = r.getheader("Location") or ""
        conn.close()
    except (OSError, http.client.HTTPException):
        return None
    if r.status in (301, 302, 303, 307, 308) and where.startswith(("https://", "http://")):
        return where
    return None


def main():
    answer, mapping = sys.argv[1], sys.argv[2]
    with open(answer, encoding="utf-8", errors="replace") as f:
        text = f.read()
    links = list(dict.fromkeys(LINK.findall(text)))[:300]
    if not links:
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        found = dict(zip(links, pool.map(resolve, links)))
    resolved = {k: v for k, v in found.items() if v}
    # Longest first, so no link is replaced inside a longer one.
    for link in sorted(resolved, key=len, reverse=True):
        text = text.replace(link, resolved[link])
    with open(answer, "w", encoding="utf-8") as f:
        f.write(text)
    with open(mapping, "w") as f:
        json.dump(resolved, f, indent=2)
    print("resolved %d of %d Gemini source links (map: %s)" % (len(resolved), len(links), mapping))


if __name__ == "__main__":
    main()
