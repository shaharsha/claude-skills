# reviving-sessions

Bring back Claude Code sessions the Claude desktop app cannot see: sessions started with `claude -p`, from the VS Code extension or under another account; sessions stranded on disk when their worktree was deleted; headless lanes that all read "General coding session"; renames that fail or land in only one account. Also reads what an ended or app-invisible session said, without the thousands of tool calls around it.

For sessions the desktop app already lists, its own tools (`list_sessions`, `send_message`, `list_events`, `start_session`, `set_session_title`, `archive_session`) do the job, and this skill stays out of the way.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Each Claude Code client lists only the sessions **it** created. The VS Code extension enumerates `~/.claude/projects/`, so it sees everything; the desktop app reads its own index, so a session started anywhere else is invisible to it, to its sidebar and to every one of its session tools. The fix — the app's undocumented `claude://resume` deep link — is not in `claude --help`, so an agent working from the help text reports the task impossible.

Once a session is visible, three more traps follow it: the app and the CLI use **different session ids** for the same session, a rename lands in **one account's** index only, and a headless session gets **no title at all**.

Transcripts have their own storage traps:

- **Transcripts are filed by working directory.** Delete a worktree and every session that ran in it disappears from the session list — while sitting intact on disk.
- **A session that changes directory gets a second file.** One session, several copies, only the newest current.
- **Most `type: "user"` entries are not from a human.** They carry tool results, and the harness injects turns that read like speech.

## What it does

```
the desktop app's index              ~/.claude/projects/*/*.jsonl
        │                                     │
        ├── claude://resume ◀── adopt ────────┤  a session the app never indexed
        ├── claude://code/new                 │
        │                                     ├── ccread ──▶ 🟢/🟡/⚪ id span title (+ worktree-filed, N copies)
        └── set_session_title                 ├── ccread <id> ──▶ the conversation, tool calls collapsed
            (+ custom-title record)           └── ccread --all --grep ──▶ search every session's prose
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install building-agents@shaharsha-skills
```

**Monorepo path:** `skills/reviving-sessions/`

## Requirements

Python 3 standard library. Nothing to install. The deep links need the Claude desktop app on macOS.

`ccread` defaults to Claude Code's transcript root, `~/.claude/projects`. Point it elsewhere with `--root` or `CCREAD_ROOT` for another harness that writes the same JSONL shape.

## Quick start

```bash
open "claude://resume?session=<uuid>"            # adopt a CLI-started session into the desktop app

scripts/ccread                                   # every session on disk, live and stale
scripts/ccread --since 2026-07-29                # only recent ones
scripts/ccread "TOR-55"                          # read it as a conversation
scripts/ccread "TOR-55" --last 20                # the end of it
scripts/ccread "TOR-55" --tools                  # with tool calls interleaved
scripts/ccread --all --grep "credential" --since 2026-07-29
```

Sessions resolve by id prefix **or** by a substring of the title or cwd, so you rarely need a uuid. The title shown is the human-set one (`customTitle`) when a session has been renamed, falling back to the auto-generated `aiTitle`.

## Gotchas

- **Run `list_sessions` before adopting.** *"Session not found"* has two causes — the app never indexed it, or you passed the CLI-side id — and adopting an already-indexed session writes a second sidebar row.
- **Never archive a row to tidy it.** `archive_session` stops the session's process and cleans up its worktree. A duplicate row costs nothing.
- **`--from 07:00` on an overnight session.** A bare `HH:MM` is anchored to the session's *last* day. Pass a full ISO stamp when you want to be explicit.
- **Repairing an orphaned transcript: parse per line, never `sed`,** and copy rather than move. SKILL.md has a working snippet.
- **`ccread` reads; it never writes.** Recovery is a separate, deliberate step.

## History

Until October 2026 this skill was `working-with-other-sessions` and also carried a file-based messaging channel (`ccsend`, `ccarm`, `ccpeers`, `ccstatus`). The desktop app's own `send_message` replaced it: it needs no arming and reaches idle sessions. Those scripts are in this repo's git history.

## Related skills

- [`writing-project-instructions`](../writing-project-instructions) — for turning what you learn from a transcript into a durable rule
- [`codex-review`](../codex-review) — a second opinion on work a transcript describes

## License

MIT
