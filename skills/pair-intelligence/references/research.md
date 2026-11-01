# Research and browse: the web, images and real pages

## Web search

`--mode research` gives Codex live web search from an empty temp directory.
Ask for the URL behind every claim and open the important ones yourself: the
search events record only the query, never the pages read, so the answer's
citations are the only trail.

Gemini has no web search here (OpenCode's search tool returns "Web search
cancelled"). It can fetch URLs you name, so give it the pages, or use Codex.

## Images

```bash
bash scripts/pair.sh --mode consult --image /abs/shot.png --prompt-file /abs/ask.md
```

- `--image` repeats. Codex opens each file by path with its image tool, Gemini
  receives them as attachments. Both work in read-only mode.
- Copy the image into a folder of its own first. A model looking at a screenshot
  will happily open the HTML, the answer key or the notes sitting next to it.
- Ask for each problem with where it is (coordinates or region), how severe, and
  whether it was seen or inferred, and for what it cannot judge from one image.
  Use the consult mode with `--cwd` set to the image's own folder and `--web off`.
  Then check: measure the pixels, or look yourself. In testing both
  engines found every planted defect and invented none.
- PDFs are not native input. Render pages to PNG or extract the text first, and
  say in the prompt which you did and how reliable the extraction is.

## Browse

```bash
bash scripts/pair.sh --engine codex --mode browse \
  --domains github.com,githubusercontent.com --prompt-file /abs/task.md
```

What the script does:

- starts a fresh, logged-out headless Chrome through agent-browser, **outside**
  the engine's sandbox, with its socket in a private temp directory;
- allows only the domains you pass, each plus its subdomains, marks page text as
  untrusted, and sends screenshots and downloads to `WORK_DIR/shots`;
- gives the engine one way in, a generated `pair-browser` command on its PATH. It
  runs as `bash -p` (so an exported `BASH_ENV` cannot run first), pins the
  browser's settings and ignores the caller's environment, and rebuilds every
  command from a fixed grammar: `open` and `read` take an http(s) URL, `click`,
  `wait`, `eval` and the like exactly one value, `fill` a target and a text,
  `snapshot` only `-i -c -d N -s TARGET`, `screenshot` only `--full --annotate
  --if-changed --threshold N` and one file name, which always lands in the shots
  folder. No other token that looks like a flag gets through, because
  agent-browser lifts global flags such as `--cdp` out of any position; `close`,
  `get cdp-url`, `wait -d` (a download path) and every other command are refused;
- closes the browser and kills its process on exit, even after a failure.

Per engine:

- **Gemini** has no sandbox, so its shell is confined by rule: `pair-browser` is
  the only command it may run (not `agent-browser`, not `curl`), and redirection
  and `$(...)` are refused. Tested: it drove the browser and could not close it.
- **Codex** runs with workspace write and network on, because its sandbox will not
  let it reach the browser's socket otherwise. Its shell is not filtered, so the
  wrapper is a convention for it, not a wall: it can reach any host with curl,
  and a model that sets out to read the wrapper can find the socket and drive the
  browser directly, which runs outside the sandbox and can write a screenshot
  anywhere you can. The allow-list still binds every page the browser loads.

List every domain the task needs: where redirects land, and the domains the page
loads its styles and scripts from (GitHub needs `githubassets.com` too), because
the allow-list blocks the page's own requests as well. Logged-in sites are not
supported, on purpose.

Screenshots stay in the temp working directory. Copy the ones the user should see
somewhere they can open, and verify each quote against the page or its raw
source before you repeat it.

This session holds untrusted page content and network access together, so keep
the prompt free of secrets, keep the working directory empty, browse only domains
you would trust with that (prefer Gemini when the pages are not), and verify every
quote against the page. In testing, a quote was exact but left out two relevant
passages the model had seen.

### Why it is built this way (tested 2026-11-01)

- Chrome crashes when started inside Codex's macOS sandbox, with or without
  `--no-sandbox`. Codex's own browser tools need the Codex desktop app.
- The browser client inside the sandbox replaces the host's browser with its own
  (which then crashes) unless both see identical `AGENT_BROWSER_*` variables.
- Codex cannot connect to the browser's socket without `network_access`.
- `~/.agent-browser` holds every session's socket and the saved-login key, which is
  why the socket lives in a private temp directory instead.
- OpenCode does not permission-check `export`, and matches deny patterns against
  the raw command text, so quoting hid flags from it. Checking arguments inside a
  wrapper, after the shell has parsed them, is what holds. Three review rounds by both engines
  found eight ways past earlier versions (flag position, `batch`, exported
  variables, quoting, a second screenshot path, `wait -d`, smuggled threshold
  values, `BASH_ENV`); each is a regression test in `scripts/test_pair.sh`.
- Unix socket paths are limited to 103 bytes, so that directory sits under `/tmp`.
