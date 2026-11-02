# Engines: Codex and Gemini

`scripts/pair.sh` already handles everything below. Read this when a run fails,
when you need a flag the script does not expose, or when you call a CLI by hand.

## Codex (OpenAI)

Tested on codex-cli 0.165.0, signed in with a ChatGPT plan.

- **Model:** `gpt-6.1-sol` by default. Efforts `low` to `max`. Usage counts against
  the ChatGPT plan's limits, not an API bill.
- **What the script passes on every call:** `--json` (events on stdout), `-o` (the
  final answer), `--skip-git-repo-check`, the sandbox as both `-s` and
  `-c sandbox_mode=...`, `approval_policy="never"`, `web_search`
  (`disabled` / `cached` / `live`), CLAUDE.md as a fallback instruction file, and
  the prompt on stdin.
- **`--ignore-user-config`, on every call (codex_review.sh too).** This machine's
  `~/.codex/config.toml` loads the Linear MCP server (with write tools) and the
  ChatGPT app's browser, Chrome and computer-use plugins, all running outside the
  sandbox. A reviewer of untrusted code gets none of them. Auth still comes from
  `~/.codex`; the script restates `project_doc_max_bytes=400000`, which that
  config raised so torque's ~394 KB CLAUDE.md is not cut at 32 KiB.
- **A live browser outside browse** (`--domains` in review, consult, ideate,
  research) swaps the sandbox flags for a permission profile:
  `default_permissions="pair_browse"` extending `:read-only`, with
  `network.enabled=true`, `--enable network_proxy` (no domain rules, so the proxy
  refuses every host) and one `network.unix_sockets` entry, the broker's. Tested
  with `codex sandbox`: the broker answers; the internet gets 403 at the proxy;
  other sockets, the repo and `/tmp` refuse; reads still work. `network_proxy` is
  marked experimental, so `pair_preflight.py` re-checks all four inside the same
  profile before every such run, and Codex does not start if one fails (exit 71).
- **Success** is a `turn.completed` event with a non-empty answer file. Codex exits
  0 when its tools failed, so the exit code alone means nothing.
- **Sessions:** `codex exec resume <id>` continues one; the script maps your
  `--name` labels to ids in `~/.cache/pair-intelligence/sessions.json`, under a
  lock, and a resumed session keeps its engine, mode and directory.
- **What the event stream leaves out:** image views (`view_image`) do not appear in
  `--json` events; they are in the session log under `~/.codex/sessions/`. Judge an
  image round by its answer (coordinates, quoted on-screen text). A browse round can
  read hundreds of thousands of input tokens, almost all from cache.

Traps, each seen in testing:

- **Hangs on stdin.** With a prompt argument and an open, non-terminal stdin it
  waits forever on "Reading additional input from stdin" (upstream issue #20919,
  open). Send the prompt on stdin with `-`, or redirect `< /dev/null`.
- **`-i` swallows the prompt.** The image flag takes several values, so a prompt
  after it is read as a file name. Give image paths in the prompt instead; Codex
  opens them itself.
- **Resume drops the sandbox.** A resumed session falls back to the global config
  (often `danger-full-access` on this machine) unless the sandbox is passed again
  with `-c sandbox_mode=...`.
- **`codex exec --search` is rejected.** Use `-c web_search="live"`.
- **Nested sandboxes fail.** Started inside another tool's sandbox it reports
  `sandbox_apply: Operation not permitted` or that "the shell host failed during
  handshake", and may still exit 0 with an apology for an answer. Run it outside.
- **Chrome will not start inside its sandbox**, and its built-in browser cannot
  run from `codex exec` ("The browser access host is unavailable": it needs a
  pipe only the desktop app provides, and its Chrome backend is your logged-in
  Chrome). The script's own browser works around both.
- **agent-browser's socket is not safe to hand over.** A client with different
  settings makes the daemon relaunch Chrome its way, allow-list gone (measured).
  Hence the broker: Codex's `pair-browser` sends its arguments to
  `pair_broker.py`, which runs the grammar wrapper outside the sandbox.
- **`codex mcp-server` was removed** (0.154). Its replacement, `codex app-server`,
  is marked experimental, so this skill keeps to `codex exec`.
- **PDFs are not accepted as input.** Convert them first.
- **It cannot run code read-only on macOS:** `python3` dies on its temp and cache
  directories (`couldn't create cache file ... Operation not permitted`), and the
  turn still ends `ok`. Its runtime claims are deductions; it usually says so.

By hand, read-only:

```bash
codex exec -s read-only -c 'sandbox_mode="read-only"' --skip-git-repo-check \
  --json -o /abs/answer.md - < /abs/prompt.md > /abs/events.jsonl
```

## Gemini (Google), through agy (the default)

Tested on the Antigravity CLI (`agy`) 1.4.12 with a Gemini API key, 2026-11-02.

- **Auth: Vertex AI or an API key, never the Antigravity login.** Google's FAQ
  forbids driving agy from other tools with that login. `PAIR_AGY_AUTH` picks:
  - `vertex` (what `auto`, the default, picks when exactly one
    `~/.config/gcloud/adc-agy-*.json` exists, or `PAIR_AGY_ADC` names one):
    plain Vertex AI on the GCP project in that ADC copy's `quota_project_id`,
    billed to that project (startup credits). agy reads the project from that
    field before `GOOGLE_CLOUD_QUOTA_PROJECT`, and the main
    `application_default_credentials.json` pins another client's project, so the
    script refuses it. `meta.json` records `auth: vertex:<project>`. If agy
    reports `Reauthentication failed`, run `gcloud auth application-default login`
    and refresh the copy (`~/.local/bin/agy-vertex --refresh-adc` on this Mac);
  - `key`: `"modelProvider": "gemini"` in `--settings` and the key in
    `GEMINI_API_KEY` (from the environment, else OpenCode's `auth.json`). Never
    combine the two: `modelProvider` switches a Vertex run back to the key.
  Neither secret reaches argv or the output.
- **Models:** the id carries the effort: `gemini-4-argon-high` (the script adds
  `-<effort>` to `--model gemini-4-argon`), `gemini-3.8-flash-low`,
  `gemini-3.1-pro-high`. `agy models` lists them.
- **What the script sets up:**
  - a private HOME (`~/.local/share/pair-intelligence/agy-home`, `PAIR_AGY_HOME`)
    so your agy settings, login, hooks and MCP servers stay out;
  - an empty workspace under `$TMPDIR`, outside any repository, removed after
    the run. The project is a folder agy may read, never its workspace (see
    traps);
  - a PreToolUse hook in that home, `agy_gate.py`, which decides every tool call
    from this run's `agy-policy.json`: reads only under `--cwd` (plus images and
    the shots folder), no `.env` or key files under any name, case or link;
    shell commands only `pair-fs`, `pair-browser` (with `--domains`) and
    `pair-fetch` (with `--web live`), and only when zsh would take every word
    literally (outside quotes just letters, digits and `_./:@,+=%-`; nothing but
    `$`, backquote, backslash and `!` refused inside double quotes; single quotes
    free); `search_web` unless `--web off`; every other tool refused, its own
    `read_url_content` included. Its decisions land in `RUN_DIR/gate.log`;
  - a settings floor under the gate: writes, MCP, URL reads and actuation, and
    the metacharacter pattern denied, so a broken gate still cannot write;
  - stream-json in and out, `--print-timeout`, `--disable-slash-commands`,
    `--conversation <id>` to resume.
- **`pair-fs`** (`pair_fs.py`): `ls`, `find GLOB`, `grep` (ripgrep, gitignore
  aware) and `git status|diff|log|show|blame|ls-files|cat` with an allow-list of
  flags. Every path is resolved and must stay inside the roots. Files named like
  secrets (`.env*`, keys, `.netrc`...; any case, through any link) never print.
  Git has many ways to name a file's contents, so none is accepted: a revision
  has no `:` (no `HEAD:file`, `:0:file`, reflog dates) and may not be a blob id,
  `-L` is blame-only and numeric, `--follow` is gone, and every diff, show and
  log excludes secret files by pathspec. `pair-fs git cat REV PATH` reads a file
  at a revision with the path checked. Git runs only when the repository sits
  inside the roots (its history would show the rest) and its config names no
  program (filters, `gpg.program`, pagers, drivers, includes and the like); on
  top, fsmonitor, pager, external diff, textconv, hooks and signature checks
  are switched off per call. Protection is by file name: a secret pasted into
  `config.py` is just code to it.
- **`pair-fetch`** (`pair_fetch.py`, `--web live` only): one public http(s) page
  as text, checked on every redirect against loopback, private and metadata
  addresses, wrapped in untrusted-content markers.
- **Success** is a `result` event with status SUCCESS, a non-empty response and
  no `denied_actions`. `RUN_DIR/tools.txt` lists every tool call with the gate's
  refusals, which is how you see what Gemini read and searched.

Traps, each seen in testing:

- **A project as workspace runs its code.** agy loads `.agents/` hooks, MCP
  servers, rules and agents from its workspace and each parent up to the repo
  root, and it started a repo's `mcp_config.json` server even with `mcp(*)`
  denied. Hence the scratch workspace. A side effect: the repo's AGENTS.md is
  not loaded; put the conventions that matter in the prompt.
- **An Ask ends the run silently.** Anything its rules leave at "ask" is
  auto-denied in headless mode, and the run then ends with an empty response,
  status SUCCESS and exit 0. The gate answers every call so this does not happen;
  if it does, the script reports `STATUS=denied`.
- **No list, grep or page tools in key mode.** The model gets read, write, shell,
  search and agent-management tools only; `pair-fs` and `pair-fetch` fill the
  gap. Without a fetcher it ran 12 searches and opened no page.
- **Rules cannot govern search or scheduling.** `search_web`, `schedule`,
  `send_message` and the subagent tools have no permission action, and
  `read_url(*)` does not stop search; the gate does.
- **Its own browser tools attach to your real Chrome** (DevTools MCP, logged-in
  profile). The gate refuses them; use `--domains`.
- **Its shell is zsh.** A command line is expanded before any wrapper sees it,
  and a glob qualifier such as `*(e:'cmd':)` runs code (measured: `*(.)`
  expanded). Hence the gate's word-by-word check.
- **Its own `--print-timeout` returns partial output as SUCCESS, exit 0**; only
  stderr says "print timeout ... returning partial output". The script reports
  that as `STATUS=timeout` (exit 124) and keeps the partial answer.
- **`--sandbox` and `--mode plan` are not read-only:** the first confines only
  shell commands and leaves the project writable, the second is a prompt prefix.
- **Hangs on stdin**, like the others: the script feeds stream-json from a file.

## Gemini, through OpenCode v2 (`--backend opencode`)

The fallback. Same model and key, about three times the input tokens per call
(OpenCode's system prompt), no web search, and no live browser outside browse.
In the 2026-11-02 comparison (same model and effort) the two matched on a review,
a screenshot with five planted defects (both found all five) and a consult.
OpenCode won research until agy got `pair-fetch`; after that agy read the same
primary sources (API reference, all six SDK READMEs) and cited them directly.

Tested on OpenCode 2.2.5 with a Gemini API key.

- **Binary:** `/Applications/OpenCode.app/Contents/Resources/opencode-cli` (the
  desktop app's v2 CLI). The `opencode` on PATH may be the older v1, whose flags
  differ, and both share one database already migrated to v2, so do not drive it
  with v1. Override the path with `PAIR_OPENCODE`.
- **Models:** `gemini-4-argon` by default (no free tier: about $2 per million input
  and $10 per million output tokens, set to double on Dec 1 2026);
  `gemini-3.8-flash` has a free tier and is fast. Effort is the variant:
  `#low`, `#medium`, `#high`. Argon at low spent no reasoning tokens and got a
  simple check wrong, so the script defaults to medium or high.
- **What the script passes:** `run --standalone --agent pair --format json`, the
  model as `google/<model>#<effort>`, `-f` per image, `-s <id>` to continue a
  session, and the prompt on stdin (an argument would show in `ps`).
- **The `pair` agent** is injected through `OPENCODE_CONFIG_CONTENT`: deny
  everything, then allow read, glob and grep, plus webfetch unless the mode's web
  setting is `off` (review and browse default to off); deny `.env` files. Tools it
  may not use are not offered to the model at all. In browse mode the only shell
  command it allows is the generated `pair-browser` wrapper, with redirection,
  `$`, backquotes, parentheses, braces and `~` refused on the raw text (zsh
  runs code from a glob qualifier); OpenCode skips `export` and matches raw
  command text, so the wrapper, not the pattern, does the real checking. `OPENCODE_DISABLE_CLAUDE_CODE=1` keeps Claude's own instructions and
  skills out of its context.
- **Events:** `step_start`, `text`, `tool_use`, `step_finish` (tokens, cost and a
  `reason`: `tool-calls` mid-turn, `stop` at the end) and `error` (for example
  `provider.no-route` for a bad model id). A turn whose last step did not finish
  with `stop` is reported `STATUS=incomplete`; the answer file then holds only
  what arrived. It exits 1 on an
  error and also when one of its tools failed, so the script reads the events.

Traps:

- **Hangs on stdin**, like Codex. Keep stdin closed.
- **No web search:** the search tool appears but every call returns "Web search
  cancelled". `webfetch` works for URLs you give it.
- **Your global OpenCode config still loads**, including its MCP servers. The
  `pair` agent cannot call their tools, but they start, and their credentials sit
  in that file.
- **v2 reads `AGENTS.md`, not `CLAUDE.md`.** A repo's CLAUDE.md conventions do not
  reach Gemini; put what it needs in the prompt.
- **No schema enforcement.** Ask for the layout in the prompt and check it.
- **`--standalone` matters:** without it, runs go through the desktop app's shared
  background service.

Not wired, but worth knowing: calling the Gemini API directly gives Google Search
grounding, enforced JSON and PDF input with no agent overhead, at the cost of
having no local file tools.
