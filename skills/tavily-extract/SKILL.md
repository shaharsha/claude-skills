---
name: tavily-extract
description: Use when a web page won't come through a normal fetch — WebFetch (or curl) returns an empty shell, a "Loading…" skeleton, or a 403/Forbidden. That happens on JavaScript-rendered single-page apps (React/Next.js/Vue dashboards, leaderboards and docs such as Artificial Analysis, LMArena, developers.openai.com, platform.claude.com) and on bot-protected hosts (Cloudflare/WAF). This skill calls the Tavily Extract API to run the page's JavaScript and return clean markdown, and can batch up to 20 URLs in one call; it also does Tavily web search. Reach for it when WebFetch comes back empty, truncated, a skeleton, or blocked, or when a task says "the SPA/client-rendered page won't fetch", "I got a 403", "scrape the data behind the JS", "the charts/tables won't come through", or "extract these N URLs". Try WebFetch first — it's free and handles server-rendered sites; use this when it can't.
---

# Tavily Extract

## Core principle

A normal fetch returns the raw HTML. For a **JavaScript-rendered SPA** that HTML is an empty shell (content is hydrated in the browser), and **bot-protected hosts** answer **403**. Tavily *runs the page's JavaScript* and fetches through browser-like infrastructure, so it returns the **rendered** content as markdown — the one thing WebFetch structurally can't do (it executes no JS and is more easily blocked).

## When to use / when NOT

Use the cheapest tool that works, in this order:

1. **WebFetch first** — free, built in, and it handles most sites, including many JS-framework doc pages that *server-render* their content. Same domain can differ: `developers.openai.com/api/docs/...` server-renders and WebFetch reads it; `developers.openai.com/cookbook/...` is client-rendered and comes back a 404 shell.
2. **This skill (Tavily Extract)** — when WebFetch returns a shell/skeleton, truncated content, or a 403. This is the JS-rendering + anti-block tool.
3. **The site's own API / embedded JSON** — for *structured* data (leaderboards, metrics), a real API beats any scrape. Artificial Analysis, for example, exposes `GET https://artificialanalysis.ai/api/v2/data/llms/models` with an `x-api-key`; its rendered charts are JS data-viz that serialize to axis labels, not numbers. When you need exact figures, prefer the API.

Do **not** reach for this on pages WebFetch already handles — it costs credits and adds a hop.

## Setup (one-time)

Needs a Tavily API key (get one at https://app.tavily.com). The script reads it in this order: `$TAVILY_API_KEY`, then `~/.config/tavily/api-key`. Set either:

```bash
export TAVILY_API_KEY=tvly-...
# or, persistent:
mkdir -p ~/.config/tavily && printf 'tvly-...' > ~/.config/tavily/api-key && chmod 600 ~/.config/tavily/api-key
```

Never hardcode the key in a command you commit or in this repo. (Shahar's key already lives in `api-keys.md` under "Tavily" and in `~/.config/tavily/api-key`.)

## Quick reference

Run the bundled script (it's executable; `python3` also works). The first argument may be a bare URL — it defaults to `extract`.

```bash
SC=scripts/tavily_extract.py            # relative to this skill's directory

# One page -> clean markdown on stdout
"$SC" https://lmarena.ai/leaderboard/agent

# Focus the extraction (reranks/trims toward your intent — cuts nav boilerplate)
"$SC" https://artificialanalysis.ai/models/gemini-3-6-flash --query "intelligence index and price"

# Batch (up to 20 URLs) and save one <slug>.md per URL instead of printing
"$SC" extract URL1 URL2 URL3 --save /tmp/out

# Cheaper/faster (less content): basic depth
"$SC" URL --depth basic

# Web search (finds URLs; returns an answer + ranked results)
"$SC" search "Gemini 3.6 Flash release date" --max-results 5
```

Options: `--depth {basic,advanced}` (default `advanced` — more content incl. tables; `basic` is cheaper), `--format {markdown,text}`, `--query TEXT`, `--chunks 1-5`, `--save DIR`.

## Gotchas

- **Soft 404s.** A rendered SPA can return **HTTP 200 with a "Page not found" body** (often buried under nav chrome, so the response is *long*, not empty). The script scans for that and prints `[warn] … likely a soft 404` — heed it; don't treat the nav shell as real content. Verify the URL if you see it.
- **Nav boilerplate.** Extracts of doc sites often lead with hundreds of lines of navigation before the real content. Use `--query` to rerank toward your intent, or just `grep` the output for the section you need — don't add an HTML parser (trafilatura etc.): Tavily already content-extracts, and there's no rendered HTML to re-parse for an SPA anyway.
- **20-URL cap** per extract call; the script warns and takes the first 20 if you pass more. Split larger batches.
- **Cost.** `advanced` depth ≈ 2 credits / 5 URLs, `basic` ≈ 1 / 5. Pass `--depth basic` when you don't need tables/embedded content. Usage is printed to stderr as `[usage]`.
- **Structured data > scrape.** If the site has an API (see step 3 above), one authenticated call beats extracting rendered markdown and re-parsing it.

## Reference

Full API docs: https://docs.tavily.com/documentation/api-reference/endpoint/extract — the script covers the common cases; add fields to `scripts/tavily_extract.py` if you need `include_images`, `topic`, etc.
