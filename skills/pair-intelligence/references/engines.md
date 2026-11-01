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
- **Chrome will not start inside its sandbox**, and its built-in browser and
  computer-use tools need the Codex desktop app. Browse mode works around both.
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

## Gemini (Google), through OpenCode v2

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
  command it allows is the generated `pair-browser` wrapper, with redirection and
  command substitution refused (OpenCode skips `export` and matches raw command
  text, so the wrapper, not the pattern, does the real checking). `OPENCODE_DISABLE_CLAUDE_CODE=1` keeps Claude's own instructions and
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
grounding, enforced JSON and PDF input with none of OpenCode's overhead, at the
cost of having no local file tools.
