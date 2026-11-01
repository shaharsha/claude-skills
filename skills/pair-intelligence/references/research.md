# Research and browse: the web, images and real pages

## Web search

`--mode research` gives the model live web access from an empty temp directory.
Ask for the URL behind every claim and open the important ones yourself.

- **Codex** searches at OpenAI. Its events record only the query, never the pages
  read, so the answer's citations are the only trail.
- **Gemini on agy** searches Google (`search_web`) and reads pages with
  `pair-fetch <url>`; both show in `RUN_DIR/tools.txt`. Under `--web cached`
  (consult and ideate) it can search but not open pages, so its claims rest on
  snippets: use research mode, or `--web live`, when the pages matter.
- **Gemini on OpenCode** has no search (its search tool returns "Web search
  cancelled"); it fetches URLs it knows or guesses.

## Images

```bash
bash scripts/pair.sh --mode consult --image /abs/shot.png --prompt-file /abs/ask.md
```

- `--image` repeats. Codex opens each file by path with its image tool, Gemini on
  agy with its file reader (the gate allows exactly those paths), Gemini on
  OpenCode as attachments. All work in read-only mode.
- Copy the image into a folder of its own first. A model looking at a screenshot
  will happily open the HTML, the answer key or the notes sitting next to it.
- Ask for each problem with where it is (coordinates or region), how severe, and
  whether it was seen or inferred, and for what it cannot judge from one image.
  Use the consult mode with `--cwd` set to the image's own folder and `--web off`.
  Then check: measure the pixels, or look yourself. In testing both
  engines found every planted defect and invented none.
- PDFs are not native input. Render pages to PNG or extract the text first, and
  say in the prompt which you did and how reliable the extraction is.

## Browse, and a live browser in any mode

```bash
bash scripts/pair.sh --engine codex --mode browse \
  --domains github.com,githubusercontent.com --prompt-file /abs/task.md

# a review that checks the code against the running page:
bash scripts/pair.sh --engine codex --mode review --cwd /abs/repo \
  --domains localhost:5173 --prompt-file /abs/review.md
```

`--domains` opens the browser in any mode; browse requires it. Browse runs with
no repository in reach. Review, consult, ideate and research keep the model
read-only with the browser added, so the model can compare a page with the code
that renders it. Codex then reaches the browser through a broker (below), Gemini
on agy through its gate; Gemini on OpenCode supports the browser in browse only.

What the script does:

- starts a fresh, logged-out headless Chrome through agent-browser, **outside**
  the engine's sandbox, with its socket in a private temp directory, from that
  empty directory (agent-browser reads `./agent-browser.json` from its working
  directory, and a repo could ship one);
- allows only the domains you pass, each plus its subdomains, marks page text as
  untrusted, and sends screenshots and downloads to `WORK_DIR/shots` in browse,
  `RUN_DIR/shots` otherwise (never into a repo);
- pins a local host to its port: `--domains localhost:5173` lets pages load only
  from `localhost:5173`, because the allow-list ignores ports and every
  agent-browser session on this machine listens on loopback (Chrome's debugging
  port, and a stream socket that accepts mouse and keyboard input). `open` and
  `read` refuse another local port, a click that lands on one goes back with
  exit 3, and `eval` is off while a local host is allowed. The dev server's own
  scripts can still reach other local ports; serve only code you trust;
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

- **Gemini** has no sandbox, so its shell is confined by rule: on agy the gate
  allows `pair-browser` (plus `pair-fs` outside browse), on OpenCode the agent
  rules allow only `pair-browser`; not `agent-browser`, not `curl`, and
  redirection and `$(...)` are refused. Tested: it drove the browser and could
  not close it.
- **Codex in review, consult, ideate or research** stays read-only. Its sandbox
  proxy cuts every socket but one: a broker's (`pair_broker.py`), started outside
  the sandbox. Codex's `pair-browser` is a thin client that sends its arguments
  there, and the broker runs the grammar wrapper. Codex never touches
  agent-browser's own socket, because a client on that socket can relaunch the
  browser without its allow-list. A preflight inside the same sandbox checks the
  broker answers and the internet, the repo and the browser's socket do not,
  before Codex starts.
- **Codex in browse** runs with workspace write and network on. Its shell is not
  filtered, so the wrapper is a convention for it, not a wall: it can reach any
  host with curl, and a model that sets out to read the wrapper can find the
  socket and drive the browser directly, which runs outside the sandbox and can
  write a screenshot anywhere you can. The allow-list still binds every page the
  browser loads, unless the model relaunches the browser itself. For untrusted
  pages, prefer browse on Gemini, or Codex in research mode with `--domains`.

List every domain the task needs: where redirects land, and the domains the page
loads its styles and scripts from (GitHub needs `githubassets.com` too), because
the allow-list blocks the page's own requests as well. Logged-in sites are not
supported, on purpose.

Screenshots stay in the shots folder. Copy the ones the user should see
somewhere they can open, and verify each quote against the page or its raw
source before you repeat it.

A browse session holds untrusted page content and network access together, so
keep the prompt free of secrets, keep the working directory empty, browse only
domains you would trust with that, and verify every quote against the page. In
testing, a quote was exact but left out two relevant passages the model had seen.
A review with `--domains` holds the repo and the pages together but no way out
besides the allow-listed domains: list only the ones the page needs.

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
- (2026-11-02) Codex's read-only sandbox reaches one unix socket only through a
  permission profile with `network.unix_sockets`, and that also needs
  `network.enabled`, which opens the internet unless the network proxy runs
  with no domain rules. A proxy domain rule for `localhost` ignores the port, so
  the shell never gets one.
