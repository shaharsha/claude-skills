#!/usr/bin/env python3
"""Tavily Extract / Search CLI — fetch pages the built-in fetcher can't.

Why this exists: a plain HTTP fetch (and Claude Code's WebFetch) returns the raw
HTML. For JavaScript-rendered SPAs that HTML is an empty shell, and bot-protected
hosts answer 403. Tavily runs the page (executes JS) and fetches through
browser-like infrastructure, so it returns the *rendered* content as clean
markdown — which is exactly what WebFetch can't do.

Stdlib only (urllib) so it runs anywhere with Python 3, no `pip install`.

Key resolution order (first hit wins):
  1. $TAVILY_API_KEY
  2. ~/.config/tavily/api-key   (first line)
See `--help` for usage; the SKILL.md covers when to reach for this vs WebFetch.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

EXTRACT_URL = "https://api.tavily.com/extract"
SEARCH_URL = "https://api.tavily.com/search"
MAX_URLS = 20  # Tavily's hard cap per extract call


def load_key() -> str:
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if key:
        return key
    keyfile = Path.home() / ".config" / "tavily" / "api-key"
    if keyfile.is_file():
        key = keyfile.read_text(encoding="utf-8").strip()
        if key:
            return key
    sys.exit(
        "No Tavily API key found. Set it once, either:\n"
        "  export TAVILY_API_KEY=tvly-...        (this shell)\n"
        "  mkdir -p ~/.config/tavily && printf 'tvly-...' > ~/.config/tavily/api-key && chmod 600 ~/.config/tavily/api-key\n"
        "Get a key at https://app.tavily.com (the SKILL.md notes where an existing key may already live)."
    )


def post(endpoint: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Authorization": f"Bearer {load_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        sys.exit(f"Tavily API error {e.code}: {body}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error reaching Tavily: {e.reason}")


def slug(url: str) -> str:
    s = re.sub(r"^https?://", "", url)
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")
    return (s[:80] or "page")


SOFT_404_PHRASES = (
    "page not found", "couldn't find that page", "couldn’t find that page",
    "we looked everywhere", "404 not found", "this page could not be found",
    "page could not be found", "page doesn't exist", "page does not exist",
)


def looks_like_soft_404(text: str) -> bool:
    """A rendered SPA can return HTTP 200 with a 'Page not found' body — catch it so
    a genuine miss isn't mistaken for real content. The 404 marker is often buried
    below nav chrome (so the body isn't short), hence a whole-text phrase scan rather
    than a length+prefix check. It's a warning, not fatal — the agent should still
    eyeball the result."""
    t = text.lower()
    if any(p in t for p in SOFT_404_PHRASES):
        return True
    return len(text.strip()) < 200  # near-empty shell = failed render


def cmd_extract(args: argparse.Namespace) -> int:
    urls = args.urls
    if len(urls) > MAX_URLS:
        print(f"[warn] {len(urls)} URLs given; Tavily caps at {MAX_URLS} per call — extracting the first {MAX_URLS}.", file=sys.stderr)
        urls = urls[:MAX_URLS]
    payload = {
        "urls": urls,
        "extract_depth": args.depth,
        "format": args.format,
        "include_usage": True,
    }
    if args.query:
        payload["query"] = args.query  # reranks/trims returned content toward this intent (cuts nav boilerplate)
    if args.chunks:
        payload["chunks_per_source"] = args.chunks

    resp = post(EXTRACT_URL, payload)
    results = resp.get("results", []) or []
    failed = resp.get("failed_results", []) or []

    if args.save:
        outdir = Path(args.save).expanduser()
        outdir.mkdir(parents=True, exist_ok=True)

    for r in results:
        url = r.get("url", "?")
        content = r.get("raw_content") or ""
        if looks_like_soft_404(content):
            print(f"[warn] {url} returned a 'page not found' body ({len(content)} chars) — likely a soft 404, not real content.", file=sys.stderr)
        if args.save:
            path = Path(args.save).expanduser() / f"{slug(url)}.md"
            path.write_text(content, encoding="utf-8")
            print(f"saved {url} -> {path} ({len(content):,} chars)")
        else:
            print(f"\n===== {url} ({len(content):,} chars) =====\n")
            print(content)

    for f in failed:
        print(f"[failed] {f.get('url','?')}: {f.get('error','extraction failed')}", file=sys.stderr)

    usage = resp.get("usage") or resp.get("request_id")
    if isinstance(resp.get("usage"), dict):
        print(f"[usage] {resp['usage']}", file=sys.stderr)
    return 0 if results else 1


def cmd_search(args: argparse.Namespace) -> int:
    payload = {
        "query": args.query,
        "max_results": args.max_results,
        "search_depth": args.depth,
        "include_answer": True,
    }
    if args.topic:
        payload["topic"] = args.topic
    resp = post(SEARCH_URL, payload)

    answer = resp.get("answer")
    if answer:
        print(f"ANSWER: {answer}\n")
    for i, r in enumerate(resp.get("results", []) or [], 1):
        title = r.get("title", "?")
        url = r.get("url", "?")
        score = r.get("score")
        snippet = (r.get("content") or "").strip().replace("\n", " ")
        score_s = f" (score {score:.2f})" if isinstance(score, (int, float)) else ""
        print(f"{i}. {title}{score_s}\n   {url}\n   {snippet[:300]}\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="tavily",
        description="Fetch JS-rendered / bot-blocked pages via Tavily (what WebFetch can't). Default command: extract.",
    )
    sub = p.add_subparsers(dest="cmd")

    e = sub.add_parser("extract", help="Render one or more URLs to clean markdown (up to 20 per call).")
    e.add_argument("urls", nargs="+", help="One or more URLs (max 20).")
    e.add_argument("--depth", choices=["basic", "advanced"], default="advanced",
                   help="advanced (default) pulls more, incl. tables/embedded content; basic is cheaper.")
    e.add_argument("--format", choices=["markdown", "text"], default="markdown")
    e.add_argument("--query", help="Rerank/trim the returned content toward this intent — cuts nav boilerplate.")
    e.add_argument("--chunks", type=int, choices=range(1, 6), help="chunks_per_source 1-5 (default 3).")
    e.add_argument("--save", metavar="DIR", help="Write one <slug>.md per URL into DIR instead of printing.")
    e.set_defaults(func=cmd_extract)

    s = sub.add_parser("search", help="Web search (finds URLs). Secondary to extract.")
    s.add_argument("query", help="Search query.")
    s.add_argument("--max-results", type=int, default=5)
    s.add_argument("--depth", choices=["basic", "advanced"], default="basic")
    s.add_argument("--topic", choices=["general", "news"], help="Optional topic filter.")
    s.set_defaults(func=cmd_search)

    # Default to `extract` when the first arg is a URL (ergonomics: `tavily <url>`).
    argv = sys.argv[1:]
    if argv and argv[0] not in {"extract", "search", "-h", "--help"}:
        argv = ["extract"] + argv
    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
