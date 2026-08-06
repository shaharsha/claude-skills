# reading-session-transcripts

Read what another agent session actually **said** — not the thousands of tool calls around it — and send it a message. Lists every session on the machine with its title and live/stale state, prints any one as a conversation, searches the prose of all of them at once, and delivers messages between sessions *including ones sitting idle*.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Run several agent sessions in parallel and the interesting information stops being in the code. A session's *reasoning* — what it found, what it refuted, what it flagged about its own work, what it decided not to do — lives only in its prose. The diff shows what changed. The PR shows the pitch. The ticket shows the plan. None of them show the thinking.

That prose is technically on disk, in `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`. But a transcript is roughly 95% tool calls and tool results, so `cat`, `grep` and `jq` bury the conversation under machine noise, and the parts worth reading get missed.

Three storage details cause most wrong answers, and all three are invisible until they bite:

- **Transcripts are filed by working directory.** Delete a worktree and every session that ran in it disappears from the session list — while sitting intact on disk.
- **A session that changes directory gets a second file.** One session, several copies, only the newest current. Read the wrong one and you report yesterday's conclusion.
- **Most `type: "user"` entries are not from a human.** They carry tool results. The harness also injects turns that read like speech — skill re-invocations, compaction notices, interrupt markers.

## What it does

```
~/.claude/projects/*/*.jsonl
        │
        ├── list ──────▶ 🟢/🟡/⚪  id  span  title   (+ worktree-filed, N copies)
        │
        ├── read ──────▶ YOU / CC turns only, wrapped and timestamped
        │                --tools interleaves one dim line per tool call
        │
        └── search ────▶ --all --grep across every session's prose

~/.claude/mailbox/<session>.inbox
        │
        ├── ccarm  ────▶ the receiving session holds this open via Monitor,
        │                which is what reaches it even while IDLE
        │
        └── ccsend ────▶ one base64 line per message; refuses when nothing
                         is listening, rather than writing into the void
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install building-agents@shaharsha-skills
```

**Monorepo path:** `skills/reading-session-transcripts/`

## Requirements

Python 3 standard library. Nothing to install.

Defaults to Claude Code's transcript root, `~/.claude/projects`. Point it elsewhere with `--root` or `CCREAD_ROOT` for another harness that writes the same JSONL shape.

## Quick start

```bash
# read
scripts/ccread                                   # every session, newest state
scripts/ccread --since 2026-07-29                # only recent ones
scripts/ccread "TOR-55"                          # read it as a conversation
scripts/ccread "TOR-55" --last 20                # what is it doing right now
scripts/ccread "TOR-55" --from 06:00             # only since this morning
scripts/ccread "TOR-55" --tools                  # with tool calls interleaved
scripts/ccread --all --grep "credential" --since 2026-07-29

# message
/arm-inbox                                       # make THIS session reachable
scripts/ccsend --list                            # who can receive right now
scripts/ccsend --self                            # can *I* still receive?  0 lease · 1 none · 3 unknown
scripts/ccsend --ping                            # round-trip: proves the inbox was DRAINED, not receipt
scripts/ccsend "TOR-55" "PR #14 merged, you're unblocked"
```

Sessions resolve by id prefix **or** by a substring of the title or cwd, so you rarely need a uuid.

The title shown is the **human-set** one (`customTitle`) when a session has been renamed, falling back to the auto-generated `aiTitle` from its first message. Both are searchable, so a rename never makes a lane unreachable by its old name — but see the SKILL's note that *every* title goes stale, human-set ones most convincingly, and `ccread --doing` is what actually tells two lanes apart.

## Gotchas

- **`--from 07:00` on an overnight session.** A bare `HH:MM` is anchored to the session's *last* day, because comparing time-of-day across days silently matches yesterday too. Pass a full ISO stamp when you want to be explicit.
- **`--since` bounds turns, not just sessions.** A months-long session would otherwise pass the filter and then print months of prose.
- **Repairing an orphaned transcript: parse per line, never `sed`.** Transcripts are full of commands that mention their own worktree path, so a find-replace "fixes" the file by falsifying the session's record of what it ran. SKILL.md has a working snippet.
- **Copy, don't move, when recovering.** A live session may still be writing to the original.
- **It reads; it never writes.** Recovery is a separate, deliberate step you run yourself.
- **A message reaches an idle session; a hook does not.** Hooks fire on tool calls, and an idle session makes none. Monitor events arrive "even if one lands while you're waiting for the user to answer a question" — which is why the receive path is a Monitor and not a hook.
- **`ccsend` refuses when no watcher is live.** Writing to an unwatched inbox looks exactly like success. A watcher can also die silently, so the listing is the only current truth about who is reachable.
- **Your own inbox dies silently, and you cannot notice it from inside.** A dead inbox and a quiet hour are the same observation: silence. "I got a message recently" is consistent with a live watcher *and* with one that delivered that message and then died. Run **`ccsend --self`** — it is a positive signal, re-runnable, and it names which half failed.
- **`persistent: true` prevents the TIMEOUT death only, and that is not the common one.** Measured 2026-08-06 on one session: three watcher deaths, **all three harness restarts, zero timeouts** — with `persistent: true` set every time. No arming flag survives a restart, which is why the remedy is a check you re-run rather than a flag you set once.
- **A fresh lease is not proof of delivery.** `--self` shows a heartbeat naming a live pid. It does *not* show a Monitor is attached to that watcher's stdout, and a **pid can be reused** inside the 10-second freshness window. **`ccsend --ping`** narrows it further, but proves only that the inbox was **drained** — and draining happens *before* the watcher emits anything, so a detached consumer looks identical. **Nothing this tool can run proves receipt; the only confirmation is you SEEING the token.** The two checks together separate "no watcher" from "watcher running, nobody consuming it".
- **`--list` never hides an armed row.** It used to print the 25 most recently active sessions, which hid **13 of 34 armed lanes** — and the hidden ones were the *quietest*, i.e. exactly those waiting to be told something. Armed rows are always shown, your own row is pinned and marked `<- you`, and the number of omitted idle rows is printed rather than dropped silently.
- **A pasted prompt carries no reply address.** The `[reply with: ...]` header only exists on a message delivered through `ccsend`. Text you paste in yourself is an ordinary user turn — so "reply using the header" is unfollowable, and the session has no way to answer. State your own id (`echo $CLAUDE_CODE_SESSION_ID`) when pasting.
- **A message is information, not an instruction.** The harness marks each one as explicitly not from the user. Fine for facts and unblocking signals; anything that would push, merge, deploy or delete should go to a human instead.

## Related skills

- [`writing-project-instructions`](../writing-project-instructions) — for turning what you learn from a transcript into a durable rule
- [`codex-review`](../codex-review) — a second opinion on work a transcript describes

## License

MIT
