# tavily-extract

Fetch the pages a normal fetcher can't — the JavaScript-rendered SPAs and bot-protected (403) hosts where a plain HTTP GET returns an empty shell or a "Loading…" skeleton. Wraps the **Tavily Extract** API, which runs the page's JavaScript and fetches through browser-like infrastructure, to return clean markdown. Batches up to 20 URLs per call, and also does Tavily web search.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

A normal fetch returns raw HTML. For a JavaScript-rendered SPA that HTML is an *empty shell* — the content is hydrated in the browser — and bot-protected hosts answer 403. This is a structural limit, not a tuning problem: a fetcher that executes no JS cannot see a client-rendered page, no matter what headers you send.

The subtlety that makes this a skill rather than a one-liner is that **the right tool is layered, and the cheap one usually wins**:

1. **Try the built-in fetcher first.** It's free and handles most sites, including many JS-framework doc pages that *server-render* their content. Even the same domain can differ — `developers.openai.com/api/docs/...` server-renders and reads fine; `developers.openai.com/cookbook/...` is client-rendered and comes back a 404 shell.
2. **Then Tavily Extract** — the JS-rendering and anti-block tool, when step 1 returns a shell, truncated content, or a 403.
3. **But for *structured* data, the site's own API beats any scrape.** Rendered charts serialize to axis labels, not numbers. Artificial Analysis, for instance, exposes `GET /api/v2/data/llms/models` with an `x-api-key` — one authenticated call beats extracting markdown and re-parsing it.

Reaching for step 2 on pages step 1 already handles just costs credits and adds a hop.

## What it does

```
URL(s) ──▶ Tavily Extract (runs the page's JS, browser-like fetch)
                    │
        --query reranks/trims toward your intent
                    │
                    ▼
        clean markdown ──▶ stdout, or one <slug>.md per URL with --save
                    │
        soft-404 detector warns on HTTP-200 "Page not found" bodies
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install utilities@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/tavily-extract" ~/.claude/skills/tavily-extract
```

## Requirements

Python 3 (stdlib only) and a Tavily API key from [app.tavily.com](https://app.tavily.com). The script reads it in this order: `$TAVILY_API_KEY`, then `~/.config/tavily/api-key`.

```bash
export TAVILY_API_KEY=tvly-...
# or, persistent:
mkdir -p ~/.config/tavily && printf 'tvly-...' > ~/.config/tavily/api-key
chmod 600 ~/.config/tavily/api-key
```

Never hardcode the key in a command you commit.

## Quick start

The first argument may be a bare URL — it defaults to `extract`.

```bash
SC=scripts/tavily_extract.py

# One page → clean markdown on stdout
"$SC" https://lmarena.ai/leaderboard/agent

# Focus the extraction (reranks/trims toward your intent — cuts nav boilerplate)
"$SC" https://artificialanalysis.ai/models/gemini-3-6-flash --query "intelligence index and price"

# Batch (up to 20 URLs), saving one <slug>.md per URL instead of printing
"$SC" extract URL1 URL2 URL3 --save /tmp/out

# Cheaper/faster, less content
"$SC" URL --depth basic

# Web search (finds URLs; returns an answer + ranked results)
"$SC" search "Gemini 3.6 Flash release date" --max-results 5
```

## Flags

| Flag | Default | Description |
|---|---|---|
| `--depth {basic,advanced}` | `advanced` | `advanced` returns more content including tables; `basic` is cheaper |
| `--format {markdown,text}` | `markdown` | Output format |
| `--query TEXT` | — | Rerank and trim the extraction toward this intent |
| `--chunks 1-5` | — | How many content chunks to return |
| `--save DIR` | — | Write one `<slug>.md` per URL instead of printing |
| `--max-results N` | — | `search` only |

## Gotchas

- **Soft 404s.** A rendered SPA can return **HTTP 200 with a "Page not found" body**, often buried under nav chrome — so the response is *long*, not empty, and reads as success. The script scans for this and prints `[warn] … likely a soft 404`. Heed it; verify the URL rather than treating a nav shell as content.
- **Nav boilerplate.** Extracts of doc sites often lead with hundreds of lines of navigation before the real content. Use `--query` to rerank, or just grep the output. **Don't add an HTML parser** (trafilatura and friends) — Tavily already content-extracts, and for an SPA there's no rendered HTML left to re-parse anyway.
- **20-URL cap** per extract call. The script warns and takes the first 20 if you pass more; split larger batches yourself.
- **Cost.** `advanced` ≈ 2 credits per 5 URLs, `basic` ≈ 1 per 5. Pass `--depth basic` when you don't need tables or embedded content. Usage prints to stderr as `[usage]`.
- **Structured data beats scraping.** If the site has an API, use it. Rendered charts give you axis labels, not the numbers behind them.

## Caveats

- This is a paid API. It's the right tool for pages that structurally can't be fetched otherwise — not a default fetcher.
- The bundled script covers the common cases. For `include_images`, `topic`, and the rest, add fields to `scripts/tavily_extract.py`; full API docs are at [docs.tavily.com](https://docs.tavily.com/documentation/api-reference/endpoint/extract).

## License

MIT — see [LICENSE](../../LICENSE).
